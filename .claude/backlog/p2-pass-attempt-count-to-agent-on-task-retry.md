---
name: Pass attempt count to agent on task retry
description: "When implement-feature retries a BLOCKED task, the delegated agent receives the same prompt as the first attempt with no signal that this is a retry. The agent has no basis to try a different strategy, ask different questions, or be more conservative.\n\nSymphony passes `attempt` (null on first run, integer on retry) to the Liquid prompt template, and continuation turns receive only continuation guidance — not the full original prompt.\n\n**Proposed behaviour:**\n- When implement-feature dispatches a task with RetryCount > 0, prepend to the delegation prompt:\n  ```\n  This is attempt {N} for task {task_id}. The previous attempt did not complete successfully.\n  Review what was attempted (check git log, modified files) before choosing a new approach.\n  ```\n- For tasks with a previous BLOCKED note (from stall detection or agent failure), include the note text in the retry prompt so the agent knows why it was blocked.\n- Task file: add `LastFailureReason` field populated by the hook or orchestrator on failure.\n\n**Acceptance criteria:**\n- Retry delegation prompt includes attempt number and last failure reason.\n- First-attempt prompts are not modified (no attempt context injected).\n- LastFailureReason is readable in `implementation_manager.py status` output."
metadata:
  topic: pass-attempt-count-to-agent-on-task-retry
  source: 'OpenAI Symphony SPEC.md — prompt template receives `attempt` variable: null on first run, integer on retry; continuation turns receive only continuation guidance, not full original prompt'
  added: '2026-03-06'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#450'
  last_synced: '2026-03-21T03:46:12Z'
---

## Story

As a **developer using Claude Code skills**, I want to **pass attempt count to agent on task retry** so that **the tooling becomes more capable and complete**.

## Description

When implement-feature retries a BLOCKED task, the delegated agent receives the same prompt as the first attempt with no signal that this is a retry. The agent has no basis to try a different strategy, ask different questions, or be more conservative.

Symphony passes `attempt` (null on first run, integer on retry) to the Liquid prompt template, and continuation turns receive only continuation guidance — not the full original prompt.

**Proposed behaviour:**
- When implement-feature dispatches a task with RetryCount > 0, prepend to the delegation prompt:
  ```
  This is attempt {N} for task {task_id}. The previous attempt did not complete successfully.
  Review what was attempted (check git log, modified files) before choosing a new approach.
  ```
- For tasks with a previous BLOCKED note (from stall detection or agent failure), include the note text in the retry prompt so the agent knows why it was blocked.
- Task file: add `LastFailureReason` field populated by the hook or orchestrator on failure.

**Acceptance criteria:**
- Retry delegation prompt includes attempt number and last failure reason.
- First-attempt prompts are not modified (no attempt context injected).
- LastFailureReason is readable in `implementation_manager.py status` output.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: OpenAI Symphony SPEC.md — prompt template receives `attempt` variable: null on first run, integer on retry; continuation turns receive only continuation guidance, not full original prompt
- **Priority**: P2
- **Added**: 2026-03-06
- **Research questions**: None
