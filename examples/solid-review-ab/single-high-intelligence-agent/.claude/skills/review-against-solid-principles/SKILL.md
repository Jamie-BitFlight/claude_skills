---
name: review-against-solid-principles
description: "Single-pass SOLID review — dispatches one reviewer over the complete ruleset, emitting the fixed candidate schema."
---

# Review Against SOLID Principles — Single-Pass Baseline (Arm A)

One agent holds the entire SOLID ruleset and reviews the target in one pass.

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

The `principles-reviewer` agent emits the fixed candidate schema.
