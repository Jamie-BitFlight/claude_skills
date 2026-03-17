# FastMCP v3 Integrations Reference

How to connect FastMCP servers to external clients and frameworks — covers Anthropic API, OpenAI Responses API, Gemini SDK, FastAPI mounting, and Claude Code installation.

SOURCE: <https://gofastmcp.com/integrations/anthropic> (accessed 2026-03-05)
SOURCE: <https://gofastmcp.com/integrations/openai> (accessed 2026-03-05)
SOURCE: <https://gofastmcp.com/integrations/gemini> (accessed 2026-03-05)
SOURCE: <https://gofastmcp.com/integrations/fastapi> (accessed 2026-03-05)
SOURCE: <https://gofastmcp.com/integrations/claude-code> (accessed 2026-03-05)
SOURCE: <https://gofastmcp.com/patterns/cli> (accessed 2026-03-05)
SOURCE: <https://gofastmcp.com/integrations/propelauth> (accessed 2026-03-17) — PropelAuth integration (v3.1)
SOURCE: <https://gofastmcp.com/apps/prefab> (accessed 2026-03-17) — Prefab Apps (v3.1)
SOURCE: <https://gofastmcp.com/clients/sampling> (accessed 2026-03-17) — Google GenAI sampling handler (v3.1)

---

## Anthropic Messages API

SOURCE: <https://gofastmcp.com/integrations/anthropic>

The Anthropic Messages API supports MCP servers as remote tool sources via the `mcp_servers` parameter.

CONSTRAINT: The Anthropic MCP connector accesses **tools only** — it queries `list_tools` and does NOT support resources or prompts.

CONSTRAINT: The server must be deployed to a public URL. The `anthropic-beta: mcp-client-2025-04-04` header is required.

```python
import anthropic

url = "https://your-server-url.com"
client = anthropic.Anthropic()

response = client.beta.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Roll some dice!"}],
    mcp_servers=[
        {
            "type": "url",
            "url": f"{url}/mcp/",
            "name": "dice-server",
        }
    ],
    extra_headers={
        "anthropic-beta": "mcp-client-2025-04-04"
    },
)
```

### Anthropic with JWT Authentication

Pass `authorization_token` in the server config when the server requires bearer token auth:

```python
response = client.beta.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Roll some dice!"}],
    mcp_servers=[
        {
            "type": "url",
            "url": f"{url}/mcp/",
            "name": "dice-server",
            "authorization_token": access_token,
        }
    ],
    extra_headers={"anthropic-beta": "mcp-client-2025-04-04"},
)
```

Server-side JWT setup (development/testing only — use proper key management in production):

```python
from fastmcp import FastMCP
from fastmcp.server.auth import JWTVerifier
from fastmcp.server.auth.providers.jwt import RSAKeyPair

key_pair = RSAKeyPair.generate()
auth = JWTVerifier(public_key=key_pair.public_key, audience="my-server")
mcp = FastMCP(name="My Server", auth=auth)
```

---

## OpenAI Responses API

SOURCE: <https://gofastmcp.com/integrations/openai>

OpenAI's Responses API (NOT Completions or Assistants API) supports MCP servers as remote tool sources.

CONSTRAINT: The Responses API accesses **tools only** — resources and prompts are not supported.

CONSTRAINT: The server must be deployed to a public URL.

```python
from openai import OpenAI

url = "https://your-server-url.com"
client = OpenAI()

resp = client.responses.create(
    model="gpt-4.1",
    tools=[
        {
            "type": "mcp",
            "server_label": "my_server",
            "server_url": f"{url}/mcp/",
            "require_approval": "never",
        },
    ],
    input="Roll some dice!",
)
print(resp.output_text)
```

### OpenAI with Bearer Token Authentication

Pass the token in the `headers` field within the tool configuration:

```python
resp = client.responses.create(
    model="gpt-4.1",
    tools=[
        {
            "type": "mcp",
            "server_label": "my_server",
            "server_url": f"{url}/mcp/",
            "require_approval": "never",
            "headers": {
                "Authorization": f"Bearer {access_token}",
            },
        },
    ],
    input="Do something!",
)
```

