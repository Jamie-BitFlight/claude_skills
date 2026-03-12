---
name: Fix missing _status key in backlog_item_to_display_dict adapter
description: 'The backlog_item_to_display_dict adapter in backlog.py omits the _status key, but _dict_to_backlog_item_fields reads d.get("_status"). This creates a latent data loss risk in round-trip conversions. Fix: add "_status": item.status to the output dict.'
metadata:
  topic: fix-missing-status-key-in-backlogitemtodisplaydict-adapter
  source: 'Code review followup from #611'
  added: '2026-03-12'
  priority: P2
  type: Bug
  status: needs-grooming
  issue: '#670'
  last_synced: '2026-03-12T12:47:27Z'
  plan: plan/tasks-36-backlog-cli-dedup-followup-2.md
---

## Story

As a **developer relying on this plugin**, I want to **fix missing _status key in backlog_item_to_display_dict adapter** so that **the tool works correctly and reliably**.

## Description

The backlog_item_to_display_dict adapter in backlog.py omits the _status key, but _dict_to_backlog_item_fields reads d.get("_status"). This creates a latent data loss risk in round-trip conversions. Fix: add "_status": item.status to the output dict.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Code review followup from #611
- **Priority**: P2
- **Added**: 2026-03-12
- **Research questions**: None
