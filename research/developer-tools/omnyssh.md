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
  confidence_map: "Overview: high | Problem Addressed: high | Features: high | Architecture: medium (code-read) | Usage: high | Limitations: low"
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
| Inefficient file transfer workflows | Two-panel SFTP browser (local left, remote right) with progress bars and bulk operations; select files and move across panels |
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

- Full PTY sessions in tabs (source: `crates/omnyssh-core/src/ssh/pty.rs` — `PtyManager`, `feed_parser`; vt100 screen model)
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

OmnySSH is structured as a **Rust cargo workspace with frontend-agnostic architecture**, separating the SSH engine from UI implementations. All source citations below are against tag `v1.1.4` (accessed 2026-10-03).

### Workspace Structure

- **`omnyssh-core`** (library): SSH engine, configuration handling, domain events, self-updater — its crate documentation states that nothing in it "may depend on terminal-rendering, input, or CLI crates". Source: `crates/omnyssh-core/src/lib.rs` — `pub mod config`, `pub mod event`, `pub mod ssh`, `pub mod update`, `pub mod utils`; `Cargo.toml` — `members = ["crates/omnyssh-core", "crates/omnyssh", "crates/omnyssh-gui"]`
  - Compiled as a library depended on by both TUI and GUI. Source: `crates/omnyssh/Cargo.toml` — `omnyssh-core = { path = "../omnyssh-core" }`, `crates/omnyssh-gui/Cargo.toml` — `omnyssh-core = { path = "../omnyssh-core" }`
- **`omnyssh`** (TUI binary `omny`): terminal interface using Ratatui. Source: `crates/omnyssh/Cargo.toml` — `[[bin]] name = "omny"`, `ratatui = "0.29"`
- **`omnyssh-gui`** (GUI binary): Tauri 2 + SvelteKit desktop application with a Rust bridge to the core. Source: `crates/omnyssh-gui/Cargo.toml` — `tauri = { version = "2", ... }`, `crates/omnyssh-gui/src/bridge.rs`, `crates/omnyssh-gui/ui/package.json` — `@sveltejs/kit`
- The workspace excludes the GUI from bare `cargo build`. Source: `Cargo.toml` — `default-members = ["crates/omnyssh-core", "crates/omnyssh"]`

### Core Components (Source: `crates/omnyssh-core/src/`)

**SSH Engine (`ssh/` module)**: a native `russh` client (version 0.46, not OpenSSH) powers the items below. Source: `crates/omnyssh-core/Cargo.toml` — `russh = "0.46"`, `russh-sftp = "2.0"`, `crates/omnyssh-core/src/ssh/session.rs` — `SshSession::connect`, `SshSession::run_command`, `SshSession::open_sftp_channel`

- Metrics collection via remote command execution: `PollManager` starts one poller task per host and each poll runs `CPU_CMD`, `MEM_CMD`, `DISK_CMD`, `UPTIME_CMD` and a process-listing command through `run_command`. Source: `crates/omnyssh-core/src/ssh/pool.rs` — `PollManager::start`, `run_host_poller`, `crates/omnyssh-core/src/ssh/metrics.rs` — `parse_cpu_top`, `parse_ram_free`, `parse_disk_df`, `parse_uptime`, `parse_top_processes`, `threshold_level`
- SFTP file transfer via `russh-sftp`. Source: `crates/omnyssh-core/src/ssh/sftp.rs` — `SftpManager`, `SftpCommand`, `FileEntry`, `list_local_dir`
- Multi-session PTY terminals: `PtyManager::open` requests a remote PTY on a russh channel; output is fed to a `vt100::Parser`. Source: `crates/omnyssh-core/src/ssh/pty.rs` — `PtyManager`, `feed_parser`
- Local port forwarding. Source: `crates/omnyssh-core/src/ssh/tunnel.rs` — `TunnelManager`, `LocalForward`
- `ProxyJump` chain resolution. Source: `crates/omnyssh-core/src/ssh/jump.rs` — `resolve_chain`
- Host and connection-state types. Source: `crates/omnyssh-core/src/ssh/client.rs` — `Host`, `MonitorMode`, `ConnectionStatus`

