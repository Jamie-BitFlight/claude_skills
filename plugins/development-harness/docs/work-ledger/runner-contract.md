# The runner contract

Every command below is `sam plan <command>`:
`uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan <command> …`. Once `plan import` puts a plan
on the ledger, overlapping `sam_plan` and `sam_task` MCP actions route to that ledger through
`sam_schema/server_ledger_routing.py`; before import they route to the content store. Runner lease
and completion commands (`renew` and `finish`) are CLI-only, so run the sequence below through the
CLI. MCP remains available for its declared read, update, and state actions on an imported plan.

## Your two facts

Your prompt names an address `P/T` and an attempt number `N`. Pass both on every command you
run. Yours are `read`, `update`, `renew` and `finish`, each on your own task; `dispatch`,
`settle`, `accept`, `reclaim` and `state` belong to the orchestrator.

## Sequence

Read this sequence before your first ledger command. For your final response, load
`dh:subagent-contract`; it owns the response destination and `STATUS:` semantics.

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
4. Select the outcome that matches this attempt. Every `finish` requires an explicit `--result`:

   | result | when | what `--note` carries |
   |---|---|---|
   | `complete` | acceptance criteria met and verification steps run | what was done |
   | `failed` | the work cannot be finished as written | what stopped you |
   | `blocked` | something outside the task must change first | what must change |
   | `needs-input` | a decision is needed before continuing | the question |

   For `complete`, append both report sections before finishing, each with `--attempt N`:

   - `Completion Report`, with the lines `TASK:`, `BRANCH:`, `FILES_CHANGED:`, `COMMITS:` and
     `NOTES:`.
   - `Verification Results`, one line per entry of the task's `verification_steps`, each
     `<step> — passed|failed: <evidence>`, or the single word `none` when the task has none.

   Append them through `update --plan-address P --task-id T --attempt N --append-section
   "<section name>" --section-content "<body>"`. Sections belong to the attempt that appended
   them: an attempt following a send-back writes its own. `failed`, `blocked` and `needs-input`
   can close without either section; record the outcome and absent deliverables honestly.
5. Finish once, as your last ledger command. For success:
   `finish --address P/T --attempt N --result=complete --note "<what was done>"`.
   For the other outcomes, use the selected explicit value:
   `finish --address P/T --attempt N --result failed|blocked|needs-input --note "<the reason>"`.
   Keep the success option and its value in one shell argument, as shown.
6. Return the response required by `dh:subagent-contract` after the closure is recorded, or
   after a refusal prevents closure.

## Codes a command may print to you

Correct flags that repair your own call, such as `--attempt`, then retry. Overrides such as
`--force`, `--more-attempts` and `--replace` belong to the orchestrator; report the refusal and
stop rather than taking another runner's leased attempt.

| code | what to do |
|---|---|
| `report-missing` | append the section it names with `--attempt N`, then run `finish` again |
| `attempt-required` | add `--attempt N` to the `update` |
| `stale-attempt` | return `STATUS: BLOCKED` with `stale-attempt` as the reason, as your last action; do not re-read and join the superseding attempt |
| `attempt-closed` | return `STATUS: DONE` only when your `finish` was already recorded, else `STATUS: BLOCKED` with `attempt-closed` |
| `network-filesystem` | return `STATUS: BLOCKED` with `network-filesystem` |
| `archived` | stop and report that the plan is closed |
