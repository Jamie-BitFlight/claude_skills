# Screenpipe

**Resource**: Screenpipe — AI memory for your screen
**URL**: <https://github.com/screenpipe/screenpipe>
**License**: MIT OR Apache-2.0
**Latest Version**: 0.3.307 (as of 2026-05-02)
**Repository**: <https://github.com/screenpipe/screenpipe>

---

## Identity & Quick Facts

Screenpipe is an open-source, local-first AI memory application that continuously captures your screen and audio, creating a searchable, AI-powered record of everything you do on your computer.

**Key Statistics**:
- **Organization**: Screenpipe (Mediar, Inc.) — Founded 2024, based in San Francisco, CA
- **Founder**: Louis Beaumont (@louis030195)
- **Latest Version**: 0.3.307 (released 2026-05-02)
- **Language**: Rust (backend), TypeScript/React (frontend with Tauri), JavaScript (MCP server)
- **License**: MIT OR Apache-2.0 (dual-licensed)
- **Platforms Supported**: macOS (Apple Silicon + Intel), Windows 10/11, Linux (source)
- **MCP Server Version**: screenpipe-mcp 0.17.0

---

## Problem Addressed

Screenpipe solves the problem of information loss during digital work. Knowledge workers, developers, researchers, and remote workers spend 8+ hours daily on-screen but cannot reliably recall what they saw, heard, or worked on. Existing solutions require cloud upload, proprietary agents, or offer limited privacy.

Screenpipe provides:

1. **Local-first memory** — All data stays on your device. No cloud upload required unless explicitly opted in via encryption and sync features.
2. **Context for AI agents** — AI assistants (Claude, Cursor, Cline) can query your screen history to understand what you're working on without explicit prompts.
3. **Deterministic data permissions** — Organizations can deploy AI agents with YAML-based, OS-level access controls — not prompt-based restrictions.

---

## Key Features

### 1. Event-driven screen capture

"Instead of recording every second, screenpipe listens for meaningful events — app switches, clicks, typing pauses, scrolling — and captures a screenshot only when something actually changes. Each capture pairs a screenshot with the accessibility tree (the structured text the OS already knows about: buttons, labels, text fields). If accessibility data isn't available (e.g. remote desktops, games), it falls back to OCR."

**Data efficiency**: Accessibility tree extraction is faster and more accurate than continuous OCR. Results: 5–10% CPU usage, 0.5–3 GB RAM, ~20 GB storage/month (vs ~2 GB continuous).

**Source**: README.md § "Event-driven screen capture" (accessed 2026-05-02)

### 2. Audio transcription and speaker identification

- **Local Whisper** (OpenAI Whisper, no cloud upload)
- **Speaker diarization** — distinguishes between speakers in multi-party calls
- **Real-time transcription** — captures what you hear (system audio) and what you say (microphone)
- **Supported backends**: OpenAI Whisper (local), Deepgram (cloud), Ollama (custom), OpenAI-compatible endpoints

**Source**: README.md § "Audio transcription" (accessed 2026-05-02)

### 3. Natural language search

- **Semantic search** using embeddings across OCR text and audio transcriptions
- **Filters**: app name, window title, browser URL, date range, speaker name
- **Results include**: screenshot images and audio clips alongside text

**Source**: README.md § "AI-powered search" (accessed 2026-05-02)

### 4. Timeline view

Visual timeline of entire screen history. Scroll through day like a DVR. Click any moment to see full screenshot, extracted text, and playback audio from any time period.

**Source**: README.md § "Timeline view" (accessed 2026-05-02)

### 5. Plugin system — Pipes

Pipes are scheduled AI agents defined as markdown files (`pipe.md`). Each pipe includes:
- **Prompt**: The AI task to run (YAML frontmatter + markdown body)
- **Schedule**: When to run (cron-like syntax)
- **Data permissions**: App/window filters, content type restrictions (ocr, audio, input, accessibility), time ranges, endpoint gating

**Enforcement**: Three-layer enforcement (skill gating, agent interception, server middleware with cryptographic tokens) prevents compromised agents from accessing denied data.

**Built-in example pipes**:
- **Obsidian sync**: Automatically sync screen activity to Obsidian vault as daily logs
- **Reminders**: Scan activity for todos, create Apple Reminders (macOS)
- **Idea tracker**: Surface startup ideas from browsing + market trends

**Source**: README.md § "Plugin system (Pipes)" (accessed 2026-05-02)

### 6. MCP server integration (Model Context Protocol)

Screenpipe runs as an MCP server, allowing AI assistants to query screen history:

