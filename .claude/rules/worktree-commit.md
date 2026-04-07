# Worktree Commit Rule

When an agent completes edit work inside a git worktree, it MUST commit all changes before
reporting complete or closing the session.

## Rule

If `git worktree list` shows the current directory is a worktree (not the main working tree),
run:

```bash
git add -A
git commit -m "<summary of changes>"
```

before any DONE/STATUS: DONE report or session close.

## Why

Worktree changes are isolated from the main working tree. Uncommitted worktree changes are
invisible to the main branch and to other agents. Without a commit, all edits made in the
worktree are lost when the worktree is cleaned up — silently, with no diff, no history, and
no recovery path.

## Detection

```bash
# Check if running in a worktree (not the main worktree)
git rev-parse --git-dir
# Returns .git for main worktree
# Returns .git/worktrees/<name>/gitdir for a worktree — commit required
```

## Applies To

All agents: task-worker, general-purpose, specialist agents. No exceptions.
