"""close_item and resolve_item refuse when the open-PR search fails.

A failed GitHub PR search used to return an empty list, so close and resolve went
ahead as if no open PR referenced the issue. These tests run the real
``gh_client.check_open_prs_for_issue`` with ``get_github`` failing, behind an
in-memory backend.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
import requests
from github import GithubException

from backlog_core import gh_client
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import BacklogError, BacklogItem, PullRequestRef
from backlog_core.operations import close_item, resolve_item

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _backend_with_failing_pr_search(mocker: MockerFixture) -> tuple[InMemoryBackend, MagicMock]:
    """Build an in-memory backend wired to a GitHub PR search that always fails.

    Args:
        mocker: pytest-mock fixture used to patch the backend's search method and
            the GitHub client it delegates to.

    Returns:
        A tuple of the configured backend and the mock replacing
        ``InMemoryBackend.check_open_prs_for_issue`` on that instance, so callers can
        assert on whether the search was invoked.
    """
    backend = InMemoryBackend()
    backend.put_work_item(BacklogItem.model_validate({"title": "Search failure item", "issue": "#5"}))

    def _search(issue_num: int, repo: str = "") -> list[PullRequestRef]:
        return gh_client.check_open_prs_for_issue(issue_num, "owner/repo")

    check_open_prs_mock = mocker.patch.object(backend, "check_open_prs_for_issue", side_effect=_search)
    mocker.patch("backlog_core.gh_client.get_github", side_effect=BacklogError("GraphQL error: timeout"))
    mocker.patch("backlog_core.operations.get_config", return_value=BacklogConfig(backend=backend))
    return backend, check_open_prs_mock


def _backend_with_network_failing_pr_search(
    mocker: MockerFixture, network_error: Exception
) -> tuple[InMemoryBackend, MagicMock]:
    """Build an in-memory backend wired to a GitHub PR search that fails at the transport level.

    Unlike ``_backend_with_failing_pr_search``, this patches ``get_github`` to raise a raw
    ``requests.exceptions`` error (as a real dropped connection or timeout would), rather than
    a ``BacklogError`` already wrapped by a mocked-out boundary. It exercises the unwrapped path
    through ``gh_client.check_open_prs_for_issue`` -- which only catches ``GithubException`` --
    to confirm the network error still surfaces as the refusal ``BacklogError``.

    Args:
        mocker: pytest-mock fixture used to patch the backend's search method and
            the GitHub client it delegates to.
        network_error: The transport-level exception ``get_github`` should raise.

    Returns:
        A tuple of the configured backend and the mock replacing
        ``InMemoryBackend.check_open_prs_for_issue`` on that instance, so callers can
        assert on whether the search was invoked.
    """
    backend = InMemoryBackend()
    backend.put_work_item(BacklogItem.model_validate({"title": "Search failure item", "issue": "#5"}))

    def _search(issue_num: int, repo: str = "") -> list[PullRequestRef]:
        return gh_client.check_open_prs_for_issue(issue_num, "owner/repo")

    check_open_prs_mock = mocker.patch.object(backend, "check_open_prs_for_issue", side_effect=_search)
    mocker.patch("backlog_core.gh_client.get_github", side_effect=network_error)
    mocker.patch("backlog_core.operations.get_config", return_value=BacklogConfig(backend=backend))
    return backend, check_open_prs_mock


def test_resolve_refuses_when_open_pr_search_fails(mocker: MockerFixture) -> None:
    """resolve_item raises BacklogError, and does not resolve the item, when the PR search fails.

    Before the fix, a failed search was read as "no open PRs" and resolve_item went
    ahead and marked the item done.
    """
    # Arrange
    backend, _ = _backend_with_failing_pr_search(mocker)

    # Act / Assert
    with pytest.raises(BacklogError, match=r"Open-PR search failed for issue #5.*force=True"):
        resolve_item(selector="Search failure item", summary="done")
    assert backend.list_work_items()[0].status != "done"


def test_close_refuses_when_open_pr_search_fails(mocker: MockerFixture) -> None:
    """close_item raises BacklogError, and does not close the item, when the PR search fails.

    Before the fix, a failed search was read as "no open PRs" and close_item went
    ahead and dismissed the item.
    """
    # Arrange
    backend, _ = _backend_with_failing_pr_search(mocker)

    # Act / Assert
    with pytest.raises(BacklogError, match=r"Open-PR search failed for issue #5.*force=True"):
        close_item(selector="Search failure item", reason="wontfix")
    assert backend.list_work_items()[0].status != "closed"


def test_resolve_with_force_skips_failing_open_pr_search(mocker: MockerFixture) -> None:
    """resolve_item(force=True) resolves the item without running the PR search at all.

    force=True must bypass the open-PR check entirely rather than run the failing
    search and swallow its error.
    """
    # Arrange
    _backend, check_open_prs_mock = _backend_with_failing_pr_search(mocker)

    # Act
    result = resolve_item(selector="Search failure item", summary="done", force=True)

    # Assert
    assert result.get("resolved") is True
    check_open_prs_mock.assert_not_called()


@pytest.mark.parametrize(
    "network_error",
    [
        GithubException(500, "server error"),
        requests.exceptions.ConnectionError("network blocked (proxy or firewall)"),
        requests.exceptions.Timeout("request timed out"),
    ],
    ids=["github-error", "connection-error", "timeout"],
)
def test_resolve_refuses_when_open_pr_search_fails_on_network_error(
    mocker: MockerFixture, network_error: Exception
) -> None:
    """resolve_item raises BacklogError, and leaves the item unresolved, on a raw network failure.

    Before the fix, only GithubException was caught in gh_client.check_open_prs_for_issue and
    operations._search_open_prs, so a raw requests.exceptions.ConnectionError/Timeout escaped
    both layers unwrapped and crashed resolve_item instead of producing the refusal BacklogError.
    """
    # Arrange
    backend, _ = _backend_with_network_failing_pr_search(mocker, network_error)

    # Act / Assert
    with pytest.raises(BacklogError, match=r"Open-PR search failed for issue #5.*force=True"):
        resolve_item(selector="Search failure item", summary="done")
    assert backend.list_work_items()[0].status != "done"


@pytest.mark.parametrize(
    "network_error",
    [
        GithubException(500, "server error"),
        requests.exceptions.ConnectionError("network blocked (proxy or firewall)"),
        requests.exceptions.Timeout("request timed out"),
    ],
    ids=["github-error", "connection-error", "timeout"],
)
def test_close_refuses_when_open_pr_search_fails_on_network_error(
    mocker: MockerFixture, network_error: Exception
) -> None:
    """close_item raises BacklogError, and leaves the item open, on a raw network failure.

    Before the fix, only GithubException was caught in gh_client.check_open_prs_for_issue and
    operations._search_open_prs, so a raw requests.exceptions.ConnectionError/Timeout escaped
    both layers unwrapped and crashed close_item instead of producing the refusal BacklogError.
    """
    # Arrange
    backend, _ = _backend_with_network_failing_pr_search(mocker, network_error)

    # Act / Assert
    with pytest.raises(BacklogError, match=r"Open-PR search failed for issue #5.*force=True"):
        close_item(selector="Search failure item", reason="wontfix")
    assert backend.list_work_items()[0].status != "closed"
