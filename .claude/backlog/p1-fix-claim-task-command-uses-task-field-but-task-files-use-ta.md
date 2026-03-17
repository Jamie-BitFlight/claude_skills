---
name: 'Fix claim-task command: uses `task` field but task files use `task_id`'
description: "In `implementation_manager.py`, `_try_claim_part()` at line 1295 checks `fm.get(\"task\")` but the YAML frontmatter format uses `task_id:` as the field name (not `task:`). This causes `claim-task` to always return `{\"claimed\": false, \"reason\": \"task-not-found\"}` for any task in a monolithic task file, even when the task ID exists.\n\nThe `status` and `ready-tasks` commands parse tasks correctly because they use a different code path. Only `claim-task` is broken.\n\nFix: change line 1295 from `fm.get(\"task\")` to `fm.get(\"task_id\") or fm.get(\"task\")` to handle both field names, or standardize on `task_id` across all parsing paths.\n\nDiscovered during execution of T5 in `plan/tasks-2-migrate-sam-task-github-subissues.md` on 2026-03-06."
metadata:
  topic: fix-claim-task-command-uses-task-field-but-task-files-use-ta
  source: Observed during T5 execution in migrate-sam-task-github-subissues feature
  added: '2026-03-06'
  priority: completed
  type: Bug
  status: done
  issue: '#497'
  last_synced: '2026-03-07T18:29:28Z'
---

## Story

As a **developer relying on this plugin**, I want to **fix claim-task command: uses `task` field but task files use `task_id`** so that **the tool works correctly and reliably**.

## Description

In `implementation_manager.py`, `_try_claim_part()` at line 1295 checks `fm.get("task")` but the YAML frontmatter format uses `task_id:` as the field name (not `task:`). This causes `claim-task` to always return `{"claimed": false, "reason": "task-not-found"}` for any task in a monolithic task file, even when the task ID exists.

The `status` and `ready-tasks` commands parse tasks correctly because they use a different code path. Only `claim-task` is broken.

Fix: change line 1295 from `fm.get("task")` to `fm.get("task_id") or fm.get("task")` to handle both field names, or standardize on `task_id` across all parsing paths.

Discovered during execution of T5 in `plan/tasks-2-migrate-sam-task-github-subissues.md` on 2026-03-06.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Observed during T5 execution in migrate-sam-task-github-subissues feature
- **Priority**: P1
- **Added**: 2026-03-06
- **Research questions**: None