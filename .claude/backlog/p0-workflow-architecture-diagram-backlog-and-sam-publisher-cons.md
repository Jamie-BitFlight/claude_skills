---
name: 'Workflow architecture diagram: backlog and SAM publisher-consumer data flow'
description: 'Create a comprehensive workflow architecture diagram that maps the full backlog and SAM development-harness pipeline. Must track: (1) each node/stage in the workflow (skills, agents, MCP tools, hooks), (2) the data structures each node receives as input and produces as output, (3) how each node transforms or generates data, (4) publisher-consumer relationships between components, (5) state transitions and lifecycle, (6) dependencies between the backlog system (create/groom/work-backlog-item, backlog MCP) and SAM system (add-new-feature, implement-feature, complete-implementation, sam CLI/MCP). Current gap: local-workflow.md has a text data flow but does not track data structure shapes, publisher-consumer edges, or cross-system dependencies. This causes holes in the workflow where components assume inputs that are not produced by any upstream stage.'
metadata:
  topic: workflow-architecture-diagram-backlog-and-sam-publisher-cons
  source: User observation — keeps finding holes in the workflow; dependencies between publishers and consumers are not tracked
  added: '2026-03-21'
  priority: P0
  type: Feature
  status: open
  issue: '#933'
  last_synced: '2026-03-21T08:07:22Z'
---

## Story

As a **developer using Claude Code skills**, I want to **workflow architecture diagram: backlog and sam publisher-consumer data flow** so that **the tooling becomes more capable and complete**.

## Description

Create a comprehensive workflow architecture diagram that maps the full backlog and SAM development-harness pipeline. Must track: (1) each node/stage in the workflow (skills, agents, MCP tools, hooks), (2) the data structures each node receives as input and produces as output, (3) how each node transforms or generates data, (4) publisher-consumer relationships between components, (5) state transitions and lifecycle, (6) dependencies between the backlog system (create/groom/work-backlog-item, backlog MCP) and SAM system (add-new-feature, implement-feature, complete-implementation, sam CLI/MCP). Current gap: local-workflow.md has a text data flow but does not track data structure shapes, publisher-consumer edges, or cross-system dependencies. This causes holes in the workflow where components assume inputs that are not produced by any upstream stage.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: User observation — keeps finding holes in the workflow; dependencies between publishers and consumers are not tracked
- **Priority**: P0
- **Added**: 2026-03-21
- **Research questions**: None

## RT-ICA

## Information Completeness Assessment

**AVAILABLE** (exists in codebase, directly readable):
- `.claude/rules/local-workflow.md` — full text data-flow diagram covering all three phases (add-new-feature, implement-feature, complete-implementation) with agent sequencing and artifact paths
- `plugins/development-harness/backlog_core/models.py` — Pydantic models: `BacklogItem`, `SamTask`, `SamTasksResult`, `ViewItemResult`, `Entry`, `Output`, `IssueStatus`, `PullRequestRef`; TypedDicts: `BranchInfo`, `MergeResult`
- `plugins/development-harness/backlog_core/server.py` — MCP tool signatures: `backlog_add`, `backlog_list`, `backlog_groom`, `backlog_update`, `backlog_view`, `backlog_sync`, `backlog_close`, `backlog_resolve`, `backlog_get_sam_tasks`, `backlog_get_ready_sam_tasks`
- `plugins/development-harness/backlog_core/operations.py` — core operation implementations
- `plugins/development-harness/backlog_core/github.py` — GitHub API integration
- `.claude/docs/TASK_FILE_FORMAT.md` — task YAML frontmatter schema fields

**DERIVABLE** (requires reading code to extract):
- Exact input/output shapes for each MCP tool (derivable from server.py signatures + return dicts)
- Publisher-consumer edges: which node writes each data structure and which node reads it
- State transition table for SAM task lifecycle (NOT STARTED → IN PROGRESS → COMPLETE → BLOCKED)
- Cross-system dependency graph: how backlog item number flows into SAM task `parent_issue_number` field
- Hook trigger conditions and the data flow through `task_status_hook.py`

**MISSING** (requires new work):
- No single diagram currently maps data structure shapes at each edge
- No document maps the publisher-consumer relationships (who produces each artifact, who consumes it)
- No explicit cross-system dependency map showing how `backlog_add` output feeds `swarm-task-planner` input
- T0/TN bookend data structures (`BookendVerification` YAML schema) not documented outside code comments

