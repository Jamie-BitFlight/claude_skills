---
title: "shpool"
research_date: "2026-03-01"
source_url: "https://github.com/shell-pool/shpool"
github_url: "https://github.com/shell-pool/shpool"
version_at_research: "v0.9.3"
license: "Apache License 2.0"
last_verified: "2026-03-01"
version_at_verification: "v0.9.3"
next_review: "2026-06-01"
---

## Overview

shpool is a lightweight shell session persistence daemon written in Rust that keeps named shell sessions alive when SSH connections drop. Unlike tmux or GNU screen, shpool does not multiplex or intercept terminal rendering — it passes raw bytes directly to the local terminal, preserving native scrollback and copy-paste behavior. The tool is designed for developers who want reconnectable remote sessions without the overhead or terminal quirks introduced by full multiplexers.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| SSH connection drops lose the running shell session and all in-flight work | shpool daemon retains ownership of named shell subprocesses; reconnecting with `shpool attach <name>` resumes the exact session |
| tmux and screen break native terminal scrollback and copy-paste | shpool passes raw shell output bytes to the local terminal, so the local terminal state machine handles all rendering natively |
| tmux re-rendering obscures what happened while disconnected | shpool maintains an in-memory VT100 render via the `shpool_vt100` crate and replays it on reattach, including output generated while disconnected |
| Determining which shpool session you are in is unclear | shpool auto-injects a prompt prefix (`shpool:$SHPOOL_SESSION_NAME`) for bash, zsh, and fish without any user configuration |
| Freezing connections block reattach | `shpool detach <name>` forces session detach so a new client can attach |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 1,707 | 2026-03-01 |
| Forks | 41 | 2026-03-01 |
| Contributors | 12 | 2026-03-01 |
| Open Issues | 36 | 2026-03-01 |
| Latest Release | v0.9.3 | 2025-11-19 |
| Primary Language | Rust | 2026-03-01 |
| Repo Created | 2024-02-28 | 2026-03-01 |

---

## Key Features

### Session Persistence

- Named sessions owned by the `shpool` daemon process survive connection drops
- Sessions addressable by arbitrary user-chosen names (e.g., `main`, `edit`, `build`)
- `--ttl` flag on `shpool attach` limits session lifetime
- Single-client-per-session model (no shared sessions, by design)

### Native Terminal Rendering

- All shell output bytes passed directly to the client terminal — no intermediate in-memory terminal re-rendering during normal operation
- Local terminal handles scrollback, copy-paste, and color rendering natively
- Avoids the rendering discrepancies introduced by tmux's virtual terminal layer

### Screen Restoration on Reattach

