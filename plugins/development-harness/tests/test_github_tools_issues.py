"""Tests for backlog_list_issues and backlog_comment_issue MCP tools.

Tests are structured in two layers:
- Operation layer: list_issues() and comment_issue() in operations.py,
  mocked at the get_github boundary.
- Server layer: backlog_list_issues and backlog_comment_issue tools via
  in-memory FastMCP Client.

No @pytest.mark.asyncio decorators — asyncio_mode = "auto" is set globally.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from backlog_core.models import BacklogError, Output, ValidationError
from backlog_core.server import mcp
from fastmcp.client import Client

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_issue(
    number: int = 1,
    title: str = "Test issue",
    state: str = "open",
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
    milestone_title: str | None = None,
) -> MagicMock:
    """Build a MagicMock mimicking a PyGithub Issue object.

    Sets pull_request=None so _collect_issues does not skip it (PRs are filtered out).
    """
    issue = MagicMock()
    issue.number = number
    issue.title = title
    issue.state = state
    # pull_request must be None — _collect_issues skips issues where pull_request is not None
    issue.pull_request = None
    issue.labels = [MagicMock(name=lb) for lb in (labels or [])]
    for i, lb_name in enumerate(labels or []):
        issue.labels[i].name = lb_name
    issue.assignees = [MagicMock(login=a) for a in (assignees or [])]
    for i, login in enumerate(assignees or []):
        issue.assignees[i].login = login
    if milestone_title:
        issue.milestone = MagicMock()
        issue.milestone.title = milestone_title
    else:
        issue.milestone = None
    issue.created_at = MagicMock()
    issue.created_at.strftime.return_value = "2026-03-01T00:00:00Z"
    issue.updated_at = MagicMock()
    issue.updated_at.strftime.return_value = "2026-03-15T00:00:00Z"
    return issue


async def _call(tool_name: str, params: dict | None = None) -> dict:
    """Call an MCP tool through the in-memory FastMCP transport and parse result."""
    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, params or {})
    return json.loads(result.content[0].text)


# ---------------------------------------------------------------------------
# Operation layer: list_issues()
# ---------------------------------------------------------------------------


def test_list_issues_returns_issues_with_expected_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_issues returns dicts with all required fields for each issue.

    Tests: list_issues operation field mapping
    How: Mock get_github to return a single issue; verify field names and values.
    Why: Field names are the contract between server and MCP consumers.
    """
    # Arrange
    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    issue = _make_issue(number=42, title="Fix crash", state="open", labels=["bug"], assignees=["alice"])
    mock_repo.get_issues.return_value = [issue]
    mock_repo.get_milestones.return_value = []
    mock_repo.get_labels.return_value = []
    mock_repo.requester.graphql_query.return_value = (
        {},
        {
            "data": {
                "repository": {
                    "issues": {
                        "nodes": [
                            {
                                "id": "I_42",
                                "number": 42,
                                "title": "Fix crash",
                                "state": "OPEN",
                                "body": "",
                                "createdAt": "2026-03-01T00:00:00Z",
                                "updatedAt": "2026-03-15T00:00:00Z",
                                "labels": {"nodes": [{"id": "L_1", "name": "bug"}]},
                                "assignees": {"nodes": [{"login": "alice"}]},
                                "milestone": None,
                            }
                        ],
                        "pageInfo": {"hasNextPage": False},
                    }
                }
            }
        },
    )
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_issues

    # Act
    result = list_issues()

    # Assert
    assert result["count"] == 1
    issues = result["issues"]
    assert isinstance(issues, list)
    entry = issues[0]
    assert isinstance(entry, dict)
    assert entry["number"] == 42
    assert entry["title"] == "Fix crash"
    assert entry["state"] == "open"
    assert "labels" in entry
    assert "assignees" in entry
    assert "created_at" in entry
    assert "updated_at" in entry


