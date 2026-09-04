# FastMCP v3 → v4 Migration Reference

Breaking changes and migration steps for upgrading to FastMCP v3 or v4 — covers v2 to v3 changes, v3 to v4 changes, migration from the bundled MCP SDK FastMCP, and migration from the low-level `mcp.server.Server` class. [1] [2] [3] [9] [10]

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
dependencies = ["fastmcp>=4.0.0,<5"]
```

FastMCP 4 rebuilds on MCP Python SDK v2 and introduces a sessionless protocol, but negotiates
both protocol eras per connection — most FastMCP 3 servers run unchanged. See
[FastMCP v3 to v4 — Breaking Changes](#fastmcp-v3-to-v4--breaking-changes-9-10) below for the changes
that do apply. [9] [10]

---

## FastMCP v2 to v3 — Breaking Changes [4]

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
def long_running() -> str: ...


# v3 — correct
@mcp.tool(task=True)
def long_running() -> str: ...
```

CONSTRAINT: `task=True` requires `pip install "fastmcp[tasks]"`. Without the extra, this raises an import error at runtime.

### 3. Auth API — `require_auth` Removed

RULE: `require_auth` was removed in v3. Use `require_scopes("scope")` for endpoint-level authorization.

```python
# v2 — removed in v3
@mcp.tool(require_auth=True)
def protected_tool() -> str: ...


# v3 — correct pattern
from fastmcp.server.auth import require_scopes


@mcp.tool(auth=require_scopes("read"))
def protected_tool() -> str: ...
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
    return [Message(f"I'm seeing: {error}"), Message("I'll help debug that.", role="assistant")]
```

### 9. Auth Providers No Longer Auto-Load Env Vars

Pass auth provider credentials explicitly via `os.environ`.

```python
# v2 — auto-loaded from FASTMCP_SERVER_AUTH_GITHUB_* env vars
auth = GitHubProvider()

# v3 — explicit
import os
from fastmcp.server.auth.providers.github import GitHubProvider

auth = GitHubProvider(client_id=os.environ["GITHUB_CLIENT_ID"], client_secret=os.environ["GITHUB_CLIENT_SECRET"])
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

## v2 Deprecations — Removed Entirely in v4 [5] [10]

These were soft-deprecated (still worked, emitted warnings) in v3. FastMCP 4 removes every one of
them — the old form now raises an error instead of a warning. Update before upgrading to v4, not
"when convenient."

### mount() prefix → namespace

```python
# Deprecated
main.mount(subserver, prefix="api")

# New
main.mount(subserver, namespace="api")
```

### import_server() → mount()

```python
# Deprecated in v3, removed in v4
main.import_server(subserver)

