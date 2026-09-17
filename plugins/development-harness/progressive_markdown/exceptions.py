"""Typed exceptions for the progressive_markdown package."""

from __future__ import annotations

__all__ = [
    "AmbiguousSectionRefError",
    "CodeBlockNotFoundError",
    "DocumentNotLoadedError",
    "OrdinalNotFoundError",
    "PaginationError",
    "ParserError",
    "ProgressiveMarkdownError",
    "ProviderError",
    "SectionNotFoundError",
]


class ProgressiveMarkdownError(Exception):
    """Base class for all progressive_markdown errors."""


class DocumentNotLoadedError(ProgressiveMarkdownError):
    """Raised when a navigation method is called before load()."""


class OrdinalNotFoundError(ProgressiveMarkdownError):
    """Raised when an ordinal does not match a node in the document map."""

    def __init__(self, requested: str, valid_ordinals: list[str]) -> None:
        """Initialize with the missing ordinal and complete valid-ordinal list."""
        super().__init__(f"Ordinal {requested!r} not found. Valid ordinals: {valid_ordinals}")
        self.requested = requested
        self.valid_ordinals = valid_ordinals


class SectionNotFoundError(ProgressiveMarkdownError):
    """Raised when a section reference cannot be resolved."""


class AmbiguousSectionRefError(ProgressiveMarkdownError):
    """Raised when a section reference matches multiple sections."""


class CodeBlockNotFoundError(ProgressiveMarkdownError):
    """Raised when a code block ID cannot be found in the document."""


class ProviderError(ProgressiveMarkdownError):
    """Raised when a MarkdownContentProvider fails or returns invalid data."""


class ParserError(ProgressiveMarkdownError):
    """Raised when markdown parsing fails."""


class PaginationError(ProgressiveMarkdownError):
    """Raised when pagination encounters an unrecoverable error."""
