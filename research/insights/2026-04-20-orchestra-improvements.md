# Improvement Proposals: Orchestra

**Research entry**: ./research/agent-frameworks/orchestra.md
**Generated**: 2026-04-20
**Patterns assessed**: 8
**Research-derived backlog issues created**: 6 (issues: #1855, #1856, #1857, #1858, #1859, #1860)
**Patterns deferred (low confidence)**: 1
**Patterns skipped (already covered or tracked)**: 1

_Note: these counters summarize outcomes from this Orchestra improvement-pattern review. "Research-derived backlog issues" refers to GitHub issues opened from this research pass, not to formal proposal counts used in separate utilization-assessment documents._

---

## Improvement 1: Per-task token budget field on the Task model

**Source pattern**: "Context Curator — During dispatch — assembling focused prompts for sub-agents... Each task has a configurable token budget (default 80,000 tokens)... Simple tasks: 50% of default budget; Standard tasks: 100% of default budget; Complex tasks: 150% of default budget" (Orchestra README / SKILL.md Step 5; decomposer.md).
**Local system**: plugins/development-harness/sam_schema/core/models.py (Task model, lines 114–223)
**Confidence**: High
**Impact**: Medium
**Backlog**: #1855 created

### Current state

The `Task` model (plugins/development-harness/sam_schema/core/models.py, lines 114–223) has no `token_budget` field. It carries `complexity` (`low | medium | high`, line 133) and `accuracy_risk` (`low | medium | high`, line 178) but neither is consumed by any dispatcher or context-assembly code to bound the prompt size passed to `dh:task-worker`. Grep of the plugin source shows zero occurrences of `token_budget`, `context_budget`, or any per-task token cap: `plugins/development-harness/sam_schema/**/*` does not define or read such a field.

### Target state

`Task.token_budget: int | None` is added to `plugins/development-harness/sam_schema/core/models.py` with a sentinel default (e.g. `None`) that signals "use the plan-level default". When `None`, the effective budget is derived from `complexity` using Orchestra's 50/100/150% rule against a plan-level `default_token_budget` field on `Plan`. `implement-feature` reads the resolved budget and records it in the delegation prompt (so `task-worker` can self-regulate its own context loading) and in the per-task artifact for post-hoc audit.

### Measurable signal

Run: `uv run fastmcp call --command "uv run --script plugins/development-harness/scripts/run_sam_server.py" sam_task --input-json '{"plan": "P1", "task": "T01", "config": {"action": "read"}}'` — the returned JSON contains key `token_budget`. In a plan YAML with `default-token-budget: 80000`, a task with `complexity: high` and no override resolves to `120000` when queried via `sam_plan(action='ready')`. `tests_sam/test_models.py` has a new test `test_task_token_budget_resolution` verifying the resolution rules.

---

## Improvement 2: Stall detection using LastActivity in ready-tasks query

**Source pattern**: Orchestra tracks task status (pending/in-progress/done/failed) across waves and surfaces stalled tasks through its dashboard and history log (SKILL.md Step 6: "final summary with failed tasks and their failure reasons"). While Orchestra does not document an explicit stall threshold, its checkpoint autonomy mode plus per-wave progress tracking creates an observable gate that `implement-feature` currently lacks.
**Local system**: plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py; plugins/development-harness/skills/implement-feature/SKILL.md (Agent Health Check section)
**Confidence**: High
**Impact**: High
**Backlog**: #1856 created

### Current state

`task_status_hook.py` writes `last-activity` on every PostToolUse (Write/Edit/Bash), and the `Task` model persists it as `last_activity: datetime | None` (models.py line 150). No code reads this field to detect or act on stalled agents. The implement-feature SKILL (lines 100–128) defines "Agent Health Check" but the only signal is "~10 minutes of silence" observed subjectively by the orchestrator via the JSONL transcript — the timestamp already on disk in the task file is never consulted. Result: the orchestrator re-spawns based on transcript analysis instead of the authoritative per-task timestamp.

### Target state

`sam_plan(action='ready')` (sam_schema/core/query.py) and `sam_plan(action='status')` return, for each `in-progress` task, a computed field `stall_minutes: int | null` = `(now - last_activity).total_seconds() / 60`. A plan-level or env-configurable threshold (`SAM_STALL_THRESHOLD_MIN`, default 10) causes `ready-tasks` to flag such tasks with `stall_detected: true`. The implement-feature SKILL Agent Health Check branch reads `stall_detected` first and only falls through to transcript analysis when `last_activity` is missing.

### Measurable signal

Run: `uv run fastmcp call --command "uv run --script plugins/development-harness/scripts/run_sam_server.py" sam_plan --input-json '{"plan": "P1", "config": {"action": "status"}}'` — each `in-progress` task in the returned JSON includes keys `stall_minutes` (int) and `stall_detected` (bool). With `SAM_STALL_THRESHOLD_MIN=5` and a task whose `last-activity` is 7 minutes old, `stall_detected: true` appears in the output. A new unit test in `tests_sam/` sets a fake `last_activity` 10 minutes in the past and asserts `stall_detected: true`.

---

## Improvement 3: Acceptance-criteria validation gate before task completion

**Source pattern**: Orchestra's Limitations section explicitly notes: "No built-in validation of agent output quality — Orchestra tracks task status (pending/in-progress/done/failed) but does not validate that sub-agent output meets acceptance criteria... No automatic gate prevents marking a task done if AC are unmet." This is identified in the research entry as a limitation Orchestra shares with our local system — worth fixing here.
**Local system**: plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py (SubagentStop handler); plugins/development-harness/agents/task-worker.md (Step 5 — Mark Complete)
**Confidence**: High
**Impact**: High
**Backlog**: #1857 created

### Current state

`task-worker.md` Step 5 marks a task complete via `sam_task(action='state', status='complete')` on the worker's own judgement. The SubagentStop hook (`task_status_hook.py`) then observes the completion and writes the `Completed` timestamp. The `strict` hook profile (implementation-manager/SKILL.md lines 208–211) *checks that AC were defined* and that the task was claimed, but never checks that AC were *met*. The `acceptance_criteria` field (models.py line 197) is a free-text string; nothing parses its checklist items against artifact evidence. A worker can write a failing test and still call `state=complete`.

### Target state

A new `dh:ac-gate` agent runs in `implement-feature` Step 4 (after task-worker returns, before concerns accumulation). It reads `task.acceptance_criteria`, extracts checklist items (`- [ ] ...` via `marko`), and for each item produces a verdict using task output evidence (modified files, test output registered as an artifact). If any item fails, the task is transitioned to `blocked` instead of `complete` and the failing items are written to the task's `notes` field. Opt-in via plan-level `ac-gate: true` to avoid breaking existing plans; opt-out is automatic when `acceptance_criteria` is empty.

### Measurable signal

Run: against a plan with `ac-gate: true` and a task whose worker wrote a passing unit test plus one failing lint, `sam_task(action='read')` after the worker exits shows `status: blocked` and `notes` contains the specific failing AC item text. Integration test `tests_sam/test_ac_gate.py` runs a dummy worker that returns COMPLETE with an unmet AC and asserts the task ends in `blocked`.

---

## Improvement 4: Project conventions extraction into delegation context

**Source pattern**: "Before dispatching, Orchestra extracts project coding standards from CLAUDE.md and settings files... Naming conventions, import patterns, testing frameworks, architectural constraints, code style rules, language/framework-specific conventions... Filters out session behavior rules... Condensed to under 2000 characters and included in Context Curator input as `.orchestra/project-conventions.md`" (SKILL.md Step 2d).
**Local system**: plugins/development-harness/skills/implement-feature/SKILL.md; plugins/development-harness/agents/task-worker.md
**Confidence**: High
**Impact**: Medium
**Backlog**: #1858 created

### Current state

`task-worker` loads whatever skills the task's `skills` field names and reads the task YAML — but receives no distilled project conventions. The harness relies on the orchestrator's own CLAUDE.md being loaded, which is a different address space from the subagent. Sub-agents therefore do not know that (for example) `ruamel.yaml` is required and `pyyaml` is banned, unless that rule appears inside the task body itself. Grep for `project-conventions`, `project_conventions`, or `extract.*conventions` across `plugins/development-harness/**` returns no hits — no code path produces such an artifact.

### Target state

A new artifact type `project-conventions` registered via the artifact manifest. A small extractor (`plugins/development-harness/scripts/extract_conventions.py`) reads the repo's `.claude/CLAUDE.md`, `plugins/*/CLAUDE.md` in scope, and per-language settings (`pyproject.toml`, `package.json`), emits a distilled ≤ 2000-char markdown under a new artifact type, and `artifact_register`s it at the parent issue. `implement-feature` Step 2 (before the progress loop) calls this extractor once and appends the artifact reference to each delegation prompt so `task-worker` reads it before executing.

### Measurable signal

Run: from a repo with `.claude/CLAUDE.md` mentioning `ruamel.yaml`, `uv run plugins/development-harness/scripts/extract_conventions.py --issue N` writes an artifact and `artifact_read(issue_number=N, artifact_type="project-conventions")` returns text ≤ 2000 chars containing the substring `ruamel.yaml`. The string `"# Session Behavior"` (an example session-behavior header) is absent from the output.

---

## Improvement 5: Autonomy modes (full_auto / checkpoint / per_task) for the dispatch loop

**Source pattern**: "Three autonomy modes provide a framework for balancing automation with user control: `full_auto` — all tasks run without user intervention; `checkpoint` (default) — user reviews after each wave of tasks completes; `per_task` — user confirms each task individually" (README + SKILL.md).
**Local system**: plugins/development-harness/skills/implement-feature/SKILL.md (Progress Loop)
**Confidence**: High
**Impact**: Medium
**Backlog**: #1859 created

### Current state

The Progress Loop in `implement-feature/SKILL.md` (lines 34–206) dispatches ready tasks in batches without user review between batches. There is no plan-level `autonomy` field on the `Plan` model, and no branch in the SKILL mermaid graph that inserts a user-confirmation gate between waves. The only "checkpoint" is the Completion Gate after **all** tasks finish — there is no intermediate wave-level or task-level gate.

### Target state

`Plan.autonomy: Literal["full_auto", "checkpoint", "per_task"] = "checkpoint"` is added to `plugins/development-harness/sam_schema/core/models.py`. `implement-feature/SKILL.md` grows an autonomy-gated branch in its Progress Loop: after each batch (checkpoint) or each task (per_task), the orchestrator reports a compact summary and waits for user confirmation before pulling the next batch. `full_auto` preserves today's behavior. The value is readable via `sam_plan(action='status')`.

### Measurable signal

Run: `uv run fastmcp call --command "uv run --script plugins/development-harness/scripts/run_sam_server.py" sam_plan --input-json '{"plan": "P1", "config": {"action": "status"}}'` — output contains key `autonomy`. With `autonomy: per_task` set on the plan and two ready tasks, implement-feature dispatches task 1, reports, and halts for user input before dispatching task 2 (verified by inspecting the transcript for the confirmation prompt string `"Confirm next task"`).

---

## Improvement 6: Pre-dispatch dirty-repo stash prompt

**Source pattern**: "Before creating worktrees, Orchestra prompts to stash uncommitted changes, preventing interference... `git stash push -m \"orchestra-auto-stash: pre-run {branch_name}\"` ... Records stashed repos so user is reminded to restore after run completion" (SKILL.md Step 2c).
**Local system**: plugins/development-harness/skills/work-milestone/SKILL.md (Entry Conditions + Step 3); plugins/development-harness/skills/implement-feature/SKILL.md
**Confidence**: High
**Impact**: Medium
**Backlog**: #1860 created

### Current state

`work-milestone/SKILL.md` (line 18) lists "Clean git state on main" as an entry *condition* but provides no action to achieve clean state — if the user is dirty, the skill fails the condition with no recovery path. Grep of `plugins/development-harness/**` for `git stash`, `stash push`, or `uncommitted` returns no matches. `implement-feature` does not check for dirty state at all before creating a worktree in its sibling skills. A user with dirty state is forced to hand-stash and re-invoke.

### Target state

A reusable `plugins/development-harness/scripts/prepare_clean_worktree.sh` is added. It runs `git status --porcelain`, and if non-empty, prompts the user: "Stash uncommitted changes? [y/N]". On `y` it runs `git stash push -m "dh-auto-stash: pre-run {branch}"` and records the stash ref in a new ephemeral state file `~/.dh/projects/{slug}/context/auto-stashes.json`. `work-milestone` Step 3 calls this script before `git worktree add`. On completion, the skill prints a reminder: `Auto-stash ref X pending; run 'git stash pop {ref}' to restore.`

### Measurable signal

Run: in a repo with `echo x > scratch.txt`, invoking `/dh:work-milestone 1` prints a y/N prompt with the literal string `"Stash uncommitted changes"`. On `y`, `git stash list` shows an entry matching `dh-auto-stash:`, and `~/.dh/projects/{slug}/context/auto-stashes.json` exists with key `branch` matching the integration branch name.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Per-task agent model selection (Opus for complex, Haiku for simple) — Orchestra's README lists `agent_model` as *global*, but the Limitations section (caveat 7) explicitly names this as an Orchestra weakness. Our harness already routes `dh:task-worker` to a single model. A per-task override might help but requires verifying `task-worker`'s current model-selection path in `profile_load` and confirming whether any spawn wrapper (e.g. kage-bunshin spawn.py) already supports per-task `--model`. Not directly observable from a single file pair. | medium | Would need to verify `agent_profile/discovery.py` and spawn.py to confirm whether per-task override already exists in some form before proposing. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Git worktree isolation (Orchestra feature 4) | Already fully implemented in `/dh:work-milestone` — see `plugins/development-harness/skills/work-milestone/SKILL.md` Step 5a (`git worktree add worktrees/{slug}`). Orchestra's pattern is equivalent; no gap. |
| DAG-based task decomposition with wave structure (feature 1) | Already implemented via `swarm-task-planner` producing waves from dependency graphs (see `plugins/development-harness/agents/swarm-task-planner.md` lines 78–100 and the existing `Dispatch Orchestration System` documented in `plugins/development-harness/CLAUDE.md`). The harness's wave-based parallelism is architecturally equivalent. |
| Cross-repository orchestration (feature 7) | Out of scope: harness is single-repo by design. Sibling-repo coordination would require replacing the `dh_paths` project-slug anchor; Orchestra's approach is incompatible with our per-project state directory model. |
| State persistence and resumability (feature 5) | Already implemented via `~/.dh/projects/{slug}/` artifact directory, GitHub Issues as source of truth, and the `dispatch_state.db` SQLite store (see `plugins/development-harness/backlog_core/dispatch_state.py`). Our resumability model is stronger (durable GH backend) than Orchestra's file-based `.orchestra/`. |
| Dashboard visualization (feature 6) | Already tracked as lower priority; the harness is CLI-first and produces audit trails via `backlog_list_comments` + `artifact_list`. A Node.js dashboard would add a non-Python runtime dependency the plugin avoids. Would require user appetite before backlogging. |
| Fallback Engine / max_retries (feature 8) | Partially covered by the existing `dispatch_item_status(... status='failed' ...)` path in `backlog_core/dispatch_state.py` and by `/work-milestone` Step 6a "Investigate Fail" branch. Gap is not clearly beyond current behavior without further design work. |
