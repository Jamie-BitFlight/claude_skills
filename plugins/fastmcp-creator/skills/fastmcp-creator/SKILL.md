---
name: fastmcp-creator
description: "Use when building, extending, or debugging FastMCP v3 Python MCP servers — covers tools, resources, prompts, providers, transforms (including CodeMode and Tool Search), auth (MultiAuth, PropelAuth), client SDK, deployment (nginx reverse proxy), Prefab Apps, and testing. Grounded in local v3.1 docs — zero speculation."
version: "3.1.0"
---

## Current Environment

**Python version:**

!`python3 --version 2>/dev/null || python --version 2>/dev/null || echo "Python not found in PATH"`

**Installed FastMCP version:**

!`uv run python -c "import fastmcp; print(f'FastMCP {fastmcp.__version__}')" 2>/dev/null || echo "FastMCP not installed — run: uv add 'fastmcp>=3.0' before scaffolding"`

---

## Trigger Matrix

When user intent matches, load the reference file listed — do not rely on training data for v3 API facts.

| User intent | v3 feature | Reference file |
|---|---|---|
| Build a new FastMCP server | `FastMCP()`, `@mcp.tool`, `@mcp.resource` | [./references/server-core.md](./references/server-core.md) |
| Compose multiple servers | `mount()`, namespace, providers | [./references/providers.md](./references/providers.md) |
| Bridge remote HTTP server to stdio | `ProxyProvider`, `create_proxy()` | [./references/providers.md](./references/providers.md) |
| Serve files or skills as resources | `FileSystemProvider`, `SkillsProvider` | [./references/providers.md](./references/providers.md) |
| Rename or filter tools from sub-server | `ToolTransform`, `Namespace` | [./references/transforms.md](./references/transforms.md) |
| Expose resources as tools | `ResourcesAsTools` | [./references/transforms.md](./references/transforms.md) |
| Search/discover tools in large catalogs | `BM25SearchTransform`, `RegexSearchTransform` | [./references/transforms.md](./references/transforms.md) |
| Sandbox tool execution via Python scripts | `CodeMode` (experimental) | [./references/transforms.md](./references/transforms.md) |
| Add authentication to a server | `require_scopes`, OAuth variants | [./references/auth.md](./references/auth.md) |
| Mix OAuth + JWT token verifiers | `MultiAuth` | [./references/auth.md](./references/auth.md) |
| Use PropelAuth for auth | `PropelAuthProvider` | [./references/auth.md](./references/auth.md) |
| Write a FastMCP client | `Client`, transports, `BearerAuth` | [./references/client-sdk.md](./references/client-sdk.md) |
| Run long tasks without blocking | `@mcp.tool(task=True)` | [./references/advanced.md](./references/advanced.md) |
| Add multi-turn user input to a tool | Elicitation API | [./references/advanced.md](./references/advanced.md) |
| Deploy to production | Prefect Horizon, HTTP, stdio, nginx | [./references/deployment.md](./references/deployment.md) |
| Deploy behind nginx reverse proxy | SSE config, TLS, subpath mounting | [./references/deployment.md](./references/deployment.md) |
| Write tests for a FastMCP server | In-memory Client, pytest patterns | [./references/testing.md](./references/testing.md) |
| Integrate with Anthropic/OpenAI/FastAPI | Integration patterns | [./references/integrations.md](./references/integrations.md) |
| Migrate from FastMCP v2 | Breaking changes, syntax fixes | [./references/migration.md](./references/migration.md) |
| Add web UI to a server | Apps HTML API, Prefab Apps | [./references/apps.md](./references/apps.md) |
| Return interactive UI from tools | `@mcp.tool(app=True)`, `PrefabApp` | [./references/advanced.md](./references/advanced.md) |
| Add request/response middleware | `Middleware`, built-in middleware | [./references/middleware.md](./references/middleware.md) |
| Find real-world usage patterns | ProxyProvider, mount(), showcase | [./references/real-world-patterns.md](./references/real-world-patterns.md) |
| Evaluate MCP server quality | Evaluation harness, QA pairs | [./references/evaluation-guide.md](./references/evaluation-guide.md) |

---

## Choose Provider Type

