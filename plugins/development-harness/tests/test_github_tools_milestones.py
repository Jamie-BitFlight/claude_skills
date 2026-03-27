"""Tests for backlog milestone MCP tools and operations.

Covers three tools and operations:
- list_milestones / backlog_list_milestones
- get_soonest_milestone / backlog_get_soonest_milestone
- create_milestone / backlog_create_milestone

Tests are structured in two layers:
- Operation layer: functions in operations.py, mocked at get_github boundary.
- Server layer: MCP tool wrappers via in-memory FastMCP Client.

No @pytest.mark.asyncio decorators — asyncio_mode = "auto" is set globally.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from backlog_core.models import BacklogError, ValidationError
from backlog_core.server import mcp
from fastmcp.client import Client

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_DUE_ON = datetime(2026, 6, 30, 0, 0, 0, tzinfo=UTC)
_DUE_ON_STR = "2026-06-30T00:00:00Z"


def _make_milestone(
    number: int = 1,
    title: str = "v1.0",
    state: str = "open",
    description: str = "",
    due_on: datetime | None = _DUE_ON,
    open_issues: int = 3,
    closed_issues: int = 7,
) -> MagicMock:
    """Build a MagicMock mimicking a PyGithub Milestone object."""
    ms = MagicMock()
    ms.number = number
    ms.title = title
    ms.state = state
    ms.description = description
    ms.due_on = due_on
    ms.open_issues = open_issues
    ms.closed_issues = closed_issues
    return ms


async def _call(tool_name: str, params: dict | None = None) -> dict:
    """Call an MCP tool through the in-memory FastMCP transport and parse result."""
    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, params or {})
    return json.loads(result.content[0].text)


# ---------------------------------------------------------------------------
# Operation layer: list_milestones()
# ---------------------------------------------------------------------------


def test_list_milestones_returns_expected_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_milestones returns dicts with all required fields.

    Tests: list_milestones field mapping
    How: Mock get_github to return one milestone; verify field names and values.
    Why: Field names are the contract between server and MCP consumers.
    """
    # Arrange
    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    mock_repo.get_milestones.return_value = [_make_milestone(number=1, title="v1.0")]
    mock_repo.requester.graphql_query.return_value = (
        {},
        {
            "data": {
                "repository": {
                    "milestones": {
                        "nodes": [
                            {
                                "id": "M_1",
                                "number": 1,
                                "title": "v1.0",
                                "state": "OPEN",
                                "description": "",
                                "dueOn": _DUE_ON_STR,
                                "issues": {"totalCount": 3},
                                "closedIssues": {"totalCount": 7},
                            }
                        ]
                    }
                }
            }
        },
    )
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_milestones

    # Act
    result = list_milestones()

    # Assert
    assert result["count"] == 1
    milestones = result["milestones"]
    assert isinstance(milestones, list)
    entry = milestones[0]
    assert isinstance(entry, dict)
    assert entry["number"] == 1
    assert entry["title"] == "v1.0"
    assert entry["state"] == "open"
    assert "description" in entry
    assert entry["due_on"] == _DUE_ON_STR
    assert "open_issues" in entry
    assert "closed_issues" in entry


