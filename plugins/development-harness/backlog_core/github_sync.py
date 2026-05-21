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
from .entry_blocks import _render_entry_raw, parse_entries
from .models import BacklogItem, Entry, GroomedData, Section, parse_issue_number
from .parsing import extract_sections

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
_GROOMED_HEADING_RE = re.compile(r"^##\s+Groomed\s*\(([^)]*)\)")
_SUBSECTION_RE = re.compile(r"### ([^\n]+)\n([\s\S]*?)(?=\n### |\Z)")

# Re-exported from rendering — canonical definition lives in rendering.SECTION_HEADING
SECTION_HEADING = _rendering.SECTION_HEADING

# Reverse lookup: heading text (lowercased) -> section key
_HEADING_TO_KEY: dict[str, str] = {v.lower(): k for k, v in SECTION_HEADING.items()}

# All known section keys plus "groomed" — used to identify unknown sections in render_issue_body
_KNOWN_SECTION_KEYS: frozenset[str] = frozenset(SECTION_HEADING) | {"groomed"}


def heading_to_section_key(heading_text: str) -> str | None:
    """Return the BacklogItem.sections key for a markdown heading text, or None if unknown.

    Args:
        heading_text: Heading text with ``##`` prefix stripped and whitespace trimmed.

    Returns:
        Normalised section key (e.g. ``"fact_check"``) or ``None`` when the heading
        does not correspond to a known section.
    """
    return _HEADING_TO_KEY.get(heading_text.lower())


def heading_to_unknown_key(heading_text: str) -> str:
    """Convert an unknown section heading to a storage key.

    Unknown headings are normalised by lowercasing and replacing spaces with
    underscores.  The prefix ``"unknown__"`` is prepended so unknown section
    keys never collide with known section keys (e.g. ``"fact_check"``).

    Args:
        heading_text: Raw heading text with ``##`` prefix stripped and whitespace
            trimmed.

    Returns:
        Storage key such as ``"unknown__custom_analysis"``.
    """
    normalised = heading_text.lower().replace(" ", "_")
    return f"unknown__{normalised}"


def unknown_key_to_heading(key: str) -> str:
    """Reconstruct a display heading from an unknown-section storage key.

    Reverses :func:`heading_to_unknown_key`: strips the ``"unknown__"`` prefix,
    replaces underscores with spaces, and title-cases the result.

    Args:
        key: Storage key such as ``"unknown__custom_analysis"``.

    Returns:
        Display heading such as ``"Custom Analysis"``.
    """
    stripped = key.removeprefix("unknown__")
    return stripped.replace("_", " ").title()


# Canonical render order for GroomedData subsections (heading text as stored in the dict)
_GROOMED_SUBSECTION_ORDER: list[str] = [
    "Priority",
    "Impact",
    "Benefits",
    "Expected Behavior",
    "Desired Structure",
    "Acceptance Criteria",
    "Resources",
    "Dependencies",
    "Effort",
]


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


def _parse_groomed_section(heading: str, content: str) -> GroomedData:
    """Parse a ``## Groomed (date)`` heading + body into a GroomedData model.

    Args:
        heading: Full heading string, e.g. ``"## Groomed (2026-03-01)"``.
        content: Section body text (content after the heading line).

    Returns:
        GroomedData with date and subsections populated.
    """
    date_match = _GROOMED_HEADING_RE.match(heading)
    date = date_match.group(1).strip() if date_match else ""
    subsections: dict[str, str] = {}
    for sub_match in _SUBSECTION_RE.finditer(content):
        sub_key = sub_match.group(1).strip()
        sub_content = sub_match.group(2).strip()
        subsections[sub_key] = sub_content
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

        # Groomed section: heading starts with "Groomed"
        if heading_name.startswith("Groomed"):
            parsed_sections["groomed"] = _parse_groomed_section(heading, content)
            continue

        # Entry-bearing sections — normalised case lookup
        section_key = _HEADING_TO_KEY.get(heading_name.lower())
        if section_key is not None:
            entries = parse_entries(content, show="all")
            parsed_sections[section_key] = Section(entries=entries)
        else:
            # Unknown heading: store with prefixed key so it survives round-trips.
            unknown_key = heading_to_unknown_key(heading_name)
            entries = parse_entries(content, show="all")
            parsed_sections[unknown_key] = Section(entries=entries)

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


def _merge_entries(local_entries: list[Entry], remote_entries: list[Entry]) -> list[Entry]:
    """Merge two entry lists into a single chronologically-ordered list.

    Merge rules (applied per entry id):
    - struck state wins over active for the same id
    - when both have the same struck state, longer content wins
    - entries unique to either side are always preserved
    - result is sorted chronologically by id

    Args:
        local_entries: Entries from the local BacklogItem.
        remote_entries: Entries from the remote (GitHub) BacklogItem.

    Returns:
        Merged list of Entry objects ordered by id (ascending).
    """
    local_by_id: dict[str, Entry] = {e.id: e for e in local_entries}
    remote_by_id: dict[str, Entry] = {e.id: e for e in remote_entries}

    merged: dict[str, Entry] = {}
    for eid in set(local_by_id) | set(remote_by_id):
        local_e = local_by_id.get(eid)
        remote_e = remote_by_id.get(eid)

        if local_e is None and remote_e is not None:
            merged[eid] = remote_e
        elif remote_e is None and local_e is not None:
            merged[eid] = local_e
        elif local_e is not None and remote_e is not None:
            if local_e.struck and not remote_e.struck:
                # struck wins over active
                merged[eid] = local_e
            elif remote_e.struck and not local_e.struck:
                merged[eid] = remote_e
            else:
                # same struck state — longer content wins; local wins on tie
                merged[eid] = local_e if len(local_e.content) >= len(remote_e.content) else remote_e

    return [merged[eid] for eid in sorted(merged)]


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
