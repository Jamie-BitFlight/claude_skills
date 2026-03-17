# FastMCP v3 Migration Reference

Breaking changes and migration steps for upgrading to FastMCP v3 — covers v2 to v3 changes, migration from the bundled MCP SDK FastMCP, and migration from the low-level `mcp.server.Server` class.

SOURCE: <https://gofastmcp.com/getting-started/upgrading/from-fastmcp-2> (accessed 2026-03-05)
SOURCE: <https://gofastmcp.com/getting-started/upgrading/from-mcp-sdk> (accessed 2026-03-05)
SOURCE: <https://gofastmcp.com/getting-started/upgrading/from-low-level-sdk> (accessed 2026-03-05)

---

## Install

```bash
pip install --upgrade fastmcp
# or
uv add --upgrade fastmcp
```

Pin your version constraint to avoid breaking on the next major:

```toml
[project]
dependencies = ["fastmcp>=3.0.0,<4"]
```

---

## FastMCP v2 to v3 — Breaking Changes

SOURCE: <https://gofastmcp.com/getting-started/upgrading/from-fastmcp-2>

### 1. Decorator Syntax — Parentheses Removed

RULE: `@mcp.tool` (no parentheses) is the v3 canonical pattern. `@mcp.tool()` with parentheses is the v2 pattern.

```python
# v2 — with parentheses (wrong in v3)
@mcp.tool()
def my_tool(x: int) -> str:
    return str(x)

# v3 — without parentheses (correct)
@mcp.tool
def my_tool(x: int) -> str:
    return str(x)
```

Same applies to `@mcp.resource` and `@mcp.prompt`.

### 2. Background Tasks — `task=True` Replaces `TaskConfig`

RULE: Use `task=True` in v3. `task=TaskConfig(mode="required")` is the v2 API and does NOT work in v3.

```python
# v2 — old TaskConfig API (breaks in v3)
@mcp.tool(task=TaskConfig(mode="required"))
def long_running() -> str:
    ...

# v3 — correct
@mcp.tool(task=True)
def long_running() -> str:
    ...
```

CONSTRAINT: `task=True` requires `pip install "fastmcp[tasks]"`. Without the extra, this raises an import error at runtime.

### 3. Auth API — `require_auth` Removed

RULE: `require_auth` was removed in v3. Use `require_scopes("scope")` for endpoint-level authorization.

```python
# v2 — removed in v3
@mcp.tool(require_auth=True)
def protected_tool() -> str:
    ...

# v3 — correct pattern
from fastmcp.server.auth import require_scopes

@mcp.tool(auth=require_scopes("read"))
def protected_tool() -> str:
    ...
```

### 4. Constructor — Transport Settings Removed

Transport settings were removed from the `FastMCP()` constructor. Pass them to `run()` instead.

```python
# v2 — raises TypeError in v3
mcp = FastMCP("server", host="0.0.0.0", port=8080)
mcp.run()

# v3 — correct
mcp = FastMCP("server")
mcp.run(transport="http", host="0.0.0.0", port=8080)
```

Removed kwargs: `host`, `port`, `log_level`, `debug`, `sse_path`, `streamable_http_path`,
`json_response`, `stateless_http`, `tool_serializer`, `include_tags`, `exclude_tags`, `tool_transformations`.

The three per-type duplicate-handling kwargs (`on_duplicate_tools`, `on_duplicate_resources`,
`on_duplicate_prompts`) were removed and replaced with a single unified `on_duplicate` parameter
that applies uniformly to tools, resources, and prompts. Passing the old kwargs raises
`TypeError: Use on_duplicate= instead.`

```python
# v2 — raises TypeError in v3
mcp = FastMCP("server", on_duplicate_tools="warn", on_duplicate_resources="error")

# v3 — correct
mcp = FastMCP("server", on_duplicate="warn")
```

### 5. Component Listing Methods Renamed

`get_tools()`, `get_resources()`, `get_prompts()`, `get_resource_templates()` are renamed and now return lists instead of dicts.

```python
# v2 — dict-indexed, removed in v3
tools = await server.get_tools()
tool = tools["my_tool"]

# v3 — list, iterate by name
tools = await server.list_tools()
tool = next((t for t in tools if t.name == "my_tool"), None)
```

### 6. Component enable()/disable() Moved to Server

Calling `.enable()` or `.disable()` on a component object raises `NotImplementedError` in v3. Use the server-level API.

```python
# v2 — raises NotImplementedError in v3
tool = await server.get_tool("my_tool")
tool.disable()

# v3 — correct
server.disable(names={"my_tool"}, components={"tool"})
# or by tag
server.disable(tags={"draft"})
```

