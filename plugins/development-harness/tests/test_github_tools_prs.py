"""Tests for backlog_list_merged_prs MCP tool and list_merged_prs operation.

Tests are structured in two layers:
- Operation layer: list_merged_prs() in operations.py, mocked at get_github boundary.
- Server layer: backlog_list_merged_prs tool via in-memory FastMCP Client.

No @pytest.mark.asyncio decorators — asyncio_mode = "auto" is set globally.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from backlog_core.models import BacklogError, Output
from backlog_core.server import mcp

from tests.helpers import call_mcp_tool

if TYPE_CHECKING:
    import pytest

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_MERGED_AT = datetime(2026, 3, 15, 12, 0, 0, tzinfo=UTC)
_MERGED_AT_STR = "2026-03-15T12:00:00Z"


def _make_pr(
    number: int = 1,
    title: str = "feat: add feature",
    merged_at: datetime | None = _MERGED_AT,
    author: str = "alice",
    url: str = "https://github.com/owner/repo/pull/1",
    head_ref: str = "feature-branch",
    body: str = "",
) -> MagicMock:
    """Build a MagicMock mimicking a PyGithub PullRequest object."""
    pr = MagicMock()
    pr.number = number
    pr.title = title
    pr.merged_at = merged_at
    pr.html_url = url
    pr.body = body
    pr.user = MagicMock()
    pr.user.login = author
    pr.head = MagicMock()
    pr.head.ref = head_ref
    return pr


async def _call(tool_name: str, params: dict | None = None) -> dict:
    """Call an MCP tool through the in-memory FastMCP transport and parse result.

    Delegates to tests.helpers.call_mcp_tool bound to this module's mcp server.
    """
    return await call_mcp_tool(mcp, tool_name, params)


# ---------------------------------------------------------------------------
# Operation layer: list_merged_prs()
# ---------------------------------------------------------------------------


def test_list_merged_prs_returns_only_merged_prs(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_merged_prs filters out closed-but-not-merged PRs."""
    # Arrange
    merged_pr = _make_pr(number=10, merged_at=_MERGED_AT)
    closed_pr = _make_pr(number=11, merged_at=None)
    mock_repo = MagicMock()
    mock_repo.get_pulls.return_value = [merged_pr, closed_pr]
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_merged_prs

    # Act
    result = list_merged_prs()

    # Assert
    assert result["count"] == 1
    prs = result["pull_requests"]
    assert isinstance(prs, list)
    assert len(prs) == 1
    first_pr = prs[0]
    assert isinstance(first_pr, dict)
    assert first_pr["number"] == 10


def test_list_merged_prs_returns_expected_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_merged_prs returns dicts with all required fields."""
    # Arrange
    pr = _make_pr(
        number=42,
        title="fix: resolve crash",
        merged_at=_MERGED_AT,
        author="bob",
        url="https://github.com/owner/repo/pull/42",
        head_ref="fix/crash",
    )
    mock_repo = MagicMock()
    mock_repo.get_pulls.return_value = [pr]
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_merged_prs

    # Act
    result = list_merged_prs()

    # Assert
    prs = result["pull_requests"]
    assert isinstance(prs, list)
    assert len(prs) == 1
    entry = prs[0]
    assert isinstance(entry, dict)
    assert entry["number"] == 42
    assert entry["title"] == "fix: resolve crash"
    assert entry["merged_at"] == _MERGED_AT_STR
    assert entry["author"] == "bob"
    assert entry["url"] == "https://github.com/owner/repo/pull/42"
    assert entry["head_branch"] == "fix/crash"


def test_list_merged_prs_respects_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_merged_prs stops collecting once limit is reached."""
    # Arrange
    prs_source = [_make_pr(number=i, merged_at=_MERGED_AT) for i in range(5)]
    mock_repo = MagicMock()
    mock_repo.get_pulls.return_value = prs_source
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_merged_prs

    # Act
    result = list_merged_prs(limit=3)

    # Assert
    assert result["count"] == 3
    pull_requests = result["pull_requests"]
    assert isinstance(pull_requests, list)
    assert len(pull_requests) == 3


