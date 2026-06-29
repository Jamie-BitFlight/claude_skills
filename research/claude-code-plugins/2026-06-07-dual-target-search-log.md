---
title: "Dual-Target Plugin Search Log"
---

# Dual-Target Plugin Search Log

Date: 2026-06-07

## Goal

Find public GitHub repositories that:

1. contain both Claude and Codex plugin packaging
2. meet the explicit star threshold of more than 4000 stars
3. are useful as migration references for translating `claude_skills` plugins to Codex

## Acceptance Criteria

A repository qualifies only if all of the following are true:

- GitHub star count is greater than 4000
- the repository contains both `.claude-plugin/` and `.codex-plugin/`
- the dual-target structure is real at the plugin level or nested plugin level, not just mentioned in a README

Nonqualifying repositories may be recorded as fallback references, but they do not satisfy the search goal.

## Methods Used

### 1. API-backed repository search

Used GitHub repository search queries to surface candidates mentioning both Claude and Codex plugin concepts.

This produced noisy results because README text and repo descriptions are much less precise than actual directory structure.

### 2. API-backed repository metadata verification

Used `https://api.github.com/repos/<owner>/<repo>` to verify:

- exact star count
- canonical repo URL
- repo-level metadata

This replaced weak page-snippet star estimates.

### 3. Structural verification via GitHub contents API

Checked repo root contents and, where needed, nested plugin paths for:

- `.claude-plugin/`
- `.codex-plugin/`

### 4. Local clone verification

Cloned shortlisted repositories and used `find` to confirm whether `.codex-plugin/` existed anywhere in the tree, not just at repo root.

This was required because some repos are dual-target only within nested plugin folders.

## Qualifying Repositories

### `obra/superpowers`

- stars: 220395
- dual-target status: yes
- structure: root `.claude-plugin/` and root `.codex-plugin/`
- notes:
  - Codex manifest adds `skills` and `interface`
  - shared `skills/`, `hooks/`, and `assets/`

### `EveryInc/compound-engineering-plugin`

- stars: 20363
- dual-target status: yes
- structure:
  - `plugins/compound-engineering/.claude-plugin/`
  - `plugins/compound-engineering/.codex-plugin/`
  - `plugins/coding-tutor/.claude-plugin/`
  - `plugins/coding-tutor/.codex-plugin/`
- notes:
  - repo root is not itself a Codex plugin
  - nested plugin folders are the relevant migration references
  - README documents Codex-specific installation caveats for agents

### `earthtojake/text-to-cad`

- stars: 5769
- dual-target status: yes
- structure:
  - repo-level `.claude-plugin/marketplace.json`
  - repo-level `.codex-plugin/marketplace.json`
  - `plugins/cad/.claude-plugin/`
  - `plugins/cad/.codex-plugin/`
- notes:
  - useful example of dual marketplaces plus nested plugin packaging

## Rejected Candidates

### Rejected for missing `.codex-plugin/`

- `trailofbits/skills` — 5590 stars
- `phuryn/pm-skills` — 12256 stars
- `wshobson/agents` — no verified Codex plugin directories in the checked clone

### Rejected for star threshold

- `nvk/llm-wiki` — 542 stars
- `duyet/codex-claude-plugins` — 4 stars

### Rejected as Codex-only references

- `openai/plugins` — 2029 stars
- `openai/role-specific-plugins` — 215 stars

These are still useful for Codex-side schema and packaging examples.

## Search Gotchas

- README matches are noisy and must not be treated as structural evidence.
- repo root checks are insufficient for nested plugin collections.
- GitHub code search API requires auth for the queries attempted here, so local cloning and contents API checks are more reliable in this environment.
- exact stars must come from the GitHub API, not search snippets.

## Outcome

The explicit star-threshold search succeeded.

Confirmed qualifying dual-target repos:

1. `obra/superpowers`
2. `EveryInc/compound-engineering-plugin`
3. `earthtojake/text-to-cad`
