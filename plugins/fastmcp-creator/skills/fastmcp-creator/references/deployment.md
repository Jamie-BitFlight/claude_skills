# FastMCP Deployment Reference

How to run, configure, and deploy FastMCP servers — covers transport selection, CLI usage, HTTP deployment, `fastmcp.json` project configuration, horizontal scaling, and managed hosting via Prefect Horizon.

SOURCE: <https://gofastmcp.com/deployment/running-server> (accessed 2026-03-05)

---

## Transport Protocols

RULE: STDIO is the default transport. Call `mcp.run()` without arguments to use STDIO.

```python
from fastmcp import FastMCP

mcp = FastMCP("MyServer")

@mcp.tool
def hello(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()  # STDIO transport — default
```

CONSTRAINT: STDIO is correct for local development, Claude Desktop integration, command-line tools, and single-user applications. HTTP transport is required when you need network access or multiple concurrent clients.

CONSTRAINT: SSE transport (`transport="sse"`) exists only for backward compatibility. Use HTTP transport for all new projects.

SOURCE: <https://gofastmcp.com/deployment/running-server> (accessed 2026-03-05)

### HTTP Transport

```python
if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000)
```

Server is accessible at `http://localhost:8000/mcp`.

PATTERN: Use `run_async()` inside async contexts — `run()` creates its own event loop and cannot be called from inside an async function:

```python
import asyncio
from fastmcp import FastMCP

mcp = FastMCP(name="MyServer")

async def main():
    await mcp.run_async(transport="http", port=8000)

if __name__ == "__main__":
    asyncio.run(main())
```

SOURCE: <https://gofastmcp.com/deployment/running-server> (accessed 2026-03-05)

---

## FastMCP CLI

SOURCE: <https://gofastmcp.com/deployment/running-server> (accessed 2026-03-05)

PATTERN: Run a server without modifying source — the CLI automatically finds instances named `mcp`, `server`, or `app`:

```bash
fastmcp run server.py
```

PATTERN: Run with specific Python version and additional packages:

```bash
fastmcp run server.py --python 3.11
fastmcp run server.py --with pandas --with numpy
fastmcp run server.py --with-requirements requirements.txt
fastmcp run server.py --python 3.10 --with httpx --transport http
```

PATTERN: Pass arguments to servers after `--`:

```bash
fastmcp run config_server.py -- --config config.json
fastmcp run database_server.py -- --database-path /tmp/db.sqlite --debug
```

PATTERN: Auto-reload during development — watches for file changes and restarts automatically (available in FastMCP 3.0.0+):

```bash
fastmcp run server.py --reload

# Watch specific directories
fastmcp run server.py --reload --reload-dir ./src --reload-dir ./lib

# Combine with HTTP transport
fastmcp run server.py --reload --transport http --port 8080
```

CONSTRAINT: Auto-reload uses stateless mode. For HTTP transport, some bidirectional features like elicitation are not available during reload mode. SSE transport does not support auto-reload.

SOURCE: <https://gofastmcp.com/deployment/running-server> (accessed 2026-03-05)

---

## Custom Routes

PATTERN: Add custom HTTP endpoints alongside the MCP endpoint using `@mcp.custom_route`:

```python
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse, JSONResponse

mcp = FastMCP("MyServer")

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")

@mcp.custom_route("/status", methods=["GET"])
async def status(request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "mcp-server"})
```

CONSTRAINT: Custom routes are served by the same web server as the MCP endpoint. The MCP endpoint is at `/mcp/`; custom routes are at the root domain.

SOURCE: <https://gofastmcp.com/deployment/running-server> (accessed 2026-03-05)

---

## HTTP Deployment

SOURCE: <https://gofastmcp.com/deployment/http> (accessed 2026-03-05)

### Direct HTTP Server

PATTERN: Simplest production deployment — use `run()` with HTTP transport:

```python
from fastmcp import FastMCP

mcp = FastMCP("My Server")

@mcp.tool
def process_data(input: str) -> str:
    return f"Processed: {input}"

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
```

Run with: `python server.py`. Server accessible at `http://localhost:8000/mcp`.

### ASGI Application

PATTERN: Create an ASGI app for Uvicorn/Gunicorn deployment with multiple workers:

```python
from fastmcp import FastMCP

mcp = FastMCP("My Server")

@mcp.tool
def process_data(input: str) -> str:
    return f"Processed: {input}"

app = mcp.http_app()
```

Run with: `uvicorn app:app --host 0.0.0.0 --port 8000`

PATTERN: Custom MCP path:

```python
mcp.run(transport="http", host="0.0.0.0", port=8000, path="/api/mcp/")
app = mcp.http_app(path="/api/mcp/")
```

### Custom Middleware

PATTERN: Add Starlette middleware — required for CORS when serving browser-based clients:

