"""Shared test helper functions for development-harness test suites.

Centralises helpers used across multiple test files to eliminate copy-paste
duplication. Both ``tests/`` and ``tests_backlog/`` import from here via
``from tests.helpers import ...`` — enabled by the ``pythonpath = ["."]``
pytest configuration in pyproject.toml.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

if TYPE_CHECKING:
    from pathlib import Path

    from fastmcp import FastMCP


async def call_mcp_tool(mcp: FastMCP, tool_name: str, params: dict | None = None) -> dict:
    """Call a tool through the in-memory FastMCP transport and parse the result.

    Args:
        mcp: The FastMCP server instance to connect to.
        tool_name: Registered MCP tool name (e.g. ``"backlog_list"``).
        params: Optional parameter dict to pass to the tool.

    Returns:
        Parsed JSON response dict from the tool.

    Why: Ensures MCP tool wrappers behave correctly end-to-end without HTTP.
    Opens a Client connected to the mcp server, calls tool, parses JSON.
    """
    from fastmcp.client import Client

    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, params or {})
    return json.loads(result.content[0].text)


def make_dh_paths_mock(project_root: Path, user_dh_root: Path | None = None) -> MagicMock:
    """Return a MagicMock that satisfies dh_paths usage in backend and config tests.

    Args:
        project_root: The fake project root path to return from git_project_root().
        user_dh_root: Optional fixed user DH root path. When omitted, _dh_user_root()
            uses a side_effect that resolves Path.home() at call time, so tests can
            monkeypatch HOME before calling the mock.

    Returns:
        A MagicMock with git_project_root, _dh_user_root, and project_dh_dir configured.

    Why: Isolates dh_paths filesystem lookups so tests don't depend on real
    project structure or home directory layout. The deferred Path.home() resolution
    (when user_dh_root is None) lets monkeypatching HOME take effect correctly.
    """
    from pathlib import Path as _Path

    mock = MagicMock()
    mock.git_project_root.return_value = project_root
    if user_dh_root is not None:
        mock._dh_user_root.return_value = user_dh_root
    else:
        mock._dh_user_root.side_effect = lambda: _Path.home() / ".dh"
    mock.project_dh_dir.return_value = project_root / ".dh"
    return mock
