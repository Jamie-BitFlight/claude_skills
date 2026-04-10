---
created: 2026-04-10
updated: 2026-04-10
resource: Violit
status: draft
category: ui-frameworks
---

# Violit

**Tagline**: "Faster than Light, Beautiful as Violet. Structure of Streamlit × Performance of React."

**Version**: 0.5.2 (released 2026-04-09)

**License**: MIT

**Repository**: <https://github.com/violit-dev/violit>

**Homepage**: <https://github.com/violit-dev/violit>

---

## Overview

Violit is a next-generation Python web framework that adopts a **fine-grained state architecture** for instant reactivity, fundamentally different from Streamlit's full-script rerun model. It maintains Streamlit's elegant, developer-friendly syntax while delivering the performance characteristics of modern reactive frameworks like React. Violit enables building responsive web dashboards and applications in pure Python without the performance penalties of traditional frameworks.

**Primary use case**: Data scientists and Python developers building real-time dashboards, analytical tools, and interactive applications without resorting to JavaScript or complex callback chains.

---

## Problem Addressed

**Streamlit's architectural limitation**: Streamlit reruns the entire script on every user interaction, causing performance degradation as data size increases and requiring manual optimization decorators (`@cache_data`, `@fragment`, `st.rerun()`) to maintain responsiveness.

Violit solves this by:

1. **Zero full reruns**: "Updates only the components connected to the modified State" — fine-grained updates target only affected UI elements
2. **Optimization by default**: No decorators or manual caching required; the reactive architecture makes expensive optimizations unnecessary
3. **Consistent responsivity**: "Maintains consistent reactivity regardless of data scale" — slider interactions, form updates, and data transformations respond at interactive speeds even with large datasets

---

## Key Statistics

- **GitHub Stars**: 368 (as of 2026-04-10)
- **GitHub Forks**: 11 (as of 2026-04-10)
- **Python Version Support**: 3.10+
- **Creation Date**: 2026-01-18
- **Last Update**: 2026-04-09 (released v0.5.2)
- **Development Status**: Pre-Alpha (from pyproject.toml classifiers)
- **Language**: 100% Python (539,536 bytes)

---

## Key Features

### 1. **Fine-Grained Reactivity (Core Differentiator)**

State changes trigger updates **only to dependent components**, not the entire application. Implemented via:

- **DependencyTracker**: Maps which components depend on each state value
- **Dirty component identification**: When state X changes, only components subscribing to X re-render
- **Lambda-based reactive expressions**: `app.write(lambda: f"Count: {count.value}")` creates computed dependencies automatically

Example:
```python
count = app.state(0)
app.button("Click", on_click=lambda: count.set(count.value + 1))
app.write(count)  # Auto-updates when count changes — no rerun
```

### 2. **Hybrid Execution Modes**

- **WebSocket Mode (Default)**: "Ultra-low latency bidirectional communication" for real-time, interactive applications. Uses `WsEngine` with persistent connections.
- **Lite Mode**: "HTTP-based, advantageous for handling large-scale concurrent connections" — stateless HTMX-based fallback for high-concurrency deployments

### 3. **Desktop Native App Support**

"Can run as a perfect desktop application without Electron using the `--native` option" via `pywebview`, enabling distribution as standalone executables on Windows, macOS, and Linux.

### 4. **Theme System**

20+ built-in professional themes: `dark`, `light`, `ocean`, `cyberpunk`, `terminal`, `dracula`, `monokai`, `pastel`, `nord`, `forest`, `sunset`, `vaporwave`, `blueprint`, `neo_brutalism`, `soft_neu`, `hand_drawn`, `bauhaus`, `editorial`, `glass`, `retro`, `ant`, `bootstrap`, `material`, `rgb_gamer`, and more.

Set at initialization: `app = vl.App(theme='cyberpunk')`
Change at runtime: `app.set_theme('ocean')`

Custom theme support planned.

### 5. **Streamlit-Compatible API Surface**

Widget names and signatures match Streamlit, lowering migration friction:
- Text & display: `app.title()`, `app.markdown()`, `app.code()`, `app.divider()`
- Input widgets (all return State objects): `app.text_input()`, `app.slider()`, `app.selectbox()`, `app.checkbox()`, `app.date_input()`, etc.
- Data widgets: `app.dataframe()` (AG-Grid, interactive), `app.table()` (static), `app.metric()`, `app.json()`
- Charts: `app.plotly_chart()`, `app.line_chart()`, `app.bar_chart()`, `app.scatter_chart()`
- Layout: `app.columns()`, `app.container()`, `app.tabs()`, `app.expander()`, `app.sidebar`
- Feedback: `app.toast()`, `app.success()`, `app.error()`, `app.spinner()`, `app.progress()`, `app.balloons()`

