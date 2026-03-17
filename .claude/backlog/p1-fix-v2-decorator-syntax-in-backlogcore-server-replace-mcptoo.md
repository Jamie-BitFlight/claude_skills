---
name: 'Fix v2 decorator syntax in backlog_core server: replace @mcp.tool() with @mcp.tool'
description: "All 10 tools in backlog_core/server.py use `@mcp.tool()` with empty parentheses — the v2 pattern. FastMCP v3 canonical syntax is `@mcp.tool` without parentheses when no arguments are passed. While the old form may still work, it violates the v3 API contract and produces deprecation warnings in some toolchains.\n\nFiles affected: `.claude/skills/backlog/backlog_core/server.py`\n\nEvery tool declaration (backlog_add, backlog_list, backlog_view, backlog_sync, backlog_close, backlog_resolve, backlog_update, backlog_groom, backlog_normalize, backlog_pull) needs the empty parens removed.\n\nSource: fastmcp v3 docs `quickstart.mdx` — RULE: `@mcp.tool` without parentheses is the v3 canonical form. `@mcp.tool()` with empty parens is a v2 holdover."
metadata:
  topic: fix-v2-decorator-syntax-in-backlogcore-server-replace-mcptoo
  source: 'GitHub Issue #463'
  added: '2026-03-06'
  priority: completed
  type: Bug
  status: done
  issue: '#463'
  last_synced: '2026-03-14T16:00:33Z'
---

## Story

As a **developer relying on this plugin**, I want to **fix v2 decorator syntax in backlog_core server: replace @mcp.tool() with @mcp.tool** so that **the tool works correctly and reliably**.

## Description

All 10 tools in backlog_core/server.py use `@mcp.tool()` with empty parentheses — the v2 pattern. FastMCP v3 canonical syntax is `@mcp.tool` without parentheses when no arguments are passed. While the old form may still work, it violates the v3 API contract and produces deprecation warnings in some toolchains.

Files affected: `.claude/skills/backlog/backlog_core/server.py`

Every tool declaration (backlog_add, backlog_list, backlog_view, backlog_sync, backlog_close, backlog_resolve, backlog_update, backlog_groom, backlog_normalize, backlog_pull) needs the empty parens removed.

Source: fastmcp v3 docs `quickstart.mdx` — RULE: `@mcp.tool` without parentheses is the v3 canonical form. `@mcp.tool()` with empty parens is a v2 holdover.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: fastmcp-creator skill review of backlog_core/server.py
- **Priority**: P1
- **Added**: 2026-03-06
- **Research questions**: None