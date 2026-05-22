# Pre-Existing Issues Protocol

**Purpose**: Every issue a linter detects gets recorded. No detected problem silently disappears, regardless of whether the agent caused it.

## The Core Rule

When a linter run reveals issues in files the current agent did not modify, the phrase "pre-existing issues not related to my changes" is a trigger to act — not a reason to skip.

Two outcomes are possible. Apply the correct one based on whether the issue blocks the pipeline:

> **Pre-fix gate required**: Before acting on any discovered issue, apply the three-step
> Proactive Fix Gate from CLAUDE.md (Proactive Fix Gate section): (1) load domain skill,
> (2) state mission alignment, (3) classify complexity and route to --quick or planning.
> Do not proceed to any fix step without completing the gate.

```mermaid
flowchart TD
    Start([Linter detects issue in file agent did not touch]) --> Q1{Does this issue block CI or the current linter run?}
    Q1 -->|Yes — exit code nonzero, pipeline fails| Fix["Apply Proactive Fix Gate<br>If trivial: route to --quick<br>If complex: add to plan"]
    Q1 -->|No — advisory or informational| Record["Record it in the repo tracking system<br>Do not defer silently"]
    Fix --> Verify["Verify fix — linter exits 0<br>Include in resolution report"]
    Record --> Discover[Discover the repo tracking system]
    Discover --> Write[Write the work item]
    Write --> Report["Note in resolution report<br>'Pre-existing issues recorded — N items'"]
    Verify --> Done([Continue])
    Report --> Done
```

## Step 1 — Discover the Repo's Tracking System

Search for the tracking system in this priority order. Use the first one found:

```bash
# Check common tracking file locations
ls .claude/backlog/ 2>/dev/null
ls .claude/tasks/ 2>/dev/null
ls .planning/ 2>/dev/null
ls TODO.md 2>/dev/null
ls TODO 2>/dev/null
ls docs/TODO.md 2>/dev/null
```

Also check:

- Any `*.backlog`, `*.todo`, or `*.tasks` files at repo root
- A `tasks/` or `planning/` directory at repo root
- GSD planning directories (`.gsd/`, `gsd/`)
- SAM task files (`sam.md`, `.sam/`)

**If no tracking system exists**: Create a per-item file in `.claude/backlog/` using the format below. Note in the resolution report that you created it.

## Step 2 — Write the Work Item

Record each pre-existing issue with enough detail for future triage. Use the format appropriate to the tracking system found.

**For `.claude/backlog/` per-item files** (create one file per issue, named `{priority}-linting-{tool}-{rule}-{timestamp}.md`):

```markdown
## [LINTING] <tool>: <rule-code> in <file>:<line>

- **Source**: Pre-existing issue discovered during linting session (YYYY-MM-DD)
- **Tool**: <ruff|mypy|pyright|bandit>
- **Rule**: <rule-code> — <one-line rule description>
- **Location**: `<file>:<line>`
- **Linter message**: `<exact message from linter output>`
- **Impact**: <blocking CI | advisory | informational>
- **Added**: YYYY-MM-DD
```

**For `.claude/tasks/` directories**: Write a file named `linting-<tool>-<rule>-<timestamp>.md` with the same fields.

**For TODO.md / TODO files**: Append a line:

```
- [ ] [LINTING] <tool> <rule-code> in <file>:<line> — <one-line description> (discovered YYYY-MM-DD)
```

## Step 3 — Report in the Resolution Summary

In the resolution report (`.claude/reports/linting-resolution-*.md`), include a section:

```markdown
## Pre-Existing Issues Recorded

Found N pre-existing issues during linting run. Recorded to <tracking-system-path>.

| File | Tool | Rule | Impact | Tracking Entry |
|------|------|------|--------|----------------|
| file.py:42 | ruff | F401 | advisory | .claude/backlog/p2-linting-ruff-f401-.... |
```

If zero pre-existing issues were found, include:

```markdown
## Pre-Existing Issues

None detected in files outside the current task scope.
```

## The Triage Pipeline for Recorded Issues

Recording is step one. The full pipeline for a recorded issue, when it is later groomed:

```mermaid
flowchart TD
    Recorded([Issue recorded in tracking system]) --> Groom[Groom — what is it, where is it, what does it affect]
    Groom --> Reproduce[Reproduce — confirm the issue still exists, get exact linter output]
    Reproduce --> Plan[Plan — determine fix approach, estimate scope]
    Plan --> Select[Select appropriate agent — linting-root-cause-resolver or other]
    Select --> Execute[Execute fix using resolution workflow]
    Execute --> Verify[Verify — linter exits 0, no regressions]
    Verify --> Close[Close tracking item with resolution evidence]
```

This triage pipeline is outside the scope of the current linting session. The agent's responsibility is steps 1–3 above: detect, classify, record. Grooming and execution happen in a future session when the user prioritizes the item.

## What "Blocking" Means

A pre-existing issue is **blocking** if:

- The linter exits nonzero on a file the current task requires clean
- CI would fail on this issue (it is not in an `allowed-failures` list)
- The current task's verification step cannot pass while this issue exists

A pre-existing issue is **non-blocking** (record only) if:

- It is in a file completely unrelated to the current task
- The linter reports it as a warning, not an error
- It exists in a directory excluded from the current scope

When uncertain: treat as blocking and fix it. The cost of a false positive (fixing something that wasn't strictly required) is lower than the cost of a false negative (leaving a genuine blocker in place).
