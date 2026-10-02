---
name: omnyssh
title: OmnySSH
subtitle: SSH server management dashboard with live metrics, terminals, SFTP, and snippets
research_date: 2026-10-02
source_url: https://github.com/timhartmann7/omnyssh
github_repository: https://github.com/timhartmann7/omnyssh
version_at_research: 1.1.4
license: Apache-2.0
freshness_tracking:
  last_verified: 2026-10-02
  version_at_verification: 1.1.4
  next_review: 2027-01-02
  confidence_map: "Overview: high | Features: high | Architecture: medium | Usage: high | Limitations: high | Relevance: medium"
---

# OmnySSH

## Overview

OmnySSH is an open-source SSH client and server management tool providing "Every server you manage, in one window." It combines a live dashboard with real-time metrics collection, multi-tab PTY terminals, two-panel SFTP file management, and command snippets with broadcast execution. Available as both a terminal user interface (TUI) and a Tauri 2-based desktop GUI, it reads existing `~/.ssh/config` without modification and requires no account or telemetry. Designed to replace tmux/ssh workflows with a cohesive visual interface while remaining lightweight (approximately 130 MB RAM with multiple sessions).

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Managing multiple SSH connections scattered across terminal tabs and tmux sessions | Unified dashboard organizing all hosts as cards with live status and one-click connection switching |
| Manual SSH key setup and secure credential management | Automated SSH key generation, `authorized_keys` configuration with rollback protection, and passphrase caching |
| Lack of visibility into remote server health | Live dashboard displaying CPU, RAM, disk usage, uptime, OS version, and top processes per host; bars turn yellow/red as thresholds breach |
| Inefficient file transfer workflows | Two-panel SFTP browser (local left, remote right) with drag-and-drop, progress bars, and bulk operations |
| Repetitive command execution across hosts | Snippets with parameter substitution; execute a single snippet across multiple selected hosts at once |
| Terminal bloat from competing tools | Single lightweight application (~20 MB download) versus Termius (~649 MB RAM, 9 processes) or scattered tmux + ssh tools |

---

## Key Features

### Live Dashboard

- Cards for every host with:
  - CPU, RAM, and disk utilization bars (visual indicators: yellow at warning level, red at critical)
  - Uptime and OS version
  - Top processes eating CPU (up to 3 processes shown)
  - Docker badge showing container count
  - Live refresh from background metrics poller
  - Streamer mode to replace real IPs with fake ones (safe for recordings/screen sharing)

### Real Terminals

- Full PTY sessions in tabs (source: `crates/omnyssh-core/src/ssh/pty.rs` — terminal emulator via vt100 screen model)
- Multi-session terminal management: open as many concurrent connections as needed
- Switch between open sessions via sidebar
- Sessions persist while working in dashboard
- Terminal search and session navigation via fuzzy search (`⌘K` or `/`)

### Two-Panel SFTP File Manager

- Local filesystem panel (left) and remote filesystem panel (right)
- Tick files and move across panels with progress indication
- Bulk operations: select multiple files at once
- Local file pane supports drive letter switching on Windows

### Snippets and Broadcast Execution

- Save frequently-used commands as reusable snippets
- Parameter substitution: `sudo systemctl restart {{service}}` prompts for `service` value at execution
- Execute a single snippet across multiple selected hosts in parallel

### Fuzzy Search

- `⌘K` or `/` to search all hosts and currently-open sessions
- Jump to terminal on selected host or resume previously-opened session
- Global command palette for navigation

### Themes

- Light and dark mode built into both TUI and GUI
- TUI supports four themes: `default`, `dracula`, `nord`, `gruvbox`
- Remappable keybindings via `config.toml` (TUI only)

### Cross-Platform Support

- **macOS**: Apple Silicon (aarch64) and Intel (x86_64); installs to `/Applications`
- **Linux**: x86_64 via AppImage, `.deb`, or `.rpm`; installs to app menu
- **Windows**: x86_64 `.exe` installer
- **TUI**: Prebuilt binaries for Linux, macOS, Windows, and Termux

---

## Technical Architecture

OmnySSH is structured as a **Rust cargo workspace with frontend-agnostic architecture**, separating the SSH engine from UI implementations.