```mermaid
flowchart TD
    Q1{What do you need?}
    Q1 -->|Define tools/resources in this server| LC["LocalProvider — default<br>No mount() needed<br>Source: providers/local.mdx"]
    Q1 -->|Add another FastMCP server's tools| MC["FastMCPProvider / mount()<br>mcp.mount(sub, namespace='ns')<br>Source: providers/mounting.mdx"]
    Q1 -->|Wrap remote HTTP MCP server| PC["ProxyProvider<br>create_proxy('http://remote/mcp')<br>Source: providers/proxy.mdx"]
    Q1 -->|Serve files from disk as resources| FC["FileSystemProvider('path/')<br>reload=True for dev, False for prod<br>Source: providers/filesystem.mdx"]
    Q1 -->|Expose Claude/Cursor skill files| SC["SkillsProvider / ClaudeSkillsProvider()<br>skill:// URI scheme<br>Source: providers/skills.mdx"]
    Q1 -->|Build a custom provider| CC["Subclass Provider base class<br>Source: providers/custom.mdx"]
```

---

## Choose Transport

```mermaid
flowchart TD
    Q1{How will clients connect?}
    Q1 -->|Local tool in Claude Code / desktop app| ST["stdio — default<br>fastmcp run server.py:mcp<br>Source: deployment/running-server.mdx"]
    Q1 -->|Web service or multi-client| HT["HTTP transport<br>mcp.run(transport='http', port=8000)<br>Source: deployment/http.mdx"]
    Q1 -->|Testing — in-process| IT["In-memory transport<br>async with Client(mcp) as client<br>Source: patterns/testing.mdx"]
    Q1 -->|Managed cloud deployment| PH["Prefect Horizon<br>fastmcp run via GitHub integration<br>Source: deployment/prefect-horizon.mdx"]
```

---

## Choose Auth Approach

```mermaid
flowchart TD
    Q1{Auth requirement?}
    Q1 -->|No auth needed| NA["No auth — default FastMCP behavior"]
    Q1 -->|Validate bearer tokens per tool| RS["require_scopes('scope')<br>@mcp.tool(auth=require_scopes('write'))<br>Source: servers/auth/token-verification.mdx"]
    Q1 -->|Full OAuth2 server built-in| FO["Full OAuth server<br>Source: servers/auth/full-oauth-server.mdx"]
    Q1 -->|Delegate to external IdP — Auth0, Azure| OP["OIDC proxy / OAuth proxy<br>Source: servers/auth/oidc-proxy.mdx"]
    Q1 -->|Mix OAuth + JWT for hybrid clients| MA["MultiAuth — compose OAuth server<br>+ token verifiers (v3.1)<br>Source: servers/auth/multi-auth.mdx"]
    Q1 -->|Use PropelAuth| PA["PropelAuthProvider<br>OAuth + token introspection (v3.1)<br>Source: integrations/propelauth.mdx"]
    Q1 -->|Client calling protected server| CA["Client auth — BearerAuth / CIMDAuth / OAuthAuth<br>Source: clients/auth/*.mdx"]
```

---

## Quick-Start Examples

### Minimal server

```python
# SOURCE: servers/server.mdx + servers/tools.mdx (accessed 2026-03-05)
from fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool  # RULE: no parentheses — v3 canonical syntax
def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()
```

### Server composition

```python
# SOURCE: servers/providers/mounting.mdx (accessed 2026-03-05)
from fastmcp import FastMCP

weather = FastMCP("weather")
main = FastMCP("main")

main.mount(weather, namespace="weather")
# Tools from weather become weather_<tool-name> on main
```

### Background task

```python
# SOURCE: servers/tasks.mdx — requires fastmcp[tasks] extra (accessed 2026-03-05)
from fastmcp import FastMCP

mcp = FastMCP("task-server")

@mcp.tool(task=True)  # RULE: task=True, NOT task=TaskConfig(...)
async def long_running(data: str) -> str:
    """Process data in background."""
    return "done"
```

---

## v3 API Corrections

CONSTRAINT: These v2 patterns are deprecated or removed. Generate only the v3 form.

| v2 / wrong pattern | v3 correct pattern | Source |
|---|---|---|
| `@mcp.tool()` with parentheses | `@mcp.tool` without parentheses | `quickstart.mdx` |
| `task=TaskConfig(mode="required")` | `task=True` | `servers/tasks.mdx` |
| `require_auth` | `require_scopes("scope")` | `servers/authorization.mdx` |
| `.mcpb` packaging | Prefect Horizon or stdio deploy | `deployment/running-server.mdx` |
| `ctx.get_state()` / `ctx.set_state()` | Verify in `context.mdx` — not confirmed v3 | `servers/context.mdx` |

---

## Version Gating

### FastMCP 3.0 — Available

All core features (tools, resources, prompts, providers, transforms, auth, tasks, elicitation,
client SDK, deployment) are available in FastMCP 3.0.

### FastMCP 3.1 — Available (current)

