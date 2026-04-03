---
title: "TUI Studio"
slug: tui-studio
category: developer-tools
status: current
confidence:
  identity: high
  features: high
  architecture: high
  usage_examples: high
  limitations: medium
freshness_date: 2026-03-29
next_review: 2026-06-29
---

## Overview

TUI Studio is a Figma-like visual editor for designing Terminal User Interface (TUI) applications. It provides drag-and-drop component placement, real-time ANSI preview, and multi-framework code generation to six different TUI frameworks (Ink, BubbleTea, Blessed, Textual, OpenTUI, Tview) in a single click.

**Source**: Official website meta description — "A Figma-like visual editor for TUI applications. Drag-and-drop components, edit properties in real-time, and export to 6 frameworks with one click." (<https://tui.studio>, accessed 2026-03-29)

---

## Problem Addressed

Building terminal user interfaces has traditionally required writing substantial boilerplate code with no visual design tooling. Before TUI Studio, developers could not visualize layouts before runtime, had no standard design tools for terminal UIs, and struggled to maintain consistency across multiple screens and projects.

**Source**: Project documentation — "Building TUIs requires writing lots of boilerplate code. Hard to visualize layouts before running. No standard design tools for terminal UIs. Difficult to maintain consistency across screens." (<https://github.com/jalonsogo/tui-studio/blob/main/docs/TUI_DESIGNER_OVERVIEW.md>, accessed 2026-03-29)

---

## Key Statistics

- **Status**: Alpha (<https://github.com/jalonsogo/tui-studio>, accessed 2026-03-29)
- **Current Version**: 0.3.6 (released 2026-02-22) per changelog (<https://github.com/jalonsogo/tui-studio/blob/main/CHANGELOG.md>, accessed 2026-03-29)
- **License**: MIT License, Copyright 2026 TUI Designer Contributors (LICENSE file in repository, accessed 2026-03-29)
- **Repository**: <https://github.com/jalonsogo/tui-studio>
- **Components Supported**: 20+ components including Screen, Box, Button, TextInput, Checkbox, Radio, Select, Toggle, Text, Spinner, ProgressBar, Table, List, Tree, Menu, Tabs, Breadcrumb, Modal, Spacer
- **Color Themes**: 8 (Dracula, Nord, Solarized Dark/Light, Monokai, Gruvbox, Tokyo Night, Nightfox, Sonokai)
- **Export Targets**: 6 frameworks (Ink, BubbleTea, Blessed, Textual, OpenTUI, Tview)

**Source**: README.md and website description (<https://github.com/jalonsogo/tui-studio/blob/main/README.md>; <https://tui.studio>, both accessed 2026-03-29)

---

## Key Features

### Visual Canvas with Live Preview
The editor provides "Drag-and-drop components onto a live canvas with real-time ANSI preview at configurable zoom levels." Users can visually place components and see actual terminal rendering in real-time as they design.

**Source**: Feature description from official website (<https://tui.studio>, accessed 2026-03-29)

### 20+ TUI Components
Includes "Screen, Box, Button, TextInput, Checkbox, Radio, Select, Toggle, Text, Spinner, ProgressBar, Table, List, Tree, Menu, Tabs, Breadcrumb, Modal, Spacer" — covering the full range of typical terminal UI patterns.

**Source**: README features list (<https://github.com/jalonsogo/tui-studio/blob/main/README.md>, accessed 2026-03-29)

### Layout Engine
"Absolute, Flexbox, and Grid layout modes with full property control — just like CSS in the browser." Each component supports standard CSS-like layout properties, enabling complex nested compositions.

**Source**: Official website and README (<https://tui.studio>, <https://github.com/jalonsogo/tui-studio/blob/main/README.md>, both accessed 2026-03-29)

### Color Themes
The editor ships with "Dracula, Nord, Solarized, Monokai, Gruvbox, Tokyo Night, Nightfox, Sonokai — updating the canvas live." Theme changes render immediately on the canvas, allowing designers to preview different visual styles without re-exporting.

**Source**: Website feature carousel and README (<https://tui.studio>, <https://github.com/jalonsogo/tui-studio/blob/main/README.md>, both accessed 2026-03-29)

### Multi-Framework Export
"Generate production-ready code for Ink, BubbleTea, Blessed, Textual, OpenTUI, and Tview." Each export target produces idiomatic code in its respective framework's language (TypeScript for Ink, Go for BubbleTea, Python for Textual, etc.).

**Source**: README and official website (<https://github.com/jalonsogo/tui-studio/blob/main/README.md>; <https://tui.studio>, both accessed 2026-03-29)

### Layers Panel (Figma-style)
"Hierarchical component tree with drag-to-reorder, visibility toggle, lock, and inline rename." The panel mirrors Figma's layer organization, allowing complex designs to be managed through a traditional design tool workflow.

**Source**: README features section (<https://github.com/jalonsogo/tui-studio/blob/main/README.md>, accessed 2026-03-29)

### Property Panel
"Edit layout, style, and component-specific props for the selected component." Properties update the canvas in real-time, removing the need for code-edit-preview cycles.

**Source**: README (<https://github.com/jalonsogo/tui-studio/blob/main/README.md>, accessed 2026-03-29)

### Undo/Redo and Command Palette
Full history for all tree mutations with Cmd/Ctrl+Z and Cmd/Ctrl+Shift+Z. The command palette (`Cmd/Ctrl+P`) provides quick access to component creation, theme switching, and dark/light mode toggle.

**Source**: README keyboard shortcuts and features section (<https://github.com/jalonsogo/tui-studio/blob/main/README.md>, accessed 2026-03-29)

### Gradient Backgrounds
"Add linear gradients to any element background with angle control and N color stops; rendered as discrete character-cell bands matching real ANSI terminal output." Gradients render as per-column true-color ANSI codes in exported output.

**Source**: Changelog entry v0.2.0 (<https://github.com/jalonsogo/tui-studio/blob/main/CHANGELOG.md>, accessed 2026-03-29)

### Save/Load Projects
Projects are saved as portable `.tui` JSON files with version, metadata (name, theme, save timestamp), and tree structure. Projects can be opened from anywhere and shared with team members.

**Source**: File format specification in README (<https://github.com/jalonsogo/tui-studio/blob/main/README.md>, accessed 2026-03-29)

---

## Technical Architecture

### Frontend Stack
TUI Studio is built with "React 19, TypeScript 5.8, Vite 7" for the editor UI, "Zustand 5" for state management, "Tailwind CSS" for editor styling, and "Lucide React" for icons.

**Source**: Tech stack section in README (<https://github.com/jalonsogo/tui-studio/blob/main/README.md>, accessed 2026-03-29)

### State Management (Zustand)
The application uses four Zustand stores:

1. **ComponentStore** — Tree manipulation and history (undo/redo) with methods: `setRoot`, `addComponent`, `removeComponent`, `updateComponent`, `moveComponent`, `duplicateComponent`, `groupComponents`, `ungroupComponents`. Stores component tree as hierarchical nodes with flat lookup via `Map<string, ComponentNode>`.

2. **CanvasStore** — Viewport state managing "Dimensions (in terminal columns/rows)", `zoom`, `panX`, `panY`, grid visibility, snap-to-grid toggle, and grid cell size.

3. **SelectionStore** — Multi-selection support for batch operations and single component selection tracking.

4. **ThemeStore** — Active theme, accent color presets, and editor dark/light mode preference persistence.

**Source**: Store definitions in src/stores/ directory (<https://github.com/jalonsogo/tui-studio/blob/main/src/stores/componentStore.ts>, canvasStore.ts, selectionStore.ts, themeStore.ts, accessed 2026-03-29)

### Component Tree Model
Components are hierarchical `ComponentNode` objects with:
- Unique `id` (generated via `generateComponentId()`)
- `type` (mapped to COMPONENT_LIBRARY constants)
- `layout` object (properties for Absolute/Flexbox/Grid modes)
- `style` object (colors, borders, text properties)
- `props` object (component-specific properties like Button label, Table rows, etc.)
- `children: ComponentNode[]` array for nesting

**Source**: Type definitions and App.tsx component tree operations (<https://github.com/jalonsogo/tui-studio/blob/main/src/App.tsx>, src/types/, accessed 2026-03-29)

### Core Systems
**Editor Layout** — Primary layout is: Toolbar (top), LeftSidebar (Layers panel + component library), Canvas (center), PropertyPanel (right), CommandPalette overlay.

**Canvas Rendering** — Live ANSI preview rendered at configurable zoom levels. Grid snapping and absolute/flexbox/grid layout calculations performed client-side.

**Code Export** — Framework-specific exporters transform the component tree into idiomatic code for each target language and framework. Export strategies documented in code example reference.

**Source**: App.tsx main component structure (<https://github.com/jalonsogo/tui-studio/blob/main/src/App.tsx>, accessed 2026-03-29); docs reference (<https://github.com/jalonsogo/tui-studio/blob/main/docs/TUI_DESIGNER_CODE_EXAMPLE.md>, accessed 2026-03-29)

---

## Installation & Usage

### Quick Start
```bash
git clone https://github.com/jalonsogo/tui-studio.git
cd tui-studio
npm install
npm run dev
```

Open `http://localhost:5173`.

**Source**: README Quick Start section (<https://github.com/jalonsogo/tui-studio/blob/main/README.md>, accessed 2026-03-29)

### Keyboard Shortcuts

| Action          | Shortcut                          |
| --------------- | --------------------------------- |
| Command Palette | `Cmd/Ctrl+P`                      |
| Save            | `Cmd/Ctrl+S`                      |
| Open            | `Cmd/Ctrl+O`                      |
| Export          | `Cmd/Ctrl+E`                      |
| Copy            | `Cmd/Ctrl+C`                      |
| Paste           | `Cmd/Ctrl+V`                      |
| Delete          | `Backspace` / `Delete`            |
| Undo            | `Cmd/Ctrl+Z`                      |
| Redo            | `Cmd/Ctrl+Shift+Z` / `Cmd/Ctrl+Y` |

**Component hotkeys** (when not typing): `b` (Button), `r` (Box), `k` (Checkbox), `a` (Radio), `s` (Select), `o` (Toggle), `n` (Spinner), `j` (Spacer), `t` (Tabs), `l` (List), `e` (Tree), `m` (Menu), `i` (TextInput), `p` (ProgressBar), `y` (Text).

**Source**: README Keyboard Shortcuts section (<https://github.com/jalonsogo/tui-studio/blob/main/README.md>, accessed 2026-03-29)

### File Format
Projects are saved as `.tui` files (JSON):
```json
{
  "version": "1",
  "meta": { "name": "My Screen", "theme": "dracula", "savedAt": "..." },
  "tree": { ... }
}
```

**Source**: README File Format section (<https://github.com/jalonsogo/tui-studio/blob/main/README.md>, accessed 2026-03-29)

### Development Commands
```bash
npm run dev      # Start dev server
npm run build    # TypeScript compile + production build
npm run lint     # ESLint
npm run preview  # Preview production build
```

**Source**: README Commands section (<https://github.com/jalonsogo/tui-studio/blob/main/README.md>, accessed 2026-03-29)

---

## Relevance to Claude Code Development

TUI Studio is relevant for developers building:

1. **Terminal-based applications** that require visual design workflows similar to web development. Claude Code users could use TUI Studio to prototype and export terminal UIs for integration into CLI applications.

2. **Multi-framework TUI exports** — The ability to export a single design to six different frameworks (TypeScript/React, Go, JavaScript, Python, and Go variants) aligns with polyglot development patterns in AI-assisted projects where different subsystems use different languages.

3. **Visual design workflows for terminal UIs** — Brings Figma-like design workflows to terminal development, reducing the gap between designer intent and developer implementation.

4. **Component-driven TUI architecture** — The component library and layers system enable team-based TUI development with reusable patterns, similar to design systems for web applications.

---

## Limitations and Caveats

No limitations are explicitly documented in official sources. However, given the alpha status ("Status: alpha" badge on repository), the following caveats should be noted:

- **Alpha stability**: The project carries an alpha status badge, indicating the API and features may change before 1.0 release.
- **Single-screen focus**: Documentation examples focus on single-screen designs; multi-page/multi-screen project workflows are not explicitly detailed in reviewed sources.
- **Desktop application availability**: The website mentions "native app" and macOS DMG installer in changelog (v0.3.4, "macOS DMG installer"), but web-based deployment options are not documented beyond the localhost dev server.
- **Terminal emulation limits**: ANSI preview is limited to client-side CSS-based simulation; actual terminal rendering behavior may vary across different terminal emulators.

**Source**: Project status badge and changelog (<https://github.com/jalonsogo/tui-studio>, <https://github.com/jalonsogo/tui-studio/blob/main/CHANGELOG.md>, accessed 2026-03-29)

---

## References

- Official website: <https://tui.studio> (accessed 2026-03-29)
- GitHub repository: <https://github.com/jalonsogo/tui-studio> (accessed 2026-03-29)
- README.md: <https://github.com/jalonsogo/tui-studio/blob/main/README.md> (accessed 2026-03-29)
- Changelog: <https://github.com/jalonsogo/tui-studio/blob/main/CHANGELOG.md> (accessed 2026-03-29)
- Documentation overview: <https://github.com/jalonsogo/tui-studio/blob/main/docs/TUI_DESIGNER_OVERVIEW.md> (accessed 2026-03-29)
- License: MIT License, Copyright 2026 TUI Designer Contributors (<https://github.com/jalonsogo/tui-studio/blob/main/LICENSE>, accessed 2026-03-29)

---

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Gridland](./gridland.md) | developer-tools | Shares React-based TUI framework approach with write-once, deploy-anywhere multi-environment rendering |
| [Sidecar](./sidecar.md) | developer-tools | Bubbletea TUI framework for real-time terminal interfaces; similar component-driven UI architecture for agent workflows |
| [Agent Deck](./agent-deck.md) | developer-tools | Terminal session manager with unified TUI design for AI coding agents; overlapping use case for terminal UI composition |
| [Lopaka](./lopaka.md) | developer-tools | Visual-to-code editor for embedded displays; shares design-then-export pattern and multi-framework code generation strategy |
| [Pixel Agents](./pixel-agents.md) | developer-tools | Visual rendering of terminal interfaces via React and Canvas; complements TUI Studio's visual design approach for agent development |

---

## Freshness Tracking

**Last reviewed**: 2026-03-29
**Next review**: 2026-06-29 (3 months)

**What was verified**:
- ✓ Project identity and core claim ("Figma-like visual editor for TUIs")
- ✓ Feature list and component count (20+)
- ✓ Framework export targets (6 frameworks)
- ✓ Technical stack (React 19, Zustand 5, Vite 7)
- ✓ Installation and usage documentation
- ✓ File format and project structure
- ✓ Current version (0.3.6, released 2026-02-22)

**Sources still accessible**: All primary sources accessible as of 2026-03-29.
