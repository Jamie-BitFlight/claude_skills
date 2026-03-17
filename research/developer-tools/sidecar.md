# Sidecar

**Research Date**: 2026-03-17
**Source URL**: <https://marcus.github.io/sidecar/>
**GitHub Repository**: <https://github.com/marcus/sidecar>
**Version at Research**: v0.78.0
**License**: MIT

---

## Overview

Sidecar is a local-first terminal UI application written in Go that provides real-time visibility into AI agent activity without interrupting the development workflow. It displays git status, AI conversation history across multiple agent adapters, task management via TD, file browsing, and workspace management—designed to run alongside coding agents (Claude Code, Cursor, Gemini, Copilot, etc.) in split-terminal layouts.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Loss of visibility into AI agent actions during code generation | Real-time file changes, git diffs, and commit history visible in split-pane UI alongside agent output |
| Context window loss across AI agent sessions | Persistent conversation history browser supporting 10+ agent adapters (Claude Code, Cursor, Gemini CLI, Copilot CLI, Kiro, OpenCode, Pi Agent, Warp, Amp, Codex) with token usage tracking and search |
| Task context fragmentation across development sessions | Integration with TD task manager to track work, log progress, and maintain context across agent context windows |
| Manual workflow coordination (staging files, reviewing changes, managing branches) | Interactive git plugin with staged/unstaged file distinction, inline diff viewing, side-by-side diff mode, commit staging, and worktree switching |
| Switching between isolated project contexts | Project switcher (press `@`) supporting multiple configured projects with per-project state persistence; worktree switcher (press `W`) for git worktree isolation |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 843 | 2026-03-17 |
| GitHub Forks | 63 | 2026-03-17 |
| Contributors | 13 | 2026-03-17 |
| Latest Release | v0.78.0 | 2026-03-10 |
| Created | 2025-12-26 | 2026-03-17 |
| Last Pushed | 2026-03-10 | 2026-03-17 |

---

## Key Features

### Git Status Plugin

- View staged, modified, and untracked files in a split-pane interface with syntax-highlighted diffs
- Stage/unstage files with single keypresses (`s`/`u`); view full-screen diffs with `d`
- Toggle side-by-side diff view with `v`; browse commit history and view commit diffs
- Auto-refresh on filesystem changes; split view with file sidebar and diff pane (`h`/`l` to switch focus)
- Commit interface with `c`; full command: `git add`, `git status`, `git diff`, `git log`, `git show`, `git branch`, `git worktree`, `git stash`, `git rev-parse`, `git rev-list`, `git fetch`, `git tag`, `git blame`, `git check-ignore` (read-only except for explicit write operations)

### Conversations Plugin

- Unified view across 10+ supported agent adapters with persistent local session history
- Displays message content, token counts, model names, estimated costs, and tool calls
- Search sessions with `/`; expand messages to view full content
- Supports adapters: Amp Code, Claude Code, Codex, Cursor CLI, Gemini CLI, GitHub Copilot CLI, Kiro, OpenCode, Pi Agent, Warp
- Data sources: SQLite and JSON session files (Cursor, Warp use SQLite databases; Claude Code uses JSONL files in `~/.claude/projects/` and `~/.config/claude/projects/`)

### TD Monitor Plugin

- Real-time task tracking integration with TD (marcus/td), a task management system designed for AI agents across context windows
- Displays current focused task, scrollable task list with status indicators, activity log with session context
- Quick task review submission with `r`; shares SQLite database (`.todos/issues.db`) with TD CLI via `.td-root` symlinks
- Runs `td` CLI commands (`td version`, `td search`) for task data; read-only on task display, write access for review submissions

### File Browser Plugin

- Collapsible directory tree with click-to-expand and arrow navigation
- Syntax-highlighted code preview with support for 100+ languages via Chroma v2.14.0
- Auto-refresh on file changes; inline editor for explicit file edits (writes propagate immediately)
- Queries git status and blame information per file

### Workspaces Plugin

