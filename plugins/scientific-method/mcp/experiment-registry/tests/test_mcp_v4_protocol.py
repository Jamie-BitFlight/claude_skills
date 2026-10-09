"""FastMCP v4 protocol metadata regression tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from fastmcp import Client

_SERVER_PATH = Path(__file__).parent.parent / "server.py"
_spec = importlib.util.spec_from_file_location("experiment_registry_server", _SERVER_PATH)
assert _spec is not None
assert _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


async def test_mcp_protocol_preserves_public_tool_annotations() -> None:
    async with Client(_module.mcp) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}

    readonly_tools = {
        "list_experiment_types",
        "inspect_experiment_type",
        "get_current_step",
        "list_experiments",
        "resume_experiment",
        "get_experiment_summary",
    }
    write_tools = {"start_experiment", "complete_step"}

    assert set(tools) == readonly_tools | write_tools
    assert all(tools[name].annotations.read_only_hint is True for name in readonly_tools)
    assert all(tools[name].annotations is None for name in write_tools)
