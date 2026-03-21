---
name: Add unit tests for session-historian new commands and helpers
description: 'The session-historian enhancement (session-historian-enhance) added four new commands (errors, tools, irritation, current-path), a shared _resolve_session helper, and seven private helper functions. None of these have unit tests. The helper functions are pure data transforms well-suited to unit testing. Project standard requires 80% minimum coverage. Success: pytest suite covering all new helpers and commands, ruff and ty clean.'
metadata:
  topic: add-unit-tests-for-session-historian-new-commands-and-helper
  source: Code review finding — session-historian-enhance implementation review 2026-03-11
  added: '2026-03-11'
  priority: P2
  type: Feature
  status: needs-grooming
  plan: plan/tasks-34-session-historian-enhance-followup-1.md
  issue: '#607'
  last_synced: '2026-03-21T03:45:27Z'
---

## Story

As a **developer using Claude Code skills**, I want to **add unit tests for session-historian new commands and helpers** so that **the tooling becomes more capable and complete**.

## Description

The session-historian enhancement (session-historian-enhance) added four new commands (errors, tools, irritation, current-path), a shared _resolve_session helper, and seven private helper functions. None of these have unit tests. The helper functions are pure data transforms well-suited to unit testing. Project standard requires 80% minimum coverage. Success: pytest suite covering all new helpers and commands, ruff and ty clean.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Code review finding — session-historian-enhance implementation review 2026-03-11
- **Priority**: P2
- **Added**: 2026-03-11
- **Research questions**: None
