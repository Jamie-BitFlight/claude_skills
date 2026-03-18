# tori-cli

**Research Date**: 2026-03-18
**Source URL**: <https://toricli.sh/>
**GitHub Repository**: <https://github.com/thobiasn/tori-cli>
**Version at Research**: v0.3.1
**License**: MIT

---

## Overview

Tori is a lightweight TUI-based remote Docker and host monitoring tool written in Go. It provides real-time metrics, log tailing, and alerting for Docker containers and host systems through a persistent agent running on remote servers, with a terminal client connecting via SSH-tunneled Unix sockets. Zero exposed ports, single binary, minimal infrastructure.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Docker monitoring requires exposed HTTP APIs or complex infrastructure | Tori uses SSH tunnels to a Unix socket—no open ports, no HTTP endpoints |
| Distributed monitoring across multiple servers is tedious | Multi-server support with instant server switching in the TUI |
| Log analysis requires manual SSH sessions or external tools | Built-in log tailing with regex search, date/time filtering, and level filtering within the TUI |
| Alert rules in complex monitoring stacks lack configurability | Declarative TOML-based alert rules with email and webhook notifications |
| Monitoring tool dependencies bloat server deployments | Single Go binary with no external dependencies—works with just `/proc` and `/sys` access |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 155 | 2026-03-18 |
| GitHub Forks | 7 | 2026-03-18 |
| Primary Language | Go (v1.25.6) | 2026-03-18 |
| Latest Release | v0.3.1 | 2026-03-06 |
| Repository Age | ~1 month (created 2026-02-10) | 2026-03-18 |

---

## Key Features

### Host Metrics Collection

- CPU usage percentage, memory usage, disk usage per mountpoint, swap usage
- Network statistics (bytes in/out, packets in/out per interface)
- Load averages (1, 5, 15-minute intervals)
- System uptime (collected from `/proc` and `/sys` directly—no external dependencies)

### Docker Container Monitoring

- Container state tracking (running, exited, paused, etc.)
- CPU and memory stats with resource limit awareness (`cpu_limit_percent` for containers with CPU limits)
- Container health status (healthy, unhealthy)
- Restart count tracking
- Automatic grouping by Docker Compose project via `com.docker.compose.project` label
- Tracking toggle per-container or per-group (manual or automatic via include/exclude patterns)
- Real-time event listening via Docker Events API with exponential backoff reconnection

### Log Tailing and Filtering

- Per-container log collection with configurable retention (default: 7 days)
- Remote log filtering: case-insensitive regex search, log level filtering (DEBUG → INFO → WARNING → ERROR)
- Date/time range filtering within the TUI
- Match highlighting inline
- SQLite storage with hourly pruning of expired logs
- Selective log collection (only tracked containers have logs stored)

### Alerting System

- Host-scoped rules (CPU %, memory %, disk %, load average, swap %)
- Container-scoped rules (CPU %, memory %, state, health, restart count)
- Log-scoped rules (pattern matching within a time window, case-insensitive substring or regex)
- Configurable thresholds with `for` duration (time condition must persist before firing) and cooldown suppression
- Multi-channel notifications: email (SMTP with optional TLS) and HTTP webhooks (support custom headers and Go template payloads)
- Per-rule silencing with up to 30-day duration
- State machine: inactive → pending (if `for > 0`) → firing → resolved → inactive

### Multi-Server Management

- Define multiple remote servers in client config (`~/.config/tori/config.toml`)
- Instant server switching via `S` key with per-server isolated data
- Concurrent session management—all servers stream data simultaneously
- Support for custom SSH ports and private key paths

### Configuration

**Agent Config** (`/etc/tori/config.toml`):
- Storage path and retention days
- Socket path and permission mode (0660 for systemd, 0666 for Docker)
- Host `/proc` and `/sys` paths (overridable for Docker deployments)
- Docker socket path
- Collection interval (default: 10s)
- Container include/exclude auto-tracking patterns
- Alert rule definitions with condition syntax: `scope.field op value`
- Email and webhook notification settings

**Client Config** (`~/.config/tori/config.toml`):
- Server definitions with SSH host, port, identity file, socket path
- Display preferences (date/time format strings using Go time layout)
- Theme color overrides (ANSI 0–15, 256-palette, or hex values)

---

## Technical Architecture

