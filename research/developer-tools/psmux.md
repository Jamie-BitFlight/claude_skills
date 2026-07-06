---
title: "psmux"
research_date: "2026-03-01"
source_url: "https://github.com/marlocarlo/psmux"
github_url: "https://github.com/marlocarlo/psmux"
version_at_research: "v0.4.7"
license: "MIT"
last_verified: "2026-03-01"
version_at_verification: "v0.4.7"
next_review: "2026-06-01"
---

## Overview

psmux is a native Windows terminal multiplexer built in Rust, designed as a full tmux replacement for PowerShell, Windows Terminal, and cmd.exe. It speaks the tmux command language, reads `.tmux.conf` directly, and supports tmux themes and plugins — without requiring WSL, Cygwin, or MSYS2. It ships as three executable aliases (`psmux`, `pmux`, `tmux`) so existing tmux muscle memory and scripts work unchanged on Windows.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| tmux does not run natively on Windows without WSL, Cygwin, or MSYS2 | psmux runs directly on Windows 10/11 using the ConPTY API — no Linux subsystem required |
| Windows Terminal tabs cannot persist sessions (detach/reattach) | psmux implements full session persistence with detach (`Prefix+d`) and attach (`psmux attach -t name`) |
| Existing `.tmux.conf` configs and tmux plugins break on Windows | psmux reads `~/.tmux.conf` natively and has a plugin ecosystem porting popular tmux plugins to PowerShell |
| Windows terminal tooling lacks scripting depth | psmux implements 76 tmux-compatible commands, 126+ format variables, and 15+ event hooks for automation |
| Mouse support over SSH is broken on Windows ConPTY | psmux has first-class SSH mouse support on Windows 11 build 22523+ (22H2+) |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 269 | 2026-03-01 |
| Forks | 23 | 2026-03-01 |
| Contributors | 3 | 2026-03-01 |
| Open Issues | 12 | 2026-03-01 |
| Latest Release | v0.4.7 | 2026-03-01 |
| Repository Created | 2025-11-30 | 2026-03-01 |
| Last Commit | 2026-03-01 | 2026-03-01 |

