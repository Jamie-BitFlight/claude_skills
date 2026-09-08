---
name: implement-feature
description: Use when the plan_ref returned by add-new-feature is provided. Executes the SAM implementation loop — opens an attempt per ready task, dispatches each to a specialist agent in parallel, settles and judges what comes back, manages bookend tasks (T0 baseline capture and TN verification), and tracks concerns and contract violations per task. Drives task state through the work ledger via the SAM CLI.
argument-hint: "<plan_ref>"
user-invocable: true
---

# Implement Feature (SAM Workflow Execution)

This workflow continues from `add-new-feature`. It executes tasks from the selected provider until complete or blocked.

<plan_ref>$ARGUMENTS</plan_ref>

<sam_cli>
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py"
</sam_cli>

<mcp_server_scripts>
SAM server: uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/run_sam_server.py"
Backlog server: uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/run_backlog_server.py" --project-dir .
</mcp_server_scripts>

---

**Where task state lives**: every command that moves a task — `ready`, `dispatch`, `settle`,
`read`, `accept`, `reclaim`, `state`, `status` — runs through the `<sam_cli/>` command above,
against the work ledger. The `sam_plan` and `sam_task` MCP tools answer from the content store,
which holds the plan's authored content and none of the attempt, lease, or outcome state this loop
turns on, so this workflow reaches task state through the CLI.

**MCP server availability**: This skill uses `mcp__plugin_dh_backlog__*` tools for backlog items
and artifacts. The server initializes in ~1–2 seconds after a session restart, and Claude Code
handles connection waiting automatically. If a tool is unavailable, see the troubleshooting steps at ${CLAUDE_PLUGIN_ROOT}/docs/mcp-connection-check.md — its commands use the `<sam_cli/>` and `<mcp_server_scripts/>` values above.

## Resolve Plan

Treat the value from the `plan_ref` key as an opaque reference. Pass it unchanged to every SAM operation and delegation prompt.

Confirm the plan exists:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan status --plan-address "{plan_ref}"
```

## Put the Plan in the Ledger

The loop below opens an attempt per task, and an attempt is a ledger row. A plan authored through
the SAM plan operations lives in the content store, where there is nothing to open — `plan
dispatch` on such a plan answers `no task {plan_ref}/{task_id} in the ledger` and the wave cannot
start. Bring the plan across before the first dispatch:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan import --from content --plan-address "{plan_ref}"
```

This is safe to run when you are unsure: a plan the ledger already holds answers `exists` and
changes nothing. Once it has run, every `plan` command naming this address reads and writes the
ledger — including the `status` command above, which then reports the ledger's own columns.

The two stores answer `status` in shapes that share field names while disagreeing about where
those fields sit, so the import above changes how every later status read is addressed: plan-level
fields move inside a top-level `row` key, and `tasks` becomes an array of task rows. Read
[./references/plan-status-shapes.md](./references/plan-status-shapes.md) before reading any field
off a status response. The short of it: a key absent from the shape that answered reads as a
default, and where that key gates a confirmation the gate never fires.

## Record the Implementation Base SHA

The judge diffs a worker's `FILES_CHANGED` against the commit the plan started from, so that commit
has to be recorded before the first one lands.

Re-run the status command now that the import has run, and read `row.base_sha`. When it carries a
value the plan already records it and this step is done — a plan created in the ledger sets it at
creation, and re-recording it now would capture a later commit instead of the true starting point.
The pre-import status cannot answer this: the content shape has no `base_sha` field at all.

Otherwise read the plan's `row.context`. If it already contains a line matching
`**Implementation base SHA**: <sha>`, a prior run recorded it; skip this step for the same reason.

Otherwise, before the Progress Loop makes its first commit: run `git rev-parse HEAD` and prepend
`**Implementation base SHA**: {sha}\n\n` to the existing context — do not replace it, since
setting `context` overwrites the whole field — then write it back:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan update \
  --plan-address "{plan_ref}" --set context="{updated context}"
```

---

## Progress Loop

1. Query status:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan status --plan-address "{plan_ref}"
```

After receiving the status response, extract and store the autonomy mode. This loop runs after the
import, so the ledger is what answered and the mode is a column of its plan row:

`autonomy_mode = status["row"]["autonomy"]`

This value governs gate behavior throughout the remainder of the Progress Loop for this plan.

A resolved mode is what a working read looks like: the ledger writes its `plans.autonomy` column
when the plan is created, and `plan import` carries the authored value across. Supplying a default
yourself is never part of this read.

