# Tolaria

**Research Date**: 2026-04-26
**Source URL**: <https://github.com/refactoringhq/tolaria>
**GitHub Repository**: <https://github.com/refactoringhq/tolaria>
**Version at Research**: v0.1.0
**License**: AGPL-3.0-or-later

---

## Overview

Tolaria is a desktop application for macOS and Linux designed for managing markdown-based knowledge bases and second brains. Built with Tauri (Rust backend), React, and TypeScript, it provides a four-panel interface for organizing, searching, and collaborating on personal notes, company documentation, and AI agent context. The application emphasizes offline-first operation, git-based version control, and AI-readability through structured conventions.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Fragmented knowledge spread across tools and platforms | Unified vault of markdown files as source of truth; all data portable |
| Knowledge unavailable to AI agents and automation | Standard frontmatter conventions and MCP server integration expose vault structure to Claude Code, Cursor, and compatible clients |
| Vendor lock-in and data portability concerns | Files-first design: plain markdown with YAML frontmatter, no proprietary formats; zero cloud dependencies |
| Manual context switching and tab management | Four-panel layout (Sidebar, Note List, Editor, Inspector) with keyboard-first navigation and command palette |
| Difficulty tracking relationships between notes | Dynamic wikilink detection, relationship types, neighborhood view for exploring note graphs |
| Version history and collaboration coordination | Git-first architecture: every vault is a git repo with full commit history, push/pull sync, conflict resolution |
| Knowledge graphs not optimized for AI traversal | Convention-over-configuration approach: standard field names (`type:`, `status:`, `belongs_to:`, `related_to:`) signal meaning to both humans and agents without custom setup |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | Unknown (shallow clone did not fetch) | 2026-04-26 |
| Current Version | 0.1.0 | 2026-04-26 |
| Latest Commit | 694419d (fix: disable native text suggestions) | 2026-04-26 |
| License | AGPL-3.0-or-later | 2026-04-26 |
| Supported Platforms | macOS, Linux; iOS/iPadOS prototype documented | 2026-04-26 |

---

## Key Features

### Core Vault Management

- **Files-first architecture**: Vaults are folders of plain `.md` files with YAML frontmatter; no database or proprietary format
- **Git integration**: Every vault is a git repository with full version history, remote support (GitHub, GitLab, Gitea, self-hosted), and conflict resolution UI
- **Flat vault structure**: Notes live at vault root as `.md` files; type information stored in frontmatter (`type:` field), not folder location; `type/` folder reserved for type definition documents only
- **Crash-safe file operations**: Note renames use transactional staging in `.tolaria-rename-txn/` directory with recovery on next scan; folder moves and deletes update wikilinks atomically

### Editor and Note Content

- **BlockNote rich text editor** with markdown roundtrip guarantees: formatting toolbar exposes only operations that survive save/load cycles (bold, italic, strike, code, links); unsupported features (color, alignment, underline) are hidden
- **CodeMirror 6 raw editor** for markdown source editing with live frontmatter parsing
- **Wikilink support**: Type `[[` to open suggestion menu; links resolve by filename stem, alias, or title; namespace collisions resolved via priority ordering
- **Arrow ligature normalization**: ASCII sequences (`->`, `<->`) normalized consistently across rich and raw editor modes; escaped forms (`\\->`) remain literal
- **Markdown-safe formatting** via `blocksToMarkdownLossy()` → `postProcessWikilinks()` pipeline; all BlockNote structures map cleanly to CommonMark

### Search and Discovery

- **Keyword-based search** across vault files using `walkdir`-based scanning; no indexing step required
- **Title and content scoring**: Results ranked by relevance (title matches prioritized); snippets extracted around first match
- **Real-time results** with 300ms debounce as user types

### Relationship Navigation

