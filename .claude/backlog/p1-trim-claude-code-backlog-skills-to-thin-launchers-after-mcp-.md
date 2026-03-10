---
name: Trim Claude Code backlog skills to thin launchers after MCP prompt consolidation
description: "Depends on #473 (MCP prompts + guided tools in backlog_core).\n\nOnce the server has prompts and guided tools, the Claude Code skills become thin launchers. Each skill's workflow instructions are replaced by a prompts/get call to the server.\n\nChanges per skill:\n- /backlog → DELETE the skill entirely; backlog_guide() prompt is the replacement. Update CLAUDE.md reference to point to the MCP prompt.\n- /create-backlog-item → Reduce to ~10 lines: fetch create_item_guided prompt, call backlog_add_guided tool, report result. Remove all field collection logic, duplicate detection prose, and step-by-step instructions (those now live in the server prompt).\n- /groom-backlog-item → Keep orchestration only (fact-check, RT-ICA, agent spawning). Remove item loading steps 1-3 — replace with: fetch groom_item(selector) prompt which returns item state. Remove step 9 write instructions — already documented in the prompt.\n- /work-backlog-item → Keep orchestration only (RT-ICA gate, SAM invocation, sub-agent routing). Remove item loading steps 1-2 — replace with: fetch work_item(selector) prompt. Remove close/resolve step 9 — replace with: call backlog_close_confirmed or backlog_resolve_confirmed tools.\n\nSuccess criteria: each trimmed skill is under 50 lines. All workflow intelligence has a single home in the MCP server.\n\nFiles: .claude/skills/backlog/SKILL.md, .claude/skills/create-backlog-item/SKILL.md, .claude/skills/groom-backlog-item/SKILL.md, .claude/skills/work-backlog-item/SKILL.md"
metadata:
  topic: trim-claude-code-backlog-skills-to-thin-launchers-after-mcp-
  source: 'GitHub Issue #474'
  added: '2026-03-06'
  priority: P1
  type: Refactor
  status: needs-grooming
  issue: '#474'
  last_synced: '2026-03-10T06:56:07Z'
---

## Story

As a **maintainer of the codebase**, I want to **trim claude code backlog skills to thin launchers after mcp prompt consolidation** so that **the code is cleaner and more maintainable**.

## Description

Depends on #473 (MCP prompts + guided tools in backlog_core).

Once the server has prompts and guided tools, the Claude Code skills become thin launchers. Each skill's workflow instructions are replaced by a prompts/get call to the server.

Changes per skill:
- /backlog → DELETE the skill entirely; backlog_guide() prompt is the replacement. Update CLAUDE.md reference to point to the MCP prompt.
- /create-backlog-item → Reduce to ~10 lines: fetch create_item_guided prompt, call backlog_add_guided tool, report result. Remove all field collection logic, duplicate detection prose, and step-by-step instructions (those now live in the server prompt).
- /groom-backlog-item → Keep orchestration only (fact-check, RT-ICA, agent spawning). Remove item loading steps 1-3 — replace with: fetch groom_item(selector) prompt which returns item state. Remove step 9 write instructions — already documented in the prompt.
- /work-backlog-item → Keep orchestration only (RT-ICA gate, SAM invocation, sub-agent routing). Remove item loading steps 1-2 — replace with: fetch work_item(selector) prompt. Remove close/resolve step 9 — replace with: call backlog_close_confirmed or backlog_resolve_confirmed tools.

Success criteria: each trimmed skill is under 50 lines. All workflow intelligence has a single home in the MCP server.

Files: .claude/skills/backlog/SKILL.md, .claude/skills/create-backlog-item/SKILL.md, .claude/skills/groom-backlog-item/SKILL.md, .claude/skills/work-backlog-item/SKILL.md

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Architecture review — consolidating Claude Code skills into MCP server
- **Priority**: P1
- **Added**: 2026-03-06
- **Research questions**: None
