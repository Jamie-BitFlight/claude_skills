---
name: SAM bookend validation — baseline capture (T0) and verification gate (TN) as mandatory plan tasks
description: "Every SAM plan needs two mandatory bookend tasks that bracket implementation work. T0 (baseline capture) runs before any implementation — it executes the plan's acceptance criteria against the current codebase and records what passes and fails. TN (verification gate) runs after all implementation tasks — it re-runs the same checks and compares against the baseline. This is TDD at the plan level.\n\nThe problem: the current swarm-task-planner creates implementation tasks and test-writing tasks but never creates a 'prove it works' task. The feature-verifier runs as a post-completion quality gate outside the plan, but it checks structure (task count, field presence) not behavior (does the feature actually work end-to-end). This allowed a converter that destroyed content to pass validation.\n\nWhat's needed:\n1. Plan schema: add structured acceptance_criteria field with check_command, expected_baseline, expected_final per criterion. Add goal and context fields.\n2. swarm-task-planner: auto-generate T0 (baseline) and TN (verification gate) from the acceptance criteria.\n3. T0 agent: runs each check command, records actual output, writes structured baseline YAML.\n4. TN agent: re-runs baseline checks, compares results, produces pass/fail/regressed report.\n5. Verdict: if any baseline-failing check is still failing after implementation, the plan is incomplete — more iterations needed.\n\nWhat success looks like: running /implement-feature produces a T0-baseline.yaml before implementation starts and a TN-verification.yaml after it completes. The verification report shows which checks flipped from failing to passing.\n\nHow you'll know it's working: the content-destroyer bug (readers stripping markdown body during conversion) would have been caught by TN — the verification check 'load .md, write .yaml, compare content length' would have failed."
metadata:
  topic: sam-bookend-validation-baseline-capture-t0-and-verification-
  source: Session observation — feature verification passed structural checks but missed behavioral failure (content loss during format conversion, 2026-03-15)
  added: '2026-03-15'
  priority: completed
  type: Feature
  status: done
  issue: '#718'
  last_synced: '2026-03-15T05:30:21Z'
  groomed: '2026-03-15'
  plan: plan/tasks-5-sam-bookend-validation.md
---

## Fact-Check

<div><sub>2026-03-15T05:25:54Z</sub>

Claims checked: 3 (all internal tooling claims — verified against codebase, not web sources)

[VERIFIED] "feature-verifier checks structure not behavior" — the feature-verifier agent (plugins/python3-development/agents/feature-verifier.md) performs goal-backward verification starting from expected outcomes. However, its checks are based on file existence, function presence, and structural properties — not on executing acceptance criteria commands and comparing output. It does not run behavioral tests against the implementation.
Evidence: Agent file inspection, session observation 2026-03-15

[VERIFIED] "swarm-task-planner never creates a 'prove it works' task" — the swarm-task-planner agent (plugins/python3-development/agents/swarm-task-planner.md) generates implementation tasks and test-writing tasks. No task template includes running acceptance criteria before or after implementation to capture baseline/final state.
Evidence: Agent file inspection, task file output from multiple SAM sessions

[VERIFIED] "a converter that destroyed content passed validation" — observed in session 2026-03-15: three legacy format readers in the unified SAM task schema module stripped markdown body content during YAML conversion. The feature-verifier passed structural checks (task count, field presence) without detecting the content loss.
Evidence: Session transcript 2026-03-15, commits 03a806da and 3da1780e (fix commits for the content destruction)
</div>

## RT-ICA

<div><sub>2026-03-15T05:26:10Z</sub>

Goal: SAM plans automatically capture pre-implementation baseline (T0) and post-implementation verification (TN) so behavioral failures are caught before completion is claimed.

Conditions:
1. Current swarm-task-planner agent workflow is documented | Status: AVAILABLE | File: plugins/python3-development/agents/swarm-task-planner.md
2. Current feature-verifier agent workflow is documented | Status: AVAILABLE | File: plugins/python3-development/agents/feature-verifier.md
3. SAM task file format is documented | Status: AVAILABLE | File: .claude/docs/TASK_FILE_FORMAT.md
4. Plan schema supports acceptance_criteria field | Status: MISSING | Current schema has no structured acceptance_criteria with check_command/expected fields
5. T0 agent definition exists | Status: MISSING | No agent for baseline capture exists
6. TN agent definition exists | Status: MISSING | No agent for verification gate exists
7. /implement-feature skill integrates T0/TN into execution loop | Status: DERIVABLE | The skill already has a task execution loop; T0 and TN would be regular tasks with special Priority/ordering
8. Baseline/verification output format defined | Status: MISSING | No YAML schema for T0-baseline.yaml or TN-verification.yaml
9. Evidence of the failure this prevents | Status: AVAILABLE | Content-destroyer bug in session 2026-03-15 (commits 03a806da, 3da1780e)
10. Interaction with /complete-implementation quality gates | Status: DERIVABLE | TN runs inside the plan; /complete-implementation runs after — they are complementary, not conflicting

