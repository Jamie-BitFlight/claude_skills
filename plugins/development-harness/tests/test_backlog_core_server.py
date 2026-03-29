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
import logging
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import backlog_core.server as _server_mod
import pytest
from backlog_core.models import BackendAvailability, BackendStatus, BacklogError, Output
from backlog_core.server import _beads_lifespan, mcp
from fastmcp.client import Client

if TYPE_CHECKING:
    from pathlib import Path

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
    assert call_kwargs["from_github"] is False
    assert call_kwargs["label"] is None
    assert response["items"][0]["title"] == "Item A"


async def test_backlog_list_passes_filter_params():
    """backlog_list forwards from_github and label flags."""
    op_result = {"items": []}
    with patch("backlog_core.operations.list_items", return_value=op_result) as mock_list:
        await _call("backlog_list", {"from_github": True, "label": "priority:p0"})

    call_kwargs = mock_list.call_args.kwargs
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


async def test_backlog_list_search_filters_across_title_description_topic_type():
    """backlog_list search= matches items where any of title, description, topic, or type contains the needle."""
    items = [
        {"title": "SAM migration", "description": "migrate tasks", "topic": "devops", "type": "Feature"},
        {"title": "Auth bug", "description": "oauth token issue", "topic": "security", "type": "Bug"},
        {"title": "Docs update", "description": "update readme", "topic": "sam-related", "type": "Docs"},
        {"title": "Refactor", "description": "clean up", "topic": "quality", "type": "Refactor"},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "sam"})

    returned_titles = [item["title"] for item in response["items"]]
    # "SAM migration" matches title; "Docs update" matches topic "sam-related"
    assert "SAM migration" in returned_titles
    assert "Docs update" in returned_titles
    # Items without "sam" in any field are excluded
    assert "Auth bug" not in returned_titles
    assert "Refactor" not in returned_titles


async def test_backlog_list_search_is_case_insensitive():
    """backlog_list search= comparison is case-insensitive."""
    items = [
        {"title": "SAM Pipeline", "description": "", "topic": "", "type": "Feature"},
        {"title": "unrelated", "description": "", "topic": "", "type": "Bug"},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response_lower = await _call("backlog_list", {"search": "sam"})
        response_upper = await _call("backlog_list", {"search": "SAM"})

    assert response_lower["items"] == response_upper["items"]
    assert len(response_lower["items"]) == 1
    assert response_lower["items"][0]["title"] == "SAM Pipeline"


async def test_backlog_list_search_none_returns_all_items():
    """backlog_list without search= does not filter by search and returns all items."""
    items = [
        {"title": "Item A", "description": "", "topic": "", "type": "Feature"},
        {"title": "Item B", "description": "", "topic": "", "type": "Bug"},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {})

    assert response["pagination"]["total"] == 2
    assert len(response["items"]) == 2


async def test_backlog_list_pagination_returns_correct_page():
    """backlog_list offset=10, limit=5 returns items 10-14 from the filtered set."""
    items = [{"title": f"Item {i}", "description": "", "topic": "", "type": "Feature"} for i in range(20)]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"offset": 10, "limit": 5})

    assert response["pagination"]["offset"] == 10
    assert response["pagination"]["limit"] == 5
    assert response["pagination"]["total"] == 20
    assert response["pagination"]["has_more"] is True
    assert len(response["items"]) == 5
    assert response["items"][0]["title"] == "Item 10"
    assert response["items"][4]["title"] == "Item 14"
    assert "next_call" in response


async def test_backlog_list_pagination_last_page_has_more_false():
    """backlog_list returns has_more=False when the page exhausts the item list."""
    items = [{"title": f"Item {i}", "description": "", "topic": "", "type": "Feature"} for i in range(8)]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"offset": 5, "limit": 5})

    assert response["pagination"]["has_more"] is False
    assert len(response["items"]) == 3  # items 5, 6, 7
    assert "next_call" not in response


async def test_backlog_list_autopagination_stays_within_token_budget():
    """backlog_list auto-pagination (limit=0) keeps response JSON under ~17600 chars."""
    import json

    # 500 items with a realistic-sized description each (~200 chars per item serialised).
    items = [
        {
            "title": f"Backlog item number {i:04d}",
            "description": "A detailed description of this backlog item that is moderately long.",
            "topic": "engineering",
            "type": "Feature",
            "priority": "P1",
            "issue": f"#{i}",
            "plan": "",
        }
        for i in range(500)
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {})

    # The items sub-list alone must fit in the budget.
    items_json_len = len(json.dumps(response["items"]))
    assert items_json_len <= 17_600
    assert response["pagination"]["has_more"] is True
    assert "next_call" in response


