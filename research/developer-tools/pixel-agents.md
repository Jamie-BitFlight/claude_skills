---
title: "Pixel Agents"
research_date: "2026-03-05"
source_url: "https://marketplace.visualstudio.com/items?itemName=pablodelucca.pixel-agents"
github_url: "https://github.com/pablodelucca/pixel-agents"
version_at_research: "v1.0.2"
license: "MIT"
last_verified: "2026-03-05"
version_at_verification: "v1.0.2"
next_review: "2026-06-05"
---

## Overview

Pixel Agents is a VS Code extension that renders each open Claude Code terminal as an animated pixel-art character in a virtual office environment. Characters visually reflect real-time agent activity — walking when idle, typing when writing code, reading when searching files, and displaying speech bubbles when waiting for user input. The extension operates purely observationally by parsing Claude Code's JSONL transcript files; no modifications to Claude Code itself are required.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| No visual feedback on what multiple concurrent Claude Code agents are doing | Characters animate in real time based on tool usage extracted from JSONL transcripts |
| Difficult to notice when an agent is blocked waiting for user permission or input | Speech bubble indicators appear on the character when the agent is waiting |
| No ambient awareness of agent activity when focused elsewhere in VS Code | Persistent webview panel shows all agents simultaneously, with sound notifications on turn completion |
| Sub-agent spawning from Agent tool is invisible to the user | Sub-agents spawn as separate linked characters in the office, showing parent-child relationships |
| Multi-root workspaces make it unclear which folder a new agent terminal will operate in | Workspace folder picker prompts the user when "+ Agent" is clicked in a multi-root workspace |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 3,029 | 2026-03-05 |
| Forks | 416 | 2026-03-05 |
| Open Issues | 49 | 2026-03-05 |
| Contributors | 2 (per release notes, repo was created 2026-02-08) | 2026-03-05 |
| Latest Release | v1.0.2 | 2026-02-27 |
| Primary Language | TypeScript (63% of codebase) | 2026-03-05 |

---

## Key Features

### Agent Visualization

- One animated pixel-art character per Claude Code terminal instance
- Characters use a state machine: idle → walk → type/read, driven by tool invocations in transcripts
- Sub-agents spawned via the Agent tool appear as linked child characters in the office
- 6 diverse character skins based on the JIK-A-4 Metro City free top-down character pack

### Activity Tracking

- Reads Claude Code JSONL transcript files via `fs.watch()` and `fs.watchFile()` (macOS fallback)
- Detects specific tool usage: file writes trigger typing animation, file reads trigger reading animation, bash commands trigger distinct states
- Heuristic-based idle/waiting detection using timers and turn-duration events (acknowledged limitation)
- Speech bubbles displayed when agent awaits user input or permission

### Office Environment

- Canvas-rendered 2D top-down office with BFS pathfinding for character movement
- Built-in layout editor with floor, wall (auto-tiling), and furniture placement tools
- Editor tools: select, paint, erase, place, eyedropper, pick
- 50-level undo/redo stack (Ctrl+Z / Ctrl+Y)
- Grid expandable up to 64×64 tiles
- Layouts persist across VS Code windows; export/import as JSON via Settings modal

### VS Code Integration

- Appears in the bottom panel area alongside the integrated terminal
- "+ Agent" button spawns a new Claude Code terminal and its associated character
- Workspace folder picker for multi-root workspace support
- Compatible with VS Code forks (Cursor, etc.) via lowered engine requirement (`^1.107.0`)
- Optional sound notification (chime) when an agent completes its turn

### Asset System

- Default characters and basic layout work out of the box
- Full furniture catalog requires purchasing the Office Interior Tileset (16x16) by Donarg ($2 USD on itch.io) and running `npm run import-tileset`
- Tileset import pipeline uses `@anthropic-ai/sdk` and `pngjs` for image processing

---

## Technical Architecture

The extension is structured as two separate build targets bundled together:

**Extension Host (TypeScript + esbuild)**

