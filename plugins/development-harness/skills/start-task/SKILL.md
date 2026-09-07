---
name: start-task
description: Use when executing a task the orchestrator dispatched — reads the task and its orchestrator response from the work ledger, writes active-task context for hooks, loads task-level skills, implements against acceptance criteria, records divergences and the completion report as task sections, and closes the attempt. Triggers on task execution within the implement-feature loop or when an agent picks up a specific task from a plan.
argument-hint: <plan-address> [--task <task-id>] [--attempt <n>] [--complete <task-id>]
user-invocable: true
hooks:
  PostToolUse:
  - matcher: Write|Edit|Bash
    hooks:
    - type: command
      command: uv run --script "${CLAUDE_PLUGIN_ROOT}/skills/implementation-manager/scripts/task_status_hook.py"
---

# Start Task (SAM Task Execution Helper)

You are implementing a specific task in a SAM plan, addressed as `P{id}/T{id}`. The backend resolves that address and returns the task — no path is involved.

Your whole interface to task state is the SAM CLI's `plan` group. It reaches the work ledger: the
store that holds each task's status, the attempts opened on it, the sections each attempt appended,
and the lease that tells the orchestrator you are still working. The `sam_task` and `sam_plan` MCP
tools answer from the content store, which holds the plan's authored content and none of that
state, so task state moves through the commands below and not through those tools.

<task_input>
$ARGUMENTS
</task_input>

<sam_cli>
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py"
</sam_cli>

<mcp_server_scripts>
SAM server: uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/run_sam_server.py"
Backlog server: uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/run_backlog_server.py" --project-dir .
</mcp_server_scripts>

---

**Tool availability**: task state moves through the `<sam_cli/>` command above, which needs no MCP server. The artifact and backlog steps below use `mcp__plugin_dh_backlog__*` tools; if one is unavailable, see the troubleshooting steps at ${CLAUDE_PLUGIN_ROOT}/docs/mcp-connection-check.md — its commands use the `<sam_cli/>` and `<mcp_server_scripts/>` values above.

## Parse Arguments

- `plan_address` (required): plan address in `P{hex}` form, e.g. `Pdec8934d`
- `--task <id>` (optional): Task ID to start (defaults to first ready task)
- `--attempt <n>` (optional): the attempt number the orchestrator opened for this dispatch. Carry
  it on every ledger command below. It is the key that proves a command belongs to this dispatch:
  a command from a superseded attempt is refused with `stale-attempt`.
- `--complete <id>` (optional): Task ID to close

---

## If `--complete <task-id>` Provided

With an attempt number, close the attempt. This is the runner's own close, and it records the
outcome as well as the status:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan finish \
  --address P{N}/T{M} --attempt {n} --result complete --note "{what was done}"
```

`finish --result complete` answers `report-missing` until this attempt has both a `Completion
Report` and a `Verification Results` section. Append them first (see "Close the Attempt" below),
then run `finish` again.

Without an attempt number, no runner is closing anything, so move the status directly and say why:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan state \
  --address P{N}/T{M} --new-status complete --reason "{why this moved without a runner}"
```

`--reason` is required — the ledger records why a status moved with no runner behind it.

---

## Starting a Task

1. Read the task via the SAM CLI, naming your attempt. This is your first command:

   ```bash
   uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan read --address P{N}/T{M} --attempt {n}
   ```

   Naming the attempt also pushes out your lease, so the orchestrator can tell a working runner
   from a stalled one. Leave `--attempt` off only when your dispatch named no attempt number.

   The result carries the task row — title, requirements, constraints, acceptance criteria,
   verification steps, and the `skills` list to load before implementing — and the sections
   recorded on the task. Two of those sections decide what you do first:

   - `Orchestrator Response` — why a previous attempt was sent back. Act on it before anything
     else.
   - `Completion Report` from an earlier attempt — when it carries a `BRANCH:` line, switch to
     that branch before you start.

   Use the address form `P{N}/T{M}` where `N` is the plan number and `M` is the task number from the `--task` argument.