```python
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

mcp = FastMCP("MyServer")

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=[
            "mcp-protocol-version",
            "mcp-session-id",
            "Authorization",
            "Content-Type",
        ],
        expose_headers=["mcp-session-id"],
    )
]

app = mcp.http_app(middleware=middleware)
```

CONSTRAINT: `expose_headers=["mcp-session-id"]` is required for browser-based MCP clients. Without it, JavaScript cannot read the session ID from responses, causing session management to fail.

CONSTRAINT: Most MCP clients (Claude Code, Cursor, ChatGPT) do NOT need CORS configuration — they connect server-to-server, not from a browser. Only enable CORS for browser-based debugging tools like MCP Inspector.

SOURCE: <https://gofastmcp.com/deployment/http> (accessed 2026-03-05)

### Mounting in Web Frameworks

PATTERN: Mount FastMCP in a Starlette application:

```python
from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount

mcp = FastMCP("MyServer")
mcp_app = mcp.http_app(path='/mcp')

app = Starlette(
    routes=[
        Mount("/mcp-server", app=mcp_app),
    ],
    lifespan=mcp_app.lifespan,  # Required — must pass lifespan
)
```

MCP endpoint accessible at `/mcp-server/mcp/`.

PATTERN: Mount FastMCP in a FastAPI application:

```python
from fastapi import FastAPI
from fastmcp import FastMCP

mcp = FastMCP("API Tools")
mcp_app = mcp.http_app(path="/")

api = FastAPI(lifespan=mcp_app.lifespan)  # Required — must pass lifespan

@api.get("/api/status")
def status():
    return {"status": "ok"}

api.mount("/mcp", mcp_app)

# Run: uvicorn app:api --host 0.0.0.0 --port 8000
# MCP endpoint: http://localhost:8000/mcp
```

CONSTRAINT: Always pass the lifespan from `mcp.http_app()` to the enclosing application. Without it, the session manager does not initialize and requests fail.

SOURCE: <https://gofastmcp.com/deployment/http> (accessed 2026-03-05)

### Horizontal Scaling

CONSTRAINT: Default Streamable HTTP transport uses server-side sessions stored in process memory. This works for single-instance deployments but fails under load balancers because most MCP clients (Claude Code, Cursor) use `fetch()` internally and do not forward `Set-Cookie` headers — sticky sessions cannot identify the correct instance.

PATTERN: Enable stateless HTTP mode for horizontally scaled deployments:

```python
# Option 1: Constructor
mcp = FastMCP("My Server", stateless_http=True)

# Option 2: run() method
mcp.run(transport="http", stateless_http=True)
```

```bash
# Option 3: Environment variable
FASTMCP_STATELESS_HTTP=true uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

CONSTRAINT: Stateless mode eliminates server-side sessions. Stateful MCP features (elicitation, sampling) are not available in stateless mode.

SOURCE: <https://gofastmcp.com/deployment/http> (accessed 2026-03-05)

### SSE Polling for Long-Running Operations

PATTERN: Use `EventStore` to enable resumable SSE connections — prevents load balancer timeouts for long-running tasks (available in v2.14.0+):

```python
from fastmcp import FastMCP, Context
from fastmcp.server.event_store import EventStore

mcp = FastMCP("My Server")

@mcp.tool
async def long_running_task(ctx: Context) -> str:
    for i in range(100):
        await ctx.report_progress(i, 100)
        if i % 30 == 0 and i > 0:
            await ctx.close_sse_stream()  # Gracefully close, client will reconnect
        await do_expensive_work()
    return "Done!"

event_store = EventStore()
app = mcp.http_app(
    event_store=event_store,
    retry_interval=2000,  # Client reconnects after 2 seconds
)
```

PATTERN: Redis-backed event store for distributed deployments:

```python
from fastmcp.server.event_store import EventStore
from key_value.aio.stores.redis import RedisStore

redis_store = RedisStore(url="redis://localhost:6379")
event_store = EventStore(
    storage=redis_store,
    max_events_per_stream=100,
    ttl=3600,
)

