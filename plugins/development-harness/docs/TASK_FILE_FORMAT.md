# SAM Task File Format

**Status**: Snapshot (last synced 2026-03-31)
**Purpose**: Reference for SAM task file structure and the SAM MCP server as the primary interface

> **Drift warning**: This document drifts from the implementation between updates. The authoritative source for field definitions is `plugins/development-harness/sam_schema/core/models.py` (the `Task` Pydantic model). For planning or implementation work, verify field names, types, and defaults against `models.py` and the generated schema (`uv run sam schema --model Task`). For conceptual discussion, this document is sufficient as a point-in-time snapshot.

All task file I/O routes through the SAM MCP server (`mcp__plugin_dh_sam__*`) or the `uv run sam` CLI fallback. No component reads or writes task files directly via Read/Edit/Write tools.

---

## Quick Reference

### SAM MCP Tools (Primary)

Three consolidated tools replace the previous 8-tool interface. Each tool uses a
discriminated union `config` parameter where `action` selects the operation.

**sam_task** — task-scoped operations (requires `plan` and `task`):

```text
mcp__plugin_dh_sam__sam_task(plan="P{id}", task="T{M}", config={"action":"read"})
    -- Read task (returns TaskAssignment with plan context + task fields)
mcp__plugin_dh_sam__sam_task(plan="P{id}", task="T{M}", config={"action":"claim"})
    -- Claim task (transition from not-started to in-progress)
mcp__plugin_dh_sam__sam_task(plan="P{id}", task="T{M}", config={"action":"state","status":"complete"})
    -- Transition task status (complete | blocked | deferred | skipped)
mcp__plugin_dh_sam__sam_task(plan="P{id}", task="T{M}", config={"action":"update","set_fields_json":"{...}"})
    -- Patch task fields (JSON object {"field": "value", ...})
mcp__plugin_dh_sam__sam_task(plan="P{id}", task="T{M}", config={"action":"update","append_section":"Heading","section_content":"..."})
    -- Append a markdown section to the task body
```

**sam_plan** — plan-scoped operations (`plan` required for read/status/ready/update; omit for list/create):

```text
mcp__plugin_dh_sam__sam_plan(config={"action":"list"})
    -- List all plans
mcp__plugin_dh_sam__sam_plan(config={"action":"list","search":"text"})
    -- List plans with case-insensitive substring filter
mcp__plugin_dh_sam__sam_plan(config={"action":"create","slug":"...","goal":"...","tasks":[...]})
    -- Create a new plan from a list of task definition objects
mcp__plugin_dh_sam__sam_plan(plan="P{id}", config={"action":"read"})
    -- Read plan summary (Plan fields)
mcp__plugin_dh_sam__sam_plan(plan="P{id}", config={"action":"status"})
    -- Plan progress summary (task counts, completion %)
mcp__plugin_dh_sam__sam_plan(plan="P{id}", config={"action":"ready"})
    -- List tasks ready for dispatch (not-started, all deps resolved)
mcp__plugin_dh_sam__sam_plan(plan="P{id}", config={"action":"update","context":"..."})
    -- Update plan context field
mcp__plugin_dh_sam__sam_plan(plan="P{id}", config={"action":"update","set_fields_json":"{...}"})
    -- Patch plan-level fields
mcp__plugin_dh_sam__sam_plan(plan="P{id}", config={"action":"append_task","task_yaml":"<single-task YAML string>"})
    -- Append a single task to a plan in state="drafting"; backends do not enforce the drafting precondition
mcp__plugin_dh_sam__sam_plan(plan="P{id}", config={"action":"finalize"})
    -- Finalize a drafting plan: clear state="drafting" → state="ready", making tasks dispatchable
```

#### Incremental Append Workflow

For large plans (rule of thumb: 16+ tasks), use the three-call incremental workflow instead of a
single monolithic `create` call:

```text
1. sam_plan(action='create', tasks=[])
   -- Creates a plan in state="drafting". Returns plan_id (e.g. "Pd9e0f1a2").

2. sam_plan(plan='P{id}', action='append_task', task=<single task dict>) × N
   -- Appends one task at a time. Each call validates the task via Task.model_validate().
   -- state remains "drafting" throughout. Callers must serialize writes (single-writer
      assumption — concurrent append_task calls for the same plan are not safe).

3. sam_plan(plan='P{id}', action='finalize')
   -- Clears state="drafting" → state="ready". Plan is now visible to sam_plan ready/status.
```