def test_list_issues_respects_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_issues stops collecting once limit is reached.

    Tests: list_issues limit parameter
    How: Provide 5 issues, request limit=2, verify only 2 returned.
    Why: Limit prevents unbounded API consumption.
    """
    # Arrange
    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    mock_repo.get_issues.return_value = [_make_issue(number=i) for i in range(5)]
    mock_repo.get_milestones.return_value = []
    mock_repo.get_labels.return_value = []
    mock_repo.requester.graphql_query.return_value = (
        {},
        {
            "data": {
                "repository": {
                    "issues": {
                        "nodes": [
                            {
                                "id": f"I_{i}",
                                "number": i,
                                "title": "Test issue",
                                "state": "OPEN",
                                "body": "",
                                "createdAt": "2026-03-01T00:00:00Z",
                                "updatedAt": "2026-03-15T00:00:00Z",
                                "labels": {"nodes": []},
                                "assignees": {"nodes": []},
                                "milestone": None,
                            }
                            for i in range(5)
                        ],
                        "pageInfo": {"hasNextPage": False},
                    }
                }
            }
        },
    )
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_issues

    # Act
    result = list_issues(limit=2)

    # Assert
    assert result["count"] == 2
    issues = result["issues"]
    assert isinstance(issues, list)
    assert len(issues) == 2


def test_list_issues_returns_empty_when_no_issues(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_issues returns empty list when repository has no matching issues.

    Tests: list_issues empty case
    How: Return empty list from get_issues mock.
    Why: Empty result must be handled gracefully with count=0.
    """
    # Arrange
    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    mock_repo.get_issues.return_value = []
    mock_repo.get_milestones.return_value = []
    mock_repo.get_labels.return_value = []
    mock_repo.requester.graphql_query.return_value = (
        {},
        {"data": {"repository": {"issues": {"nodes": [], "pageInfo": {"hasNextPage": False}}}}},
    )
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_issues

    # Act
    result = list_issues()

    # Assert
    assert result["count"] == 0
    assert result["issues"] == []


def test_list_issues_invalid_state_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_issues raises ValidationError for unrecognised state values.

    Tests: list_issues state validation
    How: Pass an invalid state string and expect ValidationError.
    Why: Prevents silent misbehaviour from typos in the state parameter.
    """
    # Arrange
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: MagicMock())

    from backlog_core.operations import list_issues

    # Act / Assert
    with pytest.raises(ValidationError, match="Invalid state"):
        list_issues(state="invalid")


def test_list_issues_github_exception_raises_backlog_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_issues wraps GithubException as BacklogError.

    Tests: list_issues error handling
    How: Raise GithubException from get_issues mock; verify BacklogError raised.
    Why: Callers receive a consistent error type regardless of PyGithub internals.
    """
    # Arrange
    from github import GithubException

    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    mock_repo.get_issues.side_effect = GithubException(status=500, data="Server error", headers={})
    mock_repo.get_milestones.return_value = []
    mock_repo.get_labels.return_value = []
    mock_repo.requester.graphql_query.side_effect = GithubException(status=500, data="Server error", headers={})
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_issues

    # Act / Assert
    with pytest.raises(BacklogError, match="GitHub API error"):
        list_issues()


