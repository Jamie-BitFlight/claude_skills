# Development Harness Codex MCP CWD Validation

## Scope

Validate whether removing `cwd: "."` from the Development Harness MCP configuration
allows its PEP 723 servers to load from an isolated Codex marketplace installation.

## Evidence

- 2026-08-05: `codex plugin add dh@jamie-bitflight-skills` successfully installed
  Development Harness from an isolated marketplace.
- 2026-08-05: a paired, isolated, zip-extracted test held the marketplace,
  installed plugin, Codex prompt, model, and 45-second process bound constant.
  The only changed field was the two DH MCP `cwd` values.
- Control (`cwd: "."`): Codex launched both scripts from the cached plugin root.
  The SAM server exited because GitPython could not find a Git repository from that
  directory. The backlog server started FastMCP but then failed configuration for the
  same missing project root.
- Variant (no `cwd`): Codex launched `uv run --script scripts/run_*_server.py`
  from the agent repository current directory. Those relative paths therefore resolved
  outside the plugin bundle and `uv` attempted the repository project environment,
  which failed while building `cvxopt` before an MCP initialize response.
- The variant agent reported no available DH plan-record tool. The control agent did
  not complete before the fixed process bound, but its captured server stderr identifies
  the startup failure before the MCP handshake.
- Codex source at the inspected `openai/codex` main checkout shows that marketplace
  plugins use `parse_plugin_mcp_config` through the host loader. A relative
  `cwd` is resolved against the plugin root; an omitted `cwd` is left unset.

## Decision

Do not commit the `cwd` removal or an empty `hooks` object. Both edits are reverted
to the existing branch baseline because neither tested configuration produces a usable
DH MCP server.

## Open Design Problem

The standard host-loaded Codex MCP configuration needs both:

1. A plugin-resolved path to the PEP 723 server script.
2. The agent project directory as the MCP process working directory, so DH can resolve
   the active project Git root.

The tested standard `mcpServers` parser resolves relative `cwd` values, but does not
expand relative script arguments against the plugin root when `cwd` is omitted.
Determine the supported Codex mechanism for this two-root requirement before another
configuration change. The next experiment must use a plugin-root-resolved launcher path
while preserving the agent project directory for DH root discovery.

## References

- [Codex plugin MCP parser](https://github.com/openai/codex/blob/main/codex-rs/codex-mcp/src/plugin_config.rs) (accessed 2026-08-05)
- [Codex host plugin loader](https://github.com/openai/codex/blob/main/codex-rs/core-plugins/src/loader.rs) (accessed 2026-08-05)