Decision: APPROVED (with 4 MISSING conditions to resolve during planning)
Missing: plan schema acceptance_criteria field, T0 agent, TN agent, baseline/verification YAML format
</div>

## Groomed (2026-03-15)

### Issue Classification

<div><sub>2026-03-15T05:26:20Z</sub>

Type: missing-guardrail
Scenario-target: SAM plan completes all implementation tasks and passes feature-verifier structural checks, but the implemented feature has a behavioral defect (e.g., data loss, wrong output) that goes undetected until a human inspects the output.
Analysis method: none (missing-guardrail does not require RCA)
Guardrail needed: mandatory T0 (baseline) and TN (verification gate) tasks that execute acceptance criteria commands and compare results — catching behavioral failures that structural checks miss.
</div>

### Priority

<div><sub>2026-03-15T05:28:13Z</sub>

9/10 — The content-destruction bug that motivated this item (session 2026-03-15, commits 03a806da and 3da1780e) passed all existing validation gates. The feature-verifier confirmed structural properties (task count, field presence) but had no mechanism to detect behavioral data loss. Without T0/TN bookends, the only signal that a feature destroyed content was human inspection after completion. This pattern recurs whenever acceptance criteria are not executed — not just inspected.
</div>

### Reproducibility

<div><sub>2026-03-15T05:28:25Z</sub>

1. Create or use an existing SAM plan file with at least one acceptance criterion expressed as a runnable command (e.g., `uv run pytest tests/test_feature.py -v`).
2. Run `/implement-feature` on the plan.
3. Observe: the orchestrator dispatches implementation tasks and marks them complete.
4. Run `/complete-implementation` on the same plan.
5. Observe: the feature-verifier reports `VERIFIED` based on file existence and structural checks.
6. Inspect actual feature behavior by running the acceptance criterion command manually.
7. Observe: the command may fail or produce incorrect output — but the SAM pipeline already declared success.

Verified instance (session 2026-03-15): three legacy-format readers in the unified SAM task schema module stripped markdown body content during YAML conversion. The feature-verifier confirmed task count and field presence. Content loss was discovered only by manually examining output files. Fixes: commits 03a806da and 3da1780e.
</div>

### Output / Evidence

<div><sub>2026-03-15T05:28:35Z</sub>

- The content-destruction bug: run `git show 03a806da` to see the fix — three readers in the legacy format path were stripping markdown body content from task files during conversion. The feature-verifier reported VERIFIED immediately before the content loss was discovered.
- Any session where `/complete-implementation` produces `VERIFIED` but manual spot-check of output files reveals incorrect or absent content demonstrates the gap.
- To see the gap today: run `uv run pytest packages/sam_schema/` — tests verify structural parsing correctness, not end-to-end behavioral outcomes against acceptance criteria commands.
</div>

### Impact

<div><sub>2026-03-15T05:28:44Z</sub>

- Blocks: All SAM plans where acceptance criteria include runnable commands — without T0/TN, those commands are never executed during the SAM pipeline. Implementation can destroy, corrupt, or omit behavior without triggering a failure.
- Bottleneck: The feature-verifier (post-completion quality gate) checks structural properties only — file existence, task count, field presence. It cannot detect behavioral failures because it does not run commands.
- Downstream: Any agent or human consuming the output of a SAM-managed feature inherits defects silently passed by structural-only validation.
</div>

### Benefits

<div><sub>2026-03-15T05:28:52Z</sub>

- Behavioral regressions introduced during implementation are caught before `/complete-implementation` declares the feature done.
- The T0 baseline makes "what was already broken" explicit — T0-failing checks that remain failing after TN are separated from implementation regressions (newly failing checks), preventing false blame on implementation work.
- Plan acceptance criteria become executable contracts, not aspirational prose — the swarm-task-planner must write runnable commands, not narrative descriptions.
- Developers gain observable evidence of what changed: the TN verification report shows exactly which checks flipped from failing to passing.
</div>

