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

## Task-owned runtime state

Reuse immutable source references and installed runtimes for an admitted runtime check. Retain the
compact report, logs, and source references needed for its claim, then clean task-owned disposable
directories when work finishes or is cancelled. On resource exhaustion, stop the branch and report
the limit; RAM-backed storage is not overflow staging. See `task-outcome-discipline.md` for
admitting the branch in the first place.

For a prose-only change, run changed-file checks with the existing shared toolchain and cache.
Mandatory repository setup, including required compatibility generation, remains required. Do
not add runtime setup, copy a runtime, or provision a worktree-local runtime beyond that
mandatory setup. When a needed tool is unavailable, report the smallest exact check that
requires it before provisioning anything.

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

## Where a committed file goes

`.claude/` holds Claude Code configuration; `docs/` holds project documentation. Before creating a
file in either, `ls` the likely parent — an existing directory convention decides the location.

## Hard rule

Never write agent output to `.claude/` — writes there are commonly gated by a confirmation
prompt outside this repo's control; do not rely on `.claude/` for disposable output regardless.
