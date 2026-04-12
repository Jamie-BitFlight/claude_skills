---
name: PyScript
category: developer-tools
version: 2026.3.1
release-date: 2026-03-02
repository: https://github.com/pyscript/pyscript
documentation: https://docs.pyscript.net/2026.3.1/
license: Apache-2.0
---

# PyScript 2026.3.1

## Overview

PyScript is an open source platform that brings Python to modern web browsers. It enables developers to write rich web applications entirely in Python without requiring backend servers or JavaScript knowledge. PyScript compiles Python interpreters to WebAssembly (WASM), allowing Python to run directly in browsers on desktop, mobile, tablet, and any browser-enabled device.

**Repository Statistics** (as of 2026-04-12):
- **Stars**: 18.7k
- **Forks**: 1.5k
- **License**: Apache-2.0
- **Primary Languages**: Python (59.7%), JavaScript (23.2%), HTML (16.0%)
- **Commits**: 1,326 on main branch
- **Total Releases**: 47

## Problem Addressed

PyScript democratizes web development by eliminating traditional barriers to entry. Developers no longer need to:
- Deploy and manage backend servers
- Manage databases and server infrastructure
- Learn JavaScript to build interactive web applications

As stated in the official documentation: PyScript enables developers to "write your application logic in Python, use Python libraries for data processing or visualisation, and deploy your work with just a URL." This makes web development accessible to "the 99% of the rest of the planet who use computers."

## Key Statistics

| Metric | Value |
|--------|-------|
| **Current Version** | 2026.3.1 |
| **Release Date** | March 2, 2026 |
| **GitHub Stars** | 18,700+ |
| **GitHub Forks** | 1,500+ |
| **Minimum Python Interpreter** | MicroPython (170 KB) |
| **Full Implementation** | Pyodide (CPython via WASM) |

## Key Features

### Python Interpreters

PyScript supports two distinct Python interpreters, each optimized for different use cases:

1. **Pyodide** - Full CPython compiled to WebAssembly
   - Access to entire Python standard library
   - Support for data science packages: NumPy, Pandas, Matplotlib, Scikit-learn
   - Ideal for data processing and visualization applications
   - Requires larger initial download (~50+ MB)

2. **MicroPython** - Lean, efficient implementation
   - Only 170 KB in size
   - Optimized for mobile devices and constrained environments
   - Includes essential Python standard library subset
   - Ideal for fast startup times and mobile web applications

### Web Integration API

The `pyscript` namespace provides a Pythonic API for browser interaction:
- **DOM Manipulation**: Full access to Document Object Model through Python
- **Event Handling**: Decorator-based event binding
- **HTML Elements**: Support for 91 container elements (div, span, button, table, etc.) and 11 void/self-closing elements (img, input, br, hr, etc.)
- **CSS Integration**: Set-like interface for managing CSS classes, dict-like interface for inline styles

### Foreign Function Interface (FFI)

PyScript provides automatic translation between Python and JavaScript objects:
- Python code can call browser APIs directly
- Seamless object type conversion between languages
- Bi-directional communication through multiple mechanisms

### Advanced Capabilities

- **Web Workers**: Background Python execution prevents UI blocking during computationally intensive tasks
- **Device Access**: Camera, file storage, local data, and other device capabilities
- **Plugin System**: Extensible architecture allows third parties to create and contribute plugins
- **Pre-loaded Libraries**: AI/data science libraries available out-of-the-box
- **Async Support** (v2026.3.1): Complete asyncio.Future support with MicroPython

### Version 2026.3.1 Specific Features

- Latest MicroPython with weakref support
- Template strings support
- Complete asyncio.Future implementation
- 4 variants of WASM build:
  - Standard
  - Debugging
  - NumPy-like API
  - Comprehensive (all libraries)

## Technical Architecture

### Core Components

**JavaScript Foundation**: PyScript consists primarily of JavaScript code organized in the `pyscript.core` package, compiled to browser-ready modules stored in `dist/` directories.

