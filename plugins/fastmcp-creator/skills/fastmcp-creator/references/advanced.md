# FastMCP Advanced Features Reference

Background tasks, server-side elicitation, and advanced execution patterns — use this when building tools that run for seconds or minutes, require multi-turn user interaction, or need fine-grained execution control.

SOURCE: `.claude/worktrees/fastmcp/docs/servers/tasks.mdx` (accessed 2026-03-05)

---

## Background Tasks

SOURCE: `.claude/worktrees/fastmcp/docs/servers/tasks.mdx` (accessed 2026-03-05)

CONSTRAINT: Background tasks require the `tasks` optional extra. Install with:

```bash
pip install "fastmcp[tasks]"
```

RULE: Use `task=True` as the v3 pattern for background task support. `task=True` enables background execution — clients may request it or call the tool synchronously.

```python
import asyncio
from fastmcp import FastMCP

mcp = FastMCP("MyServer")

@mcp.tool(task=True)
async def slow_computation(duration: int) -> str:
    """A long-running operation."""
    for i in range(duration):
        await asyncio.sleep(1)
    return f"Completed in {duration} seconds"
```

CONSTRAINT: Background tasks require async functions. Using `task=True` with a sync function raises `ValueError` at registration time.

SOURCE: `.claude/worktrees/fastmcp/docs/servers/tasks.mdx` (accessed 2026-03-05)

PATTERN: Enable background tasks globally for all server components:

```python
mcp = FastMCP("MyServer", tasks=True)
```

CONSTRAINT: If any synchronous tools exist on a server with `tasks=True`, those must explicitly set `task=False` to avoid errors.

SOURCE: `.claude/worktrees/fastmcp/docs/servers/tasks.mdx` (accessed 2026-03-05)

### Progress Reporting

PATTERN: Inject the `Progress` dependency to report progress back to clients during task execution:

```python
from fastmcp import FastMCP
from fastmcp.dependencies import Progress

mcp = FastMCP("MyServer")

@mcp.tool(task=True)
async def process_files(files: list[str], progress: Progress = Progress()) -> str:
    await progress.set_total(len(files))

    for file in files:
        await progress.set_message(f"Processing {file}")
        # ... do work ...
        await progress.increment()

    return f"Processed {len(files)} files"
```

Progress API:

- `await progress.set_total(n)` — set the total number of steps
- `await progress.increment(amount=1)` — increment progress counter
- `await progress.set_message(text)` — update the status message

RULE: Progress works in both immediate and background execution modes — use the same code regardless of how the client invokes the function.

SOURCE: `.claude/worktrees/fastmcp/docs/servers/tasks.mdx` (accessed 2026-03-05)

### Task Backends

PATTERN: Default is in-memory backend — zero configuration, no external dependencies. Limitations: ephemeral (tasks lost on restart), ~250ms pickup latency, no horizontal scaling.

PATTERN: Redis backend for production — configure via environment variable:

```bash
export FASTMCP_DOCKET_URL=redis://localhost:6379
```

Redis advantages: persistent across restarts, single-digit millisecond pickup latency, horizontal scaling.

PATTERN: Add additional workers via CLI for horizontal scaling (Redis backend required):

```bash
fastmcp tasks worker server.py
```

Configure worker concurrency:

```bash
export FASTMCP_DOCKET_CONCURRENCY=20
fastmcp tasks worker server.py
```

CONSTRAINT: Task-enabled components must be defined at server startup. Components added dynamically after the server starts are not available for background execution.

SOURCE: `.claude/worktrees/fastmcp/docs/servers/tasks.mdx` (accessed 2026-03-05)

### Advanced Docket Dependencies

PATTERN: Access Docket instance and worker metadata from within tasks:

```python
from docket import Docket, Worker
from fastmcp import FastMCP
from fastmcp.dependencies import Progress, CurrentDocket, CurrentWorker

mcp = FastMCP("MyServer")

@mcp.tool(task=True)
async def my_task(
    progress: Progress = Progress(),
    docket: Docket = CurrentDocket(),
    worker: Worker = CurrentWorker(),
) -> str:
    # Schedule additional background work
    await docket.add(another_task, arg1, arg2)
    worker_name = worker.name
    return "Done"
```

SOURCE: `.claude/worktrees/fastmcp/docs/servers/tasks.mdx` (accessed 2026-03-05)