---

## Google Gemini SDK

SOURCE: <https://gofastmcp.com/integrations/gemini>

Gemini's MCP integration requires a FastMCP `Client` session. Pass `mcp_client.session` directly to the Gemini SDK tools configuration.

CONSTRAINT: Gemini's MCP support accesses **tools only** — resources and prompts are not supported.

CONSTRAINT: The Gemini MCP integration is marked experimental in the SDK.

```python
from fastmcp import Client
from google import genai
import asyncio

mcp_client = Client("server.py")   # local stdio server
gemini_client = genai.Client()

async def main():
    async with mcp_client:
        response = await gemini_client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents="Roll 3 dice!",
            config=genai.types.GenerateContentConfig(
                temperature=0,
                tools=[mcp_client.session],
            ),
        )
        print(response.text)

asyncio.run(main())
```

For remote/authenticated servers, change only the client configuration:

```python
from fastmcp import Client
from fastmcp.client.auth import BearerAuth

mcp_client = Client(
    "https://my-server.com/mcp/",
    auth=BearerAuth("<your-token>"),
)
```

---

## FastAPI Integration

SOURCE: <https://gofastmcp.com/integrations/fastapi>

FastAPI integration supports two directions:

PATTERN: Generate an MCP server FROM a FastAPI app — converts endpoints into MCP tools via `OpenAPIProvider`.

PATTERN: Mount an MCP server INTO a FastAPI app — add MCP functionality to an existing web application.

CONSTRAINT: FastMCP does not include FastAPI as a dependency — install it separately.

### Generate MCP Server from FastAPI App

```python
from fastmcp import FastMCP
from fastapi import FastAPI

app = FastAPI(title="My API")

# ... define FastAPI routes ...

mcp = FastMCP.from_fastapi(app=app)

if __name__ == "__main__":
    mcp.run()
```

RULE: FastAPI operation IDs become MCP component names. Always specify explicit `operation_id` values on endpoints to get meaningful tool names.

```python
@app.get("/users/{user_id}", operation_id="get_user_by_id")
def get_user(user_id: int):
    return {"id": user_id}
```

### Mount MCP Server into FastAPI App

```python
from fastmcp import FastMCP
from fastapi import FastAPI

mcp = FastMCP("Analytics Tools")

@mcp.tool
def analyze_data(category: str) -> dict:
    """Analyze data for a category."""
    return {"category": category, "count": 42}

mcp_app = mcp.http_app(path="/mcp")

# Pass lifespan to FastAPI — required for session manager initialization
app = FastAPI(title="My App", lifespan=mcp_app.lifespan)
app.mount("/analytics", mcp_app)
# MCP endpoint available at: /analytics/mcp
```

CONSTRAINT: Always pass `lifespan=mcp_app.lifespan` to FastAPI when mounting. Omitting it prevents the session manager from initializing.

### Combining Lifespans

When your FastAPI app already has a lifespan:

```python
from fastapi import FastAPI
from fastmcp import FastMCP
from fastmcp.utilities.lifespan import combine_lifespans
from contextlib import asynccontextmanager

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # startup
    yield
    # shutdown

mcp = FastMCP("Tools")
mcp_app = mcp.http_app(path="/")

app = FastAPI(lifespan=combine_lifespans(app_lifespan, mcp_app.lifespan))
app.mount("/mcp", mcp_app)
```

### Serving Both REST and MCP from One App

```python
from fastmcp import FastMCP
from fastapi import FastAPI

mcp = FastMCP.from_fastapi(app=app, name="E-commerce MCP")
mcp_app = mcp.http_app(path="/mcp")

combined_app = FastAPI(
    title="E-commerce API with MCP",
    routes=[*mcp_app.routes, *app.routes],
    lifespan=mcp_app.lifespan,
)
```

---

## Claude Code Installation

SOURCE: <https://gofastmcp.com/integrations/claude-code>

### Automatic Installation via CLI

