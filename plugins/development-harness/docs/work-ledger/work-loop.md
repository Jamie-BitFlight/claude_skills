# The work loop

The procedure: which command the orchestrator runs, with which flags, and how to read what each
one prints. What the loop *is* — its invariants, what reaches the orchestrator as a return and what
it can only learn by asking, and how loops nest — is the orchestration loop section of
[ARCHITECTURE.md](../../ARCHITECTURE.md), and this page assumes it rather than restating it.

The commands, their preconditions, their effects and the codes they print are defined in
[ledger_spec.py](../../dh_core/ledger_spec.py). The runner's side is
[runner-contract.md](./runner-contract.md).

Every command below is `sam plan <command>`:
`uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan <command> …`. Once `plan import` puts a plan
on the ledger, overlapping `sam_plan` and `sam_task` MCP actions route to that ledger through
`sam_schema/server_ledger_routing.py`; before import they route to the content store. The lifecycle
commands used by this loop (`dispatch`, `settle`, `accept`, and `reclaim`) are CLI-only, so run the
procedure below through the CLI. MCP remains available for its declared read, status, ready,
update, state, append, and finalize actions on an imported plan.

## Each turn

1. `status --plan-address P` — run this on every turn, whatever prompted it. It returns every task
   row with its derived columns (`ready`, `expired`, `stale`, `returned`, `renew_by`) and the
   plan's `progress`. Nothing announces a lease running out, a conflict group freeing or an attempt
   going stale; this query is the only thing that reports them. `ready --plan-address P` narrows to
   the tasks that may be started now. For each:
2. `dispatch --address P/T [--ttl S] [--worktree DIR]` prints the attempt number. Give the runner
   its own git worktree where the harness offers one, and pass that directory as `--worktree`. On
   `leased` or `not-ready`, go to the next task. Any other code stops this plan's loop and goes to
   the user.
3. Before launching a runner, read `dh:subagent-contract` for response/transport semantics and
   pass it [the runner contract](./runner-contract.md) to read before its first ledger command.
   Launch the runner with a prompt naming the address, the attempt number, and the specialist
   profile the task's `agent` field names when it names one. Launch it whichever way this harness
   allows: its own sub-agent call, a script that starts one in a directory you choose, or a child
   harness process such as `claude -p`. Keep a table of launch handle to address and attempt in
   your working notes.
4. When the launch ends, `settle --address P/T --attempt N --return-text "<what came back>"`.
5. Judge, per the table below.
6. Repeat from step 1 on the next return, without waiting for the tasks you started together to
   return together, until `status --plan-address P` reports plan progress `done` or a judge row
   puts the task to the user.

## The judge

Read before deciding: `read --address P/T` gives the current attempt's `Completion Report` and
`Verification Results`. For a task with `attempts` equal to zero, a direct `complete` instead
requires a current-generation `Direct Completion Record` tagged at attempt zero; it carries `TASK:`,
`FILES_CHANGED:`, `COMMITS:`, `REUSE DECISION:`, `VERIFICATION:` and `NOTES:`. A reclaim or plan
replacement invalidates earlier direct evidence for completion and refinement while retaining its
append-only audit history. Compare the applicable durable evidence against the task's
`acceptance_criteria` and `verification_steps`, and against the diff of the record's
`FILES_CHANGED` list since `plans.base_sha`. A direct record is not a runner report and never
substitutes for one after an attempt exists.

An export carries only current direct evidence. Rejected direct records remain in the source ledger's
audit history, but an export/import round trip must not restore them as fresh completion or divergence
evidence. Valid current records remain usable after that same round trip.

Creating a plan starts a new evidence generation even when its ID was used by an older plan.
`Direct Completion Record` and `Direct Divergence Notes` are both reserved zero-attempt carriers;
appending either after a runner attempt is refused with `direct-evidence-attempt` rather than storing
proof that cannot be read back as current or used for completion.

| id | observed | command |
|---|---|---|
| J1 | `complete`, its applicable durable evidence is present, every acceptance criterion met and every verification step passed | `accept --address P/T --note "<why>"` |
| J2 | `complete`, applicable evidence absent, a criterion unmet, or a verification step failed | `reclaim --address P/T --reason judge --response "<what to change and why>"` |
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
| J15 | `reclaim` printed a line starting `attempts-exhausted` | put the attempt history to the user; on a go-ahead, `reclaim --address P/T --reason more --more-attempts --response "<the guidance>"`; on a stop, `state --address P/T --new-status skipped --reason user` |
| J16 | `reclaim` printed a line starting `task-accepted` or `dependents-started` | add `--force` for a TN send-back (J17) or a user instruction, and say which in `--reason` |
| J17 | TN verdict FAIL | `reclaim --force` on the TN task and on every task whose report's `FILES_CHANGED` overlaps the files the failing criterion names, each with the regression as `--response` |
| J18 | `accept`, `reclaim` or `export` printed a line starting `already-accepted`, `already-open` or `unchanged` | proceed |
| J19 | `accept` printed a line starting `not-complete` | go to the row its status names |
| J20 | any command printed a line starting `archived` | the plan is closed; stop and tell the user |

A milestone item merges after J14 passes: run the plan's `quality_gates` on a scratch merge of the
item's branch in a throwaway worktree, then accept, then fast-forward `integration_branch`.

## Waves

A wave is a set of work loops running at once, not a set of tasks running inside one. Each of its
members is a separate session in its own worktree, running its own plan under its own manager —
`skills/kage-bunshin` launches those sessions and `skills/work-milestone` launches one per
milestone item. That level is the outer one in ARCHITECTURE.md's orchestration loop section.

Nothing on this page is a wave. This page is one loop, and what `ready` lists at a given moment is
that loop's readiness answer, not a batch: the answer changes as each return lands, so re-ask it
rather than working through the set you last received. Accept each task the moment J1 says so.

## Export

Run `export --plan-address P` after each judgement and at completion; it prints a line starting `unchanged` when
there is nothing new to write.