**Underlying Technologies**:
1. **PolyScript** - A core layer (written in JavaScript) that bootstraps WASM-compiled interpreters in browsers. Provides clear separation of concerns: small, efficient, and powerful
2. **Coincident** - JavaScript library used to simplify worker-based tasks and background processing
3. **WebAssembly** - Both Python interpreters (MicroPython and Pyodide) are compiled to WASM using Emscripten, providing secure computing sandbox

### Python-JavaScript Interoperability

Three primary mechanisms enable Python-JavaScript integration:

1. **Shared Storage** - Key-value store accessible from both languages. "Data written from Python appears immediately in JavaScript, and vice versa."

2. **Donkey API** - Worker-based asynchronous Python execution from JavaScript
   - Methods: `process()`, `execute()`, `evaluate()`
   - Supports both 'py' (Pyodide) and 'mpy' (MicroPython) interpreters
   - Configurable worker threading and package dependencies

3. **Bridge API** - Import Python module functions directly into JavaScript as async functions that must be awaited

### Python Standard Library in PyScript

The `pyscript` namespace includes built-in Python modules:
- **pyscript.web** - Lightweight Pythonic interface to DOM and HTML elements
  - `page` object - document representation with query capabilities
  - `Element` classes - base class for all HTML elements
  - `ElementCollection` - batch operations on collections
  - `Classes` - set-like interface for CSS classes
  - `Style` - dict-like interface for inline styles
  - Special methods: `canvas.draw()`, `canvas.download()`, `video.snap()`

### Build and Development Infrastructure

- **Build Tool**: Makefile automating setup, formatting, building, and testing
- **Testing**: Three-tier approach using Playwright automation, uPyTest framework for browser-based testing
- **Code Quality**: ESLint for JavaScript validation, automated formatting tools
- **Language Support**: 59.7% Python, 23.2% JavaScript, 16.0% HTML codebase

## Installation & Usage

### Minimal Example

```html
<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width,initial-scale=1" />
        <title>PyScript!</title>
        <link
            rel="stylesheet"
            href="https://pyscript.net/releases/2026.3.1/core.css"
        />
        <script
            type="module"
            src="https://pyscript.net/releases/2026.3.1/core.js"
        ></script>
    </head>
    <body>
        <!-- type mpy (MicroPython) or py (Pyodide) to run some Python -->
        <script type="mpy" terminal>
            print("Hello, world!")
        </script>
    </body>
</html>
```

### Getting Started Resources

1. **Beginning PyScript Tutorial** - Recommended starting point for new developers
2. **User Guide** - Comprehensive documentation covering core concepts, DOM manipulation, filesystem access, JavaScript integration
3. **API Reference** - Detailed module documentation at `docs.pyscript.net`
4. **Example Applications** - Community examples available at `pyscript.com/@examples`

### Core Packages

- **@pyscript/core** (v0.7.18) - Main PyScript runtime
- **@pyscript/bridge** (v0.2.2) - JavaScript-based way to use PyScript modules
- Distributed via npm, unpkg, jsDelivr, and as direct script includes

## Relevance to Claude Code Development

### Potential Use Cases for Claude Code Users

1. **Browser-based Python Development Environments** - Creating web IDEs where users can write, test, and execute Python code directly in browsers without backend infrastructure
2. **AI/ML Demonstrations** - Building interactive web dashboards for machine learning visualizations using PyScript with NumPy, Pandas, and Matplotlib
3. **Data Processing Tools** - Serverless web applications for data analysis, transformation, and visualization
4. **Educational Content** - Interactive Python tutorials and coding exercises that run entirely client-side
5. **Prototyping** - Rapid prototyping of Python-based algorithms and data science workflows without deployment overhead

### Agent Integration Opportunities

- **Code Execution Agent** - An agent could leverage PyScript to execute Python code securely within browser environments
- **Documentation Interactive Examples** - Enhance technical documentation with executable PyScript examples
- **Skill Development** - Create Claude Code skills that leverage PyScript for specific Python-in-browser workflows

## Limitations and Caveats

1. **Initial Load Time** - Pyodide (full CPython) requires significant download (~50+ MB). MicroPython addresses this but with reduced library support.

2. **Browser Dependency** - Applications require a modern browser with WebAssembly support. Limited or no support for older browsers (Internet Explorer, etc.).

