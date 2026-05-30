# Ad-hoc Orchestrator Playbook

How an orchestrator runs the ensemble on the fly, mid-task, without a pre-built skill. Use when
you face rule-following work (apply a checklist/rubric against an input) and want higher recall +
lower latency than holding the whole ruleset in one pass yourself.

## Table of Contents

- [Recognize the opportunity](#recognize-the-opportunity)
- [Partition the ruleset, not the input](#partition-the-ruleset-not-the-input)
- [The knobs](#the-knobs)
- [Procedure: recognize → decompose → dispatch → reduce](#procedure-recognize--decompose--dispatch--reduce)
- [The reducer algorithm](#the-reducer-algorithm)
- [Worker task types](#worker-task-types)
- [Worked examples](#worked-examples)
- [Anti-patterns](#anti-patterns)

## Recognize the opportunity

Trigger signals: an instruction with "ensure … follows", "review for", "look for …
opportunities", a named framework, or any enumerable rubric of 10+ criteria you would otherwise
apply in one pass. For the full recognition typology, see
[./partitioning-patterns.md](./partitioning-patterns.md).

## Partition the ruleset, not the input

Every worker reviews the SAME input; only its rule slice differs. The denoising comes from
overlapping rule coverage on shared input — multiple workers independently reaching the same
finding, which the reducer counts as corroboration. Sharding the input (different files per
worker) buys speed but NOT denoising, because no two workers can corroborate the same location.
Shard input only as a secondary axis when one worker cannot hold the whole input, and keep
rule-overlap within each shard.

## The knobs

- **Worker count** — typically 3–7. One worker per natural rule cluster.
- **Overlap degree** — each rule appears in at least 2 workers' slices. More overlap = stronger
  denoising, higher cost. Zero overlap = speed only, no corroboration signal.
- **Candidates cap per worker** — bound each worker's output (e.g. ≤ K findings) so a confused
  worker cannot flood the reducer.
- **Keep threshold** — minimum corroboration weight to survive the reducer. Higher = more
  precision, lower recall. For recall-biased work, keep weight ≥ 1 and rank rather than cut hard.

## Procedure: recognize → decompose → dispatch → reduce

1. **Scope (Phase 0).** Fix the exact input set deterministically (a file, a `git diff`, a target).
   No reasoning yet.
2. **Enumerate.** List every rule. If the rubric is implicit, make it explicit first
   (see partitioning-patterns).
3. **Cluster into overlapping slices.** Group rules into 3–7 scenario-bound slices; ensure each
   rule lands in ≥ 2 slices.
4. **Build worker prompts.** Copy `../assets/worker-prompt-skeleton.md` once per slice; fill the
   placeholders; set the identical input scope on all.
5. **Dispatch (Phase 1 / map).** Launch all workers in one parallel batch, cheapest tier, low
   effort. Each writes findings in the fixed schema.
6. **Reduce (Phase 2).** Run the reducer algorithm below.
7. **Emit.** Ranked, capped, structured output. An empty result is a valid terminal.

## The reducer algorithm

```python
# findings: list of dicts from all workers, each: {rule_id, location, verdict, evidence, severity}
from collections import defaultdict

def reduce(findings, keep_threshold=1):
    # 1. Keep only violations.
    violations = [f for f in findings if f["verdict"] == "VIOLATION"]

    # 2. Dedup + count corroboration: same defect, same place, same rule -> one weighted entry.
    merged = defaultdict(lambda: {"weight": 0, "evidence": [], "severity": None})
    for f in violations:
        key = (normalize(f["rule_id"]), normalize(f["location"]))
        m = merged[key]
        m["weight"] += 1                      # +1 per corroborating worker
        m["evidence"].append(f["evidence"])
        m["severity"] = max_sev(m["severity"], f.get("severity"))

    # 3. Drop the low-weight tail; a lone-worker finding has weight 1.
    survivors = [(k, v) for k, v in merged.items() if v["weight"] >= keep_threshold]

    # 4. Rank: corroboration weight first, then severity. Correctness outranks cleanup.
    survivors.sort(key=lambda kv: (kv[1]["weight"], sev_rank(kv[1]["severity"])), reverse=True)
    return survivors
```

`normalize` collapses trivial differences (whitespace, line drift) so the same finding from two
workers collides. Tune `keep_threshold`: for recall-biased ad-hoc work, keep weight ≥ 1 and rank;
for precision-biased gates, raise the threshold so only corroborated findings survive.

## Worker task types

Decompose into two role types — keep each worker to ONE type:

- **Detection/classification workers (map).** Apply a rule slice to the shared input, emit
  fixed-schema findings. High rigidity, cheapest model. The default worker.
- **Verifier workers (optional second pass).** Take a single surviving candidate plus the input
  and return one constrained verdict (CONFIRMED / PLAUSIBLE / REFUTED). Use when precision must be
  raised beyond what corroboration weighting alone provides.

The orchestrator itself is the **reducer** — mid tier (sonnet), medium effort — never a worker.

## Worked examples

- **Rule partition for denoising (the journal review).** One input file, 4 workers, each a
  different quarter of the rule list, overlapping coverage. Result: comparable recall to a single
  expensive pass, far faster, with hallucinations diluted by corroboration.
- **Territory partition for recall (this repo survey).** A large input set sharded across finder
  workers (different plugins per worker) for breadth. This is the input-shard axis — it raised
  recall but, with non-overlapping territory, gave no per-finding corroboration. The narrow
  second pass demonstrated the recall cost of over-broad slices: smaller scope per worker found
  more. Lesson: keep slices small, and add rule-overlap when you need denoising, not just breadth.

## Anti-patterns

- **Non-overlapping partition when you need reliability.** Gives speed only; no corroboration
  signal, so single-worker hallucinations survive.
- **Slices too broad.** Overloads the cheap worker back into the silent-criteria-dropping regime
  the pattern exists to avoid.
- **Reducing before dedup.** Corroboration counting is meaningless until `(rule_id, location)` is
  normalized — dedup first, then weight.
- **An expensive model as a worker.** Wastes the economics; cheap workers + overlap is the design.