**Drafting state semantics**: While a plan is in `state="drafting"`:

- `sam_plan(action='read')` returns the plan with the drafting marker (`{state: "drafting"}` or `{drafting: True}`)
- `sam_plan(action='status')` returns the drafting marker instead of task counts
- `sam_plan(action='ready')` returns the drafting marker instead of a ready-tasks list

This prevents partial plans from being dispatched before all tasks have been appended.

**When to choose incremental vs monolithic**:

| Condition | Recommendation |
|-----------|---------------|
| < 16 tasks | Monolithic `create` (single call with `tasks=[...]`) |
| 16+ tasks | Incremental: `create(tasks=[])` → `append_task` × N → `finalize` |

**sam_active_task** — session-scoped active task context:

```text
mcp__plugin_dh_sam__sam_active_task(config={"action":"set","plan":"P{id}","task":"T{M}"})
    -- Register active task for current session (replaces direct active-task-{sid}.json writes)
mcp__plugin_dh_sam__sam_active_task(config={"action":"get"})
    -- Retrieve active task context for current session
mcp__plugin_dh_sam__sam_active_task(config={"action":"update","set_fields_json":"{...}"})
    -- Update fields on the active task without repeating its address
mcp__plugin_dh_sam__sam_active_task(config={"action":"clear"})
    -- Clear active task context for current session
```

> **Note — readonly annotation loss (`sam_task`)**: The legacy `sam_read` tool was
> annotated `readonly=True` in FastMCP, so Claude Code did not prompt for confirmation
> on read operations. `sam_task` cannot be readonly because it also includes write
> actions (`claim`, `state`, `update`). Consequence: Claude Code will show a
> confirmation prompt for `sam_task(action="read")` calls that previously did not
> require one. This is a known, accepted trade-off — a clean 3-tool interface
> outweighs the read UX regression. If read-without-prompt becomes required, a
> separate readonly `sam_task_read` tool can be extracted in a future iteration.

#### Deprecated Tools (migration reference only)

The following 8 tools are replaced by the 3-tool interface above. They return a
`ToolError` when called and must not appear in new agent code or skill files.

| Deprecated tool | Replaced by |
|---|---|
| `sam_read(plan, task)` | `sam_task(plan, task, config={"action":"read"})` |
| `sam_claim(plan, task)` | `sam_task(plan, task, config={"action":"claim"})` |
| `sam_state(plan, task, status)` | `sam_task(plan, task, config={"action":"state","status":...})` |
| `sam_update(plan, context)` | `sam_plan(plan, config={"action":"update","context":...})` |
| `sam_update(plan, task, ...)` | `sam_task(plan, task, config={"action":"update",...})` |
| `sam_ready(plan)` | `sam_plan(plan, config={"action":"ready"})` |
| `sam_status(plan)` | `sam_plan(plan, config={"action":"status"})` |
| `sam_list(...)` | `sam_plan(config={"action":"list",...})` |
| `sam_create(...)` | `sam_plan(config={"action":"create",...})` |

### CLI Fallback

When MCP is unavailable, use the `uv run sam` CLI:

```bash
uv run sam list                                      # List all plans
uv run sam list --search "my-feature"                # List with search filter
echo "$YAML" | uv run sam create {slug} --goal "..." --stdin  # Create plan
uv run sam read P{id} --format json                  # Read plan summary (e.g. Pc7d8e9f0)
uv run sam read P{id}/T{M} --format json             # Read task (e.g. Pc7d8e9f0/T04)
uv run sam update P{id} --context "..."              # Update plan context
uv run sam state P{id}/T{M} {status}                 # Transition task status
uv run sam claim P{id}/T{M}                          # Claim a task
uv run sam ready P{id} --format json                 # List ready tasks
uv run sam status P{id}                              # Plan progress summary
uv run sam validate P{id} --format json              # Validate plan (CLI only)
uv run sam migrate tasks-{N}-{slug}.md               # Migrate legacy format (CLI only)
```

---

## Naming Convention

### File Names

Plan files are stored under the per-project state directory (`~/.dh/projects/{project-slug}/plan/`), resolved via `dh_paths.plan_dir()`. The `{project-slug}` is computed from the absolute project root path by replacing `/` with `-`.