### 7. Context State Methods Are Now Async

`ctx.set_state()` and `ctx.get_state()` are async in v3 because state is session-scoped and backed by a storage backend.

```python
# v2 — sync, breaks in v3
ctx.set_state("key", "value")
value = ctx.get_state("key")

# v3 — async (must await)
await ctx.set_state("key", "value")
value = await ctx.get_state("key")
```

State values must be JSON-serializable by default. For non-serializable values (e.g., HTTP clients):

```python
await ctx.set_state("client", my_http_client, serializable=False)
# serializable=False values are request-scoped only
```

### 8. Prompts Use `Message` Class

`mcp.types.PromptMessage` is replaced by `fastmcp.prompts.Message`.

```python
# v2 — PromptMessage
from mcp.types import PromptMessage, TextContent

@mcp.prompt
def my_prompt() -> PromptMessage:
    return PromptMessage(role="user", content=TextContent(type="text", text="Hello"))

# v3 — Message (simpler)
from fastmcp.prompts import Message

@mcp.prompt
def my_prompt() -> Message:
    return Message("Hello")
```

Multi-turn prompts:

```python
@mcp.prompt
def debug(error: str) -> list[Message]:
    return [
        Message(f"I'm seeing: {error}"),
        Message("I'll help debug that.", role="assistant"),
    ]
```

### 9. Auth Providers No Longer Auto-Load Env Vars

Pass auth provider credentials explicitly via `os.environ`.

```python
# v2 — auto-loaded from FASTMCP_SERVER_AUTH_GITHUB_* env vars
auth = GitHubProvider()

# v3 — explicit
import os
from fastmcp.server.auth.providers.github import GitHubProvider

auth = GitHubProvider(
    client_id=os.environ["GITHUB_CLIENT_ID"],
    client_secret=os.environ["GITHUB_CLIENT_SECRET"],
)
```

### 10. OAuth Default Storage Changed

Default OAuth client storage changed from `DiskStore` to `FileTreeStore` (addresses CVE-2025-69872 pickle deserialization vulnerability). Clients using default storage re-register automatically on first connection after upgrade.

### 11. WSTransport Removed

Use `StreamableHttpTransport` instead of the removed `WSTransport`.

```python
# v2 — removed
from fastmcp.client.transports import WSTransport
transport = WSTransport("ws://localhost:8000/ws")

# v3 — correct
from fastmcp.client.transports import StreamableHttpTransport
transport = StreamableHttpTransport("http://localhost:8000/mcp")
```

### 12. Metadata Namespace Changed

FastMCP metadata key in component `meta` dicts changed from `_fastmcp` to `fastmcp`.

```python
# v2
tags = tool.meta.get("_fastmcp", {}).get("tags", [])

# v3
tags = tool.meta.get("fastmcp", {}).get("tags", [])
```

### 13. Repository Moved

GitHub repository moved from `jlowin/fastmcp` to `PrefectHQ/fastmcp`. GitHub redirects existing clones, but update git remotes when convenient:

```bash
git remote set-url origin https://github.com/PrefectHQ/fastmcp.git
```

---

## v2 Deprecations (Still Work, Emit Warnings)

SOURCE: <https://gofastmcp.com/getting-started/upgrading/from-fastmcp-2> — "Deprecated Features" section

Update these when convenient — they still work in v3 but will be removed in a future release.

### mount() prefix → namespace

```python
# Deprecated
main.mount(subserver, prefix="api")

# New
main.mount(subserver, namespace="api")
```

### import_server() → mount()

```python
# Deprecated
main.import_server(subserver)

# New
main.mount(subserver)
```

### Module Paths for Proxy and OpenAPI

```python
# Deprecated
from fastmcp.server.proxy import FastMCPProxy
from fastmcp.server.openapi import FastMCPOpenAPI

# New
from fastmcp.server.providers.proxy import FastMCPProxy
from fastmcp.server.providers.openapi import OpenAPIProvider

# FastMCPOpenAPI pattern — also deprecated, use provider instead
from fastmcp import FastMCP
server = FastMCP("my_api", providers=[OpenAPIProvider(spec, client)])
```

### add_tool_transformation() → add_transform()

```python
# Deprecated
mcp.add_tool_transformation("name", config)

# New
from fastmcp.server.transforms import ToolTransform
mcp.add_transform(ToolTransform({"name": config}))
```

### FastMCP.as_proxy() → create_proxy()

```python
# Deprecated
proxy = FastMCP.as_proxy("http://example.com/mcp")

# New
from fastmcp.server import create_proxy
proxy = create_proxy("http://example.com/mcp")
```

---

## Migrating from MCP SDK FastMCP (v1 Bundled)

