---
title: Tabularis — A Database Client for Developers
resource: Tabularis
homepage: https://tabularis.dev
github: https://github.com/debba/tabularis
license: Apache License 2.0
created: 2026-04-11
version: 0.9.15
---

# Tabularis — A Database Client for Developers

## Overview

Tabularis is a lightweight, cross-platform database client for developers built with Tauri and React. It provides a desktop application for MySQL/MariaDB, PostgreSQL, and SQLite with advanced features including SQL notebooks, visual query builders, and built-in MCP (Model Context Protocol) server integration for AI agent access.

**Key Identity:**
- **Name**: Tabularis
- **Latest Version**: 0.9.15 (released 2026-04-08)
- **Repository**: <https://github.com/debba/tabularis>
- **License**: Apache License 2.0
- **Homepage**: <https://tabularis.dev>
- **Language**: TypeScript (frontend), Rust (backend)
- **Platform**: Windows, macOS, Linux (AppImage, Snap, AUR, .deb, .rpm)
- **Stars**: 1,053 (as of 2026-04-11)
- **Forks**: 68
- **Active Development**: Yes (latest commit 2026-04-10)

**Origin Story**: "This project began as an AI-assisted development experiment, exploring how far intelligent agents could accelerate building a fully functional tool from scratch."

## Problem Addressed

Tabularis targets developers who need a lightweight, fast database client without heavyweight features. The problem statement addresses:

1. **Heavy GUI complexity** — Commercial tools have bloated interfaces
2. **Security concerns** — Need for local password storage and SSH tunneling without cloud
3. **AI integration gap** — Existing database clients lack modern AI workflow integration
4. **Cross-platform friction** — Limited native clients for Windows, macOS, and Linux
5. **Development velocity** — Need fast database management for local and remote connections

## Key Statistics

- **1,053 GitHub stars** (as of 2026-04-11)
- **68 forks**
- **26 open issues**
- **Version 0.9.15** (released 2026-04-08) — pre-1.0, active development
- **Release Cadence**: ~1 release every 1-2 weeks
- **Supported Databases**: MySQL/MariaDB, PostgreSQL (multi-schema), SQLite
- **Localization**: English, Italian, Spanish, Chinese (Simplified)

## Key Features

### 1. Connection Management
- Multi-database support with collapsible sidebar nodes
- SSH tunneling with automatic readiness detection
- Secure password storage via system Keychain
- Connection profiles with save/clone/manage workflow
- Grid and list view modes with real-time search
- Branded driver icons (PostgreSQL, MySQL, SQLite)

### 2. Database Explorer
- Tree view for tables, columns, keys, indexes, views, stored routines
- Inline editing of table/column properties
- Interactive ER diagrams with Pan, Zoom, Layout controls
- Context actions: show data, count rows, modify schema, duplicate/delete
- SQL Dump & Import for backup/restore workflows
- Parallel metadata fetching for fast schema loading

### 3. SQL Editor
- Monaco Editor with syntax highlighting and auto-completion
- Tabbed interface with isolated connections per tab
- Split view for side-by-side database connections
- Multi-statement execution (Run All, Run Selected, Run Individual)
- Smart query splitting via `dbgate-query-splitter` (handles stored procedures, $$-delimited blocks)
- Multi-result tabs with close, rename, re-run context menu
- Saved queries persisted to disk
- AI assist overlay with floating action buttons

### 4. SQL Notebooks
- Multi-cell workspace combining SQL and Markdown
- Inline results and charts (bar, line, pie via Recharts)
- Cross-cell variable references: `{{cellName.columnName}}`
- Global parameters: `{{$paramName}}`
- Sequential run-all with stop-on-error and completion summary
- Auto-run dependencies before query execution
- Drag-and-drop cell reordering, collapse/expand controls
- AI-generated cell names (individual or batch)
- Export to `.tabularis-notebook`, HTML, CSV, JSON
- Outline panel for notebook structure navigation

### 5. Visual Query Builder
- Drag-and-drop query building with ReactFlow
- Visual JOIN creation between tables
- WHERE/HAVING filters, aggregates (COUNT, SUM, AVG), sorting, limits
- Real-time SQL code generation

### 6. Data Grid
- Inline and batch cell editing with optimistic updates
- Row creation, deletion, multi-select
- Copy selected rows to clipboard
- Export to CSV or JSON
- Read-only mode for aggregates, edit mode for tables
- MySQL GEOMETRY support (initial) with spatial data inputs

### 7. Keyboard Shortcuts
- Built-in shortcuts: `Ctrl+B` toggle sidebar, `Ctrl+T` new tab, `Ctrl+→/←` paginate
- Fully customizable from Settings with visual recording
- Platform-aware (`Cmd` on macOS, `Ctrl` on Windows/Linux)
- Visual hints: `Ctrl+Shift` reveals numbered badges (1–9) for connection switching
- Persistent overrides in `keybindings.json`