- Create and manage isolated project branches as sibling directories with `n` (create) / `D` (delete)
- Link TD tasks to workspaces for context tracking with `t`
- Launch coding agents (Claude Code, Codex, Gemini CLI, Cursor CLI, OpenCode, Pi Agent) directly from sidecar with `a`
- Merge workflow: commit staged changes, push branch, create PR, and cleanup with `m`
- Auto-adds sidecar state files to `.gitignore` (`.sidecar/`, `.sidecar-*`, `.sidecar-pr`, `.sidecar-base`, etc.)
- Tmux session management: creates per-workspace tmux sessions, captures output capped at 2 MB (configurable via `tmuxCaptureMaxBytes`)
- Preview diffs and task details in split-pane view; view workspace state (branch, merged status, PR link)

### Project & Worktree Switching

- **Project Switcher** (`@`): Switch between configured projects from `~/.config/sidecar/config.json` without restarting; all plugins reinitialize with new project context; per-project state (active plugin, cursor position) is remembered
- **Worktree Switcher** (`W`): Switch between git worktrees within the current repository; sidecar remembers which worktree was active when the project is revisited and auto-restores it

### Theme Management

- Press `#` to open theme switcher with 2 built-in themes (default, dracula) and 453 community color schemes sourced from iTerm2-Color-Schemes
- Live preview as you navigate; search filtering for community schemes; press `Tab` to browse schemes; press `Enter` to save active theme
- Per-project theme overrides via `.sidecar/config.json`

### UI and State Persistence

- Keymap-driven navigation: Tab/Shift+Tab for plugin switching, 1–9 to jump to plugin by number, j/k for item navigation, Ctrl+D/U for page scrolling, g/G for top/bottom jumps
- Persistent UI state stored in `~/.config/sidecar/state.json`: diff modes, pane widths, active plugin, scroll positions, per-project state
- Help modal toggle with `?`; diagnostics modal with `!` showing version and update commands

---

## Technical Architecture

**Language & Framework**: Go 1.25.5, using Charm stack (Bubbletea v1.3.10 for TUI, Lipgloss v1.1.1 for styling, Bubbles for components)

**Core Components**:

- **Main entry** (`cmd/sidecar/main.go`): Initializes Bubbletea TUI model, parses CLI flags (`--project`, `--debug`, `--config`, `--version`), sets up logging to file (never stderr to avoid TUI corruption), manages feature flags (`--enable-feature`, `--disable-feature`)
- **App model** (`internal/app/model.go`): ~38KB file containing the central Bubbletea Model managing plugin state, event routing, modal lifecycle (project switcher, theme switcher, worktree switcher, diagnostics, update notifications), and view rendering
- **Plugin interface** (`internal/plugin/`): Abstraction for plugin initialization, update, and view methods; allows modular plugin registration via adapter pattern
- **Adapter registry** (`internal/adapter/`): Plugin adapters for 10+ agent types (amp, claudecode, codex, cursor, geminicli, copilot, kiro, opencode, pi, piagent, warp)—each adapter reads session files in agent-specific formats and normalizes to unified message/token structures
- **Git operations** (`internal/app/git.go`): Wraps git CLI commands; returns parsed status, diff, log, and worktree data; implements read-write operations (stage, unstage, commit, push, merge, stash) triggered by user keystrokes
- **File system watching** (`github.com/fsnotify/fsnotify`): Monitors `.git` directory, project files, and agent session directories; triggers UI refreshes on changes
- **Database layer** (`modernc.org/sqlite`): SQLite3 binding for reading Cursor chat history (`.cursor/chats/`) and TD task database (`.todos/issues.db`); supports WAL mode for concurrent access
- **Syntax highlighting** (`github.com/alecthomas/chroma/v2`): Lexer-based code preview generation for 100+ languages

**Data Flow**:

1. User presses key in TUI → routed to active plugin via Bubbletea `Update(msg)` handler
2. Plugin (e.g., Git Status) spawns git CLI command, captures stdout/stderr, parses into domain objects (FileStatus, DiffLine, CommitInfo)
3. Parsed data cached in plugin state; fsnotify watchers trigger re-fetch on filesystem changes
4. View handler (`View()`) renders cached state as ANSI terminal output; Lipgloss applies colors and layout
5. Tmux integration (Workspaces): sends commands via `tmux send-keys`, captures output via `tmux capture-pane`, manages session lifecycle

**Extension Points**:

- **Plugin system**: Add new plugin by implementing `Plugin` interface (init, update, view) and registering in `cmd/sidecar/main.go` plugin list
- **Adapter system**: Register new agent type by creating adapter in `internal/adapter/{name}/` following Adapter interface; adapter normalizes agent-specific session format to Message/Session structs
- **Config overrides**: Per-project `.sidecar/config.json` can override theme, enable/disable plugins, set refresh intervals

