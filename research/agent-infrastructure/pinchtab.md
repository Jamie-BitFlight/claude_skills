---
title: "PinchTab"
research_date: "2026-03-01"
source_url: "https://pinchtab.com/docs"
github_url: "https://github.com/pinchtab/pinchtab"
version_at_research: "v0.7.6"
license: "MIT"
last_verified: "2026-03-01"
version_at_verification: "v0.7.6"
next_review: "2026-06-01"
---

## Overview

PinchTab is a standalone HTTP server (12MB Go binary) that gives AI agents direct control over Chrome browsers via a simple REST API, using the Chrome DevTools Protocol (CDP) as the underlying transport. It prioritizes token efficiency by exposing the browser's accessibility tree instead of screenshots, reducing per-page token costs by 5-13x compared to visual approaches. The tool manages multiple isolated Chrome instances, persistent browser profiles, and provides stealth mode for bypassing bot detection.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Browser automation for AI agents is token-expensive when using screenshots | Accessibility tree snapshot delivers ~800 tokens/page vs. 10,000+ for screenshots |
| CDP is complex: agents must manage WebSocket connections and protocol details | HTTP REST API wraps CDP entirely; agents send JSON, get JSON back |
| Multiple agents need isolated browser sessions without shared state | Multi-instance orchestrator with per-instance Chrome processes and isolated profiles |
| Bot detection blocks headless automation | Stealth injection scripts mask automation signatures at the CDP level |
| Login sessions expire or don't persist between agent runs | Named profiles persist cookies, local storage, and auth state across instance restarts |
| Fragile coordinate-based clicking breaks across page layouts | Accessibility tree element refs (e0, e1...) provide stable, layout-independent targeting |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 2,304 | 2026-03-01 |
| Forks | 133 | 2026-03-01 |
| Contributors | 10 | 2026-03-01 |
| Latest Release | v0.7.6 | 2026-03-01 |
| Open Issues | 7 | 2026-03-01 |
| Binary Size | 12MB | 2026-03-01 |
| Primary Language | Go (73% by bytes) | 2026-03-01 |

Downloads/month: Not tracked publicly (npm package and binary downloads tracked per-release; v0.7.6 linux-amd64 had 513 downloads in ~3 days post-release).

