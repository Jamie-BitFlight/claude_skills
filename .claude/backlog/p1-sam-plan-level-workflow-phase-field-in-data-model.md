---
name: 'SAM: Plan-level workflow phase field in data model'
description: "**Current state**: The SAM workflow has three implicit phases (planning via `/add-new-feature`, execution via `/implement-feature`, quality gates via `/complete-implementation`) but no explicit plan-level phase field in the data model. Running `uv run sam status P{N}` returns task counts (`total_tasks`, `by_status`, `ready_tasks`, `blocked_tasks`, `completion_pct`) but does not report which workflow phase the plan is in. The orchestrator infers phase from task status counts (e.g., \"all tasks COMPLETE\" means ready for quality gates), but this inference is implicit and undocumented. File: `plugins/python3-development/skills/implement-feature/SKILL.md` — the Progress Loop section queries `sam status` and `sam ready` but has no mechanism to read or write a plan-level phase. File: `packages/sam_schema/` — no workflow phase field exists in the Plan model.\n\n**Target state**: The `sam_schema` Plan model includes an optional `phase` field with defined values: `planning`, `executing`, `quality-gates`, `complete`, `blocked`. The `sam status P{N}` output includes `\"phase\": \"executing\"` in its JSON response. The `/add-new-feature` skill sets phase to `planning` on plan creation. The `/implement-feature` skill sets phase to `executing` when entering the progress loop. The `/complete-implementation` skill sets phase to `quality-gates` on entry and `complete` on success.\n\n**Measurable signal**: Run `uv run sam status P{N}` on any active plan — output JSON contains a `phase` field with one of the defined values. Read any plan YAML file — frontmatter contains `phase: executing` (or equivalent). The `/implement-feature` SKILL.md references the phase field in its Progress Loop section."
metadata:
  topic: sam-plan-level-workflow-phase-field-in-data-model
  source: 'Research entry: ./research/research-agent-patterns/the-delegation.md — pattern: Agency State Machine (explicit phase transitions)'
  added: '2026-03-18'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#779'
  last_synced: '2026-03-21T08:07:36Z'
---

## Story

As a **developer using Claude Code skills**, I want to **sam: plan-level workflow phase field in data model** so that **the tooling becomes more capable and complete**.

## Description

**Current state**: The SAM workflow has three implicit phases (planning via `/add-new-feature`, execution via `/implement-feature`, quality gates via `/complete-implementation`) but no explicit plan-level phase field in the data model. Running `uv run sam status P{N}` returns task counts (`total_tasks`, `by_status`, `ready_tasks`, `blocked_tasks`, `completion_pct`) but does not report which workflow phase the plan is in. The orchestrator infers phase from task status counts (e.g., "all tasks COMPLETE" means ready for quality gates), but this inference is implicit and undocumented. File: `plugins/python3-development/skills/implement-feature/SKILL.md` — the Progress Loop section queries `sam status` and `sam ready` but has no mechanism to read or write a plan-level phase. File: `packages/sam_schema/` — no workflow phase field exists in the Plan model.

**Target state**: The `sam_schema` Plan model includes an optional `phase` field with defined values: `planning`, `executing`, `quality-gates`, `complete`, `blocked`. The `sam status P{N}` output includes `"phase": "executing"` in its JSON response. The `/add-new-feature` skill sets phase to `planning` on plan creation. The `/implement-feature` skill sets phase to `executing` when entering the progress loop. The `/complete-implementation` skill sets phase to `quality-gates` on entry and `complete` on success.

**Measurable signal**: Run `uv run sam status P{N}` on any active plan — output JSON contains a `phase` field with one of the defined values. Read any plan YAML file — frontmatter contains `phase: executing` (or equivalent). The `/implement-feature` SKILL.md references the phase field in its Progress Loop section.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Research entry: ./research/research-agent-patterns/the-delegation.md — pattern: Agency State Machine (explicit phase transitions)
- **Priority**: P1
- **Added**: 2026-03-18
- **Research questions**: None
