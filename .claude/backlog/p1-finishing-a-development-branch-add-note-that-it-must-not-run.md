---
name: 'finishing-a-development-branch: add note that it must not run while subagent-driven-development is in progress in the same worktree'
description: 'The `superpowers:finishing-a-development-branch` skill can be invoked from the plan at the end of `superpowers:executing-plans`, but when `superpowers:subagent-driven-development` is the active execution pattern the finishing step must not run mid-session — it is only valid after the final code quality reviewer has approved all tasks. The skill currently has no guard against being invoked while subagent-driven-development is still dispatching subagents. A note (and ideally a check) is needed: if a subagent-driven-development session is in progress in the current worktree, warn and refuse to run finishing-a-development-branch until all tasks show complete.'
metadata:
  topic: finishing-a-development-branch-add-note-that-it-must-not-run
  source: Session observation — executing-plans invoked finishing-a-development-branch without awareness that subagent-driven-development was the active execution pattern
  added: '2026-03-04'
  priority: P1
  type: Docs
  status: needs-grooming
  issue: '#430'
  last_synced: '2026-03-12T12:48:26Z'
---

## Story

As a **developer reading the documentation**, I want to **finishing-a-development-branch: add note that it must not run while subagent-driven-development is in progress in the same worktree** so that **documentation is accurate and trustworthy**.

## Description

The `superpowers:finishing-a-development-branch` skill can be invoked from the plan at the end of `superpowers:executing-plans`, but when `superpowers:subagent-driven-development` is the active execution pattern the finishing step must not run mid-session — it is only valid after the final code quality reviewer has approved all tasks. The skill currently has no guard against being invoked while subagent-driven-development is still dispatching subagents. A note (and ideally a check) is needed: if a subagent-driven-development session is in progress in the current worktree, warn and refuse to run finishing-a-development-branch until all tasks show complete.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation — executing-plans invoked finishing-a-development-branch without awareness that subagent-driven-development was the active execution pattern
- **Priority**: P1
- **Added**: 2026-03-04
- **Research questions**: None
