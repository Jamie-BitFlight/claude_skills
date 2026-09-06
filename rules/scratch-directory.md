# Scratch Directory Convention

`.tmp/scratch/` is the fallback output location for agent reports, analysis, and temporary
files when no explicit path is given in the task or prompt. Superseded by any task-specific
directive.

```text
.tmp/scratch/
├── reports/     ← agent research output, investigation findings
├── analysis/    ← intermediate analysis, comparison tables
├── tests/       ← throwaway test scripts, one-off verifications
├── plans/       ← draft plans not ready for SAM
└── notes/       ← scratchpad, working hypotheses
```

Add subdirectories freely. Nothing in `.tmp/` is committed, linted, or quality-checked.

## Delegation pattern

```text
DEFINITION OF SUCCESS:
Write findings to .tmp/scratch/reports/YYYYMMDD-<slug>.md
Return: STATUS: DONE (or PARTIAL) + path to the file
```

The returned path is for the requesting agent to read directly. Do not invent an ad hoc handoff by
passing it to a later step, agent, or gate that the producing workflow does not already define —
that step reads results through the artifact or plan operations instead. Exception: when a skill's
own documented pipeline explicitly names a scratch path as the input to its next stage (for example
passing a change plan or a draft-output path from one stage to a validator or verifier stage within
that same skill), that skill's stage definitions govern and the handoff is allowed.

## Hard rule

Never write agent output to `.claude/` — every write to that directory triggers a security
prompt for the user.
