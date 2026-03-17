---
name: Research freshness should be a delta indicator, not a blocker
description: "The research-curator skill currently blocks re-research of entries that haven't reached their \"Next Review Recommended\" date. This is wrong — freshness should be informational context (a delta showing how old the data is), not a gate that prevents updates.\n\nExample: everything-claude-code entry was 8 days old (researched 2026-02-26, next review 2026-05-26) but in that time the project shipped TWO major releases (v1.7.0, v1.8.0), gained 10K stars, added new agents and skills, and completely repositioned from \"config bundle\" to \"agent harness performance system\".\n\nChanges needed:\n1. Remove the blocking behavior in the research-curator SKILL.md default mode — always allow re-research\n2. Show freshness as context: \"Entry is N days old (last: YYYY-MM-DD, version X.Y.Z)\" — but proceed\n3. Consider replacing \"Next Review Recommended\" with a staleness indicator that factors in the source's activity level (high-activity repos need more frequent review)\n4. The orchestrator should show the delta and ask \"Entry exists (N days old). Proceeding with refresh.\" rather than stopping"
metadata:
  topic: research-freshness-should-be-a-delta-indicator-not-a-blocker
  source: User observation during /research-curator session 2026-03-06
  added: '2026-03-06'
  priority: completed
  type: Feature
  status: done
  issue: '#444'
  last_synced: '2026-03-06T05:50:49Z'
  plan: plan/tasks-24-research-freshness-delta.md
---

## Story

As a **developer using Claude Code skills**, I want to **research freshness should be a delta indicator, not a blocker** so that **the tooling becomes more capable and complete**.

## Description

The research-curator skill currently blocks re-research of entries that haven't reached their "Next Review Recommended" date. This is wrong — freshness should be informational context (a delta showing how old the data is), not a gate that prevents updates.

Example: everything-claude-code entry was 8 days old (researched 2026-02-26, next review 2026-05-26) but in that time the project shipped TWO major releases (v1.7.0, v1.8.0), gained 10K stars, added new agents and skills, and completely repositioned from "config bundle" to "agent harness performance system".

Changes needed:
1. Remove the blocking behavior in the research-curator SKILL.md default mode — always allow re-research
2. Show freshness as context: "Entry is N days old (last: YYYY-MM-DD, version X.Y.Z)" — but proceed
3. Consider replacing "Next Review Recommended" with a staleness indicator that factors in the source's activity level (high-activity repos need more frequent review)
4. The orchestrator should show the delta and ask "Entry exists (N days old). Proceeding with refresh." rather than stopping

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: User observation during /research-curator session 2026-03-06
- **Priority**: P1
- **Added**: 2026-03-06
- **Research questions**: None