```bash
# Install with auto-detected server object
fastmcp install claude-code server.py

# Explicit entrypoint
fastmcp install claude-code server.py:mcp

# With environment variables
fastmcp install claude-code server.py \
  --server-name "My Server" \
  --env API_KEY=secret

# With dependencies
fastmcp install claude-code server.py --with pandas --with requests

# With requirements file
fastmcp install claude-code server.py --with-requirements requirements.txt

# From .env file
fastmcp install claude-code server.py --env-file .env
```

### Manual Configuration

```bash
# Add via claude mcp add (stdio transport)
claude mcp add my-server -- uv run --with fastmcp fastmcp run server.py

# With environment variables
claude mcp add my-server -e API_KEY=secret -- uv run --with fastmcp fastmcp run server.py

# With scope
claude mcp add my-server --scope user -- uv run --with fastmcp fastmcp run server.py
```

CONSTRAINT: Claude Code must be installed and the CLI available at `~/.claude/local/claude` for `fastmcp install claude-code` to work.

RULE: For remote FastMCP servers (HTTP/SSE transport), use Claude Code's native `claude mcp add --transport http` command rather than the install command. See `./claude-code-mcp-integration.md` for complete Claude Code MCP configuration reference.

---

## PropelAuth Authentication

PropelAuth is a `RemoteAuthProvider` using PropelAuth's OAuth and token introspection.

RULE: Create a Backend Integration in the PropelAuth dashboard first. See
<https://docs.propelauth.com> for dashboard setup.

For `PropelAuthProvider` constructor parameters, environment variables, introspection caching
configuration, and `get_access_token()` usage in tools, see
[./auth.md — PropelAuth Provider](./auth.md).

SOURCE: <https://gofastmcp.com/integrations/propelauth> (accessed 2026-03-17)

---

## Prefab Apps — Interactive Tool UIs

SOURCE: <https://gofastmcp.com/apps/prefab> (accessed 2026-03-17) — v3.1.0

Prefab is a declarative UI framework for building interactive MCP tool UIs in pure Python — no HTML or JavaScript required. Tools return Prefab components; FastMCP handles renderer registration and protocol wiring.

CONSTRAINT: Requires `fastmcp[apps]` extra. Prefab is in early active development — pin `prefab-ui` to a specific version in `pyproject.toml`.

```bash
pip install "fastmcp[apps]"
```

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

RULE: Use `app=True` on `@mcp.tool` to enable Prefab rendering. FastMCP registers a shared `ui://prefab/renderer.html` resource automatically — no additional configuration needed.

PATTERN: Wrap return in `ToolResult` when the LLM also needs to reason about the data — the component tree becomes `structured_content`; the text field is what the LLM reads.

For full Prefab component reference (charts, tables, forms, state management, reactive expressions), see the [Prefab UI documentation](https://prefab.prefect.io) and the [advanced patterns reference](./advanced.md).

---

## Google GenAI Sampling Handler

Alternative to the Anthropic and OpenAI sampling handlers, using Google's Gemini models.

Install: `pip install "fastmcp[gemini]"`

For `GoogleGenAISamplingHandler` usage and comparison with other handlers, see
[./advanced.md — Google GenAI Sampling Handler](./advanced.md).

SOURCE: <https://gofastmcp.com/clients/sampling> (accessed 2026-03-17)

---

## FastMCP CLI — Cross-Integration Tool

SOURCE: <https://gofastmcp.com/patterns/cli>

The `fastmcp` CLI bridges FastMCP servers with any MCP client:

```bash
# List tools on any server (URL, file, or stdio command)
fastmcp list http://localhost:8000/mcp
fastmcp list server.py
fastmcp list --command 'npx -y @modelcontextprotocol/server-github'

# Call a tool directly
fastmcp call server.py greet name=World
fastmcp call http://localhost:8000/mcp search query=hello limit=5

# Install into supported clients
fastmcp install claude-code server.py
fastmcp install claude-desktop server.py
fastmcp install cursor server.py
fastmcp install gemini-cli server.py

# Generate MCP JSON config for any client
fastmcp install mcp-json server.py --name "My Server" --with pandas

# Run server with auto-reload (development)
fastmcp run server.py --reload
```

PATTERN: Use `fastmcp list` and `fastmcp call` to give LLM clients without native MCP support access to MCP tools via shell commands.