async def test_backlog_list_search_combined_with_section_filter():
    """backlog_list search= and section= can be combined — both filters apply."""
    items = [
        {"title": "SAM auth", "description": "", "topic": "", "type": "Feature", "priority": "P1"},
        {"title": "SAM deploy", "description": "", "topic": "", "type": "Feature", "priority": "P2"},
    ]
    # Operations layer already applied the section filter before returning items.
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result) as mock_list:
        response = await _call("backlog_list", {"section": "P1", "search": "sam"})

    # section is forwarded to operations
    assert mock_list.call_args.kwargs["section"] == "P1"
    # search is applied in the tool layer — both items match "sam"
    assert len(response["items"]) == 2


async def test_backlog_list_search_or_operator_matches_either_term():
    """backlog_list search='auth OR deploy' matches items containing either term."""
    items = [
        {"title": "Auth service", "description": "", "topic": "", "type": "Feature"},
        {"title": "Deploy pipeline", "description": "", "topic": "", "type": "Feature"},
        {"title": "Refactor models", "description": "", "topic": "", "type": "Refactor"},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "auth OR deploy"})

    returned_titles = [item["title"] for item in response["items"]]
    assert "Auth service" in returned_titles
    assert "Deploy pipeline" in returned_titles
    assert "Refactor models" not in returned_titles


async def test_backlog_list_search_and_operator_requires_both_terms():
    """backlog_list search='auth AND bug' only matches items containing both terms."""
    items = [
        {"title": "Auth bug", "description": "", "topic": "", "type": "Bug"},
        {"title": "Auth feature", "description": "", "topic": "", "type": "Feature"},
        {"title": "Deploy bug", "description": "", "topic": "", "type": "Bug"},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "auth AND bug"})

    returned_titles = [item["title"] for item in response["items"]]
    assert "Auth bug" in returned_titles
    assert "Auth feature" not in returned_titles
    assert "Deploy bug" not in returned_titles


async def test_backlog_list_search_regex_slash_form_matches_pattern():
    """backlog_list search='/auth.*bug/' matches items via regex."""
    items = [
        {"title": "Auth token bug", "description": "", "topic": "", "type": "Bug"},
        {"title": "Auth feature", "description": "", "topic": "", "type": "Feature"},
        {"title": "Unrelated", "description": "", "topic": "", "type": "Refactor"},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "/auth.*bug/"})

    returned_titles = [item["title"] for item in response["items"]]
    assert "Auth token bug" in returned_titles
    assert "Auth feature" not in returned_titles
    assert "Unrelated" not in returned_titles


async def test_backlog_list_search_regex_prefix_form_matches_pattern():
    """backlog_list search='regex:auth.*bug' matches items via regex: prefix form."""
    items = [
        {"title": "Auth token bug", "description": "", "topic": "", "type": "Bug"},
        {"title": "Auth feature", "description": "", "topic": "", "type": "Feature"},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "regex:auth.*bug"})

    returned_titles = [item["title"] for item in response["items"]]
    assert "Auth token bug" in returned_titles
    assert "Auth feature" not in returned_titles


async def test_backlog_list_search_field_specific_title_prefix():
    """backlog_list search='title:auth' restricts match to the title field only."""
    items = [
        {"title": "Auth service", "description": "", "topic": "", "type": "Feature"},
        {"title": "Unrelated", "description": "", "topic": "auth", "type": "Feature"},
        {"title": "Deploy", "description": "", "topic": "", "type": "Bug"},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "title:auth"})

    returned_titles = [item["title"] for item in response["items"]]
    assert "Auth service" in returned_titles
    # "Unrelated" has auth in topic, not title — must not match title:auth
    assert "Unrelated" not in returned_titles
    assert "Deploy" not in returned_titles


async def test_backlog_list_search_field_specific_type_prefix():
    """backlog_list search='type:bug' restricts match to the type field only."""
    items = [
        {"title": "Auth bug fix", "description": "", "topic": "", "type": "Bug"},
        {"title": "Bug tracker", "description": "", "topic": "", "type": "Feature"},
        {"title": "Deploy", "description": "", "topic": "", "type": "Feature"},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "type:bug"})

    returned_titles = [item["title"] for item in response["items"]]
    assert "Auth bug fix" in returned_titles
    # "Bug tracker" has "bug" in title but type is Feature — must not match type:bug
    assert "Bug tracker" not in returned_titles


async def test_backlog_list_search_invalid_regex_falls_back_to_plain_text():
    """backlog_list search='/[invalid/' falls back to plain substring match on the raw term."""
    items = [
        {"title": "/[invalid/ literal", "description": "", "topic": "", "type": "Feature"},
        {"title": "Unrelated", "description": "", "topic": "", "type": "Feature"},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "/[invalid/"})

    # Falls back to substring match on the literal string "/[invalid/"
    returned_titles = [item["title"] for item in response["items"]]
    assert "/[invalid/ literal" in returned_titles
    assert "Unrelated" not in returned_titles


