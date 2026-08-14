"""Tests for tests/helpers.py's own timeout-handling logic.

This is test infrastructure, but call_mcp_tool has real timeout logic
worth its own regression coverage -- see the init_timeout gap this file
tests for.
"""

from __future__ import annotations

import asyncio

import pytest
from fastmcp import FastMCP
from mcp import ClientSession

from tests.helpers import call_mcp_tool

_SAFETY_NET_SECONDS = 5.0


async def test_call_mcp_tool_bounds_a_stalled_initialization_handshake(monkeypatch: pytest.MonkeyPatch) -> None:
    """A stalled MCP initialization handshake must fail within timeout_seconds.

    Regression test for the gap where call_mcp_tool passed timeout (the
    per-request read timeout) but not init_timeout (a separate FastMCP
    Client parameter defaulting to disabled) -- a server that stalls
    during the initialize() handshake, before any tool call even starts,
    would hang forever despite the documented timeout bound.

    The whole test is wrapped in a hard wall-clock safety net well above
    the configured timeout, so if the fix regresses this test fails
    loudly instead of hanging the suite.
    """

    async def _hang_forever(self: ClientSession, *args: object, **kwargs: object) -> None:
        await asyncio.sleep(999)

    monkeypatch.setattr(ClientSession, "initialize", _hang_forever)

    mcp = FastMCP("stall-test")

    with pytest.raises(RuntimeError, match="Failed to initialize"):
        await asyncio.wait_for(call_mcp_tool(mcp, "nonexistent_tool", timeout_seconds=1.0), timeout=_SAFETY_NET_SECONDS)