- **Dynamic relationship detection**: Any frontmatter field containing `[[wikilinks]]` is treated as a relationship (no hardcoded field list)
- **Standard relationship vocabulary** (`belongs_to:`, `related_to:`, `has:`) stored in snake_case on disk, humanized in UI; custom field names preserve their original casing
- **Neighborhood mode**: Select an entity in the sidebar to explore outgoing relationships (grouped by type), inverse relationships, backlinks, and all connected notes in a single scrollable view
- **Backlink detection**: Scans vault for notes referencing the current note via wikilinks

### Type System

- **Flexible types without enforcement**: Entity types (`type:` frontmatter field) tag notes but do not restrict fields or validate structure; no required fields
- **Type documents** as navigable entities: `type/project.md`, `type/person.md` define type metadata (icon, color, sidebar order, template, sort, visibility, pinned properties)
- **Sidebar grouping** by type with per-type filtering, sorting, and visibility controls
- **Instance listing**: Viewing a type document shows all notes of that type (capped at 50, sorted by modified-at desc)

### AI Integration

#### MCP (Model Context Protocol) Server

- **14 built-in tools** for vault operations: `open_note`, `create_note`, `search_notes`, `edit_note_frontmatter`, `delete_note`, `link_notes`, `list_notes`, `vault_context`, `ui_*` controls
- **Multiple transports**: stdio for Claude Code/Cursor; WebSocket bridges (port 9710 tool bridge, port 9711 UI bridge) for real-time integration with app UI
- **Explicit registration**: User-initiated setup in status bar or command palette; writes server config to `~/.claude.json`, `~/.cursor/mcp.json`, or generic MCP config
- **Non-destructive config updates**: Additive upsert semantics; preserves other configured servers

#### AI Agent Integration

- **CLI agent support**: Claude Code (via `claude_cli.rs` adapter) and Codex (via `codex exec --json`) spawned as subprocesses with vault access
- **Streaming UI**: Reasoning blocks (collapsed on first text), tool action cards with results, full response reveal on completion
- **Context builder** (`ai-context.ts`): Structured JSON snapshot of active note, linked notes, open tabs, vault metadata; 60% of 180k token budget (~108k max)
- **File operation detection**: Captures tool inputs to detect vault writes, triggers vault reload to stay synchronized
- **Authentication**: Claude Code uses existing CLI login; Codex surfaces friendly prompt for `codex login`; no API keys stored in app settings

### Version Control and Sync

- **Auto-sync** with configurable interval; pulls on schedule, pushes after commits
- **Conflict resolution UI**: `ConflictResolverModal` for merge conflicts; inline `ConflictNoteBanner` in editor for conflicted notes with Keep mine / Keep theirs actions
- **Push-rejected recovery**: Detects divergence, sets pull-required status, offers one-click `pullAndPush()`
- **Local-only vaults**: Git-backed vaults without remote show neutral "No remote" chip in status bar; explicit "Add Remote" flow for later connection
- **Automatic checkpoints** (`useAutoGit`): Configurable idle/inactive thresholds; deterministic `Updated N note(s)` message; shares checkpoint runner with manual Commit button
- **Pulse view**: Git activity feed filtered by date, shows changed files with status icons, links to GitHub commits when `githubUrl` available; infinite-scroll pagination (20 commits per page)

### Vault Caching and Performance

- **Git-based incremental caching** in `~/.laputa/cache/<vault-hash>.json`:
  - Same commit → re-parse only uncommitted changes via `git status --porcelain`
  - Different commit → `git diff` to find changed files → selective re-parse
  - No cache → full `walkdir` scan
- **Three-layer data model**: Filesystem (source of truth) → Cache (fast startup index) → React state (in-memory session); cache is disposable and always reconstructible

### Settings and Customization

- **Per-vault UI settings**: zoom, view mode (all/editor-list/editor-only), editor mode (raw/preview), tag colors, status colors, property display modes, Inbox toggles
- **App-level settings**: auto-pull interval, AutoGit thresholds (idle/inactive), telemetry opt-in, crash reporting, analytics, release channel (stable/alpha), default AI agent, theme mode (light/dark)
- **Vault list management**: Multiple vaults persistent in `~/.config/com.tolaria.app/vaults.json`; vault switching resets sidebar and active note

