#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["ruamel.yaml>=0.18.0", "typer>=0.21.0"]
# ///
"""Migrate research entries from text-header format to YAML frontmatter.

Text-header entries use bold key-value pairs before the first ``---`` separator::

    # Title

    **Research Date**: 2026-06-18
    **Source URL**: <https://github.com/...>
    **Version at Research**: 1.0.0
    **License**: MIT

    ---

    ## Overview

YAML frontmatter entries use a standard YAML block::

    ---
    title: "Title"
    research_date: "2026-06-18"
    source_url: "https://github.com/..."
    version_at_research: "1.0.0"
    license: "MIT"
    category: "agent-frameworks"
    last_verified: "2026-06-18"
    version_at_verification: "1.0.0"
    next_review: "2026-09-18"
    ---

    # Title

    ## Overview

Both formats are valid after migration. Run ``validate_research.py`` to confirm.
"""

from __future__ import annotations

import re
from io import StringIO
from pathlib import Path
from typing import Annotated

import typer
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString as DQ

app = typer.Typer(add_completion=False, help="Migrate research entries to YAML frontmatter.")

# ---------------------------------------------------------------------------
# Regex patterns for text-header field extraction
# ---------------------------------------------------------------------------

_FIELD_PATTERN = re.compile(r"^\*\*([^*]+)\*\*\s*:\s*(.+)$")
_ANGLE_URL = re.compile(r"^<(.+)>$")
_TITLE_PATTERN = re.compile(r"^#\s+(.+)$")

# Maps bold-header field names → canonical YAML key
_HEADER_KEY_MAP: dict[str, str] = {
    "Research Date": "research_date",
    "Source URL": "source_url",
    "GitHub Repository": "github_url",
    "Documentation": "documentation_url",
    "Version at Research": "version_at_research",
    "License": "license",
}

# Maps Freshness Tracking bold fields → canonical YAML key
_FRESHNESS_KEY_MAP: dict[str, str] = {
    "Last Verified": "last_verified",
    "Version at Verification": "version_at_verification",
    "Next Review Recommended": "next_review",
    "Next Review": "next_review",
}

_yaml = YAML()
_yaml.default_flow_style = False
_yaml.preserve_quotes = True
_yaml.width = 4096  # prevent line-wrapping in output


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def _strip_angle_url(value: str) -> str:
    """Remove surrounding angle brackets from a URL value if present.

    Args:
        value: Raw value string from the text header.

    Returns:
        URL string without surrounding ``<`` ``>``.
    """
    match = _ANGLE_URL.match(value.strip())
    return match.group(1) if match else value.strip()


def _extract_title(lines: list[str]) -> str:
    """Extract the first ``# Heading`` title from the file.

    Args:
        lines: All file lines.

    Returns:
        Title string, or empty string when no heading is found.
    """
    for line in lines:
        match = _TITLE_PATTERN.match(line.strip())
        if match:
            return match.group(1).strip()
    return ""


def _extract_header_fields(header_lines: list[str]) -> dict[str, str]:
    """Parse key-value fields from the text-header block.

    Only lines matching ``**Field Name**: value`` are extracted. All other
    content (heading lines, blank lines, plain text) is ignored.

    Args:
        header_lines: Lines before the first ``---`` separator.

    Returns:
        Dict mapping canonical YAML key → value string.
    """
    fields: dict[str, str] = {}
    for line in header_lines:
        match = _FIELD_PATTERN.match(line.strip())
        if not match:
            continue
        raw_name = match.group(1).strip()
        raw_value = match.group(2).strip()
        yaml_key = _HEADER_KEY_MAP.get(raw_name)
        if yaml_key:
            fields[yaml_key] = _strip_angle_url(raw_value)
    return fields


def _extract_freshness_fields(body_lines: list[str]) -> dict[str, str]:
    """Parse freshness fields from the ``## Freshness Tracking`` section.

    Looks for ``**Field**: value`` lines within the Freshness Tracking section.
    Also handles table rows of the form ``| Field | Value |``.

    Args:
        body_lines: Lines of the file body (after the opening ``---`` separator).

    Returns:
        Dict mapping canonical YAML key → value string.
    """
    fields: dict[str, str] = {}
    in_freshness = False

    for line in body_lines:
        stripped = line.strip()
        if stripped == "## Freshness Tracking":
            in_freshness = True
            continue
        if in_freshness and stripped.startswith("## "):
            break

        if not in_freshness:
            continue

        # Bold key-value line: **Last Verified**: 2026-06-18
        match = _FIELD_PATTERN.match(stripped)
        if match:
            raw_name = match.group(1).strip()
            raw_value = match.group(2).strip()
            yaml_key = _FRESHNESS_KEY_MAP.get(raw_name)
            if yaml_key:
                fields[yaml_key] = raw_value
            continue

        # Table row: | Last Verified | 2026-06-18 |
        if stripped.startswith("|") and stripped.endswith("|"):
            parts = [p.strip() for p in stripped.strip("|").split("|")]
            MIN_TABLE_COLS = 2
            if len(parts) >= MIN_TABLE_COLS:
                raw_name = parts[0].strip()
                raw_value = parts[1].strip()
                yaml_key = _FRESHNESS_KEY_MAP.get(raw_name)
                if yaml_key and raw_value and raw_value != "---":
                    fields[yaml_key] = raw_value

    return fields


