# Stoat

**Research Date**: 2026-03-18
**Source URL**: <https://github.com/jxdones/stoat>
**GitHub Repository**: <https://github.com/jxdones/stoat>
**Version at Research**: v0.9.0
**License**: MIT License

---

## Overview

Stoat is a keyboard-driven terminal user interface (TUI) database client built in Go using the Bubbletea framework. It bridges the gap between basic command-line database clients and heavyweight GUI applications, providing an efficient, vim-keybinding-compatible interface for developers who work primarily in terminal environments. The project's stated philosophy is to serve as "the database client for people who don't leave the terminal."

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Context-switching between terminals and GUI database tools | Provides a full-featured database interface within the terminal using vim-style keyboard navigation |
| Need to memorize special database CLI commands | Dedicated UI tabs for schema exploration (columns, indexes, constraints) without requiring special syntax |
| Inefficient data inspection workflows | Direct cell editing, row deletion, and client-side filtering with keyboard shortcuts |
| Terminal-based development in restricted/remote environments | Works seamlessly in SSH sessions and minimal environments without GUI dependencies |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 17 | 2026-03-18 |
| GitHub Forks | 2 | 2026-03-18 |
| Contributors | 1 | 2026-03-18 |
| Latest Release | v0.9.0 | 2026-03-18 |
| Open Issues | 1 | 2026-03-18 |
| Primary Language | Go | 2026-03-18 |
| Repository Created | 2026-02-19 | 2026-03-18 |

---

## Key Features

### Navigation & User Interface

- **Vim-style keyboard controls**: hjkl navigation, gg/G jumps, count prefixes for efficient navigation without mouse dependencies
- **Multi-tab schema exploration**: Dedicated tabs for viewing columns, indexes, constraints, and relationships
- **Records view**: Browse database rows with support for pagination (Ctrl+N/B for next/previous pages)
- **Inline cell editing**: Modify cell values with Enter to confirm or Esc to cancel
- **Row deletion**: Press `dd` to delete rows with confirmation prompt; blocked in read-only mode and when viewing query results

### Query & Scripting

- **Inline query box**: Ad-hoc SQL execution within the TUI
- **External editor integration**: Press Ctrl+E to launch external editor for multi-line SQL queries
- **Saved query snippets**: Store frequently-used queries per connection in configuration
- **SQL syntax highlighting**: Keywords, strings, numbers, comments, and operators are color-coded according to active theme

### Data Management

- **Client-side filtering**: Filter loaded rows without rewriting queries
- **Clipboard support**: Copy cell values to clipboard for external use
- **Read-only mode enforcement**: Enforced at both the database connection level and UI level for secure production database access
- **Pagination support**: Navigate large result sets with keyboard controls

### Customization

- **11 built-in themes**: default, dracula, solarized, catppuccin, everforest, gruvbox, one-dark, rose-pine, princess, one-shell, blueish
- **Per-theme syntax colors**: Each theme defines `SyntaxKeyword`, `SyntaxString`, `SyntaxNumber`, `SyntaxComment`, `SyntaxOperator` colors
- **Per-theme sidebar colors**: Explicit `SidebarSelectedBg` and `SidebarSelectedFg` fields for active item highlighting
- **Configuration via YAML**: Settings stored in `~/.stoat/config.yaml` including connection definitions and per-connection read-only settings

---

## Technical Architecture

Stoat implements a classic TUI architecture using Go's Bubbletea framework, which is based on The Elm Architecture pattern (Model-Update-View).

**Core Components**:

- **Database drivers**: Support for SQLite and PostgreSQL via native Go drivers with extensibility for planned MariaDB support
- **TUI rendering engine**: Bubbletea handles terminal rendering, input processing, and state management
- **Query executor**: SQL execution layer that abstracts database-specific syntax while supporting raw SQL pass-through
- **Theme system**: Modular color definitions applied at render time, enabling runtime theme switching without restart

**Data Flow**:

1. User input captured via Bubbletea's input handling → Update function processes commands
2. State modifications trigger re-render via Bubbletea's View function
3. Database queries execute asynchronously with results cached for client-side operations (filtering, pagination)
4. Configuration loaded from YAML at startup; connection definitions include credentials and read-only flags

