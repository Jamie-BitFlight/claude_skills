# FastMCP v3 Testing Reference

How to test FastMCP v3 servers using in-memory transport and pytest — covers fixtures, assertions, mocking, and network transport testing. [1] [2] [3] [4]

---

## In-Memory Transport — Primary Test Pattern

RULE: Use `Client(mcp)` (in-memory transport) for all unit tests. Do NOT use HTTP transport unless testing network-specific behavior.

The in-memory transport runs the real MCP protocol implementation without network overhead. Pass your server instance directly to the client — no deployment, no subprocess, no network. Everything runs in the same Python process with full debugger support. [5]

```python
from fastmcp import FastMCP
from fastmcp.client import Client

mcp = FastMCP("TestServer")

@mcp.tool
def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"

async def test_greet_tool():
    async with Client(mcp) as client:
        result = await client.call_tool("greet", {"name": "World"})
        assert result.data == "Hello, World!"
```

---

## pytest Configuration

RULE: Set `asyncio_mode = "auto"` in `pyproject.toml`. This eliminates `@pytest.mark.asyncio` decorators on every async test. [6]

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

Install `pytest-asyncio` as a development dependency:

```bash
pip install pytest-asyncio
# or
uv add --dev pytest-asyncio
```

CONSTRAINT: Do NOT add `@pytest.mark.asyncio` to individual test functions when `asyncio_mode = "auto"` is configured. The decorator is redundant and clutters test code.

---

## Fixtures Pattern

RULE: Use pytest fixtures to create reusable server configurations. Do NOT open FastMCP clients inside fixtures — this creates hard-to-diagnose event loop issues. Create the server in the fixture and open the client inside each test. [7]

```python
import pytest
from fastmcp import FastMCP
from fastmcp.client import Client

@pytest.fixture
def weather_server():
    server = FastMCP("WeatherServer")

    @server.tool
    def get_temperature(city: str) -> dict:
        """Get temperature for a city."""
        temps = {"NYC": 72, "LA": 85, "Chicago": 68}
        return {"city": city, "temp": temps.get(city, 70)}

    return server

async def test_temperature_tool(weather_server):
    async with Client(weather_server) as client:
        result = await client.call_tool("get_temperature", {"city": "LA"})
        assert result.data == {"city": "LA", "temp": 85}
```

Using the fixture-level client pattern (from `testing.mdx`):

```python
from fastmcp.client.transports import FastMCPTransport

@pytest.fixture
async def main_mcp_client():
    async with Client(transport=mcp) as mcp_client:
        yield mcp_client

async def test_list_tools(main_mcp_client: Client[FastMCPTransport]):
    tools = await main_mcp_client.list_tools()
    assert len(tools) == 5
```

---

## Assertion Patterns — Tools, Resources, Prompts [8]

```python
from fastmcp import FastMCP
from fastmcp.client import Client

mcp = FastMCP("TestServer")

@mcp.tool
def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y

@mcp.resource("config://app")
def app_config() -> dict:
    """Application configuration."""
    return {"version": "1.0", "debug": False}

@mcp.prompt
def review(code: str) -> str:
    """Review code."""
    return f"Please review:\n\n{code}"

async def test_tool_call():
    async with Client(mcp) as client:
        result = await client.call_tool("add", {"x": 3, "y": 4})
        assert result.data == 7

async def test_resource_read():
    async with Client(mcp) as client:
        result = await client.read_resource("config://app")
        assert result[0].text is not None

async def test_prompt_get():
    async with Client(mcp) as client:
        result = await client.get_prompt("review", {"code": "def foo(): pass"})
        assert len(result.messages) == 1
```

---

## Parameterized Tests

Use `@pytest.mark.parametrize` for variations of the same behavior. Use separate tests for different behaviors. [9]

```python
import pytest
from fastmcp import FastMCP
from fastmcp.client import Client

mcp = FastMCP("MathServer")

@mcp.tool
def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y

@pytest.fixture
async def mcp_client():
    async with Client(mcp) as client:
        yield client

@pytest.mark.parametrize(
    "x, y, expected",
    [
        (1, 2, 3),
        (2, 3, 5),
        (0, 0, 0),
        (-1, 1, 0),
    ],
)
async def test_add(x: int, y: int, expected: int, mcp_client):
    result = await mcp_client.call_tool("add", {"x": x, "y": y})
    assert result.data == expected
```

---

## Inline Snapshots for Complex Structures

Use `inline-snapshot` for testing JSON schemas and complex data structures. [10]

```python
from inline_snapshot import snapshot
from fastmcp import FastMCP

mcp = FastMCP("TestServer")

@mcp.tool
def calculate(amount: float, rate: float = 0.1) -> dict:
    """Calculate tax."""
    return {"amount": amount, "tax": amount * rate}

async def test_tool_schema():
    tools = mcp.list_tools()
    schema = tools[0].inputSchema
    assert schema == snapshot()  # Auto-populated on first run
```

Commands:

```bash
pytest --inline-snapshot=create        # populate empty snapshots
pytest --inline-snapshot=fix           # update after intentional changes
pytest --inline-snapshot=fix,create    # combined: create new and fix existing
```

For values that change between runs (timestamps, IDs, random data), use `dirty-equals` for flexible equality assertions:

```python
from dirty_equals import IsDatetime, IsStr
from inline_snapshot import snapshot
from fastmcp import FastMCP
from fastmcp.client import Client

mcp = FastMCP("TestServer")

@mcp.tool
def status() -> dict:
    """Return server status."""
    import datetime
    return {"status": "ok", "checked_at": datetime.datetime.now().isoformat()}

async def test_status_tool():
    async with Client(mcp) as client:
        result = await client.call_tool("status", {})
        assert result.data == {"status": "ok", "checked_at": IsStr()}
```

