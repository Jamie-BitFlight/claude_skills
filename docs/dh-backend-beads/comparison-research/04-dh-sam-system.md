---
title: "DH SAM System — Comprehensive Reference"
date: "2026-05-14"
scope: "Full documentation of the SAM (Structured Agent-Managed) task plan system in the development-harness plugin, for use in designing a beads-based equivalent"
sources:
  - plugins/development-harness/sam_schema/core/models.py
  - plugins/development-harness/sam_schema/core/action_models.py
  - plugins/development-harness/sam_schema/core/dependencies.py
  - plugins/development-harness/sam_schema/core/task_backend.py
  - plugins/development-harness/sam_schema/core/context_backend.py
  - plugins/development-harness/sam_schema/server.py
  - plugins/development-harness/docs/TASK_FILE_FORMAT.md
  - plugins/development-harness/skills/start-task/SKILL.md
  - plugins/development-harness/skills/implement-feature/SKILL.md
  - plugins/development-harness/skills/task-decomposition/SKILL.md
  - plugins/development-harness/CLAUDE.md
  - plugins/development-harness/tests_sam/fixtures/pure_yaml_single.yaml
  - plugins/development-harness/tests_sam/fixtures/plan_with_bookends.yaml
  - plugins/development-harness/tests_sam/fixtures/t0_baseline_sample.yaml
  - plugins/development-harness/tests_sam/fixtures/tn_verification_sample.yaml
---

# DH SAM System — Comprehensive Reference

## 1. What SAM Is

SAM (Structured Agent-Managed) is the task plan system inside the `development-harness` plugin. It
provides a YAML-based plan format, three MCP tools for reading and writing plan state, a dependency
graph with readiness queries, and a session-scoped active-task parking mechanism. Plans are stored
outside the repo at `~/.dh/projects/{project-slug}/plan/` and accessed exclusively through the MCP
tools or the `uv run sam` CLI fallback — never via direct Read/Edit/Write tool calls.

The three public MCP tools are:

- `sam_plan` — plan-level CRUD plus list, status, ready-task queries, and incremental build flow
- `sam_task` — single-task read, claim, state transition, and field update
- `sam_active_task` — session-scoped active-task parking for agent state continuity

---

## 2. MCP Tool Reference

### 2.1 `sam_plan`

**Tool name**: `mcp__plugin_dh_sam__sam_plan`

**Signature**:

```text
sam_plan(config, plan_dir="plan", plan=None)
```

The `config` parameter is a discriminated union on the `action` field. The `plan` parameter is
required for read/status/ready/update/append_task/finalize; omitted for list/create.

**Actions**:

#### `read`

Returns all Plan-level fields for the given plan address. Returns `Plan` JSON with
`by_alias=True, exclude_none=True`. Does not return plan_id in the output dict.

```text
sam_plan(plan="P1", config={"action": "read"})
```

Response shape: Plan model fields (see Plan Schema section).

#### `create`

Creates a new plan file and returns the assigned plan ID.

```text
sam_plan(config={
  "action": "create",
  "slug": "auth-system",
  "goal": "Implement token-based authentication",
  "tasks": [{task_definition}, ...],
  "context": "Optional context prose",
  "issue": 42
})
```

- `slug` (required): short identifier; used to compose the filename `P{hex}-{slug}.yaml`
- `goal` (required): human-readable goal statement stored as `Plan.goal`
- `tasks` (default `[]`): list of `TaskDefinition` objects. Empty list enters `state="drafting"`.
- `context` (optional): stored as `Plan.context`
- `issue` (optional): GitHub issue number; when provided, auto-registers the plan as a
  `task-plan` artifact on the issue via `artifact_register`

Response: `{"plan_id": "Pc7d8e9f0", "task_count": 14, "plan_ref": "#42,Pc7d8e9f0"}`

#### `list`

Lists all plans with optional search and auto-pagination.

```text
sam_plan(config={"action": "list", "search": "auth", "offset": 0, "limit": null})
```

- `search`: case-insensitive substring filter across feature, description, and goal fields
- `offset`: zero-based index for pagination (default 0)
- `limit`: max items to return; when null, auto-calculates based on 4400-token budget (cl100k_base)

Response: paginated dict with `items`, `count`, `pagination`, `messages`, `warnings`, `errors`,
and optional `next_call` key. Each item: `{feature, goal, description, task_count, issue, plan_ref}`.

#### `status`

Returns plan-level progress summary including autonomy mode.

```text
sam_plan(plan="P1", config={"action": "status"})
```

Response: `{feature, total_tasks, by_status, ready_tasks, blocked_tasks, completion_pct, has_cycles, autonomy, state}`

When plan is in `state="drafting"`: returns a `PlanStatus` model with `state="drafting"` and zeroed/empty progress fields.

