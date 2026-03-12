---
name: Fix agent_frontmatter_keys inconsistency in ecosystem_registry
description: '`plugins/plugin-creator/scripts/ecosystem_registry.py:get_ecosystem_owned_keys()` unions only `skill_frontmatter_keys` across registered ecosystems, ignoring `agent_frontmatter_keys`. The sibling function `get_ecosystem_for_key()` correctly checks both fields. This inconsistency means agent files using ecosystem-owned keys would not be protected by the guard set built from `get_ecosystem_owned_keys()`. Current impact is zero because `agent_frontmatter_keys` is empty for all registered ecosystems, but the data model supports future ecosystems and the inconsistency is a latent correctness bug. The fix should union both fields and update the docstring. A test covering the `agent_frontmatter_keys` branch in `get_ecosystem_for_key()` is also missing and must be added.'
metadata:
  topic: fix-agentfrontmatterkeys-inconsistency-in-ecosystemregistry
  source: Agent task — code review follow-up from plan/tasks-27-multi-ecosystem-plugin-creator-followup-3.md
  added: '2026-03-06'
  priority: P1
  type: Bug
  status: needs-grooming
  plan: plan/tasks-27-multi-ecosystem-plugin-creator-followup-3.md
  issue: '#515'
  last_synced: '2026-03-12T12:48:07Z'
---

## Story

As a **developer using Claude Code skills**, I want to **fix agent_frontmatter_keys inconsistency in ecosystem_registry** so that **the tooling becomes more capable and complete**.

## Description

`plugins/plugin-creator/scripts/ecosystem_registry.py:get_ecosystem_owned_keys()` unions only `skill_frontmatter_keys` across registered ecosystems, ignoring `agent_frontmatter_keys`. The sibling function `get_ecosystem_for_key()` correctly checks both fields. This inconsistency means agent files using ecosystem-owned keys would not be protected by the guard set built from `get_ecosystem_owned_keys()`. Current impact is zero because `agent_frontmatter_keys` is empty for all registered ecosystems, but the data model supports future ecosystems and the inconsistency is a latent correctness bug. The fix should union both fields and update the docstring. A test covering the `agent_frontmatter_keys` branch in `get_ecosystem_for_key()` is also missing and must be added.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Agent task — code review follow-up from plan/tasks-27-multi-ecosystem-plugin-creator-followup-3.md
- **Priority**: P1
- **Added**: 2026-03-06
- **Research questions**: None
