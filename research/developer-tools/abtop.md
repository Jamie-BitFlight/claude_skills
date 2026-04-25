# abtop

**Research Date**: 2026-04-25
**Source URL**: <https://github.com/graykode/abtop>
**GitHub Repository**: <https://github.com/graykode/abtop>
**Version at Research**: v0.3.7
**License**: MIT

---

## Overview

abtop is a real-time terminal user interface monitor for AI coding agents, inspired by btop (a system resource monitor). It displays live metrics for Claude Code and Codex CLI sessions, including token consumption, context window utilization, rate limit quotas, running child processes, and orphaned ports. The tool reads local file and process metadata only — no API keys, authentication, or network calls to external services.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Monitoring multiple concurrent AI agent sessions across projects | Session-aware TUI displays all active Claude Code and Codex CLI sessions in a single scrollable list with real-time status |
| Tracking token consumption and rate limits in real-time | Per-session token count with delta-rate graph (braille characters), account-level 5-hour and 7-day rate limit percentage bars |
| Context window overflow risk | Per-session context window utilization percentage with gradient color coding (green < 80%, yellow 80–90%, red > 90%) and compaction detection |
| Orphaned processes and ports left behind after sessions end | Orphan port detection and killing via port scanner (`lsof`), preventing resource leaks and port conflicts |
| Finding and jumping to the terminal running a specific agent session | tmux integration — press Enter on a session to jump directly to its tmux pane |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 1,200 | 2026-04-25 |
| GitHub Forks | 94 | 2026-04-25 |
| Open Issues | 10 | 2026-04-25 |
| Primary Language | Rust (99.6%) | 2026-04-25 |
| Latest Release | v0.3.7 | 2026-04-25 |
| Total Releases | 24 | 2026-04-25 |

---

## Key Features

### Session Discovery and Monitoring

- Automatic discovery of Claude Code sessions from `~/.claude/sessions/` directory structure (Source: src/collector/claude.rs — `refresh_config_dirs()`, `collect_sessions()`)
- Automatic discovery of Codex CLI sessions via process introspection (Source: src/collector/codex.rs — `CodexCollector::collect()`)
- Support for multiple active profiles and concurrent sessions
- Real-time session status detection: Thinking (generating, no active tool), Executing (tool active), Waiting (idle, user input), RateLimited (quota exceeded), or Done (finished) (Source: src/model/session.rs — `SessionStatus` enum)
- Live per-session token count with token-rate delta tracking (computed per tick, stored in ring buffer for graphing) (Source: src/app.rs — `GRAPH_HISTORY_LEN = 200`)

### Rate Limit Tracking

- Account-level rate limit monitoring for Claude and Codex with 5-hour and 7-day window percentages (Source: src/model/session.rs — `RateLimitInfo` struct with `five_hour_pct` and `seven_day_pct` fields)
- Rate limit status hook installation via `abtop --setup`, which configures Claude Code's StatusLine to write quota state to a JSON file that abtop parses (Source: src/setup.rs, README: "abtop --setup" installs rate limit collection hook)
- Rate limit polling on slow ticks (every 5 ticks ≈ 10s) to balance responsiveness with filesystem load (Source: src/collector/rate_limit.rs)

### Context Window Monitoring

- Per-session context window utilization percentage displayed as a gradient-colored bar (Source: src/ui/context.rs)
- Compaction detection: identifies when Claude's message history compaction has reduced the active context (Source: src/model/session.rs — `SessionFile` struct tracks compaction state)
- Percentage-based visualization with color shifts (green under 80%, yellow 80–90%, red above 90%) (Source: src/ui/mod.rs — gradient interpolation functions)

### Child Process and Port Monitoring

