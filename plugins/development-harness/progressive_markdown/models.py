"""Pydantic v2 models for the progressive Markdown navigation layer.

These models describe the index produced by parsing a Markdown document
into a section tree.  They are intentionally plain data carriers with no
parsing logic; all construction happens in ``parser.py``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = ["CodeBlockRef", "MarkdownIndex", "SectionRef"]


class SectionRef(BaseModel):
    """A single section node in the parsed Markdown section tree.

    Args:
        id: Stable identifier of the form ``sec_NNNN`` (zero-padded 4-digit
            counter, assigned in document order).
        selector: Hierarchical path selector of the form ``h{level}.{n}``
            where *n* is the 1-based position among siblings at this level
            (e.g. ``h2.1``, ``h3.2``).
        slug: URL-safe slug derived from the heading text
            (lower-case, spaces replaced by hyphens, non-alphanumeric
            characters removed).
        title: Raw heading text as it appears in the document.
        level: Heading level 1-6.
        start_line: Best-effort 0-based line index of the heading itself.
        end_line: Best-effort 0-based line index of the last line that
            belongs to this section (exclusive of child sections).
        child_ids: Ordered list of direct child section IDs.
        code_block_ids: Ordered list of code block IDs whose source
            positions fall within this section's line range.
    """

    id: str
    selector: str
    slug: str
    title: str
    level: int
    start_line: int
    end_line: int
    child_ids: list[str] = Field(default_factory=list)
    code_block_ids: list[str] = Field(default_factory=list)


class CodeBlockRef(BaseModel):
    """A fenced code block extracted from the parsed Markdown document.

    Args:
        id: Stable identifier of the form ``code_NNNN`` (zero-padded
            4-digit counter, assigned in document order).
        language: Fenced code block language identifier (e.g. ``"python"``,
            ``"bash"``).  ``None`` when the fence has no language tag.
        content: Raw content of the fenced code block (without the fence
            delimiters themselves).
        start_line: Best-effort 0-based line index of the opening fence.
        end_line: Best-effort 0-based line index of the closing fence.
        section_id: ID of the immediately enclosing section, or ``None``
            when the block appears outside any section.
        summary: Deterministic one-line description in the format
            ``"{language}, {n} lines, {first_line_preview}"``.
    """

    id: str
    language: str | None = None
    content: str
    start_line: int
    end_line: int
    section_id: str | None = None
    summary: str


class MarkdownIndex(BaseModel):
    """Full index of a parsed Markdown document.

    Args:
        source: Human-readable source label (e.g. a filename or ``"inline"``).
        root_section_ids: Ordered list of top-level (no parent) section IDs.
        sections: Mapping from section ID to ``SectionRef``.
        sections_by_slug: Mapping from slug to list of section IDs sharing
            that slug (multiple sections may produce the same slug).
        sections_by_selector: Mapping from selector string to section ID.
            Selectors are unique within a document.
        code_blocks: Mapping from code block ID to ``CodeBlockRef``.
    """

    source: str
    root_section_ids: list[str] = Field(default_factory=list)
    sections: dict[str, SectionRef] = Field(default_factory=dict)
    sections_by_slug: dict[str, list[str]] = Field(default_factory=dict)
    sections_by_selector: dict[str, str] = Field(default_factory=dict)
    code_blocks: dict[str, CodeBlockRef] = Field(default_factory=dict)