The following features were added in FastMCP 3.1.0 and require `fastmcp>=3.1.0`:

- **Tool Search transforms** — `BM25SearchTransform`, `RegexSearchTransform` for large tool catalogs
- **CodeMode transform** (experimental) — sandboxed Python execution for tool invocation (`fastmcp[code-mode]`)
- **`transforms=` kwarg** — server-level `FastMCP("name", transforms=[...])` constructor parameter
- **MultiAuth** — compose OAuth server + multiple token verifiers
- **PropelAuth provider** — `PropelAuthProvider` for PropelAuth OAuth + token introspection
- **Prefab Apps** (experimental) — `@mcp.tool(app=True)` with declarative UI components (`fastmcp[apps]`)
- **Google GenAI sampling handler** — alternative to Anthropic/OpenAI sampling
- **`-m/--module` flag** — `fastmcp run -m my_package.server` for module mode
- **`FASTMCP_TRANSPORT`** env var — default transport selection without CLI flag
- **`http_client` parameter** — connection pooling for token verifiers
- **`include_unversioned`** option in VersionFilter
- **`Tool.from_tool()`** — immediate transformation at registration time

SOURCE: <https://github.com/PrefectHQ/fastmcp> releases v3.1.0, v3.1.1 (accessed 2026-03-17)

---

## Reference Files

All 13 v3 reference files sourced from <https://gofastmcp.com> (published docs) and <https://github.com/PrefectHQ/fastmcp> (source code):

- [./references/server-core.md](./references/server-core.md) — `FastMCP()`, tools, resources, prompts, context, lifespan, `transforms=` kwarg
- [./references/providers.md](./references/providers.md) — LocalProvider, FastMCPProvider, ProxyProvider, FileSystemProvider, SkillsProvider
- [./references/transforms.md](./references/transforms.md) — Namespace, ToolTransform, Enabled, ResourcesAsTools, PromptsAsTools, BM25SearchTransform, RegexSearchTransform, CodeMode
- [./references/auth.md](./references/auth.md) — `require_scopes`, OAuth variants, token verification, MultiAuth, PropelAuth, `http_client` pooling
- [./references/client-sdk.md](./references/client-sdk.md) — `Client`, transports, BearerAuth, CIMD, OAuth, sampling, elicitation, `fastmcp discover`, fuzzy matching
- [./references/apps.md](./references/apps.md) — low-level HTML API, Prefab Apps (experimental)
- [./references/advanced.md](./references/advanced.md) — tasks, elicitation, storage backends, dependency injection, versioning, visibility, Prefab Apps, Google GenAI sampling
- [./references/middleware.md](./references/middleware.md) — Middleware base class, hook hierarchy, 11 built-in middleware, tag-based access control
- [./references/deployment.md](./references/deployment.md) — stdio, HTTP, server config, Prefect Horizon, nginx reverse proxy, module mode, `FASTMCP_TRANSPORT`
- [./references/testing.md](./references/testing.md) — in-memory Client, FastMCPTransport, pytest patterns, inline-snapshot
- [./references/integrations.md](./references/integrations.md) — Anthropic, OpenAI, Gemini, Google GenAI, FastAPI, GitHub, Auth0, Azure, PropelAuth, Claude Code
- [./references/migration.md](./references/migration.md) — v2 → v3 breaking changes, from MCP SDK
- [./references/real-world-patterns.md](./references/real-world-patterns.md) — ProxyProvider, mount(), SkillsProvider, showcase

Preserved references (not overwritten):

- [./references/evaluation-guide.md](./references/evaluation-guide.md) — evaluating server quality
- [./references/typescript-mcp-server.md](./references/typescript-mcp-server.md) — TypeScript MCP SDK (out of v3 overhaul scope)
- [./references/claude-code-mcp-integration.md](./references/claude-code-mcp-integration.md) — `.mcp.json` config, Claude Code deployment

---

## Related Skills

- For pytest patterns and in-memory testing fixtures:
  `Skill(skill: "fastmcp-creator:fastmcp-python-tests")`
- For `fastmcp list` / `fastmcp call` / `fastmcp discover` CLI usage:
  `Skill(skill: "fastmcp-creator:fastmcp-client-cli")`
- For Python project setup (pyproject.toml, uv, src layout):
  `Skill(skill: "python3-development:python3-development")`
- For evaluating MCP server quality: [./references/evaluation-guide.md](./references/evaluation-guide.md)
- For Claude Code MCP config (`.mcp.json`): [./references/claude-code-mcp-integration.md](./references/claude-code-mcp-integration.md)
