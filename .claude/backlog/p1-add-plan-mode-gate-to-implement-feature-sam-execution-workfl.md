---
name: Add plan-mode gate to implement-feature SAM execution workflow before destructive agent dispatch
description: "**Current state**: `plugins/python3-development/skills/implement-feature/SKILL.md` dispatches task agents directly into full execution mode via `Skill(skill='start-task', ...)`. No mechanism exists for the agent to surface a structured plan for human review before the sub-agent executes file edits, bash commands, or other irreversible operations. The `start-task` skill (`plugins/python3-development/skills/start-task/SKILL.md`) claims the task and proceeds immediately to implementation in step 3 without a plan-first gate.\n\n**Target state**: `implement-feature` supports an optional `--plan-first` mode (or task-level flag `plan_review: true` in task YAML frontmatter). When enabled, the sub-agent invoked via `start-task` enters a plan-only phase: it reads task acceptance criteria, produces a structured markdown plan (listing each file it will edit, each bash command it will run, and rationale), writes the plan to `plan/task-plan-{task_id}.md`, and halts. The orchestrator (implement-feature loop) reads the plan file, surfaces it to the user for approval, and only dispatches the full execution agent after approval is received. Rejection returns feedback to the agent and requests a revised plan. This mirrors the `swarm-patterns` Pattern 5 plan_approval_response mechanism but applied at the SAM task level.\n\n**Measurable signal**: `implement-feature` SKILL.md contains a `--plan-first` flag description and a plan-approval step in its Progress Loop section. `start-task` SKILL.md documents a `plan_review: true` task field that triggers plan-only mode before execution. A task YAML file with `plan_review: true` causes `start-task` to write `plan/task-plan-{task_id}.md` and exit before any Write/Edit/Bash tool calls."
metadata:
  topic: add-plan-mode-gate-to-implement-feature-sam-execution-workfl
  source: 'Research entry: ./research/coding-agents/1code.md — pattern: Plan mode before agent mode (Patterns Worth Adopting section)'
  added: '2026-03-17'
  priority: P1
  type: Feature
  status: open
  issue: '#758'
  last_synced: '2026-03-17T01:15:03Z'
  groomed: '2026-03-17'
---

## RT-ICA

<div><sub>2026-03-17T01:07:35Z</sub>

RT-ICA Snapshot: Add plan-mode gate to implement-feature SAM execution workflow
Goal: Add optional plan-first mode to SAM task execution so agents surface a structured plan for human review before irreversible operations.
Conditions:
1. implement-feature SKILL.md execution loop structure is understood | Status: DERIVABLE
2. start-task SKILL.md task claim and execution flow is understood | Status: DERIVABLE
3. Task YAML frontmatter schema supports additional fields | Status: DERIVABLE
4. swarm-patterns Pattern 5 plan_approval_response mechanism exists and is documented | Status: DERIVABLE
5. Plan file naming convention (plan/task-plan-{task_id}.md) does not conflict with existing conventions | Status: DERIVABLE
6. Hook system (SubagentStop, PostToolUse) interaction with plan-only mode is understood | Status: DERIVABLE
7. Agent tool plan mode parameter exists for delegated agents | Status: DERIVABLE
AVAILABLE count: 0
DERIVABLE count: 7
MISSING count: 0
</div>

## Groomed (2026-03-17)

### Issue Classification

<div><sub>2026-03-17T01:08:29Z</sub>

Type: missing-guardrail
Confidence: high
Rationale: The item describes a safety mechanism that should exist but doesn't — a human review/approval gate before destructive operations (file edits, bash commands). Current state directly dispatches agents to execution without plan review. Target state adds an optional --plan-first mode with structured plan output and approval step before execution proceeds. This mirrors the established swarm-patterns Pattern 5 plan_approval_response mechanism, confirming the pattern is proven and bounded. Design is not open-ended because it has clear precedent, specific task-level flag (plan_review: true), specific output file path convention (plan/task-plan-{task_id}.md), and defined approval loop. This is a guardrail (preventing unreviewed agent actions) that is currently absent.
</div>

### Impact

<div><sub>2026-03-17T00:00:00Z</sub>

