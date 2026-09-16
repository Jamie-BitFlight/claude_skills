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

The development-harness plugin implements the structured development lifecycle for tracked backlog items. It spans capture through verified closure using a chain of skills backed by the configured backlog backend provider as the source of truth and `~/.dh/projects/{slug}/` as the local state directory. The repository's default configuration currently selects GitHub Issues.

**Skills available:** `/dh:work-backlog-item`, `/dh:add-new-feature`, `/dh:implement-feature`, `/dh:complete-implementation`, `/dh:gate-push`, `/dh:work-milestone`

Plugin-level source copies exist at `plugins/development-harness/skills/` for each skill.

---

## Skill Router — "I want to do X"

```mermaid
flowchart TD
    Start([What do you want to do?]) --> Q1{Intent?}

    Q1 -->|Capture new work —<br>bug, feature idea, observation| Create["/dh:work-backlog-item create<br>Modes: guided intake, quick title, --auto title<br>Writes to ~/.dh/projects/{slug}/backlog/"]

    Q1 -->|Prepare an item for planning —<br>verify claims, map impact, estimate effort| Groom["/dh:work-backlog-item groom {title|section|all}<br>RT-ICA + parallel swarm: fact-checker,<br>impact-analyst, rtica-assessor, classifier, groomer<br>Requires: item exists in backlog"]

    Q1 -->|Plan AND execute a backlog item<br>end-to-end through closure| Work["/dh:work-backlog-item {title|#N|--auto}<br>Handles: auto-groom, RT-ICA gate, SAM planning,<br>GitHub sync, close, resolve<br>STOPS if item already has a plan address"]

    Q1 -->|Plan a feature — produce SAM artifacts<br>without executing| Plan["/dh:add-new-feature {feature description}<br>Phases: discovery → codebase analysis →<br>architecture spec → task decomposition →<br>validation → context manifest<br>Output: feature slug + P{id} task plan"]

    Q1 -->|Execute an existing plan —<br>task plan already produced| Execute["/dh:implement-feature {plan address or slug}<br>Loops ready tasks, dispatches agents,<br>calls complete-implementation when all tasks COMPLETE"]

    Q1 -->|Work a single specific task<br>inside an existing plan| Single["/dh:start-task {plan-address} --task {task-id}<br>Used by implement-feature per-task dispatch —<br>invoke directly to target one task"]

    Q1 -->|Run quality gates after<br>all tasks are COMPLETE| QG["/dh:complete-implementation {plan address|#N}<br>7-task SAM path (with plan): multi-perspective review →<br>code review → verification → integration →<br>doc drift → doc update → context refinement<br>or 5-task proportional path (issue only), which omits<br>multi-perspective review and context refinement"]

    Q1 -->|Work a full milestone<br>in parallel isolated worktrees| Milestone["/dh:work-milestone<br>Wave-based parallel execution — each item<br>gets its own worktree. Use /dh:groom-milestone first."]
```

---

## Lifecycle — Creation to Verified Closure

```mermaid
flowchart TD
    Capture["/dh:work-backlog-item create<br>Stores the item in the configured backend<br>(default backend: GitHub issue)<br>Status: needs-grooming"] --> Groom
    Groom["/dh:work-backlog-item groom<br>Swarm: impact-analyst, fact-checker,<br>rtica-assessor, classifier, groomer<br>Status: needs-grooming → groomed"] --> Work
    Work["/dh:work-backlog-item work<br>Status: in-progress → discovery gate →<br>groom check → RT-ICA gate → feasibility gate →<br>dh:add-new-feature → plan address on the item"] -->|auto mode| Execute
    Execute["/dh:implement-feature<br>Work loop per ready task: dispatch →<br>runner runs finish → orchestrator settles →<br>orchestrator accepts or reclaims"] --> QG
    QG["/dh:complete-implementation<br>Quality gate plan (7 tasks; 5 without a plan) →<br>status:verified → final commit with Fixes #N, push →<br>backlog resolve"] --> Done(["Status: done"])

    Work -.->|item already has a plan address| Execute
    Work -.->|interactive mode| Stop(["Stops after planning"])
    Close["/dh:work-backlog-item close<br>Dismiss with a reason"] --> Closed(["Status: closed"])
    Resolve["/dh:work-backlog-item resolve<br>Needs status:verified when the item has a plan"] --> Done
```

**Key invariants:**

- When the item already has a plan address, `/dh:work-backlog-item` runs `/dh:implement-feature` with that address and stops.
- When the RT-ICA gate returns BLOCKED, `/dh:work-backlog-item` sets the item status to `blocked` and stops.
- Only the final commit in `/dh:complete-implementation` carries the `Fixes #N` trailer; task-level commits during `/dh:implement-feature` omit it.
- The SubagentStop hook settles an attempt that the orchestrator did not settle. The hook writes no task status.
- For an item with a plan, `/dh:work-backlog-item resolve` requires the `status:verified` label. The `--force` flag bypasses this check.

---

## Quick Decision Reference

| Situation | Skill |
|---|---|
| Item does not exist yet | `/dh:work-backlog-item create` |
| Item exists, not yet groomed | `/dh:work-backlog-item groom {title}` |
| Item is groomed, no plan yet | `/dh:work-backlog-item {title}` |
| Item has a plan address | `/dh:implement-feature {plan address or slug}` |
| Plan is executing, one task needs focus | `/dh:start-task {plan} --task {id}` |
| All tasks complete, run quality gates | `/dh:complete-implementation {plan address}` |
| Issue number, no plan | `/dh:complete-implementation #{N}` (proportional gates) |
| Groomed item, skip to planning directly | `/dh:add-new-feature {description}` then `/dh:implement-feature` |
| Full milestone in parallel worktrees | `/dh:groom-milestone` then `/dh:work-milestone` |
| Dismiss without completing | `/dh:work-backlog-item close {title}` |
| Mark completed with evidence | `/dh:work-backlog-item resolve {title}` |
