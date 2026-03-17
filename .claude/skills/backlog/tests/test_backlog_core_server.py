"""Tests for the FastMCP 3.x server layer in backlog_core/server.py.

All 10 MCP tools are tested through the in-memory FastMCP transport using
Client(mcp). Operations are mocked at the boundary via
``unittest.mock.patch("backlog_core.operations.<function_name>")``.

Each tool is tested for:
- Successful operation (verifies parameter forwarding and dict merge)
- BacklogError handling (verifies error key is present in response)

No @pytest.mark.asyncio decorators — asyncio_mode = "auto" is set globally.
All imports are at module level.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from backlog_core.models import BacklogError, Output
from backlog_core.server import mcp
from fastmcp.client import Client

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_output_dict(
    messages: list[str] | None = None, warnings: list[str] | None = None, errors: list[str] | None = None
) -> dict[str, list[str]]:
    """Build the Output.to_dict() structure returned by all operations."""
    return {"messages": messages or [], "warnings": warnings or [], "errors": errors or []}


def _extract_log_messages(mock_log: AsyncMock, level: str | None = None) -> list[str]:
    """Extract message strings from a mocked Context.log call list.

    Args:
        mock_log: The AsyncMock patching Context.log.
        level: If provided, filter to only calls with this log level.

    Returns:
        List of message strings from the captured calls.
    """
    calls = mock_log.call_args_list
    if level is not None:
        calls = [c for c in calls if c.kwargs.get("level") == level]
    messages: list[str] = []
    for c in calls:
        msg = c.kwargs.get("message")
        if msg is None and c.args:
            msg = c.args[0]
        if msg is not None:
            messages.append(msg)
    return messages


async def _call(tool_name: str, params: dict | None = None) -> dict:
    """Call a tool through the in-memory FastMCP transport and parse the result.

    Args:
        tool_name: The registered MCP tool name.
        params: Optional dict of parameters to pass to the tool.

    Returns:
        Parsed JSON response dict from the tool.
    """
    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, params or {})
    return json.loads(result.content[0].text)


# ---------------------------------------------------------------------------
# backlog_add
# ---------------------------------------------------------------------------


async def test_backlog_add_success_returns_merged_result():
    """backlog_add passes params to operations.add_item and merges output."""
    op_result = {"file_path": "/tmp/p1-my-item.md", "title": "My Item", "priority": "P1"}
    with patch("backlog_core.operations.add_item", return_value=op_result) as mock_add:
        response = await _call("backlog_add", {"title": "My Item", "priority": "P1", "description": "A test item"})

    mock_add.assert_called_once()
    call_kwargs = mock_add.call_args.kwargs
    assert call_kwargs["title"] == "My Item"
    assert call_kwargs["priority"] == "P1"
    assert call_kwargs["description"] == "A test item"
    assert response["file_path"] == "/tmp/p1-my-item.md"
    assert response["title"] == "My Item"
    assert "messages" in response
    assert "warnings" in response
    assert "errors" in response


async def test_backlog_add_passes_optional_params():
    """backlog_add forwards source, type_, create_issue, and force to operations."""
    op_result = {"file_path": "/tmp/p0-bug.md", "title": "Bug", "priority": "P0"}
    with patch("backlog_core.operations.add_item", return_value=op_result) as mock_add:
        await _call(
            "backlog_add",
            {
                "title": "Bug",
                "priority": "P0",
                "description": "A real bug",
                "source": "CI pipeline",
                "type": "Bug",
                "create_issue": False,
                "force": True,
            },
        )

    call_kwargs = mock_add.call_args.kwargs
    assert call_kwargs["source"] == "CI pipeline"
    assert call_kwargs["type_"] == "Bug"
    assert call_kwargs["create_issue"] is False
    assert call_kwargs["force"] is True


async def test_backlog_add_backlog_error_returns_error_key():
    """backlog_add catches BacklogError and includes error key in response."""
    with patch("backlog_core.operations.add_item", side_effect=BacklogError("duplicate found")):
        response = await _call("backlog_add", {"title": "Dupe", "priority": "P1", "description": "Already exists"})

    assert response["error"] == "duplicate found"
    assert "messages" in response


async def test_backlog_add_output_messages_included():
    """backlog_add includes output messages from the Output collector."""
    out = Output()
    out.info("created file")
    out.warn("no github token")

    def _add_with_messages(**kwargs):
        kwargs["output"].info("created file")
        kwargs["output"].warn("no github token")
        return {"file_path": "/tmp/p1-item.md"}

    with patch("backlog_core.operations.add_item", side_effect=_add_with_messages):
        response = await _call("backlog_add", {"title": "Item", "priority": "P1", "description": "Test"})

    assert "created file" in response["messages"]
    assert "no github token" in response["warnings"]


# ---------------------------------------------------------------------------
# backlog_list
# ---------------------------------------------------------------------------


async def test_backlog_list_success_returns_items():
    """backlog_list passes params to operations.list_items and merges output."""
    op_result = {"items": [{"title": "Item A", "priority": "P1", "issue": "", "plan": ""}]}
    with patch("backlog_core.operations.list_items", return_value=op_result) as mock_list:
        response = await _call("backlog_list", {})

    mock_list.assert_called_once()
    call_kwargs = mock_list.call_args.kwargs
    assert call_kwargs["with_status"] is False
    assert call_kwargs["from_github"] is False
    assert call_kwargs["label"] is None
    assert response["items"][0]["title"] == "Item A"


async def test_backlog_list_passes_filter_params():
    """backlog_list forwards with_status, from_github, and label flags."""
    op_result = {"items": []}
    with patch("backlog_core.operations.list_items", return_value=op_result) as mock_list:
        await _call("backlog_list", {"with_status": True, "from_github": True, "label": "priority:p0"})

    call_kwargs = mock_list.call_args.kwargs
    assert call_kwargs["with_status"] is True
    assert call_kwargs["from_github"] is True
    assert call_kwargs["label"] == "priority:p0"


async def test_backlog_list_passes_new_filter_params():
    """backlog_list forwards section, status, and title to list_items."""
    op_result = {"items": []}
    with patch("backlog_core.operations.list_items", return_value=op_result) as mock_list:
        await _call("backlog_list", {"section": "P1", "status": "needs-grooming", "title": "auth"})
    call_kwargs = mock_list.call_args.kwargs
    assert call_kwargs["section"] == "P1"
    assert call_kwargs["status"] == "needs-grooming"
    assert call_kwargs["title"] == "auth"


async def test_backlog_list_passes_type_and_topic_params():
    """backlog_list forwards type_ and topic filter params to list_items."""
    op_result = {"items": []}
    with patch("backlog_core.operations.list_items", return_value=op_result) as mock_list:
        await _call("backlog_list", {"type": "Bug", "topic": "auth"})

    call_kwargs = mock_list.call_args.kwargs
    assert call_kwargs["type_"] == "Bug"
    assert call_kwargs["topic"] == "auth"


async def test_backlog_list_type_and_topic_default_to_none():
    """backlog_list passes type_ and topic as None when not provided."""
    op_result = {"items": []}
    with patch("backlog_core.operations.list_items", return_value=op_result) as mock_list:
        await _call("backlog_list", {})

    call_kwargs = mock_list.call_args.kwargs
    assert call_kwargs["type_"] is None
    assert call_kwargs["topic"] is None


async def test_backlog_list_backlog_error_returns_error_key():
    """backlog_list catches BacklogError and includes error key in response."""
    with patch("backlog_core.operations.list_items", side_effect=BacklogError("backlog dir missing")):
        response = await _call("backlog_list", {})

    assert response["error"] == "backlog dir missing"


# ---------------------------------------------------------------------------
# backlog_view
# ---------------------------------------------------------------------------


async def test_backlog_view_success_returns_item_detail():
    """backlog_view calls operations.view_item and merges result with output."""
    op_result = {
        "title": "My Feature",
        "priority": "P1",
        "description": "details",
        "source": "issue",
        "added": "2026-01-01",
        "plan": "",
        "issue": "#42",
        "file_path": "/tmp/p1-my-feature.md",
        "groomed": False,
        "status": "",
        "number": 42,
        "state": "open",
        "body": "## Details\nsome content",
        "labels": ["priority:p1"],
        "milestone": "",
    }
    with patch("backlog_core.operations.view_item", return_value=op_result) as mock_view:
        response = await _call("backlog_view", {"selector": "#42"})

    mock_view.assert_called_once()
    call_kwargs = mock_view.call_args.kwargs
    assert call_kwargs["selector"] == "#42"
    assert call_kwargs["offset"] == 0
    assert call_kwargs["limit"] == 0
    assert response["title"] == "My Feature"
    assert response["issue"] == "#42"


async def test_backlog_view_passes_pagination_params():
    """backlog_view forwards offset and limit to operations."""
    op_result = {"title": "Item", "body": "line1\nline2\nline3"}
    with patch("backlog_core.operations.view_item", return_value=op_result) as mock_view:
        await _call("backlog_view", {"selector": "Item", "offset": 5, "limit": 20})

    call_kwargs = mock_view.call_args.kwargs
    assert call_kwargs["offset"] == 5
    assert call_kwargs["limit"] == 20


async def test_backlog_view_backlog_error_returns_error_key():
    """backlog_view catches BacklogError when item is not found."""
    with patch("backlog_core.operations.view_item", side_effect=BacklogError("No item found for: #999")):
        response = await _call("backlog_view", {"selector": "#999"})

    assert "No item found for: #999" in response["error"]


# ---------------------------------------------------------------------------
# backlog_sync
# ---------------------------------------------------------------------------


async def test_backlog_sync_success_returns_counts():
    """backlog_sync calls operations.sync_items and returns created/pushed counts."""
    op_result = {"created": 3, "pushed": 2}
    with patch("backlog_core.operations.sync_items", return_value=op_result) as mock_sync:
        response = await _call("backlog_sync", {})

    mock_sync.assert_called_once()
    call_kwargs = mock_sync.call_args.kwargs
    assert call_kwargs["dry_run"] is False
    assert response["created"] == 3
    assert response["pushed"] == 2


async def test_backlog_sync_dry_run_forwarded():
    """backlog_sync passes dry_run=True to operations.sync_items."""
    op_result = {"created": 0, "pushed": 0}
    with patch("backlog_core.operations.sync_items", return_value=op_result) as mock_sync:
        await _call("backlog_sync", {"dry_run": True})

    assert mock_sync.call_args.kwargs["dry_run"] is True


async def test_backlog_sync_backlog_error_returns_error_key():
    """backlog_sync catches BacklogError and includes error key."""
    with patch("backlog_core.operations.sync_items", side_effect=BacklogError("GitHub unavailable")):
        response = await _call("backlog_sync", {})

    assert response["error"] == "GitHub unavailable"


# ---------------------------------------------------------------------------
# backlog_close
# ---------------------------------------------------------------------------


async def test_backlog_close_success_returns_closed_item():
    """backlog_close calls operations.close_item and merges result."""
    op_result = {"title": "Done Feature", "issue": "#7"}
    with patch("backlog_core.operations.close_item", return_value=op_result) as mock_close:
        response = await _call("backlog_close", {"selector": "Done Feature", "reason": "wontfix"})

    mock_close.assert_called_once()
    call_kwargs = mock_close.call_args.kwargs
    assert call_kwargs["selector"] == "Done Feature"
    assert call_kwargs["reason"] == "wontfix"
    assert call_kwargs["reference"] == ""
    assert call_kwargs["comment"] == ""
    assert call_kwargs["cleanup"] is False
    assert call_kwargs["force"] is False
    assert response["title"] == "Done Feature"


async def test_backlog_close_passes_cleanup_and_force():
    """backlog_close forwards cleanup and force flags."""
    op_result = {"title": "Item", "issue": "#5"}
    with patch("backlog_core.operations.close_item", return_value=op_result) as mock_close:
        await _call("backlog_close", {"selector": "Item", "reason": "duplicate", "cleanup": True, "force": True})

    call_kwargs = mock_close.call_args.kwargs
    assert call_kwargs["cleanup"] is True
    assert call_kwargs["force"] is True


async def test_backlog_close_backlog_error_returns_error_key():
    """backlog_close catches BacklogError (e.g. item not found)."""
    with patch("backlog_core.operations.close_item", side_effect=BacklogError("item not found")):
        response = await _call("backlog_close", {"selector": "Item", "reason": "wontfix"})

    assert response["error"] == "item not found"


# ---------------------------------------------------------------------------
# backlog_resolve
# ---------------------------------------------------------------------------


async def test_backlog_resolve_success_returns_resolved_item():
    """backlog_resolve calls operations.resolve_item and merges result."""
    op_result = {"title": "Old Feature", "summary": "duplicate of #10", "issue": "#3"}
    with patch("backlog_core.operations.resolve_item", return_value=op_result) as mock_resolve:
        response = await _call("backlog_resolve", {"selector": "Old Feature", "summary": "duplicate of #10"})

    mock_resolve.assert_called_once()
    call_kwargs = mock_resolve.call_args.kwargs
    assert call_kwargs["selector"] == "Old Feature"
    assert call_kwargs["summary"] == "duplicate of #10"
    assert call_kwargs["cleanup"] is False
    assert call_kwargs["force"] is False
    assert response["title"] == "Old Feature"
    assert response["summary"] == "duplicate of #10"


async def test_backlog_resolve_passes_cleanup_and_force():
    """backlog_resolve forwards cleanup and force to operations."""
    op_result = {"title": "Item", "summary": "out of scope", "issue": ""}
    with patch("backlog_core.operations.resolve_item", return_value=op_result) as mock_resolve:
        await _call("backlog_resolve", {"selector": "Item", "summary": "out of scope", "cleanup": True, "force": True})

    call_kwargs = mock_resolve.call_args.kwargs
    assert call_kwargs["cleanup"] is True
    assert call_kwargs["force"] is True


async def test_backlog_resolve_backlog_error_returns_error_key():
    """backlog_resolve catches BacklogError when resolution fails."""
    with patch("backlog_core.operations.resolve_item", side_effect=BacklogError("open PRs exist")):
        response = await _call("backlog_resolve", {"selector": "Item", "summary": "no longer needed"})

    assert response["error"] == "open PRs exist"


# ---------------------------------------------------------------------------
# backlog_update
# ---------------------------------------------------------------------------


async def test_backlog_update_success_with_plan():
    """backlog_update calls operations.update_item and merges result."""
    op_result = {"title": "Feature", "changes": ["plan attached"]}
    with patch("backlog_core.operations.update_item", return_value=op_result) as mock_update:
        response = await _call("backlog_update", {"selector": "Feature", "plan": "plan/tasks-feature.md"})

    mock_update.assert_called_once()
    call_kwargs = mock_update.call_args.kwargs
    assert call_kwargs["selector"] == "Feature"
    assert call_kwargs["plan"] == "plan/tasks-feature.md"
    assert call_kwargs["status"] is None
    assert call_kwargs["create_issue"] is False
    assert call_kwargs["section"] is None
    assert call_kwargs["content"] is None
    assert response["title"] == "Feature"


async def test_backlog_update_passes_status_and_create_issue():
    """backlog_update forwards status and create_issue to operations."""
    op_result = {"title": "Item", "changes": ["status updated"]}
    with patch("backlog_core.operations.update_item", return_value=op_result) as mock_update:
        await _call("backlog_update", {"selector": "Item", "status": "in-progress", "create_issue": True})

    call_kwargs = mock_update.call_args.kwargs
    assert call_kwargs["status"] == "in-progress"
    assert call_kwargs["create_issue"] is True


async def test_backlog_update_passes_section_content():
    """backlog_update forwards section and content for groomed update."""
    op_result = {"title": "Item", "changes": ["groomed"]}
    with patch("backlog_core.operations.update_item", return_value=op_result) as mock_update:
        await _call("backlog_update", {"selector": "Item", "section": "Acceptance Criteria", "content": "some content"})

    call_kwargs = mock_update.call_args.kwargs
    assert call_kwargs["section"] == "Acceptance Criteria"
    assert call_kwargs["content"] == "some content"


async def test_backlog_update_passes_section_and_content():
    """backlog_update forwards section and content for incremental update."""
    op_result = {"title": "Item", "changes": ["section updated"]}
    with patch("backlog_core.operations.update_item", return_value=op_result) as mock_update:
        await _call("backlog_update", {"selector": "Item", "section": "Acceptance Criteria", "content": "- [ ] Done"})

    call_kwargs = mock_update.call_args.kwargs
    assert call_kwargs["section"] == "Acceptance Criteria"
    assert call_kwargs["content"] == "- [ ] Done"


async def test_backlog_update_passes_title():
    """backlog_update forwards title to operations.update_item."""
    op_result = {"title": "Old", "renamed_to": "New Title"}
    with patch("backlog_core.operations.update_item", return_value=op_result) as mock_update:
        await _call("backlog_update", {"selector": "Old", "title": "New Title"})

    call_kwargs = mock_update.call_args.kwargs
    assert call_kwargs["title"] == "New Title"


async def test_backlog_update_passes_description():
    """backlog_update forwards description to operations.update_item."""
    op_result = {"title": "Item", "description_updated": True}
    with patch("backlog_core.operations.update_item", return_value=op_result) as mock_update:
        await _call("backlog_update", {"selector": "Item", "description": "Updated description."})

    call_kwargs = mock_update.call_args.kwargs
    assert call_kwargs["description"] == "Updated description."


async def test_backlog_update_backlog_error_returns_error_key():
    """backlog_update catches BacklogError."""
    with patch("backlog_core.operations.update_item", side_effect=BacklogError("item not found")):
        response = await _call("backlog_update", {"selector": "Missing"})

    assert response["error"] == "item not found"


# ---------------------------------------------------------------------------
# backlog_groom
# ---------------------------------------------------------------------------


async def test_backlog_groom_success_with_section_content():
    """backlog_groom calls operations.groom_item with section and content."""
    op_result = {"title": "Feature", "synced": True}
    with patch("backlog_core.operations.groom_item", return_value=op_result) as mock_groom:
        response = await _call(
            "backlog_groom", {"selector": "Feature", "section": "Acceptance Criteria", "content": "- [ ] Pass tests"}
        )

    mock_groom.assert_called_once()
    call_kwargs = mock_groom.call_args.kwargs
    assert call_kwargs["selector"] == "Feature"
    assert call_kwargs["section"] == "Acceptance Criteria"
    assert call_kwargs["content"] == "- [ ] Pass tests"
    assert response["title"] == "Feature"
    assert response["synced"] is True


async def test_backlog_groom_passes_section_and_content():
    """backlog_groom forwards section and content for incremental update."""
    op_result = {"title": "Item", "synced": False}
    with patch("backlog_core.operations.groom_item", return_value=op_result) as mock_groom:
        await _call("backlog_groom", {"selector": "Item", "section": "Background", "content": "Some background info"})

    call_kwargs = mock_groom.call_args.kwargs
    assert call_kwargs["section"] == "Background"
    assert call_kwargs["content"] == "Some background info"


async def test_backlog_groom_backlog_error_returns_error_key():
    """backlog_groom catches BacklogError."""
    with patch("backlog_core.operations.groom_item", side_effect=BacklogError("item not found")):
        response = await _call("backlog_groom", {"selector": "#999"})

    assert response["error"] == "item not found"


# ---------------------------------------------------------------------------
# backlog_normalize
# ---------------------------------------------------------------------------


async def test_backlog_normalize_success_returns_count():
    """backlog_normalize calls operations.normalize_items and returns count."""
    op_result = {"normalized": 5}
    with patch("backlog_core.operations.normalize_items", return_value=op_result) as mock_normalize:
        response = await _call("backlog_normalize", {})

    mock_normalize.assert_called_once()
    call_kwargs = mock_normalize.call_args.kwargs
    assert call_kwargs["dry_run"] is False
    assert response["normalized"] == 5


async def test_backlog_normalize_dry_run_forwarded():
    """backlog_normalize passes dry_run to operations."""
    op_result = {"normalized": 0}
    with patch("backlog_core.operations.normalize_items", return_value=op_result) as mock_normalize:
        await _call("backlog_normalize", {"dry_run": True})

    assert mock_normalize.call_args.kwargs["dry_run"] is True


async def test_backlog_normalize_backlog_error_returns_error_key():
    """backlog_normalize catches BacklogError."""
    with patch("backlog_core.operations.normalize_items", side_effect=BacklogError("malformed files")):
        response = await _call("backlog_normalize", {})

    assert response["error"] == "malformed files"


# ---------------------------------------------------------------------------
# backlog_pull
# ---------------------------------------------------------------------------


async def test_backlog_pull_success_returns_count():
    """backlog_pull calls operations.pull_items and returns pulled count."""
    op_result = {"pulled": 4}
    with patch("backlog_core.operations.pull_items", return_value=op_result) as mock_pull:
        response = await _call("backlog_pull", {})

    mock_pull.assert_called_once()
    call_kwargs = mock_pull.call_args.kwargs
    assert call_kwargs["dry_run"] is False
    assert call_kwargs["force"] is False
    assert response["pulled"] == 4


async def test_backlog_pull_passes_dry_run_and_force():
    """backlog_pull forwards dry_run and force to operations."""
    op_result = {"pulled": 0}
    with patch("backlog_core.operations.pull_items", return_value=op_result) as mock_pull:
        await _call("backlog_pull", {"dry_run": True, "force": True})

    call_kwargs = mock_pull.call_args.kwargs
    assert call_kwargs["dry_run"] is True
    assert call_kwargs["force"] is True


async def test_backlog_pull_backlog_error_returns_error_key():
    """backlog_pull catches BacklogError."""
    with patch("backlog_core.operations.pull_items", side_effect=BacklogError("no GitHub token")):
        response = await _call("backlog_pull", {})

    assert response["error"] == "no GitHub token"


async def test_backlog_pull_with_issue_number_selector_calls_pull_by_selector():
    """backlog_pull(selector='#321') routes to operations.pull_by_selector."""
    op_result = {"file_path": "/tmp/test.md"}
    with patch("backlog_core.operations.pull_by_selector", return_value=op_result) as mock_pull:
        response = await _call("backlog_pull", {"selector": "#321"})

    mock_pull.assert_called_once()
    assert response["file_path"] == "/tmp/test.md"


async def test_backlog_pull_with_url_selector_calls_pull_by_selector():
    """backlog_pull(selector='https://github.com/owner/repo/issues/42') routes to pull_by_selector."""
    op_result = {"file_path": "/tmp/test.md"}
    with patch("backlog_core.operations.pull_by_selector", return_value=op_result) as mock_pull:
        response = await _call("backlog_pull", {"selector": "https://github.com/owner/repo/issues/42"})

    mock_pull.assert_called_once()
    assert response["file_path"] == "/tmp/test.md"


async def test_backlog_pull_with_title_selector_calls_pull_by_selector():
    """backlog_pull(selector='some title') routes to pull_by_selector."""
    op_result = {"file_path": "/tmp/test.md"}
    with patch("backlog_core.operations.pull_by_selector", return_value=op_result) as mock_pull:
        response = await _call("backlog_pull", {"selector": "some title substring"})

    mock_pull.assert_called_once()
    assert response["file_path"] == "/tmp/test.md"


async def test_backlog_pull_selector_error_returns_error_key():
    """backlog_pull with selector propagates BacklogError."""
    with patch("backlog_core.operations.pull_by_selector", side_effect=BacklogError("item not found")):
        response = await _call("backlog_pull", {"selector": "#999"})

    assert response["error"] == "item not found"


async def test_backlog_pull_single_diff_true_returns_diff_field():
    """backlog_pull with diff=True on a single item returns non-empty 'diff' field."""
    op_result = {"file_path": "/tmp/p1-item.md", "diff": "- old line\n+ new line\n"}
    with patch("backlog_core.operations.pull_by_selector", return_value=op_result) as mock_pull:
        response = await _call("backlog_pull", {"selector": "#42", "diff": True})

    # Arrange: pull_by_selector called with diff=True
    call_kwargs = mock_pull.call_args.kwargs
    assert call_kwargs["diff"] is True
    # Assert: diff key present and non-empty in response
    assert "diff" in response
    assert response["diff"] == "- old line\n+ new line\n"


async def test_backlog_pull_single_diff_false_omits_diff_field():
    """backlog_pull with diff=False (default) returns no 'diff' field."""
    op_result = {"file_path": "/tmp/p1-item.md"}
    with patch("backlog_core.operations.pull_by_selector", return_value=op_result) as mock_pull:
        response = await _call("backlog_pull", {"selector": "#42"})

    # Arrange: pull_by_selector called with diff=False (default)
    call_kwargs = mock_pull.call_args.kwargs
    assert call_kwargs.get("diff", False) is False
    # Assert: no diff key in response
    assert "diff" not in response


async def test_backlog_pull_no_selector_uses_bulk_pull():
    """backlog_pull without selector calls pull_items (bulk), not pull_by_selector."""
    op_result = {"pulled": 3}
    with (
        patch("backlog_core.operations.pull_items", return_value=op_result) as mock_bulk,
        patch("backlog_core.operations.pull_by_selector") as mock_single,
    ):
        response = await _call("backlog_pull", {})

    mock_bulk.assert_called_once()
    mock_single.assert_not_called()
    assert response["pulled"] == 3


# ---------------------------------------------------------------------------
# Cross-cutting: output dict structure is always present
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Signature checks: backlog_groom and backlog_view parameter contracts
# ---------------------------------------------------------------------------


def test_backlog_groom_no_groomed_content_param():
    """backlog_groom should not accept groomed_content parameter."""
    import inspect

    from backlog_core.server import backlog_groom

    sig = inspect.signature(backlog_groom)
    assert "groomed_content" not in sig.parameters


def test_backlog_groom_has_entry_id_param():
    """backlog_groom should accept entry_id parameter."""
    import inspect

    from backlog_core.server import backlog_groom

    sig = inspect.signature(backlog_groom)
    assert "entry_id" in sig.parameters


def test_backlog_strike_entry_tool_exists():
    """backlog_strike_entry should be a registered MCP tool."""
    from backlog_core.server import backlog_strike_entry

    assert callable(backlog_strike_entry)


def test_backlog_view_show_string_int_conversion():
    """backlog_view should accept show parameter."""
    import inspect

    from backlog_core.server import backlog_view

    sig = inspect.signature(backlog_view)
    assert "show" in sig.parameters


# ---------------------------------------------------------------------------
# backlog_list: type and topic parameter schema presence
# ---------------------------------------------------------------------------


def test_backlog_list_type_param_schema():
    """backlog_list MCP tool schema includes a 'type_' parameter for type filtering.

    Tests: MCP tool parameter schema completeness for type filter.
    How: Inspect backlog_list function signature for type_ parameter.
    Why: MCP consumers discover available filters through tool schema introspection.
    """
    import inspect

    from backlog_core.server import backlog_list

    sig = inspect.signature(backlog_list)
    assert "type_" in sig.parameters


def test_backlog_list_topic_param_schema():
    """backlog_list MCP tool schema includes a 'topic' parameter for topic filtering.

    Tests: MCP tool parameter schema completeness for topic filter.
    How: Inspect backlog_list function signature for topic parameter.
    Why: MCP consumers discover available filters through tool schema introspection.
    """
    import inspect

    from backlog_core.server import backlog_list

    sig = inspect.signature(backlog_list)
    assert "topic" in sig.parameters


# ---------------------------------------------------------------------------
# backlog_view show string-to-int conversion
# ---------------------------------------------------------------------------


async def test_backlog_view_show_numeric_string_converts_to_int():
    """backlog_view converts show='2' (string) to int 2 before passing to view_item."""
    op_result = {"title": "My Item", "body": "content"}
    with patch("backlog_core.operations.view_item", return_value=op_result) as mock_view:
        await _call("backlog_view", {"selector": "#1", "show": "2"})

    call_kwargs = mock_view.call_args.kwargs
    assert call_kwargs["show"] == 2, f"Expected int 2, got {call_kwargs['show']!r}"


async def test_backlog_view_show_non_numeric_string_passed_as_str():
    """backlog_view passes show='last' as a string (not converted to int)."""
    op_result = {"title": "My Item", "body": "content"}
    with patch("backlog_core.operations.view_item", return_value=op_result) as mock_view:
        await _call("backlog_view", {"selector": "#1", "show": "last"})

    call_kwargs = mock_view.call_args.kwargs
    assert call_kwargs["show"] == "last", f"Expected str 'last', got {call_kwargs['show']!r}"


@pytest.mark.parametrize(
    ("tool_name", "params", "mock_target", "mock_return"),
    [
        (
            "backlog_add",
            {"title": "T", "priority": "P1", "description": "D"},
            "backlog_core.operations.add_item",
            {"file_path": "f"},
        ),
        ("backlog_list", {}, "backlog_core.operations.list_items", {"items": []}),
        ("backlog_view", {"selector": "#1"}, "backlog_core.operations.view_item", {"title": "T"}),
        ("backlog_sync", {}, "backlog_core.operations.sync_items", {"created": 0}),
        ("backlog_normalize", {}, "backlog_core.operations.normalize_items", {"normalized": 0}),
        ("backlog_pull", {}, "backlog_core.operations.pull_items", {"pulled": 0}),
    ],
)
async def test_output_fields_always_present_on_success(tool_name, params, mock_target, mock_return):
    """Every tool response includes messages, warnings, and errors keys on success."""
    with patch(mock_target, return_value=mock_return):
        response = await _call(tool_name, params)

    assert "messages" in response, f"{tool_name}: missing 'messages' key"
    assert "warnings" in response, f"{tool_name}: missing 'warnings' key"
    assert "errors" in response, f"{tool_name}: missing 'errors' key"
    assert isinstance(response["messages"], list)
    assert isinstance(response["warnings"], list)
    assert isinstance(response["errors"], list)


@pytest.mark.parametrize(
    ("tool_name", "params", "mock_target"),
    [
        ("backlog_add", {"title": "T", "priority": "P1", "description": "D"}, "backlog_core.operations.add_item"),
        ("backlog_list", {}, "backlog_core.operations.list_items"),
        ("backlog_view", {"selector": "#1"}, "backlog_core.operations.view_item"),
        ("backlog_sync", {}, "backlog_core.operations.sync_items"),
        ("backlog_close", {"selector": "X", "reason": "wontfix"}, "backlog_core.operations.close_item"),
        ("backlog_resolve", {"selector": "X", "summary": "done"}, "backlog_core.operations.resolve_item"),
        ("backlog_update", {"selector": "X"}, "backlog_core.operations.update_item"),
        ("backlog_groom", {"selector": "X"}, "backlog_core.operations.groom_item"),
        ("backlog_normalize", {}, "backlog_core.operations.normalize_items"),
        ("backlog_pull", {}, "backlog_core.operations.pull_items"),
        (
            "backlog_strike_entry",
            {"selector": "X", "entry_id": "2026-01-01T00:00:00Z", "reason": "test"},
            "backlog_core.operations.strike_entry",
        ),
    ],
)
async def test_output_fields_always_present_on_error(tool_name, params, mock_target):
    """Every tool response includes error key and output fields on BacklogError."""
    with patch(mock_target, side_effect=BacklogError("test error")):
        response = await _call(tool_name, params)

    assert "error" in response, f"{tool_name}: missing 'error' key on BacklogError"
    assert response["error"] == "test error"
    assert "messages" in response, f"{tool_name}: missing 'messages' key on BacklogError"
    assert "warnings" in response, f"{tool_name}: missing 'warnings' key on BacklogError"
    assert "errors" in response, f"{tool_name}: missing 'errors' key on BacklogError"


# ---------------------------------------------------------------------------
# Tool registration verification
# ---------------------------------------------------------------------------


async def test_all_tools_are_registered():
    """Verify all expected tool names are registered in the MCP server."""
    expected = {
        "backlog_add",
        "backlog_list",
        "backlog_view",
        "backlog_sync",
        "backlog_close",
        "backlog_resolve",
        "backlog_update",
        "backlog_groom",
        "backlog_normalize",
        "backlog_pull",
        "backlog_strike_entry",
    }
    async with Client(mcp) as client:
        tools = await client.list_tools()

    registered = {t.name for t in tools}
    assert expected.issubset(registered), f"Missing tools: {expected - registered}"


def test_mcp_server_name_is_backlog_mcp():
    """The FastMCP instance is named 'backlog'."""
    assert mcp.name == "backlog"


# ---------------------------------------------------------------------------
# Output collector is passed (not None) to operations
# ---------------------------------------------------------------------------


async def test_backlog_add_passes_output_instance_to_operations():
    """backlog_add provides an Output instance as the 'output' keyword arg."""
    captured: list[Output] = []

    def _capture(**kwargs):
        captured.append(kwargs["output"])
        return {"file_path": "/tmp/p1-x.md"}

    with patch("backlog_core.operations.add_item", side_effect=_capture):
        await _call("backlog_add", {"title": "X", "priority": "P1", "description": "D"})

    assert len(captured) == 1
    assert isinstance(captured[0], Output)


async def test_backlog_list_passes_output_instance_to_operations():
    """backlog_list provides an Output instance as the 'output' keyword arg."""
    captured: list[Output] = []

    def _capture(**kwargs):
        captured.append(kwargs["output"])
        return {"items": []}

    with patch("backlog_core.operations.list_items", side_effect=_capture):
        await _call("backlog_list", {})

    assert len(captured) == 1
    assert isinstance(captured[0], Output)


# ---------------------------------------------------------------------------
# Tool returns non-error result — error key must NOT be present
# ---------------------------------------------------------------------------


async def test_backlog_add_no_error_key_on_success():
    """Successful backlog_add response must not contain an 'error' key."""
    with patch("backlog_core.operations.add_item", return_value={"file_path": "/tmp/p1-ok.md"}):
        response = await _call("backlog_add", {"title": "OK", "priority": "P1", "description": "Fine"})

    assert "error" not in response


async def test_backlog_sync_no_error_key_on_success():
    """Successful backlog_sync response must not contain an 'error' key."""
    with patch("backlog_core.operations.sync_items", return_value={"created": 1, "pushed": 0}):
        response = await _call("backlog_sync", {})

    assert "error" not in response


# ---------------------------------------------------------------------------
# ctx logging: backlog_sync
# ---------------------------------------------------------------------------


async def test_backlog_sync_ctx_info_start_message():
    """backlog_sync emits ctx.info with start message before the operation."""
    op_result = {"created": 2, "pushed": 1}
    with (
        patch("backlog_core.operations.sync_items", return_value=op_result),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_sync", {})

    messages = _extract_log_messages(mock_log)
    assert "Starting backlog sync" in messages


async def test_backlog_sync_ctx_info_start_message_dry_run():
    """backlog_sync emits ctx.info with '(dry-run)' suffix when dry_run=True."""
    op_result = {"created": 0, "pushed": 0}
    with (
        patch("backlog_core.operations.sync_items", return_value=op_result),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_sync", {"dry_run": True})

    messages = _extract_log_messages(mock_log)
    assert "Starting backlog sync (dry-run)" in messages


async def test_backlog_sync_ctx_info_completion_message():
    """backlog_sync emits ctx.info with completion summary including counts."""
    op_result = {"created": 3, "pushed": 5}
    with (
        patch("backlog_core.operations.sync_items", return_value=op_result),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_sync", {})

    messages = _extract_log_messages(mock_log)
    assert "Sync complete: 3 issue(s) created, 5 item(s) pushed" in messages


async def test_backlog_sync_ctx_warning_surfaces_output_warnings():
    """backlog_sync surfaces each out.warnings entry via ctx.warning."""

    def _sync_with_warnings(**kwargs):
        kwargs["output"].warn("token expiring soon")
        kwargs["output"].warn("rate limit near")
        return {"created": 0, "pushed": 0}

    with (
        patch("backlog_core.operations.sync_items", side_effect=_sync_with_warnings),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_sync", {})

    warning_messages = _extract_log_messages(mock_log, level="warning")
    assert "token expiring soon" in warning_messages
    assert "rate limit near" in warning_messages


# ---------------------------------------------------------------------------
# ctx logging: backlog_groom
# ---------------------------------------------------------------------------


async def test_backlog_groom_ctx_info_start_message():
    """backlog_groom emits ctx.info with 'Grooming item: {selector}' before operation."""
    op_result = {"title": "Auth Feature", "synced": True}
    with (
        patch("backlog_core.operations.groom_item", return_value=op_result),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_groom", {"selector": "#42"})

    messages = _extract_log_messages(mock_log)
    assert "Grooming item: #42" in messages


async def test_backlog_groom_ctx_info_completion_message():
    """backlog_groom emits ctx.info with 'Groomed: {title}' after operation."""
    op_result = {"title": "Auth Feature", "synced": True}
    with (
        patch("backlog_core.operations.groom_item", return_value=op_result),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_groom", {"selector": "#42"})

    messages = _extract_log_messages(mock_log)
    assert "Groomed: Auth Feature" in messages


async def test_backlog_groom_ctx_warning_surfaces_output_warnings():
    """backlog_groom surfaces out.warnings via ctx.warning."""

    def _groom_with_warnings(**kwargs):
        kwargs["output"].warn("section missing")
        return {"title": "Item", "synced": False}

    with (
        patch("backlog_core.operations.groom_item", side_effect=_groom_with_warnings),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_groom", {"selector": "Item"})

    warning_messages = _extract_log_messages(mock_log, level="warning")
    assert "section missing" in warning_messages


# ---------------------------------------------------------------------------
# ctx logging: backlog_normalize
# ---------------------------------------------------------------------------


async def test_backlog_normalize_ctx_info_start_message():
    """backlog_normalize emits ctx.info with start message before operation."""
    op_result = {"updated": 3}
    with (
        patch("backlog_core.operations.normalize_items", return_value=op_result),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_normalize", {})

    messages = _extract_log_messages(mock_log)
    assert "Starting normalize" in messages


async def test_backlog_normalize_ctx_info_start_message_dry_run():
    """backlog_normalize emits ctx.info with '(dry-run)' suffix when dry_run=True."""
    op_result = {"updated": 0}
    with (
        patch("backlog_core.operations.normalize_items", return_value=op_result),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_normalize", {"dry_run": True})

    messages = _extract_log_messages(mock_log)
    assert "Starting normalize (dry-run)" in messages


async def test_backlog_normalize_ctx_info_completion_message():
    """backlog_normalize emits ctx.info with 'Normalized N file(s)' after operation."""
    op_result = {"updated": 7}
    with (
        patch("backlog_core.operations.normalize_items", return_value=op_result),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_normalize", {})

    messages = _extract_log_messages(mock_log)
    assert "Normalized 7 file(s)" in messages


async def test_backlog_normalize_ctx_info_completion_message_dry_run():
    """backlog_normalize completion message includes '(dry-run)' suffix."""
    op_result = {"updated": 2}
    with (
        patch("backlog_core.operations.normalize_items", return_value=op_result),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_normalize", {"dry_run": True})

    messages = _extract_log_messages(mock_log)
    assert "Normalized 2 file(s) (dry-run)" in messages


async def test_backlog_normalize_ctx_warning_surfaces_output_warnings():
    """backlog_normalize surfaces out.warnings via ctx.warning."""

    def _normalize_with_warnings(**kwargs):
        kwargs["output"].warn("malformed frontmatter in p1-old.md")
        return {"updated": 1}

    with (
        patch("backlog_core.operations.normalize_items", side_effect=_normalize_with_warnings),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_normalize", {})

    warning_messages = _extract_log_messages(mock_log, level="warning")
    assert "malformed frontmatter in p1-old.md" in warning_messages


# ---------------------------------------------------------------------------
# ctx logging: backlog_pull (bulk)
# ---------------------------------------------------------------------------


async def test_backlog_pull_bulk_ctx_info_start_message():
    """backlog_pull (bulk) emits ctx.info with start message before operation."""
    op_result = {"pulled": 5}
    with (
        patch("backlog_core.operations.pull_items", return_value=op_result),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_pull", {})

    messages = _extract_log_messages(mock_log)
    assert "Starting bulk pull from GitHub" in messages


async def test_backlog_pull_bulk_ctx_info_start_message_dry_run():
    """backlog_pull (bulk) emits ctx.info with '(dry-run)' suffix."""
    op_result = {"pulled": 0}
    with (
        patch("backlog_core.operations.pull_items", return_value=op_result),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_pull", {"dry_run": True})

    messages = _extract_log_messages(mock_log)
    assert "Starting bulk pull from GitHub (dry-run)" in messages


async def test_backlog_pull_bulk_ctx_info_completion_message():
    """backlog_pull (bulk) emits ctx.info with 'Pull complete: N item(s) pulled'."""
    op_result = {"pulled": 8}
    with (
        patch("backlog_core.operations.pull_items", return_value=op_result),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_pull", {})

    messages = _extract_log_messages(mock_log)
    assert "Pull complete: 8 item(s) pulled" in messages


async def test_backlog_pull_bulk_ctx_warning_surfaces_output_warnings():
    """backlog_pull (bulk) surfaces out.warnings via ctx.warning."""

    def _pull_with_warnings(**kwargs):
        kwargs["output"].warn("issue #99 has no body")
        return {"pulled": 1}

    with (
        patch("backlog_core.operations.pull_items", side_effect=_pull_with_warnings),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_pull", {})

    warning_messages = _extract_log_messages(mock_log, level="warning")
    assert "issue #99 has no body" in warning_messages


# ---------------------------------------------------------------------------
# ctx logging: backlog_pull (single-item)
# ---------------------------------------------------------------------------


async def test_backlog_pull_single_ctx_info_start_message():
    """backlog_pull (single) emits ctx.info with 'Pulling issue: {selector}'."""
    op_result = {"file_path": "/tmp/p1-item.md"}
    with (
        patch("backlog_core.operations.pull_by_selector", return_value=op_result),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_pull", {"selector": "#321"})

    messages = _extract_log_messages(mock_log)
    assert "Pulling issue: #321" in messages


async def test_backlog_pull_single_ctx_info_completion_message():
    """backlog_pull (single) emits ctx.info with 'Pulled: {file_path}' after operation."""
    op_result = {"file_path": "/tmp/p1-my-item.md"}
    with (
        patch("backlog_core.operations.pull_by_selector", return_value=op_result),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_pull", {"selector": "#42"})

    messages = _extract_log_messages(mock_log)
    assert "Pulled: /tmp/p1-my-item.md" in messages


async def test_backlog_pull_single_ctx_info_nothing_pulled():
    """backlog_pull (single) emits 'Nothing pulled' when file_path is absent."""
    op_result = {"message": "already up to date"}
    with (
        patch("backlog_core.operations.pull_by_selector", return_value=op_result),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_pull", {"selector": "#42"})

    messages = _extract_log_messages(mock_log)
    assert "Nothing pulled" in messages


async def test_backlog_pull_single_ctx_warning_surfaces_output_warnings():
    """backlog_pull (single) surfaces out.warnings via ctx.warning."""

    def _pull_with_warnings(selector, **kwargs):
        kwargs["output"].warn("local file newer")
        return {"file_path": "/tmp/p1-item.md"}

    with (
        patch("backlog_core.operations.pull_by_selector", side_effect=_pull_with_warnings),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_pull", {"selector": "#10"})

    warning_messages = _extract_log_messages(mock_log, level="warning")
    assert "local file newer" in warning_messages


# ---------------------------------------------------------------------------
# ctx logging: log levels are correct
# ---------------------------------------------------------------------------


async def test_backlog_sync_ctx_uses_info_level_for_start_and_completion():
    """backlog_sync uses 'info' level for start and completion messages."""
    op_result = {"created": 0, "pushed": 0}
    with (
        patch("backlog_core.operations.sync_items", return_value=op_result),
        patch("fastmcp.server.context.Context.log", new_callable=AsyncMock) as mock_log,
    ):
        await _call("backlog_sync", {})

    info_messages = _extract_log_messages(mock_log, level="info")
    assert "Starting backlog sync" in info_messages
    assert "Sync complete: 0 issue(s) created, 0 item(s) pushed" in info_messages
