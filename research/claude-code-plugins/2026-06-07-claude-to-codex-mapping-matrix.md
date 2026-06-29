---
title: "Claude to Codex Plugin Mapping Matrix"
---

# Claude to Codex Plugin Mapping Matrix

Date: 2026-06-07

Status: working draft based on:

- official Codex plugin docs
- `obra/superpowers`
- `EveryInc/compound-engineering-plugin`
- `earthtojake/text-to-cad`

## Evidence Sources

- Codex docs: `https://developers.openai.com/codex/plugins`
- Codex docs: `https://developers.openai.com/codex/plugins/build`
- Qualifying repo: `obra/superpowers`
- Qualifying repo: `EveryInc/compound-engineering-plugin`
- Qualifying repo: `earthtojake/text-to-cad`

## Core Translation Rules

| Claude concept | Codex concept | Status | Evidence | Migration rule |
| --- | --- | --- | --- | --- |
| `.claude-plugin/plugin.json` base metadata | `.codex-plugin/plugin.json` base metadata | portable | all 3 qualifying repos | carry over shared metadata fields directly where valid |
| plugin `name` | plugin `name` | portable | all 3 | preserve exactly |
| plugin `version` | plugin `version` | portable | all 3 | preserve exactly |
| plugin `description` | plugin `description` | portable | all 3 | preserve or refine for Codex |
| `author`, `homepage`, `repository`, `license`, `keywords` | same fields | portable | all 3 | preserve when present |
| plugin `skills` | Codex plugin `skills` | portable | `text-to-cad` Claude already includes `skills`; all Codex manifests include `skills` | set `skills: "./skills/"` when a skills directory exists |
| Codex display metadata | `interface` block | Codex-only add | all 3 | add `interface` in Codex even when Claude manifest lacks it |
| repo-level Claude marketplace | repo-level Codex marketplace | adapt | `text-to-cad` | separate marketplace files per runtime are normal |

## Secondary Surfaces

| Surface | Current confidence | Notes |
| --- | --- | --- |
| `skills/` | high | strongest shared concept across runtimes |
| `interface` metadata | high | clearly Codex-specific and present in all qualifying Codex manifests |
| `commands/` | low-medium | needs more repo-backed evidence; likely requires adaptation rather than literal carryover |
| `agents/` | low-medium | `compound-engineering` README says Codex may need extra installation flow for agents |
| `hooks` | low | not yet grounded by qualifying dual-target repo evidence |
| `mcpServers` / `.mcp.json` | low | supported by Codex docs, but no strong dual-target migration pattern established yet |
| app integrations | low | not yet relevant to `claude_skills` plugin pass |

## Observed Patterns

## Pattern 1: Codex manifest extends a slimmer Claude manifest

Observed in:

- `obra/superpowers`
- `EveryInc/compound-engineering-plugin`
- `earthtojake/text-to-cad`

Practical rule:

- start from the Claude metadata
- add Codex-required or Codex-beneficial fields:
  - `skills`
  - `interface`

## Pattern 2: Dual-target packaging may be nested

Observed in:

- `EveryInc/compound-engineering-plugin`
- `earthtojake/text-to-cad`

Practical rule:

- do not assume the repo root is the plugin root
- scan nested `plugins/*` folders for the actual dual-target plugin pairs

## Pattern 3: Codex may need runtime-specific supplement steps

Observed in:

- `EveryInc/compound-engineering-plugin`

Practical rule:

- plugin install success does not prove parity for agents or advanced runtime behavior
- runtime-dependent features need separate validation rows in the tracker

## Current High-Confidence Base Port

For `claude_skills`, the high-confidence first-stage Codex translation is:

1. create `.codex-plugin/plugin.json`
2. preserve shared metadata
3. add `skills: "./skills/"`
4. add a repo or personal Codex marketplace
5. validate install/load/invocation through Codex CLI

## Open Questions

1. What is the strongest valid mapping for Claude `commands/` into Codex?
2. Which Claude `agents/` concepts are directly portable versus requiring extra installation?
3. What is the Codex-equivalent packaging for hook-heavy Claude plugins?
4. What is the documented and field-tested packaging path for MCP-heavy plugins?
