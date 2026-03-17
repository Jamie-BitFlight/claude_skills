<!-- Extracted from advanced.md to reduce file size. Canonical middleware reference. -->

## Middleware

SOURCE: <https://gofastmcp.com/servers/middleware> (accessed 2026-03-17)

CONSTRAINT: Middleware is a FastMCP-specific concept — it is not part of the MCP protocol specification. Available since FastMCP 2.9.0.

PATTERN: Middleware forms a pipeline around every operation. Requests flow through each middleware in order; responses flow back in reverse. The key decision point is `call_next(context)` — calling it continues the chain, not calling it stops processing entirely.

```text
Request → Middleware A → Middleware B → Handler → Middleware B → Middleware A → Response
```

### Base Class and Subclassing

PATTERN: Subclass `Middleware` from `fastmcp.server.middleware` and override the hooks you need. Unoverridden hooks pass through automatically.

```python
from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext

class LoggingMiddleware(Middleware):
    async def on_message(self, context: MiddlewareContext, call_next):
        print(f"→ {context.method}")
        result = await call_next(context)
        print(f"← {context.method}")
        return result

mcp = FastMCP("MyServer")
mcp.add_middleware(LoggingMiddleware())
```

PATTERN: `MiddlewareContext` attributes available in every hook:

| Attribute | Type | Description |
|---|---|---|
| `method` | `str` | MCP method name (e.g., `"tools/call"`) |
| `source` | `str` | Origin: `"client"` or `"server"` |
| `type` | `str` | Message type: `"request"` or `"notification"` |
| `message` | `object` | The MCP message data |
| `timestamp` | `datetime` | When the request was received |
| `fastmcp_context` | `Context` | FastMCP context object (if available) |

### Hook Hierarchy

PATTERN: Multiple hooks fire per request, from general to specific. Override only what you need:

| Level | Hook | Fires when |
|---|---|---|
| Message | `on_message` | Every MCP message (requests and notifications) |
| Type | `on_request` | Requests expecting a response |
| Type | `on_notification` | Fire-and-forget notifications |
| Operation | `on_call_tool` | Tool execution |
| Operation | `on_read_resource` | Resource reads |
| Operation | `on_get_prompt` | Prompt retrieval |
| Operation | `on_list_tools` | Tool listing |
| Operation | `on_list_resources` | Resource listing |
| Operation | `on_list_prompts` | Prompt listing |
| Operation | `on_initialize` | Client session initialization (v2.13.0+) |

CONSTRAINT: `on_initialize` cannot modify the initialization response. Raise `McpError` **before** `call_next()` to reject a client — raising after `call_next()` only logs the error because the response has already been sent.

### Middleware Ordering

PATTERN: Add middleware in the order you want it to run on the way in. First added = outermost wrapper (first in, last out).

```python
from fastmcp import FastMCP
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware

mcp = FastMCP("MyServer")
mcp.add_middleware(ErrorHandlingMiddleware())   # 1st in, last out — catches all errors
mcp.add_middleware(RateLimitingMiddleware())    # 2nd
mcp.add_middleware(LoggingMiddleware())         # 3rd in, first out — sees post-processed request
```

RULE: Place error handling first so it catches exceptions from all subsequent middleware. Place logging last (innermost) so it records execution after other middleware has processed the request.

### Constructor Parameters

PATTERN: Initialize middleware with configuration via `__init__`:

```python
from fastmcp.server.middleware import Middleware, MiddlewareContext

class ConfigurableMiddleware(Middleware):
    def __init__(self, api_key: str, rate_limit: int = 100):
        self.api_key = api_key
        self.rate_limit = rate_limit

    async def on_request(self, context: MiddlewareContext, call_next):
        return await call_next(context)

mcp.add_middleware(ConfigurableMiddleware(api_key="secret", rate_limit=50))
```

### Denying Requests

PATTERN: Raise the appropriate exception to stop processing and return an error to the client. Do not skip `call_next()` without raising — that silently suppresses the request.

```python
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.exceptions import ToolError

class AuthMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = context.message.name
        if tool_name in ["delete_all", "admin_config"]:
            raise ToolError("Access denied: requires admin privileges")
        return await call_next(context)
```

| Operation | Exception type |
|---|---|
| Tool calls | `ToolError` |
| Resource reads | `ResourceError` |
| Prompt retrieval | `PromptError` |
| General requests | `McpError` |

### Modifying Requests and Responses

PATTERN: Mutate `context.message.arguments` before `call_next()` to transform the request. Mutate `result` after `call_next()` to transform the response.

