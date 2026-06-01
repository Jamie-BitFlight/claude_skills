"""OrdinalPathMapper — interface stub (T13 TDD scaffold).

This file declares the public types and method signatures required by
``tests/unit/test_ordinal_mapper.py``.  All methods raise ``NotImplementedError``
so pytest tests fail red on every assertion.  T14 replaces these stubs with a
working implementation.

Architect spec references (do NOT change the interface without re-reading these):
- §4.2.2: OrdinalPathMapper class contract
- §5.5:   Map line format
- §5.6:   Level-2 emission gate (entry_count > 1 OR est_tokens > TOKEN_BUDGET)
- ADR-1:  Ordinal level assignment algorithm
- ADR-2:  Encoding — always ``progressive_markdown.list_navigator.ENCODING``
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backlog_core.content_normalizer import NormalizedSection


@dataclass(frozen=True, slots=True)
class OrdinalEntry:
    """One line of the flat ordinal map produced by ``OrdinalPathMapper.build_map()``."""

    ordinal: str
    """Dot-path key, e.g. ``"3"``, ``"3.0"``, ``"3.0.0"``."""

    title: str
    """Heading or entry title (truncated to 50 chars in ``format_map_line``)."""

    est_tokens: int
    """tiktoken ``cl100k_base`` count of the resolved body content.  Always >= 0."""

    first_line_preview: str
    """First non-empty line of content, max 60 chars.  Empty string when no content."""


@dataclass(frozen=True, slots=True)
class ResolvedUnit:
    """Content resolved from a specific ordinal by ``OrdinalPathMapper.resolve()``."""

    ordinal: str
    """The ordinal string that was resolved."""

    title: str
    """Section or entry heading text."""

    content: str
    """Raw markdown text of the section/entry body."""

    total_tokens: int
    """tiktoken ``cl100k_base`` count of ``content``."""


class OrdinalPathMapper:
    """Build flat ordinal dot-path maps and resolve ordinals to content.

    Responsible for:
    - Assigning dot-path ordinals from a normalized section list (document-order)
    - Serializing the map to formatted text lines
    - Resolving an ordinal string to a ``ResolvedUnit``
    - Reporting all valid ordinals when resolution fails

    Does NOT:
    - Normalize ``ViewItemResult`` shapes (``ItemContentNormalizer``'s responsibility)
    - Count tokens for response bounding (``TokenBoundedExtractor``'s responsibility)
    - Assemble MCP response dicts (``BacklogViewDisclosureHandler``'s responsibility)
    - Parse or validate inbound request parameters (``DisclosureRequestParser``'s responsibility)

    Level-2 emission gate (architect spec §5.6):
        Level-2 lines (entry within a section) are emitted only when
        ``entry_count > 1`` OR ``section_est_tokens > TOKEN_BUDGET``.
        Empty sections (0 entries) appear as level-1 only with est_tokens=0.
    """

    def __init__(
        self,
        sections: list[NormalizedSection],
        encoding_name: str = "cl100k_base",
    ) -> None:
        """Initialise with a normalized section list.

        Args:
            sections: Ordered ``list[NormalizedSection]`` from
                ``ItemContentNormalizer.normalize()``.  An empty list is valid
                (e.g. when ``format_map_line`` is tested standalone).
            encoding_name: tiktoken encoding used for token counting.
                Must match the ``ENCODING`` constant in
                ``progressive_markdown.list_navigator`` (ADR-2).
        """
        raise NotImplementedError

    def build_map(self) -> list[OrdinalEntry]:
        """Return an ordered flat list of ``OrdinalEntry`` for every section and visible entry.

        Level-1 entries (sections) are always emitted.
        Level-2 entries (entries within a section) are emitted only when
        ``entry_count > 1`` OR ``section_est_tokens > TOKEN_BUDGET``.
        Level-3 entries (body sub-headings within an entry) are not emitted
        in the default map.

        Returns:
            Flat list of ``OrdinalEntry``, document-order, level-1 before level-2.
        """
        raise NotImplementedError

    def format_map_line(self, entry: OrdinalEntry) -> str:
        """Format one ``OrdinalEntry`` as a contract-exact map line.

        Format::

            {ordinal} {title} ({est_tokens}t) [— "{first_line_preview}"]

        Rules (architect spec §5.5):
        - Preview clause (``— "…"``) omitted when ``first_line_preview`` is empty.
        - Title truncated at 50 chars, ending with ``"…"`` (U+2026).
        - Preview truncated at 60 chars.
        - ``(0t)`` when ``est_tokens == 0``; no preview appended.

        Args:
            entry: An ``OrdinalEntry`` produced by ``build_map()`` or constructed
                directly for format testing.

        Returns:
            Single-line string (no trailing newline).
        """
        raise NotImplementedError

    def resolve(self, ordinal: str) -> ResolvedUnit:
        """Resolve an ordinal to a ``ResolvedUnit``.

        ``build_map()`` must be called before ``resolve()`` to populate the
        internal ordinal index.

        Args:
            ordinal: Dot-path ordinal string, e.g. ``"4"`` or ``"4.0"``.
                Must match the format produced by ``build_map()``.

        Returns:
            ``ResolvedUnit`` with ``content`` being the raw markdown body:
            - Level-1 ordinal: concatenation of all entry bodies in the section.
            - Level-2 ordinal: the specific entry body.
            - Empty section (0 entries): ``content=""`` and ``total_tokens=0``.

        Raises:
            OrdinalNotFoundError: ``ordinal`` is not present in this document's map.
                The exception's ``valid_ordinals`` attribute lists all known ordinals.
        """
        raise NotImplementedError

    def valid_ordinals(self) -> list[str]:
        """Return all valid ordinal strings for this document.

        ``build_map()`` must be called first to populate the internal index.

        Returns:
            List of ordinal strings in document order.
        """
        raise NotImplementedError
