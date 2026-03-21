---
name: Add skill composition templates to skill-creator — document patterns for combining multiple skills in compound workflows
description: "## Current state\n\nThe skill-creator skill (plugins/plugin-creator/skills/skill-creator/SKILL.md) documents how to create individual skills but contains no guidance on composing multiple skills into compound workflows. No file in the repository provides skill composition templates or multi-skill workflow examples. Agents creating or using skills have no reference for how to chain skill invocations across domains (e.g., research-curator + backlog + implement-feature as a compound pipeline).\n\nGrep for \"skill-composition\", \"cross-domain\", and \"compound workflow\" across .claude/ returned zero results. The external-pattern-integrator skill handles integrating external patterns into local skills but does not address composing local skills together."
metadata:
  topic: add-skill-composition-templates-to-skill-creator-document-pa
  source: 'Research entry: ./research/skill-generation-tools/claude-scientific-skills.md — pattern: Bundled cross-domain examples showing multi-step workflow composition across skill domains'
  added: '2026-03-16'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#750'
  last_synced: '2026-03-21T03:45:21Z'
---

## Story

As a **developer using Claude Code skills**, I want to **add skill composition templates to skill-creator — document patterns for combining multiple skills in compound workflows** so that **the tooling becomes more capable and complete**.

## Description

## Current state

The skill-creator skill (plugins/plugin-creator/skills/skill-creator/SKILL.md) documents how to create individual skills but contains no guidance on composing multiple skills into compound workflows. No file in the repository provides skill composition templates or multi-skill workflow examples. Agents creating or using skills have no reference for how to chain skill invocations across domains (e.g., research-curator + backlog + implement-feature as a compound pipeline).

Grep for "skill-composition", "cross-domain", and "compound workflow" across .claude/ returned zero results. The external-pattern-integrator skill handles integrating external patterns into local skills but does not address composing local skills together.

## Target state

The skill-creator SKILL.md (or a new references/skill-composition-patterns.md file within the skill-creator skill directory) contains:

1. A "Skill Composition Patterns" section with 2-3 concrete examples showing how to invoke multiple skills in sequence within a single agent workflow
2. Each example names specific skills from this repo (not hypothetical ones) and shows the Skill() invocation sequence
3. Guidance on when to compose skills vs. create a new skill that subsumes the workflow

## Measurable signal

Run: Grep for "Skill Composition" in plugins/plugin-creator/skills/skill-creator/ — at least one match. The matched file contains at least 2 concrete multi-skill workflow examples using Skill() invocations with real skill names from this repo.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Research entry: ./research/skill-generation-tools/claude-scientific-skills.md — pattern: Bundled cross-domain examples showing multi-step workflow composition across skill domains
- **Priority**: P2
- **Added**: 2026-03-16
- **Research questions**: None