3. **Python Feature Subset** - MicroPython intentionally limits standard library to optimize for browser constraints. Full CPython compatibility not guaranteed.

4. **Performance Constraints** - WASM-compiled Python generally runs slower than native Python, though acceptable for most web applications. Not suitable for extreme computational workloads.

5. **Network and Security** - Client-side execution means no server-side computation. Applications are subject to browser security policies (CORS, content security policies, etc.).

6. **Third-party Package Limitations** - While Pyodide supports many PyPI packages, packages with C extensions or system dependencies may not work or may require compilation to WebAssembly.

7. **State Persistence** - State exists only within the browser session. Persistent storage requires integration with browser APIs (localStorage, IndexedDB) or external servers.

No limitations regarding PyScript's core Python execution model or syntax support have been documented in reviewed official sources.

## References

- [PyScript Official Homepage](https://pyscript.net/) (accessed 2026-04-12)
- [PyScript Documentation - What is PyScript?](https://docs.pyscript.net/2026.3.1/user-guide/what/) (accessed 2026-04-12)
- [PyScript User Guide](https://docs.pyscript.net/2026.3.1/user-guide/) (accessed 2026-04-12)
- [PyScript Web API Documentation](https://docs.pyscript.net/2026.3.1/api/web/) (accessed 2026-04-12)
- [PyScript Developer Guide](https://docs.pyscript.net/2026.3.1/developers/) (accessed 2026-04-12)
- [PyScript Python-JavaScript Interoperability](https://docs.pyscript.net/2026.3.1/user-guide/from_javascript/) (accessed 2026-04-12)
- [GitHub Repository](https://github.com/pyscript/pyscript) (accessed 2026-04-12)
- [PyScript Core README](https://github.com/pyscript/pyscript/blob/main/core/README.md) (accessed 2026-04-12)
- [Online IDE](https://pyscript.com/) (accessed 2026-04-12)
- [YouTube Channel - PyScript TV](https://www.youtube.com/@PyScriptTV) (accessed 2026-04-12)
- [Community Discord](https://discord.gg/BYB2kvyFwm) (accessed 2026-04-12)

## Freshness Tracking

| Section | Confidence | Last Verified | Next Review |
|---------|------------|---------------|-------------|
| **Metadata/Identity** | high | 2026-04-12 | 2026-07-12 |
| **Key Statistics** | high | 2026-04-12 | 2026-07-12 |
| **Features** | high | 2026-04-12 | 2026-07-12 |
| **Technical Architecture** | high | 2026-04-12 | 2026-07-12 |
| **Installation & Usage** | high | 2026-04-12 | 2026-07-12 |
| **Limitations** | medium | 2026-04-12 | 2026-07-12 |
| **Relevance to Claude Code** | medium | 2026-04-12 | 2026-07-12 |

**Confidence Notes**:
- High: Extracted directly from official PyScript 2026.3.1 documentation, GitHub repository, and published release notes
- Medium: Based on inferred patterns from documentation and general web platform constraints; not explicitly documented as limitations in reviewed sources

**Last Updated**: 2026-04-12
**Research Method**: Documentation extraction, repository README analysis, official API documentation review, GitHub metadata collection

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Capacitor](./capacitorjs.md) | developer-tools | cross-platform native bridge pattern: both WebView + native plugin architecture for web-to-mobile |
| [Gridland](./gridland.md) | developer-tools | write-once-run-anywhere rendering: canvas-based component compilation to browser and native terminal |
| [Google AI Studio](./google-ai-studio.md) | developer-tools | browser-based IDE for Python-like code execution and experimentation |
| [Claude Quickstarts](./claude-quickstarts.md) | developer-tools | reference examples for browser automation and Next.js UI integration patterns |
| [Vert](./vert.md) | developer-tools | client-side WebAssembly-based processing without backend requirements |
| [Vercel Chatbot](./vercel-chatbot.md) | developer-tools | production-ready Next.js template for deploying browser-based Python applications |
| [Pretext](./pretext.md) | developer-tools | DOM-free browser measurement library enabling text layout precision in canvas environments |
| [Repomix](./repomix.md) | developer-tools | AI-friendly packaging for codebase analysis, complementary to PyScript's data processing capabilities |
