# FastMCP Apps Reference

Interactive UI extension for MCP tools — use this when a tool needs to return a rendered iframe instead of plain text or JSON.

> **WARNING: FastMCP 3.1 Python-native app framework (unreleased).** The Python-native framework described in `apps/overview.mdx` — which generates UIs without writing HTML or JavaScript — is NOT available in FastMCP 3.0. Do NOT generate code using that framework. Only the low-level HTML/JS API documented below is available in stable FastMCP 3.0.
>
> SOURCE: <https://gofastmcp.com/apps/overview> (accessed 2026-03-05)

---

## What Is Available in FastMCP 3.0

The MCP Apps extension (`io.modelcontextprotocol/ui`) allows tools to return interactive HTML UIs rendered in a sandboxed iframe inside the host client. FastMCP provides typed helpers for working with this extension directly.

Available in FastMCP 3.0:

- `AppConfig` — links tools to UI resources and controls visibility
- `ui://` resources — automatically served with MIME type `text/html;profile=mcp-app`
- `ResourceCSP` and `ResourcePermissions` — iframe security and sandbox controls

CONSTRAINT: The low-level API requires you to write HTML yourself and wire up host communication via the `@modelcontextprotocol/ext-apps` JavaScript SDK.

SOURCE: <https://gofastmcp.com/apps/overview> (accessed 2026-03-05)

---

## How It Works

An MCP App has two parts:

1. A **tool** that does the computation and returns data
2. A **`ui://` resource** containing the HTML that renders that data

The tool declares which resource to use via `AppConfig`. When the host calls the tool, it also fetches the linked resource, renders it in a sandboxed iframe, and pushes the tool result into the app via `postMessage`. The app can also call tools back, enabling interactive workflows.

```python
import json

from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig, ResourceCSP

mcp = FastMCP("My App Server")

# The tool does the computation
@mcp.tool(app=AppConfig(resource_uri="ui://my-app/view.html"))
def generate_chart(data: list[float]) -> str:
    return json.dumps({"values": data})

# The resource provides the UI
@mcp.resource("ui://my-app/view.html")
def chart_view() -> str:
    return "<html>...</html>"
```

SOURCE: <https://gofastmcp.com/apps/low-level> (accessed 2026-03-05)

---

## AppConfig

PATTERN: Import from `fastmcp.server.apps`. On tools, set `resource_uri` to point to the UI resource:

```python
from fastmcp.server.apps import AppConfig

@mcp.tool(app=AppConfig(resource_uri="ui://my-app/view.html"))
def my_tool() -> str:
    return "result"
```

PATTERN: Pass a raw dict with camelCase keys (matches the wire format):

```python
@mcp.tool(app={"resourceUri": "ui://my-app/view.html"})
def my_tool() -> str:
    return "result"
```

### Tool Visibility

The `visibility` field controls where a tool appears in the host:

- `["model"]` — visible to the LLM (default behavior)
- `["app"]` — only callable from within the app UI, hidden from the LLM
- `["model", "app"]` — both

```python
@mcp.tool(
    app=AppConfig(
        resource_uri="ui://my-app/view.html",
        visibility=["app"],
    )
)
def refresh_data() -> str:
    """Only callable from the app UI, not by the LLM."""
    return fetch_latest()
```

CONSTRAINT: On **resources**, `resource_uri` and `visibility` must NOT be set — the resource is the UI. Use `AppConfig` on resources only for `csp`, `permissions`, and display settings.

SOURCE: <https://gofastmcp.com/apps/low-level> (accessed 2026-03-05)

---

## UI Resources

RULE: Resources using the `ui://` scheme are automatically served with MIME type `text/html;profile=mcp-app`. You do not need to set this manually.

```python
@mcp.resource("ui://my-app/view.html")
def my_view() -> str:
    return "<html>...</html>"
```

The HTML communicates with the host using the `@modelcontextprotocol/ext-apps` JavaScript SDK:

```html
<script type="module">
  import { App } from "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps";

  const app = new App({ name: "My App", version: "1.0.0" });

  // Receive tool results pushed by the host
  app.ontoolresult = ({ content }) => {
    const text = content?.find(c => c.type === 'text');
    if (text) {
      document.getElementById('output').textContent = text.text;
    }
  };

  // Connect to the host
  await app.connect();
</script>
```

JavaScript SDK methods available on the `App` object:

- `app.ontoolresult` — callback receiving tool results pushed by the host
- `app.callServerTool({name, arguments})` — call a server tool from within the app
- `app.onhostcontextchanged` — callback for host context changes
- `app.getHostContext()` — get current host context

SOURCE: <https://gofastmcp.com/apps/low-level> (accessed 2026-03-05)

---

## Security

CONSTRAINT: Apps run in sandboxed iframes with a deny-by-default Content Security Policy. By default, only inline scripts and styles are allowed — no external network access.

### Content Security Policy

PATTERN: Declare external resources needed by your app using `ResourceCSP`:

```python
from fastmcp.server.apps import AppConfig, ResourceCSP

@mcp.resource(
    "ui://my-app/view.html",
    app=AppConfig(
        csp=ResourceCSP(
            resource_domains=["https://unpkg.com", "https://cdn.example.com"],
            connect_domains=["https://api.example.com"],
        )
    ),
)
def my_view() -> str:
    return "<html>...</html>"
```

CSP fields and what they control:

- `connect_domains` — `fetch`, XHR, WebSocket (`connect-src`)
- `resource_domains` — scripts, images, styles, fonts (`script-src`, etc.)
- `frame_domains` — nested iframes (`frame-src`)
- `base_uri_domains` — document base URI (`base-uri`)

### Sandbox Permissions