## Groomed (2026-03-21)

### Impact Radius

Files that need updating when the diagram is created or updated:

**Primary output (new file to create):**
- `.claude/docs/workflow-architecture-diagram.md` — the diagram itself

**Files that may reference or link to the new diagram:**
- `.claude/rules/local-workflow.md` — should gain a link to the new diagram in its Data Flow Diagram section
- `.claude/CLAUDE.md` — may reference the new diagram under SAM workflow documentation
- `plugins/development-harness/CLAUDE.md` — may reference it under Composition Model section
- `plugins/development-harness/backlog_core/README.md` (if exists) — may reference it

**Source files the diagram must accurately reflect (read-only inputs):**
- `plugins/development-harness/backlog_core/models.py` — Pydantic models and TypedDicts
- `plugins/development-harness/backlog_core/server.py` — MCP tool input/output signatures
- `plugins/development-harness/backlog_core/operations.py` — operation implementations
- `plugins/development-harness/backlog_core/github.py` — GitHub sync logic
- `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` — hook triggers and data flow
- `.claude/docs/TASK_FILE_FORMAT.md` — task YAML schema
- `plugins/development-harness/agents/swarm-task-planner.md` — task file generation
- `plugins/python3-development/agents/t0-baseline-capture.md` — T0 baseline YAML schema
- `plugins/python3-development/agents/tn-verification-gate.md` — TN verification YAML schema

### Issue Classification

- **Type:** Docs / Architecture documentation
- **Label:** `type:docs`
- **Category:** Developer tooling — internal workflow documentation
- **Scope:** Cross-system (backlog system + SAM execution system)
- **Audience:** AI agents consuming local-workflow.md and orchestrator-level skills

### Acceptance Criteria

All criteria must be verifiable by reading the produced diagram file.

**AC1 — All nodes identified**
The diagram names every node in the pipeline:
- Backlog system: `backlog_add`, `backlog_list`, `backlog_groom`, `backlog_update`, `backlog_view`, `backlog_sync`, `backlog_get_ready_sam_tasks`, `backlog_get_sam_tasks`
- SAM skills: `/add-new-feature`, `/implement-feature`, `/start-task`, `/complete-implementation`
- Agents: `feature-researcher`, `codebase-analyzer`, `python-cli-design-spec`, `swarm-task-planner`, `plan-validator`, `context-gathering`, `t0-baseline-capture`, `tn-verification-gate`, `code-reviewer`, `feature-verifier`, `integration-checker`, `doc-drift-auditor`, `service-docs-maintainer`, `context-refinement`
- Hooks: `task_status_hook.py` (SubagentStop event), `task_status_hook.py` (PostToolUse event)
- CLI: `sam status`, `sam ready`, `sam claim`, `sam read`, `sam update`

**AC2 — Data structure shapes at each edge**
Every edge in the diagram labels the data structure it carries. Examples:
- `backlog_add` → GitHub Issue: `{file_path, title, priority, issue_number, messages}`
- `sam ready P{N}` → orchestrator: `{ready_tasks: SamTask[], count: int, feature: str}`
- `swarm-task-planner` → task file: YAML frontmatter with `task_id`, `status`, `agent`, `skills`, `dependencies`, `priority`
- `t0-baseline-capture` → `plan/T0-baseline-{slug}.yaml`: per-criterion `{criterion_id, check_command, exit_code, stdout, stderr}`
- `tn-verification-gate` → `plan/TN-verification-{slug}.yaml`: `BookendVerification[]` with `{criterion_id, check_command, t0_exit_code, tn_exit_code, status, stdout_diff_summary}`

**AC3 — Publisher-consumer table**
A table (or equivalent annotation) explicitly lists for each artifact: who creates it (publisher) and who reads it (consumer). Minimum coverage:
- `.claude/backlog/*.md` files
- `plan/feature-context-{slug}.md`
- `plan/architect-{slug}.md`
- `plan/tasks-{N}-{slug}.md`
- `plan/T0-baseline-{slug}.yaml`
- `plan/TN-verification-{slug}.yaml`
- `.claude/context/active-task-{session_id}.json`

