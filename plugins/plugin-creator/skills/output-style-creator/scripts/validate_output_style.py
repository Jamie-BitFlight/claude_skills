#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic>=2.9", "pyyaml>=6.0"]
# ///
"""Validate and discover Claude Code output styles.

Two subcommands:

    validate_output_style.py check <style-path>
    validate_output_style.py discover [--plugin <plugin-path>] [--start <directory>]

Both emit compact JSON on stdout for an agent to parse. ``check`` exits non-zero when the style
fails validation, so a caller can gate on the exit code without parsing the payload.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterator
from io import TextIOWrapper
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

# Ensure UTF-8 output on Windows (cp1252 default cannot encode every character a style may carry).
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

FRONTMATTER = re.compile(r"\A---[ \t]*\r?\n(.*?)^---[ \t]*(?:\r?\n|\Z)", re.DOTALL | re.MULTILINE)
STRING_FIELDS = ("name", "description")
BOOLEAN_FIELDS = ("keep-coding-instructions", "force-for-plugin")


class ValidationResult(BaseModel):
    """Outcome of validating one output-style file.

    Attributes:
        path: The style file that was checked.
        valid: True when no problem was found.
        problems: One entry per failed rule, in the order the rules run.
        fields: The parsed frontmatter keys and their Python types, for the caller's own checks.
    """

    path: str
    valid: bool
    problems: list[str]
    fields: dict[str, str]


class DiscoveryResult(BaseModel):
    """Output styles visible from a starting directory.

    Attributes:
        user: Styles under the user-level directory.
        managed: Styles under the operating system's managed settings directory.
        project: Styles under every ``.claude/output-styles/`` from ``start`` up to the repo root.
        plugin: Styles under the plugin's default directory and every ``outputStyles`` path it declares.
        plugin_declared_paths: The raw ``outputStyles`` entries read from the plugin manifest.
    """

    user: list[str]
    managed: list[str]
    project: list[str]
    plugin: list[str]
    plugin_declared_paths: list[str]


def read_frontmatter(path: Path) -> tuple[str, dict[str, Any]]:
    """Extract and parse a style file's YAML frontmatter.

    Args:
        path: The style file to read.

    Returns:
        The raw frontmatter text and the parsed mapping. An empty block yields an empty mapping,
        because every declared field is optional.

    Raises:
        ValueError: The file has no complete frontmatter block.
        TypeError: The frontmatter parses to something other than a YAML mapping.
    """
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError("frontmatter must open and close with --- on its own line")
    front = match.group(1)
    data = yaml.safe_load(front)
    if data is None:
        # Every field is optional — the filename supplies the name — so an empty block is valid.
        return front, {}
    if not isinstance(data, dict):
        raise TypeError("frontmatter must be a YAML mapping")
    return front, data


def description_nodes(node: yaml.Node | None, seen: set[int] | None = None) -> Iterator[yaml.Node]:
    """Yield every value node keyed ``description`` anywhere in a composed document.

    Walks nested mappings and sequences rather than only the top level, so a description reached
    through a YAML anchor or merge key is inspected too. A recursive alias produces a cyclic node
    graph, so each node is visited once.

    Args:
        node: The composed node to walk, or None.
        seen: Node identities already visited on this walk.

    Yields:
        Each value node whose key is ``description``.
    """
    seen = set() if seen is None else seen
    if node is None or id(node) in seen:
        return
    seen.add(id(node))
    if isinstance(node, yaml.MappingNode):
        for key, value in node.value:
            if getattr(key, "value", None) == "description":
                yield value
            yield from description_nodes(value, seen)
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            yield from description_nodes(item, seen)


def uses_merge_key(node: yaml.Node | None, seen: set[int] | None = None) -> bool:
    """Report whether a composed document uses a YAML merge key.

    A merge (``<<: *anchor``) sources a field from another mapping, which hides where the value
    was written and defeats any source-span check on the field itself. The style schema is a flat
    mapping of known fields, so a merge has no legitimate use here. A recursive alias produces a
    cyclic node graph, so each node is visited once.

    Args:
        node: The composed node to walk, or None.
        seen: Node identities already visited on this walk.

    Returns:
        True when any mapping in the document carries a ``<<`` key.
    """
    seen = set() if seen is None else seen
    if node is None or id(node) in seen:
        return False
    seen.add(id(node))
    if isinstance(node, yaml.MappingNode):
        return any(getattr(key, "value", None) == "<<" or uses_merge_key(value, seen) for key, value in node.value)
    if isinstance(node, yaml.SequenceNode):
        return any(uses_merge_key(item, seen) for item in node.value)
    return False


def validate(path: Path) -> ValidationResult:
    """Check one output-style file against the frontmatter schema.

    Args:
        path: The style file to check.

    Returns:
        The validation outcome, with one problem entry per failed rule.
    """
    try:
        front, data = read_frontmatter(path)
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        return ValidationResult(path=str(path), valid=False, problems=[str(exc)], fields={})

    problems: list[str] = [
        f"{field} must be a string when present"
        for field in STRING_FIELDS
        if field in data and not isinstance(data[field], str)
    ]
    problems.extend(
        f"{field} must be a boolean when present, not a quoted string"
        for field in BOOLEAN_FIELDS
        if field in data and not isinstance(data[field], bool)
    )

    composed = yaml.compose(front)
    if uses_merge_key(composed):
        problems.append("frontmatter must not use a YAML merge key; write each field directly")

    description = data.get("description")
    if isinstance(description, str):
        if any(node.start_mark.line != node.end_mark.line for node in description_nodes(composed)):
            problems.append("description must occupy a single line")
        if re.search(r"[\r\n]", description):
            problems.append("description must not contain a newline")

    problems.extend(
        f"frontmatter key {key!r} must be a string, not {type(key).__name__}"
        for key in data
        if not isinstance(key, str)
    )

    fields = {str(key): type(value).__name__ for key, value in data.items()}
    return ValidationResult(path=str(path), valid=not problems, problems=problems, fields=fields)


def managed_settings_directory() -> Path:
    r"""Return the operating system's managed settings directory.

    Claude Code reads a managed policy from a system directory that differs per platform. The
    legacy Windows path ``C:\\ProgramData\\ClaudeCode`` is not read and is not returned here.

    Returns:
        The system directory for this platform.
    """
    if sys.platform == "darwin":
        return Path("/Library/Application Support/ClaudeCode")
    if sys.platform == "win32":
        return Path("C:/Program Files/ClaudeCode")
    return Path("/etc/claude-code")


def repository_root(start: Path) -> Path:
    """Find the repository root above a directory.

    Args:
        start: The directory to search upward from.

    Returns:
        The nearest ancestor containing a ``.git`` entry, or the filesystem root when none exists.
    """
    for directory in [start, *start.parents]:
        if (directory / ".git").exists():
            return directory
    return Path(start.anchor or "/")


def styles_in(directory: Path) -> list[str]:
    """List the markdown files in a directory.

    Args:
        directory: The directory to list. A missing directory yields an empty list.

    Returns:
        The sorted markdown file paths as strings.
    """
    if not directory.is_dir():
        return []
    return sorted(str(entry) for entry in directory.glob("*.md") if entry.is_file())


def declared_output_style_paths(plugin: Path) -> list[str] | None:
    """Read a plugin manifest's ``outputStyles`` entries.

    The key replaces Claude Code's default ``output-styles/`` scan, so a plugin declaring
    ``./extras/`` ships nothing in the default directory.

    Args:
        plugin: The plugin root directory.

    Returns:
        The declared paths, normalised to a list, or None when the key is absent or the manifest
        cannot be read or does not hold a JSON object. An empty list means the key declares no paths, which is not the same as an
        absent key: the key still replaces the default scan, so nothing is loaded.
    """
    manifest = plugin / ".claude-plugin" / "plugin.json"
    try:
        root = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(root, dict):
        return None
    declared = root.get("outputStyles")
    if isinstance(declared, str):
        return [declared]
    if isinstance(declared, list):
        return [entry for entry in declared if isinstance(entry, str)]
    return None


def discover(start: Path, plugin: Path | None) -> DiscoveryResult:
    """Collect every output style visible from a starting directory.

    Claude Code loads every ``.claude/output-styles/`` between the working directory and the
    repository root, so this walks the ancestors rather than checking only ``start``.

    Args:
        start: The working directory to search upward from.
        plugin: A plugin root to inspect as well, or None.

    Returns:
        The styles found at each scope.
    """
    project: list[str] = []
    root = repository_root(start)
    for directory in [start, *start.parents]:
        project.extend(styles_in(directory / ".claude" / "output-styles"))
        if directory == root:
            break

    plugin_styles: list[str] = []
    declared: list[str] = []
    if plugin is not None:
        found = declared_output_style_paths(plugin)
        declared = found if found is not None else []
        # An absent key leaves the default scan in place; any declaration replaces it, empty included.
        searched = (
            [plugin / entry.removeprefix("./") for entry in declared]
            if found is not None
            else [plugin / "output-styles"]
        )
        for directory in searched:
            plugin_styles.extend(styles_in(directory) or ([str(directory)] if directory.is_file() else []))

    return DiscoveryResult(
        user=styles_in(Path.home() / ".claude" / "output-styles"),
        managed=styles_in(managed_settings_directory() / ".claude" / "output-styles"),
        project=project,
        plugin=plugin_styles,
        plugin_declared_paths=declared,
    )


def main() -> int:
    """Run the requested subcommand.

    Returns:
        0 on success, 1 when a style fails validation.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    check = subcommands.add_parser("check", help="Validate one output-style file.")
    check.add_argument("style_path", type=Path, help="Path to the style markdown file.")

    find = subcommands.add_parser("discover", help="List output styles visible from a directory.")
    find.add_argument("--start", type=Path, default=Path.cwd(), help="Directory to search upward from.")
    find.add_argument("--plugin", type=Path, default=None, help="Plugin root to inspect as well.")

    args = parser.parse_args()

    if args.command == "check":
        result = validate(args.style_path)
        sys.stdout.write(result.model_dump_json() + "\n")
        return 0 if result.valid else 1

    sys.stdout.write(discover(args.start.resolve(), args.plugin).model_dump_json() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