- **Works with**: Claude Desktop, Cursor, VS Code (Cline, Continue), any MCP-compatible client
- **Installation**: `claude mcp add screenpipe -- npx -y screenpipe-mcp`
- **Transport**: stdio (default) or HTTP with bearer auth (for remote clients)
- **Tools exposed**: `search_content` (standard), full toolset in stdio mode (export-video, list-meetings, activity-summary, search-elements, frame-context)

**Source**: README.md § "MCP server" (accessed 2026-05-02), screenpipe-mcp/README.md (accessed 2026-05-02)

### 7. Developer API

Full REST API on localhost:3030 (default):
- **Search endpoints**: GET `/search?q=query&content_type=ocr|audio|all&limit=N`
- **Frame access**: GET `/frames` — raw screenshot data with timestamps
- **Audio endpoint**: GET `/search?content_type=audio` — audio transcriptions
- **Raw SQL**: Direct access to underlying SQLite database
- **SDK**: JavaScript/TypeScript SDK available

**Example**:
```javascript
import { pipe } from "@screenpipe/js";
const results = await pipe.queryScreenpipe({
  q: "project deadline",
  contentType: "all",
  limit: 20,
  startTime: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
});
```

**Source**: README.md § "Developer API" and "API examples" (accessed 2026-05-02)

### 8. Apple Intelligence integration (macOS)

On supported Macs: Apple Intelligence provides on-device AI processing for:
- Daily summaries
- Action items
- Reminders

Zero cloud dependency, zero cost.

**Source**: README.md § "Apple Intelligence integration" (accessed 2026-05-02)

### 9. Privacy and security controls

- **100% local by default** — SQLite database stored on device
- **Optional encryption** — End-to-end encrypted sync between devices (zero-knowledge encryption)
- **Deterministic AI permissions** — Per-pipe YAML control of agent data access (not prompt-based)
- **Content filtering** — Automated exclusion of passwords, PII
- **Export/delete** — Full user control over data lifecycle
- **No account required** — Core app works without sign-up

**Source**: README.md § "Privacy and security" (accessed 2026-05-02)

### 10. Multi-monitor and team deployment

- **All monitors** simultaneously on a single machine
- **Team deployment** (screenpipe Teams):
  - Central config management (push capture settings to fleet)
  - Shared pipes across team
  - Per-pipe AI data permissions
  - Admin dashboard
  - MDM ready (Intune, SCCM, Robopack)
  - Enterprise SSO/SAML, audit logs, SOC 2 / HIPAA compliance ready

**Source**: README.md § "Teams & enterprise" (accessed 2026-05-02)

---

## Technical Architecture

### Core components

**1. Event engine** (`screenpipe-engine`, `screenpipe-events`)
- Listens for OS-level events (app switch, click, typing pause, scroll, clipboard change, idle periods)
- Triggers frame capture when event occurs
- Hash-based frame comparison to skip identical frames (>80% skip rate on static screens)

**Source**: Cargo.toml workspace members list, README.md § "Technical architecture" (accessed 2026-05-02)

**2. Screen capture pipeline** (`screenpipe-screen`, `screenpipe-a11y`)
- **Primary**: Accessibility tree extraction (structured text: buttons, labels, fields)
- **Fallback**: OCR (platform-specific: Apple Vision on macOS, Windows native OCR, Tesseract on Linux)
- **ScreenCaptureKit** (macOS) or equivalent platform APIs for frame capture
- Runs event-driven, not continuously

**3. Audio capture and transcription** (`screenpipe-audio`)
- **Input**: Microphone (user speech)
- **Output**: System audio (what user hears)
- **Engines**:
  - Local: OpenAI Whisper + Metal GPU acceleration (macOS)
  - Cloud: Deepgram, OpenAI
  - Custom: Ollama, OpenAI-compatible endpoints
  - Newer: Qwen3-asr with OpenBLAS (Linux/Windows)
- **Diarization**: Identifies speaker changes and assigns speaker names

**4. Storage** (`screenpipe-db`)
- **SQLite** with FTS5 (full-text search)
- Local on disk (~300 MB/8 hours vs ~2 GB with continuous recording)
- Schema: tables for frames, audio_transcriptions, speakers, audio_chunks, metadata

**5. API server** (`screenpipe-server`)
- REST API on localhost:3030
- Endpoints: search, frames, audio, elements, health, pipe management
- Authentication: optional bearer token for HTTP transport

**6. Plugin/Pipe engine**
- Markdown-based agent definition
- YAML frontmatter for permissions (allow-apps, deny-apps, time-range, content-types, endpoints)
- Scheduled execution (cron syntax)
- Integrates with AI agent (Claude, pi, etc.) for prompt execution

