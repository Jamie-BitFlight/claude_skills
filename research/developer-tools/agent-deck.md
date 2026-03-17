# Agent Deck

**Research Date**: 2026-03-17
**Source URL**: <https://github.com/asheshgoplani/agent-deck>
**GitHub Repository**: <https://github.com/asheshgoplani/agent-deck>
**Version at Research**: v0.26.3 (latest at 2026-03-17)
**License**: MIT

---

## Overview

Agent Deck is a terminal session manager for AI coding agents that provides unified control over multiple Claude Code, Gemini CLI, OpenCode, and Codex sessions from a single TUI (terminal user interface). It addresses the complexity of managing multiple concurrent AI sessions by offering intelligent session organization, smart status detection (running/waiting/idle/error), session forking with context inheritance, MCP (Model Context Protocol) management, and socket pooling to reduce resource consumption across sessions.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Managing multiple AI coding sessions across projects becomes chaotic with many terminal tabs and windows | Agent Deck provides a single unified TUI that shows all sessions with color-coded status indicators, enabling instant navigation and organization |
| Context switching between projects and AI agents is slow and error-prone | Press `Enter` to attach to any session; fork sessions with `f` to explore multiple branches; search globally with `G` to find conversations across projects |
| MCP (Model Context Protocol) configuration requires manual editing of config files for each tool | Press `m` to toggle MCPs per session; Agent Deck handles automatic tool restart and manages scope (LOCAL/GLOBAL) |
| Running many MCP servers simultaneously consumes excessive memory | Socket pooling shares MCP processes via Unix domain sockets, reducing memory usage by 85-90% while auto-recovering from MCP crashes in ~3 seconds |
| Monitoring and orchestrating multiple agent sessions is manual, reactive work | Conductors are persistent Claude Code sessions that monitor child sessions, auto-respond when confident, and escalate to Telegram/Slack for remote control |
| Multiple agents working on the same repository create branch/merge conflicts | Git worktree integration isolates each session in its own working directory with automatic cleanup and branch management |
| Testing risky agent tasks in production environments is unsafe | Docker sandbox feature isolates sessions in containers with bind-mounted project directories, auto-sharing host authentication |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 1,568 | 2026-03-17 |
| GitHub Forks | 162 | 2026-03-17 |
| Contributors | 41 | 2026-03-17 |
| Latest Release | v0.26.3 | 2026-03-17 |
| Release Frequency | Multiple per week (v0.25.0 on 2026-03-11, v0.25.1 on 2026-03-11, v0.26.0 on 2026-03-14, v0.26.2 on 2026-03-16, v0.26.3 on 2026-03-17) | 2026-03-17 |
| Primary Language | Go 1.24+ | 2026-03-17 |

---

## Key Features

### Session Management

- **TUI Session Browser**: Press `Enter` to attach to any session; `n` to create new sessions; search via `/` for fuzzy matching across all sessions
- **Session Forking**: Press `f` for quick fork or `F` to customize name/group; inherits full conversation history; fork your forks to explore multiple solution branches
- **Status Detection**: Real-time smart polling detects running (●), waiting (◐), idle (○), and error (✕) states with visual indicators
- **Multi-Tool Support**: Native support for Claude Code, Gemini CLI with full status/MCP/fork integration; OpenCode and Codex status detection; configurable custom tool definitions in `[tools.*]` config.toml section
- **Session Groups**: Organize sessions into named groups; press `M` to move sessions between groups; groups persist across restarts

### MCP Management

- **MCP Manager Dialog**: Press `m` to toggle MCP servers per session; `Space` to toggle, `Tab` to cycle scope (LOCAL/GLOBAL); type-to-jump navigation
- **Scope Control**: Toggle MCP visibility between LOCAL (current session only) and GLOBAL (all sessions); changes auto-trigger tool restart
- **MCP Socket Pool**: Enable with `pool_all = true` in config.toml; shares MCP processes via Unix domain sockets reducing memory by 85-90%; reconnecting proxy auto-recovers from MCP crashes in ~3 seconds
- **Configuration**: Define MCPs once in `~/.agent-deck/config.toml`; toggle per session or globally

### Skills Management (Claude-specific)