SOURCE: [marlocarlo/psmux GitHub API](https://api.github.com/repos/marlocarlo/psmux) (accessed 2026-03-01)

---

## Key Features

### tmux Compatibility

- 76 tmux commands implemented (e.g., `new-session`, `split-window`, `send-keys`, `capture-pane`)
- 126+ format variables with full modifier support
- Reads `~/.tmux.conf`, `~/.psmux.conf`, or `~/.config/psmux/psmux.conf` automatically
- `bind-key`/`unbind-key` with key tables for full keybinding customization
- 15+ event hooks (`after-new-window`, etc.)
- `if-shell` / `run-shell` for conditional config logic
- Paste buffer management, full target syntax (`session:window.pane`, `%id`, `@id`)

### Session and Pane Management

- Session persistence with detach and reattach (`psmux attach -t name`)
- Split panes horizontally and vertically
- 5 layout modes: even-h, even-v, main-h, main-v, tiled
- Pane zoom toggle (`Prefix+z`)
- Synchronized panes (broadcast input to all panes)
- 53 vim keybindings in copy/scroll mode with search and registers

### Performance (Rust, opt-level 3)

- Session creation: < 100ms for `new-session -d` to return
- New window or pane split: < 80ms overhead on top of shell startup
- Lazy pane resize: only active window's panes are resized; background windows resize on-demand
- Cached shell resolution via `OnceLock` to avoid repeated PATH lookups per spawn
- 10ms polling for client-server discovery enabling sub-100ms session attach
- 8KB reader buffers to minimize mutex contention across pane reader threads
- Stress-tested with 15+ rapid windows, 18+ panes, and 5 concurrent sessions

### Mouse Support

- Full mouse support locally on Windows 10 and Windows 11
- First-class SSH mouse support (click panes, drag-resize borders, scroll, click tabs) on Windows 11 build 22523+ (22H2+)
- Windows 10 as SSH server has a ConPTY limitation that prevents mouse-enable escape sequences from forwarding

### Plugin and Theme Ecosystem

- Plugin manager `ppm` (analogous to tpm for tmux)
- TUI plugin browser `tppanel` for installing, updating, and removing plugins
- Available plugins: `psmux-sensible`, `psmux-yank` (clipboard), `psmux-resurrect` (save/restore sessions), `psmux-pain-control`, `psmux-prefix-highlight`
- Supported themes: Catppuccin, Dracula, Nord, Tokyo Night, Gruvbox
- 14 style options, 24-bit color, text attributes in status bar

### Installation Methods

- WinGet: `winget install psmux`
- Cargo: `cargo install psmux`
- Scoop: via `psmux` bucket
- Chocolatey: `choco install psmux`
- PowerShell one-liner installer
- Manual ZIP download from GitHub Releases (x64, x86, ARM64)
- Build from source with `cargo build --release`

---

## Technical Architecture

psmux uses a client-server architecture mirroring tmux's design:

- **Server process**: manages sessions, windows, and panes; writes a discovery file before spawning the first shell so clients can connect immediately
- **Client process**: connects to the server via the discovery file; uses 10ms polling for sub-100ms attach latency
- **ConPTY integration**: uses the Windows Console Pseudoconsole API directly for PTY allocation per pane, enabling true terminal emulation without WSL
- **Rust runtime**: compiled with opt-level 3, full LTO (Link-Time Optimization), and a single codegen unit for maximum binary performance
- **Format engine**: full tmux-compatible status bar format engine with conditionals, loops, 126+ variables, and modifier support
- **Copy mode**: implemented with 53 vim keybindings using an internal buffer state machine

The three binaries (`psmux.exe`, `pmux.exe`, `tmux.exe`) are functional aliases pointing to the same implementation, enabling drop-in replacement for existing `tmux` calls in scripts and shell profiles.

---

## Installation & Usage

```powershell
# Install via WinGet (recommended for most users)
winget install psmux

# Install via Cargo (cross-platform Rust toolchain)
cargo install psmux

# Install via Scoop
scoop bucket add psmux https://github.com/marlocarlo/scoop-psmux
scoop install psmux

# Install via Chocolatey
choco install psmux

# PowerShell one-liner
irm https://raw.githubusercontent.com/marlocarlo/psmux/master/scripts/install.ps1 | iex
```

```powershell
# Start a new session (psmux, pmux, and tmux are identical)
psmux
tmux

# Start a named session
psmux new-session -s work
tmux new-session -s work

# List sessions
psmux ls

# Attach to an existing session
psmux attach -t work

# Split pane horizontally
# Prefix + %

# Split pane vertically
# Prefix + "

# Detach from session (session persists)
# Prefix + d

# Enter copy/scroll mode
# Prefix + [
```

```powershell
# Scripting example: create layout, run commands, capture output
psmux new-session -d -s build -x 220 -y 50
psmux split-window -h -t build
psmux send-keys -t build:0.0 "cargo build --release" Enter
psmux send-keys -t build:0.1 "cargo test" Enter
psmux capture-pane -t build:0.0 -p
```

```powershell
# Plugin manager setup in ~/.psmux.conf
# set -g @plugin 'psmux-plugins/ppm'
# set -g @plugin 'psmux-plugins/psmux-sensible'
# set -g @plugin 'psmux-plugins/psmux-yank'
# run '~/.psmux/plugins/ppm/ppm.ps1'
# Press Prefix + I to install declared plugins
```

---

## Relevance to Claude Code Development

### Applications

- Claude Code agents running on Windows-native environments (non-WSL) that need PTY allocation for interactive commands can use psmux as the PTY provider, analogous to how the `interactive-terminal-workarounds.md` rule recommends tmux on Linux
- The `run_in_background` and long-running command patterns documented in CLAUDE.md map directly to psmux session persistence: a background agent task can detach and reattach without process loss
- Windows CI/CD pipelines that run Claude Code agent workflows can use psmux to provide isolated PTY sessions per agent invocation

### Patterns Worth Adopting

- **Discovery-file client-server pattern**: psmux writes its server discovery file before spawning the first shell, enabling near-instant client attach. This is a general pattern for any CLI tool that needs sub-100ms IPC handshake — applicable to agent coordination scripts
- **Lazy resize on focus**: only resize the active resource (window/pane) and defer background resource updates until needed. Applicable to UI rendering in agent dashboards or terminal output panels
- **Alias binaries**: shipping `psmux.exe`, `pmux.exe`, and `tmux.exe` as identical functional aliases enables drop-in compatibility. A Claude Code skill that wraps a tool could ship a compatibility alias for an existing tool name

### Integration Opportunities

- The `interactive-terminal-workarounds.md` rule currently documents tmux for PTY provision on Linux. A parallel Windows section could reference psmux for Windows-native Claude Code deployments
- Agent workflows that use `tmux new-session -d` for background task isolation on Linux could be made cross-platform with psmux, since it accepts the same command syntax
- `capture-pane` support in psmux enables the same output-capture pattern documented in the interactive terminal workarounds rule, making it a Windows-compatible drop-in for those patterns

---

## References

- [marlocarlo/psmux GitHub Repository](https://github.com/marlocarlo/psmux) (accessed 2026-03-01)
- [psmux GitHub API metadata](https://api.github.com/repos/marlocarlo/psmux) (accessed 2026-03-01)
- [psmux v0.4.7 Release Notes](https://github.com/marlocarlo/psmux/releases/tag/v0.4.7) (accessed 2026-03-01)
- [psmux-plugins repository](https://github.com/marlocarlo/psmux-plugins) (referenced in README, accessed 2026-03-01)
- [tppanel — Tmux Plugin Panel](https://github.com/marlocarlo/tppanel) (referenced in README, accessed 2026-03-01)

---
