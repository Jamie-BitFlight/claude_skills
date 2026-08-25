# Benchmarks — Section Evaluation Loop Experiment

Record of an A/B experiment testing one change to this skill's Step 2/Step 3 sequencing. Kept
outside `SKILL.md` per this repo's skill-authoring convention (skills contain only runtime-facing
content); this file is a maintainer-facing experiment record.

## Limitations — read before trusting the verdict

This was run in a live development session, not a controlled benchmark harness. Treat the results
as indicative, not statistically conclusive:

- **No environment isolation between runs.** Each run got its own copy of the target skill
  directory, but all 12 runs shared the same host session, model version, and point in time — not
  independent process/container sandboxes with a pinned environment snapshot. A systemic session-
  or model-level effect could bias every run in the same direction without showing up as a
  between-run difference.
- **No blind comparison was actually performed.** The original experiment design (see git history
  of this file for the full spec) called for an independent evaluator scoring outputs without
  knowing which variant produced them. That step was dropped mid-experiment for cost reasons
  (the operator was near a weekly usage cap and asked to stop further multi-agent dispatch); the
  "Key findings," "Hypothesis analysis," and "Verdict" sections below were synthesized directly by
  the orchestrating session with full knowledge of which run was baseline vs. candidate throughout.
  That is a real source of confirmation bias this record cannot rule out.
- **Small sample.** 3 runs per variant per target, 2 targets, 12 runs total. Large enough to see
  one clear miss and several disagreements, not large enough to estimate a reliable failure rate
  for either variant.
- **Uneven verification depth.** Every `gh` run-report was read in full by the orchestrator; most
  `research-curator` run-reports were relayed via the dispatched agent's own summary rather than
  independently re-read end to end (noted per-row in the results table below). Self-reported word
  counts and dispositions were only spot-checked, not universally re-derived.
- **Targets and run counts were chosen by the orchestrating session**, not randomly sampled from
  the full skill population — `gh` and `research-curator` were picked for structural richness
  (scripts, multiple references, accumulated fix-commit history), which may not represent typical
  skills in this repo.

Given these gaps, this experiment is good evidence for "the section loop is not an obvious,
uncomplicated win" and for the specific failure mode described in Hypothesis analysis below. It is
not strong enough evidence to treat the DO NOT PROMOTE verdict as final without a follow-up run
that adds blind scoring and process isolation.

## Experiment

**Question**: does replacing whole-skill sentence-level counterfactual pruning (Step 2:
section-level goal alignment, then Step 3: a single pass over the whole file) with a strict
one-section-at-a-time evaluation loop (goal → contract dependency → instruction analysis →
runtime test → preservation test → disposition → edit → local verification, closing one section
before opening the next) improve pruning fidelity or dead-weight discrimination?

- **Variant A (baseline)**: the skill as committed, unmodified.
- **Variant B (candidate)**: Step 2 replaced with the section loop above; Step 3 renamed/reworded
  to "Analysis criteria for the current section" and pointed at from inside the loop. No other
  rule, disposition definition, or completion criterion changed.

## Reproducing this experiment

All commands assume the repo checked out at:

```text
commit 5770b115dad8eba7528f825f55a637fad85d2d8e
```

**Baseline variant** = `plugins/plugin-creator/skills/evaluate-and-tighten-skills/SKILL.md` at
that commit, byte-for-byte.

**Candidate variant** = the same file with this diff applied (Step 2 replaced, Step 3 renamed and
reworded; nothing else changed):

