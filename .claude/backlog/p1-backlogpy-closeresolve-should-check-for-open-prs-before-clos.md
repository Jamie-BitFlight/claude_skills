---
name: backlog.py close/resolve should check for open PRs before closing issues
description: backlog.py close/resolve commands should check for open PRs linked to the issue and warn/block before closing. Currently the script closes issues without checking PR state, which can prematurely close issues that have in-flight work.
metadata:
  topic: backlogpy-closeresolve-should-check-for-open-prs-before-clos
  source: Session observation
  added: '2026-02-27'
  priority: completed
  type: Bug
  status: done
  issue: '#312'
---

## Story

As a **developer using Claude Code skills**, I want to **backlog.py close/resolve should check for open prs before closing issues** so that **the tooling becomes more capable and complete**.

## Description

backlog.py close/resolve commands should check for open PRs linked to the issue and warn/block before closing. Currently the script closes issues without checking PR state, which can prematurely close issues that have in-flight work.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation
- **Priority**: P1
- **Added**: 2026-02-27
- **Research questions**: None