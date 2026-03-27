# Gridland

**Research Date**: 2026-03-24
**Source URL**: <https://gridland.io>
**GitHub Repository**: <https://github.com/thoughtfulllc/gridland>
**Version at Research**: 0.2.53 (@gridland/web)
**License**: Not declared in repository

---

## Overview

Gridland is a React-based framework for building terminal user interface (TUI) applications that run in both the terminal and browser environments using a single codebase. Built on the OpenTUI rendering engine, it enables developers to create modern, interactive CLI applications with React component patterns while maintaining the ability to deploy to web browsers and compile to standalone binaries without requiring Node, Bun, or npm on the end user's machine.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Building terminal UIs requires platform-specific rendering code (terminal vs browser) | React-based approach with OpenTUI abstraction layer allows write-once, deploy-anywhere for TUI applications |
| Terminal applications are isolated from web distribution channels | Browser-compatible rendering enables distribution via web browser while maintaining native terminal performance |
| CLI tool deployment requires users to install JavaScript runtimes (Node, Bun, npm) | Compile-to-binary support via Bun's native compilation produces standalone executables with zero runtime dependencies |
| Reusable terminal UI component ecosystems are fragmented | Shadcn registry integration provides copy-paste component ownership model for terminal UI |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Primary Package Version | 0.2.53 (@gridland/web) | 2026-03-24 |
| Repository Commit Count | 1 | 2026-03-24 |
| Last Commit | 2026-03-24 17:33:00 -0400 | 2026-03-24 |
| Total Packages | 11 | 2026-03-24 |
| Package Manager | Bun (workspace monorepo) | 2026-03-24 |

Note: This shallow clone contains only the latest commit. Full repository history and GitHub statistics were not accessible via standard API endpoints.

---

## Key Features

### Multi-Environment Rendering

- **React Component Model**: Full React 19.0.0 support with JSX for declaring terminal UI layouts and interactions (`Source: packages/web/package.json, packages/web/src/index.ts`)
- **Browser Canvas Rendering**: CanvasPainter class provides pixel-accurate rendering to HTML5 Canvas in browsers (`Source: packages/web/src/canvas-painter.ts`)
- **Terminal Rendering via OpenTUI**: Native terminal rendering through OpenTUI 0.1.86 (platform-specific distributions for Darwin x64, Darwin arm64, Linux x64, Linux arm64) (`Source: packages/bun/package.json`)
- **Headless Rendering**: HeadlessRenderer and createHeadlessRoot APIs enable testing and server-side rendering without display output (`Source: packages/web/src/index.ts — exports`)

### Component Library and Architecture

- **Renderable System**: Base abstraction layer (BaseRenderable) supporting composition of visual primitives (`Source: packages/core/src/Renderable.ts`)
- **Pre-built Components**: Text, Box, Select, TabSelect, Input, Textarea, Slider, ScrollBox, EditBuffer, Markdown, Code, ASCIIFont (`Source: packages/core/src/renderables/`)
- **Shadcn Registry Integration**: Copy-paste UI component distribution model (`Source: README.md — "bunx shadcn@latest add @gridland/chat"`)
- **React Reconciler Integration**: react-reconciler 0.33.0 for React component tree synchronization to custom renderers (`Source: packages/web/package.json, packages/bun/package.json`)

### Text and Buffer Management

- **TextBuffer Abstraction**: Unified text storage with styling information, line wrapping, and efficient chunk-based manipulation (`Source: packages/core/src/text-buffer.ts, packages/web/src/browser-text-buffer.ts`)
- **Styled Text Support**: StyledText composition supporting per-chunk color, background, and text attributes (`Source: packages/core/src/lib/styled-text`)
- **EditBuffer for Interactive Editing**: EditBuffer class with cursor management, insert/delete operations, and undo/redo support (`Source: packages/core/src/edit-buffer.ts`)
- **TextBufferView**: Viewport abstraction for handling visible line ranges and chunked rendering (`Source: packages/web/src/browser-text-buffer-view.ts`)