```diff
-## Step 2: Section-level goal alignment
-
-Before sentence-level pruning, classify each section against the goals resolved above.
-
-For each section, ask:
-
-> Which explicit skill goal does this section or instruction help the executing agent achieve, and how?
-
-Classify:
-
-* **DIRECT** - directly causes behavior required by a goal.
-* **SUPPORTING** - provides a decision principle, constraint, domain fact, or capability needed to achieve a goal across variable situations.
-* **UNALIGNED** - does not materially contribute to any explicit goal.
-
-Flag `UNALIGNED` sections before tightening individual sentences. They cannot remain runtime behavior merely because they already exist in the current implementation.
-
-Do not immediately discard them. During the counterfactual deletion pass, determine whether they contain a durable goal, maintenance fact, local implementation invariant, or architectural decision that belongs somewhere else. Otherwise delete them.
-
-## Step 3: Counterfactual deletion pass
-
-Read the complete skill section by section, including frontmatter and referenced instructional material.
-
-For each sentence or independently removable instruction, first classify its function:
+## Step 2: Section evaluation loop
+
+Before editing, read the complete target skill and all materially relevant resources so each
+section can be evaluated in the context of the whole skill, its goals, behavioral contract, and
+maintenance constraints.
+
+Then process the target skill in source order, one section at a time.
+
+Complete the full evaluation of the current section before beginning evaluation of the next
+section.
+
+For each section:
+
+1. **Goal alignment**
+   Identify which explicit skill goal or goals the section advances.
+
+   Classify the section:
+
+   - **DIRECT** - directly causes behavior required by a goal.
+   - **SUPPORTING** - provides a decision principle, constraint, domain fact, or capability needed to achieve a goal across variable situations.
+   - **UNALIGNED** - does not materially contribute to any explicit goal.
+
+2. **Contract dependency**
+   Identify which behavioral-contract requirements, if any, depend on this section.
+
+3. **Instruction analysis**
+   Apply the Step 3 analysis criteria to each sentence or independently removable instruction in this section.
+
+4. **Runtime decision**
+   Determine the minimum material required for runtime execution or context-dependent reasoning.
+
+5. **Preservation decision**
+   For material removed from runtime context, determine whether its smallest durable fact should be relocated or deleted.
+
+6. **Disposition**
+   Assign each relevant piece its final disposition:
+   `KEEP-RUNTIME`, `KEEP-REASONING`, `MOVE-GOALS`, `MOVE-LOCAL`, `MOVE-MAINTENANCE`, `MOVE-ADR`, or `DELETE`.
+
+7. **Edit**
+   Apply only the changes justified by this section's evaluation.
+
+8. **Local verification**
+   Reread the edited section with its surrounding context.
+
+   Confirm:
+   - every behavioral-contract requirement depending on this section remains supported;
+   - required reasoning or resolution information remains available;
+   - removed runtime material has the correct preservation disposition;
+   - the edit has not changed the meaning of adjacent sections.
+
+Only after this verification is complete may evaluation move to the next section.
+
+Later sections may be read to understand context, dependencies, or references. Do not assign
+their dispositions or make their pruning decisions until their turn in the section loop.
+
+Do not batch classifications, deletion decisions, or dispositions across multiple sections.
+
+After every section completes this loop, run the whole-skill preservation pass.
+
+## Step 3: Analysis criteria for the current section
+
+Apply these criteria to the current section while executing the Step 2 section evaluation loop.
+
+For each sentence or independently removable instruction, first classify its function:
```

`references/example.md` and `references/maintenance-placement.md` are identical between
variants; only Step 2/3 of `SKILL.md` differ.

**Targets** (both unmodified at commit `5b6bcb8a389ae77deda0d006124b955ceacce2b7`, the last commit
to touch either path as of the experiment — confirmed via `git status --short` showing no
uncommitted changes to either directory before the experiment began):

- `.claude/skills/gh/` (625-word `SKILL.md`, 4 references, 3 scripts, 2 test files — chosen for
  scripts + multiple progressive-disclosure references + accumulated fix-commit history)
- `.claude/skills/research-curator/` (2718-word `SKILL.md`, 6 references, 5 scripts — chosen as
  the largest, most reference/script-dense skill in the tested pool, for the deepest accumulated
  maintenance/history surface)

**Method**: 3 independent runs per variant per target (12 runs total), each in its own copy of the
target directory (`cp -R` from the pristine target, one copy per run, never shared or reset
in-place), each executed by a fresh agent with no visibility into any other run's output or
existence. Every run agent was told to follow the assigned variant's `SKILL.md` verbatim as if
invoked normally, and was explicitly instructed that word/token reduction is not a success metric.

Full run artifacts (tightened `SKILL.md`, any `MAINTENANCE.md`/relocated files, and each run's own
`run-report.md` — behavioral contract, section-by-section trace, Completion block) live under
`.tmp/scratch/experiments/section-loop/` in the worktree this experiment ran in; that directory is
gitignored and not reproduced by checking out the commit above — only the inputs are. Re-running
this experiment means re-executing the method above from the commit and diff given here.

## Results — `gh` (6/6 runs, all run-reports read in full)

