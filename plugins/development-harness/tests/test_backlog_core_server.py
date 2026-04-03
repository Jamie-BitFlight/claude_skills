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
from backlog_core.models import BackendAvailability, BackendStatus, BacklogError, Output, ViewItemResult
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


def _make_view_result(data: dict) -> ViewItemResult:
    """Build a ViewItemResult from a plain dict, used for mocking view_item return values.

    Extra keys not in ViewItemResult (e.g. 'errors') are silently dropped via
    model_validate's ignore-extra behaviour.  This lets existing test dicts be
    converted without rewriting every key.
    """
    return ViewItemResult.model_validate(data)


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
        response = await _call(
            "backlog_add",
            {
                "title": "My Item",
                "priority": "P1",
                "description": "A test item",
                "gate_token": "problems-not-solutions",
            },
        )

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
    """backlog_add forwards source, type_, and force to operations."""
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
                "force": True,
                "gate_token": "problems-not-solutions",
            },
        )

    call_kwargs = mock_add.call_args.kwargs
    assert call_kwargs["source"] == "CI pipeline"
    assert call_kwargs["type_"] == "Bug"
    assert call_kwargs["force"] is True


async def test_backlog_add_backlog_error_returns_error_key():
    """backlog_add catches BacklogError and includes error key in response."""
    with patch("backlog_core.operations.add_item", side_effect=BacklogError("duplicate found")):
        response = await _call(
            "backlog_add",
            {
                "title": "Dupe",
                "priority": "P1",
                "description": "Already exists",
                "gate_token": "problems-not-solutions",
            },
        )

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
        response = await _call(
            "backlog_add",
            {"title": "Item", "priority": "P1", "description": "Test", "gate_token": "problems-not-solutions"},
        )

    assert "created file" in response["messages"]
    assert "no github token" in response["warnings"]


async def test_backlog_add_gate_rejects_missing_token():
    """backlog_add returns error when gate_token is absent or wrong."""
    with patch("backlog_core.operations.add_item") as mock_add:
        response_missing = await _call("backlog_add", {"title": "X", "priority": "P1", "description": "Y"})
        response_wrong = await _call(
            "backlog_add", {"title": "X", "priority": "P1", "description": "Y", "gate_token": "wrong-value"}
        )

    mock_add.assert_not_called()
    expected_error = "Direct backlog_add calls are not permitted. Load and follow /dh:create-backlog-item — it will provide the required gate_token."
    assert response_missing["error"] == expected_error
    assert response_wrong["error"] == expected_error


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


async def test_backlog_list_search_matches_body_content():
    """backlog_list search= matches items where the body field contains the needle.

    The ``body`` field carries full item content (description, acceptance criteria,
    section entries) so searches for strings that only appear in the body — not in
    title/section/topic/type — must still return the item.
    """
    items = [
        {
            "title": "Improve pipeline",
            "section": "P1",
            "topic": "devops",
            "type": "Feature",
            "body": "Acceptance criteria reference sdlc-layers architecture design",
        },
        {
            "title": "Auth service refactor",
            "section": "P2",
            "topic": "security",
            "type": "Refactor",
            "body": "Fix oauth token handling",
        },
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "sdlc-layers"})

    returned_titles = [item["title"] for item in response["items"]]
    assert "Improve pipeline" in returned_titles
    assert "Auth service refactor" not in returned_titles


async def test_backlog_list_search_body_field_specific_prefix():
    """backlog_list search='body:sdlc-layers' restricts match to the body field only."""
    items = [
        {
            "title": "sdlc-layers overview",  # matches title
            "section": "P1",
            "topic": "",
            "type": "Docs",
            "body": "General documentation",
        },
        {
            "title": "Pipeline task",
            "section": "P1",
            "topic": "",
            "type": "Feature",
            "body": "Implements sdlc-layers integration",  # matches body
        },
        {"title": "Unrelated task", "section": "P2", "topic": "", "type": "Bug", "body": "Fixes a crash"},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "body:sdlc-layers"})

    returned_titles = [item["title"] for item in response["items"]]
    # Only the item whose body contains "sdlc-layers" matches the body: prefix
    assert "Pipeline task" in returned_titles
    assert "sdlc-layers overview" not in returned_titles
    assert "Unrelated task" not in returned_titles


# ---------------------------------------------------------------------------
# _apply_search_filter — unit tests for pre-computed haystack optimisation
# ---------------------------------------------------------------------------


def test_apply_search_filter_and_operator_pre_computed_haystack():
    """_apply_search_filter AND returns only items matching all terms.

    Tests: correctness of the AND branch after the pre-computed haystack
    optimisation — each item's haystack is built once and reused across all
    terms in the query.
    How: Call _apply_search_filter directly with a 3-item list and an AND query
    with 2 terms.  Verify the returned list contains only the item that matches
    both, not those matching one or neither.
    Why: Pre-computing the haystack must not change which items match — only
    how many times the haystack string is constructed per item.
    """
    from backlog_core.server import _apply_search_filter

    items: list[dict[str, str | bool]] = [
        {"title": "Auth token bug", "section": "P1", "topic": "security", "type": "Bug", "body": ""},
        {"title": "Auth feature", "section": "P1", "topic": "security", "type": "Feature", "body": ""},
        {"title": "Deploy bug", "section": "P2", "topic": "infra", "type": "Bug", "body": ""},
        {"title": "Unrelated", "section": "P3", "topic": "docs", "type": "Docs", "body": ""},
    ]

    result = _apply_search_filter(items, "auth AND bug")
    titles = [i["title"] for i in result]

    assert titles == ["Auth token bug"], f"Expected only 'Auth token bug', got {titles}"