- **Skills Manager**: Press `s` on Claude sessions to attach/detach skills from a managed pool
- **Pool Workflow**: Skills stored in `~/.agent-deck/skills/pool`; apply writes to `.agent-deck/skills.toml` and materializes into `.claude/skills`
- **Type-to-Jump**: Search and select skills by typing in the dialog; same pattern as MCP Manager

### Git Worktree Integration

- **Worktree Creation**: `agent-deck add . -c claude --worktree feature/a --new-branch` creates isolated working directory; `--location subdirectory` places under `.worktrees/` in repo
- **Worktree Locations**: Configurable via `[worktree].default_location`: `sibling` (default, next to repo), `subdirectory` (inside `.worktrees/`), or custom path like `~/worktrees` or `/tmp/worktrees`
- **Worktree Cleanup**: `agent-deck worktree finish "My Session"` merges branch, removes worktree, and deletes session; `agent-deck worktree cleanup` removes orphaned worktrees
- **Multi-Agent Isolation**: Each worktree is isolated working directory with its own branch; multiple agents can work on the same repo without merge conflicts

### Docker Sandbox

- **Containerized Sessions**: Check "Run in Docker sandbox" during session creation or set `default_enabled = true` in config; project directory bind-mounted read-write
- **Container Shell**: Press `T` on sandboxed sessions to open container shell for debugging
- **One-Shot Sessions**: `agent-deck try "task description"` runs sandboxed session that auto-cleans
- **Auth Sharing**: Host tool auth (Claude, Gemini, etc.) automatically shared into containers via shared sandbox directories; Keychain credentials extracted on macOS
- **Overlay Configuration**: Documented in Docker Sandbox Guide reference; custom image support included
- **Cleanup**: Set `[docker].auto_cleanup = true` (default) to remove containers when sessions end; `false` keeps containers for inspection

### Conductor (Persistent AI Monitors)

- **Conductor Setup**: `agent-deck -p work conductor setup ops --description "Ops monitor"` creates persistent Claude Code session for orchestration
- **Profiles**: Multiple conductors per profile; each gets own directory identity and settings in `~/.agent-deck/conductor/`
- **Bridging**: Optional Telegram and/or Slack integration via bridge daemon; socket mode support for Slack with slash commands (`/ad-status`, `/ad-sessions`, `/ad-restart`, `/ad-help`)
- **Message Routing**: Telegram/Slack prefix routing (`name: message`) routes to specific conductors
- **Monitoring**: Built-in transition notifiers watch status changes; heartbeat monitoring on configurable interval (default 15 minutes); parent nudges when child sessions move running→waiting/error/idle
- **Launching Child Sessions**: `AGENT_DECK_SESSION_ID` auto-enables parent routing; `--no-parent` disables; extra args in `--cmd` are preserved via auto-wrapping

### Search and Navigation

- **Fuzzy Search**: Press `/` to search across all sessions; filter by status with `!` (running), `@` (waiting), `#` (idle), `$` (error)
- **Global Search**: Press `G` to search across all Claude conversations globally
- **Notification Bar**: Waiting sessions appear in tmux status bar; press `Ctrl+b` then `1`–`6` to jump directly to them

### Web UI

- **Web Mode**: `agent-deck web` starts browser interface on <http://127.0.0.1:8420>
- **Read-Only Mode**: `agent-deck web --read-only` for output-only access
- **Custom Listen Address**: `--listen 127.0.0.1:9000` to change port
- **Bearer Token Protection**: `--token my-secret` protects API/WebSocket access; open with `?token=my-secret` query param

### Settings and Profiles

- **Profiles**: Create profiles with `--profile/-p`; isolate sessions, MCPs, and conductor configs by profile
- **Settings Panel**: Press `S` in TUI to access settings; configure default tool, notes visibility, follow-CWD behavior
- **Custom Tools**: Define custom tools in `[tools.*]` sections of config.toml with configurable hotkeys

---

## Technical Architecture

Agent Deck is structured as a modular Go application with clear separation of concerns:

**Core Session Management**:
- Source: `internal/session/` — provides session discovery, lifecycle management, and multi-tool support
- `internal/session/claude.go`, `internal/session/gemini.go`, `internal/session/opencode*.go` — tool-specific session implementations
- `internal/session/conductor.go` — persistent conductor session orchestration
- `internal/session/hook_watcher.go` — detects session state changes via tool-specific hooks (Claude hooks, Gemini hooks, Codex hooks)
- `internal/session/event_writer.go` — asynchronous event management for status updates

