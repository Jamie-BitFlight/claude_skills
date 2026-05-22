"""Pydantic v2 data models for the agent-profile MCP package.

All models use ``from __future__ import annotations`` for deferred evaluation
and ``Field(description=...)`` on every field for MCP schema generation.

This module has no imports from other ``agent_profile`` sub-modules so it can
be imported in isolation during testing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from pathlib import Path


class AgentEntry(BaseModel):
    """Lightweight reference to a discovered agent definition file.

    Produced by ``discovery.py`` during the scan phase before any parsing
    or skill resolution occurs.
    """

    name: str = Field(description="Bare agent name as it appears in the filename, e.g. 'python-cli-architect'.")
    plugin: str = Field(description="Name of the owning plugin directory, e.g. 'python3-development'.")
    path: Path = Field(description="Absolute filesystem path to the agent's .md definition file.")


class AgentMetadata(BaseModel):
    """Structured frontmatter extracted from an agent definition file.

    Corresponds to the YAML block between the ``---`` delimiters at the top
    of every agent ``.md`` file.
    """

    name: str = Field(description="Agent name declared in frontmatter, e.g. 'python-cli-architect'.")
    description: str = Field(description="One-line description of the agent's purpose.")
    skills: list[str] = Field(
        default_factory=list,
        description="Ordered list of skill URIs this agent loads, e.g. ['python3-development', 'dh:subagent-contract'].",
    )
    tools: list[str] = Field(
        default_factory=list, description="MCP tool names or glob patterns the agent is allowed to call."
    )
    model: str | None = Field(
        default=None, description="Preferred model identifier, e.g. 'claude-sonnet-4-6'. None means use caller default."
    )
    color: str | None = Field(
        default=None, description="Display colour hint for the agent in the Claude Code UI, e.g. '#FF6B35'."
    )


class AgentProfile(BaseModel):
    """Complete compiled profile for an agent, ready for context injection.

    Returned by the ``profile_load`` MCP tool. Contains the agent's own
    instruction body and all resolved skill content bundled into a single
    loadable unit.
    """

    name: str = Field(description="Agent name, e.g. 'python-cli-architect'.")
    plugin: str = Field(description="Owning plugin directory name, e.g. 'python3-development'.")
    description: str = Field(description="One-line description from the agent frontmatter.")
    model: str | None = Field(
        default=None, description="Preferred model identifier from frontmatter. None means use caller default."
    )
    tools: list[str] = Field(
        default_factory=list, description="MCP tool names or glob patterns the agent is allowed to call."
    )
    body: str = Field(
        description=(
            "Instruction body extracted from the agent .md file below the frontmatter delimiter. "
            "This is the agent's role definition and workflow instructions."
        )
    )
    skills: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered list of skill URI strings as declared in the agent frontmatter. "
            "Load each skill into context via ``Skill(skill=uri)`` — resolution is handled "
            "by the Claude Code SDK, not by this server."
        ),
    )
    warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Non-fatal issues encountered during resolution, e.g. unresolvable skill URIs or "
            "circular dependency detections. Consumers should surface these to the operator."
        ),
    )


class ProfileListEntry(BaseModel):
    """Summary metadata for a single agent, used in ``profile_list`` responses.

    Does not include the agent body or resolved skill content — consumers call
    ``profile_load`` to obtain the full profile for a specific agent.
    """

    name: str = Field(description="Agent name, e.g. 'code-reviewer'.")
    plugin: str = Field(description="Owning plugin directory name, e.g. 'python3-development'.")
    description: str = Field(description="One-line description from the agent frontmatter.")
    skill_count: int = Field(
        description="Number of skill URIs declared in the agent frontmatter (not recursively expanded)."
    )
    model: str | None = Field(
        default=None, description="Preferred model identifier from frontmatter. None when not declared."
    )


# Rebuild models that reference Path which is under TYPE_CHECKING.
# Required by Pydantic v2 when `from __future__ import annotations` is active
# and the type is only imported inside `if TYPE_CHECKING`.
from pathlib import Path as _Path

_rebuild_ns = {"Path": _Path}
AgentEntry.model_rebuild(_types_namespace=_rebuild_ns)