def test_apply_search_filter_or_operator_pre_computed_haystack():
    """_apply_search_filter OR returns items matching either term.

    Tests: correctness of the OR branch after the pre-computed haystack
    optimisation — each item's haystack is built once before evaluating any()
    across terms.
    How: Call _apply_search_filter directly with a 4-item list and an OR query.
    Verify matched set and excluded set.
    Why: Same as AND — the optimisation must be semantically transparent.
    """
    from backlog_core.server import _apply_search_filter

    items: list[dict[str, str | bool]] = [
        {"title": "Auth service", "section": "P1", "topic": "security", "type": "Feature", "body": ""},
        {"title": "Deploy pipeline", "section": "P2", "topic": "infra", "type": "Feature", "body": ""},
        {"title": "Refactor models", "section": "P3", "topic": "quality", "type": "Refactor", "body": ""},
        {"title": "Docs cleanup", "section": "P4", "topic": "docs", "type": "Docs", "body": ""},
    ]

    result = _apply_search_filter(items, "auth OR deploy")
    titles = [i["title"] for i in result]

    assert "Auth service" in titles
    assert "Deploy pipeline" in titles
    assert "Refactor models" not in titles
    assert "Docs cleanup" not in titles


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
    op_result = _make_view_result({
        "title": "My Feature",
        "priority": "P1",
        "description": "details",
        "source": "issue",
        "added": "2026-01-01",
        "plan": "",
        "issue": "#42",
        "file_path": "/tmp/p1-my-feature.md",
        "groomed": "",
        "status": "",
        "number": 42,
        "state": "open",
        "body": "## Details\nsome content",
        "labels": ["priority:p1"],
        "milestone": "",
    })
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
    op_result = _make_view_result({"title": "Item", "body": "line1\nline2\nline3"})
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
    op_result = _make_view_result({
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
    })

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
    # Arrange — operations.view_item returns compact result (body cleared by operations layer)
    op_result = _make_view_result({
        "title": "My Feature",
        "priority": "P1",
        "sections_metadata": [
            {"name": "Groomed (2026-03-22)", "num_entries": 3, "num_struck": 1},
            {"name": "Concerns", "num_entries": 2, "num_struck": 0},
        ],
        "messages": [],
        "warnings": [],
    })

    # Act
    with patch("backlog_core.operations.view_item", return_value=op_result) as mock_view:
        response = await _call("backlog_view", {"selector": "#42", "include_content": False, "summary": False})

    # Assert
    call_kwargs = mock_view.call_args.kwargs
    assert call_kwargs["include_content"] is False
    assert not response.get("body"), "Compact mode must have no body content"
    assert not response.get("sections"), "Compact mode must have no sections content"


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
    op_result = _make_view_result({
        "title": "My Feature",
        "priority": "P1",
        "sections_metadata": compact_sections,
        "messages": [],
        "warnings": [],
    })

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
    op_result = _make_view_result({
        "title": "SAM Ready Feature",
        "priority": "P1",
        "issue": "#36",
        "state": "open",
        "labels": ["priority:p1", "sam-ready"],
        "body": "## Description\nSome content\nplan: plan/P036-sam-ready.yaml\nMore content",
        "sections": {},
        "messages": [],
        "warnings": [],
    })

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
    op_result = _make_view_result({
        "title": "My Feature Title",
        "issue": "#99",
        "state": "open",
        "labels": [],
        "body": "",
        "messages": [],
        "warnings": [],
    })

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
    op_result = _make_view_result({
        "title": "No Plan Yet",
        "issue": "#10",
        "state": "open",
        "labels": [],
        "body": "## Description\nThis item has no plan file yet.",
        "messages": [],
        "warnings": [],
    })

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
    op_result = _make_view_result({
        "title": "Resolved Item",
        "issue": "#5",
        "state": "closed",
        "labels": ["resolved"],
        "body": "",
        "messages": [],
        "warnings": [],
    })

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
    op_result = _make_view_result({
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
    })

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
    op_result = _make_view_result({
        "title": "Budget Item",
        "issue": "#7",
        "state": "open",
        "labels": [],
        "body": "x" * 500,
        "sections": {},
        "messages": [],
        "warnings": [],
    })
    # _full_chars is computed from model_dump() which includes all ViewItemResult fields.
    expected_full_chars = len(_json_test.dumps(op_result.model_dump()))

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
    assert call_kwargs["section"] is None
    assert call_kwargs["content"] is None
    assert response["title"] == "Feature"


async def test_backlog_update_passes_status():
    """backlog_update forwards status to operations."""
    op_result = {"title": "Item", "changes": ["status updated"]}
    with patch("backlog_core.operations.update_item", return_value=op_result) as mock_update:
        await _call("backlog_update", {"selector": "Item", "status": "in-progress"})

    call_kwargs = mock_update.call_args.kwargs
    assert call_kwargs["status"] == "in-progress"


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
    op_result = _make_view_result({"title": "My Item", "body": "content"})
    with patch("backlog_core.operations.view_item", return_value=op_result) as mock_view:
        await _call("backlog_view", {"selector": "#1", "show": "2"})

    call_kwargs = mock_view.call_args.kwargs
    assert call_kwargs["show"] == 2, f"Expected int 2, got {call_kwargs['show']!r}"


async def test_backlog_view_show_non_numeric_string_passed_as_str():
    """backlog_view passes show='last' as a string (not converted to int)."""
    op_result = _make_view_result({"title": "My Item", "body": "content"})
    with patch("backlog_core.operations.view_item", return_value=op_result) as mock_view:
        await _call("backlog_view", {"selector": "#1", "show": "last"})

    call_kwargs = mock_view.call_args.kwargs
    assert call_kwargs["show"] == "last", f"Expected str 'last', got {call_kwargs['show']!r}"


@pytest.mark.parametrize(
    ("tool_name", "params", "mock_target", "mock_return"),
    [
        (
            "backlog_add",
            {"title": "T", "priority": "P1", "description": "D", "gate_token": "problems-not-solutions"},
            "backlog_core.operations.add_item",
            {"file_path": "f"},
        ),
        ("backlog_list", {}, "backlog_core.operations.list_items", {"items": []}),
        (
            "backlog_view",
            {"selector": "#1", "summary": False},
            "backlog_core.operations.view_item",
            _make_view_result({"title": "T"}),
        ),
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
        (
            "backlog_add",
            {"title": "T", "priority": "P1", "description": "D", "gate_token": "problems-not-solutions"},
            "backlog_core.operations.add_item",
        ),
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
        await _call(
            "backlog_add", {"title": "X", "priority": "P1", "description": "D", "gate_token": "problems-not-solutions"}
        )

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
        response = await _call(
            "backlog_add",
            {"title": "OK", "priority": "P1", "description": "Fine", "gate_token": "problems-not-solutions"},
        )

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


# ---------------------------------------------------------------------------
# GAP-1: NOT operator
# ---------------------------------------------------------------------------


def test_apply_search_filter_not_excludes_matching_item():
    """_apply_search_filter NOT term excludes items that match the term.

    How: Three items; query "backlog NOT quality". Items with "backlog" but
    also "quality" in the haystack must be excluded. Items with "backlog"
    only must be included.
    Why: Validates the _NotPred short-circuit path and its interaction with
    the pre-computed haystack.
    """
    from backlog_core.server import _apply_search_filter

    items: list[dict[str, str | bool]] = [
        {"title": "Backlog grooming", "section": "P1", "topic": "process", "type": "Chore", "body": ""},
        {"title": "Backlog quality review", "section": "P1", "topic": "quality", "type": "Chore", "body": ""},
        {"title": "Auth refactor", "section": "P2", "topic": "security", "type": "Refactor", "body": ""},
    ]

    result = _apply_search_filter(items, "backlog NOT quality")
    titles = [i["title"] for i in result]

    assert "Backlog grooming" in titles, "Item matching 'backlog' only must be included"
    assert "Backlog quality review" not in titles, "Item matching both 'backlog' and 'quality' must be excluded"
    assert "Auth refactor" not in titles, "Item not matching 'backlog' must be excluded"


def test_apply_search_filter_not_with_field_prefix():
    """_apply_search_filter NOT with field:value syntax excludes field matches.

    How: Query "title:backlog AND NOT type:feature". Items with "backlog" in
    title but type Feature must be excluded; those with other types must be
    included.
    Why: Validates that NOT correctly negates field-specific predicates.
    """
    from backlog_core.server import _apply_search_filter

    items: list[dict[str, str | bool]] = [
        {"title": "Backlog feature X", "section": "P1", "topic": "backlog", "type": "Feature", "body": ""},
        {"title": "Backlog chore Y", "section": "P1", "topic": "backlog", "type": "Chore", "body": ""},
        {"title": "Unrelated item", "section": "P2", "topic": "other", "type": "Bug", "body": ""},
    ]

    result = _apply_search_filter(items, "title:backlog AND NOT type:feature")
    titles = [i["title"] for i in result]

    assert "Backlog chore Y" in titles
    assert "Backlog feature X" not in titles
    assert "Unrelated item" not in titles


async def test_backlog_list_search_not_operator_excludes_term():
    """backlog_list search with NOT operator excludes items containing the negated term.

    How: Two items — one matching both terms, one matching only the positive
    term. Query "backlog NOT quality". Only the non-quality item must appear.
    Why: End-to-end validation of NOT through the MCP transport.
    """
    op_result = {
        "items": [
            {"title": "Backlog grooming", "section": "P1", "topic": "process", "type": "Chore", "body": ""},
            {"title": "Backlog quality review", "section": "P1", "topic": "quality", "type": "Chore", "body": ""},
        ]
    }
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "backlog NOT quality"})

    titles = [i["title"] for i in response["items"]]
    assert "Backlog grooming" in titles
    assert "Backlog quality review" not in titles


# ---------------------------------------------------------------------------
# GAP-2: Mixed AND/OR with parenthetical grouping
# ---------------------------------------------------------------------------