---

## Server-Side Elicitation

SOURCE: `.claude/worktrees/fastmcp/docs/servers/elicitation.mdx` (accessed 2026-03-05)

PATTERN: Use `ctx.elicit()` to request structured input from users mid-execution. The tool pauses until the client provides a response.

```python
from fastmcp import FastMCP, Context
from dataclasses import dataclass

mcp = FastMCP("Elicitation Server")

@dataclass
class UserInfo:
    name: str
    age: int

@mcp.tool
async def collect_user_info(ctx: Context) -> str:
    result = await ctx.elicit(
        message="Please provide your information",
        response_type=UserInfo
    )

    if result.action == "accept":
        user = result.data
        return f"Hello {user.name}, you are {user.age} years old"
    elif result.action == "decline":
        return "Information not provided"
    else:  # cancel
        return "Operation cancelled"
```

Elicitation result actions:

- `accept` — user provided valid input; data in `result.data`
- `decline` — user chose not to provide information
- `cancel` — user cancelled the entire operation

SOURCE: `.claude/worktrees/fastmcp/docs/servers/elicitation.mdx` (accessed 2026-03-05)

### Pattern Matching

PATTERN: Use typed result classes for pattern matching:

```python
from fastmcp.server.elicitation import (
    AcceptedElicitation,
    DeclinedElicitation,
    CancelledElicitation,
)

@mcp.tool
async def pattern_example(ctx: Context) -> str:
    result = await ctx.elicit("Enter your name:", response_type=str)

    match result:
        case AcceptedElicitation(data=name):
            return f"Hello {name}!"
        case DeclinedElicitation():
            return "No name provided"
        case CancelledElicitation():
            return "Operation cancelled"
```

SOURCE: `.claude/worktrees/fastmcp/docs/servers/elicitation.mdx` (accessed 2026-03-05)

### Multi-Turn Elicitation

PATTERN: Make multiple `ctx.elicit()` calls to gather information progressively:

```python
@mcp.tool
async def plan_meeting(ctx: Context) -> str:
    title_result = await ctx.elicit("What's the meeting title?", response_type=str)
    if title_result.action != "accept":
        return "Meeting planning cancelled"

    duration_result = await ctx.elicit("Duration in minutes?", response_type=int)
    if duration_result.action != "accept":
        return "Meeting planning cancelled"

    priority_result = await ctx.elicit(
        "Is this urgent?",
        response_type=["yes", "no"]
    )
    if priority_result.action != "accept":
        return "Meeting planning cancelled"

    urgent = priority_result.data == "yes"
    return f"Meeting '{title_result.data}' for {duration_result.data} minutes (Urgent: {urgent})"
```

SOURCE: `.claude/worktrees/fastmcp/docs/servers/elicitation.mdx` (accessed 2026-03-05)

### Elicitation Response Types

PATTERN: Scalar types — FastMCP automatically wraps them in MCP-compatible object schemas:

```python
result = await ctx.elicit("What's your name?", response_type=str)
result = await ctx.elicit("Pick a number!", response_type=int)
result = await ctx.elicit("True or false?", response_type=bool)
```

PATTERN: Constrained choices using list of strings, `Literal`, or Python enum:

```python
from typing import Literal

result = await ctx.elicit(
    "What priority level?",
    response_type=["low", "medium", "high"],
)

result = await ctx.elicit(
    "What priority level?",
    response_type=Literal["low", "medium", "high"]
)
```

PATTERN: Multi-select — wrap choices in an additional list level (available in v2.14.0+):

```python
result = await ctx.elicit(
    "Choose tags",
    response_type=[["bug", "feature", "documentation"]]  # List of a list
)
```

PATTERN: Titled options for better UI display (SEP-1330 compliant, available in v2.14.0+):

```python
result = await ctx.elicit(
    "What priority level?",
    response_type={
        "low": {"title": "Low Priority"},
        "medium": {"title": "Medium Priority"},
        "high": {"title": "High Priority"}
    }
)
```

PATTERN: Structured responses via dataclass or Pydantic model:

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class TaskDetails:
    title: str
    description: str
    priority: Literal["low", "medium", "high"]
    due_date: str

