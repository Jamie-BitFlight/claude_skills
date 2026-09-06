# The runner contract

What an agent does when it is given a task address and an attempt number, whichever skill or
profile it runs under. The commands and the codes they print are defined once, in
[ledger_spec.py](../../dh_core/ledger_spec.py); this file says when to run them. The
orchestrator's side is [work-loop.md](./work-loop.md).

Every command is `sam plan <command>`:
`uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan <command> …`, or the `sam_task` MCP
action of the same name.

## Your two facts

Your prompt names an address `P/T` and an attempt number `N`. Pass both on every `read`,
`update`, `renew` and `finish` you run.

## Sequence

1. `read --address P/T --attempt N`, as your first command. When the orchestrator sent this
   task back, an `Orchestrator Response` heads the output: act on it before anything else. The
   previous attempt's `Completion Report`, shown under its `(attempt N)` heading, carries a
   `BRANCH:` line; switch to that branch first when one is there.
2. Work the task. Each command you run prints `renew_by`. Before starting anything that may run
   past it, such as a test suite or a build, run `renew --address P/T --attempt N`.
3. Record a divergence when you find one:
   `update --plan-address P --task-id T --attempt N --append-section "Divergence Notes"
   --section-content "<the note>"`.
4. Append the report, both sections, each with `--attempt N`:
   - `Completion Report`, with the lines `TASK:`, `BRANCH:`, `FILES_CHANGED:`, `COMMITS:` and
     `NOTES:`.
   - `Verification Results`, one line per entry of the task's `verification_steps`, each
     `<step> — passed|failed: <evidence>`, or the single word `none` when the task has none.
5. Finish, as your last ledger command:

   ```text
   sam plan finish --address P/T --attempt N --result complete
   sam plan finish --address P/T --attempt N --result failed      --note "<what stopped you>"
   sam plan finish --address P/T --attempt N --result blocked     --note "<what you need>"
   sam plan finish --address P/T --attempt N --result needs-input --note "<the question>"
   ```

6. Return the `STATUS:` line of `/dh:subagent-contract` as your first line: `STATUS: DONE` once
   `finish` was recorded, whatever its `--result`. The orchestrator reads the result from the
   ledger.

## Codes a command may print to you

| code | what to do |
|---|---|
| `report-missing` | append the section it names with `--attempt N`, then run `finish` again |
| `attempt-required` | add `--attempt N` to the `update` |
| `stale-attempt` | a newer attempt owns this task; return `STATUS: BLOCKED` with `stale-attempt` as the reason, as your last action |
| `attempt-closed` | your attempt is finished or was settled; return `STATUS: DONE` when you had already run `finish`, else `STATUS: BLOCKED` with `attempt-closed` |
| `network-filesystem` | the ledger cannot open here; return `STATUS: BLOCKED` with `network-filesystem` |

## Your commands

`read`, `update`, `renew` and `finish`, each with `--attempt N`, each on your own task.
`dispatch`, `settle`, `accept`, `reclaim` and `state` belong to the orchestrator.