- Maintains a continuously updated in-memory VT100 render via the [`shpool_vt100`](https://crates.io/crates/shpool_vt100) crate
- Three configurable `session_restore_mode` values: `"screen"` (default, fills current terminal with prior output), `"simple"` (only SIGWINCH to prompt ncurses apps to redraw), `{ lines = n }` (restore last n lines up to `output_spool_lines` limit)
- Output generated while no client was connected is captured and shown on reattach

### Daemon Architecture

- Runs as a background daemon (typically via systemd user service)
- Autodaemonization: if no daemon is detected, shpool forks one automatically before attaching (enabled by default, controlled by `nodaemonize` config or `-d/-D` flags)
- Unix socket-based IPC between client and daemon
- systemd socket activation supported via `shpool.socket` unit file

### Shell Integration

- Auto-detects bash, zsh, and fish and injects a configurable prompt prefix
- `$SHPOOL_SESSION_NAME` environment variable available in-session for custom prompt hooks
- `huponexit` bash option recommended to clean up background processes on session exit

### SSH Workflow Integration

- Designed for use with standard SSH — no special client software required on the connecting machine
- `RemoteCommand` SSH config option enables automatic session attachment on connect
- Supports session naming by local TTY number for automatic per-window sessions
- Custom shell function pattern (`shpool-ssh`) for interactive session selection

### Configuration

- TOML config at `~/.config/shpool/config.toml`
- Configurable: prompt prefix, session restore mode, detach keybinding, initial directory, output spool line count, nodaemonize behavior
- Detach keybinding defaults to `Ctrl-Space Ctrl-q`; remappable via `[[keybinding]]` table entries

### Subcommands

- `shpool daemon` — run in daemon mode (invoked by systemd, rarely called directly)
- `shpool attach <name>` — create or reconnect to named session
- `shpool detach [name]` — detach from session without killing it
- `shpool list` — enumerate active sessions
- `shpool kill <name>` — terminate a named session

---

## Technical Architecture

shpool operates as a client-daemon pair communicating over a Unix socket.

```text
Client (shpool attach)
        |
        | Unix socket IPC
        v
Daemon (shpool daemon)
        |
        +---> Named session table
               |
               +---> Subshell process (bash/zsh/fish)
               |         |
               |         | raw bytes (stdout/stderr)
               |         v
               +---> shpool_vt100 in-memory VT100 render (for reattach replay)
               |
               +---> raw bytes forwarded to client terminal
```

Key design decisions:

- **No terminal multiplexing**: the daemon does not run a virtual terminal during active sessions; bytes flow through with no re-rendering
- **VT100 state tracking**: despite no live multiplexing, the `shpool_vt100` crate tracks terminal state continuously so reattach can replay the screen
- **Process ownership**: the daemon holds the shell process, not the SSH connection; the SSH process can die without killing the shell
- **Minimum Rust version**: 1.74.0 (as of v0.9.3)
- **Platform support**: Linux (primary, full test coverage); macOS (partial, some tests disabled)

---

## Installation & Usage

```bash
# Install from crates.io
cargo install shpool

# Set up systemd user service (Linux with systemd)
curl -fLo "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/shpool.service" \
  --create-dirs \
  https://raw.githubusercontent.com/shell-pool/shpool/master/systemd/shpool.service
sed -i "s|/usr|$HOME/.cargo|" \
  "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/shpool.service"
curl -fLo "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/shpool.socket" \
  --create-dirs \
  https://raw.githubusercontent.com/shell-pool/shpool/master/systemd/shpool.socket
systemctl --user enable shpool
systemctl --user start shpool
loginctl enable-linger
```

```bash
# Create or reconnect to a named session
shpool attach main

# List active sessions
shpool list

# Detach from current session (from inside a session)
shpool detach

# Force-detach a session by name (from outside)
shpool detach main

# Kill a session
shpool kill main
```

```text
# SSH config for automatic attach (~/.ssh/config on client)
Host = main edit
    Hostname remote.host.example.com
    RemoteCommand shpool attach -f %k
    RequestTTY yes
```

```toml
# ~/.config/shpool/config.toml — example configuration
prompt_prefix = "[$SHPOOL_SESSION_NAME]"
session_restore_mode = "screen"

[[keybinding]]
binding = "Ctrl-a d"
action = "detach"
```

---

## Relevance to Claude Code Development

### Applications

- Claude Code agents frequently run inside remote SSH sessions. Using shpool on the remote host means a dropped SSH connection does not kill a long-running agent task — the agent process survives inside the shpool session and can be reattached to observe output
- The `shpool list` + `shpool attach` workflow maps directly to the pattern of resuming work across interrupted development sessions without losing terminal context

### Patterns Worth Adopting

- **Named session taxonomy**: shpool's named-session model (one name per logical task, e.g., `main`, `build`, `test`) is a transferable pattern for any long-running process management system
- **Autodaemonization**: shpool's on-demand daemon forking (fork if missing, otherwise connect) is a clean pattern for tools that need a background service without requiring manual service management from users
- **Screen replay from in-memory VT state**: maintaining a VT100 render separately from the live data path solves the "what happened while I was gone" problem without imposing rendering overhead during normal operation — applicable to any buffered output capture system

### Integration Opportunities

- Claude Code skill execution via `shpool attach` would allow `/implement-feature` agent runs to survive network interruptions during long multi-task execution loops
- A wrapper skill could automate `shpool attach <feature-slug>` at the start of each agent delegation and `shpool list` for status checks, providing resilient subagent execution environments
- The `$SHPOOL_SESSION_NAME` environment variable pattern could be adapted for Claude Code session context injection (e.g., injecting the current task ID into the shell environment automatically)

---

## References

- [shpool GitHub Repository](https://github.com/shell-pool/shpool) (accessed 2026-03-01)
- [shpool README](https://github.com/shell-pool/shpool/blob/master/README.md) (accessed 2026-03-01)
- [shpool CONFIG.md](https://github.com/shell-pool/shpool/blob/master/CONFIG.md) (accessed 2026-03-01)
- [shpool HACKING.md](https://github.com/shell-pool/shpool/blob/master/HACKING.md) (accessed 2026-03-01)
- [shpool_vt100 crate on crates.io](https://crates.io/crates/shpool_vt100) (accessed 2026-03-01)
- [GitHub API — shell-pool/shpool](https://api.github.com/repos/shell-pool/shpool) (accessed 2026-03-01)
- [GitHub Releases — v0.9.3](https://github.com/shell-pool/shpool/releases/tag/v0.9.3) (accessed 2026-03-01)

---
