# Worker Prompt Skeleton

Copy this template once per rule slice, fill every `{{PLACEHOLDER}}`, and dispatch the workers
in parallel (cheapest tier, low effort). Every worker shares the SAME input and the SAME fixed
schema; only `YOUR RULE SLICE` differs between workers, and slices deliberately overlap.

## Worker prompt template

```text
You are a rigid {{WORKER_ROLE}}. cwd: {{WORKING_DIR}}. NO creativity — follow these steps exactly.

GOAL: {{ONE_SENTENCE_GOAL}}

INPUT — review ONLY this (identical for every worker): {{INPUT_SCOPE}}

YOUR RULE SLICE — apply ONLY these rules. Each rule carries its OWN stable group id (the same id
the other worker assigned to that group also uses). You may hold rules from more than one group:
- [group {{GROUP_OF_RULE_1}}] {{RULE_1}}
- [group {{GROUP_OF_RULE_2}}] {{RULE_2}}
- [group {{GROUP_OF_RULE_3}}] {{RULE_3}}

STEP 1 — For each rule, locate every place in the input where it applies ({{DETECTION_METHOD}}).
STEP 2 — For each location, decide VIOLATION or PASS strictly against the rule text.
         Do NOT infer, extrapolate, or judge anything outside your rule slice.
STEP 3 — Emit one block per finding in the FIXED SCHEMA below. No prose outside the blocks.

FIXED CANDIDATE SCHEMA (emit this EXACT block shape, one block per finding — the reducer
parses it literally, so do not rename fields or change the leading "- group:"):
- group: {{THE GROUP ID OF THE RULE THIS FINDING VIOLATES — per finding, NOT a fixed worker id}}
  rule: {{free-form descriptive slug — for humans only, NOT used to match findings}}
  location: {{file:line}}
  verdict: VIOLATION | PASS
  severity: {{critical | high | medium | low}}
  evidence: "{{exact short quote from the input}}"

CORROBORATION KEY — the reducer dedups on (group, location), NOT on your rule slug. `group` MUST
be the id of the specific RULE that this finding violates — not a single per-worker constant. If
you hold rules from two groups (e.g. groups 1 and 2 under rotating overlap), a finding against a
group-1 rule emits `group: 1` and a finding against a group-2 rule emits `group: 2`. Tagging every
finding with one worker-level id would mislabel the second group and break corroboration with the
other worker assigned to it. The rule slug may differ between workers; only the group id must match.

OUTPUT CONTRACT:
Write all findings to {{OUTFILE}}. {{OUTFILE}} MUST be an ABSOLUTE path (e.g.
/home/user/project/.tmp/scratch/reports/worker-{{ID}}.md). Do NOT use a relative path — workers
may resolve a different cwd, scattering outputs the reducer cannot find.
FINAL MESSAGE:
STATUS: DONE
File: {{OUTFILE}}
Count: <total>, violations: <n>
Then inline every VIOLATION block. If none, state that explicitly.

Trace every finding to a real located hit. No invented locations or quotes.
```

## Dispatch checklist

- Spawn the `plugin-creator:focused-reviewer` agent (lean, haiku, minimal tools) — NOT
  `general-purpose`, which inherits every skill and MCP tool description and burns tokens on
  every worker. Fill this skeleton into its prompt as the TARGET / RULE SLICE / GROUP / OUTFILE.
- If the target is a website or API endpoint, add the ONE specific MCP tool the worker needs to
  the spawn `tools` list — do not grant all tools.
- One worker per rule slice; slices overlap so each genuine finding sits in 2+ workers' coverage.
- Model: cheapest tier (haiku). Effort: low. Run all workers in one parallel batch.
- Keep each slice small enough that the job is mechanical matching, not inference.
- Give every worker the identical `INPUT_SCOPE`. (Shard input only as a secondary axis when one
  worker cannot hold it — keep rule-overlap within each shard.)

## Reducer input contract

The reducer script `../scripts/reduce.py` consumes the worker output files and keys corroboration
on `(group, location)` — never the free-form `rule` slug. Keep `group` identical across all
workers who hold that group, and write `location` as `file:line`; the reducer normalizes it to
`basename:line` so two workers collide into one weighted entry. Run it with:

```bash
uv run ../scripts/reduce.py {{ABSOLUTE_REPORT_DIR}} --glob 'worker-*.md' [--keep-threshold N]
```