async def test_backlog_list_response_includes_pagination_key_always():
    """backlog_list always includes a pagination key in a successful response."""
    op_result = {"items": [{"title": "X", "description": "", "topic": "", "type": "Bug"}]}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {})

    assert "pagination" in response
    assert "offset" in response["pagination"]
    assert "limit" in response["pagination"]
    assert "total" in response["pagination"]
    assert "has_more" in response["pagination"]


async def test_backlog_list_response_includes_backend_key():
    """backlog_list always includes a 'backend' key in the response root.

    Tests: backend dict is present in every successful response.
    How: Call backlog_list with mocked list_items and probe_backend_status.
    Why: Consumers rely on backend availability signal to diagnose empty results.
    """
    op_result = {"items": []}
    reachable_status = BackendStatus(
        availability=BackendAvailability.REACHABLE,
        open_count=47,
        total_count=203,
        cache_open_count=0,
        cache_total_count=0,
    )
    with (
        patch("backlog_core.operations.list_items", return_value=op_result),
        patch("backlog_core.server._probe_backend_status", return_value=reachable_status),
    ):
        response = await _call("backlog_list", {})

    assert "backend" in response
    assert response["backend"]["name"] == "GitHub"
    assert response["backend"]["availability"] == "reachable"
    assert response["backend"]["open_count"] == 47
    assert response["backend"]["total_count"] == 203


async def test_backlog_list_backend_reachable_message_format():
    """backlog_list messages includes a formatted backend status line when reachable.

    Tests: human-readable backend status string with live counts.
    How: Mock probe_backend_status to return reachable status with known counts.
    Why: Users should see 'Backend: GitHub, Backend availability: reachable, Backend items (N open / M total)'.
    """
    op_result = {"items": []}
    reachable_status = BackendStatus(
        availability=BackendAvailability.REACHABLE,
        open_count=178,
        total_count=245,
        cache_open_count=0,
        cache_total_count=0,
    )
    with (
        patch("backlog_core.operations.list_items", return_value=op_result),
        patch("backlog_core.server._probe_backend_status", return_value=reachable_status),
    ):
        response = await _call("backlog_list", {})

    status_messages = [m for m in response["messages"] if m.startswith("Backend:")]
    assert len(status_messages) == 1
    assert (
        status_messages[0] == "Backend: GitHub, Backend availability: reachable, Backend items (178 open / 245 total)"
    )


async def test_backlog_list_backend_unavailable_message_format():
    """backlog_list messages includes a formatted backend status line when unavailable.

    Tests: human-readable backend status string with cache fallback counts.
    How: Mock probe_backend_status to return needs_authentication status with cache counts.
    Why: Users should see 'Backend: GitHub, Backend availability: needs_authentication, Backend items (--- open / --- total)[cache: N open / M total]'.
    """
    op_result = {"items": [{"title": "Cached item", "priority": "P1", "issue": "", "plan": ""}]}
    unavailable_status = BackendStatus(
        availability=BackendAvailability.NEEDS_AUTHENTICATION,
        open_count=None,
        total_count=None,
        cache_open_count=0,
        cache_total_count=300,
        error="GITHUB_TOKEN not set",
    )
    with (
        patch("backlog_core.operations.list_items", return_value=op_result),
        patch("backlog_core.server._probe_backend_status", return_value=unavailable_status),
    ):
        response = await _call("backlog_list", {})

    assert response["backend"]["availability"] == "needs_authentication"
    assert response["backend"]["open_count"] is None
    status_messages = [m for m in response["messages"] if m.startswith("Backend:")]
    assert len(status_messages) == 1
    assert "--- open / --- total" in status_messages[0]
    assert "[cache:" in status_messages[0]


async def test_backlog_list_backend_unavailable_cache_open_count_reflects_filtered_total():
    """backlog_list sets cache_open_count to the filtered item total even when GitHub is unavailable.

    Tests: cache_open_count reflects the list result, not a stale probe value.
    How: Return 2 items from list_items with unavailable probe_backend_status.
    Why: cache_open_count is the count of what was actually served, independent of GitHub.
    """
    op_result = {"items": [{"title": "Item A"}, {"title": "Item B"}]}
    unavailable_status = BackendStatus(
        availability=BackendAvailability.NEEDS_AUTHENTICATION,
        open_count=None,
        total_count=None,
        cache_open_count=0,
        cache_total_count=50,
        error="GITHUB_TOKEN not set",
    )
    with (
        patch("backlog_core.operations.list_items", return_value=op_result),
        patch("backlog_core.server._probe_backend_status", return_value=unavailable_status),
    ):
        response = await _call("backlog_list", {})

    # cache_open_count is updated to reflect the filtered item count (2)
    assert response["backend"]["cache_open_count"] == 2