**SSH Identity & Authentication**:

- Passphrase handling for encrypted keys: Source: `crates/omnyssh-core/src/ssh/identity.rs` — `IdentityError`, `ask_passphrase`, `unlock`
- Password authentication with retry flag: a `Prompter` sends `CoreEvent::PasswordRequired` (which carries a `retry` field) and waits for `answer`. Source: `crates/omnyssh-core/src/ssh/password.rs` — `Prompter`, `answer`, `PasswordError`
- Known hosts verification against `~/.ssh/known_hosts`. Source: `crates/omnyssh-core/src/ssh/known_hosts.rs` — `check`, `learn` (both `pub(crate)`), `crates/omnyssh-core/src/ssh/session.rs` — `KnownHostsHandler`
- Automated SSH key setup: Ed25519 is the only `KeyType` variant; the flow is a step state machine with commands that append to `authorized_keys`, disable password login, reload sshd, and roll back. Source: `crates/omnyssh-core/src/ssh/key_setup.rs` — `KeyType`, `KeySetupMachine`, `generate_key_pair`, `build_authorized_keys_command`, `build_disable_password_command`, `build_reload_sshd_command`, `build_rollback_command`, `setup_key_for_host`

**Configuration**:

- SSH config parser: reads `ProxyJump`, `IdentityFile`, `LocalForward`, `Include` and other directives; `Include` recursion is limited to 3 levels and glob patterns come from the `glob` crate. Source: `crates/omnyssh-core/src/config/ssh_config.rs` — `parse_ssh_config`, `load_from_file`, `crates/omnyssh-core/Cargo.toml` — `glob = "0.3"`
- Application config (TOML): themes, keybindings, auto key-setup and update settings. Source: `crates/omnyssh-core/src/config/app_config.rs` — `AppConfig`, `UiConfig`, `KeybindingsConfig`, `UpdateConfig`, `load_app_config`
- Snippets persisted as a TOML file. Source: `crates/omnyssh-core/src/config/snippets.rs` — `Snippet`, `SnippetsFile`, `load_snippets`, `save_snippets`
- Host list load/save. Source: `crates/omnyssh-core/src/config/mod.rs` — `load_hosts`, `save_hosts`, `load_all_hosts`

**Smart Server Context Discovery**: one SSH command runs a probe script; the output is parsed into named sections and each provider checks those sections. Source: `crates/omnyssh-core/src/ssh/discovery.rs` — `quick_scan`, `crates/omnyssh-core/src/ssh/probe.rs` — `generate_quick_scan_script`, `ProbeOutput`, `crates/omnyssh-core/src/ssh/services/mod.rs` — `ServiceProvider`, `ServiceRegistry`

- Providers for Docker, Nginx, PostgreSQL, Redis and Node.js detect service presence from the probe's `SERVICES`, `PROCESS` and `LISTEN` sections (for example, PostgreSQL by a `postgresql` service or port 5432, Redis by port 6379 or a `redis` process, Node.js by a `node` process). Source: `crates/omnyssh-core/src/ssh/services/postgresql.rs` — `PostgreSQLProvider`, `.../redis.rs` — `RedisProvider`, `.../nodejs.rs` — `NodeJSProvider`, `.../nginx.rs` — `NginxProvider`
- Only the Docker provider's inspected code emits metrics (`containers_total`, `containers_running`). Source: `crates/omnyssh-core/src/ssh/services/docker.rs` — `DockerProvider`, `crates/omnyssh-core/src/ssh/services/mod.rs` — `metric_int`

**Event System (`event.rs`)**: domain events for background task communication. Source: `crates/omnyssh-core/src/event.rs` — `CoreEvent`, `Metrics`, `DetectedService`

