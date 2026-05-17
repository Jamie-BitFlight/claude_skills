---
name: implementation-manager
description: Manages feature implementation task state via SAM MCP tools. Use when querying task status, listing ready tasks, claiming tasks for execution, updating task timestamps, or coordinating multi-task feature rollout. Activated by the /dh:execution orchestrator to track progress — also activates directly when managing task files or configuring hook profiles.
user-invocable: false
disable-model-invocation: false
---

# Implementation Manager

## Current Task Context

**Available features (if in project with plan/ directory):**
!`uv run sam list 2>/dev/null || echo '{"features": [], "count": 0, "message": "Not in a project with task files"}'`

**Active task context (if any):**
!`python3 -c "from dh_paths import context_dir; import os; cdir = context_dir(os.environ.get('CLAUDE_CODE_SESSION_ID', '')); files = list(cdir.glob('active-task-*.json')) if cdir.exists() else []; print(files[0].read_text() if files else 'No active task')" 2>/dev/null || echo "No active task"`

A skill for querying and managing feature implementation task files. Provides programmatic access to task status for orchestrators coordinating multi-step feature implementations.

## SAM MCP Tool Usage

The SAM MCP server (`mcp__plugin_dh_sam__*`) is the primary interface for all SAM task file operations. The `uv run sam` CLI is available as fallback when MCP is unavailable.

### Commands

#### list

List all features with task files in the project's `plan/` directory:

```text
mcp__plugin_dh_sam__sam_plan(config={"action": "list"})
```

**Output:**

```json
{
  "features": [
    {
      "slug": "prepare-host",
      "task_file": "tasks-1-prepare-host.md"
    }
  ],
  "count": 1
}
```

#### status

Get detailed status for a specific feature:

```text
mcp__plugin_dh_sam__sam_plan(config={"action": "status"}, plan="P1")
```

**Output:**

```json
{
  "feature": "prepare-host",
  "task_file": "tasks-1-prepare-host.md",
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

```text
mcp__plugin_dh_sam__sam_plan(config={"action": "ready"}, plan="P1")
```

**Output:**

```json
{
  "feature": "prepare-host",
  "ready_tasks": [
    {
      "id": "1.3",
      "name": "Create core/prepare.py Business Logic",
      "agent": "python-cli-architect"
    }
  ],
  "count": 1
}
```

#### read

Read full plan data including task fields and context:

```text
mcp__plugin_dh_sam__sam_plan(config={"action": "read"}, plan="P1")
```

#### claim

Claim a task in-progress (prevents duplicate dispatch):

```text
mcp__plugin_dh_sam__sam_task(plan="P1", task="T01", config={"action": "claim"})
```

Returns `{"claimed": false, "error": "..."}` if task is already claimed or not found.

#### update

Update plan-level fields (e.g., context manifest):

```text
mcp__plugin_dh_sam__sam_plan(config={"action": "update", "context": "Context Manifest content"}, plan="P1")
```

## Task File Format

Task files use YAML frontmatter format. The SAM MCP tools validate all fields — do not parse task files directly.

```yaml
---
task: T01
title: "Task title"
status: not-started
agent: python-cli-architect
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

### Dependency Resolution

A task is "ready" when:

1. Status is `not-started`
2. All dependencies have status `complete` (or no dependencies)

## Hook Integration

The `task_status_hook.py` script provides automated task status tracking via Claude Code hooks.

### Hook Configuration

| Command              | Hook Event   | Matcher             | Purpose                                        |
| -------------------- | ------------ | ------------------- | ---------------------------------------------- |
| `/dh:execution` | SubagentStop | (all)               | Mark task COMPLETE, add Completed timestamp    |
| `/dh:start-task`        | PostToolUse  | `Write\|Edit\|Bash` | Update LastActivity timestamp during execution |

### How It Works

**SubagentStop (Task Completion)**:

When `/dh:execution` launches a sub-agent via `/start-task {task_file} --task {id}`, the SubagentStop hook fires when the sub-agent completes. The hook script:

1. Parses the original prompt to extract task file path and task ID
2. Updates task status from `IN PROGRESS` to `COMPLETE`
3. Adds `**Completed**: {ISO timestamp}` to the task section

**PostToolUse (Activity Tracking)**:

When `/dh:start-task` runs, it creates a context file at `~/.dh/projects/{slug}/context/active-task-{session_id}.json` (resolved via `dh_paths.context_dir(session_id)`) containing the task file path and task ID. On each Write, Edit, or Bash operation, the PostToolUse hook:

1. Reads the context file to identify the active task
2. Updates `**LastActivity**: {ISO timestamp}` in the task section

### Timestamp Field Responsibilities

| Field              | Added By                  | When                              |
| ------------------ | ------------------------- | --------------------------------- |
| `**Started**`      | Agent (via `/dh:start-task`) | When agent begins work on task    |
| `**Completed**`    | Hook (SubagentStop)       | When sub-agent finishes           |
| `**LastActivity**` | Hook (PostToolUse)        | On each Write, Edit, or Bash call |

## Hook Runtime Profile Controls

The `task_status_hook.py` script supports environment-variable-based profile controls that adjust hook behavior without editing SKILL.md files.

### CLAUDE_SKILLS_HOOK_PROFILE

Controls which hook handlers run. Case-sensitive lowercase. Default when unset or empty: `standard`.

- **`minimal`** — PostToolUse (LastActivity updates) is skipped entirely. SubagentStop (task completion) runs normally. Use this to reduce I/O during task execution when activity timestamps are not needed.
- **`standard`** — All handlers run. This is the current default behavior and is backward compatible with sessions that do not set the variable.
- **`strict`** — All handlers run. SubagentStop additionally performs pre-completion validation checks and emits warnings to stderr. Warnings are observational only — they do not prevent task completion. Strict checks verify that the task was claimed (status was `in-progress` before completion) and that acceptance criteria were defined (non-empty).

Invalid values produce a warning to stderr and fall back to `standard`.

### CLAUDE_SKILLS_DISABLED_HOOKS

Comma-separated list of hook IDs to disable. Each ID is stripped of whitespace. Empty segments are excluded. Unknown IDs are silently ignored for forward compatibility. Default when unset or empty: no hooks disabled.

Hook IDs for this script:

- `task-status:post-tool-use` — the PostToolUse handler (LastActivity timestamp updates)
- `task-status:subagent-stop` — the SubagentStop handler (task completion marking)

Disabled hooks take precedence over profile. If both `CLAUDE_SKILLS_HOOK_PROFILE=strict` and `CLAUDE_SKILLS_DISABLED_HOOKS=task-status:subagent-stop` are set, SubagentStop is skipped entirely (no strict checks run).

Disabled hooks exit 0 (Claude Code treats non-zero hook exit as an error that kills the hook chain).

### Examples

```bash
# Skip PostToolUse activity tracking (reduces I/O during task execution)
export CLAUDE_SKILLS_HOOK_PROFILE=minimal

# Enable strict pre-completion validation warnings
export CLAUDE_SKILLS_HOOK_PROFILE=strict

# Disable a specific hook by ID
export CLAUDE_SKILLS_DISABLED_HOOKS=task-status:post-tool-use

# Disable multiple hooks
export CLAUDE_SKILLS_DISABLED_HOOKS="task-status:post-tool-use,task-status:subagent-stop"
```

## Integration with /execution

The `/dh:execution` orchestrator uses this skill to:

1. Query task file status via `mcp__plugin_dh_sam__sam_plan`
2. Find ready tasks via `mcp__plugin_dh_sam__sam_plan`
3. Launch appropriate agents based on task's `agent` field
4. Update timestamps via hook scripts when tasks start/complete
