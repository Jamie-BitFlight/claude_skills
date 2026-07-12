# MCP Server Connection Check

Both `mcp__plugin_dh_backlog__*` and `mcp__plugin_dh_sam__*` tools require their servers
to be connected before use. After a session restart, these servers initialize in
approximately 1–2 seconds:

- `backlog_core.server` full import: ~1.2 s (includes PyGithub, gitpython, ruamel.yaml, tiktoken)
- `sam_schema.server` full import: ~0.8 s (includes pydantic models, tiktoken)
- `tiktoken.get_encoding("cl100k_base")` alone: ~0.14 s (import 0.03 s + encoding load 0.11 s)
- Both servers start in parallel at session startup (Claude Code spawns plugin MCP servers concurrently)

Source: `backlog_core/server.py` line 77, `sam_schema/server.py` line 164.

Measured 2026-07-12 via MCP `initialize` handshake: SAM 0.9–1.0 s, backlog 1.2 s.

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

3. If the problem persists after a session restart, verify the servers can start
   manually:

   ```bash
   uv run --script scripts/run_sam_server.py
   uv run --script scripts/run_backlog_server.py --project-dir .
   ```

   If either exits with `Error: missing dependencies`, ensure `uv` is installed
   and run `uv sync` from the plugin root.

4. Check `MCP_TIMEOUT` — if set too low, Claude Code may abort the connection
   before the server finishes starting. The default is sufficient for these
   servers (~1–2 s startup well within the default timeout).

## SAM CLI Fallback

If the SAM server is unavailable and the task cannot wait, use the `sam` CLI for SAM-only
operations. It is registered as a console script in the `plugins/development-harness`
sub-project (`pyproject.toml` — `sam = "sam_schema.cli:app"`), which is a separate uv
project from the repo root. Running `uv run sam ...` from the repo root fails with
`error: Failed to spawn: 'sam'` because the root project has no such script. For backlog
operations there is no CLI equivalent — the MCP server must be available.

From the repo root, use `--project`:

```bash
uv run --project plugins/development-harness sam list
uv run --project plugins/development-harness sam status P{N}
uv run --project plugins/development-harness sam ready P{N}
```

Or `cd plugins/development-harness` first and drop `--project`:

```bash
cd plugins/development-harness
uv run sam list
uv run sam status P{N}
uv run sam ready P{N}

Note: bare `P{N}` is ambiguous when multiple plans share the same number prefix.
Always use the full `P{N}-{slug}` form (visible in `uv run sam list` output).
