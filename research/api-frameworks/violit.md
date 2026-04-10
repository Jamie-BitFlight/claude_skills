---
title: Violit — Reactive Python Web Framework (Streamlit Alternative)
category: api-frameworks
keywords: Python, web framework, reactive, state management, FastAPI, zero rerun
first_published: 2026-04-10
last_reviewed: 2026-04-10
confidence:
  overview: high
  features: high
  architecture: high
  installation: high
  usage_examples: high
  limitations: medium
status: current
---

# Violit — Reactive Python Web Framework

## Overview

**Violit** is a next-generation Python web framework that adopts a **fine-grained reactive state architecture** for instant UI reactivity, fundamentally different from Streamlit's full script rerun model. The project tagline is "Faster than Light, Beautiful as Violet" — emphasizing both performance and design aesthetic. Released in early 2026 (first commit January 18, 2026), Violit targets developers building interactive dashboards and data applications who want Streamlit's simplicity without its performance bottleneck of full-script reruns.

**Current Status**: Pre-release (v0.5.2, released 2026-04-10). 368 stars on GitHub, actively maintained with 11 forks. Licensed under MIT.

---

## Problem Addressed

Streamlit democratized UI development for Python developers by allowing entire applications to be written in pure Python without HTML/CSS/JavaScript knowledge. However, its architecture — which reruns the entire Python script on every user interaction — creates performance cliffs as applications scale.

Violit solves this by inverting the architecture: instead of rerunning the entire script, it uses a **signal-based reactive state system** where only the UI components dependent on modified state are updated. This eliminates the need for Streamlit's optimization decorators (`@cache_data`, `@fragment`, `st.rerun`) because fine-grained reactivity is the default behavior.

**Direct quoted comparison from README**:

> "Streamlit's intuitive syntax is maintained, but complex optimization tools are removed at the architecture level. ❌ No `@cache_data`, `@fragment`, `st.rerun`: Thanks to the fine-grained structure, manual optimization is unnecessary."

---

## Key Statistics

| Metric | Value | Date Accessed |
|--------|-------|---|
| GitHub Stars | 368 | 2026-04-10 |
| GitHub Forks | 11 | 2026-04-10 |
| Current Version | 0.5.2 | 2026-04-10 |
| License | MIT | 2026-04-10 |
| Python Support | 3.10, 3.11, 3.12 | From pyproject.toml |
| Latest Commit | feat: update version to 0.5.2 | 2026-04-10 |
| Development Status | Pre-Alpha | From pyproject.toml classifier |
| Open Issues | 2 | 2026-04-10 |

---

## Key Features

### 1. **Fine-Grained Reactive State Architecture**

Violit's core innovation is replacing Streamlit's full-rerun model with a reactive state system inspired by frontend frameworks like SolidJS and Signals.

**Extract from `src/violit/state.py` (lines 106-139)**:
```python
class State:
    def __init__(self, name: str, default_value: Any):
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'default_value', default_value)
        object.__setattr__(self, '_subscribers', [])

    def set(self, new_value: Any):
        store = get_session_store()
        old_value = store['states'].get(self.name, self.default_value)
        store['states'][self.name] = new_value
        if 'dirty_states' not in store: store['dirty_states'] = set()
        store['dirty_states'].add(self.name)
        # Fire side-effect subscribers
        for cb, wants_old in list(self._subscribers):
            try:
                cb(new_value, old_value) if wants_old else cb(new_value)
```

The `State` class maintains a dependency tracker that records which UI components depend on each state variable. When state is modified via `.set()`, only components explicitly referencing that state are marked dirty and re-rendered — the rest of the application skips execution entirely.

### 2. **Streamlit API Compatibility with Reactive Enhancements**

Violit mirrors Streamlit's API surface (~50+ widgets) but returns `State` objects from input widgets instead of raw values, enabling automatic reactivity.

From the **Streamlit API Support Matrix** (doc/Streamlit API Support Matrix.md):

