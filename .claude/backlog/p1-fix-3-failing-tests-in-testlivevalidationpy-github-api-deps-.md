---
name: Fix 3 failing tests in test_live_validation.py (GitHub API deps + KeyError)
description: "test_live_validation.py has 3 tests failing due to GitHub API dependencies and cascading `KeyError: 'item_title'`. Tests need proper mocking or fixture updates to work without live GitHub access."
metadata:
  topic: fix-3-failing-tests-in-testlivevalidationpy-github-api-deps-
  source: 'PR #561 code review — pre-existing issue'
  added: '2026-03-10'
  priority: P1
  type: Bug
  status: needs-grooming
  issue: '#564'
  last_synced: '2026-03-14T15:59:50Z'
---

## Story

As a **developer relying on this plugin**, I want to **fix 3 failing tests in test_live_validation.py (github api deps + keyerror)** so that **the tool works correctly and reliably**.

## Description

test_live_validation.py has 3 tests failing due to GitHub API dependencies and cascading `KeyError: 'item_title'`. Tests need proper mocking or fixture updates to work without live GitHub access.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: PR #561 code review — pre-existing issue
- **Priority**: P1
- **Added**: 2026-03-10
- **Research questions**: None