#### `ready`

Lists tasks ready for dispatch (status=not-started, all dependencies terminal).

```text
sam_plan(plan="P1", config={"action": "ready", "full": false})
```

- `full=false` (default): compact 7-field manifest per task: `{id, task, agent, skills, dependencies, status, priority}`
- `full=true`: full Task model dump (30+ fields)

When plan is in `state="drafting"`: returns a `ReadyTasksResult` model with `state="drafting"` and an empty `ready_tasks` list.

Response (compact): `{ready_tasks: [...], count: N, feature: "...", issue: 42, state: "ready"}`

#### `update`

Patches plan-level fields and/or sets the context field.

```text
sam_plan(plan="P1", config={
  "action": "update",
  "context": "New context prose",
  "set_fields_json": {"goal": "Updated goal", "issue": 42}
})
```

Response: `{"updated": true, "address": "P1"}`

#### `append_task`

Appends a single task to an existing plan. The plan must exist; it does not need to be in
`drafting` state but typically is when using the incremental build pattern.

```text
sam_plan(plan="P1", config={
  "action": "append_task",
  "task": {
    "id": "T5",
    "title": "Add rate limiting",
    "status": "not-started",
    "agent": "python-cli-architect",
    "dependencies": ["T3", "T4"],
    "priority": 3
  }
})
```

Single-writer constraint: concurrent `append_task` calls for the same plan are NOT safe. Callers
must serialize writes. Behavior under concurrent writes is undefined.

Response: `{"appended": true, "task_id": "T5"}`

#### `finalize`

Transitions a plan from `state="drafting"` to `state="ready"`, making it visible to the dispatch
loop. Only needed when the plan was created with `tasks=[]`.

```text
sam_plan(plan="P1", config={"action": "finalize"})
```

Response: `{"finalized": true, "state": "ready"}`

---

### 2.2 `sam_task`

**Tool name**: `mcp__plugin_dh_sam__sam_task`

**Signature**:

```text
sam_task(plan, task, config, plan_dir="plan")
```

Both `plan` and `task` are always required. The `config` discriminated union selects the operation.

**Actions**:

#### `read`

Returns a `TaskAssignment` — the plan-level context plus the specific task's fields. This is the
primary intake for agents about to execute a task: one call gives goal, shared context, AC, and
full task details.

```text
sam_task(plan="P1", task="T3", config={"action": "read"})
```

Response shape:

```json
{
  "plan-number": "Pc7d8e9f0",
  "plan-slug": "auth-system",
  "plan-goal": "Implement token-based authentication",
  "plan-context": "Context prose from context-gathering agent...",
  "plan-acceptance-criteria": "Free-form AC markdown...",
  "task": {
    "id": "T3",
    "title": "...",
    "status": "not-started",
    "agent": "...",
    "dependencies": [...],
    ...all other Task fields...
  }
}
```

#### `claim`

Attempts to transition a task from `not-started` to `in-progress`. Implements read-check-write;
concurrent claims result in exactly one succeeding.

```text
sam_task(plan="P1", task="T3", config={"action": "claim"})
```

Success: `{"claimed": true, "task_id": "T3", "started": "2026-05-14T10:00:00Z"}`

Failure: `{"claimed": false, "error": "Cannot claim task 'T3': expected status 'not-started' but found 'in-progress'."}`

Agents receiving `claimed: false` must STOP — do not attempt to implement the task.

#### `state`

Updates a task's status field. When status is set to `failed`, automatically cascades: all
downstream not-started tasks are transitioned to `skipped` and their `reason` field set to
`"skipped: upstream {task_id} failed"`.

```text
sam_task(plan="P1", task="T3", config={"action": "state", "status": "complete"})
```

Valid status values: `not-started`, `in-progress`, `complete`, `blocked`, `deferred`, `skipped`,
`failed`. Also accepts aliases: `done` → `complete`, `pending` → `not-started`, etc.
(See STATUS_MAP in models.py.)

Success: `{"id": "T3", "status": "complete"}`
With cascade: `{"id": "T3", "status": "failed", "skipped_downstream": ["T4", "T5"]}`

#### `update`

Patches task fields and/or appends a markdown section to the task body. All three sub-operations
are non-exclusive and may be combined in one call.

```text
sam_task(plan="P1", task="T3", config={
  "action": "update",
  "set_fields_json": {"priority": 1, "agent": "python-cli-architect"},
  "append_section": "Findings",
  "section_content": "The implementation required..."
})
```

- `set_fields_json`: dict of field=value pairs, validated through the Task Pydantic model
- `append_section`: heading name for the markdown section to append to the task body
- `section_content`: body text for the appended section (used with `append_section`)

Response: `{"updated": true, "address": "P1/T3"}`

---