```text
~/.dh/projects/{project-slug}/plan/P{id}-{slug}.yaml            # single-file plan (under 500 lines)
~/.dh/projects/{project-slug}/plan/P{id}-{slug}/                # directory plan (500+ lines)
    P{id}-PLAN.yaml               # plan-level metadata, goal, context, task list
    P{id}-ARCHITECT.md            # architecture spec
    P{id}-CONTEXT.md              # feature context
    tasks/
        T01.yaml
        T02.yaml
```

`{id}` is a hex string assigned by `sam create`. `{slug}` is lowercase-hyphenated from the feature name.

### Addressing

```text
P{id}/T{M}        -- task M in plan with id (hex match)
Pc7d8e9f0/T04     -- task T04 in plan Pc7d8e9f0
my-slug/T1        -- task T1 in plan matching slug "my-slug"
```

`sam read Pc7d8e9f0/T3` globs the plan directory under `dh_paths.plan_dir()` for `P{id}-*/` and finds `T03.yaml` (or the T03 section in a single-file plan). Plans created by `sam_plan(action='create')` have UUID-hex IDs (8 hex chars, e.g. `Pc7d8e9f0`); legacy numeric IDs (`P1`, `P42`) exist only for unmigrated plans created before this naming scheme.

### Legacy Names