- Per-session child process tracking with memory and port information (Source: src/model/session.rs — `ChildProcess` struct with pid, command, mem_kb, and optional port fields)
- Orphan port detection: identifies ports held open by processes whose parent agent sessions have ended (Source: src/model/session.rs — `OrphanPort` struct)
- Orphan port killing: press `X` to terminate all detected orphan processes (Source: README: Key Bindings — "X: Kill all orphan ports")
- File operation audit trail: R (Read), W (Write), E (Edit) operations tracked per session from tool invocation logs (Source: src/model/session.rs — `FileAccess` and `FileOp` enums)

### User Interface and Theming

- 10 built-in color themes: btop (default), dracula, catppuccin, tokyo-night, gruvbox, nord, and 4 colorblind-friendly variants (high-contrast, protanopia, deuteranopia, tritanopia) (Source: src/theme.rs — `THEME_NAMES` array, theme implementations with gradient definitions)
- Modular panel visibility: toggle Tokens (1), Context (2), Quota (3), Ports (4), Sessions (5) panels with keyboard shortcut (Source: src/app.rs — `show_context`, `show_quota`, `show_tokens`, `show_ports`, `show_sessions` boolean fields)
- Session tree view: hierarchical display of sessions and their subagents (Source: src/app.rs — `tree_view` boolean field)
- Configuration overlay: press Escape to open/close config UI for theme selection and hidden agent filtering (Source: src/app.rs — `config_open`, `config_selected` fields; src/ui/config.rs)
- Session filtering: filter displayed sessions by name (Source: src/app.rs — `filter_text`, `filter_active` fields)
- Help overlay and view menu: press `?` for keybindings, press `v` for view options (Source: src/app.rs — `help_open`, `view_open` fields)

### Installation and Distribution

- Platform-specific installers: macOS (Intel and Apple Silicon), Linux (x86_64 and ARM64), with shell script and Cargo installation options (Source: README — "Install" section lists multiple installation paths)
- Self-update capability: `abtop --update` fetches latest release from GitHub (Source: src/main.rs — `--update` flag handler calls `run_update()`)
- Homebrew support (implied by release artifacts, verified in README)

### Snapshot Export and Batch Mode

- One-time snapshot mode: `abtop --once` prints current session state and exits (useful for scripting and CI integration) (Source: src/main.rs — `--once` flag logic)
- Demo mode: `abtop --demo` populates example session data for testing and screenshots (Source: src/main.rs — `--demo` flag)

### Terminal Integration

- tmux awareness: running inside tmux enables session jumping (press Enter to switch pane) (Source: README: tmux section, src/app.rs — `JumpOutcome` enum and jump logic)
- Minimum terminal size: 80x24 with recommended 120x40; panels hide gracefully on smaller terminals (Source: README: "Recommended terminal size: **120x40** or larger. Minimum 80x24 — panels hide gracefully when small.")
- Braille graph visualization: token rate displayed using Unicode braille characters (Source: src/ui/mod.rs — `BRAILLE_UP` array with braille symbols, `make_gradient()` function)

---

## Technical Architecture

abtop uses a modular collector pattern to gather agent session data from multiple sources, each decoupled from the others:

### Core Components

**App State** (Source: src/app.rs — `struct App`)
- Central state container holding all sessions, rate limits, theme, UI state (panel visibility, filters, overlays)
- Maintains summary cache for LLM-generated session descriptions (via `claude --print`)
- Tracks token rates in a ring buffer (`VecDeque<f64>`) for the braille token-rate graph
- Manages session selection, kill confirmation state, and transient status messages

**Collector Framework** (Source: src/collector/mod.rs)
- `AgentCollector` trait: defines interface for agent-specific session discovery (Source: `pub trait AgentCollector`)
  - `collect(&mut self, shared: &SharedProcessData) -> Vec<AgentSession>` — return all live sessions
  - `live_rate_limit(&self) -> Option<RateLimitInfo>` — return agent's current rate limit status
  - `discovered_config_dirs(&self) -> Vec<PathBuf>` — return config directories to search for rate limit data
