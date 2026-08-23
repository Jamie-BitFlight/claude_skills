---
name: subagent-contract
description: Where a dispatched step puts its output, and how it signals state upstream.
user-invocable: false
---

# Subagent Contract

Report state as `STATUS: DONE` or `STATUS: BLOCKED`.

DONE carries what was accomplished, the deliverables in the form your dispatch named, and any risk
you observed.

BLOCKED carries what is blocking you, the specific input you need, and what would unblock it.
Return BLOCKED when a required input is missing, rather than inferring it.

Deliverables the repository keeps — source, tests, documentation — go in repository files. Every
other document is an artifact: register it with `artifact_register` carrying its content, since an
id registered without content persists nothing. Plans and task state go through the SAM plan and
task operations. Hand the next step a plan, task, or artifact id; a filesystem path resolves only
in the worktree that wrote it, so the next step reads it back empty instead of failing.

Report every command you ran with its outcome. Keep changes minimal and reversible, and confined
to the task you were given.
