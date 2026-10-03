---
name: subagent-contract
description: Where a dispatched step puts its output, and how it signals state upstream.
user-invocable: false
---

Load `dh:dh-cli-usage` before using `<sam_cli/>` or `<dh_scripts/>`.

# Subagent Contract

<status>

Begin your response with `STATUS: DONE` or `STATUS: BLOCKED` as its own first line. Consumers
branch on that line in that position.

When your dispatch names a ledger address and attempt, send DONE once `finish` was recorded,
whatever its durable result. This reports successful recording of the attempt's end, including
`failed`, `blocked` or `needs-input`; it does not assert task success. Send BLOCKED when closure
could not be recorded, naming the refusal or missing input and what would unblock it. Follow the
runner contract's refusal handling when the attempt is stale or already closed.

When your dispatch names no ledger address and attempt, send DONE once the acceptance criteria
are met as written and every stated constraint is respected. Send BLOCKED when the required
scope cannot be completed, including unmet criteria, failed verification or a missing required
input. Carry the completed work, the unmet scope, the observed evidence and the input or action
needed to proceed; do not infer a missing input.

DONE carries what was accomplished, the deliverables in the form your dispatch named, and any
observed risk.

This line reaches your immediate caller only, in the response it reads the moment your launch
returns. It is not a record: a reader arriving later, in another session, sees nothing of it unless
someone wrote it down. When your dispatch names a ledger address and attempt, `<work_ledger/>`
below says what to write down and how.

There is no third token here. With a ledger, a mixed outcome is recorded one row per task;
`finish --result` has no partial value. Send DONE once all the attempts you were responsible for
closing were recorded; send BLOCKED if any could not be closed, and identify them. The
`agent-orchestration` plugin's similarly named `delegate/references/sub-agent-contract.md` does
pin a third token, `PARTIAL`, for dispatches invoking that separate delegate contract. It does
not govern a dispatch naming a ledger address and attempt: that dispatch follows the ledger
status rules above, even if its prompt opens with `Your ROLE_TYPE is sub-agent.` Absence of a ledger
does not switch a DH dispatch to the delegate contract; DH dispatches without a ledger follow the
two-token rules above.

</status>

<dispatch_input>

If your dispatch concerns a specific backlog item and your `tools:` list carries
`mcp__plugin_dh_backlog`, fetch that item yourself — `backlog_view(selector=<item_ref>, ...)` —
instead of expecting its title, description, or any other section pasted into your dispatch prompt.
Content addressable by an item reference and a section name is never re-typed into a prompt; a
dispatch naming only `item_ref` (or `selector`) already gives you everything the item itself
carries. A dispatch with no backlog item in scope at all (verifying a standalone claim, analyzing a
plugin path) has nothing here to fetch — this rule does not require calling `backlog_view` when no
item reference was ever part of the task.

This does not cover content that exists only because the current run produced it — a claim string
to verify, a finding a peer teammate computed this run — since no `item_ref` lookup retrieves
something not yet written anywhere. A dispatch carrying that kind of content is not a violation of
this rule.

</dispatch_input>

<result_destination>

Put your result where your own agent file says. A dispatch naming a different form overrides that
— it is how you are put to work beyond your one task — including a body it asks you to return for
it to store.

Where neither names one: deliverables the repository keeps — source, tests, documentation — go in
repository files; every other document is an artifact, registered with `artifact_register` carrying
its content, since an id registered without content persists nothing.

Task state divides by store. The status of the task you were dispatched on, the sections you append
for this attempt, and the outcome you close it with go to the work ledger through the CLI commands
`<work_ledger/>` names. Plan and task content authored before any dispatch — a plan's tasks, their
acceptance criteria, the plan-level context manifest — goes through the SAM plan and task
operations, which is the store that holds it.

Hand the next step a plan, task, or artifact id; a filesystem path resolves only in the worktree
that wrote it, so that step reads it back empty instead of failing.

</result_destination>

<work_ledger>

When your dispatch names a task address `P/T` together with an attempt number, read
[the runner contract](../../docs/work-ledger/runner-contract.md) in full before your first ledger
command. It owns the task read, attempt identity, lease renewal, report prerequisites, explicit
outcome selection, closure and refusal handling. Use its CLI sequence; runner lease and finish
operations are CLI-only. Imported-plan MCP read/update routing is described there too.

Send the `STATUS:` line and `finish` both. They carry different things and neither substitutes for
the other: the `STATUS:` line is what your caller reads out of your response, and the orchestrator
records it against the attempt as its return text; `finish --result` is the durable outcome every
later reader queries, including an orchestrator that resumes in a new session and never saw your
response. The status rules above say which first line to send.

A dispatch naming no address and no attempt has no ledger row to write, and this section asks
nothing of it.

</work_ledger>

<reporting>

Report every command you ran with its outcome. Keep changes confined to the task you were given.

</reporting>
