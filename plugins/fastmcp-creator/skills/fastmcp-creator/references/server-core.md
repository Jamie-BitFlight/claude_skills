# FastMCP v3 Server Core Reference

How to instantiate a FastMCP server, register tools, resources, and prompts, inject context, and manage server lifecycle.

SOURCE: <https://gofastmcp.com/servers/server>, <https://gofastmcp.com/servers/tools>, <https://gofastmcp.com/servers/resources>, <https://gofastmcp.com/servers/prompts>, <https://gofastmcp.com/servers/context>, <https://gofastmcp.com/servers/lifespan>, <https://gofastmcp.com/servers/logging> (accessed 2026-03-05); <https://gofastmcp.com/servers/versioning> (accessed 2026-03-17, v3.1 features)

---

## Server Instantiation

RULE: Instantiate `FastMCP` with a human-readable name before registering any components.

```python
from fastmcp import FastMCP

mcp = FastMCP(name="MyServer")

# With instructions and version
mcp = FastMCP(
    name="HelpfulAssistant",
    instructions="This server provides data analysis tools. Call get_average() to analyze data.",
    version="1.0.0",
)
```

PATTERN: Common constructor parameters:

**Identity**

- `name` — human-readable server name (default: `"FastMCP"`)
- `instructions` — describes the server's purpose to clients
- `version` — server version string; defaults to FastMCP library version
- `website_url` — URL to a website with more information (v2.13.0+)
- `icons` — list of `Icon` representations for the server (v2.13.0+)

**Composition**

- `tools` — list of `Tool | Callable` to register programmatically (alternative to `@mcp.tool`)
- `auth` — `OAuthProvider | TokenVerifier | None` for HTTP auth
- `middleware` — list of `Middleware` for cross-cutting concerns (logging, rate limiting, etc.)
- `providers` — list of `Provider` that supply components dynamically at request time
- `transforms` — server-level list of `Transform` applied to all components (v3.1.0+)
- `lifespan` — async context manager for setup/teardown

**Behavior**

- `on_duplicate` — `"warn"` (default) | `"error"` | `"replace"` | `"ignore"`
- `strict_input_validation` — when `True`, rejects type mismatches instead of coercing (v2.13.0+)
- `mask_error_details` — when `True`, replaces internal errors with generic messages
- `list_page_size` — paginate list responses (v3.0.0+, default: `None` = all)
- `tasks` — enable background task support (default: `False`)
- `client_log_level` — minimum log level sent to clients (unreleased — expected v3.2.0)
- `dereference_schemas` — auto-dereference `$ref` in JSON schemas (default: `True`)

**Handlers and Storage**

- `sampling_handler` — custom handler for MCP sampling requests
- `sampling_handler_behavior` — `"fallback"` (default) | `"always"`
- `session_state_store` — persistent `AsyncKeyValue` backend for session state (v3.0.0+)

### `transforms=` Parameter (v3.1.0+)

RULE: Pass server-level transforms via the `transforms=` constructor argument rather than calling `add_transform()` after construction when all transforms are known upfront.

```python
from fastmcp import FastMCP
from fastmcp.server.transforms.search import BM25SearchTransform

mcp = FastMCP("Server", transforms=[BM25SearchTransform()])
```

Server-level transforms apply to all components from all providers and run after provider-level transforms. This is distinct from provider-level transforms, which apply only to components from that specific provider.

SOURCE: <https://gofastmcp.com/servers/server> (accessed 2026-03-17)

### `session_state_store` Parameter (v3.0.0+)

By default, session state uses an in-memory store suitable for single-server deployments. For distributed or serverless deployments where multiple machines handle requests, provide a custom `AsyncKeyValue` backend:

```python
from key_value.aio.stores.redis import RedisStore

mcp = FastMCP("distributed-app", session_state_store=RedisStore(...))
```

