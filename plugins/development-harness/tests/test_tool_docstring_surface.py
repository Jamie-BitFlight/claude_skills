"""Holds every MCP tool description to the surface a consumer can touch (R7).

A tool description is loaded in full on every session that connects to the server,
before the agent has asked for anything. It is the most expensive prose this plugin
ships, so it carries only what the advertised ``outputSchema`` cannot: what the tool
does, and which parameter controls it.

Two things it must not carry. A ``Returns:``, ``Raises:`` or ``Args:`` section
restates the schema FastMCP already derives from the same annotations -- see
``backlog_core/tool_responses.py`` for why that annotation exists. And a class name, a
module path, a source filename or an issue number names something the consumer cannot
reach: it reads this plugin's tools, not its repository.

The set of names a description *may* use is derived from the repository rather than
listed here, so it cannot go stale: skill and agent names from their directories, CLI
commands and flags from the Typer decorators, and tool names plus every field and enum value
of every advertised schema from the live servers. A description is read the way a consumer
receives it -- ``list_tools()`` output, not the source docstring -- which is also how
tools mounted from a submodule get checked at all. FastMCP drops a Google-style section
before advertising, so the section assertion below now guards against that changing rather
than against a section reaching a consumer today.
"""

from __future__ import annotations

import ast
import asyncio
import re
from pathlib import Path

import pytest
from backlog_core.server import mcp as backlog_mcp
from fastmcp.tools import Tool
from pydantic import JsonValue, TypeAdapter
from sam_schema.server import mcp as sam_mcp

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_SERVERS = (("backlog_core/server.py", backlog_mcp), ("sam_schema/server.py", sam_mcp))

_SECTION = re.compile(r"^\s*(Returns|Raises|Args|Attributes|Yields):\s*$", re.MULTILINE)
_BEHIND_THE_SURFACE = (
    (re.compile(r":class:|:func:|:mod:"), "a Sphinx cross-reference to a private symbol"),
    (re.compile(r"\b(?:backlog_core|sam_schema|dh_core)\.[A-Za-z_]"), "an internal module path"),
    (re.compile(r"\b[A-Za-z_]+\.py\b"), "a source filename"),
    (re.compile(r"#\d{3,}"), "an issue number from this repository's tracker"),
)

# A value rendered into the text at runtime is a value, not a symbol: ``{plan_id}`` reaches
# the consumer as the id itself.
PLACEHOLDER = re.compile(r"\{[^{}]*\}")
# Two shapes carry a symbol name that plain English does not: an underscore, and a second
# capital hump. One hump is not enough -- ``Check`` opens a sentence and also names a class.
IDENTIFIER_SHAPED = re.compile(r"[A-Za-z0-9]+_[A-Za-z0-9_]+|[A-Z][a-z]+[A-Z][A-Za-z0-9]*")

# Names that originate outside this repository, so no walk of it can enumerate them: an
# environment variable GitHub defines, GitHub's Projects V2 API, and the GraphQL query
# language. Each is something the consumer sets or talks to directly.
EXTERNAL_NAMES = frozenset({"github_token", "projectv2", "graphql"})
JSON_VALUE_ADAPTER = TypeAdapter(JsonValue)


def collect_consumer_surface(live_tools: list[tuple[str, Tool]]) -> dict[str, set[str]]:
    """Read every consumer-visible name from its defining repository surface.

    Args:
        live_tools: Source-module and live-tool pairs from both MCP servers.

    Returns:
        Consumer-visible names grouped by their declaring surface.
    """
    commands: set[str] = set()
    flags: set[str] = set()
    for module in (_PLUGIN_ROOT / "sam_schema").glob("*.py"):
        for node in ast.walk(ast.parse(module.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for decorator in node.decorator_list:
                if not (isinstance(decorator, ast.Call) and getattr(decorator.func, "attr", None) == "command"):
                    continue
                explicit_names = {
                    value.value
                    for value in [
                        *decorator.args,
                        *(keyword.value for keyword in decorator.keywords if keyword.arg == "name"),
                    ]
                    if isinstance(value, ast.Constant) and isinstance(value.value, str)
                }
                commands.update(explicit_names or {node.name.replace("_", "-")})
                for argument in [*node.args.args, *node.args.kwonlyargs]:
                    explicit_flags = {
                        sub.value.lstrip("-")
                        for sub in (ast.walk(argument.annotation) if argument.annotation else ())
                        if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and sub.value.startswith("-")
                    }
                    flags.update(explicit_flags or {argument.arg.replace("_", "-")})

    tools: set[str] = set()
    schema_terms: set[str] = set()
    for _, tool in live_tools:
        tools.add(tool.name)
        collect_schema_terms(JSON_VALUE_ADAPTER.validate_python(tool.parameters), schema_terms)
        collect_schema_terms(JSON_VALUE_ADAPTER.validate_python(tool.output_schema), schema_terms)

    return {
        "skills": {p.name for p in (_PLUGIN_ROOT / "skills").iterdir() if p.is_dir()},
        "agents": {p.stem for p in (_PLUGIN_ROOT / "agents").glob("*.md")},
        "cli commands": commands,
        "cli flags": flags,
        "tool names": tools,
        "schema fields and values": schema_terms,
    }


def collect_schema_terms(node: JsonValue, into: set[str]) -> None:
    """Collect every nested JSON Schema property name and constrained string value.

    Args:
        node: Validated JSON Schema value to traverse.
        into: Set receiving discovered property names and constrained values.
    """
    if isinstance(node, dict):
        if isinstance(properties := node.get("properties"), dict):
            into.update(properties)
        if isinstance(enum := node.get("enum"), list):
            into.update(value for value in enum if isinstance(value, str))
        if isinstance(const := node.get("const"), str):
            into.add(const)
        for value in node.values():
            collect_schema_terms(value, into)
    elif isinstance(node, list):
        for value in node:
            collect_schema_terms(value, into)


def test_explicit_typer_command_excludes_implementation_function_name() -> None:
    """An explicit Typer name, not its Python function name, is consumer-visible."""
    commands = CONSUMER_SURFACE["cli commands"]

    assert "get" in commands
    assert "active_task_get" not in commands


LIVE_TOOLS = [(relative, tool) for relative, server in _SERVERS for tool in asyncio.run(server.list_tools())]

CONSUMER_SURFACE = collect_consumer_surface(LIVE_TOOLS)

VOCABULARY = set(EXTERNAL_NAMES)
for names in CONSUMER_SURFACE.values():
    for name in names:
        VOCABULARY.add(name.lower())
        VOCABULARY.update(word.lower() for word in re.split(r"[-_.]", name) if word)

DESCRIPTIONS = [(relative, tool.name, tool.description or "") for relative, tool in LIVE_TOOLS]
assert len(DESCRIPTIONS) >= 48, f"expected the full tool surface, found {len(DESCRIPTIONS)}"


@pytest.mark.parametrize(("relative", "tool", "doc"), DESCRIPTIONS, ids=[f"{r}::{t}" for r, t, _ in DESCRIPTIONS])
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
    unknown = sorted({
        token for token in IDENTIFIER_SHAPED.findall(PLACEHOLDER.sub(" ", doc)) if token.lower() not in VOCABULARY
    })
    assert not unknown, (
        f"{relative}::{tool} names {unknown}, which is neither ordinary English nor any skill, agent, CLI "
        f"command, CLI flag, tool name, or advertised schema term this repository defines. Say it in terms "
        f"of this tool and its parameters, keeping whatever the sentence was telling the consumer."
    )
