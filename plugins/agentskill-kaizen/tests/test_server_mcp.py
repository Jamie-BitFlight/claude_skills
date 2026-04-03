"""In-memory MCP protocol tests for ``mcp/server.py``.

Exercises the real FastMCP in-memory transport — the same protocol path MCP
clients use. Verifies tool/resource registration, dispatch, and serialization.

Uses ``Client(mcp)`` per FastMCP v3 testing guidance. ``asyncio_mode = "auto"`` is
set in ``pyproject.toml`` — no ``@pytest.mark.asyncio`` needed.
"""

from __future__ import annotations

from fastmcp.client import Client
from server import mcp


async def test_mcp_server_lists_expected_tools() -> None:
    """Server exposes the eight analysis tools plus open_dashboard via MCP."""
    async with Client(mcp) as client:
        tools = await client.list_tools()

    names = {t.name for t in tools}
    assert names == {
        "get_transcript_jsonl_schema",
        "extract_tool_sequences",
        "discover_process_model",
        "check_conformance",
        "find_frequent_patterns",
        "detect_frustration_signals",
        "cluster_sessions",
        "open_dashboard",
    }


async def test_mcp_get_transcript_jsonl_schema_returns_markdown() -> None:
    """get_transcript_jsonl_schema returns schema markdown through the protocol."""
    async with Client(mcp) as client:
        result = await client.call_tool("get_transcript_jsonl_schema", {})

    data = result.data
    assert isinstance(data, str)
    assert "Claude Code Session Log Schema Reference" in data
    assert '## `type: "assistant"` Records' in data


async def test_mcp_read_resource_matches_get_transcript_tool() -> None:
    """Resource ``kaizen://session-log/schema`` matches the tool output."""
    async with Client(mcp) as client:
        tool_result = await client.call_tool("get_transcript_jsonl_schema", {})
        contents = await client.read_resource("kaizen://session-log/schema")

    assert isinstance(tool_result.data, str)
    assert len(contents) == 1
    resource_text = contents[0].text
    assert isinstance(resource_text, str)
    assert resource_text == tool_result.data
