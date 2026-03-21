---
name: Fix wrong exception type in test_atomic_write_cleans_up_temp_file_on_failure
description: In packages/sam_schema/, test_writers_new.py::TestAtomicWriteSafety::test_atomic_write_cleans_up_temp_file_on_failure asserts PermissionError but the implementation raises OSError. This mismatch causes uv run pytest packages/sam_schema/ to exit non-zero. This is a pre-existing bug that predates the deduplicate-agents-phase4 work — the test assertion does not match the exception type the implementation actually raises.
metadata:
  topic: fix-wrong-exception-type-in-testatomicwritecleansuptempfileo
  source: Agent task — auto-derived from task description (pre-existing bug, predates deduplicate-agents-phase4)
  added: '2026-03-20'
  priority: P1
  type: Feature
  status: needs-grooming
  plan: plan/P779-deduplicate-agents-phase4-followup-1.yaml
  issue: '#936'
  last_synced: '2026-03-21T03:45:01Z'
---

## Story

As a **developer using Claude Code skills**, I want to **fix wrong exception type in test_atomic_write_cleans_up_temp_file_on_failure** so that **the tooling becomes more capable and complete**.

## Description

In packages/sam_schema/, test_writers_new.py::TestAtomicWriteSafety::test_atomic_write_cleans_up_temp_file_on_failure asserts PermissionError but the implementation raises OSError. This mismatch causes uv run pytest packages/sam_schema/ to exit non-zero. This is a pre-existing bug that predates the deduplicate-agents-phase4 work — the test assertion does not match the exception type the implementation actually raises.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Agent task — auto-derived from task description (pre-existing bug, predates deduplicate-agents-phase4)
- **Priority**: P1
- **Added**: 2026-03-20
- **Research questions**: None
