---
title: Tolaria
subtitle: Desktop app for managing markdown knowledge bases with AI integration
resource_type: desktop-application
primary_url: https://github.com/refactoringhq/tolaria
license: AGPL-3.0-or-later
version: "0.1.0"
platforms: macOS, Windows, Linux
created: 2026-05-02
last_reviewed: 2026-05-02
---

## Overview

Tolaria is a free, open-source desktop application for macOS, Windows, and Linux designed to manage personal knowledge bases stored as markdown files with YAML frontmatter. The application is built by Luca Rossi (@lucaronin) and emphasizes user ownership of data, offline-first operation, and AI integration while maintaining plain-text portability. Tolaria is actively maintained (latest commit: May 2, 2026) and licensed under AGPL-3.0-or-later at version 0.1.0.

The creator uses Tolaria to manage a personal workspace of 10,000+ notes combining professional work from the Refactoring project with personal journaling and knowledge management.

## Problem Addressed

Tolaria solves several interconnected problems in personal and organizational knowledge management:

1. **Data portability and lock-in risk** — Traditional note-taking apps (Notion, Evernote, Obsidian) store data in proprietary formats or require cloud infrastructure. If the service discontinues or the user stops paying, notes become inaccessible or require complicated export processes.

2. **AI integration friction** — Knowledge bases need to be legible to both human users and AI agents. Most tools require bespoke instructions or API wrappers to make vault structure understandable to AI systems.

3. **Offline accessibility** — Cloud-dependent tools fail without internet. Knowledge should remain accessible and editable offline, with sync happening transparently when connectivity returns.

4. **Rigid schema enforcement** — Many knowledge tools require predefined fields, document types, and validation rules. Personal knowledge management benefits from flexible structure with optional conventions, not enforced schemas.

## Key Statistics

- **Stars**: Not yet publicly available (repository active as of May 2, 2026)
- **Latest release**: v0.1.0 (alpha stage)
- **Creator's vault scale**: 10,000+ notes across professional and personal domains
- **Development status**: Active (continuous commits, recent fixes to editor functionality)
- **License**: AGPL-3.0-or-later (source code sharing required for derivative works)

## Key Features

### Files-First with Git as Version Control

Notes are stored as plain markdown files with optional YAML frontmatter. Every vault is a git repository, providing:
- Full version history through git
- Ability to use any git remote (GitHub, GitLab, Gitea, self-hosted)
- Zero dependency on Tolaria servers for collaboration or backup
- Works with standard git workflows (branching, merging, rebasing)

**Source**: README.md lines 24-25

### Offline-First, Zero Lock-In

The application requires no accounts, subscriptions, or cloud services. Vaults work completely offline and can be opened in future versions of Tolaria (or not opened at all — the data is portable). This design principle directly contradicts SaaS-based knowledge apps.

**Source**: README.md line 26

### Standards-Based Markdown with YAML Frontmatter

Notes use industry-standard markdown syntax combined with YAML frontmatter for structured metadata:

```markdown
---
type: project
status: active
start_date: 2026-01-15
belongs_to: [[Professional Work]]
---

# Project Title

Note content in markdown...
```

No proprietary binary formats or locked-in data structures.

**Source**: README.md line 28

### Convention-Over-Configuration with Flexible Field Names

Tolaria ships with opinionated defaults for standard field names (`type:`, `status:`, `url:`, `Workspace:`, `belongs_to:`, `related_to:`, `has:`, `start_date:`, `end_date:`) that trigger UI affordances without any configuration. However, the system is not rigid:

- **No required fields** — Every field is optional
- **No validation** — Missing fields do not prevent note creation or editing
- **Customizable defaults** — Users can override defaults via configuration files (e.g., `config/relations.md`, `config/semantic-properties.md`) stored in their vault
- **Dynamically detected relationships** — Relationship fields are detected by checking for `[[wikilinks]]` syntax, not by hardcoded field name lists

This design makes vaults accessible out-of-the-box while supporting specialized organizational systems that power users build.

**Source**: README.md line 29, ARCHITECTURE.md lines 11-12

### AI-First Knowledge Graph with MCP Integration