### Browser Integration and Utilities

- **Portable Hooks**: Hooks library (@gridland/utils) providing useKeyboard, useTerminalDimensions, and other cross-platform utilities (`Source: README.md, packages/utils/`)
- **SelectionManager**: Text selection and clipboard interaction (`Source: packages/web/src/selection-manager.ts`)
- **File Drop Handling**: Native drag-and-drop file support (`Source: packages/web/src/file-drop.ts`)
- **Vite and Next.js Plugins**: Framework integration via gridlandWebPlugin (Vite) and withGridland (Next.js) (`Source: packages/web/package.json — exports, README.md`)

### Deployment and Compilation

- **Standalone Binary Compilation**: `bun build --compile` produces zero-dependency executables (`Source: README.md — "Compile to Binary" section`)
- **Docker Sandbox Container Runner**: @gridland/container package for isolated app execution (`Source: README.md, packages/container/`)
- **Demo Runner**: @gridland/demo CLI tool with pre-built interactive examples (landing, gradient, chat) (`Source: README.md`)
- **Create Project Scaffolding**: create-gridland CLI for rapid project initialization (`Source: packages/create-gridland/`)

### Testing Infrastructure

- **Testing Utilities Package**: @gridland/testing for TUI component testing (`Source: packages/testing/`)
- **Playwright E2E Tests**: Full browser automation testing suite (`Source: .github/workflows/test.yml`)
- **Randomized Unit Test CI**: Bun test runner with randomization and rerun-each strategy for reliability (`Source: package.json — "test:ci" script`)

---

## Technical Architecture

### Component Hierarchy

Gridland uses a three-layer composition model:

1. **React Layer**: React 19.0.0 components declaring UI structure and state management
2. **Reconciler Layer**: react-reconciler 0.33.0 synchronizing React component trees to Gridland's custom renderer protocol
3. **Renderable Layer**: Platform-agnostic Renderable classes (Text, Box, Select, etc.) implementing OpenTUI abstractions

React components emit Renderables through the reconciler; the BrowserRenderer (browser) or OpenTUI runtime (terminal) consumes Renderables and produces visual output.

### Data Flow (Rendering Pipeline)

```
React Component JSX
    ↓
React Reconciler (react-reconciler 0.33.0)
    ↓
Renderable (BaseRenderable subclasses: Text, Box, Select, etc.)
    ↓
RenderContext (BrowserRenderContext or OpenTUI context)
    ↓
Buffer (BrowserBuffer with styled text chunks)
    ↓
Platform Renderer
  ├─ CanvasPainter (browser Canvas API)
  ├─ Terminal (OpenTUI native rendering)
  └─ HeadlessRenderer (text buffer output for testing)
```

Source: packages/web/src/render-pipeline.ts, packages/web/src/browser-renderer.ts — class hierarchy and render execution.

### Layout Engine

Gridland uses Yoga layout engine (yoga-layout 3.2.1) for flexbox-style layout of terminal components, enabling responsive grid and box layouts that adapt to terminal/canvas dimensions.

Source: packages/web/package.json, packages/bun/package.json — Yoga dependency; packages/core/src/index.ts — exported Yoga API.

### React Adapter Pattern

The TUI component is the primary React entry point, accepting a root Renderable and mounting it to either a BrowserRoot (canvas) or OpenTUI terminal context. Portable hooks (@gridland/utils) provide keyboard, resize, and clipboard events in a runtime-agnostic API.

Source: packages/web/src/TUI.tsx, packages/web/src/index.ts — TUI export and mount API.

### Package Structure

- **@gridland/core**: Renderable base classes and composition model (no runtime dependencies; browser-safe exports)
- **@gridland/web**: Browser runtime (Canvas painter, browser buffer, Vite/Next.js plugins)
- **@gridland/bun**: Bun CLI runtime (OpenTUI bindings, native terminal integration)
- **@gridland/utils**: Cross-platform hooks and utilities (useKeyboard, useTerminalDimensions)
- **@gridland/ui**: Pre-built components via shadcn registry
- **@gridland/testing**: Jest/Bun test utilities
- **@gridland/container**: Docker sandbox runner
- **@gridland/demo**: Example runner
- **create-gridland**: Project scaffolding CLI

