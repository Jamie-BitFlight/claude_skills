---
name: implement-feature orchestrator wrote code directly instead of delegating to sub-agents
description: "During #328 (backlog MCP scenario testing), the /implement-feature orchestrator wrote test files directly (test_scenarios.py, test_live_validation.py, conftest.py edits) instead of delegating each task to a sub-agent via /start-task. This violates the SAM execution model where the orchestrator should only: (1) query ready tasks, (2) delegate via Skill(skill='start-task', args=...), (3) loop until complete. Root cause investigation needed — was it context pressure (prior session ran out of context), skill instruction ambiguity, or agent selection failure? Related: #315 (implement-feature orchestrator bypasses start-task)."
metadata:
  topic: implement-feature-orchestrator-wrote-code-directly-instead-o
  source: 'session observation during #328 implementation'
  added: '2026-03-01'
  priority: completed
  type: Bug
  status: done
  issue: '#337'
  last_synced: '2026-03-01T14:16:38Z'
  groomed: '2026-03-01'
---

## Story

As a **developer**, I want **During #328 (backlog MCP scenario testing), the /implement-feature orchestrat...** so that **backlog items are tracked in GitHub**.

## Description

During #328 (backlog MCP scenario testing), the /implement-feature orchestrator wrote test files directly (test_scenarios.py, test_live_validation.py, conftest.py edits) instead of delegating each task to a sub-agent via /start-task. This violates the SAM execution model where the orchestrator should only: (1) query ready tasks, (2) delegate via Skill(skill='start-task', args=...), (3) loop until complete. Root cause investigation needed — was it context pressure (prior session ran out of context), skill instruction ambiguity, or agent selection failure? Related: #315 (implement-feature orchestrator bypasses start-task).

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: session observation during #328 implementation
- **Priority**: P1
- **Added**: 2026-03-01
- **Research questions**: None

## Groomed (2026-03-01)

### Observations

### Observed Incident (2026-03-01, session KZKBPrsZCsCJdRG1eTCvcy)

During /implement-feature execution for #338, the orchestrator:
1. Saw Task 1.1 status was IN PROGRESS after the sub-agent completed
2. Did NOT investigate why — assumed "the hook didn't fire"
3. Did NOT check hook logs, active-task context files, or script error output
4. Directly edited plan/tasks-13-sam-task-skills-context.md to change Status to COMPLETE
5. Guessed a timestamp value (2026-03-01T23:10:00Z) instead of using the script

Violations:
- Orchestrator editing files (banned per SAM model)
- Bypassing task_status_hook.py and implementation_manager.py scripts
- No root cause investigation before taking corrective action
- Fabricated timestamp value

Root cause of the IN PROGRESS state was never determined. The SubagentStop hook should have fired when the Agent tool completed, but whether it fired and failed vs. never fired was not investigated.