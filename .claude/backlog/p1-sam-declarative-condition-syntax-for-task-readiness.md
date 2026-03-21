---
name: 'SAM: Declarative condition syntax for task readiness'
description: "**Current state**: Task readiness in the SAM system is determined solely by dependency graph resolution: a task is \"ready\" when its status is NOT STARTED and all dependency tasks have status COMPLETE. There is no mechanism to express conditional readiness based on observable system state (e.g., \"file X exists\", \"command Y exits 0\", \"field Z in config has value V\"). Acceptance criteria in task files are free-text prose that agents interpret; they are not machine-evaluable conditions.\n\nFile: `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` -- the `get_ready_tasks` function checks only `status` and `dependencies` fields. No condition evaluation exists.\n\n**Target state**: Task YAML frontmatter supports an optional `conditions` field containing a list of 3-token expressions in the format `scope.field op value` (e.g., `file.plan/architect-auth.md exists true`, `command.uv_run_tests exit_code 0`). The `sam ready` command evaluates these conditions alongside dependency checks. A task is \"ready\" only when both dependency graph and all conditions pass. The condition evaluator is a standalone function that can be tested independently.\n\n**Measurable signal**: Run: `uv run sam ready P{N}` on a plan where a task has `conditions: [\"file.some/path.md exists true\"]` -- output includes or excludes the task based on whether the file exists. The `conditions` field is documented in `.claude/docs/TASK_FILE_FORMAT.md`."
metadata:
  topic: sam-declarative-condition-syntax-for-task-readiness
  source: 'Research entry: ./research/developer-tools/tori-cli.md -- pattern: 3-token condition format for task conditions'
  added: '2026-03-18'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#781'
  last_synced: '2026-03-21T03:45:16Z'
---

## Story

As a **developer using Claude Code skills**, I want to **sam: declarative condition syntax for task readiness** so that **the tooling becomes more capable and complete**.

## Description

**Current state**: Task readiness in the SAM system is determined solely by dependency graph resolution: a task is "ready" when its status is NOT STARTED and all dependency tasks have status COMPLETE. There is no mechanism to express conditional readiness based on observable system state (e.g., "file X exists", "command Y exits 0", "field Z in config has value V"). Acceptance criteria in task files are free-text prose that agents interpret; they are not machine-evaluable conditions.

File: `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` -- the `get_ready_tasks` function checks only `status` and `dependencies` fields. No condition evaluation exists.

**Target state**: Task YAML frontmatter supports an optional `conditions` field containing a list of 3-token expressions in the format `scope.field op value` (e.g., `file.plan/architect-auth.md exists true`, `command.uv_run_tests exit_code 0`). The `sam ready` command evaluates these conditions alongside dependency checks. A task is "ready" only when both dependency graph and all conditions pass. The condition evaluator is a standalone function that can be tested independently.

**Measurable signal**: Run: `uv run sam ready P{N}` on a plan where a task has `conditions: ["file.some/path.md exists true"]` -- output includes or excludes the task based on whether the file exists. The `conditions` field is documented in `.claude/docs/TASK_FILE_FORMAT.md`.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Research entry: ./research/developer-tools/tori-cli.md -- pattern: 3-token condition format for task conditions
- **Priority**: P1
- **Added**: 2026-03-18
- **Research questions**: None
