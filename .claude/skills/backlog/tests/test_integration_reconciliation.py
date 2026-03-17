"""Integration tests for CLI --include-closed flag and MCP include_closed parameter.

Tests: End-to-end behavior of closed item filtering across CLI (backlog.py),
       operations layer (backlog_core/operations.py), and MCP server
       (backlog_core/server.py).
How: Create BacklogItem objects with various statuses, mock GitHub API at the
     boundary, verify filtering behavior through the full call chain.
Why: T4 added --include-closed CLI flag and modified fetch functions. T5 added
     the MCP include_closed parameter. These tests verify the end-to-end
     integration of both features.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from backlog_core.models import BacklogItem, IssueStatus
from backlog_core.operations import _filter_closed_items, list_items
from backlog_core.server import mcp
from fastmcp.client import Client

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item(
    title: str, section: str = "P1", status: str = "open", issue: str = "", skip: bool = False
) -> BacklogItem:
    """Create a BacklogItem with the given fields for testing."""
    return BacklogItem(title=title, section=section, status=status, issue=issue, skip=skip)


def _make_mixed_items() -> list[BacklogItem]:
    """Create a mix of open and terminal-status items for testing."""
    return [
        _make_item("Active feature", status="open", issue="#1"),
        _make_item("In progress work", status="in-progress", issue="#2"),
        _make_item("Groomed item", status="groomed", issue="#3"),
        _make_item("Done item", status="done", issue="#4"),
        _make_item("Resolved item", status="resolved", issue="#5"),
        _make_item("Closed item", status="closed", issue="#6"),
        _make_item("Needs grooming", status="needs-grooming", issue="#7"),
    ]


async def _call_mcp(tool_name: str, params: dict | None = None) -> dict:
    """Call a tool through the in-memory FastMCP transport and parse the result."""
    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, params or {})
    return json.loads(result.content[0].text)


# ---------------------------------------------------------------------------
# _filter_closed_items (operations layer)
# ---------------------------------------------------------------------------


class TestFilterClosedItemsOperations:
    """Verify _filter_closed_items in operations module filters by terminal status."""

    def test_excludes_done_resolved_closed_by_default(self) -> None:
        """Items with done, resolved, or closed status are excluded when include_closed is False."""
        items = _make_mixed_items()
        filtered = _filter_closed_items(items, include_closed=False)
        remaining_statuses = {it.status for it in filtered}
        assert "done" not in remaining_statuses
        assert "resolved" not in remaining_statuses
        assert "closed" not in remaining_statuses

    def test_keeps_non_terminal_items_by_default(self) -> None:
        """Items with open, in-progress, groomed, needs-grooming status are kept."""
        items = _make_mixed_items()
        filtered = _filter_closed_items(items, include_closed=False)
        remaining_statuses = {it.status for it in filtered}
        assert "open" in remaining_statuses
        assert "in-progress" in remaining_statuses
        assert "groomed" in remaining_statuses
        assert "needs-grooming" in remaining_statuses
        assert len(filtered) == 4

    def test_includes_all_items_when_include_closed_true(self) -> None:
        """All items are returned unfiltered when include_closed is True."""
        items = _make_mixed_items()
        filtered = _filter_closed_items(items, include_closed=True)
        assert len(filtered) == len(items)
        assert filtered is items  # Same reference, not a copy

    def test_empty_list_returns_empty(self) -> None:
        """Empty input list returns empty list regardless of include_closed value."""
        assert _filter_closed_items([], include_closed=False) == []
        assert _filter_closed_items([], include_closed=True) == []

    def test_all_terminal_items_returns_empty_when_excluded(self) -> None:
        """List of only terminal-status items returns empty when filtering."""
        items = [
            _make_item("Done", status="done"),
            _make_item("Resolved", status="resolved"),
            _make_item("Closed", status="closed"),
        ]
        filtered = _filter_closed_items(items, include_closed=False)
        assert len(filtered) == 0


# ---------------------------------------------------------------------------
# operations.list_items integration
# ---------------------------------------------------------------------------


class TestListItemsIncludeClosed:
    """Verify list_items function respects include_closed parameter end-to-end."""

    def test_list_items_excludes_closed_by_default(self) -> None:
        """list_items without include_closed filters out terminal status items."""
        items = _make_mixed_items()
        with (
            patch("backlog_core.operations.parse_backlog", return_value=items),
            patch("backlog_core.operations.batch_fetch_statuses", return_value={}),
        ):
            result = list_items(include_closed=False)
        titles = [it["title"] for it in result["items"]]
        assert "Done item" not in titles
        assert "Resolved item" not in titles
        assert "Closed item" not in titles
        assert "Active feature" in titles
        assert "In progress work" in titles

    def test_list_items_includes_closed_when_flag_set(self) -> None:
        """list_items with include_closed=True returns terminal status items too."""
        items = _make_mixed_items()
        with (
            patch("backlog_core.operations.parse_backlog", return_value=items),
            patch("backlog_core.operations.batch_fetch_statuses", return_value={}),
        ):
            result = list_items(include_closed=True)
        titles = [it["title"] for it in result["items"]]
        assert "Done item" in titles
        assert "Resolved item" in titles
        assert "Closed item" in titles
        assert len(result["items"]) == 7

    def test_list_items_count_reflects_filtering(self) -> None:
        """The count field in result matches the number of items after filtering."""
        items = _make_mixed_items()
        with (
            patch("backlog_core.operations.parse_backlog", return_value=items),
            patch("backlog_core.operations.batch_fetch_statuses", return_value={}),
        ):
            result_filtered = list_items(include_closed=False)
            result_all = list_items(include_closed=True)
        assert result_filtered["count"] == len(result_filtered["items"])
        assert result_all["count"] == len(result_all["items"])
        assert result_all["count"] > result_filtered["count"]

    def test_list_items_with_status_returns_status_for_all(self) -> None:
        """When with_status=True, status is returned for each item including closed ones."""
        items = _make_mixed_items()
        status_map = {
            1: IssueStatus(status="open", milestone="v1"),
            2: IssueStatus(status="open", milestone="v1"),
            3: IssueStatus(status="open", milestone=""),
            4: IssueStatus(status="closed", milestone="v1"),
            5: IssueStatus(status="closed", milestone="v1"),
            6: IssueStatus(status="closed", milestone=""),
            7: IssueStatus(status="open", milestone=""),
        }
        with (
            patch("backlog_core.operations.parse_backlog", return_value=items),
            patch("backlog_core.operations.batch_fetch_statuses", return_value=status_map),
        ):
            result = list_items(with_status=True, include_closed=True)
        items_with_status = [it for it in result["items"] if "status" in it]
        assert len(items_with_status) == 7
        # Verify closed items have their GitHub status
        done_item = next(it for it in result["items"] if it["title"] == "Done item")
        assert done_item["status"] == "closed"

    def test_list_items_skipped_items_excluded_regardless(self) -> None:
        """Items with skip=True are excluded even when include_closed=True."""
        items = [_make_item("Normal", status="open", skip=False), _make_item("Skipped", status="open", skip=True)]
        with (
            patch("backlog_core.operations.parse_backlog", return_value=items),
            patch("backlog_core.operations.batch_fetch_statuses", return_value={}),
        ):
            result = list_items(include_closed=True)
        assert result["count"] == 1
        assert result["items"][0]["title"] == "Normal"


# ---------------------------------------------------------------------------
# MCP server backlog_list — include_closed parameter propagation
# ---------------------------------------------------------------------------


class TestMCPIncludeClosedPropagation:
    """Verify the MCP server forwards include_closed to operations.list_items."""

    async def test_mcp_list_defaults_include_closed_false(self) -> None:
        """backlog_list MCP tool defaults include_closed to False."""
        op_result = {"items": [], "count": 0}
        with patch("backlog_core.operations.list_items", return_value=op_result) as mock_list:
            await _call_mcp("backlog_list", {})
        call_kwargs = mock_list.call_args.kwargs
        assert call_kwargs["include_closed"] is False

    async def test_mcp_list_forwards_include_closed_true(self) -> None:
        """backlog_list MCP tool forwards include_closed=True to operations."""
        op_result = {"items": [], "count": 0}
        with patch("backlog_core.operations.list_items", return_value=op_result) as mock_list:
            await _call_mcp("backlog_list", {"include_closed": True})
        call_kwargs = mock_list.call_args.kwargs
        assert call_kwargs["include_closed"] is True

    async def test_mcp_list_returns_closed_items_when_requested(self) -> None:
        """backlog_list with include_closed=True returns items with terminal status."""
        op_result = {
            "items": [
                {"title": "Active", "section": "P1", "issue": "", "plan": ""},
                {"title": "Done", "section": "P1", "issue": "#4", "plan": ""},
            ],
            "count": 2,
        }
        with patch("backlog_core.operations.list_items", return_value=op_result):
            response = await _call_mcp("backlog_list", {"include_closed": True})
        assert response["count"] == 2
        titles = [it["title"] for it in response["items"]]
        assert "Done" in titles
        assert "Active" in titles

    async def test_mcp_list_excludes_closed_by_default(self) -> None:
        """backlog_list without include_closed returns only non-terminal items."""
        op_result = {"items": [{"title": "Active", "section": "P1", "issue": "", "plan": ""}], "count": 1}
        with patch("backlog_core.operations.list_items", return_value=op_result):
            response = await _call_mcp("backlog_list", {})
        assert response["count"] == 1
        assert response["items"][0]["title"] == "Active"

    async def test_mcp_list_combines_include_closed_with_other_filters(self) -> None:
        """backlog_list forwards include_closed alongside other filter params."""
        op_result = {"items": [], "count": 0}
        with patch("backlog_core.operations.list_items", return_value=op_result) as mock_list:
            await _call_mcp("backlog_list", {"include_closed": True, "section": "P0", "with_status": True})
        call_kwargs = mock_list.call_args.kwargs
        assert call_kwargs["include_closed"] is True
        assert call_kwargs["section"] == "P0"
        assert call_kwargs["with_status"] is True
