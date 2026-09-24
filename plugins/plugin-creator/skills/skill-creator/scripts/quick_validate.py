#!/usr/bin/env python3
"""Strict portable Agent Skills package validation."""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_yaml = YAML(typ="safe")

# Constants
MAX_NAME_LENGTH = 64

MAX_DESCRIPTION_LENGTH = 1024
REQUIRED_ARGC = 2  # script name + skill-path

# Portable Agent Skills fields accepted by claude.ai uploads, the Skills API,
# and Anthropic's package format.
_ALLOWED_PROPERTIES = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}


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


def _validate_optional_fields(frontmatter: dict) -> str | None:
    """Validate portable optional field types and limits."""
    for key in ("license", "compatibility", "allowed-tools"):
        value = frontmatter.get(key)
        if value is not None and not isinstance(value, str):
            return f"{key} must be a string, got {type(value).__name__}"
    compatibility = frontmatter.get("compatibility")
    if isinstance(compatibility, str):
        if not compatibility.strip():
            return "compatibility must be non-empty when provided"
        if len(compatibility) > 500:
            return f"Compatibility is too long ({len(compatibility)} characters). Maximum is 500 characters."
    metadata = frontmatter.get("metadata")
    if metadata is not None and (
        not isinstance(metadata, dict)
        or not all(isinstance(key, str) and isinstance(value, str) for key, value in metadata.items())
    ):
        return "metadata must be a mapping of string keys to string values"
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

    name = unicodedata.normalize("NFKC", name.strip())
    if not name:
        return "Name is required for a portable skill package"

    if name != name.lower():
        return f"Name '{name}' must be lowercase"
    if not all(character.isalnum() or character == "-" for character in name):
        return f"Name '{name}' may contain only Unicode letters, digits, and hyphens"
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
    if not description:
        return "Description is required for a portable skill package"

    if len(description) > MAX_DESCRIPTION_LENGTH:
        return f"Description is too long ({len(description)} characters). Maximum is 1024 characters."

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

    optional_err = _validate_optional_fields(result)
    if optional_err:
        return False, optional_err

    name_err = _validate_name(result)
    if name_err:
        return False, name_err

    normalized_name = unicodedata.normalize("NFKC", result["name"].strip())
    normalized_directory = unicodedata.normalize("NFKC", skill_path.name)
    if normalized_name != normalized_directory:
        return False, f"Name '{result['name'].strip()}' must match parent directory '{skill_path.name}'"

    desc_err = _validate_description(result)
    if desc_err:
        return False, desc_err

    return True, "Skill is valid!"


if __name__ == "__main__":
    if len(sys.argv) != REQUIRED_ARGC:
        print("Usage: python quick_validate.py <skill_directory>")
        sys.exit(1)

    valid, message = validate_skill(sys.argv[1])
    print(message)
    sys.exit(0 if valid else 1)