result = await ctx.elicit(
    "Please provide task details",
    response_type=TaskDetails
)
```

CONSTRAINT: MCP spec only supports shallow objects with scalar (`string`, `number`, `boolean`) or enum properties. Nested objects are not supported.

PATTERN: Default values for elicitation fields — pre-populate form fields (available in v2.14.0+):

```python
from pydantic import BaseModel, Field
from enum import Enum

class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TaskDetails(BaseModel):
    title: str = Field(description="Task title")
    description: str = Field(default="", description="Task description")
    priority: Priority = Field(default=Priority.MEDIUM, description="Task priority")

result = await ctx.elicit("Please provide task details", response_type=TaskDetails)
```

PATTERN: Approval-only elicitation (no data needed) — pass `None` as response type:

```python
result = await ctx.elicit("Approve this action?", response_type=None)

if result.action == "accept":
    return do_action()
else:
    raise ValueError("Action rejected")
```

CONSTRAINT: Elicitation requires the client to implement an elicitation handler. If the client does not support elicitation, calls to `ctx.elicit()` raise an error. See [./client-sdk.md](./client-sdk.md) for client-side elicitation handler implementation.

SOURCE: `.claude/worktrees/fastmcp/docs/servers/elicitation.mdx` (accessed 2026-03-05)

---

## Prefab Apps (EXPERIMENTAL — SOON)

SOURCE: `https://gofastmcp.com/apps/prefab` (accessed 2026-03-17)

CONSTRAINT: Prefab Apps require the `apps` optional extra. Install with:

```bash
pip install "fastmcp[apps]"
```

WARNING: Prefab UI is in extremely early, active development — its API changes frequently and breaking changes can occur with any release. Pin `prefab-ui` to a specific version:

```toml
# pyproject.toml
dependencies = [
    "fastmcp[apps]",
    "prefab-ui==0.8.0",  # pin to a known working version
]
```

RULE: Do not recommend Prefab Apps for production use. Advise users to pin `prefab-ui` explicitly.

PATTERN: Declare a tool as a Prefab App using `app=True`. The tool returns a `PrefabApp` with declarative UI components — no HTML or JavaScript required:

```python
from prefab_ui.components import Column, Heading, BarChart, ChartSeries
from prefab_ui.app import PrefabApp
from fastmcp import FastMCP

mcp = FastMCP("Dashboard")


@mcp.tool(app=True)
def revenue_chart(year: int) -> PrefabApp:
    """Show annual revenue as an interactive bar chart."""
    data = [
        {"quarter": "Q1", "revenue": 42000},
        {"quarter": "Q2", "revenue": 51000},
        {"quarter": "Q3", "revenue": 47000},
        {"quarter": "Q4", "revenue": 63000},
    ]

    with Column(gap=4, css_class="p-6") as view:
        Heading(f"{year} Revenue")
        BarChart(
            data=data,
            series=[ChartSeries(data_key="revenue", label="Revenue")],
            x_axis="quarter",
        )

    return PrefabApp(view=view)
```

PATTERN: Return type inference — if the return annotation is a Prefab type (`PrefabApp`, `Component`, or their `Optional` variants), FastMCP enables app rendering automatically without `app=True`:

```python
@mcp.tool
def greet(name: str) -> PrefabApp:
    return PrefabApp(view=Heading(f"Hello, {name}!"))
```

Explicit `app=True` is recommended for clarity; it is required when the return type is `ToolResult` (which does not reveal a Prefab type).

### Available Components

- `Column` — layout container with `gap` and `css_class`
- `Heading` — text heading
- `BarChart` / `ChartSeries` — interactive bar chart with configurable data key and label
- `Table` — tabular data display
- `Form` — user input form
- `Toggle` / `Button` — interactive controls
- `Badge` — status indicator with `variant`
- `If` — conditional rendering using `{{ expression }}` templates

### Returning Components Directly

PATTERN: Return a component directly when you do not need `PrefabApp`'s state or stylesheet configuration. FastMCP wraps it automatically:

```python
from prefab_ui.components import Column, Heading, Badge
from fastmcp import FastMCP

mcp = FastMCP("Status")


@mcp.tool(app=True)
def status_badge() -> Column:
    """Show system status."""
    with Column(gap=2) as view:
        Heading("All Systems Operational")
        Badge("Healthy", variant="success")
    return view
```

### Interactive State with PrefabApp

PATTERN: Use `PrefabApp(view=..., state={...})` when components need to read and react to initial state. State mutations (e.g., `ToggleState`) happen in the browser — no server round-trip:

```python
from prefab_ui.components import Column, Button, If, Badge
from prefab_ui.actions import ToggleState
from prefab_ui.app import PrefabApp
from fastmcp import FastMCP

mcp = FastMCP("Demo")


@mcp.tool(app=True)
def toggle_demo() -> PrefabApp:
    """Interactive toggle with state."""
    with Column(gap=4, css_class="p-6") as view:
        Button("Toggle", on_click=ToggleState("show"))
        with If("{{ show }}"):
            Badge("Visible!", variant="success")

    return PrefabApp(view=view, state={"show": False})
```

### ToolResult — LLM Text Alongside Rendered UI

PATTERN: Wrap the return in `ToolResult` when you need the LLM to understand the data (not just render it). Without this, the LLM receives only `"[Rendered Prefab UI]"`:

```python
from prefab_ui.components import Column, Heading, BarChart, ChartSeries
from prefab_ui.app import PrefabApp
from fastmcp import FastMCP
from fastmcp.tools import ToolResult

mcp = FastMCP("Sales")


@mcp.tool(app=True)
def sales_overview(year: int) -> ToolResult:
    """Show sales data visually and summarize for the model."""
    data = get_sales_data(year)
    total = sum(row["revenue"] for row in data)

    with Column(gap=4, css_class="p-6") as view:
        Heading("Sales Overview")
        BarChart(data=data, series=[ChartSeries(data_key="revenue")])

    return ToolResult(
        content=f"Total revenue for {year}: ${total:,} across {len(data)} quarters",
        structured_content=view,
    )
```

The user sees the chart; the LLM sees the text summary and can reason about it.

### How FastMCP Wires Prefab Apps

When a tool returns a Prefab component or `PrefabApp`, FastMCP automatically:

1. Registers a shared `ui://prefab/renderer.html` resource containing the JavaScript rendering engine — fetched once by the host and reused across all Prefab tools.
2. Wires tool metadata so the host knows to load the renderer iframe when displaying the result.
3. Serializes the component tree as `structuredContent` on the tool result.

No configuration is required beyond `app=True` (or type inference).

### Previewing Prefab Apps Locally

```bash
fastmcp dev apps
```

Launches a browser-based preview so you can inspect Prefab tool output without a full MCP host.

SOURCE: `https://gofastmcp.com/apps/prefab` (accessed 2026-03-17)

---

## Google GenAI Sampling Handler

SOURCE: `https://gofastmcp.com/clients/sampling` (accessed 2026-03-17)

PATTERN: Use `GoogleGenAISamplingHandler` for server-initiated LLM calls via the Google GenAI (Gemini) API — an alternative to the Anthropic and OpenAI handlers:

```python
from fastmcp import Client
from fastmcp.client.sampling.handlers.google_genai import GoogleGenAISamplingHandler

client = Client(
    "my_mcp_server.py",
    sampling_handler=GoogleGenAISamplingHandler(default_model="gemini-2.0-flash"),
)
```

CONSTRAINT: Requires the `gemini` optional extra:

```bash
pip install "fastmcp[gemini]"
```

All three built-in sampling handlers (OpenAI, Anthropic, Google GenAI) share the same interface and support the full sampling API including tool use. Choose based on which LLM provider the client application uses.

| Handler | Import path | Extra |
|---|---|---|
| OpenAI | `fastmcp.client.sampling.handlers.openai.OpenAISamplingHandler` | `fastmcp[openai]` |
| Anthropic | `fastmcp.client.sampling.handlers.anthropic.AnthropicSamplingHandler` | `fastmcp[anthropic]` |
| Google GenAI | `fastmcp.client.sampling.handlers.google_genai.GoogleGenAISamplingHandler` | `fastmcp[gemini]` |

SOURCE: `https://gofastmcp.com/clients/sampling` (accessed 2026-03-17)

---

## Middleware

SOURCE: `.worktrees/fastmcp/docs/servers/middleware.mdx` (accessed 2026-03-17)

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

SOURCE: `.worktrees/fastmcp/docs/servers/middleware.mdx` (accessed 2026-03-17)

---

## Dependency Injection

SOURCE: `.worktrees/fastmcp/docs/servers/dependency-injection.mdx` (accessed 2026-03-17)

PATTERN: Declare what you need as parameter defaults — FastMCP resolves values automatically at runtime. Dependency parameters are excluded from the MCP schema; clients never see them as callable parameters.

