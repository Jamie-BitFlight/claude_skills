---
name: Persistent structured session metadata for cross-session context recovery
description: "**Current state**: The `task_status_hook.py` writes an ephemeral context file at `.claude/context/active-task-{session_id}.json` containing `task_file_path`, `task_id`, and optionally `parent_issue_number`. This file is deleted by the SubagentStop hook when the sub-agent finishes. The `LastActivity` timestamp is written to the task file's YAML frontmatter on each Write/Edit/Bash call. Once a session ends, there is no persistent record of which agent worked on which task, what skills were loaded, how many tool calls were made, or what the agent's final output summary was. Cross-session context recovery relies entirely on reading the task file's status fields and any code changes committed.\n\n**Target state**: The SubagentStop hook, before deleting the active-task context file, appends a structured session summary record to a persistent file at `.claude/context/session-history.jsonl`. Each record contains: `session_id`, `task_id`, `task_file_path`, `agent_type`, `skills_loaded` (list), `started` (ISO timestamp from task), `completed` (ISO timestamp), `last_activity` (ISO timestamp), `parent_issue_number` (if known), and `outcome` (COMPLETE or the final status). This file accumulates across sessions and is never deleted by hooks.\n\n**Measurable signal**: File `.claude/context/session-history.jsonl` exists after at least one SubagentStop event. Each line is valid JSON containing at minimum `session_id`, `task_id`, `agent_type`, `completed`, and `outcome` fields. Running `wc -l .claude/context/session-history.jsonl` returns a count equal to the number of completed sub-agent sessions."
metadata:
  topic: persistent-structured-session-metadata-for-cross-session-con
  source: 'Research entry: ./research/developer-tools/sidecar.md -- pattern: Context Window Recovery via persistent session history'
  added: '2026-03-17'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#775'
  last_synced: '2026-03-21T08:07:38Z'
---

## Story

As a **developer using Claude Code skills**, I want to **persistent structured session metadata for cross-session context recovery** so that **the tooling becomes more capable and complete**.

## Description

**Current state**: The `task_status_hook.py` writes an ephemeral context file at `.claude/context/active-task-{session_id}.json` containing `task_file_path`, `task_id`, and optionally `parent_issue_number`. This file is deleted by the SubagentStop hook when the sub-agent finishes. The `LastActivity` timestamp is written to the task file's YAML frontmatter on each Write/Edit/Bash call. Once a session ends, there is no persistent record of which agent worked on which task, what skills were loaded, how many tool calls were made, or what the agent's final output summary was. Cross-session context recovery relies entirely on reading the task file's status fields and any code changes committed.

**Target state**: The SubagentStop hook, before deleting the active-task context file, appends a structured session summary record to a persistent file at `.claude/context/session-history.jsonl`. Each record contains: `session_id`, `task_id`, `task_file_path`, `agent_type`, `skills_loaded` (list), `started` (ISO timestamp from task), `completed` (ISO timestamp), `last_activity` (ISO timestamp), `parent_issue_number` (if known), and `outcome` (COMPLETE or the final status). This file accumulates across sessions and is never deleted by hooks.

**Measurable signal**: File `.claude/context/session-history.jsonl` exists after at least one SubagentStop event. Each line is valid JSON containing at minimum `session_id`, `task_id`, `agent_type`, `completed`, and `outcome` fields. Running `wc -l .claude/context/session-history.jsonl` returns a count equal to the number of completed sub-agent sessions.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Research entry: ./research/developer-tools/sidecar.md -- pattern: Context Window Recovery via persistent session history
- **Priority**: P1
- **Added**: 2026-03-17
- **Research questions**: None
