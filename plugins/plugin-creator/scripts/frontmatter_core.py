"""Shared frontmatter validation core — Pydantic models, extraction, normalization.

This module is a plain library module (not a PEP 723 standalone script).
It is importable by sibling PEP 723 scripts via sys.path insertion:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from frontmatter_core import SkillFrontmatter, ...

Design constraints (SOLID, DRY):
  - Single Responsibility: validation schema only — no CLI, no YAML I/O, no plugin.json logic.
  - Open/Closed: add a new file type by adding a new Pydantic model and one entry in
    get_frontmatter_model(). No existing code changes.
  - Liskov Substitution: all frontmatter models are Pydantic BaseModel subclasses;
    callers that receive `type[BaseModel]` from get_frontmatter_model() can call
    .model_validate() and .model_dump() uniformly.
  - Interface Segregation: lean exports — models, helpers, constants only.
  - Dependency Inversion: both validate_frontmatter.py and skilllint validators depend on
    this module, not on each other.

Public API:
  Constants:
    RECOMMENDED_DESCRIPTION_LENGTH -- warn when description exceeds this many characters
    MAX_SKILL_NAME_LENGTH          -- maximum allowed skill name length

  Pydantic models:
    SkillFrontmatter    -- validates SKILL.md frontmatter
    CommandFrontmatter  -- validates commands/*.md frontmatter
    AgentFrontmatter    -- validates agents/*.md frontmatter

  Functions:
    extract_frontmatter    -- parse the YAML frontmatter block out of file content
    get_frontmatter_model  -- map a file-type string to a Pydantic model class
    fix_skill_name_field   -- add/correct the 'name' field to match directory name

Dependencies (provided by callers' PEP 723 environments):
  pydantic>=2.0.0
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RECOMMENDED_DESCRIPTION_LENGTH: int = 1024
"""Warn when a description exceeds this many characters."""

MAX_SKILL_NAME_LENGTH: int = 40
"""Maximum allowed length for a skill name or directory name."""

_SKILL_DIR_NAME_PATTERN: re.Pattern[str] = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
"""Pattern for valid skill directory names (and 'name' field values).

