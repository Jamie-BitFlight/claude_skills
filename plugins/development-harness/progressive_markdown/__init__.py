"""Progressive Markdown navigation layer for the development-harness plugin.

Provides token-budget-aware section navigation, code block viewing, link
inventory, and search over Markdown documents.

Navigator facade
----------------
``ProgressiveMarkdownNavigator``
    Main facade for navigating a Markdown document with token-budget awareness.
    Exposes ``map()``, ``view_section()``, ``view_code()``, ``search()``, and
    ``view_links()``.  Supports eager loading via ``from_markdown()`` and lazy
    loading via content providers.

Configuration
-------------
``NavigatorOptions``
    Configuration dataclass for ``ProgressiveMarkdownNavigator``.  Controls
    token budget, default page size, and heading depth limits.

Result types
------------
``NavigationResult``
    Structured result returned by all public ``ProgressiveMarkdownNavigator``
    methods.  Carries response content, pagination state, and navigation
    metadata.
``NavigationKind``
    StrEnum classifying the type of navigation result (map, section, code,
    search, links).
``Page``
    Paginated slice of a navigation result, with ``current_page``,
    ``total_pages``, and ``has_more`` fields.

Document model
--------------
``MarkdownDocument``
    Fully-parsed Markdown document: section tree, code block index, link
    inventory, and total token count.
``SectionNode``
    A single section within the document tree.  Carries heading level, slug,
    selector, source span, and child section IDs.
``CodeBlock``
    A fenced code block extracted from the document.  Carries its block ID,
    language tag, source span, and raw content.
``LinkRef``
    A hyperlink reference resolved from the document.  Carries URL, display
    text, ``LinkKind``, and ``SourceSpan``.
``LinkKind``
    Enum distinguishing inline, reference-style, and autolink variants.
``SourceSpan``
    A ``(start_line, end_line)`` pair marking where a node originates in
    the source Markdown.

Parsing internals
-----------------
``MarkdownItParser``
    Low-level tokenizer wrapper.  Converts raw Markdown source into a
    ``ParserResult`` token stream consumed by ``MarkdownIndexer``.
``ParserResult``
    Dataclass produced by ``MarkdownItParser.parse()``.  Carries the token
    stream and source metadata; passed directly to ``MarkdownIndexer.build()``.
``MarkdownIndexer``
    Builds a ``MarkdownDocument`` from a ``ParserResult``.  Use the two-step
    sequence ``MarkdownItParser().parse(source, text)`` →
    ``MarkdownIndexer().build(result)`` when you need a ``MarkdownDocument``
    without the full navigator facade.

Content providers
-----------------
``MarkdownContentProvider``
    Protocol for objects that supply Markdown source to the navigator.
    Implement this protocol to plug in custom content sources.
``CallableMarkdownContentProvider``
    Content provider backed by a zero-argument callable.  Useful for lazy
    loading (e.g., reading a file on demand).
``MCPMarkdownContentProvider``
    Content provider that fetches Markdown from an MCP resource URI.

Exceptions
----------
``ProgressiveMarkdownError``
    Base exception for all errors raised by this package.  Catch this type
    to handle any library error uniformly.
``AmbiguousSectionRefError``
    Raised by ``view_section()`` when a slug matches multiple sections.
    Caller must use a fully-qualified selector to disambiguate.
``CodeBlockNotFoundError``
    Raised by ``view_code()`` when the requested block ID does not exist.
``DocumentNotLoadedError``
    Raised when a navigation method is called before the document is loaded.
``PaginationError``
    Raised when pagination parameters are out of range or inconsistent.
``ParserError``
    Raised when the Markdown source cannot be parsed into a document tree.
``ProviderError``
    Raised when the content provider fails to supply content.
``SectionNotFoundError``
    Raised by ``view_section()`` when the section reference does not resolve
    to any section in the document.

List pagination and disclosure (``list_navigator`` sub-module)
--------------------------------------------------------------
``ProgressiveDisclosure``
    Map, navigate, and extract from any list-of-dict structured data.
    ``select()`` and ``page()`` return ``NavigationResult``; ``index()``
    and ``search()`` return MCP-friendly dicts.
``DisclosureConfig``
    Field mapping and token-budget configuration dataclass for
    ``ProgressiveDisclosure``.
``chunk_text``
    Splits a text string into token-bounded chunks using cl100k_base encoding.
    Useful for feeding large prose into context windows incrementally.
``paginate_results``
    Paginates a list of structured items using offset/limit pagination,
    producing MCP-ready index and page responses.

Module-level constants
----------------------
``TOKEN_BUDGET``
    Token ceiling for the auto-fit binary search in ``ProgressiveDisclosure``.
    Derived from ``MAX_MCP_OUTPUT_TOKENS`` env var at import time (default 9 500).
``ENCODING``
    The tiktoken cl100k_base encoding instance used for all token counting.
    Import this singleton rather than creating a new instance to guarantee
    consistency across modules.

Typical usage — navigator facade::

    from progressive_markdown import ProgressiveMarkdownNavigator, NavigatorOptions

    nav = ProgressiveMarkdownNavigator.from_markdown(content, source="README.md")
    toc = nav.map()  # paginated document map
    section = nav.view_section("installation")  # view a specific section
    code = nav.view_code("code_0001")  # view a code block

Typical usage — list pagination and disclosure::

    from progressive_markdown.list_navigator import (
        DisclosureConfig,
        ENCODING,
        ProgressiveDisclosure,
        TOKEN_BUDGET,
        chunk_text,
        paginate_results,
    )

    config = DisclosureConfig(id_field="id", title_field="title")
    disclosure = ProgressiveDisclosure(items, config=config)
    index_page = disclosure.index()
    first_page = disclosure.page(1)  # returns NavigationResult
    item = disclosure.select("T03")  # returns NavigationResult (found or error)
    text_chunks = chunk_text(large_text, budget=TOKEN_BUDGET)
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
from .indexer import MarkdownIndexer
from .list_navigator import (
    ENCODING,
    TOKEN_BUDGET,
    DisclosureConfig,
    ProgressiveDisclosure,
    chunk_text,
    paginate_results,
)
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
from .parser import MarkdownItParser, ParserResult
from .providers import CallableMarkdownContentProvider, MarkdownContentProvider, MCPMarkdownContentProvider

__all__ = [
    "ENCODING",
    "TOKEN_BUDGET",
    "AmbiguousSectionRefError",
    "CallableMarkdownContentProvider",
    "CodeBlock",
    "CodeBlockNotFoundError",
    "DisclosureConfig",
    "DocumentNotLoadedError",
    "LinkKind",
    "LinkRef",
    "MCPMarkdownContentProvider",
    "MarkdownContentProvider",
    "MarkdownDocument",
    "MarkdownIndexer",
    "MarkdownItParser",
    "NavigationKind",
    "NavigationResult",
    "NavigatorOptions",
    "Page",
    "PaginationError",
    "ParserError",
    "ParserResult",
    "ProgressiveDisclosure",
    "ProgressiveMarkdownError",
    "ProgressiveMarkdownNavigator",
    "ProviderError",
    "SectionNode",
    "SectionNotFoundError",
    "SourceSpan",
    "chunk_text",
    "paginate_results",
]
