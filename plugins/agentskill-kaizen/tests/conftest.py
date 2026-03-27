"""Shared pytest fixtures for agentskill-kaizen MCP server tests.

Provides reusable test fixtures for:
- Sample JSONL transcript files on disk
- Pre-extracted tool sequence dicts
- Frustration-signal test data
- FastMCP Context mock factory
"""

from __future__ import annotations

import json
import sys
import types as _types
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

import pytest
from fastmcp.exceptions import ToolError as _ToolError

if TYPE_CHECKING:
    from collections.abc import Callable

# ---------------------------------------------------------------------------
# Module import -- server.py uses ``from __future__ import annotations``
# which defers annotation evaluation.  FastMCP 3.x's ``@mcp.tool``
# decorator triggers Pydantic TypeAdapter resolution at decoration time,
# which fails on Python 3.11 because ``typing._eval_type`` cannot
# resolve the deferred ``Annotated[...]`` hints.
#
# Workaround: Replace FastMCP with a stub that makes ``@mcp.tool`` a
# transparent passthrough, then import the module.  The actual async tool
# functions are plain coroutines -- the decorator only adds MCP metadata.
# ---------------------------------------------------------------------------


class _StubMCP:
    """Minimal FastMCP stand-in that makes @mcp.tool a no-op decorator."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def tool(self, *args: object, **kwargs: object) -> Callable[..., object]:
        """Return a no-op decorator (or decorate the function directly)."""

        def decorator(fn: object) -> object:
            return fn

        if args and callable(args[0]):
            return args[0]
        return decorator

    def run(self) -> None:
        """No-op run for stub."""


# Temporarily replace the fastmcp module so server.py's
# ``from fastmcp import Context, FastMCP`` finds our stub.
_real_fastmcp = sys.modules.get("fastmcp")
_real_fastmcp_exc = sys.modules.get("fastmcp.exceptions")

_stub_fastmcp = _types.ModuleType("fastmcp")
vars(_stub_fastmcp).update({"FastMCP": _StubMCP, "Context": AsyncMock})

_stub_exceptions = _types.ModuleType("fastmcp.exceptions")
vars(_stub_exceptions).update({"ToolError": _ToolError})

sys.modules["fastmcp"] = _stub_fastmcp
sys.modules["fastmcp.exceptions"] = _stub_exceptions

_MCP_DIR = str(Path(__file__).resolve().parent.parent / "mcp")
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

import server as kaizen_server

__all__ = ["kaizen_server"]

# Restore real fastmcp so other test infrastructure works
if _real_fastmcp is not None:
    sys.modules["fastmcp"] = _real_fastmcp
if _real_fastmcp_exc is not None:
    sys.modules["fastmcp.exceptions"] = _real_fastmcp_exc


# ---------------------------------------------------------------------------
# JSONL transcript record builders
# ---------------------------------------------------------------------------


def _make_assistant_tool_use(tool_name: str) -> dict[str, Any]:
    """Build a minimal assistant record containing a single tool_use block."""
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": tool_name, "input": {}}]}}


def _make_user_message(text: str, *, timestamp: str = "") -> dict[str, Any]:
    """Build a minimal user record with string content."""
    record: dict[str, Any] = {"type": "user", "message": {"content": text}}
    if timestamp:
        record["timestamp"] = timestamp
    return record


def _make_user_message_blocks(blocks: list[dict[str, str]], *, timestamp: str = "") -> dict[str, Any]:
    """Build a user record with list-of-blocks content."""
    record: dict[str, Any] = {"type": "user", "message": {"content": blocks}}
    if timestamp:
        record["timestamp"] = timestamp
    return record


# ---------------------------------------------------------------------------
# Fixtures -- JSONL files on disk
# ---------------------------------------------------------------------------


@pytest.fixture
def jsonl_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for JSONL transcript files.

    Returns:
        Path to the temporary directory.
    """
    return tmp_path / "transcripts"


@pytest.fixture
def single_session_jsonl(jsonl_dir: Path) -> Path:
    """Write a single-session JSONL file with known tool calls.

    The session contains three tool-use blocks: Read, Grep, Write.

    Returns:
        Path to the directory containing the JSONL file.
    """
    jsonl_dir.mkdir(parents=True, exist_ok=True)
    records = [_make_assistant_tool_use("Read"), _make_assistant_tool_use("Grep"), _make_assistant_tool_use("Write")]
    session_file = jsonl_dir / "session-abc.jsonl"
    session_file.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return jsonl_dir