# New
main.mount(subserver)
```

CONSTRAINT: `import_server()`'s one-time static-copy semantics have no v4 replacement — `mount()`
is a live, dynamic link only. If your server relied on `import_server()` to snapshot a subserver's
components at a point in time (so later changes to the subserver would NOT propagate), there is no
direct v4 equivalent; mount the subserver and accept live updates, or copy components manually.

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

## FastMCP v3 to v4 — Breaking Changes [9] [10]

### 1. `ToolAnnotations` Fields Are Now snake_case

FastMCP 4 rebuilds on MCP Python SDK v2, which renamed every `ToolAnnotations` field from
camelCase to snake_case. Any code that constructs `mcp.types.ToolAnnotations` directly must use
the new names — this is not FastMCP-specific, it applies to any `mcp.types` model you build by
hand. [10]

```python
# v3 (SDK v1) — camelCase
ToolAnnotations(title="My Tool", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

# v4 (SDK v2) — snake_case
ToolAnnotations(
    title="My Tool", read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)
```

The same SDK v2 rename affects other `mcp.types` fields and client-transport symbols in the wild —
for example `Tool.inputSchema` → `Tool.input_schema`, and
`mcp.client.streamable_http.streamablehttp_client` → `streamable_http_client`, whose constructor
also changed from a `headers: dict` kwarg to `http_client: ... | None`.

CONSTRAINT: that `http_client` parameter does **not** take an `httpx.AsyncClient`. SDK v2's streamable-HTTP
transport (`mcp/client/streamable_http.py`) depends on and re-exports **`httpx2`** — a separate PyPI
package (`httpx2`, by the `httpx`/Pydantic team, "the next generation HTTP client"), not a typo for
`httpx` and not the same import as the `httpx` you already have for provider/auth code elsewhere in
this skill. Passing an `httpx.AsyncClient` here type-checks as a plausible-looking bug (both classes
have the same shape) but fails validation, since the parameter is typed `httpx2.AsyncClient | None`.

```python
# v3 (SDK v1)
from mcp.client.streamable_http import streamablehttp_client

streamablehttp_client(url=url, headers=headers)

# v4 (SDK v2) — note httpx2, not httpx
import httpx2
from mcp.client.streamable_http import streamable_http_client

streamable_http_client(url=url, http_client=httpx2.AsyncClient(headers=headers) if headers else None)
```

Declare `httpx2` as a direct dependency (`httpx2>=2.5.0`, matching the floor `mcp` itself pins) if you
construct this client yourself rather than relying on it transitively through `mcp`/`fastmcp`.

If you build MCP protocol objects by hand anywhere in a server or client, grep for every
`mcp.types` construction and camelCase attribute access before upgrading — this is the single
most common silent break, since a stale field name is usually accepted by the type checker only
if you're passing `**kwargs`, and otherwise fails at call time, not import time.

### 2. Background Tasks Require Explicit `TasksExtension` Registration

RULE: a server exposing `@mcp.tool(task=True)` tools must register the tasks extension itself in
v4. v3 registered it implicitly the moment a task-enabled tool was added; v4 does not.

```python
# v3 — implicit, no registration needed
from fastmcp import FastMCP

mcp = FastMCP("MyServer")


@mcp.tool(task=True)
async def slow_computation() -> str: ...


# v4 — explicit registration required
from fastmcp import FastMCP
from fastmcp_tasks import TasksExtension

mcp = FastMCP("MyServer")
mcp.add_extension(TasksExtension())


@mcp.tool(task=True)
async def slow_computation() -> str: ...
```

CONSTRAINT: without `mcp.add_extension(TasksExtension())`, task-enabled tools fail at call time
(not at import time), so this gap surfaces as a runtime error under load, not a startup failure.

### 3. `ctx.sample()`, `ctx.sample_step()`, `ctx.list_roots()` Removed

FastMCP 4's sessionless protocol has no live server-to-client callback channel, so these
server-side `Context` methods are removed outright — not deprecated — across every protocol era.
[10]

```python
# v3 — server pushes a sampling request down the live connection
@mcp.tool
async def summarize(ctx: Context, text: str) -> str:
    result = await ctx.sample(f"Summarize: {text}")
    return result.text


# v4 — no server-initiated callback; either call an LLM directly...
@mcp.tool
async def summarize(text: str) -> str:
    return await my_llm_client.complete(f"Summarize: {text}")


# ...or, when you specifically need the caller's model, return an
# InputRequiredResult and read the answer on the next round-trip instead
# of blocking on a live callback.
```

CONSTRAINT: this also affects the client side — `sampling_handler` (see
[./client-sdk.md](./client-sdk.md)) only fires when connecting to a pre-v4 server that still
calls `ctx.sample()`. A server built against FastMCP 4 can never trigger it, so a v4 server and a
`sampling_handler`-based client are not a meaningful pairing.

### 4. `Client("server.py")` String Inference Deprecated

Passing a bare string to infer stdio transport now emits a deprecation warning in v4; removal is
planned for v5.

```python
# Deprecated — warns in v4
client = Client("my_server.py")

# Preferred
from pathlib import Path

client = Client(Path("my_server.py"))
```

---

## Troubleshooting: FastMCP's Rich Logging Can Mask the Real Error

Not a v3→v4 breaking change — it applies to any FastMCP version, but SDK v2's dependency churn is
a common moment to hit it. See
[./server-core.md#rich-traceback-logging-can-mask-the-real-error](./server-core.md#rich-traceback-logging-can-mask-the-real-error)
for the mechanism and the fix.

---

## Migrating from MCP SDK FastMCP (v1 Bundled) [6]

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

## Migrating from Low-Level `mcp.server.Server` [7]

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
        await server.run(read_stream, write_stream, server.create_initialization_options())


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
async def get_prompt(name: str, arguments: dict) -> types.GetPromptResult: ...


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

---

## Migrating to fastmcp-slim (v3.3.0+) [8]

Client-only consumers (scripts or services that call MCP servers but don't host one) can reduce their dependency footprint by switching to `fastmcp-slim`:

```bash
# Before
pip install fastmcp

# After (client-only)
pip install "fastmcp-slim[client]"
```

No code changes required — the import namespace is identical:

```python
from fastmcp import Client  # works with both fastmcp and fastmcp-slim
```

Choose extras based on your LLM provider: `fastmcp-slim[client,openai]`, `fastmcp-slim[client,anthropic]`, `fastmcp-slim[client,gemini]`.

## References

1. [FastMCP From Fastmcp 2](https://gofastmcp.com/getting-started/upgrading/from-fastmcp-2) (accessed 2026-03-05)
2. [FastMCP From Mcp Sdk](https://gofastmcp.com/getting-started/upgrading/from-mcp-sdk) (accessed 2026-03-05)
3. [FastMCP From Low Level Sdk](https://gofastmcp.com/getting-started/upgrading/from-low-level-sdk) (accessed 2026-03-05)
4. [FastMCP From Fastmcp 2](https://gofastmcp.com/getting-started/upgrading/from-fastmcp-2)
5. [FastMCP From Fastmcp 2](https://gofastmcp.com/getting-started/upgrading/from-fastmcp-2) — "Deprecated Features" section
6. [FastMCP From Mcp Sdk](https://gofastmcp.com/getting-started/upgrading/from-mcp-sdk)
7. [FastMCP From Low Level Sdk](https://gofastmcp.com/getting-started/upgrading/from-low-level-sdk)
8. [FastMCP Client Only Package](https://gofastmcp.com/clients/client-only-package.md) (accessed 2026-05-23)
9. [FastMCP Upgrade Guide](https://gofastmcp.com/development/upgrade-guide) (accessed 2026-09-04)
10. [FastMCP What's New in FastMCP 4](https://gofastmcp.com/getting-started/whats-new) (accessed 2026-09-04)
