"""Markdown-aware progressive disclosure facade.

``MarkdownNavigator`` wraps a parsed ``MarkdownIndex`` and exposes MCP-friendly
methods for navigating a Markdown document with token-budget awareness.

All public methods return plain ``dict`` objects suitable for returning
directly from a FastMCP tool function.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dh_progressive_disclosure import TOKEN_BUDGET, ProgressiveDisclosure, chunk_text

from .parser import extract_section_body, parse_markdown

if TYPE_CHECKING:
    from .models import CodeBlockRef, MarkdownIndex, SectionRef

__all__ = ["MarkdownNavigator"]

# ---------------------------------------------------------------------------
# Code stub format
# ---------------------------------------------------------------------------

_STUB_TEMPLATE = '[code: {id} | lang={lang} | lines={start}-{end} | {summary_brief} | view: view_code("{id}")]'


def _code_stub(block: CodeBlockRef) -> str:
    """Render a code block as an inline stub string.

    The stub replaces the block's content in section body text before token
    counting, keeping body pagination well within the token budget even when
    a section contains large code blocks.

    Args:
        block: The code block to stub out.

    Returns:
        A single-line stub string.
    """
    lang = block.language or "text"
    content_lines = block.content.splitlines()
    n_lines = len(content_lines)
    first_line = content_lines[0][:30].strip() if content_lines else ""
    summary_brief = f"{n_lines} lines, starts: {first_line}"
    return _STUB_TEMPLATE.format(
        id=block.id, lang=lang, start=block.start_line, end=block.end_line, summary_brief=summary_brief
    )


# ---------------------------------------------------------------------------
# Ref resolution
# ---------------------------------------------------------------------------


def _resolve_section_ref(ref: str, index: MarkdownIndex) -> SectionRef | None:
    """Resolve a section reference string to a ``SectionRef``.

    Resolution order:
    1. Exact ID match (e.g. ``sec_0001``)
    2. Exact selector match (e.g. ``h2.1``)
    3. Exact slug match
    4. Case-insensitive title substring match (first match in document order)

    Args:
        ref: Reference string to resolve.
        index: The ``MarkdownIndex`` to search.

    Returns:
        The matching ``SectionRef``, or ``None`` when no match is found.
    """
    # 1. ID
    if ref in index.sections:
        return index.sections[ref]

    # 2. Selector
    if ref in index.sections_by_selector:
        sec_id = index.sections_by_selector[ref]
        return index.sections[sec_id]

    # 3. Slug
    if ref in index.sections_by_slug:
        # Return first section with this slug (deterministic: document order).
        sec_ids = index.sections_by_slug[ref]
        return index.sections[sec_ids[0]]

    # 4. Title substring (case-insensitive, first in document order).
    ref_lower = ref.lower()
    for section in index.sections.values():
        if ref_lower in section.title.lower():
            return section

    return None


# ---------------------------------------------------------------------------
# Body stub replacement
# ---------------------------------------------------------------------------


def _replace_code_blocks_with_stubs(body: str, section: SectionRef, index: MarkdownIndex) -> str:
    """Replace fenced code block content in *body* with stub strings.

    Replacement is line-based: each code block's absolute line range
    (``start_line`` to ``end_line``) is converted to body-relative offsets
    by subtracting ``section.start_line + 1`` (the line after the heading).
    The slice is replaced with a single stub line.

    Line-based replacement is unconditional — it never silently leaves a
    code block in the body, and it never duplicates content when a match
    fails.  This approach relies on the line attribution stored in
    ``CodeBlockRef`` rather than fragile regex content matching.

    Args:
        body: Raw section body text (Markdown), starting at the line after
            the section heading.
        section: The section whose code blocks to stub out.
        index: The index containing ``CodeBlockRef`` objects.

    Returns:
        Modified body text with code blocks replaced by stubs.
    """
    if not section.code_block_ids:
        return body

    lines = body.splitlines(keepends=True)
    # Offset: body starts at section.start_line + 1 in absolute terms.
    body_offset = section.start_line + 1

    # Collect replacements in reverse order so line indices stay valid.
    replacements: list[tuple[int, int, str]] = []
    for code_id in section.code_block_ids:
        block = index.code_blocks.get(code_id)
        if block is None:
            continue
        # Convert absolute line indices to body-relative (0-based).
        rel_start = block.start_line - body_offset
        rel_end = block.end_line - body_offset
        if rel_start < 0 or rel_start >= len(lines):
            continue
        replacements.append((rel_start, rel_end, _code_stub(block)))

    # Apply from bottom to top so earlier indices remain valid.
    for rel_start, rel_end, stub in sorted(replacements, key=lambda t: -t[0]):
        # Clamp to actual body length.
        safe_end = min(rel_end + 1, len(lines))
        lines[rel_start:safe_end] = [stub + "\n"]

    return "".join(lines)


# ---------------------------------------------------------------------------
# MarkdownNavigator
# ---------------------------------------------------------------------------


class MarkdownNavigator:
    """Token-budget-aware navigator over a parsed Markdown document.

    Provides TOC mapping, section viewing, code block viewing, and search —
    all returning MCP-friendly dicts with pagination metadata.

    Args:
        markdown: The raw Markdown string to navigate.
        source: Human-readable source label (e.g. a filename or ``"inline"``).
        token_budget: Maximum token count per response page.
    """

    def __init__(self, markdown: str, source: str = "inline", token_budget: int = TOKEN_BUDGET) -> None:
        """Initialise the navigator and parse the Markdown source.

        Args:
            markdown: The raw Markdown string to navigate.
            source: Human-readable source label (e.g. a filename or ``"inline"``).
            token_budget: Maximum token count per response page.
        """
        self._markdown = markdown
        self._source = source
        self._token_budget = token_budget
        self._index: MarkdownIndex = parse_markdown(markdown, source)

    @classmethod
    def from_markdown(
        cls, markdown: str, source: str = "inline", token_budget: int = TOKEN_BUDGET
    ) -> MarkdownNavigator:
        """Construct a ``MarkdownNavigator`` from a raw Markdown string.

        Args:
            markdown: Raw Markdown source to parse and navigate.
            source: Human-readable source label.
            token_budget: Maximum token count per response page.

        Returns:
            A new ``MarkdownNavigator`` instance.
        """
        return cls(markdown, source, token_budget)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def current_index(self) -> MarkdownIndex:
        """Return the parsed ``MarkdownIndex`` for this document.

        Returns:
            The ``MarkdownIndex`` instance (immutable after construction).
        """
        return self._index

    def map(self, page: int = 1, budget: int | None = None) -> dict:
        """Return a paginated table-of-contents for the document.

        Each TOC entry contains the section's ``selector``, ``id``, ``slug``,
        ``title``, ``level``, the line range (``lines``), ``child_count``,
        and ``code_count``.

        Args:
            page: 1-based page number.
            budget: Token ceiling per page.  Defaults to
                ``token_budget`` when ``None``.

        Returns:
            MCP-friendly dict with ``kind="toc"``, ``source``, ``page``,
            ``total_pages``, ``has_more``, ``entries``, and ``count``.
        """
        effective_budget = budget if budget is not None else self._token_budget
        entries = [
            {
                "selector": s.selector,
                "id": s.id,
                "slug": s.slug,
                "title": s.title,
                "level": s.level,
                "lines": f"{s.start_line}-{s.end_line}",
                "child_count": len(s.child_ids),
                "code_count": len(s.code_block_ids),
            }
            for s in self._index.sections.values()
        ]

        pd = ProgressiveDisclosure(entries, tool_name="map")
        # Temporarily adjust the budget via the disclosure config.
        pd._config.token_budget = effective_budget  # noqa: SLF001

        page_result = pd.page(page)
        pagination = page_result.get("pagination", {})

        return {
            "kind": "toc",
            "source": self._source,
            "page": pagination.get("page", 1),
            "total_pages": pagination.get("total_pages", 1),
            "has_more": pagination.get("has_more", False),
            "entries": page_result.get("items", []),
            "count": page_result.get("count", 0),
        }

    def view_section(self, ref: str, page: int = 1, budget: int | None = None) -> dict:
        """Return the content of the section identified by *ref*.

        When the section has child sections, returns a ``section_map`` (TOC
        of immediate children) instead of the body text.  When the section
        has no children, returns the ``section_body``, paginated with
        ``chunk_text``.  Code blocks within the body are replaced with stubs
        before token counting.

        Args:
            ref: Section reference — resolved by ID, selector, slug, or
                case-insensitive title substring.
            page: 1-based page number for body pagination.
            budget: Token ceiling per page.  Defaults to ``token_budget``.

        Returns:
            MCP-friendly dict.  Common keys: ``kind``, ``title``, ``ref``,
            ``id``, ``selector``.  For ``section_map``: ``children`` (list
            of child TOC entries).  For ``section_body``: ``content``,
            ``page``, ``total_pages``, ``has_more``.  Returns
            ``{"error": "..."}`` when the ref cannot be resolved.
        """
        effective_budget = budget if budget is not None else self._token_budget
        section = _resolve_section_ref(ref, self._index)
        if section is None:
            return {"error": f"Section not found: {ref!r}"}

        base = {"title": section.title, "ref": ref, "id": section.id, "selector": section.selector}

        if section.child_ids:
            children = [
                {
                    "selector": self._index.sections[cid].selector,
                    "id": cid,
                    "slug": self._index.sections[cid].slug,
                    "title": self._index.sections[cid].title,
                    "level": self._index.sections[cid].level,
                    "child_count": len(self._index.sections[cid].child_ids),
                    "code_count": len(self._index.sections[cid].code_block_ids),
                }
                for cid in section.child_ids
            ]
            return {**base, "kind": "section_map", "children": children}

        # Leaf section — return body with pagination.
        body = extract_section_body(self._markdown, section, self._index)
        stubbed = _replace_code_blocks_with_stubs(body, section, self._index)

        chunks = chunk_text(stubbed, budget=effective_budget)
        clamped_page = max(1, min(page, len(chunks)))
        total_pages = len(chunks)
        has_more = clamped_page < total_pages
        content = chunks[clamped_page - 1]

        result = {
            **base,
            "kind": "section_body",
            "content": content,
            "page": clamped_page,
            "total_pages": total_pages,
            "has_more": has_more,
        }
        if has_more:
            result["next_call"] = f'view_section("{section.selector}", page={clamped_page + 1})'
        return result

    def view_code(self, code_id: str, page: int = 1, budget: int | None = None) -> dict:
        """Return the content of a fenced code block, paginated if necessary.

        Args:
            code_id: Code block ID (e.g. ``"code_0001"``).
            page: 1-based page number.
            budget: Token ceiling per page.  Defaults to ``token_budget``.

        Returns:
            MCP-friendly dict with ``kind="code_block"``, ``id``, ``language``,
            ``summary``, ``content``, ``page``, ``total_pages``, ``has_more``.
            Returns ``{"error": "..."}`` when *code_id* is not found.
        """
        effective_budget = budget if budget is not None else self._token_budget
        block = self._index.code_blocks.get(code_id)
        if block is None:
            return {"error": f"Code block not found: {code_id!r}"}

        chunks = chunk_text(block.content, budget=effective_budget)
        clamped_page = max(1, min(page, len(chunks)))
        total_pages = len(chunks)
        has_more = clamped_page < total_pages
        content = chunks[clamped_page - 1]

        result: dict = {
            "kind": "code_block",
            "id": block.id,
            "language": block.language,
            "summary": block.summary,
            "content": content,
            "page": clamped_page,
            "total_pages": total_pages,
            "has_more": has_more,
        }
        if has_more:
            result["next_call"] = f'view_code("{block.id}", page={clamped_page + 1})'
        return result

    def search(self, query: str, top_n: int = 10) -> dict:
        """Return scored section matches for *query*.

        Scores sections by substring match on title and slug.  Each query
        token (space-delimited) that appears in the title or slug contributes
        one point per field.  Zero-score sections are excluded.  Results are
        sorted by descending score with a stable tie-break on section ID.

        Args:
            query: Free-text search string.
            top_n: Maximum number of matches to return.

        Returns:
            Dict with ``matches`` (list of ``{score, selector, id, title,
            slug}`` dicts), ``query``, and ``count``.
        """
        tokens = [t.lower() for t in query.split() if t]
        if not tokens:
            return {"matches": [], "query": query, "count": 0}

        scored: list[tuple[float, str, dict]] = []
        for section in self._index.sections.values():
            score = 0.0
            title_lower = section.title.lower()
            slug_lower = section.slug
            for token in tokens:
                if token in title_lower:
                    score += 1.0
                if token in slug_lower:
                    score += 1.0
            if score > 0:
                scored.append((
                    score,
                    section.id,
                    {
                        "score": score,
                        "selector": section.selector,
                        "id": section.id,
                        "title": section.title,
                        "slug": section.slug,
                    },
                ))

        scored.sort(key=lambda t: (-t[0], t[1]))
        matches = [entry for _, _, entry in scored[:top_n]]
        return {"matches": matches, "query": query, "count": len(matches)}