async def test_backlog_list_backend_error_path_includes_backend_key():
    """backlog_list BacklogError path also includes a 'backend' key.

    Tests: backend field present even in error responses.
    How: Raise BacklogError from list_items; probe_backend_status runs independently.
    Why: Callers must always find backend availability, even when listing fails.
    """
    unavailable_status = BackendStatus(
        availability=BackendAvailability.ERROR,
        open_count=None,
        total_count=None,
        cache_open_count=0,
        cache_total_count=0,
        error="connection refused",
    )
    with (
        patch("backlog_core.operations.list_items", side_effect=BacklogError("backlog dir missing")),
        patch("backlog_core.server._probe_backend_status", return_value=unavailable_status),
    ):
        response = await _call("backlog_list", {})

    assert "error" in response
    assert "backend" in response
    assert response["backend"]["availability"] == "error"


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
        response = await _call("backlog_view", {"selector": "#42", "summary": False})

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


async def test_backlog_view_default_includes_content():
    """backlog_view default call (include_content omitted) returns body and sections keys.

    Tests: Backward compatibility guarantee — existing callers receive body and sections.
    How: Mock operations.view_item to return a dict with body and sections keys.
         Call backlog_view without include_content parameter (defaults to True).
         Assert both keys are present in the response.
    Why: The include_content=True default must preserve existing behavior so all
         existing callers — tests, skills, agents — continue to work without modification.
    """
    # Arrange
    op_result = {
        "title": "My Feature",
        "priority": "P1",
        "body": "## Groomed (2026-03-22)\n- [ ] entry one",
        "sections": {
            "Groomed (2026-03-22)": {
                "num_entries": 1,
                "num_struck": 0,
                "entries": [{"id": "e1", "struck": False, "content": "entry one"}],
            }
        },
        "messages": [],
        "warnings": [],
    }

    # Act
    with patch("backlog_core.operations.view_item", return_value=op_result) as mock_view:
        response = await _call("backlog_view", {"selector": "#42", "summary": False})

    # Assert
    call_kwargs = mock_view.call_args.kwargs
    assert call_kwargs["include_content"] is True
    assert "body" in response
    assert "sections" in response
    assert response["body"] == "## Groomed (2026-03-22)\n- [ ] entry one"


async def test_backlog_view_compact_mode_omits_body():
    """backlog_view with include_content=False response has no 'body' or 'sections' keys.

    Tests: Compact mode response shape — body and sections are absent.
    How: Mock operations.view_item to return a compact dict (no body, no sections).
         Call backlog_view with include_content=False.
         Assert 'body' key is absent and 'sections' key is absent in the response.
    Why: Callers detecting compact mode use 'body' in response as the sentinel.
         Absent keys (not None, not empty string) is the contract.
         Large backlog items can have 53K+ character bodies — compact mode is essential
         for token-efficient metadata queries.
    """
    # Arrange — operations.view_item returns compact dict (body already popped by operations layer)
    op_result = {
        "title": "My Feature",
        "priority": "P1",
        "sections_metadata": [
            {"name": "Groomed (2026-03-22)", "num_entries": 3, "num_struck": 1},
            {"name": "Concerns", "num_entries": 2, "num_struck": 0},
        ],
        "messages": [],
        "warnings": [],
    }

    # Act
    with patch("backlog_core.operations.view_item", return_value=op_result) as mock_view:
        response = await _call("backlog_view", {"selector": "#42", "include_content": False, "summary": False})

    # Assert
    call_kwargs = mock_view.call_args.kwargs
    assert call_kwargs["include_content"] is False
    assert "body" not in response, "Compact mode must not include 'body' key"
    assert "sections" not in response, "Compact mode must not include 'sections' key"


async def test_backlog_view_compact_mode_includes_sections_metadata():
    """backlog_view with include_content=False response has 'sections_metadata' list.

    Tests: Compact mode sections_metadata structure — name and entry counts per section.
    How: Mock operations.view_item to return sections_metadata list with two sections.
         Call backlog_view with include_content=False.
         Assert sections_metadata is present, is a list, and each entry has
         name, num_entries, and num_struck keys with correct values.
    Why: The sections_metadata contract is the API surface for compact mode consumers.
         Each dict must contain exactly the three keys (name, num_entries, num_struck)
         so callers can build summaries without parsing full entry content.
    """
    # Arrange
    compact_sections = [
        {"name": "Groomed (2026-03-22)", "num_entries": 5, "num_struck": 2},
        {"name": "Concerns", "num_entries": 3, "num_struck": 0},
    ]
    op_result = {
        "title": "My Feature",
        "priority": "P1",
        "sections_metadata": compact_sections,
        "messages": [],
        "warnings": [],
    }

    # Act
    with patch("backlog_core.operations.view_item", return_value=op_result):
        response = await _call("backlog_view", {"selector": "#42", "include_content": False, "summary": False})

    # Assert
    assert "sections_metadata" in response
    metadata = response["sections_metadata"]
    assert isinstance(metadata, list)
    assert len(metadata) == 2

    first = metadata[0]
    assert first["name"] == "Groomed (2026-03-22)"
    assert first["num_entries"] == 5
    assert first["num_struck"] == 2

    second = metadata[1]
    assert second["name"] == "Concerns"
    assert second["num_entries"] == 3
    assert second["num_struck"] == 0