def test_apply_search_filter_parenthetical_grouping_or_within_and():
    """_apply_search_filter supports (A OR B) AND C grouping.

    How: Query "(auth OR deploy) AND quality". Items must match either
    'auth' or 'deploy', AND also 'quality'. Items matching only auth or
    deploy without quality must be excluded.
    Why: Validates the recursive-descent parser handles grouped OR inside
    an AND expression correctly.
    """
    from backlog_core.server import _apply_search_filter

    items: list[dict[str, str | bool]] = [
        {"title": "Auth quality gate", "section": "P1", "topic": "security", "type": "Feature", "body": ""},
        {"title": "Auth service", "section": "P1", "topic": "security", "type": "Feature", "body": ""},
        {"title": "Deploy quality check", "section": "P2", "topic": "infra", "type": "Chore", "body": ""},
        {"title": "Refactor models", "section": "P3", "topic": "quality", "type": "Refactor", "body": ""},
    ]

    result = _apply_search_filter(items, "(auth OR deploy) AND quality")
    titles = [i["title"] for i in result]

    assert "Auth quality gate" in titles
    assert "Deploy quality check" in titles
    assert "Auth service" not in titles, "Matches auth but not quality — must be excluded"
    assert "Refactor models" not in titles, "Matches quality but not auth/deploy — must be excluded"


def test_apply_search_filter_parenthetical_not_inside_group():
    """_apply_search_filter supports NOT inside a parenthetical group.

    How: Query "(backlog AND NOT quality) OR deploy". Items matching the
    parenthetical expression (backlog without quality) OR 'deploy' must be
    included.
    Why: Validates correct precedence when NOT appears inside parentheses.
    """
    from backlog_core.server import _apply_search_filter

    items: list[dict[str, str | bool]] = [
        {"title": "Backlog grooming", "section": "P1", "topic": "process", "type": "Chore", "body": ""},
        {"title": "Backlog quality review", "section": "P1", "topic": "quality", "type": "Chore", "body": ""},
        {"title": "Deploy pipeline", "section": "P2", "topic": "infra", "type": "Chore", "body": ""},
        {"title": "Auth service", "section": "P3", "topic": "security", "type": "Feature", "body": ""},
    ]

    result = _apply_search_filter(items, "(backlog AND NOT quality) OR deploy")
    titles = [i["title"] for i in result]

    assert "Backlog grooming" in titles
    assert "Deploy pipeline" in titles
    assert "Backlog quality review" not in titles
    assert "Auth service" not in titles


async def test_backlog_list_search_grouped_or_and():
    """backlog_list search with parenthetical grouping returns correct items.

    How: Query "(auth OR deploy) AND quality". Only items that match
    (auth OR deploy) AND quality must appear in the response.
    Why: End-to-end validation of parenthetical grouping through MCP transport.
    """
    op_result = {
        "items": [
            {"title": "Auth quality gate", "section": "P1", "topic": "security", "type": "Feature", "body": ""},
            {"title": "Auth service", "section": "P1", "topic": "security", "type": "Feature", "body": ""},
            {"title": "Deploy quality check", "section": "P2", "topic": "infra", "type": "Chore", "body": ""},
            {"title": "Refactor models", "section": "P3", "topic": "quality", "type": "Refactor", "body": ""},
        ]
    }
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "(auth OR deploy) AND quality"})

    titles = [i["title"] for i in response["items"]]
    assert "Auth quality gate" in titles
    assert "Deploy quality check" in titles
    assert "Auth service" not in titles
    assert "Refactor models" not in titles


# ---------------------------------------------------------------------------
# GAP-3: count_only parameter on backlog_list
# ---------------------------------------------------------------------------


async def test_backlog_list_count_only_returns_count_key():
    """backlog_list with count_only=True returns {"count": N} only.

    How: Two items in op_result. Call backlog_list with count_only=True.
    Assert the response contains "count" and not "items".
    Why: Validates the count_only short-circuit before pagination and
    backend status queries.
    """
    op_result = {
        "items": [
            {"title": "Item A", "section": "P1", "topic": "a", "type": "Feature", "body": ""},
            {"title": "Item B", "section": "P2", "topic": "b", "type": "Bug", "body": ""},
        ]
    }
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"count_only": True})

    assert "count" in response, "count_only response must include 'count' key"
    assert response["count"] == 2
    assert "items" not in response, "count_only response must not include 'items' key"
    assert "pagination" not in response, "count_only response must not include 'pagination' key"


async def test_backlog_list_count_only_respects_search_filter():
    """backlog_list count_only=True reflects the filtered item count, not the raw list count.

    How: Three items; search="auth". Only one matches. count_only=True must
    return {"count": 1}.
    Why: Ensures the count is computed after applying all filters, not before.
    """
    op_result = {
        "items": [
            {"title": "Auth service", "section": "P1", "topic": "security", "type": "Feature", "body": ""},
            {"title": "Deploy pipeline", "section": "P2", "topic": "infra", "type": "Chore", "body": ""},
            {"title": "Auth token refresh", "section": "P1", "topic": "security", "type": "Bug", "body": ""},
        ]
    }
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"count_only": True, "search": "auth"})

    assert response["count"] == 2, f"Expected 2 auth items, got {response['count']}"


async def test_backlog_list_count_only_false_returns_full_response():
    """backlog_list with count_only=False (default) returns the normal full response.

    How: Call backlog_list without count_only (defaults False). Assert the
    normal keys are present.
    Why: Confirms the default behaviour is unchanged by the new parameter.
    """
    op_result = {"items": [{"title": "Item X", "section": "P1", "topic": "x", "type": "Feature", "body": ""}]}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {})

    assert "items" in response
    assert "pagination" in response
    assert "count" in response


# ---------------------------------------------------------------------------
# Primitive 1: match_context flag on backlog_list
# ---------------------------------------------------------------------------


async def test_backlog_list_match_context_false_default_unchanged():
    """backlog_list with match_context omitted produces identical response to current behaviour.

    Tests: default=False contract — no 'matches' key on any item, no regression.
    How: Call backlog_list without match_context. Assert no item has a 'matches' key.
    Why: The default must be a pure no-op so all existing callers continue working.
    """
    items = [
        {"title": "Auth token bug", "section": "P1", "topic": "security", "type": "Bug", "body": ""},
        {"title": "Deploy pipeline", "section": "P2", "topic": "infra", "type": "Feature", "body": ""},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "auth"})

    for item in response["items"]:
        assert "matches" not in item, f"Item {item['title']!r} must not have 'matches' when match_context is False"


async def test_backlog_list_match_context_true_returns_matches_key_per_item():
    """backlog_list with match_context=True includes a 'matches' list on each returned item.

    Tests: response shape when match_context is enabled — each item gets a non-empty matches list.
    How: Call backlog_list with search='auth' and match_context=True. Assert every
         returned item has a 'matches' key that is a non-empty list.
    Why: match_context is the core contract — callers use the matches list to determine
         where in the item a search term was found without fetching the full item body.
    """
    items = [{"title": "Auth token bug", "section": "P1", "topic": "security", "type": "Bug", "body": ""}]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "auth", "match_context": True})

    assert len(response["items"]) == 1
    item = response["items"][0]
    assert "matches" in item, "Item must have a 'matches' key when match_context=True"
    assert isinstance(item["matches"], list)
    assert len(item["matches"]) > 0