### Workspace Structure

- **`omnyssh-core`** (library): SSH engine, configuration handling, domain events, metrics, self-updater — zero UI dependencies
  - Exportable public API enables multiple frontend implementations
  - Compiled as library depended on by both TUI and GUI
- **`omnyssh`** (TUI binary `omny`): Terminal interface using Ratatui framework, depends on `omnyssh-core`
- **`omnyssh-gui`** (GUI binary): Tauri 2 + SvelteKit desktop application with Rust IPC bridge

### Core Components (Source: `crates/omnyssh-core/src/`)

**SSH Engine (`ssh/` module)**: A native russh client (version 0.46, not OpenSSH) powers:
  - Metrics collection via remote command execution (CPU, RAM, disk, OS, process introspection)
  - SFTP file transfer via russh-sftp (version 2.0)
  - Multi-session PTY terminal emulation via vt100 screen parser
  - Local port forwarding / SSH tunneling
  - Source files: `client.rs`, `pool.rs`, `session.rs`, `sftp.rs`, `pty.rs`, `metrics.rs`

**SSH Identity & Authentication (`identity.rs`, `password.rs`, `known_hosts.rs`, `key_setup.rs`)**:
  - Identity file discovery and management
  - Password authentication with retry handling
  - Known hosts verification
  - Automated SSH key setup: generates Ed25519 key, appends to `authorized_keys`, disables password login with rollback on failure

**Configuration (`config/` module)**:
  - SSH config parser supporting `ProxyJump`, `Include` directives with glob patterns, and host aliases
  - Application config (TOML-based for TUI: themes, keybindings, snippets)
  - Source: `config/ssh_config.rs`, `config/app_config.rs`, `config/snippets.rs`

**Smart Server Context Discovery (`discovery.rs`, `services/`)**: Service detection on remote servers
  - Detects: Docker (container count), Nginx (configuration), PostgreSQL (status), Redis (connectivity), Node.js (version)
  - Source files: `services/docker.rs`, `services/nginx.rs`, `services/postgresql.rs`, `services/redis.rs`, `services/nodejs.rs`

**Event System (`event.rs`)**: Domain events for background task communication
  - Background tasks (metrics poller, SFTP, PTY sessions, discovery, updater) report via `CoreEvent` enum over `mpsc` channel
  - Event variants: `MetricsUpdate`, `HostStatusChanged`, `SftpConnected`, `PtyOutput`, `PtyExited`, `DiscoveryQuickScanDone`, `KeySetupProgress`, `KeySetupComplete`, `UpdateAvailable`
  - Frontends receive `CoreEvent` and wrap into UI event streams
  - Enables loosely-coupled frontend implementations

**Update Checker (`update.rs`): Self-updater**
  - Queries GitHub Releases API
  - Downloads, verifies SHA256, extracts, and replaces binary
  - Uses `reqwest` (Rustls TLS), `semver`, `sha2`, `flate2`, `tar`, and `self-replace` crate

### Data Flow

1. **Metrics polling**: Background task on interval → runs remote commands (cpu, df, uptime, ps) → parses stdout → emits `CoreEvent::MetricsUpdate` → frontend renders dashboard bars
2. **PTY session**: User connects to host → `Session` struct spawned → PTY child process spawned via russh channel → I/O reader thread → parses into vt100 terminal state → emits `CoreEvent::PtyOutput` when terminal updated → frontend renders terminal
3. **SFTP file transfer**: User selects files → `SftpManager` opens channel → `FileEntry` list returned → user drags across panels → progress callback emits `CoreEvent::FileTransferProgress` → progress bar updates

### Dependencies

**Core SSH & Networking**:
- `russh` (0.46): SSH client implementation with ring backend and RSA/Ed25519 support; zlib compression via flate2
- `russh-sftp` (2.0): SFTP protocol over russh channels

**Async Runtime**: `tokio` (1.x) — selectively enabled features only (rt-multi-thread, time, sync, process, fs, io-util, net)

**Serialization & Config**: `serde`, `toml` (0.8), `glob` (0.3) for SSH config `Include` patterns

