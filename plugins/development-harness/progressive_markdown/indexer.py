"""Build MarkdownDocument from a ParserResult.

Walks the markdown-it-py token stream linearly to extract heading structure,
code blocks, and build all lookup indexes. Token positions use the map
attribute which provides ``[start_line, end_line]`` in 0-based line numbers;
``token.map[1]`` is **exclusive** (first line after the token). Every
``SourceSpan`` constructed here uses **inclusive** ``end_line``, so all
conversions apply ``token.map[1] - 1`` to produce the last line of the span.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .models import CodeBlock, MarkdownDocument, SectionNode, SourceSpan

if TYPE_CHECKING:
    from .parser import ParserResult

__all__ = ["MarkdownIndexer"]


# ---------------------------------------------------------------------------
# Internal builder types
# ---------------------------------------------------------------------------


@dataclass
class _SectionBuilder:
    """Mutable accumulator for a section being constructed during the walk."""

    section_id: str
    selector: str
    slug: str
    title: str
    level: int
    heading_start: int  # 0-based line of heading_open token
    heading_end: int  # map[1] of heading_open (body start line)
    section_end: int  # updated as later headings are encountered
    parent_id: str | None = None
    child_ids: list[str] = field(default_factory=list)
    link_ref_ids: list[str] = field(default_factory=list)
    code_block_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Slug generation
# ---------------------------------------------------------------------------


def _make_slug(title: str) -> str:
    """Convert a heading title to a URL-safe slug.

    Args:
        title: Raw heading text.

    Returns:
        Lowercase hyphenated slug.
    """
    lowered = title.lower()
    hyphenated = re.sub(r"\s+", "-", lowered)
    return re.sub(r"[^a-z0-9\-]", "", hyphenated)


# ---------------------------------------------------------------------------
# Hierarchical selector builder
# ---------------------------------------------------------------------------


def _build_selector(level: int, sibling_index: int, parent: _SectionBuilder | None) -> str:
    """Build a hierarchical selector encoding the full parent chain.

    Args:
        level: Heading level 1-6.
        sibling_index: 1-based position among siblings under this parent.
        parent: Immediate parent builder, or None for root sections.

    Returns:
        Selector string such as ``h2.1.2`` or ``h3.1.2.1``.
    """
    if parent is None:
        return f"h{level}.{sibling_index}"
    parent_path = parent.selector.split(".", 1)[1]
    return f"h{level}.{parent_path}.{sibling_index}"


# ---------------------------------------------------------------------------
# Deterministic code block summary
# ---------------------------------------------------------------------------


def _code_summary(language: str | None, content: str) -> str:
    """Generate a deterministic one-line summary for a code block.

    Args:
        language: Language tag or None.
        content: Full code block content.

    Returns:
        Summary in the format ``"{language}, {n} lines, {preview}"``.
    """
    lang_label = language or "text"
    content_lines = content.splitlines()
    n_lines = len(content_lines)
    preview = content_lines[0][:40].strip() if content_lines else ""
    return f"{lang_label}, {n_lines} lines, {preview}"


# ---------------------------------------------------------------------------
# Main indexer
# ---------------------------------------------------------------------------


class MarkdownIndexer:
    """Build a MarkdownDocument from a ParserResult.

    Uses a heading stack algorithm compatible with documents that skip
    heading levels or have irregular nesting. Headings inside fenced
    code blocks are excluded by construction: the markdown-it-py parser
    represents them as fence content tokens, not heading_open tokens.

    Example::

        indexer = MarkdownIndexer()
        document = indexer.build(parser_result)
    """

    def build(self, result: ParserResult) -> MarkdownDocument:
        """Build and return a MarkdownDocument from a ParserResult.

        Args:
            result: Output from a MarkdownParser.parse() call.

        Returns:
            Fully indexed MarkdownDocument.
        """
        total_lines = len(result.lines)
        builders: dict[str, _SectionBuilder] = {}
        document_order: list[str] = []
        root_section_ids: list[str] = []
        sections_by_slug: dict[str, list[str]] = {}
        sections_by_selector: dict[str, str] = {}
        sections_by_title: dict[str, list[str]] = {}
        code_blocks: dict[str, CodeBlock] = {}

        # Heading stack: tracks open sections by nesting.
        open_stack: list[_SectionBuilder] = []
        # Sibling counts keyed by parent_id (None = root level).
        sibling_counts: dict[str | None, int] = {}
        section_counter = 0
        code_counter = 0

        tokens = result.tokens
        token_index = 0
        n_tokens = len(tokens)

        while token_index < n_tokens:
            token = tokens[token_index]

            if token.type == "heading_open":
                # Next token is always inline with the heading text.
                title = ""
                if token_index + 1 < n_tokens and tokens[token_index + 1].type == "inline":
                    title = tokens[token_index + 1].content
                    token_index += 1  # consume the inline token

                level = int(token.tag[1])  # h1..h6 → 1..6
                heading_start = token.map[0] if token.map else 0
                heading_end = token.map[1] if token.map else heading_start + 1

                # Close all open sections at the same or deeper level.
                while open_stack and open_stack[-1].level >= level:
                    closed = open_stack.pop()
                    closed.section_end = max(0, heading_start - 1)

                parent = open_stack[-1] if open_stack else None
                parent_id = parent.section_id if parent else None

                sibling_counts[parent_id] = sibling_counts.get(parent_id, 0) + 1
                sibling_index = sibling_counts[parent_id]

                section_counter += 1
                section_id = f"sec_{section_counter:04d}"
                selector = _build_selector(level, sibling_index, parent)
                slug = _make_slug(title)

                builder = _SectionBuilder(
                    section_id=section_id,
                    selector=selector,
                    slug=slug,
                    title=title,
                    level=level,
                    heading_start=heading_start,
                    heading_end=heading_end,
                    section_end=total_lines - 1,
                    parent_id=parent_id,
                )
                builders[section_id] = builder
                document_order.append(section_id)

                if parent_id is None:
                    root_section_ids.append(section_id)
                else:
                    builders[parent_id].child_ids.append(section_id)

                sections_by_slug.setdefault(slug, []).append(section_id)
                sections_by_selector[selector] = section_id
                sections_by_title.setdefault(title, []).append(section_id)
                open_stack.append(builder)

            elif token.type == "fence":
                code_counter += 1
                code_id = f"code_{code_counter:04d}"
                info = token.info.strip() if token.info else None
                language = info.split()[0] if info else None
                content = token.content
                span_start = token.map[0] if token.map else 0
                span_end = token.map[1] - 1 if token.map else span_start

                containing_section: str | None = None
                if open_stack:
                    containing_section = open_stack[-1].section_id
                    open_stack[-1].code_block_ids.append(code_id)

                code_block = CodeBlock(
                    id=code_id,
                    language=language,
                    info=info,
                    content=content,
                    span=SourceSpan(start_line=span_start, end_line=span_end),
                    section_id=containing_section,
                    summary=_code_summary(language, content),
                )
                code_blocks[code_id] = code_block

            token_index += 1

        # Close any remaining open sections.
        for builder in open_stack:
            builder.section_end = total_lines - 1

        # Build final SectionNode objects.
        sections: dict[str, SectionNode] = {}
        for section_id in document_order:
            b = builders[section_id]

            # Body span: from line after heading to line before first child
            # (or section end when no children).
            body_start = b.heading_end
            if b.child_ids:
                first_child_id = b.child_ids[0]
                first_child = builders[first_child_id]
                body_end = max(body_start, first_child.heading_start - 1)
            else:
                body_end = b.section_end

            sections[section_id] = SectionNode(
                id=section_id,
                selector=b.selector,
                slug=b.slug,
                title=b.title,
                level=b.level,
                span=SourceSpan(start_line=b.heading_start, end_line=b.section_end),
                heading_span=SourceSpan(start_line=b.heading_start, end_line=b.heading_end - 1),
                body_span=SourceSpan(start_line=body_start, end_line=max(body_start, body_end)),
                parent_id=b.parent_id,
                child_ids=list(b.child_ids),
                code_block_ids=list(b.code_block_ids),
            )

        return MarkdownDocument(
            source=result.source,
            raw_markdown=result.raw_markdown,
            lines=result.lines,
            root_section_ids=root_section_ids,
            sections=sections,
            sections_by_slug=sections_by_slug,
            sections_by_selector=sections_by_selector,
            sections_by_title=sections_by_title,
            code_blocks=code_blocks,
        )