| Run | Words before→after | Reduction | MAINTENANCE.md | Automation-section factual inaccuracy | Notes |
|---|---|---|---|---|---|
| baseline-1 | 625→402 | 35.7% | not created | Deleted, reported as a Goal deviation | Kept entire `## Sources` in place, citing `citation-requirements.md` as an external constraint |
| baseline-2 | 625→387 | 38.1% | created (1 entry) | Deleted, reported as a Goal deviation | |
| baseline-3 | 625→389 | 37.8% | created (2 entries) | Deleted, but reported "Goal deviations found: none" | Inconsistent with baseline-1/2 on the identical finding |
| candidate-1 | 625→401 (+177 in MAINTENANCE.md) | 35.8% | created (4 entries) | **Corrected in place**; also independently corrected a second inaccuracy (`--detect-only`'s false "writes gh-examples.md" claim) | Treated both as in-scope Resolvability fixes |
| candidate-2 | 625→451 | 27.8% | not needed | **Missed** — reversed its own initial correct read to KEEP-RUNTIME without checking the script source | Only run of 6 that did not verify this claim against `github_project_setup.py` |
| candidate-3 | 625→409 | 34.6% | created (1 entry) | Deleted (not corrected); found a *second*, different inaccuracy no other run caught (`-R` claimed to apply to `gh project`, contradicted by `projects-v2.md`'s own `--owner`-based examples) | Explicitly declined to correct the `gh-examples.md` claim, calling correction "outside this procedure's toolkit" — opposite call from candidate-1 on the same fact |

All 6 runs independently verified the target's `SKILL-GOALS.md` and read `scripts/*.py` /
`references/*.md` in full before disposing of any material; word counts above are each run's own
self-reported `wc -w` figure, not independently re-measured except where noted.

## Results — `research-curator` (6/6 runs; baseline-2 and candidate-1 read in full, the rest
relayed via the dispatched agent's own summary)

| Run | Words before→after (SKILL.md only unless noted) | Reduction | MAINTENANCE.md | Notes |
|---|---|---|---|---|
| baseline-1 | 3473→2964 (SKILL.md **+** `references/batch-mode.md` combined) | 14.7% (combined denominator, not comparable to the other rows) | not reported | Deleted a `--layer 0\|1\|2` mechanism as foreign to all 6 goals, without diagnosing *why* it was wrong — no other run touched it |
| baseline-2 | ~2719→2535 | 6.8% | not needed | Flagged (not fixed) two orphaned reference files and a mermaid/prose validation-gate gap |
| baseline-3 | 2718→2503 | 7.9% | created | Also tightened `references/validation-rules.md` (406→296); surfaced a real `header_fields` severity contradiction between that file and the actual script — reported, not fixed; found 2 orphaned scripts + 2 orphaned reference files |
| candidate-1 | 2718→2522 (independently verified via `wc -w`) | 7.2% | created (1 entry) | Found **and fixed** 4 genuine pre-existing runtime defects (see Key finding 6) — one of which would have broken the script invocation as originally written. Its `run-report.md` was still mid-write (Completion/Files-touched sections showed `<!-- PENDING -->`) when first checked; it completed shortly after |
| candidate-2 | 2718→2481 | 8.7% | created (1 entry) | Flagged (not fixed) the same Rerun Mode mermaid/prose gate gap baseline-2 found, plus a Goal-5 scope gap (cross-reference graph only realized in Batch Mode) |
| candidate-3 | 2718→2283 | 16.0% | not created | Found the same `--layer` mechanism baseline-1 deleted, but **checked for external dependents first** (found real callers in `knowledge-explorer`/`refresh-research`) and correctly kept it as `Uncertain` instead of deleting it |

## Key findings

1. **Fidelity split on the one verifiable factual defect in `gh`.** All 3 baseline runs and 2 of 3
   candidate runs independently caught and removed/corrected the same false claim
   (`github_project_setup.py` "delegates all GitHub operations to the authenticated gh CLI"),
   verified against the script's own docstring in every case that caught it. `gh candidate-2` is
   the only run of 6 that reversed a correct initial read to `KEEP-RUNTIME` without checking the
   script — the single clearest fidelity failure across both variants.
2. **Candidate runs disagree with each other on scope for factual corrections.** `candidate-1`
   treated correcting a false claim as in-scope ("Resolvability" fix); `candidate-3` found a
   near-identical false claim and explicitly declined to correct it, calling correction
   "outside this procedure's toolkit." Same variant, same procedure text, opposite disposition.
3. **Baseline is not perfectly consistent either.** `gh baseline-3` deleted the same inaccurate
   sentence `baseline-1`/`baseline-2` flagged as a Goal deviation, but reported
   "Goal deviations found: none" — a reporting inconsistency, not a fidelity miss (the deletion
   itself was correct).
4. **The section loop is not uniformly worse at dependency-checking.** `research-curator
   candidate-3` did more diligence than `baseline-1` on the identical `--layer` mechanism —
   baseline-1 deleted it as foreign without checking for external callers; candidate-3 checked,
   found real dependents, and correctly kept it as `Uncertain`. This cuts against a simple
   "section loop always causes premature closure" reading.
5. **`research-curator candidate-1` found and fixed 4 genuine pre-existing runtime defects that
   no baseline run caught or corrected**, including one script invocation missing a required Typer
   subcommand ("this was Validate Mode's primary script call and would have failed at runtime as
   originally written"), a diagram missing a validation-gate branch that its own adjacent prose
   required, a prose/diagram timing contradiction, and — most notably — root-caused the same
   `--layer` claim `baseline-1` had blindly deleted: candidate-1 identified it as copy-paste
   leakage from an unrelated skill (verified by grepping for the leaked skill names) and corrected
   it to the true dependency, rather than removing it outright. `baseline-3` found a comparable
   real defect (`header_fields` severity contradiction) but only reported it, per every baseline
   run's consistent stance that fixing factual/logic defects is outside a pruning pass's scope.
6. **Fixing defects (as opposed to reporting them) is out of scope for *both* variants' written
   procedure** — nothing in either Step 2's wording licenses adding new correct content (a missing
   subcommand, a missing diagram branch). `candidate-1` invented an unauthorized "Corrected"
   section in its Completion report to hold these fixes, a template deviation from the sanctioned
   Removed/Uncertain/Goal-deviations/Relocated/Maintenance-file shape every other run of 12 used.
   Valuable work, but not evidence specifically attributable to the section-loop hypothesis being
   tested — nothing in the candidate's Step 2 text instructs fixing anything, so this looks like
   this one run's own initiative rather than a systematic effect of the process change.

## Hypothesis analysis

Two hypotheses, not one:

- **H1 — sequential section processing improves consideration.** Evidence: genuinely mixed, and
  target-dependent. On `gh`, candidate found one extra defect (`candidate-3`) but also produced
  the worst miss of all 12 runs (`candidate-2`). On `research-curator`, candidate's edge is
  clearer: `candidate-1` diagnosed and corrected a defect `baseline-1` had blindly deleted, and
  `candidate-3` did dependent-checking `baseline-1` skipped on the identical material. Averaged
  across both targets this looks like "candidate finds more, baseline is more consistently
  reliable" rather than a clean win or loss for either.
- **H2 — closing each section before moving on causes local optimization or premature
  completion.** Evidence: plausible but not confirmed. `gh candidate-2`'s reversal from a correct
  `EXPLAINS` read to `KEEP-RUNTIME` without inspecting the script source is consistent with a
  completion-boundary effect. But the same variant's `candidate-1`/`candidate-3` runs on
  `research-curator` show the opposite pattern (more dependency-following, not less) on similarly
  structured material. If premature closure were a systematic property of the section loop, it
  should show up more than once in 6 candidate runs; on the current evidence it looks like a
  per-run failure mode, not a designed-in one.

## Verdict

**NO MATERIAL DIFFERENCE, leaning DO NOT PROMOTE** on the current evidence.

- Fidelity: baseline > candidate on `gh` (candidate produced the one clear miss across all 12
  runs); candidate ≥ baseline on `research-curator` (candidate-1's defect diagnosis-and-fix beat
  baseline-1's blind deletion of the same material; candidate-3's dependent-check beat
  baseline-1's on the same finding). These point in opposite directions across the two targets.
- Discovery breadth: candidate > baseline overall (3 novel findings — `gh candidate-3`'s second
  inaccuracy, `rc candidate-1`'s 4 fixed defects, `rc candidate-3`'s dependent-check — vs. 1 for
  baseline, `rc baseline-3`'s severity contradiction).
- Disposition consistency: baseline > candidate (candidate's `gh` runs disagreed with each other
  on whether correcting a factual claim is in scope; baseline's `gh` inconsistency was
  reporting-only, not a disposition disagreement — though `rc candidate-1`'s unauthorized
  "Corrected" section shows the scope-creep risk isn't unique to disposition labeling).
- Overall: this evidence does not support a confident promote or reject. The single worst outcome
  in the whole experiment (`gh candidate-2`) happened under the candidate variant, but so did the
  single best outcome (`rc candidate-1`'s defect fixes). The variance within the candidate variant
  is at least as large as the variance between variants — which is itself evidence that a 3-run
  sample per variant per target is too small to attribute outcomes to the process change rather
  than to individual-run luck. A proper follow-up (larger sample, blind scoring, isolated
  environment — see Limitations) is needed before either promoting or permanently rejecting this
  change.

## Evidence

- Source diff and commit: see "Reproducing this experiment" above.
- Per-run artifacts (not committed, gitignored): `.tmp/scratch/experiments/section-loop/runs/{gh,research-curator}/{baseline,candidate}-{1,2,3}/run-report.md`
- `gh` target: `.claude/skills/gh/`
- `research-curator` target: `.claude/skills/research-curator/`