### 8. Plugin System
- **JSON-RPC 2.0 over stdin/stdout** — language-agnostic extensibility
- **Install without restart** — browse and install from Settings → Available Plugins
- **Any database support** — add DuckDB, MongoDB, or custom databases via plugins
- **Capability declaration** — readonly mode, table management, UI extensions
- **Plugin registry** in `plugins/registry.json`
- **Developer guide** in `plugins/PLUGIN_GUIDE.md`

### 9. Logging & Debugging
- Real-time log viewing in Settings
- Level filtering (DEBUG, INFO, WARN, ERROR)
- In-memory buffer with configurable retention
- Query expansion in logs
- Export logs to `.log` files
- CLI debug mode: `tabularis --debug` for verbose logging

### 10. MCP Server Integration
Built-in MCP (Model Context Protocol) server for AI agent access.

**Supported Clients**: Claude Desktop, Cursor, Windsurf

**Available Tools**:
- `list_connections` — List all saved database connections
- `list_tables` — List tables with optional schema filter
- `describe_table` — Full schema (columns, indexes, foreign keys)
- `run_query` — Execute any SQL query and return results

**Setup**: Settings → MCP Server Integration (one-click), or manual JSON config

## Technical Architecture

### Frontend Stack
- **React 19.2.4** with TypeScript 5.9.3
- **Tailwind CSS v4.2.2** with PostCSS
- **Monaco Editor** for SQL syntax and auto-completion
- **TanStack React Table v8.21.3** with virtualization
- **Recharts v3.8.1** for charts
- **ReactFlow v12.10.2** + Dagre v0.8.5 for ER diagrams
- **React Router v7.13.2**
- **i18next v25.10.10** with browser language detection
- **Vite v7.3.1** build tool
- **Vitest v4.1.2** with Testing Library

### Backend Stack (Rust)
- **Tauri v2.10.2** — desktop framework with OS integration
- **SQLx v0.8.6** — async SQL with compile-time checking (SQLite, MySQL, PostgreSQL)
- **Tokio v1.49.0** — async runtime
- **Russh v0.43** — pure-Rust SSH client
- **Keyring v3.6.3** — system keychain integration
- **Serde v1.0** — JSON/YAML serialization
- **Clap v4.5.56** — CLI argument parsing

**Core Model**: `Driver` (pluggable database driver) → `Connection` (to database) → `Query` (SQL execution). Drivers implement JSON-RPC plugin interface. Backend uses async/await for all I/O with connection pooling.

