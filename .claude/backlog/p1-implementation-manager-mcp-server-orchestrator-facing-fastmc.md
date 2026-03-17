---
name: Integrate SAM task operations into backlog MCP server (not standalone)
description: "Integrate SAM task file operations into the backlog MCP server (`.claude/skills/backlog/`) as additional tools — not a standalone FastMCP server.\n\nThe orchestrator currently manages SAM task files through a combination of:\n- CLI calls to `implementation_manager.py` (read-only, single-feature-scoped)\n- Manual Edit/Read tool calls on markdown/YAML task files (error-prone, no state machine)\n- Manual JSON writes for context files (3 separate operations that can partially fail)\n- Zero tracking of delegated subagent work (delegation black hole)\n\n**Architecture direction (revised):** These tools belong in the backlog MCP server alongside issue CRUD, not in a separate MCP server. The backlog MCP already manages GitHub Issues and local file cache — task operations are the same concern at a finer granularity.\n\n**Note:** This item is now scoped to integrating into the existing backlog MCP (`backlog_core/server.py`). If #480 (migrate task tracking to GitHub sub-issues) ships first, some of these tools will query GitHub sub-issues rather than local task files. Coordinate with #480.\n\n## Tools to add to backlog MCP\n\n### Core Query Tools\n- **task_dashboard** — Cross-feature overview: all features, task counts, blockers, in-progress items\n- **task_view** — Single task full detail: acceptance criteria, agent, skills, dependencies, timestamps\n- **task_ready** — Ready tasks for a feature (deps satisfied, not started)\n- **task_dependency_graph** — Which tasks block which, as adjacency list\n\n### Status Mutation Tools\n- **task_transition** — Atomic status change with state machine validation\n- **task_block** — Mark BLOCKED with reason string\n- **task_unblock** — Clear BLOCKED state\n- **task_add_note** — Append timestamped implementation note to a task\n\n### Context & Session Tools\n- **task_claim** — Set active task: writes context file, sets IN PROGRESS, adds Started timestamp (one call instead of three)\n- **task_release** — Inverse of claim: marks COMPLETE, adds Completed timestamp, deletes context file\n- **task_active** — What tasks are currently claimed across all sessions\n\n### Delegation Tracking\n- **task_log_delegation** — Record task delegated to agent Y at time Z\n- **task_log_result** — Record subagent outcome: success/failure, summary, files changed\n- **task_active_agents** — Which tasks have live subagents right now\n\n### Workflow Intelligence\n- **task_next** — Recommend what to work on: dependencies, priority, complexity, in-flight\n- **task_validate** — Structure/frontmatter validation\n- **task_create** — Add follow-up task to existing feature, auto-wired with dependencies\n\n### Explicit exclusions\n- No subagent output tailing\n- No task deletion\n- No auto-scheduling/prioritization\n\n## Implementation Notes\n- Add tools to `.claude/skills/backlog/backlog_core/server.py` using FastMCP v3 (`@mcp.tool` — no parentheses, v3 canonical syntax). Installed version: FastMCP 3.1.0.\n- Reuse `task_format.py` and `implementation_manager.py` as the data layer\n- State machine for task_transition: NOT_STARTED → IN_PROGRESS → COMPLETE, any → BLOCKED, BLOCKED → NOT_STARTED/IN_PROGRESS\n- All tools return structured JSON matching existing CLI output conventions"
metadata:
  topic: implementation-manager-mcp-server-orchestrator-facing-fastmc
  source: Session observation — manual hook fix (#337) revealed systematic tooling gap
  added: '2026-03-01'
  priority: completed
  type: Bug
  status: done
  issue: '#365'
  last_synced: '2026-03-06T05:50:55Z'
---

## Story

As a **developer using Claude Code skills**, I want to **implementation manager mcp server — orchestrator-facing fastmcp server wrapping sam task file operations** so that **the tooling becomes more capable and complete**.

## Description

Build a FastMCP server that exposes SAM task file operations as MCP tools for the orchestrator. Replaces manual CLI invocations, raw file edits, and JSON wrangling with atomic, validated tool calls.

## Problem
The orchestrator currently manages SAM task files through a combination of:
- CLI calls to implementation_manager.py (read-only, single-feature-scoped)
- Manual Edit/Read tool calls on markdown/YAML task files (error-prone, no state machine)
- Manual JSON writes for context files (3 separate operations that can partially fail)
- Zero tracking of delegated subagent work (delegation black hole)

The SubagentStop hook regex bug (fixed in #337) is a symptom: the hook is the sole completion-marking mechanism because no explicit tool exists.

## Proposed MCP Tools

### Core Query Tools (replace CLI + Read gymnastics)
- **task_dashboard** — Cross-feature overview: all features, task counts, blockers, in-progress items. Today queries are one-slug-at-a-time with no bird's-eye view.
- **task_view** — Single task full detail: acceptance criteria, agent, skills, dependencies, timestamps, notes. Today requires Read of whole file + manual scanning.
- **task_ready** — Ready tasks for a feature (deps satisfied, not started). Exists as CLI but requires uv run + JSON parse.
- **task_dependency_graph** — Which tasks block which, as adjacency list or rendered text. Today mentally reconstructed from Dependencies fields.

### Status Mutation Tools (replace manual Edit calls)
- **task_transition** — Atomic status change with state machine validation (e.g. can't go COMPLETE→NOT STARTED). Today raw markdown/YAML edits with no enforcement.
- **task_block** — Mark BLOCKED with a reason string, record who/what blocked it. Today edit status + manually add note, reason often lost.
- **task_unblock** — Clear BLOCKED state, reset to NOT STARTED or IN PROGRESS. No tooling exists.
- **task_add_note** — Append timestamped implementation note to a task. Context lost between sessions; notes in task file would persist.

### Context & Session Tools (replace manual JSON wrangling)
- **task_claim** — Set active task for session: writes context file, sets IN PROGRESS, adds Started timestamp — one call instead of three. Today 3 separate operations that can partially fail.
- **task_release** — Inverse of claim: marks COMPLETE, adds Completed timestamp, deletes context file. Hook does this but fragile — explicit tool is reliable fallback.
- **task_active** — What tasks are currently claimed across all sessions. Today get_task_context.py finds one file with no multi-session awareness.

### Delegation Tracking (doesn't exist at all today)
- **task_log_delegation** — Record: task X delegated to agent Y at time Z with session_id W. Zero tracking today — task disappears until hook fires or doesn't.
- **task_log_result** — Record subagent outcome: success/failure, summary, files changed. Subagent returns text that vanishes at next compaction.
- **task_active_agents** — Which tasks have live subagents right now. No way to know if a background agent is still running or died silently.

### Workflow Intelligence
- **task_next** — Recommend what to work on: considers dependencies, priority, complexity, what's in progress. Today run ready-tasks, mentally sort, check what's in flight — repetitive every loop.
- **task_validate** — Structure/frontmatter validation (exists as CLI, needs MCP wrapping).
- **task_create** — Add follow-up task to existing feature, auto-wired with dependencies. Today manually write markdown matching format.

### Explicit exclusions
- No subagent output tailing (Agent tool already returns results)
- No task deletion (too destructive for autonomous use; use BLOCKED instead)
- No auto-scheduling/prioritization (orchestrator logic, not data layer)

## Implementation Notes
- Add tools to `.claude/skills/backlog/backlog_core/server.py` using FastMCP v3 (`@mcp.tool` — no parentheses). Installed version: FastMCP 3.1.0.
- Reuse existing task_format.py and implementation_manager.py as the data layer
- State machine for task_transition: NOT_STARTED → IN_PROGRESS → COMPLETE, any → BLOCKED, BLOCKED → NOT_STARTED/IN_PROGRESS
- All tools return structured JSON matching existing CLI output conventions

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation — manual hook fix (#337) revealed systematic tooling gap
- **Priority**: P1
- **Added**: 2026-03-01
- **Research questions**: None