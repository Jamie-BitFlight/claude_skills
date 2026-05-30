# Worker Prompt Skeleton

Copy this template once per rule slice, fill every `{{PLACEHOLDER}}`, and dispatch the workers
in parallel (cheapest tier, low effort). Every worker shares the SAME input and the SAME fixed
schema; only `YOUR RULE SLICE` differs between workers, and slices deliberately overlap.

## Worker prompt template

```text
You are a rigid {{WORKER_ROLE}}. cwd: {{WORKING_DIR}}. NO creativity — follow these steps exactly.

GOAL: {{ONE_SENTENCE_GOAL}}

INPUT — review ONLY this (identical for every worker): {{INPUT_SCOPE}}

YOUR RULE SLICE — apply ONLY these rules (your partial, deliberately-overlapping ruleset):
- {{RULE_1}}
- {{RULE_2}}
- {{RULE_3}}

STEP 1 — For each rule, locate every place in the input where it applies ({{DETECTION_METHOD}}).
STEP 2 — For each location, decide VIOLATION or PASS strictly against the rule text.
         Do NOT infer, extrapolate, or judge anything outside your rule slice.
STEP 3 — Emit one block per finding in the FIXED SCHEMA below. No prose outside the blocks.

FIXED CANDIDATE SCHEMA (emit this EXACT block shape, one block per finding — the reducer
parses it literally, so do not rename fields or change the leading "- group:"):
- group: {{YOUR ASSIGNED GROUP ID — the stable rule-group number, identical across all workers}}
  rule: {{free-form descriptive slug — for humans only, NOT used to match findings}}
  location: {{file:line}}
  verdict: VIOLATION | PASS
  severity: {{critical | high | medium | low}}
  evidence: "{{exact short quote from the input}}"

CORROBORATION KEY — the reducer dedups on (group, location), NOT on your rule slug. Two workers
who both hold this group and flag the same line corroborate each other even if they name the rule
differently. That is why `group` MUST be the orchestrator-assigned id, identical across workers,
and `rule` is descriptive only.

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