<div><sub>2026-03-17T01:09:52Z</sub>
</div>

<div><sub>2026-03-17T01:12:43Z</sub>

- **Blocks**: Any developer who wants to review and approve a sub-agent's intended changes before those changes are applied. Currently there is no pause point — the agent executes immediately.
- **Bottleneck**: High-risk or complex tasks where a file edit or bash command error is expensive to reverse. Without this gate, the cost of a mistake is discovered after the fact, during code review or quality gates, when rework is more expensive.
- **User experience change**: When `--plan-first` is passed to `implement-feature` (or `plan_review: true` is set on a task), the orchestrator surfaces a structured plan file at `plan/task-plan-{task_id}.md` before dispatching the execution sub-agent. The user approves or rejects with feedback; rejected plans are revised and re-surfaced.
- **Safety improvement**: The SubagentStop hook false-COMPLETE risk (plan-only sub-agents being marked COMPLETE prematurely) is eliminated by the guard logic added to `task_status_hook.py`.
- **No impact on existing workflows**: The `--plan-first` flag and `plan_review: true` field are opt-in. Tasks without the flag dispatch exactly as they do today.
</div>

### Code — Producers

- `plugins/python3-development/skills/implement-feature/SKILL.md::Progress Loop` — orchestrates task dispatch; needs `--plan-first` flag parsed and routed before the `Skill(skill="start-task", ...)` call. When `--plan-first` is active, the loop must pause after plan generation and surface the plan for approval before dispatching the sub-agent.
- `plugins/python3-development/skills/start-task/SKILL.md::Starting a Task` — executes implementation inside a sub-agent; needs `plan_review: true` field support added to steps 2a-3: if the task YAML contains `plan_review: true`, generate and output a structured plan, then halt and await orchestrator approval signal before claiming and executing.
- `packages/sam_schema/sam_schema/core/models.py::Task` — canonical Pydantic model for task fields; `plan_review` field does not exist. A new optional `plan_review: bool = False` field with `AliasChoices("plan-review", "plan_review")` must be added and `Task.model_rebuild()` updated.
- `packages/sam_schema/sam_schema/writers/yaml_writer.py` — serializes Task model to YAML; will need to round-trip the new `plan_review` field (serialization alias `plan-review`).

### Code — Consumers

- `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py::handle_subagent_stop` — parses the sub-agent prompt for `/start-task` or `Skill(skill="start-task", ...)` invocations to mark tasks COMPLETE. If plan-mode introduces a new sub-agent invocation pattern (e.g. `Skill(skill="start-task", args="... --plan-only ...")`) the regex patterns in `extract_task_info_from_prompt` will miss it and silently skip completion marking. Needs updated regex or guard logic.
- `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py::handle_activity_update` — reads active-task context file written by `/start-task`. If plan-mode halts before writing the context file, PostToolUse events during planning will silently find no context and skip LastActivity updates — this is acceptable but should be verified as intentional.
- `packages/sam_schema/sam_schema/core/query.py` — `get_task`, `update_status`, `update_plan_fields` are the Python API used by the hook; no changes needed unless plan-mode introduces a new status value.
- `packages/sam_schema/sam_schema/cli.py` — `sam ready` output shape (JSON with `skills` per task) is consumed by `implement-feature`; if `plan_review` field is added to the Task model it should appear in `sam ready` output so the orchestrator can gate dispatch. Verify `--format json` output includes new field.

### Documentation (will become stale)

- `.claude/rules/local-workflow.md` — the "Execution Loop" section (steps 1-5) documents the current unconditional dispatch loop with no mention of plan-mode or approval gate; the "Phase 2: Execution" section will need a `--plan-first` branch and human-approval step documented.
- `.claude/rules/local-workflow.md::Phase 2a: Task Execution` — step 3 "Claim the task" will no longer be the first action when `plan_review: true`; sequence must be updated.
- `.claude/rules/local-workflow.md::Hook Script: task_status_hook.py` — Event Handling table documents SubagentStop as unconditionally marking COMPLETE; conditional behavior for plan-only sub-agents must be noted.
- `.claude/rules/local-workflow.md::Data Flow Diagram` — does not show plan-approval branch; diagram needs a plan-mode fork node.
- `.claude/docs/TASK_FILE_FORMAT.md` — Task schema field table does not list `plan_review`; must be added with type, default, and semantics.
- `plugins/python3-development/skills/implementation-manager/SKILL.md` — Hook Configuration table and "How It Works" section describe unconditional SubagentStop → COMPLETE; conditional behavior for plan-mode not covered.

