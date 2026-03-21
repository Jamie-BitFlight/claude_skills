---
name: Remove duplicate _MIN_CONFLICT_GROUP_SIZE from validator.py
description: _MIN_CONFLICT_GROUP_SIZE constant is defined in both backlog_core/operations.py and dispatch_schema/core/validator.py. T01 of simplify review fixes was supposed to remove the duplicate from validator.py and import from the canonical location but did not complete this change.
metadata:
  topic: remove-duplicate-minconflictgroupsize-from-validatorpy
  source: 'Code review of Issue #938 — simplify review fixes'
  added: '2026-03-21'
  priority: P1
  type: Bug
  status: needs-grooming
  issue: '#952'
  last_synced: '2026-03-21T08:07:18Z'
---

## Story

As a **developer relying on this plugin**, I want to **remove duplicate _min_conflict_group_size from validator.py** so that **the tool works correctly and reliably**.

## Description

_MIN_CONFLICT_GROUP_SIZE constant is defined in both backlog_core/operations.py and dispatch_schema/core/validator.py. T01 of simplify review fixes was supposed to remove the duplicate from validator.py and import from the canonical location but did not complete this change.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Code review of Issue #938 — simplify review fixes
- **Priority**: P1
- **Added**: 2026-03-21
- **Research questions**: None