| Widget Category | Coverage | Example |
|---|---|---|
| Text & Media | ✅ Full | `app.write`, `app.markdown`, `app.title`, `app.image`, `app.video` |
| Data & Charts | ✅ Full | `app.dataframe` (Ag-Grid native), `app.plotly_chart`, `app.metric` |
| Input Widgets | ✅ Full | `app.text_input`, `app.slider`, `app.selectbox`, `app.file_uploader` |
| Layout | ✅ Full | `app.columns`, `app.tabs`, `app.expander`, `app.sidebar` |
| Chat Interface | ✅ Full | `app.chat_input`, `app.chat_message` |

Notable unsupported widgets: `st.latex`, `st.map`, `st.popover`, `st.camera_input` — all marked as low-priority or having superior alternatives (e.g., use Mapbox via `plotly_chart` instead of `st.map`).

### 3. **Hybrid Execution Runtime (WebSocket + HTTP/HTMX)**

From README:
> "**WebSocket Mode**: Ultra-low latency bidirectional communication (Default)
> **Lite Mode**: HTTP-based, advantageous for handling large-scale concurrent connections"

The framework ships with two execution engines (`src/violit/engine.py`):
- **WsEngine**: Maintains persistent WebSocket connections, pushing component updates to clients in real-time (~10-100ms latency).
- **LiteEngine**: Uses HTMX for request-response cycles, better for serverless or scale-out deployments.

### 4. **Desktop Application Mode**

Violit can run as a native desktop application without Electron using `pywebview` (a lightweight WebView wrapper).

From README:
> "**Desktop Mode**: Can run as a perfect desktop application without Electron using the `--native` option."

Execution: `python app.py --native` spawns a native window (GTK on Linux, Cocoa on macOS, Win32 on Windows) running the same app.

### 5. **Theme System with 20+ Professional Presets**

From README theme families and app initialization:

```python
app = vl.App(theme='cyberpunk')  # Set at init
app.set_theme('ocean')            # Change at runtime
```

Theme families documented in `doc/LLM_REFERENCE.md` (lines 316-323):
- **Dark**: `dark`, `dracula`, `monokai`, `ocean`, `forest`, `sunset`
- **Light**: `light`, `pastel`, `retro`, `nord`, `soft_neu`
- **Tech**: `cyberpunk`, `terminal`, `cyber_hud`, `blueprint`
- **Professional**: `editorial`, `bootstrap`, `ant`, `material`, `lg_innotek`

CSS is generated at runtime and compiled into the theme engine (`src/violit/theme.py`, 1404 lines).

### 6. **Hot Reload Development Mode**

Built-in file watcher (`FileWatcher` class in `src/violit/app.py`, lines 52-108) detects Python file changes and reloads the application without manual restart.

Invoked via: `python app.py --reload`

### 7. **Form Submission and Batch Input**

Violit provides `app.form()` context manager for batch input (all fields submitted together), addressing Streamlit's limitation where each widget update triggers a full rerun:

```python
with app.form("login"):
    username = app.text_input("Username")
    password = app.text_input("Password", type="password")
    submitted = app.form_submit_button("Login")
```

---

## Technical Architecture

### Core Components

**1. State Management (`src/violit/state.py`, 407 lines)**

The reactive foundation consists of two primary classes:

- **`State`**: Represents a single mutable reactive value. Supports value access (`.value`), assignment (`.set(new_value)`), subscriptions (`.subscribe(callback)`), and operator overloading (`count + 1`, `name + "!"` return `ComputedState`).

- **`ComputedState`**: Derived state computed from one or more `State` objects. Automatically recalculates when dependencies change. Example: `computed_total = count * 2` creates a `ComputedState` that updates whenever `count` changes.

**Session Storage Model** (from `state.py` lines 34-81):
```python
STATIC_STORE = {}  # Static components (built once at app init)
GLOBAL_STORE = TTLCache(maxsize=1000, ttl=1800)  # User sessions (1800s TTL)

def get_session_store():
    sid = session_ctx.get()
    if sid is None:
        return STATIC_STORE
    if sid not in GLOBAL_STORE:
        GLOBAL_STORE[sid] = {
            'states': {},
            'tracker': DependencyTracker(),  # Maps state names → component IDs
            'builders': {},
            'actions': {},
            'component_count': 0,
            'fragment_components': {},
            'order': [],
            'sidebar_order': [],
            'theme': Theme(initial_theme)
        }
    return GLOBAL_STORE[sid]
```

