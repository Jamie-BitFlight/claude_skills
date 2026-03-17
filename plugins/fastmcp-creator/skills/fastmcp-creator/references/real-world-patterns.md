# FastMCP v3 Real-World Patterns

Production-proven patterns for structuring, composing, and deploying FastMCP v3 servers — covers server composition, transport bridging, development workflows, CLI integration, and community examples.

SOURCE: <https://gofastmcp.com/patterns/contrib> (accessed 2026-03-05)
SOURCE: <https://gofastmcp.com/patterns/cli> (accessed 2026-03-05)
SOURCE: <https://gofastmcp.com/community/showcase> (accessed 2026-03-05)
SOURCE: `plan/feature-context-fastmcp-creator-v3-overhaul.md` — GitHub usage research (accessed 2026-03-05)

---

## Server Composition with mount() and Namespaces

PATTERN: Build specialized sub-servers and compose them into a main server using `mount()` with namespaces. This is the primary way large codebases organize FastMCP tools.

SOURCE: `plan/feature-context-fastmcp-creator-v3-overhaul.md` — Real-World Usage Patterns (accessed 2026-03-05)

```python
from fastmcp import FastMCP

# Specialized sub-servers
weather_server = FastMCP("WeatherServer")
database_server = FastMCP("DatabaseServer")
auth_server = FastMCP("AuthServer")

@weather_server.tool
def get_temperature(city: str) -> dict:
    """Get current temperature for a city."""
    return {"city": city, "temp": 72}

@database_server.tool
def query_users(limit: int = 10) -> list:
    """Query user records."""
    return []

# Main server composes all sub-servers
main = FastMCP("MainServer")
main.mount(weather_server, namespace="weather")
main.mount(database_server, namespace="db")
main.mount(auth_server, namespace="auth")

# Tools available as: weather_get_temperature, db_query_users, auth_*
```

RULE: Use `namespace=` parameter (not the deprecated `prefix=`). See `./migration.md` for the v2 → v3 rename.

---

## ProxyProvider — Transport Bridging

PATTERN: Use `create_proxy()` to wrap a remote HTTP MCP server behind a local stdio server. Common in enterprise environments where clients only support stdio but servers run over HTTP.

SOURCE: `plan/feature-context-fastmcp-creator-v3-overhaul.md` — Real-World Usage Patterns (accessed 2026-03-05)

```python
from fastmcp.server import create_proxy

# Expose a remote HTTP server as a local stdio server
proxy = create_proxy("http://remote-server.internal/mcp")

if __name__ == "__main__":
    proxy.run()  # runs via stdio by default
```

CONSTRAINT: `FastMCP.as_proxy()` is deprecated in v3 — use `from fastmcp.server import create_proxy` instead.

---

## FileSystemProvider — Hot-Reload Development Pattern

PATTERN: Use `FileSystemProvider` with `reload=True` during development for hot-reload without server restart. Disable reload in production.

SOURCE: `plan/feature-context-fastmcp-creator-v3-overhaul.md` — Real-World Usage Patterns (accessed 2026-03-05)

```python
from fastmcp import FastMCP
from fastmcp.server.providers.filesystem import FileSystemProvider
from pathlib import Path

mcp = FastMCP("DocsServer")

# Development — hot-reload enabled
docs_provider = FileSystemProvider(
    path=Path("./docs"),
    reload=True,
)

# Production — reload disabled
docs_provider = FileSystemProvider(
    path=Path("./docs"),
    reload=False,
)

mcp.add_provider(docs_provider)
```

---

## SkillsProvider — Exposing Skills as MCP Resources

PATTERN: Use `ClaudeSkillsProvider()` to expose `~/.claude/skills/` as MCP resources with `skill://` URIs. Enables sharing skills across Claude/Cursor sessions via an MCP server.

SOURCE: `plan/feature-context-fastmcp-creator-v3-overhaul.md` — Real-World Usage Patterns (accessed 2026-03-05)

```python
from fastmcp import FastMCP
from fastmcp.server.providers.skills import ClaudeSkillsProvider

mcp = FastMCP("SkillsServer")

# Expose ~/.claude/skills/ as skill:// resources
mcp.add_provider(ClaudeSkillsProvider())

if __name__ == "__main__":
    mcp.run()
```

---

## Background Tasks — Long-Running Operations

PATTERN: Use `task=True` for tools that need to run asynchronously in the background. Requires the `fastmcp[tasks]` optional dependency.

SOURCE: `plan/feature-context-fastmcp-creator-v3-overhaul.md` — Real-World Usage Patterns (accessed 2026-03-05)

```bash
pip install "fastmcp[tasks]"
```

```python
from fastmcp import FastMCP

mcp = FastMCP("WorkerServer")

@mcp.tool(task=True)
def process_large_dataset(file_path: str) -> dict:
    """Process a large dataset in the background."""
    # Long-running work — runs via Docket + Redis
    result = heavy_computation(file_path)
    return {"status": "complete", "rows": result}
```

CONSTRAINT: `task=True` is the v3 API. `task=TaskConfig(mode="required")` is the v2 API and does NOT work in v3. See `./migration.md`.

CONSTRAINT: Without `fastmcp[tasks]` installed, `task=True` raises an import error at runtime.

---

## Visibility and Per-Session Feature Gating

PATTERN: Use `ctx.enable_components(tags={"premium"})` to unlock features per session. Combine with `require_scopes` for auth-based access control.

SOURCE: `plan/feature-context-fastmcp-creator-v3-overhaul.md` — Real-World Usage Patterns (accessed 2026-03-05)