# ---------------------------------------------------------------------------
# backlog_view — summary mode (summary=True / summary=False)
# ---------------------------------------------------------------------------


async def test_backlog_view_summary_true_returns_compact_manifest():
    """backlog_view with summary=True (default) returns 5-field routing manifest.

    Tests: summary=True response shape — issue_number, title, labels, status, plan_path.
    How: Mock operations.view_item to return a full-detail dict with body containing
         a plan: line, labels list, issue string, and state field.
         Call backlog_view without summary parameter (defaults to True).
         Assert all 5 routing fields plus _summary, _full_chars, _hint are present.
    Why: The summary manifest is the contract for token-efficient routing — agents
         receive just enough metadata to decide whether to fetch the full body.
    """
    # Arrange
    op_result = {
        "title": "SAM Ready Feature",
        "priority": "P1",
        "issue": "#36",
        "state": "open",
        "labels": ["priority:p1", "sam-ready"],
        "body": "## Description\nSome content\nplan: plan/P036-sam-ready.yaml\nMore content",
        "sections": {},
        "messages": [],
        "warnings": [],
        "errors": [],
    }

    # Act
    with patch("backlog_core.operations.view_item", return_value=op_result):
        response = await _call("backlog_view", {"selector": "#36"})

    # Assert — compact fields present
    assert response["issue_number"] == 36
    assert response["title"] == "SAM Ready Feature"
    assert response["labels"] == ["priority:p1", "sam-ready"]
    assert response["status"] == "open"
    assert response["plan_path"] == "plan/P036-sam-ready.yaml"
    assert response["_summary"] is True
    assert isinstance(response["_full_chars"], int)
    assert response["_full_chars"] > 0
    assert "summary=False" in response["_hint"]
    assert "#36" in response["_hint"]


async def test_backlog_view_summary_true_hint_contains_selector():
    """backlog_view summary=True _hint embeds the exact selector the caller passed.

    Tests: _hint fidelity — caller can copy-paste the suggested call.
    How: Call backlog_view with selector='My Feature Title' and summary=True.
         Assert _hint contains that exact selector string.
    Why: The hint is actionable only if the selector is correct for the caller's context.
    """
    # Arrange
    op_result = {
        "title": "My Feature Title",
        "issue": "#99",
        "state": "open",
        "labels": [],
        "body": "",
        "messages": [],
        "warnings": [],
        "errors": [],
    }

    # Act
    with patch("backlog_core.operations.view_item", return_value=op_result):
        response = await _call("backlog_view", {"selector": "My Feature Title"})

    # Assert
    assert "My Feature Title" in response["_hint"]


async def test_backlog_view_summary_true_plan_path_none_when_absent():
    """backlog_view summary=True sets plan_path=None when no plan: line in body.

    Tests: plan_path extraction when body has no plan: annotation.
    How: Mock operations.view_item with body containing no plan: line.
         Assert plan_path is None in the summary response.
    Why: Callers must distinguish "has a plan" from "no plan" without parsing body.
    """
    # Arrange
    op_result = {
        "title": "No Plan Yet",
        "issue": "#10",
        "state": "open",
        "labels": [],
        "body": "## Description\nThis item has no plan file yet.",
        "messages": [],
        "warnings": [],
        "errors": [],
    }

    # Act
    with patch("backlog_core.operations.view_item", return_value=op_result):
        response = await _call("backlog_view", {"selector": "#10"})

    # Assert
    assert response["plan_path"] is None


async def test_backlog_view_summary_true_closed_issue_status_is_closed():
    """backlog_view summary=True maps state='closed' to status='closed'.

    Tests: status field derivation for closed issues.
    How: Mock operations.view_item with state='closed'.
         Assert status == 'closed' in the summary response.
    Why: Callers use status to skip further processing on closed items.
    """
    # Arrange
    op_result = {
        "title": "Resolved Item",
        "issue": "#5",
        "state": "closed",
        "labels": ["resolved"],
        "body": "",
        "messages": [],
        "warnings": [],
        "errors": [],
    }

    # Act
    with patch("backlog_core.operations.view_item", return_value=op_result):
        response = await _call("backlog_view", {"selector": "#5"})

    # Assert
    assert response["status"] == "closed"