The application is designed as a structured knowledge graph where notes are nodes representing people, projects, events, responsibilities, and ideas. AI integration is built into the core:

- **MCP (Model Context Protocol) Server** — Tolaria bundles an MCP server for AI agents to query and modify vault contents via standardized tooling
- **Multi-AI support** — Officially supports Claude Code, Codex CLI, and Gemini CLI setup paths
- **Generative AI in the editor** — Built-in integration with Claude API (@anthropic-ai/sdk v0.78.0) for AI-assisted note writing
- **File-based agent instructions** — An `AGENTS.md` file in the vault allows users to define custom agent instructions for their specific vault structure

Notes are designed to be legible to both humans and AI systems without requiring bespoke per-vault AI instructions.

**Source**: README.md line 30, mcp-server/package.json, package.json dependency on @anthropic-ai/sdk

### Keyboard-First Interaction

The application prioritizes keyboard navigation and shortcuts for power users:
- Command palette for quick access to all features
- Keyboard-driven editor and sidebar navigation
- Minimal reliance on mouse-based UI actions

**Source**: README.md line 31

### Four-Panel UI Layout

The interface is inspired by Bear Notes and uses a four-panel layout:
1. Sidebar with vault structure and saved views
2. Note list showing filtered/searched results
3. Note editor (markdown or rich text)
4. Optional detail pane for metadata and properties

**Source**: ARCHITECTURE.md line 4

### Multi-Editor Support

Notes can be edited in two modes:
- **Markdown editor** — CodeMirror-based editor with syntax highlighting, YAML frontmatter support, and markdown language modes
- **Rich text editor** — BlockNote-based WYSIWYG editor with support for code blocks, KaTeX equations, Mermaid diagrams, and other block types

Users can switch editors per-note.