def _detect_category(filepath: Path, research_root: Path) -> str:
    """Infer category from the parent directory name relative to research root.

    Args:
        filepath: Absolute path to the entry file.
        research_root: Root of the research directory tree.

    Returns:
        Category string (parent dir name), or empty string when indeterminate.
    """
    try:
        relative = filepath.relative_to(research_root)
        parts = relative.parts
        return parts[0] if len(parts) > 1 else ""
    except ValueError:
        return ""


# ---------------------------------------------------------------------------
# Body stripping helpers
# ---------------------------------------------------------------------------


def _get_body_after_header(lines: list[str]) -> list[str]:
    """Return lines after the first ``---`` separator, including the separator itself.

    For text-header format, the ``---`` separates the header block from the body.
    We drop everything up to and including the first ``---``, then return what
    follows (which begins with ``## Overview`` or similar).

    Args:
        lines: All file lines.

    Returns:
        Lines after the first ``---``, or all lines when no separator found.
    """
    for i, line in enumerate(lines):
        if line.strip() == "---":
            return lines[i + 1 :]
    return lines


def _strip_freshness_section(body_lines: list[str]) -> list[str]:
    """Remove the ``## Freshness Tracking`` section from body lines.

    The entire section (heading through end of content or next ``##`` heading) is
    removed because its data moves into the YAML frontmatter.

    Args:
        body_lines: File body lines (after header ``---``).

    Returns:
        Body lines with the Freshness Tracking section removed.
    """
    result: list[str] = []
    skip = False

    for line in body_lines:
        stripped = line.strip()
        if stripped == "## Freshness Tracking":
            skip = True
            continue
        if skip and stripped.startswith("## "):
            skip = False
        if not skip:
            result.append(line)

    return result


# ---------------------------------------------------------------------------
# Frontmatter builder
# ---------------------------------------------------------------------------


def _build_frontmatter(
    title: str, header_fields: dict[str, str], freshness_fields: dict[str, str], category: str
) -> str:
    """Serialise collected fields into a YAML frontmatter block.

    Field ordering matches the canonical format documented in the module
    docstring. All string values are double-quoted for readability.

    Args:
        title: Entry title extracted from the ``# Heading`` line.
        header_fields: Fields from the text-header block.
        freshness_fields: Fields from the Freshness Tracking section.
        category: Category inferred from directory path.

    Returns:
        Complete frontmatter string including opening and closing ``---``.
    """
    data: dict[str, object] = {}

    if title:
        data["title"] = DQ(title)
    if "research_date" in header_fields:
        data["research_date"] = DQ(header_fields["research_date"])
    if "source_url" in header_fields:
        data["source_url"] = DQ(header_fields["source_url"])
    if "github_url" in header_fields:
        data["github_url"] = DQ(header_fields["github_url"])
    if "documentation_url" in header_fields:
        data["documentation_url"] = DQ(header_fields["documentation_url"])
    if "version_at_research" in header_fields:
        data["version_at_research"] = DQ(header_fields["version_at_research"])
    if "license" in header_fields:
        data["license"] = DQ(header_fields["license"])
    if category:
        data["category"] = DQ(category)
    if "last_verified" in freshness_fields:
        data["last_verified"] = DQ(freshness_fields["last_verified"])
    if "version_at_verification" in freshness_fields:
        data["version_at_verification"] = DQ(freshness_fields["version_at_verification"])
    if "next_review" in freshness_fields:
        data["next_review"] = DQ(freshness_fields["next_review"])

    buf = StringIO()
    _yaml.dump(data, buf)
    yaml_text = buf.getvalue().rstrip("\n")
    return f"---\n{yaml_text}\n---\n"


# ---------------------------------------------------------------------------
# Single-file migration
# ---------------------------------------------------------------------------


def _is_yaml_frontmatter(lines: list[str]) -> bool:
    """Return True when the file already uses YAML frontmatter.

    Args:
        lines: All file lines.

    Returns:
        True when the first non-empty line is ``---``.
    """
    return bool(lines) and lines[0].strip() == "---"


