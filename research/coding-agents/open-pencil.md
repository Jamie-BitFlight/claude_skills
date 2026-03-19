# Open Pencil

## Overview

**Open Pencil** is an open-source, AI-native design editor built as a Figma alternative. It natively reads and writes `.fig` files (Figma's binary format), includes built-in AI design capabilities with multi-provider LLM support, and is fully programmable via headless CLI, Figma Plugin API, and MCP (Model Context Protocol) server for AI agent integration. The application runs as a desktop app (Tauri v2 for macOS, Windows, Linux) and as a browser-based PWA. Current version is 0.10.0 (released 2026-03-15).

**Primary use case for Claude Code**: Teach AI coding agents to read, analyze, and modify design files programmatically. Agents can inspect design tokens, export assets as Tailwind CSS, analyze design systems for inconsistencies, and collaborate with human designers in real-time.

SOURCE: README.md (accessed 2026-03-19) — lines 1-5, 21-29
SOURCE: package.json (accessed 2026-03-19) — version field
SOURCE: GitHub API (accessed 2026-03-19) — created 2026-02-27, updated 2026-03-19

## Problem Addressed

Figma is a closed platform that actively restricts programmatic access to design files. Figma's proprietary binary `.fig` format can only be fully read by Figma's own software. Figma discontinued support for Chrome DevTools Protocol (CDP) in version 126, breaking automation workflows that relied on it. Design files cannot be modified programmatically without Figma's official (read-only) MCP server. Designers need to script design operations, audit design systems for inconsistencies, and enable AI agents to work with designs outside of Figma's ecosystem.

Open Pencil provides: (1) native `.fig` file format support with full read-write capability, (2) open-source codebase (MIT license) with no proprietary restrictions, (3) scriptable operations via CLI and programmatic APIs, (4) native AI integration via MCP for agents, (5) design data remains on the user's machine.

SOURCE: README.md (accessed 2026-03-19) — "Why" section, lines 199-203

## Key Statistics

- **GitHub Stars**: 2,752 (as of 2026-03-19)
- **GitHub Forks**: 242 (as of 2026-03-19)
- **Repository Created**: 2026-02-27
- **Latest Release**: v0.10.0 (2026-03-15)
- **License**: MIT
- **Primary Language**: TypeScript
- **Status**: Active development, not ready for production use

SOURCE: GitHub API (accessed 2026-03-19) — repo metadata endpoint
SOURCE: README.md (accessed 2026-03-19) — "Status: Active development" note

## Key Features

### 1. Figma File Interoperability

Reads and writes native `.fig` files without reverse-engineering. Full fidelity preservation for clipboards and nodes: `clipsContent`, `constraints`, `arcData`, `strokeCap/Join`, `layoutAlignSelf`, `textAutoResize`, `autoRename` all preserved through Figma Kiwi serialization. Variable-bound fill colors resolved through alias chains. Instance swap overrides propagated through clone chains.

**Mechanism**: Custom Kiwi binary codec with Zstd compression and ZIP packaging. Component overrides resolved transitively through component hierarchy.

SOURCE: CHANGELOG.md (accessed 2026-03-19) — v0.10.0 Improved .fig import fidelity section (lines 53-62), Fixes section (lines 81-82)

### 2. AI-Native Design Workflow

Built-in chat with 87+ design tools covering shape creation, fills/strokes, auto-layout, components, variables, boolean operations, and analysis. Multi-provider LLM support: Anthropic Claude, OpenAI, Google AI, OpenRouter, Z.ai (GLM-5, GLM-4.7, GLM-4.6, GLM-4.5), MiniMax (M2.5, M2.1, M2).

**Skeleton-first AI workflow**: 4-phase design process — plan → skeleton → content fill via `replace_id` → polish. Batched AI tools: `calc` accepts arrays of expressions, `stock_photo` fetches images in parallel (Pexels or Unsplash), `batch_update` applies multiple property changes in one call, `describe` accepts `ids` array for multi-node inspection.

**Mechanism**: 87 tools marshaled as ToolDef objects with full Figma Plugin API access. AI visual feedback: blue pulsing border on modified nodes, green flash on completion. Configurable max output tokens (default 16384).

SOURCE: README.md (accessed 2026-03-19) — "AI & MCP" section, lines 131-140
SOURCE: CHANGELOG.md (accessed 2026-03-19) — v0.10.0 Features section (lines 36-52)

### 3. Headless CLI for Design Inspection

`@open-pencil/cli` package exposes tree inspection, node queries via XPath, property inspection, and export without opening the editor.

**Example commands**:
- `open-pencil tree design.fig` — browse node tree with depth indentation
- `open-pencil query design.fig "//FRAME[@width < 300]"` — XPath selector for frames under 300px wide
- `open-pencil find design.fig --type TEXT` — search nodes by type
- `open-pencil node design.fig --id 1:23` — detailed property inspection for a single node
- `open-pencil analyze colors design.fig` — audit color palette usage with frequency counts and hex codes
- `open-pencil analyze typography design.fig` — font, size, weight statistics
- `open-pencil analyze clusters design.fig` — detect repeated patterns (component reuse candidates)

**Mechanism**: RPC commands dispatched to headless `@open-pencil/core` engine running in Bun. All commands support `--json` for machine-readable output.

SOURCE: README.md (accessed 2026-03-19) — CLI section (lines 31-108)
SOURCE: AGENTS.md (accessed 2026-03-19) — Commands section (lines 48-59)

### 4. Export Formats

PNG, JPG, WEBP, SVG rasterization. **Tailwind CSS + JSX export**: any design selection exports as HTML with Tailwind v4 utility classes. Grid layouts export with `grid`, `grid-cols-N`, `gap-x-*`/`gap-y-*`, child `col-start-*`/`row-start-*`/`col-span-*`/`row-span-*` utilities.

**Mechanism**: JSX-to-design renderer (`@open-pencil/core/render` subpath) uses Sucrase for fast JS execution. Tailwind export strips TypeScript casts (`as any`, `as const`) from AI-generated JSX.

SOURCE: README.md (accessed 2026-03-19) — lines 73-84
SOURCE: CHANGELOG.md (accessed 2026-03-19) — v0.9.0 Features (line 100)

### 5. Real-Time Collaboration

P2P collaboration via WebRTC, no server required, no account. Presence, cursors, follow mode. Powered by Trystero (WebRTC) + Yjs (CRDT).

**Mechanism**: Each peer connects directly; shared room ID in link (`app.openpencil.dev/share/<room-id>`). CRDT ensures eventual consistency without a central authority.

SOURCE: README.md (accessed 2026-03-19) — Collaboration section (lines 190-197)

### 6. Flex and CSS Grid Layout

Auto-layout with flex (`flex-direction: row | column`), gap, padding, alignment, track sizing. CSS Grid support via custom Yoga WASM fork with cherry-picked grid PRs. Grid child positioning via column/row span controls. Grid overlay on canvas during edit.

**Mechanism**: Yoga layout engine (WASM). Custom fork at `github.com/open-pencil/yoga` branch `grid` with grid layout support not yet upstreamed to official Yoga.

SOURCE: README.md (accessed 2026-03-19) — "Auto layout & CSS Grid" feature (line 27)
SOURCE: CHANGELOG.md (accessed 2026-03-19) — v0.9.0 Features (lines 98-100)

### 7. MCP Server for AI Agents

Stdio and HTTP MCP servers expose all 90 design tools (87 core + 3 file management). Agents connect via MCP clients: Claude Code, Cursor, Windsurf, or any MCP-compatible agent.

**Stdio setup** (Claude Code, Cursor, Windsurf):
```json
{
  "mcpServers": {
    "open-pencil": {
      "command": "openpencil-mcp"
    }
  }
}
```

**HTTP setup** (scripts, CI): `openpencil-mcp-http` listens at `http://localhost:3100/mcp`.

**Agent skill**: `npx skills add open-pencil/skills@open-pencil` — installs skill for Claude Code, Cursor, Windsurf, Codex, and compatible agents.

SOURCE: README.md (accessed 2026-03-19) — "MCP server" section (lines 154-188)

### 8. Plugin API via `eval`

Figma Plugin API accessible via headless CLI — modify live documents with JS:
```sh
open-pencil eval design.fig -c "figma.currentPage.children.length"
open-pencil eval design.fig -c "figma.currentPage.selection.forEach(n => n.opacity = 0.5)" -w
```

**Mechanism**: Full Figma Plugin API surface through sandboxed `eval`. `-w` flag writes changes back to file.

SOURCE: README.md (accessed 2026-03-19) — "Script with Figma Plugin API" section (lines 110-117)

## Technical Architecture

### Monorepo Structure

Bun workspace with four packages:

1. **`@open-pencil/core`** (v0.10.0)
   - Scene graph, renderer, layout engine, Kiwi codec, clipboard, vector operations, snapping, undo
   - Zero DOM dependencies — runs headless in Bun
   - Domain-specific subpath exports: `scene-graph`, `kiwi`, `tools`, `renderer`, `render`, `rpc`, `figma-api`, `canvaskit`, `layout`, `color`, `render-image`, `profiler`
   - Dependencies: CanvasKit WASM, Yoga WASM, Kiwi codec (fflate, fzstd), Sucrase JSX transpiler, SVG path utilities, nanoevents

2. **`@open-pencil/cli`** (v0.10.0)
   - Headless CLI for inspection, export, linting
   - Binary: `openpencil` command
   - Uses `citty` (command framework) + `agentfmt` (pretty-printing)
   - Depends on `@open-pencil/core` + CanvasKit

3. **`@open-pencil/mcp`** (v0.8.0)
   - MCP server for AI agent integration
   - Stdio + HTTP transports (Hono web framework)
   - Exposes all 90 design tools as MCP resources
   - Reuses `createServer()` factory from core

4. **`packages/docs`**
   - VitePress documentation site
   - Deployed to Cloudflare Pages at `openpencil.dev`

5. **`src/` (root app)**
   - Vue 3 desktop editor (Tauri v2)
   - Thin re-export shims from `@open-pencil/core` in `src/engine/`
   - Build targets: macOS (arm64 + x64), Windows (x64 + arm64), Linux (x64)
   - Web app (PWA) deployed to `app.openpencil.dev`

### Rendering Layer

**CanvasKit WASM** (Skia) for 2D rendering. All rendering operations go through Skia primitives: fill, stroke, gradient, radial/angular/diamond gradients, drop shadows, blur, clipping to rounded corners. Text rendering with paragraph shaper for multi-line CJK support. Fallback font chain for missing fonts.

**Performance optimization (v0.10.0)**:
- Offload .fig parsing (unzip + Kiwi decode) to Web Worker — main thread stays responsive
- Offload .fig compression during save to Web Worker (was blocking 450ms+)
- Add instance index (`componentId → Set<nodeId>`) — `getInstances()` O(1) instead of tree scan
- Defer graph event subscription until after layout — eliminates redundant `syncInstances` calls
- Cache label collection (sections/components) per scene mutation instead of walking full tree every frame
- Blocking font loading before first render ensures correct glyphs

SOURCE: AGENTS.md (accessed 2026-03-19) — Monorepo section (lines 9-16), Core subpath exports (lines 18-38)
SOURCE: CHANGELOG.md (accessed 2026-03-19) — v0.10.0 Performance section (lines 26-34)

### Data Flow: File Read

1. User opens `.fig` file in web app or desktop app
2. Tauri/Vite delegates to `@open-pencil/core` kiwi codec
3. Kiwi decoder unzips container, decompresses Zstd payload, deserializes Kiwi binary format
4. **Web Worker** offloads this blocking operation (new in v0.10.0)
5. SceneGraph constructed in memory with all nodes, props, variables, components
6. Renderer subscribes to graph mutations
7. SkiaRenderer renders tree to canvas on first paint

### Data Flow: File Write

1. User makes edits on canvas or via AI chat tools
2. Tools mutate SceneGraph nodes
3. Mutations trigger undo/redo stack push
4. File save initiated
5. **Web Worker** offloads Kiwi encoding + Zstd compression (new in v0.10.0, was 450ms+ blocking on main)
6. Encoded payload written to disk (Tauri file plugin)

### AI Tools System

All 87+ AI tools defined as `ToolDef` objects with:
- Name, description, parameters (Zod schema)
- Execution function with access to SceneGraph
- Return value schema

Tool categories:
- **Creation**: `create_frame`, `create_text`, `create_ellipse`, `create_polygon`, `create_star`, `create_line`, `create_path`
- **Modification**: `set_fill`, `set_stroke`, `set_layout`, `set_rotation`, `set_size`, `set_position`, `set_properties`
- **Layout**: `set_layout`, `set_constraints`, `set_resizing`
- **Components**: `create_component`, `create_instance`, `swap_instance`, `detach_instance`
- **Variables**: `create_variable`, `set_variable_binding`
- **Boolean**: `boolean_union`, `boolean_subtract`, `boolean_intersect`, `boolean_xor`
- **Analysis**: `describe`, `analyze`, `find_nodes`
- **Export**: `render` (render to image), `export_image_file` (MCP-specific), `stock_photo` (Pexels/Unsplash)

New in v0.10.0: Batched tools (`calc` arrays, `stock_photo` parallel, `batch_update`, `describe` with `ids`), skeleton-first workflow, auto-depth describe, gradient support.

SOURCE: README.md (accessed 2026-03-19) — "Built-in chat" section (lines 133-135)
SOURCE: CHANGELOG.md (accessed 2026-03-19) — v0.10.0 Features (lines 36-52)

### Tech Stack Summary

| Layer | Technology |
|-------|------------|
| Rendering | Skia (CanvasKit WASM, v0.40.0) |
| Layout | Yoga WASM (custom grid fork, v3.3.0-grid.2) |
| UI Framework | Vue 3 + Reka UI (headless components) + Tailwind CSS 4 |
| File Format | Kiwi binary + Zstd compression + ZIP container |
| Collaboration | Trystero (WebRTC P2P) + Yjs (CRDT) |
| Desktop | Tauri v2 (Rust) |
| Web | Vite (build) + PWA (service workers, Workbox) |
| CLI | Bun runtime + Citty (command framework) |
| AI/MCP | Multi-provider LLM adapters (Anthropic, OpenAI, Google, OpenRouter, Z.ai, MiniMax) + MCP SDK + Hono (HTTP) |
| Code Quality | Oxlint (Rust linter), Oxfmt (Rust formatter), Playwright (E2E visual regression, 188 tests), Bun test (764 unit tests) |

SOURCE: README.md (accessed 2026-03-19) — "Tech stack" section (lines 249-259)
SOURCE: AGENTS.md (accessed 2026-03-19) — Tech stack table (lines 249-259)

### Extension Points

1. **Custom LLM providers**: Adapter interface in `@open-pencil/core/tools` for routing chat requests to custom endpoints
2. **Stock photo providers**: `stock_photo` tool provider adapter for custom image sources (beyond Pexels/Unsplash)
3. **Tool definitions**: New tools can be registered via `ALL_TOOLS` array in core
4. **Plugin API via eval**: Figma Plugin API surface available to JS scripts

SOURCE: README.md (accessed 2026-03-19) — "Built-in chat" note (lines 134-135)
SOURCE: CHANGELOG.md (accessed 2026-03-19) — v0.10.0 Features "Stock photo integration" (line 40)

## Installation & Usage

### Desktop App

**macOS (Homebrew)**:
```sh
brew install open-pencil/tap/open-pencil
```

**Manual download**: [releases page](https://github.com/open-pencil/open-pencil/releases/latest)

**Web app**: No installation required — use at `app.openpencil.dev`

### CLI

```sh
bun add -g @open-pencil/cli
```

**Tree inspection**:
```sh
open-pencil tree design.fig
```

**XPath query**:
```sh
open-pencil query design.fig "//FRAME[@width < 300]"
```

**Export**:
```sh
open-pencil export design.fig -f jsx --style tailwind
```

**Analysis**:
```sh
open-pencil analyze colors design.fig
open-pencil analyze typography design.fig
open-pencil analyze spacing design.fig
```

**Scripting with Plugin API**:
```sh
open-pencil eval design.fig -c "figma.currentPage.children.length"
open-pencil eval design.fig -c "figma.currentPage.selection.forEach(n => n.opacity = 0.5)" -w
```

### MCP Server (Claude Code Integration)

**Installation**:
```sh
bun add -g @open-pencil/mcp
```

**Configuration** (`~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "open-pencil": {
      "command": "openpencil-mcp"
    }
  }
}
```

**HTTP server** (for scripts/CI):
```sh
openpencil-mcp-http  # http://localhost:3100/mcp
```

### Desktop App — Agent Integration

1. Install ACP adapter: `npm i -g @zed-industries/claude-agent-acp`
2. Add MCP permission to `~/.claude/settings.json`:
   ```json
   {
     "permissions": {
       "allow": ["mcp__open-pencil"]
     }
   }
   ```
3. Open desktop app → Ctrl+J → select Claude Code from provider dropdown

SOURCE: README.md (accessed 2026-03-19) — Installation/CLI/AI & MCP sections (lines 11-188)

## Relevance to Claude Code Development

### Primary Use Cases

1. **Design System Auditing**: Agents can analyze entire design systems (colors, typography, spacing, components) for inconsistencies. `open-pencil analyze` tools extract structured data (color hex codes, font families, usage counts, repeated patterns) suitable for diff-based auditing.

2. **Design-to-Code Export**: Agents can read Figma designs, inspect component hierarchy, and export selections as Tailwind CSS JSX. Useful for design handoff workflows — designers create in Figma, agents generate HTML/React components.

3. **Design Modification via AI Chat**: Describe what you want ("Add a card component with a 4px border radius"), and the AI assistant creates shapes, sets fills/strokes, manages auto-layout, and renders the result. 87+ design tools available.

4. **Design Token Generation**: Agents can extract design tokens (colors, typography, spacing, shadows) from a Figma file and generate design system code (CSS variables, Tailwind config, design tokens JSON).

5. **Visual Regression Testing**: Export design at different states, compare pixel-perfect with baseline via image diffing. CI-friendly headless export via MCP.

6. **Collaboration Workflows**: Build multi-agent systems where one agent inspects design, another modifies based on feedback, third agent exports/validates. Real-time P2P collaboration via WebRTC means no server overhead.

7. **Figma File Manipulation without Figma**: Open Pencil's native `.fig` support means agents can read/write Figma files in CI pipelines, Cursor/Claude Code, or standalone scripts — no Figma desktop or account required.

### Integration Examples

**Design token extraction for AI agents**:
```sh
open-pencil analyze colors design.fig --json | jq '.[].hex' > palette.json
open-pencil analyze typography design.fig --json > typography.json
```

**Headless design-to-code pipeline**:
```sh
# Agent 1: Analyze design
open-pencil tree design.fig --json

# Agent 2: Export as code
open-pencil export design.fig --selection "Components" -f jsx --style tailwind

# Agent 3: Validate export
open-pencil eval design.fig -c "figma.currentPage.selection.length"
```

**MCP integration** (native in Claude Code):
- Agent runs `open-pencil` MCP tools to query, read, write `.fig` files
- Skill: `npx skills add open-pencil/skills@open-pencil` — installs OpenPencil skill for Claude Code agents

SOURCE: README.md (accessed 2026-03-19) — Why, What it does, CLI, AI & MCP sections; examples inferred from feature documentation
SOURCE: AGENTS.md (accessed 2026-03-19) — Commands section

## Limitations and Caveats

1. **Not production-ready**: README explicitly states "Status: Active development. Not ready for production use." (as of v0.10.0, 2026-03-15). Desktop builds for Windows code signing not yet complete (planned in roadmap).

2. **Incomplete feature coverage**: Roadmap items not yet shipped: prototyping (frame transitions, interaction triggers, overlay management, preview mode), shader effects (SkSL), raster tile caching, component library publishing, grid child positioning UI, skewing, OkHCL color support.

3. **Browser/Desktop parity**: Web app does not have full feature parity with desktop (no Tauri plugins for file system access, etc.). Feature tests include separate projects: `--project=openpencil` (web) vs. `--project=figma` (cross-compatibility).

4. **Figma compatibility edge cases**: Instance override resolution, symbol swapping, and constraint propagation through clone chains are being hardened — v0.10.0 fixed 11+ specific edge cases (DSD resolution, SCALE constraint propagation, self-referencing symbolOverrides). More edge cases likely exist in complex Figma files.

5. **Font loading constraints**: Fonts must load before first render to ensure correct glyphs. Variable fonts excluded from local font access (fallback to Google Fonts). CJK text requires paragraph shaper fallback, which may not match Figma's exact rendering. Missing fonts result in fallback chain application, potentially different visual result than Figma.

6. **Layout precision**: Yoga layout fork with custom grid implementation not yet fully upstreamed. Grid implementation may differ from CSS Grid spec in edge cases.

7. **No documented limitations for AI tool outputs**: AI tools (87+) can theoretically create invalid design states (e.g., nested components violating Figma's rules, circular variable bindings). No documented constraints or validation rules for tool outputs.

8. **File save blocking duration**: While v0.10.0 moved Kiwi encoding to Web Worker (was 450ms+ blocking), large files may still incur noticeable blocking on main thread during final write. Exact threshold not documented.

9. **Collaboration limitation**: P2P via WebRTC means no central authority for conflict resolution if severe divergence occurs during simultaneous editing. Yjs CRDT handles eventual consistency, but order-of-operations conflicts may result in unexpected state. No documented conflict resolution strategy.

SOURCE: README.md (accessed 2026-03-19) — "Status: Active development" note (line 5), Roadmap section (lines 205-215)
SOURCE: CHANGELOG.md (accessed 2026-03-19) — v0.10.0 Improved .fig import fidelity section (lines 53-62), Fixes section (lines 65-92)

## References

- **GitHub Repository**: <https://github.com/open-pencil/open-pencil> (accessed 2026-03-19)
- **README.md**: Installation, features, CLI, AI & MCP, collaboration, tech stack, roadmap (accessed 2026-03-19)
- **CHANGELOG.md**: v0.10.0 (2026-03-15) and v0.9.0 (2026-03-09) release notes, performance improvements, features, fixes (accessed 2026-03-19)
- **AGENTS.md**: Monorepo structure, commands, core subpath exports, releases, CI workflows (accessed 2026-03-19)
- **package.json** (root, core, cli, mcp): Version v0.10.0, dependencies, scripts, exports (accessed 2026-03-19)
- **GitHub API**: Repository metadata — stars (2,752), forks (242), license (MIT), language (TypeScript), created 2026-02-27, updated 2026-03-19 (accessed 2026-03-19)

## Freshness Tracking

**Last reviewed**: 2026-03-19
**Next review**: 2026-06-19 (3 months)

**Confidence by section**:
- **Overview**: high — official README, GitHub metadata, active repository
- **Problem Addressed**: high — explicit "Why" section in README, clear design rationale
- **Key Statistics**: high — GitHub API metadata current as of today
- **Key Features**: high — comprehensive feature documentation in README and CHANGELOG v0.10.0 (released 2026-03-15, 4 days old)
- **Technical Architecture**: high — AGENTS.md contributor reference, monorepo structure documented, tech stack table explicit
- **Installation & Usage**: high — official README installation steps, CLI examples with exact command syntax
- **Relevance to Claude Code**: medium — inferred from feature capabilities and MCP integration points; not explicitly documented in primary sources
- **Limitations and Caveats**: high — explicitly documented in README ("not ready for production"), CHANGELOG release notes, and roadmap