def test_list_milestones_none_due_on_returns_null(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_milestones serialises milestones without a due date as None.

    Tests: list_milestones null due_on handling
    How: Provide milestone with due_on=None; verify result due_on is None.
    Why: Nullable due_on is valid; consumers must handle None without crashing.
    """
    # Arrange
    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    mock_repo.get_milestones.return_value = [_make_milestone(due_on=None)]
    mock_repo.requester.graphql_query.return_value = (
        {},
        {
            "data": {
                "repository": {
                    "milestones": {
                        "nodes": [
                            {
                                "id": "M_1",
                                "number": 1,
                                "title": "v1.0",
                                "state": "OPEN",
                                "description": "",
                                "dueOn": None,
                                "issues": {"totalCount": 3},
                                "closedIssues": {"totalCount": 7},
                            }
                        ]
                    }
                }
            }
        },
    )
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_milestones

    # Act
    result = list_milestones()

    # Assert
    milestones = result["milestones"]
    assert isinstance(milestones, list)
    first = milestones[0]
    assert isinstance(first, dict)
    assert first["due_on"] is None


def test_list_milestones_passes_state_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_milestones forwards the state parameter to get_milestones.

    Tests: list_milestones state forwarding
    How: Capture kwargs passed to get_milestones; verify state is forwarded.
    Why: State filtering is the core feature of this operation.
    """
    # Arrange
    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    mock_repo.get_milestones.return_value = []
    mock_repo.requester.graphql_query.return_value = ({}, {"data": {"repository": {"milestones": {"nodes": []}}}})
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_milestones

    # Act — verifies state="closed" is accepted without error
    list_milestones(state="closed")


def test_list_milestones_empty_returns_zero_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_milestones returns count=0 and empty list when repo has no milestones.

    Tests: list_milestones empty case
    How: Return empty list from get_milestones; verify count and empty list.
    Why: Empty result must be handled without errors.
    """
    # Arrange
    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    mock_repo.get_milestones.return_value = []
    mock_repo.requester.graphql_query.return_value = ({}, {"data": {"repository": {"milestones": {"nodes": []}}}})
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_milestones

    # Act
    result = list_milestones()

    # Assert
    assert result["count"] == 0
    assert result["milestones"] == []


# ---------------------------------------------------------------------------
# Operation layer: get_soonest_milestone()
# ---------------------------------------------------------------------------


def test_get_soonest_milestone_returns_earliest_due_date(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_soonest_milestone returns the milestone with the earliest due date.

    Tests: get_soonest_milestone sorting logic
    How: Provide two milestones with different due dates; verify earliest returned.
    Why: The 'soonest' selection is the defining behaviour of this operation.
    """
    # Arrange
    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    # reversed order intentionally — graphql returns far first, near second
    mock_repo.requester.graphql_query.return_value = (
        {},
        {
            "data": {
                "repository": {
                    "milestones": {
                        "nodes": [
                            {
                                "id": "M_2",
                                "number": 2,
                                "title": "v2.0",
                                "state": "OPEN",
                                "description": "",
                                "dueOn": "2026-12-31T00:00:00+00:00",
                                "issues": {"totalCount": 0},
                                "closedIssues": {"totalCount": 0},
                            },
                            {
                                "id": "M_1",
                                "number": 1,
                                "title": "v1.0",
                                "state": "OPEN",
                                "description": "",
                                "dueOn": "2026-04-01T00:00:00+00:00",
                                "issues": {"totalCount": 0},
                                "closedIssues": {"totalCount": 0},
                            },
                        ]
                    }
                }
            }
        },
    )
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import get_soonest_milestone

    # Act
    result = get_soonest_milestone()

    # Assert
    ms = cast("dict[str, object]", result["milestone"])
    assert ms is not None
    assert ms["title"] == "v1.0"
    assert ms["number"] == 1


def test_get_soonest_milestone_none_when_no_milestones(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_soonest_milestone returns milestone=None when repo has no open milestones.

    Tests: get_soonest_milestone empty repo case
    How: Return empty list from get_milestones; verify milestone key is None.
    Why: Consumers must be able to check for None without crashing.
    """
    # Arrange
    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    mock_repo.get_milestones.return_value = []
    mock_repo.requester.graphql_query.return_value = ({}, {"data": {"repository": {"milestones": {"nodes": []}}}})
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import get_soonest_milestone

    # Act
    result = get_soonest_milestone()

    # Assert
    assert result["milestone"] is None


def test_get_soonest_milestone_skips_milestones_without_due_date(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_soonest_milestone excludes milestones that have no due date.

    Tests: get_soonest_milestone due_on=None exclusion
    How: Provide one milestone with due_on and one without; verify dated one returned.
    Why: Milestones without due dates cannot be ranked by recency.
    """
    # Arrange
    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    mock_repo.requester.graphql_query.return_value = (
        {},
        {
            "data": {
                "repository": {
                    "milestones": {
                        "nodes": [
                            {
                                "id": "M_2",
                                "number": 2,
                                "title": "v2.0",
                                "state": "OPEN",
                                "description": "",
                                "dueOn": None,
                                "issues": {"totalCount": 0},
                                "closedIssues": {"totalCount": 0},
                            },
                            {
                                "id": "M_1",
                                "number": 1,
                                "title": "v1.0",
                                "state": "OPEN",
                                "description": "",
                                "dueOn": "2026-06-01T00:00:00+00:00",
                                "issues": {"totalCount": 0},
                                "closedIssues": {"totalCount": 0},
                            },
                        ]
                    }
                }
            }
        },
    )
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import get_soonest_milestone

    # Act
    result = get_soonest_milestone()

    # Assert
    ms = cast("dict[str, object]", result["milestone"])
    assert ms is not None
    assert ms["title"] == "v1.0"


def test_get_soonest_milestone_falls_back_to_first_when_no_due_dates(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_soonest_milestone returns first milestone when none have due dates.

    Tests: get_soonest_milestone all-undated fallback
    How: Provide milestones all with due_on=None; verify first is returned with warning.
    Why: A graceful fallback is better than returning None when milestones exist.
    """
    # Arrange
    mock_repo = MagicMock()
    mock_repo.full_name = "owner/repo"
    mock_repo.requester.graphql_query.return_value = (
        {},
        {
            "data": {
                "repository": {
                    "milestones": {
                        "nodes": [
                            {
                                "id": "M_1",
                                "number": 1,
                                "title": "v1.0",
                                "state": "OPEN",
                                "description": "",
                                "dueOn": None,
                                "issues": {"totalCount": 0},
                                "closedIssues": {"totalCount": 0},
                            },
                            {
                                "id": "M_2",
                                "number": 2,
                                "title": "v2.0",
                                "state": "OPEN",
                                "description": "",
                                "dueOn": None,
                                "issues": {"totalCount": 0},
                                "closedIssues": {"totalCount": 0},
                            },
                        ]
                    }
                }
            }
        },
    )
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import get_soonest_milestone

    # Act
    result = get_soonest_milestone()

    # Assert — first milestone returned, warning added
    ms = cast("dict[str, object]", result["milestone"])
    assert ms is not None
    assert ms["number"] == 1
    warnings = result.get("warnings", [])
    assert isinstance(warnings, list)
    assert len(warnings) > 0


# ---------------------------------------------------------------------------
# Operation layer: create_milestone()
# ---------------------------------------------------------------------------


def test_create_milestone_returns_milestone_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_milestone returns a milestone dict with all expected fields.

    Tests: create_milestone return shape
    How: Mock create_milestone on repo; verify returned dict keys.
    Why: Callers need the milestone number immediately after creation.
    """
    # Arrange
    mock_ms = _make_milestone(number=5, title="v3.0")
    mock_repo = MagicMock()
    mock_repo.create_milestone.return_value = mock_ms
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import create_milestone

    # Act
    result = create_milestone(title="v3.0")

    # Assert
    ms = cast("dict[str, object]", result["milestone"])
    assert ms is not None
    assert ms["number"] == 5
    assert ms["title"] == "v3.0"
    assert "state" in ms
    assert "due_on" in ms


def test_create_milestone_empty_title_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_milestone raises ValidationError when title is empty or whitespace.

    Tests: create_milestone title validation
    How: Pass empty title string; expect ValidationError.
    Why: An empty milestone title is invalid and would confuse consumers.
    """
    # Arrange
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: MagicMock())

    from backlog_core.operations import create_milestone

    # Act / Assert
    with pytest.raises(ValidationError, match="title must be non-empty"):
        create_milestone(title="")


def test_create_milestone_parses_date_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_milestone parses ISO 8601 date string and passes datetime to PyGithub.

    Tests: create_milestone due_on date parsing
    How: Capture kwargs passed to create_milestone on mock repo; verify due_on is datetime.
    Why: PyGithub expects a datetime object, not a string.
    """
    # Arrange
    mock_ms = _make_milestone(number=1, title="v1.0", due_on=datetime(2026, 6, 30, tzinfo=UTC))
    mock_repo = MagicMock()
    mock_repo.create_milestone.return_value = mock_ms
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import create_milestone

    # Act
    create_milestone(title="v1.0", due_on="2026-06-30")

    # Assert
    call_kwargs = mock_repo.create_milestone.call_args.kwargs
    assert isinstance(call_kwargs.get("due_on"), datetime)


def test_create_milestone_invalid_date_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_milestone raises ValidationError when due_on cannot be parsed.

    Tests: create_milestone due_on parse failure
    How: Pass nonsensical date string; verify ValidationError is raised.
    Why: Silent date parsing failure would create milestones with wrong due dates.
    """
    # Arrange
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: MagicMock())

    from backlog_core.operations import create_milestone

    # Act / Assert
    with pytest.raises(ValidationError):
        create_milestone(title="v1.0", due_on="not-a-date")


# ---------------------------------------------------------------------------
# Server layer: backlog_list_milestones tool
# ---------------------------------------------------------------------------


async def test_backlog_list_milestones_success_returns_milestones_list() -> None:
    """backlog_list_milestones returns milestones list with count and output keys.

    Tests: backlog_list_milestones server tool success path
    How: Patch list_milestones with fake result; verify response shape.
    Why: Verifies the tool is registered and wired to the operation.
    """
    # Arrange
    fake_result = {
        "milestones": [
            {
                "number": 1,
                "title": "v1.0",
                "state": "open",
                "description": "",
                "due_on": _DUE_ON_STR,
                "open_issues": 3,
                "closed_issues": 7,
            }
        ],
        "count": 1,
        "messages": [],
        "warnings": [],
    }

    with patch("backlog_core.operations.list_milestones", return_value=fake_result):
        # Act
        result = await _call("backlog_list_milestones", {"state": "open"})

    # Assert
    assert result["count"] == 1
    assert len(result["milestones"]) == 1
    assert "messages" in result
    assert "warnings" in result


async def test_backlog_list_milestones_backlog_error_returns_error_key() -> None:
    """backlog_list_milestones returns dict with error key on BacklogError.

    Tests: backlog_list_milestones error handling
    How: Raise BacklogError from patched list_milestones; verify error key.
    Why: Tool must not raise; MCP requires serialisable error response.
    """
    # Arrange
    with patch("backlog_core.operations.list_milestones", side_effect=BacklogError("API error")):
        # Act
        result = await _call("backlog_list_milestones", {})

    # Assert
    assert "error" in result
    assert "API error" in result["error"]


# ---------------------------------------------------------------------------
# Server layer: backlog_get_soonest_milestone tool
# ---------------------------------------------------------------------------


async def test_backlog_get_soonest_milestone_returns_milestone_dict() -> None:
    """backlog_get_soonest_milestone returns milestone dict with output keys.

    Tests: backlog_get_soonest_milestone server tool success path
    How: Patch get_soonest_milestone with fake result; verify response shape.
    Why: Verifies the tool is registered and wired to the operation.
    """
    # Arrange
    fake_result = {
        "milestone": {
            "number": 1,
            "title": "v1.0",
            "state": "open",
            "description": "",
            "due_on": _DUE_ON_STR,
            "open_issues": 2,
            "closed_issues": 5,
        },
        "messages": [],
        "warnings": [],
    }

    with patch("backlog_core.operations.get_soonest_milestone", return_value=fake_result):
        # Act
        result = await _call("backlog_get_soonest_milestone", {})

    # Assert
    assert result["milestone"] is not None
    assert result["milestone"]["title"] == "v1.0"
    assert "messages" in result


async def test_backlog_get_soonest_milestone_none_when_no_milestones() -> None:
    """backlog_get_soonest_milestone returns milestone=None when no milestones exist.

    Tests: backlog_get_soonest_milestone empty case
    How: Patch get_soonest_milestone to return milestone=None; verify serialisation.
    Why: None milestone must survive JSON serialisation round-trip.
    """
    # Arrange
    fake_result = {"milestone": None, "messages": [], "warnings": []}

    with patch("backlog_core.operations.get_soonest_milestone", return_value=fake_result):
        # Act
        result = await _call("backlog_get_soonest_milestone", {})

    # Assert
    assert result["milestone"] is None


async def test_backlog_get_soonest_milestone_backlog_error_returns_error_key() -> None:
    """backlog_get_soonest_milestone returns dict with error key on BacklogError.

    Tests: backlog_get_soonest_milestone error handling
    How: Raise BacklogError from patched operation; verify error key.
    Why: Tool must not raise; MCP requires serialisable error response.
    """
    # Arrange
    with patch("backlog_core.operations.get_soonest_milestone", side_effect=BacklogError("GitHub down")):
        # Act
        result = await _call("backlog_get_soonest_milestone", {})

    # Assert
    assert "error" in result
    assert "GitHub down" in result["error"]


# ---------------------------------------------------------------------------
# Server layer: backlog_create_milestone tool
# ---------------------------------------------------------------------------


async def test_backlog_create_milestone_success_returns_milestone_fields() -> None:
    """backlog_create_milestone returns created milestone fields.

    Tests: backlog_create_milestone server tool success path
    How: Patch create_milestone with fake result; verify response keys.
    Why: Callers need the milestone number returned immediately after creation.
    """
    # Arrange
    fake_result = {
        "milestone": {
            "number": 5,
            "title": "v3.0",
            "state": "open",
            "description": "",
            "due_on": _DUE_ON_STR,
            "open_issues": 0,
            "closed_issues": 0,
        },
        "messages": [],
        "warnings": [],
    }

    with patch("backlog_core.operations.create_milestone", return_value=fake_result):
        # Act
        result = await _call("backlog_create_milestone", {"title": "v3.0", "due_on": "2026-06-30"})

    # Assert
    assert result["milestone"]["number"] == 5
    assert result["milestone"]["title"] == "v3.0"
    assert "messages" in result


async def test_backlog_create_milestone_forwards_params() -> None:
    """backlog_create_milestone forwards title, description, and due_on to create_milestone.

    Tests: backlog_create_milestone parameter forwarding
    How: Capture kwargs via side_effect; verify all params forwarded.
    Why: If params are not forwarded the milestone is created with wrong data.
    """
    # Arrange
    captured: dict[str, object] = {}

    def fake_create(
        repo: str = "", title: str = "", description: str = "", due_on: str | None = None, output: object = None
    ) -> dict:
        captured["title"] = title
        captured["description"] = description
        captured["due_on"] = due_on
        return {
            "milestone": {
                "number": 1,
                "title": title,
                "state": "open",
                "description": description,
                "due_on": due_on,
                "open_issues": 0,
                "closed_issues": 0,
            },
            "messages": [],
            "warnings": [],
        }

    with patch("backlog_core.operations.create_milestone", side_effect=fake_create):
        # Act
        await _call(
            "backlog_create_milestone", {"title": "Sprint 1", "description": "First sprint", "due_on": "2026-04-01"}
        )

    # Assert
    assert captured["title"] == "Sprint 1"
    assert captured["description"] == "First sprint"
    assert captured["due_on"] == "2026-04-01"


async def test_backlog_create_milestone_backlog_error_returns_error_key() -> None:
    """backlog_create_milestone returns dict with error key on BacklogError.

    Tests: backlog_create_milestone error handling
    How: Raise BacklogError from patched operation; verify error key.
    Why: Tool must not raise; MCP requires serialisable error response.
    """
    # Arrange
    with patch("backlog_core.operations.create_milestone", side_effect=BacklogError("Milestone title already used")):
        # Act
        result = await _call("backlog_create_milestone", {"title": "v1.0"})

    # Assert
    assert "error" in result
    assert "Milestone title already used" in result["error"]