SOURCE: [GitHub API repos/pinchtab/pinchtab](https://api.github.com/repos/pinchtab/pinchtab) (accessed 2026-03-01)

---

## Key Features

### Token-Efficient Browser Interaction

- Accessibility tree (a11y) snapshot delivers ~800 tokens per page vs. 5,000-13,000 for screenshots
- Three snapshot output formats: JSON (structured), text (indented tree, lowest token cost), YAML
- Interactive filter (`?filter=interactive`) returns only clickable/focusable elements, further reducing tokens
- Ref caching: element refs (e0, e1, e2...) from last snapshot are cached per tab; `/action` resolves `{"ref":"e5"}` without re-fetching the a11y tree

SOURCE: [pinchtab/pinchtab architecture docs](https://github.com/pinchtab/pinchtab/blob/main/docs/architecture/pinchtab-architecture.md) (accessed 2026-03-01)

### Multi-Instance Orchestration

- Single orchestrator process on port 9867 manages N Chrome instances on ports 9868-9968
- Each instance is a separate Chrome process with completely isolated state
- Lazy Chrome initialization: Chrome starts on first HTTP request, not at instance creation
- Instances identified by stable hash IDs (`inst_XXXXXXXX`); survive orchestrator restarts
- Dashboard UI for real-time monitoring of all instances and their tabs

SOURCE: [pinchtab/pinchtab core-concepts docs](https://github.com/pinchtab/pinchtab/blob/main/docs/core-concepts.md) (accessed 2026-03-01)

### Persistent Browser Profiles

- Named profiles store cookies, local storage, cache, and browsing history in Chrome user data directories
- One profile per instance; multiple tabs share the profile's session state
- "Log in once, stay logged in" pattern: profile persists auth across instance restarts
- Profile operations: create, list, reset via CLI or HTTP API

### Stealth Mode

- JavaScript injection masks Playwright/Puppeteer/CDP automation signatures
- Injected at browser context level before any page scripts execute
- Human-like mouse movement via cubic bezier curves (random control points, variable timing)
- Human-like typing simulation: 80ms/char base delay, random pauses, occasional typos with backspace correction

### Flexible Deployment

- Self-hosted mode: PinchTab launches and manages its own Chrome process
- Remote Chrome mode: connect via `CDP_URL` environment variable to an existing Chrome instance (useful for shared Chrome in containers)
- Docker image (Alpine + Chromium): `docker run -d -p 9867:9867 pinchtab/pinchtab`
- npm package wrapper: `npm install -g pinchtab` (downloads platform binary on postinstall)
- Shell installer: `curl -fsSL https://pinchtab.com/install.sh | bash`
- Pre-built binaries for darwin-amd64, darwin-arm64, linux-amd64, linux-arm64, windows-amd64, windows-arm64

---

## Technical Architecture

PinchTab implements a three-layer architecture:

```text
┌─────────────────────────────────────────┐
│   AI Agent (CLI / curl / SDK)           │
└──────────────┬──────────────────────────┘
               │ HTTP/JSON (port 9867)
               ▼
┌─────────────────────────────────────────┐
│   PinchTab Orchestrator (Go HTTP server)│
│  ┌──────────────┐  ┌────────────────┐   │
│  │ Orchestrator │  │   Dashboard    │   │
│  │ (instance    │  │   (web UI)     │   │
│  │  lifecycle)  │  └────────────────┘   │
│  └──────┬───────┘                       │
│         │ HTTP proxy to child instances  │
│  ┌──────▼───────────────────────────┐   │
│  │ Bridge (per instance)            │   │
│  │  tab registry + snapshot cache   │   │
│  └──────┬───────────────────────────┘   │
└─────────┼───────────────────────────────┘
          │ CDP WebSocket
          ▼
┌─────────────────────────────────────────┐
│   Chrome (headless or headed)           │
└─────────────────────────────────────────┘
```

**Go package layout** (`internal/` pattern for encapsulation):

- `internal/bridge` — Core CDP logic: tab lifecycle, ref caching, snapshot pipeline, `BridgeAPI` interface
- `internal/orchestrator` — Multi-instance lifecycle via `HostRunner` interface (decouples process management from business logic)
- `internal/profiles` — Chrome user data directory CRUD, identity discovery (parses Chrome internal JSON files)
- `internal/dashboard` — Backend logic and embedded static assets for web UI
- `internal/assets` — Centralized embedded files (stealth scripts, HTML templates)
- `internal/human` — Anti-detection: Bezier mouse curves, keystroke timing simulation
- `internal/handlers` — HTTP API handlers and middleware
- `cmd/pinchtab` — Entry points and CLI command definitions

**Snapshot pipeline** (a11y tree → agent-readable output):

```text
Chrome a11y tree (CDP)
       │
       ▼
  Raw JSON parse (RawAXNode)  ← Manual parsing avoids cdproto crash on unknown PropertyName values
       │
       ▼
  Flatten to []A11yNode        ← DFS walk, assigns stable refs (e0, e1, e2...)
       │
       ├──▶ JSON               ← Full structured output (default)
       ├──▶ Text               ← Indented tree, lowest token count
       └──▶ YAML               ← Alternative structured format
```

SOURCE: [pinchtab architecture docs](https://github.com/pinchtab/pinchtab/blob/main/docs/architecture/pinchtab-architecture.md) (accessed 2026-03-01)

---

## Installation & Usage

```bash
# macOS / Linux one-liner
curl -fsSL https://pinchtab.com/install.sh | bash

# npm (downloads platform binary on postinstall)
npm install -g pinchtab

# Docker
docker run -d -p 9867:9867 pinchtab/pinchtab

# Build from source (Go 1.25+)
go build -o pinchtab ./cmd/pinchtab
```

```bash
# Start the orchestrator (listens on :9867)
pinchtab

# --- CLI usage ---
# Navigate and inspect
pinchtab nav https://example.com
pinchtab snap -i -c          # snapshot: interactive elements only, compact output
pinchtab click e5            # click element by ref
pinchtab fill e3 "user@example.com"
pinchtab press e7 Enter
pinchtab text                # extract all text (~800 tokens)

# Multi-instance workflow
pinchtab instance launch --mode headless   # returns inst_XXXXXXXX
pinchtab instance launch --mode headed --port 9999
pinchtab profiles                          # list profiles
pinchtab profile create work               # create named profile
```

```bash
# --- HTTP API usage ---
# Create instance
curl -X POST http://localhost:9867/instances/launch \
  -H "Content-Type: application/json" \
  -d '{"mode":"headless"}'
# Returns: {"id":"inst_0a89a5bb","port":"9868","status":"starting"}

# Open tab in instance
TAB=$(curl -X POST http://localhost:9867/instances/inst_0a89a5bb/tabs/open \
  -d '{"url":"https://example.com"}' | jq -r '.tabId')

# Get snapshot (interactive elements only)
curl "http://localhost:9867/instances/inst_0a89a5bb/snapshot?filter=interactive"

# Click element by ref
curl -X POST "http://localhost:9867/instances/inst_0a89a5bb/action" \
  -d '{"kind":"click","ref":"e5"}'

# Extract text (token-efficient)
curl "http://localhost:9867/instances/inst_0a89a5bb/text"
```

**Optimized pattern for AI scraping agents (93% token reduction vs. exploratory approach):**

SOURCE: [pinchtab agent-optimization guide](https://github.com/pinchtab/pinchtab/blob/main/docs/guides/agent-optimization.md) (accessed 2026-03-01)

```bash
# Navigate, wait for a11y tree population, extract headlines
curl -X POST http://localhost:9867/navigate \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}' && \
sleep 3 && \
curl http://localhost:9867/snapshot | \
jq '.nodes[] | select(.name | length > 15) | .name' | \
head -30
```

Note: 3-second wait is required after navigation — Chrome's accessibility tree populates after DOM render. Skipping this returns only the root node (`{"count":1,"nodes":[{"ref":"e0","role":"RootWebArea"}]}`).

---

## Relevance to Claude Code Development

### Applications

- Claude Code agents performing web research tasks can use PinchTab to navigate, extract structured text, and interact with web UIs without incurring the token cost of screenshot-based approaches
- Multi-instance profile isolation maps directly to multi-agent workflows where each agent maintains a distinct authenticated session (e.g., different GitHub accounts, SaaS logins)
- The REST API design makes PinchTab callable from any Claude Code bash tool invocation — no SDK required

### Patterns Worth Adopting

- **Accessibility tree over DOM/screenshots**: The a11y tree-first approach is applicable to any tool that needs to describe UI state to an LLM — the token reduction (5-13x) is a structural win regardless of the tool
- **Ref caching with stable IDs**: The pattern of assigning short, stable refs (e0, e1...) to elements in a snapshot and caching ref→nodeID mappings avoids redundant tree traversal on every action call — applicable to any stateful agent tool
- **Prescriptive system prompts for agent tools**: The agent-optimization guide demonstrates that giving agents exact command patterns (not task descriptions) reduces token use by 14x for repetitive tasks. This is directly applicable to how we document Claude Code skill usage in system prompts
- **Wait-for-stability polling**: The recommendation to poll for a11y tree count > threshold before acting (instead of fixed sleep) is the correct production pattern for any async state dependency

### Integration Opportunities

- Claude Code skills that do web research could delegate browser steps to a running PinchTab instance via `Bash(curl ...)` calls, keeping all context in structured JSON rather than images
- The MCP protocol could wrap PinchTab HTTP endpoints as tools, enabling Claude Code to invoke browser actions as native tool calls without bash indirection
- PinchTab's multi-instance API could serve as the backend for a Claude Code skill that manages parallel web-browsing sub-agents, each with an isolated Chrome profile

---

## References

- [PinchTab GitHub Repository](https://github.com/pinchtab/pinchtab) (accessed 2026-03-01)
- [PinchTab Documentation Site](https://pinchtab.com/docs) (accessed 2026-03-01)
- [Architecture Documentation](https://github.com/pinchtab/pinchtab/blob/main/docs/architecture/pinchtab-architecture.md) (accessed 2026-03-01)
- [Core Concepts Documentation](https://github.com/pinchtab/pinchtab/blob/main/docs/core-concepts.md) (accessed 2026-03-01)
- [Agent Optimization Guide](https://github.com/pinchtab/pinchtab/blob/main/docs/guides/agent-optimization.md) (accessed 2026-03-01)
- [v0.7.6 Release Notes](https://github.com/pinchtab/pinchtab/releases/tag/v0.7.6) (accessed 2026-03-01)

---