- `SharedProcessData` struct (Source: `struct SharedProcessData`) — process information fetched once per tick and shared across all collectors to avoid redundant syscalls
  - `process_info: HashMap<u32, ProcInfo>` — PID → process details (command, memory, status)
  - `children_map: HashMap<u32, Vec<u32>>` — PID → child PIDs
  - `ports: HashMap<u32, Vec<u16>>` — PID → open ports
  - `slow_tick: bool` — true every 5 ticks (~10s) for expensive operations

**Claude Collector** (Source: src/collector/claude.rs — `pub struct ClaudeCollector`)
- Discovers Claude Code sessions from `~/.claude/sessions/` and `CLAUDE_CONFIG_DIR` environment variable (Source: lines 66–88 in claude.rs)
- Refreshes known config directories on slow ticks by reading `/proc/<pid>/environ` for running Claude processes (expensive, deferred to slow tick)
- Parses session JSON and transcript files incrementally (caches parse results to avoid re-reading entire files)
- Extracts token counts, context window %, status, current task, git status, file operation audit trail, and child processes

**Codex Collector** (Source: src/collector/codex.rs)
- Discovers Codex CLI sessions via process introspection (alternative to Claude Code)
- Shares same session data model (`AgentSession`)

**Rate Limit Collector** (Source: src/collector/rate_limit.rs — `pub fn read_rate_limits()`)
- Parses rate limit state written by Claude Code's StatusLine hook
- Returns account-level quota: 5-hour and 7-day window percentages and reset timestamps

**Process and Port Scanner** (Source: src/collector/process.rs)
- `get_process_info()` — reads `/proc` (Linux) or `ps` + `proc_pidinfo` (macOS) for process listing
- `get_children_map()` — builds parent-child process relationships
- `get_open_ports()` — runs `lsof -i` (Unix) to map PIDs to open TCP/UDP ports

### Data Flow

```
┌────────────────────────────────────────────────────────────┐
│                    Each Tick (main loop)                   │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
          ┌─────────────────────────────────────┐
          │ SharedProcessData::fetch()          │
          │ • Get process info (ps, /proc)      │
          │ • Build parent-child map            │
          │ • Get open ports (lsof) every 5 ticks
          └─────────────────────────────────────┘
                            │
                            ▼
        ┌──────────────────────────────────────┐
        │ Collectors.collect(shared)           │
        │ ├─ ClaudeCollector → sessions        │
        │ └─ CodexCollector → sessions         │
        └──────────────────────────────────────┘
                            │
                            ▼
    ┌────────────────────────────────────────────────┐
    │ Merge all sessions into App::sessions          │
    │ • Compute token deltas from prev tick          │
    │ • Add to token_rates ring buffer               │
    │ • Queue LLM summary jobs (max 3 concurrent)    │
    │ • Detect orphan ports                          │
    └────────────────────────────────────────────────┘
                            │
                            ▼
    ┌────────────────────────────────────────────────┐
    │ Render UI (src/ui/mod.rs + submodules)         │
    │ • Filter by filter_text if active              │
    │ • Apply theme colors from Theme struct         │
    │ • Render panels: header, sessions, tokens,     │
    │   context, quota, ports, footer                │
    └────────────────────────────────────────────────┘
                            │
                            ▼
             ┌──────────────────────────────┐
             │ Handle keyboard input        │
             │ (selection, kill, theme, etc)│
             └──────────────────────────────┘
```

### Key Design Decisions

**Read-Only File Access**: abtop reads only `.claude/sessions/`, `.claude/projects/`, and rate limit JSON files; it never modifies Claude Code's configuration or state. This ensures compatibility across versions and multiple agent instances without synchronization issues. (Source: README — "All read-only. No API keys. No auth.")

**Slow Tick Optimization**: Expensive operations (scanning `/proc/<pid>/environ`, running `lsof`) run only every 5 ticks (~10s) to balance real-time responsiveness with system load. Rate limits and session counts update every 2 seconds. (Source: src/app.rs — rate limit counter logic, src/collector/mod.rs — `slow_tick` parameter)

