---
name: Expose backlog items as MCP resources via backlog://{slug} URI scheme
description: "Individual backlog items are currently only accessible by calling backlog_view (a tool). MCP resources provide a read path that is separate from tools — clients can browse/read without consuming a tool call slot or triggering side effects.\n\nExpose each per-item file as a backlog://{slug} resource using @mcp.resource(\"backlog://{slug}\"). This gives clients (including Claude Code) direct access to item bodies without going through the tool layer.\n\nFiles affected: .claude/skills/backlog/backlog_core/server.py\n\nChanges required:\n1. Add @mcp.resource(\"backlog://{slug}\") handler that reads the per-item file and returns its body as text\n2. Add @mcp.resource(\"backlog://\") list handler returning all item slugs\n\nThis is additive — no existing tools change.\n\nSource: fastmcp v3 docs servers/resources.mdx — @mcp.resource for URI-addressed content"
metadata:
  topic: expose-backlog-items-as-mcp-resources-via-backlog-slug-uri-s
  source: fastmcp-creator skill analysis of backlog_core/server.py
  added: '2026-03-07'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#513'
  last_synced: '2026-03-14T16:00:22Z'
---

## Story

As a **developer using Claude Code skills**, I want to **expose backlog items as mcp resources via backlog://{slug} uri scheme** so that **the tooling becomes more capable and complete**.

## Description

Individual backlog items are currently only accessible by calling backlog_view (a tool). MCP resources provide a read path that is separate from tools — clients can browse/read without consuming a tool call slot or triggering side effects.

Expose each per-item file as a backlog://{slug} resource using @mcp.resource("backlog://{slug}"). This gives clients (including Claude Code) direct access to item bodies without going through the tool layer.

Files affected: .claude/skills/backlog/backlog_core/server.py

Changes required:
1. Add @mcp.resource("backlog://{slug}") handler that reads the per-item file and returns its body as text
2. Add @mcp.resource("backlog://") list handler returning all item slugs

This is additive — no existing tools change.

Source: fastmcp v3 docs servers/resources.mdx — @mcp.resource for URI-addressed content

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: fastmcp-creator skill analysis of backlog_core/server.py
- **Priority**: P2
- **Added**: 2026-03-07
- **Research questions**: None
