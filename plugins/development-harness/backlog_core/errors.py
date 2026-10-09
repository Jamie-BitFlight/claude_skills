"""Dependency-neutral public errors for backlog operations."""

from __future__ import annotations


class BacklogError(Exception):
    """General backlog operation error with an optional retryability verdict."""

    def __init__(self, *args: object, retryable: bool | None = None) -> None:
        """Initialize with exception arguments and an optional retryability verdict."""
        super().__init__(*args)
        self.retryable = retryable


class SearchTimeoutError(BacklogError):
    """Raised when one search request exhausts its matching-time budget."""

    def __init__(self) -> None:
        """Initialize the stable non-retryable matching-timeout error."""
        super().__init__("Search regex evaluation exceeded 100 ms", retryable=False)


class SearchExecutionError(BacklogError):
    """Raised when regex worker execution cannot establish a match result."""

    def __init__(self) -> None:
        """Initialize the stable unknown-retryability execution error."""
        super().__init__("Search regex execution failed")
