---
title: "Claude Skills to Codex Port Status"
---

# Claude Skills to Codex Port Status

Date: 2026-06-07

Legend:

- `base-port`: Codex manifest + marketplace path exist
- `runtime-validated`: verified via Codex CLI install/load/invocation
- `needs-deeper-port`: plugin contains commands, hooks, agents, or MCP that need more than the base port

| Plugin | Components | Migration class | Base port | Runtime validated | Needs deeper port | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `agent-orchestration` | skills | skill-only | yes | no | low | candidate for early validation batch |
| `agentskill-kaizen` | skills, commands, agents, mcp | complex | yes | no | high | likely requires multiple Codex surfaces |
| `bash-development` | skills, agents | skills+agents | yes | no | medium | |
| `brainstorming-skill` | skills | skill-only | yes | no | low | |
| `clang-format` | skills | skill-only | yes | no | low | |
| `commitlint` | skills | skill-only | yes | no | low | |
| `conventional-commits` | skills | skill-only | yes | no | low | |
| `dasel` | skills, agents, hooks | hook-heavy | yes | no | high | |
| `development-harness` | skills, agents, hooks | hook-heavy | yes | no | high | |
| `dot-dash` | skills, hooks | hook-heavy | yes | no | high | |
| `fastmcp-creator` | skills | skill-only | yes | no | low | |
| `frustration-analyzer` | skills, agents, mcp | mcp-heavy | yes | yes | high | plugin visible and selectable in Codex CLI validation; Codex manifest now declares `mcpServers`; plugin-scoped MCP namespace still not exposed in-session |
| `gitlab-skill` | skills, commands | command-heavy | yes | yes | medium | plugin visible and selectable in Codex CLI validation |
| `holistic-linting` | skills, commands, agents | command-heavy | yes | no | medium | |
| `litellm` | skills | skill-only | yes | no | low | |
| `llamafile` | skills | skill-only | yes | no | low | |
| `orchestrator-discipline` | skills, hooks | hook-heavy | yes | yes | high | plugin visible and selectable in Codex CLI validation; root `hooks.json` now mapped explicitly in Codex manifest; hook trust/execution still unverified |
| `perl-development` | skills, agents | skills+agents | yes | no | medium | |
| `plugin-creator` | skills, agents | skills+agents | yes | no | medium | |
| `process-siren` | skills, agents, mcp | mcp-heavy | yes | yes | high | plugin visible and selectable in Codex CLI validation; Codex manifest now declares `mcpServers`; plugin-scoped MCP namespace still not exposed in-session |
| `python-engineering` | skills, agents | skills+agents | yes | yes | medium | plugin visible and selectable in Codex CLI validation |
| `python3-development` | skills, agents | skills+agents | yes | no | medium | |
| `rtfp` | skills, agents | skills+agents | yes | no | medium | |
| `scientific-method` | skills, agents, hooks, mcp | complex | yes | yes | high | plugin visible and selectable in Codex CLI validation; inline Claude MCP config extracted to root `.mcp.json`; plugin-scoped MCP namespace still not exposed in-session |
| `summarizer` | skills, agents, hooks | hook-heavy | yes | no | high | |
| `the-rewrite-room` | skills, commands, agents, hooks | complex | yes | no | high | |
| `twelve-factor-app` | skills | skill-only | yes | no | low | |
| `uv` | skills | skill-only | yes | no | low | |
| `verification-gate` | skills | skill-only | yes | yes | low | plugin visible and selectable in Codex CLI validation |
| `xdg-base-directory` | skills | skill-only | yes | no | low | |

## Validation Evidence

### Completed runtime validation

- `python-engineering`
  - marketplace registration: pass
  - plugin listing via Codex CLI: pass
  - install via Codex CLI: pass
  - in-session plugin visibility through `codex exec`: pass
  - expected skill selection (`python3-cli` for Typer CLI request): pass

- `gitlab-skill`
  - install via Codex CLI: pass
  - in-session plugin visibility through `codex exec`: pass
  - visible skill inventory includes `gitlab-skill:gitlab-skill`: pass
  - expected skill selection for `.gitlab-ci.yml` plus local validation request: pass

- `verification-gate`
  - install via Codex CLI: pass
  - in-session plugin visibility through `codex exec`: pass
  - visible skill inventory includes `verification-gate:verification-gate`: pass
  - expected skill selection for a root-cause verification request: pass

- `orchestrator-discipline`
  - install via Codex CLI: pass
  - in-session plugin visibility through `codex exec`: pass
  - visible skill inventory includes:
    - `orchestrator-discipline:orchestrator-discipline`
    - `orchestrator-discipline:orchestrator-discipline-meta-docs`
  - expected skill selection for orchestrator delegation-discipline request: pass
  - Codex manifest now maps root `hooks.json`: pass
  - hook trust and actual hook firing in-session: unverified

