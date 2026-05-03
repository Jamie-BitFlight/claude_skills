# Improvement Proposals: no-mistakes

**Research entry**: ./research/developer-tools/no-mistakes.md
**Generated**: 2026-05-03
**Patterns assessed**: 8
**Backlog items created**: TBD (filled in below after creation)
**Deferred (low confidence)**: 2
**Skipped (already covered or out of scope)**: 1

---

## Improvement 1: Run /complete-implementation quality gates in an isolated worktree

**Source pattern**: "Non-Blocking Isolated Worktree — Push to no-mistakes starts validation in a temporary worktree without interrupting local development. Your working directory remains unchanged while the gate processes your code." (Key Features section). Also "Isolated Validation Worktree: Non-blocking validation that doesn't interrupt developer workflow" (Patterns Worth Adopting).
**Local system**: plugins/development-harness/skills/complete-implementation/SKILL.md
**Confidence**: High
**Impact**: High
**Backlog**: #{TBD}

### Current state

`/complete-implementation` runs all 6 quality-gate phases (T1 Code Review through T6 Context Refinement) directly against the developer's current working tree. The SKILL.md only mentions "worktree-isolated agents" once (line 354), referring to plan-artifact discovery via the artifact manifest — not to running the gates themselves in an isolated worktree. The Quality Gate Plan Creation section (lines 380–438) creates the SAM plan and dispatches agents in-place. There is no `git worktree add` step, no temporary directory creation, and no rollback step that protects the developer's working tree from auto-fix mutations performed by T1's fix loop (lines 612–618) or by T5 documentation regeneration. The `work-milestone` skill DOES use isolated worktrees (line 44, line 124 of `work-milestone/SKILL.md`), but only for parallel kage-bunshin sessions across milestone items — it is not invoked for single-feature `/complete-implementation` runs.

### Target state

`/complete-implementation` creates an isolated worktree at `~/.dh/projects/{slug}/qg-worktrees/{branch}-{ulid}` before any phase dispatches. All 6 phases execute inside that worktree. Auto-fix commits land on the worktree's branch first. The developer's original working tree is never mutated by quality-gate execution. After completion, the worktree branch is fast-forwarded onto the developer's branch only after the developer approves the diff (or the existing autonomy mode authorizes it). The worktree is destroyed on success or on rejection.

### Measurable signal

Run: `/complete-implementation #N` against a feature branch with uncommitted changes in the working tree. After the run completes, `git status` in the original working tree shows the same uncommitted changes intact (unchanged hash for any unstaged file). Inspect `~/.dh/projects/{slug}/qg-worktrees/` — directory exists during the run, removed after. New SKILL.md section "Worktree Setup" between "Pre-Phase: Artifact Discovery" and "Quality Gate Plan Creation" documents the worktree lifecycle commands.

---

## Improvement 2: Configurable gate composition for /complete-implementation per project

**Source pattern**: "Multi-Stage Validation Gates — All gates run in the isolated worktree. Gates can auto-fix issues or require human review." plus the YAML config example: `gates: - name: rebase ... - name: lint ... auto_fix: true ... - name: test ... command: 'npm test'` (Configuration section). Also "Multi-Stage Gates: Composable quality checks (lint → test → review → docs) can be reordered or conditionally enabled per project" (Patterns Worth Adopting).
**Local system**: plugins/development-harness/skills/complete-implementation/SKILL.md
**Confidence**: High
**Impact**: Medium
**Backlog**: #{TBD}

### Current state

The 6 quality-gate phases (T1–T6) are hardcoded in `build_quality_gate_plan()` (referenced lines 411–414 of the SKILL.md, defined in `sam_schema.core.quality_gates`). The phase-task mapping table (lines 446–456) lists T1=Code Review, T2=Feature Verification, T3=Integration Check, T4=Documentation Drift Audit, T5=Documentation Update, T6=Context Refinement — fixed agents, fixed order, fixed dependency chain. There is no per-project config file analogous to no-mistakes' `.no-mistakes/config.yaml` `gates:` array where a project owner can disable phases (e.g., a docs-only repo might skip Feature Verification), reorder them, or substitute a custom shell-command gate (e.g., `command: ./scripts/check-license-headers.sh`). The only conditional skip is T5 when T4 reports no drift (lines 504–506).

### Target state

