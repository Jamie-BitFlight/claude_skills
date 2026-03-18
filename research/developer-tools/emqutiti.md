# Emqutiti

**Research Date**: 2026-03-18
**Source URL**: <https://github.com/marang/emqutiti>
**GitHub Repository**: <https://github.com/marang/emqutiti>
**Version at Research**: v0.7.7
**License**: MIT License

---

## Overview

Emqutiti is a polished MQTT client for the terminal built on Bubble Tea (a Go TUI framework). It provides a slick interface for publishing and subscribing to MQTT topics with support for managing multiple broker profiles through a single configuration file. Profiles live in `~/.config/emqutiti/config.toml` enabling easy broker switching via keyboard commands.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| No unified terminal-based MQTT client with polished UI | Bubble Tea-based TUI with responsive layout and keyboard navigation |
| Manual credential management across multiple brokers | OS keyring integration for secure credential storage, with environment variable overrides |
| Tedious bulk publishing tasks | Interactive CSV import wizard with dry-run capability and persisted settings |
| Loss of MQTT message history during exploration | Persistent message history and trace recording with offline headless mode |
| Difficult switching between multiple MQTT brokers | Profile-based configuration with default profile auto-connect |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 4 | 2026-03-18 |
| GitHub Forks | 0 | 2026-03-18 |
| Contributors | 1 (marang) | 2026-03-18 |
| Latest Release | v0.7.7 | 2026-02-14 |
| Last Commit | 2026-02-14 | 2026-03-18 |
| Total Commits | 1026 (by primary author) | 2026-03-18 |
| Open Issues | 0 | 2026-03-18 |

---

## Key Features

### UI and Interaction

- Responsive layout driven by `tea.WindowSizeMsg` and lipgloss styling that adapts to terminal size
- Multi-pane interface with left/right pane switching via `Left`/`Right` arrow keys
- Focus management via Tab/Shift+Tab with mouse support for clicking elements
- Global shortcuts: `Ctrl+D` (exit), `Ctrl+P` (payloads), `Ctrl+T` (topics), `Ctrl+B` (broker manager), `Ctrl+S` (publish), `Ctrl+E` (publish retained), `Ctrl+L` (log viewer)
- History view with message filtering, selection management, and full message viewer

### Connection Management

- Multiple broker profiles with CRUD operations (`Ctrl+X` to disconnect, `Ctrl+O` to toggle default)
- Support for schema variations: `mqtt`, `mqtts`, `tcp`, `ssl`, `ws`, `wss`
- TLS certificate management: `ca_cert_path`, `client_cert_path`, `client_key_path` configuration options
- Client ID randomization via `random_id_suffix = true`
- TLS verification bypass with `skip_tls_verify = true` for self-signed brokers
- Environment variable loading: `Load from env` option reads `EMQUTITI_<PROFILE>_*` variables

### Import and Tracing

- CSV import wizard mapping columns to JSON payloads with dry-run preview
- Headless trace execution: `emqutiti --trace KEY --topics "pattern/#" -p profile [--start RFC3339] [--end RFC3339]`
- Persistent trace storage under `~/.config/emqutiti/data/<profile>/traces`
- Trace replay via `Alt+R` (manage traces) or `Ctrl+R` in the app

### Storage and Data

- Message persistence via BadgerDB (on-disk key-value store)
- Initial footprint reduced from 2GB to maximum of 10MB with growth allowed as needed
- Configuration saved to `~/.config/emqutiti/config.toml` (TOML format)
- gRPC database proxy started on `127.0.0.1:54321` by default (configurable via `proxy_addr`)

---

## Technical Architecture

Emqutiti uses a component-based TUI architecture with focused modules and clear separation of concerns:

### Core Application Flow

- **Entry point**: `cmd/emqutiti/main.go` calls `app.Main(cfg.ParseFlags())` after parsing command-line flags (Source: cmd/emqutiti/main.go)
- **Flag parsing**: `cmd/config.go` handles `-i/--import`, `-p/--profile`, `-l/--list-profiles`, and trace-specific flags (`--trace`, `--topics`, `--start`, `--end`)
- **Main loop**: Built on Bubble Tea's event-driven model with `Init()`, `Update(msg)`, and `View()` methods

### Key Components

- **Connections Component** (`connections/` package): MQTT client connection management with Profile struct for broker configuration. Exposes `Client` interface for Subscribe, Disconnect operations (Source: connections/api.go)
- **Focus Management** (`focus.go`): Focus traversal via `focusMap`, `focusOrder`, `elemPos` tracking, and viewport offset management for responsive navigation (Source: focus.go — SetFocus, focusFromMouse, ScrollToFocused)
- **History Component** (`history/` package): Message history storage and filtering with selection-based operations
- **Topics Component** (`topics/` package): Topic subscription management and message display
- **Traces Component** (`traces/` package): Headless trace recording with `Client` interface for MQTT operations (Source: traces/runtime.go — Client interface)
- **Importer Component** (`importer/` package): CSV import wizard with mapping and dry-run support
- **Confirm Component** (`confirm/` package): Reusable confirmation dialogs

