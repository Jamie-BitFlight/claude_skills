"""Unified operations layer for the development harness.

Both the CLI (sam_schema/cli.py) and MCP servers (sam_schema/server.py,
backlog_core/server.py) import from this module. No business logic
lives in the frontends — they are thin adapters that parse arguments,
call operations from this module, and format output.

Architecture:
    Layer 1 (protocols):  dh_core.protocols  — backend interface (data CRUD)
    Layer 2 (operations): dh_core.operations — all business logic
    Layer 3 (frontends):  CLI + MCP server   — thin adapters

The operations layer is the single import surface for both frontends.
Frontends must not import backend implementations or legacy layers
(query.py, yaml_writer, LocalYamlTaskProvider, GistTaskLayer) directly.
"""