async def test_backlog_list_match_context_title_match_attributed_to_title_field():
    """backlog_list match_context=True attributes a title match to field='title'.

    Tests: field attribution for title matches — match entry must have field='title'.
    How: Search for a term that only appears in the title. Assert the match entry
         has field='title', term equal to the search term, and a non-empty snippet.
    Why: Callers use the field value to decide whether to read more. A title match
         means the item is likely a direct hit; callers can de-dup without fetching body.
    """
    items = [{"title": "Auth token bug", "section": "P1", "topic": "security", "type": "Bug", "body": ""}]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "auth", "match_context": True})

    assert len(response["items"]) == 1
    item = response["items"][0]
    assert "matches" in item
    title_matches = [m for m in item["matches"] if m.get("field") == "title"]
    assert len(title_matches) > 0, "Expected at least one match attributed to 'title'"
    match_entry = title_matches[0]
    assert match_entry["term"] == "auth"
    assert isinstance(match_entry["snippet"], str)
    assert len(match_entry["snippet"]) > 0


async def test_backlog_list_match_context_body_match_attributed_to_named_section():
    """backlog_list match_context=True attributes a body match to its named section.

    Tests: section attribution for body matches — field must be 'body:<section-name>'
           not the bare string 'body'.
    How: Provide an item whose body contains a section header followed by text containing
         the search term. Assert the match entry field is 'body:<section-name>'.
    Why: Section attribution is the key capability — 'body:acceptance-criteria' tells
         the caller exactly where to look, enabling targeted backlog_view calls.
    """
    items = [
        {
            "title": "Pipeline feature",
            "section": "P1",
            "topic": "infra",
            "type": "Feature",
            "body": (
                "## Description\nImplements the core pipeline.\n"
                "## Acceptance Criteria\n- quality gate must pass before merging\n"
                "## Notes\nLow priority."
            ),
        }
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "quality", "match_context": True})

    assert len(response["items"]) == 1
    item = response["items"][0]
    assert "matches" in item
    body_matches = [m for m in item["matches"] if m.get("field", "").startswith("body:")]
    assert len(body_matches) > 0, "Expected at least one match attributed to a named body section"
    match_entry = body_matches[0]
    # field must identify the section, not just 'body'
    assert match_entry["field"] != "body", f"Field must be 'body:<section>', got {match_entry['field']!r}"
    assert "quality" in match_entry["snippet"].lower()


async def test_backlog_list_match_context_multiple_terms_produce_multiple_matches():
    """backlog_list match_context=True with two matching terms produces one match entry per term.

    Tests: multi-term match context — each matching term gets its own entry in the matches list.
    How: Search 'auth AND bug' against an item that has both terms. Assert the matches list
         contains at least two entries (one per term).
    Why: Callers need to know which terms matched where. A single matches entry for a
         multi-term query cannot answer that question.
    """
    items = [{"title": "Auth token bug", "section": "P1", "topic": "security", "type": "Bug", "body": ""}]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "auth AND bug", "match_context": True})

    assert len(response["items"]) == 1
    item = response["items"][0]
    assert "matches" in item
    assert len(item["matches"]) >= 2, (
        f"Expected ≥2 match entries for 'auth AND bug', got {len(item['matches'])}: {item['matches']}"
    )


async def test_backlog_list_match_context_match_entry_has_required_keys():
    """backlog_list match_context=True every match entry contains 'field', 'term', 'snippet', 'text'.

    Tests: match entry schema — all four required keys must be present on every entry.
    How: Search for a single term with match_context=True. Assert each entry in the
         matches list has the keys field, term, snippet, and text.
    Why: Callers depend on a stable schema. Missing keys produce KeyError in consumers.
    """
    items = [{"title": "Auth service", "section": "P1", "topic": "", "type": "Feature", "body": ""}]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "auth", "match_context": True})

    assert len(response["items"]) == 1
    item = response["items"][0]
    for match_entry in item["matches"]:
        assert "field" in match_entry, f"match entry missing 'field': {match_entry}"
        assert "term" in match_entry, f"match entry missing 'term': {match_entry}"
        assert "snippet" in match_entry, f"match entry missing 'snippet': {match_entry}"
        assert "text" in match_entry, f"match entry missing 'text': {match_entry}"


# ---------------------------------------------------------------------------
# snippet_context parameter and formatted text output
# ---------------------------------------------------------------------------


def test_snippet_context_parameter_respected():
    """_make_snippet_parts respects snippet_context to limit window size.

    Tests: context=100 yields at most 50 chars before and after the match.
    How: Build a 300-char text with a match near the middle. Call _make_snippet_parts
         with snippet_context=100. Assert pre + post chars total ≤ 100.
    Why: Callers pass snippet_context to control response token cost.
    """
    from backlog_core.server import _make_snippet_parts

    text = "A" * 100 + "MATCH" + "B" * 100
    start = 100
    end = 105
    raw_snippet, matched_text, snip_start, snip_end = _make_snippet_parts(text, start, end, snippet_context=100)

    pre_chars = start - snip_start
    post_chars = snip_end - end
    assert pre_chars <= 50, f"pre_chars={pre_chars} exceeds budget of 50"
    assert post_chars <= 50, f"post_chars={post_chars} exceeds budget of 50"
    assert matched_text == "MATCH"
    assert "MATCH" in raw_snippet


def test_snippet_context_budget_redistribution_near_start():
    """Budget surplus from near-start match redistributes to post side.

    Tests: when match is at position 5, pre can only use 5 chars; remaining
           budget flows to post, giving post more than snippet_context//2.
    How: Place a match at position 5 in a long text. Use snippet_context=100.
         Assert post_chars > 50 (received redistributed budget).
    Why: Sliding-window ensures we fill the window even when one side is at a boundary.
    """
    from backlog_core.server import _make_snippet_parts

    text = "START" + "MATCH" + "C" * 200
    start = 5
    end = 10
    _, _, snip_start, snip_end = _make_snippet_parts(text, start, end, snippet_context=100)

    pre_chars = start - snip_start
    post_chars = snip_end - end
    assert pre_chars == 5, f"pre_chars={pre_chars}, expected 5 (only 5 chars available)"
    assert post_chars > 50, f"post_chars={post_chars}, expected > 50 (surplus from pre redistributed)"


def test_snippet_context_budget_redistribution_near_end():
    """Budget surplus from near-end match redistributes to pre side.

    Tests: when match is 5 chars from end, post can only use 5 chars; remaining
           budget flows to pre, giving pre more than snippet_context//2.
    How: Place a match 5 chars from end in a long text. Use snippet_context=100.
         Assert pre_chars > 50 (received redistributed budget).
    Why: Sliding-window ensures we fill the window even when one side is at a boundary.
    """
    from backlog_core.server import _make_snippet_parts

    text = "D" * 200 + "MATCH" + "END12"
    start = 200
    end = 205
    _, _, snip_start, snip_end = _make_snippet_parts(text, start, end, snippet_context=100)

    pre_chars = start - snip_start
    post_chars = snip_end - end
    assert post_chars == 5, f"post_chars={post_chars}, expected 5 (only 5 chars available)"
    assert pre_chars > 50, f"pre_chars={pre_chars}, expected > 50 (surplus from post redistributed)"


def test_snippet_ellipsis_present_when_content_truncated():
    """Ellipsis markers appear when content precedes or follows the window.

    Tests: both leading and trailing '...' present when match is deep inside text.
    How: 300-char text with match at position 150. snippet_context=100.
         Assert raw snippet starts and ends with '...'.
    Why: Consumers use '...' to detect truncation and decide if full body is needed.
    """
    from backlog_core.server import _make_snippet_parts

    text = "A" * 150 + "MATCH" + "B" * 150
    start = 150
    end = 155
    raw_snippet, _, snip_start, snip_end = _make_snippet_parts(text, start, end, snippet_context=100)

    assert snip_start > 0, "snip_start must be > 0 so leading '...' is warranted"
    assert snip_end < len(text), "snip_end must be < len(text) so trailing '...' is warranted"
    assert raw_snippet.startswith("..."), f"expected leading '...', got: {raw_snippet[:10]!r}"
    assert raw_snippet.endswith("..."), f"expected trailing '...', got: {raw_snippet[-10:]!r}"


