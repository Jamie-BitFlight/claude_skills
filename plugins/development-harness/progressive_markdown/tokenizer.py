"""Token budget management using tiktoken.

Provides lossless text splitting respecting semantic boundaries (paragraphs,
lines, then character bisection) while staying within a token budget.
"""

from __future__ import annotations

import re

import tiktoken

__all__ = ["TokenBudgeter"]


class TokenBudgeter:
    """Count tokens and split text to fit within a token budget.

    Args:
        model: tiktoken model name for encoding selection.
        encoding_name: tiktoken encoding name (used when model is None).
        default_budget: Default token budget used when no budget is passed.

    Example::

        budgeter = TokenBudgeter(default_budget=11000)
        chunks = budgeter.split_to_budget("long text...", budget=500)
        assert "".join(chunks) == "long text..."
    """

    def __init__(
        self,
        model: str | None = None,
        encoding_name: str = "cl100k_base",
        default_budget: int = 11000,
    ) -> None:
        """Initialise with an optional model name or encoding name.

        Args:
            model: tiktoken model name (e.g. ``"gpt-4"``). When provided,
                overrides encoding_name for encoder selection.
            encoding_name: tiktoken encoding name (e.g. ``"cl100k_base"``).
                Used when model is None.
            default_budget: Default token budget per chunk.
        """
        if model:
            self._enc = tiktoken.encoding_for_model(model)
        else:
            self._enc = tiktoken.get_encoding(encoding_name)
        self._default_budget = default_budget

    def count(self, text: str) -> int:
        """Return the token count for text.

        Args:
            text: Text to count tokens for.

        Returns:
            Number of tokens in text.
        """
        return len(self._enc.encode(text))

    def fits(self, text: str, budget: int | None = None) -> bool:
        """Return True if text fits within the budget.

        Args:
            text: Text to check.
            budget: Token ceiling. Defaults to default_budget when None.

        Returns:
            True when token count <= budget.
        """
        effective = budget if budget is not None else self._default_budget
        return self.count(text) <= effective

    def split_to_budget(self, text: str, budget: int | None = None) -> list[str]:
        """Split text into chunks that each fit within the token budget.

        Splitting respects semantic boundaries in priority order:
        blank-line paragraph breaks > single newlines > character bisection.

        The result is lossless: ``"".join(split_to_budget(text)) == text``.

        Args:
            text: Text to split. May contain any Unicode content.
            budget: Token ceiling per chunk. Defaults to default_budget.

        Returns:
            List of one or more strings whose concatenation equals text.
            Returns ``[""]`` for empty text, ``[text]`` when it fits.
        """
        effective = budget if budget is not None else self._default_budget
        return _split_impl(text, effective, self._enc)

    def truncate_to_budget(self, text: str, budget: int | None = None) -> str:
        """Return the longest prefix of text that fits within the budget.

        Uses character bisection to find the largest character offset i
        such that ``count(text[:i]) <= budget``.

        Args:
            text: Text to truncate.
            budget: Token ceiling. Defaults to default_budget.

        Returns:
            Prefix of text fitting within budget. Returns full text when
            it already fits. Returns empty string when budget is 0.
        """
        effective = budget if budget is not None else self._default_budget
        if not text:
            return ""
        if self.count(text) <= effective:
            return text
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if len(self._enc.encode(text[:mid])) <= effective:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo]


# ---------------------------------------------------------------------------
# Internal splitting implementation (shared with list_navigator)
# ---------------------------------------------------------------------------


def _split_impl(text: str, budget: int, enc: tiktoken.Encoding) -> list[str]:
    """Core lossless token-budget text splitting.

    Args:
        text: Text to split.
        budget: Maximum token count per chunk.
        enc: tiktoken encoding instance.

    Returns:
        Ordered list of chunks whose concatenation equals text.
    """
    if not text:
        return [""]
    if len(enc.encode(text)) <= budget:
        return [text]

    # Level 1: split on blank-line paragraph boundaries (capture-preserving).
    # re.split with a capturing group keeps the delimiter in the output list.
    parts_para = re.split(r"(\n\n+)", text)
    if len(parts_para) > 1:
        chunks = _pack_parts(parts_para, budget, enc)
        if len(chunks) > 1:
            return chunks

    # Level 2: split on single newlines.
    parts_line = re.split(r"(\n)", text)
    if len(parts_line) > 1:
        chunks = _pack_parts(parts_line, budget, enc)
        if len(chunks) > 1:
            return chunks

    # Level 3: character bisection for content with no usable newlines.
    return _char_bisect_chunks(text, budget, enc)


def _pack_parts(parts: list[str], budget: int, enc: tiktoken.Encoding) -> list[str]:
    """Greedily pack string parts into chunks each fitting within budget.

    Args:
        parts: String fragments including captured delimiter strings.
        budget: Maximum token count per chunk.
        enc: tiktoken encoding instance.

    Returns:
        List of packed chunks. May return single-element list when all fit.
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
    """Split text via binary search for the largest safe character offset.

    Args:
        text: Non-empty text to split.
        budget: Maximum token count per chunk.
        enc: tiktoken encoding instance.

    Returns:
        Ordered list of chunks whose concatenation equals text.
    """
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(enc.encode(remaining)) <= budget:
            chunks.append(remaining)
            break
        lo, hi = 1, len(remaining)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if len(enc.encode(remaining[:mid])) <= budget:
                lo = mid
            else:
                hi = mid - 1
        chunks.append(remaining[:lo])
        remaining = remaining[lo:]
    return chunks or [""]