**Source**: package.json dependencies on @codemirror/*and @blocknote/*

### Markdown Rendering with Extensions

The application renders markdown with GitHub Flavored Markdown (GFM) extensions, code highlighting, and custom block types (Mermaid diagrams, KaTeX math, embeds).

**Source**: package.json dependencies on remark-gfm, rehype-highlight, mermaid, katex

## Technical Architecture

### Three-Layer Data Representation

Tolaria maintains three synchronized representations of vault data:

1. **Filesystem** — `.md` files on disk (source of truth)
   - Each note is a standalone markdown file with optional YAML frontmatter
   - Directory structure reflects vault organization

2. **Cache** — `~/.laputa/cache/<hash>.json` (fast startup index)
   - Reconstructible from filesystem
   - Built during vault opening via `scan_vault_cached()`
   - Deleted when vault is reloaded to ensure freshness

3. **React State** — In-memory `VaultEntry[]` (session runtime)
   - Derived from cache on app load
   - Updated as user makes changes
   - Always written to filesystem first; disk write confirms before state update

**Invariant**: The filesystem is the single source of truth. If state diverges (external file edit, crash, race condition), running "Reload Vault" (Cmd+K) invalidates the cache and performs a full filesystem rescan, replacing React state with fresh data.

**Source**: ARCHITECTURE.md "Three representations, one authority"

### Data Flow and Write Semantics

```
User Action (edit/create/rename)
    ↓
Tauri IPC Command (save_note_content, update_frontmatter, etc.)
    ↓
Rust Backend (write to filesystem)
    ↓
Confirmation → React State Update (optimistic or reactive)
    ↓
File Watcher notifies of external changes
    ↓
refreshPulledVaultState() updates React components
```

All vault mutations flow through Tauri Rust commands. React never directly modifies files.

**Source**: ARCHITECTURE.md ownership rules

### Ownership Boundaries

| Layer | Owner | Writes to | Reads from |
|-------|-------|-----------|------------|
| Filesystem | Tauri Rust commands (save_note_content, update_frontmatter, etc.) | Disk `.md` files | — |
| Cache | `scan_vault_cached()` in vault/cache.rs | `~/.laputa/cache/` directory | Filesystem + git diff |
| React State | `useVaultLoader`, `useEntryActions`, `useNoteActions` hooks | In-memory `entries` | Cache (on load), filesystem (on reload) |

**Source**: ARCHITECTURE.md

### External Change Detection

A native file watcher runs through `start_vault_watcher` / `stop_vault_watcher` (Rust `notify` crate):
- Monitors active vault for external changes
- Ignores churn from `.git/`, `node_modules/`, temp files, and `.tolaria-rename-txn`
- Emits `vault-changed` events
- `useVaultWatcher` batches events, suppresses recent app-owned saves, and refreshes UI for remaining changes
- Status bar displays reload spinner during external updates

**Source**: ARCHITECTURE.md "External Change Detection"

### Progressive Vault Loading

Vault opening renders the main app shell while full entry scanning completes asynchronously:
- `useVaultLoader` keeps `isLoading` true until entries are ready
- Folders and saved views load independently, making sidebar useful before full note index completes
- Command palette and editor remain mounted (not hidden behind full-app skeleton)
- Full skeleton is reserved for app-level capability checks (initial Git state probe)

**Source**: ARCHITECTURE.md "Progressive Vault Loading"

### Tech Stack

**Frontend**:
- **React** (19.2.0) — UI framework
- **TypeScript** (5.9.3) — Type safety
- **Tailwind CSS** (4.1.18) — Utility CSS
- **Vite** (7.3.1) — Build tool
- **CodeMirror 6** — Markdown editor with syntax highlighting
- **BlockNote** (0.46.2) — Rich text editor with block-based editing
- **Mantine** (8.3.14) — UI component library
- **Radix UI** — Headless UI primitives (dropdown, dialog, tooltip, tabs, select)
- **React Markdown** + remark-gfm — Markdown rendering with GFM extensions

**Desktop Framework**:
- **Tauri 2** (2.10.0) — Cross-platform desktop runtime (Rust backend + Typescript frontend)
- **Tauri plugins** — dialog, process, updater, opener, prevent-default

**Backend (Rust)**:
- **tokio** (async runtime with multi-threading)
- **notify** (file watching for external vault changes)
- **gray_matter** (YAML frontmatter parsing)
- **walkdir** (filesystem traversal)
- **serde_json** + **serde_yaml** (serialization)
- **regex** + **chrono** (pattern matching and dates)

**AI Integration**:
- **@anthropic-ai/sdk** (0.78.0) — Claude API for generative features
- **@modelcontextprotocol/sdk** (1.0.0) — MCP server for agent tooling

**Development & Testing**:
- **Vitest** — Unit testing framework
- **Playwright** (1.58.2) — End-to-end testing with smoke and regression suites
- **ESLint** + **TypeScript ESLint** — Linting
- **Husky** — Git hooks
- **PostHog** (1.363.5) — Analytics (opt-in)

**Localization**:
- **@translated/lara-cli** — Translation management

**Source**: package.json and src-tauri/Cargo.toml

### MCP Server Integration

Tolaria bundles an MCP (Model Context Protocol) server for AI agents:

**MCP Server Package**:
- **Location**: `/mcp-server/` directory
- **Implementation**: Node.js with @modelcontextprotocol/sdk (1.0.0)
- **Gray Matter** (4.0.3) — Parses markdown with YAML frontmatter in MCP tools
- **WebSocket** (8.19.0) — Transport layer

The MCP server exposes tools for reading, searching, and modifying vault notes. AI agents running Claude Code, Codex CLI, or Gemini CLI can invoke these tools to query the vault structure and update notes.

**Source**: mcp-server/package.json

### Rust Backend Architecture

The Rust backend (src-tauri/) handles:
- File system operations (read, write, delete)
- Git integration (history, status, operations)
- Vault scanning and caching
- File watching and change detection
- YAML frontmatter parsing and validation
- Tauri IPC command routing

**Runtime features**:
- Multi-threaded async (tokio)
- Full filesystem access without sandboxing constraints (Tauri 2 allowlist)
- Error handling with Sentry integration for crash reporting

**Source**: src-tauri/Cargo.toml

## Installation & Usage

### Desktop Installation

**Via Homebrew (macOS)**:
```bash
brew install --cask tolaria
```

**Download from releases**:
- Visit [https://refactoringhq.github.io/tolaria/download/](https://refactoringhq.github.io/tolaria/download/)
- Download for macOS, Windows, or Linux
- Run the installer

**Source**: README.md lines 40-46

### Getting Started

On first launch, users can optionally clone the [getting started vault](https://github.com/refactoringhq/tolaria-getting-started), which provides a walkthrough of the app's features.

**Source**: README.md line 50

### Local Development Setup

**Prerequisites**:
- Node.js 20 or later
- pnpm 8 or later
- Rust (stable channel, 1.77.2 or later)
- macOS or Linux for development (Windows development not yet documented)

**Linux system dependencies** (Tauri 2 requires WebKit2GTK and GTK):

For Arch/Manjaro:
```bash
sudo pacman -S --needed webkit2gtk-4.1 base-devel curl wget file openssl \
  appmenu-gtk-module libappindicator-gtk3 librsvg
```

For Debian/Ubuntu 22.04+:
```bash
sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget file \
  libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev \
  libsoup-3.0-dev patchelf
```

For Fedora 38+:
```bash
sudo dnf install webkit2gtk4.1-devel openssl-devel curl wget file \
  libappindicator-gtk3-devel librsvg2-devel
```

**Source**: README.md lines 62-82

### Development Workflow

```bash
# Install dependencies
pnpm install

# Run browser-based mock mode (for testing UI without desktop runtime)
pnpm dev
# Opens http://localhost:5173

# Run native desktop app with hot reload
pnpm tauri dev
```

**Testing**:
```bash
# Unit and integration tests (Vitest)
pnpm test
pnpm test:watch

# End-to-end tests (Playwright)
pnpm test:e2e
pnpm playwright:smoke
pnpm playwright:regression

# Test coverage
pnpm test:coverage
```

**Build for production**:
```bash
pnpm build        # TypeScript check + Vite build
pnpm tauri build  # Full desktop app binary
```

**Source**: README.md lines 89-97

### Bundled MCP Server

The MCP server is bundled with the Tauri app for AI agent integration. It is started automatically when Tolaria launches.

```bash
# For standalone MCP server development
cd mcp-server
npm start
npm test
```

**Source**: mcp-server/package.json

## Relevance to Claude Code Development

Tolaria directly addresses three key AI development challenges:

### 1. Structured Context for AI Agents

Tolaria vaults are designed as knowledge graphs with legible structure for AI systems. The combination of:
- YAML frontmatter for semantic metadata
- WikiLink syntax for relationship declarations
- MCP tooling for agent queries

...enables AI agents (Claude Code, Codex CLI, Gemini CLI) to navigate and reason about vault contents without custom per-vault instructions. This is particularly valuable for developing autonomous agents that need persistent, evolving context.

**Source**: README.md line 30, ARCHITECTURE.md "AI-first knowledge graph"

### 2. Plain-Text Knowledge Base Compatibility

Tolaria vaults are plain markdown files with git history. This makes them compatible with:
- Standard code review workflows (git diffs are human-readable)
- Version control systems (no special database or lock files)
- Text-based AI processing (no proprietary parsing required)
- Integration with coding agents that operate on text files

Claude Code agents can directly read, modify, and version control Tolaria notes as part of broader development workflows.

**Source**: README.md lines 24-25

### 3. Offline-First, Portable Knowledge Graph

For agents operating in restricted environments or on local machines, Tolaria's offline-first design ensures:
- No cloud dependency for agent context
- Works with air-gapped or private networks
- Full version history available locally
- No subscription or service continuity risk

This is critical for developing agents that manage long-term project memory and knowledge that must persist across platform changes.

**Source**: README.md line 26

### 4. Convention-Based Agent Guidance

Tolaria's AGENTS.md support allows vault authors to define agent instructions once and have all AI tools (Claude Code, Codex, Gemini) follow them automatically. This eliminates per-tool prompt customization for AI context management.

**Source**: README.md line 30, CLAUDE.md

## Limitations and Caveats

### 1. Early-Stage Software (v0.1.0)

Tolaria is at alpha stage (v0.1.0, released May 2, 2026). The application is not yet production-hardened. Breaking changes to vault format, data structures, or file schemas are possible before v1.0.

**Confidence**: high (source: version number in package.json)

### 2. No Windows Development Setup Documentation

README states "macOS or Linux for development," implying Windows development is not yet supported or documented. Users on Windows can run the prebuilt app but cannot contribute code or build locally.

**Confidence**: high (source: README.md line 61)

### 3. Limited UI Customization

The application enforces a four-panel layout and keyboard-first interaction model. UI customization (layout, panel ordering, theme colors beyond system preferences) is not documented as available. Power users seeking highly custom UIs may find limitations.

**Confidence**: medium (not explicitly stated in docs; inferred from architecture focus on conventions)

### 4. MCP Server Scope Not Fully Documented

The MCP server reference in package.json and AGENTS.md indicates AI tooling support, but the full set of available MCP tools, parameters, and examples are not documented in the retrieved sources. Developers would need to inspect mcp-server source code to understand available operations.

**Confidence**: medium (tool availability confirmed in code, full API not yet in public docs)

### 5. No Sync Across Devices

Tolaria does not provide built-in device sync. Users must manage sync themselves via git (push to remote, pull on another device). This is intentional (zero lock-in design) but requires manual git operations or external tools (GitHub Actions, Syncthing).

**Confidence**: high (stated in architecture as "Git-first" but not automatic sync)

### 6. Types Are Suggestions, Not Enforcement

The type system is explicitly non-enforcing (no validation, no required fields). This provides flexibility but can lead to inconsistent vault structure if not self-discipline. Organizations using Tolaria would need to establish and maintain conventions via team documentation.

**Confidence**: high (source: README.md line 29, "Types as lenses, not schemas")

## References

- README.md — <https://github.com/refactoringhq/tolaria/blob/main/README.md> (accessed 2026-05-02)
- ARCHITECTURE.md — <https://github.com/refactoringhq/tolaria/blob/main/docs/ARCHITECTURE.md> (accessed 2026-05-02)
- package.json — <https://github.com/refactoringhq/tolaria/blob/main/package.json> (accessed 2026-05-02)
- src-tauri/Cargo.toml — <https://github.com/refactoringhq/tolaria/blob/main/src-tauri/Cargo.toml> (accessed 2026-05-02)
- mcp-server/package.json — <https://github.com/refactoringhq/tolaria/blob/main/mcp-server/package.json> (accessed 2026-05-02)
- CONTRIBUTING.md — <https://github.com/refactoringhq/tolaria/blob/main/CONTRIBUTING.md> (accessed 2026-05-02)
- Repository — <https://github.com/refactoringhq/tolaria> (accessed 2026-05-02)

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Docs MCP Server](../mcp-ecosystem/docs-mcp-server.md) | mcp-ecosystem | alternative MCP-based knowledge system designed for AI agent queries |
| [Samuraizer](../ai-research-tools/samuraizer.md) | ai-research-tools | shares knowledge base + semantic search + AI-powered summarization pattern |
| [Screenpipe](../mcp-ecosystem/screenpipe.md) | mcp-ecosystem | parallel local-first Tauri + MCP server architecture for capturing and organizing context |
| [Claude Brain](../context-management/claude-brain.md) | context-management | complements Tolaria by providing persistent memory injection for Claude Code sessions |

---

## Freshness Tracking

| Section | Confidence | Last Verified | Next Review |
|---------|------------|---------------|------------|
| Identity/Metadata | high | 2026-05-02 | 2026-08-02 |
| Problem Addressed | high | 2026-05-02 | 2026-08-02 |
| Key Statistics | medium | 2026-05-02 | 2026-06-02 |
| Key Features | high | 2026-05-02 | 2026-08-02 |
| Technical Architecture | high | 2026-05-02 | 2026-08-02 |
| Installation & Usage | high | 2026-05-02 | 2026-08-02 |
| Relevance to Claude Code | high | 2026-05-02 | 2026-08-02 |
| Limitations | high | 2026-05-02 | 2026-08-02 |

**Confidence rationale**:
- **High**: Extracted directly from official documentation (README, ARCHITECTURE, source files), version-controlled repository, recent commits
- **Medium**: Star count not yet available (repo too new), MCP API details not in public docs (requires source inspection)

**Next review trigger**: Breaking changes to vault format, v1.0 release, major feature additions documented on GitHub, or query from user.
