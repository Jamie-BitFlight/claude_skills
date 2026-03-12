---
name: 'Fix broken import in test_backlog_gh_first.py (ModuleNotFoundError: state_handler)'
description: "test_backlog_gh_first.py has a broken import — `ModuleNotFoundError: No module named 'state_handler'` — which prevents the entire test file from running. The module was likely renamed or moved. Fix the import to match the current module location while preserving test design intent."
metadata:
  topic: fix-broken-import-in-testbacklogghfirstpy-modulenotfounderro
  source: 'PR #561 code review — pre-existing issue'
  added: '2026-03-10'
  priority: P1
  type: Bug
  status: needs-grooming
  issue: '#563'
  last_synced: '2026-03-12T12:47:37Z'
---

## Story

As a **developer relying on this plugin**, I want to **fix broken import in test_backlog_gh_first.py (modulenotfounderror: state_handler)** so that **the tool works correctly and reliably**.

## Description

test_backlog_gh_first.py has a broken import — `ModuleNotFoundError: No module named 'state_handler'` — which prevents the entire test file from running. The module was likely renamed or moved. Fix the import to match the current module location while preserving test design intent.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: PR #561 code review — pre-existing issue
- **Priority**: P1
- **Added**: 2026-03-10
- **Research questions**: None