---

## Installation & Usage

### Create a New Project

```bash
bunx create-gridland my-app
cd my-app
bun install
bun dev
```

Source: README.md — Quick Start section.

### Add to Vite Project

```bash
bun add @gridland/web

# vite.config.ts
import { gridlandWebPlugin } from "@gridland/web/vite-plugin"

export default defineConfig({
  plugins: [gridlandWebPlugin()],
})
```

Source: README.md — Add to Existing Project / Vite.

### Add to Next.js Project

```bash
bun add @gridland/web

# next.config.ts
import { withGridland } from "@gridland/web/next-plugin"

export default withGridland({})
```

Source: README.md — Add to Existing Project / Next.js.

### React Component Example

```tsx
import { TUI, Text, Box } from "@gridland/web"

export default function App() {
  return (
    <TUI>
      <Box padding={1} borderStyle="rounded">
        <Text content="Hello, Gridland!" />
      </Box>
    </TUI>
  )
}
```

### Run Demo

```bash
bunx @gridland/demo landing
bunx @gridland/demo gradient
bunx @gridland/demo chat
```

Source: README.md — Try the Demos.

### Compile to Standalone Binary

```bash
bun build --compile src/cli.tsx --outfile my-app
./my-app
```

No Node, Bun, or npm required for end users.

Source: README.md — Compile to Binary.

### Sandboxed Container Execution

```bash
bunx @gridland/container @gridland/demo -- landing
```

Runs any app in isolated Docker container.

Source: README.md — Sandboxed Execution.

---

## Relevance to Claude Code Development

### Applications

- **Terminal UI for Agent Interfaces**: Gridland's React model maps naturally to agent session management — rendering real-time status, progress bars, and interactive menus without platform-specific terminal code.
- **Browser-Based REPL and Playground**: Gridland's browser rendering enables web-based terminal emulation for cloud-hosted Claude Code sessions, skill demonstrations, or interactive documentation.
- **Distribution of CLI Tooling**: Gridland's compile-to-binary feature eliminates installation friction for Claude Code plugins and skills that expose CLI commands — users download a single executable rather than requiring Node/Python/npm setup.

### Patterns Worth Adopting

- **React Component Model for UI**: Gridland's approach of using React + reconciler for non-web rendering demonstrates that React is platform-agnostic when paired with custom reconcilers — applicable to any rendering target (audio, data visualization, real-time dashboards).
- **Portable Hooks Over Platform Abstractions**: @gridland/utils' hook-based API (useKeyboard, useTerminalDimensions) is more discoverable and composable than conditional platform detection — worth applying to any framework that targets multiple environments.
- **Copy-Paste Component Ownership via Shadcn**: Rather than a monolithic component library, shadcn's registry model lets users vendor components into their own source, enabling customization without forking. This pattern could apply to Claude Code skills — users adopt individual skills into their workspace rather than depending on the central registry.

### Integration Opportunities

- **Skill UI Framework**: Build a Gridland-based UI library for agent skills, enabling skills to render terminal or browser dashboards for progress, configuration, and real-time results without platform-specific code.
- **Interactive Documentation**: Embed Gridland apps in Claude Code documentation (both terminal and web) for runnable examples, interactive API explorers, and live demos.
- **Agent Session Rendering**: Use Gridland to render agent orchestration views (task DAG, status feeds, artifact previews) in both terminal and browser, with identical React code.

---

## Limitations and Caveats

