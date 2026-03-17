---
name: Replace remaining duplicated dict-based functions in backlog.py with core imports
description: 'Follow-up from #611 dedup: 7 functions in backlog.py still have local implementations rather than delegating to backlog_core equivalents: _find_fuzzy_duplicates, _build_issue_body_from_file, items_needing_issues, items_with_issues, _parse_issue_selector, _issue_to_local_fields, _fetch_open_issues_by_title. Each should be evaluated for migration to core or adapter wrapping.'
metadata:
  topic: replace-remaining-duplicated-dict-based-functions-in-backlog
  source: 'Code review followup from #611'
  added: '2026-03-12'
  priority: P2
  type: Refactor
  status: in-progress
  issue: '#669'
  last_synced: '2026-03-14T15:59:43Z'
  plan: plan/tasks-35-backlog-cli-dedup-followup-1.md
---

## Story

As a **maintainer of the codebase**, I want to **replace remaining duplicated dict-based functions in backlog.py with core imports** so that **the code is cleaner and more maintainable**.

## Description

Follow-up from #611 dedup: 7 functions in backlog.py still have local implementations rather than delegating to backlog_core equivalents: _find_fuzzy_duplicates, _build_issue_body_from_file, items_needing_issues, items_with_issues, _parse_issue_selector, _issue_to_local_fields, _fetch_open_issues_by_title. Each should be evaluated for migration to core or adapter wrapping.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Code review followup from #611
- **Priority**: P2
- **Added**: 2026-03-12
- **Research questions**: None
