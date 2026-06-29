---
title: "Byobu"
research_date: "2026-03-01"
source_url: "https://byobu.org"
github_url: "https://github.com/dustinkirkland/byobu"
version_at_research: "6.14"
license: "GNU General Public License v3.0"
last_verified: "2026-03-01"
version_at_verification: "6.14"
next_review: "2026-06-01"
---

## Overview

Byobu is a GPLv3 open source text-based window manager and terminal multiplexer that layers
enhanced profiles, convenient keybindings, configuration utilities, and toggle-able system
status notifications on top of either GNU Screen or tmux. Originally created by Dustin Kirkland
to make Ubuntu servers more productive, it works across most Linux, BSD, and macOS distributions.
Rather than replacing the underlying multiplexer, byobu acts as a polished interface layer that
makes tmux or screen immediately useful without manual configuration.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| tmux and GNU screen have steep configuration curves — bare installs require significant `.tmux.conf` authoring before they are usable | Byobu ships a complete, opinionated configuration with sane defaults so users get a productive environment immediately after install |
| Multiplexer keybindings are cryptic and hard to remember (e.g., `Ctrl-b "` for a split) | Function-key bindings (F2 new window, F3/F4 navigate, Shift-F2 horizontal split) are discoverable and consistent |
| Remote server state (CPU, memory, disk, network, uptime, updates) requires running separate commands | Status bar plugins display live system metrics directly in the terminal — no separate monitoring tool needed |
| Sessions are lost when SSH connections drop | Persistent tmux/screen sessions survive disconnections; byobu can auto-launch on SSH login |
| Switching between tmux and screen requires learning two different configurations | Byobu provides a unified keybinding layer; backend can be selected once via `byobu-select-backend` |
| Split-pane layouts are lost when sessions end | `Ctrl-Shift-F8` saves layout; `Alt-Shift-F8` restores it |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 1,507 | 2026-03-01 |
| GitHub Forks | 133 | 2026-03-01 |
| Contributors | 59 | 2026-03-01 |
| Open Issues | 4 | 2026-03-01 |
| Latest Release | 6.14 | 2026-03-01 |
| Release Date | 2026-02-15 | 2026-03-01 |
| Repository Created | 2013-01-15 | 2026-03-01 |
| Primary Language | Shell | 2026-03-01 |

