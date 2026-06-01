"""Pydantic v2 public models for the progressive_markdown package.

All models are plain data carriers with no parsing or rendering logic.
"""

from __future__ import annotations

import os
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

# Derived from MAX_MCP_OUTPUT_TOKENS at import time, leaving 500 tokens of overhead for
# envelope fields.  When the env var is absent, 9_500 tokens is the fallback ceiling.
_DEFAULT_BUDGET: int = (
    int(os.environ["MAX_MCP_OUTPUT_TOKENS"]) - 500 if "MAX_MCP_OUTPUT_TOKENS" in os.environ else 9_500
)

# Markdown heading levels are defined by the CommonMark spec as 1-6.
_MAX_HEADING_LEVEL: int = 6

__all__ = [
    "CodeBlock",
    "LinkKind",
    "LinkRef",
    "MarkdownDocument",
    "NavigationKind",
    "NavigationResult",
    "NavigatorOptions",
    "PMBaseModel",
    "Page",
    "SectionNode",
    "SourceSpan",
]


class PMBaseModel(BaseModel):
    """Base model shared by all progressive_markdown models."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        frozen=False,
        str_strip_whitespace=False,
        arbitrary_types_allowed=False,
    )


class LinkKind(StrEnum):
    """Distinguishes the different kinds of markdown links."""

    link = "link"
    image = "image"
    autolink = "autolink"
    reference_definition = "reference_definition"


class NavigationKind(StrEnum):
    """Identifies the kind of NavigationResult returned by the navigator."""

    document_map = "document_map"
    section_map = "section_map"
    section_body = "section_body"
    code_block = "code_block"
    links = "links"
    search_results = "search_results"
    error = "error"


class SourceSpan(PMBaseModel):
    """Line span within the source markdown document (0-based).

    Args:
        start_line: 0-based line index of the first line (inclusive).
        end_line: 0-based line index of the last line (inclusive).
    """

    start_line: int
    end_line: int

    @field_validator("start_line")
    @classmethod
    def _validate_start_line(cls, v: int) -> int:
        """Validate start_line is non-negative.

        Args:
            v: Value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: When start_line is negative.
        """
        if v < 0:
            msg = "start_line must be >= 0"
            raise ValueError(msg)
        return v

    @field_validator("end_line")
    @classmethod
    def _validate_end_line(cls, v: int, info: object) -> int:
        """Validate end_line >= start_line.

        Args:
            v: Value to validate.
            info: Pydantic validation info with field data.

        Returns:
            The validated value.

        Raises:
            ValueError: When end_line < start_line.
        """
        # info.data holds previously validated fields
        data = getattr(info, "data", {})
        start = data.get("start_line", 0)
        if v < start:
            msg = f"end_line ({v}) must be >= start_line ({start})"
            raise ValueError(msg)
        return v


class LinkRef(PMBaseModel):
    """A link or image reference extracted from a markdown document.

    Args:
        id: Stable unique identifier assigned by the extractor.
        text: Display text (link label or alt text for images).
        target: URL or path the link points to.
        title: Optional link title attribute.
        kind: Classification of the link type.
        span: Source span within the document, when available.
        source_token_type: Raw markdown-it token type for the link.
    """

    id: str
    text: str
    target: str
    title: str | None = None
    kind: LinkKind
    span: SourceSpan | None = None
    source_token_type: str | None = None


class CodeBlock(PMBaseModel):
    """A fenced code block extracted from a markdown document.

    Args:
        id: Stable identifier (e.g. ``code_0001``).
        language: Fenced code block language tag, or None when absent.
        info: Full info string from the fence line (language + optional args).
        content: Raw content of the code block without fence delimiters.
        span: Source span within the document.
        section_id: ID of the immediately containing section, or None.
        summary: Deterministic one-line summary (no LLM call).
    """

    id: str
    language: str | None = None
    info: str | None = None
    content: str
    span: SourceSpan | None = None
    section_id: str | None = None
    summary: str


class SectionNode(PMBaseModel):
    """A section node in the parsed markdown section tree.

    Args:
        id: Stable identifier (e.g. ``sec_0001``).
        selector: Hierarchical path selector (e.g. ``h2.1.2``).
        slug: URL-safe slug derived from the heading text.
        title: Raw heading text as it appears in the document.
        level: Heading level 1-6.
        span: Full section span including all child sections.
        heading_span: Span of the heading line itself.
        body_span: Span of the section body (after heading, before first child).
        parent_id: ID of the parent section, or None for root sections.
        child_ids: Ordered list of direct child section IDs.
        link_ref_ids: IDs of links appearing in this section's body.
        code_block_ids: IDs of code blocks in this section's body.
    """

    id: str
    selector: str
    slug: str
    title: str
    level: int
    span: SourceSpan
    heading_span: SourceSpan
    body_span: SourceSpan
    parent_id: str | None = None
    child_ids: list[str] = Field(default_factory=list)
    link_ref_ids: list[str] = Field(default_factory=list)
    code_block_ids: list[str] = Field(default_factory=list)

    @field_validator("level")
    @classmethod
    def _validate_level(cls, v: int) -> int:
        """Validate level is between 1 and 6.

        Args:
            v: Value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: When level is outside 1-6.
        """
        if not (1 <= v <= _MAX_HEADING_LEVEL):
            msg = f"level must be between 1 and {_MAX_HEADING_LEVEL}, got {v}"
            raise ValueError(msg)
        return v


class MarkdownDocument(PMBaseModel):
    """Full index of a parsed markdown document.

    Args:
        source: Human-readable source label (filename or ``"inline"``).
        raw_markdown: Original markdown text.
        lines: Source lines split from raw_markdown.
        root_section_ids: Ordered IDs of top-level (no-parent) sections.
        sections: Mapping from section ID to SectionNode.
        sections_by_slug: Mapping from slug to list of section IDs.
        sections_by_selector: Mapping from selector string to section ID.
        sections_by_title: Mapping from title to list of section IDs.
        links: Mapping from link ID to LinkRef.
        code_blocks: Mapping from code block ID to CodeBlock.
    """

    source: str
    raw_markdown: str
    lines: list[str]
    root_section_ids: list[str] = Field(default_factory=list)
    sections: dict[str, SectionNode] = Field(default_factory=dict)
    sections_by_slug: dict[str, list[str]] = Field(default_factory=dict)
    sections_by_selector: dict[str, str] = Field(default_factory=dict)
    sections_by_title: dict[str, list[str]] = Field(default_factory=dict)
    links: dict[str, LinkRef] = Field(default_factory=dict)
    code_blocks: dict[str, CodeBlock] = Field(default_factory=dict)


class Page(PMBaseModel):
    """A single page of paginated content.

    Args:
        content: Text content for this page.
        page_number: 1-based page number.
        total_pages: Total number of pages.
        token_count: Approximate token count of content.
        budget: Token budget used for this page.
    """

    content: str
    page_number: int
    total_pages: int
    token_count: int
    budget: int

    @field_validator("page_number")
    @classmethod
    def _validate_page_number(cls, v: int) -> int:
        """Validate page_number >= 1.

        Args:
            v: Value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: When page_number < 1.
        """
        if v < 1:
            msg = "page_number must be >= 1"
            raise ValueError(msg)
        return v

    @field_validator("total_pages")
    @classmethod
    def _validate_total_pages(cls, v: int) -> int:
        """Validate total_pages >= 1.

        Args:
            v: Value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: When total_pages < 1.
        """
        if v < 1:
            msg = "total_pages must be >= 1"
            raise ValueError(msg)
        return v

    @field_validator("budget")
    @classmethod
    def _validate_budget(cls, v: int) -> int:
        """Validate budget > 0.

        Args:
            v: Value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: When budget <= 0.
        """
        if v <= 0:
            msg = "budget must be > 0"
            raise ValueError(msg)
        return v


class NavigationResult(PMBaseModel):
    """The result returned by all ProgressiveMarkdownNavigator public methods.

    Args:
        kind: Classification of what this result contains.
        title: Human-readable title for the result.
        pages: Ordered list of content pages.
        current_page: 1-based index of the current page.
        total_pages: Total number of pages.
        metadata: Arbitrary JSON-serializable metadata for the result.

    Computed:
        has_more: True when current_page < total_pages.
    """

    kind: NavigationKind
    title: str
    pages: list[Page]
    current_page: int
    total_pages: int
    metadata: dict[str, object] = Field(default_factory=dict)

    @field_validator("current_page")
    @classmethod
    def _validate_current_page(cls, v: int) -> int:
        """Validate current_page >= 1.

        Args:
            v: Value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: When current_page < 1.
        """
        if v < 1:
            msg = "current_page must be >= 1"
            raise ValueError(msg)
        return v

    @field_validator("total_pages")
    @classmethod
    def _validate_total_pages(cls, v: int) -> int:
        """Validate total_pages >= 1.

        Args:
            v: Value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: When total_pages < 1.
        """
        if v < 1:
            msg = "total_pages must be >= 1"
            raise ValueError(msg)
        return v

    @computed_field
    @property
    def has_more(self) -> bool:
        """Return True when more pages follow the current page.

        Returns:
            True when current_page < total_pages, False otherwise.
        """
        return self.current_page < self.total_pages

    def current_content(self) -> str:
        """Return the content of the current page.

        Returns:
            Content string for the current page, or empty string when no pages.
        """
        if not self.pages:
            return ""
        idx = min(self.current_page - 1, len(self.pages) - 1)
        return self.pages[idx].content


class NavigatorOptions(PMBaseModel):
    """Configuration options for ProgressiveMarkdownNavigator.

    Args:
        default_budget: Default token budget per page.
        parser_preset: markdown-it-py preset to use (e.g. ``"commonmark"``).
        tiktoken_model: tiktoken model name for encoding selection.
        tiktoken_encoding: tiktoken encoding name (used when tiktoken_model is None).
        extract_code_blocks: Whether to extract and index code blocks.
        include_links_in_maps: Whether to include link counts in document maps.
    """

    default_budget: int = _DEFAULT_BUDGET
    parser_preset: str = "commonmark"
    tiktoken_model: str | None = None
    tiktoken_encoding: str = "cl100k_base"
    extract_code_blocks: bool = True
    include_links_in_maps: bool = True