app = mcp.http_app(event_store=event_store)
```

SOURCE: <https://gofastmcp.com/deployment/http> (accessed 2026-03-05)

---

## `fastmcp.json` Project Configuration

SOURCE: <https://gofastmcp.com/deployment/server-configuration> (accessed 2026-03-05)

RULE: `fastmcp.json` is the canonical way to configure FastMCP projects — prefer it over CLI arguments for reproducible deployments. Available in v2.12.0+.

PATTERN: Minimal configuration — only `source` is required:

```json
{
  "$schema": "https://gofastmcp.com/public/schemas/fastmcp.json/v1.json",
  "source": {
    "path": "server.py",
    "entrypoint": "mcp"
  }
}
```

Run with: `fastmcp run` (auto-detects `fastmcp.json` in current directory)

PATTERN: Full configuration structure — source (WHERE), environment (WHAT), deployment (HOW):

```json
{
  "$schema": "https://gofastmcp.com/public/schemas/fastmcp.json/v1.json",
  "source": {
    "path": "src/server.py",
    "entrypoint": "app"
  },
  "environment": {
    "type": "uv",
    "python": ">=3.10",
    "dependencies": ["pandas>=2.0", "requests"],
    "editable": ["."]
  },
  "deployment": {
    "transport": "http",
    "host": "127.0.0.1",
    "port": 8000,
    "log_level": "DEBUG",
    "env": {
      "API_URL": "https://api.${ENVIRONMENT}.example.com",
      "DATABASE_URL": "${DB_URL}"
    }
  }
}
```

PATTERN: CLI arguments override `fastmcp.json` values for ad-hoc adjustments:

```bash
# Override port
fastmcp run fastmcp.json --port 8080

# Override transport
fastmcp run fastmcp.json --transport http

# Skip environment setup when already in a venv
fastmcp run fastmcp.json --skip-env
```

PATTERN: Multiple environment files:

```bash
fastmcp run dev.fastmcp.json   # Development
fastmcp run prod.fastmcp.json  # Production
```

Deployment configuration fields:

- `transport` — `"stdio"` (default), `"http"`, or `"sse"`
- `host` — network interface, default `"127.0.0.1"`
- `port` — port number, default `3000`
- `path` — URL path for MCP endpoint, default `"/mcp/"`
- `log_level` — `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"` (default `"INFO"`)
- `env` — environment variables; supports `${VAR_NAME}` interpolation
- `cwd` — working directory for the server process
- `args` — command-line arguments passed after `--` to the server

SOURCE: <https://gofastmcp.com/deployment/server-configuration> (accessed 2026-03-05)

---

## nginx Reverse Proxy

SOURCE: <https://gofastmcp.com/deployment/http> (accessed 2026-03-17)

In production, run your FastMCP server behind nginx for TLS termination, domain routing, and security.

### Running FastMCP as a Linux Service

Create `/etc/systemd/system/fastmcp.service`:

```ini
[Unit]
Description=FastMCP Server
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/fastmcp
ExecStart=/opt/fastmcp/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
Environment="PATH=/opt/fastmcp/.venv/bin"

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable fastmcp
sudo systemctl start fastmcp
```

### nginx Configuration

Create `/etc/nginx/sites-available/fastmcp`:

```nginx
server {
    listen 80;
    server_name mcp.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name mcp.example.com;

    ssl_certificate /etc/letsencrypt/live/mcp.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mcp.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Required for SSE (Server-Sent Events) streaming
        proxy_buffering off;
        proxy_cache off;

        # Allow long-lived connections for streaming responses
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/fastmcp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

CONSTRAINT: `proxy_buffering off` is the most critical SSE setting. Without it, nginx buffers the entire event stream and delivers it only when the connection closes, breaking real-time communication. If clients connect but never receive progress updates or streaming tool results, this is the first setting to check.

CONSTRAINT: `proxy_http_version 1.1` and `proxy_set_header Connection ''` are both required. They enable keep-alive connections and prevent clients from sending `Connection: close` to the upstream, which would terminate SSE streams.

CONSTRAINT: Default nginx `proxy_read_timeout` is 60 seconds. Long-running MCP tools will drop the connection. Set to at least 300 seconds; use [SSE Polling](#sse-polling-for-long-running-operations) for tools that may exceed any fixed timeout.

### Subpath Mounting via nginx

To serve the MCP server at a subpath (e.g., `https://example.com/api/mcp`) instead of the root domain, use a trailing slash on both the `location` block and `proxy_pass` — nginx strips the prefix before forwarding:

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000/;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
}
```

CONSTRAINT: The trailing `/` on both `location /api/` and `proxy_pass http://127.0.0.1:8000/` is required for prefix stripping. If you omit it from either side, nginx forwards the `/api/` prefix to your server, causing 404 errors on the MCP endpoint.

---

## `FASTMCP_TRANSPORT` Environment Variable

SOURCE: <https://gofastmcp.com/more/settings> (accessed 2026-03-17)

PATTERN: Set `FASTMCP_TRANSPORT` to select the default transport without passing `--transport` on every CLI invocation:

```bash
export FASTMCP_TRANSPORT=http
fastmcp run server.py  # Uses HTTP transport by default
```

Accepted values: `"stdio"` (default), `"http"`, `"sse"`, `"streamable-http"`.

PATTERN: Combine with other environment variables for a fully config-driven deployment:

```bash
FASTMCP_TRANSPORT=http FASTMCP_HOST=0.0.0.0 FASTMCP_PORT=9000 fastmcp run server.py
```

