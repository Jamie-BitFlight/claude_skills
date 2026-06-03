# Converting an Existing Skill into the Ensemble Form

A step-by-step workflow to take a skill/agent that applies a large ruleset in a single pass and
restructure it into a fan-out ensemble (partitioned overlapping workers + corroboration-weighted
reducer). Also the recipe for standardizing the `multi-perspective-review` prior art.

## Table of Contents

- [Preconditions](#preconditions)
- [Workflow](#workflow)
- [Fidelity-preserving audit (no instruction loss)](#fidelity-preserving-audit-no-instruction-loss)
- [Standardizing multi-perspective-review](#standardizing-multi-perspective-review)
- [Validation gate (feedback loop)](#validation-gate-feedback-loop)

## Preconditions

Confirm the candidate fits before converting (see the parent SKILL.md "When to Use"):

- The skill applies a ruleset of ~10+ independent criteria.
- It applies them in a single agent pass today (slow + silent criteria-dropping).
- The ruleset can be split into scenario-bound slices that can overlap.

If the ruleset is under ~5 criteria, or the task needs one coherent creative judgment, STOP — the
ensemble overhead exceeds the return.

## Workflow

1. **Enumerate the ruleset.** Read the source skill/agent and extract every criterion as a
   discrete, stably-named rule. If the rubric is implicit ("pythonic", "modernization", "review
   for quality"), make it explicit first using
   [./partitioning-patterns.md](./partitioning-patterns.md).

2. **Cluster into groups and plan the assignment.** Group the rules into 3+ stable groups (prefer
   the natural boundaries the rubric already names — a framework's categories, a checklist's
   sections), write them to a JSON file (group id → rules), and run
   `../scripts/plan_ensemble.py RULES.json --report-dir /abs/dir` to produce the balanced
   rotating-overlap assignment. The planner guarantees each rule lands in exactly `window` workers
   (uniform redundancy) so corroboration is even across the ruleset.

3. **Define the control header.** Write the one-line header that compiles an effort/scale
   parameter into concrete knobs: worker count, candidates-per-worker cap, verify policy, output
   cap. The same skill body then scales rigor by that parameter.

4. **Emit worker definitions.** Copy `../assets/worker-prompt-skeleton.md` once per slice and fill
   the placeholders. All workers share the identical input scope and the fixed candidate schema;
   only the rule slice differs. Workers run on the cheapest tier at low effort.

5. **Emit the reducer.** Specify the dedup → corroboration-weight → drop-tail → rank step (the
   algorithm in [./orchestrator-playbook.md](./orchestrator-playbook.md)). The reducer runs on a
   mid tier (sonnet) at medium effort.

6. **Wire the orchestrator.** The new SKILL.md body becomes: Phase 0 scope (deterministic) →
   Phase 1 dispatch workers in parallel → Phase 2 reduce → emit ranked/capped/structured output.
   Keep the worker prompts and schema in `assets/`, detail in `references/`, body lean.

7. **Preserve provenance.** Cite the source skill the ruleset came from, and keep the original
   skill's rule text intact inside the worker slices — conversion must not drop or reword criteria.

## Fidelity-preserving audit (no instruction loss)

When the conversion target is an EXISTING skill, the hard requirement is that no current
instruction is dropped, reworded into something weaker, or silently merged with another. Step 1
(enumerate) and step 7 (preserve provenance) of the workflow above carry this; this section is the
explicit audit that proves it. Run it as a gate before declaring the conversion done.

1. Inventory every instruction. Parse the source skill's markdown into a structured list of
   discrete criteria — one row per criterion, capturing its exact source text and location. Use a
   markdown AST parser (`marko`, the repo convention) rather than reading by eye, so no list item,
   table row, or inline rule is missed. The output is a coverage table seeded with the source rows.

2. Map each criterion to rule id(s) + group. One source criterion may expand into several rules
   (finer detection); that is fine. NEVER collapse two distinct source criteria into one rule —
   that drops a distinction the source made. Record the mapping in the coverage table.

3. Preserve text verbatim. The rule text inside each worker slice must be the source criterion's
   exact wording, or a restatement that quotes the original verbatim alongside it. No summarizing,
   no paraphrase that narrows scope. A reworded rule is a fidelity loss even when nothing is
   "missing".

4. Assert full coverage. Every source row maps to at least one rule, and every rule lands in at
   least one worker. `plan_ensemble.py` guarantees uniform redundancy across workers; this step
   guarantees completeness of the source-to-rule mapping. Zero unmapped source rows is the pass
   condition.

5. Round-trip reconstruction. From the union of all worker slices, reconstruct the ruleset and diff
   it against the source inventory. Any criterion you cannot reconstruct from the slices is a
   fidelity loss — fix the slicing before proceeding.

6. No-orphan check (reverse direction). Every rule must trace back to a source criterion. A rule
   with no source row is an invented criterion smuggled in during conversion — scope creep, the
   other fidelity failure. Remove it or raise it with the user as a deliberate addition.

7. Behavioral spot-check. Run the new ensemble and the original single-pass skill on the same known
   input. Any finding the original produced that the ensemble misses must trace to a mapped rule
   (then the rule was lost in slicing — return to step 2). If it traces to no rule, the inventory in
   step 1 was incomplete. See [./measuring-success.md](./measuring-success.md) for the metric set.

Coverage table template (every source row must end fully mapped):

```text
| source criterion (exact text) | source location | rule id(s) | group | worker(s) |
|-------------------------------|-----------------|------------|-------|-----------|
```

If the source rubric is implicit ("pythonic", "review for quality"), enumerate it explicitly FIRST
via [./partitioning-patterns.md](./partitioning-patterns.md), then inventory the enumerated rules —
you cannot audit fidelity against a rubric that was never written down.

## Standardizing multi-perspective-review

`development-harness/skills/multi-perspective-review` already runs a 4-worker parallel review
(Security, Performance, Quality, Accessibility) with a merge gate — a partial instance of this
pattern. To bring it to the full pattern, apply only the deltas:

- Add the **fixed candidate schema** to each reviewer worker (it currently returns free-form SOP
  output).
- Replace the **any-REJECT merge** with the **corroboration-weighted reducer** so findings the
  perspectives independently agree on rank highest.
- Add **deliberate overlap** between perspectives on shared concerns (e.g. input validation spans
  Security and Quality) so corroboration has something to count.

## Validation gate (feedback loop)

Before declaring the conversion done, prove it on a known input:

1. Pick an input the single-pass skill already reviewed (a known-answer file).
2. Run the new ensemble on it.
3. Compare against the single-pass baseline: recall (findings caught), precision (false
   positives), and latency.
4. The conversion passes when recall is at least equal to the baseline AND latency is lower. If
   recall dropped, the slices are too narrow or lost a rule — return to step 2 of the workflow. If
   precision dropped, raise the reducer keep-threshold or add a verifier pass (see playbook).
5. Re-run until both conditions hold. Record the baseline-vs-ensemble numbers as the skill's
   evaluation evidence.
