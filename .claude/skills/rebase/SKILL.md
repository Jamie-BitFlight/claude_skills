---
name: rebase
description: "Strategic rebase with mandatory pre-analysis. Use when asked to rebase a branch onto main (or any target). Runs a file-level diff of both sides before touching git, produces a per-file disposition plan (KEEP/MERGE/DROP/REWRITE), and only then executes the rebase. Prevents surprise conflicts and silent data loss from rebasing without knowing what changed on both sides. Triggers: 'rebase', 'rebase onto main', 'rebase this branch', 'rebase and merge', 'update branch from main'."
---

# Rebase

## Mandatory Pre-Rebase Analysis

Complete all steps before running `git rebase`. Do not skim commit messages as a proxy for file-level changes — read the actual diffs.

### Step 1 — Identify the merge base and branch files

```bash
MERGE_BASE=$(git merge-base <branch> <target>)
git diff <target>...<branch> --name-only        # files touched by the branch
git diff "${MERGE_BASE}..<target>" --name-only  # files changed on target since divergence
```

### Step 2 — Diff overlapping files

For every file that appears in BOTH lists (changed on branch AND changed on target since divergence), run:

```bash
git diff "${MERGE_BASE}..<target>" -- <file>    # what target changed
git diff "${MERGE_BASE}..<branch>" -- <file>    # what the branch changed
```

Read both diffs. Determine what each side changed and in which regions.

### Step 3 — Assign a disposition to every overlapping file

| Disposition | When to use |
|---|---|
| KEEP | Branch version wins; target change is irrelevant or already superseded by the branch |
| MERGE | Both sides changed different regions — list which regions each side owns |
| DROP | Branch change is superseded by what target already landed; discard it |
| REWRITE | Semantic intent of the branch change survives, but the implementation must change to account for what target did |

Files touched only by the branch (no overlap with target) — mark as NO_CONFLICT.

### Step 4 — State the plan before executing

Output the full plan in this format before any `git rebase` command:

```text
Pre-rebase plan — <branch> onto <target>

Overlapping files:
  path/to/file.py: MERGE — branch adds X in foo(); target rewrites bar(); no region overlap
  path/to/other.py: DROP — target already landed the same change
  path/to/third.py: REWRITE — branch intent survives; must account for renamed parameter on target

No-conflict files (branch-only): path/a.py, path/b.py
```

### Step 5 — Execute the rebase

```bash
git rebase <target>
```

On each conflict:
1. Resolve according to the plan.
2. If the conflict deviates from the plan (e.g., a region marked NO_CONFLICT has an unexpected conflict), stop, explain the deviation, update the plan entry, then resolve.

After completing, verify with `git log --oneline` and run the test suite.

## Rules

- Do not run `git rebase` before writing the Step 4 plan.
- Do not resolve conflicts by accepting one side wholesale without checking the plan.
- Do not use commit message titles as a substitute for reading file-level diffs.
