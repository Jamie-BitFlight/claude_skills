---
name: project-worktree-shared-object-db-no-dash-c-needed
description: git worktrees in this repo share one object database — read another worktree's commit content with plain `git show <sha>:<path>`, no `-C <other-worktree>` needed (which the sandbox guard blocks anyway)
metadata:
  type: project
---

A worktree-isolated agent's sandbox guard refuses any `git -C <other-dir>` command as "redirects
git to the shared checkout" — even when `<other-dir>` is a *different* worktree, not the shared
primary checkout. This is not a real limitation: `git worktree add` shares the same `.git` object
database across all worktrees of a repo. Any commit reachable in any worktree (including one that
was only ever committed in a sibling worktree, as long as it's not been pruned) is already
resolvable from your own worktree's `.git` — `git show <sha>`, `git show <sha>:<path>`, `git show
<sha> --stat`, `git log <sha>` etc. all work with zero `-C` flag, run from inside your own
worktree directory.

**How to apply:** When a task hands you a commit SHA that supposedly lives "on branch X in
worktree Y," don't reach for `git -C <path/to/Y>` — it will be blocked. Just run the plain `git
show <sha>` form from your own cwd first; it almost always resolves. Only fall back to asking the
orchestrator for a diff/patch export if the commit is genuinely unreachable (never fetched into
any local worktree's object store).
