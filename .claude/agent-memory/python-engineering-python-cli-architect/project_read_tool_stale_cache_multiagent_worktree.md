---
name: read-tool-stale-cache-multiagent-worktree
description: Read tool returned a stale (pre-session, ~130-line) version of a file that had grown to 274 lines on disk from other agents' already-merged commits; python3/Bash reads were current
metadata:
  type: project
---

In a multi-agent swarm session sharing one worktree (backlog_core/#2970 session, 2026-08-18), the
`Read` tool returned a version of `plugins/development-harness/backlog_core/rendering.py` that was
stale relative to disk — 130 lines, missing `normalize_unknown_sections`/`heading_to_unknown_key`/
`SECTION_HEADING_ALIAS`-derived content that sibling agents (fix-2956/fix-2964/fix-2971/fix-2979)
had already committed to the same branch. `wc -l`, `python3 -c "open(...).readlines()"`, and a
second/third `Read` call on the same path all still returned the stale 130-line content on the
first several attempts; only reading the file's content via `python3 -c "for i, line in
enumerate(f, 1): print(...)"` (full manual iteration, not `Read`) surfaced the true 274-line
current state. `git status` was clean and `git log` showed the sibling commits already present —
this was not a live concurrent-write race, it was the `Read` tool's own cache holding a snapshot
from earlier in the session, before the other agents' commits landed on this branch.

**Why:** Fast-moving multi-agent sessions where several teammates commit to the same shared branch
mid-session can leave the orchestrating/verifying agent's `Read` tool cache behind actual disk
state, with no visible staleness indicator (no truncation notice, no warning) — this is a Read-tool
gotcha, not a git or worktree-sharing issue (see also [[project_worktree_shared_object_db_no_dash_c_needed]]).

**How to apply:** Before trusting a `Read` result to be current in a session where other named
agents (per the `SubagentStart` teammate list) are or were working on the same shared files, cross-
check with a fresh `Bash`/`python3` read (`wc -l`, `git show HEAD:path`, or a manual line-iteration
print) before relying on line numbers or content from `Read` for a subsequent `Edit`. If `wc -l`
and `Read`'s line count disagree, trust `wc -l`/a fresh interpreter read, not `Read`.
