---
name: 'development-harness: Remove hardcoded machine path and fix version drift'
description: Contains a hardcoded machine-specific path (likely `/home/user/...` or similar) that won't work on other systems. Version references have drifted from actual tool versions. Role table has inconsistencies between documented and actual roles.
metadata:
  topic: development-harness-remove-hardcoded-machine-path-and-fix-ve
  source: Plugin code review session 2026-02-21
  added: '2026-02-21'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#97'
  last_synced: '2026-03-12T12:48:56Z'
---

## Story

As a **developer using Claude Code skills**, I want to **development-harness: remove hardcoded machine path and fix version drift** so that **the tooling becomes more capable and complete**.

## Description

Contains a hardcoded machine-specific path (likely `/home/user/...` or similar) that won't work on other systems. Version references have drifted from actual tool versions. Role table has inconsistencies between documented and actual roles.

## Files

`plugins/development-harness/` (SKILL.md and reference files)

## Context

- **Source**: Plugin code review session 2026-02-21
- **Priority**: P2
- **Added**: 2026-02-21
- **Research questions**: None
