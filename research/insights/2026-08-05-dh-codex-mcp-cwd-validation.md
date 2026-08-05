# Development Harness Codex MCP CWD Validation

## Scope

Validate whether removing `cwd: "."` from the Development Harness MCP configuration
allows its PEP 723 servers to load from an isolated Codex marketplace installation.

## Evidence

- 2026-08-05: `codex plugin add dh@jamie-bitflight-skills` successfully installed
  Development Harness from an isolated marketplace.
- 2026-08-05: an isolated, zip-extracted bundle was installed and invoked with
  `codex exec`. The agent was instructed to use a DH MCP tool without reading plugin
  files.
- Result: Codex reported that DH plan-record MCP tools were unavailable. Only
  `mcp__sequential_thinking__sequentialthinking` loaded. Codex logged MCP handshake
  failures for the two DH stdio server processes.
- Codex source at the inspected `openai/codex` main checkout shows that marketplace
  plugins use `parse_plugin_mcp_config` through the host loader. A relative
  `cwd` is resolved against the plugin root; an omitted `cwd` is left unset.

## Decision

Do not commit the `cwd` removal or an empty `hooks` object. Both edits are reverted
to the existing branch baseline because the tested bundle had no usable DH MCP tools.

## Open Design Problem

The standard host-loaded Codex MCP configuration needs both:

1. A plugin-resolved path to the PEP 723 server script.
2. The agent project directory as the MCP process working directory, so DH can resolve
   the active project Git root.

The tested standard `mcpServers` parser resolves relative `cwd` values, but does not
expand relative script arguments against the plugin root when `cwd` is omitted.
Determine the supported Codex mechanism for this two-root requirement before another
configuration change.

## References

- [Codex plugin MCP parser](https://github.com/openai/codex/blob/main/codex-rs/codex-mcp/src/plugin_config.rs) (accessed 2026-08-05)
- [Codex host plugin loader](https://github.com/openai/codex/blob/main/codex-rs/core-plugins/src/loader.rs) (accessed 2026-08-05)