### Configuration / CI

- No CI workflow files directly reference `implement-feature` or `start-task` commands — no CI changes required.
- `packages/sam_schema/pyproject.toml` — no changes needed unless a new `TaskStatus` enum value is introduced (it is not, per the item description).

### Agent Instructions

- `plugins/python3-development/agents/swarm-task-planner.md` — task template fields are emitted here; if `plan_review: true` is a per-task opt-in, the planner needs to know when to set it. The CLEAR task writing section does not include `plan_review` as a valid field. Will need an addendum or new field guidance.
- `plugins/python3-development/agents/context-refinement.md` — references `/python3-development:implement-feature` by name; not structurally affected but may need a note about plan-mode sessions.
- `plugins/development-harness/agents/context-refinement.md` — same reference; same low-risk note.
- `plugins/python3-development/agents/tn-verification-gate.md` — mentions returning to `/implement-feature` for fixes; not structurally affected.
- `.claude/skills/work-backlog-item/references/step-procedures.md` — instructs user `To execute: /implement-feature {slug}` at Steps Q and end of Step 6; if `--plan-first` becomes the recommended invocation for high-risk tasks, this callout should be updated.
- `.claude/skills/work-backlog-item/references/example-sessions.md` — includes three literal `/implement-feature` invocations in example output; informational, low-risk.
- `.claude/skills/work-backlog-item/references/github-integration.md` — one literal `/implement-feature` invocation; informational, low-risk.

### Systems Inventory

| File | Role | Impact |
|---|---|---|
| `plugins/python3-development/skills/implement-feature/SKILL.md` | Orchestrator: dispatches tasks | Code change required — add `--plan-first` flag handling |
| `plugins/python3-development/skills/start-task/SKILL.md` | Executor: claims and runs tasks | Code change required — add `plan_review: true` early-halt path |
| `plugins/python3-development/skills/complete-implementation/SKILL.md` | Quality gate after all tasks COMPLETE | Not directly affected; recursion into `implement-feature` carries the flag if present |
| `plugins/python3-development/skills/add-new-feature/SKILL.md` | Planning upstream of `implement-feature` | Not affected |
| `plugins/python3-development/skills/implementation-manager/SKILL.md` | Documents hook integration | Content update needed |
| `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` | Hook: marks COMPLETE on SubagentStop | Code change required — guard against plan-only sub-agent misclassification |
| `plugins/python3-development/skills/implementation-manager/scripts/get_task_context.py` | Reads active-task context for dynamic injection | Not directly affected |
| `packages/sam_schema/sam_schema/core/models.py::Task` | Canonical task schema | Code change required — add `plan_review` field |
| `packages/sam_schema/sam_schema/writers/yaml_writer.py` | Serializes Task to YAML | Code change required — round-trip new field |
| `packages/sam_schema/sam_schema/core/query.py` | Python API for task read/write | No change unless new status value introduced |
| `packages/sam_schema/sam_schema/cli.py` | `sam ready` JSON output | Verify new field appears in output; no change if model auto-serializes |
| `packages/sam_schema/tests/test_models.py` | Tests Task model fields | Test update required — add `plan_review` field coverage |
| `packages/sam_schema/tests/test_readers/test_legacy_reader.py` | Tests legacy markdown reader | Test update required — verify `plan_review` round-trips in legacy format |
| `packages/sam_schema/tests/test_readers/test_manifest_reader.py` | Tests manifest/YAML reader | Test update required — verify `plan_review` field parsed from YAML |
| `packages/sam_schema/tests/test_writers/test_yaml_writer.py` | Tests YAML serialization | Test update required — verify `plan-review` serialization alias |
| `.claude/rules/local-workflow.md` | Authoritative SAM workflow doc | Content update required — add plan-mode branch throughout |
| `.claude/docs/TASK_FILE_FORMAT.md` | Task field reference | Content update required — document `plan_review` field |
| `plugins/python3-development/agents/swarm-task-planner.md` | Generates task YAML | Agent instruction update — teach when to emit `plan_review: true` |
| `.claude/skills/work-backlog-item/references/step-procedures.md` | Instructs user to invoke `implement-feature` | Low-priority content update — mention `--plan-first` for high-risk tasks |
| `.claude/skills/swarm-patterns/SKILL.md` | Pattern 5 documents plan approval via swarm primitives | Not affected — this is a different mechanism (TeamCreate/SendMessage), not SAM |
| `plugins/python3-development/agents/context-refinement.md` | References implement-feature | Informational only; no change required |
| `plugins/development-harness/agents/context-refinement.md` | References implement-feature | Informational only; no change required |