### MQTT Protocol

- **Primary client**: `github.com/eclipse/paho.mqtt.golang` (Paho MQTT Go client library v1.5.0)
- **Headless broker support**: `github.com/mochi-co/mqtt` v1.3.2 for local testing
- **Message callback**: Standardized `mqtt.MessageHandler` signature for subscription callbacks

### UI Rendering

- **Bubble Tea** v1.3.5: Core TUI framework with `tea.Model`, `tea.Cmd`, and message-driven state management
- **Lipgloss** v1.1.1+: Terminal styling and layout composition
- **Bubbles** v0.21.0: Reusable TUI widgets
- **Glamour** v0.10.0: Markdown rendering for documentation
- **X libraries**: `charmbracelet/x/ansi`, `charmbracelet/x/term`, `charmbracelet/x/cellbuf` for low-level terminal control

### Database and Storage

- **BadgerDB** v4.8.0: On-disk key-value store for message and trace persistence
- **gRPC** v1.74.2 + Protobuf v1.36.6: Database proxy protocol (Source: proxy/proxy.proto)
- **TOML** (BurntSushi v1.5.0): Configuration file parsing

### Credentials

- **Zalando keyring** v0.2.6: OS keyring integration for password storage (`keyring:emqutiti-profile/user` format)
- Password override: `EMQUTITI_DEFAULT_PASSWORD` environment variable

### Utilities

- **Fuzzy matching**: `sahilm/fuzzy` v0.1.1 for topic search
- **Clipboard**: `atotto/clipboard` v0.1.4 for copy-to-clipboard in history view
- **Rune width**: `mattn/go-runewidth` v0.0.16 for terminal width calculation

---

## Installation & Usage

### Installation

From source:

```bash
go install github.com/marang/emqutiti/cmd/emqutiti@latest
```

Arch Linux via AUR:

```bash
yay -S emqutiti
```

Linux (Debian/Ubuntu):

```bash
# Download and install .deb package
# Available from GitHub Releases
sudo dpkg -i emqutiti_0.7.7_linux_amd64.deb
```

Linux (Fedora/RHEL):

```bash
# Download and install .rpm package
# Available from GitHub Releases
sudo rpm -i emqutiti_0.7.7_linux_amd64.rpm
```

Flatpak:

```bash
flatpak install io.github.marang.Emqutiti
```

### Basic Usage

Start the interactive TUI:

```bash
emqutiti
```

If a profile is marked as default, the app auto-connects on startup.

### CSV Import

Launch with CSV file and target profile:

```bash
emqutiti -i data.csv -p local
```

The wizard displays column-to-JSON mapping and supports dry-run preview before publishing.

### Headless Tracing (Offline Recording)

Record messages without the UI:

```bash
emqutiti --trace run1 --topics "sensors/#" -p local
```

With time range:

```bash
emqutiti --trace myrun --topics "sensors/#" -p local \
  --start "2025-08-05T11:47:00Z" --end "2025-08-05T11:49:00Z"
```

Times must be RFC3339 formatted. Traces are stored under `~/.config/emqutiti/data/<profile>/traces`.

### Configuration Example

Create `~/.config/emqutiti/config.toml`:

```toml
proxy_addr = "127.0.0.1:54321"
default_profile = "local"

[[profiles]]
name     = "local"
schema   = "tcp"
host     = "localhost"
port     = 1883
username = "user"
password = "keyring:emqutiti-local/user"
```

Configuration options include: `random_id_suffix`, `skip_tls_verify`, `ca_cert_path`, `client_cert_path`, `client_key_path`, and `Load from env` setting.

### Keyboard Shortcuts

**Global**: `Ctrl+D` (exit), `Ctrl+P` (payloads), `Ctrl+T` (topics), `Alt+R` (manage traces), `Ctrl+B` (broker manager), `Ctrl+X` (disconnect), `Ctrl+S` (publish), `Ctrl+E` (publish retained), `Ctrl+L` (log viewer), `Ctrl+Shift+Up`/`Ctrl+Shift+Down` (resize panels)

**Navigation**: `Esc` (back), `Tab`/`Shift+Tab` (cycle focus), `Up`/`Down` or `j`/`k` (scroll), `Left`/`Right` (switch pane)

**History View**: `Space` (toggle selection), `Shift+Up`/`Shift+Down` (extend selection), `Ctrl+A` (select all), `Ctrl+C` (copy), `a` (archive), `Delete` (remove), `/` (filter), `Ctrl+F` (clear filters), `Enter` (view full message)

---

## Development

### Building

```bash
make build
```

This compiles the emqutiti binary with trimmed paths and optimized flags:

```bash
go build -trimpath -ldflags="-s -w" -o emqutiti ./cmd/emqutiti
```

### Testing

```bash
go test ./...
```

