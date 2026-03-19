# OpenPencil

**Repository**: <https://github.com/open-pencil/open-pencil>
**Homepage**: <https://openpencil.dev>
**License**: MIT (Copyright 2026 Danila Poyarkov)
**Version**: v0.10.0 (released 2026-03-15)
**Status**: Active development. Not ready for production use.
**Try Online**: <https://app.openpencil.dev/demo>

---

## Overview

OpenPencil is an open-source design editor that reads and writes native Figma files (.fig format) with built-in AI capabilities and full programmatic control. It positions itself as an alternative to Figma by offering native file format support, AI-assisted design creation, and transparent access to design automation without vendor lock-in.

The project created a shallow clone date of 2026-02-27 (repository creation) and is under active development with the latest release v0.10.0 published 2026-03-15.

**Key statistics**:
- **GitHub stars**: 2,752 (as of 2026-03-19)
- **Forks**: 242
- **Open issues**: 36
- **Repository size**: 9,898 KB
- **Language**: TypeScript (primary)
- **Available**: Web app (no install), macOS (Homebrew), desktop (Tauri for Windows/macOS/Linux), CLI

---

## Problem Addressed

OpenPencil addresses three critical friction points with Figma:

1. **Closed proprietary platform** — "Figma is a closed platform that actively fights programmatic access. Their MCP server is read-only. [figma-use](https://github.com/dannote/figma-use) added full read/write automation via CDP — then Figma 126 killed CDP."

2. **Vendor lock-in** — "Your design files are in a proprietary binary format that only their software can fully read. Your workflows break when they decide to ship a point release."

3. **Limited automation** — Figma's documented MCP server provides read-only access, preventing design system automation, CI integration, and AI-assisted design at scale.

OpenPencil's approach: "Open source (MIT), reads .fig files natively, every operation is scriptable, and your data never leaves your machine."

---

## Key Features

### 1. Native .fig File Support

- **Opens and edits Figma files** — full read/write access to `.fig` format without reverse-engineering or proprietary APIs
- **Copy/paste between apps** — nodes can be copied between Figma and OpenPencil, enabling hybrid workflows
- **Preserves Figma compatibility** — edits remain compatible with Figma Desktop

**Mechanism**: The core package (`@open-pencil/core`) provides the Figma API proxy (`figma-api.ts`, `figma-api-proxy.ts`) and binary codec (`kiwi-serialize.ts`). Files are encoded in Kiwi binary format + Zstd compression + ZIP container. This architecture allows direct file manipulation without Figma's APIs.

### 2. AI-Assisted Design

- **Built-in chat interface** — Press Cmd+J (macOS) / Ctrl+J to open AI assistant; describe what you want in natural language
- **87+ design tools** — Create shapes, set fills/strokes, manage auto-layout, work with components and variables, run boolean operations, analyze design tokens, export assets
- **Multi-provider LLM support** — Bring your own API key (Anthropic, OpenAI, Google AI, OpenRouter, or any compatible endpoint)
- **No backend required** — Runs entirely client-side; no account creation, no server storage

**Mechanism**: The `src/ai/tools.ts` module exports 87 tools as structured tool definitions for LLM consumption. The `src/ai/chat-debug.ts` and related composables (`use-chat.ts`) handle UI and state. The chat interface integrates `@ai-sdk/*` providers (Anthropic, OpenAI, Google, OpenRouter via `@openrouter/ai-sdk-provider`) and uses the Figma Plugin API to mutate the scene graph in real time.

### 3. Fully Programmable Ecosystem

**Headless CLI** — Query and modify .fig files without opening the editor:

```bash
open-pencil tree design.fig                    # Browse node hierarchy
open-pencil find design.fig --type TEXT        # Search by node type
open-pencil node design.fig --id 1:23          # Inspect single node
open-pencil query design.fig "//FRAME"         # XPath selectors
open-pencil export design.fig -f jsx --style tailwind  # Tailwind JSX export
open-pencil analyze colors design.fig          # Design token audit
open-pencil eval design.fig -c "figma.currentPage.name"  # Figma Plugin API scripts
```

All commands support `--json` for machine-readable output.

**MCP Server** — Connect Claude Code, Cursor, Windsurf, or any MCP client to read/write `.fig` files with 90 tools (87 core + 3 file management). Two deployment modes:

- **Stdio mode** (Claude Code, Cursor, Windsurf): Install `@open-pencil/mcp`, configure in settings JSON
- **HTTP mode** (scripts, CI): Run `openpencil-mcp-http` at <http://localhost:3100/mcp>

**Figma Plugin API via `eval`** — Full Figma Plugin API available in CLI and MCP; modify nodes and write changes back:

```bash
open-pencil eval design.fig -c "figma.currentPage.selection.forEach(n => n.opacity = 0.5)" -w
```

When the desktop app is running, omit the file argument to operate on the live canvas — useful for automation scripts and AI agents.

### 4. Real-Time Collaboration

- **P2P via WebRTC** — No server, no account required
- **Live cursor and presence** — See collaborators' cursors, selections, and edits in real time
- **Follow mode** — Click a peer's avatar to follow their viewport
- **CRDT-based sync** — Uses Yjs for conflict-free collaborative editing

**Mechanism**: Collaboration stack uses Trystero (WebRTC P2P) + Yjs (CRDT) + y-indexeddb (local state). Share a generated link (`app.openpencil.dev/share/<room-id>`) to invite collaborators.

### 5. Layout Engine

- **Flexbox layout** — Full flex support (flex direction, gap, padding, alignment)
- **CSS Grid layout** — Grid support with gap, padding, alignment, track sizing
- **Powered by Yoga WASM** — Uses a custom fork of Yoga that adds grid support (`@open-pencil/yoga-layout@3.3.0-grid.2`)

### 6. Export & Code Generation

- **Image export** — Render to PNG, JPG, WebP, SVG at custom scale and quality
- **Tailwind CSS JSX export** — Export selections as HTML with Tailwind v4 utility classes

Example output:
```html
<div className="flex flex-col gap-4 p-6 bg-white rounded-xl">
  <p className="text-2xl font-bold text-[#1D1B20]">Card Title</p>
  <p className="text-sm text-[#49454F]">Description text</p>
</div>
```

### 7. Design Token Analysis

Terminal-based audit of design systems:

```bash
open-pencil analyze colors design.fig     # Extract and count color palette
open-pencil analyze typography design.fig # Identify typography patterns
open-pencil analyze spacing design.fig    # Spacing consistency audit
open-pencil analyze clusters design.fig   # Component instance clustering
```

Output includes color frequency, component match scoring, and usage statistics.

### 8. Coding Agent Integration

- **Claude Code integration** — Install ACP adapter and MCP permissions to use Claude Code directly in the chat panel
- **Skill system** — `npx skills add open-pencil/skills@open-pencil` registers OpenPencil skills for Claude Code, Cursor, Windsurf, Codex, and other agent frameworks
- **90+ tools** — All design operations are available to AI agents through the MCP interface

---

## Technical Architecture

### Core Components

The architecture follows a modular monorepo structure with four primary packages:

#### 1. **@open-pencil/core** (v0.10.0)

Central engine providing scene graph, rendering, file codec, and design operations.

**Key modules**:

- **Scene Graph** (`scene-graph*.ts`) — Node tree structure with support for frames, groups, components, instances, text, shapes, vector networks. Types and operations defined in `scene-graph.ts`; instance operations in `scene-graph-instances.ts`; hit-testing in `scene-graph-hit-test.ts`

- **File Codec** (`kiwi-serialize.ts`, `fig-export.ts`) — Kiwi binary format serialization/deserialization. Handles .fig file encoding (Kiwi + Zstd + ZIP) and round-trip preservation

- **Rendering** (`renderer/`, `render/`, `canvaskit.ts`) — CanvasKit WASM (Skia) rendering backend for GPU-accelerated 2D graphics

- **Layout Engine** (`layout.ts`) — Yoga WASM wrapper for flex and grid layout computation with Figma-compatible sizing and alignment semantics

- **Color & Style** (`color.ts`, constants) — Color manipulation (Culori integration), fill/stroke/effect type definitions, gradient transforms

- **Figma API Proxy** (`figma-api.ts`, `figma-api-proxy.ts`) — Compatibility layer exposing Figma Plugin API semantics on native .fig data; enables scripts written for Figma to run on OpenPencil files

**Exports** (conditional):
- Default: Full scene graph and tools API
- `./scene-graph` — Scene node types and operations only
- `./kiwi` — File codec (read/write .fig)
- `./tools` — Design tool definitions for AI agents
- `./renderer` — Graphics rendering
- `./layout` — Layout engine
- `./figma-api` — Figma API compatibility layer
- `./canvaskit` — Low-level Skia bindings

**Dependencies**: CanvasKit WASM, Yoga WASM (custom grid fork), Culori (color), Kiwi binary, Zstd compression, Nanoevents, Sucrase (JS eval)

#### 2. **@open-pencil/cli** (v0.10.0)

Headless command-line interface for batch operations, file inspection, export, analysis, and scripting.

**Bin**: `openpencil` — Global CLI executable installed via `bun add -g @open-pencil/cli`

