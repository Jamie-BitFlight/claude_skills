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

This line reaches your immediate caller only, in the response it reads the moment your launch
returns. It is not a record: a reader arriving later, in another session, sees nothing of it unless
someone wrote it down. When your dispatch names a ledger address and attempt, `<work_ledger/>`
below says what to write down and how.

There is no third token here. A mixed outcome — some of it done, some of it not — is not something
this line reports, because the ledger already holds it one row per task and `finish --result` has
no partial value. Report `STATUS: DONE` and let the rows say how each turned out. The
`agent-orchestration` plugin's similarly named `delegate/references/sub-agent-contract.md` does
pin a third token, `PARTIAL`; that contract governs delegations with no ledger behind them, where
the response is the only channel there is. It does not apply to a dispatch that named an address.

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

When your dispatch names a task address `P/T` together with an attempt number, that task has a row
in the work ledger, and the ledger is where your state belongs. The CLI is how you reach it — the
`sam_task` and `sam_plan` MCP tools answer from the content store and carry none of these commands:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan <command> …
```

Read your task first, with both facts on the command. Act on any `Orchestrator Response` the output
carries before anything else — it is what a previous attempt was sent back for:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan read --address P/T --attempt N
```

Append what you produced as task sections, each carrying the attempt, and close the attempt once as
your last ledger command:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan update --plan-address P --task-id T --attempt N \
  --append-section "Completion Report" --section-content "<TASK:, BRANCH:, FILES_CHANGED:, COMMITS:, NOTES:>"
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan update --plan-address P --task-id T --attempt N \
  --append-section "Verification Results" --section-content "<one line per verification step, or none>"
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan finish --address P/T --attempt N \
  --result complete|failed|blocked|needs-input --note "<what stopped you, what you need, or your question>"
```

`finish --result complete` answers `report-missing` until this attempt carries both a `Completion
Report` section and a `Verification Results` section, so append both before you finish. The other
results close the attempt without them. Sections are recorded against the attempt that appended
them, so an attempt following a send-back appends its own.

Send the `STATUS:` line and `finish` both. They carry different things and neither substitutes for
the other: the `STATUS:` line is what your caller reads out of your response, and the orchestrator
records it against the attempt as its return text; `finish --result` is the durable outcome every
later reader queries, including an orchestrator that resumes in a new session and never saw your
response. `STATUS: DONE` is what you send once `finish` was recorded, whatever its `--result`.

The full runner sequence — renewing the lease before work that may outrun it, recording a
divergence, and what each refusal code asks of you — is in
[the runner contract](../../docs/work-ledger/runner-contract.md).

A dispatch naming no address and no attempt has no ledger row to write, and this section asks
nothing of it.

</work_ledger>

<reporting>

Report every command you ran with its outcome. Keep changes confined to the task you were given.

</reporting>