### Multi-Window Support

- **Detached note windows**: Open notes in separate Tauri windows for focused editing
- **Triggers**: `Cmd+Shift+Click`, Command Palette "Open in New Window", `Cmd+Shift+O` keyboard shortcut
- **Secondary windows**: Editor-only layout, 800×700 initial sizing; same auto-save debounce and raw-editor frontmatter parsing as main window
- **Platform-specific chrome**: macOS native title bar; Linux uses React-rendered window chrome

### Getting Started and Onboarding

- **Welcome screen** on first launch: Create new vault, open existing folder, or clone public Getting Started starter vault
- **Starter vault clone**: Automatic repository seed (`refactoringhq/tolaria-getting-started`) with root guidance `AGENTS.md`, type scaffolding (`type.md`, `note.md`), and compatibility `CLAUDE.md` shim
- **Local-only by default**: Cloned starter vaults have all remotes removed; user connects to a remote later via explicit Add Remote flow
- **One-time AI agents onboarding**: Detects Claude Code and Codex availability; surfaces install links if missing; persists dismissal

### Telemetry and Updates

- **Optional telemetry**: Opt-in anonymous crash reporting (Sentry) and usage analytics (PostHog); both disabled by default
- **Path scrubber**: Vault content, note titles, file paths excluded from crash reports via `beforeSend` hook
- **In-app updater**: Tauri-backed automatic updates with progress bar; configurable release channel (stable/alpha)
- **Feature flags**: PostHog-backed feature rollout; Alpha channel always enabled; Stable channel respects PostHog rules; localStorage override for testing

---

## Technical Architecture

### System Overview

```
Tauri v2 Window (Desktop Shell)
├── React Frontend (TypeScript)
│   ├── App.tsx (state orchestrator)
│   ├── Sidebar (navigation, filters, type groups, folder tree)
│   ├── NoteList / PulseView (filtered list or activity feed)
│   ├── Editor (BlockNote + diff + raw modes)
│   ├── Inspector (metadata, relationships, git history OR AI panel)
│   ├── CommandPalette (Cmd+K launcher)
│   ├── SearchPanel (keyword results)
│   └── StatusBar (vault picker, sync status, version)
│
├── Rust Backend (Tauri Commands)
│   ├── vault/ (scanning, caching, parsing, rename, image save, migration)
│   ├── frontmatter/ (YAML read/write)
│   ├── git/ (commit, status, history, conflict, remote, pulse, clone)
│   ├── search.rs (keyword search)
│   ├── ai_agents.rs (CLI agent detection and stream normalization)
│   ├── claude_cli.rs (Claude Code subprocess spawning)
│   ├── mcp.rs (MCP server lifecycle and config registration)
│   ├── commands/ (Tauri command handlers)
│   └── settings.rs (app settings persistence)
│
└── External Services
    ├── Claude CLI / Codex CLI (agent subprocesses)
    ├── MCP Server (stdio + WebSocket bridges)
    ├── Git CLI (system executable)
    └── Git Remotes (GitHub/GitLab/Gitea/etc.)
```

**Source**: ARCHITECTURE.md lines 106-154 — System Overview diagram and description

### Three-Representation Data Model

1. **Filesystem** (`.md` files on disk): Single source of truth
2. **Cache** (`~/.laputa/cache/<hash>.json`): Git-based incremental index for fast startup
3. **React State** (`VaultEntry[]` in memory): Derived from cache or filesystem on session load

**Invariants**:
- Disk-first writes: All vault mutations write to disk via Tauri IPC before updating React state
- Optimistic UI with rollback: `persistOptimistic` updates state before disk confirmation, with failure callbacks that revert
- Recovery via reload: `Reload Vault` (Cmd+K) invalidates cache and full-rescans filesystem, replacing all state
- Cache is disposable: `reload_vault` command deletes cache before rescanning, guaranteeing fresh data

