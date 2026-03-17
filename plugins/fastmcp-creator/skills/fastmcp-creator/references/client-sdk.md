# FastMCP Client SDK Reference

Programmatic client for connecting to MCP servers — use this when building test harnesses, deterministic integrations, or agentic systems that call FastMCP tools programmatically.

SOURCE: <https://gofastmcp.com/clients/client> (accessed 2026-03-05)

---

## CLI Client Commands

SOURCE: <https://gofastmcp.com/cli/client> (accessed 2026-03-17)

The FastMCP CLI can act as an MCP client — connecting to any server (local or remote) to list tools, call them, and discover configured servers. Useful for development, debugging, scripting, and giving shell-capable LLM agents MCP access.

### fastmcp list

Connects to a server and prints its tools as function signatures with parameter names, types, and descriptions:

```bash
fastmcp list http://localhost:8000/mcp
fastmcp list server.py
fastmcp list weather          # name-based resolution
fastmcp list claude-code:my-server  # source:name disambiguation
```

Show full JSON Schema for inputs or outputs with `--input-schema` / `--output-schema`:

```bash
fastmcp list server.py --input-schema
fastmcp list server.py --output-schema
```

Include resources and prompts (tools only by default):

```bash
fastmcp list server.py --resources --prompts
```

Machine-readable output for LLM consumption or automation:

```bash
fastmcp list server.py --json
```

**Options:**

| Option | Flag | Description |
| ------ | ---- | ----------- |
| Command | `--command` | Connect via stdio (e.g., `'npx -y @mcp/server'`) |
| Transport | `--transport`, `-t` | Force `http` or `sse` for URL targets |
| Resources | `--resources` | Include resources in output |
| Prompts | `--prompts` | Include prompts in output |
| Input Schema | `--input-schema` | Show full input schemas |
| Output Schema | `--output-schema` | Show full output schemas |
| JSON | `--json` | Structured JSON output |
| Timeout | `--timeout` | Connection timeout in seconds |
| Auth | `--auth` | `oauth` (default for HTTP), a bearer token, or `none` |

### fastmcp call

Invokes a single tool on a server. Pass arguments as `key=value` pairs — the CLI fetches the schema and coerces string values to the right types automatically:

```bash
fastmcp call server.py greet name=World
fastmcp call http://localhost:8000/mcp search query=hello limit=5
```

Type coercion is schema-driven: `"5"` becomes integer `5`. Booleans accept `true`/`false`, `yes`/`no`, `1`/`0`. Arrays and objects are parsed as JSON.

**Complex arguments** — pass a JSON object positionally or use `--input-json` as a base dict merged with `key=value` overrides:

```bash
# Positional JSON object
fastmcp call server.py create_item '{"name": "Widget", "tags": ["sale"], "metadata": {"color": "blue"}}'

# --input-json with key=value overrides
fastmcp call server.py search --input-json '{"query": "hello", "limit": 5}' limit=10
```

**Fuzzy typo correction** — if you misspell a tool name, the CLI suggests corrections automatically. Missing required arguments produce a clear message with the tool's signature.

**Structured output:**

```bash
fastmcp call server.py get_weather city=London --json
```

**Interactive elicitation** — when a tool requests additional input during execution, the CLI prompts you in the terminal showing each field's name, type, and whether it's required. Type `decline` to skip a field or `cancel` to abort the call.

**Options:**

| Option | Flag | Description |
| ------ | ---- | ----------- |
| Command | `--command` | Connect via stdio |
| Transport | `--transport`, `-t` | Force `http` or `sse` |
| Input JSON | `--input-json` | Base arguments as JSON (merged with `key=value` pairs) |
| JSON | `--json` | Raw JSON output |
| Timeout | `--timeout` | Connection timeout in seconds |
| Auth | `--auth` | `oauth`, a bearer token, or `none` |

### fastmcp discover

Scans your machine for MCP servers configured in editors and tools:

```bash
fastmcp discover
fastmcp discover --source claude-code
fastmcp discover --source cursor --source gemini --json
```

Sources scanned:

- **Claude Desktop** — `claude_desktop_config.json`
- **Claude Code** — `~/.claude.json`
- **Cursor** — `.cursor/mcp.json` (walks up from current directory)
- **Gemini CLI** — `~/.gemini/settings.json`
- **Goose** — `~/.config/goose/config.yaml`
- **Project** — `./mcp.json` in the current directory

Any server that appears here can be used by name with `list`, `call`, and other commands — no need to copy URLs or paths.

### Name-Based Server Resolution

If servers are configured in an editor or tool, refer to them by name — FastMCP scans configs from Claude Desktop, Claude Code, Cursor, Gemini CLI, and Goose:

```bash
fastmcp list weather
fastmcp call weather get_forecast city=London
```

When the same name appears in multiple configs, use `source:name` to disambiguate:

```bash
fastmcp list claude-code:my-server
fastmcp call cursor:weather get_forecast city=London
```

### Authentication (CLI)

For HTTP targets, the CLI enables OAuth authentication by default. Pass `--auth none` to skip for local dev servers, or pass a bearer token directly:

```bash
# Skip auth entirely
fastmcp call http://localhost:8000/mcp my_tool --auth none

# Bearer token
fastmcp list http://localhost:8000/mcp --auth "Bearer sk-..."
```

SOURCE: <https://gofastmcp.com/cli/overview> (accessed 2026-03-17)

---

## Creating a Client

RULE: Always use `async with client:` for connection lifecycle management. Client operations require an active connection context.

```python
from fastmcp import Client, FastMCP

# In-memory server — ideal for testing (no network or subprocess)
server = FastMCP("TestServer")
client = Client(server)

# HTTP server — production remote endpoint
client = Client("https://example.com/mcp")

# Local Python script — stdio transport inferred from file path
client = Client("my_mcp_server.py")

async def main():
    async with client:
        await client.ping()
        tools = await client.list_tools()
        result = await client.call_tool("example_tool", {"param": "value"})
        print(result)
```

SOURCE: <https://gofastmcp.com/clients/client> (accessed 2026-03-05)

---

## Transport Selection

SOURCE: <https://gofastmcp.com/clients/transports> (accessed 2026-03-05)

### In-Memory Transport

PATTERN: Use `Client(server)` passing a `FastMCP` instance directly. Shares the same process memory — environment variables are visible to the server.

```python
from fastmcp import FastMCP, Client

mcp = FastMCP("TestServer")

@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

client = Client(mcp)

async with client:
    result = await client.call_tool("greet", {"name": "World"})
```

CONSTRAINT: Unlike STDIO transports, in-memory servers share the same memory space and environment variables as your client code.

SOURCE: <https://gofastmcp.com/clients/transports> (accessed 2026-03-05)

### STDIO Transport

CONSTRAINT: STDIO servers run in isolated environments by default. They do NOT inherit your shell's environment variables. Pass required configuration explicitly.

```python
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

transport = StdioTransport(
    command="python",
    args=["my_server.py", "--verbose"],
    env={"API_KEY": "secret", "LOG_LEVEL": "DEBUG"},
    cwd="/path/to/server"
)
client = Client(transport)
```

PATTERN: Selective environment forwarding — pass only what the server needs:

```python
import os
from fastmcp.client.transports import StdioTransport

required_vars = ["API_KEY", "DATABASE_URL", "REDIS_HOST"]
env = {var: os.environ[var] for var in required_vars if var in os.environ}

transport = StdioTransport(command="python", args=["server.py"], env=env)
client = Client(transport)
```

PATTERN: Session persistence — STDIO transports keep the subprocess alive across multiple `async with` blocks by default (`keep_alive=True`). Disable for complete isolation:

```python
transport = StdioTransport(command="python", args=["server.py"], keep_alive=False)
```

SOURCE: <https://gofastmcp.com/clients/transports> (accessed 2026-03-05)

### HTTP Transport

PATTERN: Use `StreamableHttpTransport` for explicit configuration. HTTP is the recommended transport for production remote servers.

```python
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

transport = StreamableHttpTransport(
    url="https://api.example.com/mcp",
    headers={
        "Authorization": "Bearer your-token-here",
        "X-Custom-Header": "value"
    }
)
client = Client(transport)
```

CONSTRAINT: SSE transport (`SSETransport`) is maintained for backward compatibility only. Use `StreamableHttpTransport` for all new projects.

SOURCE: <https://gofastmcp.com/clients/transports> (accessed 2026-03-05)

### Multi-Server Configuration

PATTERN: Pass a dict with `mcpServers` key to connect to multiple servers. Tool names are prefixed with server names to avoid collisions.

```python
from fastmcp import Client

config = {
    "mcpServers": {
        "weather": {
            "url": "https://weather.example.com/mcp",
            "transport": "http"
        },
        "assistant": {
            "command": "python",
            "args": ["./assistant.py"],
            "env": {"LOG_LEVEL": "INFO"}
        }
    }
}

client = Client(config)

async with client:
    # Tools are namespaced by server name
    weather = await client.call_tool("weather_get_forecast", {"city": "NYC"})
    answer = await client.call_tool("assistant_ask", {"question": "What?"})
```

PATTERN: Filter tools by tag within multi-server config:

```python
config = {
    "mcpServers": {
        "weather": {
            "url": "https://weather.example.com/mcp",
            "include_tags": ["forecast"]  # Only tools tagged "forecast"
        }
    }
}
```

CONSTRAINT: `MCPConfigTransport` (multi-server config) maintains session persistence across tool calls — each server connection is reused within a single `async with client:` block. This is the correct behavior for multi-tool workflows; do NOT create a new client per tool call when using config-based multi-server setups.

SOURCE: <https://gofastmcp.com/clients/transports> (accessed 2026-03-05)

---

## Client Operations

SOURCE: <https://gofastmcp.com/clients/client> (accessed 2026-03-05)

### Tools

```python
async with client:
    tools = await client.list_tools()
    result = await client.call_tool("multiply", {"a": 5, "b": 3})
    print(result.data)  # 15
```

### Resources

```python
async with client:
    resources = await client.list_resources()
    content = await client.read_resource("file:///config/settings.json")
    print(content[0].text)
```

### Prompts

```python
async with client:
    prompts = await client.list_prompts()
    messages = await client.get_prompt("analyze_data", {"data": [1, 2, 3]})
    print(messages.messages)
```

### Connection Lifecycle

PATTERN: Access server metadata after initialization:

```python
from fastmcp import Client, FastMCP

mcp = FastMCP(name="MyServer", instructions="Use the greet tool to say hello!")

async with Client(mcp) as client:
    print(f"Server: {client.initialize_result.serverInfo.name}")
    print(f"Instructions: {client.initialize_result.instructions}")
    print(f"Capabilities: {client.initialize_result.capabilities.tools}")
```

SOURCE: <https://gofastmcp.com/clients/client> (accessed 2026-03-05)

---

## Authentication

### Bearer Token Auth

SOURCE: <https://gofastmcp.com/clients/auth/bearer> (accessed 2026-03-05)

CONSTRAINT: Bearer token authentication applies only to HTTP-based transports.

PATTERN: Pass a string token directly — FastMCP adds the `Bearer` prefix automatically. Do NOT include `Bearer` in the string.

```python
from fastmcp import Client

async with Client(
    "https://your-server.fastmcp.app/mcp",
    auth="<your-token>",
) as client:
    await client.ping()
```

PATTERN: Use `BearerAuth` class for explicit control:

```python
from fastmcp import Client
from fastmcp.client.auth import BearerAuth

async with Client(
    "https://your-server.fastmcp.app/mcp",
    auth=BearerAuth(token="<your-token>"),
) as client:
    await client.ping()
```

PATTERN: Custom headers for non-standard token schemes:

```python
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

async with Client(
    transport=StreamableHttpTransport(
        "https://your-server.fastmcp.app/mcp",
        headers={"X-API-Key": "<your-token>"},
    ),
) as client:
    await client.ping()
```

SOURCE: <https://gofastmcp.com/clients/auth/bearer> (accessed 2026-03-05)

### OAuth Authentication

SOURCE: <https://gofastmcp.com/clients/auth/oauth> (accessed 2026-03-05)

CONSTRAINT: OAuth authentication applies only to HTTP-based transports and requires user browser interaction.

PATTERN: Simplest OAuth — pass string `"oauth"` for default settings:

```python
from fastmcp import Client

async with Client("https://your-server.fastmcp.app/mcp", auth="oauth") as client:
    await client.ping()
```

PATTERN: Full OAuth configuration via `OAuth` helper — implements Authorization Code Grant with PKCE:

```python
from fastmcp import Client
from fastmcp.client.auth import OAuth

oauth = OAuth(scopes=["user"])

async with Client("https://your-server.fastmcp.app/mcp", auth=oauth) as client:
    await client.ping()
```

PATTERN: Pre-registered OAuth client — skip Dynamic Client Registration when `client_id` is known:

```python
from fastmcp.client.auth import OAuth

oauth = OAuth(
    client_id="my-registered-client-id",
    client_secret="my-client-secret",  # Optional for public clients using PKCE
)
```

PATTERN: Persistent encrypted token storage (required for production — default is in-memory):

```python
from fastmcp.client.auth import OAuth
from key_value.aio.stores.disk import DiskStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet
import os

encrypted_storage = FernetEncryptionWrapper(
    key_value=DiskStore(directory="~/.fastmcp/oauth-tokens"),
    fernet=Fernet(os.environ["OAUTH_STORAGE_ENCRYPTION_KEY"])
)

oauth = OAuth(token_storage=encrypted_storage)
```

SOURCE: <https://gofastmcp.com/clients/auth/oauth> (accessed 2026-03-05)

### CIMD Authentication