**If `autonomy_mode` does not resolve to `full_auto`, `checkpoint` or `per_task`** — the response
carries no `row`, the column is empty, or it holds something else — STOP the Progress Loop before
dispatching anything. Report the plan address, the status response's top-level keys, and that
autonomy could not be determined; ask the user which mode to run under, and use the mode they name.

Do not fall back to `full_auto`. The modes differ only in which confirmations reach the user and
`full_auto` is the one that asks for none, so reading an unresolved value as `full_auto` turns
every failure of this read into an unattended run the user did not choose — and does it silently,
because a run that asks for nothing looks exactly like a run the user asked not to be asked about.
A halt costs one question; work committed by agents the user meant to approve one at a time cannot
be taken back.

2. If tasks remain, query ready tasks **once** and store the result as the current batch:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan ready --plan-address "{plan_ref}"
```

Output shape: `{"items": [...], "count": N}`. Readiness is derived from each task's status and its
dependencies, so this command answers it rather than you.

> **Run `plan ready` ONCE per batch.** Store the returned task list. Loop over the stored list
> without fetching ready tasks again — step 5 below governs when the next batch is fetched.

3. Dispatch based on `autonomy_mode`:

If `autonomy_mode == "per_task"`:

Process tasks from the ready list one at a time:

- Dispatch task N via a single `Agent` call.
- Complete steps 4, 4a, 4b for task N.
- Present the per-task gate (after step 4b, described below) before dispatching task N+1.

Else (`autonomy_mode` is `"full_auto"` or `"checkpoint"`):

When multiple tasks are simultaneously ready (non-zero `count` with 2+ tasks in the ready list),
dispatch one `Agent()` call per ready task, all in parallel. When only one task is ready, dispatch
it with a single `Agent` call the same way `per_task` mode does.

For each task being dispatched:

- Choose which agent to dispatch with the decision in `dh:dispatch-contract`. Pass only the task reference (`plan_ref` + task ID) and the attempt number — the task definition's `agent` field is read after dispatch, not by the orchestrator.
- Open the attempt. This sets the task in-progress, starts its lease, and prints the attempt
  number, which is the key every command the worker runs carries back:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan dispatch --address "{plan_ref}/{task_id}"
```

  Add `--worktree {dir}` when the worker gets its own git worktree. Two codes mean "move to the
  next task in the batch rather than this one": `leased` and `not-ready`. Any other code stops the
  wave and goes to the user.

- Launch the chosen agent with the task reference and the attempt number as its entire prompt:

```text
{plan_ref}/{task_id}, attempt {attempt}
```

- The dispatch carries a task reference and the receiver resolves what to load from it.
  `dh:task-worker` reads the task record, loads the profile named in its `agent` field, and the
  task-execution skill it delegates to loads the task's own `skills` list; a specialist dispatched
  directly already carries its own behavior. Task-level skills stay additive to whatever the agent
  profile declares.

- Keep a table of launch handle to address and attempt. It is what lets you tell a worker still
  running from one whose launch already ended, and it is what step 4 needs in order to settle.

### Agent Health Check (While Waiting)

After dispatching a batch, the orchestrator waits for completion messages. Trigger a health check
when any of these occur: no message from any dispatched agent after ~10 minutes of silence, the
user asks about agent status, or `git log` shows no new commits when implementation work should be
in progress. Execute the full check — crash/idle/active branches and re-spawn logic — defined in
[./references/agent-health-check.md](./references/agent-health-check.md).

4. After each agent returns, record what came back against the attempt you opened, then judge it.

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan settle \
  --address "{plan_ref}/{task_id}" --attempt {attempt} --return-text "{the agent's response}"
```

Run `settle` as soon as a launch returns, including when the response is empty or the agent
crashed. It is what makes a launch that ended distinguishable from one still working; an unsettled
attempt reads as a worker still at it, and the loop waits on a worker that is gone.

Then judge against the ledger rather than the response text:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan read --address "{plan_ref}/{task_id}"
```

Compare the `Completion Report` and `Verification Results` sections against the task's acceptance
criteria and verification steps, and against the diff of the files the report lists since the
plan's base SHA. Where they hold:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan accept --address "{plan_ref}/{task_id}" --note "{why}"
```

Where a criterion is unmet, a verification step failed, or a report section is missing, send it
back with what to change — `reclaim` writes the response and returns the task to `not-started` in
one move, so the next `dispatch` finds it ready and its worker reads the answer first:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan reclaim \
  --address "{plan_ref}/{task_id}" --reason judge --response "{what to change and why}"
```

The full judge table — every status and settled state, and the command each calls for, including
the stale-lease and attempts-exhausted rows — is
[the work loop](../../docs/work-ledger/work-loop.md).

