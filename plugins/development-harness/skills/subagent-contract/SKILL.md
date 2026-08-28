---
name: subagent-contract
description: Where a dispatched step puts its output, and how it signals state upstream.
user-invocable: false
---

# Subagent Contract

<status>

Begin your response with `STATUS: DONE` or `STATUS: BLOCKED` as its own first line. Consumers
branch on that line in that position.

DONE carries what was accomplished, the deliverables in the form your dispatch named, and any risk
you observed. Send it once the acceptance criteria are met as written and every stated constraint
is respected.

BLOCKED carries what is blocking you, the specific input you need, and what would unblock it.
Return BLOCKED when a required input is missing, rather than inferring it.

</status>

<result_destination>

Put your result where your own agent file says. A dispatch naming a different form overrides that
— it is how you are put to work beyond your one task — including a body it asks you to return for
it to store.

Where neither names one: deliverables the repository keeps — source, tests, documentation — go in
repository files; every other document is an artifact, registered with `artifact_register` carrying
its content, since an id registered without content persists nothing; plans and task state go
through the SAM plan and task operations.

Hand the next step a plan, task, or artifact id; a filesystem path resolves only in the worktree
that wrote it, so that step reads it back empty instead of failing.

</result_destination>

<reporting>

Report every command you ran with its outcome. Keep changes confined to the task you were given.

</reporting>
