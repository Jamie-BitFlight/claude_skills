# MCP Server Connection Check

Both `mcp__plugin_dh_backlog__*` and `mcp__plugin_dh_sam__*` tools require their servers to be
connected before use. Agent harnesses normally wait for connecting servers automatically. Apply
this procedure only when the harness reports that a server failed or a tool call returns a
connection error.

1. Inspect the harness's MCP server status. If the DH backlog and SAM servers are connected, rerun
   the original tool call.
2. Restart the agent session so plugin MCP servers restart.
3. If the failure persists, load `dh:dh-cli-usage` and run both source commands below, substituting
   `<dh_scripts/>` from that skill:

   ```text
   uv run --script "<dh_scripts/>/run_sam_server.py"
   uv run --script "<dh_scripts/>/run_backlog_server.py" --project-dir .
   ```

4. If either command reports missing dependencies, run `uv self update` and retry. Each script
   resolves its own PEP 723 dependencies.
5. Check the harness's MCP startup timeout and restore its default when a local override aborts
   startup before either source command initializes.

If a structured SAM operation is needed while the SAM server is unavailable, use the validated
CLI transport. Load `dh:dh-cli-usage`, prefix each line with `<sam_cli/>`, and use named options:

```text
plan list
plan status --plan-address P{N}
plan ready --plan-address P{N}
```

Do not use the retired standalone console script, flat commands, or selectable output-format
flags. Call MCP composites only through connected `mcp__plugin_dh_*` tools.
