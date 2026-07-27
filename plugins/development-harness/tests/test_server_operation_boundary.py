"""Pin the MCP mock boundary: server.operations must be dh_core.operations.

Regression guard: if a future refactor repoints ``backlog_core.server`` at a
different operations module, every MCP wrapper test that patches
``dh_core.operations.<fn>`` would silently miss. This test fails loudly first.

Also smoke-tests that patching ``dh_core.operations.list_labels`` is the target
the ``backlog_list_labels`` MCP tool actually dereferences — proving the mock
boundary is correct without making a real network call.
"""

from __future__ import annotations

from unittest.mock import patch

from backlog_core import operations as legacy_operations, server
from dh_core import operations as unified_operations

from tests.helpers import call_mcp_tool


def test_server_uses_unified_operations_module() -> None:
    """server.operations is dh_core.operations, not backlog_core.operations."""
    assert server.operations is unified_operations
    assert server.operations is not legacy_operations


async def test_server_mcp_mock_target_is_dh_core() -> None:
    """Patching dh_core.operations.list_labels intercepts the backlog_list_labels tool."""
    expected = {"labels": [], "count": 0, "messages": [], "warnings": []}
    with patch("dh_core.operations.list_labels", return_value=expected) as mocked:
        result = await call_mcp_tool(server.mcp, "backlog_list_labels", {"limit": 5})
    mocked.assert_called_once()
    assert result["count"] == 0
