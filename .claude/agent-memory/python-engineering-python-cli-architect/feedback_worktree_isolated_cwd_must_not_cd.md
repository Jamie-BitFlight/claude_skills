---
name: feedback-worktree-isolated-cwd-must-not-cd
description: In a worktree-isolated agent session, cd-ing to the shared checkout path lets non-git mutating commands (uv add/remove, pip, etc.) silently pollute the shared tree — only git commands are guarded against this
metadata:
  type: feedback
---

The default cwd for a worktree-isolated agent is already the worktree
(`.claude/worktrees/agent-*`). Running `cd /home/.../claude_skills && <command>` inside a single
Bash call moves that command's execution into the **shared main checkout** for the duration of
that call.

A guard exists that blocks `git` commands from targeting the shared checkout (via `cd` or `git -C`)
with an explicit "isolated in the worktree" refusal message. **No equivalent guard exists for
non-git mutating commands** — `uv add`, `uv remove`, `pip install`, file-writing shell redirects,
etc. all execute silently against whatever `cd` target was given, including the shared checkout.

**What happened**: `cd /home/.../claude_skills && uv add --script research/knowledge-explorer.py
click` and a companion `uv add --dev click` both ran, unblocked, against the shared checkout —
confirmed by re-reading the shared checkout's `research/knowledge-explorer.py` and `pyproject.toml`
afterward and finding `click` present in both. Caught only because a subsequent `Edit` call on the
same (wrong) path was refused by the worktree-isolation guard, which prompted a check of the
Bash-mutated files.

**Fix applied**: surgical revert via the exact inverse commands (`uv remove --script ... click`,
`uv remove --dev click`) run against the shared checkout — not `git checkout`/`git reset` (which
would have been blocked anyway, and which also risks discarding other legitimate uncommitted work
in that shared tree per [[project_ruff_fix_true_autofix.md]]-adjacent working-tree-safety rules).
Then redid both `uv add` calls correctly scoped to the worktree path.

**How to apply**: in a worktree-isolated session, never `cd` to an absolute path outside the
worktree for ANY command, not just git. Verify the default `pwd` at the start of a session and use
that as the working root for every subsequent command (or plain relative paths, which resolve
against whatever the actual — reset — cwd is per-call). If a command must reference the shared
checkout path for a legitimate read-only reason, use an absolute path without `cd` and confirm the
command has no side effects before running it.