**7. Desktop app UI** (`apps/screenpipe-app-tauri`)
- Built with Tauri (Rust + TypeScript)
- Next.js-based React frontend
- Black & white geometric minimalist design (no color, sharp corners)
- Components: Timeline view, Search interface, Settings, Pipe management, Tray icon

**8. MCP server** (`packages/screenpipe-mcp`)
- TypeScript (MCP SDK v1.27.1+)
- Stdio or HTTP transport
- Exposes search and context tools to Claude, Cursor, etc.

**Source**: README.md § "Technical architecture" (accessed 2026-05-02), CLAUDE.md § "Key Directories" (accessed 2026-05-02), Cargo.toml workspace structure (accessed 2026-05-02)

### Data flow

```
OS Events (click, type, app switch)
  ↓
Capture trigger (screenshot + accessibility tree)
  ↓
Frame comparison (hash match? skip)
  ↓
OCR/Accessibility extraction
  ↓
Audio processing (Whisper/Deepgram)
  ↓
SQLite storage (screenshots as JPEG, metadata indexed)
  ↓
API layer (localhost:3030)
  ↓
Search / Timeline / Pipes / MCP clients
```

**Source**: README.md § "Technical architecture" diagram (accessed 2026-05-02)

### Deployment tiers

**Personal**:
- Desktop app (one-time $400 purchase)
- Optional Pro subscription ($39/month): cloud sync, priority support
- Lifetime + Pro: $600 one-time

**Teams**:
- Central admin dashboard
- Shared configurations
- Per-pipe AI data permissions
- Custom pricing
- MDM integration

**Enterprise**:
- SSO/SAML
- Audit logs
- SLA
- SOC 2 / HIPAA compliance ready

**Source**: README.md § "Pricing" (accessed 2026-05-02)

---

## Relevance to Claude Code Development

Screenpipe is highly relevant to Claude Code and AI agent development in four key areas:

### 1. Context infrastructure for AI agents

Screenpipe's core mission is providing full context of human work to AI agents. The MCP integration allows Claude Code, Cursor, Cline, and Continue to:
- Query what the user has been working on
- Search historical context (code files viewed, conversations, debugging steps)
- Trigger automated actions based on screen activity (e.g., "when user edits auth.ts, run related tests")

This eliminates the need for explicit prompts — AI can act on ambient context.

**Source**: VISION.md § "What screenpipe is" — "Context infrastructure for AI agents" (accessed 2026-05-02)

### 2. Privacy-first AI automation

Screenpipe's deterministic, OS-level data permissions (YAML frontmatter, not prompt-based) model is directly applicable to Claude Code plugins and skills. It demonstrates:
- How to enforce data access boundaries at enforcement layers (skill gating, agent interception, middleware tokens)
- How to let admins control what AI can access without trusting the AI to "behave" — three-layer enforcement prevents circumvention even if an agent is compromised

**Source**: README.md § "Pipe data permissions" (accessed 2026-05-02)

### 3. MCP server design and integration

Screenpipe-mcp is a well-designed MCP server that:
- Exposes both stdio and HTTP transports
- Includes bearer-token auth for remote connections
- Demonstrates progressive disclosure (basic tools in HTTP, full toolset in stdio)
- Provides concrete example of integrating with Claude Desktop, Cursor, and other AI assistants

Valuable reference for building other MCP servers that extend Claude Code's capabilities.

**Source**: packages/screenpipe-mcp/README.md (accessed 2026-05-02), package.json (accessed 2026-05-02)

### 4. Event-driven architecture for continuous monitoring

Screenpipe's event-driven capture (not continuous polling) is architecturally relevant for building Claude Code plugins that monitor and react to user activity without excessive CPU/memory overhead. The hash-based frame comparison and accessibility tree extraction patterns are applicable to building efficient context-gathering agents.

**Source**: README.md § "Event-driven screen capture", VISION.md § "Engineering principles" (accessed 2026-05-02)

---

## Integrations

**AI coding assistants**: Cursor, Claude Code, Cline, Continue, OpenCode, Gemini CLI
**AI chat assistants**: ChatGPT (via MCP), Claude Desktop (via MCP), any MCP-compatible client
**Note-taking**: Obsidian, Notion
**Local AI**: Ollama, any OpenAI-compatible model server
**Automation**: Custom pipes (scheduled AI agents as markdown files)

**Source**: README.md § "Integrations" (accessed 2026-05-02)

---

## Limitations and Caveats

### 1. Storage requirements

