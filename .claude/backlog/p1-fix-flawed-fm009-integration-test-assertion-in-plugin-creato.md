---
name: Fix flawed FM009 integration test assertion in plugin-creator
description: "In `plugins/plugin-creator/tests/test_frontmatter_fixes.py` line 251, the FM009 assertion uses `str.split('fm009')[1:]` with the `in` operator against a list, which tests list membership rather than substring presence. The assertion always passes regardless of actual output — it provides zero test coverage of its stated intent. The fix should use `str.partition('fm009')[2]` and a substring `in` check so the assertion actually fails when the validator incorrectly emits FM009 for an mcp: field. All 26 existing tests must continue to pass after the fix."
metadata:
  topic: fix-flawed-fm009-integration-test-assertion-in-plugin-creato
  source: Agent task — code review follow-up from plan/tasks-25-multi-ecosystem-plugin-creator-followup-1.md
  added: '2026-03-06'
  priority: P1
  type: Bug
  status: needs-grooming
  plan: plan/tasks-25-multi-ecosystem-plugin-creator-followup-1.md
  issue: '#516'
  last_synced: '2026-03-12T12:48:06Z'
---

## Story

As a **developer using Claude Code skills**, I want to **fix flawed fm009 integration test assertion in plugin-creator** so that **the tooling becomes more capable and complete**.

## Description

In `plugins/plugin-creator/tests/test_frontmatter_fixes.py` line 251, the FM009 assertion uses `str.split('fm009')[1:]` with the `in` operator against a list, which tests list membership rather than substring presence. The assertion always passes regardless of actual output — it provides zero test coverage of its stated intent. The fix should use `str.partition('fm009')[2]` and a substring `in` check so the assertion actually fails when the validator incorrectly emits FM009 for an mcp: field. All 26 existing tests must continue to pass after the fix.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Agent task — code review follow-up from plan/tasks-25-multi-ecosystem-plugin-creator-followup-1.md
- **Priority**: P1
- **Added**: 2026-03-06
- **Research questions**: None
