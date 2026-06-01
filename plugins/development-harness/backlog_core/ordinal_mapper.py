"""Ordinal path mapper for progressive disclosure.

Receives a ``list[NormalizedSection]`` (canonical ordered form produced by
``ItemContentNormalizer``) and builds dot-path ordinals, formats map lines,
and resolves ordinals to ``ResolvedUnit`` values.

Single responsibility: ordinal assignment and resolution only.

Does NOT:
- Normalize ``ViewItemResult`` (``ItemContentNormalizer``'s responsibility).
- Apply token bounds to responses (``TokenBoundedExtractor``'s responsibility).
- Assemble MCP response dicts (``BacklogViewDisclosureHandler``'s responsibility).
- Parse or validate inbound request parameters (``DisclosureRequestParser``'s
  responsibility).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from progressive_markdown.list_navigator import ENCODING as _ENCODING, TOKEN_BUDGET

from backlog_core.disclosure_types import OrdinalNotFoundError

if TYPE_CHECKING:
    from backlog_core.content_normalizer import NormalizedSection

# ---------------------------------------------------------------------------
# Format constants (architect spec §5.5)
# ---------------------------------------------------------------------------

_TITLE_MAX: int = 50
_PREVIEW_MAX: int = 60
_ELLIPSIS: str = "…"  # U+2026 HORIZONTAL ELLIPSIS — single code point
_EM_DASH: str = "—"   # U+2014 EM DASH


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OrdinalEntry:
    """One line in the ordinal map produced by ``OrdinalPathMapper.build_map()``.

    Attributes:
        ordinal: Dot-path key, e.g. ``"4"``, ``"4.0"``, ``"4.0.1"``.
        title: Section or entry heading text.  Truncated to
            ``_TITLE_MAX`` chars (with ``…``) by ``format_map_line``.
        est_tokens: Exact tiktoken cl100k_base count of the content at this
            ordinal — never an approximation (ADR-2).
        first_line_preview: First non-empty, non-heading line of the content;
            max ``_PREVIEW_MAX`` chars; empty string when content has no body
            text.
    """

    ordinal: str
    title: str
    est_tokens: int
    first_line_preview: str


@dataclass(frozen=True, slots=True)
class ResolvedUnit:
    """Full content for a resolved ordinal.

    Attributes:
        ordinal: The ordinal string that was resolved.
        title: Section or entry heading text.
        content: Full raw markdown text of the resolved unit.
        total_tokens: Exact tiktoken cl100k_base count of ``content`` (ADR-2).
    """

    ordinal: str
    title: str
    content: str
    total_tokens: int


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _extract_entry_title(content: str) -> str:
    """Extract a human-readable title from entry content.

    If the first non-empty line is a markdown heading (starts with ``#``),
    strips the heading markers and returns the heading text.  Otherwise
    returns the first non-empty line verbatim (capped by ``format_map_line``
    if necessary).

    Args:
        content: Raw markdown entry content.

    Returns:
        Title string; empty string when ``content`` is blank.
    """
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        return stripped
    return ""


def _extract_preview(content: str) -> str:
    """Extract the first non-empty, non-heading line for the preview field.

    Heading lines (those starting with ``#`` after stripping whitespace) are
    skipped so the preview always surfaces actual body text.

    Args:
        content: Raw markdown content to scan.

    Returns:
        First qualifying line (stripped), or empty string when no non-heading
        content is present.
    """
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        return stripped
    return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class OrdinalPathMapper:
    """Assign and resolve dot-path ordinals for a normalized section list.

    Ordinal levels:

    - Level 1 (``"N"``): section index in the normalized list (0-based).
    - Level 2 (``"N.M"``): entry index ``M`` within section ``N``.

    Level-2 lines are emitted only when the emission gate fires
    (architect spec §5.6)::

        entry_count > 1  OR  section_est_tokens > TOKEN_BUDGET

    Empty sections (0 entries) always produce a level-1 entry with
    ``est_tokens=0`` and no level-2 children.

    Token counting always uses the ``ENCODING`` singleton imported from
    ``progressive_markdown.list_navigator`` (cl100k_base), never a freshly
    registered encoding instance (ADR-2).

    Example usage::

        mapper = OrdinalPathMapper(sections)
        entries = mapper.build_map()
        for entry in entries:
            print(mapper.format_map_line(entry))
        unit = mapper.resolve("4.0")
    """

    def __init__(
        self,
        sections: list[NormalizedSection],
        encoding_name: str = "cl100k_base",
    ) -> None:
        """Initialise the mapper.

        Args:
            sections: Ordered list from ``ItemContentNormalizer.normalize()``.
                An empty list is valid (e.g. for standalone ``format_map_line``
                usage in tests).
            encoding_name: Declared for API compatibility.  The mapper always
                uses the ``ENCODING`` singleton from
                ``progressive_markdown.list_navigator`` (cl100k_base) to
                guarantee consistent token counting across all progressive-
                disclosure components (ADR-2).  A new tiktoken encoding is
                never registered here.
        """
        self._sections = sections
        # ADR-2: Reuse the module-level ENCODING singleton from list_navigator
        # so all progressive-disclosure components share one cl100k_base instance.
        self._enc = _ENCODING
        self._map_entries: list[OrdinalEntry] = []
        self._resolution_map: dict[str, ResolvedUnit] = {}

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def build_map(self) -> list[OrdinalEntry]:
        """Build the ordinal map for all sections.

        Produces one level-1 ``OrdinalEntry`` per section in document order,
        plus level-2 entries when the emission gate fires::

            entry_count > 1  OR  section_est_tokens > TOKEN_BUDGET

        Empty sections always produce a level-1 entry (``est_tokens=0``).

        Populates the internal ordinal index used by ``resolve()`` and
        ``valid_ordinals()``.  Calling ``build_map()`` again replaces the
        previous index.

        Returns:
            Ordered list of ``OrdinalEntry``.  Within each section, the
            level-1 entry appears before its level-2 children.
        """
        entries: list[OrdinalEntry] = []
        resolution: dict[str, ResolvedUnit] = {}

        for section in self._sections:
            level1_ordinal = str(section.index)

            # Canonical section content: all entry bodies joined by blank lines.
            # This is exactly the string returned by resolve("<N>") for level-1.
            section_content = "\n\n".join(e.content for e in section.entries)
            section_tokens = (
                len(self._enc.encode(section_content)) if section_content else 0
            )
            level1_preview = _extract_preview(section_content)

            level1_entry = OrdinalEntry(
                ordinal=level1_ordinal,
                title=section.title,
                est_tokens=section_tokens,
                first_line_preview=level1_preview,
            )
            entries.append(level1_entry)
            resolution[level1_ordinal] = ResolvedUnit(
                ordinal=level1_ordinal,
                title=section.title,
                content=section_content,
                total_tokens=section_tokens,
            )

            # Level-2 emission gate (architect spec §5.6).
            emit_level2: bool = (
                len(section.entries) > 1 or section_tokens > TOKEN_BUDGET
            )

            if emit_level2:
                for entry in section.entries:
                    level2_ordinal = f"{section.index}.{entry.index}"
                    entry_content = entry.content
                    entry_tokens = (
                        len(self._enc.encode(entry_content)) if entry_content else 0
                    )
                    entry_title = _extract_entry_title(entry_content)
                    entry_preview = _extract_preview(entry_content)

                    level2_entry = OrdinalEntry(
                        ordinal=level2_ordinal,
                        title=entry_title,
                        est_tokens=entry_tokens,
                        first_line_preview=entry_preview,
                    )
                    entries.append(level2_entry)
                    resolution[level2_ordinal] = ResolvedUnit(
                        ordinal=level2_ordinal,
                        title=entry_title,
                        content=entry_content,
                        total_tokens=entry_tokens,
                    )

        self._map_entries = entries
        self._resolution_map = resolution
        return entries

    def format_map_line(self, entry: OrdinalEntry) -> str:
        r"""Format one map line per the contract spec (architect spec §5.5).

        Format::

            {ordinal} {title} ({est_tokens}t) [— "{preview}"]

        The em-dash (U+2014) and preview clause are omitted entirely when
        ``entry.first_line_preview`` is the empty string.

        Caps enforced:

        - Title: max 50 chars; truncated with ``…`` (U+2026 HORIZONTAL
          ELLIPSIS, a single code point).
        - Preview: max 60 chars.

        Args:
            entry: ``OrdinalEntry`` to format.  May be constructed directly
                for testing without calling ``build_map()`` first.

        Returns:
            Formatted map line string (no trailing newline).
        """
        title = entry.title
        if len(title) > _TITLE_MAX:
            title = title[: _TITLE_MAX - 1] + _ELLIPSIS

        base = f"{entry.ordinal} {title} ({entry.est_tokens}t)"

        if entry.first_line_preview:
            preview = entry.first_line_preview
            if len(preview) > _PREVIEW_MAX:
                preview = preview[:_PREVIEW_MAX]
            return f'{base} {_EM_DASH} "{preview}"'
        return base

    def resolve(self, ordinal: str) -> ResolvedUnit:
        """Resolve a dot-path ordinal to its full content.

        ``build_map()`` must be called before ``resolve()``.

        Level-1 ordinal (``"N"``): returns all entry bodies joined by blank
        lines; empty string for sections with no entries.

        Level-2 ordinal (``"N.M"``): returns the specific entry body.

        Args:
            ordinal: Dot-path ordinal string (e.g. ``"4"``, ``"4.0"``).

        Returns:
            ``ResolvedUnit`` with full content and exact cl100k_base token
            count.

        Raises:
            OrdinalNotFoundError: When ``ordinal`` is not present in the map
                built by the most recent ``build_map()`` call.  The exception
                carries the full ``valid_ordinals`` list so callers can recover
                without a second round-trip.
        """
        if ordinal in self._resolution_map:
            return self._resolution_map[ordinal]
        raise OrdinalNotFoundError(ordinal, self.valid_ordinals())

    def valid_ordinals(self) -> list[str]:
        """Return all ordinals from the most recent ``build_map()`` call.

        Triggers a lazy ``build_map()`` call when ``_sections`` is non-empty
        and the map has not yet been built.  This ensures callers can retrieve
        valid ordinals without an explicit ``build_map()`` call.

        Returns:
            Ordered list of ordinal strings matching ``build_map()`` output.
            Empty list when ``_sections`` is empty (no sections to map).
        """
        if not self._map_entries and self._sections:
            self.build_map()
        return [e.ordinal for e in self._map_entries]


__all__ = ["OrdinalEntry", "OrdinalPathMapper", "ResolvedUnit"]
