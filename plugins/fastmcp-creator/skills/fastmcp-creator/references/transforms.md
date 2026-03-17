# FastMCP v3 Transforms Reference

How transforms modify components as they flow from providers to clients. Covers all five built-in transforms and custom transform authoring.

SOURCE: <https://gofastmcp.com/servers/transforms/transforms>, `namespace.mdx`, `tool-transformation.mdx`, `resources-as-tools.mdx`, `prompts-as-tools.mdx`, `tool-search.mdx`, `code-mode.mdx`, <https://gofastmcp.com/servers/authorization> (visibility/Enabled), <https://github.com/PrefectHQ/fastmcp/blob/main/src/fastmcp/server/transforms/search/base.py> (search_result_serializer) (accessed 2026-03-17)

---

## Mental Model

Transforms are filters in a pipeline. Components flow from providers through transforms to reach clients:

```text
Provider -> [Transform A] -> [Transform B] -> Client
```

When listing components, transforms receive sequences and return transformed sequences. When a client requests a component by name, transforms work in reverse — mapping the client's requested name back to the original.

---

## Built-in Transforms

FastMCP provides the following built-in transforms:

| Transform | Version | Purpose |
|-----------|---------|---------|
| `Namespace` | v3.0.0 | Prefix component names to prevent conflicts |
| `ToolTransform` | v3.0.0 | Rename tools, modify descriptions, reshape arguments |
| `Enabled` (visibility) | v3.0.0 | Control which components are visible at runtime |
| `ResourcesAsTools` | v3.0.0 | Expose resources to tool-only clients |
| `PromptsAsTools` | v3.0.0 | Expose prompts to tool-only clients |
| `RegexSearchTransform` | v3.1.0 | Replace full catalog with regex-based on-demand search |
| `BM25SearchTransform` | v3.1.0 | Replace full catalog with BM25 relevance-ranked search |
| `CodeMode` (experimental) | v3.1.0 | Replace catalog with programmable search+execute meta-tools |

---

## Namespace Transform

RULE: Use `Namespace` to prefix all component names from a provider or server. The most common use is through `mcp.mount(server, namespace="name")`.

```python
from fastmcp import FastMCP

weather = FastMCP("Weather")
calendar = FastMCP("Calendar")

@weather.tool
def get_data() -> str:
    return "Weather data"

@calendar.tool
def get_data() -> str:
    return "Calendar data"

# Without namespacing, both tools are named "get_data" — conflict
main = FastMCP("Main")
main.mount(weather, namespace="weather")
main.mount(calendar, namespace="calendar")

# Clients see: weather_get_data, calendar_get_data
```

Naming rules:

| Component | Original | With `Namespace("api")` |
|-----------|----------|-------------------------|
| Tool | `my_tool` | `api_my_tool` |
| Prompt | `my_prompt` | `api_my_prompt` |
| Resource | `data://info` | `data://api/info` |
| Template | `data://{id}` | `data://api/{id}` |

PATTERN: Apply `Namespace` directly using `mcp.add_transform()` or `provider.add_transform()` for explicit control.

```python
from fastmcp.server.transforms import Namespace

mcp = FastMCP("Server")

@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

mcp.add_transform(Namespace("v1"))

# Tool is now: v1_greet
```

---

## ToolTransform

`ToolTransform` modifies tool schemas as they flow through a provider. Provide a dictionary mapping original tool names to their `ToolTransformConfig`.

```python
from fastmcp import FastMCP
from fastmcp.server.transforms import ToolTransform
from fastmcp.tools.tool_transform import ToolTransformConfig

mcp = FastMCP("Server")

@mcp.tool
def verbose_internal_data_fetcher(query: str) -> str:
    """Fetches data from the internal database."""
    return f"Results for: {query}"

mcp.add_transform(ToolTransform({
    "verbose_internal_data_fetcher": ToolTransformConfig(
        name="search",
        description="Search the database.",
    )
}))

# Clients see "search" with the cleaner description
```

PATTERN: Use `Tool.from_tool()` for immediate transformation when you have direct access to the tool object.