Tori uses a two-process architecture separated by SSH and Unix sockets:

```
┌─────────────────────────────────────────────┐
│  Local Machine (Client)                     │
│  ┌───────────────────────────────────────┐  │
│  │  tori TUI Client (Bubbletea)          │  │
│  │  • Dashboard view (metrics, container)│  │
│  │  • Alerts view (rules, history)       │  │
│  │  • Log detail view (search, filter)   │  │
│  │  • Multi-server picker                │  │
│  └──────────────┬────────────────────────┘  │
└─────────────────┼───────────────────────────┘
                  │
           SSH tunnel to Unix socket
                  │
┌─────────────────┼───────────────────────────┐
│  Remote Server (Agent)                      │
│  ┌──────────────▼────────────────────────┐  │
│  │  tori Agent                           │  │
│  │  Unix socket: /run/tori/tori.sock     │  │
│  │                                       │  │
│  │  Components:                          │  │
│  │  ├── HostCollector (reads /proc/sys) │  │
│  │  ├── DockerCollector (Docker socket) │  │
│  │  ├── LogTailer (per-container)       │  │
│  │  ├── Alerter (state machine)         │  │
│  │  ├── Notifier (email/webhook)        │  │
│  │  ├── EventWatcher (Docker Events API)│  │
│  │  ├── Store (SQLite with WAL mode)    │  │
│  │  └── Hub (pub/sub message fan-out)   │  │
│  └───────────────────────────────────────┘  │
│       ├─ Docker socket (/var/run/...)       │
│       ├─ /proc, /sys (host metrics)         │
│       ├─ SQLite DB (/var/lib/tori/tori.db)  │
│       └─ SMTP/Webhooks (notifications)      │
└─────────────────────────────────────────────┘
```

**Protocol & Transport**:
- Wire format: 4-byte big-endian length prefix + msgpack-encoded envelopes
- Streaming subscriptions (agent pushes metrics/alerts/logs) with topic-based subscription
- Request-response for client actions (acknowledge alert, silence rule, toggle tracking)
- Version handshake on connection (client sends build version, agent checks mismatch and emits warning on dashboard)

**Storage**:
- SQLite in WAL mode at `/var/lib/tori/tori.db` with single-writer enforcement (`SetMaxOpenConns(1)`)
- Tables: `metrics` (host and container stats), `logs` (per-container), `alerts` (firing/resolved history), `tracking_state` (which containers to monitor)
- Hourly pruning by timestamp (`alerts` pruned on `fired_at`, logs pruned on `created_at`)

**Compute Loop** (Agent):
```
collect():
  1. Read host metrics from /proc/stat, /proc/meminfo, /proc/diskstats, /proc/net/dev, /proc/uptime
  2. List Docker containers and fetch stats via ContainerStatsOneShot API (one-shot, not streaming)
  3. Sync log tailers (start/stop per-container goroutines based on tracked containers)
  4. Evaluate all alert rules (host, container, log) against the collected MetricSnapshot
  5. Publish new metrics/alerts to Hub (fans out to all connected clients)
  6. Prune stale logs and alerts (hourly)
  7. GC stale alert instances for destroyed containers
```

**Alert Evaluation**:
- Three scopes: `host` (one instance per rule), `container` (one instance per container per rule), `log` (one instance per rule—window is global, not per-container)
- Conditions parsed as 3-token strings: `scope.field op value` (validated on config load)
- String fields (`state`, `health`) support `==`/`!=` only; numeric fields support `>`, `<`, `>=`, `<=`, `==`, `!=`
- State machine enforces no duplicate notifications: inactive → pending (if `for > 0`) → firing → resolved → inactive
- Cooldown and notify_cooldown prevent flapping and notification spam

**TUI** (Bubbletea/Lipgloss/Bubbles):
- All colors defined in a single `Theme` struct with ANSI defaults (0–15) inherited from terminal
- Dashboard: host sparklines (CPU, mem), container list with resource gauges, compose group expansion
- Alerts: rules list with current firing state, alert history with severity coloring
- Detail view: log entries with inline match highlighting, date/time range picker, level filter cycle
- Keybindings: vim-style navigation (`j`/`k`), `+`/`-` for time window zoom, `t` to toggle tracking, `S` for server switch

---

## Installation & Usage

### Server (Agent)

**Systemd (Linux)**:

```bash
curl -fsSL https://raw.githubusercontent.com/thobiasn/tori-cli/main/deploy/install.sh | sudo sh
sudo systemctl enable --now tori
sudo vim /etc/tori/config.toml  # configure alerts, notifications
```

**Docker Compose**:

```bash
curl -O https://raw.githubusercontent.com/thobiasn/tori-cli/main/deploy/docker-compose.yml
# Edit TORI_CONFIG environment variable to add alert rules
docker compose up -d
```

**Docker run**:

```bash
docker run -d --name tori \
  --restart unless-stopped \
  --pid host \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v /run/tori:/run/tori \
  -v tori-data:/var/lib/tori \
  -v ./config.toml:/etc/tori/config.toml:ro \
  ghcr.io/thobiasn/tori-cli:latest
```

**From source**:

```bash
go build -o tori ./cmd/tori
sudo ./tori agent --config /etc/tori/config.toml
```

### Client (Local Machine)

```bash
curl -fsSL https://raw.githubusercontent.com/thobiasn/tori-cli/main/deploy/install.sh | sh -s -- --client
```

Installs to `~/.local/bin/tori` (or `/usr/local/bin/tori` if run with sudo).

### Configuration Example

**Agent config** (`/etc/tori/config.toml`):

```toml
[storage]
path = "/var/lib/tori/tori.db"
retention_days = 7

[socket]
path = "/run/tori/tori.sock"
mode = "0660"

[docker]
socket = "/var/run/docker.sock"
include = ["myapp-*"]      # auto-track containers matching patterns
# exclude = ["tori-*"]

[collect]
interval = "10s"

[alerts.high_cpu]
condition = "host.cpu_percent > 90"
for = "2m"
severity = "warning"
actions = ["notify"]

[alerts.container_down]
condition = "container.state == 'exited'"
for = "30s"
severity = "critical"
actions = ["notify"]

[notify.email]
enabled = true
smtp_host = "smtp.example.com"
smtp_port = 587
from = "tori@example.com"
to = ["you@example.com"]
username = "tori@example.com"
password = "app-password-here"
tls = "starttls"

[[notify.webhooks]]
enabled = true
url = "https://hooks.slack.com/services/..."
template = '{"text": "{{.Subject}}\n{{.Body}}\nSeverity: {{.Severity}}"}'
```

**Client config** (`~/.config/tori/config.toml`):

```toml
[servers.prod]
host = "user@prod.example.com"
socket = "/run/tori/tori.sock"
port = 22
identity_file = "~/.ssh/prod_key"

[servers.staging]
host = "user@staging.example.com"

[display]
date_format = "2006-01-02"
time_format = "15:04:05"

[theme]
accent = "4"                # ANSI blue
critical = "#f7768e"        # hex override
```

### Usage

```bash
# Connect to all configured servers
tori

# Connect via SSH (ad-hoc, no config)
tori user@myserver.com

# With custom SSH port
tori user@host --port 2222

# With specific key
tori user@host --identity ~/.ssh/id_ed25519

# Custom remote socket path
tori user@host --remote-socket /custom/tori.sock

# Direct local socket (no SSH)
tori --socket /run/tori/tori.sock
```

**Keybindings**:
- `1` / `2`: Dashboard / Alerts view
- `j` / `k`: Navigate
- `gg` / `G`: Top / bottom
- `t`: Toggle tracking for container or group
- `S`: Switch server
- `Enter`: Expand detail view
- `s`: Silence alert rule or filter by level
- `/`: Open filter/search dialog
- `+` / `-`: Zoom time window
- `q`: Quit

---

## Relevance to Claude Code Development

### Applications

- **SSH-first architecture pattern**: Tori's design (no exposed ports, SSH tunnels only) is relevant for secure agent deployment patterns where the orchestrator must access remote agents without HTTP endpoints. The Unix socket + SSH tunnel model could inform how Claude Code agents communicate with remote execution environments.

- **Binary distribution and installation**: The single-binary Go approach with a simple shell install script mirrors best practices for distributing CLI tools. Tori's install.sh pattern (curl | sh with version pinning) is worth studying for packaging Claude Code skills as distributable binaries.

- **State machine design for alerting**: The alert state machine (inactive → pending → firing → resolved) is a clean pattern for managing long-lived conditions that require hysteresis (preventing flapping). Applicable to agent status tracking and availability detection.

