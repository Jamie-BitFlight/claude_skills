#!/usr/bin/env python3
"""Quick validation script for skills - minimal version."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_yaml = YAML(typ="safe")

# Constants
MAX_NAME_LENGTH = 64

# Detects a bare YAML block-scalar indicator on the description line, e.g.
#   description: >-
#   description: |-
# These are parsed by YAML as empty string (not ">-") so the string-equality
# guard in _validate_description() cannot catch them — raw-text check is needed.
_BARE_BLOCK_SCALAR_RE = re.compile(r"^description:\s*[|>][-+]?\s*$", re.MULTILINE)
MAX_DESCRIPTION_LENGTH = 1024
REQUIRED_ARGC = 2  # script name + skill-path

# All properties allowed in SKILL.md frontmatter (March 2026 spec)
_ALLOWED_PROPERTIES = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
    "argument-hint",
    "model",
    "context",
    "agent",
    "user-invocable",
    "disable-model-invocation",
    "hooks",
}


def _read_frontmatter(skill_path: Path) -> tuple[bool, str | dict]:
    """Read and parse SKILL.md frontmatter YAML.

    Args:
        skill_path: Path to the skill directory

    Returns:
        Tuple of (True, frontmatter_dict) on success or (False, error_message) on failure
    """
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found"

    content = skill_md.read_text()
    if not content.startswith("---"):
        return False, "No YAML frontmatter found"

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    try:
        frontmatter = _yaml.load(match.group(1))
        if not isinstance(frontmatter, dict):
            return False, "Frontmatter must be a YAML dictionary"
    except YAMLError as e:
        return False, f"Invalid YAML in frontmatter: {e}"

    return True, frontmatter


def _validate_allowed_keys(frontmatter: dict) -> str | None:
    """Check for unexpected properties in frontmatter.

    Args:
        frontmatter: Parsed frontmatter dictionary

    Returns:
        Error message string if unexpected keys found, None if valid
    """
    unexpected_keys = set(frontmatter.keys()) - _ALLOWED_PROPERTIES
    if unexpected_keys:
        return (
            f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
            f"Allowed properties are: {', '.join(sorted(_ALLOWED_PROPERTIES))}"
        )
    return None


def _validate_name(frontmatter: dict) -> str | None:
    """Validate the name field in frontmatter.

    Args:
        frontmatter: Parsed frontmatter dictionary

    Returns:
        Error message string if invalid, None if valid
    """
    name = frontmatter.get("name", "")
    if not isinstance(name, str):
        return f"Name must be a string, got {type(name).__name__}"

    name = name.strip()
    if not name:
        return None

    if not re.match(r"^[a-z0-9-]+$", name):
        return f"Name '{name}' should be hyphen-case (lowercase letters, digits, and hyphens only)"
    if name.startswith("-") or name.endswith("-") or "--" in name:
        return f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
    if len(name) > MAX_NAME_LENGTH:
        return f"Name is too long ({len(name)} characters). Maximum is 64 characters."

    return None


def _validate_description(frontmatter: dict) -> str | None:
    """Validate the description field in frontmatter.

    Args:
        frontmatter: Parsed frontmatter dictionary

    Returns:
        Error message string if invalid, None if valid
    """
    description = frontmatter.get("description", "")
    if not isinstance(description, str):
        return f"Description must be a string, got {type(description).__name__}"

    description = description.strip()
    if description in {">-", "|-", ">", "|"}:
        return (
            "Description appears to be a YAML multiline indicator (>-, |-, |) "
            "which is broken in Claude Code. Use single-line quoted strings instead."
        )

    if not description:
        return None

    if "<" in description or ">" in description:
        return "Description cannot contain angle brackets (< or >)"
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return f"Description is too long ({len(description)} characters). Maximum is 1024 characters."

    return None


def _validate_description_raw(skill_path: Path) -> str | None:
    """Check raw SKILL.md text for a bare block-scalar indicator on the description line.

    YAML parses ``description: >-`` (with no block content) as an empty string,
    so _validate_description() cannot detect it via the parsed dict. This function
    reads the raw SKILL.md text and catches the pattern directly.

    Args:
        skill_path: Path to the skill directory

    Returns:
        Error message string if a bare block-scalar indicator is found, None otherwise
    """
    skill_md = skill_path / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    if _BARE_BLOCK_SCALAR_RE.search(content):
        return (
            "Description uses a bare YAML block scalar indicator (>-, |-) on its own line — "
            "this is broken in Claude Code. Use a single-line string value instead."
        )
    return None


def validate_skill(skill_path: str | Path) -> tuple[bool, str]:
    """Basic validation of a skill.

    Args:
        skill_path: Path to the skill directory

    Returns:
        Tuple of (is_valid, message)
    """
    skill_path = Path(skill_path)

    _ok, result = _read_frontmatter(skill_path)
    if not isinstance(result, dict):
        return False, result

    keys_err = _validate_allowed_keys(result)
    if keys_err:
        return False, keys_err

    name_err = _validate_name(result)
    if name_err:
        return False, name_err

    desc_err = _validate_description(result)
    if desc_err:
        return False, desc_err

    desc_raw_err = _validate_description_raw(skill_path)
    if desc_raw_err:
        return False, desc_raw_err

    return True, "Skill is valid!"


if __name__ == "__main__":
    if len(sys.argv) != REQUIRED_ARGC:
        print("Usage: python quick_validate.py <skill_directory>")
        sys.exit(1)

    valid, message = validate_skill(sys.argv[1])
    print(message)
    sys.exit(0 if valid else 1)
