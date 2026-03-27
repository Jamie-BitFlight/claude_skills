---
name: implement-feature
description: Use when a SAM task plan exists and you need to execute the implementation loop — picks up ready tasks, delegates each to its specified agent, and relies on hooks to update task timestamps and status. Activates when a task file path or feature slug is provided after planning is complete. Task plans are stored under ~/.dh/projects/{slug}/plan/ and resolved via dh_paths.plan_dir().
argument-hint: <task-file-path or feature-slug>
user-invocable: true
hooks:
  SubagentStop:
  - hooks:
    - type: command
      command: python3 "${CLAUDE_SKILL_DIR}/../../implementation-manager/scripts/task_status_hook.py"
---

# Implement Feature (SAM Workflow Execution)

As you review code, update your agent memory with patterns, conventions, and recurring issues you discover.

This workflow continues from `add-new-feature`. It executes tasks from a SAM task file until complete (or blocked).

<feature_input>$ARGUMENTS</feature_input>

---

## Resolve Task File

Rules:

- If `<feature_input/>` ends with `.md`, treat it as the task file path and extract the plan address `P{N}` from the filename (e.g., `plan/tasks-3-integrate-sam-schema.md` → `P3`).
- Otherwise, treat it as a feature slug (or partial slug) and resolve plan address via `sam_status`:

```text
mcp__plugin_dh_sam__sam_status(plan="<feature_input/>")
```

---

## Progress Loop

1. Query status:

```text
mcp__plugin_dh_sam__sam_status(plan="P{N}")
```

2. If tasks remain, query ready tasks **once** and store the result as the current batch:

If parent story issue number is known, prefer the MCP tool:

```text
backlog_get_ready_sam_tasks(parent_issue_number=N)
Output shape: {"feature": "...", "ready_tasks": [...], "count": N}
Falls back to local cache if GitHub unavailable.
```

If parent issue number is unknown, use the SAM MCP tool:

```text
mcp__plugin_dh_sam__sam_ready(plan="P{N}")
```

> **Call `sam_ready` (or `backlog_get_ready_sam_tasks`) ONCE per batch.** Store the returned
> task list. Loop over the stored list — do NOT call `sam_ready` again within the loop.
> After all tasks in the current batch are dispatched and completed, use
> `mcp__plugin_dh_sam__sam_status` (~270 chars) to check whether more tasks remain.
> Only call `sam_ready` again when the previous batch is fully dispatched and you need the
> next batch of ready tasks.

3. For each ready task (or batch of ready tasks):

When multiple tasks are simultaneously ready (non-zero `count` with 2+ tasks in the ready list), dispatch them in parallel using `TeamCreate`:

```text
TeamCreate(team_name: "impl-{slug}")
```

Spawn one teammate per ready task. When only one task is ready, a single Agent call is acceptable. `TeamCreate` is the standard parallel dispatch mechanism — use it whenever 2+ tasks are ready at the same time.

For each task being dispatched:

- Route to the agent named in the task's `agent` field (or resolved from `role`).
- Check the task's `skills` list from the ready-tasks JSON output.
- If `skills` is non-empty, include skill-loading instructions in the delegation prompt:

```text
Before starting work, load these skills: {comma-separated skill names}.
For each skill, call: Skill(skill="{skill-name}")
```

- If `skills` is empty or missing, do not add skill-loading instructions (backward compatible).
- Launch the agent with a prompt that invokes `start-task`:

```text
Skill(skill="start-task", args="{task_file_path} --task {task_id}")
```

> **Note**: Task-level skills are additive to agent-level skills. If the agent definition
> already declares skills via its frontmatter, task-level skills supplement them (they do not
> replace agent-level skills). Loading the same skill twice is a no-op.

4. After each agent returns, check its output for a `<concerns>` block. If present, append each concern to the backlog item as a checklist entry:

```text
mcp__plugin_dh_backlog__backlog_groom(
    selector="#{issue}",
    section="Concerns",
    content="- [ ] {concern text} (reported by {agent_name} on {task_id})",
    append=True
)
```

Concerns accumulate across all task agents. They feed into the validation stage in `/complete-implementation` — each verified concern becomes a new backlog item.

5. After all tasks in the current batch complete, call `mcp__plugin_dh_sam__sam_status` to
   check plan progress. If tasks remain, return to step 2 to fetch the next batch of ready
   tasks. Do NOT call `sam_ready` again until the previous batch is fully dispatched.

> **Hook behavior on SubagentStop**: When a sub-agent finishes, `task_status_hook.py` marks
> the task complete in the local task file. After marking the task complete locally, the hook
> calls `backlog_core.github.update_task_status()` to sync the completion to the GitHub
> sub-issue (if `github_issue` field is set in the task YAML). GitHub sync failure does not
> affect the hook exit code.

---

## Bookend Task Ordering

When the plan contains `acceptance-criteria-structured` entries, `swarm-task-planner` generates T0 and TN bookend tasks. No special handling is needed in this loop — existing readiness logic dispatches them in the correct order automatically:

- **T0** has `priority: 1` and `dependencies: []`, so it is the first ready task and dispatches before any implementation task.
- **TN** has `dependencies: [all non-bookend task IDs]`, so it becomes ready only after all implementation tasks complete and dispatches last.

T0 runs agent `t0-baseline-capture`. TN runs agent `tn-verification-gate`. Both agents write YAML result files to `~/.dh/projects/{project-slug}/plan/T0-baseline-{slug}.yaml` and `~/.dh/projects/{project-slug}/plan/TN-verification-{slug}.yaml` (resolved via `dh_paths.plan_dir()`). These files are read by `/complete-implementation` in its pre-Phase 1 check.

### Bookend Artifact Registration

When the parent story issue number is known, include `artifact_register` instructions in each bookend task's delegation prompt so the bookend artifacts are registered in the issue's artifact manifest:

**T0 delegation prompt addition:**

```text
After writing plan/T0-baseline-{slug}.yaml, register it:
  mcp__plugin_dh_backlog__artifact_register(issue_number=N, artifact_type="T0-baseline", path="plan/T0-baseline-{slug}.yaml", agent="t0-baseline-capture")
```

**TN delegation prompt addition:**

```text
After writing plan/TN-verification-{slug}.yaml, register it:
  mcp__plugin_dh_backlog__artifact_register(issue_number=N, artifact_type="TN-verification", path="plan/TN-verification-{slug}.yaml", agent="tn-verification-gate")
```

If the issue number is not known, skip registration. The artifacts remain discoverable via filesystem conventions.

---

## Completion Gate

When all tasks show `COMPLETE`, invoke:

```text
Skill(skill="complete-implementation", args="{task_file_path}")
```
