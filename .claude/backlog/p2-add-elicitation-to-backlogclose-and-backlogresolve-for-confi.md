---
name: Add elicitation to backlog_close and backlog_resolve for confirmation of destructive operations
description: "`backlog_close` and `backlog_resolve` permanently close GitHub issues and optionally delete local files. These operations are irreversible. Currently they execute immediately upon invocation — there is no confirmation step.\n\nFastMCP v3 provides `ctx.elicit()` for server-side mid-execution user prompts. This allows a tool to pause and ask \"Are you sure?\" before committing a destructive action. The client renders the confirmation UI; the tool resumes only on `accept`.\n\nFiles affected: `.claude/skills/backlog/backlog_core/server.py`\n\nWork required:\n- Add `ctx: Context` to backlog_close and backlog_resolve\n- Before executing the irreversible GitHub close call, `await ctx.elicit(\"Close #{issue}: {title}?\", response_type=None)`\n- On `decline` or `cancel`, return early with a safe message\n- Gate this behind a parameter `confirm: bool = True` so automated callers (CI, scripts) can skip elicitation\n\nNote: elicitation requires the client to implement an elicitation handler. Tools must handle the case where the client does not support it.\n\nSource: FastMCP v3 docs `servers/elicitation.mdx` — `ctx.elicit(message, response_type=None)` is approval-only elicitation."
metadata:
  topic: add-elicitation-to-backlogclose-and-backlogresolve-for-confi
  source: 'GitHub Issue #470'
  added: '2026-03-06'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#470'
  last_synced: '2026-03-21T03:46:06Z'
---

## Story

As a **developer using Claude Code skills**, I want to **add elicitation to backlog_close and backlog_resolve for confirmation of destructive operations** so that **the tooling becomes more capable and complete**.

## Description

`backlog_close` and `backlog_resolve` permanently close GitHub issues and optionally delete local files. These operations are irreversible. Currently they execute immediately upon invocation — there is no confirmation step.

FastMCP v3 provides `ctx.elicit()` for server-side mid-execution user prompts. This allows a tool to pause and ask "Are you sure?" before committing a destructive action. The client renders the confirmation UI; the tool resumes only on `accept`.

Files affected: `.claude/skills/backlog/backlog_core/server.py`

Work required:
- Add `ctx: Context` to backlog_close and backlog_resolve
- Before executing the irreversible GitHub close call, `await ctx.elicit("Close #{issue}: {title}?", response_type=None)`
- On `decline` or `cancel`, return early with a safe message
- Gate this behind a parameter `confirm: bool = True` so automated callers (CI, scripts) can skip elicitation

Note: elicitation requires the client to implement an elicitation handler. Tools must handle the case where the client does not support it.

Source: FastMCP v3 docs `servers/elicitation.mdx` — `ctx.elicit(message, response_type=None)` is approval-only elicitation.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: fastmcp-creator skill review of backlog_core/server.py
- **Priority**: P2
- **Added**: 2026-03-06
- **Research questions**: None