def test_list_issues_passes_state_to_get_issues(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_issues passes the state parameter through to get_issues.

    Tests: list_issues state forwarding
    How: Capture kwargs passed to get_issues and verify state is forwarded.
    Why: Filtering by state is required for the feature to be useful.
    """
    # Arrange
    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    mock_repo.get_issues.return_value = []
    mock_repo.get_milestones.return_value = []
    mock_repo.get_labels.return_value = []
    mock_repo.requester.graphql_query.return_value = (
        {},
        {"data": {"repository": {"issues": {"nodes": [], "pageInfo": {"hasNextPage": False}}}}},
    )
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_issues

    # Act
    list_issues(state="closed")


def test_list_issues_output_messages_merged(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_issues merges Output messages into returned dict.

    Tests: list_issues Output integration
    How: Provide pre-populated Output; verify its messages appear in result.
    Why: The messages/warnings keys are part of the return contract.
    """
    # Arrange
    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    mock_repo.get_issues.return_value = []
    mock_repo.get_milestones.return_value = []
    mock_repo.get_labels.return_value = []
    mock_repo.requester.graphql_query.return_value = (
        {},
        {"data": {"repository": {"issues": {"nodes": [], "pageInfo": {"hasNextPage": False}}}}},
    )
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_issues

    out = Output()
    out.messages.append("pre-existing message")

    # Act
    result = list_issues(output=out)

    # Assert
    assert "messages" in result
    messages = result["messages"]
    assert isinstance(messages, list)
    assert "pre-existing message" in messages
    assert "warnings" in result


# ---------------------------------------------------------------------------
# Operation layer: comment_issue()
# ---------------------------------------------------------------------------


def test_comment_issue_returns_expected_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """comment_issue returns issue_number, comment_id, and comment_url.

    Tests: comment_issue field mapping
    How: Mock get_issue and create_comment; verify returned dict keys.
    Why: Callers depend on comment_id and comment_url for downstream linking.
    """
    # Arrange
    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    mock_repo.requester.graphql_query.side_effect = [
        # First call: _fetch_issue_graphql
        (
            {},
            {
                "data": {
                    "repository": {
                        "issue": {
                            "id": "I_NODE_42",
                            "number": 42,
                            "title": "Fix crash",
                            "state": "OPEN",
                            "body": "",
                            "createdAt": "2026-03-01T00:00:00Z",
                            "updatedAt": "2026-03-15T00:00:00Z",
                            "labels": {"nodes": []},
                            "assignees": {"nodes": []},
                            "milestone": None,
                        }
                    }
                }
            },
        ),
        # Second call: _add_comment_graphql
        ({}, {"data": {"addComment": {"commentEdge": {"node": {"id": "C_999"}}}}}),
    ]
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import comment_issue

    # Act
    result = comment_issue(issue_number=42, body="LGTM!")

    # Assert
    assert result["issue_number"] == 42
    assert result["comment_id"] == "C_999"
    assert "comment_url" in result


def test_comment_issue_invalid_number_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """comment_issue raises ValidationError when issue_number is zero or negative.

    Tests: comment_issue number validation
    How: Pass issue_number=0 and expect ValidationError.
    Why: Prevents creating a comment on an invalid issue.
    """
    # Arrange
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: MagicMock())

    from backlog_core.operations import comment_issue

    # Act / Assert
    with pytest.raises(ValidationError):
        comment_issue(issue_number=0, body="some text")


def test_comment_issue_empty_body_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """comment_issue raises ValidationError when body is empty.

    Tests: comment_issue body validation
    How: Pass empty body string and expect ValidationError.
    Why: An empty comment is not useful and indicates a caller bug.
    """
    # Arrange
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: MagicMock())

    from backlog_core.operations import comment_issue

    # Act / Assert
    with pytest.raises(ValidationError):
        comment_issue(issue_number=1, body="")


def test_comment_issue_github_exception_raises_backlog_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """comment_issue wraps GithubException as BacklogError.

    Tests: comment_issue error handling
    How: Raise GithubException from create_comment; verify BacklogError raised.
    Why: Uniform error type makes caller error handling predictable.
    """
    # Arrange
    from github import GithubException

    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    mock_repo.requester.graphql_query.side_effect = GithubException(status=404, data="Not found", headers={})
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import comment_issue

    # Act / Assert
    with pytest.raises(BacklogError, match="GitHub API error"):
        comment_issue(issue_number=42, body="A comment")


# ---------------------------------------------------------------------------
# Server layer: backlog_list_issues tool
# ---------------------------------------------------------------------------


async def test_backlog_list_issues_success_returns_issues_list() -> None:
    """backlog_list_issues tool returns issues list with count and output keys.

    Tests: backlog_list_issues server tool success path
    How: Patch operations.list_issues with fake result; call via FastMCP client.
    Why: Verifies server wiring: tool invocation reaches the operation layer.
    """
    # Arrange
    fake_result = {
        "issues": [
            {
                "number": 1,
                "title": "Bug fix",
                "state": "open",
                "labels": [],
                "assignees": [],
                "milestone": None,
                "created_at": "",
                "updated_at": "",
            }
        ],
        "count": 1,
        "messages": [],
        "warnings": [],
    }

    with patch("backlog_core.operations.list_issues", return_value=fake_result):
        # Act
        result = await _call("backlog_list_issues", {})

    # Assert
    assert result["count"] == 1
    assert len(result["issues"]) == 1
    assert "messages" in result
    assert "warnings" in result


async def test_backlog_list_issues_passes_params() -> None:
    """backlog_list_issues forwards state, milestone, labels, and limit to list_issues.

    Tests: backlog_list_issues parameter forwarding
    How: Capture call kwargs via side_effect; verify forwarding.
    Why: Parameters must reach the operation or filtering silently breaks.
    """
    # Arrange
    captured: dict[str, object] = {}

    def fake_list(
        repo: str = "",
        milestone: str | None = None,
        labels: str | None = None,
        state: str = "open",
        limit: int = 30,
        output: object = None,
    ) -> dict:
        captured["state"] = state
        captured["limit"] = limit
        captured["milestone"] = milestone
        captured["labels"] = labels
        return {"issues": [], "count": 0, "messages": [], "warnings": []}

    with patch("backlog_core.operations.list_issues", side_effect=fake_list):
        # Act
        await _call("backlog_list_issues", {"state": "closed", "limit": 10, "milestone": "v1.0", "labels": "bug"})

    # Assert
    assert captured["state"] == "closed"
    assert captured["limit"] == 10
    assert captured["milestone"] == "v1.0"
    assert captured["labels"] == "bug"