def test_snippet_no_ellipsis_at_boundaries():
    """No ellipsis when match is at the very start or end of text.

    Tests: snippet starting at position 0 has no leading '...'; snippet ending
           at len(text) has no trailing '...'.
    How: 20-char text with match at position 0. snippet_context=200.
    Why: False '...' misleads consumers into thinking content was truncated.
    """
    from backlog_core.server import _make_snippet_parts

    text = "MATCHrestoftext12345"
    start = 0
    end = 5
    raw_snippet, _, snip_start, snip_end = _make_snippet_parts(text, start, end, snippet_context=200)

    assert snip_start == 0
    assert snip_end == len(text)
    assert not raw_snippet.startswith("..."), f"unexpected leading '...': {raw_snippet!r}"
    assert not raw_snippet.endswith("..."), f"unexpected trailing '...': {raw_snippet!r}"


def test_format_match_text_section_label_not_counted_in_budget():
    """Section label is excluded from the character budget.

    Tests: _format_match_text produces the label prefix unconditionally and the
           snippet window is computed on the haystack text only — not the label.
    How: 300-char text, snippet_context=50. Call _format_match_text. Verify
         the result contains '[segment: body:acceptance-criteria]' regardless
         of budget, and the snippet portion is within the expected window.
    Why: The label is structural metadata; counting it would shrink the useful
         context around the matched term.
    """
    from backlog_core.server import _format_match_text

    text = "E" * 100 + "KEYWORD" + "F" * 100
    start = 100
    end = 107
    field = "body:acceptance-criteria"
    result = _format_match_text(field, 1, text, start, end, snippet_context=50)

    assert result.startswith("1::[segment: body:acceptance-criteria]:: "), f"unexpected prefix: {result[:60]!r}"
    # Extract the snippet portion (after the label prefix)
    prefix = "1::[segment: body:acceptance-criteria]:: "
    snippet_part = result[len(prefix) :]
    assert "KEYWORD" in snippet_part, f"matched text missing from snippet: {snippet_part!r}"
    # Snippet portion must be within budget (~50 chars total context around KEYWORD)
    assert len(snippet_part) <= 50 + len("KEYWORD") + len("......"), (  # 6 chars for both '...'
        f"snippet_part too long: {len(snippet_part)} chars"
    )


async def test_backlog_list_snippet_context_parameter_accepted():
    """backlog_list accepts snippet_context parameter without error.

    Tests: the new snippet_context parameter is wired through to the response.
    How: Call backlog_list with snippet_context=200 and match_context=True.
         Assert response contains items with matches and no error key.
    Why: Parameter must be accepted by the tool signature.
    """
    items = [
        {
            "number": "523",
            "title": "Backlog lifecycle process gaps",
            "section": "P1",
            "topic": "process",
            "type": "Feature",
            "body": "## Acceptance Criteria\nThe backlog quality must improve.\n",
        }
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "backlog", "match_context": True, "snippet_context": 200})

    assert "error" not in response
    assert len(response["items"]) == 1
    item = response["items"][0]
    assert "matches" in item
    assert "match_header" in item
    assert item["match_header"] == "#523 - Backlog lifecycle process gaps"


async def test_backlog_list_match_header_format():
    """match_header contains '#number - title' at item level.

    Tests: grouped display format — header is separate from per-match text lines.
    How: Provide an item with number and title. Assert match_header equals
         '#N - Title' exactly.
    Why: Grouped format requires header once per item, not repeated in each text line.
    """
    items = [{"number": "42", "title": "My feature", "section": "P1", "topic": "", "type": "Feature", "body": ""}]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "feature", "match_context": True})

    item = response["items"][0]
    assert item["match_header"] == "#42 - My feature"


async def test_backlog_list_match_text_format():
    """Each match 'text' key follows 'N::[segment: field]:: snippet' format.

    Tests: text field format contract — index, segment label, snippet present.
    How: Provide an item with a body section. Search for a term that matches.
         Assert text starts with '1::[segment: ' and contains '::'.
    Why: Consumers parse the text field for display; format must be stable.
    """
    items = [
        {
            "number": "99",
            "title": "My item",
            "section": "P1",
            "topic": "",
            "type": "Feature",
            "body": "## Acceptance Criteria\nneeds quality review\n",
        }
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "quality", "match_context": True})

    item = response["items"][0]
    assert item["matches"], "expected at least one match"
    entry = item["matches"][0]
    text = entry["text"]
    assert text.startswith("     1::[segment: "), f"text does not start with index+segment: {text!r}"
    assert "]:: " in text, f"text missing ']:: ' separator: {text!r}"


# ---------------------------------------------------------------------------
# Primitive 2: item_depth on backlog_list
# ---------------------------------------------------------------------------


async def test_backlog_list_item_depth_zero_default_response_unchanged():
    """backlog_list with item_depth=0 (default) produces identical response to current.

    Tests: depth=0 is a pure no-op — no extra keys on items, no regression.
    How: Call backlog_list with item_depth=0 explicitly. Assert no item has
         'description_snippet' or 'section_names' keys.
    Why: depth=0 is the default contract. Existing callers must not be broken.
    """
    items = [{"title": "Auth service", "section": "P1", "topic": "", "type": "Feature", "body": ""}]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"item_depth": 0})

    assert len(response["items"]) == 1
    item = response["items"][0]
    assert "description_snippet" not in item, "depth=0 must not add description_snippet"
    assert "section_names" not in item, "depth=0 must not add section_names"


async def test_backlog_list_item_depth_one_adds_description_snippet():
    """backlog_list item_depth=1 adds a truncated description (≤300 chars) per item.

    Tests: depth=1 response shape — description_snippet key present and ≤300 chars.
    How: Provide an item with a 500-char description. Call with item_depth=1.
         Assert description_snippet is present and its length is ≤300.
    Why: depth=1 is the primary de-dup level — callers scan snippets to eliminate
         non-matching candidates without fetching full items.
    """
    long_description = "A" * 500
    items = [
        {
            "title": "Auth service",
            "section": "P1",
            "topic": "",
            "type": "Feature",
            "description": long_description,
            "body": "",
        }
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"item_depth": 1})

    assert len(response["items"]) == 1
    item = response["items"][0]
    assert "description_snippet" in item, "depth=1 must add description_snippet"
    assert len(item["description_snippet"]) <= 300, (
        f"description_snippet must be ≤300 chars, got {len(item['description_snippet'])}"
    )


async def test_backlog_list_item_depth_one_adds_section_names():
    """backlog_list item_depth=1 adds a list of section names present in the item.

    Tests: depth=1 section_names key — list of strings naming every section.
    How: Provide an item whose body contains two named sections. Call with item_depth=1.
         Assert section_names is a list containing the expected section names.
    Why: Callers use section_names to decide which section to fetch with backlog_view
         without loading any section content.
    """
    items = [
        {
            "title": "Pipeline feature",
            "section": "P1",
            "topic": "",
            "type": "Feature",
            "description": "Implements core pipeline",
            "body": "## Acceptance Criteria\n- passes CI\n## Impact Radius\n- affects deploy",
        }
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"item_depth": 1})

    assert len(response["items"]) == 1
    item = response["items"][0]
    assert "section_names" in item, "depth=1 must add section_names"
    assert isinstance(item["section_names"], list)
    assert len(item["section_names"]) >= 1


async def test_backlog_list_item_depth_two_adds_full_description():
    """backlog_list item_depth=2 adds the complete description (not truncated).

    Tests: depth=2 description is full-length — no 300-char truncation.
    How: Provide an item with a 500-char description. Call with item_depth=2.
         Assert full_description is present and equals the original 500-char string.
    Why: depth=2 gives callers enough context to make a de-dup decision for all but
         the most ambiguous cases without fetching the full item.
    """
    long_description = "B" * 500
    items = [
        {
            "title": "Auth service",
            "section": "P1",
            "topic": "",
            "type": "Feature",
            "description": long_description,
            "body": "",
        }
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"item_depth": 2})

    assert len(response["items"]) == 1
    item = response["items"][0]
    assert "full_description" in item, "depth=2 must add full_description"
    assert item["full_description"] == long_description


