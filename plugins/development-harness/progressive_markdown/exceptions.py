"""Typed exceptions for the progressive_markdown package."""

from __future__ import annotations

__all__ = [
    "AmbiguousSectionRefError",
    "CodeBlockNotFoundError",
    "DocumentNotLoadedError",
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