**Concurrency & Performance**:

- Bubbletea runs single-threaded event loop; file watchers (fsnotify) run in goroutines and post events back to main loop via channels
- Pprof server available via `SIDECAR_PPROF=1` environment variable (default port 6060) for memory profiling
- Tmux capture capped at 2 MB to prevent memory bloat; configurable via `tmuxCaptureMaxBytes`
- Version check cached for 3 hours in `~/.config/sidecar/version_cache.json` to avoid repeated network requests

**Privacy & Local-First Design**:

- Zero telemetry, zero analytics, zero tracking; runs entirely locally
- Network requests: GitHub API version check on startup (cached 3 hours), optional changelog fetch (user-initiated only)
- File access: reads git data (via CLI), agent session files (read-only, never written to), project files (read-write via inline editor)
- Configuration: ~/.config/sidecar/, per-project .sidecar/ directory; state persisted in state.json and version_cache.json

---

## Installation & Usage

### Quick Install

```bash
# macOS (recommended — builds from source, avoids Gatekeeper warnings)
brew install marcus/tap/sidecar

# Linux / Other
curl -fsSL https://raw.githubusercontent.com/marcus/sidecar/main/scripts/setup.sh | bash

# Binary downloads
# Visit https://github.com/marcus/sidecar/releases
```

### Basic Usage

```bash
# Run from any project directory
sidecar

# Specify project root
sidecar --project /path/to/project

# Enable debug logging
sidecar --debug

# Check version
sidecar --version
```

### Configuration

Config file: `~/.config/sidecar/config.json`

```json
{
  "projects": {
    "list": [
      { "name": "sidecar", "path": "~/code/sidecar" },
      { "name": "td", "path": "~/code/td" }
    ]
  },
  "plugins": {
    "git-status": { "enabled": true, "refreshInterval": "1s" },
    "td-monitor": { "enabled": true, "refreshInterval": "2s" },
    "conversations": { "enabled": true },
    "file-browser": { "enabled": true },
    "workspaces": { "enabled": true }
  },
  "ui": {
    "showClock": true,
    "theme": {
      "name": "default",
      "overrides": {}
    }
  }
}
```

### Suggested Workflow

Split your terminal horizontally:

```text
┌──────────────────────────────┬──────────────────────┐
│  Claude Code / Cursor        │  Sidecar             │
│  (left pane)                 │  (right pane)        │
├──────────────────────────────┼──────────────────────┤
│ $ claude                     │  [Git] [Tasks]       │
│ > fix the auth bug...        │  [Files] [Workspaces]│
└──────────────────────────────┴──────────────────────┘
```

Keyboard shortcuts:
- **Global**: `q` (quit), `@` (project switcher), `W` (worktree switcher), `#` (theme switcher), `?` (help), `!` (diagnostics/updates), `Tab`/`Shift+Tab` (navigate plugins), `1-9` (jump to plugin)
- **Git Status**: `s` (stage), `u` (unstage), `d` (full-screen diff), `v` (side-by-side mode), `c` (commit), `h`/`l` (switch focus)
- **Workspaces**: `n` (new), `D` (delete), `a` (attach agent), `t` (link task), `m` (merge), `p` (push), `o` (open in finder/terminal)

---

## Relevance to Claude Code Development

### Applications

- **Agent Monitoring Dashboard**: Sidecar bridges the gap between agent output (in stderr) and code changes. Run Claude Code on the left terminal pane and Sidecar on the right to watch task progress, file modifications, and commit history in real time without breaking focus from the agent's reasoning.
- **Context Window Recovery**: The Conversations plugin aggregates session history across all supported AI agents, enabling developers to review past conversations, token usage, and reasoning chains when context resets between agent invocations.
- **Task-Driven Development**: TD Monitor integration allows agents to log progress, tasks to persist across sessions, and developers to verify task completion against code changes without switching applications.
- **Workspace Isolation for Parallel Work**: Workspaces plugin supports multiple feature branches managed as sibling directories with integrated agent launchers and PR workflows—useful for parallel feature development or experimenting with multiple agent approaches on the same codebase.

### Patterns Worth Adopting

