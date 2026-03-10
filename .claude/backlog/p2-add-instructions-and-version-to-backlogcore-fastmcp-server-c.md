---
name: Add instructions= and version= to backlog_core FastMCP server constructor
description: "The server is instantiated as `FastMCP(\"backlog\")` with no `instructions=` or `version=` parameters. MCP clients use the `instructions` field to understand what a server does before calling any tools. Without it, clients have no server-level guidance — they must infer purpose from tool docstrings alone.\n\nFiles affected: `.claude/skills/backlog/backlog_core/server.py`\n\nAdd `instructions=` describing the server's role (backlog management, GitHub Issues sync, per-item file management) and `version=` aligned with the package version.\n\nSource: FastMCP v3 docs `servers/server.mdx` — `instructions` describes the server's purpose to clients; `version` provides version string for tooling."
metadata:
  topic: add-instructions-and-version-to-backlogcore-fastmcp-server-c
  source: 'GitHub Issue #464'
  added: '2026-03-06'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#464'
  last_synced: '2026-03-10T06:56:12Z'
---

## Story

As a **developer using Claude Code skills**, I want to **add instructions= and version= to backlog_core fastmcp server constructor** so that **the tooling becomes more capable and complete**.

## Description

The server is instantiated as `FastMCP("backlog")` with no `instructions=` or `version=` parameters. MCP clients use the `instructions` field to understand what a server does before calling any tools. Without it, clients have no server-level guidance — they must infer purpose from tool docstrings alone.

Files affected: `.claude/skills/backlog/backlog_core/server.py`

Add `instructions=` describing the server's role (backlog management, GitHub Issues sync, per-item file management) and `version=` aligned with the package version.

Source: FastMCP v3 docs `servers/server.mdx` — `instructions` describes the server's purpose to clients; `version` provides version string for tooling.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: fastmcp-creator skill review of backlog_core/server.py
- **Priority**: P2
- **Added**: 2026-03-06
- **Research questions**: None
