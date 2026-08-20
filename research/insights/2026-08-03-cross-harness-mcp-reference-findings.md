# Cross-Harness MCP Reference Findings

## Purpose

Identify high-uptake public repositories that can inform portable Claude Code
and Codex plugin MCP packaging. This report distinguishes configuration that is
declared in source from a configuration proven to load and execute.

## Evidence Pipeline

1. `scripts/discover_cross_harness_mcp_candidates.py` collected candidates
   from Codex MCP manifest-key searches, fetched stars and forks in GraphQL
   batches, and sorted by stars then forks.
2. `scripts/verify_cross_harness_mcp_structure.py` inspected only repository
   trees for the ordered candidates. It required an aligned Claude manifest,
   Codex manifest, and MCP configuration under the same plugin root.
3. A semantic read inspected the exact manifests and MCP config files for the
   accepted candidates. No plugin was installed or executed.

The first GitHub Code Search query advertised 852 results but returned 846
across every available page. The ranked corpus is therefore marked partial;
the six missing result identities are unknown. Direct user-supplied repositories
are preserved as explicit seeds rather than discarded by that limitation.

Generated artifacts:

- `2026-08-03-cross-harness-mcp-candidate-rankings-with-direct-seeds.json`
- `2026-08-03-cross-harness-mcp-structure-results-with-direct-seeds.json`

## Ranked References

| Rank | Repository | Stars at collection | Structure result | MCP packaging observation |
| --- | --- | ---: | --- | --- |
| 1 | `affaan-m/ECC` | 237,100 | accepted | Root `.mcp.json` is a `mcpServers` wrapper. Codex points to it; Claude declares an empty inline `mcpServers` object. |
| 2 | `thedotmack/claude-mem` | 89,348 | accepted | `plugin/.mcp.json` is a `mcpServers` wrapper. Codex points to it; Claude has no manifest MCP reference. |
| 3 | `MemPalace/mempalace` | 57,992 | rejected | Aligned manifests found, but no bundled MCP config under the aligned root. |
| 4 | `wshobson/agents` | 38,437 | accepted | `plugins/runapi-mcp/.mcp.json` is a `mcpServers` wrapper. Neither paired manifest references it. |
| 5 | `mksglu/context-mode` | 19,569 | rejected | No bundled MCP config under the aligned root. |
| 6 | `yusufkaraaslan/Skill_Seekers` | 14,681 | rejected | No aligned Claude/Codex plugin root with bundled MCP config. |
| 7 | `mrexodia/ida-pro-mcp` | 11,020 | rejected | No bundled MCP config under the aligned root. |
| 8 | `Q00/ouroboros` | 5,253 | accepted | Claude and Codex point to separate root MCP files. |
| 9 | `zhongerxin/Cowart` | 5,217 | rejected | No aligned Claude/Codex plugin root with bundled MCP config. |

## Configuration Patterns

### ECC: shared file referenced by Codex only

