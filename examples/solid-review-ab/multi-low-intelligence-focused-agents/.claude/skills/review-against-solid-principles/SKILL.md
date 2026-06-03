---
name: review-against-solid-principles
description: "Ensemble SOLID review — fans the ruleset across overlapping focused workers over the same code, then reduces by corroboration."
---

# Review Against SOLID Principles — Ensemble (Arm B)

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

   Use the worker assignment and recommended keep-threshold from the planner's output.

2. Map (parallel). Spawn the `principles-reviewer` agent once per worker in the plan. Give
   each its `groups` + per-group `rules` as YOUR RULE SLICE, the identical targets (all files under
   `../corpus/cases/`), and its planner `outfile`. Run all workers in one parallel batch. Workers
   write `location` as `corpus/cases/<file>:<line>`.

3. Reduce (deterministic). Merge by corroboration on `(group, location)` and write the ranked result
   to `./findings/findings.md`:

   ```bash
   uv run <scripts>/reduce.py "$(pwd)/findings/workers" --glob 'worker-*.md' \
     --keep-threshold 2 > ./findings/findings.md
   ```

The reduced, ranked findings in `./findings/findings.md` are the arm's output — the scorer parses
them against `../corpus/gold.json`.

Each `principles-reviewer` worker emits the fixed candidate schema.
