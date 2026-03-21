---
name: Extend orchestrator-discipline plugin to gate Edit/Write on skill content files
description: "The orchestrator-discipline plugin's PreToolUse hooks currently exclude .md files from the source file read warning, allowing the orchestrator to freely read and edit SKILL.md and references/*.md files. This creates a gap where the orchestrator bypasses delegation to /skill-creator or content optimizer agents for skill content modifications.\n\nObserved failure (session 2026-03-07): Orchestrator directly edited 4 skill reference files (back-links, cross-links, section merges, file moves) instead of delegating to agents. The hooks did not fire because .md files are in the exclusion list.\n\nNeeded: A new PreToolUse hook on Edit/Write that fires when the target path matches */skills/*/SKILL.md or */skills/*/references/*.md. The hook should inject additionalContext reminding the orchestrator to delegate skill content changes to /plugin-creator:skill-creator or contextual-ai-documentation-optimizer agents. Reading these files for routing decisions should remain allowed — only Edit/Write should be gated."
metadata:
  topic: extend-orchestrator-discipline-plugin-to-gate-editwrite-on-s
  source: Session observation 2026-03-07 — orchestrator bypassed delegation for skill content edits
  added: '2026-03-07'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#507'
  last_synced: '2026-03-21T08:08:21Z'
---

## Story

As a **developer using Claude Code skills**, I want to **extend orchestrator-discipline plugin to gate edit/write on skill content files** so that **the tooling becomes more capable and complete**.

## Description

The orchestrator-discipline plugin's PreToolUse hooks currently exclude .md files from the source file read warning, allowing the orchestrator to freely read and edit SKILL.md and references/*.md files. This creates a gap where the orchestrator bypasses delegation to /skill-creator or content optimizer agents for skill content modifications.

Observed failure (session 2026-03-07): Orchestrator directly edited 4 skill reference files (back-links, cross-links, section merges, file moves) instead of delegating to agents. The hooks did not fire because .md files are in the exclusion list.

Needed: A new PreToolUse hook on Edit/Write that fires when the target path matches */skills/*/SKILL.md or */skills/*/references/*.md. The hook should inject additionalContext reminding the orchestrator to delegate skill content changes to /plugin-creator:skill-creator or contextual-ai-documentation-optimizer agents. Reading these files for routing decisions should remain allowed — only Edit/Write should be gated.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation 2026-03-07 — orchestrator bypassed delegation for skill content edits
- **Priority**: P1
- **Added**: 2026-03-07
- **Research questions**: None
