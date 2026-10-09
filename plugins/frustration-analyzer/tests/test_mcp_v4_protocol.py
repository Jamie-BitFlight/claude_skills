"""FastMCP v4 protocol metadata regression tests."""

from __future__ import annotations

from _server import _module
from fastmcp import Client


async def test_mcp_protocol_preserves_public_tool_annotations() -> None:
    async with Client(_module.mcp) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}

    readonly_tools = {"list_sessions", "get_context_window", "scan_transcripts", "get_scenario", "generate_social_post"}
    write_tools = {"extract_user_messages", "render_rage_receipt"}

    assert set(tools) == readonly_tools | write_tools
    assert all(tools[name].annotations is not None for name in tools)
    assert all(
        (
            tools[name].annotations.read_only_hint,
            tools[name].annotations.destructive_hint,
            tools[name].annotations.idempotent_hint,
            tools[name].annotations.open_world_hint,
        )
        == (True, False, True, False)
        for name in readonly_tools
    )
    assert all(
        (
            tools[name].annotations.read_only_hint,
            tools[name].annotations.destructive_hint,
            tools[name].annotations.idempotent_hint,
            tools[name].annotations.open_world_hint,
        )
        == (False, False, True, False)
        for name in write_tools
    )
