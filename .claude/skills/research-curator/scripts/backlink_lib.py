#!/usr/bin/env -S uv run --quiet --script
# noqa: SIZE_OK - Existing shared backlink API kept intact; this change adds only its extraction-cache seam.
# /// script
# requires-python = ">=3.11"
# dependencies = ["marko>=2.0.0", "pydantic>=2.12.5"]
#
# [tool.ty.environment]
# root = ["."]
# ///
"""Shared library for backlink detection: cross-reference table parsing, relationship-description transforms, and idempotent backlink emission."""

from __future__ import annotations

import importlib.metadata
import pathlib
import re
import sqlite3
import sys
from contextlib import suppress

import marko
import marko.block
import marko.ext.gfm.elements as gfm_elements
import marko.inline

from backlink_cache import CrossReferenceExtractionCache, content_sha256
from backlink_models import CrossReferenceScan, CrossRefRow, ScanSkip

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_H2_LEVEL = 2
_CROSS_REF_MIN_COLS = 3
_TABLE_SEPARATOR_MIN_PIPES = 2
_EXTRACTION_CACHE_VERSION = 1
_PARSER_FINGERPRINT = f"marko={importlib.metadata.version('marko')};extractor={_EXTRACTION_CACHE_VERSION}"
_NON_ENTRY_FILENAMES = {"README.md", "CLAUDE.md", "AGENTS.md"}


# ---------------------------------------------------------------------------
# Deterministic relationship-description transform
#
# There used to be a verb-substitution table here (INVERSE_VERBS) that tried to
# invert forward relationship prose into a reciprocal claim -- e.g. "provides X"
# became "consumes X provided by". Removed per #3524: measuring it against the
# real vault corpus (823 asymmetric edges) showed 767/823 forward phrases never
# matched a verb at all, 21/823 matched a verb and got inverted, and 35/823 hit
# the same-category "shares" rule. Of the 21 verb-matched rows, at least one
# produced a confidently-worded but false integration claim (a "provides AST
# graph context ... through MCP" row inverted into an MCP integration that does
# not exist). A human hand-inverting the same corpus for PR #3510, working file
# by file with full context, made the identical class of mistake twice out of
# seven tries. If careful manual inversion has a two-in-seven false-claim rate,
# a fixed verb table applied blindly across 823 pairs is not going to do better.
#
# The next attempt replaced verb inversion with verbatim attribution -- quote
# the forward phrase under a "cites this entry:" prefix instead of inverting
# it. That is *also* unsound, for a different reason: cross-reference-format.md
# establishes the Entry column as the relationship phrase's grammatical
# subject ("provides the embedding layer this tool queries" -- Entry is the
# provider). A forward phrase living in source's table, in the row whose Entry
# is target, describes target, not source. Copying that phrase verbatim into a
# new row written into target's file, with Entry set to source, keeps the same
# words attached to the wrong subject -- e.g. Syft's row about Hound
# ("complements SBOM generation with hypothesis-driven security analysis")
# describes Hound's capability; quoting it back into hound.md under
# Entry=Syft reads as attributing hypothesis-driven security analysis to
# Syft. Measured: 27/788 attributed rows lead with an active capability verb
# and 63/788 name the target's own display name -- both patterns that read as
# a claim about the wrong entity once relocated. Only a phrase that is true
# regardless of which side is named as subject (a mutual "shares" relation) is
# safe to reuse verbatim; see the same-category "shares" rule below.
#
# A deterministic transform has no way to verify whether a described
# integration is real, and no way to safely re-subject arbitrary prose written
# for a different Entry -- so it must not assert either. See
# transform_to_backlink_description below.
# ---------------------------------------------------------------------------


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


def parse_cross_references_table_with_parser(entry_markdown: str, parser: marko.Markdown) -> list[CrossRefRow]:
    """Parse Cross-References rows with a caller-owned serial Marko parser.

    Args:
        entry_markdown: Full text of a research entry.
        parser: Marko GFM parser owned by the calling thread.

    Returns:
        Ordered table rows, or an empty list when no target table exists.
    """
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


