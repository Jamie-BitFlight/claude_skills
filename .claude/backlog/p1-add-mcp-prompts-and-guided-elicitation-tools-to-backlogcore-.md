---
name: Add MCP prompts and guided elicitation tools to backlog_core to consolidate workflow logic
description: "The workflow logic currently scattered across /backlog, /create-backlog-item, /groom-backlog-item, and /work-backlog-item skills should live in the MCP server so it travels with the tools and stays current without skill updates.\n\nTwo additions to backlog_core/server.py:\n\n**New MCP prompts** (return message content clients inject into LLM context):\n- `backlog_guide()` — full tool reference documentation as messages; replaces /backlog skill entirely\n- `create_item_guided()` — intake field instructions and format as messages\n- `groom_item(selector)` — fetches item via operations.view_item() server-side, returns item state + grooming workflow as messages\n- `work_item(selector)` — returns item state + planning instructions as messages\n- `close_or_resolve(selector)` — returns item state + close vs. resolve decision guide as messages\n\n**New guided tools using ctx.elicit()** (interactive versions of existing CRUD tools):\n- `backlog_add_guided` — elicits title, priority, description, type interactively then calls operations.add_item(); replaces the /create-backlog-item interactive flow\n- `backlog_close_confirmed` — elicits confirmation before closing, then delegates to operations.close_item(); absorbs the confirm step currently in the skill\n- `backlog_resolve_confirmed` — elicits summary + confirmation before resolving; absorbs the confirm step currently in the skill\n- `backlog_setup_github` — runs label taxonomy + milestone init; absorbs setup-github command from /work-backlog-item\n\nPrerequisites: ctx.elicit() requires async tools (see #472) and Context logging (#465).\n\nFiles: .claude/skills/backlog/backlog_core/server.py, operations.py"
metadata:
  topic: add-mcp-prompts-and-guided-elicitation-tools-to-backlogcore-
  source: 'GitHub Issue #473'
  added: '2026-03-06'
  priority: P1
  type: Feature
  status: in-progress
  issue: '#473'
  last_synced: '2026-03-14T16:00:27Z'
  groomed: '2026-03-06'
  plan: plan/tasks-1-mcp-prompts-elicitation.md
---

## Story

As a **developer**, I want **The workflow logic currently scattered across /backlog, /create-backlog-item,...** so that **backlog items are tracked in GitHub**.

## Description

The workflow logic currently scattered across /backlog, /create-backlog-item, /groom-backlog-item, and /work-backlog-item skills should live in the MCP server so it travels with the tools and stays current without skill updates.

Two additions to backlog_core/server.py:

**New MCP prompts** (return message content clients inject into LLM context):
- `backlog_guide()` — full tool reference documentation as messages; replaces /backlog skill entirely
- `create_item_guided()` — intake field instructions and format as messages
- `groom_item(selector)` — fetches item via operations.view_item() server-side, returns item state + grooming workflow as messages
- `work_item(selector)` — returns item state + planning instructions as messages
- `close_or_resolve(selector)` — returns item state + close vs. resolve decision guide as messages

**New guided tools using ctx.elicit()** (interactive versions of existing CRUD tools):
- `backlog_add_guided` — elicits title, priority, description, type interactively then calls operations.add_item(); replaces the /create-backlog-item interactive flow
- `backlog_close_confirmed` — elicits confirmation before closing, then delegates to operations.close_item(); absorbs the confirm step currently in the skill
- `backlog_resolve_confirmed` — elicits summary + confirmation before resolving; absorbs the confirm step currently in the skill
- `backlog_setup_github` — runs label taxonomy + milestone init; absorbs setup-github command from /work-backlog-item