1a. **Discover plan artifacts via manifest** (when issue number is known):

   If the task row carries a `github_issue` value or the plan carries an `issue` field, query the artifact manifest to discover available plan artifacts:

   ```bash
   uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact list --item-id N
   ```

   If the response contains artifacts (non-empty `artifacts` list), use `artifact_read` to fetch the architect spec and feature context content:

   ```bash
   uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact read --item-id N --artifact-type architect
   uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact read --item-id N --artifact-type feature-context
   ```

   Use the returned content as context for implementation instead of reading filesystem paths directly. This is especially important for worktree-isolated agents that cannot access uncommitted plan files from the root worktree.

   **Fallback**: If `artifact_list` returns an empty manifest (no `artifacts` entries) or an error, try `artifact_read` with types `architect` and `feature-context` directly. These artifact types are registered by the agents that produce them.

2. Select the task:
   - If `--task` provided, use that ID
   - Else run `plan ready --plan-address P{N}` and take the first task it lists — readiness is derived from status and dependencies, so the ledger answers this rather than you

2a. **Load task-level skills** (if present):
   - Read `skills` from the task row of the `plan read` result (an array of skill names).
   - If absent or empty, skip.
   - For each skill name, invoke: `Skill(skill="{skill-name}")`
   - If a skill fails to load, log a warning and continue. Do not abort task execution.
   - Task-level skills are **additive** to any skills already declared in the agent definition's frontmatter.

3. Your attempt is already open.

   `dispatch` opened it when the orchestrator launched you, which is what set the task
   `in-progress` and started the lease. There is nothing to claim, and nothing to write to the
   status field by hand.

   The CLI's `plan claim` command does not reach the ledger. It writes to the content store, so a
   task claimed that way leaves the ledger row exactly where it was and the orchestrator watching a
   task that never moved. Use `plan read --attempt {n}` (step 1) as your first command instead.

   If `plan read` refuses:

   | code | what it means and what to do |
   |---|---|
   | `stale-attempt` | another attempt superseded yours. Stop and return STATUS: BLOCKED with `stale-attempt` as the reason. |
   | `attempt-closed` | this attempt was already closed. Return STATUS: DONE when you had already run `finish`, otherwise STATUS: BLOCKED with `attempt-closed`. |
   | `archived` | the plan is closed. Stop and report it. |

4. Register the active-task context via the SAM CLI (required for hook-driven updates):

   ```bash
   uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" active-task set \
     --address P{N}/T{M} \
     --parent-issue N \
     --session-id "${CLAUDE_CODE_SESSION_ID}"
   ```

   This is session-scoped context for the PostToolUse hook, which stamps `last-activity` on the
   task while you work. It is not task state and holds nothing the ledger holds.

   It is not how the SubagentStop hook finds you. That hook takes your address and attempt from
   your own launch prompt, because this record is keyed by `${CLAUDE_CODE_SESSION_ID}` — the
   parent session's id inside a sub-agent, so a wave's workers all share one — and carries no
   attempt number.

   Omit `--parent-issue` if the story issue number is not known; absence is `None`. It accepts
   `str | int` — GitHub integer IDs (e.g., `42`) and beads string IDs (e.g., `"bd-a3f8"`) are both
   valid.

4a. **Renew the lease before work that may outrun it.**

   Your lease has a deadline. Before starting anything long — a full test suite, a build, a large
   refactor — push it out:

   ```bash
   uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan renew --address P{N}/T{M} --attempt {n}
   ```

   `renew` prints `renew_by`: the instant the lease next expires. `plan read` and `plan update`
   push the deadline out too whenever you pass `--attempt`, but `renew` is the command that tells
   you where the new deadline sits. A lease left to expire lets the orchestrator take the task back
   and hand it to another runner, and your commands then answer `stale-attempt`.