The `DependencyTracker` (lines 6-32) records which UI components reference which state variables. When a state is modified, `get_dirty_components(state_name)` returns the set of component IDs that need re-rendering.

**2. Broadcast System (`src/violit/broadcast.py`, 450 lines)**

WebSocket-based real-time broadcasting for pushing updates to connected clients:

- **`Broadcaster` class**: Manages event distribution to active sessions.
- **Core Methods**:
  - `eval_all(js_code)`: Execute arbitrary JavaScript on all clients (low-level API).
  - `broadcast_event(event_name, data)`: Dispatch domain events to all sessions (e.g., `'post_added'`). Events are auto-assigned a UUID for deduplication.
  - `get_active_sessions()`: Returns list of currently connected session IDs.

Threading model: Broadcast calls spawn background asyncio threads to avoid blocking the request handler.

**3. Execution Engines (`src/violit/engine.py`, 47 lines)**

Two pluggable execution models:

- **`WsEngine`**: WebSocket-based real-time updates. Maintains `sockets: Dict[sid, WebSocket]` and supports:
  - `push_updates(sid, components)`: Send component HTML to client, replacing by ID.
  - `push_eval(sid, code)`: Execute JavaScript on client.

- **`LiteEngine`**: HTMX/HTTP-based alternative. Click attributes use `hx-post` instead of `onclick`.

The app selects an engine at initialization (`app = vl.App(mode="ws")` or `mode="lite"`).

**4. Component Rendering (`src/violit/component.py`, 80 lines)**

The `Component` base class represents any renderable UI element. Key methods:
- `render()`: Returns HTML string of the component.
- `id` property: Unique identifier within the session (auto-generated or explicit).

Components are stateless — their output depends entirely on the current state values and rendering context.

**5. Widget System (`src/violit/widgets/`, 266KB across 12 files)**

Modular widget mixins implemented as class mixins on the main `App` class:

- **TextWidgetsMixin**: `title`, `header`, `markdown`, `code`, `write`, `latex`, `divider`.
- **InputWidgetsMixin**: `text_input`, `slider`, `checkbox`, `selectbox`, `multiselect`, `file_uploader`, `date_input`, `color_picker`.
- **DataWidgetsMixin**: `dataframe` (Ag-Grid), `table`, `metric`, `json`, `data_editor`.
- **ChartWidgetsMixin**: `plotly_chart`, `pyplot`, `line_chart`, `bar_chart`, `area_chart`, `scatter_chart`.
- **MediaWidgetsMixin**: `image`, `audio`, `video`.
- **LayoutWidgetsMixin**: `columns`, `container`, `expander`, `tabs`, `empty`, `sidebar`.
- **StatusWidgetsMixin**: `success`, `error`, `warning`, `info`, `spinner`, `progress`, `toast`, `balloons`, `snow`.
- **FormWidgetsMixin**: `form`, `form_submit_button`.
- **ChatWidgetsMixin**: `chat_message`, `chat_input`, `chat_history`.
- **CardWidgetsMixin**: `card` (custom card component).
- **ListWidgetsMixin**: Loop/conditional rendering helpers.

