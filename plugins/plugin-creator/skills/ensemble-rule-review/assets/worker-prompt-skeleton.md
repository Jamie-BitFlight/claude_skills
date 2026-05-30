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

FIXED CANDIDATE SCHEMA (emit this exact shape — the reducer depends on it):
- rule_id: {{stable id of the rule}}
  location: {{file:line or section anchor}}
  verdict: VIOLATION | PASS
  evidence: "{{exact short quote from the input}}"
  severity: {{high | med | low}}

OUTPUT CONTRACT:
Write all findings to {{OUTFILE}}.
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

The reducer (see `../references/orchestrator-playbook.md`) consumes the worker output files and
keys on `(rule_id, location)` to count corroboration. Keep `rule_id` and `location` stable and
normalized across workers so the same finding from two workers collides into one weighted entry.