**Terminal Emulation**: `vt100-omnyssh` (0.15) — screen model parser for PTY output (custom fork)

**Error Handling**: `anyhow`, `thiserror` (2.x), `async-trait`

**Utilities**: `dirs` (5), `chrono` (0.4), `tracing` (0.1)

**TUI (omnyssh crate)**: `ratatui` for terminal rendering, event loop, and widgets

**GUI (omnyssh-gui crate)**: Tauri 2, SvelteKit (Node.js 20+), Rust-JavaScript IPC bridge

### Extensibility

The workspace architecture allows new frontends to be added as crates depending on `omnyssh-core` without modifying core code. The event channel abstraction (`CoreEvent` enum) enables frontends to receive all domain events identically. SSH authentication prompts (password, passphrase) are handled via async trait objects (`async-trait`) so frontends can implement UI-specific prompts.

---

## Installation & Usage

### Desktop GUI (macOS, Linux, Windows)

**One-line installer** (auto-detects OS/architecture):

```bash
curl -fsSL https://raw.githubusercontent.com/timhartmann7/omnyssh/main/install.sh | sh
```

Optional flags:
- `--tui` — install TUI only
- `--both` — install both GUI and TUI

Installs to `/Applications` (macOS) or system app menu (Linux), or `Program Files` (Windows).