### Expected Behavior

<div><sub>2026-03-15T05:29:02Z</sub>

When `/implement-feature` starts, the first dispatched task is T0 (baseline capture). T0 runs each `check_command` from the plan's structured acceptance criteria, records the actual output (pass/fail/stdout/stderr), and writes `plan/T0-baseline-{slug}.yaml`. No implementation task starts until T0 completes.

After all implementation tasks complete and before `/complete-implementation` runs, TN (verification gate) executes. TN re-runs every `check_command` from the same acceptance criteria, compares each result against the T0 baseline, and writes `plan/TN-verification-{slug}.yaml` with a pass/fail/regressed status for each criterion.

The TN report is the final gate before the plan is declared complete. If any criterion that was passing at T0 is now failing at TN, the plan is incomplete — more iterations are needed. If any criterion that was failing at T0 is still failing at TN, that is expected (pre-existing state) and does not block completion unless the acceptance criterion was designated as a required flip.
</div>

### Desired Structure

<div><sub>2026-03-15T05:29:17Z</sub>

The target state has four observable components:

**Structured acceptance criteria in the plan schema** (observable): the `sam_schema` Pydantic `Task` model gains a structured `AcceptanceCriterion` model alongside the existing `acceptance_criteria` markdown field. Each criterion has a `check_command` (runnable shell command), `expected_baseline` (pass/fail at T0), and `expected_final` (required outcome at TN). The `swarm-task-planner` writes these fields into plan YAML. The field is optional for tasks without executable criteria.

**T0 task auto-generated in every plan** (observable): when `swarm-task-planner` writes a plan that includes at least one task with structured acceptance criteria, a T0 task is automatically inserted at Priority 1 with dependencies: none, and all other tasks depend on T0. Running `sam ready P1` before any implementation task starts returns T0 as the only ready task.

**T0-baseline YAML file written** (observable): after T0 completes, `plan/T0-baseline-{slug}.yaml` exists. It contains one entry per criterion: `criterion_id`, `check_command`, `stdout`, `stderr`, `exit_code`, `timestamp`. The file is readable by `sam_schema` readers.

**TN task auto-generated and TN verification YAML written** (observable): TN is inserted at the terminal priority level, dependent on all implementation tasks. After TN completes, `plan/TN-verification-{slug}.yaml` exists with one entry per criterion: `criterion_id`, `check_command`, `t0_exit_code`, `tn_exit_code`, `status` (`passed`, `regressed`, `pre-existing-fail`, `newly-passing`). The TN report is the final artifact before `/complete-implementation` runs.
</div>

### Acceptance Criteria

<div><sub>2026-03-15T05:29:29Z</sub>

1. `sam ready P1` on a newly created plan returns only T0 as the ready task — no implementation tasks are ready until T0 completes.
2. After T0 completes, `plan/T0-baseline-{slug}.yaml` exists and contains one entry per structured acceptance criterion with `check_command`, `exit_code`, `stdout`, `stderr`, and `timestamp`.
3. After all implementation tasks complete, `plan/TN-verification-{slug}.yaml` exists and contains one entry per criterion with `t0_exit_code`, `tn_exit_code`, and `status` in (`passed`, `regressed`, `pre-existing-fail`, `newly-passing`).
4. If any criterion has `status: regressed` in the TN verification YAML, `/complete-implementation` does not proceed — it surfaces the regression as a blocking failure with the criterion's `check_command` and diff of stdout.
5. If all criteria have `status` in (`passed`, `pre-existing-fail`, `newly-passing`) — no regressions — `/complete-implementation` proceeds normally.
6. The `swarm-task-planner` agent produces at least one task in a test plan that includes a structured `check_command` field when the input feature description includes runnable acceptance criteria.
7. The content-destruction scenario: a plan whose T0 criterion runs `uv run pytest tests/test_conversion.py::test_body_preserved -v` and exits 0 (content present before implementation) would produce `status: regressed` in TN if the implementation strips body content — blocking completion.
</div>

### Resources

<div><sub>2026-03-15T05:29:44Z</sub>