**Mechanism**: Routes commands to core API. Entry point at `packages/cli/src/index.ts`. Depends on `@open-pencil/core` and uses Citty for CLI argument parsing.

#### 3. **@open-pencil/mcp** (v0.8.0)

Model Context Protocol server exposing design tools to Claude Code, Cursor, and other MCP clients.

**Bin**: `openpencil-mcp` — Stdio mode; `openpencil-mcp-http` — HTTP mode

**Endpoints**: 90 tools (87 core design tools + 3 file management tools)

**Tech**: Uses MCP SDK, Hono (HTTP framework), Zod (validation), WebSocket support for long-lived connections

**Mechanism**: Wraps core API tools as MCP resources. Stdio mode reads MCP protocol from stdin; HTTP mode exposes JSON-RPC at `http://localhost:3100/mcp`

#### 4. **Desktop App (Tauri v2)**

Native application for macOS, Windows, Linux.

**Tech Stack**:
- **Frontend**: Vue 3, Reka UI, Tailwind CSS 4, Vite
- **Desktop runtime**: Tauri v2 (Rust)
- **File system**: Tauri plugin for file I/O
- **Shell integration**: Tauri plugin for subprocess control
- **Dialog support**: Tauri plugin for native file/save dialogs

**Size**: ~7 MB binary

**Features**:
- Native title bar and menu
- File open/save dialogs
- Tray integration (Tauri plugins)
- Direct subprocess communication with CLI via Tauri shell plugin

**Collaboration**: Uses Trystero (WebRTC) + Yjs (CRDT); peers connect directly without server relay.

### Data Flow

```
User Input (Canvas/Chat)
  ↓
Vue 3 components + Composables (use-canvas.ts, use-chat.ts, etc.)
  ↓
Editor store (stores/editor.ts) — Yjs CRDT state
  ↓
@open-pencil/core SceneGraph API (scene-graph.ts)
  ↓
Yoga layout engine (layout.ts) — computes bounds/layout
  ↓
CanvasKit renderer (renderer/) — GPU-accelerated draw
  ↓
Canvas / DOM

File I/O Flow:
  .fig file (Kiwi + Zstd + ZIP)
  ↓
  kiwi-serialize.ts (decode)
  ↓
  SceneGraph object
  ↓
  [Edit via scene graph API]
  ↓
  kiwi-serialize.ts (encode)
  ↓
  .fig file (written via Tauri fs plugin or Node fs via MCP)

AI Integration Flow:
  User chat message
  ↓
  AI provider (@ai-sdk/*) — Anthropic, OpenAI, Google, OpenRouter
  ↓
  LLM processes with 87 tool definitions (src/ai/tools.ts)
  ↓
  LLM selects tools and invokes them
  ↓
  Tool handler mutates SceneGraph via core API
  ↓
  Yjs CRDT broadcasts changes to live collaborators
  ↓
  Renderer recomputes and redraws canvas
```

### Extension Points

1. **Figma Plugin API** — All scripts using standard Figma Plugin API (figma.currentPage, figma.createShape, etc.) work via the compatibility layer. Scripts can be injected via `eval` command or integrated into the chat

2. **Tool definitions** — AI tools are defined declaratively in `src/ai/tools.ts` with descriptions, parameters, and handlers. New tools can be added to this registry

3. **MCP server** — Stdio and HTTP modes allow custom MCP clients to connect. All 90 tools are exposed as MCP resources with JSON-RPC

4. **Collaboration hooks** — Yjs CRDT is the source of truth; custom awareness providers or conflict resolution strategies can be implemented via y-protocols plugin architecture

5. **Rendering backend** — Current backend is CanvasKit (Skia WASM). The roadmap mentions "Experimental WebGPU/Graphite rendering backend" as a future extension point

---

## Installation & Usage

### Web (No Installation)

Visit **<https://app.openpencil.dev>** or use the demo at **<https://app.openpencil.dev/demo>**. Runs as a PWA; works offline.

### macOS (Homebrew)

```bash
brew install open-pencil/tap/open-pencil
```

### Download