class CachedExtractor:
    """Reuse one Marko parser and optional cache, requesting a clean restart after late cache failure."""

    def __init__(self, cache_path: pathlib.Path | None, quiet: bool) -> None:
        """Create a serial extractor for one graph scan.

        Args:
            cache_path: SQLite cache path, or None for uncached extraction.
            quiet: Suppress cache-fallback warnings when true.
        """
        self._quiet = quiet
        self._parser = marko.Markdown(extensions=["gfm"])
        self._cache: CrossReferenceExtractionCache | None = None
        self.files_parsed = 0
        self.cache_hits = 0
        self.requires_uncached_restart = False
        if cache_path is not None:
            try:
                self._cache = CrossReferenceExtractionCache(cache_path)
            except (OSError, sqlite3.Error) as exc:
                self._disable_cache(exc)

    def _disable_cache(self, exc: OSError | sqlite3.Error) -> None:
        if self._cache is not None:
            with suppress(OSError, sqlite3.Error):
                self._cache.close()
        self._cache = None
        if not self._quiet:
            print(f"warning: extraction-cache-disabled: {exc}", file=sys.stderr)

    def extract(self, content: bytes, text: str) -> list[CrossRefRow]:
        """Return cached or freshly parsed rows for one document.

        Args:
            content: Exact document bytes used as the cache identity.
            text: UTF-8-decoded document passed to Marko on a miss.

        Returns:
            Ordered Cross-References rows.
        """
        content_identity = content_sha256(content)
        if self._cache is not None:
            try:
                cached_rows = self._cache.get(content_identity, _PARSER_FINGERPRINT)
            except (OSError, sqlite3.Error) as exc:
                self.requires_uncached_restart = self.files_parsed > 0 or self.cache_hits > 0
                self._disable_cache(exc)
            else:
                if cached_rows is not None:
                    self.cache_hits += 1
                    return cached_rows

        self.files_parsed += 1
        rows = parse_cross_references_table_with_parser(text, self._parser)
        if self._cache is not None:
            self._cache.put(content_identity, _PARSER_FINGERPRINT, rows)
        return rows

    def close(self) -> None:
        """Commit complete extractions and close the optional cache."""
        if self._cache is None:
            return
        try:
            self._cache.commit()
        except (OSError, sqlite3.Error) as exc:
            self._disable_cache(exc)
            return
        with suppress(OSError, sqlite3.Error):
            self._cache.close()
        self._cache = None


def record_scan_skip(skips: list[ScanSkip], relative_file: pathlib.Path, reason: str, message: str) -> None:
    """Record one coverage hole for the scan result.

    Args:
        skips: Scan result list to append to.
        relative_file: Affected path relative to the vault.
        reason: Scan phase that failed.
        message: Human-readable failure detail.
    """
    skips.append(ScanSkip(path=relative_file.as_posix(), reason=reason, detail=message))


def resolve_targets(
    source: pathlib.Path, relative_file: pathlib.Path, cross_reference_rows: list[CrossRefRow], skips: list[ScanSkip]
) -> list[pathlib.Path]:
    """Resolve currently existing targets for parsed rows.

    Args:
        source: Absolute source-entry path.
        relative_file: Source path relative to the vault.
        cross_reference_rows: Parsed Cross-References rows.
        skips: Scan result list for resolution failures.

    Returns:
        Resolved targets that currently exist.
    """
    targets: list[pathlib.Path] = []
    for row in cross_reference_rows:
        try:
            target = resolve_link_path(source, row.link_path)
        except (OSError, ValueError) as exc:
            record_scan_skip(skips, relative_file, "resolve", f"resolve {row.link_path!r} in {relative_file}: {exc}")
            continue
        if target.exists():
            targets.append(target)
    return targets


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
    return parse_cross_references_table_with_parser(entry_markdown, marko.Markdown(extensions=["gfm"]))


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


def bare_reference_description(source_name: str, source_category: str) -> str:
    """Return the relationship text used when no more specific description is safe.

    This is the single source of truth for that one literal string. It covers two
    distinct situations, both of which have no true, specific relationship claim
    available:

    - transform_to_backlink_description falls back here for any forward phrase it
      cannot safely reuse (i.e. anything that isn't a mutual "shares" relation) --
      reusing the phrase's own words under a different Entry would misattribute
      whatever it describes to the wrong entity (see that function's docstring).
    - A caller with no parseable forward row at all (e.g. a malformed or
      unresolvable Cross-References table) has no phrase to work from in the first
      place.

    Args:
        source_name: Display name of the source entry (the one adding the backlink).
        source_category: Category of the source entry.

    Returns:
        A deterministic, content-free reference description.
    """
    return f"referenced by {source_name} ({source_category})"


# "shares" as the phrase's whole first word, not a prefix of one. Without \b,
# "shareset semantics differ" matches and asserts nothing symmetric.
_SHARES_LEAD_PATTERN = re.compile(r"^\s*shares\b", re.IGNORECASE)


