# FastMCP Advanced Features Reference

Background tasks, server-side elicitation, and advanced execution patterns — use this when building tools that run for seconds or minutes, require multi-turn user interaction, or need fine-grained execution control.

SOURCE: <https://gofastmcp.com/servers/tasks> (accessed 2026-03-05)

---

## Background Tasks

SOURCE: <https://gofastmcp.com/servers/tasks> (accessed 2026-03-05)

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

SOURCE: <https://gofastmcp.com/servers/tasks> (accessed 2026-03-05)

PATTERN: Enable background tasks globally for all server components:

```python
mcp = FastMCP("MyServer", tasks=True)
```

CONSTRAINT: If any synchronous tools exist on a server with `tasks=True`, those must explicitly set `task=False` to avoid errors.

SOURCE: <https://gofastmcp.com/servers/tasks> (accessed 2026-03-05)

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

SOURCE: <https://gofastmcp.com/servers/tasks> (accessed 2026-03-05)

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

SOURCE: <https://gofastmcp.com/servers/tasks> (accessed 2026-03-05)

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

SOURCE: <https://gofastmcp.com/servers/tasks> (accessed 2026-03-05)

---

## Server-Side Elicitation

SOURCE: <https://gofastmcp.com/servers/elicitation> (accessed 2026-03-05)

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

SOURCE: <https://gofastmcp.com/servers/elicitation> (accessed 2026-03-05)

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

SOURCE: <https://gofastmcp.com/servers/elicitation> (accessed 2026-03-05)

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

SOURCE: <https://gofastmcp.com/servers/elicitation> (accessed 2026-03-05)

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

SOURCE: <https://gofastmcp.com/servers/elicitation> (accessed 2026-03-05)

---

## Prefab Apps (EXPERIMENTAL)

Prefab Apps let tool functions return declarative UI components (bar charts, tables, forms) via
the `prefab-ui` library. FastMCP registers a shared renderer resource and serializes the component
tree as `structuredContent`.

Install: `pip install "fastmcp[apps]"`

PATTERN: `@mcp.tool(app=True)` decorator or `-> PrefabApp` return type annotation.

For full documentation — component reference, `ToolResult` dual-audience pattern, `fastmcp dev apps`
previewing, and coexistence with custom HTML apps — see [./apps.md](./apps.md).

SOURCE: <https://gofastmcp.com/apps/prefab> (accessed 2026-03-17)

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

For the full middleware reference — `Middleware` base class, hook hierarchy, built-in middleware
(Logging, RateLimiting, ErrorHandling, Retry, Caching, etc.), tag-based access control, and
server composition scope — see [./middleware.md](./middleware.md).

---

## Dependency Injection

SOURCE: <https://gofastmcp.com/servers/dependency-injection> (accessed 2026-03-17)

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

SOURCE: <https://gofastmcp.com/servers/dependency-injection> (accessed 2026-03-17)