**AC4 — SAM task state lifecycle**
The diagram or a companion table shows the full lifecycle of a SAM task's `status` field:
`NOT STARTED` → `IN PROGRESS` (via `sam claim`) → `COMPLETE` (via SubagentStop hook) with `BLOCKED` as an alternate terminal state. Each transition names the actor that triggers it.

**AC5 — Cross-system dependency edge is explicit**
The diagram shows the edge where a backlog item's GitHub issue number becomes the `parent_issue_number` field in the active-task context file and SAM task YAML. The path from `backlog_add` output → `/add-new-feature` → `swarm-task-planner` task generation → `/implement-feature` → `start-task` → context file is traceable in the diagram.

**AC6 — Hook trigger conditions are documented**
Both hook events in `task_status_hook.py` are shown with their trigger conditions:
- `SubagentStop`: fired by `/implement-feature` when sub-agent finishes; reads active-task context file, sets status COMPLETE, deletes context file, syncs to GitHub
- `PostToolUse (Write|Edit|Bash)`: fired by `/start-task` on each tool use; updates `LastActivity` timestamp in task section

**AC7 — Diagram is in Mermaid or structured text**
The diagram uses either Mermaid `flowchart TD` syntax or the existing structured text-tree style already used in `local-workflow.md`. Must render correctly in GitHub markdown (verified by viewing the issue after commit).

### Priority

**P0 — justified.**

AI agents that orchestrate the SAM workflow (e.g., `/implement-feature`, `/start-task`) currently rely on `local-workflow.md` for context. That file documents agent sequencing but does not document data structure shapes at each edge or publisher-consumer relationships. This causes agents to make incorrect assumptions about what fields are available when consuming an artifact — a systematic failure mode observable in sessions where agents pass incomplete data between stages.

The gap is not theoretical: without publisher-consumer documentation, any agent that reads a task file or calls `backlog_get_ready_sam_tasks` must infer field names from incomplete context. The `SamTask` model fields (`task_id`, `feature`, `agent`, `skills`, `dependencies`, `priority`, `status`) and the `SamTasksResult` wrapper shape are only defined in source code, not in agent-facing documentation.

P0 because every implementation task that uses the SAM workflow runs with incomplete information until this is resolved.

### Effort

**Medium** — 3–5 hours of focused agent work.

Breakdown:
- Read and extract data structures from source files (models.py, server.py, task_status_hook.py, TASK_FILE_FORMAT.md): ~1 hour
- Read agent files for T0/TN baseline/verification YAML schemas: ~30 min
- Compose publisher-consumer table: ~30 min
- Draft diagram with labeled edges: ~1–2 hours
- Verify diagram accuracy against source (AC7 check): ~30 min

Single agent can complete in one session. No parallelism required — the work is sequential (read → extract → compose → verify).

No code changes. Output is one new documentation file plus one link update in `local-workflow.md`.

### Dependencies

**No blocking dependencies.** All source files exist and are readable today.

**Soft dependencies (should be stable before diagram is written):**
- `SamTask` Pydantic model fields — if fields are being added/changed by another in-flight item, wait for that to land first to avoid immediate staleness
- `BookendVerification` YAML schema for T0/TN files — defined in agent files; stable as of 2026-03-21
- `task_status_hook.py` hook event handling — stable; no known pending changes

**Upstream reference:**
- `.claude/docs/TASK_FILE_FORMAT.md` must exist and be current (verify before starting)

### Files

**Create:**
- `.claude/docs/workflow-architecture-diagram.md` — primary deliverable: full pipeline diagram with labeled data-structure edges, publisher-consumer table, state lifecycle, and cross-system dependency map

**Update:**
- `.claude/rules/local-workflow.md` — add link to the new diagram in the "Data Flow Diagram" section header

**Read (source of truth, do not modify):**
- `plugins/development-harness/backlog_core/models.py`
- `plugins/development-harness/backlog_core/server.py`
- `plugins/development-harness/backlog_core/operations.py`
- `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py`
- `.claude/docs/TASK_FILE_FORMAT.md`
- `plugins/development-harness/agents/swarm-task-planner.md`
- `plugins/python3-development/agents/t0-baseline-capture.md`
- `plugins/python3-development/agents/tn-verification-gate.md`
