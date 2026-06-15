---
title: "Claude Skills to Codex Port Status"
---

# Claude Skills to Codex Port Status

Date: 2026-06-07

Legend:

- `base-port`: Codex manifest + marketplace path exist
- `runtime-validated`: verified via Codex CLI install/load/invocation
- `needs-deeper-port`: plugin contains commands, hooks, agents, or MCP that need more than the base port

Important QA correction:

- Auto-selection based on a skill description is not core compatibility proof.
- Plausible domain answers are not proof that a skill loaded.
- Core skill validation must be based on explicit named-skill activation in an isolated Codex session, with no manual `SKILL.md` reads.
- Skills that require chained loads are not fully validated unless that chain actually completes.

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
| `frustration-analyzer` | skills, agents, mcp | mcp-heavy | yes | no | high | named-skill injection observed, but MCP tool namespace was absent and Codex fell back to manual file reads; source `.mcp.json` is now rewritten to relative path + `cwd`, but no-workaround runtime revalidation is still pending |
| `gitlab-skill` | skills, commands | command-heavy | yes | yes | medium | plugin visible and selectable in Codex CLI validation |
| `holistic-linting` | skills, commands, agents | command-heavy | yes | no | medium | |
| `litellm` | skills | skill-only | yes | no | low | |
| `llamafile` | skills | skill-only | yes | no | low | |
| `orchestrator-discipline` | skills, hooks | hook-heavy | yes | no | high | packaging passes without manifest `hooks`, but isolated Codex `exec` still did not fire plugin-bundled hooks, even with `--enable plugin_hooks` |
| `perl-development` | skills, agents | skills+agents | yes | no | medium | |
| `plugin-creator` | skills, agents | skills+agents | yes | no | medium | |
| `process-siren` | skills, agents, mcp | mcp-heavy | yes | no | high | plugin visible in Codex, but plugin-scoped MCP namespace still not exposed in-session |
| `python-engineering` | skills, agents | skills+agents | yes | yes | medium | plugin visible and selectable in Codex CLI validation |
| `python3-development` | skills, agents | skills+agents | yes | no | medium | |
| `rtfp` | skills, agents | skills+agents | yes | no | medium | |
| `scientific-method` | skills, agents, hooks, mcp | complex | yes | no | high | plugin visible in Codex, but plugin-scoped MCP namespace still not exposed in-session |
| `summarizer` | skills, agents, hooks | hook-heavy | yes | no | high | |
| `the-rewrite-room` | skills, commands, agents, hooks | complex | yes | no | high | |
| `twelve-factor-app` | skills | skill-only | yes | no | low | |
| `uv` | skills | skill-only | yes | yes | low | repo-marketplace install validated in a temp `CODEX_HOME`; current symlinked layout caused no Codex install/runtime failure |
| `verification-gate` | skills | skill-only | yes | yes | low | isolated zip/copy install validated; plugin selected in Codex and enforced PEP 723 vs `uv sync` alignment |
| `xdg-base-directory` | skills | skill-only | yes | yes | low | isolated zip/copy install validated; Codex answered correct XDG directory mapping from temp install |

## Validation Evidence

### Completed runtime validation

- `python-engineering`
  - marketplace registration: pass
  - plugin listing via Codex CLI: pass
  - install via Codex CLI: pass
  - broader plugin visibility through `codex exec`: pass
  - prior `python3-cli` routing check: informational only; not sufficient under the stricter named-skill activation standard
  - explicit named-skill activation for `python-engineering:orchestrate`: pass
  - exact skill availability confirmation:
    - `Available: yes`
    - `Skill: python-engineering:orchestrate`
  - mandatory chained load check for `python-engineering:orchestrate`: fail
    - `Activated: yes`
    - `SecondarySkillLoaded: no`
    - `SecondarySkill: python-engineering:orchestrating-python-development`
  - conclusion: `python-engineering:orchestrate` is available and activatable in Codex, but its required chained skill load did not complete, so full instruction-chain compatibility is not yet proven

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
  - isolated temp marketplace from copied/zipped plugin directory: pass
  - isolated install with `codex plugin add verification-gate@isolated-codex-plugin-validation`: pass
  - isolated `codex exec` from unrelated temp project: pass
  - Codex selected `verification-gate:verification-gate` and loaded the installed plugin skill from the temp cache: pass
  - expected PEP 723 inline metadata vs `uv sync` misalignment analysis: pass