Rules (per agentskills.io/specification and init_skill.py):
- Lowercase letters, digits, and hyphens only (a-z, 0-9, -)
- May start with a digit or letter
- Must not start or end with a hyphen
- Must not contain consecutive hyphens (--)
"""


# ---------------------------------------------------------------------------
# Pydantic frontmatter models
# ---------------------------------------------------------------------------


class SkillFrontmatter(BaseModel):
    """Pydantic model for SKILL.md frontmatter validation.

    Source: .claude/skills/claude-skills-overview-2026/SKILL.md lines 52-67
    """

    model_config = ConfigDict(extra="allow")

    name: str | None = Field(None, max_length=64, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    description: str | None = None
    argument_hint: str | None = Field(None, alias="argument-hint")
    allowed_tools: str | None = Field(None, alias="allowed-tools")
    model: str | None = None
    skills: str | None = None
    context: Literal["fork"] | None = None
    agent: str | None = None
    user_invocable: bool | None = Field(None, alias="user-invocable")
    disable_model_invocation: bool | None = Field(None, alias="disable-model-invocation")
    hooks: dict[str, Any] | None = None

    @field_validator("skills", "allowed_tools", mode="before")
    @classmethod
    def normalize_comma_separated(cls, v: object) -> str | None:
        """Convert YAML arrays to comma-separated strings.

        Returns:
            Normalized comma-separated string or None.
        """
        if isinstance(v, list):
            return ", ".join(str(x) for x in v)
        return v if isinstance(v, str) else None

    @field_validator("description", mode="before")
    @classmethod
    def normalize_single_line(cls, v: object) -> str | None:
        """Collapse multiline descriptions to single line.

        Returns:
            Normalized single-line string or None.
        """
        if isinstance(v, str) and "\n" in v:
            return " ".join(v.split())
        return v if isinstance(v, str) else None


class CommandFrontmatter(BaseModel):
    """Pydantic model for commands/*.md frontmatter validation."""

    model_config = ConfigDict(extra="allow")

    description: str
    argument_hint: str | None = Field(None, alias="argument-hint")
    allowed_tools: str | None = Field(None, alias="allowed-tools")
    model: str | None = None
    context: Literal["fork"] | None = None
    agent: str | None = None
    hooks: dict[str, Any] | None = None

    @field_validator("allowed_tools", mode="before")
    @classmethod
    def normalize_comma_separated(cls, v: object) -> str | None:
        """Convert YAML arrays to comma-separated strings.

        Returns:
            Normalized comma-separated string or None.
        """
        if isinstance(v, list):
            return ", ".join(str(x) for x in v)
        return v if isinstance(v, str) else None

    @field_validator("description", mode="before")
    @classmethod
    def normalize_single_line(cls, v: object) -> str | None:
        """Collapse multiline descriptions to single line.

        Returns:
            Normalized single-line string or None.
        """
        if isinstance(v, str) and "\n" in v:
            return " ".join(v.split())
        return v if isinstance(v, str) else None


class AgentFrontmatter(BaseModel):
    """Pydantic model for agents/*.md frontmatter validation.

    Source: .claude/skills/agent-creator/references/agent-schema.md

    Note: Field names use camelCase to match the official agent schema.
    Ruff N815 warnings suppressed for these fields as they match external spec.
    """

    model_config = ConfigDict(extra="allow")

    name: str = Field(max_length=64, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    description: str
    tools: str | None = None
    disallowedTools: str | None = None
    model: Literal["sonnet", "opus", "haiku", "inherit"] | None = None
    permissionMode: Literal["default", "acceptEdits", "dontAsk", "bypassPermissions", "plan"] | None = None
    maxTurns: int | None = None
    skills: str | None = None
    mcpServers: list[Any] | dict[str, Any] | None = None
    hooks: dict[str, Any] | None = None
    memory: Literal["user", "project", "local"] | None = None
    background: bool | None = None
    isolation: Literal["worktree"] | None = None
    color: str | None = None

    @field_validator("skills", "tools", "disallowedTools", mode="before")
    @classmethod
    def normalize_comma_separated(cls, v: object) -> str | None:
        """Convert YAML arrays to comma-separated strings.

        Returns:
            Normalized comma-separated string or None.
        """
        if isinstance(v, list):
            return ", ".join(str(x) for x in v)
        return v if isinstance(v, str) else None

    @field_validator("description", mode="before")
    @classmethod
    def normalize_single_line(cls, v: object) -> str | None:
        """Collapse multiline descriptions to single line.

        Returns:
            Normalized single-line string or None.
        """
        if isinstance(v, str) and "\n" in v:
            return " ".join(v.split())
        return v if isinstance(v, str) else None


# ---------------------------------------------------------------------------
# Registry (Open/Closed extension point)
# ---------------------------------------------------------------------------

#: Maps file-type string values to their Pydantic model class.
#: To add a new file type: append one entry here and create its model class above.
#: No other code changes required.
_MODEL_REGISTRY: dict[str, type[SkillFrontmatter | CommandFrontmatter | AgentFrontmatter]] = {
    "skill": SkillFrontmatter,
    "command": CommandFrontmatter,
    "agent": AgentFrontmatter,
}


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def extract_frontmatter(content: str) -> tuple[str | None, int, int]:
    """Extract the YAML frontmatter block from markdown file content.

    Args:
        content: Full file content, potentially starting with '---'.

    Returns:
        Tuple of (frontmatter_text, start_line, end_line).
        Returns (None, 0, 0) if no valid frontmatter block is found.
    """
    if not content.startswith("---"):
        return None, 0, 0

    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return None, 0, 0

    frontmatter_text = content[4 : end_match.start() + 3]
    start_line = 1
    end_line = frontmatter_text.count("\n") + 2

    return frontmatter_text, start_line, end_line


def get_frontmatter_model(
    file_type_value: str,
) -> type[SkillFrontmatter | CommandFrontmatter | AgentFrontmatter] | None:
    """Return the Pydantic model class for a given file-type string.

    Args:
        file_type_value: String value of the file type, e.g. 'skill', 'command', 'agent'.
            Accepts StrEnum values directly since StrEnum.__str__ returns the value.

    Returns:
        Pydantic model class, or None if the type has no registered model.

    Example:
        model_class = get_frontmatter_model(file_type.value)
        if model_class:
            validated = model_class.model_validate(data)
    """
    return _MODEL_REGISTRY.get(str(file_type_value))


def fix_skill_name_field(normalized_dict: dict[str, Any], file_path: Path, fixes: list[str]) -> dict[str, Any]:
    """Add or correct the 'name' field to match the skill's parent directory name.

    The 'name' field must equal the directory name containing SKILL.md.
    - If absent: derived from the directory name and prepended.
    - If present but wrong: corrected in-place.
    - If the directory name does not match the required pattern: no change.

    Args:
        normalized_dict: Current frontmatter key/value pairs.
        file_path: Path to the SKILL.md file.
        fixes: Mutable list of fix descriptions; this function appends to it.

    Returns:
        Updated normalized_dict (may be a new dict if 'name' was inserted).
    """
    dir_name = file_path.parent.name
    if not _SKILL_DIR_NAME_PATTERN.match(dir_name):
        return normalized_dict

    current_name = normalized_dict.get("name")
    if current_name is None:
        fixes.append(f"Added 'name' field '{dir_name}' derived from directory name")
        return {"name": dir_name, **normalized_dict}

    if current_name != dir_name:
        fixes.append(f"Corrected 'name' field from '{current_name}' to '{dir_name}' to match directory name")
        normalized_dict["name"] = dir_name

    return normalized_dict
