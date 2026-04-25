---
title: Raincast
description: AI-powered native desktop app generator that builds functional Tauri applications from natural language descriptions
author: tito
repository: https://github.com/tihiera/raincast
version: 0.1.0
published_date: 2026-04-02
license: MIT
keywords:
  - app-generation
  - ai-coding
  - tauri
  - desktop-apps
  - code-generation
  - agentic-ai
---

## Overview

Raincast is a desktop application that generates other desktop applications. Users describe their desired app in plain English, and Raincast produces a fully functional, shippable native application: a compiled binary with a real UI, backend commands, file system access, and system integration. It is not a mockup or prototype—the output is production-ready code for macOS, Windows, and Linux.

**Key claim from primary source**: "Describe what you want, and Raincast builds a fully functional native app: with a real UI, backend commands, file system access, and system integration. Not a mockup. Not a prototype. A compiled, shippable application." (README.md, accessed 2026-04-25)

The generator produces complete React + Tauri applications with live preview during development, allowing developers to see the app running with hot reload before final compilation to a standalone binary.

**Status**: Version 0.1.0, development version released 2026-04-02. MIT licensed.

---

## Problem Addressed

Raincast solves the gap between UI description and functional implementation. Traditional app development requires manual integration of:

1. Frontend code (React UI, layout, styling)
2. Backend commands (Rust, file I/O, shell execution, system monitoring)
3. Configuration (Tauri runtime config, window chrome, permissions)

The manual approach is time-consuming, error-prone, and requires expertise in multiple technologies (TypeScript, React, Rust, Tauri). Raincast collapses this pipeline into a single natural-language input.

**Extracted from source**: "You describe what you want in plain English, and Raincast builds a fully functional native app" (README.md). The generator handles "React frontend, Rust backend commands, and Tauri config" automatically (README.md).

---

## Key Statistics