### Ecosystem Completeness Checklist

- [ ] `Task` Pydantic model gains `plan_review: bool = False` field with `AliasChoices("plan-review", "plan_review")`
- [ ] `implement-feature` SKILL.md documents `--plan-first` flag and plan-approval loop
- [ ] `start-task` SKILL.md documents `plan_review: true` early-halt path (plan generation before claim)
- [ ] `task_status_hook.py::extract_task_info_from_prompt` updated to handle plan-only sub-agent invocation pattern
- [ ] `task_status_hook.py` SubagentStop handler: no false-COMPLETE for plan-only sub-agents
- [ ] `sam ready` JSON output verified to include `plan_review` field
- [ ] `local-workflow.md` Execution Loop, Phase 2a, Hook table, and Data Flow Diagram updated
- [ ] `TASK_FILE_FORMAT.md` field table updated with `plan_review`
- [ ] `implementation-manager/SKILL.md` Hook Configuration table updated
- [ ] `swarm-task-planner` agent: guidance on when to emit `plan_review: true`
- [ ] Tests added/updated: `test_models.py`, `test_legacy_reader.py`, `test_manifest_reader.py`, `test_yaml_writer.py`
- [ ] No new `TaskStatus` enum value required (plan-mode uses `not-started` while awaiting approval)
- [ ] `complete-implementation` recursion path: verify `--plan-first` flag propagates correctly when recursing

</div>

### Reproducibility

<div><sub>2026-03-17T01:12:22Z</sub>

1. Open `plugins/python3-development/skills/implement-feature/SKILL.md` and read the Progress Loop section — observe that the loop calls `Skill(skill="start-task", args="{task_file_path} --task {task_id}")` with no conditional plan-review step between the `sam ready` query and the sub-agent dispatch.
2. Open `plugins/python3-development/skills/start-task/SKILL.md` and read steps 1–6 — observe that step 3 claims the task and step 6 begins implementation immediately; there is no plan generation, plan file write, or user approval step between claim and execution.
3. Create a SAM task file containing a task with `plan_review: true` in its YAML frontmatter — invoke `/implement-feature` — observe that the task is dispatched to `start-task` without a plan-approval pause; the sub-agent executes file edits and bash commands directly.
4. Check `plan/` directory after dispatch — observe that no `task-plan-{task_id}.md` file is written; no plan-approval signal appears in the orchestrator output.

**Observable signal**: The `plan_review` field in task YAML has no effect on dispatch behavior because `implement-feature` does not read it and `start-task` does not check for it before claiming and executing.
</div>

### Priority

<div><sub>2026-03-17T01:12:31Z</sub>

8/10 — Safety guardrail for irreversible operations with bounded implementation scope and proven precedent.

Rationale:
- **Safety impact is direct**: `start-task` sub-agents execute Write, Edit, and Bash tool calls — operations that overwrite files and run shell commands — without any human-approval checkpoint. Loss of data or incorrect edits cannot be undone once a sub-agent completes.
- **Pattern is proven**: swarm-patterns Pattern 5 documents an identical plan-approval mechanism (`mode: "plan"`, `plan_approval_request`, `plan_approval_response`). This is not speculative design — it is an established, fact-checked pattern already present in the codebase.
- **Scope is bounded**: 5 code files + 4 test files + 3 docs + 1 agent instruction. The critical risk (task_status_hook.py false-COMPLETE) is identified and bounded. No new enum values, no schema migrations, no CI changes.
- **Not P0**: The system functions without this gate; existing tasks complete successfully. The missing guardrail increases risk for high-complexity or high-risk tasks but does not block current workflows.
- **Not P2**: The absence of this gate is an active safety gap for any task where destructive changes are hard to review after the fact. It is not cosmetic or speculative.
</div>

