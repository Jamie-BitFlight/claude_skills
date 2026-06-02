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

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from progressive_markdown.indexer import MarkdownIndexer
from progressive_markdown.list_navigator import ENCODING as _ENCODING, TOKEN_BUDGET
from progressive_markdown.parser import MarkdownItParser

from backlog_core.disclosure_types import OrdinalNotFoundError

if TYPE_CHECKING:
    from progressive_markdown.models import CodeBlock, SectionNode

    from backlog_core.content_normalizer import NormalizedSection

# ---------------------------------------------------------------------------
# Format constants (architect spec §5.5)
# ---------------------------------------------------------------------------

_TITLE_MAX: int = 50
_PREVIEW_MAX: int = 60
_ELLIPSIS: str = "…"  # U+2026 HORIZONTAL ELLIPSIS — single code point
_EM_DASH: str = "—"  # U+2014 EM DASH

# Regex for fenced code blocks: opening fence line, content, closing fence.
# re.DOTALL makes '.' match newlines so multi-line fence bodies are captured.
_FENCE_PATTERN: re.Pattern[str] = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)

# Minimum number of root-level sections an entry must contain for
# the navigate-on-parent (content="") behavior to activate (§5.4).
# Entries with a single root section are treated as leaves — their
# full content is returned, not a child map.
_MIN_ROOT_SECTIONS_FOR_PARENT: int = 2


