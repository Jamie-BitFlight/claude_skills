"""Tests for the sections parameter of the backlog_groom MCP tool.

Covers:
- Parameter validation: sections is accepted and forwarded to operations.groom_item
- Mutual exclusion: sections rejects all per-section modifier combinations
- Sections routing: tool passes sections dict through to groom_item
- Signature contract: sections parameter is present on the tool

All tests use the in-memory FastMCP transport via Client(mcp).
Operations are mocked at ``backlog_core.operations.groom_item``.

No @pytest.mark.asyncio decorators — asyncio_mode = "auto" is set globally.
All imports are at module level.
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import pytest
from backlog_core.models import BacklogError
from backlog_core.server import backlog_groom, mcp
from fastmcp.client import Client

# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


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
# Signature contract
# ---------------------------------------------------------------------------


def test_backlog_groom_has_sections_param() -> None:
    """backlog_groom should accept a sections parameter.

    Tests: backlog_groom tool signature
    How: Inspect the function signature and assert 'sections' is present.
    Why: Regression guard — verifies T03 wired the parameter correctly.
         A missing parameter would raise a TypeError at call time without
         this explicit check.
    """
    sig = inspect.signature(backlog_groom)
    assert "sections" in sig.parameters


def test_backlog_groom_sections_param_defaults_to_none() -> None:
    """backlog_groom sections parameter defaults to None.

    Tests: backlog_groom tool signature default
    How: Inspect the function signature and assert 'sections' default is None.
    Why: Default of None ensures backward compatibility — callers that don't
         pass sections get the existing single-section code path unchanged.
    """
    sig = inspect.signature(backlog_groom)
    assert sig.parameters["sections"].default is None


# ---------------------------------------------------------------------------
# sections success path
# ---------------------------------------------------------------------------


async def test_backlog_groom_sections_calls_groom_item() -> None:
    """backlog_groom with sections dict delegates to operations.groom_item.

    Tests: backlog_groom MCP tool sections routing
    How: Call tool with sections={section_name: content}. Mock groom_item.
         Assert groom_item was called exactly once.
    Why: Verifies the sections param reaches operations rather than being
         dropped or short-circuited in the server layer.
    """
    # Arrange
    op_result = {
        "title": "My Feature",
        "sections_written": ["Background", "Research"],
        "groomed_updated": True,
        "messages": [],
        "warnings": [],
        "errors": [],
    }

    # Act
    with patch("backlog_core.operations.groom_item", return_value=op_result) as mock_groom:
        response = await _call(
            "backlog_groom", {"selector": "#42", "sections": {"Background": "Some context", "Research": "Key findings"}}
        )

    # Assert
    mock_groom.assert_called_once()
    assert isinstance(response, dict)
    assert "sections_written" in response
    assert response["sections_written"] == ["Background", "Research"]
    assert response["groomed_updated"] is True


async def test_backlog_groom_sections_forwarded_to_groom_item() -> None:
    """backlog_groom forwards the sections dict unchanged to groom_item.

    Tests: backlog_groom sections parameter forwarding
    How: Call with specific sections dict. Capture groom_item call kwargs.
         Assert kwargs["sections"] matches the input exactly.
    Why: groom_item dispatches based on sections is not None; if the server
         layer transforms or drops the dict, the batch path is never reached.
    """
    # Arrange
    sections_input = {"Acceptance Criteria": "- [ ] Pass all tests", "Context": "Migrating from legacy system"}
    op_result = {
        "title": "Feature",
        "sections_written": list(sections_input.keys()),
        "groomed_updated": True,
        "messages": [],
        "warnings": [],
        "errors": [],
    }

    # Act
    with patch("backlog_core.operations.groom_item", return_value=op_result) as mock_groom:
        await _call("backlog_groom", {"selector": "Feature", "sections": sections_input})

    # Assert
    call_kwargs = mock_groom.call_args.kwargs
    assert call_kwargs["sections"] == sections_input


async def test_backlog_groom_sections_none_forwarded_when_absent() -> None:
    """backlog_groom forwards sections=None when parameter is omitted.

    Tests: backlog_groom sections=None forwarding
    How: Call tool without sections param. Assert groom_item receives sections=None.
    Why: groom_item's dispatch logic checks `if sections is not None` to choose
         batch vs single-section path. If the server sends a wrong default,
         the routing silently breaks.
    """
    # Arrange
    op_result = {"title": "Item", "synced": False, "messages": [], "warnings": [], "errors": []}

    # Act
    with patch("backlog_core.operations.groom_item", return_value=op_result) as mock_groom:
        await _call("backlog_groom", {"selector": "Item", "section": "Background", "content": "text"})

    # Assert
    call_kwargs = mock_groom.call_args.kwargs
    assert call_kwargs["sections"] is None


async def test_backlog_groom_empty_sections_dict_calls_groom_item() -> None:
    """backlog_groom with sections={} still calls groom_item (no short-circuit in server layer).

    Tests: backlog_groom empty sections dict
    How: Call tool with sections={}. Assert groom_item is called with sections={}.
    Why: The server layer must not short-circuit on empty dict — that decision
         belongs to operations.groom_item. Short-circuiting here would hide
         the empty-dict no-op from the operations layer.
    """
    # Arrange
    op_result = {
        "title": "Item",
        "sections_written": [],
        "groomed_updated": False,
        "messages": [],
        "warnings": [],
        "errors": [],
    }

    # Act
    with patch("backlog_core.operations.groom_item", return_value=op_result) as mock_groom:
        await _call("backlog_groom", {"selector": "Item", "sections": {}})

    # Assert
    mock_groom.assert_called_once()
    call_kwargs = mock_groom.call_args.kwargs
    assert call_kwargs["sections"] == {}


async def test_backlog_groom_sections_backlog_error_returns_error_key() -> None:
    """backlog_groom with sections propagates BacklogError as error dict.

    Tests: backlog_groom sections error handling
    How: Mock groom_item to raise BacklogError. Call with sections param.
         Assert response contains "error" key with the message.
    Why: The MCP tool must catch BacklogError regardless of which parameter
         path triggered it. Error propagation must not leak raw exceptions.
    """
    # Arrange / Act
    with patch("backlog_core.operations.groom_item", side_effect=BacklogError("item not found")):
        response = await _call("backlog_groom", {"selector": "#999", "sections": {"Background": "text"}})

    # Assert
    assert "error" in response
    assert response["error"] == "item not found"


# ---------------------------------------------------------------------------
# Mutual exclusion — parametrized
# ---------------------------------------------------------------------------

_MUTUAL_EXCLUSION_CASES: list[tuple[str, dict]] = [
    ("sections+section", {"selector": "Item", "sections": {"Background": "text"}, "section": "Background"}),
    ("sections+content", {"selector": "Item", "sections": {"Background": "text"}, "content": "raw content"}),
    ("sections+entry_id", {"selector": "Item", "sections": {"Background": "text"}, "entry_id": "2026-01-01T00:00:00Z"}),
    ("sections+replace_section", {"selector": "Item", "sections": {"Background": "text"}, "replace_section": True}),
    ("sections+reason", {"selector": "Item", "sections": {"Background": "text"}, "reason": "outdated"}),
    ("sections+append", {"selector": "Item", "sections": {"Background": "text"}, "append": True}),
]


@pytest.mark.parametrize(("case_id", "params"), _MUTUAL_EXCLUSION_CASES, ids=[c[0] for c in _MUTUAL_EXCLUSION_CASES])
async def test_backlog_groom_sections_mutual_exclusion_returns_error(case_id: str, params: dict) -> None:
    """backlog_groom returns error dict when sections is combined with any per-section modifier.

    Tests: backlog_groom mutual exclusion guard
    How: Call tool with sections alongside each modifier. Assert error key present
         and groom_item is never called.
    Why: Allowing sections alongside section/content/entry_id/replace_section/
         reason/append creates ambiguous intent — which write mode wins?
         The server must reject these combinations before delegating to operations.
    """
    # Act — groom_item must NOT be called for any of these combinations
    with patch("backlog_core.operations.groom_item") as mock_groom:
        response = await _call("backlog_groom", params)

    # Assert
    assert "error" in response, f"Expected error key for case '{case_id}', got: {response}"
    assert "sections" in response["error"], (
        f"Error message should mention 'sections' for case '{case_id}', got: {response['error']}"
    )
    mock_groom.assert_not_called()


# ---------------------------------------------------------------------------
# Mutual exclusion — exact error message contract
# ---------------------------------------------------------------------------


async def test_backlog_groom_sections_mutual_exclusion_error_message() -> None:
    """backlog_groom sections mutual exclusion error names all conflicting parameters.

    Tests: backlog_groom mutual exclusion error message contract
    How: Call with sections + section. Assert error message lists all modifiers.
    Why: Downstream error handlers and tests rely on the exact error text to
         distinguish this validation failure from other error types.
    """
    # Act
    with patch("backlog_core.operations.groom_item"):
        response = await _call(
            "backlog_groom", {"selector": "Item", "sections": {"Background": "text"}, "section": "Background"}
        )

    # Assert
    expected_error = (
        "sections is mutually exclusive with section, content, entry_id, replace_section, reason, and append"
    )
    assert response["error"] == expected_error


async def test_backlog_groom_sections_mutual_exclusion_no_output_keys() -> None:
    """backlog_groom mutual exclusion error response omits messages/warnings keys.

    Tests: backlog_groom mutual exclusion response shape
    How: Call with conflicting sections + section. Assert only "error" key is present
         (no "messages", "warnings" from Output — those are not merged on early return).
    Why: The early-return path at line 774 returns {\"error\": \"...\"} without
         calling out.to_dict(). Tests confirm the exact shape so callers can rely
         on the absence of spurious keys.
    """
    # Act
    with patch("backlog_core.operations.groom_item"):
        response = await _call(
            "backlog_groom", {"selector": "Item", "sections": {"Background": "text"}, "content": "text"}
        )

    # Assert
    assert set(response.keys()) == {"error"}