**Source**: ARCHITECTURE.md lines 44-84 — Three representations, one authority

### VaultEntry Data Model

```typescript
interface VaultEntry {
  path: string              // Relative to vault root
  filename: string          // Just the filename
  title: string             // First # heading → legacy title: → slug-to-title
  isA: string | null        // Entity type from frontmatter `type:` field
  aliases: string[]         // Alternative names for wikilink resolution
  belongsTo: string[]       // Parent relationships
  relatedTo: string[]       // Related entity links
  relationships: Record<string, string[]>  // All custom wikilink fields
  outgoingLinks: string[]   // All [[wikilinks]] in note body
  status: string | null     // Active, Done, Paused, Archived, Dropped
  modifiedAt: number | null // Unix timestamp
  createdAt: number | null  // Unix timestamp
  fileSize: number
  wordCount: number | null  // Body words only
  snippet: string | null    // First 200 chars of body
  archived: boolean
  properties: Record<string, string>  // Scalar frontmatter fields
}
```

**Source**: ABSTRACTIONS.md lines 114-136 — VaultEntry TypeScript definition

### Semantic Field Names (Convention over Configuration)

| Field | Meaning | UI Behavior |
|-------|---------|-------------|
| `type:` | Entity type (Project, Person, Quarter) | Type chip in note list + sidebar grouping |
| `status:` | Lifecycle stage (active, done, blocked) | Colored chip in note list + editor header |
| `icon:` | Per-note icon (emoji or Phosphor name) | Rendered on note title surfaces |
| `url:` | External link | Clickable link chip in editor header |
| `date:`, `start_date:`, `end_date:` | Single date or duration | Date badges in editor header |
| `goal:` + `result:` | Progress | Progress indicator in editor header |
| `Workspace:` | Vault context filter | Global workspace filter |
| `belongs_to:`, `related_to:`, `has:` | Relationship types | Relationship chip groups in Inspector |

Relationship fields detected dynamically — any field with `[[wikilinks]]` is treated as a relationship.

**Source**: ABSTRACTIONS.md lines 11-30 — Semantic Field Names table

### Git Integration

All git operations shell out to system `git` CLI (not libgit2). No git credentials or tokens stored in app settings; user's system git configuration handles authentication (SSH keys, Git Credential Manager, macOS Keychain, `gh auth`, etc.).

**Key Operations**:
- **Vault scanning**: `git log`, `git status --porcelain`, `git diff` for incremental caching and modified-file detection
- **Commits**: `git add -A && git commit`; broken signing helpers retry once unsigned for app-managed commits; user signing config honored for later commits
- **Push/Pull**: `git pull --rebase`, `git push`; clone commands run in blocking Tokio tasks so UI stays responsive during slow/failing network ops
- **Conflict resolution**: Detects conflicts, offers Keep mine / Keep theirs / manual resolution via `ConflictResolverModal`
- **Remote connection**: `git_add_remote` validates history compatibility, refuses ahead-of-local remotes, only enables tracking after safe push/fetch

**Source**: ARCHITECTURE.md lines 340-576 — Git Sync Flow and Remote Clone & Auth Model; ABSTRACTIONS.md lines 348-436 — Git Integration section

### MCP Server Architecture

```
MCP Server (Node.js) spawned by Tauri on startup
├── index.js (server entry)
├── vault.js (14 tools: find, read, create, search, edit, delete, link, list, context)
└── ws-bridge.js (WebSocket bridge)
    ├── port 9710 (tool bridge — AI clients call vault tools)
    └── port 9711 (UI bridge — Frontend listens for UI actions from MCP tools)
```

**Tool Surface** (14 tools):
- Note operations: `open_note`, `read_note`, `create_note`, `delete_note`, `append_to_note`
- Search and discovery: `search_notes`, `list_notes`, `vault_context`
- Metadata: `edit_note_frontmatter`, `link_notes`
- UI controls: `ui_open_note`, `ui_open_tab`, `ui_highlight`, `ui_set_filter`