**Secret Redaction**: Tool names and file paths are displayed, but credentials are filtered before rendering. abtop's `redact_secrets()` function masks common token prefixes (`sk-ant-`, `sk-proj-`, `ghp_`, etc.) before UI display. (Source: src/collector/mod.rs — `pub(crate) fn redact_secrets()` function)

**Session Summary via LLM**: abtop uses `claude --print` to generate human-readable summaries of in-progress sessions (via subprocess call, not the Claude API). Summaries are cached and retry up to 2 times if the `claude` command times out. (Source: src/app.rs — `MAX_SUMMARY_JOBS = 3`, `MAX_SUMMARY_RETRIES = 2`)

---

## Installation & Usage

### Install via Shell Script

```bash
curl --proto '=https' --tlsv1.2 -LsSf https://github.com/graykode/abtop/releases/latest/download/abtop-installer.sh | sh
```

### Install via Cargo

```bash
cargo install abtop
```

### Launch TUI

```bash
abtop                    # Launch interactive terminal UI
abtop --once             # Print snapshot and exit
abtop --setup            # Install rate limit collection hook
abtop --theme dracula    # Launch with a specific theme
abtop --update           # Self-update to latest release
```

### Configuration

Create `~/.config/abtop/config.toml`:

```toml
theme = "btop"
# Hide specific agent CLIs from the TUI (case-insensitive).
hidden_agents = ["codex"]
```

### Key Bindings

| Key | Action |
|-----|--------|
| ↑/↓ or k/j | Select session |
| Enter | Jump to session terminal (tmux only) |
| x | Kill selected session |
| X | Kill all orphan ports |
| t | Cycle theme |
| 1–5 | Toggle panel visibility |
| Esc | Open/close config page |
| ? | Show help overlay |
| v | Open view menu |
| q | Quit |
| r | Force refresh |

### tmux Integration

abtop works standalone, but session jumping (Enter key) works only inside tmux:

```bash
tmux new -s work
# pane 0: abtop
# pane 1: claude project-a
# pane 2: claude project-b
# → Enter on a session in abtop jumps to its pane
```

---

## Relevance to Claude Code Development

### Applications

- **Multi-session monitoring**: When running 3+ concurrent Claude Code or Codex sessions across projects, abtop provides unified visibility into token consumption, context window usage, and rate limit status without context switching between terminals.
- **Rate limit observability**: Real-time 5-hour and 7-day quota tracking prevents surprise rate limit blocks and enables session prioritization when quota is constrained.
- **Resource leak detection**: Orphan port detection catches forgotten servers spawned by agents, preventing port conflicts and resource exhaustion.
- **Session debugging**: The file operation audit trail (Read/Write/Edit count) and task status field support quick diagnosis of stuck or misbehaving sessions.

### Patterns Worth Adopting

- **Modular collector architecture**: The `AgentCollector` trait enables adding new agent types (future Sonnet-standalone CLI, other vendors) without modifying core app logic.
- **Slow tick optimization**: Deferred expensive syscalls (file scanning, port enumeration) to infrequent ticks is a scalable pattern for real-time TUIs.
- **Read-only state discovery**: Parsing session metadata from files (JSON, transcripts) rather than requiring agent API cooperation keeps abtop decoupled and forward-compatible.
- **Theme framework**: The gradient-based color system with colorblind variants is a reusable pattern for terminal UI theming.

### Integration Opportunities

- **Claude Code plugin integration**: abtop could be packaged as a Claude Code marketplace plugin (or skill) to expose session monitoring as a subcommand or sidebar widget.
- **Rate limit alerting**: Integration with alert systems (e.g., terminal bell, status line markers) when quota exceeds thresholds.
- **Session export**: Extend `--once` mode to output JSON, YAML, or Markdown for CI/CD dashboards and session reporting.
- **Subagent tree visualization**: The tree_view mode could be enhanced to show parent-child relationships for orchestrated multi-agent workflows.

