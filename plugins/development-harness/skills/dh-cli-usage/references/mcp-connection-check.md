# MCP server connection check

Load `dh:dh-cli-usage` before resolving `<sam_cli/>` or `<dh_scripts/>` below.

You are here because an `mcp__plugin_dh_backlog__*` or `mcp__plugin_dh_sam__*` call failed.

1. Restart the agent session once so the harness reloads its MCP configuration. In Claude Code
   only, when stderr says startup exceeded the MCP timeout, increase `MCP_TIMEOUT` before restarting.

2. If the server is still unavailable, run its diagnostic from the project repository root. Run
   each command separately; do not start both servers in one shell invocation.

   ```bash
   uv run --script "<dh_scripts/>/run_bounded.py" --timeout-seconds 60 -- uvx --from "fastmcp-slim[server]>=4.0.0" fastmcp list --command 'uv run --script "<dh_scripts/>/run_backlog_server.py" --project-dir .' --timeout 45
   ```

   ```bash
   uv run --script "<dh_scripts/>/run_bounded.py" --timeout-seconds 60 -- uvx --from "fastmcp-slim[server]>=4.0.0" fastmcp list --command 'uv run --script "<dh_scripts/>/run_sam_server.py" --project-dir .' --timeout 45
   ```

   Exit 0 with a tool list proves the client completed an MCP handshake. Exit 124, another non-zero
   exit, a traceback, or a server error is the failure signal; preserve that stderr for step 4.

3. Use the CLI for any operation that has one:

   ```bash
   <sam_cli/> plan list
   <sam_cli/> plan status --plan-address P{N}
   <sam_cli/> plan ready --plan-address P{N}
   ```

   Pass addresses and task data as named options; read
   [command reference](./command-reference.md) for the full set. The MCP composites have no CLI
   form.

4. When a server fails to start and the operation has no CLI form, report `STATUS: BLOCKED` with the
   exact command and its stderr, and make no further `mcp__plugin_dh_*` call against that server.
