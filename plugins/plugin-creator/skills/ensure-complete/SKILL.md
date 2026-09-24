---
name: ensure-complete
description: Validate a completed plugin refactor against its task evidence, baseline assessment, documentation, and current validators. Use after implement-refactor or when deciding whether refactoring is complete.
argument-hint: <task-file-path>
model: sonnet
user-invocable: true
---

# Complete Refactor

<task_file>
$ARGUMENTS
</task_file>

Run the phases in order. Create one tracking item per phase and a final-summary item before Phase
1. Mark each phase complete only after its output passes the stated gate. A `STATUS: BLOCKED`
response stops the workflow and is returned with the completed and remaining phases.

## Phase 1: Reassess

Dispatch `plugin-creator:plugin-assessor` with the task file and plugin root. Require its standard
report through the preloaded `plugin-creator:assessment-reporting` skill, including:

- current score and marketplace readiness;
- comparison with the baseline assessment or refactor design;
- remaining findings with severity and affected paths;
- `STATUS: DONE`, or `STATUS: BLOCKED` naming the missing input.

Gate: verify the report exists, the score comparison is reproducible from the named baseline, and
every current plugin component is accounted for.

## Phase 2: Validate The Refactor

Dispatch `plugin-creator:refactor-validator` with the task file, plugin root, and before/after
evidence. Let that agent own validator selection and canonical schema interpretation; do not copy
its checklists here.

Gate: verify every completed task has acceptance evidence, all reported validator commands and
results are present, and every finding has severity, `file:line`, evidence, and remediation.

## Phase 3: Audit Documentation Drift

Dispatch `plugin-creator:refactor-validator` with a documentation-only scope: compare the task's
changed capabilities and paths with the plugin README, skills, agents, references, and plugin
manifest. Require resolved-link evidence and a list of stale, missing, or contradictory docs.

Gate: verify every changed or removed public component has a documentation disposition. An empty
finding set must be stated explicitly.

## Phase 4: Dispose Findings

Combine findings from Phases 1-3. If any finding remains, dispatch
`plugin-creator:refactor-planner` to create
`.plugin-creator/plans/tasks-refactor-{plugin-slug}-followup-{N}.md` and update the existing plan
index. Every finding must map to one task or an explicit accepted disposition; every task must have
dependencies, an execution role, acceptance criteria, and verification steps.

Gate: either no unresolved finding remains, or the follow-up task file exists and accounts for
every unresolved finding.

## Completion

If follow-up tasks exist, return their paths to the caller. This skill validates and plans exactly
once; it does not execute follow-ups or re-enter validation. `/plugin-creator:implement-refactor`
owns follow-up execution and invokes this skill once after each completed task file.

If no follow-up tasks exist, update `.plugin-creator/plans/REFACTOR-PLAN.md` using its existing
completed-entry format. Do not invent a completion date or score when the evidence does not provide
one.

Return:

```text
STATUS: DONE
Task file: {path}
Plugin: {plugin}
Assessment: {report path or inline}
Score: {before} -> {after}
Refactor validation: {result}
Documentation drift: {result}
Follow-up tasks: {paths or "none"}
Plan index: {updated path}
```

When blocked:

```text
STATUS: BLOCKED
Phase: {phase}
Reason: {specific missing input or failed gate}
Completed: {verified outputs}
Remaining: {uncompleted outputs}
```