async def test_backlog_view_summary_false_returns_full_response():
    """backlog_view with summary=False returns the full operations result unchanged.

    Tests: summary=False pass-through — existing callers unaffected.
    How: Mock operations.view_item to return a dict with body and sections.
         Call backlog_view with summary=False.
         Assert body and sections are present and _summary key is absent.
    Why: summary=False must be a strict pass-through to preserve backward compat
         for callers that need the full body, comments, and timeline.
    """
    # Arrange
    op_result = {
        "title": "My Feature",
        "issue": "#42",
        "state": "open",
        "labels": ["priority:p1"],
        "body": "## Groomed (2026-03-22)\n- [ ] entry one",
        "sections": {
            "Groomed (2026-03-22)": {
                "num_entries": 1,
                "num_struck": 0,
                "entries": [{"id": "e1", "struck": False, "content": "entry one"}],
            }
        },
        "messages": [],
        "warnings": [],
        "errors": [],
    }

    # Act
    with patch("backlog_core.operations.view_item", return_value=op_result):
        response = await _call("backlog_view", {"selector": "#42", "summary": False})

    # Assert — full response keys present
    assert "body" in response
    assert "sections" in response
    assert response["body"] == "## Groomed (2026-03-22)\n- [ ] entry one"
    # _summary sentinel must be absent — this is a full response
    assert "_summary" not in response


async def test_backlog_view_summary_true_full_chars_reflects_full_response_size():
    """backlog_view summary=True _full_chars equals len(json.dumps(full_response)).

    Tests: _full_chars accuracy — caller can rely on it for token budget decisions.
    How: Mock operations.view_item with a known body. Compute expected _full_chars
         by serialising the merged dict the same way the handler does.
         Assert _full_chars matches.
    Why: An inaccurate _full_chars defeats the purpose of the hint — callers would
         not know whether fetching the full body is worth the token cost.
    """
    import json as _json_test

    # Arrange
    op_result = {
        "title": "Budget Item",
        "issue": "#7",
        "state": "open",
        "labels": [],
        "body": "x" * 500,
        "sections": {},
        "messages": [],
        "warnings": [],
        "errors": [],
    }
    expected_full_chars = len(_json_test.dumps({**op_result}))

    # Act
    with patch("backlog_core.operations.view_item", return_value=op_result):
        response = await _call("backlog_view", {"selector": "#7"})

    # Assert
    assert response["_full_chars"] == expected_full_chars


def test_backlog_view_summary_param_in_signature():
    """backlog_view signature includes 'summary' parameter.

    Tests: MCP tool schema completeness — 'summary' is discoverable by callers.
    How: Inspect backlog_view function signature for summary parameter.
    Why: MCP consumers discover available parameters through tool schema introspection.
    """
    import inspect

    from backlog_core.server import backlog_view

    sig = inspect.signature(backlog_view)
    assert "summary" in sig.parameters


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


async def test_backlog_groom_accepts_mark_groomed_parameter():
    """backlog_groom forwards mark_groomed=True to operations.groom_item."""
    op_result = {"title": "Feature", "synced": True}
    with patch("backlog_core.operations.groom_item", return_value=op_result) as mock_groom:
        await _call(
            "backlog_groom", {"selector": "Feature", "section": "Background", "content": "Done", "mark_groomed": True}
        )

    mock_groom.assert_called_once()
    call_kwargs = mock_groom.call_args.kwargs
    assert call_kwargs["mark_groomed"] is True


async def test_backlog_groom_mark_groomed_defaults_false():
    """backlog_groom passes mark_groomed=False to groom_item when not specified."""
    op_result = {"title": "Feature", "synced": True}
    with patch("backlog_core.operations.groom_item", return_value=op_result) as mock_groom:
        await _call("backlog_groom", {"selector": "Feature", "section": "Background", "content": "Done"})

    mock_groom.assert_called_once()
    call_kwargs = mock_groom.call_args.kwargs
    assert call_kwargs["mark_groomed"] is False


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
        ("backlog_view", {"selector": "#1", "summary": False}, "backlog_core.operations.view_item", {"title": "T"}),
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


# ---------------------------------------------------------------------------
# _bootstrap_beads: all 4 execution paths + sentinel + lifespan integration
# ---------------------------------------------------------------------------


