"""Progressive Markdown navigation layer for the development-harness plugin.

Provides token-budget-aware section navigation, code block viewing, link
inventory, and search over Markdown documents.

Typical usage::

    from progressive_markdown import ProgressiveMarkdownNavigator, NavigatorOptions

    nav = ProgressiveMarkdownNavigator.from_markdown(content, source="README.md")
    toc = nav.map()  # paginated document map
    section = nav.view_section("installation")  # view a specific section
    code = nav.view_code("code_0001")  # view a code block

List navigator exports (structured data pagination and disclosure)::

    from progressive_markdown.list_navigator import (
        ENCODING,
        TOKEN_BUDGET,
        DisclosureConfig,
        ProgressiveDisclosure,
        chunk_text,
        paginate_results,
    )
"""

from __future__ import annotations

from .exceptions import (
    AmbiguousSectionRefError,
    CodeBlockNotFoundError,
    DocumentNotLoadedError,
    PaginationError,
    ParserError,
    ProgressiveMarkdownError,
    ProviderError,
    SectionNotFoundError,
)
from .list_navigator import chunk_text, paginate_results
from .models import (
    CodeBlock,
    LinkKind,
    LinkRef,
    MarkdownDocument,
    NavigationKind,
    NavigationResult,
    NavigatorOptions,
    Page,
    SectionNode,
    SourceSpan,
)
from .navigator import ProgressiveMarkdownNavigator
from .providers import CallableMarkdownContentProvider, MarkdownContentProvider, MCPMarkdownContentProvider

__all__ = [
    "AmbiguousSectionRefError",
    "CallableMarkdownContentProvider",
    "CodeBlock",
    "CodeBlockNotFoundError",
    "DocumentNotLoadedError",
    "LinkKind",
    "LinkRef",
    "MCPMarkdownContentProvider",
    "MarkdownContentProvider",
    "MarkdownDocument",
    "NavigationKind",
    "NavigationResult",
    "NavigatorOptions",
    "Page",
    "PaginationError",
    "ParserError",
    "ProgressiveMarkdownError",
    "ProgressiveMarkdownNavigator",
    "ProviderError",
    "SectionNode",
    "SectionNotFoundError",
    "SourceSpan",
    "chunk_text",
    "paginate_results",
]
