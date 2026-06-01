"""ProgressiveMarkdownNavigator facade.

Composes all package subsystems (parser, indexer, tokenizer, pagination,
renderers) behind a single, dependency-injected public interface.
"""

from __future__ import annotations

from .codeblocks import CodeBlockExtractor, CodeBlockStubRenderer
from .exceptions import (
    AmbiguousSectionRefError,
    CodeBlockNotFoundError,
    DocumentNotLoadedError,
    SectionNotFoundError,
)
from .indexer import MarkdownIndexer
from .links import LinkExtractor
from .models import (
    MarkdownDocument,
    NavigationKind,
    NavigationResult,
    NavigatorOptions,
    Page,
    SectionNode,
)
from .pagination import Paginator
from .parser import MarkdownItParser, MarkdownParser
from .providers import CallableMarkdownContentProvider, MarkdownContentProvider
from .renderers import (
    CodeBlockRenderer,
    DocumentMapRenderer,
    LinkInventoryRenderer,
    SectionBodyRenderer,
    SectionMapRenderer,
)
from .tokenizer import TokenBudgeter

__all__ = ["ProgressiveMarkdownNavigator"]


class ProgressiveMarkdownNavigator:
    """Token-budget-aware navigator over a parsed markdown document.

    Provides document map, section navigation, code block viewing, link
    inventory, and search — all returning NavigationResult instances with
    structured Page objects.

    All dependencies are injectable for testing. Factory classmethods
    cover the common construction patterns.

    Args:
        provider: Content provider for loading markdown text.
        options: Navigator configuration options.
        indexer: Markdown indexer (built from parser result).
        token_budgeter: Token counting and splitting.
        paginator: Page assembler.
        document_map_renderer: Full document TOC renderer.
        section_map_renderer: Single section breadcrumb/children renderer.
        section_body_renderer: Section body renderer with code stubs.
        link_renderer: Link inventory renderer.
        code_renderer: Code block renderer.

    Example::

        nav = ProgressiveMarkdownNavigator.from_markdown(markdown_text)
        result = nav.map()
        print(result.pages[0].content)
        print(result.model_dump_json())
    """

    def __init__(
        self,
        provider: MarkdownContentProvider,
        options: NavigatorOptions | None = None,
        indexer: MarkdownIndexer | None = None,
        token_budgeter: TokenBudgeter | None = None,
        paginator: Paginator | None = None,
        document_map_renderer: DocumentMapRenderer | None = None,
        section_map_renderer: SectionMapRenderer | None = None,
        section_body_renderer: SectionBodyRenderer | None = None,
        link_renderer: LinkInventoryRenderer | None = None,
        code_renderer: CodeBlockRenderer | None = None,
    ) -> None:
        """Initialise with injectable dependencies.

        Args:
            provider: Content provider used by load() and from_provider().
            options: Navigator options. Defaults to NavigatorOptions().
            indexer: Indexer instance. Built with default parser when None.
            token_budgeter: Token budgeter. Built from options when None.
            paginator: Paginator. Built from token_budgeter when None.
            document_map_renderer: Document map renderer. Default when None.
            section_map_renderer: Section map renderer. Default when None.
            section_body_renderer: Section body renderer. Default when None.
            link_renderer: Link inventory renderer. Default when None.
            code_renderer: Code block renderer. Default when None.
        """
        self._provider = provider
        self._options = options or NavigatorOptions()
        self._document: MarkdownDocument | None = None

        # Build parser and indexer.
        _parser: MarkdownParser = MarkdownItParser(preset=self._options.parser_preset)
        self._parser = _parser
        self._indexer = indexer or MarkdownIndexer()
        self._link_extractor = LinkExtractor()
        self._code_extractor = CodeBlockExtractor()

        # Build tokenizer and pagination.
        self._budgeter = token_budgeter or TokenBudgeter(
            model=self._options.tiktoken_model,
            encoding_name=self._options.tiktoken_encoding,
            default_budget=self._options.default_budget,
        )
        self._paginator = paginator or Paginator(self._budgeter)

        # Build renderers.
        stub_renderer = CodeBlockStubRenderer()
        self._doc_map_renderer = document_map_renderer or DocumentMapRenderer()
        self._section_map_renderer = section_map_renderer or SectionMapRenderer()
        self._section_body_renderer = section_body_renderer or SectionBodyRenderer(stub_renderer)
        self._link_renderer = link_renderer or LinkInventoryRenderer()
        self._code_renderer = code_renderer or CodeBlockRenderer()

    @classmethod
    def from_markdown(
        cls,
        markdown: str,
        source: str = "inline",
        options: NavigatorOptions | None = None,
    ) -> ProgressiveMarkdownNavigator:
        """Construct a navigator and immediately load the given markdown.

        Args:
            markdown: Raw markdown text to parse and navigate.
            source: Human-readable source label.
            options: Navigator configuration options.

        Returns:
            Navigator with the document pre-loaded.
        """
        provider = CallableMarkdownContentProvider(lambda _s, **_kw: markdown)
        nav = cls(provider=provider, options=options)
        nav.load(source)
        return nav

    @classmethod
    def from_provider(
        cls,
        provider: MarkdownContentProvider,
        source: str,
        options: NavigatorOptions | None = None,
        **provider_kwargs: object,
    ) -> ProgressiveMarkdownNavigator:
        """Construct a navigator and load markdown via the provider.

        Args:
            provider: Content provider to use for fetching markdown.
            source: Source identifier passed to provider.get_markdown().
            options: Navigator configuration options.
            **provider_kwargs: Additional kwargs forwarded to get_markdown().

        Returns:
            Navigator with the document pre-loaded.
        """
        nav = cls(provider=provider, options=options)
        nav.load(source, **provider_kwargs)
        return nav

    # ------------------------------------------------------------------
    # Document loading
    # ------------------------------------------------------------------

    def load(self, source: str, **provider_kwargs: object) -> MarkdownDocument:
        """Load and parse markdown from the provider.

        Args:
            source: Source identifier passed to provider.get_markdown().
            **provider_kwargs: Additional kwargs forwarded to get_markdown().

        Returns:
            The parsed MarkdownDocument.
        """
        markdown = self._provider.get_markdown(source, **provider_kwargs)
        result = self._parser.parse(source, markdown)
        document = self._indexer.build(result)
        self._link_extractor.extract(result, document)
        self._document = document
        return document

    def current_document(self) -> MarkdownDocument:
        """Return the currently loaded document.

        Returns:
            The loaded MarkdownDocument.

        Raises:
            DocumentNotLoadedError: When load() has not been called.
        """
        if self._document is None:
            msg = "No document loaded. Call load() or use from_markdown()/from_provider() first."
            raise DocumentNotLoadedError(msg)
        return self._document

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def map(self, page: int = 1, budget: int | None = None) -> NavigationResult:
        """Return a paginated document map (table of contents).

        Args:
            page: 1-based page number to retrieve.
            budget: Token ceiling per page. Uses default_budget when None.

        Returns:
            NavigationResult with kind=document_map.

        Raises:
            DocumentNotLoadedError: When load() has not been called.
        """
        document = self.current_document()
        effective = budget or self._options.default_budget
        blocks = self._doc_map_renderer.render_blocks(document)
        pages = self._paginator.paginate_blocks(blocks, effective)
        return _build_result(
            kind=NavigationKind.document_map,
            title=f"Document Map: {document.source}",
            pages=pages,
            requested_page=page,
        )

    def links(self, page: int = 1, budget: int | None = None) -> NavigationResult:
        """Return a paginated link inventory.

        Args:
            page: 1-based page number to retrieve.
            budget: Token ceiling per page. Uses default_budget when None.

        Returns:
            NavigationResult with kind=links.

        Raises:
            DocumentNotLoadedError: When load() has not been called.
        """
        document = self.current_document()
        effective = budget or self._options.default_budget
        blocks = self._link_renderer.render_blocks(document)
        pages = self._paginator.paginate_blocks(blocks, effective)
        return _build_result(
            kind=NavigationKind.links,
            title=f"Links: {document.source}",
            pages=pages,
            requested_page=page,
        )

    def view_section(
        self,
        ref: str,
        page: int = 1,
        budget: int | None = None,
    ) -> NavigationResult:
        """View a section by reference.

        When the section has children, returns a section_map showing the
        children TOC and the section's own intro prose (text before the
        first child) if non-empty.

        When the section has no children, returns section_body with the
        paginated body text (code blocks replaced with stubs).

        Args:
            ref: Section reference — resolved by ID, selector, slug,
                or case-insensitive title substring.
            page: 1-based page number to retrieve.
            budget: Token ceiling per page. Uses default_budget when None.

        Returns:
            NavigationResult with kind=section_map or kind=section_body.

        Raises:
            DocumentNotLoadedError: When load() has not been called.
            SectionNotFoundError: When ref cannot be resolved.
            AmbiguousSectionRefError: When ref matches multiple sections.
        """
        document = self.current_document()
        section = self.resolve_section(ref)
        effective = budget or self._options.default_budget

        if section.child_ids:
            return self._view_section_as_map(document, section, ref, page, effective)
        return self._view_section_as_body(document, section, ref, page, effective)

    def view_code(
        self,
        code_id: str,
        page: int = 1,
        budget: int | None = None,
    ) -> NavigationResult:
        """View a code block by ID.

        Args:
            code_id: Code block ID (e.g. ``"code_0001"``).
            page: 1-based page number to retrieve.
            budget: Token ceiling per page. Uses default_budget when None.

        Returns:
            NavigationResult with kind=code_block.

        Raises:
            DocumentNotLoadedError: When load() has not been called.
            CodeBlockNotFoundError: When code_id is not found.
        """
        document = self.current_document()
        block = document.code_blocks.get(code_id)
        if block is None:
            msg = f"Code block not found: {code_id!r}"
            raise CodeBlockNotFoundError(msg)

        effective = budget or self._options.default_budget
        rendered = self._code_renderer.render(block)
        pages = self._paginator.paginate_text(rendered, effective)
        return _build_result(
            kind=NavigationKind.code_block,
            title=f"Code: {code_id} ({block.language or 'text'})",
            pages=pages,
            requested_page=page,
            metadata={
                "id": block.id,
                "language": block.language,
                "summary": block.summary,
            },
        )

    def resolve_section(self, ref: str) -> SectionNode:
        """Resolve a section reference string to a SectionNode.

        Resolution order:
        1. Exact ID match (e.g. ``sec_0001``)
        2. Exact selector match (e.g. ``h2.1``)
        3. Exact slug match
        4. Case-insensitive title substring match (first in document order)

        Args:
            ref: Reference string to resolve.

        Returns:
            The matching SectionNode.

        Raises:
            DocumentNotLoadedError: When load() has not been called.
            SectionNotFoundError: When no section matches ref.
            AmbiguousSectionRefError: When ref matches multiple sections
                and disambiguation is not possible.
        """
        document = self.current_document()

        # 1. Exact ID.
        if ref in document.sections:
            return document.sections[ref]

        # 2. Exact selector.
        if ref in document.sections_by_selector:
            return document.sections[document.sections_by_selector[ref]]

        # 3. Exact slug.
        if ref in document.sections_by_slug:
            ids = document.sections_by_slug[ref]
            if len(ids) == 1:
                return document.sections[ids[0]]
            # Multiple sections share the slug — return first (document order).
            return document.sections[ids[0]]

        # 4. Case-insensitive title substring (first match in document order).
        ref_lower = ref.lower()
        for section in document.sections.values():
            if ref_lower in section.title.lower():
                return section

        msg = f"Section not found: {ref!r}"
        raise SectionNotFoundError(msg)

    def search_sections(
        self,
        query: str,
        page: int = 1,
        budget: int | None = None,
    ) -> NavigationResult:
        """Search sections by keyword match on title and slug.

        Scoring: each space-delimited query token that appears as a substring
        of the title or slug contributes one point. Zero-score sections are
        excluded. Results are sorted by descending score with stable tie-break
        on section ID.

        Args:
            query: Free-text search string.
            page: 1-based page number for paginated results.
            budget: Token ceiling per page. Uses default_budget when None.

        Returns:
            NavigationResult with kind=search_results.

        Raises:
            DocumentNotLoadedError: When load() has not been called.
        """
        document = self.current_document()
        effective = budget or self._options.default_budget

        tokens = [t.lower() for t in query.split() if t]
        if not tokens:
            empty_pages = self._paginator.paginate_text("No results.", effective)
            return _build_result(
                kind=NavigationKind.search_results,
                title=f'Search: "{query}"',
                pages=empty_pages,
                requested_page=page,
                metadata={"query": query, "count": 0},
            )

        scored: list[tuple[float, str, SectionNode]] = []
        for section in document.sections.values():
            score = 0.0
            title_lower = section.title.lower()
            for token in tokens:
                if token in title_lower:
                    score += 1.0
                if token in section.slug:
                    score += 1.0
            if score > 0:
                scored.append((score, section.id, section))

        scored.sort(key=lambda t: (-t[0], t[1]))
        matches = [s for _, _, s in scored]

        lines = [
            f"[{s.selector}] {s.title}  (slug={s.slug})\n"
            for s in matches
        ]
        text = "".join(lines) if lines else "No results."
        pages = self._paginator.paginate_text(text, effective)
        return _build_result(
            kind=NavigationKind.search_results,
            title=f'Search: "{query}"',
            pages=pages,
            requested_page=page,
            metadata={"query": query, "count": len(matches)},
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _view_section_as_map(
        self,
        document: MarkdownDocument,
        section: SectionNode,
        ref: str,
        page: int,
        budget: int,
    ) -> NavigationResult:
        """Build a section_map result for a parent section.

        Includes the children map and the section's own intro prose
        (text before the first child) when non-empty.

        Args:
            document: The loaded document.
            section: The parent section to map.
            ref: Original reference string (for metadata).
            page: Requested page number.
            budget: Token budget.

        Returns:
            NavigationResult with kind=section_map.
        """
        map_blocks = self._section_map_renderer.render_blocks(document, section)

        # Intro prose: body text before the first child section.
        intro_body = self._section_body_renderer.render(document, section)
        if intro_body.strip():
            combined = intro_body + "\n" + "".join(map_blocks)
        else:
            combined = "".join(map_blocks)

        pages = self._paginator.paginate_text(combined, budget)
        return _build_result(
            kind=NavigationKind.section_map,
            title=section.title,
            pages=pages,
            requested_page=page,
            metadata={
                "ref": ref,
                "id": section.id,
                "selector": section.selector,
                "child_count": len(section.child_ids),
            },
        )

    def _view_section_as_body(
        self,
        document: MarkdownDocument,
        section: SectionNode,
        ref: str,
        page: int,
        budget: int,
    ) -> NavigationResult:
        """Build a section_body result for a leaf section.

        Args:
            document: The loaded document.
            section: The leaf section to render.
            ref: Original reference string (for metadata).
            page: Requested page number.
            budget: Token budget.

        Returns:
            NavigationResult with kind=section_body.
        """
        body = self._section_body_renderer.render(document, section)
        pages = self._paginator.paginate_text(body, budget)
        return _build_result(
            kind=NavigationKind.section_body,
            title=section.title,
            pages=pages,
            requested_page=page,
            metadata={
                "ref": ref,
                "id": section.id,
                "selector": section.selector,
            },
        )


# ---------------------------------------------------------------------------
# Result builder helpers
# ---------------------------------------------------------------------------


def _build_result(
    kind: NavigationKind,
    title: str,
    pages: list[Page],
    requested_page: int,
    metadata: dict[str, object] | None = None,
) -> NavigationResult:
    """Construct a NavigationResult from pages and page selection.

    Args:
        kind: Navigation kind for the result.
        title: Human-readable title.
        pages: List of Page objects (at least one).
        requested_page: 1-based page number requested by the caller.
        metadata: Optional metadata dict.

    Returns:
        NavigationResult with current_page clamped to valid range.
    """
    if not pages:
        pages = [Page(content="", page_number=1, total_pages=1, token_count=0, budget=1)]
    total = len(pages)
    current = max(1, min(requested_page, total))
    return NavigationResult(
        kind=kind,
        title=title,
        pages=pages,
        current_page=current,
        total_pages=total,
        has_more=current < total,
        metadata=metadata or {},
    )
