"""FastMCP server exposing agent-profile tools.

Two tools are provided:

- ``profile_load`` — compile a named agent definition into a loadable skill
  bundle (``AgentProfile``).
- ``profile_list`` — enumerate all agent definitions across plugins, optionally
  filtered to a single plugin.

This server is mounted into the backlog_core server with the ``profile_``
namespace prefix, exposing the tools as ``profile_load`` and ``profile_list``
in the backlog MCP namespace. The internal function names use a leading
underscore (``_load``, ``_list``) to avoid shadowing Python builtins; the
``name=`` kwarg on each ``@mcp.tool`` decorator sets the exposed MCP tool name.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from agent_profile.discovery import find_agent, get_plugins_root, scan_all_agents
from agent_profile.models import AgentProfile, ProfileListEntry
from agent_profile.parser import parse_agent_file

logger = logging.getLogger(__name__)

mcp: FastMCP = FastMCP("agent-profile")


@mcp.tool(
    name="load",
    annotations=ToolAnnotations(
        title="Load Agent Profile",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
def _load(
    agent_name: Annotated[
        str,
        Field(
            description=(
                "Agent name in bare form (e.g. 'python-cli-architect') or "
                "plugin-qualified form (e.g. 'python3-development:code-reviewer'). "
                "Subdirectory agents should be plugin-qualified to avoid ambiguity."
            )
        ),
    ],
) -> dict:
    """Compile an agent definition into a loadable profile.

    Finds the agent ``agent_name`` names, reads its frontmatter and instruction
    body, and returns a profile ready for context injection into a task-worker.
    Skills come back as raw name strings for the caller to load itself.

    Args:
        agent_name: Agent name in bare or plugin-qualified form.

    Returns:
        On success: ``AgentProfile`` model serialised as a dict, containing
        ``name``, ``plugin``, ``description``, ``model``, ``tools``, ``body``,
        ``skills`` (list of raw URI strings), and ``warnings``.

        On failure: ``{"error": "<description>"}`` — never raises a Python
        exception to the MCP client.
    """
    try:
        plugins_root = get_plugins_root()
    except FileNotFoundError as exc:
        return {"error": f"Cannot locate plugins root: {exc}"}

    try:
        entry = find_agent(agent_name, plugins_root)
    except FileNotFoundError as exc:
        return {"error": str(exc)}
    except ValueError as exc:
        return {"error": str(exc)}

    try:
        metadata, body = parse_agent_file(entry.path)
    except FileNotFoundError as exc:
        return {"error": f"Agent file disappeared after discovery: {exc}"}
    except ValueError as exc:
        return {"error": f"Failed to parse agent file '{entry.path}': {exc}"}

    warnings: list[str] = []
    if not body:
        warnings.append(f"Agent '{entry.name}': instruction body is empty.")

    profile = AgentProfile(
        name=metadata.name,
        plugin=entry.plugin,
        description=metadata.description,
        model=metadata.model,
        tools=metadata.tools,
        body=body,
        skills=metadata.skills,
        warnings=warnings,
    )
    return profile.model_dump(mode="json")


@mcp.tool(
    name="list",
    annotations=ToolAnnotations(
        title="List Agent Profiles",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
def _list(
    plugin: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "When provided, restrict the listing to agents owned by this plugin "
                "(e.g. 'development-harness', 'python3-development'). "
                "When omitted or null, all plugins are included."
            ),
        ),
    ] = None,
) -> dict:
    """Enumerate agent definitions across all plugins.

    Reads every plugin's agent definitions and returns one summary entry per
    agent. An agent that cannot be parsed is skipped with a warning rather than
    failing the call. Pass ``plugin`` to enumerate a single plugin.

    Args:
        plugin: Optional plugin name to filter results. When ``None``, all
            plugins are included.

    Returns:
        ``{"agents": [...ProfileListEntry dicts...], "count": N, "plugin_filter": plugin}``

        On failure to locate the plugins root:
        ``{"error": "<description>", "agents": [], "count": 0, "plugin_filter": plugin}``
    """
    try:
        plugins_root = get_plugins_root()
    except FileNotFoundError as exc:
        return {"error": f"Cannot locate plugins root: {exc}", "agents": [], "count": 0, "plugin_filter": plugin}

    all_entries = scan_all_agents(plugins_root)

    if plugin is not None:
        all_entries = [e for e in all_entries if e.plugin == plugin]

    result_entries: list[dict] = []
    parse_warnings: list[str] = []

    for entry in all_entries:
        try:
            metadata, _ = parse_agent_file(entry.path)
        except (FileNotFoundError, ValueError) as exc:
            parse_warnings.append(f"Skipped agent '{entry.plugin}/{entry.name}': {exc}")
            continue

        list_entry = ProfileListEntry(
            name=metadata.name,
            plugin=entry.plugin,
            description=metadata.description,
            skill_count=len(metadata.skills),
            model=metadata.model,
        )
        result_entries.append(list_entry.model_dump(mode="json"))

    response: dict = {"agents": result_entries, "count": len(result_entries), "plugin_filter": plugin}
    if parse_warnings:
        response["warnings"] = parse_warnings
    return response