### Scope

<div><sub>2026-03-17T01:12:54Z</sub>

**In scope**:
- `implement-feature` SKILL.md: `--plan-first` flag and plan-approval loop in the Progress Loop section
- `start-task` SKILL.md: `plan_review: true` field detection, plan generation step (before claim), plan file write to `plan/task-plan-{task_id}.md`, halt after plan write
- `packages/sam_schema/sam_schema/core/models.py`: add `plan_review: bool = False` field to `Task` model
- `packages/sam_schema/sam_schema/writers/yaml_writer.py`: round-trip `plan_review` / `plan-review` serialization alias
- `task_status_hook.py`: guard `handle_subagent_stop` against false-COMPLETE for plan-only sub-agent invocations
- `sam ready` JSON output: verify `plan_review` field appears (no code change expected if model auto-serializes)
- Documentation: `local-workflow.md` (Execution Loop, Phase 2a, Hook table, Data Flow Diagram), `TASK_FILE_FORMAT.md`, `implementation-manager/SKILL.md`
- Agent instruction: `swarm-task-planner.md` — when to emit `plan_review: true`
- Tests: `test_models.py`, `test_legacy_reader.py`, `test_manifest_reader.py`, `test_yaml_writer.py`

**Out of scope**:
- New `TaskStatus` enum value — plan-mode tasks remain `not-started` while awaiting approval
- CI workflow changes — no CI files reference `implement-feature` or `start-task`
- `swarm-patterns` SKILL.md — Pattern 5 is the source precedent, not modified here
- `complete-implementation` SKILL.md — not structurally affected; recursion propagates the flag if present
- `add-new-feature` SKILL.md — upstream planning phase; not affected
- Mandatory plan-review for all tasks — the gate is opt-in only
</div>

### Expected Behavior

<div><sub>2026-03-17T01:13:11Z</sub>

When `implement-feature` is invoked with `--plan-first`, or when a task in the ready list has `plan_review: true` in its YAML frontmatter:

1. The orchestrator dispatches the sub-agent in plan-only mode (not execution mode).
2. The sub-agent reads the task's acceptance criteria, lists the files it intends to edit, lists each bash command it intends to run, and provides rationale for each action. It writes this structured plan to `plan/task-plan-{task_id}.md`.
3. The sub-agent halts after writing the plan file. No Write, Edit, or Bash tool calls that modify the codebase are made during the plan phase. The task status remains `not-started`.
4. The orchestrator reads `plan/task-plan-{task_id}.md` and surfaces it to the user for review.
5. If the user approves: the orchestrator dispatches the sub-agent again in full execution mode. The sub-agent claims the task, executes against acceptance criteria, and the SubagentStop hook marks the task COMPLETE.
6. If the user rejects with feedback: the orchestrator writes rejection feedback to `plan/task-plan-{task_id}-feedback.md` and re-invokes the plan-only sub-agent. The sub-agent reads the feedback, revises the plan, overwrites `plan/task-plan-{task_id}.md`, and halts again for re-review.
7. Tasks without `plan_review: true` and runs without `--plan-first` behave identically to current behavior — no plan file is written, no approval step occurs, execution proceeds immediately.

The `task_status_hook.py` SubagentStop handler does not mark a plan-only sub-agent as COMPLETE. It distinguishes plan-only invocations from execution invocations by the presence of a `--plan-only` flag or equivalent signal in the sub-agent prompt.
</div>

### Acceptance Criteria

<div><sub>2026-03-17T01:13:20Z</sub>

