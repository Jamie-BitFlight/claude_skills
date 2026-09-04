# Testing MCP Servers Against Fresh Source Code

Built-in MCP tool calls (`mcp__plugin_dh_backlog__*`, `mcp__plugin_dh_sam__*`) run against the **plugin cache**, not the current source. After modifying `backlog_core/` or `sam_schema/`, the cache is stale until a session restart + version bump. To test changes immediately, use `fastmcp` CLI against the source files:

Run all commands from the **project root** (where `pyproject.toml` lives). `$(pwd)` resolves to the project root at execution time.

**Suppress banner noise**: Set `FASTMCP_SHOW_SERVER_BANNER=false` to suppress the startup banner. Set `FASTMCP_LOG_ENABLED=false` to suppress INFO log lines. Both can be combined:

```bash
FASTMCP_SHOW_SERVER_BANNER=false FASTMCP_LOG_ENABLED=false uv run fastmcp call ...
```

SOURCE: [FastMCP Settings docs](https://gofastmcp.com/more/settings) — `FASTMCP_SHOW_SERVER_BANNER` (bool, default true), also controllable via `--no-banner`.

**Backlog server** (`scripts/run_backlog_server.py`):

```bash
# List all tools
FASTMCP_SHOW_SERVER_BANNER=false FASTMCP_LOG_ENABLED=false uv run fastmcp list \
  --command "uv run --script $(pwd)/plugins/development-harness/scripts/run_backlog_server.py"

# View a backlog item (full content)
FASTMCP_SHOW_SERVER_BANNER=false FASTMCP_LOG_ENABLED=false uv run fastmcp call \
  --command "uv run --script $(pwd)/plugins/development-harness/scripts/run_backlog_server.py" \
  --target backlog_view \
  --input-json '{"selector": "groom-milestone", "summary": false}'

# List backlog items (compact — body excluded by default, use fields=["body"] to include)
FASTMCP_SHOW_SERVER_BANNER=false FASTMCP_LOG_ENABLED=false uv run fastmcp call \
  --command "uv run --script $(pwd)/plugins/development-harness/scripts/run_backlog_server.py" \
  --target backlog_list \
  --input-json '{"search": "sdlc", "limit": 3}'
```

**SAM server** (`scripts/run_sam_server.py`):

```bash
# List all tools
FASTMCP_SHOW_SERVER_BANNER=false FASTMCP_LOG_ENABLED=false uv run fastmcp list \
  --command "uv run --script $(pwd)/plugins/development-harness/scripts/run_sam_server.py"

# List all plans
FASTMCP_SHOW_SERVER_BANNER=false FASTMCP_LOG_ENABLED=false uv run fastmcp call \
  --command "uv run --script $(pwd)/plugins/development-harness/scripts/run_sam_server.py" \
  --target sam_plan \
  --input-json '{"config":{"action":"list"}}'
```

**Why `--command` is required**: The server files use relative imports (`from . import models`) and sibling packages (`import dh_paths`). Running `fastmcp call server.py` directly hits an asyncio conflict when invoked from within Claude Code's async context. The `--command` flag launches the runner script as a fresh subprocess, matching how the plugin cache launches the server.

**`--json` output structure**: When using `--json`, fastmcp wraps the result — parse with:

```python
outer = json.loads(stdout)
data = json.loads(outer["content"][0]["text"])
```

**`backlog_list` filter notes**:

- `status` matches workflow labels (e.g. `"status:in-progress"`, `"status:groomed"`), NOT GitHub open/closed state. Passing `"open"` returns zero results.
- `body` is excluded from default list responses. Use `fields=["body"]` to include it, or check `available_fields` in the response for the full list of requestable fields.

**Backend selection during testing**: Prefix `fastmcp call` commands with `BACKLOG_BACKEND=sqlite` or `BACKLOG_BACKEND=memory` to test against a non-GitHub backend without requiring live credentials:

```bash
BACKLOG_BACKEND=memory FASTMCP_SHOW_SERVER_BANNER=false FASTMCP_LOG_ENABLED=false \
uv run fastmcp call \
  --command "uv run --script $(pwd)/plugins/development-harness/scripts/run_backlog_server.py" \
  --target backlog_list \
  --input-json '{}'
```

**When to use this vs built-in MCP calls**: Use `fastmcp call` to verify behavior after editing `backlog_core/` or `sam_schema/` source files. Use built-in MCP calls for normal workflow operations where the cached server is sufficient.
