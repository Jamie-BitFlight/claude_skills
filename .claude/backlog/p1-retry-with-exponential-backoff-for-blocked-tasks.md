---
name: Retry with exponential backoff for BLOCKED tasks
description: "Tasks that fail and are marked BLOCKED currently stay BLOCKED permanently. There is no automatic retry path — a human must manually reset the status to NOT STARTED or the task is abandoned for the session.\n\nSymphony's model: each failed worker records an attempt count; the orchestrator schedules a retry with exponential backoff (`min(10000 * 2^(attempt-1), max_retry_backoff_ms)`); on retry, the issue is re-fetched from the tracker — if it's no longer active, the claim is released instead of retrying.\n\n**Proposed behaviour:**\n- Add `RetryCount` and `RetryAfter` fields to task metadata (YAML frontmatter and legacy markdown formats).\n- When task_status_hook.py detects a SubagentStop with no COMPLETE marker, increment RetryCount and set RetryAfter = now + backoff(RetryCount).\n- implementation_manager.py `ready-tasks` command: include tasks where status=BLOCKED, RetryCount < max_retries (default 3), and RetryAfter <= now.\n- implement-feature passes `attempt=N` in the delegation prompt when RetryCount > 0.\n- Max retries configurable; exhausted retries leave task BLOCKED with `max retries exceeded` note.\n\n**Acceptance criteria:**\n- A task that fails is automatically retried up to 3 times with increasing delay.\n- RetryCount and RetryAfter are visible in `implementation_manager.py status` output.\n- After max retries, task stays BLOCKED permanently and is not re-dispatched."
metadata:
  topic: retry-with-exponential-backoff-for-blocked-tasks
  source: 'OpenAI Symphony SPEC.md §8 — failure-driven retry: delay = min(10000 * 2^(attempt-1), max_retry_backoff_ms); default cap 5 min'
  added: '2026-03-06'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#449'
  last_synced: '2026-03-12T12:48:23Z'
---

## Story

As a **developer using Claude Code skills**, I want to **retry with exponential backoff for blocked tasks** so that **the tooling becomes more capable and complete**.

## Description

Tasks that fail and are marked BLOCKED currently stay BLOCKED permanently. There is no automatic retry path — a human must manually reset the status to NOT STARTED or the task is abandoned for the session.

Symphony's model: each failed worker records an attempt count; the orchestrator schedules a retry with exponential backoff (`min(10000 * 2^(attempt-1), max_retry_backoff_ms)`); on retry, the issue is re-fetched from the tracker — if it's no longer active, the claim is released instead of retrying.

**Proposed behaviour:**
- Add `RetryCount` and `RetryAfter` fields to task metadata (YAML frontmatter and legacy markdown formats).
- When task_status_hook.py detects a SubagentStop with no COMPLETE marker, increment RetryCount and set RetryAfter = now + backoff(RetryCount).
- implementation_manager.py `ready-tasks` command: include tasks where status=BLOCKED, RetryCount < max_retries (default 3), and RetryAfter <= now.
- implement-feature passes `attempt=N` in the delegation prompt when RetryCount > 0.
- Max retries configurable; exhausted retries leave task BLOCKED with `max retries exceeded` note.

**Acceptance criteria:**
- A task that fails is automatically retried up to 3 times with increasing delay.
- RetryCount and RetryAfter are visible in `implementation_manager.py status` output.
- After max retries, task stays BLOCKED permanently and is not re-dispatched.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: OpenAI Symphony SPEC.md §8 — failure-driven retry: delay = min(10000 * 2^(attempt-1), max_retry_backoff_ms); default cap 5 min
- **Priority**: P1
- **Added**: 2026-03-06
- **Research questions**: None