SOURCE: [GitHub API — dustinkirkland/byobu](https://api.github.com/repos/dustinkirkland/byobu) (accessed 2026-03-01)

---

## Key Features

### Session and Window Management

- F2 creates a new window; F3/F4 navigate between windows; Alt-Left/Right also moves between windows
- Ctrl-F2 creates a vertical split; Shift-F2 creates a horizontal split
- Ctrl-Shift-F2 creates a new session; Alt-Up/Down navigates between sessions
- F6 detaches the session and logs out; Shift-F6 detaches without logging out
- Shift-F7 saves scrollback history to a file; F7 enters scrollback mode with Alt-PageUp/Down navigation

### Pane and Layout Control

- Shift-arrow keys move focus between splits; Shift-Alt-arrow keys resize splits
- Ctrl-F6 kills the focused split pane
- Shift-F8 cycles through split arrangements; Ctrl-Shift-F8 saves the current layout; Alt-Shift-F8 restores it
- Alt-F11 expands a split to a full window; Shift-F11 zooms into/out of a split; Ctrl-F11 joins a window as a vertical split

### Status Bar Notification System

Byobu ships 40+ status plugins that display live system data in the terminal status bar.
Each plugin is an independent shell script in `/usr/lib/byobu/`. Plugins are individually
enabled/disabled and cycle-able with Shift-F5.

Enabled by default (tmux right bar):

- `raid` — RAID array health
- `reboot_required` — pending reboot indicator (Ubuntu/Debian)
- `updates_available` — package update count
- `uptime` — system uptime
- `load_average` — 1/5/15-minute load averages
- `cpu_count` — logical CPU count
- `cpu_freq` — current CPU frequency
- `memory` — RAM usage
- `disk` — disk usage
- `date` / `time` — current date and time

Available but disabled by default:

- `network` — network throughput (bytes/sec in/out)
- `disk_io` — disk I/O throughput
- `battery` — battery charge and charging state
- `wifi_quality` — WiFi signal strength
- `cpu_temp` — CPU temperature
- `fan_speed` — fan RPM
- `entropy` — kernel entropy pool size
- `processes` — running process count
- `packages` — installed package count
- `mail` — unread mail count
- `users` — logged-in user count
- `ip_address` / `hostname` / `whoami` — identity information
- `custom` — user-defined status script hook
- `time_utc` / `time_binary` — alternate time formats
- `apport` — crash report indicator
- `services` — systemd service health
- `swap` — swap usage
- `trash` — trash directory size
- `distro` / `release` / `arch` / `logo` — OS identity indicators

### Configuration and Customization

- F9 opens `byobu-config`, a newt-based (text UI) configuration menu for toggling status plugins and key bindings
- F5 reloads the profile and refreshes the status bar
- Ctrl-Shift-F5 randomizes the status bar color
- Shift-F5 cycles through multiple tmux right-bar configurations (user can define multiple `tmux_right=` lines)
- Alt-F5 toggles UTF-8 support
- Ctrl-F5 reconnects SSH, GPG, and D-Bus agent sockets (useful after reconnecting to a detached session)
- User overrides go in `$HOME/.byobu/` (or `$XDG_CONFIG_HOME/byobu/`); system defaults in `/usr/share/byobu/`
- `BYOBU_PYTHON` environment variable selects the Python interpreter for status scripts

### Keyboard Broadcast and Multi-Window Operations

- Ctrl-F9 runs a command in all windows simultaneously
- Shift-F9 runs a command in all splits simultaneously
- Alt-F9 toggles keyboard input broadcast to all panes (mirrors keystrokes)

### Backend Flexibility

- `byobu-select-backend` switches between tmux and GNU screen backends
- `byobu-tmux` and `byobu-screen` wrappers invoke the selected backend with byobu's profile applied
- Keybinding layer is consistent regardless of backend; F12 provides the native escape sequence passthrough
- Shift-F12 toggles byobu's keybindings off entirely, exposing raw tmux/screen bindings

### Auto-Launch and SSH Integration

- Can be configured to launch automatically on SSH login via `byobu-enable` / `byobu-disable`
- `byobu-launch` script integrates with shell profile for automatic attachment to existing sessions
- Sessions persist through SSH disconnects — reconnecting resumes the exact session state

---

## Technical Architecture

Byobu is implemented as a collection of Shell scripts organized around three layers:

```text
User Terminal (SSH or local)
        |
        v
    byobu launcher
    (byobu-launch, byobu-tmux, or byobu-screen)
        |
        v
    Backend multiplexer (tmux >= 1.5 or GNU Screen)
    with byobu's profile loaded via -f flag
        |
        |---> /usr/share/byobu/profiles/  (tmux/screen config profiles)
        |---> /usr/share/byobu/keybindings/  (F-key → tmux/screen binding mappings)
        |---> /usr/share/byobu/status/status  (enabled/disabled plugin list)
        |
        v
    Status update loop (every N seconds)
        |
        v
    /usr/lib/byobu/{plugin}  (individual status scripts, one per metric)
        |
        v
    Status bar rendered by tmux/screen using plugin output strings
```

Key architectural decisions:

- Each status plugin is an independent Shell script that outputs a formatted string; byobu concatenates them into the status bar
- Plugin enable/disable state is stored in `$HOME/.byobu/status` as a plain-text file (`plugin_name=0` or `plugin_name=1`)
- Profiles use tmux's `-f` flag to load a custom config file without modifying the user's `~/.tmux.conf`
- Keybindings are defined per backend (separate files for tmux and screen) mapping F-keys to the backend's native key sequences
- The `include` script in `/usr/lib/byobu/` provides shared shell functions used by all status plugins (color formatting, unit conversions, etc.)
- Python is used for certain status plugins requiring more complex parsing (e.g., `updates_available`, `packages`); the interpreter is configurable via `BYOBU_PYTHON`
- `byobu-config` uses the `python-newt` library to render a text UI configuration dialog within the terminal

---

## Installation & Usage

```bash
# Ubuntu / Debian
sudo apt install byobu

# macOS (Homebrew)
brew install byobu

# From source (requires tmux >= 1.5 and autoconf/automake)
git clone https://github.com/dustinkirkland/byobu.git
cd byobu
./autogen.sh
./configure --prefix=/usr --sysconfdir=/etc
make
sudo make install

# Non-root local install
./configure --prefix="$HOME/byobu"
make install
echo 'export PATH="$HOME/byobu/bin:$PATH"' >> ~/.bashrc
```

```bash
# Start byobu
byobu

# Select tmux or screen as backend
byobu-select-backend

# Enable auto-launch on SSH login
byobu-enable

# Disable auto-launch
byobu-disable

# Open configuration TUI (also F9 inside byobu)
byobu-config

# Explicitly use tmux backend
byobu-tmux

# Explicitly use screen backend
byobu-screen
```

```bash
# Essential keybindings (tmux backend)
# F2           — new window
# F3 / F4      — previous / next window
# Ctrl-F2      — new vertical split
# Shift-F2     — new horizontal split
# Shift-F3/F4  — move between splits
# F6           — detach session + logout
# Shift-F6     — detach without logout
# F7           — enter scrollback history
# F9           — open byobu-config
# Shift-F12    — toggle byobu keybindings on/off
```

```bash
# Docker testing (from 6.14 release notes)
docker build -t byobu:6.14 -f testing/docker/Dockerfile.ubuntu .
docker run -it --rm byobu:6.14
```

---

## Relevance to Claude Code Development

### Applications

- Claude Code agents running inside tmux sessions (a common pattern) benefit from byobu as a session manager — it provides persistent sessions, split panes for multiple agent contexts, and status bar visibility into system resource consumption during heavy agent workloads
- The status bar's `updates_available`, `reboot_required`, `memory`, `load_average`, and `disk` plugins surface system health information that can indicate when a development environment is under stress (memory pressure, stale packages, pending reboots) without leaving the terminal
- The existing research entry [using-tmux-with-claude-code.md](./using-tmux-with-claude-code.md) documents tmux integration patterns; byobu is a direct enhancement of that workflow

### Patterns Worth Adopting

- Byobu's plugin architecture for the status bar — each metric is an independent shell script with a defined output contract — is a clean pattern for building composable monitoring dashboards in shell-based tools
- The `custom` status plugin (a user-defined hook script at `$HOME/.byobu/bin/custom`) demonstrates how to expose extension points in a shell tool without modifying core code
- The separation of user config (`$HOME/.byobu/`) from system defaults (`/usr/share/byobu/`) with clean override semantics is a reusable configuration layering pattern
- Shift-F5 cycling through multiple `tmux_right=` status bar configurations shows a low-complexity approach to multi-view dashboards in constrained display contexts

### Integration Opportunities

- A byobu status plugin could display Claude Code session status (active agent, task count, last activity) directly in the terminal status bar — the plugin API requires only a shell script that outputs a formatted string
- The `byobu-launch` auto-attach pattern could be adapted to automatically attach Claude Code agents to existing tmux sessions when re-entering a development environment
- The keyboard broadcast feature (Alt-F9, Ctrl-F9, Shift-F9) mirrors keystrokes/commands across panes — analogous to the multi-agent command fan-out pattern in Claude Code orchestration

---

## References

- [byobu.org — Official Site](https://byobu.org) (accessed 2026-03-01)
- [GitHub — dustinkirkland/byobu](https://github.com/dustinkirkland/byobu) (accessed 2026-03-01)
- [GitHub API — Repository Metadata](https://api.github.com/repos/dustinkirkland/byobu) (accessed 2026-03-01)
- [GitHub — Release 6.14 Notes](https://github.com/dustinkirkland/byobu/releases/tag/6.14) (accessed 2026-03-01)
- [GitHub — README.md](https://github.com/dustinkirkland/byobu/blob/master/README.md) (accessed 2026-03-01)
- [GitHub — Status Plugin List (usr/share/byobu/status/status)](https://github.com/dustinkirkland/byobu/blob/master/usr/share/byobu/status/status) (accessed 2026-03-01)
- [GitHub — Status Plugin Scripts (usr/lib/byobu/)](https://github.com/dustinkirkland/byobu/tree/master/usr/lib/byobu) (accessed 2026-03-01)
- [GitHub — Tmux Help File (help.tmux.txt)](https://github.com/dustinkirkland/byobu/blob/master/usr/share/doc/byobu/help.tmux.txt) (accessed 2026-03-01)

---