```python
from fastmcp import FastMCP
from fastmcp.server.context import Context

mcp = FastMCP("Demo")

@mcp.tool
async def my_tool(query: str, ctx: Context) -> str:
    await ctx.info(f"Processing: {query}")
    return f"Results for: {query}"
```

When a client calls `my_tool`, they see only `query`. The `ctx` parameter is injected because FastMCP recognizes the `Context` type annotation. This works identically for tools, resources, resource templates, and prompts.

PATTERN: Use `CurrentContext()` as an explicit default to make the injection visible in the signature:

```python
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context

@mcp.tool
async def my_tool(query: str, ctx: Context = CurrentContext()) -> str:
    await ctx.info(f"Processing: {query}")
    return f"Results for: {query}"
```

Both approaches are equivalent. The type-annotation form is more concise; `CurrentContext()` is more explicit.

### Built-in Dependencies

#### `Context` — MCP Request Context

Provides logging, progress reporting, resource access, and other request-scoped operations.

```python
from fastmcp.server.context import Context

@mcp.tool
async def process_data(data: str, ctx: Context) -> str:
    await ctx.info(f"Processing: {data}")
    return "Done"
```

PATTERN: Use `get_context()` from helper functions or middleware that cannot declare `ctx` as a parameter:

```python
from fastmcp.server.dependencies import get_context

async def log_something(message: str):
    ctx = get_context()
    await ctx.info(message)
```

#### `CurrentFastMCP()` — Server Instance (v2.14+)

Access the `FastMCP` server instance for introspection or server-level configuration.

```python
from fastmcp.dependencies import CurrentFastMCP

@mcp.tool
async def server_info(server: FastMCP = CurrentFastMCP()) -> str:
    return f"Server: {server.name}"
```

Function form: `from fastmcp.server.dependencies import get_server`

#### `CurrentRequest()` — HTTP Request (v2.2.11+)

Access the Starlette `Request` when running over HTTP transports (SSE or Streamable HTTP). Raises `RuntimeError` outside an HTTP context.

```python
from fastmcp.dependencies import CurrentRequest
from starlette.requests import Request

@mcp.tool
async def client_info(request: Request = CurrentRequest()) -> dict:
    return {
        "user_agent": request.headers.get("user-agent", "Unknown"),
        "client_ip": request.client.host if request.client else "Unknown",
    }
```

#### `CurrentHeaders()` — HTTP Headers (v2.2.11+)

Access HTTP headers with graceful fallback — returns an empty dict when no HTTP request is available. Safe for code that may run over any transport.

```python
from fastmcp.dependencies import CurrentHeaders

@mcp.tool
async def get_auth_type(headers: dict = CurrentHeaders()) -> str:
    auth = headers.get("authorization", "")
    return "Bearer" if auth.startswith("Bearer ") else "None"
```

CONSTRAINT: Problematic headers (`host`, `content-length`) are excluded by default. Use `get_http_headers(include_all=True)` to include all headers.

#### `CurrentAccessToken()` — Auth Token (v2.11.0+)

Access the authenticated user's token when the server uses authentication. Raises if not authenticated.

```python
from fastmcp.dependencies import CurrentAccessToken
from fastmcp.server.auth import AccessToken

@mcp.tool
async def get_user_id(token: AccessToken = CurrentAccessToken()) -> str:
    return token.claims.get("sub", "unknown")
```

`AccessToken` fields: `client_id`, `scopes`, `expires_at`, `claims`.

PATTERN: Use `get_access_token()` (function form) for optional auth — returns `None` if not authenticated:

```python
from fastmcp.server.dependencies import get_access_token

@mcp.tool
async def get_user_info() -> dict:
    token = get_access_token()
    if token is None:
        return {"authenticated": False}
    return {"authenticated": True, "user": token.claims.get("sub")}
```

#### `TokenClaim()` — Single Token Claim

Extract one specific claim from the token without needing the full `AccessToken` object. Raises `RuntimeError` if the claim is absent.

```python
from fastmcp.server.dependencies import TokenClaim

@mcp.tool
async def add_expense(
    amount: float,
    user_id: str = TokenClaim("oid"),  # Azure object ID
) -> dict:
    await db.insert({"user_id": user_id, "amount": amount})
    return {"status": "created", "user_id": user_id}
```

