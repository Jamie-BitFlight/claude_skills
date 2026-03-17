# FastMCP v3 Providers Reference

How FastMCP sources components from different origins: local code, mounted servers, remote proxies, filesystems, and skills directories.

SOURCE: <https://gofastmcp.com/servers/providers/overview>, `local.mdx`, `mounting.mdx`, `proxy.mdx`, `filesystem.mdx`, `skills.mdx`, `custom.mdx` (accessed 2026-03-05)

---

## What Is a Provider?

Every FastMCP server has one or more component providers. A provider is a source of tools, resources, and prompts. When a client asks "what tools do you have?", FastMCP queries each provider and combines the results.

`LocalProvider` is always first — components registered via decorators take precedence. Additional providers are queried in registration order.

---

## Built-in Providers

| Provider | What it does | How you use it |
|----------|--------------|----------------|
| `LocalProvider` | Stores components defined in code | `@mcp.tool`, `mcp.add_tool()` |
| `FastMCPProvider` | Wraps another FastMCP server | `mcp.mount(server)` |
| `OpenAPIProvider` | Generates tools/resources from an OpenAPI spec | `FastMCP.from_openapi(spec, client)` |
| `ProxyProvider` | Connects to remote MCP servers | `create_proxy(client)` |
| `FileSystemProvider` | Discovers components in `.py` files | `FastMCP(providers=[FileSystemProvider(...)])` |
| `SkillsDirectoryProvider` | Exposes skill directories as resources | `mcp.add_provider(SkillsDirectoryProvider(...))` |
| `ClaudeSkillsProvider` | Convenience wrapper for `~/.claude/skills/` | `mcp.add_provider(ClaudeSkillsProvider())` |

---

## LocalProvider

`LocalProvider` stores components you define directly using decorators or direct methods. Every `FastMCP` instance has one as its first provider.

```python
from fastmcp import FastMCP

mcp = FastMCP("MyServer")

# All of these store components in the server's LocalProvider
@mcp.tool
def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"

@mcp.resource("data://config")
def get_config() -> str:
    """Return configuration data."""
    return '{"version": "1.0"}'

@mcp.prompt
def analyze(topic: str) -> str:
    """Create an analysis prompt."""
    return f"Please analyze: {topic}"
```

PATTERN: Use `mcp.add_tool()`, `mcp.add_resource()`, and `mcp.add_prompt()` to register pre-built component objects directly.

PATTERN: Create a standalone `LocalProvider` to share components across multiple servers.

```python
from fastmcp.server.providers import LocalProvider

shared_tools = LocalProvider()

@shared_tools.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

server1 = FastMCP("Server1", providers=[shared_tools])
server2 = FastMCP("Server2", providers=[shared_tools])
```

---

## Mounting Servers (FastMCPProvider)

`mcp.mount()` composes multiple servers together. Under the hood, FastMCP creates a `FastMCPProvider` (v3.0.0+) for the mounted server.

```python
from fastmcp import FastMCP

weather_server = FastMCP("Weather")

@weather_server.tool
def get_forecast(city: str) -> str:
    """Get weather forecast for a city."""
    return f"Sunny in {city}"

main = FastMCP("MainApp")
main.mount(weather_server)

# main now exposes get_forecast
```

### Namespacing on Mount

RULE: Use `namespace=` to avoid naming conflicts when mounting multiple servers.

```python
weather = FastMCP("Weather")
calendar = FastMCP("Calendar")

@weather.tool
def get_data() -> str:
    return "Weather data"

@calendar.tool
def get_data() -> str:
    return "Calendar data"

main = FastMCP("Main")
main.mount(weather, namespace="weather")
main.mount(calendar, namespace="calendar")

# Clients see: weather_get_data, calendar_get_data
```

Namespacing transform rules:

| Component | Original | With `namespace="api"` |
|-----------|----------|-------------------------|
| Tool | `my_tool` | `api_my_tool` |
| Prompt | `my_prompt` | `api_my_prompt` |
| Resource | `data://info` | `data://api/info` |
| Template | `data://{id}` | `data://api/{id}` |

### Mounting vs Importing

| Feature | `mount()` | `import_server()` |
|---------|-----------|-------------------|
| Link type | Live (dynamic) | One-time copy (static) |
| Updates | Reflected immediately | Not reflected |
| Use case | Modular runtime composition | Bundling finalized components |

---

## Proxy Provider (Remote MCP Servers)

`create_proxy()` connects to remote MCP servers. Use it to bridge transports, aggregate backends, or add authentication.

```python
from fastmcp.server import create_proxy

# Proxy a remote HTTP server — runs locally over stdio
proxy = create_proxy("http://api.example.com/mcp", name="MyProxy")

if __name__ == "__main__":
    proxy.run()  # Defaults to stdio
```