# ---------------------------------------------------------------------------
# Value objects (public)
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
        content: Full raw markdown text of the resolved unit.  Empty string
            when ``has_sub_heading_children`` is ``True`` (ADR-7).
        total_tokens: Exact tiktoken cl100k_base count of ``content`` (ADR-2).
        has_sub_heading_children: ``True`` iff this node has direct SectionNode
            children (sub-headings).  Set from ``_SubtreeNode`` during
            ``resolve()``.  Code-only nodes are ``False`` (ADR-4).
        is_code_block: ``True`` iff this ordinal addresses a code fence body.
        child_ordinals: Direct sub-heading child ordinals (document order).
            Populated from ``_SubtreeNode`` for level-3+ nodes; empty for
            level-2 parents (see ``_build_child_map`` for discovery logic).
        code_block_ordinals: Direct-body fence ordinals (document order).
        child_map: Pre-rendered listing of direct sub-heading children using
            the same ``format_map_line`` format as MAP responses.  Non-empty
            only when ``has_sub_heading_children`` is ``True``.
    """

    ordinal: str
    title: str
    content: str
    total_tokens: int
    has_sub_heading_children: bool = False
    is_code_block: bool = False
    child_ordinals: list[str] = field(default_factory=list)
    code_block_ordinals: list[str] = field(default_factory=list)
    child_map: str = ""


# ---------------------------------------------------------------------------
# Internal types (§6.1 — NOT exported)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _SubtreeNode:
    """Internal recursive ordinal node built during ``build_map()``.

    NOT exported from this module.  Only ``OrdinalEntry`` and ``ResolvedUnit``
    are public; ``_SubtreeNode`` is an implementation detail of the eager
    ``_ResolutionIndex`` (§5.3).

    Attributes:
        ordinal: Dot-path ordinal string for this node.
        title: Heading text or language tag (code blocks).
        content: Prose-with-tokens for leaf nodes; ``""`` when
            ``has_sub_heading_children=True`` (ADR-7).
        total_tokens: Exact cl100k_base token count of ``content``.
        has_sub_heading_children: True iff this node has direct SectionNode
            children (sub-headings).  Code-only nodes are False (ADR-4).
        is_code_block: True iff this ordinal addresses a code fence body.
        child_ordinals: Direct sub-heading child ordinals (document order).
        code_block_ordinals: Direct-body fence ordinals (document order).
    """

    ordinal: str
    title: str
    content: str
    total_tokens: int
    has_sub_heading_children: bool
    is_code_block: bool
    child_ordinals: list[str]
    code_block_ordinals: list[str]


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


def _entry_ordinal_for_sub_heading(parent_ordinal: str, idx: int) -> str:
    """Return the sub-heading ordinal for the idx-th child of parent_ordinal.

    Args:
        parent_ordinal: Dot-path ordinal of the parent node.
        idx: 0-based sibling index among the parent's direct children.

    Returns:
        Ordinal string ``"{parent}.{idx}"``.
    """
    return f"{parent_ordinal}.{idx}"


def _entry_ordinal_for_code(parent_ordinal: str, k: int) -> str:
    """Return the code-fence ordinal for the k-th fence in parent_ordinal.

    Args:
        parent_ordinal: Dot-path ordinal of the containing node.
        k: 0-based fence index within the node's direct body.

    Returns:
        Ordinal string ``"{parent}.code.{k}"``.
    """
    return f"{parent_ordinal}.code.{k}"


def _replace_code_fences_with_tokens(content: str, fence_ordinals: list[str]) -> str:
    """Replace fenced code blocks in ``content`` with navigation tokens.

    Replaces each fence in document order with its corresponding navigation
    token ``[code:{ordinal}]``.  The number of fences replaced matches
    ``len(fence_ordinals)``; any additional fences beyond that are left
    unchanged (guarded against index overflow).

    Args:
        content: Raw markdown text containing zero or more code fences.
        fence_ordinals: Ordered list of ordinal strings for each fence.

    Returns:
        Modified content with fences replaced by ``[code:{ordinal}]`` tokens.
    """
    if not fence_ordinals:
        return content

    counter: list[int] = [0]

    def _replacer(m: re.Match[str]) -> str:
        i = counter[0]
        if i < len(fence_ordinals):
            counter[0] = i + 1
            return f"[code:{fence_ordinals[i]}]"
        return m.group(0)

    return _FENCE_PATTERN.sub(_replacer, content)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class OrdinalPathMapper:
    """Assign and resolve dot-path ordinals for a normalized section list.

    Ordinal levels:

    - Level 1 (``"N"``): section index in the normalized list (0-based).
    - Level 2 (``"N.M"``): entry index ``M`` within section ``N``.
    - Level 3+ (``"N.M.K"`` etc.): recursive sub-headings inside an entry.
    - Code fence (``"N.M.code.K"``): k-th fence in the direct body of ``N.M``.

    Level-2 lines are emitted only when the emission gate fires
    (architect spec §5.6)::

        entry_count > 1  OR  section_est_tokens > TOKEN_BUDGET

    Level-3+ and code-fence ordinals are emitted when the parsed entry content
    contains at least one sub-heading or code fence (§5.4 structural gate).

    Empty sections (0 entries) always produce a level-1 entry with
    ``est_tokens=0`` and no level-2 children.

    Token counting always uses the ``ENCODING`` singleton imported from
    ``progressive_markdown.list_navigator`` (cl100k_base), never a freshly
    registered encoding instance (ADR-2).

    Backward-compatibility invariant (§5.2): flat content (no headings, no
    fences) produces an identical ordinal set to the pre-feature implementation.

    Example usage::

        mapper = OrdinalPathMapper(sections)
        entries = mapper.build_map()
        for entry in entries:
            print(mapper.format_map_line(entry))
        unit = mapper.resolve("4.0")
    """

    def __init__(self, sections: list[NormalizedSection], encoding_name: str = "cl100k_base") -> None:
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
        # Eager resolution index covering all depths (§5.3).
        # Replaces the previous two-level _resolution_map.
        self._resolution_index: dict[str, _SubtreeNode] = {}

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def build_map(self) -> list[OrdinalEntry]:
        """Build the ordinal map for all sections.

        Produces one level-1 ``OrdinalEntry`` per section in document order,
        plus level-2 entries when the emission gate fires::

            entry_count > 1  OR  section_est_tokens > TOKEN_BUDGET

        For entries that contain markdown sub-headings or code fences,
        recursive sub-ordinals (level 3+) and code-fence ordinals are added
        eagerly to both the returned list and the internal resolution index.

        Empty sections always produce a level-1 entry (``est_tokens=0``).

        Populates the internal ordinal index used by ``resolve()`` and
        ``valid_ordinals()``.  Calling ``build_map()`` again replaces the
        previous index.

        Returns:
            Ordered list of ``OrdinalEntry``.  Within each section, the
            level-1 entry appears first, followed by level-2 entries; each
            level-2 entry is immediately followed by its sub-ordinals in
            document order.
        """
        entries: list[OrdinalEntry] = []
        resolution_index: dict[str, _SubtreeNode] = {}

        for section in self._sections:
            level1_ordinal = str(section.index)

            # Canonical section content: all entry bodies joined by blank lines.
            section_content = "\n\n".join(e.content for e in section.entries)
            section_tokens = len(self._enc.encode(section_content)) if section_content else 0
            level1_preview = _extract_preview(section_content)

            entries.append(
                OrdinalEntry(
                    ordinal=level1_ordinal,
                    title=section.title,
                    est_tokens=section_tokens,
                    first_line_preview=level1_preview,
                )
            )
            resolution_index[level1_ordinal] = _SubtreeNode(
                ordinal=level1_ordinal,
                title=section.title,
                content=section_content,
                total_tokens=section_tokens,
                has_sub_heading_children=False,
                is_code_block=False,
                child_ordinals=[],
                code_block_ordinals=[],
            )

            # Level-2 emission gate (architect spec §5.6).
            emit_level2: bool = len(section.entries) > 1 or section_tokens > TOKEN_BUDGET

            if emit_level2:
                for entry in section.entries:
                    level2_ordinal = f"{section.index}.{entry.index}"
                    entry_content = entry.content
                    entry_title = _extract_entry_title(entry_content)

                    # Analyze subtree before creating the level-2 OrdinalEntry
                    # so its est_tokens and preview reflect the final content.
                    final_content, final_tokens, final_preview, sub_ents, sub_idx = self._index_entry_subtree(
                        level2_ordinal, entry_content
                    )

                    # Append level-2 entry BEFORE its sub-ordinals (document order).
                    entries.append(
                        OrdinalEntry(
                            ordinal=level2_ordinal,
                            title=entry_title,
                            est_tokens=final_tokens,
                            first_line_preview=final_preview,
                        )
                    )
                    resolution_index[level2_ordinal] = _SubtreeNode(
                        ordinal=level2_ordinal,
                        title=entry_title,
                        content=final_content,
                        total_tokens=final_tokens,
                        has_sub_heading_children=not final_content,
                        is_code_block=False,
                        child_ordinals=[],
                        code_block_ordinals=[],
                    )

                    # Extend with sub-ordinals collected by _index_entry_subtree.
                    entries.extend(sub_ents)
                    resolution_index.update(sub_idx)

        self._map_entries = entries
        self._resolution_index = resolution_index
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

        Args:
            ordinal: Dot-path ordinal string (e.g. ``"4"``, ``"4.0"``,
                ``"4.0.1"``, ``"4.0.code.0"``).

        Returns:
            ``ResolvedUnit`` with full content and navigate-on-parent fields
            populated from the internal ``_SubtreeNode``.  When
            ``has_sub_heading_children`` is ``True``, ``child_map`` contains
            a pre-rendered listing of direct sub-heading children (same format
            as MAP responses).

        Raises:
            OrdinalNotFoundError: When ``ordinal`` is not present in the map
                built by the most recent ``build_map()`` call.  The exception
                carries the full ``valid_ordinals`` list so callers can recover
                without a second round-trip.
        """
        if ordinal in self._resolution_index:
            node = self._resolution_index[ordinal]
            child_map = self._build_child_map(ordinal) if node.has_sub_heading_children else ""
            return ResolvedUnit(
                ordinal=node.ordinal,
                title=node.title,
                content=node.content,
                total_tokens=node.total_tokens,
                has_sub_heading_children=node.has_sub_heading_children,
                is_code_block=node.is_code_block,
                child_ordinals=node.child_ordinals,
                code_block_ordinals=node.code_block_ordinals,
                child_map=child_map,
            )
        raise OrdinalNotFoundError(ordinal, self.valid_ordinals())

    def _build_child_map(self, parent_ordinal: str) -> str:
        """Render direct sub-heading children of ``parent_ordinal`` as map lines.

        Discovers children by scanning ``_resolution_index`` for ordinals that
        are exactly one depth level below ``parent_ordinal`` and contain no
        ``".code."`` segment (sub-heading children only, no code fences).

        Level-2 parent nodes (``N.M``) have ``child_ordinals=[]`` because they
        are created before ``_index_entry_subtree`` populates sub-ordinals.
        This method bypasses that gap by discovering children from the index
        directly rather than relying on ``node.child_ordinals``.

        Args:
            parent_ordinal: Dot-path ordinal of the parent node (e.g. ``"4.0"``).

        Returns:
            Newline-joined formatted map lines for direct sub-heading children,
            in document (numeric) order.  Returns ``""`` when no children are
            found (safe fallback).
        """
        prefix = parent_ordinal + "."
        target_depth = parent_ordinal.count(".") + 1
        child_ordinals: list[str] = sorted(
            (
                co
                for co in self._resolution_index
                if co.startswith(prefix) and co.count(".") == target_depth and ".code." not in co
            ),
            key=lambda o: int(o.rsplit(".", 1)[-1]),
        )
        lines: list[str] = []
        for co in child_ordinals:
            cn = self._resolution_index[co]
            entry = OrdinalEntry(ordinal=cn.ordinal, title=cn.title, est_tokens=cn.total_tokens, first_line_preview="")
            lines.append(self.format_map_line(entry))
        return "\n".join(lines)

    def valid_ordinals(self) -> list[str]:
        """Return all ordinals from the most recent ``build_map()`` call.

        Triggers a lazy ``build_map()`` call when ``_sections`` is non-empty
        and the map has not yet been built.  This ensures callers can retrieve
        valid ordinals without an explicit ``build_map()`` call.

        Returns:
            Ordered list of ordinal strings matching ``build_map()`` output,
            including all recursive sub-ordinals.  Empty list when
            ``_sections`` is empty (no sections to map).
        """
        if not self._map_entries and self._sections:
            self.build_map()
        return [e.ordinal for e in self._map_entries]

    # ------------------------------------------------------------------
    # Subtree indexing (level-3+ and code-fence ordinals)
    # ------------------------------------------------------------------

    def _index_entry_subtree(
        self, parent_ordinal: str, entry_content: str
    ) -> tuple[str, int, str, list[OrdinalEntry], dict[str, _SubtreeNode]]:
        """Parse entry content and collect all sub-ordinal data.

        Implements the §5.4 structural gate: emits sub-ordinals only when
        the parsed document has at least one section (heading) or code block.
        Flat content short-circuits immediately (§5.2 backward-compat invariant).

        Uses the construction sequence verified in T01 (DN-1):
        ``MarkdownItParser().parse(source, content) → MarkdownIndexer().build(result)``

        Args:
            parent_ordinal: Dot-path ordinal of the level-2 entry being indexed.
            entry_content: Raw markdown text of the entry.

        Returns:
            Tuple of:
            - ``final_content``: Content to store for ``parent_ordinal``.
              Empty string when the entry has sub-heading children (ADR-7).
            - ``final_tokens``: Exact cl100k_base count of ``final_content``.
            - ``final_preview``: First non-empty, non-heading body line.
            - ``sub_ents``: ``OrdinalEntry`` list for all sub-ordinals, in
              document order (fences before headings at each level).
            - ``sub_idx``: ``_SubtreeNode`` dict for all sub-ordinals.
        """
        sub_ents: list[OrdinalEntry] = []
        sub_idx: dict[str, _SubtreeNode] = {}

        # DN-1: MarkdownIndexer.build() takes ParserResult, not str.
        doc = MarkdownIndexer().build(MarkdownItParser().parse("inline", entry_content))

        # §5.2 short-circuit: flat content (no headings, no fences).
        # DN-2: MarkdownDocument fields are .sections and .code_blocks
        # (not .sections_by_id / .code_blocks_by_id).
        if not doc.sections and not doc.code_blocks:
            raw_tokens = len(self._enc.encode(entry_content)) if entry_content else 0
            return (entry_content, raw_tokens, _extract_preview(entry_content), sub_ents, sub_idx)

        entry_lines = entry_content.split("\n")

        # Identify direct-body fences: code blocks NOT inside any named section.
        # Fences before the first heading have section_id=None and are absent
        # from all SectionNode.code_block_ids.  doc.code_blocks preserves
        # insertion (document) order (Python 3.7+ dicts).
        direct_fence_ids: list[str] = [
            cb_id
            for cb_id in doc.code_blocks
            if cb_id not in {fence_id for node in doc.sections.values() for fence_id in node.code_block_ids}
        ]

        # §5.4 sub-heading gate: _MIN_ROOT_SECTIONS_FOR_PARENT or more root-level
        # sections activate navigate-on-parent (content="").  Single-heading entries
        # are treated as leaves to preserve the pre-feature resolve() contract.
        has_root_sections: bool = len(doc.root_section_ids) >= _MIN_ROOT_SECTIONS_FOR_PARENT

        # Emit code-fence ordinals for the direct body (before sub-headings).
        self._emit_direct_fence_ordinals(parent_ordinal, direct_fence_ids, doc.code_blocks, sub_ents, sub_idx)

        if has_root_sections:
            # ADR-7: parent with sub-heading children → content="" total_tokens=0.
            self._collect_section_children(
                parent_ordinal, doc.root_section_ids, doc.sections, doc.code_blocks, entry_lines, sub_ents, sub_idx
            )
            return ("", 0, "", sub_ents, sub_idx)

        # Code-only (fences in direct body, no sub-headings): replace fences
        # with navigation tokens and return modified prose.
        prose = (
            _replace_code_fences_with_tokens(
                entry_content, [_entry_ordinal_for_code(parent_ordinal, k) for k in range(len(direct_fence_ids))]
            )
            if direct_fence_ids
            else entry_content
        )
        prose_tokens = len(self._enc.encode(prose)) if prose else 0
        return (prose, prose_tokens, _extract_preview(prose), sub_ents, sub_idx)

    def _emit_direct_fence_ordinals(
        self,
        parent_ordinal: str,
        fence_ids: list[str],
        code_blocks: dict[str, CodeBlock],
        sub_ents: list[OrdinalEntry],
        sub_idx: dict[str, _SubtreeNode],
    ) -> None:
        """Append ``OrdinalEntry`` and ``_SubtreeNode`` records for direct-body fences.

        Args:
            parent_ordinal: Dot-path ordinal of the containing node.
            fence_ids: Ordered code-block IDs for the node's direct body.
            code_blocks: Full ``MarkdownDocument.code_blocks`` dict.
            sub_ents: Accumulator list; appended in place.
            sub_idx: Accumulator dict; updated in place.
        """
        for k, fence_id in enumerate(fence_ids):
            fence_ordinal = _entry_ordinal_for_code(parent_ordinal, k)
            cb = code_blocks[fence_id]
            fence_body = cb.content
            fence_title = cb.language or "code block"
            fence_tokens = len(self._enc.encode(fence_body)) if fence_body else 0
            sub_ents.append(
                OrdinalEntry(
                    ordinal=fence_ordinal,
                    title=fence_title,
                    est_tokens=fence_tokens,
                    first_line_preview=_extract_preview(fence_body),
                )
            )
            sub_idx[fence_ordinal] = _SubtreeNode(
                ordinal=fence_ordinal,
                title=fence_title,
                content=fence_body,
                total_tokens=fence_tokens,
                has_sub_heading_children=False,
                is_code_block=True,
                child_ordinals=[],
                code_block_ordinals=[],
            )

    def _collect_section_children(
        self,
        parent_ordinal: str,
        child_section_ids: list[str],
        doc_sections: dict[str, SectionNode],
        doc_code_blocks: dict[str, CodeBlock],
        entry_lines: list[str],
        sub_ents: list[OrdinalEntry],
        sub_idx: dict[str, _SubtreeNode],
    ) -> None:
        """Recursively collect sub-heading and fence ordinals into sub_ents/sub_idx.

        Processes ``child_section_ids`` in document order (sibling index 0,
        1, 2, …), emitting the sub-heading node followed by its direct-body
        fences, then recursing into grandchildren.

        ``SectionNode.code_block_ids`` order is used for fence indexing per
        §4.2 (NOT ``doc_code_blocks`` dict order, which is global).

        Args:
            parent_ordinal: Dot-path ordinal of the parent node.
            child_section_ids: Ordered IDs of direct child sections.
            doc_sections: Full ``MarkdownDocument.sections`` dict.
            doc_code_blocks: Full ``MarkdownDocument.code_blocks`` dict.
            entry_lines: Lines of the original entry content (for body extraction).
            sub_ents: Accumulator list; appended in place.
            sub_idx: Accumulator dict; updated in place.
        """
        for sibling_idx, section_id in enumerate(child_section_ids):
            node = doc_sections[section_id]
            sub_ordinal = _entry_ordinal_for_sub_heading(parent_ordinal, sibling_idx)

            # Extract body text using body_span (inclusive end line, ADR-DN-1).
            body_lines = entry_lines[node.body_span.start_line : node.body_span.end_line + 1]
            body_text = "\n".join(body_lines)

            has_sub_children: bool = bool(node.child_ids)
            # SectionNode.code_block_ids: direct-body fences in document order.
            section_fence_ids: list[str] = node.code_block_ids

            # Fence ordinals for this node's direct body.
            fence_ordinals_for_node = [_entry_ordinal_for_code(sub_ordinal, k) for k in range(len(section_fence_ids))]

            if has_sub_children:
                # ADR-7: parent node with sub-heading children → content="".
                node_content = ""
                node_tokens = 0
                node_preview = ""
            else:
                # Leaf or code-only: prepend the heading line so agents see the
                # heading title in context (body_span starts AFTER the heading).
                heading_line = f"{'#' * node.level} {node.title}"
                full_body = f"{heading_line}\n{body_text}" if body_text else heading_line
                # Replace direct-body fences with navigation tokens.
                if section_fence_ids:
                    node_content = _replace_code_fences_with_tokens(full_body, fence_ordinals_for_node)
                else:
                    node_content = full_body
                node_tokens = len(self._enc.encode(node_content)) if node_content else 0
                node_preview = _extract_preview(node_content)

            # Append the sub-heading node BEFORE its own children/fences.
            sub_ents.append(
                OrdinalEntry(
                    ordinal=sub_ordinal, title=node.title, est_tokens=node_tokens, first_line_preview=node_preview
                )
            )
            sub_idx[sub_ordinal] = _SubtreeNode(
                ordinal=sub_ordinal,
                title=node.title,
                content=node_content,
                total_tokens=node_tokens,
                has_sub_heading_children=has_sub_children,
                is_code_block=False,
                child_ordinals=[_entry_ordinal_for_sub_heading(sub_ordinal, k) for k in range(len(node.child_ids))],
                code_block_ordinals=fence_ordinals_for_node,
            )

            # Emit fence ordinals for this node's direct body.
            self._emit_direct_fence_ordinals(sub_ordinal, section_fence_ids, doc_code_blocks, sub_ents, sub_idx)

            # Recurse into grandchildren.
            if node.child_ids:
                self._collect_section_children(
                    sub_ordinal, node.child_ids, doc_sections, doc_code_blocks, entry_lines, sub_ents, sub_idx
                )


__all__ = ["OrdinalEntry", "OrdinalPathMapper", "ResolvedUnit"]