- `orchestrator-discipline`
  - install via Codex CLI: pass
  - isolated temp `CODEX_HOME`: `/private/tmp/codex-hook-test-home`
  - isolated install via local marketplace: pass
  - isolated `codex exec` forced direct Bash `ls`: pass
  - expected PreToolUse block from plugin hook `prevent-bash-tool-misuse.cjs`: fail
  - trace file `/private/tmp/codex-hook-test.jsonl` showed:
    - command execution for `/usr/local/bin/zsh -lc ls`
    - no hook lifecycle items
  - rerun with `--enable plugin_hooks`: fail
  - trace file `/private/tmp/codex-hook-test-plugin-hooks.jsonl` again showed command execution only
  - conclusion: plugin-bundled hooks are not validated as functional in this Codex CLI path

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
  - current runtime state should be treated as failed until a no-workaround named-skill path exists

- `frustration-analyzer`
  - install via Codex CLI: pass
  - isolated temp `CODEX_HOME`: `/private/tmp/codex-hook-test-home`
  - isolated install via local marketplace: pass
  - named-skill prompt for `frustration-analyzer:rtfp`: injected
    - stderr emitted `codex.skill.injected` warning for `frustration-analyzer:rtfp`
  - MCP namespace visible in-session: fail
    - trace `/private/tmp/codex-rtfp-test.jsonl` showed no native `mcp__frustration-analyzer__...` tool availability
    - the agent called `list_mcp_resources` and got an empty resource list
  - no-workaround validation result: fail
    - the agent manually read cached `SKILL.md` and plugin files to continue
    - under the stricter QA standard this invalidates the run
  - initial effective MCP registration confirmed unresolved placeholder:
    - `codex mcp list` showed `uv run --script ${CLAUDE_PLUGIN_ROOT}/mcp/server.py`
  - direct subprocess env probe in disposable cache:
    - `/private/tmp/plugin-mcp-env.txt`: `PLUGIN_ROOT` and `CLAUDE_PLUGIN_ROOT` both blank
    - `/private/tmp/plugin-mcp-codex-home.txt`: `CODEX_HOME` blank
  - disposable installed-cache rewrite test:
    - rewrote `.mcp.json` to `uv run --script mcp/server.py` with `cwd: "."`
    - `codex mcp list` then showed:
      - `Args`: `run --script mcp/server.py`
      - `Cwd`: plugin cache root under `/private/tmp/codex-hook-test-home/plugins/cache/.../frustration-analyzer/0.2.27/.`
    - direct launcher from that installed cache directory reached dependency resolution and then failed on blocked PyPI access for `tiktoken`
  - conclusion: the original failure is specifically the unresolved `${CLAUDE_PLUGIN_ROOT}` path; Codex locally accepts a relative-path + `cwd` MCP form for this plugin class

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

- `xdg-base-directory`
  - isolated temp marketplace from copied/zipped plugin directory: pass
  - isolated install with `codex plugin add xdg-base-directory@isolated-codex-plugin-validation`: pass
  - isolated `codex exec` from unrelated temp project: pass
  - smoke prompt output included correct XDG defaults:
    - config: `$HOME/.config`
    - data: `$HOME/.local/share`
    - cache: `$HOME/.cache`
    - state: `$HOME/.local/state`
    - runtime: no default; use only when `XDG_RUNTIME_DIR` is set and valid
  - note: this remains a weak validation artifact until re-run as an explicit named-skill activation test