**WebSocket Bridge Protocol**:
- Tool bridge (9710): `{ "id": "req-1", "tool": "search_notes", "args": { ... } }` → `{ "id": "req-1", "result": { ... } }`
- UI bridge (9711): Broadcasts `{ "type": "ui_action", "action": "open_note", "path": "..." }` to frontend

**Explicit external setup**: User initiates registration from status bar; writes to `~/.claude.json`, `~/.cursor/mcp.json`, or generic MCP config; non-destructive upsert preserves other servers.

**Source**: ARCHITECTURE.md lines 283-371 — MCP Server section; vault.js tool descriptions lines 287-304

### State Management

No Redux or global context. State lives in root `App.tsx` and custom hooks:

- `App.tsx`: Selection, panel widths, dialog visibility, toast, view mode
- `useVaultLoader`: Entries, allContent, modifiedFiles
- `useNoteActions`: Composes creation, rename, frontmatter ops
- `useTabManagement`: Navigation history, note switching
- `useVaultSwitcher`: Active vault path
- `useCliAiAgent`: Messages, status, tool actions
- `useAutoSync`: Sync interval, pull/push state
- `useCommitFlow`: Commit dialog state, shared checkpoint runner

Data flows unidirectionally: App passes data and callbacks as props to children. No child-to-child communication.

**Source**: ARCHITECTURE.md lines 742-768 — State Management section

### Multi-Window Implementation

Detached note windows created via `openNoteInNewWindow()` which creates a new `WebviewWindow` with query params (`?window=note&path=...&vault=...&title=...`). Secondary windows route to `NoteWindow.tsx` instead of `App.tsx` at boot.

**Source**: ARCHITECTURE.md lines 191-208 — Multi-Window (Note Windows) section

### Styling and Theme System

- **Global CSS variables** (`src/index.css`): Semantic app colors, borders, surfaces, interaction states; bridged to Tailwind v4 via `@theme inline`
- **Editor theme** (`src/theme.json`): BlockNote-specific typography; flattened to CSS vars by `useEditorTheme`; editor colors resolve through same semantic app variables
- **Theme runtime** (`useEditorTheme` hook): Applies `data-theme` and `.dark` class before React renders; localStorage mirror avoids startup flash when dark mode selected

Internal app-owned light and dark themes; not vault-authored. Theme mode is installation-local preference.

**Source**: ARCHITECTURE.md lines 409-416 — Styling section

---

## Installation & Usage

### Prerequisites

- Node.js 20+
- pnpm 8+
- Rust stable
- macOS or Linux (Windows support for remote agents via WSL documented but not primary target)

### Linux System Dependencies

```bash
# Arch/Manjaro
sudo pacman -S --needed webkit2gtk-4.1 base-devel curl wget file openssl \
  appmenu-gtk-module libappindicator-gtk3 librsvg

# Debian/Ubuntu 22.04+
sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget file \
  libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev \
  libsoup-3.0-dev patchelf

# Fedora 38+
sudo dnf install webkit2gtk4.1-devel openssl-devel curl wget file \
  libappindicator-gtk3-devel librsvg2-devel
```

Tauri 2 on Linux requires WebKit2GTK 4.1 and GTK 3. The bundled MCP server still spawns system `node` at runtime on Linux.

**Source**: README.md lines 51-70 — Linux system dependencies

### Quick Start

```bash
# Install dependencies
pnpm install

# Development mode
pnpm dev

# Browser-based mock mode (no Tauri)
# Open http://localhost:5173

# Native desktop app
pnpm tauri dev

# Production build
pnpm build
pnpm tauri build
```

**Download Release**:

Latest release available at: <https://github.com/refactoringhq/tolaria/releases/latest/download/Tolaria.app.tar.gz>

**Getting Started Vault** (on first launch):

