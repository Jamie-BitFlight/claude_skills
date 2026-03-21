---
name: Circuit breaker hook for agent failure loops
description: 'Add a PostToolUseFailure hook that tracks consecutive tool failures. After 3 failures: inject try a different approach guidance. After 5 lifetime trips: escalate to stop and rethink. Catches agent failure loops that our blocker reporting misses. Pattern sourced from Citadel circuit-breaker.js.'
metadata:
  topic: circuit-breaker-hook-for-agent-failure-loops
  source: Citadel assessment .claude/reports/citadel-assessment-20260320.md
  added: '2026-03-21'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#929'
  last_synced: '2026-03-21T08:07:25Z'
---

## Story

As a **developer using Claude Code skills**, I want to **circuit breaker hook for agent failure loops** so that **the tooling becomes more capable and complete**.

## Description

Add a PostToolUseFailure hook that tracks consecutive tool failures. After 3 failures: inject try a different approach guidance. After 5 lifetime trips: escalate to stop and rethink. Catches agent failure loops that our blocker reporting misses. Pattern sourced from Citadel circuit-breaker.js.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Citadel assessment .claude/reports/citadel-assessment-20260320.md
- **Priority**: P1
- **Added**: 2026-03-21
- **Research questions**: None