| Type | Item |
|------|------|
| Prior work — task schema | `packages/sam_schema/sam_schema/core/models.py` — `Task` model with `acceptance_criteria` as plain markdown string; needs structured `AcceptanceCriterion` extension |
| Prior work — schema package | `packages/sam_schema/` — full Pydantic schema module from #715; YAML readers, writers, CLI, MCP server |
| Prior work — task format spec | `.claude/docs/TASK_FILE_FORMAT.md` — canonical field definitions |
| Agent | `@python3-development:swarm-task-planner` — `plugins/python3-development/agents/swarm-task-planner.md` — produces plan tasks; must be updated to auto-generate T0 and TN |
| Agent | `@python3-development:feature-verifier` — `plugins/python3-development/agents/feature-verifier.md` — current post-completion structural verifier; TN is its behavioral complement inside the plan |
| Workflow doc | `.claude/rules/local-workflow.md` — SAM workflow end-to-end; T0 inserts before implementation tasks, TN inserts after |
| Script | `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` — task readiness logic; must treat T0 as a precondition for all other tasks |
| Script | `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` — completion hook; triggers TN gate check |
| Evidence | Commits 03a806da and 3da1780e (2026-03-15) — content-destruction fix that would have been caught by TN |
</div>

### Dependencies

<div><sub>2026-03-15T05:29:55Z</sub>

- Depends on: #715 (Unified task/plan schema module) — the structured `AcceptanceCriterion` Pydantic model must be added to `packages/sam_schema/sam_schema/core/models.py`. #715 is closed/in-progress as of 2026-03-15; the `sam_schema` package exists but `acceptance_criteria` is currently a plain markdown string field. This item requires extending the model before T0/TN tasks can read structured criteria.
- Blocks: None identified — no current backlog items are waiting on T0/TN bookend validation.
- Related (not blocking): #88 (SAM: Artifact Schema Validation) — overlapping intent; #88 covers schema validation of plan artifact structure, this item covers behavioral execution of acceptance criteria. They are complementary but independent.
- Related (not blocking): #314 (Add Process Quality Discipline to SAM pipeline) — same pipeline, different layer; #314 adds issue classification and proportional response, this item adds behavioral verification gates.
</div>

### Blockers

<div><sub>2026-03-15T05:30:09Z</sub>

RT-ICA status: APPROVED with 4 MISSING conditions — all are design decisions for the planning phase, not external blockers.

1. **Structured `AcceptanceCriterion` schema** — `packages/sam_schema/sam_schema/core/models.py` currently defines `acceptance_criteria` as a plain markdown string. A structured model with `check_command`, `expected_baseline`, and `expected_final` must be designed and added. Dependency: #715 must have landed the `sam_schema` package (it has, as of 2026-03-15 — confirmed via `packages/sam_schema/` glob).

2. **T0 agent definition** — no T0 baseline-capture agent file exists in `plugins/python3-development/agents/`. The agent name, tool access (Bash for running check commands), and output format (T0-baseline YAML) must be defined.

3. **TN agent definition** — no TN verification-gate agent file exists. The agent must read T0-baseline YAML, re-run check commands, compare results, and write TN-verification YAML.

4. **Baseline/verification YAML format** — no schema for `T0-baseline-{slug}.yaml` or `TN-verification-{slug}.yaml` is defined. Fields: `criterion_id`, `check_command`, `exit_code`, `stdout`, `stderr`, `timestamp` (T0); `criterion_id`, `t0_exit_code`, `tn_exit_code`, `status` (TN). The planning phase must formalize these.

No external systems, approvals, or infrastructure changes block planning from starting now.
</div>

### Effort

<div><sub>2026-03-15T05:30:21Z</sub>

High — Five components must be designed and built:

1. **Schema extension** (`packages/sam_schema/`) — add `AcceptanceCriterion` Pydantic model with `check_command`, `expected_baseline`, `expected_final`; extend `Task` model; update YAML readers/writers to handle both plain-string and structured forms; add tests.
2. **T0 agent** — new agent file in `plugins/python3-development/agents/`; Bash tool access; reads plan structured criteria; writes T0-baseline YAML; must handle command failures gracefully (non-zero exit is expected at T0 for pre-failing checks).
3. **TN agent** — new agent file; reads T0-baseline YAML and plan criteria; re-runs commands; computes `status` per criterion; writes TN-verification YAML; surfaces regressions.
4. **swarm-task-planner update** — agent instructions must auto-generate T0 and TN tasks with correct dependencies, priority ordering, and agent assignments whenever the plan includes structured acceptance criteria.
5. **implement-feature / complete-implementation integration** — T0 must be the first dispatched task; TN verdict must be checked before `/complete-implementation` proceeds; local-workflow.md must document the bookend protocol.

Complexity driver: command execution in an agent context (Bash tool), comparing YAML outputs, and threading the verdict through the existing hooks and quality gates without breaking the current flow.
</div>