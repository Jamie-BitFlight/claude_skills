---
name: assessor
description: Assess a plugin and produce an executable refactoring design, task plan, and context manifest. Use when preparing systematic plugin refactoring.
argument-hint: <plugin-name>
model: sonnet
user-invocable: true
---

If the user's intent does not match this skill, activate `/plugin-creator:plugin-lifecycle` to route it.

# Plan Plugin Refactoring

<plugin_name>
$ARGUMENTS
</plugin_name>

Execute the phases in order. Before Phase 1, create separate tracking tasks named for assessment, design, task-file creation, plan-index update, context gathering, and final handoff. Mark each in progress before execution and complete only after verifying its output. After each phase, display its key findings and output paths before continuing.

## Phase 1: Assess

Dispatch `plugin-creator:plugin-assessor` with:

- **Input:** `./plugins/<plugin_name>/` and the request to assess structural correctness, quality issues, and refactoring opportunities.
- **Context:** identify the plugin manifest and any skill, command, agent, hook, MCP, and reference content under the plugin root.
- **Execution ownership:** the agent runs its complete assessment protocol. Do not restate its phases, schemas, or scoring rules in the dispatch prompt.
- **Required output:** the standard assessment produced through its preloaded `/plugin-creator:assessment-reporting` skill, including marketplace readiness, scored findings, affected paths, severities, orphan classifications, and recommended execution roles.
- **Completion:** `STATUS: DONE` plus the inline report or report path. `STATUS: BLOCKED` must name the missing input.

Verify the report exists, contains the score and marketplace-readiness result, and accounts for every discovered component. Then activate `/plugin-creator:audit-skill-lifecycle <plugin_name>` and `/plugin-creator:audit-agent-lifecycle <plugin_name>` to add semantic lifecycle findings.

Activate `/plugin-creator:audit-skill-completeness` for individual marketplace candidates, low-scoring skills, or when the user requests deep quality evaluation. Otherwise record that this optional audit was not run.

Phase 1 is complete when the structural report and both lifecycle audit results are present, and every optional-audit decision is recorded.

## Phase 2: Design

Dispatch `plugin-creator:refactor-planner` with:

- **Input:** the complete Phase 1 assessment and audit results.
- **Target:** `.plugin-creator/plans/refactor-design-{plugin-slug}.md`, where the slug is the plugin directory name.
- **Context:** plugin root, current component paths, all findings, and validator output. Treat SK006/SK007 findings as the source of truth for complexity; do not copy numeric thresholds.
- **Required content:** every finding mapped to a concrete transformation, target path, dependencies, preserved behavior, and safe parallelization group. Include split plans, agent optimizations, documentation changes, and orphan resolutions only when present in the findings.
- **Completion:** write the target and return `STATUS: DONE` with its path, or `STATUS: BLOCKED` with the missing input.

Read the design and verify every Phase 1 finding has one disposition. Phase 2 is complete when the design exists and has no undisposed finding.

## Phase 3: Plan Tasks

Dispatch `plugin-creator:refactor-planner` with:

- **Inputs:** `.plugin-creator/plans/refactor-design-{plugin-slug}.md` and the existing `.plugin-creator/plans/REFACTOR-PLAN.md` when present.
- **Targets:** `.plugin-creator/plans/tasks-refactor-{plugin-slug}.md` and the matching plan-index entry.
- **Task contract:** each task names its ID, type, target, dependencies, priority, execution role, at least three acceptance criteria, required inputs, expected outputs, at least three verification steps, and safe parallel peers. Express ordering through dependencies rather than temporal estimates.
- **Routing:** `SKILL_SPLIT` to `/plugin-creator:refactor-skill`; `AGENT_OPTIMIZE` to `plugin-creator:subagent-refactorer`; `DOC_IMPROVE` to `plugin-creator:ai-doc-optimizer`; read-only audits to `plugin-creator:skill-auditor`; upstream synchronization to `plugin-creator:skill-content-updater`; description-only work to `/plugin-creator:write-frontmatter-description`.
- **Verification tasks:** validate the completed plugin, then update plugin documentation when the design requires it.
- **Completion:** write both targets and return `STATUS: DONE` with paths and parallelization groups, or `STATUS: BLOCKED` with the missing input.

Verify both files and confirm dependency edges match the design. Phase 3 is complete when every designed transformation has an executable task and every task has a verification path.

## Phase 4: Gather Context

Dispatch `plugin-creator:refactor-planner` with:

- **Inputs:** the design, task file, and `./plugins/<plugin_name>/`.
- **Write target:** the task file's `Context Manifest` section.
- **Required content:** current summaries for each target, existing patterns to preserve, cross-references, and external dependencies. Pass source paths; do not substitute summaries for unread source.
- **Completion:** return `STATUS: DONE` with the updated task-file path and manifest counts, or `STATUS: BLOCKED` with the missing input.

Verify the `Context Manifest` exists and accounts for every task target. Phase 4 is complete when no task lacks source context or dependency evidence.

## Final Handoff

Verify every tracking task is complete, then return:

```text
STATUS: DONE
Plugin: <plugin_name>
Assessment: {inline or report path}
Design: .plugin-creator/plans/refactor-design-{plugin-slug}.md
Tasks: .plugin-creator/plans/tasks-refactor-{plugin-slug}.md
Plan index: .plugin-creator/plans/REFACTOR-PLAN.md
Context manifest: present
Parallel groups: {groups or "none"}
Next action: /plugin-creator:implement-refactor {plugin-slug}
```

If execution cannot continue:

```text
STATUS: BLOCKED
Phase: {phase}
Reason: {specific missing input or failed verification}
Completed: {verified outputs}
Remaining: {uncompleted outputs}
```