def migrate_file(filepath: Path, research_root: Path, *, dry_run: bool) -> tuple[bool, str]:
    """Migrate one file from text-header to YAML frontmatter.

    Idempotent: files already using YAML frontmatter are skipped without error.

    Args:
        filepath: Path to the markdown file to migrate.
        research_root: Root used for category detection.
        dry_run: When True, compute the migration but do not write the file.

    Returns:
        Tuple of (changed: bool, message: str). ``changed`` is True when the
        file was (or would be) written. ``message`` describes the outcome.
    """
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines()

    if _is_yaml_frontmatter(lines):
        return False, "already yaml_frontmatter — skipped"

    title = _extract_title(lines)
    header_lines, _ = _split_header(lines)
    header_fields = _extract_header_fields(header_lines)
    body_after_header = _get_body_after_header(lines)
    freshness_fields = _extract_freshness_fields(body_after_header)
    category = _detect_category(filepath, research_root)

    frontmatter = _build_frontmatter(title, header_fields, freshness_fields, category)

    # Strip the old header block and freshness section from the body
    body_stripped = _strip_freshness_section(body_after_header)

    # Drop leading blank lines from body so the title heading sits flush
    while body_stripped and not body_stripped[0].strip():
        body_stripped.pop(0)

    # Build the new file: frontmatter + blank line + # Title + blank line + body
    new_lines = frontmatter.splitlines()
    new_lines.append("")
    if title:
        new_lines.append(f"# {title}")
        new_lines.append("")
    new_lines.extend(body_stripped)

    # Ensure single trailing newline
    new_text = "\n".join(new_lines).rstrip("\n") + "\n"

    if not dry_run:
        filepath.write_text(new_text, encoding="utf-8")
        return True, "migrated"

    return True, "would migrate (dry-run)"


def _split_header(lines: list[str]) -> tuple[list[str], int]:
    """Return lines before the first ``---`` separator and the separator index.

    Args:
        lines: All file lines.

    Returns:
        Tuple of (header_lines, separator_index). ``separator_index`` is the
        index of the ``---`` line, or ``len(lines)`` when none is found.
    """
    for i, line in enumerate(lines):
        if line.strip() == "---":
            return lines[:i], i
    return lines.copy(), len(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _collect_files(paths: list[Path]) -> list[Path]:
    """Expand paths to a flat list of markdown files, excluding README.md.

    Args:
        paths: Files or directories provided by the caller.

    Returns:
        Sorted, deduplicated list of ``.md`` file paths.
    """
    collected: list[Path] = []
    for p in paths:
        if p.is_file():
            if p.suffix == ".md" and p.name != "README.md":
                collected.append(p.resolve())
        elif p.is_dir():
            collected.extend(f.resolve() for f in sorted(p.rglob("*.md")) if f.name != "README.md")
    seen: set[Path] = set()
    result: list[Path] = []
    for f in collected:
        if f not in seen:
            seen.add(f)
            result.append(f)
    return result


@app.command()
def migrate(
    paths: Annotated[
        list[Path] | None, typer.Argument(help="Files or directories to migrate. Defaults to ./research/.")
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would change without writing.")] = False,
    check: Annotated[bool, typer.Option("--check", help="Exit non-zero if any file needs migration.")] = False,
) -> None:
    """Migrate text-header research entries to YAML frontmatter format.

    Skips files that already use YAML frontmatter. Safe to run multiple times.
    """
    resolved_paths: list[Path] = paths or [Path("./research/")]
    research_root = _find_research_root(resolved_paths)
    files = _collect_files(resolved_paths)

    if not files:
        typer.echo("No markdown files found.")
        raise typer.Exit(0)

    needs_migration: list[Path] = []
    migrated: list[Path] = []
    skipped: list[Path] = []

    for filepath in files:
        changed, _message = migrate_file(filepath, research_root, dry_run=dry_run or check)
        relative = filepath.relative_to(research_root) if filepath.is_relative_to(research_root) else filepath
        if changed:
            needs_migration.append(filepath)
            if not dry_run and not check:
                migrated.append(filepath)
            typer.echo(f"  {'would migrate' if dry_run or check else 'migrated'}: {relative}")
        else:
            skipped.append(filepath)

    typer.echo(f"\nTotal: {len(files)} files")
    if dry_run or check:
        typer.echo(f"  needs migration: {len(needs_migration)}")
        typer.echo(f"  already yaml_frontmatter: {len(skipped)}")
    else:
        typer.echo(f"  migrated: {len(migrated)}")
        typer.echo(f"  skipped (already yaml_frontmatter): {len(skipped)}")

    if check and needs_migration:
        raise typer.Exit(1)


def _find_research_root(paths: list[Path]) -> Path:
    """Determine the research root directory from the provided path list.

    Uses the first directory in the list, or the parent of the first file.

    Args:
        paths: Paths supplied by the caller.

    Returns:
        A Path representing the root for relative path computation.
    """
    for p in paths:
        resolved = p.resolve()
        return resolved if resolved.is_dir() else resolved.parent
    return Path.cwd()


if __name__ == "__main__":
    app()
