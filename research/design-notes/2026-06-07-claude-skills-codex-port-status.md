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
| `frustration-analyzer` | skills, agents, mcp | mcp-heavy | yes | no | high | |
| `gitlab-skill` | skills, commands | command-heavy | yes | no | medium | |
| `holistic-linting` | skills, commands, agents | command-heavy | yes | no | medium | |
| `litellm` | skills | skill-only | yes | no | low | |
| `llamafile` | skills | skill-only | yes | no | low | |
| `orchestrator-discipline` | skills, hooks | hook-heavy | yes | no | high | |
| `perl-development` | skills, agents | skills+agents | yes | no | medium | |
| `plugin-creator` | skills, agents | skills+agents | yes | no | medium | |
| `process-siren` | skills, agents, mcp | mcp-heavy | yes | no | high | |
| `python-engineering` | skills, agents | skills+agents | yes | yes | medium | plugin visible and selectable in Codex CLI validation |
| `python3-development` | skills, agents | skills+agents | yes | no | medium | |
| `rtfp` | skills, agents | skills+agents | yes | no | medium | |
| `scientific-method` | skills, agents, hooks, mcp | complex | yes | no | high | |
| `summarizer` | skills, agents, hooks | hook-heavy | yes | no | high | |
| `the-rewrite-room` | skills, commands, agents, hooks | complex | yes | no | high | |
| `twelve-factor-app` | skills | skill-only | yes | no | low | |
| `uv` | skills | skill-only | yes | no | low | |
| `verification-gate` | skills | skill-only | yes | no | low | |
| `xdg-base-directory` | skills | skill-only | yes | no | low | |

## Validation Evidence

### Completed runtime validation

- `python-engineering`
  - marketplace registration: pass
  - plugin listing via Codex CLI: pass
  - install via Codex CLI: pass
  - in-session plugin visibility through `codex exec`: pass
  - expected skill selection (`python3-cli` for Typer CLI request): pass

## Next Suggested Representative Ports

1. skill-only: `verification-gate`
2. skills+agents: `python3-development`
3. command-heavy: `gitlab-skill`
4. hook-heavy: `orchestrator-discipline`
5. mcp-heavy: `process-siren`