- **Protocol versioning and warnings**: The version handshake approach (client sends version, server checks and warns but never blocks) is a pragmatic upgrade strategy that could apply to Claude Code's agent protocol evolution.

### Patterns Worth Adopting

- **Flat package structure for domain cohesion**: Tori's `internal/agent/` package (no sub-packages, one file per concern) demonstrates how to organize related code without premature abstraction hierarchy. This aligns with Go idioms and the CLAUDE.md guidance on code simplicity.

- **Configuration validation at load time**: Alert conditions are validated at TOML parse time via a whitelist parser, catching errors early rather than during evaluation. This pattern could improve Claude Code's skill configuration validation.

- **Pub/sub hub for multi-client distribution**: The Hub's topic-based fan-out (clients subscribe to `metrics`, `logs`, `alerts`, `containers`) is a clean pattern for broadcasting updates from a single producer (the agent) to multiple consumers (TUI, external clients). Applicable to skill pub/sub and multi-consumer streaming.

- **Deterministic time injection for testing**: The Alerter's `now func() time.Time` field allows time-based logic to be tested without `time.Sleep`. A pattern worth adopting in any agent system with time-dependent state.

### Integration Opportunities

- **Remote monitoring agent for Claude Code executions**: A tori-like agent could monitor Claude Code task execution on remote machines—metrics (CPU, memory), logs (agent output), and alerts (task failure, timeout). The Unix socket transport model is directly reusable.

- **Alert rule syntax for task conditions**: Tori's 3-token condition format (`scope.field op value`) could be adapted to define task readiness conditions, success criteria, or SLA alerts in Claude Code's task management system.

- **Log tailing from remote agent output**: Tori's remote log streaming with filtering/search could inspire how Claude Code retrieves and searches logs from distributed agent executions without requiring central log aggregation.

---

## References

- [tori GitHub Repository](https://github.com/thobiasn/tori-cli) (accessed 2026-03-18)
- [tori Official Website](https://toricli.sh/) (accessed 2026-03-18)
- [tori on LinuxLinks](https://www.linuxlinks.com/tori-remote-server-monitoring/) (accessed 2026-03-18)
- [tori on Terminal Trove](https://terminaltrove.com/tori/) (accessed 2026-03-18)
- [Docker Monitoring Tools Comparison - Dash0](https://www.dash0.com/comparisons/best-docker-monitoring-tools) (accessed 2026-03-18)
- Repository source files: `cmd/tori/main.go`, `internal/agent/*.go`, `internal/tui/*.go`, `internal/protocol/*.go` (accessed via local clone, 2026-03-18)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Sidecar](./sidecar.md) | developer-tools | Co-host TUI companion for AI agents; both use Go/Bubbletea for real-time multi-system visibility alongside agent execution |
| [Agent Deck](./agent-deck.md) | developer-tools | Parallel session orchestration pattern; both provide unified TUI interfaces for managing multiple remote environments (AI sessions vs. Docker/host systems) |
| [Stoat](./stoat.md) | developer-tools | Shared TUI framework (Go/Bubbletea) and vim-keybinding design pattern for terminal-first data introspection |
| [Byobu](./byobu.md) | developer-tools | Terminal multiplexing and status bar monitoring; complements tori's metrics collection with session management for long-running remote operations |
| [AsyncSSH](../async-libraries/asyncssh.md) | async-libraries | SSH transport layer complement; tori's Unix socket + SSH tunnel model parallels asyncssh's reverse tunnel and port forwarding patterns for firewalled agent access |
| [Orbstack](./orbstack.md) | developer-tools | Docker infrastructure alternative; tori monitors Docker deployments while orbstack optimizes Docker runtime for macOS development environments |
| [devenv](./devenv.md) | developer-tools | Infrastructure-as-code philosophy; both provide single-binary/declarative configuration approaches to managing distributed server and development environments without external dependencies |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-18 |
| Version at Verification | v0.3.1 (released 2026-03-06) |
| Next Review Recommended | 2026-06-18 |
| Confidence Map | Overview: high (README + source read); Problem Addressed: high (feature list from docs); Key Statistics: high (GitHub API); Key Features: high (README + source); Technical Architecture: high (code-read + CLAUDE.md); Installation & Usage: high (README + install script); Relevance: medium (inference from architecture) |
