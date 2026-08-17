---
name: project-dh-multi-agent-worktree-contention
description: this machine runs many concurrent claude_skills agent worktrees with full pytest -n auto suites — isolate timing/regression verification against a throwaway baseline worktree, not git stash
metadata:
  type: project
---

`ps aux` on this machine routinely shows a dozen-plus `.claude/worktrees/agent-*` checkouts each
running their own `pytest -n auto` (xdist, full-core) suite concurrently (observed 2026-08-16/17
while working PR #2946). A single subagent's own commands can appear to hang or its subprocess
tests can time out purely from CPU starvation, not from a real regression.

**Why this matters:** `git stash` on the working tree is blocked by the auto-mode permission
classifier in this environment (even inside an isolated worktree) — do not rely on it for
before/after comparisons. Since a fresh agent worktree branch has no commits of its own yet,
`HEAD` at the start of a task already **is** the pre-change baseline; `git worktree add <scratch
path> HEAD` gives a fully independent checkout to run the "before" measurement in, with zero risk
of disturbing the in-progress working tree. Clean it up with
`git worktree remove <path> --force` when done.

**How to apply:** before concluding "my change caused this test failure/timeout," reproduce the
same test against a `git worktree add <path> HEAD` baseline under the *same* ambient contention.
If the baseline also fails/times out, the cause is environmental, not the change under test — this
is the falsification step, not an excuse to skip it. In PR #2946 this correctly ruled OUT
contention as the sole cause for one round of `test_network_guard.py` failures (baseline passed
cleanly) and pointed at a real regression (a module-level import added during lint cleanup) — see
[[project-dh-conftest-lazy-import-cost]].

Practical tip: `uv run <heavy pytest command>` inside a brand-new worktree first has to resolve/
build `.venv`, so the very first background run there can look stalled — check with
`ps -o pid,etime,time,rss -p <pid>` (low `TIME` relative to `ELAPSED` = CPU-starved by contention,
not stuck) before assuming failure.
