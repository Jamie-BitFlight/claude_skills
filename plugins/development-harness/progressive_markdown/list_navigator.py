"""Progressive disclosure engine for MCP endpoints that return structured data.

Three operations from one class: index (TOC), page (bounded chunks), select
(single item), and search (scored matches).  ``page()`` and ``select()``
return :class:`~progressive_markdown.models.NavigationResult`; ``index()``
and ``search()`` return MCP-friendly dicts that can be returned directly
from a FastMCP tool.

Also exports ``paginate_results`` — a drop-in replacement for the private
``_paginate_results`` function that was previously embedded in
``sam_schema.server``.  Existing callers keep working unchanged.

Module-level constants
----------------------
TOKEN_BUDGET : int
    Token ceiling for the auto-fit binary search.  Equals
    ``int(MAX_MCP_OUTPUT_TOKENS) - 500`` when that env var is set, or 9 500
    when it is absent.  Computed once at import time from
    ``progressive_markdown.models._DEFAULT_BUDGET``.
ENCODING : tiktoken.Encoding
    The tiktoken cl100k_base encoding instance used for all token counting.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

import tiktoken

from .models import _DEFAULT_BUDGET, NavigationKind, NavigationResult, Page

__all__ = ["ENCODING", "TOKEN_BUDGET", "DisclosureConfig", "ProgressiveDisclosure", "chunk_text", "paginate_results"]

# ---------------------------------------------------------------------------
# Module-level constants (previously private to sam_schema.server)
# ---------------------------------------------------------------------------

TOKEN_BUDGET: int = _DEFAULT_BUDGET
ENCODING: tiktoken.Encoding = tiktoken.get_encoding("cl100k_base")


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclass
class DisclosureConfig:
    """Field mapping and budget configuration for a specific data shape.

    Args:
        id_field: Name of the field that uniquely identifies each item.
        title_field: Name of the field used as a human-readable label.
        status_field: Name of the field indicating item state.
        summary_fields: Ordered list of fields to include in index/search responses.
        token_budget: Maximum token count for auto-fit page sizing.
        encoding: tiktoken encoding name used for token counting.
    """

    id_field: str = "id"
    title_field: str = "title"
    status_field: str = "status"
    summary_fields: list[str] = field(default_factory=lambda: ["id", "title", "status"])
    token_budget: int = TOKEN_BUDGET
    encoding: str = "cl100k_base"


# ---------------------------------------------------------------------------
# NavigationResult builder
# ---------------------------------------------------------------------------


def _disclosure_to_result(
    kind: NavigationKind,
    title: str,
    pages: list[Page],
    requested_page: int,
    metadata: dict[str, object],
) -> NavigationResult:
    """Build a ``NavigationResult`` from disclosure parameters.

    Args:
        kind: Classification of the result content.
        title: Human-readable title for the result.
        pages: Ordered list of content pages (usually one for list operations).
        requested_page: 1-based index of the current page within *pages*.
        metadata: Arbitrary JSON-serializable metadata for the result.

    Returns:
        NavigationResult with all required fields populated.
    """
    total_pages = max(1, len(pages))
    current_page = max(1, min(requested_page, total_pages))
    return NavigationResult(
        kind=kind,
        title=title,
        pages=pages,
        current_page=current_page,
        total_pages=total_pages,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Progressive disclosure engine
# ---------------------------------------------------------------------------


class ProgressiveDisclosure:
    """Map, navigate, and extract from any list-of-dict structured data.

    Three operations, one class:

    - ``index()``          → TOC: summary fields only, all items, no full bodies (dict)
    - ``page(page_num)``   → page N of full items, auto-fit budget (NavigationResult)
    - ``select(selector)`` → single item by ID field value (NavigationResult)
    - ``search(query)``    → scored matches on title and summary fields (dict)

    ``page()`` and ``select()`` return ``NavigationResult`` (Pydantic model).
    ``index()`` and ``search()`` return MCP-friendly dicts.

    Args:
        items: Full list of dicts to disclose.
        config: Field mapping and budget configuration.  Defaults to
            ``DisclosureConfig()`` when not provided.
        tool_name: Name used in ``next_call`` hint strings.

    Example::

        pd = ProgressiveDisclosure(tasks, DisclosureConfig(id_field="id"))
        toc = pd.index()   # all items, summary fields only (dict)
        page1 = pd.page(1)  # first page, auto-fit budget (NavigationResult)
        item = pd.select("T03")  # NavigationResult (found or error)
        hits = pd.search("auth")  # scored matches (dict)
    """

    def __init__(
        self, items: list[dict[str, Any]], config: DisclosureConfig | None = None, tool_name: str = "tool"
    ) -> None:
        """Initialise with a list of items and optional configuration.

        Args:
            items: Full list of dicts to disclose.
            config: Field mapping and budget configuration.  Defaults to
                ``DisclosureConfig()`` when not provided.
            tool_name: Name used in ``next_call`` hint strings.
        """
        self._items = items
        self._config = config or DisclosureConfig()
        self._tool_name = tool_name
        self._enc: tiktoken.Encoding = tiktoken.get_encoding(self._config.encoding)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index(self) -> dict[str, Any]:
        """Return a summary-only view of all items (the table of contents).

        Each entry in the returned list contains only the fields declared in
        ``config.summary_fields``.  Fields absent from an item are omitted
        silently so that sparse datasets do not raise errors.

        Returns:
            Dict with ``index`` (list of summary dicts) and ``total`` (item count).
        """
        cfg = self._config
        summaries = [{k: item[k] for k in cfg.summary_fields if k in item} for item in self._items]
        return {"index": summaries, "total": len(summaries)}

    def page(self, page_num: int = 1) -> NavigationResult:
        """Return page *page_num* (1-based) of full items as a NavigationResult.

        Page size is determined automatically by the binary-search token-budget
        algorithm so the serialised items fit within ``config.token_budget``.

        Args:
            page_num: Page number (1-based).  Clamped to the valid range.

        Returns:
            NavigationResult wrapping the page items (kind=document_map, one
            content page).  Pagination metadata — ``page``, ``page_size``,
            ``total_pages``, ``total``, ``has_more``, and optionally
            ``next_call`` — is in ``NavigationResult.metadata``.
        """
        total = len(self._items)

        if total == 0:
            empty_content = "No items"
            token_count = len(self._enc.encode(empty_content))
            empty_page = Page(
                content=empty_content,
                page_number=1,
                total_pages=1,
                token_count=token_count,
                budget=self._config.token_budget,
            )
            return _disclosure_to_result(
                kind=NavigationKind.document_map,
                title="empty list",
                pages=[empty_page],
                requested_page=1,
                metadata={"total": 0},
            )

        effective_size = self._auto_page_size(self._items)
        total_pages = max(1, (total + effective_size - 1) // effective_size)
        clamped_n = max(1, min(page_num, total_pages))
        offset = (clamped_n - 1) * effective_size
        page_slice = self._items[offset : offset + effective_size]
        has_more = (offset + len(page_slice)) < total

        content = json.dumps(page_slice)
        token_count = len(self._enc.encode(content))
        result_page = Page(
            content=content,
            page_number=1,
            total_pages=1,
            token_count=token_count,
            budget=self._config.token_budget,
        )
        meta: dict[str, object] = {
            "page": clamped_n,
            "page_size": len(page_slice),
            "total_pages": total_pages,
            "total": total,
            "has_more": has_more,
        }
        if has_more:
            meta["next_call"] = f"{self._tool_name}(page={clamped_n + 1})"
        return _disclosure_to_result(
            kind=NavigationKind.document_map,
            title=f"page {clamped_n} of {total_pages}",
            pages=[result_page],
            requested_page=1,
            metadata=meta,
        )

    def select(self, selector: str) -> NavigationResult:
        """Return the single item whose id field matches *selector*.

        Args:
            selector: Value to match against ``config.id_field``.

        Returns:
            NavigationResult wrapping the matching item (kind=section_body,
            one page) when found.  When the selector does not match any item,
            returns a NavigationResult with kind=error — never returns None.
            Callers migrating from the previous dict return can use
            ``result.model_dump()`` or check ``result.kind``.
        """
        id_field = self._config.id_field
        for item in self._items:
            if item.get(id_field) == selector:
                content = json.dumps(item)
                token_count = len(self._enc.encode(content))
                result_page = Page(
                    content=content,
                    page_number=1,
                    total_pages=1,
                    token_count=token_count,
                    budget=self._config.token_budget,
                )
                return _disclosure_to_result(
                    kind=NavigationKind.section_body,
                    title=str(item.get(self._config.title_field, selector)),
                    pages=[result_page],
                    requested_page=1,
                    metadata={"id": selector},
                )
        not_found_msg = f"Item '{selector}' not found"
        token_count = len(self._enc.encode(not_found_msg))
        error_page = Page(
            content=not_found_msg,
            page_number=1,
            total_pages=1,
            token_count=token_count,
            budget=self._config.token_budget,
        )
        return _disclosure_to_result(
            kind=NavigationKind.error,
            title=f"not found: {selector}",
            pages=[error_page],
            requested_page=1,
            metadata={"id": selector},
        )

    def search(self, query: str, top_n: int = 10) -> dict[str, Any]:
        """Return scored matches on title and summary fields.

        Scoring is a simple token-overlap count: each space-delimited query
        token that appears (case-insensitively) as a substring of any summary
        field value contributes one point per field-value match.  Items with
        a score of zero are excluded.  Results are sorted by descending score
        with a stable secondary sort on the id field to ensure determinism.

        Args:
            query: Free-text search string.
            top_n: Maximum number of matches to return.

        Returns:
            Dict with ``matches`` (list of ``{score, item}`` dicts where
            *item* contains only summary fields), ``query``, and ``count``.
        """
        cfg = self._config
        tokens = [t.lower() for t in query.split() if t]
        if not tokens:
            return {"matches": [], "query": query, "count": 0}

        scored: list[tuple[float, str, dict[str, Any]]] = []
        for item in self._items:
            score = 0.0
            for sf in cfg.summary_fields:
                value = str(item.get(sf, "")).lower()
                score += sum(1.0 for t in tokens if t in value)
            if score > 0:
                summary = {k: item[k] for k in cfg.summary_fields if k in item}
                item_id = str(item.get(cfg.id_field, ""))
                scored.append((score, item_id, summary))

        scored.sort(key=lambda t: (-t[0], t[1]))
        matches = [{"score": s, "item": summary} for s, _, summary in scored[:top_n]]
        return {"matches": matches, "query": query, "count": len(matches)}

    def chunk_text(self, text: str, budget: int | None = None) -> list[str]:
        """Split *text* into ordered chunks each fitting within *budget* tokens.

        Splitting respects semantic boundaries in this priority order:
        blank-line paragraph breaks → single newlines → character bisection
        (when no newline boundary is available).

        Reassembling all chunks reproduces the original text exactly:
        ``"".join(chunk_text(text)) == text``

        Args:
            text: The text to split.  May contain any Unicode content.
            budget: Token ceiling per chunk.  Defaults to
                ``config.token_budget`` when ``None``.

        Returns:
            A list of one or more non-empty strings whose concatenation
            equals *text*.  Returns ``[""]`` for empty *text* and
            ``[text]`` when *text* already fits within *budget*.
        """
        effective_budget = budget if budget is not None else self._config.token_budget
        return _chunk_text_impl(text, effective_budget, self._enc)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _auto_page_size(self, items: list[dict[str, Any]], budget: int | None = None) -> int:
        """Find the largest k such that items[:k] fits within the token budget.

        Uses the same binary-search algorithm as the original
        ``_paginate_results`` in ``sam_schema.server``.  The lo=1 floor
        ensures at least one item is always returned even when a single item
        exceeds the budget.

        Args:
            items: Full item list to probe.
            budget: Token ceiling to use.  When ``None``, falls back to
                ``config.token_budget``.

        Returns:
            Largest integer k >= 1 such that
            ``len(enc.encode(json.dumps(items[:k]))) <= effective_budget``.
        """
        if not items:
            return 0
        effective_budget = budget if budget is not None else self._config.token_budget
        lo, hi = 1, len(items)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if len(self._enc.encode(json.dumps(items[:mid]))) <= effective_budget:
                lo = mid
            else:
                hi = mid - 1
        return lo


# ---------------------------------------------------------------------------
# Text chunking — intra-unit lossless splitter
# ---------------------------------------------------------------------------


def _chunk_text_impl(text: str, budget: int, enc: tiktoken.Encoding) -> list[str]:
    """Core implementation for lossless token-budget text chunking.

    Splits *text* into an ordered list of chunks where each chunk fits
    within *budget* tokens, using semantic boundary discovery at three
    priority levels: blank-line paragraph breaks, single newlines, then
    character-level bisection for content with no newlines.

    The character bisection uses ``largest i such that
    len(enc.encode(text[:i])) <= budget`` which operates on the source
    string, making it lossless by construction (slice + concatenation =
    original string).

    Args:
        text: Text to split.
        budget: Maximum token count per chunk.
        enc: tiktoken encoding instance used for token counting.

    Returns:
        Ordered list of chunks whose concatenation equals *text*.
        Returns ``[""]`` for empty *text* and ``[text]`` for text that
        already fits within *budget*.
    """
    if not text:
        return [""]
    if len(enc.encode(text)) <= budget:
        return [text]

    # --- Level 1: split on blank-line paragraph boundaries (capture-preserving) ---
    # re.split with a capturing group keeps the delimiter in the output list,
    # so "".join(parts) == text is guaranteed.
    parts_para = re.split(r"(\n\n+)", text)
    if len(parts_para) > 1:
        chunks = _pack_parts(parts_para, budget, enc)
        if len(chunks) > 1:
            return chunks

    # --- Level 2: split on single newlines ---
    parts_line = re.split(r"(\n)", text)
    if len(parts_line) > 1:
        chunks = _pack_parts(parts_line, budget, enc)
        if len(chunks) > 1:
            return chunks

    # --- Level 3: character bisection (no newlines, or single giant line) ---
    return _char_bisect_chunks(text, budget, enc)


def _pack_parts(parts: list[str], budget: int, enc: tiktoken.Encoding) -> list[str]:
    """Greedily pack *parts* into chunks each fitting within *budget* tokens.

    Adjacent parts (including captured delimiter strings) are accumulated
    into a running buffer.  When adding the next part would exceed the
    budget, the buffer is emitted as a chunk and a new buffer begins.

    Parts that individually exceed the budget are passed to
    ``_char_bisect_chunks`` and their sub-chunks are emitted atomically.

    Args:
        parts: List of string fragments (delimiters included as captured groups).
        budget: Maximum token count per chunk.
        enc: tiktoken encoding instance.

    Returns:
        List of chunks.  May return a single-element list when all parts
        fit in one chunk.
    """
    chunks: list[str] = []
    buffer = ""
    buffer_tokens = 0

    for part in parts:
        if not part:
            continue
        part_tokens = len(enc.encode(part))
        if part_tokens > budget:
            # Part itself exceeds budget — sub-split it.
            if buffer:
                chunks.append(buffer)
                buffer = ""
                buffer_tokens = 0
            chunks.extend(_char_bisect_chunks(part, budget, enc))
        elif buffer_tokens + part_tokens <= budget:
            buffer += part
            buffer_tokens += part_tokens
        else:
            if buffer:
                chunks.append(buffer)
            buffer = part
            buffer_tokens = part_tokens

    if buffer:
        chunks.append(buffer)

    return chunks or [""]


def _char_bisect_chunks(text: str, budget: int, enc: tiktoken.Encoding) -> list[str]:
    """Split *text* by binary-searching for the largest safe character offset.

    For each chunk: find the largest character index *i* such that
    ``len(enc.encode(text[:i])) <= budget``, emit ``text[:i]`` as a chunk,
    then recurse on ``text[i:]``.  Slicing the original string and
    concatenating is lossless by construction.

    Args:
        text: Text to split.  Must be non-empty.
        budget: Maximum token count per chunk.
        enc: tiktoken encoding instance.

    Returns:
        Ordered list of chunks.
    """
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(enc.encode(remaining)) <= budget:
            chunks.append(remaining)
            break
        # Binary search for largest character offset within budget.
        lo, hi = 1, len(remaining)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if len(enc.encode(remaining[:mid])) <= budget:
                lo = mid
            else:
                hi = mid - 1
        # lo=1 minimum ensures progress even for single oversized characters.
        chunks.append(remaining[:lo])
        remaining = remaining[lo:]
    return chunks or [""]


def chunk_text(text: str, budget: int | None = None) -> list[str]:
    """Module-level convenience wrapper for lossless token-budget text chunking.

    Splits *text* into an ordered list of chunks where each chunk fits
    within *budget* tokens.  Reassembling all chunks reproduces the
    original text exactly: ``"".join(chunk_text(text)) == text``.

    Splitting respects semantic boundaries in priority order:
    blank-line paragraph breaks → single newlines → character bisection.

    Args:
        text: The text to split.  May contain any Unicode content.
        budget: Token ceiling per chunk.  Defaults to ``TOKEN_BUDGET``
            when ``None``.

    Returns:
        A list of one or more strings whose concatenation equals *text*.
        Returns ``[""]`` for empty *text* and ``[text]`` for text already
        within *budget*.
    """
    effective_budget = budget if budget is not None else TOKEN_BUDGET
    return _chunk_text_impl(text, effective_budget, ENCODING)


# ---------------------------------------------------------------------------
# Drop-in shim: paginate_results (replaces _paginate_results in server.py)
# ---------------------------------------------------------------------------


def paginate_results(
    all_items: list[dict[str, Any]],
    *,
    offset: int,
    limit: int | None,
    messages: list[str],
    warnings: list[str],
    errors: list[str],
    tool_name: str,
) -> dict[str, Any]:
    """Paginate *all_items* within the token budget and return the response dict.

    This is a drop-in replacement for the private ``_paginate_results``
    function that was previously embedded in ``sam_schema.server``.  The
    signature and response shape are identical so existing callers require
    no changes beyond updating the import.

    Uses ``ProgressiveDisclosure._auto_page_size`` internally for the
    token-budget binary search, but returns the legacy **offset/limit**
    pagination shape (not the page-number shape produced by
    ``ProgressiveDisclosure.page()``).

    Args:
        all_items: Full list of items to paginate.
        offset: Number of items to skip from the start of the list.
        limit: Explicit page size.  ``None`` triggers auto-fit via the
            token-budget binary search.
        messages: Informational messages to echo in the response.
        warnings: Warning messages to echo in the response.
        errors: Error messages to echo in the response.
        tool_name: Name used in the ``next_call`` hint string.

    Returns:
        Dict with ``items``, ``count``, ``pagination``
        (``{offset, limit, total, has_more}``), ``messages``, ``warnings``,
        ``errors``, and optionally ``next_call``.
    """
    total = len(all_items)
    page_items = all_items[offset:]

    effective_limit: int
    if limit is not None:
        effective_limit = limit
    elif not page_items:
        effective_limit = 0
    else:
        # Delegate to the shared binary-search kernel.
        # ProgressiveDisclosure uses the module-level TOKEN_BUDGET and cl100k_base.
        pd = ProgressiveDisclosure(page_items, tool_name=tool_name)
        effective_limit = pd._auto_page_size(page_items)  # noqa: SLF001

    page = page_items[:effective_limit]
    has_more = (offset + len(page)) < total
    result: dict[str, Any] = {
        "items": page,
        "count": len(page),
        "pagination": {"offset": offset, "limit": effective_limit, "total": total, "has_more": has_more},
        "messages": messages,
        "warnings": warnings,
        "errors": errors,
    }
    if has_more:
        next_offset = offset + len(page)
        result["next_call"] = f"{tool_name}(offset={next_offset}, limit={effective_limit})"
    return result
