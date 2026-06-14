# Codex Plugin Usability Orchestration

Date: 2026-06-13

Goal: make the existing `plugins/` packages as usable as possible in Codex while preserving Claude Code compatibility and avoiding undocumented compatibility shims.

## Operating Contract

Codex usability is judged from the distributed plugin directory, not from the surrounding source repository. A plugin must work after being copied or unzipped as a standalone directory and installed from a Codex marketplace entry.

Codex-facing files must use Codex-documented surfaces only:

| Surface | Codex-native rule |
| --- | --- |
| Manifest | `.codex-plugin/plugin.json` is the Codex manifest. |
| Skills | Use the manifest `skills` field to point at the bundled skills directory. Skills must remain useful after Codex loads their `SKILL.md` through progressive disclosure. |
| Hooks | Use Codex hook packaging conventions only. Root `hooks.json` needs an explicit manifest path; `hooks/hooks.json` is the default convention. Hook execution and trust must be validated separately from packaging. |
| MCP | Use Codex plugin `mcpServers` manifest configuration only. User policy controls live under Codex plugin MCP configuration, not Claude config. |
| Variables | Do not invent custom compatibility variables. Do not assume `CLAUDE_*` variables exist in Codex. Distinguish harness-substituted skill text from process environment variables. |
| Commands and agents | Treat Claude commands and Claude agents as separate concepts. Map them to Codex only when a documented Codex surface exists; otherwise document degraded behavior. |

## Definition Of Done

Each plugin gets a status from an isolated Codex install test:

| Status | Meaning |
| --- | --- |
| `works` | Core plugin workflow loads and runs through Codex from a standalone copied/unzipped plugin. |
| `works-with-degradation` | Codex skill workflow works, but a Claude-only surface such as agents, commands, hooks, or MCP is explicitly unavailable or reduced. |
| `packaged-only` | Codex can install and list the plugin, but the core workflow has not been proven usable. |
| `blocked` | A required capability cannot be mapped to documented Codex behavior or cannot run in the current environment. |

A plugin cannot be marked `works` unless its core path is validated outside the repository, without manually reading its `SKILL.md` by path or relying on repo-relative files.

## Validation Harness Requirements

The repeatable validation path must:

1. Copy only the plugin directory into a temporary marketplace tree.
2. Optionally zip and unzip the plugin before installation to simulate distribution.
3. Register a temporary Codex marketplace pointing at that isolated tree.
4. Install the plugin by marketplace name.
5. Start `codex exec` from an unrelated temporary project directory.
6. Ask a prompt that should trigger the plugin skill naturally.
7. Record whether skills, hooks, MCP servers, and degraded surfaces are actually available.

The validation prompt must forbid manual workaround behavior such as reading the plugin source path directly.

## Active Subagents

Status: complete. Results are consolidated in `2026-06-13-codex-plugin-inventory-matrix.md`.

| Agent | Scope | Expected output |
| --- | --- | --- |
| Volta | Official Codex plugin distribution contract | Documented facts and bounded inferences for manifests, skills, hooks, MCP, variables, and validation. |
| Sagan | Dual Claude/Codex reference repository census | Star-sorted qualifying repos with both `.claude-plugin/` and `.codex-plugin/`, plus mapping observations. |
| Avicenna | Inventory batch A | `agentskill-kaizen`, `gitlab-skill`, `bash-development`, `holistic-linting`, `commitlint`. |
| Kepler | Inventory batch B | `scientific-method`, `clang-format`, `rtfp`, `dot-dash`, `brainstorming-skill`. |
| Lagrange | Inventory batch C | `process-siren`, `perl-development`, `development-harness`, `xdg-base-directory`, `llamafile`. |
| Leibniz | Inventory batch D | `uv`, `agent-orchestration`, `the-rewrite-room`, `python3-development`, `plugin-creator`. |

## Queued Subagents

Status: complete. These batches ran after the first wave freed the agent pool.

These batches are queued because the active agent pool is capped:

| Batch | Scope |
| --- | --- |
| E | `frustration-analyzer`, `orchestrator-discipline`, `conventional-commits`, `dasel`, `twelve-factor-app`. |
| F | `python-engineering`, `litellm`, `summarizer`, `fastmcp-creator`, `verification-gate`. |

## Validation Harness

Added `scripts/validate_codex_plugin_isolated.py`.

The harness:

1. Copies exactly one plugin into a temporary marketplace tree.
2. Optionally zips and unzips that copied plugin before installation.
3. Writes an isolated `.agents/plugins/marketplace.json`.
4. Uses a temp `CODEX_HOME`.
5. Runs from an unrelated temp project directory.
6. Prints commands by default and executes them only with `--run`.
7. Uses `codex plugin add`, matching the installed CLI.

Verified locally:

```bash
python3 -m py_compile scripts/validate_codex_plugin_isolated.py
python3 scripts/validate_codex_plugin_isolated.py --help
python3 scripts/validate_codex_plugin_isolated.py --plugin xdg-base-directory --zip-unzip
```

## Local Integration Rules

The main agent owns integration, rebasing, conflict handling, and final acceptance decisions.

Subagents are allowed to gather evidence or make bounded patches only when assigned a disjoint write set. No subagent should edit the same plugin files as another subagent in the same wave.

Do not convert Claude plugin behavior by pattern matching. Every conversion must cite one of:

| Evidence type | Examples |
| --- | --- |
| Official Codex behavior | Codex manual, plugin build docs, installed official plugin examples, Codex source when available. |
| Existing Claude behavior | The plugin's `.claude-plugin/plugin.json`, skills, hooks, commands, agents, scripts, and tests. |
| Runtime validation | Isolated install, `codex exec`, hook firing, MCP namespace/tool visibility, script output. |
| Explicit degradation | A documented note that a Claude-only surface has no verified Codex equivalent. |

## Known Risks To Recheck

| Risk | Required handling |
| --- | --- |
| Claude `!`` command pre-resolution in `SKILL.md` | Do not emulate with shell fallback. If Codex has no documented equivalent, rewrite as explicit instructions or mark degraded. |
| `${CLAUDE_PLUGIN_ROOT}` in skills or MCP config | Do not assume Codex substitution. Prefer skill-local assets/scripts, Codex-documented config, or mark blocked until runtime-proven. |
| `CLAUDE_ENV_FILE`, `CLAUDE_CODE_SESSION_ID`, and Claude feature flags | Treat as Claude-only unless a Codex-native documented equivalent is found. |
| Root-level repo assumptions | Reject if the plugin fails when copied outside this repository. |
| MCP packaging vs MCP runtime availability | Track separately; a manifest field proves packaging only, not usable tools. |
| Hook packaging vs hook execution | Track separately; a manifest field proves packaging only, not trust or firing. |

## Immediate Work Plan

1. Preserve the current worktree and rebase safely from `origin/main`.
2. Finalize the Codex distribution contract from official docs/source evidence.
3. Complete all six plugin inventory batches. Completed in `2026-06-13-codex-plugin-inventory-matrix.md`.
4. Build an isolated plugin validation harness. Completed with `scripts/validate_codex_plugin_isolated.py`.
5. Normalize manifests and `.mcp.json` files only where official Codex packaging supports it.
6. Convert or document Claude-only skill, command, agent, hook, and MCP behavior.
7. Run representative isolated validations first, then finish the remaining plugin matrix.
