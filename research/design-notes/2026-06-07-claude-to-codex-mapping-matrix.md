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
- variable translation matrix in `2026-06-08-claude-variable-compatibility-matrix.md`

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
| plugin `.mcp.json` | Codex plugin `mcpServers` | portable in packaging, runtime-dependent in behavior | official Codex docs | set `mcpServers: "./.mcp.json"` when the plugin root includes `.mcp.json`; `.mcp.json` itself should be a direct server map or wrapped `mcp_servers` object, not a top-level `mcpServers` wrapper |
| inline Claude `mcpServers` object | generated root `.mcp.json` + Codex `mcpServers` path | adapt | local `scientific-method`, `development-harness`, `plugin-creator`, `python3-development` | if the Claude manifest carries MCP server definitions inline and no root `.mcp.json` exists, materialize a root `.mcp.json` in Codex’s documented shape and point the Codex manifest at it |
| root `hooks.json` | Codex plugin `hooks` | portable | official Codex docs | set `hooks: "./hooks.json"` when hooks live at the plugin root |
| `hooks/hooks.json` | default Codex hook path | portable | official Codex docs | no explicit manifest field required when hooks live at `./hooks/hooks.json` |
| Codex display metadata | `interface` block | Codex-only add | all 3 | add `interface` in Codex even when Claude manifest lacks it |
| repo-level Claude marketplace | repo-level Codex marketplace | adapt | `text-to-cad` | separate marketplace files per runtime are normal |

## Secondary Surfaces

| Surface | Current confidence | Notes |
| --- | --- | --- |
| `skills/` | high | strongest shared concept across runtimes |
| `interface` metadata | high | clearly Codex-specific and present in all qualifying Codex manifests |
| `commands/` | low-medium | needs more repo-backed evidence; likely requires adaptation rather than literal carryover |
| `agents/` | low-medium | `compound-engineering` README says Codex may need extra installation flow for agents |
| `hooks` | medium | officially documented; Codex auto-detects `./hooks/hooks.json`; plugin hooks remain trust-gated at runtime |
| `mcpServers` / `.mcp.json` | medium | officially documented and now wired into local manifests; packaging is straightforward but runtime namespace exposure still needs plugin-by-plugin validation |
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

## Pattern 4: Packaging parity does not guarantee MCP parity

Observed in:

- local `process-siren` validation
- local `frustration-analyzer` validation
- local `scientific-method` validation

Practical rule:

- add `mcpServers: "./.mcp.json"` when present because that is the documented Codex manifest path
- if the Claude manifest stores MCP servers inline, generate a root `.mcp.json` from that inline object for the Codex port
- **Superseded 2026-08-19**: keep the top-level `mcpServers` wrapper in `.mcp.json` — do not
  strip it to a direct server map. The `frustration-analyzer` canonical-manifest fix
  (`f9adf1f8`) established and tested the wrapped shape
  (`tests/test_frustration_analyzer_python_compatibility.py::test_codex_mcp_launcher_...`
  reads `config["mcpServers"]["frustration-analyzer"]`), and every `.mcp.json` shipped in this
  repo (`process-siren`, `development-harness`, `python3-development`, `plugin-creator`,
  `agentskill-kaizen`) now uses the wrapper. `scripts/sync_codex_plugin_manifests.py` was fixed
  to match — it now normalizes `mcp_servers` -> `mcpServers` while preserving the wrapper instead
  of stripping it.
- then validate whether the plugin-scoped MCP namespace actually appears in-session
- if the namespace does not appear, record that as a runtime gap instead of claiming full MCP support

Practical corollary:

- verify the local launcher runtime before blaming plugin packaging
- for this repo, MCP-heavy checks initially failed behind missing or broken executables:
  - `uv` missing from `PATH`
  - `/usr/local/bin/node` and `npx` broken against a missing ICU library
- after re-running with a fixed runtime path, plugin-scoped MCP namespaces still did not surface, which increases confidence that the remaining gap is inside Codex/plugin runtime behavior rather than just local launcher breakage

## Pattern 5: Hook portability has two layers

Observed in:

- official Codex plugin docs
- local `orchestrator-discipline` validation

Practical rule:

- package hooks correctly first:
  - `./hooks/hooks.json` needs no explicit manifest field
  - root `./hooks.json` does need an explicit `hooks` field
- then validate trust/execution separately because Codex does not auto-trust plugin hooks on install

## Current High-Confidence Base Port

For `claude_skills`, the high-confidence first-stage Codex translation is:

1. create `.codex-plugin/plugin.json`
2. preserve shared metadata
3. add `skills: "./skills/"`
4. add a repo or personal Codex marketplace
5. validate install/load/invocation through Codex CLI
6. add `mcpServers` when `.mcp.json` exists
7. add `hooks` only when hooks are not already at the default `./hooks/hooks.json` path

## Open Questions

1. What is the strongest valid mapping for Claude `commands/` into Codex?
2. Which Claude `agents/` concepts are directly portable versus requiring extra installation?
3. What is the best repeatable validation method for proving plugin hook trust and execution?
4. After removing obvious launcher/runtime problems, why do some correctly packaged plugin MCP servers still fail to surface a plugin-scoped namespace in-session?

## Variable Translation Layer

See:

- [2026-06-08-claude-variable-compatibility-matrix.md](/Users/jamienelson/Documents/Codex/2026-06-07/can-you-clone-the-https-github/claude_skills/research/claude-code-plugins/2026-06-08-claude-variable-compatibility-matrix.md:1)

Current high-confidence conclusions:

- `SKILL.md` substitution tokens and process environment variables must be analyzed separately
- `${CLAUDE_SKILL_DIR}` may be useful in skill content, but only as a validated harness-substitution mechanism, not as assumed shell fallback
- `${CLAUDE_PLUGIN_ROOT}` is acceptable mainly for hooks, not as the default skill portability pattern
- `${CLAUDE_PLUGIN_ROOT}` inside `.mcp.json` is a high-risk Codex portability surface and must be runtime-validated
- `CLAUDE_ENV_FILE`, `CLAUDE_CODE_SESSION_ID`, and `CLAUDE_CODE_*` feature flags should be treated as Claude-specific until a Codex-native equivalent is explicitly documented and validated