@pytest.fixture
def multi_session_jsonl(jsonl_dir: Path) -> Path:
    """Write three session JSONL files with varied tool calls.

    Sessions:
        session-one:   Read, Grep, Read
        session-two:   Write, Edit
        session-three: Read, Grep, Write, Edit

    Returns:
        Path to the directory containing the JSONL files.
    """
    jsonl_dir.mkdir(parents=True, exist_ok=True)

    sessions: dict[str, list[str]] = {
        "session-one": ["Read", "Grep", "Read"],
        "session-two": ["Write", "Edit"],
        "session-three": ["Read", "Grep", "Write", "Edit"],
    }
    for name, tools in sessions.items():
        records = [_make_assistant_tool_use(t) for t in tools]
        fpath = jsonl_dir / f"{name}.jsonl"
        fpath.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return jsonl_dir


@pytest.fixture
def frustration_jsonl(jsonl_dir: Path) -> Path:
    """Write JSONL files containing user messages with frustration signals.

    Returns:
        Path to the directory containing the JSONL files.
    """
    jsonl_dir.mkdir(parents=True, exist_ok=True)

    records = [
        _make_user_message("no, that's wrong", timestamp="2026-01-01T00:00:00Z"),
        _make_user_message("looks good to me", timestamp="2026-01-01T00:01:00Z"),
        _make_user_message("wait, hold on a second", timestamp="2026-01-01T00:02:00Z"),
        _make_user_message("why did you do that again?", timestamp="2026-01-01T00:03:00Z"),
        # toolUseResult records should be skipped
        {
            "type": "user",
            "toolUseResult": True,
            "message": {"content": "no this is wrong"},
            "timestamp": "2026-01-01T00:04:00Z",
        },
        # assistant record should be skipped
        _make_assistant_tool_use("Read"),
    ]
    fpath = jsonl_dir / "frustration-session.jsonl"
    fpath.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return jsonl_dir


@pytest.fixture
def empty_jsonl_dir(jsonl_dir: Path) -> Path:
    """Create an empty directory with no JSONL files.

    Returns:
        Path to the empty directory.
    """
    jsonl_dir.mkdir(parents=True, exist_ok=True)
    return jsonl_dir


@pytest.fixture
def malformed_jsonl(jsonl_dir: Path) -> Path:
    """Write a JSONL file with a mix of valid and malformed lines.

    Line 1: valid assistant tool-use record
    Line 2: not valid JSON
    Line 3: blank line (should be skipped)
    Line 4: valid assistant tool-use record

    Returns:
        Path to the directory containing the JSONL file.
    """
    jsonl_dir.mkdir(parents=True, exist_ok=True)
    content = (
        json.dumps(_make_assistant_tool_use("Read"))
        + "\n{not valid json\n\n"
        + json.dumps(_make_assistant_tool_use("Write"))
    )
    fpath = jsonl_dir / "malformed-session.jsonl"
    fpath.write_text(content, encoding="utf-8")
    return jsonl_dir


# ---------------------------------------------------------------------------
# Fixtures -- pre-extracted sequences
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_sequences() -> dict[str, list[str]]:
    """Provide pre-extracted tool sequences for three sessions.

    Returns:
        Dict mapping session IDs to ordered tool-name lists.
    """
    return {
        "session-one": ["Read", "Grep", "Read"],
        "session-two": ["Write", "Edit"],
        "session-three": ["Read", "Grep", "Write", "Edit"],
    }


@pytest.fixture
def single_sequence() -> dict[str, list[str]]:
    """Provide a single-session pre-extracted sequence.

    Returns:
        Dict with one session mapping.
    """
    return {"only-session": ["Read", "Grep", "Write"]}


# ---------------------------------------------------------------------------
# Fixtures -- FastMCP Context mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_context() -> AsyncMock:
    """Provide a mock FastMCP Context with async info/warning methods.

    Returns:
        AsyncMock standing in for fastmcp.Context.
    """
    ctx = AsyncMock()
    ctx.info = AsyncMock()
    ctx.warning = AsyncMock()
    return ctx