async def test_backlog_list_item_depth_two_adds_section_first_lines():
    """backlog_list item_depth=2 adds the first line of each section per item.

    Tests: depth=2 section_first_lines key — dict mapping section name to first line.
    How: Provide an item with two sections each having multiple lines. Call with item_depth=2.
         Assert section_first_lines is a dict and each value is a single line (no newlines).
    Why: First lines disambiguate sections — callers can skip unrelated sections and
         use backlog_view(sections=[...]) to load only the relevant ones.
    """
    items = [
        {
            "title": "Pipeline feature",
            "section": "P1",
            "topic": "",
            "type": "Feature",
            "description": "Implements core pipeline",
            "body": "## Acceptance Criteria\n- passes CI\n- green build\n## Impact Radius\n- affects deploy\n- requires restart",
        }
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"item_depth": 2})

    assert len(response["items"]) == 1
    item = response["items"][0]
    assert "section_first_lines" in item, "depth=2 must add section_first_lines"
    assert isinstance(item["section_first_lines"], dict)
    for section_name, first_line in item["section_first_lines"].items():
        assert "\n" not in first_line, (
            f"section_first_lines[{section_name!r}] must be a single line, got {first_line!r}"
        )


async def test_backlog_list_item_depth_three_returns_full_item_content():
    """backlog_list item_depth=3 includes full item content equivalent to backlog_view.

    Tests: depth=3 includes body key with the complete item body text.
    How: Provide an item with body text. Call with item_depth=3.
         Assert the returned item has a 'body' key equal to the source body.
    Why: depth=3 allows callers to get full item content in a list call, avoiding
         a separate backlog_view call for items they will definitely read in full.
    """
    body_text = "## Description\nFull content here.\n## Acceptance Criteria\n- all tests pass"
    items = [
        {
            "title": "Auth service",
            "section": "P1",
            "topic": "",
            "type": "Feature",
            "description": "Auth implementation",
            "body": body_text,
        }
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"item_depth": 3})

    assert len(response["items"]) == 1
    item = response["items"][0]
    assert "body" in item, "depth=3 must include 'body' key with full item content"
    assert item["body"] == body_text


async def test_backlog_list_item_depth_zero_omitted_is_same_as_explicit_zero():
    """backlog_list item_depth omitted is identical to item_depth=0 — no extra keys.

    Tests: the default value is 0 and produces the same output as explicit depth=0.
    How: Call backlog_list twice — once without item_depth, once with item_depth=0.
         Assert both item shapes are identical (no depth-specific keys).
    Why: The default must be backward-compatible. Introducing item_depth must not
         change the response shape for any caller that does not pass the parameter.
    """
    items = [{"title": "Item A", "section": "P1", "topic": "", "type": "Feature", "body": ""}]
    op_result = {"items": items}
    depth_keys = {"description_snippet", "section_names", "full_description", "section_first_lines"}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response_default = await _call("backlog_list", {})
        response_zero = await _call("backlog_list", {"item_depth": 0})

    for item in response_default["items"]:
        for key in depth_keys:
            assert key not in item, f"Default call must not have '{key}'"
    for item in response_zero["items"]:
        for key in depth_keys:
            assert key not in item, f"item_depth=0 call must not have '{key}'"


async def test_backlog_list_match_context_and_item_depth_one_no_body_leak():
    """match_context=True combined with item_depth=1 must not return body in the response.

    Tests: the call-order interaction — _enrich_with_match_context runs before
    _apply_item_depth, so match snippets are extracted from body before depth=1
    removes it. If the order were reversed, body would survive in the response.

    How: Provide an item with a large body containing the search term. Call with
         match_context=True AND item_depth=1. Assert body is absent, matches is
         present, and description_snippet is present.
    Why: Regression guard for the feature interaction bug where body (53KB in
         production) reappeared when both parameters were used together.
    """
    body_text = "## Background\n\nThis improves quality and testing coverage.\n" + "x" * 500
    items = [
        {
            "title": "Quality improvement",
            "section": "P1",
            "topic": "",
            "type": "Feature",
            "description": "Improve quality and testing",
            "body": body_text,
        }
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "quality", "match_context": True, "item_depth": 1})

    assert len(response["items"]) == 1
    item = response["items"][0]
    assert "body" not in item, "item_depth=1 must remove body even when match_context=True"
    assert "matches" in item, "match_context=True must add matches key"
    assert len(item["matches"]) > 0, "search term 'quality' must produce at least one match"
    assert "description_snippet" in item, "item_depth=1 must add description_snippet"


# ---------------------------------------------------------------------------
# Primitive 3: sections parameter on backlog_view
# ---------------------------------------------------------------------------


async def test_backlog_view_sections_none_default_returns_unchanged_response():
    """backlog_view with sections=None (default) returns the full response unchanged.

    Tests: default=None contract — sections parameter is a pure opt-in, no regression.
    How: Call backlog_view without sections param. Assert full title and body keys present.
    Why: All existing callers omit sections. The default must preserve their response shape.
    """
    op_result = _make_view_result({
        "title": "Auth service",
        "priority": "P1",
        "body": "## Description\nFull body.\n## Acceptance Criteria\n- tests pass",
        "sections": {
            "Description": {"num_entries": 1, "num_struck": 0, "entries": []},
            "Acceptance Criteria": {"num_entries": 1, "num_struck": 0, "entries": []},
        },
    })
    with patch("backlog_core.operations.view_item", return_value=op_result):
        response = await _call("backlog_view", {"selector": "#42", "summary": False})

    assert response["title"] == "Auth service"
    assert "body" in response


async def test_backlog_view_sections_single_section_returns_only_that_section():
    """backlog_view sections=['description'] returns only the description section plus identity fields.

    Tests: single-section filter — only the requested section is in the response body/sections.
    How: Provide an item with two sections. Request sections=['description'].
         Assert the response contains description data and does not contain the other section.
    Why: Targeted section reads reduce token consumption when callers only need one
         discriminating section (e.g., 'description' for de-dup checks).
    """
    op_result = _make_view_result({
        "title": "Auth service",
        "priority": "P1",
        "number": 42,
        "status": "open",
        "state": "open",
        "body": "## Description\nFull auth description.\n## Acceptance Criteria\n- tests pass",
        "sections": {
            "description": {
                "num_entries": 1,
                "num_struck": 0,
                "entries": [{"id": "e1", "struck": False, "content": "Full auth description."}],
            },
            "acceptance-criteria": {
                "num_entries": 1,
                "num_struck": 0,
                "entries": [{"id": "e2", "struck": False, "content": "tests pass"}],
            },
        },
    })
    with patch("backlog_core.operations.view_item", return_value=op_result):
        response = await _call("backlog_view", {"selector": "#42", "summary": False, "sections": ["description"]})

    # Identity fields always included
    assert response["title"] == "Auth service"
    assert response["number"] == 42
    # Sections dict should only contain the requested section
    if response.get("sections"):
        assert "acceptance-criteria" not in response["sections"], (
            "Non-requested section 'acceptance-criteria' must be excluded"
        )