Each mixin contains the logic for rendering its widgets using Shoelace Web Components (the framework's standard UI library) with dynamically injected Plotly and AG-Grid libraries.

**6. Theme Engine (`src/violit/theme.py`, 1404 lines)**

A full CSS generation and theming system. The `Theme` class:
- Loads preset theme definitions from hardcoded theme data.
- Generates CSS variables (e.g., `--sl-color-primary`, `--sl-color-neutral`).
- Supports runtime theme switching via `app.set_theme()`.
- Provides 30+ named themes (verified from codebase, though README lists only ~20).

### Data Flow: State Change to UI Update

**Example scenario**: User clicks button to increment a counter.

1. **User Action**: Browser sends `onclick` message (WebSocket) to backend with component ID.
2. **Action Handler** (`app.py` WebSocket route): Looks up the component's callback function and executes it.
3. **State Mutation** (callback): `count.set(count.value + 1)` is called. The `State.set()` method:
   - Updates the value in the session store.
   - Marks state as "dirty": `store['dirty_states'].add('count')`.
   - Fires side-effect subscribers (if any).
4. **Dependency Tracking**: The `DependencyTracker` queries which components depend on the `'count'` state.
5. **Dirty Component Collection**: All components that depend on `'count'` are collected.
6. **Re-render**: Only those components execute their builder functions again, producing new HTML.
7. **Broadcast**: Component HTML is sent to the client via WebSocket.
8. **DOM Update** (client-side): JavaScript replaces the component by ID, preserving other DOM nodes.

This mechanism ensures **zero rerun** of the main script and only dirty component logic executes.

### Rendering Context

Three context variables track rendering state (from `context.py`):
- **`session_ctx`**: Current session ID (None during static build, set during user session).
- **`rendering_ctx`**: Component ID currently being rendered (used by dependency tracker).
- **`layout_ctx`**: Current layout context (`"main"`, `"sidebar"`, or custom).

These use Python's `contextvars` module for thread-safe context isolation.

---

## Installation & Usage

### Installation

```bash
pip install violit

# Or development version
pip install git+https://github.com/violit-dev/violit.git
```

**Python Version**: Requires Python 3.10+. Tested on 3.10, 3.11, 3.12.

From `pyproject.toml`:
```toml
requires-python = ">=3.10"
```

### Quick Start Example

From README:

```python
import violit as vl

app = vl.App(title="Hello Violit", theme='ocean')

app.title("💜 Hello, Violit!")
app.markdown("Experience the speed of **Zero Rerun**.")

count = app.state(0)

col1, col2 = app.columns(2)
with col1:
    app.button("➕ Plus", on_click=lambda: count.set(count.value + 1))
with col2:
    app.button("➖ Minus", on_click=lambda: count.value - 1))

app.metric("Current Count", count)

app.run()
```

### Execution Modes

```bash
# WebSocket mode (default, lowest latency)
python app.py

# Desktop app mode (native window)
python app.py --native

# Custom port
python app.py --port 8020

# Hot reload on file change
python app.py --reload
```

### Core API Patterns

**State Creation and Reactivity** (from `doc/LLM_REFERENCE.md`, lines 78-96):

```python
count = app.state(0)           # Create with default value
name = app.state("", key="user_name")  # With explicit key

# Reading
count.value    # → 0
count()        # Shorthand

# Writing
count.set(5)       # Preferred in callbacks
count.value = 5    # Also works

# Reactivity rules:
app.text(count)                   # ✅ Reactive (State object)
app.text(count.value)             # ❌ Not reactive (frozen value)
app.text("Count: " + count)       # ✅ Reactive (operator overload)
app.text(lambda: f"Count: {count.value}")  # ✅ Reactive (lambda)
```

**Button Handling** (critical difference from Streamlit):

```python
# ❌ Streamlit pattern (does NOT work in Violit)
if app.button("Click"):
    do_something()

# ✅ Violit pattern (correct)
app.button("Click", on_click=do_something)
app.button("Increment", on_click=lambda: count.set(count.value + 1))
```

Buttons do NOT return booleans in Violit. The `on_click` callback receives no arguments and executes immediately when clicked.

**Layout with Context Managers**:

```python
col1, col2 = app.columns(2)
with col1:
    app.text("Left column")
with col2:
    app.text("Right column")

# Column ratios
c1, c2, c3 = app.columns([2, 1, 1])  # 50%, 25%, 25% widths

with app.sidebar:
    app.markdown("## Sidebar")
    theme = app.selectbox("Theme", ["dark", "light", "ocean"])
    app.button("Apply", on_click=lambda: app.set_theme(theme.value))
```

**Input Widgets Return State**:

```python
# All input widgets return State objects
name = app.text_input("Name", value="Alice")  # State[str]
age = app.number_input("Age", value=25)        # State[int]
tags = app.multiselect("Tags", ["A", "B"])    # State[List[str]]

# Access current values in callbacks
app.button("Greet", on_click=lambda: app.toast(f"Hello {name.value}!"))

# Display reactively
app.text("Your name is " + name)  # Updates whenever user types
```

---

## Comparison with Alternatives

### vs Streamlit

| Aspect | Streamlit | Violit |
|--------|-----------|--------|
| **Execution Model** | Full script rerun on every interaction | Fine-grained state reactivity (only dirty components re-render) |
| **Performance** | Degrades with data size (must cache) | Consistent (no caching needed) |
| **Optimization Decorators** | Requires `@cache_data`, `@fragment`, `st.rerun` | None needed (by design) |
| **Desktop Apps** | Not supported | ✅ Native apps via `--native` |
| **State API** | Dict-based `st.session_state` | Object-based `State` with automatic dependency tracking |
| **Button Pattern** | `if st.button()` (if-block) | `app.button(..., on_click=fn)` (callback) |
| **Learning Curve** | Very easy | Very easy (90% API compatibility) |

**Direct Quote from README Comparison** (lines 125-148):

> "Streamlit re-executes the **entire script** on button click, but Violit executes only **that function**."
>
> ```python
> # Violit
> count = app.state(0)
> app.button("Click", on_click=lambda: count.set(count.value + 1))
> app.write(count)
> ```

### vs Dash

Dash requires callback registration with `@callback` decorators specifying Input/Output IDs. Violit's reactive state system eliminates this boilerplate.

```python
# Dash (callback hell)
@callback(Output("out", "children"), Input("btn", "n_clicks"))
def update(n):
    return f"Value: {n}"

# Violit (automatic reactivity)
count = app.state(0)
app.button("Click", on_click=lambda: count.set(count.value + 1))
app.write(count)  # Auto-updates
```

### vs Panel / NiceGUI

Panel uses Param for state binding, NiceGUI uses Vue.js binding syntax. Both require explicit binding declarations. Violit's operator overloading and dependency tracking make bindings implicit.

```python
# NiceGUI (explicit binding)
ui.label().bind_text_from(count, 'val', backward=lambda x: f'Value: {x}')

# Violit (implicit reactivity)
app.text("Value: " + count)  # No binding declaration
```

### vs Reflex

Reflex compiles Python to JavaScript, requiring class-based state and a build step. Violit runs pure Python:

```python
# Reflex (class + compile)
class State(rx.State):
    count: int = 0
    def increment(self):
        self.count += 1
# Requires: reflex init, reflex run

# Violit (pure Python, no compile)
count = app.state(0)
app.button("Click", on_click=lambda: count.set(count.value + 1))
app.run()  # Direct execution
```

---

## Relevance to Claude Code Development

Violit is highly relevant for the Claude Code ecosystem in several dimensions:

### 1. **AI-Friendly Framework Design**

Violit's API is explicitly designed to be easily generated and understood by AI systems. Evidence:

- **Streamlit API Compatibility**: Most developers know Streamlit, so Violit's API is immediately familiar to LLM-based code generation systems.
- **LLM Reference Documentation** (`doc/LLM_REFERENCE.md`, 490 lines): Comprehensive guide documenting all API changes vs Streamlit, with worked examples. The document is labeled "AI/LLM Code Generation Reference" and includes a "Common Mistakes" section explicitly addressing patterns that confuse code generation (e.g., button if-blocks that don't work).
- **Consistent Naming**: All widgets follow Streamlit naming, all methods are named predictably, no surprising aliases.

### 2. **Rapid Prototyping for Agent-Generated UIs**

For agents building interactive dashboards (data analysis, log viewers, monitoring tools), Violit's zero-rerun architecture means:
- Responsive UIs even with slow computations (computation doesn't block reactivity).
- No manual optimization needed (no need for agents to understand `@cache_data` or `@fragment`).
- Desktop mode allows shipping standalone apps without deployment infrastructure.

### 3. **Hybrid Execution Models Support Agentic Workflows**

The WebSocket and HTTP/HTMX modes support different deployment patterns:
- **WebSocket**: Low-latency interactive dashboards where agents are actively running computations.
- **Lite (HTMX)**: Stateless agents that handle each request independently (better for serverless, Kubernetes, multi-replica scenarios).

### 4. **State as First-Class Reactive Objects**

For agents generating complex UIs with many dependent values, Violit's reactive state system means:
- Agents don't need to manually track dependencies or write callback glue code.
- Computed states (e.g., `total = price * quantity`) are automatically tracked.
- Operators on state objects (`count + 1`, `name + "!"`) compose naturally.

### 5. **Theme and Styling as Configuration**

The 30+ built-in themes and CSS variable system mean agents can generate polished UIs without custom styling logic:
- `app = vl.App(theme='cyberpunk')` requires no CSS knowledge.
- Runtime theme switching (`app.set_theme()`) enables user preference UIs.

### 6. **Desktop Application Distribution**

For autonomous agents that need to deliver standalone tools to users, the `--native` mode is a distribution advantage over Streamlit.

---

## Limitations and Caveats

### Documented Limitations

**Unsupported Widgets** (from Streamlit API Support Matrix):
- `st.latex` (LaTeX rendering)
- `st.map` (interactive map) — recommended alternative: use Mapbox via `plotly_chart`
- `st.popover` — use `app.dialog` instead
- `st.camera_input` (webcam capture)

**Limited Third-Party Integration** (from Support Matrix):
- `streamlit-lottie` — not yet integrated (marked "Planned").
- `streamlit-webrtc` — real-time video/audio support marked "Planned".
- Some `streamlit-extras` components may require manual CSS migration.

### Pre-Release Constraints

**Development Status**: Violit is classified as "Pre-Alpha" in `pyproject.toml`. Implications:
- API surface may change before v1.0 (though core State and widget APIs appear stable).
- Undocumented edge cases may exist.
- Community plugin ecosystem is nascent (no third-party widget packages found).

From `pyproject.toml`:
```python
classifiers = [
    "Development Status :: 2 - Pre-Alpha",
```

### Performance Characteristics Not Benchmarked

README states: "*Detailed benchmark data will be updated soon.*" and shows placeholder for benchmark chart. While the fine-grained reactivity architecture is theoretically superior to full reruns, concrete latency figures are not yet published. Benchmark data would be critical for production adoption decisions.

### Limited Async Support

From Roadmap (README lines 296-310):
> ⏳ **async**: Async processing support

Implies current version has limited async/concurrent task handling. For compute-heavy agents, blocking operations on the main thread could still freeze the UI.

### Deployment Infrastructure

Unlike Streamlit Cloud and Streamlit Community Cloud, Violit has:
- No announced cloud hosting platform (though `Violit.Cloud` appears in roadmap as "⏳ Planned").
- Requires manual deployment on FastAPI-compatible hosts (Uvicorn, Gunicorn, cloud VMs).
- No built-in secrets management or environment variable support documented.

### Documentation Gaps

- No official tutorial series (README is comprehensive but brief).
- No API docs beyond the LLM reference and support matrix.
- Limited examples in repo (README hello-world, but no real-world dashboards in `/examples` directory).

### State Serialization and Persistence

State is stored in TTLCache with 1800s TTL (from `state.py` line 37). For long-running applications or session persistence across restarts:
- State is lost after 30 minutes of inactivity.
- No built-in state snapshot/restore mechanism documented.
- Workaround: manually implement state loading/saving via `state.on_change()` callbacks to a database.

---

## References

1. **GitHub Repository**: <https://github.com/violit-dev/violit> (accessed 2026-04-10)
2. **README.md**: Full feature overview and comparison tables. <https://github.com/violit-dev/violit#readme> (accessed 2026-04-10)
3. **pyproject.toml**: Package metadata, dependencies, classifiers. (accessed 2026-04-10 from shallow clone)
4. **Source Code**:
   - `src/violit/state.py`: State and ComputedState classes, dependency tracking (407 lines)
   - `src/violit/app.py`: Main App class, widget mixins, execution engines (2300+ lines)
   - `src/violit/broadcast.py`: WebSocket broadcasting system (450 lines)
   - `src/violit/engine.py`: WsEngine and LiteEngine implementations (47 lines)
   - `src/violit/widgets/`: 12 mixin files, 266KB total, implement Streamlit API
   - `src/violit/theme.py`: Theme engine and CSS generation (1404 lines)
5. **Documentation**:
   - `doc/Streamlit API Support Matrix.md`: Widget compatibility table (accessed 2026-04-10)
   - `doc/LLM_REFERENCE.md`: Comprehensive API reference for code generation (490 lines, accessed 2026-04-10)
6. **GitHub API**: Repository metadata snapshot (368 stars, 2 open issues as of 2026-04-10)

---

## Freshness Tracking

**Last Reviewed**: 2026-04-10
**Next Review**: 2026-07-10 (3 months)

### What May Change

- **API Breaking Changes**: Pre-alpha status means core APIs could shift before v1.0. Monitor releases.
- **Performance Benchmarks**: README promises "detailed benchmark data will be updated soon" — track published results.
- **Async Support**: Roadmap item in progress; new async APIs may be added.
- **Custom Themes and Components**: Both marked "⏳ Planned" on roadmap; community extensions will appear.
- **Cloud Platform**: `Violit.Cloud` service promised but not yet available.
- **Package Versioning**: Current version 0.5.2; watch for minor versions (0.6.x, 0.7.x) until 1.0.0.

### Confidence Map

| Section | Confidence | Reason |
|---------|------------|--------|
| Overview | high | Official README and GitHub repo as primary source |
| Problem Addressed | high | Architecture comparison is explicit in docs and code |
| Key Statistics | high | GitHub API data and pyproject.toml (machine-readable) |
| Key Features | high | All features extracted from code and official docs |
| Technical Architecture | high | Full source code read; state, broadcast, engine models documented |
| Installation | high | Official installation command and Python version verified |
| Usage Examples | high | All examples from README and LLM_REFERENCE.md docs |
| Comparison with Alternatives | high | Explicit comparisons in README; code patterns verified |
| Limitations | medium | Undocumented limitations inferred from missing features and "Planned" roadmap items. Performance benchmarks not yet published. |
| Relevance to Claude Code | high | AI-friendly design documented in official `doc/LLM_REFERENCE.md` |

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [FastAPI](./fastapi.md) | api-frameworks | Modern Python web framework; Violit layers reactive UI on top of FastAPI-compatible async patterns |
| [Tornado](./tornado.md) | api-frameworks | Python web framework with native WebSocket support; complementary for live-update dashboards requiring persistent connections |
| [Motia](./motia.md) | api-frameworks | Unified backend framework; alternative approach to state management and handler composition vs Violit's fine-grained reactivity |
| [PocketBase](./pocketbase.md) | api-frameworks | Self-contained backend with realtime subscriptions and admin dashboard; Violit handles interactive frontend while PocketBase provides backend |
| [AnyIO](../async-libraries/anyio.md) | async-libraries | Backend-agnostic async concurrency; Violit's async runtime depends on core patterns like this |
| [Trio](../async-libraries/trio.md) | async-libraries | Structured concurrency library; alternative async foundation to asyncio that Violit could integrate with |
| [Ultra-MCP](../mcp-ecosystem/ultra-mcp.md) | mcp-ecosystem | React dashboard with real-time state updates; shares reactive UI architecture patterns with Violit's signal-based model |

---

## Entry Metadata

- **Resource Type**: Python Framework / API
- **Domain**: Web UI Development, Data Dashboards, Python Ecosystem
- **Maturity**: Early (Pre-Alpha, v0.5.2)
- **Community Size**: Small but growing (368 stars, 11 forks, actively maintained)
- **Use Cases**: Interactive dashboards, data analysis tools, monitoring UIs, desktop applications
- **Claude Code Relevance**: High — AI-friendly API design, zero-rerun architecture reduces optimization burden for agents
