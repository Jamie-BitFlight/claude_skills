"""Tests for how a refused GraphQL query reaches the listing path.

``batch_fetch_statuses`` returns a mapping, and an empty mapping is a real answer:
"no item carries a status". In a sandbox that serves REST but rejects GraphQL, the
refusal used to be converted into that same empty mapping, so every listing rendered
blank statuses and reported no reason.

Two guarantees are protected here. Every failed lookup reaches the caller as an
availability exception, and the caller that chooses to continue from cached statuses
says so in its output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import requests
from github import GithubException

from backlog_core import gh_client, operations
from backlog_core.models import (
    BackendUnavailableError,
    BacklogError,
    BacklogItem,
    GitHubUnavailableError,
    GraphQLUnavailableError,
    IssueStatus,
    Output,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pytest_mock import MockerFixture

_REFUSAL_MESSAGE = "GitHub GraphQL is not available from Claude Code sessions; use the REST API"


def _item(issue: str, title: str = "An item") -> BacklogItem:
    """Build a minimal open backlog item carrying the given issue reference."""
    return BacklogItem(title=title, issue=issue, section="P1", status="status:in-progress")


class _Repo:
    """Minimal stand-in for the PyGithub repository ``try_get_github`` returns."""

    full_name = "owner/repo"


class TestBatchFetchStatusesSurfacesTheRefusal:
    """Neither the GraphQL refusal nor a genuine failure may arrive disguised as an empty map."""

    def test_a_refusal_propagates(self, mocker: MockerFixture) -> None:
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(gh_client, "sync_issues_graphql", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE))

        with pytest.raises(GraphQLUnavailableError):
            gh_client.batch_fetch_statuses([_item("#42")])

    def test_a_generic_backlog_error_is_an_availability_failure(self, mocker: MockerFixture) -> None:
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(gh_client, "sync_issues_graphql", side_effect=BacklogError("query rejected"))

        with pytest.raises(BackendUnavailableError, match="query rejected"):
            gh_client.batch_fetch_statuses([_item("#42")])

    def test_a_github_exception_is_an_availability_failure(self, mocker: MockerFixture) -> None:
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(
            gh_client,
            "sync_issues_graphql",
            side_effect=GithubException(status=500, data={"message": "Server Error"}, headers={}),
        )

        with pytest.raises(BackendUnavailableError, match="Server Error"):
            gh_client.batch_fetch_statuses([_item("#42")])

    @pytest.mark.parametrize(
        "transport_error",
        [
            requests.exceptions.ConnectionError("connection dropped"),
            requests.exceptions.Timeout("request timed out"),
            requests.exceptions.ChunkedEncodingError("chunk lost"),
            requests.exceptions.ContentDecodingError("bad encoding"),
        ],
    )
    def test_a_transport_failure_is_an_availability_failure(
        self, mocker: MockerFixture, transport_error: requests.exceptions.RequestException
    ) -> None:
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(gh_client, "sync_issues_graphql", side_effect=transport_error)

        with pytest.raises(BackendUnavailableError, match=str(transport_error)):
            gh_client.batch_fetch_statuses([_item("#42")])

    def test_a_non_transport_exception_preserves_its_semantics(self, mocker: MockerFixture) -> None:
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(gh_client, "sync_issues_graphql", side_effect=RuntimeError("invalid response shape"))

        with pytest.raises(RuntimeError, match="invalid response shape"):
            gh_client.batch_fetch_statuses([_item("#42")])

    def test_a_try_get_github_failure_propagates_as_github_unavailable(self, mocker: MockerFixture) -> None:
        """A network error/500/rate limit resolving the repo itself is not a refusal either.

        This is the earlier of the two swallow points #3546 fixed: ``try_get_github``
        itself used to fold *any* ``GithubException`` from ``get_repo`` — not just a
        missing token — into the same ``None`` a missing token produces.
        """
        mocker.patch.object(
            gh_client, "try_get_github", side_effect=GitHubUnavailableError("GitHub repository unavailable")
        )

        with pytest.raises(GitHubUnavailableError):
            gh_client.batch_fetch_statuses([_item("#42")])

    def test_an_unreachable_backend_is_an_availability_failure(self, mocker: MockerFixture) -> None:
        mocker.patch.object(gh_client, "try_get_github", return_value=None)

        with pytest.raises(BackendUnavailableError, match="unable to create a GitHub client"):
            gh_client.batch_fetch_statuses([_item("#42")])

    def test_fetches_open_and_closed_issues_and_records_unlabeled_issues(self, mocker: MockerFixture) -> None:
        """Closed and unlabeled issues remain distinguishable from absent issues."""
        repo = _Repo()
        mocker.patch.object(gh_client, "try_get_github", return_value=repo)
        fetch = mocker.patch.object(
            gh_client,
            "sync_issues_graphql",
            return_value=[{"number": 42, "labels": [], "milestone": None, "state": "CLOSED"}],
        )

        result = gh_client.batch_fetch_statuses([_item("#42")])

        assert result == {42: IssueStatus(status="", milestone="", state="CLOSED")}
        fetch.assert_called_once_with(repo, "owner", "repo", state="OPEN,CLOSED")


class TestFetchItemStatusSurfacesTheRefusal:
    """The single-item fallback must not swallow the same refusal batch_fetch_statuses
    re-raises -- GraphQLUnavailableError is a BacklogError subclass, so a plain
    ``except (BacklogError, GithubException): return ""`` silently reports the
    refusal as "no status set" unless the refusal is caught and re-raised first."""

    def test_a_refusal_propagates(self, mocker: MockerFixture) -> None:
        mocker.patch.object(gh_client, "get_github", return_value=_Repo())
        mocker.patch.object(gh_client, "_fetch_issue_graphql", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE))

        with pytest.raises(GraphQLUnavailableError):
            gh_client.fetch_item_status(_item("#42"))

    def test_a_generic_backlog_error_still_falls_back_to_an_empty_string(self, mocker: MockerFixture) -> None:
        """Offline continuity is deliberate: an ordinary failure keeps its existing fallback."""
        mocker.patch.object(gh_client, "get_github", return_value=_Repo())
        mocker.patch.object(gh_client, "_fetch_issue_graphql", side_effect=BacklogError("query rejected"))

        assert gh_client.fetch_item_status(_item("#42")) == ""

    def test_a_github_exception_still_falls_back_to_an_empty_string(self, mocker: MockerFixture) -> None:
        mocker.patch.object(gh_client, "get_github", return_value=_Repo())
        mocker.patch.object(
            gh_client,
            "_fetch_issue_graphql",
            side_effect=GithubException(status=500, data={"message": "Server Error"}, headers={}),
        )

        assert gh_client.fetch_item_status(_item("#42")) == ""

    def test_an_item_with_no_issue_reference_short_circuits_before_any_call(self, mocker: MockerFixture) -> None:
        get_github = mocker.patch.object(gh_client, "get_github", return_value=_Repo())

        assert gh_client.fetch_item_status(_item("")) == ""
        assert not get_github.called


class TestBatchFetchStatusesSkipsAPointlessQuery:
    """A list with no numeric issue reference has nothing to look up."""

    def test_an_empty_item_list_issues_no_request(self, mocker: MockerFixture) -> None:
        get_github = mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        graphql = mocker.patch.object(gh_client, "sync_issues_graphql", return_value=[])

        assert gh_client.batch_fetch_statuses([]) == {}
        assert not get_github.called
        assert not graphql.called

    def test_items_without_a_numeric_issue_issue_no_request(self, mocker: MockerFixture) -> None:
        """A local-only backlog cannot be keyed by issue number, so the query is dead weight."""
        graphql = mocker.patch.object(gh_client, "sync_issues_graphql", return_value=[])
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())

        assert gh_client.batch_fetch_statuses([_item(""), _item("")]) == {}
        assert not graphql.called

    def test_one_numeric_issue_is_enough_to_query(self, mocker: MockerFixture) -> None:
        """The skip must not swallow a mixed list that does carry a lookup key."""
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        graphql = mocker.patch.object(gh_client, "sync_issues_graphql", return_value=[])

        gh_client.batch_fetch_statuses([_item(""), _item("#7")])

        assert graphql.called


class _Backend:
    """Backend stub exposing only what ``list_items`` reads."""

    supports_batch_status_fetch = True

    def __init__(self, items: list[BacklogItem]) -> None:
        self._items = items

    def list_work_items(self) -> list[BacklogItem]:
        return self._items

    def batch_fetch_statuses(self, items: list[BacklogItem], repo: str = "") -> dict[int, IssueStatus]:
        return gh_client.batch_fetch_statuses(items, repo)


def _patch_backend(mocker: MockerFixture, items: list[BacklogItem]) -> None:
    """Point ``operations.get_config()`` at a backend serving *items*."""
    mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=_Backend(items)))


def _warnings(result: Mapping[str, object]) -> list[str]:
    """Narrow the heterogeneous ``list_items`` result to its warning strings."""
    raw = result.get("warnings", [])
    return [str(entry) for entry in raw] if isinstance(raw, list) else []


class TestListItemsReportsBlankStatuses:
    """A listing that proceeds without live statuses has to say why."""

    def test_a_refusal_does_not_fail_the_listing(self, mocker: MockerFixture) -> None:
        """Serving the cache when the live query is refused is the documented behaviour."""
        _patch_backend(mocker, [_item("#42")])
        mocker.patch.object(operations, "batch_fetch_statuses", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE))

        result = operations.list_items(output=Output())

        assert result["count"] == 1

    def test_a_refusal_records_a_warning(self, mocker: MockerFixture) -> None:
        _patch_backend(mocker, [_item("#42")])
        mocker.patch.object(operations, "batch_fetch_statuses", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE))

        warnings = _warnings(operations.list_items(output=Output()))

        assert warnings, "a listing rendered without live statuses must carry a warning"

    def test_the_warning_names_the_cause(self, mocker: MockerFixture) -> None:
        """A reader has to be able to tell a refused query from an unset status."""
        _patch_backend(mocker, [_item("#42")])
        mocker.patch.object(operations, "batch_fetch_statuses", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE))

        warnings = _warnings(operations.list_items(output=Output()))

        assert any(_REFUSAL_MESSAGE in str(w) for w in warnings)

    def test_a_healthy_listing_carries_no_such_warning(self, mocker: MockerFixture) -> None:
        """The warning marks degradation, so a normal listing must stay clean."""
        _patch_backend(mocker, [_item("#42")])
        mocker.patch.object(
            operations,
            "batch_fetch_statuses",
            return_value={42: IssueStatus(status="status:in-progress", milestone="")},
        )

        warnings = _warnings(operations.list_items(output=Output()))

        assert not any("Live status unavailable" in str(w) for w in warnings)

    @pytest.mark.parametrize(
        "transport_error",
        [
            requests.exceptions.ConnectionError("connection dropped"),
            requests.exceptions.Timeout("request timed out"),
            requests.exceptions.ChunkedEncodingError("chunk lost"),
            requests.exceptions.ContentDecodingError("bad encoding"),
        ],
    )
    def test_a_transport_failure_excludes_unverified_statuses(
        self, mocker: MockerFixture, transport_error: requests.exceptions.RequestException
    ) -> None:
        _patch_backend(mocker, [_item("#42")])
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(gh_client, "sync_issues_graphql", side_effect=transport_error)

        result = operations.list_items(status="status:in-progress", output=Output())

        assert result["count"] == 0
        assert any(str(transport_error) in warning for warning in _warnings(result))
