"""Parse Markdown into a section tree using marko.

This module converts a Markdown string into a ``MarkdownIndex`` - a fully
indexed, queryable representation of sections and fenced code blocks.  All
structural information (hierarchy, parent/child relationships, code block
membership) is derived from the marko AST, which ensures that ``##`` headings
inside fenced code blocks are never misidentified as section headings.

Line attribution is best-effort: marko does not attach line numbers to AST
nodes, so this module tracks cumulative line positions by scanning the raw
Markdown text alongside the tree walk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import marko
import marko.block
import marko.inline

from .models import CodeBlockRef, MarkdownIndex, SectionRef

__all__ = ["extract_section_body", "parse_markdown"]


# ---------------------------------------------------------------------------
# Internal builder types
# ---------------------------------------------------------------------------


@dataclass
class _SectionBuilder:
    """Mutable accumulator for a section being constructed during the walk.

    Args:
        id: Assigned section ID.
        selector: Hierarchical selector (e.g. ``h2.1``).
        slug: URL-safe slug.
        title: Raw heading text.
        level: Heading level 1-6.
        start_line: 0-based line index of the heading.
        end_line: 0-based line index of the last line in this section.
        parent_id: ID of the parent section (``None`` for root sections).
        child_ids: Mutable list of direct child section IDs.
        code_block_ids: Mutable list of code block IDs in this section.
    """

    id: str
    selector: str
    slug: str
    title: str
    level: int
    start_line: int
    end_line: int
    parent_id: str | None = None
    child_ids: list[str] = field(default_factory=list)
    code_block_ids: list[str] = field(default_factory=list)

    def to_ref(self) -> SectionRef:
        """Convert to an immutable ``SectionRef``.

        Returns:
            A ``SectionRef`` populated from this builder's fields.
        """
        return SectionRef(
            id=self.id,
            selector=self.selector,
            slug=self.slug,
            title=self.title,
            level=self.level,
            start_line=self.start_line,
            end_line=self.end_line,
            child_ids=list(self.child_ids),
            code_block_ids=list(self.code_block_ids),
        )


@dataclass
class _WalkState:
    """Mutable accumulator for the full AST walk.

    Centralises all counters and index dicts so ``parse_markdown`` does not
    exceed the local-variable limit.

    Args:
        total_lines: Total source line count, used for end_line defaults.
        section_builders: Map from section ID to its ``_SectionBuilder``.
        sections_by_slug: Map from slug to list of section IDs.
        sections_by_selector: Map from selector string to section ID.
        root_section_ids: Ordered list of top-level section IDs.
        code_blocks: Map from code block ID to ``CodeBlockRef``.
        document_order: Section IDs in document order.
        open_stack: Stack of currently open section builders.
        section_counter: Monotonically increasing section ID counter.
        code_counter: Monotonically increasing code block ID counter.
    """

    total_lines: int
    section_builders: dict[str, _SectionBuilder] = field(default_factory=dict)
    sections_by_slug: dict[str, list[str]] = field(default_factory=dict)
    sections_by_selector: dict[str, str] = field(default_factory=dict)
    root_section_ids: list[str] = field(default_factory=list)
    code_blocks: dict[str, CodeBlockRef] = field(default_factory=dict)
    document_order: list[str] = field(default_factory=list)
    open_stack: list[_SectionBuilder] = field(default_factory=list)
    section_counter: int = 0
    code_counter: int = 0

    def active_section_id(self) -> str | None:
        """Return the ID of the innermost open section, or ``None``.

        Returns:
            Section ID string, or ``None`` when no section is open.
        """
        return self.open_stack[-1].id if self.open_stack else None

    def close_sections_at_or_below(self, level: int, end_line: int) -> None:
        """Close all open sections whose level is >= *level*.

        Args:
            level: Heading level that triggered the closure.
            end_line: Line index to assign as the end of closed sections.
        """
        while self.open_stack and self.open_stack[-1].level >= level:
            self.open_stack[-1].end_line = end_line
            self.open_stack.pop()

    def next_section_id(self) -> str:
        """Return the next section ID and advance the counter.

        Returns:
            Section ID string in the form ``sec_NNNN``.
        """
        self.section_counter += 1
        return f"sec_{self.section_counter:04d}"

    def next_code_id(self) -> str:
        """Return the next code block ID and advance the counter.

        Returns:
            Code block ID string in the form ``code_NNNN``.
        """
        self.code_counter += 1
        return f"code_{self.code_counter:04d}"


# ---------------------------------------------------------------------------
# Slug generation
# ---------------------------------------------------------------------------


def _make_slug(title: str) -> str:
    """Convert a heading title to a URL-safe slug.

    Converts to lower-case, replaces one or more whitespace characters with
    a single hyphen, and strips all remaining non-alphanumeric non-hyphen
    characters.

    Args:
        title: Raw heading text.

    Returns:
        Lower-case hyphenated slug.

    Examples:
        >>> _make_slug("Hello World")
        'hello-world'
        >>> _make_slug("Pydantic v2 Models!")
        'pydantic-v2-models'
    """
    lowered = title.lower()
    hyphenated = re.sub(r"\s+", "-", lowered)
    return re.sub(r"[^a-z0-9\-]", "", hyphenated)


# ---------------------------------------------------------------------------
# Heading text extraction
# ---------------------------------------------------------------------------


def _heading_text(node: marko.block.Heading) -> str:
    """Extract the plain text from a marko Heading node.

    Args:
        node: A marko ``Heading`` AST node.

    Returns:
        Concatenated text of all ``RawText`` children.
    """
    parts: list[str] = [child.children for child in node.children if isinstance(child, marko.inline.RawText)]
    return "".join(parts)


# ---------------------------------------------------------------------------
# Fenced code content extraction
# ---------------------------------------------------------------------------


def _fenced_code_content(node: marko.block.FencedCode) -> str:
    """Extract the raw text content from a marko FencedCode node.

    FencedCode.children is a list of ``RawText`` nodes in practice.
    This helper accesses the first child's ``.children`` attribute via a
    safe isinstance check, avoiding unresolved-attribute type errors.

    Args:
        node: A marko ``FencedCode`` AST node.

    Returns:
        The raw content string, or an empty string when the block is empty.
    """
    if not node.children:
        return ""
    first = node.children[0]
    if isinstance(first, marko.inline.RawText):
        return first.children
    return ""


# ---------------------------------------------------------------------------
# Line position tracker
# ---------------------------------------------------------------------------


class _LineTracker:
    """Track cumulative line offsets for AST nodes by walking the raw source.

    marko does not expose line numbers on AST nodes, so this class
    maintains a cursor into the raw source string and uses string searching
    to attribute source positions to each top-level block.

    The tracker always moves the cursor forward - it never searches
    backwards - so it is O(N) in the source length.

    Args:
        source: The raw Markdown string that was parsed.
    """

    def __init__(self, source: str) -> None:
        """Initialise with the raw Markdown source string.

        Args:
            source: The raw Markdown string that was parsed.
        """
        self._source = source
        self._lines = source.splitlines(keepends=True)
        self._cursor: int = 0

    def total_lines(self) -> int:
        """Return the total number of lines in the source.

        Returns:
            Integer line count.
        """
        return len(self._lines)

    def locate_heading(self, level: int, title: str) -> int:
        """Return the 0-based line index of the next occurrence of this heading.

        Searches forward from the current cursor position.

        Args:
            level: Heading level (1-6).
            title: Expected heading title text (used to disambiguate).

        Returns:
            0-based line index, or the current cursor position when the
            heading cannot be located (best-effort).
        """
        prefix = "#" * level + " "
        for idx in range(self._cursor, len(self._lines)):
            line = self._lines[idx].rstrip("\n\r")
            if line.startswith(prefix):
                candidate = line[level + 1 :].strip()
                if candidate == title:
                    self._cursor = idx
                    return idx
        return self._cursor

    def locate_fence(self, lang: str, content_preview: str) -> int:
        """Return the 0-based line index of the next opening fence matching *lang*.

        Args:
            lang: Expected language tag (may be empty string).
            content_preview: First 20 characters of fence content used to
                disambiguate when multiple fences share the same language.

        Returns:
            0-based line index, or current cursor position (best-effort).
        """
        for idx in range(self._cursor, len(self._lines)):
            line = self._lines[idx].rstrip("\n\r")
            if line.startswith(("```", "~~~")):
                fence_lang = line.lstrip("`~").strip()
                if fence_lang == lang:
                    next_line = self._lines[idx + 1].rstrip("\n\r") if idx + 1 < len(self._lines) else ""
                    if not content_preview or next_line.startswith(content_preview[:20]):
                        self._cursor = idx
                        return idx
        return self._cursor

    def fence_end_line(self, start: int, content: str) -> int:
        """Return the 0-based line index of the closing fence for a code block.

        Args:
            start: 0-based line index of the opening fence.
            content: Full content of the code block (without fence lines).

        Returns:
            0-based line index of the closing fence.
        """
        content_lines = content.count("\n")
        return start + 1 + content_lines


# ---------------------------------------------------------------------------
# Hierarchical selector builder
# ---------------------------------------------------------------------------


def _build_hierarchical_selector(level: int, sibling_index: int, parent: _SectionBuilder | None) -> str:
    """Return a selector that encodes the full parent chain for a section.

    The format is ``h{level}.{path}`` where ``path`` is the dot-joined
    ancestry path from root (level-1) down to the current sibling index.

    For a root section (no parent): ``h{level}.{sibling_index}``
    For a child section: ``h{level}.{parent_path}.{sibling_index}``
    where ``parent_path`` is the path portion of the parent's selector
    (i.e. the parent selector minus its ``h{N}.`` prefix).

    Examples:
        >>> _build_hierarchical_selector(1, 1, None)
        'h1.1'
        >>> parent_h1 = ...  # selector = 'h1.1'
        >>> _build_hierarchical_selector(2, 1, parent_h1)
        'h2.1.1'
        >>> parent_h2 = ...  # selector = 'h2.1.1'
        >>> _build_hierarchical_selector(3, 1, parent_h2)
        'h3.1.1.1'

    Args:
        level: Heading level (1-6).
        sibling_index: 1-based sibling position under the current parent.
        parent: The immediate parent ``_SectionBuilder``, or ``None`` for roots.

    Returns:
        Selector string such as ``h2.1.2`` or ``h3.1.2.1``.
    """
    if parent is None:
        return f"h{level}.{sibling_index}"
    # Strip the h{N}. prefix from the parent selector to obtain its path.
    parent_path = parent.selector.split(".", 1)[1]
    return f"h{level}.{parent_path}.{sibling_index}"


# ---------------------------------------------------------------------------
# Summary generator for code blocks
# ---------------------------------------------------------------------------


def _code_summary(language: str | None, content: str) -> str:
    """Generate a deterministic one-line summary for a code block.

    Args:
        language: Language tag or ``None``.
        content: Full code block content.

    Returns:
        Summary in the format ``"{language}, {n} lines, {first_line_preview}"``.
    """
    lang_label = language or "text"
    lines = content.splitlines()
    n_lines = len(lines)
    preview = lines[0][:40].strip() if lines else ""
    return f"{lang_label}, {n_lines} lines, {preview}"


# ---------------------------------------------------------------------------
# Node processors
# ---------------------------------------------------------------------------


def _process_heading(
    node: marko.block.Heading, state: _WalkState, tracker: _LineTracker, sibling_counts: dict[str | None, int]
) -> None:
    """Process a single Heading node and update *state*.

    Args:
        node: The heading AST node.
        state: Mutable walk state to update.
        tracker: Line position tracker.
        sibling_counts: Mutable dict mapping parent_id (or None for roots)
            to the count of children already registered under that parent.
            Updated in place.
    """
    title = _heading_text(node)
    level = node.level
    start_line = tracker.locate_heading(level, title)

    state.close_sections_at_or_below(level, max(0, start_line - 1))

    # Determine parent after closing deeper sections.
    parent_builder: _SectionBuilder | None = state.open_stack[-1] if state.open_stack else None
    parent_id: str | None = parent_builder.id if parent_builder is not None else None

    # Increment sibling count under this parent (key = parent_id or None for roots).
    sibling_counts[parent_id] = sibling_counts.get(parent_id, 0) + 1
    sibling_index = sibling_counts[parent_id]

    sec_id = state.next_section_id()
    selector = _build_hierarchical_selector(level, sibling_index, parent_builder)
    slug = _make_slug(title)

    builder = _SectionBuilder(
        id=sec_id,
        selector=selector,
        slug=slug,
        title=title,
        level=level,
        start_line=start_line,
        end_line=state.total_lines - 1,
        parent_id=parent_id,
    )
    state.section_builders[sec_id] = builder
    state.document_order.append(sec_id)

    if parent_id is None:
        state.root_section_ids.append(sec_id)
    else:
        state.section_builders[parent_id].child_ids.append(sec_id)

    state.sections_by_slug.setdefault(slug, []).append(sec_id)
    state.sections_by_selector[selector] = sec_id
    state.open_stack.append(builder)


def _process_fenced_code(node: marko.block.FencedCode, state: _WalkState, tracker: _LineTracker) -> None:
    """Process a single FencedCode node and update *state*.

    Args:
        node: The fenced code AST node.
        state: Mutable walk state to update.
        tracker: Line position tracker.
    """
    raw_content = _fenced_code_content(node)
    lang: str | None = node.lang or None
    start_line = tracker.locate_fence(node.lang or "", raw_content[:20])
    end_line = tracker.fence_end_line(start_line, raw_content)

    code_id = state.next_code_id()
    block = CodeBlockRef(
        id=code_id,
        language=lang,
        content=raw_content,
        start_line=start_line,
        end_line=end_line,
        section_id=state.active_section_id(),
        summary=_code_summary(lang, raw_content),
    )
    state.code_blocks[code_id] = block

    if state.open_stack:
        state.open_stack[-1].code_block_ids.append(code_id)


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------


def parse_markdown(markdown: str, source: str = "inline") -> MarkdownIndex:
    """Parse a Markdown string into a fully indexed ``MarkdownIndex``.

    Uses ``marko.parse`` to produce an AST, then walks ``Document.children``
    to extract headings and fenced code blocks.  Heading nesting is resolved
    via a level-stack algorithm (compatible with real-world documents that
    skip levels or have irregular nesting).

    Headings inside fenced code blocks are excluded by construction - the
    marko AST represents them as ``FencedCode`` content, not as ``Heading``
    nodes.

    Args:
        markdown: Raw Markdown string to parse.
        source: Human-readable label stored in the returned index
            (typically a filename or ``"inline"``).

    Returns:
        A populated ``MarkdownIndex`` with all sections and code blocks.
    """
    doc = marko.parse(markdown)
    tracker = _LineTracker(markdown)
    # Maps parent_id (or None for root) to the count of children already added.
    sibling_counts: dict[str | None, int] = {}
    state = _WalkState(total_lines=tracker.total_lines())

    for node in doc.children:
        if isinstance(node, marko.block.Heading):
            _process_heading(node, state, tracker, sibling_counts)
        elif isinstance(node, marko.block.FencedCode):
            _process_fenced_code(node, state, tracker)

    for builder in state.open_stack:
        builder.end_line = state.total_lines - 1

    sections: dict[str, SectionRef] = {sid: state.section_builders[sid].to_ref() for sid in state.document_order}

    return MarkdownIndex(
        source=source,
        root_section_ids=state.root_section_ids,
        sections=sections,
        sections_by_slug=state.sections_by_slug,
        sections_by_selector=state.sections_by_selector,
        code_blocks=state.code_blocks,
    )


# ---------------------------------------------------------------------------
# Body extraction
# ---------------------------------------------------------------------------


def extract_section_body(markdown: str, section: SectionRef, index: MarkdownIndex) -> str:
    """Return the raw Markdown body of *section*, with child sections excluded.

    Only the lines belonging to this section but not to any direct child
    section are returned.  Lines are taken verbatim from the original source
    so that the returned text is safe to re-parse or display.

    Args:
        markdown: Original Markdown source.
        section: The section whose body to extract.
        index: The ``MarkdownIndex`` produced from the same *markdown*.

    Returns:
        The section body text (may be empty for sections with only children).
    """
    lines = markdown.splitlines(keepends=True)

    body_start = section.start_line + 1
    body_end = section.end_line + 1

    if section.child_ids:
        first_child = index.sections[section.child_ids[0]]
        body_end = first_child.start_line

    return "".join(lines[body_start:body_end])
