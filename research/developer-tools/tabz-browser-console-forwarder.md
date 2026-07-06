---
title: "Tabz — Browser Console to Terminal Forwarder"
research_date: "2026-03-01"
source_url: "https://github.com/GGPrompts/Tabz"
github_url: "https://github.com/GGPrompts/Tabz"
version_at_research: "v1.0.0 (package.json); CLAUDE.md documents internal version as v1.2.0; latest commit 2025-12-27 (no tagged releases)"
license: "MIT"
last_verified: "2026-03-01"
version_at_verification: "v1.0.0 (package.json) / v1.2.0 (CLAUDE.md internal)"
next_review: "2026-06-01"
---

## Overview

Tabz is a lightweight, tab-based browser terminal interface built with React, TypeScript, and xterm.js that forwards browser console output to the backend terminal in real time. The project contains a browser-to-terminal console forwarding subsystem (`consoleForwarder.ts`) that intercepts `console.log/warn/error/info/debug`, batches them, and POSTs them to a Node.js backend endpoint which writes them to stdout — making browser logs visible in tmux sessions. This pattern was explicitly designed for AI coding assistants (Claude Code) to debug frontend applications autonomously via `tmux capture-pane` without requiring a human to watch the browser DevTools panel.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI agents (Claude Code) cannot read browser DevTools console output | `consoleForwarder.ts` intercepts all `console.*` calls and POSTs batched logs to the backend |
| Browser and server logs exist in separate streams, requiring human correlation | Backend `/api/console-log` endpoint writes browser logs to stdout with `[Browser:source]` prefix, unifying both streams in the same terminal |
| Identifying which source file caused a browser log requires DevTools inspection | `Error().stack` is parsed at log time to extract the originating filename and line number, appended as `[Browser:SimpleTerminalApp.tsx:123]` |
| High-frequency logging creates excessive HTTP traffic | Logs are buffered in an array and flushed in a single POST every 100ms via a debounced `setTimeout` |
| Forwarding should not run in production builds | Guard `if (import.meta.env.PROD) return;` ensures the forwarder is dev-only; Vite strips the dead branch from production bundles |
| CORS restrictions prevent direct backend calls from the browser | Vite dev server proxy (`/api → http://localhost:8127`) means the forwarder uses a relative URL with no CORS issue |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 1 | 2026-03-01 |
| Forks | 0 | 2026-03-01 |
| Contributors | 1 | 2026-03-01 |
| Latest Release | No tagged releases | 2026-03-01 |
| Last Commit | 2025-12-27 | 2026-03-01 |
| Primary Language | TypeScript (69% of codebase) | 2026-03-01 |
| Repository Size | 3,300 KB | 2026-03-01 |
| Extracted From | [Opustrator](https://github.com/GGPrompts/opustrator) | 2026-03-01 |

---

## Key Features

### Browser Console Forwarding (`src/utils/consoleForwarder.ts`)

- Overrides all five `console` methods (`log`, `warn`, `error`, `info`, `debug`) at app startup while preserving originals — both local DevTools output and remote forwarding occur simultaneously
- Parses `new Error().stack` to extract the TypeScript source file and line number (e.g., `SimpleTerminalApp.tsx:123`) for each log entry, providing source context without a sourcemap server
- Buffers log entries in an in-memory array and flushes as a JSON batch to `POST /api/console-log` after a 100ms debounce timeout, reducing per-message HTTP overhead
- Guards activation behind `import.meta.env.PROD` check — Vite eliminates the entire forwarder from production bundles
- Uses relative URL `/api/console-log` to route through the Vite dev proxy (`vite.config.ts` proxies `/api` to `http://localhost:8127`) — no CORS configuration required
- Registers a `beforeunload` handler to flush the buffer on page close, preventing log loss

### Backend Log Reception (`backend/routes/api.js`)

- `POST /api/console-log` accepts a JSON array of log objects `{ level, message, source, timestamp }`
- Prefixes each entry as `[Browser:filename.tsx:line]` or `[Browser]` when source is unavailable
- Routes to `logger.error/warn/debug/info` based on `level`, integrating browser logs into the same structured logging pipeline as backend events
- When the backend runs inside a tmux session, all output (browser + backend) is capturable via `tmux capture-pane -t <session> -p`

### Tab-Based Terminal UI (main feature set)

- React + xterm.js frontend with WebGL rendering (`@xterm/addon-webgl`) running on Vite dev server at port 3007
- Node.js + Express + node-pty backend at port 8127 providing real PTY processes over WebSocket
- Supports 15+ terminal types: Claude Code, Bash, LazyGit, TFE, and TUI tools
- Dual tmux context menu system: tab-level menu (session ops) and pane-level menu (split, swap, zoom, kill)
- Full keyboard shortcut coverage: `Alt+H/V` (split), `Alt+U/D` (swap pane), `Alt+M` (mark), `Alt+S` (swap marked), `Alt+Z` (zoom toggle), `Alt+X` (kill pane)
- Tmux window switcher submenu showing all windows with active indicator
- Zustand state management for terminal registry with Immer for immutable updates
- Drag-and-drop tab reordering via `@dnd-kit/core` and `@dnd-kit/sortable`
- 14 terminal color themes defined in `src/styles/terminal-themes.ts`
- Per-spawn configuration: `workingDir`, `defaultTheme`, `defaultTransparency`, `defaultFontSize`, `defaultFontFamily`
- Optional gg-hub integration: reads project manifests to auto-populate spawn menu with project-specific terminals

### Docker Support

- `Dockerfile` and `docker-compose.yml` included for containerized deployment
- `docker-entrypoint.sh` handles startup mode selection
- `CLEANUP_ON_START` and `FORCE_CLEANUP` env vars control terminal state persistence across restarts

---

## Technical Architecture

```text
Browser (dev mode only)                    Backend (Node.js, port 8127)
─────────────────────────────────────────  ────────────────────────────────────
main.tsx
  └─ setupConsoleForwarding()              POST /api/console-log
       │                                        │
       ├─ Override console.log/warn/error/info/debug
       │                                        │
       ├─ getSource() → Error().stack      logger.info/warn/error()
       │    parse .tsx?:line                    │
       │                                        ▼
       ├─ formatArgs() → compact string    stdout (prefixed [Browser:src:line])
       │                                        │
       └─ queueLog() → logBuffer[]              ▼
            │                             tmux session (if running in tmux)
            └─ setTimeout(flushLogs,100)        │
                  │                             ▼
                  └─ fetch('/api/console-log')  tmux capture-pane -t <session> -p
                       (Vite proxy → :8127)          ← AI agent reads this output

Terminal UI                                WebSocket PTY
─────────────────────────────────────────  ────────────────────────────────────
React + xterm.js (port 3007)    ←─ws─────  node-pty (real PTY processes)
Zustand store (terminals[])               terminal-registry.js (state)
@dnd-kit (tab drag-and-drop)              unified-spawn.js (15+ terminal types)
14 color themes                           tmux-session-manager.js
```

**Vite proxy configuration** (`vite.config.ts`):

```typescript
server: {
  port: 3007,
  proxy: {
    '/api': { target: 'http://localhost:8127', changeOrigin: true },
    '/ws':  { target: 'ws://localhost:8127', ws: true }
  }
}
```

**Log payload format** (single batch):

```json
{
  "logs": [
    { "level": "log",   "message": "terminal connected", "source": "Terminal.tsx:89",  "timestamp": 1735307000000 },
    { "level": "error", "message": "WebSocket closed",   "source": "Terminal.tsx:145", "timestamp": 1735307000050 }
  ]
}
```

**Backend log output** (appears on stdout / in tmux):

```text
[Browser:Terminal.tsx:89]  terminal connected
[Browser:Terminal.tsx:145] WebSocket closed
```

---

## Installation & Usage

```bash
# Clone the repository
git clone https://github.com/GGPrompts/Tabz.git
cd Tabz

# Install frontend dependencies
npm install --ignore-scripts

# Install backend dependencies
cd backend && npm install && cd ..
```

```bash
# Start backend (in tmux for log capture)
tmux new-session -d -s tabz-dev
tmux send-keys -t tabz-dev 'cd backend && npm start' Enter

# Start frontend dev server (in another pane/window)
npm run dev
# → http://localhost:3007
```

```bash
# Capture all logs (browser + backend) for AI agent inspection
tmux capture-pane -t tabz-dev -p
```

**Activating console forwarding in an existing project** — extract `consoleForwarder.ts` and call at app startup:

```typescript
// main.tsx
import { setupConsoleForwarding } from './utils/consoleForwarder';

setupConsoleForwarding(); // must be called before any console.* output

ReactDOM.createRoot(document.getElementById('root')!).render(<App />);
```

**Add backend endpoint** (`backend/routes/api.js`):

```javascript
router.post('/console-log', asyncHandler(async (req, res) => {
  const { logs } = req.body;
  logs.forEach(({ level, message, source }) => {
    const prefix = source ? `[Browser:${source}]` : '[Browser]';
    console[level in console ? level : 'log'](`${prefix} ${message}`);
  });
  res.json({ success: true, received: logs.length });
}));
```

---

## Relevance to Claude Code Development

### Applications

- **Autonomous frontend debugging**: Claude Code agents running in tmux can read browser console output through `tmux capture-pane` without requiring a human to relay DevTools logs. This closes the feedback loop for frontend debugging tasks where the agent would otherwise be blind to client-side errors.
- **Unified log stream for AI triage**: Prefixing browser logs with `[Browser:source:line]` and merging them into the backend stdout stream lets an AI agent correlate frontend events with backend events by scanning a single capture — no context switching between browser and terminal.
- **Zero-overhead adoption in dev builds**: The `import.meta.env.PROD` guard and Vite proxy mean the pattern costs nothing in production and requires no CORS setup during development — safe to add to any Vite-based project.

### Patterns Worth Adopting

- **Batch-then-flush with fixed debounce**: Collecting multiple log entries and flushing after 100ms prevents per-call HTTP overhead without requiring a queue worker or message broker. The pattern applies to any event stream destined for a backend (metrics, traces, user actions).
- **`Error().stack` for source attribution**: Parsing the V8 stack trace inside the logging wrapper to extract `filename:line` is a lightweight alternative to sourcemap servers for development-time attribution. The regex `([^/\\]+\.tsx?):(\d+)` targets TypeScript source names and survives Vite's fast refresh.
- **Compact object formatting for log readability**: The `formatArgs()` function truncates large objects to `{key1, key2, key3...}` and arrays to `Array(N)` — keeping logs readable in a narrow terminal without losing structural information.
- **Dual output preservation**: Overriding console methods while calling the stored original ensures the browser DevTools panel stays functional. AI agents read the tmux stream; human developers still use DevTools. Both workflows coexist.

### Integration Opportunities

- **Claude Code skill for log capture**: The `tmux capture-pane` workflow documented in Tabz's CLAUDE.md could be formalized as a Claude Code skill — spawning a dev server, attaching the console forwarder, and providing a tool that returns captured log output for analysis.
- **Extracting `consoleForwarder.ts` as a standalone utility**: The 120-line file has no runtime dependencies beyond `fetch` and is framework-agnostic. It can be published as a zero-dependency npm package or vendored directly into any Vite project to enable AI-agent-friendly browser debugging.
- **Backend endpoint as a Claude Code MCP server tool**: The `/api/console-log` endpoint could be exposed as an MCP tool that lets Claude Code actively query buffered browser logs on demand rather than polling `tmux capture-pane`.
- **Pattern for any headless browser testing**: The same forwarding mechanism applies to Playwright/Puppeteer test environments where `page.on('console')` events need to appear in the test runner's stdout for AI agent consumption.

---

## References

- [GGPrompts/Tabz GitHub Repository](https://github.com/GGPrompts/Tabz) (accessed 2026-03-01)
- [src/utils/consoleForwarder.ts — primary source](https://github.com/GGPrompts/Tabz/blob/master/src/utils/consoleForwarder.ts) (accessed 2026-03-01)
- [backend/routes/api.js — /api/console-log endpoint](https://github.com/GGPrompts/Tabz/blob/master/backend/routes/api.js) (accessed 2026-03-01)
- [vite.config.ts — proxy configuration](https://github.com/GGPrompts/Tabz/blob/master/vite.config.ts) (accessed 2026-03-01)
- [CLAUDE.md — project AI debugging context](https://github.com/GGPrompts/Tabz/blob/master/CLAUDE.md) (accessed 2026-03-01)
- [CHANGELOG.md — version history](https://github.com/GGPrompts/Tabz/blob/master/CHANGELOG.md) (accessed 2026-03-01)
- [LESSONS_LEARNED.md — engineering decisions](https://github.com/GGPrompts/Tabz/blob/master/LESSONS_LEARNED.md) (accessed 2026-03-01)
- [GGPrompts/Opustrator — parent project](https://github.com/GGPrompts/opustrator) (accessed 2026-03-01)

---