- `extension.ts` — activation entry point, registers commands and the webview panel
- `agentManager.ts` — tracks active Claude Code terminals, maps PIDs/sessions to characters
- `fileWatcher.ts` — monitors JSONL transcript directories using `fs.watch` with `fs.watchFile` as secondary watcher on macOS; handles path sanitization for Unicode, CJK, spaces, and special characters
- `transcriptParser.ts` — parses Claude Code JSONL format to extract tool invocations and infer agent state
- `timerManager.ts` — manages heuristic idle timers for detecting agent waiting/completion states
- `layoutPersistence.ts` — reads/writes office layout JSON to VS Code workspace storage
- `PixelAgentsViewProvider.ts` — VS Code WebviewViewProvider that hosts the canvas UI
- `assetLoader.ts` — loads sprite sheets and tileset assets for the webview

**Webview UI (React 19 + Vite + Canvas 2D)**

- Canvas 2D rendering with a lightweight game loop
- BFS pathfinding for character movement across the office grid
- Character state machine drives animation frame selection
- React components for editor UI, speech bubbles, and settings modal

**Data flow**: JSONL transcript files → fileWatcher → transcriptParser → agentManager → message posted to webview → canvas state updated → animation rendered.

---

## Installation & Usage

```bash
# Install from VS Code Marketplace (recommended)
# Search "Pixel Agents" in VS Code Extensions panel
# or use the marketplace URL:
# https://marketplace.visualstudio.com/items?itemName=pablodelucca.pixel-agents

# Build from source
git clone https://github.com/pablodelucca/pixel-agents.git
cd pixel-agents
npm install
cd webview-ui && npm install && cd ..
npm run build
# Press F5 in VS Code to launch Extension Development Host

# Import full furniture tileset (requires purchased tileset from itch.io)
npm run import-tileset
```

```text
Usage workflow:
1. Open the Pixel Agents panel (bottom panel area, alongside terminal)
2. Click "+ Agent" to spawn a new Claude Code terminal + character
3. Start a Claude Code session — the character animates based on agent activity
4. Click a character to select it, then click a seat to reassign its desk
5. Click "Layout" to open the office editor and customize the office space
```

---

## Relevance to Claude Code Development

### Applications

- Directly targets Claude Code users as its primary audience — the extension is purpose-built for visualizing Claude Code agent activity
- Demonstrates a pattern for observing Claude Code state without any API or plugin hook: pure JSONL transcript parsing is sufficient to infer what the agent is doing at each moment
- Shows that sub-agent hierarchies (Agent tool spawns) are externally observable and can be visualized

### Patterns Worth Adopting

- **JSONL transcript as an external event bus**: The transcript file format is stable enough to build reliable observability tools against. This pattern could be applied to other Claude Code monitoring or debugging tools.
- **State machine for agent activity**: The idle → walk → type/read state machine with heuristic timers is a reusable model for representing agent lifecycle in any UI or logging layer.
- **Dual file watching (watch + watchFile fallback)**: The macOS-specific reliability fix using `fs.watchFile` as a secondary watcher is a portable pattern for cross-platform file monitoring in Node.js extensions.
- **Separate build targets**: Splitting the extension host and webview into independent build pipelines (esbuild for the host, Vite for the webview) is a clean architecture for VS Code extensions with rich UIs.

### Integration Opportunities

- A Claude Code plugin or skill could read agent status information from Pixel Agents-style transcript parsing to trigger actions (e.g., alert when an agent has been waiting for input for N minutes)
- The transcript parsing approach could be extended to emit structured events to a logging or observability system without requiring any changes to Claude Code itself
- The office visualization model (desks as directories, agents as workers) aligns with planned Claude Code agent team features — this extension could serve as a reference UI for visualizing multi-agent coordination in future skill development

---

## References

- [Pixel Agents GitHub Repository](https://github.com/pablodelucca/pixel-agents) (accessed 2026-03-05)
- [VS Code Marketplace — Pixel Agents](https://marketplace.visualstudio.com/items?itemName=pablodelucca.pixel-agents) (accessed 2026-03-05)
- [GitHub API — repos/pablodelucca/pixel-agents](https://api.github.com/repos/pablodelucca/pixel-agents) (accessed 2026-03-05)
- [Release v1.0.2 notes](https://github.com/pablodelucca/pixel-agents/releases/tag/v1.0.2) (accessed 2026-03-05)
- [Office Interior Tileset (16x16) by Donarg](https://donarg.itch.io/officetileset) (referenced in README, not accessed directly)
- [JIK-A-4 Metro City character pack](https://jik-a-4.itch.io/metrocity-free-topdown-character-pack) (referenced in README, not accessed directly)

---
