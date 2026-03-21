---
name: 'Mission interview: agentskill-kaizen'
description: "Interview the user with 5 mission statement questions to draft and refine `plugins/agentskill-kaizen/mission.json`.\n\nRun: `/plugin-creator:mission-statement plugins/agentskill-kaizen --interview`\n\n**Q1 — Non-Negotiable:** \"What is the one thing this plugin must never sacrifice, even to ship faster?\"\n\n**Q2 — Bad Twin:** \"What would a superficially similar but wrong version of this plugin do? What makes it wrong?\"\n\n**Q3 — Trade-offs:** \"When forced to choose between breadth vs depth / correctness vs speed / explicit vs implicit — which does this plugin choose, and why?\" (Ask all three. If \"both\", ask \"if you could only have one.\")\n\n**Q4 — Removal Trigger:** \"What would make you remove this plugin from the marketplace entirely?\"\n\n**Q5 — Anti-Pattern Example:** \"Give me a specific example of a fix or improvement this plugin should refuse to make, even if asked.\"\n\nAfter interview: update `mission.json` with answers, set `interview_backlog_item` to this issue number, validate with 3 known past decisions."
metadata:
  topic: mission-interview-agentskill-kaizen
  source: Mission statement development process
  added: '2026-03-07'
  priority: P2
  type: Chore
  status: needs-grooming
  issue: '#523'
  last_synced: '2026-03-21T03:45:53Z'
---

## Story

As a **maintainer of the project infrastructure**, I want to **mission interview: agentskill-kaizen** so that **the project infrastructure stays healthy**.

## Description

Interview the user with 5 mission statement questions to draft and refine `plugins/agentskill-kaizen/mission.json`.

Run: `/plugin-creator:mission-statement plugins/agentskill-kaizen --interview`

**Q1 — Non-Negotiable:** "What is the one thing this plugin must never sacrifice, even to ship faster?"

**Q2 — Bad Twin:** "What would a superficially similar but wrong version of this plugin do? What makes it wrong?"

**Q3 — Trade-offs:** "When forced to choose between breadth vs depth / correctness vs speed / explicit vs implicit — which does this plugin choose, and why?" (Ask all three. If "both", ask "if you could only have one.")

**Q4 — Removal Trigger:** "What would make you remove this plugin from the marketplace entirely?"

**Q5 — Anti-Pattern Example:** "Give me a specific example of a fix or improvement this plugin should refuse to make, even if asked."

After interview: update `mission.json` with answers, set `interview_backlog_item` to this issue number, validate with 3 known past decisions.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Mission statement development process
- **Priority**: P2
- **Added**: 2026-03-07
- **Research questions**: None