async def test_backlog_list_issues_backlog_error_returns_error_key() -> None:
    """backlog_list_issues returns dict with error key on BacklogError.

    Tests: backlog_list_issues error handling
    How: Raise BacklogError from patched list_issues; verify error key in result.
    Why: Tool must not raise; MCP requires serialisable error response.
    """
    # Arrange
    with patch("backlog_core.operations.list_issues", side_effect=BacklogError("API unavailable")):
        # Act
        result = await _call("backlog_list_issues", {})

    # Assert
    assert "error" in result
    assert "API unavailable" in result["error"]


async def test_backlog_list_issues_empty_result() -> None:
    """backlog_list_issues returns count=0 and empty list when no issues match.

    Tests: backlog_list_issues empty response
    How: Patch list_issues to return empty; verify structure.
    Why: Consumers must handle empty results without KeyError.
    """
    # Arrange
    fake_result = {"issues": [], "count": 0, "messages": [], "warnings": []}

    with patch("backlog_core.operations.list_issues", return_value=fake_result):
        # Act
        result = await _call("backlog_list_issues", {})

    # Assert
    assert result["count"] == 0
    assert result["issues"] == []


# ---------------------------------------------------------------------------
# Server layer: backlog_comment_issue tool
# ---------------------------------------------------------------------------


async def test_backlog_comment_issue_success_returns_comment_fields() -> None:
    """backlog_comment_issue tool returns issue_number, comment_id, comment_url.

    Tests: backlog_comment_issue server tool success path
    How: Patch operations.comment_issue with fake result; call via FastMCP client.
    Why: Verifies the tool is registered and wired to the operation.
    """
    # Arrange
    fake_result = {
        "issue_number": 42,
        "comment_id": 999,
        "comment_url": "https://github.com/owner/repo/issues/42#issuecomment-999",
        "messages": ["  Comment added to issue #42"],
        "warnings": [],
    }

    with patch("backlog_core.operations.comment_issue", return_value=fake_result):
        # Act
        result = await _call("backlog_comment_issue", {"issue_number": 42, "body": "LGTM!"})

    # Assert
    assert result["issue_number"] == 42
    assert result["comment_id"] == 999
    assert "comment_url" in result
    assert "messages" in result


async def test_backlog_comment_issue_forwards_params() -> None:
    """backlog_comment_issue forwards issue_number and body to comment_issue.

    Tests: backlog_comment_issue parameter forwarding
    How: Capture call kwargs via side_effect; verify they match tool input.
    Why: If params are dropped, the comment is created on the wrong issue.
    """
    # Arrange
    captured: dict[str, object] = {}

    def fake_comment(repo: str = "", issue_number: int = 0, body: str = "", output: object = None) -> dict:
        captured["issue_number"] = issue_number
        captured["body"] = body
        return {"issue_number": issue_number, "comment_id": 1, "comment_url": "", "messages": [], "warnings": []}

    with patch("backlog_core.operations.comment_issue", side_effect=fake_comment):
        # Act
        await _call("backlog_comment_issue", {"issue_number": 7, "body": "Hello world"})

    # Assert
    assert captured["issue_number"] == 7
    assert captured["body"] == "Hello world"


async def test_backlog_comment_issue_backlog_error_returns_error_key() -> None:
    """backlog_comment_issue returns dict with error key on BacklogError.

    Tests: backlog_comment_issue error handling
    How: Raise BacklogError from patched comment_issue; verify error key.
    Why: Tool must not raise; MCP requires serialisable error response.
    """
    # Arrange
    with patch("backlog_core.operations.comment_issue", side_effect=BacklogError("Issue not found")):
        # Act
        result = await _call("backlog_comment_issue", {"issue_number": 99, "body": "text"})

    # Assert
    assert "error" in result
    assert "Issue not found" in result["error"]
