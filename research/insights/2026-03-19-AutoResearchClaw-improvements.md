# Improvement Proposals: AutoResearchClaw

**Research entry**: ./research/agent-infrastructure/AutoResearchClaw.md
**Generated**: 2026-03-19
**Patterns assessed**: 3
**Backlog items created**: 0
**Deferred (low confidence)**: 0
**Deferred (medium confidence)**: 3
**Skipped (already covered or tracked)**: 0

---

## Improvement 1: Autonomous PIVOT/REFINE decision point in SAM execution loop

**Source pattern**: "Stage 15 analyzes results and decides next action. PROCEED -> advance to paper writing. REFINE -> tweak hyperparameters, re-run experiments (jump to Stage 13). PIVOT -> new research direction identified, return to Stage 8." (Section: Key Features > 6. Autonomous PIVOT/REFINE Decision Loop)
**Local system**: plugins/python3-development/skills/implement-feature/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the local SAM execution loop uses discrete task files with a linear forward-only dispatch model (ready -> in-progress -> complete). Implementing PIVOT/REFINE would require new task statuses (e.g., NEEDS_REFINEMENT, PIVOTED), a decision agent that evaluates intermediate results, and loopback logic in the Progress Loop. The research entry's pattern operates within a monolithic 23-stage pipeline DAG, which is architecturally different from SAM's per-task dispatch. Confirming this gap is actionable would require prototyping the decision agent and verifying it integrates with the existing readiness logic and hook system.

### Current state

The `/implement-feature` Progress Loop (implement-feature/SKILL.md, lines 37-81) dispatches ready tasks sequentially. When a task completes, the SubagentStop hook marks it COMPLETE unconditionally. There is no mechanism for an agent to signal "results are unsatisfactory -- re-run with different parameters" or "approach is wrong -- pivot to alternative." The only adaptive path is post-completion follow-up task creation by `code-reviewer` in `/complete-implementation`, which creates new task files rather than re-routing existing ones.

Related backlog items exist but do not cover this gap:
- #85 "SAM: Error Recovery / Rollback Procedures" -- covers rollback on failure, not autonomous result-quality-based rerouting
- #758 "Add plan-mode gate to implement-feature" -- covers pre-execution gating, not mid-execution adaptive decisions

### Target state

The implement-feature execution loop includes an optional decision step after task completion: a lightweight evaluation agent reads the task's output artifacts and acceptance criteria results, then emits one of PROCEED / REFINE / PIVOT. REFINE re-opens the task with updated parameters (new status: `NEEDS_REFINEMENT`, retry count incremented). PIVOT creates a new task branch from the current point. The decision agent's output is a structured JSON record logged to the task file.

### Measurable signal

After implementing a task, `uv run sam read P{N}/T{M} --format json` includes a `decision` field with value `proceed`, `refine`, or `pivot`. Tasks with `refine` show `retry_count > 0` in their metadata. The implement-feature loop re-dispatches REFINE tasks without manual intervention.

---

## Improvement 2: Structured self-healing repair loop for task execution failures

**Source pattern**: "Runs experiment code in sandbox; captures stdout, stderr, and metrics. If experiment fails: 1. Parse error message 2. Route to LLM with error context + original code 3. LLM generates targeted fix 4. Re-run in sandbox (up to 10 refinement cycles). Logs all repair attempts and final success/failure status." (Section: Key Features > 4. Self-Healing Experiment Code)
**Local system**: plugins/python3-development/skills/start-task/SKILL.md, plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py
**Confidence**: Medium
**Impact**: High
**Backlog**: Deferred -- confidence medium: the SubagentStop hook (task_status_hook.py line 365) marks the task COMPLETE unconditionally when the sub-agent finishes, regardless of whether the agent actually succeeded or failed. However, the sub-agent itself may perform ad-hoc error recovery during its execution window -- this behavior varies by agent type and is not structurally visible from the hook or orchestrator level. Confirming the gap requires observing actual task failure rates and whether agents self-repair effectively within their current execution context.

### Current state

`task_status_hook.py` handles SubagentStop by calling `sam_update_status(full_path, task_id, SamTaskStatus.COMPLETE)` (line 365). There is no check of whether the sub-agent's work actually succeeded. The hook does not examine the sub-agent's output, error state, or acceptance criteria pass/fail status. If the sub-agent encounters errors and exits, the task is still marked COMPLETE.

The `/start-task` skill (SKILL.md step 7) instructs the agent to "implement against the task acceptance criteria and run its verification steps" but does not define a structured retry protocol when verification fails. There is no mechanism to:
1. Capture structured error output from failed verification
2. Route the error back to an LLM with targeted repair context
3. Re-execute the verification (up to N cycles)
4. Log repair attempts with before/after state