def phrase_is_symmetric_shares(forward_phrase: str, source_name: str) -> bool:
    """Report whether a forward phrase stays true with either entry as its subject.

    This table's Entry column is the relationship phrase's grammatical subject,
    so a phrase can only be reused verbatim under a different Entry when its
    truth does not depend on which side that is. Two conditions, both required:

    1. The phrase leads with the symmetric verb "shares" as a whole word, so it
       carries no leading clause describing one particular entity.
    2. The phrase does not name ``source_name`` as the object of "with". A
       phrase shaped "shares <X> with <source>" satisfies (1) and is still not
       symmetric: the backlink row names the source as Entry, so the phrase's
       subject becomes the entity its own "with" clause names, and the row
       asserts "Robyn shares a queueing model with Robyn".

       Only the "with" construction is rejected, because only it makes subject
       and object the same entity. A phrase that merely mentions the source
       elsewhere -- "Shares Tauri + Rust cross-platform desktop architecture;
       Yume focuses on multi-agent orchestration UI" -- is redundant under the
       source's own Entry, not false, and stays eligible. Seven of the thirty-one
       "shares"-leading rows in the corpus mention their source that way, and
       none of the thirty-one names it as the object of "with"; rejecting the
       seven would replace true content with the bare fallback for no gain.

    Args:
        forward_phrase: The relationship description from the forward row.
        source_name: Display name of the source entry, which becomes the Entry
            -- and therefore the subject -- of the backlink row.

    Returns:
        ``True`` when the phrase is safe to carry over verbatim.
    """
    if not _SHARES_LEAD_PATTERN.match(forward_phrase):
        return False
    return re.search(rf"\bwith\s+{re.escape(source_name)}\b", forward_phrase, re.IGNORECASE) is None