Read the agent's output for a `<concerns>` block as well. If present, append each concern to the backlog item as a checklist entry:

```text
mcp__plugin_dh_backlog__backlog_groom(
    selector="{issue}",  # {issue} is str | int — GitHub integer ID or beads string ID.
                         # See the tool's own selector parameter description for format rules.
    section="Concerns",
    content="- [ ] {concern text} (reported by {agent_name} on {task_id})",
    append=True
)
```

Use the MCP tool for this call.

Concerns accumulate across all task agents. They feed into the validation stage in `/complete-implementation` — each verified concern becomes a new backlog item.

4a. If a parent issue number is known (`str | int` — GitHub integer ID or beads string ID), attempt contract verification against the architect spec:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact read --item-id N --artifact-type architect
```

If `artifact_read` returns content (architect spec exists), resolve the files modified by the just-completed task:

```bash
git diff --name-only HEAD~1..HEAD
```

Then spawn the contract-verification agent:

```text
Agent(
    subagent_type="dh:contract-verification",
    prompt="""
Verify the just-completed task against the architect spec.

Task ID: {task_id}
Plan: {plan_ref}
Issue number: {issue}
Modified files:
{modified_files_list}

Fetch the architect spec yourself (per your own agent file) and read its Component Design and
Type System Design sections.
For each modified file, grep for function/class definitions and extract actual signatures.
Compare against the contracts defined in the spec.
Deliver findings per your own agent file's Delivery section — do not return them in your
response text; the dispatcher does not read it.
"""
)
```

If `artifact_read` fails or returns no content (no architect spec for this issue), skip step 4a entirely. Proportional quality gate items without an architect spec automatically skip this step.

4b. Confirm the batch is done

In `per_task` mode this is a no-op: the single dispatched `Agent()` call already returned, so the
task is terminal by construction. In `full_auto`/`checkpoint` mode, multiple agents were dispatched
concurrently — before the batch commit, confirm every task in the batch is terminal through
`plan status --plan-address "{plan_ref}"`, never by assuming a silent agent has finished. Each task
row carries `status`, `accepted`, `attempts`, and a `stale` flag that says when a lease ran out
with no worker behind it.

**Commit Ownership**

Commit responsibility depends on which execution mode is active.

**Same-worktree mode (default — no isolation flag):** The orchestrator owns all commits. Commit timing depends on `autonomy_mode`:

- **`per_task` mode**: The Per-task Confirmation Gate (below) ensures only one task runs at a time. Commit after step 4b, before dispatching the next task — no concurrent agents are writing:

  ```bash
  git add -A
  git commit -m "<type>(task): {task_id} — {task_title}"
  ```

- **`full_auto` and `checkpoint` modes**: Multiple tasks in a batch execute concurrently. Do NOT commit after each individual step 4b — other batch agents may still be writing to the worktree. Commit once **after step 5** confirms all tasks in the current batch are complete:

  ```bash
  git add -A
  git commit -m "<type>(task-batch): {plan_ref} — {task_ids}"
  ```

  Confirm every task in the batch is terminal (step 4b) before this commit.

In both cases, choose `<type>` to match the dominant change in the committed work (`feat`, `fix`, `docs`, `refactor`, etc.). Do NOT include `Fixes #N`, `Closes #N`, or `Resolves #N` trailers — see `start-task/SKILL.md` step 6. Issue closure is handled exclusively by `/complete-implementation`.

**Isolated-worktree mode (via `/dh:work-milestone`):** Each agent owns its own commits. The agent commits in its isolated worktree after completing its task. The orchestrator merges each worktree back when the completion message arrives. The orchestrator does NOT issue commit calls in this mode.

**Per-task Confirmation Gate** (active when `autonomy_mode == "per_task"` only):

After task N completes (steps 4 through 4b finished), before dispatching task N+1:

1. Display a compact task result summary:
   - Task ID and title
   - Completion status (complete / error)
   - Any concerns raised — read fresh via `backlog_view(selector="{issue}", section="Concerns", show="last")` (no `#` prefix, per step 4 above) immediately before rendering this summary, not from step 4's in-memory `<concerns>` block check. Step 4a's contract-verification agent (when dispatched) delivers its findings directly to the Concerns section and is never captured by step 4's check, so a fresh read is the only way this summary sees them.

2. Present a confirmation prompt to the user. The exact wording is implementation-defined;
   examples include "Ready to dispatch the next task? (yes/no)" or a numbered menu
   of options. The prompt must make clear which task will be dispatched next (task ID and title).