PATTERN: Request browser capabilities (camera, clipboard) via `ResourcePermissions`:

```python
from fastmcp.server.apps import AppConfig, ResourcePermissions

@mcp.resource(
    "ui://my-app/view.html",
    app=AppConfig(
        permissions=ResourcePermissions(
            camera={},
            clipboard_write={},
        )
    ),
)
def my_view() -> str:
    return "<html>...</html>"
```

CONSTRAINT: Hosts may or may not grant requested permissions. Use JavaScript feature detection as a fallback.

SOURCE: <https://gofastmcp.com/apps/low-level> (accessed 2026-03-05)

---

## Checking Client Support

PATTERN: Check at runtime whether the host supports the Apps extension before returning UI-optimized content:

```python
from fastmcp import Context
from fastmcp.server.apps import AppConfig, UI_EXTENSION_ID

@mcp.tool(app=AppConfig(resource_uri="ui://my-app/view.html"))
async def my_tool(ctx: Context) -> str:
    if ctx.client_supports_extension(UI_EXTENSION_ID):
        return rich_response()
    else:
        return plain_text_response()
```

SOURCE: <https://gofastmcp.com/apps/low-level> (accessed 2026-03-05)

---

## Complete Example: QR Code Server

Requires `qrcode[pil]`. Based on the official MCP Apps example.

```python
import base64
import io

import qrcode
from mcp import types

from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig, ResourceCSP
from fastmcp.tools import ToolResult

mcp = FastMCP("QR Code Server")

VIEW_URI = "ui://qr-server/view.html"


@mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
def generate_qr(text: str = "https://gofastmcp.com") -> ToolResult:
    """Generate a QR code from text."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image()
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode()

    return ToolResult(
        content=[types.ImageContent(type="image", data=b64, mimeType="image/png")]
    )


@mcp.resource(
    VIEW_URI,
    app=AppConfig(csp=ResourceCSP(resource_domains=["https://unpkg.com"])),
)
def view() -> str:
    """Interactive QR code viewer."""
    return """\
<!DOCTYPE html>
<html>
<head>
  <meta name="color-scheme" content="light dark">
  <style>
    body { display: flex; justify-content: center;
           align-items: center; height: 340px; width: 340px;
           margin: 0; background: transparent; }
    img  { width: 300px; height: 300px; border-radius: 8px; }
  </style>
</head>
<body>
  <div id="qr"></div>
  <script type="module">
    import { App } from
      "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps";

    const app = new App({ name: "QR View", version: "1.0.0" });

    app.ontoolresult = ({ content }) => {
      const img = content?.find(c => c.type === 'image');
      if (img) {
        const el = document.createElement('img');
        el.src = `data:${img.mimeType};base64,${img.data}`;
        el.alt = "QR Code";
        document.getElementById('qr').replaceChildren(el);
      }
    };

    await app.connect();
  </script>
</body>
</html>"""
```

SOURCE: <https://gofastmcp.com/apps/low-level> (accessed 2026-03-05)

---

## Prefab Apps (FastMCP 3.1, Experimental)

> **EXPERIMENTAL — FastMCP 3.1+.** Prefab is in active early development; its API changes frequently. Pin `prefab-ui` to a specific version. Not recommended for production.
>
> SOURCE: <https://gofastmcp.com/apps/prefab> (accessed 2026-03-17)

[Prefab UI](https://prefab.prefect.io) is a declarative UI framework for Python. You describe your interface using Python components and return it from a tool — FastMCP registers the renderer, wires the protocol metadata, and delivers the component tree to the host. No HTML or JavaScript required.

### Installation

```bash
pip install "fastmcp[apps]"
```

Pin `prefab-ui` to a specific version to avoid breaking changes from a routine upgrade:

```toml
# pyproject.toml
dependencies = [
    "fastmcp[apps]",
    "prefab-ui==0.8.0",  # pin to a known working version
]
```

### Basic Usage — `@mcp.tool(app=True)`

Use `app=True` on the `@mcp.tool` decorator. Return a `PrefabApp` or a Prefab component directly:

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

RULE: `app=True` is equivalent to a return type annotation of `PrefabApp` or `Component`. Explicit `app=True` is recommended for clarity and is required when the return type is `ToolResult`.

### What You Can Return

**Components directly** — FastMCP wraps them in a `PrefabApp` automatically:

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

**`PrefabApp`** — for explicit control over initial state and the rendering engine:

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

**`ToolResult`** — when you need the LLM to understand the result alongside the UI (both audiences served):

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

The user sees the chart. The LLM sees the text summary and can reason about it.

### Previewing Prefab Apps Locally

Use `fastmcp dev apps` to launch a browser-based preview UI for your Prefab App tools:

```bash
fastmcp dev apps server.py
```

### How It Works Internally

When a tool returns a Prefab component or `PrefabApp`, FastMCP:

1. Registers a shared `ui://prefab/renderer.html` resource (fetched once by the host, reused across all Prefab tools).
2. Wires the tool metadata so the host loads the renderer iframe when displaying the result.
3. Serializes the component tree as `structuredContent` on the tool result, which the renderer interprets and displays.

No configuration is required beyond `app=True`.

### Coexistence with Custom HTML Apps

Prefab tools and custom HTML tools coexist in the same server. Prefab tools share a single renderer; custom tools point to their own:

```python
from fastmcp.server.apps import AppConfig

@mcp.tool(app=True)
def team_directory() -> PrefabApp:
    ...

@mcp.tool(app=AppConfig(resource_uri="ui://my-app/map.html"))
def map_view() -> str:
    ...
```

SOURCE: <https://gofastmcp.com/apps/prefab> (accessed 2026-03-17)