### 2.3 `sam_active_task`

**Tool name**: `mcp__plugin_dh_sam__sam_active_task`

**Signature**:

```text
sam_active_task(config, session_id=None)
```

When `session_id` is None, uses the `"_default"` sentinel (suitable for single-agent scenarios).
Session scoping allows multiple concurrent agents to each park their own active task.

Context is stored at `~/.dh/projects/{project-slug}/context/active-task-{session_id}.json` by
the LocalContextBackend. The SubagentStop hook reads these files directly from the filesystem.

**Actions**:

#### `get`

Retrieves the active task context for the session.

```text
sam_active_task(config={"action": "get"}, session_id="abc123")
```

Response (set): `{"active_task": {task_file_path, task_id, parent_issue_number, session_id, feature_slug, started_at}}`
Response (not set): `{"active_task": null}`

#### `set`

Stores a task address as the active task for this session. Used immediately after a successful
`claim` to enable hook-driven status updates.

```text
sam_active_task(config={
  "action": "set",
  "plan": "P1",
  "task": "T3",
  "plan_dir": "plan",
  "parent_issue_number": 42
}, session_id="abc123")
```

- `plan`: plan address (e.g., `"P1"`)
- `task`: task ID (e.g., `"T3"`)
- `plan_dir`: plan directory sentinel (default `"plan"`) — stored for backend retrieval
- `parent_issue_number`: optional GitHub issue for the parent story; used by SubagentStop for sync

Response: `{"active_task": {ActiveTaskContext fields}}`

#### `update`

Updates fields on the currently active task without repeating the plan/task address. Raises
`ToolError` if no active task is set.

```text
sam_active_task(config={
  "action": "update",
  "set_fields_json": {"status": "in-progress"},
  "append_section": "Work Log",
  "section_content": "Completed auth module..."
}, session_id="abc123")
```

Response: `{"updated": true, "address": "Pc7d8e9f0/T3"}`

#### `clear`

Removes the active task context for the session.

```text
sam_active_task(config={"action": "clear"}, session_id="abc123")
```

Response: `{"cleared": true}` if context existed, `{"cleared": false}` if not set.

---

## 3. Plan YAML Schema

Plans are stored as single `.yaml` files (small plans, under 500 lines) or as a directory with a
`PLAN.yaml` plus per-task `.yaml` files (large plans). The authoritative model is
`sam_schema/core/models.py` `Plan` class.

### Plan-Level Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `plan-id` | `str` | no | null | Backend-assigned hex ID (e.g., `"Pc7d8e9f0"`). Persisted in YAML for survival across state-directory wipes. |
| `feature` | `str` | **yes** | — | Human-readable feature name (slug-like) |
| `version` | `str` | no | `"1.0"` | Schema version |
| `description` | `str` | no | `""` | Longer description of the plan |
| `state` | `str` | no | `"ready"` | Plan lifecycle state: `"drafting"` or `"ready"` |
| `goal` | `str` | no | null | One-sentence goal statement |
| `context` | `str` | no | null | Shared context narrative for all tasks; written by context-gathering agent |
| `acceptance-criteria` | `str` | no | null | Plan-level AC as free-form markdown |
| `acceptance-criteria-structured` | `list[AcceptanceCriterion]` | no | `[]` | Structured AC list for T0/TN verification; see Bookend section |
| `issue` | `str` | no | null | GitHub issue number (coerced to string; bare int in YAML is accepted) |
| `architecture` | `str` | no | null | Reference to architecture document |
| `feature-context` | `str` | no | null | Reference to feature-context document |
| `codebase-patterns` | `str` | no | null | Codebase patterns relevant to this plan |
| `tasks` | `list[Task]` | no | `[]` | All tasks in the plan |
| `source_path` | `Path` | no | null | Runtime-only: path to the YAML file |
| `backend-ref` | `str` | no | null | Override the default backend for this plan |
| `autonomy` | `str` | no | `"full_auto"` | Dispatch gating mode: `full_auto`, `checkpoint`, or `per_task` |

### Autonomy Modes

| Mode | Behavior |
|------|----------|
| `full_auto` | Dispatch all tasks without pausing; backward-compatible default |
| `checkpoint` | Pause for user confirmation after each dependency wave completes |
| `per_task` | Dispatch one task at a time via single Agent call; pause for confirmation before each |

### Minimal valid plan

```yaml
feature: auth-system
goal: "Implement token-based auth"
tasks:
  - id: T1
    title: Define auth data models
    status: not-started
```

### Full plan example