### 6. **State-Based Component Dependencies**

Input widgets return **State objects** (not raw values), enabling reactive binding without explicit callback wiring:

```python
name = app.text_input("Name")          # name is State[str]
app.text("Hello, " + name)             # Reactive display (auto-updates)
app.text(lambda: f"Hello {name.value}")  # Computed state
```

Manual callbacks unnecessary for most use cases.

### 7. **Session Management with Automatic Cleanup**

- Static store (`STATIC_STORE = {}`) for components created during app initialization
- TTL-cached global store (`TTLCache(maxsize=1000, ttl=1800)`) for user sessions with automatic expiration after 1800 seconds of inactivity
- Per-session state isolation while sharing static component definitions

### 8. **Control Flow Simplification**

No `st.rerun()` or `st.stop()` equivalent needed:
- State changes trigger immediate partial updates
- Python control flow (`if`, `return`, loops) works as expected without triggering reruns

---

## Technical Architecture

### **Execution Model: Signal-Based Reactivity**

Violit implements a fine-grained reactive execution model inspired by Solid.js / SolidStart:

```
User interaction → State change → DependencyTracker.get_dirty_components()
  → Identify affected components → Broadcaster.push_eval() → WebSocket → Frontend update
```

**Key architectural components**:

1. **State Engine** (`src/violit/state.py`)
   - `State` objects wrap values and track reads during component rendering
   - `DependencyTracker` maintains bidirectional mapping: `{state_name → {component_ids}}`
   - Supports operator overloading: `count + 1` creates a `ComputedState`
   - API: `.value` (read), `.set()` (write), `()` (shorthand read)

2. **Context System** (`session_ctx`, `rendering_ctx`, `fragment_ctx`, `layout_ctx`, `action_ctx`)
   - Tracks current session during rendering
   - Enables scoped state isolation in multi-user scenarios
   - Powers sidebar, fragment, and action contexts

3. **Broadcaster** (`src/violit/broadcast.py`)
   - WebSocket-based real-time system pushing JavaScript evaluation to connected clients
   - Methods: `eval_all()`, `push_eval()`, `_broadcast_eval_async()`
   - Supports session exclusion for selective updates

4. **Engine Abstraction**
   - `WsEngine`: WebSocket-based with persistent bidirectional communication
   - `LiteEngine`: HTMX-based stateless HTTP alternative
   - Both implement same update protocol

5. **Theme System** (`src/violit/theme.py`)
   - Preset-based (20+ themes) with CSS injection
   - Runtime theme switching via `app.set_theme()`
   - Custom theme support planned

6. **Widget Mixins** (modular architecture)
   - `TextWidgetsMixin`, `InputWidgetsMixin`, `DataWidgetsMixin`, `ChartWidgetsMixin`
   - `MediaWidgetsMixin`, `LayoutWidgetsMixin`, `StatusWidgetsMixin`
   - `FormWidgetsMixin`, `ChatWidgetsMixin`, `CardWidgetsMixin`, `ListWidgetsMixin`
   - Each mixin encapsulates a widget category for maintainability

### **Tech Stack**

- **Backend**: FastAPI (async Python) + uvicorn
- **Frontend**: Web Components (Shoelace UI library), Plotly.js (charting), AG-Grid (interactive dataframes)
- **Protocol**: WebSocket (primary) + HTTP/HTMX (lite mode)
- **State Management**: Custom signal-based reactivity (not Redux/MobX)
- **Desktop Runtime**: pywebview (native OS integration without Electron)

### **Data Flow Example: Counter Button**

```python
count = app.state(0)  # Creates State object, auto-keyed by file:line

@app.button("Click", on_click=...)
# During render: DependencyTracker registers component UUID → 'count' dependency

# User clicks button
λ: count.set(count.value + 1)  # State change

# Broadcast flow:
# 1. DependencyTracker.get_dirty_components('count') → [component_uuid]
# 2. Broadcaster.push_eval(session_id, "update_component(uuid, new_state)")
# 3. WebSocket sends to frontend
# 4. Frontend executes: Shoelace element re-renders with new count value
# 5. Entire page does NOT re-execute — only the component updates
```

---

## Installation & Usage

### **Installation**

```bash
# Stable release
pip install violit

# Development version
pip install git+https://github.com/violit-dev/violit.git
```

**Requirements**: Python 3.10+ (verified for 3.10, 3.11, 3.12)

### **Hello, Violit!**