Any backend compatible with the [py-key-value-aio](https://github.com/strawgate/py-key-value) `AsyncKeyValue` protocol works. Supported backends include Redis, DynamoDB, and MongoDB.

CONSTRAINT: State set during `on_initialize` middleware persists to subsequent tool calls when using the same session object (STDIO, SSE, single-server HTTP). For distributed HTTP deployments, state is isolated by the `mcp-session-id` header.

SOURCE: <https://gofastmcp.com/servers/context> (accessed 2026-03-17)

---

## Tools

### Basic Tool Registration

RULE: Use `@mcp.tool` without parentheses as the canonical v3 decorator for simple tools.

```python
from fastmcp import FastMCP

mcp = FastMCP(name="CalculatorServer")

@mcp.tool
def add(a: int, b: int) -> int:
    """Adds two integer numbers together."""
    return a + b
```

FastMCP automatically:

- Uses the function name (`add`) as the tool name
- Uses the docstring as the tool description
- Generates an input schema from type annotations
- Handles validation and error reporting

### Tool with Custom Metadata

PATTERN: Use `@mcp.tool(...)` with parentheses only when passing arguments.

```python
@mcp.tool(
    name="find_products",
    description="Search the product catalog with optional category filtering.",
    tags={"catalog", "search"},
)
def search_products(query: str, category: str | None = None) -> list[dict]:
    """Internal docstring (ignored when description is provided above)."""
    return [{"id": 1, "name": "Product A"}]
```

CONSTRAINT: `*args` and `**kwargs` are not supported. FastMCP requires a complete parameter schema.

### Context-Aware Tool Factory Pattern

PATTERN: Use a `Context`-injecting factory function to create per-user tool customizations at request time. This enables user-specific behavior without registering separate tools per user.

```python
from fastmcp import FastMCP, Context
from fastmcp.dependencies import CurrentContext

mcp = FastMCP("PersonalizedServer")

@mcp.tool
async def get_user_tools(ctx: Context = CurrentContext()) -> list[str]:
    """Return the list of tools available to the current user."""
    user_id = ctx.client_id or "anonymous"
    # Customize behavior based on session identity
    if user_id.startswith("admin:"):
        return ["search", "delete", "export"]
    return ["search"]

@mcp.tool
async def search(query: str, ctx: Context = CurrentContext()) -> list[dict]:
    """Search with per-user result filtering."""
    user_id = ctx.client_id or "anonymous"
    await ctx.info(f"User {user_id} searching: {query}")
    # Results filtered based on user identity
    all_results = run_search(query)
    return [r for r in all_results if user_can_see(user_id, r)]
```

PATTERN: Use `ctx.get_state()` to build per-session personalization that accumulates across calls.

```python
@mcp.tool
async def set_user_preference(key: str, value: str, ctx: Context) -> str:
    """Store a user preference for this session."""
    await ctx.set_state(f"pref:{key}", value)
    return f"Preference '{key}' saved"

@mcp.tool
async def get_user_preference(key: str, ctx: Context) -> str | None:
    """Retrieve a user preference for this session."""
    return await ctx.get_state(f"pref:{key}")
```

SOURCE: <https://gofastmcp.com/servers/context> (accessed 2026-03-17)

### Async Tools

FastMCP supports both `def` and `async def`. Synchronous tools run in a threadpool automatically.

```python
import asyncio
from fastmcp import FastMCP

mcp = FastMCP(name="AsyncServer")

@mcp.tool
async def fetch_data(url: str) -> str:
    """Fetch data from a URL asynchronously."""
    # async I/O operations preferred for efficiency
    return f"Data from {url}"
```

---

## Resources

### Basic Resource

RULE: Use `@mcp.resource("uri://pattern")` — the URI argument is always required.

```python
from fastmcp import FastMCP

mcp = FastMCP(name="DataServer")

@mcp.resource("data://config")
def get_config() -> str:
    """Provides application configuration as JSON."""
    import json
    return json.dumps({"theme": "dark", "version": "1.2.0"})
```

PATTERN: Resources are lazy — the function runs only when a client requests `resources/read`.

### Resource Templates

Parameterize the URI with `{param_name}` placeholders. Function parameters match placeholder names.

```python
@mcp.resource("users://{user_id}/profile")
def get_user_profile(user_id: int) -> dict:
    """Retrieves a user profile by ID."""
    return {"id": user_id, "name": f"User {user_id}", "status": "active"}
```

PATTERN: Wildcard parameter `{param*}` captures multiple path segments (slashes included).

```python
@mcp.resource("path://{filepath*}")
def get_path_content(filepath: str) -> str:
    """Read content at a nested file path."""
    return f"Content at: {filepath}"
```

### Resource Return Types

Resources must return `str`, `bytes`, or `ResourceResult`.

```python
from fastmcp.resources import ResourceResult, ResourceContent

@mcp.resource("data://users")
def get_users() -> ResourceResult:
    return ResourceResult(
        contents=[
            ResourceContent(content='[{"id": 1}]', mime_type="application/json"),
        ],
        meta={"total": 1}
    )
```

CONSTRAINT: `enabled=False` on `@mcp.resource` is deprecated in v3.0.0. Use `mcp.disable()` instead.

---

## Prompts

### Basic Prompt

RULE: Use `@mcp.prompt` without parentheses for simple prompts. The decorator uses the function name as the prompt identifier.

```python
from fastmcp import FastMCP
from fastmcp.prompts import Message

mcp = FastMCP(name="PromptServer")

@mcp.prompt
def ask_about_topic(topic: str) -> str:
    """Generates a user message asking for an explanation."""
    return f"Can you please explain the concept of '{topic}'?"

@mcp.prompt
def generate_code_request(language: str, task: str) -> list[Message]:
    """Generates a conversation for code generation."""
    return [
        Message(f"Write a {language} function that: {task}"),
        Message("I'll help you write that function.", role="assistant"),
    ]
```

### Prompt with Custom Metadata

```python
@mcp.prompt(
    name="analyze_data_request",
    description="Creates a request to analyze data with specific parameters",
    tags={"analysis", "data"},
)
def data_analysis_prompt(data_uri: str, analysis_type: str = "summary") -> str:
    return f"Please perform a '{analysis_type}' analysis on the data at {data_uri}."
```

CONSTRAINT: `*args` and `**kwargs` are not supported as prompt parameters.

---

## Context Object

PATTERN: Access MCP context by adding a `ctx: Context` parameter to any tool, resource, or prompt function. FastMCP injects the context automatically based on the type hint.

```python
from fastmcp import FastMCP, Context

mcp = FastMCP(name="ContextDemo")

@mcp.tool
async def process_file(file_uri: str, ctx: Context) -> str:
    """Processes a file with context logging."""
    await ctx.info(f"Processing {file_uri}")
    return f"Processed: {file_uri}"
```

RULE: Context methods are async — functions that call them usually need `async def`.

### Logging via Context

Send messages back to the MCP client during tool execution.

```python
@mcp.tool
async def analyze_data(data: list[float], ctx: Context) -> dict:
    """Analyze numerical data with logging."""
    await ctx.debug("Starting analysis")
    await ctx.info(f"Analyzing {len(data)} data points")

    if not data:
        await ctx.warning("Empty data list provided")
        return {"error": "empty"}

    result = sum(data) / len(data)
    await ctx.info(f"Analysis complete, average: {result}")
    return {"average": result}
```

Log level methods: `ctx.debug()`, `ctx.info()`, `ctx.warning()`, `ctx.error()`

### Progress Reporting

```python
@mcp.tool
async def long_operation(items: list[str], ctx: Context) -> list[str]:
    """Process a list of items with progress reporting."""
    results = []
    for i, item in enumerate(items):
        results.append(item.upper())
        await ctx.report_progress(progress=i + 1, total=len(items))
    return results
```

### Resource and Prompt Access via Context

```python
@mcp.tool
async def read_config(ctx: Context) -> str:
    """Read the configuration resource."""
    content_list = await ctx.read_resource("data://config")
    return content_list[0].content

@mcp.tool
async def list_available(ctx: Context) -> dict:
    """List available resources and prompts."""
    resources = await ctx.list_resources()
    prompts = await ctx.list_prompts()
    return {
        "resources": [r.uri for r in resources],
        "prompts": [p.name for p in prompts],
    }
```

### Session State (v3.0.0+)

Store data that persists across multiple requests in the same MCP session. Each client session has isolated state.

```python
@mcp.tool
async def increment_counter(ctx: Context) -> int:
    """Increment a per-session counter."""
    count = await ctx.get_state("counter") or 0
    await ctx.set_state("counter", count + 1)
    return count + 1

@mcp.tool
async def get_counter(ctx: Context) -> int:
    """Get the current counter value."""
    return await ctx.get_state("counter") or 0
```

Session state method signatures:

- `await ctx.set_state(key, value, *, serializable=True)` — store a value
- `await ctx.get_state(key)` — retrieve a value (`None` if not found)
- `await ctx.delete_state(key)` — remove a value

CONSTRAINT: State expires after 1 day. Non-JSON-serializable values (e.g., HTTP clients) require `serializable=False` and persist only for the current request.

### Request Metadata

```python
@mcp.tool
async def request_info(ctx: Context) -> dict:
    """Return information about the current request."""
    return {
        "request_id": ctx.request_id,
        "client_id": ctx.client_id or "unknown",
    }
```

Available properties: `ctx.request_id`, `ctx.client_id`, `ctx.session_id`, `ctx.transport`

---

## Lifespan Management

RULE: Use the `@lifespan` decorator to run setup code once at server start and teardown at stop. Always wrap teardown in `try/finally`.

```python
from fastmcp import FastMCP, Context
from fastmcp.server.lifespan import lifespan

@lifespan
async def app_lifespan(server):
    # Setup: runs once when server starts
    db = await connect_to_database()
    try:
        yield {"db": db}  # Dict becomes ctx.lifespan_context
    finally:
        # Teardown: runs when server stops
        await db.close()

mcp = FastMCP("MyServer", lifespan=app_lifespan)

@mcp.tool
async def query_data(query: str, ctx: Context) -> list:
    """Query the database."""
    db = ctx.lifespan_context["db"]
    return await db.execute(query)
```

PATTERN: Compose multiple lifespans with the `|` operator.

```python
@lifespan
async def config_lifespan(server):
    config = load_config()
    yield {"config": config}

@lifespan
async def db_lifespan(server):
    db = await connect_to_database()
    try:
        yield {"db": db}
    finally:
        await db.close()

mcp = FastMCP("MyServer", lifespan=config_lifespan | db_lifespan)
```

---

## Running the Server

```python
from fastmcp import FastMCP

mcp = FastMCP(name="MyServer")

@mcp.tool
def greet(name: str) -> str:
    """Greet a user by name."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    # STDIO transport (default) — for local integrations
    mcp.run()

    # HTTP transport — for web services
    # mcp.run(transport="http", host="127.0.0.1", port=9000)
```

Supported transports: `"stdio"` (default), `"http"` (Streamable HTTP), `"sse"` (legacy, deprecated)

### Custom HTTP Routes

```python
from starlette.requests import Request
from starlette.responses import PlainTextResponse

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")
```

---

## Tag-Based Filtering

PATTERN: Apply `tags` to any component at registration, then filter at the server level.

```python
@mcp.tool(tags={"public", "utility"})
def public_tool() -> str:
    return "This tool is public"

@mcp.tool(tags={"internal", "admin"})
def admin_tool() -> str:
    return "This tool is for admins only"

# Server-level filtering
mcp = FastMCP(include_tags={"public"})          # Only expose "public" components
mcp = FastMCP(exclude_tags={"internal"})         # Hide "internal" components
mcp = FastMCP(include_tags={"admin"}, exclude_tags={"deprecated"})
```

RULE: Exclude tags always take priority over include tags.

---

## Component Versioning (v3.0.0+)

Register multiple implementations of the same tool, resource, or prompt under one identifier. Clients see the highest version by default. Use `VersionFilter` to expose specific ranges.

```python
from fastmcp import FastMCP
from fastmcp.server.providers import LocalProvider
from fastmcp.server.transforms import VersionFilter

components = LocalProvider()

@components.tool(version="1.0")
def calculate(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y

@components.tool(version="2.0")
def calculate(x: int, y: int, z: int = 0) -> int:
    """Add two or three numbers."""
    return x + y + z

# Serve different version ranges to different clients
api_v1 = FastMCP("API v1", providers=[components])
api_v1.add_transform(VersionFilter(version_lt="2.0"))

api_v2 = FastMCP("API v2", providers=[components])
api_v2.add_transform(VersionFilter(version_gte="2.0"))
```

RULE: For any given component name, either version all implementations or version none. Mixing versioned and unversioned components with the same name raises a `ValueError` at registration time.

### `VersionFilter` Parameters

- `version_gte` — include components at or above this version (inclusive)
- `version_lt` — include components below this version (exclusive)
- `include_unversioned` — whether to include unversioned components (default: `True`)

PATTERN: Use `include_unversioned=False` to produce a strictly versioned API surface that excludes any components that have not been given a version tag.

```python
# Only expose versioned components — unversioned components are hidden
api_v2 = FastMCP("API v2", providers=[components])
api_v2.add_transform(VersionFilter(version_gte="2.0", include_unversioned=False))
```

CONSTRAINT: By default (`include_unversioned=True`), unversioned components pass through all `VersionFilter` instances unaffected. This prevents accidentally hiding existing components when adding version filtering to a mixed codebase. Set `include_unversioned=False` explicitly when you want a clean versioned-only surface.

SOURCE: <https://gofastmcp.com/servers/versioning> (accessed 2026-03-17)

---

## Component Visibility Control (v3.0.0+)

Enable or disable components at runtime without re-registering.

```python
# Disable by tag
mcp.disable(tags={"internal"})

# Disable by component key
mcp.disable(keys={"tool:my_tool", "resource:data://secret"})

# Allowlist: only enable components with specific tags
mcp.enable(tags={"public"}, only=True)
```

CONSTRAINT: Disabled components do not appear in list responses and cannot be called.

---

## Cross-Reference

- Providers and mounting: [./providers.md](./providers.md)
- Transforms: [./transforms.md](./transforms.md)
- Authentication and authorization: [./auth.md](./auth.md)
- Claude Code MCP integration: [./claude-code-mcp-integration.md](./claude-code-mcp-integration.md)