```python
from fastmcp.tools import Tool, tool
from fastmcp.tools.tool_transform import ArgTransform

@tool
def search(q: str, limit: int = 10) -> list[str]:
    """Search for items."""
    return [f"Result {i} for {q}" for i in range(limit)]

better_search = Tool.from_tool(
    search,
    name="find_items",
    description="Find items matching your search query.",
    transform_args={
        "q": ArgTransform(name="query", description="The search terms to look for."),
        "limit": ArgTransform(name="max_results"),
    },
)

mcp = FastMCP("Server")
mcp.add_tool(better_search)
```

### Tool-Level Modification Options

| Option | Description |
|--------|-------------|
| `name` | New name for the tool |
| `description` | New description |
| `title` | Human-readable title |
| `tags` | Set of tags for categorization |
| `annotations` | MCP ToolAnnotations |
| `meta` | Custom metadata dictionary |
| `enabled` | Whether the tool is visible to clients |

### Argument-Level Options (via ArgTransform)

| Option | Description |
|--------|-------------|
| `name` | Rename the argument |
| `description` | New description |
| `default` | New default value |
| `default_factory` | Callable that generates a default (requires `hide=True`) |
| `hide` | Remove from client-visible schema (inject as constant) |
| `required` | Make an optional argument required |
| `type` | Change the argument's type |
| `examples` | Example values for the argument |

PATTERN: Hide arguments to inject constants or secrets.

```python
from fastmcp.tools.tool_transform import ArgTransform
import uuid

transform_args = {
    "api_key": ArgTransform(hide=True, default="secret-key"),
    "request_id": ArgTransform(hide=True, default_factory=lambda: str(uuid.uuid4())),
}
```

CONSTRAINT: `default_factory` requires `hide=True`. Visible arguments need static defaults representable in JSON Schema.

### Custom Transform Functions

For advanced scenarios, provide a `transform_fn` that intercepts tool execution.

```python
from fastmcp.tools import Tool, tool
from fastmcp.tools.tool_transform import forward, ArgTransform

@tool
def divide(a: float, b: float) -> float:
    """Divide a by b."""
    return a / b

async def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        raise ValueError("Cannot divide by zero")
    return await forward(numerator=numerator, denominator=denominator)

safe_division = Tool.from_tool(
    divide,
    name="safe_divide",
    transform_fn=safe_divide,
    transform_args={
        "a": ArgTransform(name="numerator"),
        "b": ArgTransform(name="denominator"),
    },
)
```

`forward()` handles argument mapping automatically using transformed names — call it with the renamed parameter names and it maps back to the original function's parameters. Use `forward_raw()` for direct calls with the original parameter names, bypassing the mapping entirely.

### Context-Aware Tool Factories

`Tool.from_tool()` composes with factory functions to create per-connection tool variants. A factory returns a fully configured `Tool` object for a specific runtime context — for example, hiding a `user_id` argument and injecting the current user's ID at connection time.

```python
from fastmcp import FastMCP
from fastmcp.tools import Tool, tool
from fastmcp.tools.tool_transform import ArgTransform

@tool
def get_user_data(user_id: str, query: str) -> str:
    """Fetch data for a specific user."""
    return f"Data for user {user_id}: {query}"


def create_user_tool(user_id: str) -> Tool:
    """Factory that creates a user-specific version of get_user_data."""
    return Tool.from_tool(
        get_user_data,
        name="get_my_data",
        description="Fetch your data. No need to specify a user ID.",
        transform_args={
            "user_id": ArgTransform(hide=True, default=user_id),
        },
    )


mcp = FastMCP("User Server")
current_user_id = "user-123"  # from auth context
mcp.add_tool(create_user_tool(current_user_id))

# Clients see "get_my_data(query: str)" — user_id is injected automatically
```

PATTERN: Use this for multi-tenant servers where each connection gets tools pre-configured with identity, or for wrapping generic tools with environment-specific defaults.

