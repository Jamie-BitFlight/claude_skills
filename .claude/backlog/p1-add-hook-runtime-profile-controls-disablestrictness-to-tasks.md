---
name: Add hook runtime profile controls (disable/strictness) to task_status_hook
description: "## Current state\n\nAll hooks defined in SKILL.md frontmatter (`PostToolUse` matcher for Write|Edit|Bash on `start-task`, `SubagentStop` on `implement-feature`) execute unconditionally. There is no mechanism to disable individual hooks, reduce hook frequency (e.g., skip PostToolUse LastActivity updates during high-throughput edits), or set a profile level. If a hook causes performance issues or interferes with debugging, the only option is to edit the SKILL.md frontmatter directly."
metadata:
  topic: add-hook-runtime-profile-controls-disablestrictness-to-tasks
  source: 'Research entry: ./research/agent-frameworks/everything-claude-code.md — pattern: Hook runtime controls (ECC_HOOK_PROFILE, ECC_DISABLED_HOOKS)'
  added: '2026-03-10'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#577'
  last_synced: '2026-03-12T12:47:35Z'
---

## Story

As a **developer using Claude Code skills**, I want to **add hook runtime profile controls (disable/strictness) to task_status_hook** so that **the tooling becomes more capable and complete**.

## Description

## Current state

All hooks defined in SKILL.md frontmatter (`PostToolUse` matcher for Write|Edit|Bash on `start-task`, `SubagentStop` on `implement-feature`) execute unconditionally. There is no mechanism to disable individual hooks, reduce hook frequency (e.g., skip PostToolUse LastActivity updates during high-throughput edits), or set a profile level. If a hook causes performance issues or interferes with debugging, the only option is to edit the SKILL.md frontmatter directly.

## Target state

`task_status_hook.py` reads environment variables at startup: `CLAUDE_SKILLS_HOOK_PROFILE` (values: `minimal`, `standard`, `strict`; default `standard`) and `CLAUDE_SKILLS_DISABLED_HOOKS` (comma-separated hook IDs like `post:edit:last-activity`). In `minimal` profile, PostToolUse LastActivity updates are skipped (only SubagentStop completion marking runs). In `strict` profile, additional validation checks run (e.g., verify task file exists before writing). Disabled hooks exit immediately with code 0 when their ID matches the environment variable.

## Measurable signal

Set `CLAUDE_SKILLS_HOOK_PROFILE=minimal` and run a task. Verify that `last_activity` is NOT updated on Write/Edit/Bash calls (PostToolUse handler exits early) but SubagentStop still marks the task complete. Set `CLAUDE_SKILLS_DISABLED_HOOKS=post:bash:last-activity` and verify the specific hook is skipped while others run.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Research entry: ./research/agent-frameworks/everything-claude-code.md — pattern: Hook runtime controls (ECC_HOOK_PROFILE, ECC_DISABLED_HOOKS)
- **Priority**: P1
- **Added**: 2026-03-10
- **Research questions**: None
