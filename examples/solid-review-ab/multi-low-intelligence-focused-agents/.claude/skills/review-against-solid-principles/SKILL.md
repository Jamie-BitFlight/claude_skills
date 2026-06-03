---
name: review-against-solid-principles
description: "Arm B (ensemble) of the SOLID A/B experiment. Fans the SOLID ruleset across 5 overlapping Haiku focused workers over the same target, then reduces by corroboration. Use to produce the multi-low-intelligence ensemble findings to compare against the single Sonnet baseline."
---

# Review Against SOLID Principles — Ensemble (Arm B)

The SOLID ruleset is partitioned across overlapping workers, all reviewing the same code, then
merged by a deterministic corroboration-weighting reducer.

Fixed paths (relative to this arm directory, the `claude -p` working directory):

- Ruleset: `../ruleset/solid-rules.json`
- Targets: every `*.py` under `../corpus/cases/`
- Worker reports: `./findings/workers/` (absolute path when calling the planner/workers)
- Final output: `./findings/findings.md`
- Ensemble scripts: `plan_ensemble.py` and `reduce.py` from the ensemble-rule-review skill. From this
  arm directory they are at `../../../plugins/plugin-creator/skills/ensemble-rule-review/scripts/`;
  the runner may pass an absolute path instead — use whichever it provides.

1. Plan (deterministic). Run the planner over the shared ruleset, with `./findings/workers/` (as an
   ABSOLUTE path) as the report dir:

   ```bash
   uv run <scripts>/plan_ensemble.py ../ruleset/solid-rules.json \
     --report-dir "$(pwd)/findings/workers" --window 2 --json
   ```

   This yields 5 workers (A-E), each covering 2 consecutive SOLID groups, uniform redundancy r=2,
   recommended `keep_threshold = 2`.

2. Map (parallel). Spawn the `principles-reviewer` agent once per worker in the plan. Give
   each its `groups` + per-group `rules` as YOUR RULE SLICE, the identical targets (all files under
   `../corpus/cases/`), and its planner `outfile`. Run all 5 in one parallel batch. Workers write
   `location` as `corpus/cases/<file>:<line>`.

3. Reduce (deterministic). Merge by corroboration on `(group, location)` and write the ranked result
   to `./findings/findings.md`:

   ```bash
   uv run <scripts>/reduce.py "$(pwd)/findings/workers" --glob 'worker-*.md' \
     --keep-threshold 2 > ./findings/findings.md
   ```

   For the E1 ablation, the runner also reduces at `--keep-threshold 1` (dedup-only) to isolate the
   corroboration weighting's F1 contribution.

The reduced, ranked findings in `./findings/findings.md` are the arm's output — the scorer parses
them against `../corpus/gold.json`.

## Candidate output schema

Workers emit findings in this exact format — one block per finding, separated by a blank line.
Fields must appear in this order:

```text
- group: <S|O|L|I|D>
  location: <corpus/cases/filename.py>:<line>
  rule: <free-form descriptive slug>
  verdict: VIOLATION
  severity: critical | high | medium | low
  evidence: "<exact short quote from the reviewed file>"
```

- `group` must match the worker's assigned SOLID group letter.
- `location` is experiment-root-relative: `corpus/cases/<file>:<line>`.
  Never emit an absolute path or arm-directory-relative path (no leading `/` or `../`).
- Emit only `VIOLATION` findings. If no violations are found, emit nothing.

The reducer keys corroboration on `(group, location)`, so the `group` field and the
experiment-root-relative `location` format are critical for the E0/E1 diagnostics.
