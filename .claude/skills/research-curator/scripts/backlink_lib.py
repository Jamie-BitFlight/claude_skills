#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["marko>=2.0.0"]
# ///
"""Shared library for backlink detection: cross-reference table parsing, relationship-description transforms, and idempotent backlink emission."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import marko
import marko.block
import marko.ext.gfm.elements as gfm_elements
import marko.inline

if TYPE_CHECKING:
    import pathlib


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class CrossRefRow:
    """A single row from a Cross-References markdown table."""

    entry_name: str
    link_path: str
    category: str
    relationship: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_H2_LEVEL = 2
_CROSS_REF_MIN_COLS = 3
_TABLE_SEPARATOR_MIN_PIPES = 2


# ---------------------------------------------------------------------------
# Deterministic relationship-description transform
# ---------------------------------------------------------------------------

INVERSE_VERBS: dict[str, str] = {
    "provides": "consumes",
    "consumes": "provides",
    "extends": "is extended by",
    "is extended by": "extends",
    "wraps": "is wrapped by",
    "is wrapped by": "wraps",
    "feeds": "is fed by",
    "is fed by": "feeds",
    "orchestrates": "is orchestrated by",
    "is orchestrated by": "orchestrates",
    "delegates to": "receives delegation from",
    "receives delegation from": "delegates to",
    "calls": "is called by",
    "is called by": "calls",
    "implements": "is implemented by",
    "is implemented by": "implements",
    "replaces": "is replaced by",
    "is replaced by": "replaces",
    "competes with": "competes with",
    "complements": "is complemented by",
    "is complemented by": "complements",
    "alternatives to": "alternative for",
    "alternative for": "alternatives to",
    "extends pattern from": "pattern extended by",
    "pattern extended by": "extends pattern from",
}

# Verbs that follow "V X" -> "inverse X" pattern
_SYMMETRIC_REST_VERBS = frozenset({"extends", "wraps", "feeds", "orchestrates", "calls", "implements", "replaces"})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _extract_text(node: object) -> str:
    """Recursively extract plain text from a marko node tree.

    Returns:
        Concatenated plain-text string from all leaf RawText nodes.
    """
    children = getattr(node, "children", None)
    if isinstance(children, str):
        return children
    if isinstance(children, list):
        return "".join(_extract_text(child) for child in children)
    return ""


def _extract_row(row_node: gfm_elements.TableRow) -> CrossRefRow:
    """Extract a CrossRefRow from a non-header marko TableRow.

    Args:
        row_node: The TableRow AST node to parse.

    Returns:
        A populated CrossRefRow instance.

    Raises:
        ValueError: When the row has fewer than the required column count, or when
            the Entry cell does not contain a markdown link.
    """
    row_children: list[object] = getattr(row_node, "children", [])
    if len(row_children) < _CROSS_REF_MIN_COLS:
        raise ValueError(
            f"Cross-References table row has {len(row_children)} cells, expected at least {_CROSS_REF_MIN_COLS}"
        )

    entry_cell = row_children[0]
    category_cell = row_children[1]
    relationship_cell = row_children[2]

    # Extract link from Entry cell
    entry_cell_children: list[object] = getattr(entry_cell, "children", [])
    link_node: object | None = None
    for cell_child in entry_cell_children:
        if isinstance(cell_child, marko.inline.Link):
            link_node = cell_child
            break

    if link_node is None:
        raise ValueError("Cross-References table Entry cell does not contain a markdown link")

    entry_name = _extract_text(link_node).strip()
    link_path: str = getattr(link_node, "dest", "")
    category = _extract_text(category_cell).strip()
    relationship = _extract_text(relationship_cell).strip()

    return CrossRefRow(entry_name=entry_name, link_path=link_path, category=category, relationship=relationship)


def _parse_table_rows(table_node: gfm_elements.Table) -> list[CrossRefRow]:
    """Extract all data rows from a Cross-References table node.

    Args:
        table_node: The marko Table AST node.

    Returns:
        List of CrossRefRow instances, one per non-header data row.

    Raises:
        ValueError: When any data row is malformed (propagated from _extract_row).
    """
    rows: list[CrossRefRow] = []
    table_children: list[object] = getattr(table_node, "children", [])
    for row_node in table_children:
        if not isinstance(row_node, gfm_elements.TableRow):
            continue
        row_cell_children: list[object] = getattr(row_node, "children", [])
        if row_cell_children and isinstance(row_cell_children[0], gfm_elements.TableCell):
            first_cell = row_cell_children[0]
            if getattr(first_cell, "header", False):
                continue
        rows.append(_extract_row(row_node))
    return rows


def _invert_directional_verb(verb: str, inverse: str, rest: str, source_name: str, source_category: str) -> str:
    """Apply directional verb inversion to produce a backlink phrase.

    Args:
        verb: The matched forward verb (lowercase).
        inverse: The inverse of the verb from INVERSE_VERBS.
        rest: The remainder of the phrase after removing the verb.
        source_name: Display name of the source entry.
        source_category: Category of the source entry.

    Returns:
        The inverted relationship phrase.
    """
    if verb == "provides":
        return f"consumes {rest} provided by"
    if verb in _SYMMETRIC_REST_VERBS:
        if rest:
            return f"{inverse} {rest}"
        return f"{inverse} {source_name} ({source_category})"
    if verb == "complements":
        return f"is complemented by {source_name} ({source_category})"
    # Generic verb swap
    if rest:
        return f"{inverse} {rest}"
    return f"{inverse} {source_name} ({source_category})"


def _find_table_insert_index(lines_stripped: list[str], heading_idx: int) -> int:
    """Locate the index after the last table row following a Cross-References heading.

    Args:
        lines_stripped: All document lines with trailing whitespace stripped.
        heading_idx: Line index (0-based) of the ## Cross-References heading.

    Returns:
        0-based index at which the new row should be inserted.
    """
    last_table_row_idx: int | None = None
    table_end_idx = heading_idx + 1
    past_header = False

    for i in range(heading_idx + 1, len(lines_stripped)):
        stripped = lines_stripped[i]
        if stripped.startswith("|"):
            is_separator = not past_header and "---" in stripped and stripped.count("|") >= _TABLE_SEPARATOR_MIN_PIPES
            if is_separator:
                past_header = True
            last_table_row_idx = i
            table_end_idx = i + 1
        elif stripped.startswith("## "):
            table_end_idx = i
            break
        elif stripped in {"", "---"} and last_table_row_idx is not None:
            # Only stop on blank lines / separators once we have seen at least one table row.
            # A blank line between the heading and the table header must not end the scan.
            table_end_idx = i
            break

    return last_table_row_idx + 1 if last_table_row_idx is not None else table_end_idx


def _find_freshness_insert_index(lines_stripped: list[str], anchor_idx: int) -> int:
    """Locate the index at which a new Cross-References section should be inserted.

    Scans forward from anchor_idx to find the next ## heading or end of document.

    Args:
        lines_stripped: All document lines with trailing whitespace stripped.
        anchor_idx: Line index (0-based) of the freshness anchor heading.

    Returns:
        0-based index at which the new section block should be inserted.
    """
    for i in range(anchor_idx + 1, len(lines_stripped)):
        stripped = lines_stripped[i]
        if stripped.startswith("## ") and not stripped.startswith("### "):
            return i
    return len(lines_stripped)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_cross_references_table(entry_markdown: str) -> list[CrossRefRow]:
    """Parse the Cross-References markdown table from an entry using marko AST.

    Walks the marko AST looking for a Heading with text "Cross-References" followed
    by a Table node. Extracts each non-header row as a CrossRefRow.

    Args:
        entry_markdown: Full text of a research entry markdown file.

    Returns:
        List of CrossRefRow instances, one per data row in the table.
        Returns an empty list when no Cross-References section or table is found.

    Raises:
        ValueError: When a Cross-References section exists but contains a malformed
            table (e.g., wrong column count, missing link in Entry cell).
    """
    parser = marko.Markdown(extensions=["gfm"])
    doc = parser.parse(entry_markdown)

    doc_children: list[object] = getattr(doc, "children", [])
    in_cross_ref_section = False

    for node in doc_children:
        if isinstance(node, marko.block.Heading) and node.level == _H2_LEVEL:
            heading_text = _extract_text(node).strip()
            in_cross_ref_section = heading_text == "Cross-References"
            continue

        if isinstance(node, marko.block.Heading):
            in_cross_ref_section = False
            continue

        if not in_cross_ref_section:
            continue

        if isinstance(node, gfm_elements.Table):
            return _parse_table_rows(node)

    return []


def extract_section_block(entry_markdown: str, heading: str) -> tuple[int, int] | None:
    """Find the start and end line numbers of a section body.

    Args:
        entry_markdown: Full text of a research entry markdown file.
        heading: The exact section heading text (without leading "## ").

    Returns:
        A (start_line, end_line) tuple (1-indexed, inclusive) for the section body
        (lines after the heading line up to but not including the next heading or
        end of file). Returns None if the heading is not found.
    """
    lines = entry_markdown.splitlines()
    heading_marker = f"## {heading}"
    start: int | None = None
    start_line: int | None = None

    for i, line in enumerate(lines):
        if line.strip() == heading_marker:
            start = i
            start_line = i + 2  # 1-indexed body start (heading line + 1)
            break

    if start is None or start_line is None:
        return None

    end_line = len(lines)
    for i in range(start + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("## ") and not stripped.startswith("### "):
            end_line = i
            break

    return (start_line, end_line)


def resolve_link_path(source_entry_path: pathlib.Path, link: str) -> pathlib.Path:
    """Resolve a relative markdown link to an absolute filesystem path.

    Args:
        source_entry_path: Absolute path to the entry file containing the link.
        link: Relative link string from the Cross-References table (e.g. "../cat/file.md").

    Returns:
        Resolved absolute Path.
    """
    return (source_entry_path.parent / link).resolve()


def category_of(entry_path: pathlib.Path, vault_root: pathlib.Path) -> str:
    """Return the category name of an entry (its parent directory name relative to vault).

    For an entry at vault_root/agent-frameworks/foo.md this returns "agent-frameworks".

    Args:
        entry_path: Absolute path to the entry file.
        vault_root: Absolute path to the vault root directory.

    Returns:
        Parent directory name of the entry relative to vault_root.

    Raises:
        ValueError: When entry_path is not inside vault_root.
    """
    try:
        relative = entry_path.relative_to(vault_root)
    except ValueError as exc:
        raise ValueError(f"Entry path {entry_path} is not inside vault root {vault_root}") from exc
    return relative.parts[0] if len(relative.parts) > 1 else entry_path.parent.name


def transform_to_backlink_description(
    forward_phrase: str, source_name: str, source_category: str, target_category: str
) -> str:
    """Transform a forward relationship phrase into a backlink relationship phrase.

    Rules applied in order:
    1. If forward_phrase starts with a known verb from INVERSE_VERBS, invert it.
    2. If source_category == target_category and "shares" appears in forward_phrase,
       append "(bidirectional)".
    3. Fallback: return "referenced by {source_name} ({source_category})".

    Args:
        forward_phrase: The relationship description from the forward cross-reference row.
        source_name: Display name of the source entry (the one adding the backlink).
        source_category: Category of the source entry.
        target_category: Category of the target entry (unused directly; kept for callers
            that may extend rule logic for cross-category cases in future).

    Returns:
        A deterministic backlink relationship description string.
    """
    phrase_lower = forward_phrase.lower()

    # Rule 1: directional verb inversion
    for verb, inverse in INVERSE_VERBS.items():
        if phrase_lower.startswith(verb):
            rest = forward_phrase[len(verb) :].strip()
            return _invert_directional_verb(verb, inverse, rest, source_name, source_category)

    # Rule 2: same-category "shares" pattern
    if source_category == target_category and "shares" in phrase_lower:
        return f"{forward_phrase} (bidirectional)"

    # Rule 3: fallback
    return f"referenced by {source_name} ({source_category})"


def backlink_exists(target_entry_markdown: str, source_entry_path_link: str) -> bool:
    """Check whether a backlink row for source_entry_path_link already exists.

    Normalises the link path before comparison (strips leading "./").

    Args:
        target_entry_markdown: Full text of the target entry to check.
        source_entry_path_link: Relative link string that would appear in the backlink row.

    Returns:
        True if any existing row's link_path (after normalisation) matches the
        normalised source_entry_path_link.
    """
    rows = parse_cross_references_table(target_entry_markdown)
    normalised_source = source_entry_path_link.removeprefix("./")
    for row in rows:
        normalised_existing = row.link_path.removeprefix("./")
        if normalised_existing == normalised_source:
            return True
    return False


def append_backlink_row(
    target_entry_markdown: str, row: CrossRefRow, freshness_anchor: str = "## Freshness Tracking"
) -> tuple[str, bool]:
    """Append a new backlink row to the Cross-References table, or create the section.

    Idempotent: if the row's link_path already exists in the table, returns the
    original markdown unchanged with modified=False.

    If ## Cross-References exists: appends the new table row at the end of the table.
    If ## Cross-References is absent: creates the section after freshness_anchor,
    matching the canonical format from research-cross-referencer.md.

    Args:
        target_entry_markdown: Full text of the target entry markdown file.
        row: CrossRefRow to append.
        freshness_anchor: Heading line (with ## prefix) marking the insertion point
            when the Cross-References section does not yet exist.

    Returns:
        Tuple of (new_markdown, modified) where modified is False when no change was
        made (row already present) and True when the markdown was updated.

    Raises:
        ValueError: When freshness_anchor is not found and no Cross-References section
            exists — insertion point cannot be determined.
    """
    # Idempotency check
    if backlink_exists(target_entry_markdown, row.link_path):
        return (target_entry_markdown, False)

    new_table_row = f"| [{row.entry_name}]({row.link_path}) | {row.category} | {row.relationship} |"
    ends_with_newline = target_entry_markdown.endswith("\n")
    lines_stripped = [ln.rstrip("\n").rstrip("\r") for ln in target_entry_markdown.splitlines()]

    # Check whether ## Cross-References already exists
    cross_ref_heading_idx: int | None = None
    for i, line in enumerate(lines_stripped):
        if line.strip() == "## Cross-References":
            cross_ref_heading_idx = i
            break

    if cross_ref_heading_idx is not None:
        insert_idx = _find_table_insert_index(lines_stripped, cross_ref_heading_idx)
        new_lines = [*lines_stripped[:insert_idx], new_table_row, *lines_stripped[insert_idx:]]
        return ("\n".join(new_lines) + ("\n" if ends_with_newline else ""), True)

    # ## Cross-References absent — insert after freshness_anchor
    anchor_idx: int | None = None
    for i, line in enumerate(lines_stripped):
        if line.strip() == freshness_anchor:
            anchor_idx = i
            break

    if anchor_idx is None:
        raise ValueError(
            f"Cannot insert Cross-References section: '{freshness_anchor}' not found in entry "
            "and no existing Cross-References section present."
        )

    insert_idx = _find_freshness_insert_index(lines_stripped, anchor_idx)

    new_section_lines = [
        "",
        "---",
        "",
        "## Cross-References",
        "",
        "| Entry | Category | Relationship |",
        "|-------|----------|--------------|",
        new_table_row,
    ]

    new_lines = lines_stripped[:insert_idx] + new_section_lines + lines_stripped[insert_idx:]
    return ("\n".join(new_lines) + ("\n" if ends_with_newline else ""), True)


def build_cross_reference_graph(vault_root: pathlib.Path) -> dict[pathlib.Path, list[pathlib.Path]]:
    """Build a directed adjacency list of all cross-reference edges in the vault.

    Walks all .md files under vault_root (excluding README.md), parses each entry's
    Cross-References table, and records directed edges (entry -> cited_entry).

    Args:
        vault_root: Absolute path to the research vault root directory.

    Returns:
        Dict mapping each entry's absolute Path to a list of absolute Paths it cites.
        Entries with no Cross-References section appear with an empty list.
        Paths that cannot be resolved (broken links) are silently skipped.
    """
    graph: dict[pathlib.Path, list[pathlib.Path]] = {}

    for md_file in sorted(vault_root.rglob("*.md")):
        if md_file.name == "README.md":
            continue
        abs_file = md_file.resolve()
        graph.setdefault(abs_file, [])

        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError:
            continue

        try:
            rows = parse_cross_references_table(text)
        except ValueError:
            continue

        for row_item in rows:
            try:
                target = resolve_link_path(abs_file, row_item.link_path)
            except (OSError, ValueError):
                continue
            if target.exists():
                graph[abs_file].append(target)

    return graph


def find_asymmetric_edges(graph: dict[pathlib.Path, list[pathlib.Path]]) -> list[tuple[pathlib.Path, pathlib.Path]]:
    """Detect (source, target) pairs without a reciprocal (target -> source) edge.

    Args:
        graph: Directed adjacency list as returned by build_cross_reference_graph.

    Returns:
        List of (source, target) tuples where target does not list source in its
        adjacency list. Deterministically ordered by source path then target path.
    """
    asymmetric: list[tuple[pathlib.Path, pathlib.Path]] = []

    for source, targets in sorted(graph.items()):
        for target in sorted(set(targets)):
            reciprocal_targets = graph.get(target, [])
            if source not in reciprocal_targets:
                asymmetric.append((source, target))

    return asymmetric
