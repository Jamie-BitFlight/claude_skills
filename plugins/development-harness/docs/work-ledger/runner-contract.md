# The runner contract

Every command below is `sam plan <command>`:
`uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan <command> …`, or the `sam_task` MCP
action of the same name.

## Your two facts

Your prompt names an address `P/T` and an attempt number `N`. Pass both on every command you
run. Yours are `read`, `update`, `renew` and `finish`, each on your own task; `dispatch`,
`settle`, `accept`, `reclaim` and `state` belong to the orchestrator.

## Sequence

1. `read --address P/T --attempt N`, as your first command. Act on any `Orchestrator Response`
   in the output before anything else. When a previous attempt's `Completion Report` carries a
   `BRANCH:` line, switch to that branch first.
2. Work the task. Each command prints `renew_by`; before starting anything that may run past it,
   such as a test suite or a build, run `renew --address P/T --attempt N`.
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