Users are prompted to clone the public Getting Started starter vault from `refactoringhq/tolaria-getting-started`. This vault includes walkthrough content and type scaffolding.

**Source**: README.md lines 74-85 — Quick start; lines 35-38 — Getting started

### MCP Registration (External Tools)

Register Tolaria as an MCP server in your Claude Code config:

```bash
# Via command palette: Cmd+K → "Register Tolaria in Claude Code"
# Or via status bar → "MCP" chip → "Install"
```

This writes server config to `~/.claude.json` for Claude Code or `~/.cursor/mcp.json` for Cursor. Manual setup is possible via these JSON files, but Tolaria provides a one-click flow.

**Source**: ARCHITECTURE.md lines 315-320 — Explicit External Tool Setup

---

## Relevance to Claude Code Development

### Applications

1. **Vault as a Development Workspace**: Store project specifications, architectural decisions, design patterns, and implementation notes as a structured git-backed knowledge graph. Use type documents to define role types (Tech Lead, Developer, QA) and maintain relationships between specs, tasks, and PRs.

2. **AI Agent Context**: MCP integration allows Claude Code to read vault content directly, understand project context from type documents and relationships, and perform structured edits (create spec, link to feature, update status). No copy-paste needed.

3. **Knowledge Persistence Across Sessions**: Every vault is a git repo; work persists across Claude Code sessions and team members. Git sync enables collaborative documentation and conflict resolution.

4. **Convention-Driven AI Readability**: Standard field names and flat structure mean Claude Code understands vault layout without bespoke instructions. AI agents benefit from the same type system, relationship conventions, and semantic properties that humans use.

5. **Local-First Development Workflow**: Offline-first, zero cloud dependencies, no subscriptions. Works in air-gapped environments. Perfect for sensitive projects where leaving the machine is not an option.

6. **Integration Testing and Reproduction**: Store failing test cases, reproduction steps, and diagnostic notes in a vault. Link notes to PRs via GitHub integration. Use Tolaria's MCP to read test context during debugging.

### Patterns Worth Adopting

1. **Convention over Configuration**: Define standard field names (`type:`, `status:`, `belongs_to:`) that have well-defined UI behavior *by default*. Users never touch a config file unless they need custom extensions. This principle reduces onboarding friction for AI agents and human users alike.

2. **Dynamic Relationship Detection**: Don't hardcode relationship field names. Scan frontmatter for any field containing `[[wikilinks]]` and treat it as a relationship. Enables extensibility without code changes.

3. **Crash-Safe File Operations**: Use transactional staging directories (`.tolaria-rename-txn/`) and recovery helpers to ensure file operations complete or roll back cleanly. Protects data integrity when operations fail mid-way.

4. **Three-Representation Architecture**: Maintain filesystem (truth) → cache (fast) → memory (current) invariants. Make cache disposable via `Reload Vault` so state can always be recovered from disk. This separation of concerns makes recovery and consistency verification trivial.

5. **Filesystem as the Database**: Plain markdown with YAML frontmatter, no proprietary format. User can edit files with any editor, use git tools directly, backup to any cloud storage. Zero dependency on the app.

6. **AI System Integration via MCP**: Expose vault operations as a standardized MCP server (stdio + WebSocket), not just as a CLI. Allows multiple AI tools to integrate without tool-specific code paths.

7. **Keyboard-First UI for Power Users**: Minimize mouse interaction. Command palette (`Cmd+K`), keyboard-navigable sidebar, shortcut routing through shared `appCommandCatalog.ts`. AI-directed operations benefit from reproducible keyboard paths.

8. **Tauri + React for Desktop**: Rust backend handles file I/O and git operations safely; React frontend is responsive. Builds to single executable per platform. No Electron overhead; faster startup and lower memory.

### Integration Opportunities