```yaml
feature: auth-system
version: "1.0"
description: |
  Authentication system with token-based auth and RBAC.
goal: "Deliver a production-ready auth API"
context: "Shared context from codebase analysis..."
acceptance-criteria: |
  - All endpoints require auth by default
  - Token expiry is configurable
issue: "42"
autonomy: checkpoint
tasks:
  - id: T0
    title: Capture baseline state
    status: not-started
    agent: t0-baseline-capture
    dependencies: []
    priority: 1
    is-bookend: true
    bookend-type: t0-baseline
  - id: T1
    title: Define auth data models
    status: not-started
    agent: python-cli-architect
    dependencies: [T0]
    priority: 2
  - id: T99
    title: Verify implementation
    status: not-started
    agent: tn-verification-gate
    dependencies: [T1]
    priority: 5
    is-bookend: true
    bookend-type: tn-verification
```

---

## 4. Task Schema

The authoritative model is `sam_schema/core/models.py` `Task` class.

### Required Task Fields

| Field | Type | Pattern | Description |
|-------|------|---------|-------------|
| `id` | `str` | `^[A-Za-z]?\d+(\.\d+)?$` | Task ID: `T1`, `T2.3`, `1`, `T10` |
| `title` | `str` | 1–200 chars | Human-readable task title |
| `status` | `TaskStatus` | enum | See Status Values below |

### Optional Structural Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent` | `str` | null | Agent name for execution; read by `task-worker` via SAM MCP, passed to `profile_load` |
| `dependencies` | `list[str]` | `[]` | Task IDs this task must wait for; each must satisfy SUCCESSFUL_STATUSES before this task becomes ready |
| `priority` | `int` (1–5) | `3` (medium) | 1=critical, 2=high, 3=medium, 4=low, 5=lowest; lower value dispatches first |
| `complexity` | `str` | `"medium"` | `low`, `medium`, or `high` |
| `skills` | `list[str]` | `[]` | Skills the executing sub-agent loads before starting work |
| `blocked-by` | `list[str]` | `[]` | Informational blockers (distinct from `dependencies` — not used by dependency graph) |
| `parallelize-with` | `list[str]` | `[]` | Task IDs that can run concurrently (informational; dependency graph controls actual ordering) |

### Optional Timestamp Fields

All ISO 8601 strings. Written by specific components; agents must not write these directly.

| Field | Written By | Mechanism |
|-------|-----------|-----------|
| `created` | `swarm-task-planner` at plan creation | `sam_plan create` |
| `started` | `start-task` skill after successful claim | `sam_task claim` |
| `completed` | `task_status_hook.py` SubagentStop handler | `sam_task state complete` |
| `last-activity` | `task_status_hook.py` PostToolUse handler | SAM schema API; skipped when status is complete |

### Optional Analytical Metadata Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `issue-classification` | `str` | null | `procedural`, `defect`, `recurring-pattern`, `missing-guardrail`, `unbounded-design` |
| `scenario-target` | `str` | null | `"{scenario} -> {improvement}"` format |
| `analysis-method` | `str` | `"none"` | `none`, `5-whys`, `6-sigma`, `design-framing` |
| `divergence-notes` | `int` | `0` | Count of `## Divergence Notes` sections in body |
| `accuracy-risk` | `str` | `"low"` | `low`, `medium`, or `high`; CoVe checks required at medium/high |
| `reason` | `str` | `""` | Rationale for task decisions — parallelization safety, dependency choices |

### Optional Markdown Content Fields

All stored as YAML multiline scalars; default is empty string.

| Field | Description |
|-------|-------------|
| `body` | Full markdown body for the task |
| `description` | Short description |
| `objective` | One-sentence goal of the task |
| `requirements` | Implementation requirements |
| `constraints` | Constraints and out-of-scope boundaries |
| `expected-outputs` | Files created or modified; artifacts produced |
| `acceptance-criteria` | Criteria the agent must satisfy |
| `verification-steps` | Commands or procedures to prove completion |
| `context-notes` | Additional context for the executing agent |
| `handoff` | Notes for downstream tasks or agents |

### Optional Bookend Metadata Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `is-bookend` | `bool` | `false` | `true` for T0 baseline or TN verification tasks |
| `bookend-type` | `str` | null | `t0-baseline` or `tn-verification`; required when `is-bookend` is true |

### Optional GitHub Integration Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `github-issue` | `int` | null | Linked GitHub sub-issue number; used by SubagentStop hook for GitHub sync |

---

## 5. Task Status Values and Lifecycle

### Status Enum

| Status | Value | Written By |
|--------|-------|-----------|
| `NOT_STARTED` | `"not-started"` | Default at plan creation |
| `IN_PROGRESS` | `"in-progress"` | `sam_task(action='claim')` only |
| `COMPLETE` | `"complete"` | `task_status_hook.py` SubagentStop handler |
| `BLOCKED` | `"blocked"` | Agent via `sam_task(action='state')` |
| `DEFERRED` | `"deferred"` | Orchestrator |
| `SKIPPED` | `"skipped"` | Orchestrator; also auto-applied to downstream of FAILED |
| `FAILED` | `"failed"` | Agent or orchestrator; triggers downstream cascade to SKIPPED |

