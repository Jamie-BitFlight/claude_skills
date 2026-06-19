"""AST-based regression test: every beads-capable selector Field description mentions a beads nanoid.

Parses backlog_core/server.py with `ast` — does NOT import the module (which would spawn
MCP machinery).  Walks the AST to locate the `selector` parameter's Field(description=...)
string for each of the seven beads-capable tools and asserts:

1. The description contains 'beads nanoid'.
2. The description is NOT a bare generic string that omits the nanoid clause.
3. Extraction targets only the selector parameter of the named tool — the test cannot
   be satisfied by the pre-existing 'beads nanoid' text on artifact item_id params or
   by a whole-file substring search.

Each tool is an independent parametrized case so failures name the offending tool.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SERVER_PY = Path(__file__).parent.parent / "backlog_core" / "server.py"

BEADS_CAPABLE_TOOLS: list[str] = [
    "backlog_close",
    "backlog_groom",
    "backlog_pull",
    "backlog_resolve",
    "backlog_strike_entry",
    "backlog_update",
    "backlog_view",
]

# Bare generic strings that must NOT appear as the full selector description.
# If a selector description equals one of these, the beads nanoid was stripped.
_BARE_GENERIC_DESCRIPTIONS: frozenset[str] = frozenset({
    "Item selector: GitHub issue URL, #N, bare number, or title substring",
    "Item selector",
    "selector",
})


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _extract_selector_descriptions(source: str) -> dict[str, str]:
    """Walk the AST of *source* and return {tool_name: selector_field_description}.

    Raises AssertionError when a tool is found but its selector annotation does
    not match the expected ``Annotated[str, Field(description=...)]`` shape —
    so a structural refactor fails loudly with the tool name rather than
    silently returning a missing key.
    """
    tree = ast.parse(source)
    results: dict[str, str] = {}
    tools_remaining = set(BEADS_CAPABLE_TOOLS)

    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        if node.name not in tools_remaining:
            continue
        tools_remaining.discard(node.name)

        selector_desc: str | None = None
        for arg in node.args.args:
            if arg.arg != "selector":
                continue
            ann = arg.annotation
            assert isinstance(ann, ast.Subscript), (
                f"{node.name}: selector annotation is not Annotated[...] (got {type(ann).__name__})"
            )
            slice_node = ann.slice
            assert isinstance(slice_node, ast.Tuple), (
                f"{node.name}: Annotated slice is not a Tuple (got {type(slice_node).__name__})"
            )
            assert len(slice_node.elts) >= 2, (
                f"{node.name}: Annotated Tuple has fewer than 2 elements (got {len(slice_node.elts)})"
            )
            field_call = slice_node.elts[1]
            assert isinstance(field_call, ast.Call), (
                f"{node.name}: second Annotated element is not a Call (got {type(field_call).__name__})"
            )
            for kw in field_call.keywords:
                if kw.arg == "description":
                    assert isinstance(kw.value, ast.Constant), (
                        f"{node.name}: selector Field description is not a string constant "
                        f"(got {type(kw.value).__name__})"
                    )
                    selector_desc = kw.value.value
                    break
            assert selector_desc is not None, f"{node.name}: selector Field has no description= keyword"
            break

        assert selector_desc is not None, f"{node.name}: no 'selector' parameter found in function signature"
        results[node.name] = selector_desc

    return results


# Module-level parse — done once, shared across parametrized cases.
_SOURCE = SERVER_PY.read_text(encoding="utf-8")
_SELECTOR_DESCRIPTIONS: dict[str, str] = _extract_selector_descriptions(_SOURCE)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool_name", BEADS_CAPABLE_TOOLS)
def test_selector_description_mentions_beads_nanoid(tool_name: str) -> None:
    """Each beads-capable tool's selector Field description must contain 'beads nanoid'."""
    assert tool_name in _SELECTOR_DESCRIPTIONS, (
        f"Tool '{tool_name}' was not found in server.py or its selector parameter "
        "could not be extracted via AST. Check that the function exists and its selector "
        "annotation follows Annotated[str, Field(description=...)]."
    )
    desc = _SELECTOR_DESCRIPTIONS[tool_name]
    assert "beads nanoid" in desc, (
        f"Tool '{tool_name}' selector Field description does not mention 'beads nanoid'.\n"
        f"  Actual description: {desc!r}\n"
        "  Fix: add 'or beads nanoid (e.g. bd-a3f8)' to the selector Field description "
        f"in backlog_core/server.py for {tool_name}()."
    )


@pytest.mark.parametrize("tool_name", BEADS_CAPABLE_TOOLS)
def test_selector_description_not_bare_generic(tool_name: str) -> None:
    """Each beads-capable tool's selector description must not be a bare generic string.

    Guards against reversion to a description that omits the beads nanoid clause.
    """
    assert tool_name in _SELECTOR_DESCRIPTIONS, f"Tool '{tool_name}' was not found in server.py."
    desc = _SELECTOR_DESCRIPTIONS[tool_name]
    assert desc not in _BARE_GENERIC_DESCRIPTIONS, (
        f"Tool '{tool_name}' selector Field description reverted to a bare generic string "
        f"that omits the beads nanoid clause.\n"
        f"  Actual description: {desc!r}\n"
        "  Fix: restore 'or beads nanoid (e.g. bd-a3f8)' in the selector Field "
        f"description for {tool_name}() in backlog_core/server.py."
    )