5. **Record divergence observations during implementation.**

   While implementing, if you discover that the architect spec or feature-context
   describes something that does not match what you are implementing, record a
   divergence note on the task through the ledger.

   **When to record**: Record a divergence note when ALL of these hold:
   - You are implementing something that differs from what the architect spec or
     feature-context describes
   - The difference is not a trivial implementation detail (e.g., different variable
     name, different import path)
   - The difference affects the observable behavior, structure, or scope of the feature

   Write the note and its running count in one command. Appending the section and setting the
   count are sub-operations of a single `update`:

   ```bash
   uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan update \
     --plan-address P{N} --task-id T{M} --attempt {n} \
     --append-section "Divergence Notes" --section-content "{note body}" \
     --set divergence_notes={new_count}
   ```

   `{new_count}` is the task's current `divergence_notes` value plus one; read the current value
   from the `plan read` result of step 1. Write the field name with an underscore —
   `divergence_notes` is the ledger column, and a hyphenated name is refused.

   The `--append-section` value supplies the `## Divergence Notes` heading — `{note body}` carries
   no heading of its own:

````markdown
### DN-1: {Brief title}

- Plan artifact: `artifact_read(item_id={N}, artifact_type="architect")`, section "{section name}"
- Plan claim: "{quoted text from plan artifact}"
- Actual implementation: "{what was actually done and why}"
- Classification: design-refinement | intent-divergence
- Recorded: {ISO timestamp}
````

   Never record a divergence note by editing a file. The task is addressed logically; on a remote
   backend no task file exists to edit, and a file written in one worktree is unreadable from
   another, so a file-based note is silently lost.

   For full artifact classification rules and divergence thresholds, see
   [plan-artifact-lifecycle.md](../../docs/plan-artifact-lifecycle.md).

6. **Commit message restriction — Fixes #N trailers are PROHIBITED in task-level commits.**

   Task-level commits must NEVER include `Fixes #N`, `Closes #N`, or `Resolves #N` trailers.
   These trailers trigger automatic GitHub issue closure. Issue closure is handled exclusively
   by `/complete-implementation` in its final commit step, after all quality gates pass.
   Including these trailers in task commits causes premature issue closure before verification
   is complete.

7. Implement against the task acceptance criteria and run its verification steps.

---

## Close the Attempt

Two sections and one command, in that order. Each carries `--attempt {n}`, because sections are
recorded against the attempt that appended them and an attempt that follows a send-back appends
its own.

1. Append the `Completion Report` with the lines `TASK:`, `BRANCH:`, `FILES_CHANGED:`, `COMMITS:`
   and `NOTES:`:

   ```bash
   uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan update \
     --plan-address P{N} --task-id T{M} --attempt {n} \
     --append-section "Completion Report" --section-content "{the report}"
   ```

2. Append the `Verification Results`: one line per entry of the task's `verification_steps`, each
   reading `<step> — passed|failed: <evidence>`, or the single word `none` when the task has no
   verification steps:

   ```bash
   uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan update \
     --plan-address P{N} --task-id T{M} --attempt {n} \
     --append-section "Verification Results" --section-content "{the results}"
   ```

3. Close the attempt once, as your last ledger command:

   ```bash
   uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" plan finish \
     --address P{N}/T{M} --attempt {n} --result complete --note "{summary}"
   ```

   Choose the result that matches what happened, and let `--note` carry what the orchestrator needs
   in order to decide:

   | result | when | what `--note` carries |
   |---|---|---|
   | `complete` | acceptance criteria met, verification steps run | what was done |
   | `failed` | the work cannot be finished as written | what stopped you |
   | `blocked` | something outside the task must change first | what must change |
   | `needs-input` | a decision is needed before you can continue | the question |

   `finish --result complete` answers `report-missing` until this attempt has both a `Completion
   Report` and a `Verification Results` section. Append whichever is missing with `--attempt {n}`,
   then run `finish` again. The other results — `failed`, `blocked`, `needs-input` — close the
   attempt without either section, so a report you cannot honestly write is not what keeps you from
   reporting the outcome.

The status you write to the ledger and the `STATUS:` line you return are different things and each
needs the other — `/dh:subagent-contract` says which carries what. Return `STATUS: DONE` once
`finish` was recorded, whatever its `--result`.
