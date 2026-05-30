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
- **Overlap degree** — use the balanced rotating construction below so every rule gets the same
  number of looks. More overlap = stronger denoising, higher cost. Zero overlap = speed only,
  no corroboration signal.
- **Candidates cap per worker** — bound each worker's output (e.g. ≤ K findings) so a confused
  worker cannot flood the reducer.
- **Keep threshold** — minimum corroboration weight to survive the reducer. The script default is
  `keep_threshold=1` (recall-biased: keep everything, rank by weight, cut nothing). This default
  does NOT drop lone-worker findings — it relies on you reading the ranked output. For a
  **precision-biased gate** (where a lone worker's hallucination must fall away automatically),
  pass `--keep-threshold 2` (or higher with more overlap) so only corroborated findings survive.
  Choose the threshold deliberately per run; do not assume the default denoises.

## Balanced rotating overlap (recommended construction)

Do NOT assign overlap ad hoc. Use a cyclic block design so every rule gets the SAME number of
independent looks — uniform redundancy makes one keep-threshold mean the same thing for every
rule.

Split the ruleset into N groups (N >= 3; more groups for a bigger list). Run N agents. Give each
agent a window of `w` consecutive groups, rotating:

```text
N=3, w=2:
  Agent A -> groups [1, 2]
  Agent B -> groups [2, 3]
  Agent C -> groups [3, 1]

Coverage: group 1 -> {A, C}   group 2 -> {A, B}   group 3 -> {B, C}
Every group is seen by exactly w=2 agents.
```

Properties:

- **Uniform redundancy r = w.** Every true finding is independently reachable by exactly `w`
  agents, so its expected corroboration weight is `w`; a lone-agent hallucination has weight 1.
  A threshold of "weight >= 2" separates them identically for every rule — no rule is privileged
  by accidentally getting more looks than another (the failure mode of ad-hoc overlap).
- **`w` is the denoise knob.** `w=2` over `N=3` -> keep on any corroboration (>= 2 agents).
  Scale up (e.g. `N=5, w=3`) -> keep on majority, tolerating one missed look per true finding.
- **Per-worker scope stays small.** Each agent carries `w/N` of the rules, so the slices remain
  in the mechanical-matching band even for large rulesets.

Caveat: uniform redundancy protects against *independent* single-agent error, not *correlated*
misses. If a rule is genuinely hard, all `w` assigned agents can miss it together (weight 0,
dropped). Raising `w` is the mitigation; this is a property of voting ensembles generally.

## Procedure: recognize → decompose → dispatch → reduce

1. **Scope (Phase 0).** Fix the exact input set deterministically (a file, a `git diff`, a target).
   No reasoning yet.
2. **Enumerate.** List every rule. If the rubric is implicit, make it explicit first
   (see partitioning-patterns).
3. **Cluster into groups + plan the assignment.** Write the enumerated rules into a JSON file
   mapping stable group id → rules (3+ groups), then run
   `../scripts/plan_ensemble.py RULES.json --report-dir /abs/dir [--window 2]`. It computes the
   rotating-overlap assignment, verifies uniform redundancy, assigns each worker its groups +
   absolute OUTFILE, and prints the recommended keep-threshold. Do NOT hand-roll the assignment —
   the planner exists to prevent the path/group/overlap bookkeeping bugs.
4. **Build worker prompts.** Copy `../assets/worker-prompt-skeleton.md` once per worker in the
   plan; fill its groups (with per-group rules), identical input scope, and the planner's OUTFILE.
5. **Dispatch (Phase 1 / map).** Spawn the `plugin-creator:focused-reviewer` agent once per
   slice — it is the lean, haiku, minimal-tool worker built for this. Do NOT use
   `general-purpose`: it inherits every skill and MCP tool description, costing a constant token
   overhead on every one of the N parallel workers. Launch all in one parallel batch, low effort.
   Each writes findings in the fixed schema to its absolute OUTFILE.
6. **Reduce (Phase 2).** Run the reducer algorithm below.
7. **Emit.** Ranked, capped, structured output. An empty result is a valid terminal.

## The reducer algorithm

A working, tested implementation ships at `../scripts/reduce.py` (run
`uv run ../scripts/reduce.py REPORT_DIR --glob 'worker-*.md' [--keep-threshold N]`). The core:

```python
# findings: list of dicts from all workers, each: {group, location, verdict, evidence, severity}
def reduce(findings, keep_threshold=1):
    # 1. Keep only violations.
    violations = [f for f in findings if f.get("verdict", "VIOLATION") == "VIOLATION"]

    # 2. Dedup + count corroboration. KEY ON (group, location) — NEVER the rule slug.
    #    Workers author their own rule slugs, so keying on rule would never corroborate;
    #    `group` is the orchestrator-assigned id, identical across workers, so it collides.
    merged = {}
    for f in violations:
        key = (f["group"], normalize(f["location"]))   # group is the stable corroboration key
        m = merged.setdefault(key, {"agents": set(), "evidence": [], "severity": "low"})
        m["agents"].add(f["worker_id"])                # weight = number of DISTINCT workers
        m["evidence"].append(f["evidence"])
        m["severity"] = max_sev(m["severity"], f.get("severity"))

    # 3. weight = len(agents); drop the low-weight tail (a lone-worker finding has weight 1).
    survivors = [(k, v) for k, v in merged.items() if len(v["agents"]) >= keep_threshold]

    # 4. Rank: corroboration weight first, then severity. Correctness outranks cleanup.
    survivors.sort(key=lambda kv: (len(kv[1]["agents"]), sev_rank(kv[1]["severity"])), reverse=True)
    return survivors
```

Two contract points the live test proved necessary:

- **Key on `group`, not the rule slug.** In the worked review run, two agents flagged the same
  line with different slugs (`any-without-justification` vs `any-not-in-boundary-module`). Keying
  on the slug splits them into two weight-1 findings; keying on `group` corroborates them to
  weight 2. Keying on the rule slug is the dominant cause of "the ensemble found nothing agreed".
- **Weight = count of DISTINCT workers**, not raw report count, so one worker emitting a finding
  twice cannot fake corroboration.

`normalize` collapses trivial location differences (absolute-vs-relative path, whitespace) so the
same line from two workers collides. Tune `keep_threshold`: for recall-biased ad-hoc work, keep
weight ≥ 1 and rank; for precision-biased gates, raise it so only corroborated findings survive.

## Worker task types

Decompose into two role types — keep each worker to ONE type:

- **Detection/classification workers (map).** Apply a rule slice to the shared input, emit
  fixed-schema findings. High rigidity, cheapest model. The default worker — use the
  `plugin-creator:focused-reviewer` agent, which is exactly this with minimal tools and no
  inherited skills.
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