### Status Aliases (STATUS_MAP)

The SAM model accepts human-readable and emoji variants and normalizes them:

```text
"done"       → "complete"
"pending"    → "not-started"
"todo"       → "not-started"
"in_progress" → "in-progress"
":white_check_mark:" → "complete"
"[DEFERRED]" → "deferred"
"[SKIPPED]"  → "skipped"
"FAILED"     → "failed"
```

### Dependency Semantics

The `DependencyGraph` class defines which statuses unblock downstream tasks:

- **SUCCESSFUL_STATUSES** (unblock downstream): `complete`, `deferred`
- **TERMINAL_STATUSES** (lifecycle complete): `complete`, `deferred`, `skipped`, `failed`

`failed` is intentionally excluded from SUCCESSFUL_STATUSES. A failed upstream task does NOT
unblock dependents — it cascades `skipped` to all not-started downstream tasks.

### Task Lifecycle Diagram

```text
                    ┌─────────────────────────────────┐
                    │                                 │
                    ▼                                 │
              ┌───────────┐                           │
   created ──▶│ not-started│                          │
              └─────┬─────┘                           │
                    │ sam_task(action='claim')         │
                    │ [atomic read-check-write]        │
                    ▼                                 │
              ┌───────────┐                           │
              │ in-progress│──── agent implements ───▶│
              └─────┬─────┘                           │
                    │                                 │
          ┌─────────┼──────────────────┬──────────────┘
          │         │                  │
          ▼         ▼                  ▼
    ┌──────────┐ ┌──────┐        ┌─────────┐
    │ complete │ │failed│        │ blocked │
    └──────────┘ └──┬───┘        └─────────┘
                    │ auto-cascade                ┌──────────┐
                    └────────────────────────────▶│ skipped  │
                                                  └──────────┘
                    ┌──────────┐  ┌──────────┐
                    │ deferred │  │ skipped  │  ← orchestrator-driven
                    └──────────┘  └──────────┘
```

### Dependency Graph Rules

From `DependencyGraph`:

1. A task is **ready** when: `status == not-started` AND all dependency task IDs are in SUCCESSFUL_STATUSES.
2. A task with a dependency that does not exist in the plan is treated as having an unsatisfied dependency (not ready).
3. Ready tasks are sorted by `priority ASC` then numeric task ID `ASC`.
4. Cycles are detected via DFS three-color algorithm; `has_cycles` is reported in `sam_plan status`.
5. On task failure: forward DFS from the failed task's ID finds all reachable not-started tasks and marks them `skipped`.

---

## 6. Plan States and the Finalize Concept

Plans have two states defined by `PlanState`:

| State | Value | Behavior |
|-------|-------|----------|
| `READY` | `"ready"` | Default; plan is dispatchable |
| `DRAFTING` | `"drafting"` | Plan is being built incrementally; not visible to dispatch |

**Drafting state** is entered when `sam_plan(action='create', tasks=[])` is called with an empty
task list. While drafting:

- `sam_plan(action='status')` returns a `PlanStatus` model with `state="drafting"` instead of counts
- `sam_plan(action='ready')` returns a `ReadyTasksResult` model with `state="drafting"` and an empty `ready_tasks` list
- `sam_plan(action='read')` returns the plan with `state="drafting"`
- `sam_plan(action='append_task')` appends tasks one at a time (single-writer only)

**Finalize** (`sam_plan(action='finalize')`) clears drafting state, setting `state="ready"`. After
finalize, status and ready queries return real data and the plan is visible to the dispatch loop.

**When to use drafting**:

- Plans with 16+ tasks to avoid large single-call payloads
- Plans constructed by agents that emit tasks one at a time

**Small plans** (under 16 tasks) use the monolithic path: a single `sam_plan(action='create')` call
with the full `tasks` list creates a `state="ready"` plan in one call.

---

## 7. The Claim Operation

Claiming is the mechanism that prevents duplicate dispatch of the same task to multiple agents.

**Protocol** (`sam_task(action='claim')`):

1. Backend reads current task status.
2. If status is `not-started`: atomically write `status=in-progress` and `started=now`. Return `{"claimed": true}`.
3. If status is anything else: return `{"claimed": false, "error": "..."}`.

**Agent obligation on claim failure**: STOP immediately. Do not implement the task. Do not write
the active-task context file. Output the full JSON result for the orchestrator.

**After successful claim**: Call `sam_active_task(action='set')` to register the session-to-task
binding. This enables the SubagentStop hook to update task status on agent exit.

The claim operation is the ONLY permitted way to mark a task `in-progress`. Direct Edit of the
`status` field in the task file is an architectural violation.