- [Claude manifest](https://github.com/affaan-m/ECC/blob/0c1d7be9a750627fb2a6534c78a998cc46d03f9c/.claude-plugin/plugin.json) declares `"mcpServers": {}`.
- [Codex manifest](https://github.com/affaan-m/ECC/blob/0c1d7be9a750627fb2a6534c78a998cc46d03f9c/.codex-plugin/plugin.json) declares `"mcpServers": "./.mcp.json"`.
- [Root config](https://github.com/affaan-m/ECC/blob/0c1d7be9a750627fb2a6534c78a998cc46d03f9c/.mcp.json) uses a top-level `mcpServers` wrapper for `chrome-devtools`.
- [MCP catalog](https://github.com/affaan-m/ECC/blob/0c1d7be9a750627fb2a6534c78a998cc46d03f9c/mcp-configs/mcp-servers.json) is root-contained but neither inspected manifest references it.

This proves the file arrangement exists. It does not prove the Claude plugin
loads the root config, or that either MCP server starts.

### Claude-mem: self-contained Codex reference with a dynamic launcher

- [Claude manifest](https://github.com/thedotmack/claude-mem/blob/b368abaeabfebb8d5cfe18836b779edda204664c/plugin/.claude-plugin/plugin.json) has no `mcpServers` field.
- [Codex manifest](https://github.com/thedotmack/claude-mem/blob/b368abaeabfebb8d5cfe18836b779edda204664c/plugin/.codex-plugin/plugin.json) points to `./.mcp.json`.
- [MCP config](https://github.com/thedotmack/claude-mem/blob/b368abaeabfebb8d5cfe18836b779edda204664c/plugin/.mcp.json) uses `mcpServers` and an inline Node launcher that probes `process.cwd()`, `CLAUDE_PLUGIN_ROOT`, and `PLUGIN_ROOT`.

The config and launcher live under the installable `plugin/` root. The launcher
behavior is declared source, not runtime evidence.

### Wshobson Agents: paired manifests plus unreferenced root config

- [Claude manifest](https://github.com/wshobson/agents/blob/c4b82b0ad771190355eb8e204b1329732a18449a/plugins/runapi-mcp/.claude-plugin/plugin.json) has no `mcpServers` field.
- [Codex manifest](https://github.com/wshobson/agents/blob/c4b82b0ad771190355eb8e204b1329732a18449a/plugins/runapi-mcp/.codex-plugin/plugin.json) has no `mcpServers` field.
- [MCP config](https://github.com/wshobson/agents/blob/c4b82b0ad771190355eb8e204b1329732a18449a/plugins/runapi-mcp/.mcp.json) uses `mcpServers` and `RUNAPI_API_KEY` as a shell environment interpolation.

This is a useful counterexample: presence of a root `.mcp.json` beside paired
manifests does not itself establish that either harness loads it.

### Ouroboros: distinct harness-targeted MCP files

- [Claude manifest](https://github.com/Q00/ouroboros/blob/525a06ab32895e60e6bf789926663387609052ee/.claude-plugin/plugin.json) points to `./.mcp.json`.
- [Claude config](https://github.com/Q00/ouroboros/blob/525a06ab32895e60e6bf789926663387609052ee/.mcp.json) launches `uvx` with `ouroboros-ai[mcp]`.
- [Codex manifest](https://github.com/Q00/ouroboros/blob/525a06ab32895e60e6bf789926663387609052ee/.codex-plugin/plugin.json) points to `./.mcp.codex.json`.
- [Codex config](https://github.com/Q00/ouroboros/blob/525a06ab32895e60e6bf789926663387609052ee/.mcp.codex.json) launches the same command with Codex-specific extras and runtime arguments.

This is the first verified reference in the set where each harness manifest
explicitly points at its own MCP configuration file. It is a source-level
packaging pattern only; no launcher has been executed.

## User-Supplied Architecture References

### Infragate CAPA

[CAPA](https://github.com/infragate/capa/tree/5a48a4c5c79e52ff8ce779d3b769226718b5dd91) is a cross-harness capability
installer and MCP gateway rather than a co-located Claude/Codex plugin bundle.
Its README says `capabilities.yaml` is rendered into provider-native files and
that `capa wrap` supports Claude and Codex. Its tree did not contain the paired
plugin manifests or bundled `.mcp*.json` configuration required for the plugin
packaging comparison.

### Claude Code Harness

[Claude Code Harness](https://github.com/Chachamaru127/claude-code-harness/tree/ef40042c2a340fd5a749f47b66325295f954c2b6)
ships paired manifests and documents Claude Code, Codex CLI, Cursor, and Grok.
Its [Codex manifest](https://github.com/Chachamaru127/claude-code-harness/blob/ef40042c2a340fd5a749f47b66325295f954c2b6/.codex-plugin/plugin.json)
points its skills field at `../codex/.codex/skills/`, outside the plugin root,
and it has no bundled root `.mcp*.json`. It is therefore useful for
cross-harness workflow adaptation, but not as a self-contained MCP plugin
packaging reference.

## Current Conclusion

The inspected set does not support adding both `mcpServers` and `mcp_servers`
to one shared file as a documented cross-harness convention. The observed
source-level arrangements are:

1. one `.mcp.json` with a `mcpServers` wrapper, referenced by Codex only;
2. one `.mcp.json` beside manifests but not referenced by either manifest; and
3. distinct `.mcp.json` and `.mcp.codex.json` files selected by their respective
   manifests.

For a self-contained distributed plugin, the Ouroboros-style explicit
harness-specific config paths are the most directly relevant source pattern.
Before adopting it, the next stage must install a disposable copy through each
harness and verify server registration, startup, and a named tool call.
