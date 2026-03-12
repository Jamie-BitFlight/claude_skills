---
name: Convert backlog_core tools to async def for non-blocking GitHub API calls
description: "All 10 tools in backlog_core/server.py are synchronous `def` functions. FastMCP runs sync tools in a thread pool automatically, but this prevents any tool from using `await` — meaning GitHub API calls, file I/O, and `ctx` methods all block.\n\nConverting tools to `async def` unblocks:\n1. `ctx.info()`, `ctx.report_progress()`, `ctx.elicit()` — these are all coroutines and require async context\n2. Future async GitHub client (e.g., `httpx` + `PyGithub` async variant) for true non-blocking I/O\n3. Background tasks via `task=True` — which requires async functions\n4. Parallel GitHub API calls via `asyncio.gather()` in batch operations\n\nFiles affected: `.claude/skills/backlog/backlog_core/server.py`, `.claude/skills/backlog/backlog_core/operations.py`, `.claude/skills/backlog/backlog_core/github.py`\n\nNote: This is a prerequisite for the background tasks item (#469) and a dependency for Context logging (#465). The PyGithub library is synchronous; async calls to it must use `asyncio.to_thread()` in the interim until an async client is adopted.\n\nSource: FastMCP v3 docs `servers/tools.mdx` — FastMCP supports both `def` and `async def`; sync tools run in threadpool; async preferred for I/O-bound operations."
metadata:
  topic: convert-backlogcore-tools-to-async-def-for-non-blocking-gith
  source: 'GitHub Issue #472'
  added: '2026-03-06'
  priority: completed
  type: Refactor
  status: done
  issue: '#472'
  last_synced: '2026-03-06T17:48:59Z'
  groomed: '2026-03-06'
  plan: plan/tasks-1-convert-backlog-core-async.md
---

## Story

As a **maintainer of the codebase**, I want to **convert backlog_core tools to async def for non-blocking github api calls** so that **the code is cleaner and more maintainable**.

## Description

All 10 tools in backlog_core/server.py are synchronous `def` functions. FastMCP runs sync tools in a thread pool automatically, but this prevents any tool from using `await` — meaning GitHub API calls, file I/O, and `ctx` methods all block.

Converting tools to `async def` unblocks:
1. `ctx.info()`, `ctx.report_progress()`, `ctx.elicit()` — these are all coroutines and require async context
2. Future async GitHub client (e.g., `httpx` + `PyGithub` async variant) for true non-blocking I/O
3. Background tasks via `task=True` — which requires async functions
4. Parallel GitHub API calls via `asyncio.gather()` in batch operations

Files affected: `.claude/skills/backlog/backlog_core/server.py`, `.claude/skills/backlog/backlog_core/operations.py`, `.claude/skills/backlog/backlog_core/github.py`