| Variable | Type | Default | Description |
| --- | --- | --- | --- |
| `FASTMCP_TRANSPORT` | `"stdio"`, `"http"`, `"sse"`, `"streamable-http"` | `stdio` | Default transport |
| `FASTMCP_HOST` | `str` | `127.0.0.1` | Bind address for HTTP |
| `FASTMCP_PORT` | `int` | `8000` | Bind port for HTTP |

---

## `fastmcp run` — Module Mode (`-m` / `--module`)

SOURCE: <https://gofastmcp.com/cli/running> (accessed 2026-03-17)

PATTERN: Run a FastMCP server packaged as a Python module using `-m`/`--module` — equivalent to `python -m my_package.server`:

```bash
fastmcp run -m my_package.server
fastmcp run --module my_package.server
```

CONSTRAINT: Module mode bypasses server object discovery. FastMCP does not import the module to find an `mcp`, `server`, or `app` variable — it delegates entirely to `python -m <module>`. The module is responsible for calling `mcp.run()` itself.

CONSTRAINT: `--transport`, `--host`, `--port`, and `--path` flags are ignored in module mode. The module manages its own server startup. FastMCP logs a warning if these options are passed alongside `-m`.

PATTERN: Use `--reload` with module mode for development auto-reload:

```bash
fastmcp run -m my_package.server --reload
```

PATTERN: Inspector support with module mode — the `fastmcp dev inspector` command also accepts `-m`:

```bash
fastmcp dev inspector -m my_package.server
```

---

## `fastmcp project prepare` — Pre-Building uv Environments

SOURCE: <https://gofastmcp.com/cli/running> (accessed 2026-03-17)

PATTERN: Pre-build a uv environment from a `fastmcp.json` file to separate slow dependency resolution from fast server startup:

```bash
# Step 1: Build the environment (one-time, performs dependency resolution)
fastmcp project prepare fastmcp.json --output-dir ./env

# Step 2: Run using the prepared environment (fast, no install step)
fastmcp run fastmcp.json --project ./env
```

The prepared directory contains a `pyproject.toml`, `.venv` with all packages installed, and a `uv.lock` for reproducibility.

CONSTRAINT: This is particularly useful in production and CI/CD where you want deterministic, pre-built environments and zero install latency on each run.

---

## `--reload` — Development Auto-Reload

SOURCE: <https://gofastmcp.com/cli/running> (accessed 2026-03-17)

PATTERN: Auto-reload watches for file changes and restarts the server automatically (available in FastMCP 3.0.0+):

```bash
fastmcp run server.py --reload

# Watch specific directories
fastmcp run server.py --reload --reload-dir ./src --reload-dir ./lib

# Combine with HTTP transport
fastmcp run server.py --reload --transport http --port 8080
```

CONSTRAINT: Auto-reload runs the server in stateless mode. For HTTP transport, bidirectional features like elicitation are unavailable during reload mode. SSE transport does not support auto-reload.

CONSTRAINT: `--reload` also works with module mode (`-m`) and the Inspector (`fastmcp dev inspector`). The Inspector has auto-reload enabled by default.

---

## Prefect Horizon — Managed Deployment

SOURCE: <https://gofastmcp.com/deployment/prefect-horizon> (accessed 2026-03-05)

PATTERN: [Prefect Horizon](https://horizon.prefect.io) is the fastest path from a FastMCP server to a production URL with built-in OAuth authentication. Free personal tier available.

Deploy in three steps:

1. Sign in at `horizon.prefect.io` with GitHub account
2. Select repository containing FastMCP server
3. Configure entrypoint and click Deploy

CONSTRAINT: Requires a GitHub repository with a Python file containing a FastMCP server instance. The `if __name__ == "__main__"` block is ignored by Horizon — do not rely on it for server startup.

CONSTRAINT: Horizon auto-detects dependencies from `requirements.txt` or `pyproject.toml` in the repository root.

After deployment, server is accessible at:

```text
https://your-server-name.fastmcp.app/mcp
```

PATTERN: Horizon redeploys automatically on every push to `main` and builds preview deployments for every PR.

PATTERN: Use `fastmcp inspect <file.py:server_object>` locally to verify what Horizon will see before deploying:

```bash
fastmcp inspect server.py:mcp
```

Horizon features:

- **Inspector** — structured view of tools, resources, prompts; run tools interactively
- **ChatMCP** — conversational testing interface optimized for rapid iteration
- **Agents** — compose multiple MCP servers into a unified chat interface
- **Gateway** — role-based access control and audit logs at the tool level
- **Registry** — catalog of servers across your organization

SOURCE: <https://gofastmcp.com/deployment/prefect-horizon> (accessed 2026-03-05)
