---
name: Add background task support to backlog_sync and backlog_pull via task=True
description: "`backlog_sync` and `backlog_pull` iterate over every open backlog item and make at least one GitHub API call per item. For a backlog with 50+ items, these operations can take 10–30 seconds and block the MCP connection.\n\nFastMCP v3 supports background task execution via `@mcp.tool(task=True)`. With this pattern, clients can initiate the operation and receive a task ID, then poll for completion. This prevents connection timeouts and allows other tools to remain available during the operation.\n\nFiles affected: `.claude/skills/backlog/backlog_core/server.py`\n\nPrerequisites:\n- Tools must be converted to `async def` (see related item: Convert sync tools to async)\n- `fastmcp[tasks]` extra must be added to pyproject.toml dependencies\n- Progress reporting via `Progress` dependency (pairs with Context logging item)\n\nWork required:\n- Add `fastmcp[tasks]` to pyproject.toml\n- Convert backlog_sync and backlog_pull to `async def` with `task=True`\n- Inject `Progress` dependency and call `progress.set_total(n)`, `progress.increment()` per item\n\nSource: FastMCP v3 docs `servers/tasks.mdx` — `@mcp.tool(task=True)` enables background execution; requires async functions and `fastmcp[tasks]` extra."
metadata:
  topic: add-background-task-support-to-backlogsync-and-backlogpull-v
  source: 'GitHub Issue #469'
  added: '2026-03-06'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#469'
  last_synced: '2026-03-21T03:46:07Z'
---

## Story

As a **developer using Claude Code skills**, I want to **add background task support to backlog_sync and backlog_pull via task=true** so that **the tooling becomes more capable and complete**.

## Description

`backlog_sync` and `backlog_pull` iterate over every open backlog item and make at least one GitHub API call per item. For a backlog with 50+ items, these operations can take 10–30 seconds and block the MCP connection.

FastMCP v3 supports background task execution via `@mcp.tool(task=True)`. With this pattern, clients can initiate the operation and receive a task ID, then poll for completion. This prevents connection timeouts and allows other tools to remain available during the operation.

Files affected: `.claude/skills/backlog/backlog_core/server.py`

Prerequisites:
- Tools must be converted to `async def` (see related item: Convert sync tools to async)
- `fastmcp[tasks]` extra must be added to pyproject.toml dependencies
- Progress reporting via `Progress` dependency (pairs with Context logging item)

Work required:
- Add `fastmcp[tasks]` to pyproject.toml
- Convert backlog_sync and backlog_pull to `async def` with `task=True`
- Inject `Progress` dependency and call `progress.set_total(n)`, `progress.increment()` per item

Source: FastMCP v3 docs `servers/tasks.mdx` — `@mcp.tool(task=True)` enables background execution; requires async functions and `fastmcp[tasks]` extra.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: fastmcp-creator skill review of backlog_core/server.py
- **Priority**: P2
- **Added**: 2026-03-06
- **Research questions**: None
