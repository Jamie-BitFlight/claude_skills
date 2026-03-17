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

## Dependency Injection — `uncalled-for` Library

SOURCE: `https://gofastmcp.com/servers/dependencies` (accessed 2026-03-17)

UPDATE: FastMCP replaced its vendored dependency injection implementation with the `uncalled-for` library (part of the Docket ecosystem). The `Depends()` API surface is unchanged — existing code requires no modification.

RULE: The `Depends()`, `CurrentContext()`, `CurrentFastMCP()`, `CurrentRequest()`, `CurrentHeaders()`, `CurrentAccessToken()`, and `Progress()` APIs all remain the same. Users should not notice any difference from prior FastMCP versions.

```python
from fastmcp import FastMCP
from fastmcp.dependencies import Depends

mcp = FastMCP("Demo")


def get_config() -> dict:
    return {"api_url": "https://api.example.com", "timeout": 30}


@mcp.tool
async def fetch_data(
    query: str,
    config: dict = Depends(get_config),
) -> str:
    return f"Fetching '{query}' from {config['api_url']}"
```

PATTERN: Core DI features (`Depends()`, `CurrentContext()`) work without installing `fastmcp[tasks]`. Background task dependencies (`CurrentDocket()`, `CurrentWorker()`, `Progress()`) still require `fastmcp[tasks]`.

The underlying library is [uncalled-for](https://github.com/chrisguidry/uncalled-for), also available as a standalone package for use outside FastMCP.

SOURCE: `https://gofastmcp.com/servers/dependencies` (accessed 2026-03-17)
