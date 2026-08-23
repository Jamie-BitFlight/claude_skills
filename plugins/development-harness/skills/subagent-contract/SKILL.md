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

Deliver each result in the form your dispatch named, including a body it asks you to return for it
to store. Where it names no form: deliverables the repository keeps — source, tests, documentation
— go in repository files; every other document is an artifact, registered with `artifact_register`
carrying its content, since an id registered without content persists nothing; plans and task state
go through the SAM plan and task operations. Hand the next step a plan, task, or artifact id; a
filesystem path resolves only in the worktree that wrote it, so that step reads it back empty
instead of failing.

Report every command you ran with its outcome. Keep changes minimal and reversible, and confined
to the task you were given.
