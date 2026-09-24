"""Tests for tests/helpers.py's own timeout-handling logic.

This is test infrastructure, but call_mcp_tool has real timeout logic
worth its own regression coverage -- see the init_timeout gap this file
tests for.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Self

import pytest
from fastmcp import FastMCP

from tests.helpers import call_mcp_tool


async def test_call_mcp_tool_has_no_default_tool_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    """The shared helper bounds initialization but leaves ordinary tool calls unbounded."""
    constructor_kwargs: dict[str, object] = {}
    call_kwargs: dict[str, object] = {}

    class RecordingClient:
        def __init__(self, _mcp: FastMCP, **kwargs: object) -> None:
            constructor_kwargs.update(kwargs)

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def call_tool(self, _name: str, _params: dict[str, object], **kwargs: object) -> object:
            call_kwargs.update(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(text=json.dumps({"ok": True}))])

    monkeypatch.setattr("fastmcp.client.Client", RecordingClient)

    result = await call_mcp_tool(FastMCP("timeout-contract"), "probe")

    assert result == {"ok": True}
    assert constructor_kwargs == {"timeout": None, "init_timeout": 30.0}
    assert call_kwargs == {}


async def test_call_mcp_tool_applies_only_an_explicit_tool_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    """An explicit deadline belongs to call_tool, not the reusable client transport."""
    constructor_kwargs: dict[str, object] = {}
    call_kwargs: dict[str, object] = {}

    class RecordingClient:
        def __init__(self, _mcp: FastMCP, **kwargs: object) -> None:
            constructor_kwargs.update(kwargs)

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def call_tool(self, _name: str, _params: dict[str, object], **kwargs: object) -> object:
            call_kwargs.update(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(text=json.dumps({"ok": True}))])

    monkeypatch.setattr("fastmcp.client.Client", RecordingClient)

    await call_mcp_tool(FastMCP("timeout-contract"), "probe", timeout_seconds=1.5)

    assert constructor_kwargs == {"timeout": None, "init_timeout": 30.0}
    assert call_kwargs == {"timeout": 1.5}
