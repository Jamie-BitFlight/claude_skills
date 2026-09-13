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
# The schema is closed: a key outside it is a typo Claude Code ignores in silence, which drops the
# behaviour the author asked for while the style still loads. See references/output-style-schema.md.
KNOWN_FIELDS = frozenset(STRING_FIELDS + BOOLEAN_FIELDS)


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


class DeclaredOutputStyles(BaseModel):
    """A plugin manifest's ``outputStyles`` declaration.

    Attributes:
        paths: The valid string entries read from the key.
        present: Whether the key is declared at all. Any declaration replaces Claude Code's
            default ``output-styles/`` scan, an empty one included.
        problems: Defects found while reading the manifest or the key. A declaration that cannot
            be read as paths attributes no styles to the plugin, rather than falling back to the
            default scan and reporting styles the manifest may not ship.
    """

    paths: list[str]
    present: bool
    problems: list[str]


class DiscoveryResult(BaseModel):
    """Output styles visible from a starting directory.

    Attributes:
        user: Styles under the user-level directory.
        managed: Styles under the operating system's managed settings directory.
        project: Styles under every ``.claude/output-styles/`` from ``start`` up to the repo root.
        project_rejected_paths: Project style files whose symlink target escapes the repository.
            A checkout can be untrusted, so a link out of the tree is not the project's content.
        plugin: Styles under the plugin's default directory and every ``outputStyles`` path it declares.
        plugin_declared_paths: The raw ``outputStyles`` entries read from the plugin manifest.
        plugin_rejected_paths: Declared entries that resolve outside the plugin root, and style
            files inside an accepted directory whose symlink target escapes it. Neither is
            searched or returned. A plugin cannot reference files outside its own directory.
        plugin_manifest_problems: Defects in the plugin manifest itself — unparseable JSON, a
            non-object root, or an ``outputStyles`` value that is not a string or an array of
            strings. A plugin reporting one attributes no styles here, since the declaration
            that would name them cannot be read.
    """

    user: list[str]
    managed: list[str]
    project: list[str]
    project_rejected_paths: list[str]
    plugin: list[str]
    plugin_declared_paths: list[str]
    plugin_rejected_paths: list[str]
    plugin_manifest_problems: list[str]


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
    problems.extend(
        f"{key!r} is not an output-style field; expected one of {', '.join(sorted(KNOWN_FIELDS))}"
        for key in data
        if isinstance(key, str) and key not in KNOWN_FIELDS
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


def styles_in(directory: Path, root: Path | None = None) -> tuple[list[str], list[str]]:
    """List the markdown files in a directory, optionally confined to a root.

    ``Path.glob`` and ``is_file`` follow symlinks, so a markdown symlink inside an accepted
    directory can point outside it. When ``root`` is given, such a file is excluded and reported
    rather than returned, because the caller reads every path this yields.

    Args:
        directory: The directory to list. A missing directory yields two empty lists.
        root: Confine results to this directory, or None to accept whatever the directory holds.

    Returns:
        The sorted markdown file paths, and the sorted paths excluded for escaping ``root``.
    """
    if not directory.is_dir():
        return [], []
    kept: list[str] = []
    escaped: list[str] = []
    for entry in sorted(directory.glob("*.md")):
        if not entry.is_file():
            continue
        if root is not None and not is_within(root, entry):
            escaped.append(str(entry))
        else:
            kept.append(str(entry))
    return kept, escaped


def json_type_name(value: object) -> str:
    """Name a decoded JSON value's type the way the manifest author wrote it.

    Args:
        value: Any value decoded from JSON.

    Returns:
        The JSON type name, so a message quotes ``null`` rather than ``NoneType``.
    """
    names = {
        type(None): "null",
        bool: "boolean",
        int: "number",
        float: "number",
        str: "string",
        list: "array",
        dict: "object",
    }
    return names.get(type(value), type(value).__name__)


def load_plugin_manifest(manifest: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Read a plugin manifest into a JSON object.

    Args:
        manifest: The ``plugin.json`` path.

    Returns:
        The decoded object and an empty problem list, or None and the defect that stopped it. A
        manifest that is simply absent is neither: None with no problem, since a directory that
        declares nothing is not malformed.
    """
    try:
        text = manifest.read_text(encoding="utf-8")
    except FileNotFoundError:
        # No manifest: the caller named a directory that declares nothing.
        return None, []
    except OSError as exc:
        # It exists but will not open — a directory, a permission denial, a bad symlink. Claude
        # Code cannot load it either, so this is a defect rather than a plugin declaring nothing.
        return None, [f"{manifest}: cannot be read ({exc.strerror or exc.__class__.__name__})"]
    try:
        root = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, [f"{manifest}: not valid JSON ({exc.msg}, line {exc.lineno} column {exc.colno})"]
    if not isinstance(root, dict):
        return None, [f"{manifest}: manifest root is {json_type_name(root)}, expected an object"]
    return root, []


def declared_output_style_paths(plugin: Path) -> DeclaredOutputStyles:
    """Read a plugin manifest's ``outputStyles`` entries.

    The key replaces Claude Code's default ``output-styles/`` scan, so a plugin declaring
    ``./extras/`` ships nothing in the default directory.

    An absent key and an unreadable declaration are different states with different consequences,
    so they are reported separately rather than both falling back to the default scan. Reporting a
    malformed manifest as though its default directory were in force would tell the agent the
    plugin ships styles that Claude Code may never load.

    Args:
        plugin: The plugin root directory.

    Returns:
        The declaration: its valid string paths, whether the key is present at all, and any defect
        found while reading it.
    """
    manifest = plugin / ".claude-plugin" / "plugin.json"
    root, problems = load_plugin_manifest(manifest)
    if root is None:
        return DeclaredOutputStyles(paths=[], present=False, problems=problems)
    if "outputStyles" not in root:
        return DeclaredOutputStyles(paths=[], present=False, problems=[])
    declared = root["outputStyles"]
    if isinstance(declared, str):
        return DeclaredOutputStyles(paths=[declared], present=True, problems=[])
    if isinstance(declared, list):
        paths = [entry for entry in declared if isinstance(entry, str)]
        problems = [
            f"{manifest}: outputStyles entry {index} is {json_type_name(entry)}, expected a string"
            for index, entry in enumerate(declared)
            if not isinstance(entry, str)
        ]
        return DeclaredOutputStyles(paths=paths, present=True, problems=problems)
    return DeclaredOutputStyles(
        paths=[],
        present=True,
        problems=[f"{manifest}: outputStyles is {json_type_name(declared)}, expected a string or an array of strings"],
    )


def is_within(root: Path, candidate: Path) -> bool:
    """Report whether a path resolves to the root itself or somewhere beneath it.

    Both sides are resolved, so a symlink is judged by its target rather than its location.

    Args:
        root: The directory that must contain the candidate.
        candidate: The path to test.

    Returns:
        True when the resolved candidate is the resolved root or lies beneath it.
    """
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    return resolved == resolved_root or resolved_root in resolved.parents


def confine_to_root(root: Path, entry: str) -> Path | None:
    """Resolve a declared manifest path, rejecting anything outside the plugin root.

    A plugin cannot reference files outside its own directory, so a declared ``../outside/`` or an
    absolute path is not a path this plugin ships, and every component path must start with
    ``./``. Discovery's output is read by an agent, so an escaping entry would hand it unrelated
    file content from an untrusted plugin.

    Args:
        root: The plugin root directory.
        entry: One raw ``outputStyles`` entry.

    Returns:
        The resolved directory when the entry carries the required ``./`` prefix and lies at or
        beneath the root, otherwise None.
    """
    if not entry.startswith("./"):
        # rules/plugin-json.md: every component path must start with "./". Claude's own plugin
        # validator rejects the manifest, so a style under such a path is not one it would load.
        return None
    candidate = root / entry.removeprefix("./")
    if not is_within(root, candidate):
        return None
    return candidate.resolve()


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
    project_rejected: list[str] = []
    root = repository_root(start)
    for directory in [start, *start.parents]:
        # A checkout can belong to someone else, so a link out of the tree is not its content.
        found, escaped = styles_in(directory / ".claude" / "output-styles", root)
        project.extend(found)
        project_rejected.extend(escaped)
        if directory == root:
            break

    plugin_styles: list[str] = []
    declared: list[str] = []
    rejected: list[str] = []
    manifest_problems: list[str] = []
    if plugin is not None:
        found = declared_output_style_paths(plugin)
        declared = found.paths
        manifest_problems = found.problems
        # An absent, readable key leaves the default scan in place; any declaration replaces it,
        # empty included. A manifest defect names no directory to scan and guesses at none.
        if not found.present and not found.problems:
            searched = [plugin / "output-styles"]
        else:
            searched = []
            for entry in declared:
                confined = confine_to_root(plugin, entry)
                if confined is None:
                    rejected.append(entry)
                else:
                    searched.append(confined)
        for directory in searched:
            found_styles, escaped = styles_in(directory, plugin)
            rejected.extend(escaped)
            if found_styles:
                plugin_styles.extend(found_styles)
            elif directory.is_file() and is_within(plugin, directory):
                plugin_styles.append(str(directory))

    return DiscoveryResult(
        user=styles_in(Path.home() / ".claude" / "output-styles")[0],
        managed=styles_in(managed_settings_directory() / ".claude" / "output-styles")[0],
        project=project,
        project_rejected_paths=project_rejected,
        plugin=plugin_styles,
        plugin_declared_paths=declared,
        plugin_rejected_paths=rejected,
        plugin_manifest_problems=manifest_problems,
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