Note: This is a prerequisite for the background tasks item (#469) and a dependency for Context logging (#465). The PyGithub library is synchronous; async calls to it must use `asyncio.to_thread()` in the interim until an async client is adopted.

Source: FastMCP v3 docs `servers/tools.mdx` — FastMCP supports both `def` and `async def`; sync tools run in threadpool; async preferred for I/O-bound operations.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: fastmcp-creator skill review of backlog_core/server.py
- **Priority**: P2
- **Added**: 2026-03-06
- **Research questions**: None

## Groomed (2026-03-06)

### Issue Classification

Refactor — architectural enablement. No defect. Converts synchronous tool definitions to `async def` so that FastMCP `Context` methods (`ctx.info()`, `ctx.warning()`, `ctx.report_progress()`, `ctx.elicit()`) become callable inside tools. Without `async def`, those coroutines cannot be awaited and any tool that calls them will raise a `RuntimeError` at runtime.

Analysis method: design-framing. Source verification confirmed all claims prior to grooming.

### Priority

6/10 — This is a prerequisite refactor, not user-visible on its own. Priority derives entirely from the items it unblocks: #465 (P1, context logging) and #473 (P1, MCP prompts and elicitation). Both are blocked until this lands. The refactor itself is low-risk and mechanically bounded.

### Impact

- Blocks: #465 (context logging and progress reporting) and #473 (MCP prompts and guided elicitation) cannot proceed until tools are `async def`
- Bottleneck: Any future tool that needs `ctx` for feedback, sampling, or elicitation faces the same barrier. Converting now prevents per-tool friction on every subsequent `ctx` addition.

### Benefits

- Unblocks #465: `ctx.info()`, `ctx.warning()`, `ctx.report_progress()` become usable in `backlog_sync`, `backlog_pull`, `backlog_groom`, `backlog_normalize`
- Unblocks #473: `ctx.elicit()` becomes usable for guided workflows and confirmation prompts
- No behavior change for callers — FastMCP runs sync tools in a threadpool; async tools run on the event loop. The MCP protocol surface and return types are unchanged.
- Positions all 10 tools to receive `ctx: Context` parameters incrementally without re-conversion

### Expected Behavior

After conversion, all 10 tools in `server.py` accept calls from FastMCP's async runtime. Tools that do not yet use `ctx` continue to behave identically. Tools that subsequently add `ctx` parameters can `await` any `ctx` coroutine without error.

Synchronous operations in `operations.py` and `github.py` (PyGithub calls) are wrapped with `asyncio.to_thread()` so the event loop is not blocked during I/O.

### Desired Structure

- All 10 `@mcp.tool()` functions in `server.py` are declared `async def`
- Calls to `operations.*` functions (which remain synchronous) are wrapped: `await asyncio.to_thread(operations.fn, ...)`
- `import asyncio` added to `server.py`
- No changes to `operations.py`, `github.py`, or `models.py` — those stay synchronous
- `mypy` / `basedpyright` type-checks pass with no new errors
- `ruff` linting passes

### Acceptance Criteria

1. `grep -c "async def" .claude/skills/backlog/backlog_core/server.py` returns `10`
2. `grep -c "await asyncio.to_thread" .claude/skills/backlog/backlog_core/server.py` returns at least `10` (one per tool body that calls `operations.*`)
3. `grep "^import asyncio" .claude/skills/backlog/backlog_core/server.py` exits 0
4. `uv run python -c "from backlog_core.server import mcp"` exits 0 (import succeeds)
5. All 10 MCP tools callable via the backlog MCP server with identical return shapes to pre-conversion (spot-check `backlog_list` and `backlog_view`)
6. `uv run ruff check .claude/skills/backlog/backlog_core/server.py` exits 0
7. Type checker (`basedpyright` or `mypy`) reports no new errors on `server.py`

### Resources

| Type | Item |
|------|------|
| Prior work | `.claude/skills/backlog/backlog_core/server.py` — 10 sync tools to convert |
| Prior work | `.claude/skills/backlog/backlog_core/operations.py` — sync operation functions called by each tool |
| Prior work | `.claude/skills/backlog/backlog_core/github.py` — PyGithub calls (stay synchronous) |
| Reference | `.claude/worktrees/fastmcp/docs/servers/tools.mdx` — FastMCP async tool pattern (VERIFIED) |
| Reference | `.claude/worktrees/fastmcp/docs/servers/context.mdx` — `ctx` coroutine signatures |

FastMCP async tool pattern (VERIFIED from `.claude/worktrees/fastmcp/docs/servers/tools.mdx`):

```python
import asyncio
from fastmcp import FastMCP, Context

mcp = FastMCP("backlog")

@mcp.tool()
async def backlog_add(...) -> dict:
    return await asyncio.to_thread(operations.add_item, ...)
```

FastMCP runs sync tools in a threadpool — converting to `async def` moves execution to the event loop. PyGithub calls inside `operations.py` remain blocking; `asyncio.to_thread()` offloads them to a thread so the event loop is not starved.

SOURCE: `.claude/worktrees/fastmcp/docs/servers/tools.mdx` (verified 2026-03-06)

### Dependencies

- Depends on: None — no prerequisites. `asyncio` is stdlib; FastMCP already supports `async def` tools.
- Blocks: #465 (Add Context logging and progress reporting — P1), #473 (Add MCP prompts and guided elicitation — P1), #470 (elicitation for close/resolve confirmation — P2), #469 (background task support — P2)

### Effort

Small — mechanically bounded to one file (`server.py`, ~385 lines). Each of the 10 tool functions requires: `def` → `async def`, wrap `operations.*` call with `await asyncio.to_thread(...)`, add `import asyncio`. No logic changes. No changes to `operations.py`, `github.py`, or `models.py`.

## Fact-Check

Claims checked: 4 | VERIFIED: 4 | REFUTED: 0 | INCONCLUSIVE: 0

**VERIFIED** — FastMCP runs sync tools in a thread pool automatically, preventing `await` usage inside those tools.
SOURCE: `.claude/worktrees/fastmcp/docs/servers/tools.mdx` (accessed 2026-03-06)

**VERIFIED** — `ctx.elicit()`, `ctx.info()`, `ctx.report_progress()` are coroutines; tools that call them must be `async def`.
SOURCE: `.claude/worktrees/fastmcp/docs/v2/servers/elicitation.mdx`, `.claude/worktrees/fastmcp/docs/servers/context.mdx` (accessed 2026-03-06)

**VERIFIED** — `asyncio.to_thread()` is the correct interim pattern for wrapping synchronous PyGithub calls inside async tools.
SOURCE: Python 3.9+ stdlib docs; FastMCP tools.mdx confirms sync tools run in threadpool — same principle applies in reverse for async tools calling sync code.

**VERIFIED** — Current state: all 10 tools in `backlog_core/server.py` are synchronous `def` — no `async def`, no `ctx` usage.
SOURCE: Direct grep of `.claude/skills/backlog/backlog_core/server.py` (accessed 2026-03-06)

## RT-ICA

Goal: Convert all 10 tools in server.py to `async def` with `asyncio.to_thread()` wrapping for synchronous operations, enabling `ctx` method usage required by #465 and #473.

| # | Condition | Status | Info Needed |
|---|-----------|--------|-------------|
| 1 | Target files identified | AVAILABLE | server.py — 10 tools; operations.py — sync business logic |
| 2 | FastMCP async tool pattern understood | AVAILABLE | `async def` + `asyncio.to_thread()` for sync calls |
| 3 | `asyncio.to_thread()` wrapping pattern | AVAILABLE | stdlib; no new dependencies |
| 4 | No prerequisite issues | AVAILABLE | This item has no blockers — it is itself foundational |
| 5 | Scope boundary clear | AVAILABLE | server.py only; operations.py stays synchronous |

Decision: APPROVED — no missing inputs. Pure refactor with clear scope and known implementation pattern.