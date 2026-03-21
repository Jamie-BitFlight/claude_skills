---
name: 'Impact Radius findings must become plan tasks or documented exclusions — 39 of 72 files had no task in #719'
description: "The grooming process produces an Impact Radius section listing every file affected by a change. The planning process (swarm-task-planner + plan-validator) creates tasks and validates acceptance criteria coverage. But nothing verifies that every Impact Radius item either has a task covering it or an explicit documented reason for exclusion.\n\nObserved on #719: Impact Radius identified 72 affected files. The swarm-task-planner created 14 tasks covering only the 7 primary components. 39 files had no task — including the code-reviewer agent (a task file producer), 6 backlog_core consumers, 16 agent instruction files, and 8 documentation files. The plan-validator checked that acceptance criteria mapped to tasks, but the acceptance criteria only listed the 7 primary components — the Impact Radius was not checked.\n\nThe gap is between grooming (which discovers affected systems) and planning (which creates tasks). The Ecosystem Completeness Checklist at the bottom of every Impact Radius section is never verified against the task plan.\n\nWhat success looks like: the plan-validator agent checks that every Impact Radius item in the groomed backlog item either (a) has a task in the plan, (b) is covered by a task that handles its category (e.g., T14 \"sync development-harness\" covers all harness agent copies), or (c) has an explicit exclusion note in the plan explaining why no task is needed. Items classified as MAYBE in the Impact Radius get a verification task to confirm whether they need changes.\n\nHow you'll know it's working: plan validation on a plan like #719 would report \"39 Impact Radius items have no covering task — BLOCKED until tasks or exclusions are added.\""
metadata:
  topic: impact-radius-findings-must-become-plan-tasks-or-documented-
  source: 'Session observation — 39 of 72 Impact Radius files had no task in #719 plan (2026-03-15)'
  added: '2026-03-15'
  priority: P1
  type: Bug
  status: needs-grooming
  issue: '#743'
  last_synced: '2026-03-21T03:45:23Z'
---

## Story

As a **developer relying on this plugin**, I want to **impact radius findings must become plan tasks or documented exclusions — 39 of 72 files had no task in #719** so that **the tool works correctly and reliably**.

## Description

The grooming process produces an Impact Radius section listing every file affected by a change. The planning process (swarm-task-planner + plan-validator) creates tasks and validates acceptance criteria coverage. But nothing verifies that every Impact Radius item either has a task covering it or an explicit documented reason for exclusion.

Observed on #719: Impact Radius identified 72 affected files. The swarm-task-planner created 14 tasks covering only the 7 primary components. 39 files had no task — including the code-reviewer agent (a task file producer), 6 backlog_core consumers, 16 agent instruction files, and 8 documentation files. The plan-validator checked that acceptance criteria mapped to tasks, but the acceptance criteria only listed the 7 primary components — the Impact Radius was not checked.

The gap is between grooming (which discovers affected systems) and planning (which creates tasks). The Ecosystem Completeness Checklist at the bottom of every Impact Radius section is never verified against the task plan.

What success looks like: the plan-validator agent checks that every Impact Radius item in the groomed backlog item either (a) has a task in the plan, (b) is covered by a task that handles its category (e.g., T14 "sync development-harness" covers all harness agent copies), or (c) has an explicit exclusion note in the plan explaining why no task is needed. Items classified as MAYBE in the Impact Radius get a verification task to confirm whether they need changes.

How you'll know it's working: plan validation on a plan like #719 would report "39 Impact Radius items have no covering task — BLOCKED until tasks or exclusions are added."

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation — 39 of 72 Impact Radius files had no task in #719 plan (2026-03-15)
- **Priority**: P1
- **Added**: 2026-03-15
- **Research questions**: None