def transform_to_backlink_description(
    forward_phrase: str, source_name: str, source_category: str, target_category: str
) -> str:
    """Transform a forward relationship phrase into a backlink relationship phrase.

    This function never invents a new directional relationship claim, and never
    reattributes an existing one to the wrong entity. cross-reference-format.md
    establishes the Entry column as the relationship phrase's grammatical subject:
    a phrase living in source's table, in the row whose Entry is target, describes
    target -- not source. Quoting that phrase verbatim into a new row written into
    target's file, with Entry set to source, would keep the same words attached to
    a different subject than the one they were written about (see the module-level
    comment above this section for a worked example and the corpus measurement).
    Verb inversion has the same problem plus an unverifiable direction change on
    top. Neither is safe for arbitrary prose.

    Exactly one category of forward phrase is safe to reuse as-is: a phrase whose
    truth does not depend on which side is named as subject. "Shares" is the only
    such case this function recognizes:

    1. If source_category == target_category and
       ``phrase_is_symmetric_shares(forward_phrase, source_name)``, append
       "(bidirectional)". That predicate holds two conditions, and the invariant
       needs both -- leading "shares" alone does not make a phrase symmetric:

       a. "shares" is the phrase's whole first word. A substring test admits the
          far more common corpus shape
          "<descriptor of the target>; shares <X> with <source>", whose leading
          clause describes exactly one entity. Relocating that phrase under a row
          whose Entry is the *other* entity re-attributes the descriptor. A
          prefix test without a word boundary is not enough either: "shareset
          semantics differ" starts with those six letters and asserts nothing
          symmetric.
       b. The phrase does not name the source entry. "shares <X> with <source>"
          passes (a) -- it leads with the verb and carries no leading clause --
          and is still not symmetric, because the backlink row names the source
          as Entry and this table's Entry column is the phrase's grammatical
          subject. The result reads "Robyn shares a queueing model with Robyn".
          Rule 2's fallback is correct for it.

       No row in the current corpus exhibits either shape; both conditions are
       guards against a phrase a future entry could legitimately write.
       See tests/research_backlinks/test_relationship_transform.py.
    2. Otherwise, fall back to bare_reference_description(). This is a deliberate
       floor, not a placeholder: cross-reference-format.md's "no generic label" bar
       governs human/agent-authored forward rows, where a specific phrase is
       achievable by reading both entries. A machine transform working from one
       already-written phrase cannot safely produce a specific claim about a
       *different* entity than the one that phrase was written about, so naming
       the source entry and its category -- with no relationship content beyond
       that -- is the only description this function can guarantee is true.

    Args:
        forward_phrase: The relationship description from the forward cross-reference row.
        source_name: Display name of the source entry (the one adding the backlink).
        source_category: Category of the source entry.
        target_category: Category of the target entry, used only for the same-category
            "shares" check in rule 1.

    Returns:
        A deterministic backlink relationship description string.
    """
    if source_category == target_category and phrase_is_symmetric_shares(forward_phrase, source_name):
        return f"{forward_phrase} (bidirectional)"

    return bare_reference_description(source_name, source_category)


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
    If ## Cross-References is absent: creates the section after freshness_anchor when
    that heading exists (legacy text-header entries), falling back to inserting after
    "## References" when it does not (frontmatter-only entries have no body Freshness
    Tracking heading) — matching the same fallback used by research-cross-referencer.md.

    Args:
        target_entry_markdown: Full text of the target entry markdown file.
        row: CrossRefRow to append.
        freshness_anchor: Heading line (with ## prefix) marking the preferred insertion
            point when the Cross-References section does not yet exist. Falls back to
            "## References" when this heading is absent.

    Returns:
        Tuple of (new_markdown, modified) where modified is False when no change was
        made (row already present) and True when the markdown was updated.

    Raises:
        ValueError: When neither freshness_anchor nor "## References" is found and no
            Cross-References section exists — insertion point cannot be determined.
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

    # ## Cross-References absent — insert after freshness_anchor, falling back to ## References
    anchor_idx: int | None = None
    for i, line in enumerate(lines_stripped):
        if line.strip() == freshness_anchor:
            anchor_idx = i
            break

    if anchor_idx is None:
        for i, line in enumerate(lines_stripped):
            if line.strip() == "## References":
                anchor_idx = i
                break

    if anchor_idx is None:
        raise ValueError(
            f"Cannot insert Cross-References section: neither '{freshness_anchor}' nor "
            "'## References' found in entry, and no existing Cross-References section present."
        )

    insert_idx = _find_freshness_insert_index(lines_stripped, anchor_idx)

    # Only prepend a horizontal rule when the preceding content does not already end with one,
    # otherwise the new section lands under a doubled "---\n\n---" separator.
    preceding = next((ln for ln in reversed(lines_stripped[:insert_idx]) if ln.strip()), "")
    separator = [] if preceding.strip() == "---" else ["", "---"]

    new_section_lines = [
        *separator,
        "",
        "## Cross-References",
        "",
        "| Entry | Category | Relationship |",
        "|-------|----------|--------------|",
        new_table_row,
    ]

    new_lines = lines_stripped[:insert_idx] + new_section_lines + lines_stripped[insert_idx:]
    return ("\n".join(new_lines) + ("\n" if ends_with_newline else ""), True)


def build_cross_reference_graph(
    vault_root: pathlib.Path, *, quiet: bool = False, cache_path: pathlib.Path | None = None
) -> CrossReferenceScan:
    """Scan the vault and return its cross-reference edge graph plus every skipped file.

    Walks all .md files under vault_root (excluding README.md), parses each entry's
    Cross-References table, and records directed edges (entry -> cited_entry).

    A file this function cannot read, parse, or resolve a link from is dropped from
    the graph and recorded in ``skips``. It is never fatal: one damaged entry does not
    abort the scan. Because the skips are returned alongside the graph, a caller that
    treats an empty asymmetric-edge list as "the vault is clean" can check whether the
    scan actually covered the vault first.

    Args:
        vault_root: Absolute path to the research vault root directory.
        quiet: When True, suppress ``warning: scan-skipped`` stderr output. The skips
            are still recorded in the returned ``skips`` list. ``check-backlinks --fix``
            calls this twice per run -- once to find asymmetric edges, once more
            afterward to verify none remain -- and a scan-skip is a pre-existing file
            defect the fix step never touches, so the second call would otherwise
            reprint every skip already reported by the first.
        cache_path: Optional SQLite path for successful extraction results. Entries
            are keyed by exact file bytes and parser version. Link resolution and
            target existence are always recomputed from the current filesystem. A
            cache read failure after earlier documents discards the partial pass and
            restarts the complete scan without a cache.

    Returns:
        A CrossReferenceScan whose ``graph`` maps each entry's absolute Path to the
        absolute Paths it cites, and whose ``skips`` lists every dropped file in
        vault-walk order. Entries with no Cross-References section appear in the graph
        with an empty list.
    """
    vault_root = vault_root.resolve()
    graph: dict[pathlib.Path, list[pathlib.Path]] = {}
    skips: list[ScanSkip] = []
    extractor = CachedExtractor(cache_path, quiet)

    try:
        for md_file in sorted(vault_root.rglob("*.md")):
            if md_file.name in _NON_ENTRY_FILENAMES:
                continue
            abs_file = md_file.resolve()
            rel_file = md_file.relative_to(vault_root)
            graph.setdefault(abs_file, [])

            try:
                content = md_file.read_bytes()
                text = content.decode("utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                record_scan_skip(skips, rel_file, "read", f"read {rel_file}: {exc}")
                continue

            try:
                rows = extractor.extract(content, text)
            except ValueError as exc:
                if extractor.requires_uncached_restart:
                    break
                record_scan_skip(skips, rel_file, "parse", f"parse {rel_file}: {exc}")
                continue
            if extractor.requires_uncached_restart:
                break
            graph[abs_file].extend(resolve_targets(abs_file, rel_file, rows, skips))
    finally:
        extractor.close()

    if extractor.requires_uncached_restart:
        return build_cross_reference_graph(vault_root, quiet=quiet, cache_path=None)

    if not quiet:
        for skip in skips:
            print(f"warning: scan-skipped, could not {skip.detail}", file=sys.stderr)

    return CrossReferenceScan(
        graph=graph, skips=skips, files_parsed=extractor.files_parsed, cache_hits=extractor.cache_hits
    )


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