~5–10 GB disk space per month. Event-driven capture dramatically reduces this vs continuous recording, but sustained usage accumulates significant storage. Users may need to implement archival or cleanup policies.

**Source**: README.md § "Frequently asked questions" (accessed 2026-05-02)

### 2. Accessibility tree limitations

Accessibility tree extraction (primary method) is not available in:
- Remote desktops
- Games with custom rendering
- Some Linux applications

Falls back to OCR in these cases, which is slower.

**Source**: README.md § "How does text extraction work?" (accessed 2026-05-02)

### 3. Transient audio device issues

Bluetooth and USB audio devices can disconnect or switch contexts (e.g., another app hijacks audio). Recovery is automated (watchdog detects, rebuilds), but there may be brief gaps in transcription.

**Source**: TESTING.md § "Bluetooth audio device hijack recovery" (accessed 2026-05-02)

### 4. Window management fragility (macOS)

Overlay window management (fullscreen spaces, tray icon, keyboard focus) has documented regressions. TESTING.md lists 50+ critical edge cases due to complexity of macOS window APIs and Tauri/NSPanel interactions.

**Source**: TESTING.md § "Window overlay & fullscreen spaces" (accessed 2026-05-02)

### 5. Platform-specific behavior

- **macOS**: Requires accessibility permissions (prompted on first run, user can deny)
- **Windows**: Built-in OCR is slower than macOS Vision
- **Linux**: Requires building from source; accessibility tree support varies by desktop environment

**Source**: README.md § "Platform support" (accessed 2026-05-02)

### 6. MCP HTTP transport feature parity

The HTTP server exposes `search_content` only. Full toolset (export-video, list-meetings, activity-summary, search-elements, frame-context) is available in stdio mode.

**Source**: screenpipe-mcp/README.md § "Option 2: HTTP Server" (accessed 2026-05-02)

### 7. Pipe execution latency

Scheduled pipes introduce latency between triggering event and agent execution. For real-time use cases (e.g., keystroke logging), direct API access is more responsive.

**Source**: README.md § "Plugin system (Pipes)" (accessed 2026-05-02)

---

## Freshness Tracking

**Date created**: 2026-05-02
**Date last reviewed**: 2026-05-02
**Next review**: 2026-08-02 (3 months)

### Confidence Summary

| Section | Confidence | Rationale |
|---------|-----------|-----------|
| Identity & Quick Facts | **high** | Official repo, Cargo.toml version verified, website documentation accessed |
| Problem Addressed | **high** | VISION.md from official repo, primary sources quoted directly |
| Key Features | **high** | README.md comprehensive, all features extracted with direct quotes |
| Technical Architecture | **high** | Code directory structure verified, Cargo.toml workspace members confirmed, README.md § "Technical architecture" detailed |
| Relevance to Claude Code | **high** | VISION.md, MCP integration explicitly documented, integration with Claude Desktop confirmed |
| Integrations | **high** | Official documentation lists all integrations |
| Limitations | **high** | TESTING.md provides extensive regression test documentation, edge cases enumerated |
| Freshness Tracking | **high** | Clone timestamp 2026-05-02, latest commit same date |

---

## References

All sources accessed 2026-05-02 from <https://github.com/screenpipe/screenpipe> shallow clone.

- **README.md** — Official project overview, feature descriptions, technical architecture, pricing, platform support
- **VISION.md** — Product vision, problem statement, engineering principles, north star metrics
- **DESIGN.md** — Design system (typography, color, geometry, components, brand voice)
- **TESTING.md** — Regression testing checklist, documented edge cases, commit references for critical areas
- **CLAUDE.md** — Development guidelines, file headers, key directories, package manager conventions
- **Cargo.toml** — Workspace structure, version 0.3.307, workspace members (crates), dependencies
- **packages/screenpipe-mcp/package.json** — MCP server version 0.17.0, dependencies, installation
- **packages/screenpipe-mcp/README.md** — MCP server installation, usage, HTTP transport, SDK examples
- **git log** — Latest commit: 2026-05-02, "docs(testing): add Bluetooth audio device hijack recovery regression test"

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Octocode-MCP](./octocode-mcp.md) | mcp-ecosystem | complementary context infrastructure: Octocode provides code research context while Screenpipe provides screen/audio activity context to AI agents |
| [Browser MCP](./browsermcp-mcp.md) | mcp-ecosystem | adjacent context capture: both extract activity from user environment via local architecture; Browser MCP captures web interactions while Screenpipe captures screen and audio |

---

## Category

**research/mcp-ecosystem** — Screenpipe is an MCP server that extends Claude Code and other AI assistants with screen history and activity context.
