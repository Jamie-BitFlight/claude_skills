"""Tests for backlog_list_labels MCP tool and list_labels operation.

Tests are structured in two layers:
- Operation layer: list_labels() in operations.py, mocked at get_github boundary.
- Server layer: backlog_list_labels tool via in-memory FastMCP Client.

No @pytest.mark.asyncio decorators — asyncio_mode = "auto" is set globally.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, patch

from backlog_core.models import BacklogError, Output
from backlog_core.server import mcp

from tests.helpers import call_mcp_tool

if TYPE_CHECKING:
    import pytest

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_label(name: str, color: str = "aabbcc", description: str | None = "") -> MagicMock:
    """Build a MagicMock mimicking a PyGithub Label object."""
    label = MagicMock()
    label.name = name
    label.color = color
    label.description = description
    return label


async def _call(tool_name: str, params: dict | None = None) -> dict:
    """Call an MCP tool through the in-memory FastMCP transport and parse result.

    Delegates to tests.helpers.call_mcp_tool bound to this module's mcp server.
    """
    return await call_mcp_tool(mcp, tool_name, params)


# ---------------------------------------------------------------------------
# Operation layer: list_labels()
# ---------------------------------------------------------------------------


def test_list_labels_returns_all_labels_when_under_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_labels returns every label when count is below the limit."""
    # Arrange
    mock_repo = MagicMock()
    mock_repo.get_labels.return_value = [
        _make_label("bug", "d73a4a", "Something is broken"),
        _make_label("enhancement", "a2eeef", "New feature request"),
    ]
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_labels

    # Act
    result = list_labels(limit=100)

    # Assert
    labels = cast("list[dict[str, str]]", result["labels"])
    assert result["count"] == 2
    assert len(labels) == 2
    assert labels[0] == {"name": "bug", "color": "d73a4a", "description": "Something is broken"}
    assert labels[1] == {"name": "enhancement", "color": "a2eeef", "description": "New feature request"}


def test_list_labels_respects_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_labels stops iterating once the limit is reached."""
    # Arrange
    mock_repo = MagicMock()
    mock_repo.get_labels.return_value = [_make_label("bug"), _make_label("enhancement"), _make_label("documentation")]
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_labels

    # Act
    result = list_labels(limit=2)

    # Assert
    labels = cast("list[dict[str, str]]", result["labels"])
    assert result["count"] == 2
    assert len(labels) == 2
    assert labels[0]["name"] == "bug"
    assert labels[1]["name"] == "enhancement"


def test_list_labels_returns_empty_when_no_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_labels handles a repository with no labels."""
    # Arrange
    mock_repo = MagicMock()
    mock_repo.get_labels.return_value = []
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_labels

    # Act
    result = list_labels()

    # Assert
    assert result["count"] == 0
    assert result["labels"] == []


def test_list_labels_maps_none_description_to_empty_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_labels maps None description to empty string."""
    # Arrange
    mock_repo = MagicMock()
    label = _make_label("bug")
    label.description = None
    mock_repo.get_labels.return_value = [label]
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_labels

    # Act
    result = list_labels()

    # Assert
    labels = cast("list[dict[str, str]]", result["labels"])
    assert labels[0]["description"] == ""


def test_list_labels_output_messages_merged(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_labels merges Output messages into the returned dict."""
    # Arrange
    mock_repo = MagicMock()
    mock_repo.get_labels.return_value = []
    monkeypatch.setattr("backlog_core.operations.get_github", lambda repo=None: mock_repo)

    from backlog_core.operations import list_labels

    out = Output()
    out.messages.append("test message")

    # Act
    result = list_labels(output=out)

    # Assert
    assert "messages" in result
    messages = cast("list[str]", result["messages"])
    assert "test message" in messages


# ---------------------------------------------------------------------------
# Server layer: backlog_list_labels tool
# ---------------------------------------------------------------------------


async def test_backlog_list_labels_success_returns_merged_result() -> None:
    """backlog_list_labels tool returns labels list with count and output keys."""
    # Arrange
    fake_result = {
        "labels": [{"name": "bug", "color": "d73a4a", "description": ""}],
        "count": 1,
        "messages": [],
        "warnings": [],
    }

    with patch("backlog_core.operations.list_labels", return_value=fake_result):
        # Act
        result = await _call("backlog_list_labels", {"limit": 50})

    # Assert
    assert result["count"] == 1
    assert len(result["labels"]) == 1
    assert result["labels"][0]["name"] == "bug"
    assert "messages" in result
    assert "warnings" in result


async def test_backlog_list_labels_uses_default_limit() -> None:
    """backlog_list_labels calls list_labels with default limit=100 when omitted."""
    # Arrange
    captured: dict[str, object] = {}

    def fake_list_labels(repo: str = "", limit: int = 100, output: object = None) -> dict:
        captured["limit"] = limit
        return {"labels": [], "count": 0, "messages": [], "warnings": []}

    with patch("backlog_core.operations.list_labels", side_effect=fake_list_labels):
        # Act
        await _call("backlog_list_labels", {})

    # Assert
    assert captured["limit"] == 100


async def test_backlog_list_labels_backlog_error_returns_error_key() -> None:
    """backlog_list_labels returns dict with error key on BacklogError."""
    # Arrange
    with patch("backlog_core.operations.list_labels", side_effect=BacklogError("GitHub unavailable")):
        # Act
        result = await _call("backlog_list_labels", {})

    # Assert
    assert "error" in result
    assert "GitHub unavailable" in result["error"]


async def test_backlog_list_labels_empty_repo_returns_zero_count() -> None:
    """backlog_list_labels returns count=0 and empty list for repos with no labels."""
    # Arrange
    fake_result = {"labels": [], "count": 0, "messages": [], "warnings": []}

    with patch("backlog_core.operations.list_labels", return_value=fake_result):
        # Act
        result = await _call("backlog_list_labels", {})

    # Assert
    assert result["count"] == 0
    assert result["labels"] == []