**Key Design Decisions**:

- **Client-side filtering**: Avoids repeated database queries during interactive filtering; trades memory for responsiveness
- **Confirmation workflows**: Row deletion and critical operations require confirmation to prevent accidental data loss
- **Vim keybindings as primary**: Leverages existing muscle memory for developers already using vim; arrow keys supported as fallback
- **Theme-aware syntax highlighting**: Each theme independently defines syntax colors, preventing theme-color conflicts

---

## Installation & Usage

### Installation Methods

```bash
# Via curl (recommended)
curl -sSL https://raw.githubusercontent.com/jxdones/stoat/main/install.sh | bash

# Via Homebrew (macOS)
brew install jxdones/tap/stoat

# Via Go
go install github.com/jxdones/stoat@latest

# From source
git clone https://github.com/jxdones/stoat.git
cd stoat
go build
```

### Configuration

Create `~/.stoat/config.yaml`:

```yaml
theme: dracula  # or: default, solarized, catppuccin, everforest, gruvbox, one-dark, rose-pine, princess, one-shell, blueish

connections:
  - name: local_sqlite
    type: sqlite
    path: ./data.db

  - name: prod_postgres
    type: postgres
    host: db.example.com
    port: 5432
    user: dbuser
    password: secret
    database: myapp
    read_only: true  # Enforce read-only mode for production
```

### Basic Usage

```bash
# Launch Stoat
stoat

# Navigate databases and tables using hjkl
# gg = jump to top, G = jump to bottom, count+k/j = jump N rows

# Execute query: Click query box or type in Records view
# Edit cell: Press Enter on a cell, edit value, press Enter to save or Esc to cancel

# Delete row: Position on row, press dd, then y to confirm

# Filtering: Type filter query (operates on loaded rows, doesn't re-query database)

# Copy to clipboard: Select cell, press c
```

---

## Relevance to Claude Code Development

### Applications

- **Terminal-first agent workflows**: Agents operating in minimal or SSH-only environments can inspect databases without context-switching to GUI tools
- **Development and testing**: Database inspection during agent task execution (e.g., verifying data after migrations, checking query results)
- **Example for TUI patterns**: Stoat demonstrates effective vim-keybinding integration and Bubbletea framework patterns applicable to other terminal tools

### Patterns Worth Adopting

- **Confirmation workflows for destructive operations**: The row deletion confirmation pattern is replicable for any CLI tool requiring data mutation safeguards
- **Read-only mode enforcement**: The dual-layer approach (database-level and UI-level read-only flags) is a model for production-safe tooling
- **Theme-aware syntax highlighting**: Per-theme color definitions enable consistent styling across different color schemes without hardcoding
- **Configuration via structured YAML**: The `~/.stoat/config.yaml` approach is more maintainable than environment variables for multi-connection scenarios

### Integration Opportunities

- **Agent context injection**: Agents could load Stoat connection configs to introspect databases during task execution
- **Query snippet library**: Stoat's saved query feature could be extended to share common queries across teams
- **Extensible database support**: The modular driver architecture enables adding database types without core changes

---

## References

- [Stoat GitHub Repository](https://github.com/jxdones/stoat) (accessed 2026-03-18)
- [Bubbletea Framework Documentation](https://github.com/charmbracelet/bubbletea) (accessed 2026-03-18)
- Stoat v0.9.0 Release Notes via GitHub API (accessed 2026-03-18)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Sidecar](./sidecar.md) | developer-tools | Go/Bubbletea TUI tool for agent workflow visibility |
| [Agent Deck](./agent-deck.md) | developer-tools | Go/Bubbletea terminal session manager with keyboard-driven navigation |
| [Dolt](../data-infrastructure/dolt.md) | data-infrastructure | Version-controlled SQL database queryable via Stoat's database client interface |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-18 |
| Version at Verification | v0.9.0 |
| Next Review Recommended | 2026-06-18 |
| Confidence Map | Overview: high (GitHub README + release notes) \| Features: high (official docs) \| Architecture: medium (inferred from feature design) \| Usage: high (verified installation methods) \| Statistics: high (GitHub API) |