### Configuration Storage
- **Linux**: `~/.config/tabularis/`
- **macOS**: `~/Library/Application Support/tabularis/`
- **Windows**: `%APPDATA%\tabularis\`

Files:
- `connections.json` — Connection profiles
- `saved_queries.json` — Saved SQL queries
- `config.json` — App settings
- `keybindings.json` — Keyboard overrides
- `preferences/{connectionId}/preferences.json` — Per-connection editor state
- `themes/` — Custom themes
- `.tabularis-notebook` — Notebook files (auto-saved)

### Extension Points
1. **Plugin System** — JSON-RPC 2.0 driver interface
2. **UI Extensions** — Custom React components via plugins
3. **AI Integration** — MCP server for agent access
4. **Themes** — Custom theme files
5. **Keyboard Shortcuts** — User-customizable bindings

## Installation & Usage

### Windows
```bash
winget install Debba.Tabularis
```
Or download from Releases: `tabularis_0.9.15_x64-setup.exe`

### macOS
```bash
brew tap debba/tabularis
brew install --cask tabularis
```

### Linux (Snap)
```bash
sudo snap install tabularis
```

### Linux (AppImage)
```bash
chmod +x tabularis_0.9.15_amd64.AppImage
./tabularis_0.9.15_amd64.AppImage
```

### Linux (AUR)
```bash
yay -S tabularis-bin
```

### Basic Workflow
1. Settings → Connections → Add connection
2. Click connection in sidebar to connect
3. SQL Editor: Ctrl+T → write SQL → Ctrl+Enter to run
4. Results display in tabs with pagination, export, edit
5. Notebooks: Notebooks → New → Add SQL/Markdown cells → Run

### Advanced Features

**SSH Tunneling**: Connection settings → SSH tab → Enable → Enter host/port/auth

**MCP Setup**: Settings → MCP Server Integration → Configure

**Plugin Install**: Settings → Available Plugins → Install → No restart required

## Relevance to Claude Code Development

### 1. Database Integration for Agents
The MCP server enables agents to:
- Query schema dynamically from live databases
- Execute exploratory queries to understand relationships
- Generate and test SQL without manual round-trips
- Validate database changes during development

**Use Case**: Agent implementing data migrations can introspect schema, write migration SQL, execute, and verify results in real-time.

### 2. Extensibility via Plugins
Plugin architecture shows how to extend apps via external executables:
- **JSON-RPC 2.0 over stdio** is language-agnostic
- **No restart required** — plugins discovered dynamically
- **Capability declaration** — plugins declare features

**Relevance**: Pattern applicable to Claude Code agent extensibility — spawn external tools that communicate via JSON-RPC.

### 3. AI-Assisted Development Model
Built "as an AI-assisted development experiment" showing:
- How agents can accelerate full-stack development
- Integration of AI features (cell naming, query assist)
- User-facing AI integration (not just agent-facing)

**Relevance**: Demonstrates shipping user-facing AI features alongside agent integration.

## Limitations and Caveats

1. **Pre-1.0 Release**: v0.9.15 is early-stage; API and features may change. Breaking changes noted in CHANGELOG.

2. **Limited Database Support**: Only MySQL/MariaDB, PostgreSQL, SQLite built-in. Other databases require plugins. Plugin ecosystem is emerging.

3. **Spatial Data Incomplete**: MySQL GEOMETRY is "initial" — requires raw SQL inputs; no visual editors.

4. **PostgreSQL Gap**: Roadmap item "Better PostgreSQL Support" not started — advanced features (arrays, JSON, window functions) may have gaps.

5. **No Team Collaboration**: Single-user desktop client; no multi-user or workspace sharing.

6. **No Query History**: Roadmap item "Query History" not implemented — only manually saved queries persist.

7. **Limited SQLite Support**: Roadmap item "Better SQLite Support" — may lack SQLite-specific features (JSON, FTS, extensions).

8. **MCP Setup Friction**: Requires one-click setup or manual config; no centralized registry.

9. **Performance Unknown**: No benchmarks for large tables (>100k rows), complex ER diagrams (>100 tables), or deep notebook dependencies.

10. **Linux Integration**: AppImage and Snap work, but native menu/tray features may be limited vs. Windows/macOS.

## References

- **Official Website**: <https://tabularis.dev> (accessed 2026-04-11)
- **GitHub Repository**: <https://github.com/debba/tabularis> (accessed 2026-04-11)
  - Stars: 1,053 | Forks: 68 | Open Issues: 26
  - Latest Commit: 2026-04-10 19:57:46 UTC
- **Discord**: <https://discord.gg/YrZPHAwMSG> (accessed 2026-04-11)
- **CHANGELOG**: <https://github.com/debba/tabularis/blob/main/CHANGELOG.md> (accessed 2026-04-11)
- **Plugin Guide**: <https://github.com/debba/tabularis/blob/main/plugins/PLUGIN_GUIDE.md> (accessed 2026-04-11)
- **Roadmap**: <https://github.com/debba/tabularis/blob/main/roadmap.json> (accessed 2026-04-11)
- **Documentation**: <https://tabularis.dev/wiki/> (accessed 2026-04-11)

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Stoat](./stoat.md) | developer-tools | Direct competitor — TUI database browser for SQLite and PostgreSQL with minimal footprint |
| [PocketBase](../data-infrastructure/pocketbase.md) | data-infrastructure | Shares embedded SQLite backend; PocketBase adds auth/subscriptions, Tabularis adds visual querying |
| [saga-mcp](../mcp-ecosystem/saga-mcp.md) | mcp-ecosystem | Both use SQLite as backing store and expose MCP interface for agent access |
| [composure](../agent-frameworks/composure.md) | agent-frameworks | Both integrate SQLite with MCP and support Claude Code integration |
| [Narsil MCP](../mcp-ecosystem/narsil-mcp.md) | mcp-ecosystem | Parallel MCP server approach; Narsil provides code intelligence tools where Tabularis provides database tools |
| [CodeGraphContext](../mcp-ecosystem/codegraphcontext.md) | mcp-ecosystem | Both provide CLI + MCP server dual modes for agent integration |
| [Yume](./yume.md) | developer-tools | Shares Tauri + Rust cross-platform desktop architecture; Yume focuses on multi-agent orchestration UI |
| [oh-my-opencode](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | Both demonstrate demand-scoped MCP integration pattern for AI agent-native tooling |

## Freshness Tracking

**Last Reviewed**: 2026-04-11

**Next Review**: 2026-07-11 (3 months)

**Confidence by Section**:
- **Identity & Metadata**: high — GitHub API, package.json, official site consistent
- **Key Features**: high — extracted from README and CHANGELOG
- **Technical Architecture**: high — dependencies verified from Cargo.toml, package.json; source inspected
- **Installation & Usage**: high — official methods verified
- **MCP Integration**: high — extracted from official README section
- **Limitations**: medium — from roadmap (documented, not speculative)
- **Relevance to Claude Code**: medium — analysis of architecture and MCP design

**Data Freshness**:
- Repository metadata: fresh (2026-04-11)
- Version: confirmed via GitHub Releases and package.json
- Features: current as of 2026-04-10 (latest commit)
- Roadmap: documented in roadmap.json
- Installation: verified against active releases