**MCP Socket Pool** (reducing memory usage):
- Source: `internal/mcppool/` — MCP process sharing and reconnection logic
- `internal/mcppool/socket_proxy.go` — Unix domain socket proxy that multiplexes client connections to shared MCP processes
- `internal/mcppool/socket_proxy_test.go` — verified recovery from MCP crashes within 3 seconds
- Pools MCP processes at global scope; HTTP server component routes client requests through proxy

**Container & Git Orchestration**:
- Source: `internal/docker/` — sandbox container management with overlay support
- `internal/docker/sandbox.go` — platform-specific implementations (Darwin/macOS vs. Linux/WSL)
- `internal/docker/docker.go` — Docker client integration for container lifecycle
- Source: `internal/git/` — worktree creation, branch management, template handling
- `internal/git/git.go` — git command wrapper with worktree isolation

**TUI & Display**:
- Source: `cmd/agent-deck/main.go` — 88KB core CLI with all TUI and command logic
- Built with [Charmbracelet Bubble Tea](https://github.com/charmbracelet/bubbletea) (TUI framework)
- Built with [Charmbracelet Lipgloss](https://github.com/charmbracelet/lipgloss) (styling) and [Charmbracelet Bubbles](https://github.com/charmbracelet/bubbles) (reusable components)
- Integrated tmux session management via creack/pty for pseudo-terminal handling

**Conductor Bridge** (Telegram/Slack):
- Source: `internal/openclaw/` — OpenClaw gateway for remote agent sessions
- `internal/openclaw/bridge.go` — Telegram/Slack bridge daemon
- WebSocket support for concurrent Slack Socket Mode connections
- Message routing with conductor namespace prefixes

**Configuration & Storage**:
- TOML configuration: `~/.agent-deck/config.toml` — session defaults, MCP definitions, tool specs, profile overrides
- SQLite database: persistent session metadata, analytics, state recovery
- Source: `internal/session/config.go` — config parsing and validation
- Profile system: per-profile CLI context, Claude config dirs, conductor settings

**Analytics & Observability**:
- Source: `internal/session/analytics.go`, `internal/session/gemini_analytics.go` — usage analytics collection
- Source: `internal/logging/` — structured logging with ringbuffer, slow-op detection, pprof integration
- `internal/logging/aggregator.go` — log aggregation and export

**Hook System** (Tool Integration):
- Source: `cmd/agent-deck/claude_hooks_cmd.go` — Claude hook installation/uninstallation; status polling via hook payloads
- Source: `cmd/agent-deck/gemini_hooks_cmd.go` — Gemini hook management
- Source: `cmd/agent-deck/codex_hooks_cmd.go` — Codex hook management (13KB file with hook-specific CLI)
- Hooks write session state changes to SQLite; agent-deck polls and displays status

**Dependency Stack**:
- [BurntSushi/toml](https://github.com/BurntSushi/toml) v1.5.0 — TOML parsing
- [Charmbracelet](https://github.com/charmbracelet/) — TUI (Bubble Tea v1.3.10, Bubbles v0.21.0, Lipgloss v1.1.0)
- [creack/pty](https://github.com/creack/pty) v1.1.24 — pseudo-terminal allocation for session isolation
- [fsnotify](https://github.com/fsnotify/fsnotify) v1.9.0 — file system watcher for hook payloads
- [gorilla/websocket](https://github.com/gorilla/websocket) v1.5.3 — Slack Socket Mode and conductor bridging
- [modernc.org/sqlite](https://modernc.org/sqlite) v1.44.3 — pure Go SQLite for session state
- [golang.org/x/term](https://pkg.go.dev/golang.org/x/term) v0.37.0 — terminal detection and control

---

## Installation & Usage

### Installation

```bash
# Install via curl (recommended)
curl -fsSL https://raw.githubusercontent.com/asheshgoplani/agent-deck/main/install.sh | bash

# Or via Homebrew
brew install asheshgoplani/tap/agent-deck

# Or via Go
go install github.com/asheshgoplani/agent-deck/cmd/agent-deck@latest

# Or from source
git clone https://github.com/asheshgoplani/agent-deck.git && cd agent-deck && make install
```

Then run: `agent-deck`

### Quick Start

```bash
agent-deck                        # Launch TUI
agent-deck add . -c claude        # Add current dir with Claude
agent-deck session fork my-proj   # Fork a Claude session
agent-deck mcp attach my-proj exa # Attach MCP to session
agent-deck skill attach my-proj docs --source pool --restart # Attach skill + restart
agent-deck web                    # Start web UI on http://127.0.0.1:8420
```

### TUI Key Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Attach to session |
| `n` / `N` | New session |
| `f` / `F` | Fork (quick / dialog) |
| `m` | MCP Manager |
| `s` | Skills Manager (Claude) |
| `M` | Move session to group |
| `S` | Settings |
| `/` / `G` | Search / Global search |
| `r` | Restart session |
| `d` | Delete |
| `T` | Container shell (sandboxed sessions) |
| `?` | Full help |

### CLI Examples

```bash
# Create session with custom profile
agent-deck -p work add . -c claude --group frontend

# Add session with worktree
agent-deck add . -c claude --worktree feature/auth --new-branch

# Create conductor for orchestration
agent-deck conductor setup ops --description "Ops monitor"

# Attach MCP to existing session
agent-deck mcp attach my-proj exa --scope GLOBAL

# Try one-shot sandboxed task
agent-deck try "analyze git logs for regressions"

# Run with custom Claude config
agent-deck -p work launch . -c claude -m "Review PR 123"

# List all sessions with status
agent-deck list

# Web UI with token protection
agent-deck web --listen 127.0.0.1:9000 --token my-secret
```

### Configuration Example

```toml
# ~/.agent-deck/config.toml

[claude]
config_dir = "~/.claude"        # Global Claude config

[profiles.work.claude]
config_dir = "~/.claude-work"   # Work-specific Claude config

[mcp]
exa = { command = "npx", args = ["-y", "@exa-ai/exa-sdk"] }
brave = { command = "node", args = ["~/.mcp-servers/brave/index.js"] }

[worktree]
default_location = "subdirectory"  # "sibling", "subdirectory", or custom path
branch_prefix = "agent-"

[docker]
default_enabled = false
mount_ssh = true
auto_cleanup = true

[tools.custom-tool]
command = "my-agent"
hotkey = "c"

auto_update = true              # Optional: auto-check for updates
```

---

## Relevance to Claude Code Development

### Applications

- **Session Orchestration**: Manage multiple Claude Code instances across projects from a single interface; each session maintains isolated context and can be forked to explore alternatives
- **MCP Configuration**: Seamlessly attach MCPs (web search, browser, file analysis) per session or globally without editing config files; socket pooling reduces resource consumption when running many MCP-dependent sessions
- **Skills Pooling**: Manage a skills pool (`~/.agent-deck/skills/pool`) and attach/detach per project; state materializes into `.claude/skills` automatically
- **Conductor Workflows**: Create persistent Claude Code sessions that monitor child sessions, detect when they need help, and escalate to Telegram/Slack for remote control or human intervention
- **Multi-Project Isolation**: Git worktrees provide isolated branches and working directories for each agent session, enabling safe multi-agent collaboration on the same repository
- **Docker Sandboxing**: Run risky agent tasks in containers with auth shared from host; auto-cleanup and full project bind-mount for file I/O

### Patterns Worth Adopting

- **Hook-Based Status Detection**: Agent Deck uses tool-specific hooks (Claude hooks, Gemini hooks, Codex hooks) installed into each tool to detect state changes and write to SQLite. This pattern is more reliable than polling file timestamps and enables instant status updates without excessive polling overhead
- **Session Forking with Context Inheritance**: Forking a session with full history enables exploring multiple solution branches without losing the original approach; applicable to any multi-decision AI workflow
- **Socket Pooling for Shared Resources**: The MCP socket pool reduces memory by 85-90% and auto-recovers from crashes in 3 seconds via a reconnecting proxy; this pattern applies to any resource-intensive service shared across multiple clients
- **Profile-Based Multi-Account Support**: Using profiles to separate Claude configs, MCPs, conductors, and tool settings enables seamless context switching between work, personal, and experimental projects without file manipulation
- **TOML-Based Configuration with Type Safety**: Agent Deck uses TOML with Go struct unmarshaling to achieve readable config with compile-time type validation; applicable to any tool with complex settings

### Integration Opportunities

- **Claude Code Skill**: Agent Deck ships a Claude Code skill (`/plugin install agent-deck@agent-deck`) with CLI reference, TUI reference, configuration guide, and troubleshooting; this pattern demonstrates embedding tool-specific guidance into Claude Code's skill ecosystem
- **OpenCode Compatibility**: Agent Deck has built-in support for OpenCode's hook API and skill discovery, enabling OpenCode users to manage Agent Deck sessions; this interoperability pattern could inform other Claude Code integrations
- **Conductor Orchestration with Claude Code**: Conductors are Claude Code sessions that monitor other sessions; this creates a meta-orchestration pattern where Claude Code can be used to build supervisors for Claude Code workloads
- **Cross-Tool Visibility**: Agent Deck's multi-tool support (Claude Code, Gemini CLI, OpenCode, Codex) demonstrates how to build a unified interface across different AI tools; applicable to Claude Code ecosystem tooling
- **Slack/Telegram Integration for Remote Operations**: The bridge daemon architecture (Telegram bot + Slack Socket Mode + message routing) provides a pattern for adding remote control to Claude Code workflows without hosting a separate service

---

## References

- [Agent Deck GitHub Repository](https://github.com/asheshgoplani/agent-deck) (accessed 2026-03-17)
- [Agent Deck README](https://github.com/asheshgoplani/agent-deck/blob/main/README.md) (accessed 2026-03-17)
- [Agent Deck CONTRIBUTING.md](https://github.com/asheshgoplani/agent-deck/blob/main/CONTRIBUTING.md) (accessed 2026-03-17)
- [Agent Deck CHANGELOG.md](https://github.com/asheshgoplani/agent-deck/blob/main/CHANGELOG.md) (accessed 2026-03-17)
- [Agent Deck go.mod](https://github.com/asheshgoplani/agent-deck/blob/main/go.mod) (accessed 2026-03-17)
- [Agent Deck cmd/agent-deck/](https://github.com/asheshgoplani/agent-deck/tree/main/cmd/agent-deck) (accessed 2026-03-17)
- [Agent Deck internal/](https://github.com/asheshgoplani/agent-deck/tree/main/internal) (accessed 2026-03-17)
- [Charmbracelet Bubble Tea](https://github.com/charmbracelet/bubbletea) (referenced as core TUI framework dependency)
- [Charmbracelet Bubbles](https://github.com/charmbracelet/bubbles) (referenced as reusable TUI component library)
- [Charmbracelet Lipgloss](https://github.com/charmbracelet/lipgloss) (referenced as styling library)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Sidecar](./sidecar.md) | developer-tools | Complementary TUI companion: Agent Deck orchestrates sessions, Sidecar provides real-time visibility and git/workspace management alongside agent output |
| [tmuxp](./tmuxp.md) | developer-tools | Alternative session manager: declarative YAML/JSON approach vs Agent Deck's TUI; both solve reproducible multi-pane terminal workspace recreation |
| [Using tmux with Claude Code](./using-tmux-with-claude-code.md) | developer-tools | Foundational tmux patterns for multi-pane agent coordination that Agent Deck's architecture builds upon with automation |
| [Claude Conductor](./claude-conductor.md) | developer-tools | Complementary orchestration layer: Conductor enforces development workflow (spec→plan→implement), Agent Deck manages session lifecycle and resource pooling |
| [1Code](../coding-agents/1code.md) | coding-agents | Shared multi-agent orchestration goals: both provide git worktree isolation per session, MCP management, and unified UI across multiple agent backends |
| [Tembo](../coding-agents/tembo.md) | coding-agents | Cloud-based counterpart: Tembo automates agent dispatch from external events; Agent Deck provides local interactive session control and persistence |
| [Everything Claude Code](./everything-claude-code.md) | developer-tools | Complementary harness approach: ECC provides 15 specialized sub-agents and hooks pipeline; Agent Deck enables running multiple agents in parallel with resource pooling |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-17 |
| Version at Verification | v0.26.3 |
| Next Review Recommended | 2026-06-17 |
| Confidence Map | `Overview: high`, `Problem Addressed: high`, `Key Statistics: high`, `Key Features: high`, `Technical Architecture: high (code-read)`, `Installation & Usage: high`, `Relevance to Claude Code Development: high` |