SOURCE: [https://gofastmcp.com/servers/transforms/tool-transformation](https://gofastmcp.com/servers/transforms/tool-transformation) (accessed 2026-03-17)

---

## Enabled (Visibility Transform)

FastMCP uses enable/disable APIs to control component visibility at runtime. Disabled components do not appear in list responses and cannot be called.

```python
from fastmcp import FastMCP

mcp = FastMCP("MyServer")

@mcp.tool(tags={"admin"})
def delete_all() -> str:
    return "Deleted"

@mcp.tool(tags={"public"})
def get_status() -> str:
    return "OK"

# Disable by tag
mcp.disable(tags={"admin"})

# Disable by component key
mcp.disable(keys={"tool:delete_all"})

# Allowlist: only enable components with specific tags
mcp.enable(tags={"public"}, only=True)
```

PATTERN: Control visibility per-session using `ctx.enable_components()` and `ctx.disable_components()` from within a tool.

```python
from fastmcp import FastMCP, Context

@mcp.tool
async def activate_namespace(namespace: str, ctx: Context) -> str:
    """Enable all tools in the given namespace tag."""
    await ctx.enable_components(tags={namespace})
    return f"Enabled components tagged '{namespace}'"
```

RULE: Component-level `enabled=False` on decorators is deprecated in v3.0.0. Use `mcp.disable()` instead.

---

## ResourcesAsTools

`ResourcesAsTools` bridges the gap for tool-only clients that cannot use the MCP resource protocol. It generates two tools that clients can call:

- `list_resources` — returns JSON describing all available resources and templates
- `read_resource` — reads a specific resource by URI

```python
from fastmcp import FastMCP
from fastmcp.server.transforms import ResourcesAsTools

mcp = FastMCP("My Server")

@mcp.resource("config://app")
def app_config() -> str:
    """Application configuration."""
    return '{"app_name": "My App", "version": "1.0.0"}'

@mcp.resource("user://{user_id}/profile")
def user_profile(user_id: str) -> str:
    """Get a user's profile by ID."""
    return f'{{"user_id": "{user_id}"}}'

# Add the transform — creates list_resources and read_resource tools
mcp.add_transform(ResourcesAsTools(mcp))
```

PATTERN: `list_resources` output distinguishes static resources (field `"uri"`) from templates (field `"uri_template"`).

PATTERN: Binary resources are automatically base64-encoded in `read_resource` responses.

---

## PromptsAsTools

`PromptsAsTools` bridges the gap for tool-only clients that cannot use the MCP prompt protocol. It generates two tools:

- `list_prompts` — returns JSON describing all prompts and their arguments
- `get_prompt` — renders a specific prompt with provided arguments

```python
from fastmcp import FastMCP
from fastmcp.server.transforms import PromptsAsTools

mcp = FastMCP("My Server")

@mcp.prompt
def analyze_code(code: str, language: str = "python") -> str:
    """Analyze code for potential issues."""
    return f"Analyze this {language} code:\n{code}"

# Add the transform — creates list_prompts and get_prompt tools
mcp.add_transform(PromptsAsTools(mcp))
```

---

## Provider-Level vs Server-Level Transforms

Transforms can be applied at two levels.

**Provider-level**: Affects only components from that provider. Runs first.

```python
from fastmcp.server.providers import FastMCPProvider
from fastmcp.server.transforms import Namespace, ToolTransform
from fastmcp.tools.tool_transform import ToolTransformConfig

sub_server = FastMCP("Sub")

@sub_server.tool
def process(data: str) -> str:
    return f"Processed: {data}"

provider = FastMCPProvider(sub_server)
provider.add_transform(Namespace("api"))
provider.add_transform(ToolTransform({
    "api_process": ToolTransformConfig(description="Process data through the API"),
}))

main = FastMCP("Main", providers=[provider])
# Tool is now: api_process with updated description
```

PATTERN: The `mount()` method returns a provider reference, letting you add transforms directly.

```python
main = FastMCP("Main")
mount = main.mount(sub_server, namespace="api")
mount.add_transform(ToolTransform({...}))
```

**Server-level**: Affects all components from all providers. Runs after provider transforms.

```python
# API versioning — prefix all tools
mcp.add_transform(Namespace("v1"))
```

PATTERN: Pass transforms directly to the `FastMCP` constructor via the `transforms=` keyword argument (v3.1.0+). This is equivalent to calling `add_transform()` for each entry after construction.

```python
from fastmcp import FastMCP
from fastmcp.server.transforms.search import BM25SearchTransform

mcp = FastMCP("Server", transforms=[BM25SearchTransform()])
```

SOURCE: [https://gofastmcp.com/servers/transforms](https://gofastmcp.com/servers/transforms) (accessed 2026-03-17)

### Transform Order

Transforms stack in the order added. First added is innermost (closest to the provider).

```python
provider.add_transform(Namespace("api"))           # Applied first
provider.add_transform(ToolTransform({             # Sees namespaced names
    "api_verbose_name": ToolTransformConfig(name="short"),
}))

# Flow: "verbose_name" -> "api_verbose_name" -> "short"
```

---

## Custom Transforms

Subclass `Transform` and override the methods you need. Leave unneeded methods as the pass-through default.

```python
from collections.abc import Sequence
from fastmcp.server.transforms import Transform, GetToolNext
from fastmcp.tools.tool import Tool

class TagFilter(Transform):
    """Filter tools to only those with specific tags."""

    def __init__(self, required_tags: set[str]):
        self.required_tags = required_tags

    async def list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]:
        return [t for t in tools if t.tags & self.required_tags]

    async def get_tool(self, name: str, call_next: GetToolNext) -> Tool | None:
        tool = await call_next(name)
        if tool and tool.tags & self.required_tags:
            return tool
        return None
```

Transform method signatures:

| Method | Pattern | Purpose |
|--------|---------|---------|
| `list_tools(tools)` | Pure function | Transform the sequence of tools |
| `get_tool(name, call_next)` | Middleware | Transform lookup by name |
| `list_resources(resources)` | Pure function | Transform the sequence of resources |
| `get_resource(uri, call_next)` | Middleware | Transform lookup by URI |
| `list_resource_templates(templates)` | Pure function | Transform the sequence of resource templates |
| `get_resource_template(uri, call_next)` | Middleware | Transform template lookup by URI |
| `list_prompts(prompts)` | Pure function | Transform the sequence of prompts |
| `get_prompt(name, call_next)` | Middleware | Transform lookup by name |

RULE: When implementing `get_*` methods, use `call_next` for routing. Map the client's requested name back to the original before calling `call_next()`.

PATTERN: Use `model_copy(update={...})` to produce modified Tool objects while keeping the underlying execution unchanged.

```python
class PrefixTransform(Transform):
    def __init__(self, prefix: str):
        self.prefix = prefix

    async def list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]:
        return [t.model_copy(update={"name": f"{self.prefix}_{t.name}"}) for t in tools]

    async def get_tool(self, name: str, call_next: GetToolNext) -> Tool | None:
        if not name.startswith(f"{self.prefix}_"):
            return None
        original = name[len(self.prefix) + 1:]
        tool = await call_next(original)
        if tool:
            return tool.model_copy(update={"name": name})
        return None
```

---

## Tool Search Transforms (v3.1.0)

When a server exposes hundreds or thousands of tools, sending the full catalog to an LLM wastes tokens and degrades tool selection accuracy. Search transforms solve this by replacing the tool listing with a search interface — the LLM discovers tools on demand instead of receiving everything upfront.

SOURCE: [https://gofastmcp.com/servers/transforms/tool-search](https://gofastmcp.com/servers/transforms/tool-search) (accessed 2026-03-17)

### How It Works

When a search transform is active, `list_tools()` returns two synthetic tools instead of the full catalog:

- `search_tools` — finds tools matching a query and returns their full definitions
- `call_tool` — executes a discovered tool by name

The original tools remain fully callable. They are hidden from the listing but not from access — the search transform controls _discovery_, not _access_. Both synthetic tools search across tool names, descriptions, parameter names, and parameter descriptions.

### RegexSearchTransform

`RegexSearchTransform` matches tools against a regex pattern using case-insensitive `re.search`. It has zero overhead and no index to build. The `search_tools` call accepts a `pattern` parameter (a regex string).

```python
from fastmcp import FastMCP
from fastmcp.server.transforms.search import RegexSearchTransform

mcp = FastMCP("My Server", transforms=[RegexSearchTransform()])

@mcp.tool
def search_database(query: str, limit: int = 10) -> list[dict]:
    """Search the database for records matching the query."""
    ...

@mcp.tool
def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email to the given recipient."""
    ...
```

```python
# LLM calls search_tools with a regex pattern
result = await client.call_tool("search_tools", {"pattern": "database"})
# Returns: search_database

result = await client.call_tool("search_tools", {"pattern": "send.*email|notify"})
# Returns: send_email
```

Results are returned in catalog order. Invalid regex patterns return an empty list rather than raising an error.

### BM25SearchTransform

`BM25SearchTransform` ranks tools by relevance using the BM25 Okapi algorithm. Better for natural language queries — scores each tool on term frequency and document rarity, returning results ranked by relevance rather than filtering by match/no-match.

Requires: `pip install "fastmcp[search]"`

```python
from fastmcp import FastMCP
from fastmcp.server.transforms.search import BM25SearchTransform

mcp = FastMCP("My Server", transforms=[BM25SearchTransform()])
```

```python
# LLM calls search_tools with natural language
result = await client.call_tool("search_tools", {
    "query": "tools for deleting things from the database"
})
# Returns: delete_record ranked first
```

BM25 builds an in-memory index lazily on the first search and automatically rebuilds it whenever the tool catalog changes (staleness is detected by hashing all searchable text).

### Choosing Between Regex and BM25

Use **regex** when the LLM can construct targeted patterns and you want deterministic, predictable results. Use **BM25** when the LLM describes needs in natural language, or when tool catalog descriptions have nuanced content where relevance ranking adds value.

### Search Transform Configuration

Both transforms accept the same options:

```python
from fastmcp.server.transforms.search import RegexSearchTransform

mcp.add_transform(RegexSearchTransform(
    max_results=10,                  # default 5; top N results
    always_visible=["help", "status"],  # pinned tools always in list_tools
    search_tool_name="find_tools",   # rename to avoid conflicts
    call_tool_name="run_tool",       # rename to avoid conflicts
    search_result_serializer=my_fn,  # custom output format (see below)
))
```

| Option | Default | Description |
|--------|---------|-------------|
| `max_results` | `5` | Maximum tools returned per search |
| `always_visible` | `[]` | Tool names pinned in `list_tools` alongside synthetic tools |
| `search_tool_name` | `"search_tools"` | Name of the generated search tool |
| `call_tool_name` | `"call_tool"` | Name of the generated call-tool proxy |
| `search_result_serializer` | JSON format | Custom serializer for search output |

PATTERN: Pinned tools appear directly in `list_tools` so the LLM can call them without searching. They are excluded from search results to avoid duplication.

### `search_result_serializer` Hook

Override how search results are formatted by providing a callable. The callable receives a sequence of `Tool` objects and returns any value (or an awaitable that resolves to any value). FastMCP includes two built-in serializers:

- `serialize_tools_for_output_json` (default) — same dict format as `list_tools`
- `serialize_tools_for_output_markdown` — compact markdown using ~65-70% fewer tokens than JSON

```python
from fastmcp.server.transforms.search.base import serialize_tools_for_output_markdown
from fastmcp.server.transforms.search import BM25SearchTransform

mcp.add_transform(BM25SearchTransform(
    search_result_serializer=serialize_tools_for_output_markdown,
))
```

Custom serializers can be sync or async:

```python
async def my_serializer(tools):
    return [{"name": t.name, "summary": t.description} for t in tools]

mcp.add_transform(RegexSearchTransform(search_result_serializer=my_serializer))
```

### The `call_tool` Proxy

The `call_tool` proxy forwards calls to the real tool through the server's normal pipeline — including transforms and middleware. It rejects attempts to call the synthetic tools themselves (`call_tool(name="call_tool")` raises an error).

RULE: Tools discovered through search can also be called directly via `client.call_tool("tool_name", {...})` without the proxy. The proxy exists for LLMs that only know about tools returned by `list_tools` and need to invoke discovered tools through a visible tool.

### Auth and Visibility

Search results respect the full authorization pipeline. Tools filtered by middleware, visibility transforms, or component-level auth checks do not appear in search results.

```python
from fastmcp.server.transforms import Visibility
from fastmcp.server.transforms.search import RegexSearchTransform

mcp = FastMCP("My Server")

mcp.add_transform(Visibility(False, tags={"admin"}))  # admin tools hidden
mcp.add_transform(RegexSearchTransform())              # search sees only visible tools
```

Session-level visibility changes via `ctx.disable_components()` are reflected immediately in search results.

---

## CodeMode Transform (Experimental, v3.1.0)

CodeMode is an experimental transform that replaces your tool catalog with meta-tools for discovering tools and writing Python scripts that orchestrate them in a sandbox. The LLM writes code once; intermediate results stay inside the sandbox without flowing through the context window.

CONSTRAINT: This feature is experimental. The core interface is stable, but discovery tool parameters may evolve.

Requires: `pip install "fastmcp[code-mode]"`

SOURCE: [https://gofastmcp.com/servers/transforms/code-mode](https://gofastmcp.com/servers/transforms/code-mode) (accessed 2026-03-17)

### Getting Started

```python
from fastmcp import FastMCP
from fastmcp.experimental.transforms.code_mode import CodeMode

mcp = FastMCP("Server", transforms=[CodeMode()])

@mcp.tool
def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y

@mcp.tool
def multiply(x: int, y: int) -> int:
    """Multiply two numbers."""
    return x * y
```

Clients connecting to this server no longer see `add` and `multiply` directly. Instead they see the meta-tools CodeMode provides. The original tools remain fully functional — accessed through the CodeMode layer.

### Meta-Tools Provided

By default, CodeMode exposes three tools:

- `search` — finds tools by natural-language BM25 query
- `get_schema` — returns parameter details for specific tools by name
- `execute` — runs LLM-written Python code in a sandbox

Inside the sandbox, `await call_tool(name, params)` is the only available function. The LLM uses it to chain tool calls and `return` a final result:

```python
# LLM writes and submits this code via the execute tool
a = await call_tool("add", {"x": 3, "y": 4})
b = await call_tool("multiply", {"x": a, "y": 2})
return b
```

### Discovery Tools

CodeMode ships with four built-in discovery tools: `Search`, `GetSchemas`, `GetTags`, and `ListTools`. By default, only `Search` and `GetSchemas` are enabled. Each supports a `default_detail` parameter setting verbosity, and the LLM can override detail level per call.

#### Detail Levels

`Search` and `GetSchemas` share the same three detail levels:

| Level | Output | Token cost |
|-------|--------|------------|
| `"brief"` | Tool names and one-line descriptions | Cheapest — good for scanning |
| `"detailed"` | Compact markdown with parameter names, types, required markers | Medium — often enough to write code |
| `"full"` | Complete JSON schema | Most expensive — everything |

`Search` defaults to `"brief"`. `GetSchemas` defaults to `"detailed"`.

#### Search

`Search` finds tools by natural-language BM25 query. At `"brief"` detail, results include tool names and descriptions — enough to decide which tools to inspect. Results include an annotation like `"2 of 10 tools:"` when fewer than the full catalog is returned, so the LLM knows more tools exist.

Cap result count with `default_limit`. The LLM can override per call:

```python
Search(default_limit=5)  # return at most 5 results per search
```

If tools have tags, `Search` accepts a `tags` parameter so the LLM can narrow results to specific categories before searching.

#### GetSchemas

`GetSchemas` returns parameter details for specific tools by name. At `"detailed"` level it renders compact markdown with parameter names, types, and required markers. At `"full"` it returns the complete JSON schema — useful for deeply nested parameters the compact format doesn't capture.

#### GetTags

`GetTags` lets the LLM browse tools by tag metadata. At `"brief"` detail, the LLM sees tag names with counts. At `"full"`, it sees tools listed under each tag:

```text
- math (3 tools)
- text (2 tools)
- untagged (1 tool)
```

Not included by default — add it when browsing by category helps orient the LLM in a large catalog. The LLM browses tags first, then passes specific tags into `Search` to narrow results.

#### ListTools

`ListTools` dumps the entire catalog at whatever detail level the LLM requests (defaulting to `"brief"`). Not included by default — for large catalogs, search-based discovery is more token-efficient. For smaller catalogs (under ~20 tools), letting the LLM see everything upfront can be faster than multiple search round-trips.

```python
from fastmcp.experimental.transforms.code_mode import CodeMode, ListTools, GetSchemas

code_mode = CodeMode(
    discovery_tools=[ListTools(), GetSchemas()],
)
```

### Discovery Patterns

**Three-stage (default)** — LLM searches for candidates, inspects schemas, then executes. Best for large or complex tool sets where minimizing context usage matters.

```python
mcp = FastMCP("Server", transforms=[CodeMode()])
```

**Four-stage with tag browsing** — add `GetTags` when tools are organized by tags, enabling the LLM to orient by category before searching.

```python
from fastmcp.experimental.transforms.code_mode import CodeMode, GetTags, Search, GetSchemas

code_mode = CodeMode(
    discovery_tools=[GetTags(), Search(), GetSchemas()],
)
mcp = FastMCP("Server", transforms=[code_mode])
```

**Two-stage** — search returns parameter schemas inline; LLM goes straight to execute. Best for smaller catalogs where the extra tokens per search result are worth one fewer round-trip. `GetSchemas` is still available as a fallback for `detail="full"` on complex tools.

```python
from fastmcp.experimental.transforms.code_mode import CodeMode, Search, GetSchemas

code_mode = CodeMode(
    discovery_tools=[Search(default_detail="detailed"), GetSchemas()],
)
mcp = FastMCP("Server", transforms=[code_mode])
```

**Single-stage** — no discovery tools; tool instructions baked into the execute description. Best for very simple servers where the LLM already knows what tools are available.

```python
from fastmcp.experimental.transforms.code_mode import CodeMode

code_mode = CodeMode(
    discovery_tools=[],
    execute_description=(
        "Available tools:\n"
        "- add(x: int, y: int) -> int: Add two numbers\n"
        "Write Python using `await call_tool(name, params)` and `return` the result."
    ),
)
mcp = FastMCP("Server", transforms=[code_mode])
```

### Custom Discovery Tools

Discovery tools are composable — mix built-ins with your own. Each custom discovery tool is a callable that receives a `GetToolCatalog` accessor and returns a `Tool`. The catalog accessor is a function (not the catalog itself) because the catalog is request-scoped — different users may see different tools based on auth.

```python
from fastmcp.experimental.transforms.code_mode import CodeMode, GetToolCatalog, GetSchemas
from fastmcp.server.context import Context
from fastmcp.tools.tool import Tool

def list_all_tools(get_catalog: GetToolCatalog) -> Tool:
    async def list_tools(ctx: Context) -> str:
        """List all available tool names."""
        tools = await get_catalog(ctx)
        return ", ".join(t.name for t in tools)

    return Tool.from_function(fn=list_tools, name="list_tools")

code_mode = CodeMode(discovery_tools=[list_all_tools, GetSchemas()])
```

The docstring of each discovery tool's inner function becomes the tool's description — write it to explain what the tool returns and when the LLM should call it.

### Sandbox Configuration

The default `MontySandboxProvider` enforces execution limits. Without limits, LLM-generated scripts can run indefinitely.

```python
from fastmcp.experimental.transforms.code_mode import CodeMode, MontySandboxProvider

sandbox = MontySandboxProvider(
    limits={"max_duration_secs": 10, "max_memory": 50_000_000},
)

mcp = FastMCP("Server", transforms=[CodeMode(sandbox_provider=sandbox)])
```

| Key | Type | Description |
|-----|------|-------------|
| `max_duration_secs` | `float` | Maximum wall-clock execution time |
| `max_memory` | `int` | Memory ceiling in bytes |
| `max_allocations` | `int` | Cap on total object allocations |
| `max_recursion_depth` | `int` | Maximum recursion depth |
| `gc_interval` | `int` | Garbage collection frequency |

All keys are optional — omit any to leave that dimension uncapped.

### Custom Sandbox Providers

Replace the default sandbox with any object implementing the `SandboxProvider` protocol:

```python
from collections.abc import Callable
from typing import Any

from fastmcp.experimental.transforms.code_mode import CodeMode, SandboxProvider

class RemoteSandboxProvider:
    async def run(
        self,
        code: str,
        *,
        inputs: dict[str, Any] | None = None,
        external_functions: dict[str, Callable[..., Any]] | None = None,
    ) -> Any:
        # Send code to your remote sandbox runtime
        ...

mcp = FastMCP("Server", transforms=[CodeMode(sandbox_provider=RemoteSandboxProvider())])
```

The `external_functions` dict contains async callables injected into the sandbox scope — `execute` uses this to provide `call_tool`.

### Custom Tool Names

```python
from fastmcp.experimental.transforms.code_mode import CodeMode, Search, GetSchemas

code_mode = CodeMode(
    discovery_tools=[
        Search(name="find_tools"),
        GetSchemas(name="describe"),
    ],
    execute_tool_name="run_workflow",
)
```

---

## Cross-Reference

- Provider configuration: [./providers.md](./providers.md)
- Server core setup: [./server-core.md](./server-core.md)
- Scope-based auth (restricts visibility by scope): [./auth.md](./auth.md)
