---
name: Meta-Process Capture — Expert Panel Dataset Builder
description: "Document the multi-agent expert panel methodology as a reusable system for building datasets that inform skills and systems. The process — assign framework experts to repositories, ask structured questions, cross-examine, synthesize, map to requirements, validate — produced high-quality sourced findings. Capture this as a repeatable pattern.\n**Key elements to document**:\n- Expert assignment protocol (one agent per source repo, source-code-only evidence standard)\n- Question group design (themed questions → cross-examination → synthesis)\n- Cross-examination as adversarial validation (experts challenge each other's claims)\n- Phased output (discussion → requirement mapping → synthesis → validation)\n- Traceability chain (claim → expert citation → file:line evidence)\n- Session continuity handling (state file enables cross-session resumption)\n**Input artifacts**: `plugins/plugin-creator/skills/assessor/references/ARL/ARL-agent-instructions.md`, `qa-expert-panel.md`"
metadata:
  topic: meta-process-capture-expert-panel-dataset-builder
  source: ARL expert panel process (sessions 2026-02-12 to 2026-02-13)
  added: '2026-02-13'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#90'
  plan: ''
  last_synced: '2026-03-12T12:49:00Z'
---

## Story

As a **developer using Claude Code skills**, I want to **meta-process capture — expert panel dataset builder** so that **the tooling becomes more capable and complete**.

## Description

Document the multi-agent expert panel methodology as a reusable system for building datasets that inform skills and systems. The process — assign framework experts to repositories, ask structured questions, cross-examine, synthesize, map to requirements, validate — produced high-quality sourced findings. Capture this as a repeatable pattern.
**Key elements to document**:
- Expert assignment protocol (one agent per source repo, source-code-only evidence standard)
- Question group design (themed questions → cross-examination → synthesis)
- Cross-examination as adversarial validation (experts challenge each other's claims)
- Phased output (discussion → requirement mapping → synthesis → validation)
- Traceability chain (claim → expert citation → file:line evidence)
- Session continuity handling (state file enables cross-session resumption)
**Input artifacts**: `plugins/plugin-creator/skills/assessor/references/ARL/ARL-agent-instructions.md`, `qa-expert-panel.md`

## Suggested Location

New skill or methodology document — captures the meta-process, not the ARL content

## Context

- **Source**: ARL expert panel process (sessions 2026-02-12 to 2026-02-13)
- **Priority**: P1
- **Added**: 2026-02-13
- **Research questions**: None