---

## 8. The Active Task Parking Concept (`sam_active_task`)

`sam_active_task` provides session-scoped storage of the currently executing task. Its purpose:

1. **Hook integration**: The `SubagentStop` hook reads `active-task-{session_id}.json` directly
   from the filesystem when an agent session ends. It uses the stored `task_file_path` and
   `task_id` to mark the task `complete` and optionally sync to GitHub.

2. **Shorthand updates**: After setting the active task, agents can call
   `sam_active_task(action='update')` to patch fields or append sections without repeating
   the plan/task address on every call.

3. **Session isolation**: Multiple concurrent agents each set their own active task keyed by
   `session_id`. Single-agent scenarios use the `"_default"` sentinel.

**`ActiveTaskContext` fields stored**:

| Field | Description |
|-------|-------------|
| `task_file_path` | Absolute path to the plan YAML file containing this task |
| `task_id` | Task identifier within the plan (e.g., `"T3"`) |
| `parent_issue_number` | Optional GitHub issue number for GitHub sync by the hook |
| `session_id` | Claude Code session identifier |
| `feature_slug` | Feature slug derived from the plan filename |
| `started_at` | ISO 8601 timestamp when the task was started |

**Storage location**: `~/.dh/projects/{project-slug}/context/active-task-{session_id}.json`

---

## 9. Acceptance Criteria Structure

Plans support two forms of acceptance criteria:

### Free-Form (Markdown String)

```yaml
acceptance-criteria: |
  - All endpoints require auth by default
  - Token expiry is configurable per service
```

Stored as `Plan.acceptance_criteria` (string). Passed to agents via `TaskAssignment.plan_acceptance_criteria`.

### Structured (for T0/TN Verification)

```yaml
acceptance-criteria-structured:
  - criterion-id: AC-1
    description: "Models exist and validate"
    check-command: "uv run pytest tests/test_models.py -v"
    expected-baseline: fail
    expected-final: pass
  - criterion-id: AC-2
    description: "Linting passes"
    check-command: "uv run ruff check src/"
    expected-baseline: pass
    expected-final: pass
```

Each `AcceptanceCriterion` has:

| Field | Description |
|-------|-------------|
| `criterion-id` | Unique identifier (e.g., `"AC-1"`) |
| `description` | Human-readable description of what is being checked |
| `check-command` | Executable shell command to run |
| `expected-baseline` | Expected result at T0: `"pass"`, `"fail"`, or `"any"` |
| `expected-final` | Expected result at TN: typically `"pass"` |

Structured criteria require both T0 and TN bookend tasks in the plan (enforced by `BookendValidator`).

### BookendResult (T0 output file)

Written to `plan/T0-baseline-{slug}.yaml` by the `t0-baseline-capture` agent:

```yaml
feature: auth-system
captured_at: "2026-03-15T10:00:00Z"
plan_path: plan/tasks-5-auth-system.md
criteria_count: 3
results:
  - criterion-id: AC-1
    check-command: "uv run pytest tests/test_auth.py -v"
    exit-code: 1
    stdout: "FAILED tests/test_auth.py::test_login - FileNotFoundError"
    stderr: ""
    timestamp: "2026-03-15T10:00:01Z"
    duration-seconds: 0.42
```

### BookendVerification (TN output file)

Written to `plan/TN-verification-{slug}.yaml` by the `tn-verification-gate` agent:

```yaml
feature: auth-system
verified_at: "2026-03-15T14:00:00Z"
plan_path: plan/tasks-5-auth-system.md
t0_baseline_path: plan/T0-baseline-auth-system.yaml
verdict: PASS
criteria_count: 3
regressions: 0
newly_passing: 1
results:
  - criterion-id: AC-1
    check-command: "uv run pytest tests/test_auth.py -v"
    t0-exit-code: 1
    tn-exit-code: 0
    status: newly-passing
    stdout-diff-summary: "T0: FAILED (FileNotFoundError) -> TN: 3 passed"
```

**CriterionStatus values**: `passed`, `regressed`, `pre-existing-fail`, `newly-passing`

---

## 10. T0/TN Verification Gate Concept

The T0/TN system captures observable system state before and after implementation to detect
regressions and prove acceptance criteria were met.

### T0 Baseline Task

- **Is a bookend**: `is-bookend: true`, `bookend-type: t0-baseline`
- **Position in plan**: `dependencies: []`, `priority: 1` → dispatches first, before any implementation
- **Agent**: `t0-baseline-capture`
- **What it does**: Runs every `check-command` from `acceptance-criteria-structured`, captures
  exit code, stdout, and stderr. Writes to `plan/T0-baseline-{slug}.yaml`.