PATTERN: Mount a proxy into an existing server to add remote components.

```python
from fastmcp import FastMCP
from fastmcp.server import create_proxy

server = FastMCP("Orchestrator")

@server.tool
def local_tool() -> str:
    return "Local result"

# Add proxied tools from a remote server
external = create_proxy("http://external-server/mcp")
server.mount(external, namespace="api")
```

PATTERN: `create_proxy()` accepts URLs, file paths, or config dicts directly.

```python
# Remote HTTP server
mcp.mount(create_proxy("http://api.example.com/mcp"), namespace="api")

# Local Python script
mcp.mount(create_proxy("./my_server.py"), namespace="local")

# npm package via config dict
github_config = {
    "mcpServers": {
        "default": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"]
        }
    }
}
mcp.mount(create_proxy(github_config), namespace="github")
```

RULE: Each request to a proxy created with `create_proxy()` gets its own isolated backend session. Shared sessions (passing an already-connected client) risk context mixing in concurrent scenarios.

PATTERN: Proxies forward MCP features automatically — sampling, elicitation, logging, and progress notifications all pass through to the upstream server.

---

## OpenAPIProvider

`OpenAPIProvider` parses an OpenAPI specification and creates MCP components from it. Each component makes live HTTP calls to the described API endpoints. Components are created eagerly at initialization time.

Import path: `fastmcp.server.providers.openapi.OpenAPIProvider`

```python
import httpx
from fastmcp import FastMCP
from fastmcp.server.providers.openapi import OpenAPIProvider

spec = httpx.get("https://api.example.com/openapi.json").json()
client = httpx.AsyncClient(base_url="https://api.example.com")

provider = OpenAPIProvider(openapi_spec=spec, client=client)

mcp = FastMCP("API Server")
mcp.add_provider(provider)
```

PATTERN: Use `FastMCP.from_openapi()` as a shorthand that creates the provider and wraps it in a server in one call.

```python
mcp = FastMCP.from_openapi(
    openapi_spec=spec,
    client=client,
    name="My API Server",
)
```

### Constructor Parameters

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `openapi_spec` | `dict[str, Any]` | required | OpenAPI schema dictionary |
| `client` | `httpx.AsyncClient \| None` | `None` | HTTP client; auto-created from spec's first `servers[].url` if omitted |
| `route_maps` | `list[RouteMap] \| None` | `None` | Ordered rules mapping routes to MCP component types; checked before defaults |
| `route_map_fn` | `RouteMapFn \| None` | `None` | Callable for per-route override after `route_maps` matching |
| `mcp_component_fn` | `ComponentFn \| None` | `None` | Called on each created component for in-place customization |
| `mcp_names` | `dict[str, str] \| None` | `None` | Maps `operationId` to explicit component names |
| `tags` | `set[str] \| None` | `None` | Tags added to every component |
| `validate_output` | `bool` | `True` | Use OpenAPI response schema for output validation; set `False` for permissive |

RULE: If `client` is omitted and the spec has no `servers[].url`, initialization raises `ValueError`. Pass an explicit client when the spec lacks server entries.

### Route Mapping

By default every endpoint becomes a `TOOL`. Use `RouteMap` objects to override this:

```python
from fastmcp.server.providers.openapi import OpenAPIProvider, RouteMap, MCPType

provider = OpenAPIProvider(
    openapi_spec=spec,
    client=client,
    route_maps=[
        # GET with path params → ResourceTemplate
        RouteMap(methods=["GET"], pattern=r".*\{.*\}.*", mcp_type=MCPType.RESOURCE_TEMPLATE),
        # All other GETs → Resource
        RouteMap(methods=["GET"], pattern=r".*", mcp_type=MCPType.RESOURCE),
        # Exclude admin routes
        RouteMap(pattern=r"^/admin/.*", mcp_type=MCPType.EXCLUDE),
    ],
)
```

Custom `route_maps` are checked first; FastMCP's default catch-all (`all routes → TOOL`) runs after. A `RouteMap(mcp_type=MCPType.EXCLUDE)` catch-all at the end of your list will suppress the default.

### Key Constraints

- Produces tools, resources, and resource templates — **never prompts** (OpenAPI has no prompt concept)
- Component names are derived from `operationId`, slugified, and truncated to 56 characters; collisions get a numeric suffix
- Name overrides via `mcp_names` map `operationId` → desired name (still slugified and truncated)
- `mcp_component_fn` modifies components in-place; its return value is ignored
- When the provider owns the `httpx.AsyncClient` (i.e., `client` was not passed), it is closed on server shutdown via `lifespan()`
- Output validation uses the response schema from the OpenAPI spec; set `validate_output=False` to accept any JSON response structure

