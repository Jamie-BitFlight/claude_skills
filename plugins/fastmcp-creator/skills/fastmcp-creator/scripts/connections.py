"""Lightweight connection handling for MCP servers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager, AsyncExitStack
from typing import TYPE_CHECKING, Any, Self

from anthropic.types import ToolParam
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

if TYPE_CHECKING:
    from types import TracebackType

# Constants for context result tuple lengths
_RESULT_LEN_TWO = 2
_RESULT_LEN_THREE = 3


class MCPConnection(ABC):
    """Base class for MCP server connections.

    Provides async context manager interface for connecting to MCP servers.
    Subclasses must implement _create_context() to specify the transport.
    """

    def __init__(self) -> None:
        """Initialize connection with no active session."""
        self.session: ClientSession | None = None
        self._stack: AsyncExitStack | None = None

    @abstractmethod
    def _create_context(self) -> AbstractAsyncContextManager[Any]:
        """Create the connection context based on connection type.

        Returns:
            Async context manager for the specific transport type.
        """

    async def __aenter__(self) -> Self:
        """Initialize MCP server connection.

        Returns:
            Self with active session.

        Raises:
            ValueError: If context result has unexpected format.
        """
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()

        try:
            ctx = self._create_context()
            result = await self._stack.enter_async_context(ctx)

            if len(result) == _RESULT_LEN_TWO:
                read, write = result
            elif len(result) == _RESULT_LEN_THREE:
                read, write, _ = result
            else:
                _raise_unexpected_context_result(result)

            session_ctx = ClientSession(read, write)
            session = await self._stack.enter_async_context(session_ctx)
            self.session = session
            await session.initialize()
        except BaseException:
            await self._stack.__aexit__(None, None, None)
            raise

        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        """Clean up MCP server connection resources."""
        if self._stack:
            await self._stack.__aexit__(exc_type, exc_val, exc_tb)
        self.session = None
        self._stack = None

    async def list_tools(self) -> list[ToolParam]:
        """Retrieve available tools from the MCP server.

        Returns:
            List of tool definitions with name, description, and input schema.

        Raises:
            RuntimeError: If called without an active session.
        """
        if self.session is None:
            raise RuntimeError("No active session. Use async with context.")
        response = await self.session.list_tools()
        return [
            ToolParam(name=tool.name, description=tool.description or "", input_schema=tool.inputSchema)
            for tool in response.tools
        ]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> list[Any]:
        """Call a tool on the MCP server with provided arguments.

        Args:
            tool_name: Name of the tool to call.
            arguments: Arguments to pass to the tool.

        Returns:
            Tool execution result content.

        Raises:
            RuntimeError: If called without an active session.
        """
        if self.session is None:
            raise RuntimeError("No active session. Use async with context.")
        result = await self.session.call_tool(tool_name, arguments=arguments)
        return list(result.content)


def _raise_unexpected_context_result(result: object) -> None:
    """Raise error for unexpected context result format.

    Args:
        result: The unexpected context result value.

    Raises:
        ValueError: Always raises with details about the unexpected result.
    """
    raise ValueError(f"Unexpected context result: {result}")


class MCPConnectionStdio(MCPConnection):
    """MCP connection using standard input/output."""

    def __init__(self, command: str, args: list[str] | None = None, env: dict[str, str] | None = None) -> None:
        """Initialize stdio connection.

        Args:
            command: Command to run the MCP server.
            args: Command-line arguments.
            env: Environment variables for the subprocess.
        """
        super().__init__()
        self.command = command
        self.args = args or []
        self.env = env

    def _create_context(self) -> AbstractAsyncContextManager[Any]:
        """Create stdio client context.

        Returns:
            Async context manager for stdio transport.
        """
        return stdio_client(StdioServerParameters(command=self.command, args=self.args, env=self.env))


class MCPConnectionSSE(MCPConnection):
    """MCP connection using Server-Sent Events."""

    def __init__(self, url: str, headers: dict[str, str] | None = None) -> None:
        """Initialize SSE connection.

        Args:
            url: SSE endpoint URL.
            headers: HTTP headers for the connection.
        """
        super().__init__()
        self.url = url
        self.headers = headers or {}

    def _create_context(self) -> AbstractAsyncContextManager[Any]:
        """Create SSE client context.

        Returns:
            Async context manager for SSE transport.
        """
        return sse_client(url=self.url, headers=self.headers)


class MCPConnectionHTTP(MCPConnection):
    """MCP connection using Streamable HTTP."""

    def __init__(self, url: str, headers: dict[str, str] | None = None) -> None:
        """Initialize HTTP connection.

        Args:
            url: HTTP endpoint URL.
            headers: HTTP headers for the connection.
        """
        super().__init__()
        self.url = url
        self.headers = headers or {}

    def _create_context(self) -> AbstractAsyncContextManager[Any]:
        """Create streamable HTTP client context.

        Returns:
            Async context manager for HTTP transport.
        """
        return streamablehttp_client(url=self.url, headers=self.headers)


def create_connection(
    transport: str,
    *,
    command: str | None = None,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    url: str | None = None,
    headers: dict[str, str] | None = None,
) -> MCPConnection:
    """Factory function to create the appropriate MCP connection.

    Args:
        transport: Connection type ("stdio", "sse", or "http")
        command: Command to run (stdio only)
        args: Command arguments (stdio only)
        env: Environment variables (stdio only)
        url: Server URL (sse and http only)
        headers: HTTP headers (sse and http only)

    Returns:
        MCPConnection instance configured for the specified transport.

    Raises:
        ValueError: If required parameters are missing or transport is unsupported.
    """
    transport = transport.lower()

    if transport == "stdio":
        if not command:
            raise ValueError("Command is required for stdio transport")
        return MCPConnectionStdio(command=command, args=args, env=env)

    if transport == "sse":
        if not url:
            raise ValueError("URL is required for sse transport")
        return MCPConnectionSSE(url=url, headers=headers)

    if transport in {"http", "streamable_http", "streamable-http"}:
        if not url:
            raise ValueError("URL is required for http transport")
        return MCPConnectionHTTP(url=url, headers=headers)

    raise ValueError(f"Unsupported transport type: {transport}. Use 'stdio', 'sse', or 'http'")
