# Improvement Proposals: Cursor Cookbook

**Research entry**: ./research/agent-frameworks/cursor-cookbook.md
**Generated**: 2026-05-05
**Patterns assessed**: 5
**Backlog items created**: 2 (issues: #2143, #2144)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 2

---

## Improvement 1: Persisted task results enabling parent-output injection into child task prompts

**Source pattern**: "Automatically stitches upstream output into child task prompts (2,000-char snippet of parent results)" — Key Features / DAG Task Runner section, and "Parent Result Injection: Stitching upstream output (2,000-char snippets) into child prompts provides context without full re-description — reduces token overhead in multi-turn scenarios" — Patterns Worth Adopting #2
**Local system**: plugins/development-harness/sam_schema/core/models.py (Task model), plugins/development-harness/skills/start-task/SKILL.md
**Confidence**: High
**Impact**: High
**Backlog**: #2143 created

### Current state

The `Task` Pydantic model at `plugins/development-harness/sam_schema/core/models.py:114` defines fields for status, dependencies, timestamps, content (description/objective/requirements), and `handoff: str = ""` (line 210), but has no field that captures the structured **output or result summary** of a completed task in a form retrievable by downstream tasks. When `start-task` (at `plugins/development-harness/skills/start-task/SKILL.md:43-72`) loads a task assignment, it reads `plan.goal`, `plan.context`, and the task itself via `sam_task(action='read')`, plus the architect spec via `artifact_read(issue_number=N, artifact_type="architect")`. There is no step that retrieves the completed-state output of dependency tasks (`task.dependencies`) and injects a summary snippet into the new agent's prompt. Each task agent therefore re-derives or re-reads what its parents produced from scratch, or relies on filesystem inspection of git diffs without a structured handoff.

### Target state

The `Task` model gains a `result_summary: str = Field(default="", max_length=N)` field (or analogous) populated by the `task_status_hook.py` SubagentStop handler (or by an explicit `sam_task(action='state', status='complete', result_summary=...)` call) when a task transitions to `complete`. The `start-task` workflow at step 1a or 2a inserts a new step that reads the `result_summary` of every entry in `task.dependencies` via `sam_task(action='read')` and prepends a "Parent Task Outputs" section to the agent's working context with each truncated to a configurable byte budget (e.g. 2000 chars per parent, matching the Cursor pattern). When dependencies are absent or `result_summary` is empty, the section is omitted (backward compatible).

### Measurable signal

After implementation, run:

```bash
uv run python -c "from sam_schema.core.models import Task; t = Task(id='T01', title='x', status='complete', result_summary='foo'); print(t.model_dump()['result-summary'])"
```

Output includes `result-summary: foo`. Then in a SAM plan with two tasks where T02 depends on T01: dispatching T02 via `start-task` produces an agent prompt whose context includes a section labeled "Parent Task Outputs" containing T01's `result_summary` truncated to the configured limit. Verify by reading the JSONL session file for the T02 agent and grep for the parent-output section header.

---

## Improvement 2: Failed terminal status with automatic downstream task skipping

**Source pattern**: "Includes timeout protection, automatic downstream task skipping on parent failure, graceful signal handling" — Key Features / DAG Task Runner section, and "Error Propagation: Automatic downstream task skipping on parent failure prevents cascading failures and wasted computation" — Patterns Worth Adopting #5
**Local system**: plugins/development-harness/sam_schema/core/models.py (TaskStatus enum), plugins/development-harness/sam_schema/core/dependencies.py (TERMINAL_STATUSES, get_ready_tasks)
**Confidence**: High
**Impact**: High
**Backlog**: #2144 created

### Current state

`TaskStatus` at `plugins/development-harness/sam_schema/core/models.py:49-57` defines six values: `not-started`, `in-progress`, `complete`, `blocked`, `deferred`, `skipped`. There is no `failed` value. `TERMINAL_STATUSES` at `plugins/development-harness/sam_schema/core/dependencies.py:15` is `frozenset({COMPLETE, DEFERRED, SKIPPED})`. A task whose execution fails has no canonical destination status — the orchestrator either leaves it `in-progress` (then queries surface it as still active), marks it `blocked` (which is non-terminal, so dependents are not unblocked), or manually edits to `skipped` (which falsely signals "intentionally skipped"). Because no status can mean "failed and downstream should not run", `get_ready_tasks()` (`dependencies.py:67-92`) cannot tell a downstream task to auto-skip when its parent has failed. The agent for the dependent task will not be dispatched (parent never enters TERMINAL_STATUSES), but the plan also never makes forward progress and the dependents are not flagged as unreachable.

### Target state

`TaskStatus` adds a `FAILED = "failed"` value. `TERMINAL_STATUSES` is split into two sets:

- `SUCCESSFUL_STATUSES = frozenset({COMPLETE, DEFERRED})`
- `TERMINAL_STATUSES = frozenset({COMPLETE, DEFERRED, SKIPPED, FAILED})` (kept for cycle/readiness checks)

`DependencyResolver` gains a `mark_downstream_skipped(failed_task_id: str) -> list[str]` method that walks the transitive dependents of a failed task, sets each to `SKIPPED` with a `reason` like "skipped: upstream {task_id} failed", and returns the list of newly-skipped task IDs. The `task_status_hook.py` SubagentStop handler (or `sam_task(action='state', status='failed')`) calls this on transition to `failed`. `get_ready_tasks()` continues to require dependencies be in `SUCCESSFUL_STATUSES` — so an auto-skipped task is itself terminal and never dispatched.

### Measurable signal

Run:

```bash
uv run pytest plugins/development-harness/sam_schema/tests/ -k "failed_status or downstream_skip"
```

A test passes that creates a 3-task plan T01 -> T02 -> T03, transitions T01 to `failed`, calls the new resolver method, and asserts T02 and T03 both have `status="skipped"` with `reason` containing "upstream T01 failed". A second assertion: `get_ready_tasks()` returns an empty list. The string `"failed"` appears in `TaskStatus` and `models.py` line range now contains a `FAILED = "failed"` member.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Streaming task state visualization (PENDING -> RUNNING -> FINISHED) with token-by-token output to a canvas | Medium | The local system has `task_status_hook.py` updating `LastActivity` timestamps and `dispatch_wave_status` for batch progress, plus `agentskill-kaizen:transcript-analyst` for session inspection. Whether token-stream visualization to a unified canvas would materially improve orchestrator decision-making, vs. the existing observability hooks, requires a documented case where lack of token-level visibility caused a missed stall or wrong dispatch choice. The Cursor pattern is UX-oriented (Cursor Canvas), and Claude Code's terminal-first orchestrator does not have an obvious analog target file to write to. Raising confidence would require: (a) a specific user-story where token-level visibility blocks a decision, or (b) a chosen rendering surface in this repo. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| CLI runtime model selection mapping task complexity (HIGH/MED/LOW) to specific AI models | Already covered. `.claude/rules/model-selection.md` (lines 3, 38) defines per-agent model selection by cognitive requirement (haiku/sonnet/opus) and orthogonal `--effort` tier (low/medium/high/max) propagated as `CLAUDE_CODE_EFFORT_LEVEL`. The local mapping is per-agent + per-effort rather than per-task-complexity, which is a deliberate design choice (the agent owns the cognitive contract, not the task). The Cursor approach inverts this — and adopting it would weaken the agent-as-specialist principle documented in CLAUDE.md. |
| DAG-based task decomposition with topological sorting and parallel execution of independent tasks | Already covered. `plugins/development-harness/sam_schema/core/dependencies.py:67-92` implements `get_ready_tasks()` which returns all tasks with terminal-status dependencies (the topological frontier), sorted by priority. `plugins/development-harness/skills/implement-feature/SKILL.md:84-94` dispatches the entire ready batch in parallel via `TeamCreate`. The Kahn-algorithm equivalent is implemented and used. |

---
