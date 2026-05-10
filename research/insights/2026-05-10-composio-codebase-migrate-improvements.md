# Improvement Proposals: Composio Codebase Migrate

**Research entry**: ./research/skill-generation-tools/composio-codebase-migrate.md
**Generated**: 2026-05-10
**Patterns assessed**: 6
**Backlog items created**: 4 (issues: #2240, #2241, #2242, #2243)
**Deferred (low confidence)**: 0
**Skipped (already covered or tracked)**: 2

---

## Improvement 1: Per-wave PR-and-merge mode in work-milestone

**Source pattern**: "Pick N files from affected set ... Create PR with batch metadata. Poll CI status via Composio API. Merge when green and loop to next batch." — Key Features section "Batched Execution with Tracking" (lines 51–60), Data Flow section (lines 116–138)
**Local system**: ./plugins/development-harness/skills/work-milestone/SKILL.md
**Confidence**: High
**Impact**: High
**Backlog**: #2240 created — P1

### Current state

`plugins/development-harness/skills/work-milestone/SKILL.md` lines 22–96 implements a single-integration-branch landing model. Per-wave merges (lines 60–73, MergeLoop → MergeResult → WaveComplete) all happen LOCALLY on `milestone/{N}-{slug}`. Only at Step 9 (line 91) does the integration branch reach `git push origin main`. There is no per-wave PR creation, no per-wave CI gate, no per-wave human review opportunity. `dispatch_state.DispatchPlan` has no `landing_mode` field. The dispatch_wave_status MCP tool reports wave completion but does not block on a green CI signal for that wave's merged delta before allowing the next wave to start.

### Target state

`work-milestone` SKILL accepts a `landing_mode: "single-pr" | "per-wave-pr"` field on the dispatch plan. In `per-wave-pr` mode, after Step 6c WaveComplete, a wave branch `milestone/{N}-wave-{W}` is pushed and a PR opened against the integration branch via existing `gh pr create -R Jamie-BitFlight/claude_skills` infrastructure. A new step `6e-WaitCI` polls `gh pr checks {PR}` until green, then `gh pr merge --squash`. Failed wave CI halts the milestone and creates a fix-up backlog item; subsequent waves do not start.

### Measurable signal

Run: `uv run python -c "from backlog_core.dispatch_state import DispatchPlan; print('landing_mode' in DispatchPlan.model_fields)"` outputs `True`. After running a 2-wave milestone in `per-wave-pr` mode: `gh pr list -R Jamie-BitFlight/claude_skills --state merged --search "wave-"` returns at least 2 wave PRs. The dispatch state DB row for each wave includes `pr_number` and `ci_status: green` before the next wave starts.

---

## Improvement 2: Codemod-runner skill catalog for AST-based multi-file refactors

**Source pattern**: "Skill supports language-specific tooling — `jscodeshift` for Node, `ts-morph` for TypeScript, `comby` for text-based transforms, `ast-grep` for structural queries" — Extension Points section (line 142). Limitations section (lines 233–234): "Regex-based codemods may catch unintended patterns. Skill recommends switching to AST-based tooling."
**Local system**: ./.claude/skills/swarm-patterns/SKILL.md (Pattern 6 Coordinated Multi-File Refactoring) and a new `.claude/skills/codemod-runner/`
**Confidence**: High
**Impact**: Medium
**Backlog**: #2241 created — P2

### Current state

Grep across `plugins/development-harness/skills/` and `.claude/skills/` for `jscodeshift`, `ts-morph`, `comby`, or `ast-grep` returns zero matches. `.claude/skills/swarm-patterns/SKILL.md` Pattern 6 (lines 223–275) describes "Coordinated Multi-File Refactoring" but worker prompts (lines 256, 262) say only "refactor the User model" / "refactor the Session controller" — there is no guidance on selecting an AST tool, scoping with ripgrep, or running a deterministic codemod versus LLM-driven file edits. Multi-file renames are performed by an LLM iterating Edit calls — non-deterministic and hard to verify with idempotency.

### Target state

A new skill at `.claude/skills/codemod-runner/SKILL.md` containing a Mermaid decision flowchart (regex → `comby`/`sed`; structural pattern → `ast-grep`; full AST → `jscodeshift`/`ts-morph`/`LibCST`/`rope`), a pre-execution scope command pattern (`rg -l '<pattern>' | wc -l` and `rg -l '<pattern>' | head -25 > batch.list`), a per-batch idempotency check (run the codemod twice, assert second run produces zero diffs), and a verification trend command (`rg '<old-pattern>' | wc -l` should monotonically decrease across batches). Pattern 6 in `.claude/skills/swarm-patterns/SKILL.md` updated to reference the new skill.

### Measurable signal

File `.claude/skills/codemod-runner/SKILL.md` exists with frontmatter `name: codemod-runner` and a Mermaid `flowchart TD` whose decision diamonds reference at least three of: `comby`, `ast-grep`, `jscodeshift`, `ts-morph`, `LibCST`. `grep -c codemod-runner .claude/skills/swarm-patterns/SKILL.md` returns at least 1. `uv run prek run --files .claude/skills/codemod-runner/SKILL.md` exits 0.

---

## Improvement 3: Trending-metric verification on TN bookend tasks

**Source pattern**: "Runs trending metrics to confirm progress: `rg 'jest\\.(mock|fn|spyOn)' | wc -l    # Should trend to 0`" — Key Features section "Verification Loop After Each Merge" (lines 78–82)
**Local system**: ./plugins/development-harness/sam_schema/core/models.py (StructuredAcceptanceCriterion) and ./plugins/development-harness/agents/tn-verification-gate.md
**Confidence**: High
**Impact**: Medium
**Backlog**: #2242 created — P2

### Current state

`plugins/development-harness/skills/implement-feature/SKILL.md` lines 277–304 (Bookend Task Ordering) defines T0 (baseline) and TN (verification) tasks using `t0-baseline-capture` and `tn-verification-gate` agents. Verification today is binary (criterion met vs. not met). There is no representation for a count metric whose value should monotonically trend toward a target across the implementation. `StructuredAcceptanceCriterion` (in `sam_schema/core/models.py`) carries no `trending_metric` field. A migration AC like "count of `from \"jest\"` imports must be 0" must currently be encoded as one AC per file (turning AC-as-outcome into AC-as-task-list) or verified manually.

### Target state

`StructuredAcceptanceCriterion` accepts an optional `trending_metric` sub-object with fields `command` (shell command emitting a single integer), `target` (default 0), and `monotonic_direction` ("decreasing" or "increasing"). `t0-baseline-capture` records every `trending_metric.command` output as part of the T0 baseline. `tn-verification-gate` reads `trending_metric` entries, runs each `command`, compares against the T0 baseline, and asserts current value matches `target` AND has moved monotonically in `monotonic_direction`.

### Measurable signal

Run: `uv run python -c "from sam_schema.core.models import StructuredAcceptanceCriterion; print('trending_metric' in StructuredAcceptanceCriterion.model_fields)"` outputs `True`. A test plan with a `trending_metric` AC produces a `tn-verification-gate` JSON output containing a `metric_history` list with both T0 and Tn values, and fields `monotonic_violated: false` and `target_met: true` when the command output equals `target`.

---

## Improvement 4: Ripgrep-driven live blast-radius validation in feasibility-gate

**Source pattern**: "ripgrep scoping to find affected files. Example workflow: `rg -l 'jest\\.(mock|fn|spyOn)' | wc -l    # Find scope`" — Key Features section "Transform Precision Definition" (lines 42–49)
**Local system**: ./plugins/development-harness/skills/work-backlog-item/references/workflows/work/feasibility-gate.md
**Confidence**: High
**Impact**: Medium
**Backlog**: #2243 created — P2

### Current state

`plugins/development-harness/skills/work-backlog-item/references/workflows/work/feasibility-gate.md` Criterion 3 "Blast radius" counts rows in the Impact Radius section (Code, Docs, Config, Agent Instructions). The count is whatever the groomer wrote at item-creation time and never re-validated against the live working tree. Grep of `feasibility-gate.md` for `rg -l` returns zero matches — there is no command that re-runs the scope query before the gate fires. A backlog item groomed two months ago with Impact Radius listing 8 systems can fire the gate today even if the actual `rg` count is 47, slipping past the >20 systems hard block at lines 7–9.

### Target state

`feasibility-gate.md` Criterion 3 gains an automated sub-step before the manual count: when an Impact Radius row carries an explicit `pattern: '<rg-pattern>'` field, the gate runs `rg -l '<rg-pattern>' | wc -l` and uses the live count. If live count > 1.5 * manual count, the gate emits `STALE_GROOM` requiring re-grooming. The Impact Radius table template grows a `pattern:` column for ripgrep-grep-able rows.

### Measurable signal

`grep -c "rg -l" plugins/development-harness/skills/work-backlog-item/references/workflows/work/feasibility-gate.md` outputs at least 1. Test: groom an item with `pattern: 'old_api_v1'` in Impact Radius, run the feasibility-gate locally — output shows both `live_count: N (from rg)` and `manual_count: M`, and emits `STALE_GROOM` when N > 1.5 * M.

---

## Deferred Proposals (confidence too low to backlog)

None. All four actionable patterns reached high confidence after reading the local source files.

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Composio CLI integration for issue tracking and PR creation | Already covered. Local stack uses `mcp__plugin_dh_backlog__*` MCP tools (GitHub Issues source-of-truth) and `gh pr create -R ...` patterns documented in CLAUDE.md `gh_cli_usage` block. The Composio CLI is functionally equivalent — replicating it would duplicate existing capability. |
| Wave-completion confirmation gate / per-task autonomy mode | Already tracked. Backlog #1859 "Add autonomy modes (full_auto/checkpoint/per_task) to implement-feature dispatch loop" status:verified covers the user-confirmation-between-waves pattern. Composio's "merge when green, loop to next batch" is the same loop with a CI gate substituted for a human gate — the autonomy infrastructure is the substrate. |
