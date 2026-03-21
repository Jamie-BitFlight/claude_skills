---
name: SubagentStop hook does not mark SAM tasks complete when agents launched via Agent tool
description: 'The SubagentStop hook (task_status_hook.py) does not fire when agents are launched via the Agent tool during /implement-feature. Tasks remain in-progress after agent completion. The orchestrator must manually call sam_state to mark tasks complete. Observed across multiple task plans in session 2026-03-21: T01-T03 for issue 919, T01-T09 for issue 920, T1 for issue 927, T01-T04 for issue 938.'
metadata:
  topic: subagentstop-hook-does-not-mark-sam-tasks-complete-when-agen
  source: Session observation — 2026-03-21 milestone orchestration implementation
  added: '2026-03-21'
  priority: P1
  type: Bug
  status: needs-grooming
  issue: '#950'
  last_synced: '2026-03-21T08:07:19Z'
---

## Story

As a **developer relying on this plugin**, I want to **subagentstop hook does not mark sam tasks complete when agents launched via agent tool** so that **the tool works correctly and reliably**.

## Description

The SubagentStop hook (task_status_hook.py) does not fire when agents are launched via the Agent tool during /implement-feature. Tasks remain in-progress after agent completion. The orchestrator must manually call sam_state to mark tasks complete. Observed across multiple task plans in session 2026-03-21: T01-T03 for issue 919, T01-T09 for issue 920, T1 for issue 927, T01-T04 for issue 938.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation — 2026-03-21 milestone orchestration implementation
- **Priority**: P1
- **Added**: 2026-03-21
- **Research questions**: None
