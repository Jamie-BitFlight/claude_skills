---
name: ARL human-probing - implement skill/agent
description: 'Design exists in `arl-human-probing-design.md`; implementation is missing. Build the skill/agent that probes humans at ARL touchpoints (e.g., when agent blocks on ambiguity, when verification fails). Success: agent can invoke human-probing flow per design; groom-backlog-item integration works.'
metadata:
  topic: arl-human-probing-implement-skillagent
  source: 'GitHub Issue #194'
  added: '2026-03-03'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#194'
  last_synced: '2026-03-12T12:48:38Z'
---

## Story

As a **developer using Claude Code skills**, I want to **arl human-probing: implement skill/agent** so that **the tooling becomes more capable and complete**.

## Description

Design exists in `arl-human-probing-design.md`; implementation is missing. Build the skill/agent that probes humans at ARL touchpoints (e.g., when agent blocks on ambiguity, when verification fails). Success: agent can invoke human-probing flow per design; groom-backlog-item integration works.

## Details

**Suggested location**: New skill under `.claude/skills/` or `plugins/`; design at `.claude/docs/sdlc-layers/arl-meta-layer/arl-human-probing-design.md`

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation — SDLC layer implementation (2026-02-23)
- **Priority**: P2
- **Added**: 2026-02-23
- **Research questions**: None
