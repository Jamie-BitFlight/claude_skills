# A/B Experiment — Single High-Intelligence Agent vs Multi Low-Intelligence Ensemble

A controlled experiment that tests the `ensemble-rule-review` pattern's central claim against a
single capable agent, on a SOLID-principles code review with a labelled gold set. It instantiates
two experiments from the skill's `references/experiment-matrix.md`:

- E2 — single-high-intelligence vs multi-low-intelligence on the same input.
- E1 — corroboration-weighting ablation (the ensemble reduced with `keep_threshold=1` dedup-only
  vs `keep_threshold=2` corroboration gate).

The point is to replace the skill's n=1 origin anecdote ("14 findings vs 13, ~35x faster") with
real precision/recall/F1 — counting findings is explicitly NOT the metric
(`ensemble-rule-review/references/measuring-success.md`).

## The two arms

| Arm | Directory | Reviewer | Mechanism |
|-----|-----------|----------|-----------|
| A — single high-intelligence | `single-high-intelligence-agent/` | one Sonnet agent | holds the full SOLID ruleset, one pass, emits the fixed schema |
| B — multi low-intelligence ensemble | `multi-low-intelligence-focused-agents/` | 5 Haiku workers + deterministic reducer | `plan_ensemble.py` over the 5 SOLID groups (window 2) -> 5 overlapping Haiku workers -> `reduce.py` |

Both arms review the SAME corpus and emit the SAME fixed candidate schema, so one scorer parses
both identically. Arm B reuses the real skill scripts (`plan_ensemble.py`, `reduce.py`) and a Haiku
worker agent mirroring `plugin-creator:focused-reviewer` — so the experiment also dogfoods the skill.

## The ruleset

`ruleset/solid-rules.json` — the 5 SOLID groups (S, O, L, I, D) decomposed into ~12 concrete
detectable rules. This is a valid `plan_ensemble.py` input. Validate / inspect the plan:

```bash
uv run ../../plugins/plugin-creator/skills/ensemble-rule-review/scripts/plan_ensemble.py \
  ruleset/solid-rules.json --report-dir /abs/reports --window 2 --json
```

The group letter (S/O/L/I/D) is the corroboration key; the `SRP-1`-style prefix in each rule is a
stable rule id for the gold labels. `reduce.py` keys corroboration on `(group, location)`, so the
scorer and gold do too.

## The fixed candidate schema (both arms emit this)

```text
- group: <S|O|L|I|D>
  rule: <free-form slug — descriptive only, not used to match>
  location: <path:line>
  verdict: VIOLATION | PASS
  severity: critical | high | medium | low
  evidence: "<exact short quote from the reviewed file>"
```

`location` is the repo-relative path plus line (e.g. `corpus/cases/01_srp_god_object.py:12`).
Normalization for matching MUST match `reduce.py`'s `normalize_location` (strip a leading `/`, trim
whitespace, PRESERVE the directory) so arm outputs, gold labels, and the reducer all align.

## The corpus and gold set

`corpus/cases/*.py` — hand-authored Python files with KNOWN violations at KNOWN locations. Each
violation maps to a group + rule id. `corpus/gold.json` is the ground truth, one entry per labelled
location:

```json
{
  "corpus/cases/01_srp_god_object.py": [
    {"group": "S", "rule_id": "SRP-1", "location": "corpus/cases/01_srp_god_object.py:12",
     "severity": "high", "kind": "true_violation"}
  ]
}
```

`kind` marks the falsification probes from `measuring-success.md` Step 3:

- `true_violation` — a real violation; arms should flag it (counts toward recall).
- `decoy_false_positive` — code that LOOKS like a violation but is correct (e.g. a legitimate
  facade that resembles a god object). Flagging it is a FALSE POSITIVE. These are the
  systematic-misread probes: if multiple Haiku workers flag the same decoy, corroboration BOOSTS a
  false finding — the direct test of whether the ensemble manufactures false confidence.
- `systematic_miss` — a real but subtle violation cheap models tend to miss; tests recall on hard
  cases.

A `decoy_false_positive` location is a negative: no arm should report `(group, location)` there.

## Scoring

`runner/` computes, per arm, against `gold.json`:

- Precision, Recall, F1 on `(group, normalized-location)` for `true_violation` + `systematic_miss`.
- False-positive rate, broken out for `decoy_false_positive` locations specifically (the shared-bias
  signal).
- Per-decoy corroboration weight in arm B (how many workers flagged each decoy) — the E0 diagnostic:
  if decoys accrue weight >= 2, corroboration is boosting shared error.
- Latency and token/cost per arm.
- E1 ablation: arm B scored at `keep_threshold=1` (dedup-only) vs `keep_threshold=2` (corroboration
  gate); the F1 delta isolates the corroboration weighting's contribution.

Success criteria (from `measuring-success.md`): arm B recall >= arm A, precision not degraded, the
corroboration gate adds measurable F1 over dedup-only, at lower latency/cost. Report the numbers;
do not declare success from finding counts.

## Running

Built to be runnable; not executed yet (dispatching live agents costs tokens). See `runner/` for the
CLI and its `--help`. Run the planner/reducer checks (deterministic, free) any time; run the live
arms when ready.

```bash
# Free — inspect the worker plan
uv run runner/cli.py plan

# Free — score previously written findings against gold
uv run runner/cli.py score

# Costs tokens — dispatch one arm
uv run runner/cli.py run-arm-a
uv run runner/cli.py run-arm-b

# Costs tokens — full experiment
uv run runner/cli.py all
```

Both arms use the identical runner invocation.  Each arm's
`.claude/skills/review-against-solid-principles/SKILL.md` controls its internal
behaviour (model, fan-out, reduce, output path).

---

**INVARIANT — keep PROMPT.md neutral.** `PROMPT.md` must stay mechanism-agnostic: a plain task
a real user would type.  All reviewer detail — schema, output paths, corpus paths, model
selection, which skill to load — lives in each arm's `.claude/`, never in the shared prompt.
Violating this conflates the experiment variable (arm strategy) with the prompt variable, making
the comparison meaningless.