- **Why**: Establishes baseline — some criteria are expected to fail at T0 (tests for code not
  yet written). A regression is defined relative to T0, not relative to "must pass."

### TN Verification Task

- **Is a bookend**: `is-bookend: true`, `bookend-type: tn-verification`
- **Position in plan**: `dependencies: [all non-bookend task IDs]`, `priority: 5` → dispatches last
- **Agent**: `tn-verification-gate`
- **What it does**: Re-runs every `check-command`, compares exit codes against T0 results.
  Classifies each criterion as: `passed`, `regressed`, `pre-existing-fail`, or `newly-passing`.
  Writes verdict to `plan/TN-verification-{slug}.yaml`.

### Bookend Validation Rules (from BookendValidator)

1. At most one T0 task per plan.
2. At most one TN task per plan.
3. T0 must have an empty `dependencies` list.
4. TN must depend on every non-bookend task ID.
5. If `acceptance-criteria-structured` is non-empty, both T0 and TN must exist.

Both bookend artifacts are registered in the issue artifact manifest via `artifact_register` and
are read by `/complete-implementation` via `artifact_read`.

---

## 11. How Plans Relate to GitHub Issues

**Plan → GitHub Issue**: Plans store an optional `issue` field (GitHub issue number). When a plan
is created with `issue=N`, it is auto-registered as a `task-plan` artifact on issue N via the
artifact manifest system. The artifact manifest is stored in the GitHub Issue body.

**Task → GitHub Sub-Issue**: Individual tasks have an optional `github-issue` field (int). This
links the task to a specific GitHub sub-issue. The SubagentStop hook calls
`backlog_core.gh_client.update_task_status()` after marking a task complete, syncing the status
to the linked sub-issue.

**Artifact manifest flow**:

1. `swarm-task-planner` calls `sam_plan(action='create', issue=N)` → auto-registers `task-plan` artifact.
2. `t0-baseline-capture` calls `artifact_register(issue_number=N, artifact_type="T0-baseline", ...)`.
3. `tn-verification-gate` calls `artifact_register(issue_number=N, artifact_type="TN-verification", ...)`.
4. Agents in worktree-isolated environments call `artifact_read(issue_number=N, artifact_type="architect")` to access plan docs that are not visible in their worktree.

**Backlog item → Plan resolution**: When the parent story issue number is known, the
`backlog_get_ready_sam_tasks(parent_issue_number=N)` tool retrieves the plan from the artifact
manifest and returns ready tasks, falling back to local cache when GitHub is unavailable.

---

## 12. Dispatch System

The dispatch loop in `/implement-feature` drives task execution:

```text
Progress Loop:
  1. sam_plan(action='status') → extract autonomy_mode, check tasks remaining
  2. sam_plan(action='ready') → get current batch of ready tasks [ONCE per batch]
  3. Dispatch each ready task:
       - Always dispatch subagent_type="dh:task-worker"
       - task-worker reads agent: field via SAM MCP, calls profile_load internally
       - Multi-task batch → TeamCreate(team_name="impl-{slug}")
       - Single-task → single Agent call
  4. After agent returns → check for <concerns> block, contract verification
  5. sam_plan(action='status') → if tasks remain, return to step 2

Autonomy gates:
  full_auto:  no pauses
  checkpoint: pause after each dependency wave
  per_task:   pause before each individual task
```

**Key dispatch rules**:

- The `agent:` field in task YAML is NOT a routing directive for the orchestrator. The orchestrator
  always dispatches `dh:task-worker`. The `agent:` field is read internally by `task-worker` via
  `sam_task(action='read')` and passed to `profile_load` to specialize behavior.
- `sam_plan(action='ready')` is called ONCE per batch. The returned list is stored and iterated.
  The next call to `ready` happens only after the entire current batch completes.
- Bookend tasks dispatch automatically via normal readiness logic — no special handling needed.
  T0 has `dependencies: []` and `priority: 1` so it always dispatches first. TN has the highest
  dependency count and `priority: 5` so it dispatches last.

**Plan addressing for dispatch**:

```text
P{hex}/T{M}     e.g., Pc7d8e9f0/T3
slug/T{M}       e.g., auth-system/T3
```

---

## 13. Backend Architecture

The SAM system uses a `TaskBackend` Protocol that decouples plan/task operations from storage.
Three backends exist:

