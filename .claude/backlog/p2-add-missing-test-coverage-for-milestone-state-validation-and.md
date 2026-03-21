---
name: Add missing test coverage for milestone state validation and issue milestone resolution
description: 'Two test gaps found in code review: (1) list_milestones is missing a state validation test (list_issues has one but milestones does not), (2) list_issues milestone title resolution happy path has no test. Low risk since the code exists — only test coverage is absent.'
metadata:
  topic: add-missing-test-coverage-for-milestone-state-validation-and
  source: Code review 2026-03-20 — P782 follow-up from backlog-mcp-github-tools feature
  added: '2026-03-20'
  priority: P2
  type: Chore
  status: needs-grooming
  issue: '#918'
  last_synced: '2026-03-21T03:45:08Z'
  plan: plan/P782-backlog-mcp-github-tools-followup-2.yaml
---

## Story

As a **maintainer of the project infrastructure**, I want to **add missing test coverage for milestone state validation and issue milestone resolution** so that **the project infrastructure stays healthy**.

## Description

Two test gaps found in code review: (1) list_milestones is missing a state validation test (list_issues has one but milestones does not), (2) list_issues milestone title resolution happy path has no test. Low risk since the code exists — only test coverage is absent.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Code review 2026-03-20 — P782 follow-up from backlog-mcp-github-tools feature
- **Priority**: P2
- **Added**: 2026-03-20
- **Research questions**: None
