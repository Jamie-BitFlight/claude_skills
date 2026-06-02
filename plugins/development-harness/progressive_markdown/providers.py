"""MarkdownContentProvider protocol and standard implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from .exceptions import ProviderError

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["CallableMarkdownContentProvider", "MCPMarkdownContentProvider", "MarkdownContentProvider"]


class MarkdownContentProvider(Protocol):
    """Protocol for objects that supply markdown content given a source string."""

    def get_markdown(self, source: str, **kwargs: object) -> str:
        """Return the markdown content for the given source.

        Args:
            source: Source identifier (e.g. filename, URL, or ID).
            **kwargs: Additional provider-specific parameters.

        Returns:
            Markdown text as a string.
        """
        ...  # pragma: no cover


class CallableMarkdownContentProvider:
    """Wrap any callable that returns a string as a MarkdownContentProvider.

    Args:
        fn: Callable that accepts a source string and optional kwargs,
            returning markdown text.

    Example::

        def my_loader(source: str) -> str:
            return Path(source).read_text()


        provider = CallableMarkdownContentProvider(my_loader)
        markdown = provider.get_markdown("README.md")
    """

    def __init__(self, fn: Callable[..., str]) -> None:
        """Initialise with a callable that returns markdown text.

        Args:
            fn: Callable with signature ``(source: str, **kwargs) -> str``.
        """
        self._fn = fn

    def get_markdown(self, source: str, **kwargs: object) -> str:
        """Return markdown content by delegating to the wrapped callable.

        Args:
            source: Source identifier passed to the callable.
            **kwargs: Additional parameters forwarded to the callable.

        Returns:
            Markdown text as a string.

        Raises:
            ProviderError: When the callable returns a non-string value.
        """
        result = self._fn(source, **kwargs)
        if not isinstance(result, str):
            msg = f"Provider returned {type(result).__name__}, expected str"
            raise ProviderError(msg)
        return result


class MCPMarkdownContentProvider:
    """Thin adapter wrapping an injected MCP callable.

    Does not import any MCP SDK. The MCP callable is injected at
    construction time, making this class testable without MCP infrastructure.

    Args:
        mcp_callable: Callable that accepts a source string and optional kwargs,
            returning markdown text. Typically an MCP tool call wrapper.

    Example::

        def mcp_fetch(source: str, **kwargs: object) -> str:
            return mcp_client.call_tool("read_markdown", {"source": source})


        provider = MCPMarkdownContentProvider(mcp_fetch)
        markdown = provider.get_markdown("docs/README.md")
    """

    def __init__(self, mcp_callable: Callable[..., str]) -> None:
        """Initialise with an MCP callable.

        Args:
            mcp_callable: Callable with signature ``(source: str, **kwargs) -> str``.
        """
        self._callable = mcp_callable

    def get_markdown(self, source: str, **kwargs: object) -> str:
        """Return markdown content by invoking the MCP callable.

        Args:
            source: Source identifier passed to the callable.
            **kwargs: Additional parameters forwarded to the callable.

        Returns:
            Markdown text as a string.

        Raises:
            ProviderError: When the callable returns a non-string value.
        """
        result = self._callable(source, **kwargs)
        if not isinstance(result, str):
            msg = f"MCP callable returned {type(result).__name__}, expected str"
            raise ProviderError(msg)
        return result