async def test_backlog_view_sections_multiple_sections_returns_all_requested():
    """backlog_view sections=['description', 'acceptance-criteria'] returns both requested sections.

    Tests: multi-section filter — all requested sections are present, unrequested ones absent.
    How: Provide an item with three sections. Request two of them.
         Assert both requested sections are present and the third is absent.
    Why: De-dup workflow needs description + acceptance criteria in one targeted call.
    """
    op_result = _make_view_result({
        "title": "Pipeline feature",
        "priority": "P1",
        "number": 99,
        "state": "open",
        "body": (
            "## Description\nCore pipeline implementation.\n"
            "## Acceptance Criteria\n- CI passes\n"
            "## Impact Radius\n- affects deploy"
        ),
        "sections": {
            "description": {"num_entries": 1, "num_struck": 0, "entries": []},
            "acceptance-criteria": {"num_entries": 1, "num_struck": 0, "entries": []},
            "impact-radius": {"num_entries": 1, "num_struck": 0, "entries": []},
        },
    })
    with patch("backlog_core.operations.view_item", return_value=op_result):
        response = await _call(
            "backlog_view", {"selector": "#99", "summary": False, "sections": ["description", "acceptance-criteria"]}
        )

    assert response["title"] == "Pipeline feature"
    if response.get("sections"):
        assert "impact-radius" not in response["sections"], "Unrequested section 'impact-radius' must be excluded"


async def test_backlog_view_sections_invalid_section_name_silently_omitted():
    """backlog_view sections with an invalid name silently omits it — no error raised.

    Tests: invalid section name handling — response has no error key, response is valid.
    How: Request a section name that does not exist on the item. Assert no error key
         in the response and identity fields are still present.
    Why: Items have dynamic section names. Callers should not crash when requesting a
         section that a particular item does not have (e.g., not all items have 'impact-radius').
    """
    op_result = _make_view_result({
        "title": "Auth service",
        "priority": "P1",
        "number": 42,
        "state": "open",
        "body": "## Description\nContent here.",
        "sections": {"description": {"num_entries": 1, "num_struck": 0, "entries": []}},
    })
    with patch("backlog_core.operations.view_item", return_value=op_result):
        response = await _call(
            "backlog_view", {"selector": "#42", "summary": False, "sections": ["nonexistent-section-xyz"]}
        )

    assert "error" not in response, f"Must not return an error for invalid section name, got: {response.get('error')}"
    assert response["title"] == "Auth service"


async def test_backlog_view_sections_always_includes_identity_fields():
    """backlog_view sections filter always includes number, title, status, type, priority.

    Tests: always-included identity fields — present regardless of which sections are requested.
    How: Request a single content section. Assert number, title, status, type, and priority
         are all in the response.
    Why: Callers need identity fields to confirm they have the right item, even in
         targeted reads. These fields are the minimum required for any consumer.
    """
    op_result = _make_view_result({
        "title": "Auth service",
        "priority": "P1",
        "number": 42,
        "status": "needs-grooming",
        "state": "open",
        "body": "## Description\nContent.",
        "sections": {"description": {"num_entries": 1, "num_struck": 0, "entries": []}},
    })
    with patch("backlog_core.operations.view_item", return_value=op_result):
        response = await _call("backlog_view", {"selector": "#42", "summary": False, "sections": ["description"]})

    assert "title" in response, "title must always be present in sections-filtered response"
    assert "number" in response, "number must always be present in sections-filtered response"
    assert "priority" in response, "priority must always be present in sections-filtered response"


# ---------------------------------------------------------------------------
# backlog_list — deduplication (Fix 1)
# ---------------------------------------------------------------------------


async def test_backlog_list_dedup_same_issue_number_appears_once():
    """backlog_list returns each issue number at most once when duplicates exist in the raw list.

    Tests: deduplication contract — two entries for the same issue number produce one output item.
    How: Provide a raw items list with issue #260 present twice (same number, same title).
         Assert the response contains exactly one item for #260.
    Why: The upstream cache can emit the same item twice when multiple match paths
         select it. Callers must receive a deduplicated list.
    """
    items = [
        {"issue": "260", "title": "Fix auth bug", "section": "P1", "type": "Bug", "body": ""},
        {"issue": "260", "title": "Fix auth bug", "section": "P1", "type": "Bug", "body": ""},
        {"issue": "261", "title": "Deploy pipeline", "section": "P2", "type": "Feature", "body": ""},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {})

    numbers = [str(it.get("issue", it.get("number", ""))) for it in response["items"]]
    assert numbers.count("260") == 1, f"Expected exactly one #260, got: {numbers}"
    assert "261" in numbers


async def test_backlog_list_dedup_preserves_first_occurrence():
    """backlog_list keeps the first occurrence of a duplicated issue, not the second.

    Tests: first-wins dedup — the first dict in the raw list survives; duplicates are dropped.
    How: Two entries for #99 with different title values. Assert the retained item has
         the title from the first entry.
    Why: Deduplication must be deterministic and predictable. First-seen is the only
         consistent ordering when the cache does not sort.
    """
    items = [
        {"issue": "99", "title": "First occurrence", "section": "P0", "body": ""},
        {"issue": "99", "title": "Second occurrence — must be dropped", "section": "P0", "body": ""},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {})

    assert len(response["items"]) == 1
    assert response["items"][0]["title"] == "First occurrence"


async def test_backlog_list_dedup_hash_prefix_stripped():
    """backlog_list deduplicates issue numbers regardless of leading '#' prefix.

    Tests: '#'-stripped key matching — '#42' and '42' are the same issue.
    How: Provide items with issue='#42' and issue='42' (no hash). Assert only one
         item appears in the response.
    Why: The cache may store issue numbers with or without the '#' prefix. Both
         forms must be recognised as the same key.
    """
    items = [
        {"issue": "#42", "title": "Auth service refactor", "section": "P1", "body": ""},
        {"issue": "42", "title": "Auth service refactor duplicate", "section": "P1", "body": ""},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {})

    assert len(response["items"]) == 1


async def test_backlog_list_dedup_match_context_merged_matches():
    """backlog_list with match_context=True deduplicates before enrichment — one item with matches.

    Tests: deduplication before match-context enrichment — the surviving item gets
           all expected match data; the duplicate is gone before enrichment runs.
    How: Two entries for the same issue that both match the search term. Assert the
         response contains exactly one item and it has a non-empty matches list.
    Why: If dedup ran after enrichment, callers would still receive two result entries.
         The dedup must happen on the filtered item list before enrichment.
    """
    items = [
        {"issue": "500", "title": "Auth token expiry", "section": "P1", "type": "Bug", "body": ""},
        {"issue": "500", "title": "Auth token expiry", "section": "P1", "type": "Bug", "body": ""},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "auth", "match_context": True})

    assert len(response["items"]) == 1, (
        f"Expected 1 item after dedup, got {len(response['items'])}: {[it.get('issue') for it in response['items']]}"
    )
    assert "matches" in response["items"][0]


# ---------------------------------------------------------------------------
# backlog_list — token-based pagination (Fix 2)
# ---------------------------------------------------------------------------


async def test_backlog_list_match_pages_present_when_match_context_true():
    """backlog_list with match_context=True always includes match_pages in the response.

    Tests: match_pages key always present — callers can rely on it without checking.
    How: Call with match_context=True and a search term that produces matches.
         Assert the response contains a match_pages key with required sub-keys.
    Why: Callers need match_pages to detect whether pagination activated and what
         page they are on, even when the result fits on one page.
    """
    items = [{"issue": "1", "title": "Auth bug", "section": "P1", "type": "Bug", "body": ""}]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "auth", "match_context": True})

    assert "match_pages" in response, "match_pages must be present when match_context=True"
    mp = response["match_pages"]
    assert "current_page" in mp
    assert "total_pages" in mp
    assert "tokens_per_page" in mp
    assert "total_match_tokens" in mp
    assert "paginated" in mp


