# Commit Cadence and Agent Worktrees

Commit often, in small file-scoped commits. Push in batches. Use worktrees for concurrent
agent writes. These three rules solve two specific race conditions — not a general aversion to
committing.

## The two real race conditions

1. **Same-tree concurrent writes + prek's stash-on-commit.** `prek` stashes unstaged changes
   before running hooks and restores them after. If an agent is mid-edit in the same working
   tree while a commit runs, the stash/restore cycle can collide with that agent's in-progress
   writes. This is why commits must be scoped to exactly the files a completed piece of work
   touched, and must wait until any agent actively writing those specific files has gone idle —
   not why commits should be deferred in general.
2. **Commit-and-push-every-time triggers CI + a review agent per push.** Each push fires a CI
   run and an automated review pass; batching many small pushes into fewer, larger ones avoids
   flooding webhook subscribers with redundant alerts. This governs **push** cadence, not
   **commit** cadence — commits are local and free.

## Corrected workflow

- **Commit early and often.** Each discrete piece of completed work gets its own commit —
  many small checkpoints, not one big commit at the end of a session. Uncommitted work in a
  shared working tree is fragile (lost on crash, wipe, or accidental `git reset`/`checkout`) and
  invisible to worktree-isolated agents (see below).
- **Push in batches.** Group related commits and push together, not on every commit. This is the
  actual lever for reducing CI/webhook noise — not withholding commits.
- **Commit via explicit file list — never blanket stage-then-commit.**

  ```bash
  # Right — commits exactly these files regardless of what else is unstaged elsewhere
  git commit path/to/file1.py path/to/file2.md -m "..."

  # Wrong — sweeps up any concurrent agent's in-progress edits into the wrong commit
  git add -A && git commit -m "..."
  git reset && git add path/to/file1.py path/to/file2.md && git commit -m "..."
  ```

- **Spawn writing agents into their own worktree** (`Agent(isolation: "worktree", ...)`) whenever
  the task involves file edits that could run concurrently with other work in this session —
  not just for genuinely long-running or parallel-batch work. This eliminates race condition 1
  entirely: the agent's working tree is physically separate, so no shared-tree stash collision is
  possible regardless of what else is being edited concurrently.
- **A worktree only sees committed state.** `git worktree add` checks out a ref (a commit), not
  the current working tree's uncommitted changes — those are invisible to a new worktree. Before
  spawning a worktree-isolated agent, commit (not necessarily push) whatever the agent needs to
  build on, or it will start from a stale base and miss recent work. Tell the agent explicitly to
  verify it's on the expected commit before starting.

## When NOT to use a worktree

Read-only agents (review, analysis, research) never need isolation — there's nothing for them to
collide with. Reserve `isolation: "worktree"` for agents that write files.