3. Await explicit user confirmation before proceeding.
   - If confirmed: dispatch the next task from the stored batch (or query the next batch if the batch is exhausted).
   - If declined or cancelled: stop the Progress Loop. Report the current plan state via
     `uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan status --plan-address "{plan_ref}"` and exit.

Skip this gate when `autonomy_mode` is `"full_auto"` or `"checkpoint"`.

5. After all tasks in the current batch complete, call `uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan status --plan-address "{plan_ref}"` to
   check plan progress. Tasks remain while the plan-level `progress` is `open`; return to step 2
   then to fetch the next batch of ready tasks. Do not fetch another ready batch until the previous
   batch is fully dispatched.

**5a. Wave-Completion Confirmation Gate** (active when `autonomy_mode == "checkpoint"` only):

After all tasks in the current batch complete and the status response from step 5 confirms that tasks remain:

1. Display a compact wave-completion summary from the step 5 status response. The ledger reports
   no completion percentage and no top-level ready list; derive both from its `tasks` array, where
   a row counts as done when `accepted` is 1 or `status` is `deferred` or `skipped`:
   - Number of tasks completed in this wave
   - Plan progress: how many rows are done out of how many `tasks` holds, with the plan-level
     `progress` word beside it
   - Number of tasks remaining: the rows that are not done
   - Next ready tasks: the rows whose `ready` is true — task IDs only

2. Present a confirmation prompt to the user. The exact wording is implementation-defined;
   examples include "Wave complete. Proceed with the next wave? (yes/no)".

3. Await explicit user confirmation before fetching another ready batch.
   - If confirmed: proceed to step 2 to fetch the next batch.
   - If declined or cancelled: stop the Progress Loop. Report the current plan state
     and exit. The plan remains in its current state and can be resumed later.

Skip this gate when `autonomy_mode` is `"full_auto"` or `"per_task"`.

Note: under `"per_task"`, per-task gates already fire for each task; no additional wave gate is needed.

> **Hook behavior on SubagentStop**: when a sub-agent finishes, `task_status_hook.py` runs
> `plan settle` for the attempt named in that sub-agent's own launch prompt, with its final
> message as the return text, then clears the active-task context. That is the same settle step 4
> asks of you; whichever runs first wins and the other is answered `already-settled`, so running
> step 4 yourself is never wrong. The hook covers the case where this session ends before step 4
> does. A settle it could not perform is printed to stderr, never absorbed.
>
> Do not treat the hook as the thing that moves the task. It writes no status at all. A task
> reaches its outcome because the worker ran `plan finish` and you ran `plan accept` — the loop
> above reads the ledger for that, not the hook's exit.

---

## Bookend Task Ordering

When the plan contains `acceptance-criteria-structured` entries, `swarm-task-planner` generates T0 and TN bookend tasks. No special handling is needed in this loop — existing readiness logic dispatches them in the correct order automatically:

- **T0** has `priority: 1` and `dependencies: []`, so it is the first ready task and dispatches before any implementation task.
- **TN** has `dependencies: [all non-bookend task IDs]`, so it becomes ready only after all implementation tasks complete and dispatches last.

T0 runs agent `t0-baseline-capture`. TN runs agent `tn-verification-gate`. Both agents register their results as artifacts via `artifact_register` (types `T0-baseline` and `TN-verification`). These artifacts are read by `/complete-implementation` in its pre-Phase 1 check via `artifact_read`.

### Bookend Artifact Registration

When the parent story issue number is known (`str | int` — GitHub integer ID or beads string ID), include `artifact_register` instructions in each bookend task's delegation prompt so the bookend artifacts are registered in the issue's artifact manifest:

**T0 delegation prompt addition:**

```text
Register the baseline content directly via MCP (no file write):
  mcp__plugin_dh_backlog__artifact_register(item_id=N, artifact_type="T0-baseline", artifact_id="T0-baseline-{slug}", content=<baseline yaml string>, agent="t0-baseline-capture")
```

**TN delegation prompt addition:**

```text
Register the verification content directly via MCP (no file write):
  mcp__plugin_dh_backlog__artifact_register(item_id=N, artifact_type="TN-verification", artifact_id="TN-verification-{slug}", content=<verification yaml string>, agent="tn-verification-gate")
```

If the issue number is not known, skip registration.

---

## Variant: Worktree Isolation

**Worktree isolation variant**: For milestone-scoped execution where each item gets its own worktree, use `/work-milestone` instead. See [work-milestone SKILL.md](../work-milestone/SKILL.md).

---

## Completion Gate

When all tasks show `COMPLETE`, load the `dh:complete-implementation` skill with `{plan_ref}` as
its argument, in this workflow's own context.