SOURCE: <https://gofastmcp.com/getting-started/upgrading/from-mcp-sdk>

If your server starts with `from mcp.server.fastmcp import FastMCP`, you are using FastMCP 1.0 bundled in the `mcp` package.

For most servers, migration is a single import change:

```python
# Before (FastMCP 1.0 via mcp package)
from mcp.server.fastmcp import FastMCP

# After (standalone FastMCP 3.x)
from fastmcp import FastMCP
```

Then apply these additional fixes if they apply:

```python
# Constructor transport kwargs → move to run()
mcp = FastMCP("server")
mcp.run(transport="http", host="0.0.0.0", port=8080)

# Prompt returns — plain string works, or use Message
from fastmcp.prompts import Message

@mcp.prompt
def review(code: str) -> str:
    return f"Please review:\n\n{code}"
```

MCP package imports still work (FastMCP includes `mcp` as a dependency):

```python
# These still work — no change needed
import mcp.types
from mcp.server.stdio import stdio_server
```

FastMCP equivalents (prefer these when available):

| `mcp` Package | FastMCP Equivalent |
|---|---|
| `mcp.types.TextContent(type="text", text=x)` | Return `x` directly from tool |
| `mcp.types.ImageContent(...)` | `from fastmcp.utilities.types import Image` |
| `mcp.types.PromptMessage(...)` | `from fastmcp.prompts import Message` |

---

## Migrating from Low-Level `mcp.server.Server`

SOURCE: <https://gofastmcp.com/getting-started/upgrading/from-low-level-sdk>

The `Server` class requires manual handler registration, hand-written JSON Schema, and transport boilerplate. FastMCP replaces all of it with decorator-based registration.

### Server and Transport

```python
# Before — manual transport boilerplate
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("my-server")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )

asyncio.run(main())

# After — FastMCP
from fastmcp import FastMCP

mcp = FastMCP("my-server")

if __name__ == "__main__":
    mcp.run()
```

### Tools

```python
# Before — two handlers + hand-written JSON Schema
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="add",
            description="Add two numbers",
            inputSchema={
                "type": "object",
                "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                "required": ["a", "b"],
            },
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "add":
        return [types.TextContent(type="text", text=str(arguments["a"] + arguments["b"]))]

# After — one decorator, type hints become JSON Schema
from fastmcp import FastMCP

mcp = FastMCP("math")

@mcp.tool
def add(a: float, b: float) -> float:
    """Add two numbers"""
    return a + b
```

### JSON Schema to Python Type Mapping

| JSON Schema | Python Type |
|---|---|
| `{"type": "string"}` | `str` |
| `{"type": "number"}` | `float` |
| `{"type": "integer"}` | `int` |
| `{"type": "boolean"}` | `bool` |
| `{"type": "array", "items": {"type": "string"}}` | `list[str]` |
| `{"type": "object"}` | `dict` |
| Optional (not in `required`) | `param: str \| None = None` |

### Resources

```python
# Before — three handlers with URI routing
@server.list_resources()
async def list_resources(): ...

@server.list_resource_templates()
async def list_resource_templates(): ...

@server.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    if str(uri) == "config://app":
        return json.dumps({"debug": False})
    ...

# After — one decorator per resource; {placeholders} auto-register templates
@mcp.resource("config://app", mime_type="application/json")
def app_config() -> str:
    """Application configuration"""
    return json.dumps({"debug": False})

@mcp.resource("users://{user_id}/profile")
def user_profile(user_id: str) -> str:
    """User profile"""
    return json.dumps({"id": user_id})
```

### Prompts

```python
# Before — two handlers
@server.list_prompts()
async def list_prompts(): ...

@server.get_prompt()
async def get_prompt(name: str, arguments: dict) -> types.GetPromptResult:
    ...

# After — one decorator; return str (auto-wrapped as user message)
from fastmcp.prompts import Message

@mcp.prompt
def review_code(code: str, language: str | None = None) -> str:
    """Review code for issues"""
    lang_note = f" (written in {language})" if language else ""
    return f"Please review this code{lang_note}:\n\n{code}"
```

### Request Context

```python
# Before — server.request_context.session.send_log_message(...)
@server.call_tool()
async def call_tool(name: str, arguments: dict):
    ctx = server.request_context
    await ctx.session.send_log_message(level="info", data="Starting...")

# After — FastMCP Context injected by parameter type
from fastmcp import FastMCP, Context

mcp = FastMCP("worker")

@mcp.tool
async def process(ctx: Context) -> str:
    """Process with logging."""
    await ctx.info("Starting...")
    await ctx.report_progress(50, 100)
    await ctx.info("Done!")
    return "Processed"
```