def test_list_merged_prs_empty_when_no_merged(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_merged_prs returns empty list when all PRs are closed but not merged."""
    # Arrange
    mock_repo = MagicMock()
    mock_repo.get_pulls.return_value = [_make_pr(merged_at=None), _make_pr(merged_at=None)]
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_merged_prs

    # Act
    result = list_merged_prs()

    # Assert
    assert result["count"] == 0
    assert result["pull_requests"] == []


def test_list_merged_prs_filters_by_search_title(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_merged_prs includes only PRs whose title contains the search string."""
    # Arrange
    matching = _make_pr(number=1, title="fix: relates to #42", merged_at=_MERGED_AT)
    non_matching = _make_pr(number=2, title="chore: unrelated cleanup", merged_at=_MERGED_AT)
    mock_repo = MagicMock()
    mock_repo.get_pulls.return_value = [matching, non_matching]
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_merged_prs

    # Act
    result = list_merged_prs(search="#42")

    # Assert
    assert result["count"] == 1
    prs = result["pull_requests"]
    assert isinstance(prs, list)
    first_pr = prs[0]
    assert isinstance(first_pr, dict)
    assert first_pr["number"] == 1


def test_list_merged_prs_filters_by_search_body(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_merged_prs matches search against PR body when title does not match."""
    # Arrange
    pr_with_body_match = _make_pr(
        number=3, title="fix: small fix", body="Fixes #99 and resolves the issue", merged_at=_MERGED_AT
    )
    pr_no_match = _make_pr(number=4, title="chore: routine", body="nothing here", merged_at=_MERGED_AT)
    mock_repo = MagicMock()
    mock_repo.get_pulls.return_value = [pr_with_body_match, pr_no_match]
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_merged_prs

    # Act
    result = list_merged_prs(search="#99")

    # Assert
    assert result["count"] == 1
    prs = result["pull_requests"]
    assert isinstance(prs, list)
    first_pr = prs[0]
    assert isinstance(first_pr, dict)
    assert first_pr["number"] == 3


def test_list_merged_prs_search_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_merged_prs search comparison ignores case."""
    # Arrange
    pr = _make_pr(number=5, title="Fix: My Special Feature", merged_at=_MERGED_AT)
    mock_repo = MagicMock()
    mock_repo.get_pulls.return_value = [pr]
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_merged_prs

    # Act
    result = list_merged_prs(search="special feature")

    # Assert
    assert result["count"] == 1


def test_list_merged_prs_github_exception_raises_backlog_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_merged_prs wraps GithubException as BacklogError."""
    # Arrange
    from github import GithubException

    mock_repo = MagicMock()
    mock_repo.get_pulls.side_effect = GithubException(status=403, data="Forbidden", headers={})
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    import pytest
    from backlog_core.models import BacklogError
    from backlog_core.operations import list_merged_prs

    # Act / Assert
    with pytest.raises(BacklogError, match="GitHub API error"):
        list_merged_prs()


def test_list_merged_prs_output_messages_merged(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_merged_prs merges Output messages into returned dict."""
    # Arrange
    mock_repo = MagicMock()
    mock_repo.get_pulls.return_value = []
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_merged_prs

    out = Output()
    out.messages.append("pre-existing message")

    # Act
    result = list_merged_prs(output=out)

    # Assert
    assert "messages" in result
    messages = result["messages"]
    assert isinstance(messages, list)
    assert "pre-existing message" in messages
    assert "warnings" in result


def test_list_merged_prs_calls_get_pulls_with_closed_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_merged_prs queries get_pulls with state='closed'."""
    # Arrange
    mock_repo = MagicMock()
    mock_repo.get_pulls.return_value = []
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_merged_prs

    # Act
    list_merged_prs()

    # Assert
    call_kwargs = mock_repo.get_pulls.call_args
    assert call_kwargs is not None
    kwargs = call_kwargs.kwargs or {}
    assert kwargs.get("state") == "closed"


# ---------------------------------------------------------------------------
# Server layer: backlog_list_merged_prs tool
# ---------------------------------------------------------------------------


async def test_backlog_list_merged_prs_success_returns_merged_result() -> None:
    """backlog_list_merged_prs tool returns pull_requests list with count and output keys."""
    # Arrange
    fake_result = {
        "pull_requests": [
            {
                "number": 10,
                "title": "fix: crash",
                "merged_at": _MERGED_AT_STR,
                "author": "alice",
                "url": "https://github.com/owner/repo/pull/10",
                "head_branch": "fix/crash",
            }
        ],
        "count": 1,
        "messages": [],
        "warnings": [],
    }

    with patch("backlog_core.operations.list_merged_prs", return_value=fake_result):
        # Act
        result = await _call("backlog_list_merged_prs", {})

    # Assert
    assert result["count"] == 1
    assert len(result["pull_requests"]) == 1
    assert result["pull_requests"][0]["number"] == 10
    assert "messages" in result
    assert "warnings" in result


async def test_backlog_list_merged_prs_passes_search_and_limit() -> None:
    """backlog_list_merged_prs forwards search and limit to list_merged_prs."""
    # Arrange
    captured: dict[str, object] = {}

    def fake_list(repo: str = "", search: str | None = None, limit: int = 20, output: object = None) -> dict:
        captured["search"] = search
        captured["limit"] = limit
        return {"pull_requests": [], "count": 0, "messages": [], "warnings": []}

    with patch("backlog_core.operations.list_merged_prs", side_effect=fake_list):
        # Act
        await _call("backlog_list_merged_prs", {"search": "#42", "limit": 5})

    # Assert
    assert captured["search"] == "#42"
    assert captured["limit"] == 5


async def test_backlog_list_merged_prs_uses_default_limit() -> None:
    """backlog_list_merged_prs uses default limit=20 when not specified."""
    # Arrange
    captured: dict[str, object] = {}

    def fake_list(repo: str = "", search: str | None = None, limit: int = 20, output: object = None) -> dict:
        captured["limit"] = limit
        return {"pull_requests": [], "count": 0, "messages": [], "warnings": []}

    with patch("backlog_core.operations.list_merged_prs", side_effect=fake_list):
        # Act
        await _call("backlog_list_merged_prs", {})

    # Assert
    assert captured["limit"] == 20


async def test_backlog_list_merged_prs_backlog_error_returns_error_key() -> None:
    """backlog_list_merged_prs returns error key dict on BacklogError."""
    # Arrange
    with patch("backlog_core.operations.list_merged_prs", side_effect=BacklogError("API rate limit exceeded")):
        # Act
        result = await _call("backlog_list_merged_prs", {})

    # Assert
    assert "error" in result
    assert "rate limit" in result["error"]


async def test_backlog_list_merged_prs_empty_result() -> None:
    """backlog_list_merged_prs returns count=0 and empty list when no merged PRs."""
    # Arrange
    fake_result = {"pull_requests": [], "count": 0, "messages": [], "warnings": []}

    with patch("backlog_core.operations.list_merged_prs", return_value=fake_result):
        # Act
        result = await _call("backlog_list_merged_prs", {})

    # Assert
    assert result["count"] == 0
    assert result["pull_requests"] == []