1. **Claude Code MCP Integration**: Tolaria already exposes 14 tools via MCP. Claude Code could use these to:
   - Read architectural decision records (ADRs) before suggesting code changes
   - Query project dependencies and type definitions
   - Write new notes or update status when closing tasks
   - Search for similar patterns in past design decisions

2. **GitHub Integration**: Link Tolaria notes to GitHub PRs, issues, and commits. Current implementation detects `githubUrl` from git remotes; extended integration could:
   - Auto-create PR notes when PRs are opened
   - Sync PR review comments back to associated notes
   - Link merged commits to their design decision notes

3. **AI Skill Development**: Use Tolaria as a test environment for multi-agent orchestration. Store agent specifications as Type documents, log agent interactions as activity records, use the MCP server to coordinate agent handoffs.

4. **Documentation Site Generator**: Vault is already structured for AI readability. An MCP tool that generates static documentation (Markdown, HTML, or OpenAPI specs) from vault types and relationships would make Tolaria a documentation platform.

5. **Dependency Graph Visualization**: The relationship system is already a graph. Exposing the relationship graph via a web-based visualization (or Claude Code's own visualization tools) would help teams understand knowledge dependencies.

---

## References

- [Tolaria GitHub Repository](https://github.com/refactoringhq/tolaria) (accessed 2026-04-26)
- [README.md](https://github.com/refactoringhq/tolaria/blob/main/README.md) (accessed 2026-04-26)
- [ARCHITECTURE.md](https://github.com/refactoringhq/tolaria/blob/main/docs/ARCHITECTURE.md) (accessed 2026-04-26)
- [ABSTRACTIONS.md](https://github.com/refactoringhq/tolaria/blob/main/docs/ABSTRACTIONS.md) (accessed 2026-04-26)
- [package.json — Dependencies](https://github.com/refactoringhq/tolaria/blob/main/package.json) (accessed 2026-04-26)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Everything Claude Code](./everything-claude-code.md) | developer-tools | Comprehensive Claude Code harness system sharing MCP integration patterns and multi-agent orchestration with Tolaria |
| [Repomix](./repomix.md) | developer-tools | Transforms codebases into AI-friendly formats; feeds into Tolaria vaults as structured knowledge for agent context |
| [Claude Pilot](./claude-pilot.md) | developer-tools | Quality-enforcement layer for Claude Code; uses structured memory patterns that align with Tolaria's semantic field conventions |
| [Worktrunk](./worktrunk.md) | developer-tools | Rust git worktree CLI for parallel AI agent workflows; shares Tolaria's git-centric development model and multi-agent support |
| [Narsil MCP](../mcp-ecosystem/narsil-mcp.md) | mcp-ecosystem | Code intelligence MCP server with graph-based codebase analysis; complements Tolaria's MCP surface with specialized code querying |
| [CocoIndex Code](../mcp-ecosystem/cocoindex-code.md) | mcp-ecosystem | Embedded MCP server for semantic code search via AST and embeddings; alternative context provider working alongside Tolaria's vault tools |
| [MemPalace](../context-management/mempalace.md) | context-management | MCP server storing structured context with hierarchical metadata; parallels Tolaria's type system and relationship-driven organization |
| [SourceSync.ai](../context-management/sourcesyncai.md) | context-management | Managed RAG platform with auto-syncing connectors; complements Tolaria vaults for ingesting external knowledge sources with semantic preservation |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-04-26 |
| Version at Verification | 0.1.0 |
| Next Review Recommended | 2026-07-26 |
| Confidence Map | `Overview: high (doc-read)`, `Features: high (doc-read)`, `Architecture: high (doc + code-read)`, `Installation: high (doc-verified)`, `Relevance: medium (analyzed)` |

**Confidence Rationale**: All documentation claims derive from primary sources (README, ARCHITECTURE.md, ABSTRACTIONS.md, package.json). Architecture section includes code-level citations from ARCHITECTURE.md and ABSTRACTIONS.md. Statistics limited to version and git history (shallow clone did not fetch star count). Relevance section is analytical based on observed architecture and design patterns.
