"""Pagination of text and block lists into token-budget-bounded pages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import Page

if TYPE_CHECKING:
    from .tokenizer import TokenBudgeter

__all__ = ["Paginator"]


class Paginator:
    """Split text or block lists into Page objects respecting a token budget.

    Args:
        token_budgeter: TokenBudgeter instance for counting and splitting.

    Example::

        paginator = Paginator(TokenBudgeter(default_budget=11000))
        pages = paginator.paginate_text("long text here...", budget=500)
        assert len(pages) >= 1
    """

    def __init__(self, token_budgeter: TokenBudgeter) -> None:
        """Initialise with a TokenBudgeter.

        Args:
            token_budgeter: TokenBudgeter used for counting and splitting.
        """
        self._budgeter = token_budgeter

    def paginate_text(self, text: str, budget: int | None = None) -> list[Page]:
        """Split text into pages each fitting within the token budget.

        Splits on semantic boundaries (paragraphs > lines > characters).
        Each page has correct page_number, total_pages, token_count, budget.

        Args:
            text: Text to paginate.
            budget: Token ceiling per page. Uses budgeter default when None.

        Returns:
            Non-empty list of Page objects. Returns a single empty page
            for empty text.
        """
        effective = budget if budget is not None else self._budgeter._default_budget  # noqa: SLF001
        chunks = self._budgeter.split_to_budget(text, effective)
        return _chunks_to_pages(chunks, effective, self._budgeter)

    def paginate_blocks(self, blocks: list[str], budget: int | None = None) -> list[Page]:
        """Accumulate blocks into pages respecting the token budget.

        Each block is treated as an indivisible unit. When a single block
        exceeds the budget, it is placed alone on its own page.

        Args:
            blocks: List of text blocks to paginate.
            budget: Token ceiling per page. Uses budgeter default when None.

        Returns:
            Non-empty list of Page objects.
        """
        effective = budget if budget is not None else self._budgeter._default_budget  # noqa: SLF001

        if not blocks:
            return [_make_page("", 1, 1, effective, self._budgeter)]

        pages_content: list[str] = []
        current_parts: list[str] = []
        current_tokens = 0

        for block in blocks:
            block_tokens = self._budgeter.count(block)
            if current_parts and current_tokens + block_tokens > effective:
                pages_content.append("".join(current_parts))
                current_parts = [block]
                current_tokens = block_tokens
            else:
                current_parts.append(block)
                current_tokens += block_tokens

        if current_parts:
            pages_content.append("".join(current_parts))

        if not pages_content:
            pages_content = [""]

        total = len(pages_content)
        return [
            _make_page(content, page_num, total, effective, self._budgeter)
            for page_num, content in enumerate(pages_content, start=1)
        ]


def _chunks_to_pages(chunks: list[str], budget: int, budgeter: TokenBudgeter) -> list[Page]:
    """Convert a list of text chunks into Page objects.

    Args:
        chunks: Text chunks to convert.
        budget: Budget value to store in each page.
        budgeter: TokenBudgeter for counting tokens.

    Returns:
        List of Page objects, one per chunk.
    """
    if not chunks:
        return [_make_page("", 1, 1, budget, budgeter)]
    total = len(chunks)
    return [_make_page(chunk, page_num, total, budget, budgeter) for page_num, chunk in enumerate(chunks, start=1)]


def _make_page(content: str, page_number: int, total_pages: int, budget: int, budgeter: TokenBudgeter) -> Page:
    """Construct a Page with computed token count.

    Args:
        content: Page text content.
        page_number: 1-based page number.
        total_pages: Total number of pages.
        budget: Token budget for this page.
        budgeter: TokenBudgeter for counting tokens.

    Returns:
        Populated Page instance.
    """
    return Page(
        content=content,
        page_number=page_number,
        total_pages=total_pages,
        token_count=budgeter.count(content),
        budget=budget,
    )
