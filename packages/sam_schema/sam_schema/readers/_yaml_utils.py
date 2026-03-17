"""Shared YAML loading and coercion utilities for SAM readers.

All readers that use ruamel.yaml import from here to avoid copy-pasting the
same YAML instance creation and CommentedMap coercion logic.
"""

from __future__ import annotations

import re
from typing import Any

from ruamel.yaml import YAML

# Module-level singleton — YAML round-trip instances are stateless between
# load() calls, so reusing one instance avoids allocating internal state on
# every parsed YAML block.  For a 50-task plan this eliminates 50+ redundant
# YAML() constructor calls during a single plan read.
_YAML_RT: YAML = YAML(typ="rt")
_YAML_RT.preserve_quotes = True


def make_yaml() -> YAML:
    """Return the shared ruamel.yaml round-trip instance.

    Reader modules use this accessor to get a consistent YAML parser that
    preserves comments, field order, and string quoting style.

    Returns:
        The module-level ``YAML`` singleton configured for round-trip mode.
    """
    return _YAML_RT


def load_yaml(content: str) -> Any:  # noqa: ANN401
    """Parse YAML text using ruamel.yaml round-trip mode.

    Args:
        content: Raw YAML text to parse.

    Returns:
        Parsed YAML structure (dict or list).

    Raises:
        ValueError: If the content cannot be parsed as valid YAML.
    """
    try:
        return _YAML_RT.load(content)
    except Exception as exc:
        msg = f"Failed to parse YAML: {exc}"
        raise ValueError(msg) from exc


def coerce_to_plain(obj: Any) -> Any:  # noqa: ANN401
    """Recursively coerce ruamel.yaml comment-map/seq objects to plain Python types.

    ruamel.yaml round-trip mode returns ``CommentedMap`` and ``CommentedSeq``
    instead of plain ``dict``/``list``. Downstream normalizers work with plain
    Python types only.

    Args:
        obj: Any value from a ruamel.yaml parse result.

    Returns:
        Plain Python ``dict``, ``list``, or scalar (unchanged).
    """
    if hasattr(obj, "items"):  # dict-like (CommentedMap)
        return {str(k): coerce_to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [coerce_to_plain(item) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# Shared prose-parsing utilities used by frontmatter_reader and manifest_reader
# ---------------------------------------------------------------------------

# Heading pattern for markdown prose sections (## / ### / ####).
_HEADING_RE = re.compile(r"^(?:#{2,4})\s+(.+)$", re.MULTILINE)

# Map recognised heading names (lowercased) to canonical task field names.
# frontmatter_reader and manifest_reader both use this identical mapping.
# legacy_reader uses a separate _PROSE_HEADING_TO_FIELD with different keys.
HEADING_TO_FIELD: dict[str, str] = {
    "description": "description",
    "context": "description",
    "background": "description",
    "objective": "objective",
    "requirements": "requirements",
    "constraints": "constraints",
    "expected outputs": "expected-outputs",
    "expected output": "expected-outputs",
    "acceptance criteria": "acceptance-criteria",
    "acceptance": "acceptance-criteria",
    "verification steps": "verification-steps",
    "verification": "verification-steps",
    "cove checks": "verification-steps",
    "cove": "verification-steps",
    "context notes": "context-notes",
    "handoff": "handoff",
}


def split_outside_fences(body: str) -> list[str]:
    """Split a markdown body on ``---`` delimiters, ignoring those inside code fences.

    A ``---`` delimiter inside a triple-backtick code fence is NOT treated as a
    task section separator. This prevents spurious task splits when task body
    content contains YAML code examples.

    Args:
        body: Markdown text that may contain multiple YAML task blocks separated
              by ``---`` lines and interspersed prose.

    Returns:
        List of segments split on section delimiters that are outside code fences.
    """
    segments: list[str] = []
    current_parts: list[str] = []
    in_fence = False

    for line in body.split("\n"):
        if line.startswith("```"):
            in_fence = not in_fence
            current_parts.append(line)
            continue

        if not in_fence and re.match(r"^---+\s*$", line):
            segments.append("\n".join(current_parts))
            current_parts = []
            continue

        current_parts.append(line)

    segments.append("\n".join(current_parts))
    return segments


def parse_prose_fields(prose: str) -> dict[str, str]:
    """Extract named content sections from a markdown prose segment.

    Looks for ``## SectionName`` or ``### SectionName`` headings and collects
    the text beneath each one.  The results are mapped to canonical task field
    names so they can be merged into a task dict.

    Uses the shared ``HEADING_TO_FIELD`` mapping defined in this module.

    Args:
        prose: Raw markdown text, possibly starting with section headings.

    Returns:
        Dict of canonical field name → text content.  Only non-empty sections
        are included.
    """
    matches = list(_HEADING_RE.finditer(prose))
    result: dict[str, str] = {}

    if not matches:
        stripped = prose.strip()
        if stripped:
            result["description"] = stripped
        return result

    for idx, match in enumerate(matches):
        heading_text = match.group(1).strip()
        field = HEADING_TO_FIELD.get(heading_text.lower())
        if field is None:
            continue

        section_start = match.end()
        section_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(prose)
        content = prose[section_start:section_end].strip()
        if not content:
            continue

        if field in result:
            result[field] = result[field] + "\n\n" + content
        else:
            result[field] = content

    return result