- Background tasks (metrics poller, SFTP, PTY sessions, discovery, tunnels, key setup, updater) report via the `CoreEvent` enum over an `mpsc` channel; the GUI's shared state holds a `mpsc::Sender<CoreEvent>`. Source: `crates/omnyssh-core/src/event.rs` — `CoreEvent`, `crates/omnyssh-core/src/ssh/pool.rs` — `PollManager::start`, `crates/omnyssh-gui/src/state.rs` — `engine_tx: mpsc::Sender<CoreEvent>`
- Event variants include `MetricsUpdate`, `HostStatusChanged`, `FileTransferProgress`, `SftpConnected`, `PtyOutput`, `PtyExited`, `DiscoveryQuickScanDone`, `TunnelStatusChanged`, `KeySetupProgress`, `KeySetupComplete`, `PasswordRequired`, `UpdateAvailable`. Source: `crates/omnyssh-core/src/event.rs` — `CoreEvent`

**Update Checker (`update.rs`)**: self-updater.

- Queries the GitHub Releases API (`releases/latest`), downloads the archive, verifies a SHA256 checksum, extracts the binary from a gzip tarball, and replaces the running binary. Source: `crates/omnyssh-core/src/update.rs` — `check`, `perform_update`, `verify_checksum`, `extract_binary`, `install_binary`
- Uses `reqwest` (Rustls TLS), `semver`, `sha2`, `flate2`, `tar`, and `self-replace`. Source: `crates/omnyssh-core/Cargo.toml` — `reqwest = { version = "0.12", default-features = false, features = ["rustls-tls", "json"] }`, `self-replace = "1"`

### Data Flow

1. **Metrics polling**: `PollManager::start` spawns a poller task per host on an interval → `run_host_poller` runs remote commands (top, free or vm_stat, df, uptime, ps) → the `parse_*` functions turn stdout into `Metrics` → `CoreEvent::MetricsUpdate` is sent → frontend renders dashboard bars. Source: `crates/omnyssh-core/src/ssh/pool.rs` — `PollManager::start`, `run_host_poller`, `crates/omnyssh-core/src/ssh/metrics.rs` — `parse_cpu_top`, `parse_disk_df`, `crates/omnyssh-core/src/event.rs` — `CoreEvent::MetricsUpdate`
2. **PTY session**: the frontend calls `PtyManager::open` → a session task owns a russh channel on which a remote PTY and shell are requested → bytes read from `channel.wait()` are fed to a `vt100::Parser` shared as `Arc<Mutex<vt100::Parser>>` → `CoreEvent::PtyOutput(id)` is sent when output arrives → frontend reads the parser state and renders it. Source: `crates/omnyssh-core/src/ssh/pty.rs` — `PtyManager::open`, `PtyManager::parser_for`, `feed_parser`, `crates/omnyssh-core/src/event.rs` — `CoreEvent::PtyOutput`
3. **SFTP file transfer**: a frontend sends `SftpCommand` values to `SftpManager::send` → the manager runs them over an SFTP channel and returns `FileEntry` lists via `CoreEvent::FileDirListed` → transfers report `CoreEvent::FileTransferProgress(transfer_id, done, total)` → progress bar updates. Source: `crates/omnyssh-core/src/ssh/sftp.rs` — `SftpManager::send`, `SftpCommand`, `FileEntry`, `crates/omnyssh-core/src/event.rs` — `CoreEvent::FileTransferProgress`, `CoreEvent::FileDirListed`

### Dependencies

Source for every version below: `Cargo.toml` (workspace) — `[workspace.dependencies]`, and `crates/omnyssh-core/Cargo.toml` — `[dependencies]`, both at tag `v1.1.4`.

**Core SSH & Networking**:
- `russh` (0.46) and `russh-keys` (0.46): SSH client and key handling
- `russh-sftp` (2.0): SFTP protocol over russh channels

**Async Runtime**: `tokio` (1.x) — workspace features `macros`, `rt-multi-thread`, `time`, `sync`, `process`, `fs`, `io-util`; `omnyssh-core` adds `net`

**Serialization & Config**: `serde`, `toml` (0.8), `glob` (0.3) for SSH config `Include` patterns

