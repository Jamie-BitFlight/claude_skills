---
name: Add Context logging and progress reporting to backlog_core long-running tools
description: "No tool in backlog_core/server.py uses `ctx: Context`. Operations like `backlog_sync`, `backlog_pull`, and `backlog_groom` make multiple sequential GitHub API calls but emit zero progress feedback to the client. The client sees nothing until the operation completes or errors.\n\nFastMCP v3 provides `ctx.info()`, `ctx.warning()`, `ctx.report_progress(progress, total)` for real-time feedback during tool execution. These map directly to MCP protocol log messages and progress notifications.\n\nFiles affected: `.claude/skills/backlog/backlog_core/server.py`\n\nWork required:\n- Add `ctx: Context` parameter to backlog_sync, backlog_pull, backlog_groom, backlog_normalize\n- Emit `ctx.info()` at key milestones (e.g., \"Fetching open issues…\", \"Syncing item: {title}\")\n- Use `ctx.report_progress(i, total)` for batch operations where total is known\n- Use `ctx.warning()` to surface warnings currently buried in `out.warnings`\n\nSource: FastMCP v3 docs `servers/context.mdx` — `ctx.info()`, `ctx.warning()`, `ctx.report_progress()` send real-time messages to the MCP client."
metadata:
  topic: add-context-logging-and-progress-reporting-to-backlogcore-lo
  source: 'GitHub Issue #465'
  added: '2026-03-06'
  priority: completed
  type: Feature
  status: done
  issue: '#465'
  last_synced: '2026-03-06T21:54:15Z'
  groomed: '2026-03-06'
  plan: plan/tasks-1-context-logging-progress.md
---

## Story

As a **developer using Claude Code skills**, I want to **add context logging and progress reporting to backlog_core long-running tools** so that **the tooling becomes more capable and complete**.

## Description

No tool in backlog_core/server.py uses `ctx: Context`. Operations like `backlog_sync`, `backlog_pull`, and `backlog_groom` make multiple sequential GitHub API calls but emit zero progress feedback to the client. The client sees nothing until the operation completes or errors.

FastMCP v3 provides `ctx.info()`, `ctx.warning()`, `ctx.report_progress(progress, total)` for real-time feedback during tool execution. These map directly to MCP protocol log messages and progress notifications.

Files affected: `.claude/skills/backlog/backlog_core/server.py`

Work required:
- Add `ctx: Context` parameter to backlog_sync, backlog_pull, backlog_groom, backlog_normalize
- Emit `ctx.info()` at key milestones (e.g., "Fetching open issues…", "Syncing item: {title}")
- Use `ctx.report_progress(i, total)` for batch operations where total is known
- Use `ctx.warning()` to surface warnings currently buried in `out.warnings`

Source: FastMCP v3 docs `servers/context.mdx` — `ctx.info()`, `ctx.warning()`, `ctx.report_progress()` send real-time messages to the MCP client.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: fastmcp-creator skill review of backlog_core/server.py
- **Priority**: P1
- **Added**: 2026-03-06
- **Research questions**: None

## Fact-Check

Claims checked: 4 | VERIFIED: 4 | REFUTED: 0 | INCONCLUSIVE: 0

**VERIFIED** — FastMCP v3 provides `ctx.info()`, `ctx.warning()`, `ctx.report_progress(progress, total)` as async coroutines on the `Context` object.
SOURCE: `.claude/worktrees/fastmcp/docs/servers/context.mdx` lines 134-136, 173 (accessed 2026-03-06)

**VERIFIED** — Import path: `from fastmcp import FastMCP, Context`; `ctx: Context` parameter is auto-excluded from MCP tool schema.
SOURCE: `.claude/worktrees/fastmcp/docs/servers/context.mdx` lines 72, 82-84 (accessed 2026-03-06)

**VERIFIED** — 4 target tools (`backlog_sync`, `backlog_pull`, `backlog_groom`, `backlog_normalize`) are currently synchronous `def` in server.py.
SOURCE: Direct grep of `.claude/skills/backlog/backlog_core/server.py` (accessed 2026-03-06)

**VERIFIED** — `ctx` methods are coroutines requiring `await`; tools must be `async def` to use them. #472 (async conversion) must land first.
SOURCE: `.claude/worktrees/fastmcp/docs/servers/context.mdx`; confirmed by #472 description (accessed 2026-03-06)

## RT-ICA

Goal: Add `ctx: Context` parameter and real-time feedback (`ctx.info()`, `ctx.report_progress()`, `ctx.warning()`) to the 4 long-running tools in server.py so MCP clients receive progress notifications during GitHub API operations.

| # | Condition | Status | Info Needed |
|---|-----------|--------|-------------|
| 1 | Target tools identified | AVAILABLE | backlog_sync, backlog_pull, backlog_groom, backlog_normalize |
| 2 | FastMCP Context API understood | AVAILABLE | ctx.info(), ctx.warning(), ctx.report_progress(i, total) — all coroutines |
| 3 | Import path known | AVAILABLE | from fastmcp import FastMCP, Context |
| 4 | Key milestones per tool identified | AVAILABLE | groomable from operations.py call sites |
| 5 | #472 (async def) merged | MISSING | Tools must be async def before ctx methods can be awaited |

Decision: APPROVED for planning (prerequisite is plannable — #472 now has a task plan). Execution is blocked on #472 merge.
Missing inputs: #472 merged (in planning as of 2026-03-06).