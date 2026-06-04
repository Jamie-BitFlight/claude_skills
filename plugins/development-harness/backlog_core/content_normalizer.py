"""Normalize ViewItemResult into an ordered list[NormalizedSection].

Single responsibility: convert both ViewItemResult shapes (under-budget with a
populated sections dict, over-budget via un-gated view_item()) into one canonical
ordered representation.  Canonical order always derives from ``[N] Title`` lines in
the sections index, never from ``dict.keys()`` iteration.

Does NOT:
- Fetch items from the backend (``BacklogViewDisclosureHandler``'s responsibility).
- Build ordinals or map lines (``OrdinalPathMapper``'s responsibility).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeGuard

if TYPE_CHECKING:
    from backlog_core.models import GroomedSectionMetadata, SectionEntryMetadata, ViewItemResult


@dataclass(frozen=True, slots=True)
class NormalizedEntry:
    """One content entry within a section."""

    index: int
    """0-based position within the parent section."""

    content: str
    """Raw markdown text of the entry."""


@dataclass(frozen=True, slots=True)
class NormalizedSection:
    """One section in document-order, with its ordered entries."""

    index: int
    """0-based position in the document — equals the level-1 ordinal."""

    title: str
    """Section heading text."""

    entries: list[NormalizedEntry]
    """Ordered entries.  Empty list for sections with no content blocks."""


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _parse_section_titles(index_source: str) -> list[str]:
    """Parse ordered section titles from the contiguous ``## Sections`` index block.

    Reads ``[N] Title (M entries)`` lines immediately following the
    ``## Sections`` header.  Stops at the first non-matching line after at
    least one ``[N]`` line has been seen — typically the blank line that
    separates the index block from the first section heading.

    This bounded parse prevents stray ``[...]`` patterns inside section body
    content from inflating the title list when ``index_source`` is the full body.

    Handles section titles containing ``(`` (e.g. ``Groomed (2026-06-01)``) by
    splitting on the **last** occurrence of `` (`` to strip the trailing
    ``(N entries)`` suffix.

    Args:
        index_source: String with a ``## Sections`` header followed by ``[N]`` lines.
            Either the ``sections_index`` field (summary path) or a body string
            that has the index block prepended (full-content path).

    Returns:
        Ordered list of section title strings, one per ``[N]`` line.
    """
    titles: list[str] = []
    in_block = False
    for line in index_source.split("\n"):
        if line.rstrip() == "## Sections":
            in_block = True
            continue
        if not in_block:
            continue
        if line.startswith("[") and "] " in line:
            after_bracket = line[line.index("] ") + 2 :]
            # rsplit on the last " (" strips "( N entries)" while preserving
            # titles like "Groomed (2026-06-01)" that contain "(" themselves.
            title = after_bracket.rsplit(" (", 1)[0]
            titles.append(title)
        elif titles:
            # First non-matching line after the block started — block is done.
            break
        # else: leading blank/ignored line before the first [N] entry — skip.
    return titles


def _is_entry_section_metadata(
    section: SectionEntryMetadata | GroomedSectionMetadata,
) -> TypeGuard[SectionEntryMetadata]:
    """Return ``True`` when *section* is ``SectionEntryMetadata``.

    Discriminates the two TypedDict shapes at the boundary by checking for the
    ``type`` discriminator key present on ``GroomedSectionMetadata``:

    - ``SectionEntryMetadata``: no ``type`` key, has ``entries: list[SectionEntryDict]``.
    - ``GroomedSectionMetadata``: ``type == "groomed"``, has ``subsections``, no flat entries.
    """
    # TypedDicts are plain dicts at runtime; "type" is only present on GroomedSectionMetadata.
    return "type" not in section


def _build_entries(section: SectionEntryMetadata | GroomedSectionMetadata) -> list[NormalizedEntry]:
    """Extract a ``NormalizedEntry`` list from a section metadata value.

    Returns an empty list for ``GroomedSectionMetadata`` (no flat entry list),
    and a ``NormalizedEntry`` per ``SectionEntryDict`` in the ``entries`` list
    for ``SectionEntryMetadata``.

    Args:
        section: Raw section metadata value from ``ViewItemResult.sections``.

    Returns:
        Ordered ``NormalizedEntry`` list, or ``[]`` for groomed/empty sections.
    """
    if not _is_entry_section_metadata(section):
        return []
    # After TypeGuard narrowing, section is SectionEntryMetadata.
    # section["entries"] is list[SectionEntryDict]; each entry["content"] is str.
    return [NormalizedEntry(index=i, content=entry["content"]) for i, entry in enumerate(section["entries"])]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class ItemContentNormalizer:
    r"""Convert a ``ViewItemResult`` into one ordered ``list[NormalizedSection]``.

    Handles both ``ViewItemResult`` shapes produced by ``operations.view_item()``:

    - **Full-content path** (``include_content=True``): ``sections_index`` field is
      ``""`` and ``body`` starts with a ``## Sections`` block prepended by
      ``operations.py`` (~line 3229: ``result.body = pending_index + "\\n" + result.body``).

    - **Summary path** (``include_content=False``): ``sections_index`` field carries
      the ``[N] Title (M entries)`` ordering; ``body`` may be ``""``.

    The canonical section ORDER always derives from ``[N] Title`` lines in whichever
    source is present.  ``dict.keys()`` insertion order is never consulted.

    Invariants (architect spec §4.2.1):
    - Empty sections (0 entries) appear as ``NormalizedSection(entries=[])``.
      Their ordinal position is preserved — no gap compression.
    - The 0-based list index of each ``NormalizedSection`` equals its level-1 ordinal.
    """

    def normalize(self, result: ViewItemResult) -> list[NormalizedSection]:
        """Return a document-order ``list[NormalizedSection]``.

        One ``NormalizedSection`` is produced per ``[N]`` line in the sections index.
        The 0-based list index of each element equals the ``[N]`` ordinal from the
        block (sequential, matches position in the returned list).

        When the sections index contains duplicate titles (e.g. two body sections
        named ``"Acceptance Criteria"``), both produce ``NormalizedSection`` entries
        with the same content from ``sections_dict`` but different list-position
        ordinals.  This is intentional: the ``[N]`` block is the authoritative source
        of structure, and the sections dict collapses duplicates — the normalizer
        preserves all ``[N]`` entries exactly.

        Args:
            result: ``ViewItemResult`` from ``operations.view_item()``.  Both
                shapes are handled: under-budget with a populated ``sections`` dict
                and full body, and over-budget via un-gated view returning full content.

        Returns:
            Ordered list of ``NormalizedSection``, one per ``[N]`` line in the
            sections index.  Sections absent from the ``sections`` dict (edge
            case) appear with ``entries=[]``.
        """
        # Prefer the sections_index field (summary path).
        # Fall back to body when field is empty (full-content path prepends the block).
        index_source = result.sections_index or result.body
        titles = _parse_section_titles(index_source)

        out: list[NormalizedSection] = []
        for title in titles:
            idx = len(out)  # sequential 0-based position (== level-1 ordinal)
            section_meta = result.sections.get(title)
            if section_meta is None:
                # Section in index but absent from dict (edge case: duplicate titles
                # collapse in sections dict; still emit entry with empty content).
                out.append(NormalizedSection(index=idx, title=title, entries=[]))
                continue
            out.append(NormalizedSection(index=idx, title=title, entries=_build_entries(section_meta)))
        return out


__all__ = ["ItemContentNormalizer", "NormalizedEntry", "NormalizedSection"]