```python
from fastmcp.server.middleware import Middleware, MiddlewareContext

class InputSanitizer(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        if context.message.name == "search":
            query = context.message.arguments.get("query", "")
            context.message.arguments["query"] = query.strip().lower()
        return await call_next(context)

class ResponseEnricher(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        result = await call_next(context)
        if context.message.name == "get_data" and result.structured_content:
            result.structured_content["processed_by"] = "enricher"
        return result
```

### Storing State for Tools

PATTERN: Store per-request state in middleware via `context.fastmcp_context.set_state()`. Tools retrieve it with `ctx.get_state()`.

```python
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_headers
from fastmcp import FastMCP, Context

class UserMiddleware(Middleware):
    async def on_request(self, context: MiddlewareContext, call_next):
        headers = get_http_headers() or {}
        user_id = headers.get("x-user-id", "anonymous")
        if context.fastmcp_context:
            context.fastmcp_context.set_state("user_id", user_id)
        return await call_next(context)

mcp = FastMCP("MyServer")
mcp.add_middleware(UserMiddleware())

@mcp.tool
def get_user_data(ctx: Context) -> str:
    user_id = ctx.get_state("user_id")
    return f"Data for user: {user_id}"
```

### Tag-Based Access Control

PATTERN: Look up the component through the server context to access its tags during execution hooks. Use this for tag-based auth without modifying individual tools.

```python
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.exceptions import ToolError

class TagBasedAuth(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        if context.fastmcp_context:
            try:
                tool = await context.fastmcp_context.fastmcp.get_tool(context.message.name)
                if "requires-auth" in tool.tags:
                    # Check auth here
                    pass
            except Exception:
                pass  # Let execution handle missing tools
        return await call_next(context)
```

PATTERN: Filter list operations to hide tools from clients — also block execution in the corresponding call hook to prevent direct invocation of hidden tools.

```python
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.exceptions import ToolError

class PrivateToolFilter(Middleware):
    async def on_list_tools(self, context: MiddlewareContext, call_next):
        tools = await call_next(context)
        return [tool for tool in tools if "private" not in tool.tags]

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        if context.fastmcp_context:
            tool = await context.fastmcp_context.fastmcp.get_tool(context.message.name)
            if "private" in tool.tags:
                raise ToolError("Tool not found")
        return await call_next(context)
```

### Complete Auth Example

PATTERN: Full API-key authentication middleware protecting specific tools:

```python
from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_headers
from fastmcp.exceptions import ToolError

class ApiKeyAuth(Middleware):
    def __init__(self, valid_keys: set[str], protected_tools: set[str]):
        self.valid_keys = valid_keys
        self.protected_tools = protected_tools

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = context.message.name
        if tool_name not in self.protected_tools:
            return await call_next(context)
        headers = get_http_headers() or {}
        api_key = headers.get("x-api-key")
        if api_key not in self.valid_keys:
            raise ToolError(f"Invalid API key for protected tool: {tool_name}")
        return await call_next(context)

mcp = FastMCP("Secure Server")
mcp.add_middleware(ApiKeyAuth(
    valid_keys={"key-1", "key-2"},
    protected_tools={"delete_user", "admin_panel"},
))

@mcp.tool
def delete_user(user_id: str) -> str:
    return f"Deleted user {user_id}"

@mcp.tool
def get_user(user_id: str) -> str:
    return f"User {user_id}"  # not protected
```

### Server Composition and Middleware Scope

PATTERN: Parent middleware runs for all requests including those routed to mounted child servers. Child middleware runs only for its own server's components.

```python
from fastmcp import FastMCP
from fastmcp.server.middleware.logging import LoggingMiddleware

parent = FastMCP("Parent")
parent.add_middleware(AuthMiddleware())  # Runs for ALL requests

child = FastMCP("Child")
child.add_middleware(LoggingMiddleware())  # Only runs for child's tools

parent.mount(child, namespace="child")
```

### Raw Handler Override

PATTERN: Override `__call__` directly to bypass the hook dispatch system and handle all messages with uniform logic:

```python
from fastmcp.server.middleware import Middleware, MiddlewareContext

class RawMiddleware(Middleware):
    async def __call__(self, context: MiddlewareContext, call_next):
        print(f"Processing: {context.method}")
        result = await call_next(context)
        print(f"Completed: {context.method}")
        return result
```

### Session Availability

CONSTRAINT: The MCP session may not be available during initialization. Check `ctx.request_context` before accessing session-specific attributes (available since v2.13.1).

