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

## Follow-up validation

- 2026-08-13: a copied-and-zipped `development-harness` plugin installed in an isolated
  `CODEX_HOME` and ran from an isolated Git repository.
- Codex invoked `sam_active_task` with `{"action":"get"}` and received
  `{"active_task": null}`.

## Decision

Keep `cwd: "."` and forward `PWD` plus `CODEX_THREAD_ID`. The packaged server needs
the plugin-root working directory for its relative launcher path, while the forwarded
Codex project directory supplies the Git-aware project root. The follow-up validation
proves this two-root configuration for the SAM MCP startup and basic tool call.

Hook execution and a complete Development Harness workflow remain separate validation
work; they are not implied by this MCP result.

## References

- [Codex plugin MCP parser](https://github.com/openai/codex/blob/main/codex-rs/codex-mcp/src/plugin_config.rs) (accessed 2026-08-05)
- [Codex host plugin loader](https://github.com/openai/codex/blob/main/codex-rs/core-plugins/src/loader.rs) (accessed 2026-08-05)