Prerequisites: ctx.elicit() requires async tools (see #472) and Context logging (#465).

Files: .claude/skills/backlog/backlog_core/server.py, operations.py

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: GitHub Issue #473
- **Priority**: P1
- **Added**: 2026-03-06
- **Research questions**: None

## Fact-Check

Claims checked: 4 | VERIFIED: 4 | REFUTED: 0 | INCONCLUSIVE: 0

**VERIFIED** — `ctx.elicit()` is an async method; tools using it must be `async def` with `await ctx.elicit(...)`.
SOURCE: FastMCP docs — `.claude/worktrees/fastmcp/docs/v2/servers/elicitation.mdx` (accessed 2026-03-06)

**VERIFIED** — FastMCP supports MCP prompts via `@mcp.prompt` decorator returning `str` or `list[Message]`.
SOURCE: FastMCP docs — `.claude/worktrees/fastmcp/docs/servers/prompts.mdx` (accessed 2026-03-06)

**VERIFIED** — Prompts return messages injected into LLM context: "The generated message(s) are returned to the LLM to guide its response."
SOURCE: FastMCP docs — `.claude/worktrees/fastmcp/docs/servers/prompts.mdx` (accessed 2026-03-06)

**VERIFIED** — Prerequisites #472 (async tools) and #465 (context logging) are both open; prerequisite chain is valid and unblocked by completed work.
SOURCE: `gh issue view 472`, `gh issue view 465` (accessed 2026-03-06)

No claims refuted. No claims inconclusive. All preconditions stated in the item description are accurate.

## RT-ICA

Goal: Consolidate backlog workflow logic into the MCP server so it travels with the tools and stays current without skill updates.

| # | Condition | Status | Info Needed |
|---|-----------|--------|-------------|
| 1 | FastMCP async tool support (#472 merged) | MISSING | #472 must land first — ctx.elicit requires async def |
| 2 | Context logging (#465 merged) | MISSING | #465 must land first — ctx methods require async context |
| 3 | Target files identified | AVAILABLE | backlog_core/server.py, operations.py |
| 4 | MCP prompts API understood | AVAILABLE | @mcp.prompt, list[Message] return type, verified in docs |
| 5 | ctx.elicit() API understood | AVAILABLE | async method, dataclass response_type, ElicitationResult |
| 6 | Skills to replace identified | AVAILABLE | /backlog, /create-backlog-item, /groom-backlog-item, /work-backlog-item (partially) |
| 7 | Guided tools spec complete | AVAILABLE | 4 tools fully described with input/output behavior |

Decision: APPROVED — item is well-specified. Prerequisites are external blockers (#472, #465), not missing information.
Missing inputs: #472 merged, #465 merged (both open as of 2026-03-06).

## Groomed (2026-03-06)

### Issue Classification

Type: unbounded-design
Scenario-target: Skills contain workflow logic (intake, grooming, working, closing flows) that could live in the MCP server, making it client-independent and always current.
Analysis method: design-framing — no defect, no recurrence; this is architectural consolidation of scattered workflow logic into its natural home.

### Priority

8/10 — Consolidates scattered workflow logic into the MCP server, making it client-independent and eliminating version skew between skills and tools. The /backlog, /create-backlog-item, /groom-backlog-item, and /work-backlog-item skills currently duplicate logic that must be kept in sync with the MCP server manually. Moving this logic into the server means any MCP client (Claude Desktop, Claude Code, Cursor, Zed) gets the full workflow without requiring skill installation or updates.

### Impact

- Workflow logic currently lives in 4 Claude Code skills — those skills are Claude Code-only; MCP prompts work across all MCP clients (Claude Desktop, Cursor, Zed, etc.)
- Duplicate intake/confirmation flows in skills and server drift over time as either side evolves
- Users on non-Claude-Code MCP clients have no guided workflow today — this unblocks them
- The /create-backlog-item interactive mode and /work-backlog-item setup-github command become redundant after this ships

### Scope

**Current state**: server.py contains 10 synchronous `def` tools — no prompts, no `ctx` usage, no `async def`. The 6 backlog_core files are: `server.py`, `operations.py`, `github.py`, `models.py`, `parsing.py`, `__init__.py`.

**New additions to server.py** — 9 new functions total:

5 MCP prompts (via `@mcp.prompt` decorator):
- `backlog_guide()` — no parameters, returns full tool reference as messages
- `create_item_guided()` — no parameters, returns intake instructions as messages
- `groom_item(selector: str)` — calls `operations.view_item()` server-side, returns item state + grooming workflow as messages (must be `async def`)
- `work_item(selector: str)` — returns item state + planning instructions as messages (must be `async def`)
- `close_or_resolve(selector: str)` — returns item state + close vs. resolve decision guide as messages (must be `async def`)

4 guided tools (via `@mcp.tool`, must be `async def` with `ctx: Context`):
- `backlog_add_guided` — multi-field elicitation then delegates to `operations.add_item()`
- `backlog_close_confirmed` — `response_type=None` elicitation for confirmation before `operations.close_item()`
- `backlog_resolve_confirmed` — structured elicitation for summary before `operations.resolve_item()`
- `backlog_setup_github` — runs label taxonomy and milestone initialization (logic currently in /work-backlog-item setup-github mode)

### Output / Evidence

Observable when done:

1. An MCP client can call `prompts/list` and see `backlog_guide`, `create_item_guided`, `groom_item`, `work_item`, `close_or_resolve` in the response
2. Calling `backlog_guide` with no arguments returns message content containing the full tool reference (same content as the /backlog SKILL.md Primary Interface section)
3. Calling `groom_item(selector="#473")` returns messages including the item's current body and grooming workflow instructions
4. Calling `backlog_add_guided` in an elicitation-capable client pauses and presents a form collecting `title`, `priority`, `description`, `type`
5. Calling `backlog_close_confirmed` presents a confirmation prompt before executing close
6. Calling `backlog_resolve_confirmed` presents a summary-collection form before executing resolve
7. All 10 existing tools remain registered and unmodified — no regressions
8. Guided tools handle all 3 elicitation outcomes (accept/decline/cancel) and return clear messages for each
9. Guided tools handle `NotSupportedError` when client does not support elicitation and return a helpful fallback message

### Dependencies

**Blocked by:**
- **#472** (P2, open) — "Convert backlog_core tools to async def" — delivers `async def` tool patterns and `asyncio.to_thread()` wrapping for PyGithub calls. Required because `ctx.elicit()` is an async method; guided tools must be `async def` to call it. **Must merge first.**
- **#465** (P1, open) — "Add Context logging and progress reporting" — delivers `ctx: Context` parameter pattern established in server.py. While #465 adds `ctx` to existing tools, #473 uses `ctx` in new async tools. Can proceed independently but both items touch `server.py` — sequence to avoid merge conflicts.

**Priority mismatch**: #472 (prerequisite) is P2 while #473 is P1. Either #472 must be bumped to P1, or #473 should be held until #472 lands.

**Blocks:** Nothing currently in backlog.

### Research

**FastMCP prompts API** — SOURCE: `.claude/worktrees/fastmcp/docs/servers/prompts.mdx` (accessed 2026-03-06)

Import path:
```python
from fastmcp.prompts import Message, PromptResult
```

Return types: `str` (auto-converted to user message), `list[Message | str]`, or `PromptResult`. Prompts can be `def` or `async def`. `async def` required when body makes I/O calls (e.g., `operations.view_item()` calls GitHub API).

**FastMCP ctx.elicit() API** — SOURCE: `.claude/worktrees/fastmcp/docs/v2/servers/elicitation.mdx` (accessed 2026-03-06)

```python
result = await ctx.elicit(message: str, response_type=<type>)
```

Supported `response_type` values:
- `str`, `int`, `bool` — scalar primitives
- `["opt1", "opt2"]` — constrained enum single-select
- `[["opt1", "opt2"]]` — multi-select
- `None` — confirmation only (no data returned)
- `dataclass`, `TypedDict`, `BaseModel` — structured multi-field; fields must be shallow primitives
- `Literal["a", "b"]` — enum via Literal type

`ElicitationResult` fields: `result.action` (`"accept"` | `"decline"` | `"cancel"`), `result.data` (populated when accept, else None).

For `backlog_add_guided`, structured elicitation dataclass:
```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class AddItemRequest:
    title: str
    priority: Literal["P0", "P1", "P2", "Ideas"]
    description: str
    type_: Literal["Feature", "Bug", "Refactor", "Docs", "Chore"] = "Feature"
```

Client capability constraint: `ctx.elicit()` raises `NotSupportedError` if the client does not implement an elicitation handler. All guided tools must catch this and return a clear fallback message directing the user to use the non-guided equivalent tool.

### Skills

Skills affected — logic partially moves to MCP server; skills become thinner wrappers or remain for Claude Code-specific orchestration:

- `.claude/skills/backlog/SKILL.md` — Primary Interface section moves to `backlog_guide()` prompt
- `.claude/skills/create-backlog-item/SKILL.md` — interactive intake moves to `backlog_add_guided` + `create_item_guided` prompt; `--auto` mode (codebase research) and `quick` mode stay skill-only
- `.claude/skills/groom-backlog-item/SKILL.md` — item state + instructions move to `groom_item` prompt; agent delegation, validity check, PR/commit search stay skill-only
- `.claude/skills/work-backlog-item/SKILL.md` — setup-github and close/resolve confirmation move to `backlog_setup_github`, `backlog_close_confirmed`, `backlog_resolve_confirmed`, `work_item` prompt; SAM planning flow and `--auto` mode stay skill-only

### Agents

Implementation: `@python3-development:python-cli-architect` — additive changes (new async functions, new imports) to server.py. No existing tools are modified.

Review: `@python3-development:python-code-reviewer` — verify async patterns, elicitation response handling (all 3 action outcomes guarded), and that existing sync tools are untouched.

### Prior Work

No partial implementation found as of 2026-03-06. Grep for `@mcp.prompt`, `mcp.prompt`, and `elicit(` across `.claude/skills/backlog/` returned no matches. No git commits referencing "mcp prompt" or "elicit" in the backlog_core area. server.py contains only 10 synchronous `def` tools — no prompts, no `ctx` usage, no `async def`.

### Files

Primary implementation:
- `.claude/skills/backlog/backlog_core/server.py` — add 5 `@mcp.prompt` functions and 4 async `@mcp.tool` functions with `ctx: Context`
- `.claude/skills/backlog/backlog_core/operations.py` — read-only dependency; `view_item()`, `add_item()`, `close_item()`, `resolve_item()` called by new guided tools

Skills to thin after implementation:
- `.claude/skills/backlog/SKILL.md`
- `.claude/skills/create-backlog-item/SKILL.md`
- `.claude/skills/groom-backlog-item/SKILL.md`
- `.claude/skills/work-backlog-item/SKILL.md`

FastMCP reference (read-only, for implementer):
- `.claude/worktrees/fastmcp/docs/servers/prompts.mdx`
- `.claude/worktrees/fastmcp/docs/v2/servers/elicitation.mdx`