```python
async def on_request(self, context: MiddlewareContext, call_next):
    ctx = context.fastmcp_context
    if ctx.request_context:
        session_id = ctx.session_id
        request_id = ctx.request_id
    else:
        # Session not yet established (e.g., during initialization)
        from fastmcp.server.dependencies import get_http_headers
        headers = get_http_headers()
    return await call_next(context)
```

### Built-in Middleware

PATTERN: FastMCP ships production-ready middleware for the most common concerns.

#### Logging

```python
from fastmcp.server.middleware.logging import LoggingMiddleware, StructuredLoggingMiddleware
```

`LoggingMiddleware` — human-readable request/response logging.
`StructuredLoggingMiddleware` — JSON-formatted logs for Datadog, Splunk, etc.

```python
mcp.add_middleware(LoggingMiddleware(
    include_payloads=True,
    max_payload_length=1000,
))
```

| Parameter | Default | Description |
|---|---|---|
| `include_payloads` | `False` | Log request/response content |
| `max_payload_length` | `500` | Truncate payloads beyond this length |
| `logger` | module logger | Custom logger instance |

#### Timing

```python
from fastmcp.server.middleware.timing import TimingMiddleware, DetailedTimingMiddleware
```

`TimingMiddleware` — logs execution duration. `DetailedTimingMiddleware` — per-operation timing with separate tracking for tools, resources, and prompts.

```python
mcp.add_middleware(TimingMiddleware())
```

#### Rate Limiting

```python
from fastmcp.server.middleware.rate_limiting import (
    RateLimitingMiddleware,
    SlidingWindowRateLimitingMiddleware,
)
```

`RateLimitingMiddleware` — token bucket algorithm (allows controlled bursts).
`SlidingWindowRateLimitingMiddleware` — precise time-window limiting without burst allowance.

```python
mcp.add_middleware(RateLimitingMiddleware(
    max_requests_per_second=10.0,
    burst_capacity=20,
))

mcp.add_middleware(SlidingWindowRateLimitingMiddleware(
    max_requests=100,
    window_minutes=1,
))
```

#### Error Handling

```python
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware, RetryMiddleware
```

`ErrorHandlingMiddleware` — centralized error logging and transformation. `RetryMiddleware` — exponential backoff retry for transient failures.

```python
mcp.add_middleware(ErrorHandlingMiddleware(
    include_traceback=True,
    transform_errors=True,
    error_callback=my_error_callback,
))

mcp.add_middleware(RetryMiddleware(
    max_retries=3,
    retry_exceptions=(ConnectionError, TimeoutError),
))
```

#### Caching

```python
from fastmcp.server.middleware.caching import ResponseCachingMiddleware
```

Caches tool calls, resource reads, and list operations with TTL-based expiration.

```python
from fastmcp.server.middleware.caching import (
    ResponseCachingMiddleware,
    CallToolSettings,
    ListToolsSettings,
    ReadResourceSettings,
)

mcp.add_middleware(ResponseCachingMiddleware(
    list_tools_settings=ListToolsSettings(ttl=30),
    call_tool_settings=CallToolSettings(included_tools=["expensive_tool"]),
    read_resource_settings=ReadResourceSettings(enabled=False),
))
```

CONSTRAINT: Cache keys are based on operation name and arguments only — they do not include user or session identity. Tools that return user-specific data derived from auth context must either disable caching or include identity in their arguments.

#### Response Limiting (v3.0.0+)

```python
from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware
```

Enforces byte size limits on tool outputs. Truncated responses receive a plain `TextContent` block with a suffix.

```python
mcp.add_middleware(ResponseLimitingMiddleware(
    max_size=500_000,
    tools=["search", "fetch_data"],  # None = all tools
))
```

| Parameter | Default | Description |
|---|---|---|
| `max_size` | `1_000_000` | Maximum response size in bytes |
| `truncation_suffix` | `"\n\n[Response truncated due to size limit]"` | Appended to truncated responses |
| `tools` | `None` | Limit only these tools (None = all tools) |

CONSTRAINT: Truncated responses no longer conform to the tool's `output_schema` — the client receives plain `TextContent` instead of structured output.

#### Ping (v3.0.0+)

```python
from fastmcp.server.middleware import PingMiddleware

mcp.add_middleware(PingMiddleware(interval_ms=5000))
```

Keeps long-lived connections alive with periodic pings. Has no effect on stateless connections.

SOURCE: <https://gofastmcp.com/servers/middleware> (accessed 2026-03-17)