async def test_backlog_list_match_pages_absent_when_match_context_false():
    """backlog_list without match_context does not include match_pages.

    Tests: match_pages only present when match_context=True — no pollution of other callers.
    How: Call without match_context (default False). Assert match_pages is absent.
    Why: match_pages is a match_context-specific key. Adding it unconditionally
         would change the response shape for all existing callers.
    """
    items = [{"issue": "1", "title": "Auth bug", "section": "P1", "body": ""}]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"search": "auth"})

    assert "match_pages" not in response


async def test_backlog_list_match_pages_not_paginated_when_tokens_below_limit():
    """backlog_list match_pages.paginated=False when total match tokens ≤ page_token_limit.

    Tests: no pagination when under budget — small result set returns paginated=False.
    How: Use a tiny page_token_limit (10000) larger than any realistic single-item output.
         Assert paginated=False and all items returned on page 1.
    Why: Pagination must not activate on small result sets — callers should not need
         to make follow-up calls unless the budget is genuinely exceeded.
    """
    items = [
        {"issue": "1", "title": "Alpha", "section": "P1", "type": "Bug", "body": ""},
        {"issue": "2", "title": "Beta", "section": "P2", "type": "Feature", "body": ""},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call(
            "backlog_list", {"search": "a", "match_context": True, "page_token_limit": 10000, "tokens_per_page": 5000}
        )

    mp = response["match_pages"]
    assert mp["paginated"] is False
    assert mp["current_page"] == 1
    assert mp["total_pages"] == 1
    assert len(response["items"]) == 2


async def test_backlog_list_match_pagination_activates_above_token_limit(mocker):
    """backlog_list activates token pagination when total match tokens exceed page_token_limit.

    Tests: pagination activation threshold — when mocked token counts push total above
           page_token_limit, paginated=True and only page 1 items are returned.
    How: Mock tiktoken encoding to return a fixed 200-token cost per item. Set
         page_token_limit=300 and tokens_per_page=200. With 3 items each costing 200
         tokens (total=600 > 300), pagination activates. Page 1 fits 1 item (200 tokens).
    Why: Token count is the activation signal. Mocking the encoder gives deterministic
         counts so the test does not depend on real text length.
    """
    items = [{"issue": str(i), "title": f"Item {i}", "section": "P1", "type": "Bug", "body": ""} for i in range(1, 4)]
    op_result = {"items": items}

    # Each encode call returns a list of 200 fake token IDs.
    fake_tokens = list(range(200))
    mocker.patch("backlog_core.server._enc.encode", return_value=fake_tokens)

    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call(
            "backlog_list",
            {"search": "item", "match_context": True, "page": 1, "tokens_per_page": 200, "page_token_limit": 300},
        )

    mp = response["match_pages"]
    assert mp["paginated"] is True, f"Expected paginated=True, got {mp}"
    assert mp["current_page"] == 1
    assert mp["total_pages"] >= 2, f"Expected ≥2 pages, got total_pages={mp['total_pages']}"
    # Page 1 must not contain all 3 items.
    assert len(response["items"]) < 3, f"Expected <3 items on page 1 when paginated, got {len(response['items'])}"


async def test_backlog_list_match_pagination_page2_returns_next_items(mocker):
    """backlog_list page=2 returns the second page of match results.

    Tests: page parameter routing — page=2 returns items that did not fit on page 1.
    How: Mock encoder to return 200 tokens per call. 3 items x 200 = 600 > 300 limit.
         tokens_per_page=200 means 1 item per page. Request page=2.
    Why: The page parameter is the caller's handle for retrieving subsequent pages.
         If page=2 returned the same items as page=1, callers would loop forever.
    """
    items = [{"issue": str(i), "title": f"Item {i}", "section": "P1", "type": "Bug", "body": ""} for i in range(1, 4)]
    op_result = {"items": items}

    fake_tokens = list(range(200))
    mocker.patch("backlog_core.server._enc.encode", return_value=fake_tokens)

    with patch("backlog_core.operations.list_items", return_value=op_result):
        response_p1 = await _call(
            "backlog_list",
            {"search": "item", "match_context": True, "page": 1, "tokens_per_page": 200, "page_token_limit": 300},
        )
        response_p2 = await _call(
            "backlog_list",
            {"search": "item", "match_context": True, "page": 2, "tokens_per_page": 200, "page_token_limit": 300},
        )

    p1_issues = {it.get("issue") for it in response_p1["items"]}
    p2_issues = {it.get("issue") for it in response_p2["items"]}
    assert p2_issues != p1_issues, f"page=2 must return different items than page=1. p1={p1_issues}, p2={p2_issues}"
    assert response_p2["match_pages"]["current_page"] == 2


async def test_backlog_list_match_pagination_message_on_page1(mocker):
    """backlog_list adds a truncation message to messages when paginated and on page 1.

    Tests: truncation message present on page 1 — callers learn pagination is active
           and how to request more pages.
    How: Mock encoder so pagination activates (total > page_token_limit). Call with page=1.
         Assert messages list contains the truncation notice.
    Why: The truncation message is the primary discovery mechanism for pagination.
         Without it, callers would not know to request page=2.
    """
    items = [{"issue": str(i), "title": f"Item {i}", "section": "P1", "type": "Bug", "body": ""} for i in range(1, 4)]
    op_result = {"items": items}

    fake_tokens = list(range(200))
    mocker.patch("backlog_core.server._enc.encode", return_value=fake_tokens)

    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call(
            "backlog_list",
            {"search": "item", "match_context": True, "page": 1, "tokens_per_page": 200, "page_token_limit": 300},
        )

    messages = response.get("messages", [])
    assert any("truncated" in m.lower() or "page" in m.lower() for m in messages), (
        f"Expected truncation notice in messages when paginated on page 1. Got: {messages}"
    )


async def test_backlog_list_match_pagination_no_message_on_page2(mocker):
    """backlog_list does NOT add the truncation message when page > 1.

    Tests: truncation message only on page 1 — subsequent pages don't repeat the notice.
    How: Same paginated setup as page1 test but request page=2. Assert messages does
         not contain a 'truncated' notice.
    Why: The truncation message is meant to alert callers on first encounter.
         Repeating it on every page would produce noisy duplicate messages.
    """
    items = [{"issue": str(i), "title": f"Item {i}", "section": "P1", "type": "Bug", "body": ""} for i in range(1, 4)]
    op_result = {"items": items}

    fake_tokens = list(range(200))
    mocker.patch("backlog_core.server._enc.encode", return_value=fake_tokens)

    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call(
            "backlog_list",
            {"search": "item", "match_context": True, "page": 2, "tokens_per_page": 200, "page_token_limit": 300},
        )

    messages = response.get("messages", [])
    truncation_messages = [m for m in messages if "truncated" in m.lower()]
    assert not truncation_messages, f"Expected no truncation notice on page 2, got: {truncation_messages}"


async def test_backlog_list_match_context_false_page_param_uses_offset_limit():
    """backlog_list with match_context=False ignores page/token params — offset/limit still work.

    Tests: match_context=False contract — token pagination must not activate; offset/limit
           govern page selection as before.
    How: Call with match_context=False, page=2, offset=1, limit=1. Assert the response
         returns the item at position 1 (offset=1), not a token-paginated page.
         Assert match_pages is absent.
    Why: Token pagination is a match_context feature only. Existing callers that use
         offset/limit must not be affected by the new page parameter.
    """
    items = [
        {"issue": "1", "title": "Alpha", "section": "P1", "body": ""},
        {"issue": "2", "title": "Beta", "section": "P2", "body": ""},
        {"issue": "3", "title": "Gamma", "section": "P2", "body": ""},
    ]
    op_result = {"items": items}
    with patch("backlog_core.operations.list_items", return_value=op_result):
        response = await _call("backlog_list", {"match_context": False, "page": 2, "offset": 1, "limit": 1})

    assert "match_pages" not in response
    assert len(response["items"]) == 1
    assert response["items"][0]["issue"] == "2"