A `.dh/quality-gates.yaml` file in the project root declares the active gate sequence: each entry has `name`, `enabled`, optional `agent` (defaults from build_quality_gate_plan), optional `command` (custom shell gate), and optional `auto_fix` flag. `build_quality_gate_plan()` reads this file when present and emits the SAM plan based on the declared sequence; falls back to the existing 6-phase default when no file exists. The Quality Gate Plan Creation section of complete-implementation/SKILL.md documents the config schema and the precedence (project config > default).

### Measurable signal

Create `.dh/quality-gates.yaml` with 3 gates (e.g., omit T2 and T3). Run `/complete-implementation #N`. The created QG plan contains exactly those 3 task IDs, no more. Without the file, the plan still contains all 6 default tasks. Schema documented in `complete-implementation/SKILL.md` and in a new reference file `plugins/development-harness/skills/complete-implementation/references/gate-config-schema.md`.

---

## Improvement 3: Surface auto-fix diffs for human approval before they land

**Source pattern**: "Auto-Fix Capability — Gates can automatically fix violations without human intervention: Linting and formatting auto-fix (--fix flags); Documentation regeneration; Test creation (when AI review identifies missing tests). Developer sees all auto-fixes before they're committed and can reject them." (Key Features section). Also "Auto-Fix with Human Review: Automatically fix format/lint issues but surface all changes to developer for approval before committing." (Patterns Worth Adopting).
**Local system**: plugins/development-harness/skills/complete-implementation/SKILL.md
**Confidence**: High
**Impact**: Medium
**Backlog**: #{TBD}

### Current state

The fix loop documented at lines 612–618 (Step 1 of Recursive Follow-up Handling) and the documentation-update phase T5 commit auto-generated changes directly without surfacing the diff for developer approval. The fix loop creates `fix-{slug}-blocking-N` SAM plans, dispatches `dh:task-worker`, and re-runs T1; the developer is not shown the cumulative diff between iterations and has no opt-out short of killing the session. The Final Step: Commit and Push section (lines 887–905) commits remaining changes in a single sweep at the end. The autonomy field (`Plan.autonomy: full_auto | checkpoint | per_task`, mentioned in CLAUDE.md `python3-development` plugin docs) gates dispatch but not auto-fix commits within `/complete-implementation`.

### Target state

When `Plan.autonomy != full_auto` AND any quality-gate phase produces auto-fix commits (T1 fix loop, T5 docs regeneration, T2-discovered missing tests), `/complete-implementation` pauses before committing. It writes a unified diff of all auto-fix changes to a known artifact location (e.g., via `artifact_register(type='qg-auto-fix-diff', content=...)`) and emits a console block listing the diff path. The developer either re-runs `/complete-implementation` with an approval flag, edits the diff, or rejects it. A new section "Auto-Fix Approval Gate" between Phase 6 and "Final Step" documents the prompt structure.

### Measurable signal

Run `/complete-implementation #N` on a plan with `autonomy: checkpoint` and a deliberate ruff violation. The run completes the T1 fix loop, then halts before commit. The output contains "AUTO-FIX REVIEW REQUIRED" and a path to the artifact with the diff. Re-run with `--approve-auto-fixes` (or a new `mcp__plugin_dh_backlog__backlog_update(approve_auto_fixes=True)` field) lets it proceed. New section "Auto-Fix Approval Gate" exists in `complete-implementation/SKILL.md`.

---

## Improvement 4: Post-PR CI-failure auto-fix watcher

**Source pattern**: "Automatic PR Opening and CI Watching — After all gates pass: 1. Branch is pushed to upstream 2. PR is opened automatically 3. (Optional) Tool watches CI and applies auto-fixes if tests fail" (Key Features section). Also `pr: auto_open: true; auto_fix_ci: true # watch CI and auto-fix failures` (Configuration section).
**Local system**: plugins/development-harness/skills/complete-implementation/SKILL.md (and a new follow-on skill if needed)
**Confidence**: High
**Impact**: Medium
**Backlog**: #{TBD}

### Current state

The Final Step at lines 887–905 of `complete-implementation/SKILL.md` commits and pushes, then proceeds to Team Shutdown (lines 909–920) and the Final Handoff Output (lines 925–947). After push, no skill in the repository monitors the GitHub Actions run for that branch. A grep across `.claude/skills/*/SKILL.md` and `plugins/*/skills/*/SKILL.md` for `gh run watch`, `monitor.*CI`, or `watch.*CI` returned zero matches (verified via the search above). When CI fails after the developer has moved on, the failure stays unfixed until the developer notices and re-invokes a fix manually.