- **License Not Declared**: Repository contains no LICENSE file and package.json files do not specify a license field. Legal status for commercial or derivative use is unclear. Source: Inspection of .worktrees/gridland/ and all package.json files.
- **Monorepo Only at Latest Commit**: Shallow clone (depth=1) contains only the latest commit (88dec72, 2026-03-24). Full git history, tag releases, and past versions are not available in this worktree. Install specific versions from npm for production use.
- **OpenTUI Native Dependency**: Terminal rendering depends on platform-specific OpenTUI binaries (0.1.86 for Darwin x64, Darwin arm64, Linux x64, Linux arm64). Windows support not evident in dependencies. Source: packages/bun/package.json — optionalDependencies.
- **No Offline Terminal Option for Browsers**: Browser rendering uses Canvas API only; no fallback to ASCII-based HTML rendering. Requires modern browser with Canvas support.
- **Compile-to-Binary Requires Bun**: The `bun build --compile` feature produces native executables but requires Bun itself to invoke (not a cross-compilation tool). Distribution for platforms Bun doesn't support may require additional build configuration. Source: README.md — Compile to Binary section.

---

## References

- [Gridland Website](https://gridland.io) (accessed 2026-03-24)
- [Gridland Documentation](https://gridland.io/docs) (accessed 2026-03-24)
- [Gridland GitHub Repository](https://github.com/thoughtfulllc/gridland) (accessed 2026-03-24)
- [OpenTUI Project](https://opentui.com) — rendering engine used by Gridland (referenced in README.md, accessed indirectly via source inspection)
- [React Official Documentation](https://react.dev) — Gridland uses React 19.0.0 (version confirmed in packages/*/package.json)
- [React Reconciler Documentation](https://github.com/facebook/react/tree/main/packages/react-reconciler) — Gridland integrates react-reconciler 0.33.0 for custom rendering
- [Yoga Layout](https://yogalayout.com) — layout engine used for flexbox composition (yoga-layout 3.2.1)
- [Bun Runtime](https://bun.sh) — Gridland development and binary compilation require Bun
- [Shadcn UI](https://ui.shadcn.com) — component distribution model referenced in README.md

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Pi Monorepo](../agent-frameworks/pi-mono.md) | agent-frameworks | Shares React + TUI rendering approach; Pi's TUI framework uses differential rendering similar to Gridland's render pipeline |
| [Pixel Agents](./pixel-agents.md) | developer-tools | Both use React + Canvas for visualization; similar animation and state-driven rendering patterns for interactive UI |
| [CopilotKit](../agent-frameworks/copilotkit.md) | agent-frameworks | React component model with bi-directional state binding; overlapping use case for agent-driven UI |
| [Yume](./yume.md) | developer-tools | Parallel multi-environment deployment strategy (native desktop + cloud); both address platform-agnostic UI distribution |
| [Anime.js](./animejs.md) | developer-tools | Animation engine patterns applicable to Gridland's interactive component system |
| [Piebald](./piebald.md) | developer-tools | Cross-platform desktop UI framework; shares Gridland's goal of unified rendering across environments |
| [Using tmux with Claude Code](./using-tmux-with-claude-code.md) | developer-tools | Terminal UI orchestration patterns applicable to Gridland's TUI rendering context |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-24 |
| Version at Verification | 0.2.53 (@gridland/web) |
| Next Review Recommended | 2026-06-24 |
| Confidence Map | `Identity: high` `Features: high (code-read)` `Architecture: high (code-read)` `Usage Examples: high` `Limitations: medium (license status inferred from absence)` |

---

**Confidence Notes**:

- Identity section: High confidence — version strings extracted from package.json, most recent commit date from git log.
- Features section: High confidence with code-read qualifier — component list extracted from directory structure, exports inferred from index.ts files, architecture patterns from source inspection.
- Architecture section: High confidence with code-read qualifier — data flow and component relationships inferred from react-reconciler integration, render-pipeline, and browser-renderer source files.
- Usage Examples: High confidence — installation and compilation commands extracted verbatim from README.md.
- Limitations: Medium confidence on license status — absence of LICENSE file and license field is observed fact, but does not confirm the absence of an external license declaration; legal status should be verified with repository maintainers.
