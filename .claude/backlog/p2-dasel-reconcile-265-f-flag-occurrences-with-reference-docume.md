---
name: 'dasel: Reconcile 265 `-f` flag occurrences with reference documentation'
description: Reference documentation states dasel uses a specific flag pattern, but 265 occurrences of the `-f` flag across the skill contradict this documentation. The hook file exists on disk but is not registered in the plugin manifest (`plugin.json`). Run `auto_sync_manifests.py --reconcile` to fix manifest drift, and audit `-f` flag usage against official dasel documentation.
metadata:
  topic: dasel-reconcile-265-f-flag-occurrences-with-reference-docume
  source: Plugin code review session 2026-02-21
  added: '2026-02-21'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#95'
  last_synced: '2026-03-21T08:09:03Z'
---

## Story

As a **developer using Claude Code skills**, I want to **dasel: reconcile 265 `-f` flag occurrences with reference documentation** so that **the tooling becomes more capable and complete**.

## Description

Reference documentation states dasel uses a specific flag pattern, but 265 occurrences of the `-f` flag across the skill contradict this documentation. The hook file exists on disk but is not registered in the plugin manifest (`plugin.json`). Run `auto_sync_manifests.py --reconcile` to fix manifest drift, and audit `-f` flag usage against official dasel documentation.

## Files

- `plugins/dasel/` (skill files with `-f` flag usage)
- `plugins/dasel/.claude-plugin/plugin.json` (missing hook registration)

## Context

- **Source**: Plugin code review session 2026-02-21
- **Priority**: P2
- **Added**: 2026-02-21
- **Research questions**: None
