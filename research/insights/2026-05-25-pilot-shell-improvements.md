# Improvement Proposals: Pilot Shell

**Research entry**: ./research/coding-agents/pilot-shell.md
**Generated**: 2026-05-25
**Patterns assessed**: 9
**Backlog items created**: 4 (issues: #2444, #2445, #2447, #2448)
**Deferred (low confidence)**: 3
**Skipped (already covered or tracked)**: 2

---

## Improvement 1: Add `/spec` orchestration skill that gates implementation on user plan approval with inline annotations

**Source pattern**: Quote from research entry, "## /spec — Spec-Driven Development Workflow" section: "Waits for user approval with inline annotation support (select text or click + to annotate; agent reads annotations at next review checkpoint)" and "Spec-review sub-agent validates completeness".
**Local system**: /home/user/claude_skills/plugins/development-harness/skills/add-new-feature/SKILL.md and implement-feature/SKILL.md
**Confidence**: High
**Impact**: High
**Backlog**: #2444 created

### Current state

The DH harness separates `add-new-feature` (planning) from `implement-feature` (execution), but the handoff has no explicit user-approval checkpoint between plan production and task dispatch. `implement-feature/SKILL.md` lines 35–95 shows the Progress Loop calls `sam_plan(action="status")` then `sam_plan(action="ready")` and dispatches tasks based on `autonomy_mode`. The `autonomy` field can be `full_auto | checkpoint | per_task` (development-harness/CLAUDE.md, "Modifying data structures" section), but the `checkpoint` mode is not bound to a structured plan-review artifact and there is no annotation mechanism for the user to write inline feedback that the orchestrator reads on resumption. The user either approves or does not — there is no annotated revision loop.

### Target state

A new skill `/dh:approve-plan` (or extension of `add-new-feature/SKILL.md`) writes a plan-approval artifact to the GitHub Issue body (via `artifact_register` with type `plan-approval`). The artifact contains: plan path, status (`pending | annotated | approved | rejected`), and an `annotations[]` array (each item: `selector` — line range or section name, `comment` text, `author`, `created_at`). On `implement-feature` invocation, the Progress Loop first reads `artifact_get(item_id=N, artifact_type="plan-approval")` and refuses to dispatch tasks unless `status == "approved"`. When `status == "annotated"`, the orchestrator routes back to a plan-revision agent that reads the annotations and produces a revised plan.

### Measurable signal

Artifact ID `"plan-approval"` is registered under development-harness artifact conventions. Running `mcp__plugin_dh_backlog__artifact_get(item_id=N, artifact_id="plan-approval")` returns a JSON object with required keys `status`, `annotations`. `implement-feature/SKILL.md` Progress Loop Step 0 (new step inserted before Step 1) refuses to proceed when `status != "approved"`.

---

## Improvement 2: Add `/dh:fix` lightweight bugfix workflow with built-in bail-out to `/dh:add-new-feature` for multi-component bugs

**Source pattern**: Quote from research entry, "## /fix — Bugfix Workflow" section: "Lightweight bugfix lane for single-file, obvious-once-traced root causes. No plan file, no approval mid-flow, but TDD still enforced. Flow: Investigate → RED (write failing test) → Fix (at root cause) → Verify end-to-end → Quality gate → Done. Bail-out condition: If investigation reveals the bug is multi-component, architectural, needs defense-in-depth, or two attempts have failed, /fix stops cleanly and directs user to use /spec instead."
**Local system**: /home/user/claude_skills/.claude/rules/fix-delegation-discipline.md and /home/user/claude_skills/plugins/development-harness/skills/work-backlog-item/SKILL.md (`--quick` mode)
**Confidence**: High
**Impact**: High
**Backlog**: #2445 created

### Current state

`fix-delegation-discipline.md` defines a reproduction-first cycle (Problem → Reproduce → Success criteria → Cycle instruction) as a rule that delegation prompts MUST include. It is a prescriptive rule for prompt construction, not an executable skill workflow. `work-backlog-item --quick` exists (work-backlog-item/SKILL.md line 146 "### --quick mode") and is routed to from CLAUDE.md's "Proactive Fix Gate" for trivial fixes. Neither path enforces TDD (RED before fix), nor provides an explicit bail-out condition that escalates from quick-fix to full SAM planning when investigation reveals multi-component scope. The orchestrator must remember to escalate; nothing automatic.

### Target state

A new skill at `plugins/development-harness/skills/fix/SKILL.md` invokable as `/dh:fix "<observable-symptom>"`. Workflow steps:

1. Investigate — produce a `root-cause` artifact citing the failing file and exact line.
2. RED — write a failing test that demonstrates the bug (no fix yet); record the test command and expected failing output.
3. Fix — change only the file identified in step 1.
4. Verify — re-run the test command; require GREEN; require the full quality gate (existing complete-implementation gates) to pass.
5. Bail-out — if investigation reveals 2+ files affected, OR if cycle 2 still fails, OR if architectural change required: write a `fix-escalation` artifact and direct user to `/dh:add-new-feature "<problem>"`. Refuse to continue in `/dh:fix`.

The bail-out condition is a Mermaid decision diamond in the SKILL.md, and the artifact is registered via `artifact_register(item_id=N, type="fix-escalation", content=...)`.

### Measurable signal

File `plugins/development-harness/skills/fix/SKILL.md` exists with frontmatter `name: fix`. Running `mcp__plugin_dh_backlog__artifact_list(item_id=N)` on a bail-out item returns an entry with `artifact_id: "fix-escalation"`. `complete-implementation/SKILL.md` recognizes a `fix-escalation` artifact and stops with status referencing `/dh:add-new-feature` as the next action.

---

## Improvement 3: Add `/dh:benchmark` skill for measuring effect of a rule, skill, or agent on output quality

**Source pattern**: Quote from research entry, "### /benchmark — Impact Measurement" section: "Runs prompts with and without a target rule or skill, grades outputs against falsifiable assertions, and produces a structured verdict + improvement plan. Isolation mode auto-hides global extensions for duration, then restores on completion (survives SIGKILL via recovery manifest)."
**Local system**: /home/user/claude_skills/plugins/development-harness/skills/impact-measurement/SKILL.md
**Confidence**: High
**Impact**: Medium
**Backlog**: #2447 created

### Current state

`impact-measurement/SKILL.md` measures **cost** (token injection cost, payload size, context window consumption) for a single artifact. It does not measure **quality effect** — there is no skill that runs the same prompt with and without a target rule/skill loaded, grades both outputs against assertions, and produces a comparative verdict. There is also no "isolation mode" — the orchestrator cannot temporarily hide a skill or rule for the duration of a benchmark and restore it afterward.

### Target state

A new skill at `plugins/development-harness/skills/benchmark/SKILL.md` (or `.claude/skills/benchmark/`). Workflow:

1. Input: target skill or rule path + list of test prompts + falsifiable assertions per prompt.
2. Run each prompt twice — once with target loaded, once with target temporarily renamed (e.g., `*.disabled` extension) so it does not auto-activate.
3. Grade each output against the assertions list (pass/fail per assertion).
4. Produce a verdict report with: per-prompt scores, aggregate delta, suspected failure causes, recommended changes.
5. Restore the disabled artifact in a `finally` block AND register a recovery manifest at `~/.dh/projects/{slug}/benchmark/recovery.json` so a SIGKILL'd benchmark is restored on next `claude` invocation via a session-start hook.

### Measurable signal

File `plugins/development-harness/skills/benchmark/SKILL.md` exists. Running it on a target skill produces a markdown report at `~/.dh/projects/{slug}/benchmark/{YYYY-MM-DD}-{target-name}.md` with sections: `## With Target`, `## Without Target`, `## Verdict`. Recovery manifest path `~/.dh/projects/{slug}/benchmark/recovery.json` is present during a run and absent afterward.

---

## Improvement 4: Register `RED → GREEN → REFACTOR` enforcement as an executable hook on task transitions, not a documented norm

**Source pattern**: Quote from research entry, "Implementation phase: Strict TDD: RED → GREEN → REFACTOR for each task" and "Quality hooks auto-lint, format, type-check on every edit" and "Full test suite runs after each task. No manual code edits — all changes go through claude Code's Edit tool."
**Local system**: /home/user/claude_skills/plugins/development-harness/skills/start-task/SKILL.md (PostToolUse hook) and /home/user/claude_skills/plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py
**Confidence**: High
**Impact**: Medium
**Backlog**: #2448 created

### Current state

`start-task/SKILL.md` lines 6–12 register a single `PostToolUse` hook firing on `Write|Edit|Bash` that runs `task_status_hook.py`. This hook updates task metadata after edits but does NOT enforce the TDD RED→GREEN→REFACTOR sequence: an agent can write implementation code with no preceding failing test, and the hook will accept it. There is a `test-failure-mindset` skill and an `analyze-test-failures` skill that prescribe reasoning, but no executable hook gate that refuses an implementation Edit when no preceding test file edit (with a failing-test run) has been recorded for the same task.

### Target state

Extend `task_status_hook.py` (or add a sibling `tdd_phase_hook.py`) to record per-task phase state in the active-task context JSON: `phase: red | green | refactor`. Hook behavior:

- On Write/Edit to a test file (matching repo test patterns from the language manifest): if `phase == "red"`, record the test file path.
- On Bash command matching `pytest|npm test|go test|...`: parse exit code; if non-zero AND a test file was edited in this phase, transition to `phase: green` (allow implementation edits next).
- On Write/Edit to a non-test source file: if `phase == "red"` (no failing test recorded yet), emit a non-blocking warning via stderr and record the violation in the task artifact (`tdd_violations[]`). Optionally, with a config flag, refuse the edit by exit code 2.

The complete-implementation quality gate reads `tdd_violations[]` from the task artifact and surfaces them as a review finding.

### Measurable signal

File `plugins/development-harness/skills/implementation-manager/scripts/tdd_phase_hook.py` exists, or `task_status_hook.py` contains a function `record_tdd_phase(...)`. Active-task JSON at `~/.dh/projects/{slug}/context/active-task-*.json` contains a `tdd_phase` field after one edit. Running `cat ~/.dh/projects/{slug}/context/active-task-*.json | jq .tdd_violations` returns an array after an implementation-without-test edit.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| **RTK output compression (60–90% token savings)** | Low | Pilot Shell's RTK is a proprietary proxy; mechanism is not described in primary sources. Cannot identify which local component to extend without understanding what RTK does at the protocol level. Raising confidence would require reading RTK's specification or observing actual proxy behavior. |
| **Semble hybrid chunk-only code search** | Low | Semble is a proprietary code search service bundled with Pilot. The local equivalent would be `/ccc` (cocoindex-code) which already provides indexed search. Without knowing what makes Semble's chunking superior or different to ccc, the gap cannot be expressed as an observable target state. |
| **Model switching with `spec_handoff_resume` hook (planner stops, user runs `/model sonnet[1m]`, next prompt routes to spec-implement without `/clear`)** | Medium | The local SAM workflow's `per_task` autonomy mode and `dispatch_spawn` already cover phase handoff via fresh `claude -p` subprocesses with different effort levels. The Pilot pattern of session-level model switching without restarting the session is mechanistically different but the local approach achieves the same outcome (different models per phase). Raising confidence would require evidence that mid-session model switch is materially better than fresh subprocess dispatch for DH workflows. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| **Local web dashboard with SQLite, recent items, session resumption (`localhost:41777`)** | Out of architectural scope for this repo. DH backlog already uses GitHub Issues as source of truth (development-harness/CLAUDE.md) and `mcp__plugin_dh_backlog__*` tools provide programmatic access. Adding a local web dashboard duplicates GitHub's web UI without adding capability the orchestrator can act on. |
| **APM-compatible extension export** | Out of scope. This repo's plugins are distributed via Claude Code marketplace (`.claude-plugin/marketplace.json`), not APM. Cross-ecosystem export is a distribution concern, not an orchestration/workflow concern. |