- [ ] `implement-feature` SKILL.md Progress Loop section documents a `--plan-first` flag; when the flag is present, the loop reads `plan_review` from each task's ready JSON and dispatches plan-only before execution dispatch.
- [ ] `start-task` SKILL.md documents `plan_review: true` as a recognized task YAML field; steps before the claim step describe plan generation and file write behavior when `plan_review: true` is detected.
- [ ] `packages/sam_schema/sam_schema/core/models.py` `Task` model contains a `plan_review: bool = False` field with `AliasChoices("plan-review", "plan_review")`.
- [ ] `sam ready --format json` output for a task with `plan_review: true` in its YAML includes `"plan_review": true` in the task object.
- [ ] A task YAML file with `plan_review: true` processed by `start-task` in plan-only mode produces `plan/task-plan-{task_id}.md` and does not produce any Write, Edit, or Bash calls that modify codebase files.
- [ ] `task_status_hook.py` SubagentStop handler does not mark a plan-only sub-agent invocation as COMPLETE; the task status remains `not-started` after a plan-only run.
- [ ] `task_status_hook.py` SubagentStop handler correctly marks an execution sub-agent invocation as COMPLETE (existing behavior preserved).
- [ ] `local-workflow.md` Phase 2 Execution Loop, Phase 2a Task Execution, Hook Script Event Handling table, and Data Flow Diagram reflect plan-mode branch and conditional COMPLETE behavior.
- [ ] `TASK_FILE_FORMAT.md` field table includes `plan_review` with type `bool`, default `false`, and semantics.
- [ ] `implementation-manager/SKILL.md` Hook Configuration table documents conditional SubagentStop behavior for plan-only sub-agents.
- [ ] `swarm-task-planner.md` agent instruction includes guidance on when to emit `plan_review: true` on a generated task.
- [ ] `test_models.py` includes a test for `plan_review: bool = False` default and `plan-review` alias deserialization.
- [ ] `test_yaml_writer.py` includes a test that a `Task` with `plan_review: true` serializes the field with the `plan-review` alias.
- [ ] `test_manifest_reader.py` and `test_legacy_reader.py` include tests that `plan_review: true` round-trips correctly through each reader.
</div>

### Files

<div><sub>2026-03-17T01:13:34Z</sub>

**Code changes required** (5 files):

| File | Change |
|------|--------|
| `plugins/python3-development/skills/implement-feature/SKILL.md` | Add `--plan-first` flag and plan-approval loop to Progress Loop section |
| `plugins/python3-development/skills/start-task/SKILL.md` | Add `plan_review: true` early-halt path before task claim |
| `packages/sam_schema/sam_schema/core/models.py` | Add `plan_review: bool = False` field with `AliasChoices` to `Task` model |
| `packages/sam_schema/sam_schema/writers/yaml_writer.py` | Round-trip `plan_review` / `plan-review` serialization alias |
| `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` | Guard `handle_subagent_stop` against false-COMPLETE for plan-only sub-agents |

**Test changes required** (4 files):

| File | Change |
|------|--------|
| `packages/sam_schema/tests/test_models.py` | Add `plan_review` field coverage |
| `packages/sam_schema/tests/test_readers/test_legacy_reader.py` | Verify `plan_review` round-trips in legacy format |
| `packages/sam_schema/tests/test_readers/test_manifest_reader.py` | Verify `plan_review` field parsed from YAML |
| `packages/sam_schema/tests/test_writers/test_yaml_writer.py` | Verify `plan-review` serialization alias |

**Documentation changes required** (3 files):

| File | Change |
|------|--------|
| `.claude/rules/local-workflow.md` | Update Execution Loop, Phase 2a, Hook Event Handling table, Data Flow Diagram |
| `.claude/docs/TASK_FILE_FORMAT.md` | Add `plan_review` field to Task schema field table |
| `plugins/python3-development/skills/implementation-manager/SKILL.md` | Update Hook Configuration table for conditional SubagentStop behavior |

**Agent instruction changes required** (1 file):

| File | Change |
|------|--------|
| `plugins/python3-development/agents/swarm-task-planner.md` | Add guidance on when to emit `plan_review: true` |

**Verification only — no change expected** (1 file):