SOURCE: <https://github.com/PrefectHQ/fastmcp/blob/main/src/fastmcp/server/providers/openapi/provider.py>, <https://github.com/PrefectHQ/fastmcp/blob/main/src/fastmcp/server/providers/openapi/__init__.py>, <https://gofastmcp.com/integrations/openapi> (accessed 2026-03-17)

---

## FileSystemProvider

`FileSystemProvider` scans a directory for Python files and registers functions decorated with `@tool`, `@resource`, or `@prompt`. No coordination between files and the server is needed.

```python
from pathlib import Path
from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider

mcp = FastMCP("MyServer", providers=[
    FileSystemProvider(Path(__file__).parent / "mcp")
])
```

PATTERN: Component files use standalone decorators from their respective modules — not server-bound decorators.

```python
# mcp/tools/greet.py
from fastmcp.tools import tool

@tool
def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"
```

```python
# mcp/resources/config.py
from fastmcp.resources import resource

@resource("config://app")
def get_app_config() -> str:
    """Get application configuration."""
    return '{"version": "1.0"}'
```

```python
# mcp/prompts/assistant.py
from fastmcp.prompts import prompt

@prompt
def code_review(code: str, language: str = "python") -> str:
    """Generate a code review prompt."""
    return f"Please review this {language} code:\n\n```{language}\n{code}\n```"
```

PATTERN: Enable `reload=True` during development to re-scan files on every request.

```python
provider = FileSystemProvider(
    root=Path(__file__).parent / "mcp",
    reload=True,  # DEVELOPMENT ONLY — adds per-request overhead
)
```

Discovery rules:

- Only `.py` files are scanned
- `__init__.py` and `__pycache__` are skipped
- Functions starting with `_` are ignored even if decorated
- Files without decorators are silently skipped

---

## SkillsProvider and ClaudeSkillsProvider

`SkillsDirectoryProvider` exposes skill directories as MCP resources using the `skill://` URI scheme. `ClaudeSkillsProvider` is a convenience wrapper for `~/.claude/skills/`.

```python
from pathlib import Path
from fastmcp import FastMCP
from fastmcp.server.providers.skills import ClaudeSkillsProvider, SkillsDirectoryProvider

mcp = FastMCP("Skills Server")

# Use ~/.claude/skills/ (Claude Code default location)
mcp.add_provider(ClaudeSkillsProvider())

# Or specify custom root(s)
mcp.add_provider(SkillsDirectoryProvider(roots=[
    Path.cwd() / ".claude" / "skills",      # Project-level first
    Path.home() / ".claude" / "skills",     # User-level fallback
]))
```

Each subdirectory containing a `SKILL.md` file becomes a discoverable skill. Clients access skills via:

- `skill://skill-name/SKILL.md` — main instruction file
- `skill://skill-name/_manifest` — JSON manifest listing all files with sizes and SHA256 hashes
- `skill://skill-name/reference.md` — supporting files

Available vendor providers: `ClaudeSkillsProvider`, `CursorSkillsProvider`, `VSCodeSkillsProvider`, `CodexSkillsProvider`, `GeminiSkillsProvider`, `GooseSkillsProvider`, `CopilotSkillsProvider`, `OpenCodeSkillsProvider`

---

## Custom Providers

Subclass `Provider` to source components from any data source — databases, APIs, config files, or dynamic runtime logic.

```python
from collections.abc import Sequence
from fastmcp.server.providers import Provider
from fastmcp.tools import Tool

class DatabaseProvider(Provider):
    def __init__(self, db_url: str):
        super().__init__()
        self.db_url = db_url
        self.db = None

    async def _list_tools(self) -> Sequence[Tool]:
        """Return tools loaded from database."""
        rows = await self.db.fetch("SELECT * FROM tools")
        return [self._make_tool(row) for row in rows]
```

PATTERN: Override `lifespan()` for connection setup and teardown.

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

class DatabaseProvider(Provider):
    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        self.db = await connect_database(self.db_url)
        try:
            yield
        finally:
            await self.db.close()
```

PATTERN: Create component objects from functions using `Tool.from_function()`.

```python
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

tool = Tool.from_function(add, name="calculator_add", description="Add two integers")
```

RULE: Only implement the `_list_*` methods for component types your provider offers. The base class returns empty sequences by default. Override `_get_*` methods only if you can fetch individual components more efficiently than scanning the full list.

---

## Adding Providers to a Server

```python
# At construction time
mcp = FastMCP(
    "MyServer",
    providers=[DatabaseProvider(db_url), ConfigProvider(config_path)],
)

# After construction
mcp = FastMCP("MyServer")
mcp.add_provider(DatabaseProvider(db_url))
```

---

## Cross-Reference

- Transforms applied to providers: [./transforms.md](./transforms.md)
- Server core and decorators: [./server-core.md](./server-core.md)
- Authentication integration: [./auth.md](./auth.md)
