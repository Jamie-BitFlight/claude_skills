# The work loop

How a task goes from ready to accepted, and what the orchestrator runs at each observation.
The commands, their preconditions, their effects and the codes they print are defined once, in
[ledger_spec.py](../../dh_core/ledger_spec.py); name them, never restate them. The runner's side
is [runner-contract.md](./runner-contract.md).

Every command below is `sam plan <command>`:
`uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan <command> …`, or the `sam_plan` or
`sam_task` MCP action of the same name. Every task command takes `--address P/T`.

## Roles

- **Orchestrator**: the skill driving a plan. It runs `ready`, `dispatch`, `settle`, `accept`,
  `reclaim`, `state` and `export`, and judges between them.
- **Launcher**: how the orchestrator starts a runner. Three shapes: the harness's sub-agent
  call; a script that starts a harness in a directory you choose; a child harness process
  (`claude -p …`) you start yourself. Give the runner its own git worktree where the harness
  offers one, and pass that directory as `dispatch --worktree`.
- **Runner**: whatever the launcher started. It holds one address and one attempt number.
- **Judge**: the orchestrator step that reads a task's row and decides.

## One task, one loop

1. `ready --plan-address P` lists the tasks to start. For each:
2. `dispatch --address P/T [--ttl S] [--worktree DIR]` prints the attempt number. `leased` and
   `not-ready` mean the task is not yours to start now; go to the next one. Any other code
   stops the wave and goes to the user.
3. Launch the runner with a prompt naming the address, the attempt number, and the specialist
   profile the task's `agent` field names when it names one. Keep a table of launch handle to
   address and attempt in your working notes; rows J4 to J7 read it.
4. When the launch ends, `settle --address P/T --attempt N --return-text "<what came back>"`.
5. Judge, per the table below.
6. Repeat from step 1 until `status --plan-address P` reports plan progress `done`, or a judge
   row puts the task to the user.

`--reason` on `accept`, `reclaim` and `state` is free text for the next reader. The codes the
ledger prints are the ones this table names in its `observed` column.

## The judge

Read before deciding: `read --address P/T` gives the current attempt's `Completion Report` and
`Verification Results`, with earlier attempts under their `(attempt N)` headings. Compare them
against the task's `acceptance_criteria` and `verification_steps`, and against the diff of the
files the report's `FILES_CHANGED` lists since `plans.base_sha`.

| id | observed | command |
|---|---|---|
| J1 | `complete`, every acceptance criterion met and every verification step passed | `accept --address P/T --reason "<why>"` |
| J2 | `complete`, a criterion unmet or a verification step failed | `reclaim --address P/T --reason judge --response "<what to change and why>"` |
| J3 | `returned`, both report sections present | judge as J1 or J2 |
| J4 | `returned`, a report section absent | `reclaim --address P/T --reason no-report --response "append Completion Report and Verification Results with --attempt, then finish"` |
| J5 | `in-progress`, launch of this session still running | wait |
| J6 | `in-progress`, launch of this session has ended | `settle` (step 4), then judge again |
| J7 | `in-progress`, no launch of this session, `stale` false | wait until `stale` |
| J8 | `in-progress`, no launch of this session, `stale` true | `reclaim --address P/T --reason stale` |
| J9 | `in-progress`, no attempt open, never settled (an imported row) | `reclaim --address P/T --reason imported` |
| J10 | `failed` | `reclaim --address P/T --reason failed --response "<the note, and what to do differently>"` |
| J11 | `blocked`, result `needs-input` | put the note to the user; on the answer, `reclaim --address P/T --reason answered --response "<the answer>"` |
| J12 | `blocked`, result `blocked` | when the note names a ledger row or a repository file you can change, change it and `reclaim --address P/T --reason unblocked --response "<what changed>"`; otherwise put the note to the user, as J11 |
| J13 | `skipped` with reason `cascade:T{n}` | judge T{n}; this row follows it |
| J14 | milestone plan, a `quality_gates` command failed on a scratch merge of the item's branch | `reclaim --address P/T --reason gates --response "<gate output>"` |
| J15 | `reclaim` printed `attempts-exhausted` | put the attempt history to the user; on a go-ahead, `reclaim --address P/T --reason more --more-attempts --response "<the guidance>"`; on a stop, `state --address P/T --new-status skipped --reason user` |
| J16 | `reclaim` printed `task-accepted` or `dependents-started` | the send-back undoes accepted work; add `--force` for a TN send-back (J17) or a user instruction, and say which in `--reason` |
| J17 | TN verdict FAIL | `reclaim --force` on the TN task and on every task whose report's `FILES_CHANGED` overlaps the files the failing criterion names, each with the regression as `--response` |
| J18 | `accept` printed `already-accepted`, `reclaim` printed `already-open`, `export` printed `unchanged` | a no-op; proceed |
| J19 | `accept` printed `not-complete` | the task has no finished attempt; go to the row its status names |
| J20 | any command printed `archived` | the plan is closed; stop and tell the user |

A milestone item merges only after J14 passes and J1 accepts it: run the plan's `quality_gates`
on a scratch merge of the item's branch in a throwaway worktree, then accept, then fast-forward
`integration_branch`.

## Waves

A wave is every task `ready` lists at one moment. Two tasks of one `conflict_group` can both be
listed; the second `dispatch` then prints `not-ready`, which step 2 skips. Accept each task the
moment J1 says so, so its dependents reach the next `ready`.

## Export

Run `export --plan-address P` at each wave end and at completion.