- `process-siren`
  - install via Codex CLI: pass
  - in-session plugin visibility through `codex exec`: pass
  - visible skill inventory includes:
    - `process-siren:improve-processes`
    - `process-siren:mermaids-treasure`
    - `process-siren:woo-sailor`
  - expected skill selection for Mermaid-conversion request: pass
  - Codex manifest now maps `mcpServers` to `./.mcp.json`: pass
  - plugin-scoped MCP namespace visible in-session: fail
  - plugin-scoped MCP namespace still absent after re-running with fixed `PATH` (`~/.local/bin` + `~/.volta/bin`): fail
  - shutdown warnings observed after MCP enable attempt:
    - `failed to initialize MCP client during shutdown: MCP startup failed: timed out handshaking with MCP server after 30s`
    - `failed to initialize MCP client during shutdown: MCP startup failed: handshaking with MCP server failed: connection closed: initialize response`

- `frustration-analyzer`
  - install via Codex CLI: pass
  - in-session plugin visibility through `codex exec`: pass
  - visible skill inventory includes `frustration-analyzer:rtfp`: pass
  - Codex manifest now maps `mcpServers` to `./.mcp.json`: pass
  - plugin-scoped MCP namespace visible in-session: fail
  - plugin-scoped MCP namespace still absent after re-running with fixed `PATH` (`~/.local/bin` + `~/.volta/bin`): fail
  - shutdown warnings observed after MCP enable attempt:
    - `failed to initialize MCP client during shutdown: MCP startup failed: handshaking with MCP server failed: connection closed: initialize response`

- `scientific-method`
  - install via Codex CLI: pass
  - in-session plugin visibility through `codex exec`: pass
  - visible skill inventory includes:
    - `scientific-method:evidence-first-debugging`
    - `scientific-method:experiment-protocol`
    - `scientific-method:scientific-thinking`
  - extracted inline Claude MCP config to root `.mcp.json`: pass
  - Codex manifest now maps `mcpServers` to `./.mcp.json`: pass
  - plugin-scoped MCP namespace visible in-session after reinstall: fail
  - shutdown warnings observed after MCP enable attempt:
    - `failed to initialize MCP client during shutdown: MCP startup failed: handshaking with MCP server failed: connection closed: initialize response`

## Runtime Prerequisites and Local Environment Notes

- `uv` was not installed initially; installed successfully to `~/.local/bin` using Astral's installer.
- `/usr/local/bin/node` and `/usr/local/bin/npx` are broken on this machine because they reference a missing ICU library.
- Working replacements already exist at `~/.volta/bin/node` and `~/.volta/bin/npx`.
- Added [with_plugin_runtime_env.sh](/Users/jamienelson/Documents/Codex/2026-06-07/can-you-clone-the-https-github/claude_skills/scripts/with_plugin_runtime_env.sh:1) to standardize plugin validation with:
  - `PATH="$HOME/.local/bin:$HOME/.volta/bin:$PATH"`
- Re-running MCP-heavy validation through that fixed runtime path removed the obvious `uv`/`node` launcher failures, but did not make plugin-scoped MCP namespaces appear in-session.

## Implementation Notes

- Added [sync_codex_plugin_manifests.py](/Users/jamienelson/Documents/Codex/2026-06-07/can-you-clone-the-https-github/claude_skills/scripts/sync_codex_plugin_manifests.py:1) to keep Codex manifests reproducible on this machine.
- Added [with_plugin_runtime_env.sh](/Users/jamienelson/Documents/Codex/2026-06-07/can-you-clone-the-https-github/claude_skills/scripts/with_plugin_runtime_env.sh:1) to validate plugins with a known-good runtime `PATH`.
- Added [2026-06-08-claude-variable-compatibility-matrix.md](/Users/jamienelson/Documents/Codex/2026-06-07/can-you-clone-the-https-github/claude_skills/research/claude-code-plugins/2026-06-08-claude-variable-compatibility-matrix.md:1) to classify `CLAUDE_*` usage by portability surface and migration rule.
- Normalized existing root `.mcp.json` files from a non-documented top-level `mcpServers` wrapper to the documented direct server-map shape.
- Generated missing root `.mcp.json` files for plugins whose Claude manifests carried inline MCP config:
  - `development-harness`
  - `plugin-creator`
  - `python3-development`
  - `scientific-method`
- Attempted a first variable cleanup pass, then reverted the `SKILL.md` edits after identifying a category error:
  - I had incorrectly mixed harness-side `SKILL.md` substitution with shell-side parameter expansion fallback
  - the reverted files were:
    - `gitlab-skill` self-local preprocessing script example
    - `skill-creator` self-local `init_skill.py` examples

## Next Suggested Representative Ports

1. skills+agents: `python3-development`
2. complex: `agentskill-kaizen`
3. command-heavy: `holistic-linting`
4. hook-heavy follow-up: `development-harness`
