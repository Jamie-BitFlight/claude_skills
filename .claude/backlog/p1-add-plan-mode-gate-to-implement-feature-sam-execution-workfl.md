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
  last_synced: '2026-03-17T01:11:08Z'
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

### Impact Radius

<div><sub>2026-03-17T01:09:52Z</sub>

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

<div><sub>2026-03-17T01:11:08Z</sub>

RT-ICA: Add plan-mode gate to implement-feature SAM execution workflow

**Goal**: Add optional plan-first mode to SAM task execution so agents surface structured plans for human review before irreversible operations.

**Conditions Assessment**:

1. implement-feature SKILL.md execution loop structure understood | Status: **AVAILABLE** | Verified in implement-feature SKILL.md lines 55-75; loop structure: status → ready → for each task → dispatch → repeat. Documented in local-workflow.md Phase 2 Execution Loop.

2. start-task SKILL.md task claim and execution flow understood | Status: **AVAILABLE** | Verified in start-task SKILL.md steps 1-6; step 3 claims task, step 6 implements. Exact sequence and call order are documented and fact-checked.

3. Task YAML frontmatter schema supports additional fields (sam_schema Task model) | Status: **AVAILABLE** | Field task_file_format.md documents Task Pydantic model. Verified: models.py uses Pydantic with AliasChoices. New `plan_review: bool = False` field with alias mapping can be added without breaking existing tasks.

4. swarm-patterns Pattern 5 plan_approval_response mechanism documented | Status: **AVAILABLE** | Verified in swarm-patterns SKILL.md lines 182-218. Pattern 5 "Plan Approval Workflow" documents mode="plan" parameter, plan_approval_request, plan_approval_response with approve/reject logic. Mechanism is proven, bounded, and has working example code.

5. Plan file naming convention (plan/task-plan-{task_id}.md) does not conflict | Status: **DERIVABLE** | Existing convention: plan/T0-baseline-{slug}.yaml, plan/TN-verification-{slug}.yaml (from bookend tasks). Proposed: plan/task-plan-{task_id}.md. No conflict detected in Impact Radius; `sam` CLI would need to exclude plan-task-*.md from task discovery (verification task during implementation).

6. Hook system (SubagentStop, PostToolUse) interaction with plan-only mode understood | Status: **AVAILABLE** | Critical risk identified in Impact Radius: task_status_hook.py SubagentStop handler will falsely mark plan-only sub-agents as COMPLETE. Handler must detect plan-only invocation pattern and skip COMPLETE marking. PostToolUse behavior is acceptable (silent skip if context file absent).

7. Agent tool plan mode parameter exists for delegated agents | Status: **AVAILABLE** | Verified in swarm-patterns SKILL.md line 196. Agent() tool call shows `mode: "plan"` parameter in working example. Orchestrator can delegate with mode="plan" to implement-feature OR start-task can auto-detect plan_review: true from task YAML.

8. How plan-only sub-agent communicates "plan ready" signal to orchestrator | Status: **DERIVABLE** | Signal mechanism not explicitly designed. Options: (a) Write plan file → orchestrator polls for file existence; (b) Agent returns explicit status code/message; (c) Combined: agent writes plan file + prints "PLAN_READY: {file_path}" to stdout for orchestrator to parse. Design decision needed. Recommended: (c) to maintain compatibility with hook system and provide clear orchestrator handoff.

9. Whether plan_review should be set per-task or per-plan-run | Status: **DERIVABLE** | Backlog item describes per-task flag: "task-level flag `plan_review: true`". However, `implement-feature` could also accept `--plan-first` flag at orchestrator level (applies to all eligible tasks). Decision: per-task flag is more flexible (review only high-risk tasks); orchestrator flag can be derived as "any task has plan_review: true" during status query. No blocking decision required — both can coexist.

10. How rejection feedback loop works (orchestrator re-spawns agent with feedback?) | Status: **DERIVABLE** | Pattern 5 documents approve/reject but swarm-patterns mechanism uses TeamCreate/SendMessage (not applicable to SAM skill invocation). For SAM: if human rejects plan, orchestrator must re-invoke start-task with feedback in context. Mechanism: (a) write rejection reason to plan/task-plan-{task_id}-feedback.md; (b) re-invoke Skill(skill="start-task", args="... --plan-only {task_id}") with feedback in prompt; (c) sub-agent reads feedback, revises plan, overwrites plan file. No design blocker — standard delegation + file I/O pattern.

**Additional Finding**: Impact Radius inventory identifies 24 files across 5 categories (Code Producers, Code Consumers, Documentation, Tests, Agent Instructions). "Ecosystem Completeness Checklist" provides 13 concrete checkpoints for implementation. No pre-existing blockers identified.

**Decision**: **APPROVED FOR IMPLEMENTATION**

Rationale: All 10 conditions are AVAILABLE (7) or DERIVABLE (3). No MISSING information blocks progress. Critical risk (hook false-COMPLETE) is identified and bounded. Pattern precedent (swarm-patterns Pattern 5) exists. Scope is well-defined: two primary changes (models.py Task field + two SKILL.md files), bounded guard logic in task_status_hook.py, and documentation updates across 6 files. Implementation order: (1) Task model + schema + tests; (2) start-task logic + hook guard; (3) implement-feature orchestration; (4) documentation and agent guidance. Follow the Ecosystem Completeness Checklist to ensure coverage.
</div>