| File | Change |
|------|--------|
| `packages/sam_schema/sam_schema/cli.py` | Verify `sam ready --format json` includes `plan_review` field after model update |
</div>

### Dependencies

<div><sub>2026-03-17T01:13:37Z</sub>

- Depends on: None — all prerequisite information (swarm-patterns Pattern 5, task_status_hook.py SubagentStop logic, sam_schema Task model, start-task and implement-feature SKILL.md structures) is available in the current codebase. RT-ICA assessment: APPROVED with 0 MISSING conditions.
- Blocks: None identified in current backlog. This feature unlocks safer dispatch for high-risk SAM tasks but no existing backlog items are gated on it.
</div>

### Effort

<div><sub>2026-03-17T01:13:52Z</sub>

Medium — 3–5 focused sessions.

Rationale:
- **Schema change** (models.py + yaml_writer.py + 4 test files): Small. Adding one `bool` field with an alias is a well-worn pattern in this codebase. Tests follow existing patterns in test_models, test_readers, test_yaml_writer.
- **Hook guard** (task_status_hook.py): Small-Medium. The SubagentStop handler has a defined regex-based detection path. Adding plan-only detection requires understanding the invocation pattern and adding a conditional branch. Risk is bounded by existing tests.
- **SKILL.md changes** (implement-feature + start-task): Medium. These are instruction files, not code — but the plan-approval loop in implement-feature requires careful description of the plan-only dispatch, file-read, user-surface, approve/reject, and re-invoke cycle. The start-task early-halt path requires inserting a pre-claim step that generates and writes the plan file.
- **Documentation** (local-workflow.md, TASK_FILE_FORMAT.md, implementation-manager/SKILL.md): Small-Medium. local-workflow.md is the most involved — Execution Loop, Phase 2a, Hook table, and Data Flow Diagram all need updates.
- **Agent instruction** (swarm-task-planner.md): Small. One addendum on when to set `plan_review: true`.
- **No unknowns**: All design decisions are resolved. The RT-ICA assessment has 0 MISSING conditions. The Ecosystem Completeness Checklist provides 13 concrete implementation checkpoints.
</div>

### Resources

<div><sub>2026-03-17T01:14:00Z</sub>

| Type | Item |
|------|------|
| Pattern precedent | `.claude/skills/swarm-patterns/SKILL.md` lines 182–218 — Pattern 5 "Plan Approval Workflow" with `mode: "plan"`, `plan_approval_request`, `plan_approval_response` approve/reject logic |
| Primary skill (orchestrator) | `plugins/python3-development/skills/implement-feature/SKILL.md` — Progress Loop section (lines 55–75): current dispatch path to modify |
| Primary skill (executor) | `plugins/python3-development/skills/start-task/SKILL.md` — steps 1–6: claim-and-execute flow to extend with plan-first path |
| Hook script | `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` — `handle_subagent_stop` and `extract_task_info_from_prompt` functions |
| Schema model | `packages/sam_schema/sam_schema/core/models.py` — `Task` Pydantic model with `AliasChoices` pattern |
| YAML serializer | `packages/sam_schema/sam_schema/writers/yaml_writer.py` — serialization alias conventions |
| Test patterns | `packages/sam_schema/tests/test_models.py`, `test_readers/`, `test_writers/` — existing field and round-trip test patterns |
| Workflow doc | `.claude/rules/local-workflow.md` — authoritative Phase 2 Execution section and Data Flow Diagram |
| Schema doc | `.claude/docs/TASK_FILE_FORMAT.md` — Task field reference table |
| Agent instruction | `plugins/python3-development/agents/swarm-task-planner.md` — CLEAR task writing section |
| Research source | `./research/coding-agents/1code.md` — "Plan mode before agent mode" pattern (item origin) |
</div>


## Fact-Check

<div><sub>2026-03-17T01:08:48Z</sub>

Claims checked: 5
VERIFIED: 5
REFUTED: 0
INCONCLUSIVE: 0

1. CLAIM: "implement-feature dispatches task agents directly into full execution mode via Skill(skill='start-task', ...)"
   VERDICT: VERIFIED
   EVIDENCE: File: plugins/python3-development/skills/implement-feature/SKILL.md, lines 71-75 — exact quote: "Launch the agent with a prompt that invokes `start-task`: `Skill(skill="start-task", args="{task_file_path} --task {task_id}")`"

