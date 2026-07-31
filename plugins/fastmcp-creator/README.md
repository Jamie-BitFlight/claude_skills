<p align="center">
  <img src="./assets/hero.png" alt="FastMCP Creator" width="800" />
</p>

# FastMCP Creator

Expert-level guidance for building FastMCP v3 Python MCP servers — tools, resources, prompts,
providers, transforms, auth, testing, and production deployment. Grounded in local v3.1 docs;
no speculation.

## The Problem It Solves

FastMCP v3 introduced a provider/transform architecture that is fundamentally different from
v2. Code written from training-data memory uses deprecated syntax — `@mcp.tool()` with
parentheses, missing `task=True` for background tools, wrong transport flags. This plugin
loads verified v3.1 reference docs and enforces correct patterns at every step.

## What's Inside

| Component | Name | Activates on |
|-----------|------|--------------|
| Skill | `fastmcp-creator` | Building, extending, or debugging FastMCP v3 servers |
| Skill | `fastmcp-client-cli` | Running `fastmcp list` / `fastmcp call` against a running server |
| Skill | `fastmcp-python-tests` | Writing pytest suites for FastMCP servers |

## Quick Start

```bash
/plugin marketplace add Jamie-BitFlight/claude_skills
/plugin install fastmcp-creator@jamie-bitflight-skills
```

Then ask Claude to build a server:

```
Build an MCP server that wraps the GitHub REST API — issues and PRs only.
```

Claude will load the v3.1 reference docs, select the right provider type and transport, write
validated Python, and include tests.

## Minimal Server

```python
from fastmcp import FastMCP

mcp = FastMCP("my-server")


@mcp.tool  # no parentheses — v3 canonical syntax
def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run()
```

## What Claude Can Build With This Plugin

**Compose multiple servers**

```python
mcp.mount(sub_server, namespace="github")
```

**Wrap a remote HTTP server as stdio**

```python
from fastmcp import create_proxy

mcp = create_proxy("http://remote-service/mcp")
```

**Serve files or Claude skills as resources**

```python
from fastmcp.providers import FileSystemProvider

mcp = FastMCP("docs", providers=[FileSystemProvider("./docs/")])
```

**Search large tool catalogs**

```python
from fastmcp.transforms import BM25SearchTransform
```

**Run long tasks without blocking**

```python
@mcp.tool(task=True)
async def long_job(params: str) -> str: ...
```

**Add auth (OAuth, JWT, PropelAuth)**

```python
from fastmcp.auth import MultiAuth, require_scopes
```

**Return interactive UI from tools**

```python
@mcp.tool(app=True)
def dashboard() -> PrefabApp: ...
```

## Skill Trigger Matrix

The `fastmcp-creator` skill activates automatically when you:

- Create or modify a FastMCP server file
- Ask about tool/resource/prompt creation
- Need provider composition (`mount()`, `ProxyProvider`, `FileSystemProvider`)
- Configure transforms (`ToolTransform`, `BM25SearchTransform`, `CodeMode`)
- Set up authentication (`MultiAuth`, `PropelAuth`, `require_scopes`)
- Write a FastMCP client (`Client`, transports, `BearerAuth`)
- Deploy to production (HTTP, stdio, nginx reverse proxy, Prefect Horizon)
- Migrate from FastMCP v2

## Testing MCP Servers

The `fastmcp-python-tests` skill covers in-memory transport testing (no real network required),
pytest fixtures, inline snapshots for complex output, async patterns, and the `CliRunner`
test harness.

```python
from fastmcp import Client
import pytest


@pytest.fixture
def client(mcp_server):  # in-memory transport
    return Client(mcp_server)


async def test_greet(client):
    result = await client.call_tool("greet", {"name": "world"})
    assert result.content[0].text == "Hello, world!"
```

## Querying a Running Server

The `fastmcp-client-cli` skill covers `fastmcp list` and `fastmcp call`:

```bash
# Discover what tools a server exposes
fastmcp list --command "uv run --script server.py"

# Call a tool
fastmcp call --command "uv run --script server.py" greet '{"name": "world"}'
```

## Version Coverage

| Version | Status |
|---------|--------|
| FastMCP 3.1 | Current — full coverage |
| FastMCP 3.0 | Available — all core features |
| FastMCP v2 | Legacy reference; migration guide included |
| TypeScript | Legacy reference only — not updated for v3 |

## Requirements

- Claude Code v2.0+
- Python 3.11+
- `uv` (the plugin's MCP reference server runs via `uv run`)

---

> **The Ancient Woe**
>
> *The isolationist kingdoms that refuse to trade because their wagon wheels are of different widths and their gold coins of different weights.*

> **The Bard's Decree**
>
> *"Lay down the universal tracks! Build the grand bridges so that the oracle of the East may seamlessly converse with the libraries of the West, with no toll collector to halt them!"*
