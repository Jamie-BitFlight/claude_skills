---
name: implement-refactor
description: Execute an assessor task file and every generated follow-up in dependency order. Use when a refactoring task file already exists.
argument-hint: <plugin-slug or task-file-path>
model: sonnet
user-invocable: true
---

# Implement Refactor

<refactor_input>
$ARGUMENTS
</refactor_input>

## 1. Resolve And Read

If the input is a markdown path, use it. Otherwise resolve
`.plugin-creator/plans/tasks-refactor-{slug}.md`. Read the complete task file and linked design.
Extract each task's ID, status, dependencies, target, execution role, acceptance criteria,
verification steps, and safe parallel peers.

Gate: stop with `STATUS: BLOCKED` when either file is absent, a task lacks an execution contract,
or dependency edges conflict with the design.

## 2. Build The Work Graph

Create one tracking item per task plus completion validation. A task is ready only when it is incomplete
and every dependency is complete. Run ready tasks in parallel only when the task file marks them as
safe peers and their write targets do not overlap. If incomplete tasks remain and none are ready,
return the dependency deadlock as `STATUS: BLOCKED`.

## 3. Route And Execute

Use the task's execution role when it is reachable in the current harness. The canonical routes
for plans produced by `/plugin-creator:assessor` are:

| Task type | Reachable route |
|---|---|
| `SKILL_SPLIT` | Activate `/plugin-creator:refactor-skill` |
| `AGENT_OPTIMIZE` | Dispatch `plugin-creator:subagent-refactorer` |
| `DOC_IMPROVE` or `ORPHAN_RESOLVE` | Dispatch `plugin-creator:ai-doc-optimizer` |
| read-only quality audit | Dispatch `plugin-creator:skill-auditor` |
| upstream documentation sync | Dispatch `plugin-creator:skill-content-updater` |
| description-only change | Activate `/plugin-creator:write-frontmatter-description` |
| `STRUCTURE_FIX` | Dispatch the harness-native `general-purpose` agent |

Reject an unavailable role instead of assuming a project-level or separately installed agent.
Pass the task file and task ID, then activate `/plugin-creator:start-refactor-task` for the task's
execution contract.

After each task returns:

1. Verify its acceptance criteria and command evidence.
2. Verify the task file status is complete.
3. Mark its tracking item complete.
4. Recalculate ready tasks.

A failed task remains incomplete. Return its evidence and blocker; do not skip it or ask the user to
choose a weaker completion path.

## 4. Validate And Recurse

Activate `/plugin-creator:ensure-complete <task-file-path>` exactly once. It owns assessment,
refactor validation, documentation validation, and follow-up planning for that task file. Do not
run those checks separately here and do not ask it to re-enter itself.

If it returns follow-up task files, execute each through Steps 1-4 in dependency order. This skill
is the sole owner of follow-up recursion. Completion means every task and follow-up task is
complete, each `ensure-complete` call returned `STATUS: DONE`, and the plan index records the result.

Return:

```text
STATUS: DONE
Plugin: {plugin}
Task file: {path}
Completed tasks: {IDs}
Validation: {commands and results}
Follow-up tasks: {completed paths or "none"}
Plan index: {updated path}
```

When blocked:

```text
STATUS: BLOCKED
Task: {ID or "workflow"}
Reason: {specific blocker}
Completed: {verified task IDs}
Remaining: {task IDs}
```
