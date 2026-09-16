# MCP Server Connection Check

Both `mcp__plugin_dh_backlog__*` and `mcp__plugin_dh_sam__*` tools require their servers
to be connected before use. After a session restart, these servers initialize in
approximately 1–2 seconds, starting in parallel at session startup.

## When to Apply This Procedure

In normal operation you do not need to apply any procedure. Claude Code handles
MCP server connection waiting automatically:

- When **tool search** is enabled (the default), `ToolSearch` internally waits for
  any server that is still connecting before returning results. You do not need
  to poll or retry.
- When tool search is disabled, Claude Code uses the `WaitForMcpServers` tool to
  wait for connecting servers before proceeding.

Apply the troubleshooting steps below only when a server has genuinely failed to
connect — i.e. `/mcp` shows the server as **failed**, or a tool call returns a
connection error (not a transient "still connecting" state).

## Troubleshooting a Failed Server

If a server shows as failed in `/mcp` or tool calls return connection errors:

1. Run `/mcp` in the Claude Code session and check the server status.
   - `plugin:dh:backlog` or `plugin:dh:sam` showing as **connected** → the issue
     is elsewhere; re-run the original tool call.
   - Showing as **failed** → continue to step 2.

2. Restart the Claude Code session. Plugin MCP servers restart automatically.

3. If the problem persists after a session restart, resolve `<dh_scripts/>` through
   `dh:dh-cli-usage`, then verify that both servers can start manually:

   ```bash
   uv run --script "<dh_scripts/>/run_backlog_server.py"
   uv run --script "<dh_scripts/>/run_sam_server.py"
   ```

   Each command starts a long-running stdio server. A clean startup that remains running verifies
   the server; stop it before starting the next command.

   If either exits with `Error: missing dependencies`, each script resolves its own dependencies
   on invocation (PEP 723 inline metadata) — run `uv self update` and retry rather than looking for
   a separate install step.

4. Check `MCP_TIMEOUT` — if set too low, Claude Code may abort the connection
   before the server finishes starting. The default is sufficient for these
   servers (~1–2 s startup well within the default timeout).

## Adapter Selection

If a structured SAM operation is needed and the SAM server is unavailable, use the validated direct script-path CLI.

Using the SAM CLI — prefix each line below with the `<sam_cli/>` value from the skill that sent you
here (this file cannot resolve this plugin's installed root on its own):

```bash
plan list
plan status --plan-address P{N}
plan ready --plan-address P{N}
```

Use named options for addresses and task data. Do not use the retired standalone console script, flat commands, or selectable output-format flags. The MCP composites remain MCP-only and should be called through their connected `mcp__plugin_dh_*` tools.


Resolve `<sam_cli/>` and `<dh_scripts/>` through `dh:dh-cli-usage`.
