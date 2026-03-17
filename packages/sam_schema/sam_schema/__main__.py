"""Entry point for running the SAM MCP server as a module.

Enables ``python -m sam_schema.server`` invocation.

Usage::

    python -m sam_schema.server
    uv run python -m sam_schema.server
"""

from __future__ import annotations

from sam_schema.server import mcp

if __name__ == "__main__":
    mcp.run()
