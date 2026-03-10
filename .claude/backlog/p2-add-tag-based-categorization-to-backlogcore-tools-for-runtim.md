---
name: Add tag-based categorization to backlog_core tools for runtime filtering
description: "No tool in backlog_core/server.py uses `tags=`. FastMCP v3 tag-based filtering allows servers (or composed parent servers) to expose only subsets of tools based on client role or context.\n\nFor backlog_core this has a practical use: when mounted into a larger MCP server (e.g., a project orchestrator), the parent could use `include_tags={\"read-only\"}` to expose only list/view tools to read-only clients, or `exclude_tags={\"destructive\"}` to prevent accidental closes/resolves.\n\nProposed tag assignments:\n- `{\"read-only\"}` → backlog_list, backlog_view\n- `{\"write\", \"github\"}` → backlog_add, backlog_update, backlog_groom, backlog_sync, backlog_pull\n- `{\"destructive\", \"github\"}` → backlog_close, backlog_resolve\n- `{\"maintenance\"}` → backlog_normalize\n\nFiles affected: `.claude/skills/backlog/backlog_core/server.py`\n\nSource: FastMCP v3 docs `servers/server.mdx` — `tags=` on decorators; `include_tags`/`exclude_tags` on `FastMCP()` constructor; `mcp.disable(tags={...})` at runtime."
metadata:
  topic: add-tag-based-categorization-to-backlogcore-tools-for-runtim
  source: 'GitHub Issue #471'
  added: '2026-03-06'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#471'
  last_synced: '2026-03-10T06:56:08Z'
---

## Story

As a **developer using Claude Code skills**, I want to **add tag-based categorization to backlog_core tools for runtime filtering** so that **the tooling becomes more capable and complete**.

## Description

No tool in backlog_core/server.py uses `tags=`. FastMCP v3 tag-based filtering allows servers (or composed parent servers) to expose only subsets of tools based on client role or context.

For backlog_core this has a practical use: when mounted into a larger MCP server (e.g., a project orchestrator), the parent could use `include_tags={"read-only"}` to expose only list/view tools to read-only clients, or `exclude_tags={"destructive"}` to prevent accidental closes/resolves.

Proposed tag assignments:
- `{"read-only"}` → backlog_list, backlog_view
- `{"write", "github"}` → backlog_add, backlog_update, backlog_groom, backlog_sync, backlog_pull
- `{"destructive", "github"}` → backlog_close, backlog_resolve
- `{"maintenance"}` → backlog_normalize

Files affected: `.claude/skills/backlog/backlog_core/server.py`

Source: FastMCP v3 docs `servers/server.mdx` — `tags=` on decorators; `include_tags`/`exclude_tags` on `FastMCP()` constructor; `mcp.disable(tags={...})` at runtime.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: fastmcp-creator skill review of backlog_core/server.py
- **Priority**: P2
- **Added**: 2026-03-06
- **Research questions**: None
