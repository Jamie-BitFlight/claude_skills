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
Return: STATUS: DONE + path to the file
```

The returned path is for the requesting agent to read directly. Never pass it on as the input of a
later step, agent, or gate — anything a subsequent step reads is an inter-step handoff and goes
through the artifact or plan operations instead.

## Hard rule

Never write agent output to `.claude/` — every write to that directory triggers a security
prompt for the user.