**Terminal Emulation**: `vt100-omnyssh` (0.15) — screen model parser for PTY output (a package renamed to `vt100` in `omnyssh-core/Cargo.toml`: `vt100 = { package = "vt100-omnyssh", version = "0.15" }`)

**Error Handling**: `anyhow`, `thiserror` (2.x), `async-trait` (0.1)

**Utilities**: `dirs` (5), `chrono` (0.4), `tracing` (0.1)

**TUI (omnyssh crate)**: `ratatui` (0.29). Source: `crates/omnyssh/Cargo.toml`

**GUI (omnyssh-gui crate)**: Tauri 2, SvelteKit. Source: `crates/omnyssh-gui/Cargo.toml` — `tauri = { version = "2", ... }`, `crates/omnyssh-gui/ui/package.json`

### Extensibility

- Frontends depend on `omnyssh-core` and the core does not depend on them: the TUI and GUI crates each declare `omnyssh-core` as a path dependency. Source: `crates/omnyssh-core/src/lib.rs` — crate-level doc comment, `crates/omnyssh/Cargo.toml` — `omnyssh-core`, `crates/omnyssh-gui/Cargo.toml` — `omnyssh-core`
- Frontends receive domain events through the `CoreEvent` enum. Source: `crates/omnyssh-core/src/event.rs` — `CoreEvent`
- Password prompts are routed through events rather than a frontend-implemented trait: `Prompter` sends `CoreEvent::PasswordRequired` and the frontend replies by calling `password::answer(request_id, password)`. The `AskPassword` trait that `Prompter` implements is `pub(crate)`. Source: `crates/omnyssh-core/src/ssh/password.rs` — `Prompter`, `answer`, `AskPassword`; passphrase prompts use `CoreEvent::KeyPassphraseRequired` in the same way. Source: `crates/omnyssh-core/src/ssh/identity.rs` — `ask_passphrase`, `unlock`

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

The app opens with an empty dashboard. It reads existing `~/.ssh/config` at startup (hosts behind `ProxyJump` bastion included) but never writes to it. Manually added hosts are stored in the application's local configuration (source: README, no details on storage mechanism provided).

---

## Limitations and Caveats

**Documented caveats** (Source: README):
- **No confirmation step in SSH key setup flow**: When initiating the automated SSH key setup process (`Set up SSH key` button), "starting the flow means going through with it" — there is no intermediate confirmation prompt to cancel the operation after it begins. The server's `sshd_config` backup is created and password login is disabled with rollback protection, but the user cannot interrupt the flow once started.

**Undocumented limitations**: The reviewed sources (README, CONTRIBUTING.md, crate documentation) document no additional limitations on compatibility, deployment environments, authentication methods, or operational constraints. (Confidence: low — absence of documented limitations does not confirm absence of limitations.)

---

## References

- [OmnySSH GitHub Repository](https://github.com/timhartmann7/omnyssh) — README, Cargo.toml workspace, core architecture (accessed 2026-10-02)
- [CONTRIBUTING.md](https://github.com/timhartmann7/omnyssh/blob/main/CONTRIBUTING.md) — workspace layout, development setup, architecture overview (accessed 2026-10-02)
- [omnyssh-core/src/lib.rs](https://github.com/timhartmann7/omnyssh/blob/main/crates/omnyssh-core/src/lib.rs) — module documentation, separation of concerns (accessed 2026-10-02)
- [omnyssh-core/src/event.rs](https://github.com/timhartmann7/omnyssh/blob/main/crates/omnyssh-core/src/event.rs) — CoreEvent enum, domain events, background task communication (accessed 2026-10-02)
- [omnyssh-core/src/ssh/](https://github.com/timhartmann7/omnyssh/tree/main/crates/omnyssh-core/src/ssh) — SSH module: client.rs, pool.rs, session.rs, sftp.rs, pty.rs, metrics.rs, discovery.rs, services/, identity.rs, password.rs, known_hosts.rs, key_setup.rs (accessed 2026-10-02)
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
