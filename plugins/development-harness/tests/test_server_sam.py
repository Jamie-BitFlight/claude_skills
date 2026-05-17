"""Tests for the SAM MCP tools added to backlog_core/server.py in Phase 2.

Four MCP tools are tested through the in-memory FastMCP transport using
Client(mcp). Operations are mocked at the boundary via
``unittest.mock.patch("backlog_core.operations.<function_name>")``.

Each tool is tested to verify:
- Successful operation returns a dict with expected keys (not raises).
- BacklogError propagation returns a dict with an "error" key.
- No-op / shape contracts for specific tool behaviours.

No @pytest.mark.asyncio decorators — asyncio_mode = "auto" is set globally.
All imports are at module level.
"""

from __future__ import annotations

from unittest.mock import patch

from backlog_core.models import BacklogError
from backlog_core.server import mcp

from tests.helpers import call_mcp_tool

# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


async def _call(tool_name: str, params: dict | None = None) -> dict:
    """Call an MCP tool through the in-memory FastMCP transport and parse result.

    Delegates to tests.helpers.call_mcp_tool bound to this module's mcp server.
    """
    return await call_mcp_tool(mcp, tool_name, params)


# ---------------------------------------------------------------------------
# backlog_create_sam_task
# ---------------------------------------------------------------------------

_MINIMAL_CREATE_PARAMS: dict = {
    "parent_issue_number": 480,
    "task_id": "T1",
    "feature": "my-feature",
    "task_type": "implement",
    "agent": "python3-development:python-cli-architect",
    "priority": 2,
}


async def test_backlog_create_sam_task_returns_dict() -> None:
    """backlog_create_sam_task returns a dict (not raises) on success.

    Tests: backlog_create_sam_task MCP tool
    How: Mock operations.create_sam_task to return a success payload.
         Call the tool via in-memory FastMCP Client.
         Assert the response is a dict with the expected keys.
    Why: Verifies the tool wraps operations correctly and merges Output messages
         into the returned dict without raising on the caller side.
    """
    # Arrange
    op_result = {
        "issue_number": 99,
        "title": "[my-feature/T1] implement: build the thing",
        "url": "https://github.com/org/repo/issues/99",
        "messages": [],
        "warnings": [],
        "errors": [],
    }

    # Act
    with patch("backlog_core.operations.create_sam_task", return_value=op_result) as mock_op:
        response = await _call("backlog_create_sam_task", _MINIMAL_CREATE_PARAMS)

    # Assert
    mock_op.assert_called_once()
    assert isinstance(response, dict)
    assert response["issue_number"] == 99
    assert "title" in response
    assert "url" in response
    assert "messages" in response
    assert "warnings" in response
    assert "errors" in response


async def test_backlog_create_sam_task_error_key() -> None:
    """backlog_create_sam_task returns {"error": "..."} when BacklogError is raised.

    Tests: backlog_create_sam_task MCP tool error handling
    How: Mock operations.create_sam_task to raise BacklogError("test error").
         Call the tool via in-memory FastMCP Client.
         Assert the response dict contains the "error" key with the error message.
    Why: The tool must never re-raise BacklogError to the MCP client — it must
         convert it to a structured error response so the caller can inspect it.
    """
    # Arrange / Act
    with patch("backlog_core.operations.create_sam_task", side_effect=BacklogError("test error")):
        response = await _call("backlog_create_sam_task", _MINIMAL_CREATE_PARAMS)

    # Assert
    assert "error" in response
    assert response["error"] == "test error"


# ---------------------------------------------------------------------------
# backlog_get_sam_tasks
# ---------------------------------------------------------------------------


async def test_backlog_get_sam_tasks_shape() -> None:
    """backlog_get_sam_tasks returns {"tasks": [...], "count": N} shape on success.

    Tests: backlog_get_sam_tasks MCP tool
    How: Mock operations.get_sam_tasks to return a known task list.
         Call the tool via in-memory FastMCP Client.
         Assert the response shape matches the documented contract.
    Why: Downstream callers (implementation_manager.py) parse "tasks" and "count";
         a shape regression would silently break the GitHub-backed query path.
    """
    # Arrange
    task_dict = {
        "task_id": "T1",
        "feature": "my-feature",
        "status": "not-started",
        "agent": "some-agent",
        "priority": 2,
        "issue_number": 99,
    }
    op_result = {
        "tasks": [task_dict],
        "count": 1,
        "parent_issue_number": 480,
        "messages": [],
        "warnings": [],
        "errors": [],
    }

    # Act
    with patch("backlog_core.operations.get_sam_tasks", return_value=op_result):
        response = await _call("backlog_get_sam_tasks", {"parent_issue_number": 480})

    # Assert
    assert "tasks" in response
    assert "count" in response
    assert isinstance(response["tasks"], list)
    assert response["count"] == 1
    assert response["tasks"][0]["task_id"] == "T1"


# ---------------------------------------------------------------------------
# backlog_update_sam_task_status
# ---------------------------------------------------------------------------


async def test_backlog_update_sam_task_status_no_op() -> None:
    """backlog_update_sam_task_status returns {"updated": False} when status unchanged.

    Tests: backlog_update_sam_task_status MCP tool no-op path
    How: Mock operations.update_sam_task_status to return {"updated": False, ...}.
         Call the tool via in-memory FastMCP Client.
         Assert response["updated"] is False.
    Why: The tool must faithfully relay the no-op indicator so callers know
         no GitHub write occurred (avoids spurious change detection).
    """
    # Arrange
    op_result = {
        "updated": False,
        "issue_number": 1,
        "new_status": "complete",
        "messages": [],
        "warnings": [],
        "errors": [],
    }

    # Act
    with patch("backlog_core.operations.update_sam_task_status", return_value=op_result):
        response = await _call("backlog_update_sam_task_status", {"issue_number": 1, "new_status": "complete"})

    # Assert
    assert "updated" in response
    assert response["updated"] is False


# ---------------------------------------------------------------------------
# backlog_get_ready_sam_tasks
# ---------------------------------------------------------------------------


async def test_backlog_get_ready_sam_tasks_shape() -> None:
    """backlog_get_ready_sam_tasks returns shape with "feature", "ready_tasks", "count".

    Tests: backlog_get_ready_sam_tasks MCP tool
    How: Mock operations.get_ready_sam_tasks to return a known ready-tasks payload.
         Call the tool via in-memory FastMCP Client.
         Assert the response contains the three required top-level keys.
    Why: This output shape is documented to match implementation_manager.py
         ready-tasks JSON so orchestrators can use either source interchangeably.
         A missing key would silently break skill loading for sub-agents.
    """
    # Arrange
    op_result = {
        "feature": "my-feature",
        "ready_tasks": [
            {"id": "T1", "name": "Build the thing", "agent": "some-agent", "skills": [], "issue_number": 99}
        ],
        "count": 1,
        "messages": [],
        "warnings": [],
        "errors": [],
    }

    # Act
    with patch("backlog_core.operations.get_ready_sam_tasks", return_value=op_result):
        response = await _call("backlog_get_ready_sam_tasks", {"parent_issue_number": 480})

    # Assert
    assert "feature" in response
    assert "ready_tasks" in response
    assert "count" in response
    assert isinstance(response["ready_tasks"], list)
    assert response["feature"] == "my-feature"
    assert response["count"] == 1