**Manual download** from [Releases](https://github.com/timhartmann7/omnyssh/releases/latest):
- macOS Apple Silicon: `OmnySSH-aarch64-apple-darwin.dmg`
- macOS Intel: `OmnySSH-x86_64-apple-darwin.dmg`
- Linux x86_64: `OmnySSH-x86_64.AppImage`, `.deb`, or `.rpm`
- Windows x86_64: `OmnySSH-x86_64-setup.exe`

### Terminal User Interface (TUI)

**Via cargo**:

```bash
cargo install omnyssh
```

**Via homebrew**:

```bash
brew install timhartmann7/tap/omnyssh
```

**Via nix**:

```bash
nix run github:timhartmann7/omnyssh
```

**Run**:

```bash
omny
```

**Keybindings** (TUI):
- `a` — add host
- `/` or `⌘K` — fuzzy search hosts and sessions
- `?` — help/keybindings
- `Shift+K` — set up SSH key on selected host
- Remappable via `~/.config/omnyssh/config.toml` (Linux), `~/Library/Application Support/omnyssh/` (macOS), `%APPDATA%\omnyssh\` (Windows)

**Configuration** (TUI):

```bash
man omny
```

— Full man page with options, keybindings, themes, and config examples.

### First Run

The app opens with an empty dashboard. It reads existing `~/.ssh/config` at startup (hosts behind `ProxyJump` bastion included) but never writes to it. Hosts are stored separately in the app's local database.

---

## Limitations and Caveats

Not mentioned in documentation.

---

## Relevance to Claude Code Development

### Applications

- **PTY multiplexing and session management** -> `AGENTS.md`
  - Term: `PTY`
  - Today: "On a TTY error (`Inappropriate ioctl for device`, `not a terminal`, `ENOTTY`), or before running any tool that requires a TTY (including `git rebase -i`/`git add -i`), read `rules/interactive-terminal-workarounds.md` for PTY providers and non-interactive equivalents."
  - Change: The interactive-terminal-workarounds skill could leverage omnyssh's PTY/terminal multiplexing patterns (vt100 screen parsing, multi-session management) to handle complex TTY requirements in AI agent orchestration workflows

- **Real-time metrics and monitoring** -> `rules/ci-workflows.md`
  - Term: `metrics`
  - Today: `Q3 -->|No — post-processing only: metrics, cache, coverage| Accept[Acceptable]`
  - Change: OmnySSH's metrics poller patterns (background tasks → structured events → UI display) could inform how CI pipeline metrics are collected and surfaced in development-harness workflows

- **Event system architecture for async communication** -> `plugins/plugin-creator/skills/hook-creator/SKILL.md`
  - Term: `event system`
  - Today: "Create hooks that integrate with the Claude Code event system. Hooks automate validation, enforcement, and context injection across the session lifecycle."
  - Change: OmnySSH's CoreEvent enum and event channel pattern (background tasks report standardized events, frontends consume via channel) parallels Claude Code's hook/event model; could inform cross-session event broadcast and loose coupling between agent subsystems

### Patterns Worth Adopting

- **Workspace-based multi-frontend architecture** -> `ARCHITECTURE.md`
  - Term: `plugins`
  - Today: "Entries are local directories under `plugins/`, plus external plugins pinned from other repositories."
  - Change: out-of-scope — claude_skills already uses directory-based workspace architecture; the library/frontends pattern OmnySSH demonstrates (core engine depended on by UI implementations) is not a direct parallel to plugin composition

### Integration Opportunities

- **SSH configuration parsing and host discovery** -> nothing in `:/plugins/ :/.claude/skills/ :/.claude/agents/ :/rules/ :/docs/ :/AGENTS.md`
  - Today: `git grep --full-name -il "SSH config" -- :/plugins/ :/.claude/skills/ :/.claude/agents/ :/rules/ :/docs/ :/AGENTS.md` → 0 matches
  - Today: `git grep --full-name -il "ssh-config" -- :/plugins/ :/.claude/skills/ :/.claude/agents/ :/rules/ :/docs/ :/AGENTS.md` → 0 matches
  - Change: If development-harness ever needs to discover and connect to remote CI/build infrastructure (for live log streaming, artifact retrieval, or distributed test execution), OmnySSH's SSH config parser (with `ProxyJump` and `Include` support) and host discovery crates could be reusable

---

## References

- [OmnySSH GitHub Repository](https://github.com/timhartmann7/omnyssh) — README, Cargo.toml workspace, core architecture (accessed 2026-10-02)
- [CONTRIBUTING.md](https://github.com/timhartmann7/omnyssh/blob/main/CONTRIBUTING.md) — workspace layout, development setup, architecture overview (accessed 2026-10-02)
- [omnyssh-core/src/lib.rs](https://github.com/timhartmann7/omnyssh/blob/main/crates/omnyssh-core/src/lib.rs) — module documentation, separation of concerns (accessed 2026-10-02)
- [omnyssh-core/src/event.rs](https://github.com/timhartmann7/omnyssh/blob/main/crates/omnyssh-core/src/event.rs) — CoreEvent enum, domain events, background task communication (accessed 2026-10-02)
- [omnyssh-core/src/ssh/mod.rs](https://github.com/timhartmann7/omnyssh/blob/main/crates/omnyssh-core/src/ssh/mod.rs) — SSH module components, russh client, metrics, SFTP, PTY, services (accessed 2026-10-02)
- [omnyssh-core/Cargo.toml](https://github.com/timhartmann7/omnyssh/blob/main/crates/omnyssh-core/Cargo.toml) — dependencies, russh version, async runtime configuration (accessed 2026-10-02)
- [Cargo.toml (root workspace)](https://github.com/timhartmann7/omnyssh/blob/main/Cargo.toml) — version 1.1.4, Rust 1.89+, workspace members (accessed 2026-10-02)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Byobu](./byobu.md) | developer-tools | Terminal multiplexer wrapper with live system metrics; directly competes in unified server management space |
| [Tmuxp](./tmuxp.md) | developer-tools | Declarative tmux workspace configuration tool; shares multi-session orchestration and layout automation patterns |
| [Libtmux](./libtmux.md) | developer-tools | Python ORM wrapper over tmux; enables programmatic session control complementary to OmnySSH's terminal management |
| [Dtach](./dtach.md) | developer-tools | Session detachment and persistence daemon; lightweight alternative for long-running process attachment patterns |
| [Shpool](./shpool.md) | developer-tools | Lightweight session multiplexer; shares persistence and multi-host terminal aggregation goals |
| [Tori-cli](./tori-cli.md) | developer-tools | Host metrics collection tool; complements OmnySSH's live dashboard observability features |
| [Sidecar](./sidecar.md) | developer-tools | Plugin-based terminal session manager; shares event-driven architecture and terminal UI patterns |
| [Psmux](./psmux.md) | developer-tools | Process multiplexer with tmux compatibility layer; alternative multiplexing approach for process orchestration |