| Metric | Value | Source |
|--------|-------|--------|
| **Repository** | <https://github.com/tihiera/raincast> | GitHub |
| **Version** | 0.1.0 | package.json, tauri.conf.json (accessed 2026-04-25) |
| **Release Date** | 2026-04-02 | Git commit timestamp (accessed 2026-04-25) |
| **License** | MIT | LICENSE file (accessed 2026-04-25) |
| **Primary Language** | TypeScript / React (frontend), Rust (backend) | src/*, src-tauri/src, package.json, Cargo.toml (accessed 2026-04-25) |
| **Framework** | Tauri v2, React 19, Vite | tauri.conf.json, package.json (accessed 2026-04-25) |
| **Runtime Requirements** | Node.js 18+, Rust stable | README.md installation section (accessed 2026-04-25) |
| **Layout Templates** | 9 templates | README.md: "dashboard, editor, chat, file manager, media player, data table, playground, utility, and generic" (accessed 2026-04-25) |

---

## Key Features

### 1. Multi-Template Layout System

Raincast provides **9 pre-built layout templates**, each tailored for a specific use case.

**Extracted from source**: "9 layout templates: dashboard, editor, chat, file manager, media player, data table, playground, utility, and generic" (README.md, accessed 2026-04-25).

Each template is implemented as a TypeScript module in `src/lib/generation/templates/`. The templates generate complete React components with:
- Layout scaffold (Flexbox/CSS Grid structure)
- Sample UI components (buttons, forms, lists)
- Tailwind CSS styling preconfigured
- Responsive design defaults

**Template coverage** (from template files):
- `chat.ts`: Conversational UI with message bubbles and input
- `dashboard.ts`: Multi-widget layout with cards and metrics display
- `dataTable.ts`: Tabular data presentation with sorting/filtering
- `editor.ts`: Code/text editor with syntax highlighting
- `fileManager.ts`: File browser with directory tree and preview
- `generic.ts`: Blank canvas for custom layouts
- `media.ts`: Media player controls and display
- `playground.ts`: Interactive code/sandbox environment
- `utility.ts`: Compact utility app with single focused purpose

**Mechanism**: Templates are functions that accept app metadata (name, description, Rust commands available) and emit React code. Each template includes default styling via `styles.ts` module which generates Tailwind CSS classes.

### 2. Rust Backend Code Generation

Raincast generates Tauri commands (backend functions) that run in the native Rust layer with full system access.

**Extracted mechanism from source**: The AI writes Tauri commands for "file I/O, shell execution, system monitoring, network calls" (README.md). Tauri commands are Rust functions decorated with `#[tauri::command]`, which expose them to the frontend via JSON-RPC bridge.

**Generated commands** are validated with `runValidation` tool (agentLoop.ts line 18), indicating static analysis checks on generated Rust code.

### 3. Live Preview with Dev-Mode Proxy Binary

The most sophisticated feature: **live preview without compiling the full Tauri binary during development**.

**Extracted from README.md** (How It Works section):
> "Generated apps call Rust backend commands via Tauri's `invoke()` bridge, but in dev mode the full Tauri binary isn't compiled yet. So Raincast builds a **proxy binary**: it parses the generated Rust source using AST extraction to find every `#[tauri::command]` function, then generates a standalone CLI binary that reads JSON from stdin, dispatches to the same functions, and writes JSON to stdout."

**Mechanism components** (from proxyExtract.ts):
1. **AST Extraction**: Regex pattern extracts `#[tauri::command]` function signatures from Rust source
2. **Proxy Generation**: Creates a standalone binary that:
   - Accepts JSON input via stdin
   - Routes JSON to the same Rust functions (using extracted function bodies)
   - Returns JSON output via stdout
3. **Frontend Routing**: During dev, `invoke()` calls route through the proxy instead of Tauri runtime
4. **Behavioral Fidelity**: File system access, shell commands, system info all work during development, not just after shipping

**Extracted from source**: "The frontend's `invoke()` calls get routed through this proxy instead of the real Tauri runtime. This means the preview behaves like the real app: file system access, shell commands, system info all work during development, not just after shipping." (README.md)

### 4. AI Provider Abstraction

Raincast supports multiple AI backends via a pluggable provider system.

**Supported providers** (from code):
- **Anthropic Claude**: Models `claude-sonnet-4-6` (pro, 65K tokens) and `claude-haiku-4-5-20251001` (fast, 16K tokens)
- **Google Gemini**: Models `gemini-3.1-pro` and `gemini-3-flash`

**Provider architecture** (from ai/ directory):
- `baseProvider.ts`: Abstract `ModelAdapter` interface with `generate()` and `generateStream()` methods
- `providers/anthropic.ts`, `providers/gemini.ts`: Concrete implementations
- `registry.ts`: Pluggable registration mechanism
- `settings.ts`: API key storage and retrieval

**Extracted from README.md**: "Raincast supports multiple AI backends: Anthropic Claude (Sonnet 4.6 pro, Haiku 4.5 fast), Google Gemini (3.1 Pro, 3 Flash). Bring your own API key. Set it in the app settings."

### 5. Agentic Multi-Turn Editing Loop

Code generation uses a tool-calling agent loop rather than single-shot LLM completion.

**Extracted from agentLoop.ts comments**:
> "Instead of reading ALL source files and making a single LLM call, the agent: 1. Reads a lightweight file manifest (plain-English summaries), 2. Decides which files to read/edit via tool calls, 3. Executes tools, feeds results back, 4. Loops until the AI says 'done'."

**Agent tools** (from agentLoop.ts):
- `read_file`: Read source file contents
- `edit_file`: Replace substring with new content
- `list_dir`: Enumerate directory structure
- `grep_files`: Search by pattern across files
- `write_file`: Create new file
- `delete_file`: Remove file
- `run_validation`: Lint/validate code
- `web_search`, `web_fetch`: Fetch external resources

**Mechanism**: The LLM receives a plain-English file manifest (summaries, not raw code) and makes tool decisions. After each tool result, it loops: decide → execute → feed back → loop, until it declares "done". This is cheaper (LLM reads only what it needs) and smarter (iterative refinement).

### 6. Native Window Chrome and System Integration

Raincast generates Tauri config with native visual effects:

**Extracted from tauri.conf.json**:
- `macOSPrivateApi: true` — enables macOS-specific APIs (vibrancy effects, native chrome)
- `transparent: true` — transparent window backgrounds
- `titleBarStyle: "Overlay"` — custom title bar positioning
- `trafficLightPosition: { x: 13, y: 25 }` — macOS traffic lights (close/minimize/zoom buttons)
- `windowEffects: { effects: ["sidebar"], state: "active" }` — window effects library

These settings produce "native window chrome, transparent backgrounds, macOS vibrancy, overlay title bars, custom window sizes" (README.md).

### 7. One-Click Binary Distribution

**From README.md**: "When you hit **Ship**, Raincast compiles the actual Tauri binary with all the real commands baked in. The proxy is only for dev."

Compilation targets all major platforms:
- macOS: `/Applications/Raincast.app`
- Windows: `Raincast_x.x.x_x64-setup.exe`
- Linux: `.deb` (Debian/Ubuntu) and `.AppImage`

Each platform gets a native installer and signed binary suitable for distribution.

---

## Technical Architecture

### Layered Component Structure

**Diagram** (from source):

```
Frontend (React + TypeScript)
    ↓
Tauri IPC Bridge (invoke/listen)
    ↓
Backend (Rust Tauri Commands)
    ├─ File System (dirs, file I/O)
    ├─ Process Execution (shell commands)
    ├─ System Monitoring (CPU, memory, uptime)
    ├─ HTTP Client (network calls)
    └─ Database (SQLite via rusqlite)
```

### Frontend Architecture (src/)

**Main App Component** (App.tsx):
- **Providers**: `ThemeProvider`, `ProjectProvider`, `GenerationProvider`, `PreviewProvider`, `SketchProvider`
- **Main layout**: Split workspace with left (PreviewPane) and right (ChatPane) panes
- **Error handling**: `ErrorBoundary` components prevent UI crashes from component exceptions
- **Offline detection**: Auto-displays offline indicator when network unavailable

**Key components**:
- `ThemeContext.tsx`: Dark/light mode state
- `components/chat/ChatPane.tsx`: User input + AI response display
- `components/preview/PreviewPane.tsx`: Live app preview render
- `components/TopTabsBar.tsx`: Project tabs + settings
- `components/SplitWorkspace.tsx`: Draggable split pane

**Generation Library** (src/lib/generation/):
- `GenerationContext.tsx`: Global state for active generation session
- `session.ts`: Generation session lifecycle (start, update, complete)
- `manifest.ts`: File manifest builder (plain-English file summaries for LLM)
- `sourceManifest.ts`: Parses generated source into structured manifest
- `scaffolds.ts`: Initial boilerplate for new projects
- `templates/`: 9 layout template generators
- `proxyExtract.ts`: Extracts Tauri commands and generates proxy binary source

**AI Integration** (src/lib/ai/):
- `agentLoop.ts`: Multi-turn tool-calling agent loop (415 lines, core orchestrator)
- `baseProvider.ts`: Abstract provider interface
- `providers/anthropic.ts`, `providers/gemini.ts`: Concrete LLM adapters
- `prompts.ts`: System prompts and design guidelines
- `settings.ts`: API key storage

### Backend Architecture (src-tauri/src/)

**Main Library** (lib.rs, ~830 lines):
- **Preview server**: Spawns dev-mode proxy binary, captures stdout/stderr to log buffers
- **Ship process**: Compiles Tauri binary for target platform, tracks PID for cancellation
- **Workspace management**: File staging, snapshots (checkpoints), atomic apply
- **File operations**: Read/write/delete, atomic transactions via SQLite
- **Database** (db.rs): SQLite tables for projects, sessions, snapshots

**Tauri Commands** (Rust functions with `#[tauri::command]` decorator):
- Project lifecycle (create, save, list, delete)
- File staging and checkpoints
- Preview server control (spawn, cancel, get logs)
- Ship compilation (build, cancel, track progress)

**Dependencies** (Cargo.toml):
- `tauri@2`: Desktop app runtime with IPC
- `rusqlite@0.32`: SQLite driver with bundled binary
- `serde/serde_json`: JSON serialization
- `uuid@1`: Unique IDs for sessions
- macOS-specific: `cocoa@0.26`, `objc@0.2` (private API access)

### Code Generation Pipeline

**User input** → **AI generation** → **File output** → **Live preview** → **Ship compilation**

1. **Prompt Analysis** (agentLoop.ts):
   - User describes app in natural language
   - Frontend builds a file manifest (plain-English summaries)
   - LLM receives manifest + system prompt

2. **Tool-Calling Loop**:
   - LLM decides which files to read/edit
   - Frontend executes tools (read_file, edit_file, write_file, etc.)
   - LLM receives tool results and decides next action
   - Loop continues until LLM says "done"

3. **Template Rendering**:
   - Layout template (e.g., `chat.ts`) renders React scaffold
   - Rust backend template generates boilerplate commands
   - Tauri config is populated with app metadata

4. **Proxy Binary Generation** (proxyExtract.ts):
   - AST extraction finds all `#[tauri::command]` functions in generated Rust
   - Standalone CLI binary created: reads JSON stdin → calls function → JSON stdout
   - Frontend routes `invoke()` calls through proxy during dev

5. **Live Preview**:
   - Preview pane renders the generated React app
   - User actions trigger proxy binary via subprocess
   - Real file I/O and system calls execute during development

6. **Ship Compilation**:
   - Tauri build process compiles full binary with all commands
   - Targets: macOS .app, Windows .exe, Linux .deb/.AppImage
   - Binary ready for distribution

### Data Flow

**Chat Input** → **LLM + Agent Loop** → **Generated Files** → **Workspace** → **Preview Proxy** → **Live App UI** → **User Sees Real App**

Each generated file is stored in `~/.app_data_dir/raincast-workspace/{project_id}/`. The workspace is transactional: files are staged, snapshots (checkpoints) are taken, and atomic apply ensures consistency.

---

## Installation & Usage

### Installation

#### macOS (automated)

```bash
curl -fsSL https://raw.githubusercontent.com/tihiera/raincast/main/scripts/install-macos.sh | bash
```

**Extracted from README.md**: "This checks for Rust and Node.js, installs them if missing, builds from source, and places the app in `/Applications`."

#### Windows

Download `Raincast_x.x.x_x64-setup.exe` from [Releases](https://github.com/tihiera/raincast/releases) and run it.

#### Linux (Debian/Ubuntu)

```bash
# Download the .deb from Releases, then:
sudo dpkg -i raincast_x.x.x_amd64.deb
sudo apt-get install -f
```

Or use AppImage:

```bash
# Download .AppImage from Releases
chmod +x raincast_x.x.x_amd64.AppImage
./raincast_x.x.x_amd64.AppImage
```

**Extracted from README.md**: "Download the `.AppImage` from Releases, make it executable, and run." (accessed 2026-04-25)

### Manual Build

```bash
git clone https://github.com/tihiera/raincast.git
cd raincast
npm install
npm run tauri dev     # development
npm run tauri build   # production binary
```

**Prerequisites** (from README.md):
- Node.js 18+
- Rust stable (via rustup)
- Xcode Command Line Tools (macOS): `xcode-select --install`
- Linux (Debian/Ubuntu): `libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf libgtk-3-dev libsoup-3.0-dev`

### Usage

1. **Launch Raincast** (or `npm run tauri dev` for development)
2. **Describe your app** in the right pane (chat input)
   - Example: "Build a VPN status utility that shows my current public IP, connection location on a minimal world map, and a one-click toggle to connect/disconnect."
3. **Watch live preview** in the left pane as the app is generated in real time
4. **Interact with the preview** — file I/O and system calls work during development via the proxy binary
5. **Ship the app** — click "Ship" to compile the final binary
6. **Distribute** the compiled binary (`.app`, `.exe`, `.deb`, `.AppImage`)

**Development commands** (from README.md):

```bash
npm run tauri dev      # frontend + Tauri backend
npm run dev            # frontend only (port 1420)
npm run tauri build    # production binary
cd packages/editkit && npm test  # editkit tests
```

---

## Relevance to Claude Code Development

### 1. Agentic Code Generation Pattern

Raincast demonstrates a sophisticated agent loop for code generation (src/lib/generation/agentLoop.ts). Rather than single-shot LLM completion, it implements:

- **Lightweight file manifests** (plain-English summaries, not raw code)
- **Tool-calling loops** (LLM decides which files to read/edit)
- **Iterative refinement** (LLM refines code based on tool results)
- **Graceful degradation** (LLM stops when code is valid)

**Applicability to Claude Code**: This pattern could be adapted for Claude Code's feature implementation workflow. Instead of reading entire codebases upfront, agents could:
1. Build a manifest of source files
2. Iteratively read and edit based on task decisions
3. Avoid context bloat from unnecessary file reads

### 2. Proxy Pattern for Dev/Prod Separation

The **proxy binary strategy** (proxyExtract.ts) separates development behavior from production:

- **Dev**: Lightweight CLI proxy reads JSON stdin, calls Rust functions, outputs JSON
- **Prod**: Full Tauri binary compiled with all functions

**Applicability**: Claude Code could use similar patterns for plugin/skill preview (dev mock) vs. production deployment.

### 3. Template-Driven Code Scaffolding

Nine layout templates (src/lib/generation/templates/) emit production-ready React code. Each template is a pure function: metadata → scaffold.

**Applicability**: Claude Code could extend skill creation with domain-specific templates (e.g., data-processing-skill, interactive-cli-skill, plugin-agent-skill).

### 4. Provider-Agnostic AI Integration

The provider abstraction (baseProvider.ts, registry.ts) decouples generation logic from LLM choice. Multiple providers (Anthropic, Gemini) can be swapped without changing the agent loop.

**Applicability**: Claude Code already does this with the plugin system, but Raincast's implementation is worth studying for elegant registration and fallback strategies.

### 5. Multimodal Input Handling

The anthropic.ts provider handles image inputs alongside text (building multimodal content blocks). Users can screenshot their app design and pass it to the LLM.

**Applicability**: Claude Code could extend this to allow users to provide images (mockups, screenshots, diagrams) as part of feature descriptions.

### 6. Error Boundaries and Graceful Degradation

ErrorBoundary components (components/ErrorBoundary.tsx) prevent UI crashes from component exceptions. Offline detection (App.tsx) disables AI features when network unavailable.

**Applicability**: Claude Code's skill/agent systems could implement similar boundaries to prevent cascading failures.

---

## Limitations and Caveats

### No Limitations Explicitly Documented

The reviewed primary sources (README.md, source code, configuration files) do not document explicit limitations, constraints, or caveats.

However, inferred limitations based on architecture:

1. **Version 0.1.0 — Early Stage**: This is a development release. Stability, performance, and feature completeness are not production-guaranteed. Code generation quality likely varies with complexity and LLM provider choice.

2. **API Key Dependency**: Raincast requires external LLM API keys (Anthropic or Gemini). The tool does not work offline for generation. Network availability is required.

3. **Proxy Binary Generation Limits**: The proxy extraction (proxyExtract.ts) uses regex-based AST parsing for Rust. This is not a full Rust parser and may fail on:
   - Complex nested macros beyond `#[tauri::command]`
   - Generic parameters with complex trait bounds
   - Procedural macros that generate commands dynamically

4. **Template Coverage**: 9 templates cover common use cases (chat, dashboard, editor, etc.), but highly specialized layouts (scientific visualization, 3D rendering, game engines) may require manual coding post-generation.

5. **Supported Platforms**: Tauri v2 is the constraint. Raincast supports macOS, Windows, and Linux but not web, mobile (iOS/Android), or other platforms Tauri doesn't support.

6. **AI Generation Quality**: The quality of generated code depends entirely on LLM capability and prompt precision. Sophisticated apps (complex state management, custom algorithms, performance-critical code) may require manual refinement post-generation.

7. **No Built-in Testing**: Generated code does not include automated tests. Users must add test coverage manually or via secondary prompts.

---

## References

- **GitHub Repository**: <https://github.com/tihiera/raincast> (accessed 2026-04-25)
- **README.md**: Full feature description, installation instructions, examples (accessed 2026-04-25)
- **package.json**: Frontend dependencies, version, scripts (accessed 2026-04-25)
- **Cargo.toml** (src-tauri/): Backend dependencies, Rust version (accessed 2026-04-25)
- **tauri.conf.json**: Window configuration, build settings, platform targets (accessed 2026-04-25)
- **src/lib/generation/agentLoop.ts**: Agent loop implementation, tool definitions (accessed 2026-04-25)
- **src/lib/generation/proxyExtract.ts**: Proxy binary generation mechanism (accessed 2026-04-25)
- **src/lib/ai/providers/anthropic.ts**: Claude integration, model selection (accessed 2026-04-25)
- **LICENSE**: MIT license (accessed 2026-04-25)

---

## Freshness Tracking

**Last reviewed**: 2026-04-25
**Next review**: 2026-07-25 (3 months)

### Confidence by Section

| Section | Confidence | Notes |
|---------|------------|-------|
| **Overview** | high | Extracted from README and verified with source code structure |
| **Problem Addressed** | high | Directly quoted from README.md |
| **Key Statistics** | high | From package.json, Cargo.toml, tauri.conf.json, git metadata |
| **Key Features** | high | Extracted and validated against source implementation; feature mechanism verified in code |
| **Technical Architecture** | medium | Inferred from source code structure; no official architecture document |
| **Installation & Usage** | high | Directly quoted from README.md; commands verified against scripts/ |
| **Relevance to Claude Code Development** | medium | Analyzed based on architectural patterns; no explicit documentation of Claude Code applicability |
| **Limitations and Caveats** | low | No limitations documented in primary sources; inferred from architecture and version stage |

**Confidence reasoning**:
- High: Sections based on official README.md or directly extractable from source code (package manifest, config files)
- Medium: Sections requiring architectural inference from code inspection
- Low: Sections based on absence (no documented limitations) or speculative inferences

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Cline](./cline.md) | coding-agents | tool-calling agentic loop for iterative code generation and tool-based refinement |
| [OpenHands](./openhands.md) | coding-agents | multi-provider agentic framework enabling model-agnostic code generation at scale |
| [Pilot](./pilot.md) | coding-agents | autonomous development pipeline integrating agentic code generation with CI/CD quality gates |
| [1Code](./1code.md) | coding-agents | multi-agent orchestration layer with visual diff preview and worktree isolation patterns |
| [Accomplish](./accomplish.md) | coding-agents | local-first agentic execution with permission-gated tool use and persistent task state |
| [Maverick](./maverick.md) | coding-agents | autonomous development with enforced quality gates and best-practice skills during code generation |
| [HyperAgents](./hyperagents.md) | coding-agents | self-improving agentic loop for multi-domain code synthesis and evolutionary optimization |
| [HumanCompiler](../skill-generation-tools/human-compiler.md) | skill-generation-tools | agent plugin generation from behavioral patterns; Raincast's template system shares prompt-to-code generation architecture |

---

**Entry created**: 2026-04-25
**Category**: coding-agents
**Status**: initial research complete
