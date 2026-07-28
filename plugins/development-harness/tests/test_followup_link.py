"""Tests for the follow-up link primitive (T-P3-FOLLOWUP).

Verifies that ``link_followup`` persists the ``followup_to`` metadata field
to YAML frontmatter (durable), and ``list_followups`` retrieves items by
origin logical ID (queryable).  Also exercises the MCP tool wrappers to
confirm parameter forwarding through the server layer.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from backlog_core.models import BacklogError
from backlog_core.server import mcp

from tests.helpers import call_mcp_tool

# ---------------------------------------------------------------------------
# Operations-layer: durability + queryability
# ---------------------------------------------------------------------------


def test_link_followup_persists_and_list_followups_queries(write_test_item) -> None:
    """link_followup writes followup_to to YAML; list_followups finds it back.

    Creates a follow-up item, links it to plan ``P1``, then re-reads the
    YAML file from disk to confirm the field survived the round-trip
    (durability).  Then queries ``list_followups("P1")`` and asserts the
    item appears (queryability).
    """
    from backlog_core.operations import link_followup, list_followups

    write_test_item("Origin item", priority="P1", description="the origin")
    followup_path = write_test_item("Follow-up task", priority="P2", description="needs more work")

    # Link the follow-up to plan P1.
    result = link_followup("Follow-up task", "P1")
    assert result["title"] == "Follow-up task"
    assert result["followup_to"] == "P1"

    # Durability: re-read the YAML file from disk and check the field is there.
    from backlog_core.yaml_io import load_item

    reloaded = load_item(followup_path)
    assert reloaded.metadata.followup_to == "P1"

    # Queryability: list_followups returns the linked item.
    listed = list_followups("P1")
    assert listed["count"] == 1
    items = list(listed["items"])
    item = items[0]
    assert item["title"] == "Follow-up task"
    assert item["followup_to"] == "P1"

    # A different origin returns nothing.
    empty = list_followups("P2")
    assert empty["count"] == 0


def test_link_followup_missing_item_raises(write_test_item) -> None:
    """link_followup raises ItemNotFoundError for an unknown selector."""
    from backlog_core.models import ItemNotFoundError
    from backlog_core.operations import link_followup

    write_test_item("Existing item", priority="P1")
    with pytest.raises(ItemNotFoundError):
        link_followup("nonexistent-item-title", "P1")


def test_link_followup_clear_then_query(write_test_item) -> None:
    """Passing an empty followup_to clears the link; list_followups excludes it."""
    from backlog_core.operations import link_followup, list_followups

    write_test_item("Follow-up A", priority="P2")
    link_followup("Follow-up A", "P1")
    assert list_followups("P1")["count"] == 1

    # Clear the link.
    link_followup("Follow-up A", "")
    assert list_followups("P1")["count"] == 0


# ---------------------------------------------------------------------------
# MCP tool wrappers: parameter forwarding
# ---------------------------------------------------------------------------


async def test_backlog_link_followup_forwards_params() -> None:
    """backlog_link_followup passes selector and followup_to to operations."""
    op_result = {"title": "My Item", "followup_to": "P1"}
    with patch("dh_core.operations.link_followup", return_value=op_result) as mock_link:
        response = await call_mcp_tool(mcp, "backlog_link_followup", {"selector": "My Item", "followup_to": "P1"})

    mock_link.assert_called_once()
    call_kwargs = mock_link.call_args.kwargs
    assert call_kwargs["selector"] == "My Item"
    assert call_kwargs["followup_to"] == "P1"
    assert response["title"] == "My Item"
    assert response["followup_to"] == "P1"
    assert "messages" in response


async def test_backlog_link_followup_backlog_error_returns_error_key() -> None:
    """backlog_link_followup catches BacklogError and includes error key."""
    with patch("dh_core.operations.link_followup", side_effect=BacklogError("not found")):
        response = await call_mcp_tool(mcp, "backlog_link_followup", {"selector": "missing", "followup_to": "P1"})
    assert response["error"] == "not found"
    assert "messages" in response


async def test_backlog_list_followups_forwards_params() -> None:
    """backlog_list_followups passes followup_to to operations."""
    op_result = {"items": [{"title": "X", "followup_to": "P1"}], "count": 1}
    with patch("dh_core.operations.list_followups", return_value=op_result) as mock_list:
        response = await call_mcp_tool(mcp, "backlog_list_followups", {"followup_to": "P1"})

    mock_list.assert_called_once()
    assert mock_list.call_args.kwargs["followup_to"] == "P1"
    assert response["count"] == 1
    assert response["items"][0]["title"] == "X"


async def test_backlog_list_followups_backlog_error_returns_error_key() -> None:
    """backlog_list_followups catches BacklogError and includes error key."""
    with patch("dh_core.operations.list_followups", side_effect=BacklogError("boom")):
        response = await call_mcp_tool(mcp, "backlog_list_followups", {"followup_to": "P1"})
    assert response["error"] == "boom"
