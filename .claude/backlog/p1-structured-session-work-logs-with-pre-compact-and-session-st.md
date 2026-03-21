---
name: Structured session work logs with pre-compact and session-start hooks
description: 'The @logging agent exists (.claude/agents/logging.md) and knows how to read transcripts and produce structured work logs (Completed/Decisions/Discovered/Next Steps). But there is no automation to invoke it at the right moments. Three pieces needed: (1) A pre-compact hook that fires the logging agent to snapshot current work into a structured log file before context is lost during compression. (2) A committed log file convention (e.g., .claude/sessions/{date}-{slug}.md) so logs survive across sessions and compressions. (3) A session-start hook that reads the most recent log file and injects it as context so the new session knows what happened. The @logging agent becomes the producer, and the /session-historian skill becomes the consumer that can also search historical logs. Related: backlog item #109 (SAM Audit Trail / Observability) covers broader telemetry — this item is specifically about the agent-facing work log continuity problem.'
metadata:
  topic: structured-session-work-logs-with-pre-compact-and-session-st
  source: Session observation — identified gap in state tracking across compressions and sessions
  added: '2026-02-28'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#317'
  last_synced: '2026-03-21T03:46:21Z'
---

## Story

As a **developer using Claude Code skills**, I want to **structured session work logs with pre-compact and session-start hooks** so that **the tooling becomes more capable and complete**.

## Description

The @logging agent exists (.claude/agents/logging.md) and knows how to read transcripts and produce structured work logs (Completed/Decisions/Discovered/Next Steps). But there is no automation to invoke it at the right moments. Three pieces needed: (1) A pre-compact hook that fires the logging agent to snapshot current work into a structured log file before context is lost during compression. (2) A committed log file convention (e.g., .claude/sessions/{date}-{slug}.md) so logs survive across sessions and compressions. (3) A session-start hook that reads the most recent log file and injects it as context so the new session knows what happened. The @logging agent becomes the producer, and the /session-historian skill becomes the consumer that can also search historical logs. Related: backlog item #109 (SAM Audit Trail / Observability) covers broader telemetry — this item is specifically about the agent-facing work log continuity problem.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation — identified gap in state tracking across compressions and sessions
- **Priority**: P1
- **Added**: 2026-02-28
- **Research questions**: None
