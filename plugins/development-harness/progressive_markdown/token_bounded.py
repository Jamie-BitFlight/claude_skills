"""Token-bounded Markdown extraction for progressive disclosure."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from progressive_markdown.list_navigator import ENCODING

__all__ = ["BoundedContent", "TokenBoundedExtractor"]


class BoundedContent(BaseModel):
    """Internal result from token-bounded extraction."""

    model_config = ConfigDict(frozen=True)

    content: str
    total_tokens: int
    returned_tokens: int
    truncated: bool


class TokenBoundedExtractor:
    """Apply cl100k_base token-bounded windowing to Markdown content."""

    def extract(self, content: str, head_tokens: int, skip_tokens: int = 0) -> BoundedContent:
        """Return the token window starting at ``skip_tokens``.

        Args:
            content: Complete source text.
            head_tokens: Maximum tokens to return.
            skip_tokens: Token offset for continuation.

        Returns:
            The bounded content and complete-content token metadata.
        """
        all_tokens: list[int] = ENCODING.encode(content)
        total_tokens = len(all_tokens)
        window_tokens = all_tokens[skip_tokens : skip_tokens + head_tokens]
        returned_tokens = len(window_tokens)
        return BoundedContent(
            content=ENCODING.decode(window_tokens),
            total_tokens=total_tokens,
            returned_tokens=returned_tokens,
            truncated=skip_tokens + returned_tokens < total_tokens,
        )
