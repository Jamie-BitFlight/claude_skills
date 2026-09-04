"""GitHub sync adapter: YAML BacklogItem <-> GitHub issue body markdown conversion.

This module owns the conversion boundary between the local YAML BacklogItem
representation and GitHub issue body markdown.  Operations.py and the MCP
server never write raw markdown body strings directly — they go through this
adapter.

Dependency direction (must remain acyclic):
    models <- parsing <- entry_blocks <- github_sync

Do not import from gh_client.py, operations.py, or server.py.
"""

from __future__ import annotations

import re

from . import rendering as _rendering
from .artifact_registry import parse_manifest_section, render_manifest_section, replace_manifest_in_body
from .entry_blocks import _deduplicate_timestamps, _render_entry_raw, parse_entries
from .models import BacklogItem, GroomedData, Section, parse_issue_number
from .parsing import _GROOMED_DATE_RE, extract_sections

__all__ = [
    "SECTION_HEADING",
    "heading_to_section_key",
    "heading_to_unknown_key",
    "merge_item",
    "parse_issue_body",
    "render_issue_body",
    "unknown_key_to_heading",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_METADATA_BLOCK_RE = re.compile(r"<!--\s*backlog-metadata:\s*\n(.*?)\n-->", re.DOTALL)
_METADATA_LINE_RE = re.compile(r"^(\w+):\s*(.*)$")
# Groomed heading gate/date extraction: canonical pattern lives in
# parsing._GROOMED_DATE_RE (imported above), matched against the heading text
# with its "## " prefix already stripped, so this module and parsing.py's
# parse_md_body_sections (the legacy .md-file parser) can never disagree
# about what counts as a real "## Groomed (date)" heading.
_SUBSECTION_RE = re.compile(r"### ([^\n]+)\n([\s\S]*?)(?=\n### |\Z)")

# Re-exported from rendering — canonical definition lives in rendering.SECTION_HEADING
SECTION_HEADING = _rendering.SECTION_HEADING

# All known section keys plus "groomed" — used to identify unknown sections in render_issue_body
_KNOWN_SECTION_KEYS: frozenset[str] = frozenset(SECTION_HEADING) | {"groomed"}


def heading_to_section_key(heading_text: str) -> str | None:
    """Return the BacklogItem.sections key for a markdown heading text, or None if unknown.

    Routes through the same alias-aware :func:`~.section_registry.resolve_section_name`
    resolver the write boundary (``operations._normalize_section_key``) uses, so a
    registered historic heading spelling (e.g. ``"Facts check"``) resolves to its
    canonical key here too, instead of only exact :data:`SECTION_HEADING` display text.

    Args:
        heading_text: Heading text with ``##`` prefix stripped and whitespace trimmed.

    Returns:
        Normalised section key (e.g. ``"fact_check"``) or ``None`` when the heading
        does not correspond to a known section.
    """
    return _rendering.resolve_section_name(heading_text)


# Re-exported from rendering — canonical definitions live there so that the
# local-write path (operations._normalize_section_key) and the GitHub-parse
# path (parse_issue_body below) normalise unknown section names identically.
heading_to_unknown_key = _rendering.heading_to_unknown_key
unknown_key_to_heading = _rendering.unknown_key_to_heading


# ---------------------------------------------------------------------------
# render_issue_body helpers
# ---------------------------------------------------------------------------


def _render_section_entries(section: Section) -> str:
    """Render all entries in a Section as concatenated div blocks.

    Args:
        section: Section whose entries to render.

    Returns:
        Entry blocks joined by blank lines.
    """
    return "\n\n".join(_render_entry_raw(e) for e in section.entries)


def _render_groomed(groomed: GroomedData) -> str:
    """Render a GroomedData as ``## Groomed ({date})`` with ### subsection children.

    Delegates to :func:`rendering.render_groomed_section` for shared
    backend-neutral rendering.  Kept for backward compatibility with existing
    callers that import this symbol directly from ``github_sync``.

    Args:
        groomed: GroomedData to render.

    Returns:
        Rendered section string (no trailing newline).
    """
    return _rendering.render_groomed_section(groomed)


# ---------------------------------------------------------------------------
# render_issue_body
# ---------------------------------------------------------------------------


def render_issue_body(item: BacklogItem, original_body: str | None = None) -> str:
    """Render a BacklogItem as a GitHub issue body markdown string.

    Embeds priority, type, status, and added metadata in an HTML comment block
    that is invisible in GitHub's rendered UI.  The description and all
    structured sections follow as visible markdown.

    When ``original_body`` is provided, any ``## Artifact Manifest`` section
    present in that body is extracted and re-appended to the rendered output so
    that manifests are preserved through write-back operations.

    Args:
        item: BacklogItem to render.
        original_body: Current GitHub issue body text, used to carry forward
            the artifact manifest section.  When ``None``, no manifest is
            appended (backwards-compatible default behaviour).

    Returns:
        Markdown-formatted issue body string ending with newline.
    """
    parts: list[str] = []

    # Invisible metadata comment block
    parts.append(
        "<!-- backlog-metadata:\n"
        f"priority: {item.priority}\n"
        f"type: {item.item_type}\n"
        f"status: {item.status}\n"
        f"added: {item.added}\n"
        "-->"
    )

    # Visible description section
    if item.description:
        parts.append(f"## Description\n\n{item.description}")

    # Entry-bearing sections in definition order
    for key, heading in SECTION_HEADING.items():
        sec = item.sections.get(key)
        if not isinstance(sec, Section) or not sec.entries:
            continue
        parts.append(f"## {heading}\n\n{_render_section_entries(sec)}")

    # Groomed section
    groomed_sec = item.sections.get("groomed")
    if isinstance(groomed_sec, GroomedData):
        parts.append(_render_groomed(groomed_sec))

    # Unknown sections — keys not in the known set and not "groomed"
    for key, sec in item.sections.items():
        if key in _KNOWN_SECTION_KEYS:
            continue
        if not isinstance(sec, Section) or not sec.entries:
            continue
        heading = unknown_key_to_heading(key)
        parts.append(f"## {heading}\n\n{_render_section_entries(sec)}")

    rendered = "\n\n".join(parts) + "\n"

    # Preserve the artifact manifest from the original body when available.
    if original_body is not None:
        issue_number = parse_issue_number(item.issue) or 0
        manifest = parse_manifest_section(original_body, issue_number)
        if manifest.artifacts:
            manifest_section = render_manifest_section(manifest)
            rendered = replace_manifest_in_body(rendered, manifest_section)

    return rendered


# ---------------------------------------------------------------------------
# parse_issue_body helpers
# ---------------------------------------------------------------------------


def _parse_metadata_block(body: str) -> dict[str, str]:
    """Extract key/value pairs from the ``<!-- backlog-metadata: -->`` comment.

    Args:
        body: Issue body text to search.

    Returns:
        Dict of metadata key/value pairs; empty dict if no comment found.
    """
    m = _METADATA_BLOCK_RE.search(body)
    if not m:
        return {}
    result: dict[str, str] = {}
    for line in m.group(1).splitlines():
        line_match = _METADATA_LINE_RE.match(line.strip())
        if line_match:
            result[line_match.group(1)] = line_match.group(2).strip()
    return result


def _parse_groomed_section(heading_name: str, content: str) -> GroomedData:
    """Parse a ``Groomed (date)`` heading name + body into a GroomedData model.

    Args:
        heading_name: Heading text with the ``## `` prefix already stripped,
            e.g. ``"Groomed (2026-03-01)"``.
        content: Section body text (content after the heading line).

    Returns:
        GroomedData with date and subsections populated.
    """
    date_match = _GROOMED_DATE_RE.match(heading_name)
    date = date_match.group(1).strip() if date_match else ""
    subsections: dict[str, str] = {}
    for sub_match in _SUBSECTION_RE.finditer(content):
        raw_sub_key = sub_match.group(1).strip()
        # Resolve through the same canonical subsection registry the write path
        # (operations._write_groomed_to_item) and the read-time fold
        # (rendering.normalize_groomed_subsections) use, so a GitHub-authored
        # "### priority" and a locally-written "Priority" collide on one key
        # instead of round-tripping as two separate subsections.
        sub_key = _rendering.resolve_subsection_name(raw_sub_key) or raw_sub_key
        sub_content = sub_match.group(2).strip()
        # When two ### headings in the same body collide onto one canonical
        # key (e.g. "### Priority" and "### priority"), the LONGER content
        # wins — the same rule _merge_groomed applies when merging local and
        # remote GroomedData — not whichever heading happens to appear last
        # in source order.
        existing = subsections.get(sub_key, "")
        subsections[sub_key] = sub_content if len(sub_content) > len(existing) else existing
    return GroomedData(date=date, subsections=subsections)


# ---------------------------------------------------------------------------
# parse_issue_body
# ---------------------------------------------------------------------------


def parse_issue_body(body: str, existing: BacklogItem | None = None) -> BacklogItem:
    """Parse a GitHub issue body markdown string into a BacklogItem.

    Extracts the ``<!-- backlog-metadata: -->`` comment for structured
    metadata, then parses ``## Section`` blocks into typed section models.
    Non-body fields (title, issue, source, plan, file_path) are carried over
    from ``existing`` when provided.

    Args:
        body: GitHub issue body text.
        existing: Optional BacklogItem to carry over non-body fields from.

    Returns:
        BacklogItem populated from the parsed issue body.
    """
    base = existing or BacklogItem()
    metadata = _parse_metadata_block(body)
    sections_raw = extract_sections(body)

    parsed_sections: dict[str, Section | GroomedData] = {}
    description = base.description

    for heading, content in sections_raw.items():
        # Strip leading "## " to get the plain heading name
        heading_name = heading.removeprefix("## ").strip()

        if heading_name == "Description":
            description = content.strip()
            continue

        # Groomed section: heading matches the canonical "## Groomed (date)" form only.
        # A loose `heading_name.startswith("Groomed")` check previously matched any
        # unregistered section whose title-cased fallback heading happens to be
        # "Groomed" (e.g. section key "GROOMED" -> unknown_key_to_heading ->
        # "Groomed", with no parens) -- misrouting a generic Section into
        # _parse_groomed_section and producing a GroomedData under "groomed"
        # alongside the correct "unknown__groomed" key, duplicating the section on
        # round-trip. Sharing parsing._GROOMED_DATE_RE with parse_md_body_sections
        # (the legacy .md-file parser, same collision class) means the two
        # parsers can't independently drift out of agreement on what counts as
        # a real Groomed heading.
        if _GROOMED_DATE_RE.match(heading_name):
            parsed_sections["groomed"] = _parse_groomed_section(heading_name, content)
            continue

        # Entry-bearing sections — routed through the same alias-aware resolver
        # the write boundary (operations._normalize_section_key) and the
        # subsection parser above use, so a registered historic heading (e.g.
        # "## Facts check") resolves to its canonical key here too instead of
        # only an exact SECTION_HEADING display-text match.
        section_key = _rendering.resolve_section_name(heading_name)
        target_key = section_key if section_key is not None else heading_to_unknown_key(heading_name)
        entries = parse_entries(content, show="all")
        # A canonical heading and one of its aliases (e.g. "## Fact-Check" and
        # "## Facts check") both resolve to the same target_key. Concatenate
        # rather than overwrite, so the earlier heading's entries are not
        # silently dropped (#3015 Greptile review finding) -- and use
        # _deduplicate_timestamps, not merge_entries, to reconcile any id
        # collision: unlike merge_item's local/remote reconciliation, these
        # are two literal, physically distinct headings in one document, not
        # two versions of the same logical entry, so an id-keyed "pick a
        # winner" merge is the wrong tool even before considering collisions.
        # A collision is also not a rare edge case here: unwrapped/legacy
        # content with no leading timestamp always falls back to the same
        # f"{added_date}T00:00:00Z" id (see entry_blocks.parse_entries), so
        # two colliding headings' unwrapped content would otherwise share an
        # id and merge_entries would keep only the struck/longer one.
        existing_section = parsed_sections.get(target_key)
        if isinstance(existing_section, Section):
            entries = [*existing_section.entries, *entries]
            _deduplicate_timestamps(entries)
        parsed_sections[target_key] = Section(entries=entries)

    return BacklogItem(
        title=base.title,
        description=description,
        sections=parsed_sections,
        priority=metadata.get("priority", base.priority),
        item_type=metadata.get("type", base.item_type),
        status=metadata.get("status", base.status),
        added=metadata.get("added", base.added),
        issue=base.issue,
        source=base.source,
        plan=base.plan,
        section=base.section,
        file_path=base.file_path,
    )


# ---------------------------------------------------------------------------
# merge_item helpers
# ---------------------------------------------------------------------------


# Re-exported from rendering — canonical definition lives in
# rendering.merge_entries, shared with normalize_unknown_sections' same-id
# fold so there is one struck-wins/longer-content-wins merge policy, not one
# per caller. Kept under this name for backward compatibility with existing
# callers that import it directly from github_sync.
_merge_entries = _rendering.merge_entries


def _merge_groomed(local: GroomedData, remote: GroomedData) -> GroomedData:
    """Merge two GroomedData objects keeping longer subsection content.

    Args:
        local: Local GroomedData (date is authoritative).
        remote: Remote GroomedData.

    Returns:
        GroomedData with per-subsection longer content and all unique keys.
    """
    merged_subsections: dict[str, str] = dict(local.subsections)
    for key, remote_content in remote.subsections.items():
        local_content = local.subsections.get(key, "")
        if len(remote_content) > len(local_content):
            merged_subsections[key] = remote_content
    return GroomedData(date=local.date or remote.date, subsections=merged_subsections)


# ---------------------------------------------------------------------------
# merge_item
# ---------------------------------------------------------------------------


def merge_item(local: BacklogItem, remote: BacklogItem) -> BacklogItem:
    """Merge a remote BacklogItem into a local one.

    Local metadata fields (title, priority, status, etc.) are authoritative.
    Section content is merged using the rules documented on each helper.

    Args:
        local: Local BacklogItem (authoritative for all non-section metadata).
        remote: Remote BacklogItem parsed from GitHub (may have richer sections).

    Returns:
        New BacklogItem with merged section content and local metadata.
    """
    merged_sections: dict[str, Section | GroomedData] = {}

    for key in set(local.sections) | set(remote.sections):
        local_sec = local.sections.get(key)
        remote_sec = remote.sections.get(key)

        if local_sec is None and remote_sec is not None:
            merged_sections[key] = remote_sec
        elif remote_sec is None and local_sec is not None:
            merged_sections[key] = local_sec
        elif isinstance(local_sec, GroomedData) and isinstance(remote_sec, GroomedData):
            merged_sections[key] = _merge_groomed(local_sec, remote_sec)
        elif isinstance(local_sec, Section) and isinstance(remote_sec, Section):
            merged_entries = _merge_entries(local_sec.entries, remote_sec.entries)
            merged_sections[key] = Section(entries=merged_entries)
        elif local_sec is not None:
            # Type mismatch — local is authoritative
            merged_sections[key] = local_sec

    return BacklogItem(
        title=local.title,
        description=local.description,
        sections=merged_sections,
        priority=local.priority,
        item_type=local.item_type,
        status=local.status,
        added=local.added,
        issue=local.issue,
        source=local.source,
        plan=local.plan,
        section=local.section,
        file_path=local.file_path,
    )
