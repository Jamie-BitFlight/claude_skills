---
name: feedback-worktree-isolated-bash
description: "Worktree-isolated sessions: run every command against worktree paths, one plain command per Bash call; the isolation guard refuses any command it cannot prove is not git, and a shell redirect after cd outside the worktree runs unchecked"
metadata:
  type: feedback
---

Run every command from the session's worktree, using paths relative to it or literal absolute paths inside it. The isolation guard refuses any command it cannot prove is not git. A shell redirect after `cd` to a directory outside the worktree runs without a guard check.

Keep each Bash call to one plain command. The guard refuses any call that has:
- git inside a command substitution (`for f in $(git diff ...)`),
- a shell variable in argument position (`sed -n 1,5p $W/file`),
- or a variable name that contains `git` (`$GITHUB_TOKEN`).

For many file writes, put them in one script and run that.

The guard also refuses `git -C <sibling worktree>`. Worktrees share one object DB, so read a sibling's commit with plain `git show <sha>[:path]` from your own worktree.
