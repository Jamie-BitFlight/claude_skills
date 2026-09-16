---
name: implementation-manager
description: Manages feature implementation task state via SAM MCP tools. Use when querying task status, listing ready tasks, dispatching tasks for execution, updating task timestamps, or coordinating multi-task feature rollout. Activated by the /dh:execution orchestrator to track progress — also activates directly when managing tasks.
user-invocable: false
disable-model-invocation: false
---

# Implementation Manager

## Current Task Context

After activation, resolve `<sam_cli/>` through `dh:dh-cli-usage` and run `<sam_cli/> plan list` to
list available plans. Do not place `<sam_cli/>` in a dynamic `!` command: dynamic commands execute
before the model can resolve the instruction token.

**Active task context (if any):**
!`python3 -c "from dh_paths import context_dir; import os; cdir = context_dir(os.environ.get('CLAUDE_CODE_SESSION_ID', '')); files = list(cdir.glob('active-task-*.json')) if cdir.exists() else []; print(files[0].read_text() if files else 'No active task')" 2>/dev/null || echo "No active task"`

A skill for querying and managing feature implementation tasks. Provides programmatic access to task status for orchestrators coordinating multi-step feature implementations.

## SAM MCP Tool Usage

Use the configured provider's native interface for native state. In a Beads workspace, use `bd` directly for CRUD, readiness, claims/status, and dependencies. Use SAM MCP or the DH CLI adapter for structured SAM plans, task metadata, artifacts, dispatch, and validation that `bd` does not provide. See [Beads and workflow usage](../../docs/beads-and-workflow-usage.md).

### Structured SAM Commands

#### list

List all features with tasks tracked in the project's `plan/` directory:

```bash
<sam_cli/> plan list
```

**Output:**

```json
{
  "items": [
    {
      "plan_id": "P1",
      "feature": "prepare-host",
      "task_count": 8
    }
  ],
  "count": 1
}
```

#### status

Get detailed status for a specific feature:

```bash
<sam_cli/> plan status --plan-address P1
```

**Output:**

```json
{
  "feature": "prepare-host",
  "total_tasks": 8,
  "completed": 8,
  "in_progress": 0,
  "not_started": 0,
  "ready_tasks": [],
  "tasks": [
    {
      "id": "1.1",
      "name": "Add Data Models to shared/models.py",
      "status": "complete",
      "dependencies": [],
      "agent": null,
      "priority": 1,
      "complexity": "low"
    }
  ]
}
```

#### ready-tasks

List tasks ready for execution (dependencies satisfied):

```bash
<sam_cli/> plan ready --plan-address P1
```

**Output:**

```json
{
  "feature": "prepare-host",
  "ready_tasks": [
    {
      "id": "1.3",
      "name": "Create core/prepare.py Business Logic",
      "agent": "{resolved_agent}"
    }
  ],
  "count": 1
}
```

#### read

With `P` alone, `plan read` reads the plan document. With `P/T`, it reads that task with the
sections its attempts recorded:

```bash
<sam_cli/> plan read --address P1/T01
```

Add `--attempt {A}` only when you hold that attempt; naming one you do not is refused as
`stale-attempt`. For every task row with its derived columns, use `plan status --plan-address P1`
on a ledger plan.

#### dispatch

Open an attempt on a ready task. This is what sets it in-progress, starts its lease, and prevents a
second runner from taking it. It prints the attempt number, which every command the runner issues
carries back:

```bash
<sam_cli/> plan dispatch --address P1/T01
```

Prints `leased` when a runner already holds the task and `not-ready` when its dependencies have not
landed; either way the task is not the one to start now.

The `plan claim` command writes to the content store rather than the ledger, so a task claimed that
way leaves the ledger row where it was. Open attempts with `dispatch`.

#### update

Set plan-level fields on the ledger, such as the context manifest:

```bash
<sam_cli/> plan update --plan-address P1 --set context="Context Manifest content"
```

`--set` names the ledger column, so write field names with underscores. Setting a field replaces
its whole value; read the current one with `plan status --plan-address P1` and write back the result when
you mean to add to it rather than replace it.

The same command's `--context` flag reaches the content store instead — the two stores hold
different plans, and the flag chosen is what selects between them.