SOURCE: <https://gofastmcp.com/clients/auth/cimd> (accessed 2026-03-05)

PATTERN: Available in FastMCP 3.0.0+. CIMD (Client ID Metadata Documents) provides domain-verified client identity. Host a JSON document at an HTTPS URL — that URL becomes your `client_id`.

```python
from fastmcp import Client
from fastmcp.client.auth import OAuth

async with Client(
    "https://mcp-server.example.com/mcp",
    auth=OAuth(
        client_metadata_url="https://myapp.example.com/oauth/client.json",
    ),
) as client:
    await client.ping()
```

PATTERN: Generate a CIMD document with the CLI:

```bash
fastmcp auth cimd create \
    --name "My Application" \
    --redirect-uri "http://localhost:*/callback" \
    --client-id "https://myapp.example.com/oauth/client.json"
```

CONSTRAINT: CIMD documents must be hosted at a publicly accessible HTTPS URL with a non-root path. The `client_id` in the document must exactly match the hosting URL.

PATTERN: Validate your hosted document before connecting clients:

```bash
fastmcp auth cimd validate https://myapp.example.com/oauth/client.json
```

SOURCE: <https://gofastmcp.com/clients/auth/cimd> (accessed 2026-03-05)

---

## Sampling

SOURCE: <https://gofastmcp.com/clients/sampling> (accessed 2026-03-05)

PATTERN: Implement a `sampling_handler` to respond to server-initiated LLM completion requests. The server delegates AI reasoning to the client.

```python
from fastmcp import Client
from fastmcp.client.sampling import SamplingMessage, SamplingParams, RequestContext

async def sampling_handler(
    messages: list[SamplingMessage],
    params: SamplingParams,
    context: RequestContext
) -> str:
    system_prompt = params.systemPrompt or "You are a helpful assistant."
    # Integrate with your LLM service here
    return "Generated response based on the messages"

client = Client(
    "my_mcp_server.py",
    sampling_handler=sampling_handler,
)
```

PATTERN: Use built-in handlers for common LLM providers. Requires the corresponding extra package.

```python
from fastmcp import Client
from fastmcp.client.sampling.handlers.openai import OpenAISamplingHandler

# Install: pip install "fastmcp[openai]"
client = Client(
    "my_mcp_server.py",
    sampling_handler=OpenAISamplingHandler(default_model="gpt-4o"),
)
```

```python
from fastmcp.client.sampling.handlers.anthropic import AnthropicSamplingHandler

# Install: pip install "fastmcp[anthropic]"
client = Client(
    "my_mcp_server.py",
    sampling_handler=AnthropicSamplingHandler(default_model="claude-sonnet-4-5"),
)
```

RULE: When you provide a `sampling_handler`, FastMCP automatically advertises full sampling capabilities (including tool support) to the server.

SOURCE: <https://gofastmcp.com/clients/sampling> (accessed 2026-03-05)

---

## Elicitation

SOURCE: <https://gofastmcp.com/clients/elicitation> (accessed 2026-03-05)

PATTERN: Implement an `elicitation_handler` to respond to server requests for structured user input during tool execution.

```python
from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult, ElicitRequestParams, RequestContext

async def elicitation_handler(
    message: str,
    response_type: type | None,
    params: ElicitRequestParams,
    context: RequestContext
) -> ElicitResult | object:
    user_input = input(f"{message}: ")

    if not user_input:
        return ElicitResult(action="decline")

    return response_type(value=user_input)

client = Client(
    "my_mcp_server.py",
    elicitation_handler=elicitation_handler,
)
```

PATTERN: Return `ElicitResult` for explicit action control:

```python
from fastmcp.client.elicitation import ElicitResult

async def elicitation_handler(message, response_type, params, context):
    user_input = input(f"{message}: ")

    if not user_input:
        return ElicitResult(action="decline")   # User declined — no data

    if user_input == "cancel":
        return ElicitResult(action="cancel")    # Cancel entire operation

    return ElicitResult(
        action="accept",
        content=response_type(value=user_input)
    )
```

RULE: Action types — `accept` (include data in `content`), `decline` (omit `content`), `cancel` (omit `content`, abort operation).

SOURCE: <https://gofastmcp.com/clients/elicitation> (accessed 2026-03-05)

---

## Callback Handler Summary

PATTERN: Provide multiple handlers at client construction time:

```python
client = Client(
    "my_mcp_server.py",
    log_handler=log_handler,
    progress_handler=progress_handler,
    sampling_handler=sampling_handler,
    elicitation_handler=elicitation_handler,
    timeout=30.0,
)
```

SOURCE: <https://gofastmcp.com/clients/client> (accessed 2026-03-05)
