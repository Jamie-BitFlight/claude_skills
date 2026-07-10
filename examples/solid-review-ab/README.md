# Judgement System — SOLID Review Experiment

A controlled experiment that runs the same SOLID-principles code review task across N arbitrary
agent/model configurations and ranks them by payoff-per-cost.  It instantiates two experiments
from the skill's `references/experiment-matrix.md`:

- E2 — single-high-intelligence vs multi-low-intelligence on the same input.
- E1 — corroboration-weighting ablation (the ensemble reduced with `keep_threshold=1` dedup-only
  vs `keep_threshold=2` corroboration gate).

The point is to replace the skill's n=1 origin anecdote ("14 findings vs 13, ~35x faster") with
real precision/recall/F1 — counting findings is explicitly NOT the metric
(`ensemble-rule-review/references/measuring-success.md`).

## Arms — manifest-driven, N-arm

Arms are declared in `arms.yaml` at the experiment root.  The seeded arms are:

| Arm | Directory | Reviewer | Mechanism |
|-----|-----------|----------|-----------|
| single-high-intelligence-agent | `single-high-intelligence-agent/` | one Sonnet agent | holds the full SOLID ruleset, one pass, emits the fixed schema |
| multi-low-intelligence-focused-agents | `multi-low-intelligence-focused-agents/` | 5 Haiku workers + deterministic reducer | `plan_ensemble.py` over the 5 SOLID groups (window 2) -> 5 overlapping Haiku workers -> `reduce.py` |

Both seeded arms review the SAME corpus and emit the SAME fixed candidate schema, so one scorer
parses both identically.  The judgement system supports any number of additional arms.

### Adding a new arm

1. Create a new directory at the experiment root (e.g. `opus-single-agent/`).
2. Add `.claude/skills/review-against-solid-principles/SKILL.md` to configure its model,
   procedure, and output path.  The arm can be any configuration — a single Opus agent, a
   heterogeneous ensemble, a different Haiku fan-out width, or any combination of models.
3. Add an entry to `arms.yaml`:

```yaml
arms:
  - name: opus-single-agent
    dir: opus-single-agent
    enabled: true
    arm_type: single   # or "ensemble" for a multi-worker arm
    models:
      - id: claude-opus-4-5
        role: primary
```

The `arm_type` field is **required** and validated at manifest load time:

- `single` — the arm writes one `findings/findings.md` file (single-agent pass).
- `ensemble` — the arm writes multiple `findings/workers/worker-*.md` files
  (fan-out workers + reducer).  If the arm declares `ensemble` but the
  `workers/` directory is absent at score time, the scorer emits an explicit
  warning rather than silently falling through to the single-agent path.

4. Add a price entry under `prices:` in `arms.yaml` if the model is not already listed.

No Python code change is required.

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
`normalize_location` also has an opt-in `slug_headings` keyword (default `False`) that
slug-normalizes `path:heading` locations for the DH workflow-extraction pipeline; the scorer and
this experiment rely on the default legacy behavior — heading-style locations are returned
stripped but otherwise unchanged.

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
- Per-decoy corroboration weight for ensemble arms (how many workers flagged each decoy) — the E0
  diagnostic: if decoys accrue weight >= 2, corroboration is boosting shared error.
- Latency and deterministic cost per arm (computed from `arms.yaml` price table, not `claude -p`'s
  live `total_cost_usd` which is non-deterministic).
- E1 ablation for ensemble arms: scored at `keep_threshold=1` (dedup-only) vs `keep_threshold=2`
  (corroboration gate); the F1 delta isolates the corroboration weighting's contribution.
- **Payoff-per-cost ranking** across all arms: `(F1 − baseline_F1) / cost_usd` where baseline is
  the lowest-cost arm.  The ranked table shows the best quality gain per dollar.

### Payoff-per-cost formula

```text
payoff_per_cost = (arm_F1 − baseline_F1) / arm_cost_usd

baseline = arm with the lowest non-zero cost_usd (manifest order breaks ties)
cost_usd = (input_tokens / 1000) × input_per_1k
         + (output_tokens / 1000) × output_per_1k
```

Token counts are captured from `claude -p`'s `usage.input_tokens` / `usage.output_tokens` fields
and written to `findings/run-meta.json` by the `run` command.  The price table in `arms.yaml`
converts tokens to USD deterministically.

- Baseline arm payoff = 0.0 (numerator is zero by definition).
- Negative payoff = arm is worse AND more expensive than the baseline.
- `None` payoff = cost data unavailable (no `run-meta.json` or zero tokens recorded).

Success criteria (from `measuring-success.md`): the ensemble arm achieves recall >= the single-agent
arm, precision is not degraded, and the corroboration gate adds measurable F1 over dedup-only.
Report the numbers; do not declare success from finding counts.

## Running

Built to be runnable; not executed yet (dispatching live agents costs tokens). See `runner/` for the
CLI and its `--help`. Run the planner/scorer checks (deterministic, free) any time; run the live
arms when ready.

```bash
# Free — inspect the worker plan
uv run runner/cli.py plan

# Free — score previously written findings against gold (includes payoff-per-cost ranking)
uv run runner/cli.py score

# Costs tokens — dispatch all enabled arms from arms.yaml
uv run runner/cli.py run

# Costs tokens — full experiment
uv run runner/cli.py all
```

All arms use the identical runner invocation.  Each arm's
`.claude/skills/review-against-solid-principles/SKILL.md` controls its internal
behaviour (model, fan-out, reduce, output path).

---

**INVARIANT — keep PROMPT.md neutral.** `PROMPT.md` must stay mechanism-agnostic: a plain task
a real user would type.  All reviewer detail — schema, output paths, corpus paths, model
selection, which skill to load — lives in each arm's `.claude/`, never in the shared prompt.
Violating this conflates the experiment variable (arm strategy) with the prompt variable, making
the comparison meaningless.
