---
name: development-harness
description: Routes to the correct dh skill entry point by intent. Use when unsure which development-harness skill to invoke, starting a development workflow, or invoking /dh directly. Covers capture, groom, plan, execute, single task, quality gates, and milestone routing.
model: opus
context: fork
user-invocable: true
---

# Development Harness — Plugin Overview and Skill Router

This skill routes to the correct entry point for the development lifecycle. Read it to decide which skill to invoke — not to execute work.

## SAM Workflow Pipeline

```text
/dh:add-new-feature  ──>  /dh:implement-feature  ──>  /dh:complete-implementation
   (planning)            (execution loop)         (quality gates)
```

---

## What This Plugin Provides

The development-harness plugin implements the structured development lifecycle for tracked backlog items. It spans capture through verified closure using a chain of skills backed by GitHub Issues as the source of truth and `~/.dh/projects/{slug}/` as the local state directory.

**Skills available:** `/dh:create-backlog-item`, `/dh:groom-backlog-item`, `/dh:work-backlog-item`, `/dh:add-new-feature`, `/dh:implement-feature`, `/dh:complete-implementation`, `/dh:gate-push`, `/dh:work-milestone`

Plugin-level source copies exist at `plugins/development-harness/skills/` for each skill.

---

## Skill Router — "I want to do X"

```mermaid
flowchart TD
    Start([What do you want to do?]) --> Q1{Intent?}

    Q1 -->|Capture new work —<br>bug, feature idea, observation| Create["/dh:create-backlog-item<br>Modes: guided intake, quick title, --auto title<br>Writes to ~/.dh/projects/{slug}/backlog/"]

    Q1 -->|Prepare an item for planning —<br>verify claims, map impact, estimate effort| Groom["/dh:groom-backlog-item {title|section|all}<br>RT-ICA + parallel swarm: fact-checker,<br>impact-analyst, rtica-assessor, classifier, groomer<br>Requires: item exists in backlog"]

    Q1 -->|Plan AND execute a backlog item<br>end-to-end through closure| Work["/dh:work-backlog-item {title|#N|--auto}<br>Handles: auto-groom, RT-ICA gate, SAM planning,<br>GitHub sync, close, resolve<br>STOPS if item already has a Plan field"]

    Q1 -->|Plan a feature — produce SAM artifacts<br>without executing| Plan["/dh:add-new-feature {feature description}<br>Phases: discovery → codebase analysis →<br>architecture spec → task decomposition →<br>validation → context manifest<br>Output: feature slug + P{id} task plan"]

    Q1 -->|Execute an existing plan —<br>task plan already produced| Execute["/dh:implement-feature {plan path or slug}<br>Loops ready tasks, dispatches agents,<br>calls complete-implementation when all tasks COMPLETE"]

    Q1 -->|Work a single specific task<br>inside an existing plan| Single["/dh:start-task {plan path} --task {task-id}<br>Used by implement-feature per-task dispatch —<br>invoke directly to target one task"]

    Q1 -->|Run quality gates after<br>all tasks are COMPLETE| QG["/dh:complete-implementation {plan path|#N}<br>7-phase SAM path (with plan) or<br>3-phase proportional path (issue only):<br>multi-perspective review → code review →<br>verification → integration →<br>doc drift → doc update → context refinement"]

    Q1 -->|Work a full milestone<br>in parallel isolated worktrees| Milestone["/dh:work-milestone<br>Wave-based parallel execution — each item<br>gets its own worktree. Use /dh:groom-milestone first."]
```

---

## Lifecycle — Creation to Verified Closure

```mermaid
flowchart TD
    Capture["/dh:create-backlog-item<br>Per-item file in ~/.dh/.../backlog/"] --> Groom
    Groom["/dh:groom-backlog-item<br>RT-ICA + impact radius + fact-check<br>Item status: needs-grooming → groomed"] --> Work
    Work["/dh:work-backlog-item<br>Auto-groom gate → RT-ICA gate →<br>SAM planning via /add-new-feature<br>Attaches plan to backlog item"] --> Execute
    Execute["/dh:implement-feature<br>SAM dispatch loop — ready tasks →<br>agents → hooks update task status"] --> QG
    QG["/dh:complete-implementation<br>7 quality gate phases → status:verified label<br>Fixes #N commit — issue closure"] --> Done(["Item resolved"])

    Work -.->|item already has Plan field| Execute
    Work -.->|close or resolve mode| Done
```

**Key invariants derived from the skill sources:**

- `/dh:work-backlog-item` stops immediately when the item already has a `Plan` field — use `/dh:implement-feature` instead
- `/dh:work-backlog-item` stops at the RT-ICA gate when MISSING conditions remain unresolved
- Task-level commits produced during `/dh:implement-feature` must NOT include `Fixes #N` — that trailer is reserved for the final commit in `/dh:complete-implementation`
- The `status:verified` label applied by `/dh:complete-implementation` is a prerequisite for `/dh:work-backlog-item resolve`

---

## Quick Decision Reference

| Situation | Skill |
|---|---|
| Item does not exist yet | `/dh:create-backlog-item` |
| Item exists, not yet groomed | `/dh:groom-backlog-item {title}` |
| Item is groomed, no plan yet | `/dh:work-backlog-item {title}` |
| Item has a Plan field | `/dh:implement-feature {plan path or slug}` |
| Plan is executing, one task needs focus | `/dh:start-task {plan} --task {id}` |
| All tasks complete, run quality gates | `/dh:complete-implementation {plan path}` |
| Issue number, no plan | `/dh:complete-implementation #{N}` (proportional gates) |
| Groomed item, skip to planning directly | `/dh:add-new-feature {description}` then `/dh:implement-feature` |
| Full milestone in parallel worktrees | `/dh:groom-milestone` then `/dh:work-milestone` |
| Dismiss without completing | `/dh:work-backlog-item close {title}` |
| Mark completed with evidence | `/dh:work-backlog-item resolve {title}` |
