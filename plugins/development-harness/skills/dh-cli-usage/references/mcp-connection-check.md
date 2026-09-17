# MCP server connection check

Load `dh:dh-cli-usage` before resolving `<sam_cli/>` or `<dh_scripts/>` below.

You are here because an `mcp__plugin_dh_backlog__*` or `mcp__plugin_dh_sam__*` call failed.

1. Make the failed call once more. A server that was still starting answers on the second call.

2. When it fails again, start each server directly and read what it prints:

   ```bash
   uv run --script "<dh_scripts/>/run_backlog_server.py"
   uv run --script "<dh_scripts/>/run_sam_server.py"
   ```

   Each runs as a long-running stdio server. A process that stays up and prints no error is a
   working server; stop it before you start the next one. On `Error: missing dependencies`, run
   `uv self update` and start it again — each script resolves its own dependencies from its PEP 723
   metadata.

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
