---
name: Expose backlog items and index as MCP resources in backlog_core
description: "backlog_core exposes only tools. MCP resources are the correct primitive for readable, addressable content. Backlog items are a natural fit: each is a file with a stable identifier (issue number or title slug).\n\nMCP clients that support resources can browse, subscribe, and read items without calling tools. This is a lower-friction access pattern for read-only consumers (e.g., a client that wants to render a backlog view).\n\nProposed resources:\n- `backlog://index` — JSON list of all open items (title, priority, issue, plan) — static resource\n- `backlog://item/{selector}` — full content of a single item; selector = issue number or title slug — resource template\n- `backlog://item/{selector}/body` — raw GitHub issue body — resource template\n\nFiles affected: `.claude/skills/backlog/backlog_core/server.py`\n\nSource: FastMCP v3 docs `servers/resources.mdx` — `@mcp.resource(\"uri://pattern\")` and `@mcp.resource(\"uri://{param}\")` for resource templates."
metadata:
  topic: expose-backlog-items-and-index-as-mcp-resources-in-backlogco
  source: 'GitHub Issue #466'
  added: '2026-03-06'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#466'
  last_synced: '2026-03-12T12:48:18Z'
---

## Story

As a **developer using Claude Code skills**, I want to **expose backlog items and index as mcp resources in backlog_core** so that **the tooling becomes more capable and complete**.

## Description

backlog_core exposes only tools. MCP resources are the correct primitive for readable, addressable content. Backlog items are a natural fit: each is a file with a stable identifier (issue number or title slug).

MCP clients that support resources can browse, subscribe, and read items without calling tools. This is a lower-friction access pattern for read-only consumers (e.g., a client that wants to render a backlog view).

Proposed resources:
- `backlog://index` — JSON list of all open items (title, priority, issue, plan) — static resource
- `backlog://item/{selector}` — full content of a single item; selector = issue number or title slug — resource template
- `backlog://item/{selector}/body` — raw GitHub issue body — resource template

Files affected: `.claude/skills/backlog/backlog_core/server.py`

Source: FastMCP v3 docs `servers/resources.mdx` — `@mcp.resource("uri://pattern")` and `@mcp.resource("uri://{param}")` for resource templates.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: fastmcp-creator skill review of backlog_core/server.py
- **Priority**: P2
- **Added**: 2026-03-06
- **Research questions**: None