Install both libraries as development dependencies: [11] [12] [13]

```bash
uv add --dev inline-snapshot dirty-equals
```

---

## Mocking External Dependencies [14]

```python
from unittest.mock import AsyncMock
from fastmcp import FastMCP
from fastmcp.client import Client

async def test_database_tool():
    server = FastMCP("DataServer")

    mock_db = AsyncMock()
    mock_db.fetch_users.return_value = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]

    @server.tool
    async def list_users() -> list:
        """List all users."""
        return await mock_db.fetch_users()

    async with Client(server) as client:
        result = await client.call_tool("list_users", {})
        assert len(result.data) == 2
        mock_db.fetch_users.assert_called_once()
```

RULE: Mock at the boundary — mock external services (databases, HTTP APIs), not internal FastMCP classes.

---

## Error Testing [15]

```python
import pytest
from fastmcp import FastMCP
from fastmcp.client import Client

async def test_tool_raises_on_invalid_input():
    server = FastMCP("test-server")

    @server.tool
    def divide(a: int, b: int) -> float:
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

    async with Client(server) as client:
        with pytest.raises(Exception):
            await client.call_tool("divide", {"a": 10, "b": 0})
```

---

## Network Transport Testing (Advanced)

Use in-process network testing when you must test actual HTTP transport behavior. [16]

```python
import pytest
from fastmcp import FastMCP, Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.utilities.tests import run_server_async

def create_test_server() -> FastMCP:
    server = FastMCP("TestServer")

    @server.tool
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    return server

@pytest.fixture
async def http_server() -> str:
    server = create_test_server()
    async with run_server_async(server) as url:
        yield url

async def test_http_transport(http_server: str):
    async with Client(
        transport=StreamableHttpTransport(http_server)
    ) as client:
        result = await client.ping()
        assert result is True
        greeting = await client.call_tool("greet", {"name": "World"})
        assert greeting.data == "Hello, World!"
```

CONSTRAINT: Only use `run_server_async` when you specifically need to test HTTP transport behavior. For all other tests, use in-memory transport.

For subprocess isolation (e.g., STDIO transport testing), use `run_server_in_process`:

```python
from fastmcp.utilities.tests import run_server_in_process

@pytest.fixture
async def http_server():
    with run_server_in_process(run_server_fn, transport="http") as url:
        yield f"{url}/mcp"
```

Mark subprocess tests with `@pytest.mark.client_process` to isolate them in CI.

---

## Test Naming and Single-Behavior Rule [17]

RULE: Each test verifies exactly one behavior. When it fails, the name tells you what broke.

```python
# Correct — name describes the specific behavior
async def test_tool_returns_error_on_missing_parameter():
    ...

async def test_resource_returns_json_content():
    ...

# Wrong — too vague, failure gives no signal
async def test_server():
    ...

async def test_tool():
    ...
```

---

## Running Tests [18]

```bash
uv run pytest -n auto               # run all tests in parallel
uv run pytest -n auto -x            # stop on first failure
uv run pytest path/to/test.py       # run specific file
uv run pytest -k "test_name"        # run tests matching pattern
uv run pytest -m "not integration"  # exclude integration tests
uv run pytest --cov=fastmcp         # run with coverage
```

---

## Extended Pytest Patterns

For comprehensive pytest patterns including fixtures, parameterization, mocking, and async patterns beyond FastMCP-specific testing, activate the `/fastmcp-python-tests` skill.

## References

1. [FastMCP Testing](https://gofastmcp.com/servers/testing) (accessed 2026-03-17) — dedicated testing page (v3.1)
2. [FastMCP Testing](https://gofastmcp.com/patterns/testing) (accessed 2026-03-05)
3. [FastMCP Tests](https://gofastmcp.com/development/tests) (accessed 2026-03-05)
4. `plugins/fastmcp-creator/skills/fastmcp-python-tests/SKILL.md` (extended pytest patterns)
5. [FastMCP Tests](https://gofastmcp.com/development/tests) — "In-Memory Testing" section
6. [FastMCP Testing](https://gofastmcp.com/patterns/testing) — "Prerequisites" section
7. [FastMCP Tests](https://gofastmcp.com/development/tests) — "Using Fixtures" section
8. [FastMCP Testing](https://gofastmcp.com/patterns/testing) — "Testing with Pytest Fixtures" section
9. [FastMCP Testing](https://gofastmcp.com/patterns/testing) — "Using the pytest parametrize decorator" section
10. [FastMCP Tests](https://gofastmcp.com/development/tests) — "Inline Snapshots" section
11. [FastMCP Testing](https://gofastmcp.com/servers/testing) (accessed 2026-03-17) — "Testing with Pytest Fixtures" section
12. [Inline Snapshot](https://github.com/15r10nk/inline-snapshot) (accessed 2026-03-17)
13. [Dirty Equals](https://github.com/samuelcolvin/dirty-equals) (accessed 2026-03-17)
14. [FastMCP Tests](https://gofastmcp.com/development/tests) — "Mocking External Dependencies" section
15. [FastMCP Tests](https://gofastmcp.com/development/tests) — "Self-Contained Setup" section
16. [FastMCP Tests](https://gofastmcp.com/development/tests) — "Testing Network Transports" section
17. [FastMCP Tests](https://gofastmcp.com/development/tests) — "Single Behavior Per Test" section
18. `plugins/fastmcp-creator/skills/fastmcp-python-tests/SKILL.md`
