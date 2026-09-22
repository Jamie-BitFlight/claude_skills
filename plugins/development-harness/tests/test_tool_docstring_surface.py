"""Holds every MCP tool description to the surface a consumer can touch (R7).

A tool description is loaded in full on every session that connects to the server,
before the agent has asked for anything. It is the most expensive prose this plugin
ships, so it carries only what the advertised ``outputSchema`` cannot: what the tool
does, and which parameter controls it.

Two things it must not carry. A ``Returns:``, ``Raises:`` or ``Args:`` section
restates the schema FastMCP already derives from the same annotations -- see
``backlog_core/tool_responses.py`` for why that annotation exists. And a module path,
a class name, a source filename or an issue number names something the consumer
cannot reach: it reads this plugin's tools, not its repository.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_SERVERS = ("backlog_core/server.py", "sam_schema/server.py")

_SECTION = re.compile(r"^\s*(Returns|Raises|Args|Attributes|Yields):\s*$", re.MULTILINE)
_BEHIND_THE_SURFACE = (
    (re.compile(r":class:|:func:|:mod:"), "a Sphinx cross-reference to a private symbol"),
    (re.compile(r"\b(?:backlog_core|sam_schema|dh_core)\.[A-Za-z_]"), "an internal module path"),
    (re.compile(r"\b[A-Za-z_]+\.py\b"), "a source filename"),
    (re.compile(r"#\d{3,}"), "an issue number from this repository's tracker"),
)


def _tool_docstrings() -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    for relative in _SERVERS:
        tree = ast.parse((_PLUGIN_ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if not any("mcp.tool" in ast.unparse(d) for d in node.decorator_list):
                continue
            found.append((relative, node.name, ast.get_docstring(node, clean=False) or ""))
    assert len(found) >= 48, f"expected the full tool surface, found {len(found)}"
    return found


@pytest.mark.parametrize(("relative", "tool", "doc"), _tool_docstrings(), ids=lambda v: v if isinstance(v, str) else "")
def test_tool_description_stays_on_the_consumer_surface(relative: str, tool: str, doc: str) -> None:
    section = _SECTION.search(doc)
    assert section is None, (
        f"{relative}::{tool} has a {section.group(1)}: section. The advertised outputSchema already "
        f"carries the field names and types; state what the tool does and which parameter controls it, "
        f"and keep only the behaviour the schema cannot express."
    )
    for pattern, what in _BEHIND_THE_SURFACE:
        hit = pattern.search(doc)
        assert hit is None, (
            f"{relative}::{tool} names {what} ({hit.group(0)!r}). A consumer reaches this plugin through "
            f"tool names, tool parameters, CLI commands, skills and agents -- name one of those instead."
        )
