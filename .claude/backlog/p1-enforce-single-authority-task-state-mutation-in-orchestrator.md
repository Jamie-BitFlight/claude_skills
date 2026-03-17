---
name: Enforce single-authority task state mutation in orchestrator
description: "Currently, task state can be mutated by three independent paths: (1) the orchestrator Claude session directly edits task files when reading ready-tasks and dispatching, (2) task_status_hook.py updates status on SubagentStop, and (3) start-task skill sets IN PROGRESS and adds Started timestamp. There is no canonical authority — any of these can write conflicting state.\n\nSymphony's model: the orchestrator is the *only* component that mutates scheduling state. Workers report outcomes back; the orchestrator converts them into explicit state transitions. This prevents duplicate dispatch and makes state auditable.\n\n**Proposed changes:**\n- Audit all write paths to task files: list every location in start-task, task_status_hook.py, implementation_manager.py, and the orchestrator prompt where task status fields are written.\n- Define which component owns each field: status, Started, Completed, LastActivity, RetryCount, RetryAfter, LastFailureReason.\n- Refactor so that status transitions (NOT STARTED → IN PROGRESS, IN PROGRESS → COMPLETE/BLOCKED) are only performed by task_status_hook.py or implementation_manager.py — never by the orchestrator Claude session editing files directly.\n- Add a guard in implementation_manager.py that detects dual-write: if a task is already IN PROGRESS when dispatch is attempted, skip it with a warning rather than dispatching a second agent.\n\n**Acceptance criteria:**\n- No task status field is written by the orchestrator's direct Edit calls.\n- Dual-dispatch guard is present and tested: two concurrent ready-task queries do not produce two agents for the same task.\n- Component ownership of each task metadata field is documented in TASK_FILE_FORMAT.md."
metadata:
  topic: enforce-single-authority-task-state-mutation-in-orchestrator
  source: OpenAI Symphony SPEC.md §7 Coordination Layer — orchestrator is the single authoritative authority for in-memory state; all worker outcomes are routed through it, preventing duplicate dispatch
  added: '2026-03-06'
  priority: completed
  type: Refactor
  status: done
  issue: '#451'
  last_synced: '2026-03-06T05:00:53Z'
  groomed: '2026-03-06'
  plan: plan/tasks-24-enforce-single-authority-task-state.md
---

## Groomed (2026-03-06)

## Groomed

**Reproducibility**: Confirmed by source audit. Three independent write paths for task metadata:
1. `start-task` SKILL.md step 3 — agent directly edits YAML frontmatter (`status: in-progress`, `started:` timestamp) via Edit calls
2. `task_status_hook.py` SubagentStop — sets `status: complete`, `completed:` timestamp
3. `task_status_hook.py` PostToolUse — sets `last_activity:` timestamp

**Resources**:
- `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` — hook script
- `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` — CLI tool (read-only today)
- `plugins/python3-development/skills/implementation-manager/scripts/task_format.py` — shared YAML utilities
- `.claude/skills/start-task/SKILL.md` — instructs agent to directly edit task files
- `.claude/docs/TASK_FILE_FORMAT.md` — Authorized Writers section partially documents ownership

**Dependencies**: None external.

**Blockers**: None.

**Effort estimate**: Medium. Changes to implementation_manager.py (new claim-task command), start-task SKILL.md (use CLI instead of direct Edit), TASK_FILE_FORMAT.md (component ownership table), task_status_hook.py (no change needed for core, possibly tests).

**RT-ICA**: APPROVED. All source files exist and confirm the problem. Dual-dispatch guard is missing — `get_ready_tasks()` returns NOT_STARTED tasks without checking for concurrent dispatch.

**Field ownership map** (current):

| Field | Current Writer | Target Writer |
|-------|---------------|---------------|
| status (→ in-progress) | start-task agent (direct Edit) | implementation_manager.py claim-task |
| started | start-task agent (direct Edit) | implementation_manager.py claim-task |
| status (→ complete) | task_status_hook.py SubagentStop | task_status_hook.py (unchanged) |
| completed | task_status_hook.py SubagentStop | task_status_hook.py (unchanged) |
| last_activity | task_status_hook.py PostToolUse | task_status_hook.py (unchanged) |