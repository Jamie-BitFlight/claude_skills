"""Unified operations layer for the development harness.

The single entry point for all plan, task, backlog, artifact, and dispatch
operations.

Both frontends (CLI and MCP server) import from this module. No business
logic lives in the frontend files. Each operation here delegates to the
backend protocol (dh_core.protocols) for data access.

This module is built incrementally. As operations are extracted from the
frontends, they are added here with:
1. The operation function (all business logic)
2. A parity test in tests/test_frontend_parity.py
3. An entry in the progress file (.hermes/plans/unified-backend-progress.md)

During the transition, operations that have not yet been extracted will
still be called directly from the frontends. The goal is to reach zero
such calls.
"""

from __future__ import annotations

__all__: list[str] = []