1. **Plugin-based architecture** for extensibility: Sidecar's adapter and plugin system demonstrates clean separation of concerns. Each agent type (Claude Code, Cursor, Gemini) is isolated in its own adapter module; each UI feature (Git, TD Monitor, Conversations) is a pluggable component. This pattern scales well as new agent types and features are added.
2. **Local-first, read-only philosophy**: Sidecar reads agent session files without modifying them; when write operations occur (staging files, committing, creating workspaces), they are explicit and user-initiated. This principle reduces side effects and makes behavior predictable.
3. **Config-driven feature toggling**: Feature flags (`--enable-feature`, `--disable-feature`) and config-based plugin enable/disable allow operators to customize Sidecar without recompilation, useful for testing new features or disabling problematic plugins.
4. **Tmux integration for agent launchers**: Workspaces manages agent sessions via tmux, capturing output and managing lifecycle. This pattern allows agents to run in isolated, observable contexts while Sidecar maintains visibility.

### Integration Opportunities

1. **Claude Code Adapter Improvements**: Currently, Claude Code sessions are read from `~/.claude/projects/` and `~/.config/claude/projects/`. Deeper integration could expose Claude Code-specific metadata (skill context, plugin state, execution plan) if Claude Code writes structured session metadata.
2. **Task Linking**: Extend the TD Monitor plugin to accept task creation prompts from Claude Code sessions, allowing agents to directly link ongoing work to task entries without manual user action.
3. **Multi-Agent Orchestration**: Use Sidecar as a coordinator for multi-agent workflows: launch one agent on a feature branch (via Workspaces), monitor its progress (via Git Status + Conversations), and conditionally launch a second agent for code review or follow-up tasks.
4. **Documentation Generation**: The File Browser's syntax highlighting and git blame data could feed a documentation generator that produces change summaries or commit message suggestions based on code diffs.

---

## References

- [Sidecar Official Documentation](https://marcus.github.io/sidecar/) (accessed 2026-03-17)
- [GitHub Repository](https://github.com/marcus/sidecar) (accessed 2026-03-17)
- [README.md](https://github.com/marcus/sidecar/blob/main/README.md) (accessed 2026-03-17)
- [PRIVACY.md](https://github.com/marcus/sidecar/blob/main/PRIVACY.md) (accessed 2026-03-17)
- [Charm Bubbletea Documentation](https://github.com/charmbracelet/bubbletea) (v1.3.10, accessed 2026-03-17)
- [Charm Lipgloss Documentation](https://github.com/charmbracelet/lipgloss) (v1.1.1, accessed 2026-03-17)
- [Chroma Syntax Highlighting](https://github.com/alecthomas/chroma) (v2.14.0, accessed 2026-03-17)
- [TD Task Management](https://github.com/marcus/td) (integrated, v0.42.0, accessed 2026-03-17)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [tmuxp](./tmuxp.md) | developer-tools | Declarative session management layer for reproducible tmux workspaces that Sidecar orchestrates |
| [Using tmux with Claude Code](./using-tmux-with-claude-code.md) | developer-tools | Tmux workflow patterns for agent coordination that Sidecar visualizes in real-time terminal UI |
| [Gas Town (gastown)](../research-agent-patterns/gastown.md) | research-agent-patterns | Multi-agent orchestration using tmux as session transport and worktree isolation |
| [GitHub CLI (gh)](./github-cli.md) | developer-tools | CLI-based git and PR automation complementing Sidecar's interactive git status and commit interface |
| [claude-replay](../coding-agents/claude-replay.md) | coding-agents | Session transcript playback tool for visualizing agent conversation history alongside Sidecar's live view |
| [Byobu](./byobu.md) | developer-tools | Terminal multiplexer providing enhanced UI and status persistence as alternative to bare tmux |
| [Claude Task Master](../task-management/claude-task-master.md) | task-management | Alternative task management system for AI-driven development workflows integrated via MCP |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-17 |
| Version at Verification | v0.78.0 |
| Next Review Recommended | 2026-06-17 |
| Confidence Map | `Overview: high (doc + README)`, `Problem Addressed: high (doc)`, `Key Statistics: high (gh API)`, `Key Features: high (doc + code-read)`, `Technical Architecture: medium (doc + code-read)`, `Installation & Usage: high (doc)`, `Relevance to Claude Code Development: high (inference from architecture)` |