| Backend | Identifier | Description |
|---------|-----------|-------------|
| `LocalYamlTaskProvider` | `"local"` | Default; YAML files under `~/.dh/projects/{slug}/plan/` |
| `InMemoryTaskProvider` | `"memory"` | Test double; no persistence |
| `GitHubTaskProvider` | `"github"` | Plans as GitHub Issues; tasks as sub-issues with `sam:` labels. **Not yet implemented** (pending #984) |

Backend selection order:
1. `TASKBACKEND` environment variable
2. `[backend] name` in `taskbackend.toml` (project root or `~/.dh/`)
3. Default: `"local"`

Similarly, a `ContextBackend` Protocol governs active-task context storage
(`get_active_task`, `set_active_task`, `clear_active_task`, `list_active_tasks`).

---

## 14. File Storage Layout

```text
~/.dh/projects/{project-slug}/
  plan/
    P{hex}-{slug}.yaml              # single-file plan (under 500 lines)
    P{hex}-{slug}/                  # directory plan (500+ lines)
      P{hex}-PLAN.yaml              # plan metadata + task list
      tasks/
        T01.yaml
        T02.yaml
    T0-baseline-{slug}.yaml         # T0 bookend output
    TN-verification-{slug}.yaml     # TN bookend output
  context/
    active-task-{session-id}.json   # active task parking (read by SubagentStop hook)
  backlog/
    *.md                            # backlog item cache (synced from GitHub Issues)
  dispatch-state.db                 # milestone dispatch state (SQLite, WAL mode)
```

Legacy plans (pre-naming-scheme) use `tasks-{N}-{slug}.md` format and are addressed as `P{N}`.
`sam migrate` converts them to the canonical YAML format.

---

## 15. Mapping to Beads

### Concepts That Map Directly

| SAM Concept | Beads Equivalent |
|-------------|-----------------|
| Plan | A container issue or milestone grouping tasks |
| Task | A beads issue or work item |
| `status: not-started` | Open, unassigned issue |
| `status: in-progress` | Issue with `in-progress` label or assignee set |
| `status: complete` | Closed issue |
| `dependencies: [T1, T2]` | Issue dependencies (if beads supports them natively) |
| `plan_id` / plan address | Milestone ID or parent issue ID |
| `issue` field on Plan | Parent GitHub Issue number |
| `github-issue` field on Task | Sub-issue number in GitHub |

### Concepts That Require Beads Extensions or Workarounds

| SAM Feature | Gap in Beads | Notes |
|-------------|-------------|-------|
| **Claim operation** (atomic read-check-write to prevent duplicate dispatch) | Beads issues have no atomic claim primitive | Requires a lock/assignment mechanism: first agent to assign the issue wins; others check assignee before starting |
| **Dependency graph evaluation** (`get_ready_tasks` — DAG with cycle detection) | Beads does not natively compute which issues are unblocked | Must be implemented as a query layer on top of beads dependency links |
| **Plan-level state (`drafting` vs `ready`)** | No milestone-level state machine in beads | Could be a label on the parent issue/milestone; incremental build pattern requires a gating mechanism |
| **Active task parking** (`sam_active_task`) | No session-scoped state store | Requires a local file or ephemeral store keyed by session ID; the SubagentStop hook pattern is specific to Claude Code sessions |
| **Bookend tasks** (T0/TN with structural validation) | No built-in concept in beads | Implement as special-labeled issues with required dependency constraints; validation must be external |
| **Structured acceptance criteria with executable check commands** | Beads issues have no executable check-command fields | Store as custom fields or in issue body with a parseable format |
| **T0/TN result files** (`BookendResult`, `BookendVerification` YAML) | No artifact storage in beads | Must be stored as issue attachments, comments, or external artifact registry |
| **SubagentStop hook → automatic status update** | Hook is specific to Claude Code agent lifecycle | Any beads-based equivalent must integrate with the agent runtime's session termination event |
| **Downstream SKIPPED cascade on FAILED** | No cascading status transitions in beads | Must be implemented as a query+update loop on the dependency graph after a failure |
| **Autonomy modes** (`full_auto`, `checkpoint`, `per_task`) | No milestone-level dispatch gating | Must be implemented in the orchestrator skill, not in beads itself |
| **Artifact manifest** (linking plan artifacts to GitHub Issues) | Partial — GitHub supports issue comments and attachments | The artifact manifest is stored in the issue body in a structured format; beads may or may not support this |
| **`parallelize-with` field** | Informational only in SAM; beads has no equivalent | Low priority — dependency graph already determines safe parallelism |

### What SAM Has That Beads Does NOT Natively Support (Summary)

1. **Atomic task claiming** with concurrency safety
2. **DAG readiness computation** (which tasks are unblocked right now)
3. **Plan drafting state** with guarded dispatch
4. **Session-scoped active task context** for hook integration
5. **Structured AC with executable commands** stored per-plan
6. **T0/TN bookend lifecycle** with structural validation and comparison result storage
7. **Downstream cascade** (auto-skipping dependents of failed tasks)
8. **Autonomy mode gating** (checkpoint/per_task pauses)
9. **SubagentStop hook** → automatic task completion on agent exit
10. **Task-level skill declarations** (which skills the executing agent loads)