def test_bootstrap_beads_happy_path_beads_exists_calls_setup_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """_bootstrap_beads calls only bd setup when bd is on PATH and .beads/ exists.

    Tests: _bootstrap_beads happy path execution path.
    How:
        1. Reset sentinel to False via monkeypatch.
        2. Create a .beads/ directory inside tmp_path so existence check returns True.
        3. Patch shutil.which to return a full path for "bd".
        4. Patch subprocess.run to capture all calls.
        5. Call _bootstrap_beads directly with tmp_path as project_dir.
    Why: Verifies that when bd is installed and the database is already initialised,
    the function skips bd init and only runs bd setup, avoiding repeated init
    in already-configured projects.
    """
    monkeypatch.setattr(_server_mod, "_beads_bootstrapped", False)
    beads_dir = tmp_path / ".beads"
    beads_dir.mkdir()

    with (
        patch("backlog_core.server.shutil.which", return_value="/usr/bin/bd") as mock_which,
        patch("backlog_core.server.subprocess.run") as mock_run,
    ):
        _server_mod._bootstrap_beads(tmp_path)

    mock_which.assert_called_with("bd")
    assert mock_run.call_count == 1
    called_cmd = mock_run.call_args_list[0][0][0]
    assert called_cmd[1:] == ["setup", "claude", "--project", "--stealth"]
    assert _server_mod._beads_bootstrapped is True


def test_bootstrap_beads_happy_path_beads_absent_calls_init_and_setup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """_bootstrap_beads calls bd init then bd setup when bd is on PATH but .beads/ is absent.

    Tests: _bootstrap_beads happy path with uninitialised project.
    How:
        1. Reset sentinel to False via monkeypatch.
        2. Do NOT create .beads/ directory — existence check returns False.
        3. Patch shutil.which to return a full path for "bd".
        4. Patch subprocess.run to capture calls.
        5. Call _bootstrap_beads directly.
    Why: Verifies that when bd is installed but the database is not yet initialised,
    the function runs bd init followed by bd setup to fully configure the project.
    """
    monkeypatch.setattr(_server_mod, "_beads_bootstrapped", False)
    # No .beads/ directory created — tmp_path exists but .beads/ is absent.

    with (
        patch("backlog_core.server.shutil.which", return_value="/usr/bin/bd"),
        patch("backlog_core.server.subprocess.run") as mock_run,
    ):
        _server_mod._bootstrap_beads(tmp_path)

    assert mock_run.call_count == 2
    init_cmd = mock_run.call_args_list[0][0][0]
    setup_cmd = mock_run.call_args_list[1][0][0]
    assert init_cmd[1:] == ["init", "--stealth", "--quiet"]
    assert setup_cmd[1:] == ["setup", "claude", "--project", "--stealth"]
    # Both bd commands use cwd=project_dir.
    assert mock_run.call_args_list[0].kwargs.get("cwd") == tmp_path
    assert mock_run.call_args_list[1].kwargs.get("cwd") == tmp_path
    assert _server_mod._beads_bootstrapped is True