Tests run offline with stubbed network calls (TLS client tests use a temporary loopback server). The keyring manual test is skipped by default:

```bash
go test -run ExampleSet_manual -tags manual
```

Before submitting PRs, run linting:

```bash
go vet ./...
```

### Demo Recording

Generate animated GIFs from `.tape` scripts:

```bash
make tape
```

Uses a containerized `vhs` environment (bundling `vhs`, `ffmpeg`, `ttyd`, `chromium`). Individual tapes can be recorded with:

```bash
vhs -o docs/assets/create_connection.gif docs/create_connection.tape
```

### Release Process

Releases are triggered by git tags matching `v*` format. The release pipeline includes:

1. **GitHub Actions release.yml**: Publishes multi-platform binaries (macOS amd64/arm64, Linux amd64/arm64, Windows amd64/arm64) and Linux packages (.deb, .rpm)
2. **GoReleaser** (.goreleaser.yaml): Builds cross-platform binaries and nFPM outputs
3. **AUR workflow** (aur.yml): Auto-updates `PKGBUILD` and `.SRCINFO` for Arch Linux users

Steps to release:

```bash
# Optional: Update PKGBUILD version manually (CI does this)
pkgver=0.7.0

# Commit pending changes
git add -A
git commit -m "Prepare release v0.7.0"

# Create and push tag
git tag v0.7.0
git push origin main --tags
```

---

## Relevance to Claude Code Development

### Applications

- **Terminal-driven development tools**: Emqutiti demonstrates best practices for building polished TUI applications in Go, relevant for implementing terminal-based features or integrations in Claude Code workflows
- **Multi-modal interfaces**: The architecture shows how to build flexible interfaces that work both interactively (TUI) and headlessly (CLI tracing mode), applicable to agent-driven tools that need both human and programmatic access
- **Secure credential handling**: The keyring integration and environment variable override patterns offer patterns for integrating with system credentials in Claude Code plugins

### Patterns Worth Adopting

- **Component-based UI architecture**: Modular packages (connections, history, topics, traces, importer) with clear APIs reduce coupling and enable testing individual components
- **Focus management system**: The focus map, focus order, and viewport offset tracking provide a reusable framework for responsive keyboard navigation across dynamic layouts
- **Configuration management**: TOML-based profile system with environment variable overrides balances flexibility and sensible defaults
- **Headless operation**: Supporting both interactive and non-interactive modes via the same client code enables automation and testing

### Integration Opportunities

- **MQTT message inspection in workflows**: Agents could query running MQTT brokers to verify message flow or system state during feature implementation (emqutiti's library dependencies expose the necessary MQTT client interfaces)
- **Terminal UI patterns in Claude Code plugins**: Adopting Bubble Tea + Lipgloss patterns from emqutiti could accelerate development of rich terminal interfaces for agent-driven tools
- **Trace recording for debugging**: The persistent trace model could inspire audit trails or playback capabilities in Claude Code task execution

---

## References

- [Emqutiti GitHub Repository](https://github.com/marang/emqutiti) (accessed 2026-03-18)
- [Bubble Tea TUI Framework](https://github.com/charmbracelet/bubbletea) (accessed 2026-03-18)
- [Bubble Tea Blog: Terminal IRC Client](https://sngeth.com/go/terminal/ui/bubble-tea/2025/08/17/building-terminal-ui-with-bubble-tea/) (accessed 2026-03-18)
- [Paho MQTT Go Client](https://github.com/eclipse/paho.mqtt.golang) (accessed 2026-03-18)
- [BadgerDB On-Disk Database](https://github.com/dgraph-io/badger) (accessed 2026-03-18)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Tori-cli](./tori-cli.md) | developer-tools | Go-based TUI monitoring tool with responsive layout via terminal framework similar to Bubble Tea |
| [GitHub CLI](./github-cli.md) | developer-tools | Go CLI with credential handling patterns (keyring/env override) relevant to emqutiti's auth model |
| [Tmuxp](./tmuxp.md) | developer-tools | YAML-based configuration management and session persistence directly complementing emqutiti's profile system |
| [Loguru](./loguru.md) | developer-tools | Structured logging and message tracing for debugging MQTT message flows in emqutiti workflows |
| [Shpool](./shpool.md) | developer-tools | Session persistence for remote connections; complements emqutiti's headless trace recording capability |
| [Libtmux](./libtmux.md) | developer-tools | Typed Python object lifecycle management (Session, Window, Pane) parallels emqutiti's component architecture pattern |
| [Yume](./yume.md) | developer-tools | Multi-modal interface design (interactive TUI + headless mode) mirrors emqutiti's dual interactive/trace operation modes |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-18 |
| Version at Verification | v0.7.7 |
| Next Review Recommended | 2026-06-18 |
| Confidence Map | `Overview: high` `Problem Addressed: high` `Key Statistics: high` `Key Features: high (doc + code-read)` `Technical Architecture: medium (code-read)` `Installation & Usage: high` `Development: high` `Relevance: medium` |
