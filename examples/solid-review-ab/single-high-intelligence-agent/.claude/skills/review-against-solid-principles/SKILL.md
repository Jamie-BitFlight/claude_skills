---
name: review-against-solid-principles
description: "Arm A (baseline) of the SOLID A/B experiment. Reviews a target file against the complete SOLID ruleset in a single high-intelligence pass, emitting the fixed candidate schema. Use to produce the single-agent baseline findings to compare against the multi-worker Haiku ensemble."
---

# Review Against SOLID Principles — Single-Pass Baseline (Arm A)

One agent holds the entire SOLID ruleset and reviews the target in one pass. No partitioning, no
overlap, no reducer.

## Procedure

Fixed paths (relative to this arm directory, the `claude -p` working directory):

- Ruleset: `../ruleset/solid-rules.json`
- Targets: every `*.py` under `../corpus/cases/`
- Output: `./findings/findings.md`

1. Dispatch ONE `principles-reviewer` subagent. Give it the ruleset path, the list of
   target files, and the output path. It reads the full ruleset and every target, applies all rules
   in a single pass, and writes the fixed-schema findings to `./findings/findings.md`.
2. Do NOT partition the rules, fan out, or spawn more than one reviewer. One subagent does the
   entire review.
3. Write the findings to `./findings/findings.md`.

Write each finding `location` as `corpus/cases/<file>:<line>` (experiment-root-relative, never
an absolute path or arm-directory-relative path).

## Candidate output schema

Emit findings in this exact format — one block per finding, separated by a blank line.
Fields must appear in this order:

```text
- group: <S|O|L|I|D>
  location: <corpus/cases/filename.py>:<line>
  rule: <free-form descriptive slug>
  verdict: VIOLATION
  severity: critical | high | medium | low
  evidence: "<exact short quote from the reviewed file>"
```

Emit only `VIOLATION` findings. If no violations are found, emit nothing.