def test_bootstrap_beads_install_path_bd_absent_npm_present(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """_bootstrap_beads runs npm install then bd init and bd setup when bd is absent but npm is present.

    Tests: _bootstrap_beads install execution path (bd absent, npm present, install succeeds).
    How:
        1. Reset sentinel to False via monkeypatch.
        2. Patch shutil.which with side_effect: first call ("bd") returns None,
           second call ("npm") returns "/usr/bin/npm", third call ("bd") post-install
           returns "/usr/local/bin/bd".
        3. Patch subprocess.run to capture 3 expected calls.
        4. Call _bootstrap_beads directly.
    Why: Verifies the install path runs npm install, then re-checks for bd, then
    runs bd init and bd setup to complete setup in a fresh environment.
    """
    monkeypatch.setattr(_server_mod, "_beads_bootstrapped", False)

    which_side_effects = [None, "/usr/bin/npm", "/usr/local/bin/bd"]

    with (
        patch("backlog_core.server.shutil.which", side_effect=which_side_effects),
        patch("backlog_core.server.subprocess.run") as mock_run,
    ):
        _server_mod._bootstrap_beads(tmp_path)

    assert mock_run.call_count == 3
    npm_cmd = mock_run.call_args_list[0][0][0]
    init_cmd = mock_run.call_args_list[1][0][0]
    setup_cmd = mock_run.call_args_list[2][0][0]
    assert npm_cmd == ["/usr/bin/npm", "install", "-g", "@beads/bd"]
    assert init_cmd[1:] == ["init", "--stealth", "--quiet"]
    assert setup_cmd[1:] == ["setup", "claude", "--project", "--stealth"]
    # npm install must NOT pass cwd (global install).
    assert mock_run.call_args_list[0].kwargs.get("cwd") is None
    assert _server_mod._beads_bootstrapped is True


def test_bootstrap_beads_graceful_degradation_npm_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """_bootstrap_beads logs a warning and skips all subprocess calls when npm is not found.

    Tests: _bootstrap_beads graceful degradation path A (npm absent).
    How:
        1. Reset sentinel to False via monkeypatch.
        2. Patch shutil.which to always return None (both bd and npm absent).
        3. Capture log output via caplog fixture.
        4. Call _bootstrap_beads directly.
        5. Assert no subprocess.run was called and warning was logged.
    Why: Verifies that the function degrades gracefully without npm rather than
    raising an exception, so the MCP server starts successfully even without the
    beads toolchain available.
    """
    monkeypatch.setattr(_server_mod, "_beads_bootstrapped", False)

    with (
        patch("backlog_core.server.shutil.which", return_value=None),
        patch("backlog_core.server.subprocess.run") as mock_run,
        caplog.at_level(logging.WARNING, logger="backlog_core.server"),
    ):
        _server_mod._bootstrap_beads(tmp_path)

    assert mock_run.call_count == 0
    assert any("npm not available" in record.message for record in caplog.records)
    assert _server_mod._beads_bootstrapped is True


def test_bootstrap_beads_graceful_degradation_npm_install_fails_silently(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """_bootstrap_beads logs a warning when npm install runs but bd is still not found afterward.

    Tests: _bootstrap_beads graceful degradation path B (npm install fails silently).
    How:
        1. Reset sentinel to False via monkeypatch.
        2. Patch shutil.which with side_effect: first call ("bd") returns None,
           second call ("npm") returns "/usr/bin/npm", third call ("bd") post-install
           still returns None (npm install did not actually install bd).
        3. Patch subprocess.run to intercept the npm call.
        4. Assert only 1 subprocess call (npm install) and warning was logged.
    Why: Verifies the install path fails gracefully when npm is present but the
    install silently fails (e.g., network error), preventing a crash in the server.
    """
    monkeypatch.setattr(_server_mod, "_beads_bootstrapped", False)

    # First "bd" call → None, "npm" call → found, second "bd" call → still None.
    which_side_effects = [None, "/usr/bin/npm", None]

    with (
        patch("backlog_core.server.shutil.which", side_effect=which_side_effects),
        patch("backlog_core.server.subprocess.run") as mock_run,
        caplog.at_level(logging.WARNING, logger="backlog_core.server"),
    ):
        _server_mod._bootstrap_beads(tmp_path)

    assert mock_run.call_count == 1
    npm_cmd = mock_run.call_args_list[0][0][0]
    assert "install" in npm_cmd
    assert any("npm install failed silently" in record.message for record in caplog.records)
    assert _server_mod._beads_bootstrapped is True


def test_bootstrap_beads_sentinel_prevents_re_execution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """_bootstrap_beads returns immediately without any work when sentinel is True.

    Tests: _bootstrap_beads sentinel guard logic.
    How:
        1. Set _beads_bootstrapped = True via monkeypatch (simulates already-ran state).
        2. Patch shutil.which and subprocess.run to detect any calls.
        3. Call _bootstrap_beads directly.
        4. Assert neither shutil.which nor subprocess.run were called at all.
    Why: Verifies the module-level sentinel prevents repeated bootstrap executions
    across multiple Client(mcp) connections in test suites, ensuring test isolation
    and preventing unwanted subprocess side effects.
    """
    monkeypatch.setattr(_server_mod, "_beads_bootstrapped", True)

    with (
        patch("backlog_core.server.shutil.which") as mock_which,
        patch("backlog_core.server.subprocess.run") as mock_run,
    ):
        _server_mod._bootstrap_beads(tmp_path)

    mock_which.assert_not_called()
    mock_run.assert_not_called()


def test_bootstrap_beads_lifespan_is_registered_in_fastmcp_constructor() -> None:
    """_beads_lifespan is wired into the FastMCP constructor via lifespan= parameter.

    Tests: Lifespan integration wiring between FastMCP constructor and _beads_lifespan.
    How:
        1. Import the mcp singleton and _beads_lifespan from backlog_core.server.
        2. Inspect the mcp object's _lifespan attribute (set by the lifespan= parameter).
        3. Assert the lifespan attribute references _beads_lifespan (not None, not a
           different lifespan object).
    Why: Verifies the lifespan=_beads_lifespan parameter was passed to the FastMCP
    constructor, ensuring the bootstrap hook will be invoked at server startup.
    Uses static attribute inspection rather than triggering the lifespan to execute,
    which avoids event loop isolation issues in pytest-asyncio multi-loop scenarios
    caused by the asyncio.get_event_loop() call inside run_in_executor.
    """
    # FastMCP stores the lifespan on the server instance via the lifespan= constructor param.
    server_lifespan = mcp._lifespan
    assert server_lifespan is not None, "lifespan= was not passed to the FastMCP constructor"
    assert server_lifespan is _beads_lifespan, (
        f"mcp._lifespan is {server_lifespan!r}, expected _beads_lifespan {_beads_lifespan!r}"
    )