---

## Limitations and Caveats

- **Windows support**: abtop requires Unix tools (`ps`, `lsof`) and is not natively supported on Windows. WSL (Windows Subsystem for Linux) is the recommended workaround. (Source: README — "Windows" section)
- **Codex CLI feature parity**: Codex CLI support lacks subagent tracking and memory status visibility compared to Claude Code (see "Supported Agents" feature matrix in README).
- **Terminal size constraints**: Panels hide gracefully on small terminals, but the TUI is designed for 120x40 or larger. Functionality on 80x24 (minimum) is degraded.
- **Rate limit data dependency**: Rate limit tracking requires the `abtop --setup` hook to be installed and Claude Code's StatusLine to be enabled. Without it, only token counts and context window % are visible.
- **Transcript parsing assumptions**: abtop parses Claude Code's internal session JSON and transcript formats, which are not part of the public API and may change. Parsing failures degrade gracefully (session shown without detailed metadata).
- **Single-machine scope**: abtop monitors only local processes and files. Distributed or remote agent sessions are not supported.

---

## References

- [abtop GitHub Repository](https://github.com/graykode/abtop) (accessed 2026-04-25)
- [abtop README](https://github.com/graykode/abtop/blob/main/README.md) (accessed 2026-04-25)
- [abtop Cargo.toml](https://github.com/graykode/abtop/blob/main/Cargo.toml) (accessed 2026-04-25)
- [abtop src/app.rs](https://github.com/graykode/abtop/blob/main/src/app.rs) (accessed 2026-04-25)
- [abtop src/collector/](https://github.com/graykode/abtop/blob/main/src/collector/) (accessed 2026-04-25)
- [abtop src/model/session.rs](https://github.com/graykode/abtop/blob/main/src/model/session.rs) (accessed 2026-04-25)
- [abtop src/ui/mod.rs](https://github.com/graykode/abtop/blob/main/src/ui/mod.rs) (accessed 2026-04-25)
- [abtop src/theme.rs](https://github.com/graykode/abtop/blob/main/src/theme.rs) (accessed 2026-04-25)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Using tmux with Claude Code](./using-tmux-with-claude-code.md) | developer-tools | abtop session jumping integrates with tmux panes; complements tmux workflows for multi-agent monitoring |
| [libtmux](./libtmux.md) | developer-tools | provides programmatic Python API for tmux session management; enables scripted control of workspaces abtop monitors |
| [byobu](./byobu.md) | developer-tools | terminal multiplexer configuration layer for tmux/screen; abtop monitors sessions within byobu-managed multiplexed environments |
| [shpool](./shpool.md) | developer-tools | session persistence daemon for SSH reconnects; abtop could monitor shpool session state alongside tmux sessions |
| [Claude-Mem](../context-management/claude-mem.md) | context-management | persistent session memory with progressive disclosure pattern; complements abtop's real-time monitoring with long-term context |
| [Logfire](../ai-observability/logfire.md) | ai-observability | full-stack observability for AI agents with token tracking; provides backend telemetry while abtop provides terminal-level session metrics |
| [SlimContext](../context-management/slimcontext.md) | context-management | context window optimization for multi-turn conversations; applies same token awareness as abtop's rate limit and context monitoring |
| [TUI Studio](./tui-studio.md) | developer-tools | visual TUI design tool; abtop's dashboard could be redesigned visually using TUI Studio's component export workflow |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-04-25 |
| Version at Verification | v0.3.7 |
| Next Review Recommended | 2026-07-25 |
| Confidence Map | Overview: high (README + WebFetch), Problem Addressed: high (README + code-read), Key Statistics: high (WebFetch 2026-04-25), Key Features: high (doc + code-read), Technical Architecture: high (code-read), Installation & Usage: high (README), Limitations: high (README), Relevance: medium (inferred from feature set) |