2. CLAIM: "No mechanism exists for the agent to surface a structured plan for human review before the sub-agent executes file edits"
   VERDICT: VERIFIED
   EVIDENCE: File: plugins/python3-development/skills/start-task/SKILL.md — task execution flow (steps 1-6) shows no plan-review gate. Step 6 proceeds directly: "Implement against the task acceptance criteria and run its verification steps." No intermediate plan-approval step exists in either implement-feature or start-task SKILL.md.

3. CLAIM: "start-task claims the task and proceeds immediately to implementation in step 3 without a plan-first gate"
   VERDICT: VERIFIED
   EVIDENCE: File: plugins/python3-development/skills/start-task/SKILL.md, steps 3-6 — step 3 (lines 69-90): claim task via `sam claim`. Step 4 (lines 92-105): write context file. Step 5 (lines 107-138): record divergence notes. Step 6 (line 140): "Implement against the task acceptance criteria...". No plan-approval step exists between task claim and implementation start.

4. CLAIM: "This mirrors the swarm-patterns Pattern 5 plan_approval_response mechanism"
   VERDICT: VERIFIED
   EVIDENCE: File: .claude/skills/swarm-patterns/SKILL.md, lines 182-218 — Pattern 5 titled "Plan Approval Workflow" documents: (line 196) `mode: "plan"` parameter, (line 201) plan_approval_request message handling, (lines 204-217) plan_approval_response mechanism with approve/reject logic. The pattern is proven and documented.

5. CLAIM: "Agent tool has a plan mode parameter for delegated agents"
   VERDICT: VERIFIED
   EVIDENCE: File: .claude/skills/swarm-patterns/SKILL.md, lines 191-198 — Agent call with explicit parameter: `mode: "plan",  // Requires plan approval`. This is used in Pattern 5 to control whether the agent enters plan-only mode (requiring explicit approval) vs. direct execution mode. The mechanism is documented and instantiated in working example code.
</div>

## RT-ICA

<div><sub>2026-03-17T01:15:03Z</sub>

RT-ICA Final: Add plan-mode gate to implement-feature SAM execution workflow
Goal: Add optional plan-first mode so agents surface structured plans for human review before irreversible operations.
Conditions:
1. implement-feature execution loop structure | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: Fact-check verified dispatch via Skill(skill='start-task') at SKILL.md lines documented
2. start-task claim and execution flow | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: Fact-check verified immediate claim+execute at step 3
3. Task YAML schema extensibility | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: Impact-analyst confirmed sam_schema Task model at models.py supports new fields
4. Pattern 5 plan_approval_response precedent | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: Fact-check verified at swarm-patterns SKILL.md lines 182-218
5. Plan file naming conflict check | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: Impact-analyst found no conflicts; plan/task-plan-{task_id}.md is unique
6. Hook system interaction (critical risk) | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: Impact-analyst identified SubagentStop false-COMPLETE risk; groomer included guard logic in acceptance criteria
7. Agent tool plan mode parameter | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: Fact-check verified mode="plan" at Pattern 5 example code line 196
8. Plan-ready signal mechanism | Snapshot: (new) DERIVABLE → Final: AVAILABLE | Citation: Groomer Expected Behavior describes write-plan-and-exit signal
9. Per-task vs per-plan-run scope | Snapshot: (new) DERIVABLE → Final: AVAILABLE | Citation: Groomer resolves both: plan_review (per-task YAML) and --plan-first (per-run flag)
10. Rejection feedback loop design | Snapshot: (new) DERIVABLE → Final: AVAILABLE | Citation: Groomer Expected Behavior step 7 describes re-spawn with feedback

Changes from snapshot:
- Conditions 1-7: DERIVABLE → AVAILABLE (resolved by fact-checker and impact-analyst in Wave 1)
- Conditions 8-10: new conditions added by impact-analyst, resolved by groomer in Wave 3
AVAILABLE count: 10
DERIVABLE count: 0
MISSING count: 0
Decision: APPROVED
</div>