```python
from fastmcp import FastMCP, Context
from fastmcp.server.auth import require_scopes

mcp = FastMCP("GatedServer")

@mcp.tool(tags={"premium"})
def premium_analysis(data: str) -> str:
    """Advanced analysis — premium feature."""
    return f"Analysis: {data}"

@mcp.tool
async def unlock_premium(ctx: Context) -> str:
    """Unlock premium features for this session."""
    ctx.enable_components(tags={"premium"})
    return "Premium features unlocked."

@mcp.tool(auth=require_scopes("write"))
def admin_action() -> str:
    """Protected action requiring write scope."""
    return "Done."
```

---

## Prefect Horizon — Managed Deployment

PATTERN: Deploy FastMCP servers to Prefect Horizon via GitHub integration. Free for personal use, no server management required.

SOURCE: `plan/feature-context-fastmcp-creator-v3-overhaul.md` — Real-World Usage Patterns (accessed 2026-03-05)

The deployment workflow:

1. Push your FastMCP server code to a GitHub repository
2. Connect the repo at [app.prefect.io](https://app.prefect.io)
3. Prefect Horizon builds and deploys; provides a public HTTPS URL

Local run command (also used by Horizon):

```bash
fastmcp run server.py:mcp
```

CONSTRAINT: No `.mcpb` packaging in v3 official docs. The Prefect Horizon deployment is the official managed hosting path. See `./deployment.md` for the full deployment reference.

---

## CLI-First Patterns

SOURCE: <https://gofastmcp.com/patterns/cli>

The `fastmcp` CLI enables scripting and automation around MCP servers.

### Discovery Workflow

```bash
# Discover what tools a server provides
fastmcp list server.py
fastmcp list server.py --input-schema
fastmcp list server.py --resources --prompts

# Inspect server structure
fastmcp inspect server.py
fastmcp inspect server.py --format fastmcp --output manifest.json
```

### Scripting with fastmcp call

```bash
# Integrate MCP tools into shell scripts
fastmcp call server.py greet name=World
fastmcp call server.py add a=3 b=4 --json

# Call remote servers
fastmcp call http://api.example.com/mcp search query=python

# Use in pipelines — parse JSON output
fastmcp call server.py get_data --json | jq '.results'
```

### Remote Proxy for LLMs Without MCP Support

```bash
# Run a local proxy to a remote server for stdio-only LLM clients
fastmcp run https://remote-server.com/mcp
```

### Factory Function Pattern

When `fastmcp run` ignores `if __name__ == "__main__"` blocks, use factory functions to run setup code:

```python
from fastmcp import FastMCP

async def create_server() -> FastMCP:
    mcp = FastMCP("MyServer")

    @mcp.tool
    def add(x: int, y: int) -> int:
        return x + y

    # Setup code that runs with fastmcp run
    await mcp.initialize_database()

    return mcp
```

```bash
fastmcp run server.py:create_server
```

### Development Loop

```bash
# Auto-reload on file changes (development)
fastmcp run server.py --reload

# Test with MCP Inspector
fastmcp dev inspector server.py

# Generate install command for CI
fastmcp install stdio server.py --copy
```

---

## Contrib Modules

SOURCE: <https://gofastmcp.com/patterns/contrib>

FastMCP includes a `contrib` package for community-contributed modules that extend functionality beyond the core library.

```python
from fastmcp.contrib import my_module
```

CONSTRAINT: Contrib modules have different stability guarantees than core FastMCP. Changes to core FastMCP may break contrib modules without warnings in the main changelog.

Browse available modules: [github.com/PrefectHQ/fastmcp/tree/main/src/fastmcp/contrib](https://github.com/PrefectHQ/fastmcp/tree/main/src/fastmcp/contrib)

To contribute a module:

1. Create a directory in `src/fastmcp/contrib/`
2. Add tests in `tests/contrib/`
3. Include `README.md` with usage and dependency documentation
4. Submit a pull request

---

## Community Showcase

SOURCE: <https://gofastmcp.com/community/showcase>

Community projects and learning resources:

```text
MCP Dummy Server — educational example with dual-transport implementation
https://github.com/WaiYanNyeinNaing/mcp-dummy-server

FastMCP Discord — community discussion, shared projects
https://discord.gg/uu8dJCgttd

GitHub Discussions — submit showcase projects, share examples
https://github.com/PrefectHQ/fastmcp/discussions
```

---

## Large Server Architecture Patterns

PATTERN: For servers with many tools, group by domain using sub-servers and mount with namespaces. This keeps each domain independently testable.

SOURCE: `plan/feature-context-fastmcp-creator-v3-overhaul.md` — Real-World Usage Patterns (accessed 2026-03-05)

```python
from fastmcp import FastMCP
from fastmcp.client import Client

# Domain-specific sub-servers — independently testable
auth_mcp = FastMCP("Auth")
data_mcp = FastMCP("Data")
admin_mcp = FastMCP("Admin")

# Register tools on sub-servers
@auth_mcp.tool
def login(username: str, password: str) -> dict:
    """Authenticate a user."""
    return {"token": "..."}

@data_mcp.tool
def get_records(limit: int = 10) -> list:
    """Retrieve records."""
    return []

# Compose into main server
main = FastMCP("ProductionServer")
main.mount(auth_mcp, namespace="auth")
main.mount(data_mcp, namespace="data")
main.mount(admin_mcp, namespace="admin")

# Test each domain independently
async def test_auth_domain():
    async with Client(auth_mcp) as client:
        result = await client.call_tool("login", {"username": "u", "password": "p"})
        assert "token" in result.data
```
