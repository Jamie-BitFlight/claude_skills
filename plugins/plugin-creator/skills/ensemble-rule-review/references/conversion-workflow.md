# Converting an Existing Skill into the Ensemble Form

A step-by-step workflow to take a skill/agent that applies a large ruleset in a single pass and
restructure it into a fan-out ensemble (partitioned overlapping workers + corroboration-weighted
reducer). Also the recipe for standardizing the `multi-perspective-review` prior art.

## Table of Contents

- [Preconditions](#preconditions)
- [Workflow](#workflow)
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