Create `hello.py`:

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
    app.button("➖ Minus", on_click=lambda: count.set(count.value - 1))

app.metric("Current Count", count)

app.run()
```

### **Running**

```bash
# Web mode (default, opens at http://localhost:8000)
python hello.py

# Desktop native app mode (pywebview window)
python hello.py --native

# Custom port
python hello.py --port 8020

# Hot reload on file changes
python hello.py --reload
```

### **App Initialization Options**

```python
app = vl.App(
    title="My App",           # Browser/window title
    theme="ocean",            # Preset theme name
    container_width="800px",  # Content max-width ("none" for full-width)
    mode="ws",                # "ws" (WebSocket, default) or "lite" (HTMX)
)
```

### **State Pattern**

All interaction happens through reactive state:

```python
# Create state
counter = app.state(0)
name = app.state("", key="user_name")  # Optional explicit key

# Read
counter.value    # → 0
counter()        # → 0 (shorthand)

# Write
counter.set(5)
counter.value = 5  # Also valid

# Reactive display (auto-updates)
app.text(counter)                       # State object directly
app.text(counter + 1)                   # Operator overloading
app.write(lambda: f"Count: {counter.value}")  # Lambda for complex formatting

# NOT reactive (value frozen at call time)
app.text(counter.value)        # ❌ Just passes int 0
app.text(f"Count: {counter.value}")  # ❌ Just passes string
```

---

## Comparison with Alternatives

| Framework | Architecture | Learning Curve | Performance | Desktop | Real-Time |
|-----------|---------|----------|---------|------------|------------|
| **Streamlit** | Full Rerun | Very Easy | Slow | ❌ | △ |
| **Dash** | Callback | Medium | Fast | ❌ | △ |
| **Panel** | Param | Hard | Fast | ❌ | ✅ |
| **Reflex** | React (Compile) | Hard | Fast | ❌ | ✅ |
| **NiceGUI** | Vue | Easy | Fast | ✅ | ✅ |
| **Violit** | **Signal** | **Very Easy** | **Fast** | **✅** | **✅** |

**vs Streamlit**: Violit's fine-grained updates eliminate the `@cache_data` / `@fragment` optimization burden while maintaining Streamlit's simple syntax.

**vs Dash**: Violit replaces callback routing with automatic state dependency tracking — no need to wire Input/Output/State triplets manually.

**vs NiceGUI**: Violit has more concise, Streamlit-like syntax; NiceGUI requires explicit binding expressions.

**vs Reflex**: Violit is pure Python with no compilation step; Reflex requires class-based state definitions and compilation to React.

---

## Limitations and Caveats

### **Documented Limitations**

1. **Widget Support Coverage**: Not all Streamlit widgets are implemented
   - ✅ Supported: text, markdown, button, input, slider, selectbox, dataframe, plotly_chart, etc.
   - ❌ Not Supported: `st.latex`, `st.camera_input`, `st.map` (recommend using Mapbox in Plotly instead), `st.popover`
   - See [Streamlit API Support Matrix](https://github.com/violit-dev/violit/blob/main/doc/Streamlit%20API%20Support%20Matrix.md) for detailed compatibility

2. **Pre-Alpha Status**: Development Status classifier is "Pre-Alpha" — API stability not guaranteed between minor versions. Expect breaking changes.

3. **Key Management**: Auto-keyed by file:line, but users can specify explicit `key=` parameter if needed.

### **Undocumented Limitations** (inferred from architecture)

1. **State Mutation Safety**: Directly mutating state values (`count.value = 5`) works but `count.set()` is the recommended pattern for consistency with reactive batching.

2. **Async Processing**: Roadmap indicates "async processing support" is pending, suggesting async/await is not fully supported in callbacks.

3. **Custom Components**: Custom component support is planned but not yet available; users are limited to built-in widget set.

4. **Stateful Backends**: DependencyTracker and session stores are in-process memory; scaling to multiple workers requires session affinity or external state store (roadmap item: Violit.Cloud).

---

## Relevance to Claude Code Development

### **AI Agent Integration Potential**

1. **Rapid Dashboard Generation**: Agents can programmatically generate Violit applications from structured specifications — the simple State-based API makes this more tractable than Dash or Reflex.

2. **Real-Time Monitoring UIs**: WebSocket-based architecture enables live streaming of agent execution progress, logs, and state changes to a browser or desktop window.

3. **Interactive Tool Chains**: Build agent orchestration dashboards where each agent worker reports status to a Violit UI with automatic partial updates (no full reruns).

4. **LLM Output Visualization**: Stream token-by-token generation results to Violit charts/dataframes with zero redraw cost per update.

### **Extension Points for Agent Tooling**

- **Custom Widget Mixins**: Develop agent-specific widgets (e.g., `AgentStatusWidget`, `PromptEditorWidget`) by extending widget mixins
- **Theme System**: Create branded themes for internal tooling
- **Multi-Page Navigation**: `app.navigation()` enables multi-workspace agent UIs
- **Sidebar Context**: Agent navigation and settings live naturally in sidebars

### **Comparison to Alternatives for Agent Dashboards**

| Aspect | Streamlit | Dash | Violit |
|--------|-----------|------|--------|
| **Agent Progress Streaming** | Full reruns block updates | Callback complexity | Fine-grained, no overhead |
| **Code Generation** | Procedural scripts are natural | Callback routing is complex | Pure Python state-driven is simpler |
| **Deployment** | Web only | Web only | Web + Desktop with `--native` |
| **Agent Team Monitoring** | N/A | N/A | Session isolation via context, multi-user ready |

---

## Freshness Tracking

**Last Reviewed**: 2026-04-10

**Next Review**: 2026-07-10 (3 months)

### **Confidence Assessment by Section**

| Section | Confidence | Evidence |
|---------|-----------|----------|
| Overview | high | README.md, official documentation, consistent across sources |
| Problem Addressed | high | Detailed architectural comparison table in README, LLM reference docs |
| Key Statistics | high | GitHub API (current as of 2026-04-10), pyproject.toml (version 0.5.2) |
| Key Features | high | Official documentation (README + LLM_REFERENCE.md), code inspection of architecture |
| Technical Architecture | high | Source code review (state.py, broadcast.py, app.py), internal documentation |
| Installation & Usage | high | Official quick start, verified examples from LLM_REFERENCE.md and README |
| Comparison | high | Official comparison table in README (Streamlit, Dash, Panel, Reflex, NiceGUI) |
| Limitations | medium | API Support Matrix documented explicitly; remaining limitations inferred from roadmap |
| Relevance to Claude Code | medium | Inferred from architecture; no direct integration examples found |

**Data Freshness Issues**:
- Benchmark placeholder in README ("Detailed benchmark data will be updated soon") — benchmarks not available for verification
- Theme gallery placeholder ("PLACEHOLDER_FOR_THEME_GALLERY_GRID") — cannot verify theme appearance
- Development velocity: Active (last push 2026-04-09), but only 368 stars and 11 forks suggests limited adoption
- Community: No discussion of community size, active contributors, or issue response time

**Confidence Reduction Factors**:
- Pre-Alpha status means API may change
- Limited adoption (368 stars) makes long-term viability uncertain
- Custom component and async support are planned, not available — roadmap items are incomplete

---

## References

**Official Sources**:
- GitHub Repository: <https://github.com/violit-dev/violit> (accessed 2026-04-10)
- README.md: <https://github.com/violit-dev/violit/blob/main/README.md> (accessed 2026-04-10)
- LLM Reference Documentation: <https://github.com/violit-dev/violit/blob/main/doc/LLM_REFERENCE.md> (accessed 2026-04-10)
- Streamlit API Support Matrix: <https://github.com/violit-dev/violit/blob/main/doc/Streamlit%20API%20Support%20Matrix.md> (accessed 2026-04-10)
- PyPI Package: <https://pypi.org/project/violit/> (verified version 0.5.2)
- GitHub Releases: <https://github.com/violit-dev/violit/releases> (accessed 2026-04-10)

**Code Sources**:
- `src/violit/state.py` — State engine, DependencyTracker, session management (accessed 2026-04-10)
- `src/violit/app.py` — App class, FastAPI integration, widget mixins (accessed 2026-04-10)
- `src/violit/broadcast.py` — WebSocket broadcaster implementation (accessed 2026-04-10)
- `pyproject.toml` — Package metadata, dependencies, version (accessed 2026-04-10)

---

## Summary

Violit is a promising next-generation Python web framework addressing Streamlit's full-rerun performance bottleneck through fine-grained reactive state management. It combines Streamlit's developer-friendly API with React-like performance characteristics, supports both web and desktop deployment, and includes a rich theme system. As of 2026-04-10, the project is actively maintained (v0.5.2, last update 2026-04-09) but remains in pre-alpha with limited adoption (368 GitHub stars). Its clean architecture and simple State-based API make it a strong candidate for agent dashboard generation and real-time monitoring tools, though lack of async processing and custom components in the current release limits some use cases. The roadmap indicates active development with plans for custom components, async support, and cloud deployment. Recommended for new projects prioritizing simplicity and fine-grained reactivity; adoption risk is moderate given pre-alpha status.
