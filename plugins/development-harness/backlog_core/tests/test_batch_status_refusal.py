"""Tests for how a refused GraphQL query reaches the listing path.

``batch_fetch_statuses`` returns a mapping, and an empty mapping is a real answer:
"no item carries a status". In a sandbox that serves REST but rejects GraphQL, the
refusal used to be converted into that same empty mapping, so every listing rendered
blank statuses and reported no reason.

Two guarantees are protected here. The refusal reaches the caller as a distinct
exception, and the caller that chooses to continue with blank statuses says so in
its output. Every other failure keeps its existing local-fallback behaviour, so an
offline read still serves the cache rather than raising.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from github import GithubException

from backlog_core import gh_client, operations
from backlog_core.models import BacklogError, BacklogItem, GraphQLUnavailableError, IssueStatus, Output

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
    """The GraphQL refusal must not arrive at the caller disguised as an empty map."""

    def test_a_refusal_propagates(self, mocker: MockerFixture) -> None:
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(gh_client, "sync_issues_graphql", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE))

        with pytest.raises(GraphQLUnavailableError):
            gh_client.batch_fetch_statuses([_item("#42")])

    def test_a_generic_backlog_error_still_falls_back_to_an_empty_map(self, mocker: MockerFixture) -> None:
        """Offline continuity is deliberate: an ordinary failure keeps serving the cache."""
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(gh_client, "sync_issues_graphql", side_effect=BacklogError("query rejected"))

        assert gh_client.batch_fetch_statuses([_item("#42")]) == {}

    def test_a_github_exception_still_falls_back_to_an_empty_map(self, mocker: MockerFixture) -> None:
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(
            gh_client,
            "sync_issues_graphql",
            side_effect=GithubException(status=500, data={"message": "Server Error"}, headers={}),
        )

        assert gh_client.batch_fetch_statuses([_item("#42")]) == {}

    def test_an_unreachable_backend_still_falls_back_to_an_empty_map(self, mocker: MockerFixture) -> None:
        """``try_get_github`` returning None is the no-token/no-network path, not a refusal."""
        mocker.patch.object(gh_client, "try_get_github", return_value=None)

        assert gh_client.batch_fetch_statuses([_item("#42")]) == {}


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

    def test_a_status_filter_uses_the_cached_status_when_live_status_is_unavailable(
        self, mocker: MockerFixture
    ) -> None:
        item = _item("#42")
        item.status = "status:in-progress"
        _patch_backend(mocker, [item])
        mocker.patch.object(operations, "batch_fetch_statuses", return_value={})

        result = operations.list_items(status="status:in-progress", output=Output())

        assert result["count"] == 1