### Target state

After Final Step push, when an issue/PR is associated with the branch, `/complete-implementation` either (a) spawns a background `claude -p` session running a new `/dh:ci-watcher #N` skill or (b) registers a deferred task. The watcher polls `gh run list -R {repo} --branch {branch} --limit 1` until status is final, and on failure fetches `gh run view --log-failed`, dispatches `dh:task-worker` with the failure log, lets it apply a fix-and-push cycle (max 2 cycles to avoid loops), and posts a comment on the PR summarising what changed. New skill `plugins/development-harness/skills/ci-watcher/SKILL.md` documents the polling cadence, max cycle count, and escape hatches.

### Measurable signal

After `/complete-implementation #N` push with autonomy=full_auto: a background process `claude -p --skill /dh:ci-watcher` is spawned (verifiable via `ps aux | grep ci-watcher` while the watcher is alive). On a deliberately broken test, after CI completes with failure, the PR receives an automated comment with the fix diff, and the branch advances by exactly one auto-fix commit per failed run (max 2). Skill file `plugins/development-harness/skills/ci-watcher/SKILL.md` exists with frontmatter declaring `user-invocable: false`.

---

## Improvement 5: Add /dh:gate-push command — push-as-gate entry point that wraps quality validation

**Source pattern**: "Push to no-mistakes starts validation in a temporary worktree without interrupting local development. ... Push through the gate with: git push no-mistakes <branch>" (Installation and Usage section). The push verb itself becomes the trigger for the gate pipeline, providing a single-action entry point.
**Local system**: plugins/development-harness/skills/complete-implementation/SKILL.md (new sibling skill)
**Confidence**: High
**Impact**: Low
**Backlog**: #{TBD}

### Current state

Today the developer must explicitly run `/dh:complete-implementation {plan-or-issue}` to invoke quality gates; only then are they pushed and a PR opened. There is no single command that takes a branch name and executes the equivalent of "validate this branch via gates, push if clean, open PR." The closest existing command is `/dh:work-backlog-item` which expects an issue title, and `/dh:complete-implementation` which expects a plan path or issue number — neither maps the human-natural verb "push this branch" to the gate pipeline.

### Target state

A new user-invocable skill `plugins/development-harness/skills/gate-push/SKILL.md` accepts a branch name as its argument. It locates the linked backlog issue (via branch-name → slug → backlog match), invokes `/dh:complete-implementation` with the resolved issue/plan, and on success completes the existing push+PR step. Behaviour matches `git push no-mistakes <branch>` semantically: one verb, full gate pipeline, automatic PR. SKILL.md describes the branch→issue resolution algorithm and what happens when no match is found (fall back to prompting the developer for the issue number).

### Measurable signal

Run `/dh:gate-push feature/foo` on a branch with a linked backlog issue. The run dispatches the same 6 quality-gate phases as `/dh:complete-implementation`. On success, `gh pr list -R Jamie-BitFlight/claude_skills --head feature/foo` returns the freshly opened PR. New skill file `plugins/development-harness/skills/gate-push/SKILL.md` exists. The frontmatter has `user-invocable: true` and `argument-hint: <branch-name>`.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Real-Time TUI Dashboard for active /complete-implementation runs | Low | The local pattern uses background `claude -p` agents, MCP-registered artifacts, and `mcp__plugin_dh_sam__sam_plan(action='status')` polling. A TUI is one possible UX layer, but the underlying state is already observable via SAM status calls. Whether a TUI vs. a `--watch` flag on `sam_status` is the right shape needs human input on the developer's actual review workflow. Without that, building a full TUI is speculative. Would need a small user-research note showing developers actually want a TUI rather than `watch sam_status`. |
| Multi-Agent Wire Format Detection (Codex/OpenCode/Pi adapters) | Low | This repository targets Claude Code as its primary agent. The `agent: claude` config in no-mistakes already represents the only relevant case. Adopting wire-format detection would be premature abstraction unless the user articulates a need to dispatch via Codex or OpenCode CLIs from within the harness. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| AI-Driven Review (Patterns Worth Adopting #3) | Already implemented by the `dh:code-reviewer` agent invoked as T1 in `/complete-implementation` (see lines 446–456 and lines 502–504 of `complete-implementation/SKILL.md`). Local coverage is at parity with or beyond no-mistakes' generic AI-review gate. |
