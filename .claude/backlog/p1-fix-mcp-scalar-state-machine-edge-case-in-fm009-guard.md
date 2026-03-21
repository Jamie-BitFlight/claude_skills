---
name: Fix mcp scalar state-machine edge case in FM009 guard
description: "The FM009 state machine in `plugins/plugin-creator/scripts/plugin_validator.py` sets `current_top_level_key = 'mcp'` for scalar forms (`mcp: null`, `mcp: false`) just as it does for block mappings. Scalar forms have no indented children, so any subsequent indented line belonging to a different block key is incorrectly treated as inside `mcp:` and skipped by the ecosystem guard. The fix must distinguish scalar vs. block top-level lines so that `current_top_level_key` is not carried forward after a scalar `mcp:` line. A new unit test exercising `mcp: null` followed by a Claude Code field with a colon must be added, and all 26 existing tests must continue to pass."
metadata:
  topic: fix-mcp-scalar-state-machine-edge-case-in-fm009-guard
  source: Agent task — code review follow-up from plan/tasks-26-multi-ecosystem-plugin-creator-followup-2.md
  added: '2026-03-06'
  priority: P1
  type: Bug
  status: needs-grooming
  plan: plan/tasks-26-multi-ecosystem-plugin-creator-followup-2.md
  issue: '#517'
  last_synced: '2026-03-21T08:08:16Z'
---

## Story

As a **developer using Claude Code skills**, I want to **fix mcp scalar state-machine edge case in fm009 guard** so that **the tooling becomes more capable and complete**.

## Description

The FM009 state machine in `plugins/plugin-creator/scripts/plugin_validator.py` sets `current_top_level_key = 'mcp'` for scalar forms (`mcp: null`, `mcp: false`) just as it does for block mappings. Scalar forms have no indented children, so any subsequent indented line belonging to a different block key is incorrectly treated as inside `mcp:` and skipped by the ecosystem guard. The fix must distinguish scalar vs. block top-level lines so that `current_top_level_key` is not carried forward after a scalar `mcp:` line. A new unit test exercising `mcp: null` followed by a Claude Code field with a colon must be added, and all 26 existing tests must continue to pass.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Agent task — code review follow-up from plan/tasks-26-multi-ecosystem-plugin-creator-followup-2.md
- **Priority**: P1
- **Added**: 2026-03-06
- **Research questions**: None