Common claim names by provider:

| Provider | User ID | Email | Name |
|---|---|---|---|
| Azure/Entra | `oid` | `email` | `name` |
| GitHub | `sub` | `email` | `name` |
| Google | `sub` | `email` | `name` |
| Auth0 | `sub` | `email` | `name` |

#### Background Task Dependencies

CONSTRAINT: Requires `pip install 'fastmcp[tasks]'`. Only available inside task-enabled components (`task=True`).

```python
from fastmcp.dependencies import CurrentDocket, CurrentWorker, Progress

@mcp.tool(task=True)
async def long_running_task(
    data: str,
    docket=CurrentDocket(),
    worker=CurrentWorker(),
    progress=Progress(),
) -> str:
    await progress.set_total(100)
    for i in range(100):
        await progress.increment()
        await progress.set_message(f"Processing chunk {i + 1}")
    return "Complete"
```

- `CurrentDocket()` — Docket instance for scheduling additional background work
- `CurrentWorker()` — Worker processing tasks (name, concurrency settings)
- `Progress()` — Atomic progress updates

### Custom Dependencies with `Depends()`

PATTERN: Wrap any callable with `Depends()` to inject its return value. Works with sync functions, async functions, and async context managers.

```python
from fastmcp.dependencies import Depends

def get_config() -> dict:
    return {"api_url": "https://api.example.com", "timeout": 30}

async def get_user_id() -> int:
    return 42

@mcp.tool
async def fetch_data(
    query: str,
    config: dict = Depends(get_config),
    user_id: int = Depends(get_user_id),
) -> str:
    return f"User {user_id} fetching '{query}' from {config['api_url']}"
```

#### Per-Request Caching

PATTERN: Dependencies are cached per request. If multiple parameters declare the same dependency, or nested dependencies share a common dependency, it resolves once per request and the same instance is reused.

```python
def get_db_connection():
    print("Connecting to database...")  # Printed only once per request

def get_user_repo(db=Depends(get_db_connection)):
    return {"db": db, "type": "user"}

def get_order_repo(db=Depends(get_db_connection)):
    return {"db": db, "type": "order"}

@mcp.tool
async def process_order(
    order_id: str,
    users=Depends(get_user_repo),
    orders=Depends(get_order_repo),
) -> str:
    # Both repos share the same db connection
    return f"Processed order {order_id}"
```

#### Resource Management (Cleanup)

PATTERN: Use an async context manager for dependencies that need teardown — database connections, file handles, HTTP clients. Cleanup runs after the function completes, even on error.

```python
from contextlib import asynccontextmanager
from fastmcp.dependencies import Depends

@asynccontextmanager
async def get_database():
    db = await connect_to_database()
    try:
        yield db
    finally:
        await db.close()

@mcp.tool
async def query_users(sql: str, db=Depends(get_database)) -> list:
    return await db.execute(sql)
```

#### Nested Dependencies

PATTERN: Dependencies can depend on other dependencies. FastMCP resolves them in the correct order and applies per-request caching across the entire dependency tree.

```python
def get_base_url() -> str:
    return "https://api.example.com"

def get_api_client(base_url: str = Depends(get_base_url)) -> dict:
    return {"base_url": base_url, "version": "v1"}

@mcp.tool
async def call_api(endpoint: str, client: dict = Depends(get_api_client)) -> str:
    return f"Calling {client['base_url']}/{client['version']}/{endpoint}"
```

### `uncalled-for` — The DI Engine

RULE: FastMCP's dependency injection is powered by the `uncalled-for` library (part of the Docket ecosystem, v3.1+). The `Depends()` API surface is unchanged from prior FastMCP versions — existing code requires no modification.

PATTERN: Core DI features (`Depends()`, `CurrentContext()`) work without installing `fastmcp[tasks]`. Background task dependencies (`CurrentDocket()`, `CurrentWorker()`, `Progress()`) require `fastmcp[tasks]`.

The underlying library [uncalled-for](https://github.com/chrisguidry/uncalled-for) is also available as a standalone package for use outside FastMCP. For advanced patterns — `TaskArgument()`, custom `Dependency` subclasses — see the [Docket dependency documentation](https://chrisguidry.github.io/docket/dependencies/).

SOURCE: `.worktrees/fastmcp/docs/servers/dependency-injection.mdx` (accessed 2026-03-17)