Plans created before this specification use `tasks-{N}-{slug}.md` naming (formerly stored in the repo-relative `plan/` directory, now resolved via `dh_paths.plan_dir()`). The addressing module resolves both patterns. Migrate using `sam migrate`. See [Legacy Format Support](#legacy-format-support).

---

## Plan Schema

Plan-level fields are defined in the `Plan` Pydantic model (`plugins/development-harness/sam_schema/core/models.py`).

Key plan fields:

```yaml
plan_number: 1
slug: my-feature
goal: "Implement the feature"
context: "Background context shared across all tasks"
acceptance_criteria:
  - "Criterion 1"
  - "Criterion 2"
issue: 719                    # GitHub issue number (optional)
feature: "My Feature Name"
status: in-progress           # not-started | in-progress | complete
autonomy: full_auto           # full_auto (default) | checkpoint | per_task
created: "2026-03-15T00:00:00Z"
tasks:
  - id: T01
    title: "First task"
    status: not-started
    ...
```

`autonomy` controls dispatch gating in the `/implement-feature` Progress Loop:

- `full_auto` (default): dispatch all tasks without pausing — backward-compatible behaviour
- `checkpoint`: pause for user confirmation after each dependency wave of tasks completes
- `per_task`: dispatch one task at a time via a single `Agent` call and pause for user confirmation before the next

For the complete field specification:

- [Plan Schema](./plan-schema.json) — generated by `uv run sam schema --model Plan`

---

## Task Schema

Task-level fields are defined in the `Task` Pydantic model (`plugins/development-harness/sam_schema/core/models.py`, lines 107–242).

### Task ID Pattern

`id` must match the pattern `^[A-Za-z]?\d+(\.\d+)?$`.

Examples of valid IDs: `T01`, `T1`, `T2.3`, `1`, `10`.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Task ID — must match `^[A-Za-z]?\d+(\.\d+)?$` (e.g., `T01`, `T2.3`) |
| `title` | `str` | Human-readable task title (1–200 characters) |
| `status` | `str` | See [Status Values](#status-values) |

### Optional Fields — Structural

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent` | `str` | `null` | Agent name for execution |
| `dependencies` | `list[str]` | `[]` | Task IDs this task depends on |
| `priority` | `int` | `3` (medium) | See [Priority Values](#priority-values) |
| `complexity` | `str` | `medium` | `low`, `medium`, or `high` |
| `skills` | `list[str]` | `[]` | Skills the executing sub-agent loads |
| `blocked-by` | `list[str]` | `[]` | Task IDs that block this task (distinct from `dependencies`) |
| `parallelize-with` | `list[str]` | `[]` | Task IDs that can run concurrently with this task |

### Optional Fields — Timestamps

All timestamps are ISO 8601 strings (e.g., `2026-03-15T13:00:00Z`).

| Field | Default | Written By |
|-------|---------|------------|
| `created` | `null` | `swarm-task-planner` at plan creation |
| `started` | `null` | `sam claim` via `start-task` skill |
| `completed` | `null` | `task_status_hook.py` SubagentStop handler |
| `last-activity` | `null` | `task_status_hook.py` PostToolUse handler |

### Optional Fields — Analytical Metadata

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `issue-classification` | `str` | `null` | See [Issue Classification Values](#issue-classification-values) |
| `scenario-target` | `str` | `null` | `"{scenario} -> {improvement}"` |
| `analysis-method` | `str` | `none` | See [Analysis Method Values](#analysis-method-values) |
| `divergence-notes` | `int` | `0` | Count of `## Divergence Notes` sections in body |
| `accuracy-risk` | `str` | `low` | Risk level for Chain of Verification — `low`, `medium`, or `high`. CoVe checks are included when `medium` or `high`. |
| `reason` | `str` | `""` | Rationale for task decisions — parallelization safety, dependency choices, or design tradeoffs. |

### Optional Fields — Markdown Content

All content fields are stored as YAML multiline scalars. Default is an empty string.

| Field | Description |
|-------|-------------|
| `body` | Full markdown body for the task |
| `description` | Short description of the task |
| `objective` | Goal and scope of the task |
| `requirements` | Implementation requirements |
| `constraints` | Constraints and boundaries |
| `expected-outputs` | Artifacts or outputs the task must produce |
| `acceptance-criteria` | Criteria that must be satisfied for the task to be complete |
| `verification-steps` | Steps to verify acceptance criteria are met |
| `context-notes` | Additional context shared with the executing agent |
| `handoff` | Notes for the next task or agent |

### Optional Fields — Bookend Metadata

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `is-bookend` | `bool` | `false` | `true` for T0 baseline or TN verification tasks |
| `bookend-type` | `str` | `null` | `t0-baseline` or `tn-verification` (required when `is-bookend` is `true`) |

### Optional Fields — GitHub Integration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `github-issue` | `int` | `null` | Linked GitHub sub-issue number |

### Status Values

| Status | Description | Written By |
|--------|-------------|-----------|
| `not-started` | Default for new tasks | `swarm-task-planner` at creation |
| `in-progress` | Agent has claimed the task | `sam claim` via `start-task` skill |
| `complete` | Task finished successfully | `task_status_hook.py` SubagentStop handler |
| `blocked` | Cannot proceed — external dependency | Agent via `sam state` |
| `deferred` | Postponed to a later session | Orchestrator |
| `skipped` | Intentionally not executed | Orchestrator |
| `failed` | Task execution failed; downstream dependents are auto-skipped | Agent or orchestrator via `sam state` |

### Priority Values

| Value | Name | Meaning |
|-------|------|---------|
| `1` | critical | Highest priority |
| `2` | high | |
| `3` | medium | Default |
| `4` | low | |
| `5` | lowest | Lowest priority |

### Issue Classification Values

| Value | Description |
|-------|-------------|
| `procedural` | Process or workflow failure |
| `defect` | Code defect |
| `recurring-pattern` | Same class of issue seen repeatedly |
| `missing-guardrail` | No check or validation exists to prevent this |
| `unbounded-design` | Design without clear scope or exit criteria |

### Analysis Method Values

| Value | Description |
|-------|-------------|
| `none` | No structured analysis applied (default) |
| `5-whys` | Five Whys root cause analysis |
| `6-sigma` | Six Sigma methodology |
| `design-framing` | Design framing analysis |

### Complete YAML Example

```yaml
id: T01
title: "Implement auth token refresh"
status: not-started
agent: python-cli-architect
dependencies: []
priority: 2
complexity: medium
skills:
  - python3-development
blocked-by: []
parallelize-with:
  - T02
created: "2026-03-15T00:00:00Z"
started: null
completed: null
last-activity: null
issue-classification: defect
scenario-target: "token expires silently -> token refreshed with user notification"
analysis-method: 5-whys
divergence-notes: 0
accuracy-risk: medium
reason: "Token refresh is isolated from request handling — safe to parallelize with T02"
objective: |
  Implement automatic refresh of expired auth tokens without user interruption.
requirements: |
  - Detect 401 responses and attempt token refresh before retrying
  - Refresh endpoint: POST /auth/refresh
acceptance-criteria: |
  - Expired token triggers refresh and retry on 401
  - Refresh failure returns clear error to caller
verification-steps: |
  - Run pytest tests/auth/test_token_refresh.py
expected-outputs: |
  - auth/token_refresh.py module
  - pytest suite with >80% coverage
constraints: |
  - Do not store refresh token in memory longer than one request cycle
context-notes: |
  Token TTL is 15 minutes. Refresh token TTL is 7 days.
handoff: |
  T02 depends on the refresh module being importable from auth.token_refresh.
body: ""
description: "Add automatic token refresh on 401 responses"
is-bookend: false
bookend-type: null
github-issue: 842
```

For the complete field specification:

- [Task Schema](./task-schema.json) — generated by `uv run sam schema --model Task`

---

## Authorized Writers

Task metadata fields are owned by specific components. The SAM MCP server and `sam_schema` API are the primary write interfaces, with the `uv run sam` CLI as fallback. No component writes task fields directly via Edit/Write tools.

| Field | Written By | Via |
|-------|-----------|-----|
| All task fields at creation | `swarm-task-planner` agent | `sam create {slug} --goal "..." --stdin` |
| `status: in-progress`, `started` | `start-task` skill | `sam claim P{id}/T{M}` (e.g. `Pc7d8e9f0/T04`) |
| `status: complete`, `completed` | `task_status_hook.py` SubagentStop handler | `sam state P{id}/T{M} complete` |
| `status: blocked` | Agent or human operator | `sam state P{id}/T{M} blocked` |
| `last-activity` | `task_status_hook.py` PostToolUse handler | `sam_schema` API — skipped if status is `complete` |
| `context` | `context-gathering` agent | `sam update P{id} --context "..."` |
| Plan metadata | orchestrator or `add-new-feature` skill | `sam update P{id} --set field=value` |
| `divergence-notes`, body sections | executing agent via `start-task` skill | `sam update P{id}/T{M} --append-section "..."` |

### Field Ownership Rules

1. `status: in-progress` and `started` are written only by `sam claim`. Agents in `start-task` must invoke `sam claim` and check exit code. Direct Edit of these fields is an architectural violation.

2. `status: complete` and `completed` are written only by `task_status_hook.py` SubagentStop handler.

3. `last-activity` is written only by `task_status_hook.py` PostToolUse handler, and only when task status is not `complete`.

4. `divergence-notes` count and `## Divergence Notes` body content are written by the executing agent via `sam update --append-section`.

5. All other fields (`id`, `title`, `agent`, `dependencies`, `priority`, `complexity`, `created`, `skills`, and analytical metadata) are written once at plan creation by `swarm-task-planner`. No component modifies them after creation.

---

## sam CLI Usage Guide (Fallback Reference)

### sam list — List all plans

```bash
uv run sam list
# Output: { "items": [...], "count": N, "total": N }

uv run sam list --search "gates"
# Filters by case-insensitive substring match across feature, description, and goal fields

uv run sam list --offset 10 --limit 5
# Pagination support
```

### sam create — Create a new plan

```bash
# Pipe YAML task definitions via stdin
echo "$YAML_CONTENT" | uv run sam create my-feature \
  --goal "Route all SAM workflow I/O through sam CLI" \
  --issue 719 \
  --stdin \
  --format json

# Output: { "path": "~/.dh/projects/{project-slug}/plan/Pc7d8e9f0-my-feature.yaml", "plan_id": "Pc7d8e9f0", "task_count": 14 }
```

Stdin YAML structure:

```yaml
tasks:
  - id: T01
    title: "First task"
    status: not-started
    agent: python-cli-architect
    dependencies: []
    priority: 1
    complexity: medium
    skills: ["python3-development"]
    body: |
      ## Objective
      ...
acceptance_criteria:
  - "AC1: criterion one"
context: "Shared context"
```

### sam read — Read task or plan

```bash
# Read a task — returns TaskAssignment (plan context + task details)
uv run sam read Pc7d8e9f0/T04 --format json

# Read a plan — returns Plan JSON
uv run sam read Pc7d8e9f0 --format json
```

TaskAssignment response shape (see [TaskAssignment Schema](./assignment-schema.json)):

```json
{
  "plan_id": "Pc7d8e9f0",
  "plan_slug": "my-feature",
  "plan_goal": "Route all SAM workflow I/O through sam CLI",
  "plan_context": "Background context shared across all tasks",
  "plan_acceptance_criteria": ["AC1: criterion one"],
  "task": {
    "id": "T04",
    "title": "TASK_FILE_FORMAT.md rewrite",
    "status": "in-progress",
    "agent": "contextual-ai-documentation-optimizer",  // bundles quality audit, content optimization, and frontmatter description writing; for upstream content sync tasks, use a general-purpose agent with drift report (pending skill-content-updater, backlog #1899)
    "dependencies": [],
    "priority": 1,
    "complexity": "medium",
    "body": "## Objective\n..."
  }
}
```

### sam update — Update plan or task fields

```bash
# Set plan context
uv run sam update Pc7d8e9f0 --context "Background context for all tasks"

# Set a specific field
uv run sam update Pc7d8e9f0 --set acceptance-criteria-structured=true

# Append a section to a task body
uv run sam update Pc7d8e9f0/T04 \
  --append-section "Divergence Notes" \
  --section-content "### DN-1: Brief title\n..."
```

### sam state — Transition task status

```bash
uv run sam state Pc7d8e9f0/T04 complete
uv run sam state Pc7d8e9f0/T04 blocked
# Valid values: not-started | in-progress | complete | blocked | deferred | skipped
```

### sam claim — Claim a task (mark in-progress)

```bash
uv run sam claim Pc7d8e9f0/T04 --format json
# Output: { "claimed": true, "task_id": "T04", "started": "2026-03-15T13:00:00Z" }
# Exit code 1: already claimed, not found, or status != not-started
```

### sam ready — List ready tasks

```bash
uv run sam ready Pc7d8e9f0 --format json
# Output: { "feature": "my-feature", "ready_tasks": [...], "count": 3 }
# A task is ready when status=not-started and all dependencies are complete.
```

### sam status — Plan progress summary

```bash
uv run sam status Pc7d8e9f0
# Output: plan progress with task counts by status, blocked tasks, next ready tasks
```

### sam validate — Validate plan against schema

```bash
uv run sam validate Pc7d8e9f0 --format json
# Output: { "valid": true/false, "errors": [...], "warnings": [...] }
```

### sam migrate — Convert legacy format to pure YAML

```bash
uv run sam migrate tasks-3-integrate-sam-schema.md
# Converts YAML frontmatter .md file to pure YAML .yaml file
# Output: ~/.dh/projects/{project-slug}/plan/Pc7d8e9f0-integrate-sam-schema.yaml
```

---

## Legacy Format Support

### Supported Legacy Patterns (Read-Only)

The `sam` CLI reads but does not write these legacy formats:

| Pattern | Example | Support |
|---------|---------|---------|
| `tasks-{N}-{slug}.md` with YAML frontmatter | `tasks-3-my-feature.md` (under plan_dir()) | Read via `sam read`, `sam ready`, `sam status` |
| `tasks-{N}-{slug}/` directory with `.md` files | `tasks-3-my-feature/T01.md` (under plan_dir()) | Read only |
| Bold markdown fields (`**Status**: NOT STARTED`) | legacy `.md` files | Read via `sam migrate` preprocessing |

### Number Collision Warning

When a canonical `P{id}-{slug}.yaml` file and a legacy `tasks-{NNN}-{slug}.md` file share the same identifier (both under `plan_dir()`), the canonical file takes precedence. The `sam` CLI emits a warning to stderr:

```text
WARNING: Pb5c6d7e8 resolved to 'Pb5c6d7e8-research-curator-code-analysis.yaml' but a legacy file
also exists with the same slug: tasks-698-gates-subprocess-timeout.md.
Run 'sam migrate Pb5c6d7e8' to remove the legacy file.
```

To resolve: migrate or rename the legacy file so identifiers are unique.

### File Path Rejection

Passing a raw file path (e.g., `tasks-698-foo.md`) as an address is rejected with a clear error. Use plan addresses (`Pb5c6d7e8`, `gates-subprocess-timeout`) instead.

### Migration Path

Migrate a legacy plan to the canonical format:

```bash
# 1. Migrate format (YAML frontmatter .md -> pure YAML .yaml)
#    Legacy files are resolved from dh_paths.plan_dir() automatically
uv run sam migrate tasks-3-my-feature.md

# 2. Rename to P{id} convention (dry run first)
uv run python scripts/rename_plan_files.py --dry-run
uv run python scripts/rename_plan_files.py

# 3. Update backlog plan references (handled by rename script with --update-backlog)
```

### Hook Runtime Environment Variables

The `task_status_hook.py` script reads two environment variables at runtime to control which handlers execute. These variables allow adjusting hook behavior without editing SKILL.md files.

**`CLAUDE_SKILLS_HOOK_PROFILE`** — selects a named profile. Case-sensitive lowercase. Valid values: `minimal`, `standard`, `strict`. Default when unset or empty: `standard`.

- `minimal` — PostToolUse handler is skipped (no LastActivity updates). SubagentStop runs normally.
- `standard` — all handlers run. Backward compatible with sessions that do not set the variable.
- `strict` — all handlers run. SubagentStop additionally performs pre-completion validation (warns to stderr if task was not claimed or acceptance criteria are empty). Warnings are observational — they do not block completion.

Invalid values produce a warning to stderr and fall back to `standard`.

**`CLAUDE_SKILLS_DISABLED_HOOKS`** — comma-separated hook IDs to disable entirely. Each ID is stripped of whitespace. Empty segments are excluded. Unknown IDs are silently ignored for forward compatibility. Default when unset or empty: no hooks disabled.

Hook IDs for `task_status_hook.py`:

- `task-status:post-tool-use` — the PostToolUse handler (LastActivity timestamp updates)
- `task-status:subagent-stop` — the SubagentStop handler (task completion marking)

Disabled hooks take precedence over profile and exit 0 after consuming stdin (Claude Code treats non-zero hook exit as error).

---

### Deprecation Timeline

- **2026-Q1**: `tasks-{N}-{slug}` naming deprecated. New plans use `P{id}-{slug}.yaml`.
- **2026-Q2**: Legacy markdown bold-field format (`**Status**: ...`) removed from read path after all plans migrated.
- **Future**: `task_format.py` and `implementation_manager.py` fallback parsers removed once all consumers use `sam` CLI.

---

## TaskAssignment Schema Reference

- [Plan Schema](./plan-schema.json) — generated by `uv run sam schema --model Plan`
- [Task Schema](./task-schema.json) — generated by `uv run sam schema --model Task`
- [TaskAssignment Schema](./assignment-schema.json) — generated by `uv run sam schema --model TaskAssignment`

Generate current schema files:

```bash
uv run sam schema --model Plan > plugins/development-harness/docs/plan-schema.json
uv run sam schema --model Task > plugins/development-harness/docs/task-schema.json
uv run sam schema --model TaskAssignment > plugins/development-harness/docs/assignment-schema.json
```

---

## Artifact Manifest Integration

Task-plan artifacts are registered in the artifact manifest with `type: "task-plan"`. The manifest is stored in the GitHub Issue body and serves as the authoritative registry for all plan artifacts.

### MCP Tools for Artifact Management

Four MCP tools support artifact registration and discovery:

```text
artifact_register   -- Register a new artifact in the manifest (adds entry to GitHub Issue body)
artifact_list       -- List all registered artifacts for a plan/issue
artifact_get        -- Get metadata for a specific artifact by path
artifact_read       -- Read artifact content by path (used by worktree-isolated agents)
```

### Auto-Registration via sam_create

When `sam_create` is invoked with an `issue` field present in the plan, it automatically registers the created task-plan artifact in the manifest. No separate `artifact_register` call is needed for the initial plan creation when the issue number is known.

Manual registration is required when:

- The plan is created without an `issue` field and the issue is linked later
- Non-plan artifacts (feature-context, architect-spec) are produced by planning agents

---

## Related Documents

Read these together to get the full system picture:

- [Default Development Flow](../skills/development-harness/references/default-development-flow.md) — S1-S7 stage sequencing, ARL touchpoint gates
- [Artifact Conventions](../skills/development-harness/references/artifact-conventions.md) — naming, file layout, cross-referencing
- [Workflow Architecture Diagram](./workflow-architecture-diagram.md) — data shapes, publisher-consumer map, state machine
- [Plan Artifact Lifecycle](./plan-artifact-lifecycle.md) — immutable vs mutable artifacts, divergence detection
- [Backlog Item Lifecycle](./backlog-item-lifecycle.md) — end-to-end issue journey from creation to closure
- [Domain model source](../sam_schema/core/models.py) — authoritative field definitions (`Task` class)
