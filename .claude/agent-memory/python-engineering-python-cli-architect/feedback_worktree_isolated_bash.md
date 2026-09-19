---
name: feedback-worktree-isolated-bash
description: "Worktree-isolated sessions: run every command against worktree paths, one plain command per Bash call; the isolation guard checks only git, so non-git mutators (uv add, pip, redirects) hit any cd target silently"
metadata:
  type: feedback
---

Run every command from the session's worktree, using paths relative to it or literal absolute paths inside it. The isolation guard blocks only git. `uv add`, `uv remove`, `pip install` and shell redirects run without any check against whatever directory you `cd` into, and that includes the shared main checkout.

Keep each Bash call to one plain command. The guard refuses as "too complex to verify" any call that has:
- `cd`/`env -C` combined with pipes or `||` chains,
- several heredoc writes chained with a `git` command,
- a shell variable in argument position (`sed -n 1,5p $W/file`),
- or path arguments that contain `git` as a substring (for example `github_*.py` filenames).

Use the Read tool for such files, or give the path relative to the current directory. For many file writes, put them in one script and run that.

The guard also refuses `git -C <sibling worktree>`. Worktrees share one object DB, so read a sibling's commit with plain `git show <sha>[:path]` from your own worktree.