- `uv`
  - install via repo marketplace `jamie-bitflight-skills`: pass
  - isolated temp `CODEX_HOME` containing only the repo marketplace plus `uv`: pass
  - installed plugin root in temp Codex home:
    - `/private/tmp/repo-uv-validate.6ugnEB/codex-home/plugins/cache/jamie-bitflight-skills/uv/2.2.16`
  - fresh `codex exec` from unrelated temp project: pass
  - prompt constrained against source-repo path inspection and sibling-plugin usage: pass
  - Codex produced valid PEP 723 `uv` workflow guidance from that temp install: pass
  - current `plugins/uv/skills/uv -> ../../python3-development/skills/uv` symlink caused no observed Codex install/runtime failure in this repo-marketplace validation: pass
  - note: this proves install/runtime viability, but not explicit named-skill activation provenance; re-run needed under the stricter QA standard

## Runtime Prerequisites and Local Environment Notes

- `uv` was not installed initially; installed successfully to `~/.local/bin` using Astral's installer.
- `/usr/local/bin/node` and `/usr/local/bin/npx` are broken on this machine because they reference a missing ICU library.
- Working replacements already exist at `~/.volta/bin/node` and `~/.volta/bin/npx`.
- Added [with_plugin_runtime_env.sh](/Users/jamienelson/Documents/Codex/2026-06-07/can-you-clone-the-https-github/claude_skills/scripts/with_plugin_runtime_env.sh:1) to standardize plugin validation with:
  - `PATH="$HOME/.local/bin:$HOME/.volta/bin:$PATH"`
- Re-running MCP-heavy validation through that fixed runtime path removed the obvious `uv`/`node` launcher failures, but did not make plugin-scoped MCP namespaces appear in-session.
- Direct isolated probing showed a deeper Codex runtime limitation for plugin-local MCP:
  - `${CLAUDE_PLUGIN_ROOT}` remained literal in `codex mcp list`
  - plugin MCP subprocesses in the tested CLI path did not receive non-empty `PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`, or `CODEX_HOME`
  - current affected repo plugins:
    - `agentskill-kaizen`
    - `development-harness`
    - `frustration-analyzer`
    - `scientific-method`
  - source repo remediation now applied for those four plugins:
    - replaced `${CLAUDE_PLUGIN_ROOT}` script paths in `.mcp.json`
    - now use relative script paths plus `cwd: "."`
  - validator-safe basis:
    - `validate_plugin.py` only enforces that `.mcp.json` contains top-level `mcpServers` and that each server entry is an object
    - the rewrite stayed within those server objects

## Implementation Notes

- Added [sync_codex_plugin_manifests.py](/Users/jamienelson/Documents/Codex/2026-06-07/can-you-clone-the-https-github/claude_skills/scripts/sync_codex_plugin_manifests.py:1) to keep Codex manifests reproducible on this machine.
- Added [with_plugin_runtime_env.sh](/Users/jamienelson/Documents/Codex/2026-06-07/can-you-clone-the-https-github/claude_skills/scripts/with_plugin_runtime_env.sh:1) to validate plugins with a known-good runtime `PATH`.
- Added [validate_codex_plugin_isolated.py](/Users/jamienelson/Documents/Codex/2026-06-07/can-you-clone-the-https-github/claude_skills/scripts/validate_codex_plugin_isolated.py:1) to validate a single plugin from a copied/zipped temp marketplace outside this repository.
- Isolated `codex exec` requires authentication in the temp `CODEX_HOME`; the harness supports explicit `--copy-auth-from-current-home` and cleans the temp home by default.
- Repo-marketplace validation and copied/zipped validation answer different questions:
  - repo-marketplace validation proves Codex can install/use the plugin through the documented marketplace flow
  - copied/zipped validation is an extra portability stress test, not the baseline Codex install model
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
