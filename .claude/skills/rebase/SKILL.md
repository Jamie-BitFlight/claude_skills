---
name: rebase
description: "Strategic rebase with mandatory pre-analysis. Use when asked to rebase a branch onto main (or any target). Runs a file-level diff of both sides before touching git, produces a per-file disposition plan (KEEP/MERGE/DROP/REWRITE), and only then executes the rebase. Prevents surprise conflicts and silent data loss from rebasing without knowing what changed on both sides. Triggers: 'rebase', 'rebase onto main', 'rebase this branch', 'rebase and merge', 'update branch from main'."
---

# Rebase

## Mandatory Pre-Rebase Analysis

Complete all steps below before running `git rebase`.

### Step 1 — Identify the merge base and branch files

```bash
MERGE_BASE=$(git merge-base <branch> <target>)
git diff <target>...<branch> --name-only        # files touched by the branch
git diff "${MERGE_BASE}..<target>" --name-only  # files changed on target since divergence
```

### Step 2 — Diff overlapping files

For each file appearing in both lists above, read both sides:

```bash
git diff "${MERGE_BASE}..<target>" -- <file>    # what target changed
git diff "${MERGE_BASE}..<branch>" -- <file>    # what the branch changed
```

Determine what each side changed and in which regions.

### Step 3 — Assign a disposition to every overlapping file

| Disposition | When to use |
|---|---|
| KEEP | Branch version wins; target change is irrelevant or already superseded |
| MERGE | Both sides changed different regions — list which regions each side owns |
| DROP | Branch change superseded by what target already landed; discard it |
| REWRITE | Branch intent survives, but implementation must change to account for target's changes |
| NO_CONFLICT | File touched only by the branch — no overlap with target |

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
git rebase <target> <branch>
```

Pass `<branch>` — the same one Steps 1-4 analysed. `git rebase`'s positional form is
`[<upstream> [<branch>]]`; omitting `<branch>` rebases whatever is currently checked out, which
is a different branch whenever the analysis targeted one you are not standing on. That rewrites
commits the plan never looked at and leaves the requested branch untouched.

Naming `<branch>` makes git check it out first, which fails with `fatal: '<branch>' is already
used by worktree at ...` when another worktree holds it. Run the rebase from the worktree that
owns the branch:

```bash
git worktree list          # find the worktree whose HEAD is <branch>
```

Then run the `git rebase <target> <branch>` above from that directory. Do not free the branch by
detaching or switching the other worktree — another session may be mid-task in it.

On each conflict:

1. Resolve according to the plan.
2. When a conflict deviates from the plan (e.g., a region marked NO_CONFLICT has an unexpected conflict): stop, explain the deviation, update the plan entry, then resolve.

After completing, verify with `git log --oneline` and run the test suite.

## Rules

- Write the Step 4 plan before running `git rebase`.
- Name `<branch>` in the `git rebase` invocation — never rely on the current checkout matching it.
- Resolve each conflict according to the plan — check before accepting either side.
- Read file-level diffs (Step 2); commit message titles are not a substitute.