Related backlog items:
- #449 "Retry with exponential backoff for BLOCKED tasks" -- covers retry for BLOCKED status, not self-healing within a task
- #450 "Pass attempt count to agent on task retry" -- closer but does not describe structured error capture or repair loop

### Target state

The `/start-task` skill includes a verification-repair loop: after running verification steps, if any fail, the agent captures the error output in a structured format (`{step, command, exit_code, stderr, stdout}`), generates a targeted fix based on the error context, applies the fix, and re-runs verification. This repeats up to a configurable maximum (default 3 cycles). All repair attempts are logged to the task file under a `## Repair Log` section with timestamps, error summaries, and fix descriptions. If the maximum is exceeded, the task is marked with a new status `REPAIR_FAILED` instead of COMPLETE.

### Measurable signal

After a task with verification failures completes, `uv run sam read P{N}/T{M} --format json` includes a `repair_log` array with entries for each repair attempt. Tasks that exhausted repair cycles show `status: repair-failed`. The SubagentStop hook reads the agent's exit state to distinguish success from failure before setting the final status.

---

## Improvement 3: Categorized knowledge base with time-decay for cross-session learning

**Source pattern**: "Markdown-based KB tracked in docs/kb/. Six categories: decisions, experiments, findings, literature, questions, reviews. Per-run accumulation; time-decay aging for lessons (30-day window). Queryable by pipeline stages for context injection." (Section: Key Features > 7. Self-Learning Across Runs / Technical Architecture > 6. Knowledge Base)
**Local system**: CLAUDE.md (context management), .claude/rules/, .claude/knowledge/
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the local repo has `.claude/knowledge/` directory and `session-historian` for recording session work, plus `.claude/rules/` for persistent conventions. These serve some of the same purposes as a categorized KB (decisions are captured in ADRs, conventions in rules files, findings in backlog items). The gap is that there is no unified queryable knowledge base with time-decay aging or automatic lesson extraction from failures. However, #775 "Persistent structured session metadata for cross-session context recovery" partially overlaps with the cross-session context aspect. Confirming whether a unified KB would add value beyond the existing mechanisms requires comparing the failure modes of the current distributed approach against a centralized KB approach.

### Current state

The repo uses several distributed mechanisms for persistent knowledge:
- `.claude/rules/*.md` -- static conventions loaded into every session
- `.claude/knowledge/` -- workflow diagrams and gap recommendations (not categorized, no time-decay)
- `session-historian` skill -- records session work but does not extract lessons or inject them into future sessions
- Backlog items -- track findings but are not queryable as context by agents during task execution
- Plan artifacts -- capture decisions for specific features but are not generalized across features

No mechanism exists to:
1. Automatically extract lessons from task failures (error patterns, successful fixes)
2. Categorize lessons by type (decision, finding, experiment result, question)
3. Age lessons with time-decay so stale knowledge is deprioritized
4. Inject relevant lessons into agent prompts based on task context

Related backlog items:
- #775 "Persistent structured session metadata for cross-session context recovery" -- covers session metadata, not categorized lessons
- #317 "Structured session work logs" -- covers work logging, not lesson extraction or injection

### Target state

A `.claude/knowledge/kb/` directory contains categorized markdown files: `decisions/`, `findings/`, `errors/`, `conventions/`. Each entry has YAML frontmatter with `created`, `last_referenced`, `decay_weight` (float 0.0-1.0, computed from age). A `kb query` command accepts a task context string and returns the top-N relevant entries by semantic similarity weighted by decay. The `/start-task` skill injects relevant KB entries into the agent's context before implementation begins.

### Measurable signal

`ls .claude/knowledge/kb/findings/` returns categorized lesson files. Each file contains `decay_weight` in frontmatter. `uv run kb query "implement authentication middleware"` returns ranked results. After a task agent fails and is retried, the retry prompt includes injected lessons from prior failures on similar tasks.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Autonomous PIVOT/REFINE decision loop | medium | Local SAM architecture uses linear task dispatch, not a pipeline DAG with loopback stages. Would need prototype to confirm integration with existing readiness logic and hook system. |
| Self-healing iterative repair loop | medium | Sub-agents may already self-repair ad hoc during execution; the gap is at the orchestrator/hook level (no structured capture of success/failure). Would need observation of actual task failure rates to confirm value. |
| Categorized knowledge base with time-decay | medium | Existing distributed mechanisms (.claude/rules, backlog, plan artifacts) serve overlapping purposes. #775 partially covers cross-session context. Would need comparison of failure modes to confirm unified KB adds value. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| (none) | All three patterns from the Relevance section were assessed |
