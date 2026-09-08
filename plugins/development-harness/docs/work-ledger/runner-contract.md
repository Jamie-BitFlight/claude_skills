# The runner contract

Every command below is `sam plan <command>`:
`uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan <command> …`. The CLI is the only path to
the ledger — there is no MCP action of the same name. `sam_schema/server.py`'s `_get_backend`
returns `ContentTaskProvider(provider)` unconditionally, with no branch that reaches
`dh_core.ledger`, so every `sam_task`/`sam_plan` MCP call resolves to the content store. The two
tools' complete action sets are the discriminated unions in `sam_schema/core/action_models.py`
(`TaskActionConfig`: `read | claim | state | update`; `PlanActionConfig`: `read | create | list |
status | ready | update | append_task | finalize`), matched exhaustively in `server.py`'s
`match config.action` arms; grepped both for `dispatch`, `finish`, `settle`, `renew`, `accept`,
`reclaim` and `import` and found none of these ledger-only commands in either union. Until an
MCP surface for the ledger exists, run every command below through the CLI.

## Your two facts

Your prompt names an address `P/T` and an attempt number `N`. Pass both on every command you
run. Yours are `read`, `update`, `renew` and `finish`, each on your own task; `dispatch`,
`settle`, `accept`, `reclaim` and `state` belong to the orchestrator.

## Sequence

1. `read --address P/T --attempt N`, as your first command. Act on any `Orchestrator Response`
   in the output before anything else. When a previous attempt's `Completion Report` carries a
   `BRANCH:` line, switch to that branch first.
2. Work the task. Only `renew` returns a `renew_by` field (`dh_core/ledger/transitions.py`'s
   `renew()` is the sole transition that sets it on its result). `read` and `update` also renew
   the lease when given `--attempt N`, but report the same deadline under the task row's `expires`
   field rather than as `renew_by`. Before starting anything that may run past that deadline, such
   as a test suite or a build, run `renew --address P/T --attempt N`, whose output names it
   directly.
3. Record a divergence when you find one:
   `update --plan-address P --task-id T --attempt N --append-section "Divergence Notes"
   --section-content "<the note>"`.
4. Append the report, both sections, each with `--attempt N`:
   - `Completion Report`, with the lines `TASK:`, `BRANCH:`, `FILES_CHANGED:`, `COMMITS:` and
     `NOTES:`.
   - `Verification Results`, one line per entry of the task's `verification_steps`, each
     `<step> — passed|failed: <evidence>`, or the single word `none` when the task has none.
5. Finish once, as your last ledger command:
   `finish --address P/T --attempt N --result complete|failed|blocked|needs-input`, with `--note`
   carrying what stopped you for `failed`, what you need for `blocked`, and the question for
   `needs-input`.
6. Return the `STATUS:` line of `/dh:subagent-contract` as your first line: `STATUS: DONE` once
   `finish` was recorded, whatever its `--result`.

## Codes a command may print to you

| code | what to do |
|---|---|
| `report-missing` | append the section it names with `--attempt N`, then run `finish` again |
| `attempt-required` | add `--attempt N` to the `update` |
| `stale-attempt` | return `STATUS: BLOCKED` with `stale-attempt` as the reason, as your last action |
| `attempt-closed` | return `STATUS: DONE` when you had already run `finish`, else `STATUS: BLOCKED` with `attempt-closed` |
| `network-filesystem` | return `STATUS: BLOCKED` with `network-filesystem` |
