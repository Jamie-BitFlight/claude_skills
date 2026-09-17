"""Tests for how a refused GraphQL query reaches the single-item status path.

``fetch_item_status`` returns a string, and the empty string is already a real
answer: "this issue carries no status label". In a sandbox that serves REST but
rejects GraphQL, the refusal was caught and converted into that same empty
string, so the single-item path repeated the bug ``batch_fetch_statuses`` was
fixed for — the caller was told something about the issue when nothing had been
learned about it.

The refusal now propagates. Every other failure keeps its empty-string fallback,
so a missing token or an unreachable API still degrades rather than raises.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from github import GithubException

from backlog_core import gh_client
from backlog_core.models import BacklogError, BacklogItem, GitHubUnavailableError, GraphQLUnavailableError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_REFUSAL_MESSAGE = "GitHub GraphQL is not available from Claude Code sessions; use the REST API"


def _item(issue: str = "#42") -> BacklogItem:
    """Build a minimal backlog item carrying the given issue reference."""
    return BacklogItem(title="An item", issue=issue, section="P1", status="status:in-progress")


class _Repo:
    """Minimal stand-in for the PyGithub repository ``get_github`` returns."""

    full_name = "owner/repo"


def _patch_repo(mocker: MockerFixture) -> None:
    """Point ``fetch_item_status`` at a repository stub instead of the network."""
    mocker.patch.object(gh_client, "get_github", return_value=_Repo())


class TestFetchItemStatusSurfacesTheRefusal:
    """A refused query must not reach the caller disguised as an absent status label."""

    def test_a_refusal_propagates(self, mocker: MockerFixture) -> None:
        _patch_repo(mocker)
        mocker.patch.object(gh_client, "_fetch_issue_graphql", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE))

        with pytest.raises(GraphQLUnavailableError):
            gh_client.fetch_item_status(_item())

    def test_the_raised_error_names_the_cause(self, mocker: MockerFixture) -> None:
        _patch_repo(mocker)
        mocker.patch.object(gh_client, "_fetch_issue_graphql", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE))

        with pytest.raises(GraphQLUnavailableError, match="GraphQL is not available"):
            gh_client.fetch_item_status(_item())


class TestFetchItemStatusKeepsItsOtherFallbacks:
    """Only the refusal changed. Every other degradation still returns a status string."""

    def test_a_generic_backlog_error_still_returns_no_status(self, mocker: MockerFixture) -> None:
        _patch_repo(mocker)
        mocker.patch.object(gh_client, "_fetch_issue_graphql", side_effect=BacklogError("query rejected"))

        assert gh_client.fetch_item_status(_item()) == ""

    def test_a_github_exception_still_returns_no_status(self, mocker: MockerFixture) -> None:
        _patch_repo(mocker)
        mocker.patch.object(
            gh_client,
            "_fetch_issue_graphql",
            side_effect=GithubException(status=500, data={"message": "Server Error"}, headers={}),
        )

        assert gh_client.fetch_item_status(_item()) == ""

    @pytest.mark.parametrize(
        "transport_error",
        [
            gh_client.requests.exceptions.ConnectionError("connection dropped"),
            gh_client.requests.exceptions.Timeout("request timed out"),
            gh_client.requests.exceptions.ChunkedEncodingError("chunk lost"),
            gh_client.requests.exceptions.ContentDecodingError("bad encoding"),
        ],
    )
    def test_a_transport_failure_still_returns_no_status(
        self, mocker: MockerFixture, transport_error: Exception
    ) -> None:
        _patch_repo(mocker)
        mocker.patch.object(gh_client, "_fetch_issue_graphql", side_effect=transport_error)

        assert gh_client.fetch_item_status(_item()) == ""

    def test_a_missing_token_still_returns_no_status(self, mocker: MockerFixture) -> None:
        """``get_github`` raising is the no-token path, not an environment-wide refusal."""
        mocker.patch.object(gh_client, "get_github", side_effect=GitHubUnavailableError("GITHUB_TOKEN not set"))

        assert gh_client.fetch_item_status(_item()) == ""

    def test_an_item_without_an_issue_returns_no_status(self, mocker: MockerFixture) -> None:
        graphql = mocker.patch.object(gh_client, "_fetch_issue_graphql")

        assert gh_client.fetch_item_status(_item("")) == ""
        assert not graphql.called
