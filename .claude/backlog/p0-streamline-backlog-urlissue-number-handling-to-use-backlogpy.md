---
name: Streamline backlog URL/issue-number handling to use backlog.py instead of gh CLI
description: "Skills (groom-backlog-item, work-backlog-item) and backlog.py should parse GitHub issue URLs (e.g., https://github.com/Jamie-BitFlight/claude_skills/issues/249) and bare issue numbers (e.g., 249 or #249) directly, using backlog.py's own HTTP/API logic instead of requiring gh CLI installation. Currently, every time an issue URL or number is given, the system tries gh CLI, fails, installs gh, checks info using gh, then starts work. This should be one step. Success: one-step issue lookup with no gh dependency for reading/viewing issues."
metadata:
  topic: streamline-backlog-urlissue-number-handling-to-use-backlogpy
  source: User request
  added: '2026-02-28'
  priority: completed
  type: Feature
  status: done
  issue: '#300'
  last_synced: '2026-02-28T16:55:11Z'
---

## Story

As a **developer using Claude Code skills**, I want to **streamline backlog url/issue-number handling to use backlog.py instead of gh cli** so that **the tooling becomes more capable and complete**.

## Description

Skills (groom-backlog-item, work-backlog-item) and backlog.py should parse GitHub issue URLs (e.g., https://github.com/Jamie-BitFlight/claude_skills/issues/249) and bare issue numbers (e.g., 249 or #249) directly, using backlog.py's own HTTP/API logic instead of requiring gh CLI installation. Currently, every time an issue URL or number is given, the system tries gh CLI, fails, installs gh, checks info using gh, then starts work. This should be one step. Success: one-step issue lookup with no gh dependency for reading/viewing issues.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: User request
- **Priority**: P0
- **Added**: 2026-02-28
- **Research questions**: None