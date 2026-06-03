# Measuring Success

How to know whether an ensemble actually works — and not be fooled by the metric that lies. Ordered
cheapest-first: the free diagnostic needs no labels and can falsify the design in minutes; the full
evaluation needs a labeled corpus.

## What NOT to measure: raw finding count

Finding count is the trap. "The ensemble returned 14 findings, the single agent returned 13" is a
LATENCY anecdote wearing a quality costume. Count parity is not recall parity: the 14 could include
5 false positives and still miss 6 true findings. The entire adversarial risk of this pattern —
corroboration boosting a shared-model error — surfaces as false positives, which a raw count cannot
see. Never report counts as evidence of quality.

SOURCE: the skill's own origin anecdote (1 Sonnet pass, 13 findings vs 4 Haiku workers, 14 findings,
~35x faster) confounds three simultaneous changes (model tier, architecture, measurement) and has
no gold set; it is unreproduced. Treat it as a speed observation only.

## Step 0 — The free diagnostic (no gold set, run first)

Before building any labeled corpus, dump the corroboration-weight distribution per `(group,
location)` from existing worker output logs (the reducer already computes weight = count of
distinct workers; see [./orchestrator-playbook.md](./orchestrator-playbook.md) and `../scripts/
reduce.py`).

Read the distribution:

- If weight is near-constant per group (≈`window` for everything the workers emit, ≈0 otherwise),
  the denoising instrument is empirically degenerate — agreement carries no information and the
  reducer is just a deduplicating pass. This happens when workers sharing a group produce
  near-identical output (same model, same input, same prompt, low effort). Fix: inject within-group
  diversity (see [./experiment-matrix.md](./experiment-matrix.md)) before investing in a full eval.
- If weight varies meaningfully across findings (some at `window`, some lower), the instrument is
  discriminating — proceed to the full evaluation to quantify how well.

This is the fastest falsification of the central claim and costs nothing but reading logs you
already have.

## Step 1 — Build a labeled gold corpus

Pick inputs and have a human (or a stronger independent model, then human-spot-checked) adjudicate
the ground-truth findings per rule. Without this, recall and precision are unknowable. Reuse an
input the single-pass skill already reviewed so you have a baseline.

## Step 2 — Measure precision / recall / F1, not counts

Against the gold set, for each configuration:

| Metric | Definition | Why it matters |
|---|---|---|
| Recall | true findings caught / total true findings | The pattern's headline promise (overlap raises coverage) |
| Precision | true findings / all reported findings | Catches corroboration-boosted false positives |
| F1 | harmonic mean of precision and recall | Single comparison number across configs |
| False-positive rate on injected systematic errors | see Step 3 | Direct test of the shared-bias failure mode |
| Latency / cost | wall-clock and token spend | The contested-least claim; usually the ensemble wins here |

## Step 3 — Falsification tests (do these, not just the happy path)

The design makes specific predictions. Test the ones that would DISPROVE it:

1. Ablate the corroboration weighting (reducer with vs without weighting). If F1 does not improve
   with weighting on, the corroboration step adds nothing and the value is just dedup + parallelism.
2. Sweep N / window. Bagging predicts F1 plateaus at the correlated-error floor; Condorcet predicts
   F1 can DEGRADE as homogeneous correlated workers are added. A rising-then-falling F1 curve
   confirms correlated-error dominance.
3. Heterogeneous vs homogeneous arm. Run one arm with N identical cheap workers, one with diverse
   model families. If the heterogeneous arm wins, ρ (shared error) was the bottleneck — the
   predicted result.
4. Inject known systematic-error constructs (cases the cheap worker reliably misreads) and measure
   whether corroboration boosts the false finding above the keep threshold. This is the direct
   falsification of "a single worker's hallucination sinks below threshold."
5. Repeat each arm 5+ times. Single LLM runs are non-deterministic; one run is not a measurement.

SOURCE: variance floors at ρσ² and adding correlated estimators cannot cross it (Breiman 2001;
ESL §15.2); positively correlated jurors can lower majority accuracy as the jury grows (Kaniovski
2010); diverse panels beat single/homogeneous judges and are cheaper (Verga et al., *Replacing
Judges with Juries*, arXiv:2404.18796, 2024).

## Step 4 — Calibrate the keep threshold on the gold set

The keep threshold decides whether 2-of-`window` agreement is signal or shared bias. The right
value depends on the measured ρ and per-worker competence — it cannot be guessed. Sweep the
threshold against the gold set and pick the value that maximizes F1 (or recall at a precision
floor, if false negatives are costlier). Do not assume the script default denoises; the default
`keep_threshold=1` drops nothing.

## Success definition

An ensemble succeeds when ALL hold against the gold set, not the count:

- Recall ≥ the single-pass baseline.
- Precision not degraded versus the baseline (no corroboration-boosted false-positive inflation).
- Corroboration weighting adds measurable F1 over a dedup-only reducer (Step 3.1) — otherwise drop
  the weighting and keep the cheaper dedup.
- Latency and cost lower than the single-pass baseline.

Record the baseline-vs-ensemble numbers as the skill's evaluation evidence. The conversion
validation gate in [./conversion-workflow.md](./conversion-workflow.md) consumes these.