## Task Schema

Tasks are represented as YAML frontmatter fields, defined in `sam_schema/core/models.py`. The SAM MCP tools validate all fields — do not parse tasks directly from storage.

```yaml
---
task: T01
title: "Task title"
status: not-started
agent: {resolved_agent}
dependencies: []
priority: 1
complexity: medium
accuracy-risk: low
skills: []
---
```

### Status Values

- `not-started` — task has not been started
- `in-progress` — task is claimed and being executed
- `complete` — task is done
- `blocked` — task cannot proceed
- `deferred` — task is intentionally postponed
- `skipped` — task was bypassed without execution
- `failed` — task execution ended in failure

### Dependency Resolution

A task is "ready" when:

1. Status is `not-started`
2. All dependencies have status `complete`, `deferred`, or `skipped` (or no dependencies)

## Hook Integration

The `task_status_hook.py` script settles the attempt a stopping sub-agent was launched for, via one Claude Code hook.

### Hook Configuration

| Command         | Hook Event   | Matcher | Purpose                                                  |
| --------------- | ------------ | ------- | --------------------------------------------------------- |
| `/dh:execution` | SubagentStop | (all)   | Settle the attempt the stopping worker was launched for |

### How It Works

**SubagentStop (settle)**:

A SubagentStop hook registered in `hooks/hooks.json` runs in the orchestrator's session when a
sub-agent it launched stops, so it is the orchestrator's observation point. It records that the
launch ended, and nothing else:

1. Reads the sub-agent's own initial prompt from `agent_transcript_path` and takes the plan
   address, the task id and the attempt number from it. The dispatch contract requires all three
   in the prompt (`{plan}/{task}, attempt {A}`), and the transcript is per-sub-agent, so parallel
   workers correlate to distinct attempts.
2. Runs `plan settle --address {plan}/{task} --attempt {A} --return-text "{the final message}"`.

It writes no task status. The runner's own `plan finish --result` records the outcome and the
orchestrator's `plan accept` / `plan reclaim` records the verdict — see
[ARCHITECTURE.md](../../ARCHITECTURE.md) § "What a hook may write" for why a third writer of that
one fact would drift from both. The worker's final message is stored verbatim as the attempt's
return text, which is evidence the judge reads.

Every failure is reported on stderr, never absorbed: a prompt naming no attempt, a plan the ledger
does not hold, and a settle the CLI refused. The hook still exits 0, because the
SubagentStop critical path must not be blocked.

The orchestrator settles as its own next step too, and whichever gets there first wins — the
other is answered `already-settled`. The hook exists for the launch whose orchestrator step never
ran.

### Timestamp Field Responsibilities

| Field           | Added By                                                              | When                                    |
| --------------- | ---------------------------------------------------------------------- | --------------------------------------- |
| `**Started**`   | `plan dispatch`, when the orchestrator opens the attempt               | When the worker is launched             |
| `**Completed**` | `plan finish --result complete`, or `plan accept` on a returned task   | When the runner or the judge closes it  |

## Hook Runtime Controls

### CLAUDE_SKILLS_DISABLED_HOOKS

Comma-separated list of hook IDs to disable. Each ID is stripped of whitespace. Empty segments are excluded. Unknown IDs are silently ignored for forward compatibility. Default when unset or empty: no hooks disabled.

The hook ID for this script: `task-status:subagent-stop` — the SubagentStop handler (settling the attempt).

Disabled hooks exit 0 (Claude Code treats non-zero hook exit as an error that kills the hook chain).

### Example

```bash
# Disable the settle hook
export CLAUDE_SKILLS_DISABLED_HOOKS=task-status:subagent-stop
```

## Integration with /execution

The `/dh:execution` orchestrator uses this skill to:

1. Query task status via `<sam_cli/> plan status`
2. Find ready tasks via `<sam_cli/> plan ready`
3. Open an attempt per task via `plan dispatch`, then launch the agent its `agent` field names,
   passing the address and the attempt number
4. Settle each launch with `plan settle` when it returns, then judge with `plan read` and close
   with `plan accept` or send back with `plan reclaim`


Resolve `<sam_cli/>` and `<dh_scripts/>` through `dh:dh-cli-usage`.