Visit [releases page](https://github.com/open-pencil/open-pencil/releases/latest) for macOS, Windows, Linux binaries.

### CLI

```bash
bun add -g @open-pencil/cli
open-pencil --help
```

### MCP Server (Stdio)

```bash
bun add -g @open-pencil/mcp
```

Configure in `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "open-pencil": {
      "command": "openpencil-mcp"
    }
  }
}
```

Then use in Claude Code chat panel.

### MCP Server (HTTP)

```bash
openpencil-mcp-http
```

Listens at `http://localhost:3100/mcp`. Suitable for CI scripts and programmatic access.

### Skill (Claude Code, Cursor, Windsurf)

```bash
npx skills add open-pencil/skills@open-pencil
```

### Development Setup

```bash
bun install
bun run dev        # Dev server at localhost:1420
bun run tauri dev  # Desktop app (requires Rust)
```

### Quality Gates

| Command | Purpose |
|---------|---------|
| `bun run check` | Linting + type checking (oxlint) |
| `bun run test` | E2E visual regression tests (Playwright, 188 tests) |
| `bun run test:unit` | Unit tests (Bun test, 764 tests) |
| `bun run format` | Code formatting (oxfmt) |

---

## Limitations and Caveats

### Status: Pre-Production

From the README: "Status: Active development. Not ready for production use." Implies API stability and features are subject to change.

### Missing Features (Roadmap)

The project explicitly lists planned features not yet implemented:

- **Prototyping** — frame transitions, interaction triggers, overlay management, preview mode
- **Shader effects** — custom visual effects via SkSL shaders
- **Raster tile caching** — instant zoom/pan for complex documents
- **Component libraries** — publish, share, and consume design systems across files
- **CI tools** — design linting, code export, visual regression in pipelines
- **Grid UI** — grid column/row span controls, grid overlay on canvas
- **Skewing and OkHCL color support**
- **Windows code signing** — currently no Azure Authenticode
- **WebGPU/Graphite rendering** — experimental backend not yet available

### Collaboration Limitations

Collaboration via P2P WebRTC has the following constraints (not explicitly documented but inherent to WebRTC):

- Network traversal failures may prevent peer-to-peer connections in some corporate/firewall environments (TURN relay not mentioned as fallback)
- Real-time sync is dependent on local network latency and WebRTC connection quality

### Figma Compatibility Boundaries

While OpenPencil reads/writes .fig files natively and provides Figma Plugin API compatibility, some Figma-specific features may have limited or no support:

- **Figma variables** and **design tokens** are partially supported (types are defined in scene-graph.ts) but may lack feature parity with Figma's implementation
- **Prototyping and interactions** are on the roadmap but not yet implemented
- **Smart components and advanced constraints** — limited documentation of support level

### File Format Constraints

.fig files are Kiwi binary + Zstd compression + ZIP. Round-trip fidelity with Figma depends on:

- Codec completeness (kiwi-serialize.ts coverage of all node types)
- No loss of Figma-specific metadata during encode/decode
- Compatibility with Figma versions (no versioning strategy documented)

### AI Tool Reliability

The 87 AI tools are deterministic wrappers around core APIs, but:

- **LLM hallucination** — AI may invent tool calls or parameters not matching actual tool definitions (use "ground to core API" principle when building agents)
- **Tool parameter correctness** — LLM may construct invalid or incomplete tool invocations; robust error handling on the agent side is required

---

## Relevance to Claude Code Development

OpenPencil is directly relevant to Claude Code and broader agent development in several ways:

### 1. MCP Server Implementation Example

OpenPencil's MCP server (`@open-pencil/mcp`) is a production reference for building protocol-compliant MCP servers:

- Exposes 90 tools as structured resources (resource types, descriptions, parameters with schemas)
- Implements both stdio and HTTP transports for different execution contexts
- Uses Zod for runtime parameter validation
- Demonstrates how to wrap domain-specific APIs (design tools) for LLM consumption

**Use case**: Study OpenPencil's MCP implementation to understand best practices for server design, tool definition structure, and transport handling.

### 2. Structured Tool Definitions for AI

The `src/ai/tools.ts` module defines 87 tools as declarative specifications consumable by any LLM provider:

- Each tool has name, description, input schema, and handler function
- Tools are provider-agnostic (work with Anthropic, OpenAI, Google AI, OpenRouter)
- Input validation via Zod + Valibot

**Use case**: Reference OpenPencil's tool design patterns when building Claude Code skills or MCP servers. The modular tool registry approach is reusable.

### 3. Multi-Provider LLM Integration

OpenPencil integrates four LLM providers via AI SDK:

```json
{
  "@ai-sdk/anthropic": "^3.0.58",
  "@ai-sdk/google": "^3.0.43",
  "@ai-sdk/openai": "^3.0.37",
  "@openrouter/ai-sdk-provider": "^2.2.3"
}
```

Users bring their own API keys; no backend lock-in. The chat interface supports provider switching.

**Use case**: Model OpenPencil's provider abstraction when building multi-model support into Claude Code plugins or skills.

### 4. P2P Collaboration via WebRTC

OpenPencil's Trystero + Yjs stack is a reference for building real-time collaboration into agent-driven applications:

- Yjs provides CRDT-based conflict-free merging of concurrent edits
- Trystero abstracts WebRTC connection management
- Works without a central server

**Use case**: Adapt OpenPencil's collaboration architecture for multi-agent or agent-human co-editing scenarios.

### 5. Agent-Friendly File Format Access

The native .fig file codec and Figma Plugin API compatibility layer enable Claude Code agents to:

- Read and modify Figma files without vendor APIs
- Automate design system tasks (consistency audits, component extraction)
- Integrate design workflows into broader AI agent pipelines

**Use case**: Claude Code agents can use the OpenPencil CLI or MCP server to automate design operations as part of larger tasks (e.g., "generate UI mockups, export as Tailwind, and integrate into prototype").

### 6. Headless Automation

The CLI and MCP server both support headless operation — no desktop UI required. This enables:

- CI/CD integration (design linting, visual regression)
- Programmatic file batch processing
- Real-time design tool access in agent scripts

**Use case**: Claude Code agents can invoke `open-pencil` CLI commands or connect to the MCP server to operate on designs in automated workflows.

---

## References

- **GitHub Repository**: <https://github.com/open-pencil/open-pencil> (accessed 2026-03-19)
- **Homepage & Documentation**: <https://openpencil.dev> (accessed 2026-03-19)
- **Live Demo**: <https://app.openpencil.dev/demo> (accessed 2026-03-19)
- **Latest Release**: v0.10.0, published 2026-03-15 (<https://api.github.com/repos/open-pencil/open-pencil/releases/latest>)
- **MCP Reference**: <https://openpencil.dev/reference/mcp-tools> (mentioned in README, accessed 2026-03-19)
- **License**: MIT (Copyright 2026 Danila Poyarkov, verified from LICENSE file)
- **Package Metadata**:
  - `@open-pencil/core` v0.10.0 (packages/core/package.json)
  - `@open-pencil/cli` v0.10.0 (packages/cli/package.json)
  - `@open-pencil/mcp` v0.8.0 (packages/mcp/package.json)
  - App version 0.10.0 (root package.json)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Google Stitch](./google-stitch.md) | ai-design-tools | Complementary AI design tool: Stitch generates UI from text/images, OpenPencil edits and exports native .fig files |
| [UI UX Pro Max Skill](./ui-ux-pro-max-skill.md) | skill-generation-tools | Injects design system context into AI agents; pairs with OpenPencil's code export for consistent UI generation |
| [Browser MCP](../mcp-ecosystem/browsermcp-mcp.md) | mcp-ecosystem | Reference architecture for MCP server design: both expose domain tools (design vs browser automation) as structured resources |

---

## Freshness Tracking

**Last reviewed**: 2026-03-19
**Next review**: 2026-06-19 (3 months)

### Confidence Summary

| Section | Confidence | Notes |
|---------|------------|-------|
| **Identity & Metadata** | high | GitHub API + repo metadata verified; version from official release |
| **Problem Addressed** | high | Quoted directly from README.md problem statement |
| **Key Features** | high | All features extracted from README with exact command examples and mechanism details |
| **Technical Architecture** | high | Core package exports and modular structure verified from package.json files; module listing from filesystem; data flow inferred from dependency graph and source file organization |
| **Installation & Usage** | high | Installation commands and development setup copied verbatim from README; verified Bun and Tauri integration |
| **Limitations & Caveats** | medium | Pre-production status and roadmap items extracted from README; collaboration constraints and file format boundaries are inferred from architecture (not explicitly documented) |
| **Relevance to Claude Code** | high | MCP implementation and tool definitions are factual capabilities; integration pathways documented in README |
| **References** | high | All URLs verified as accessible; release metadata from GitHub API; license from LICENSE file |

**Data Sources**:
- README.md — primary source for features, installation, development, architecture overview
- GitHub API responses — repository metadata (stars, forks, open issues, language, license, latest release)
- package.json files (root, packages/core, packages/cli, packages/mcp) — version numbers, dependencies, workspace structure
- LICENSE file — license type and copyright holder
- Repository filesystem structure — module organization and file inventory
- .fig file codec architecture inferred from file naming conventions and documented tech stack (Kiwi + Zstd + ZIP)

**Confidence Factors**:
- Official documentation (README) is comprehensive and up-to-date (repository pushed 2026-03-17)
- Package metadata consistent across monorepo
- Repository is young (created 2026-02-27) with rapidly evolving feature set; some architectural details may be incomplete or subject to change
- Roadmap items explicitly state features "not ready for production" — pre-release stability expected
