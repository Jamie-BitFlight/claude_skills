---
title: HolyClaude
tagline: "Containerized AI development workstation: Claude Code + web UI + 7 AI CLIs + headless browser + 50+ dev tools"
category: agent-infrastructure
resource_url: https://github.com/CoderLuii/HolyClaude
last_accessed: 2026-03-28
confidence:
  identity: high
  features: high
  architecture: high
  usage: high
  limitations: medium
---

## Overview

HolyClaude is a pre-configured Docker container that provides a complete AI development workstation in a single `docker compose up` command. It bundles Claude Code CLI (Anthropic's official AI coding agent), a web-based IDE (CloudCLI), six additional AI CLIs, Chromium with Xvfb, Playwright, and 50+ developer tools into a multi-architecture Docker image available in two variants: full (batteries-included) and slim (on-demand installation).

The project addresses a recurring DevOps friction point: manually installing and configuring Claude Code, a browser-based IDE, a headless browser, AI CLIs, and supporting development tools across multiple package managers (apt, npm, pip) — a process that typically takes 1-2 hours, requires Docker expertise, and fails at multiple edge cases (Chromium in Docker, shared memory limits, permission mapping, WORKDIR ownership).

**License**: MIT
**Repository**: <https://github.com/CoderLuii/HolyClaude>
**Latest version**: v1.1.4 (released 2026-03-28)
**GitHub metrics** (as of 2026-03-28): 1,128 stars, 113 forks, 0 open issues

---

## Problem Addressed

> "You were going to spend 2 hours setting this up manually. Or you could just `docker compose up`."

SOURCE: README.md (accessed 2026-03-28)

HolyClaude solves three distinct DevOps problems:

1. **Installation complexity**: Installing Claude Code CLI requires the Anthropic installer (which hangs if WORKDIR is root-owned), configuring a web UI, wiring it to Claude, installing Chromium with proper Docker sandboxing, configuring Xvfb display server, adjusting shared memory limits, and installing 7 AI CLIs plus 50+ development tools across three package managers (apt, npm, pip).

2. **Docker edge cases**: Chromium fails in Docker without proper shared memory (`shm_size` >= 2GB), seccomp settings, and Linux capabilities (`SYS_ADMIN`, `SYS_PTRACE`). Xvfb requires correct display server setup. File permissions require UID/GID mapping. Network-mounted volumes require polling-based file watchers instead of inotify.

3. **One-off setup cost**: Every new machine, VPS, or team member rebuilds the same configuration manually. HolyClaude eliminates this by providing a single, tested image.

---

## Key Statistics

| Metric | Value | Source |
|--------|-------|--------|
| **GitHub Stars** | 1,128 (as of 2026-03-28) | GitHub API |
| **GitHub Forks** | 113 | GitHub API |
| **Open Issues** | 0 | GitHub API |
| **Latest Version** | v1.1.4 | Git tag (2026-03-28) |
| **Repository Created** | 2026-03-22 | GitHub API |
| **Last Updated** | 2026-03-28 | GitHub API |
| **License** | MIT License | GitHub API |
| **Primary Language** | Dockerfile | GitHub API |

---

## Key Features

### 1. Pre-installed Claude Code CLI

> "This runs the real Claude Code CLI. Not a wrapper. Not a proxy. Not a knock-off."

SOURCE: README.md line 45 (accessed 2026-03-28)

The container installs the official Anthropic Claude Code CLI binary. Authentication works via:

- **Claude Max/Pro subscription**: Sign in through CloudCLI web UI using OAuth (same flow as desktop Claude Code)
- **Anthropic API key**: Paste your API key in the web UI (same billing as pay-per-use)

No proxy, no token interception. Credentials are stored in the bind-mounted `./data/claude/` directory and survive container rebuilds.

SOURCE: README.md lines 176-184 (accessed 2026-03-28)

### 2. Seven AI CLIs in One Container

> "Seven AI CLIs. One container. No other Docker image gives you this."

SOURCE: README.md line 609 (accessed 2026-03-28)

All of the following are pre-installed and authenticated via environment variables or web UI:

| CLI | Command | Authentication | Use case |
|-----|---------|-----------------|----------|
| Claude Code | `claude` | CloudCLI web UI (OAuth) or API key | Primary AI agent |
| Gemini CLI | `gemini` | `GEMINI_API_KEY` env var | Google's coding agent |
| OpenAI Codex | `codex` | `OPENAI_API_KEY` env var | OpenAI's coding agent (not ChatGPT) |
| Cursor | `cursor` | `CURSOR_API_KEY` env var | Cursor's AI agent |
| TaskMaster AI | `task-master` | Uses existing AI provider keys | Task planning and orchestration |
| Junie | `junie` | JetBrains AI subscription | JetBrains' coding agent |
| OpenCode | `opencode` | Configure via TUI | Open source agent (multiple providers) |

SOURCE: README.md lines 607-620 (accessed 2026-03-28)

### 3. Headless Browser with Playwright

Chromium is pre-installed and configured for headless operation:

- **Xvfb**: X11 virtual framebuffer display server (`:99`) for rendering headless GUI
- **Playwright**: Browser automation library (npm package, pre-configured)
- **Screenshots and testing**: Full support via Chromium's headless API

**Critical configuration**: Chromium requires `SYS_ADMIN` and `SYS_PTRACE` Linux capabilities and `seccomp=unconfined` in Docker — standard for any containerized browser (Playwright docs, Puppeteer docs, CI pipelines running browser tests).

Shared memory (`shm_size`) must be >= 2GB:

> "Docker gives containers 64MB of shared memory by default. Chromium uses `/dev/shm` heavily for tab rendering. At 64MB, tabs crash randomly. 2GB is the recommended minimum for any Chromium-in-Docker setup."

SOURCE: README.md line 293 (accessed 2026-03-28)

### 4. CloudCLI Web UI (:3001)

A web-based IDE for managing Claude Code, viewing file trees, and interacting with the CLI via browser. Single port exposed: `3001` (configurable).

SOURCE: README.md lines 264, 330 (accessed 2026-03-28)

### 5. Two Image Variants

| Variant | Size | What's included | Best for |
|---------|------|-----------------|----------|
| **`latest` (full)** | ~1.5 GB | Everything: all tools, all libraries, all CLIs pre-installed | Most users, zero wait time for additional tools |
| **`slim`** | ~500 MB | Core tools only; Claude installs extras on-demand | Small VPS, limited disk, metered bandwidth |

Both variants include Node.js 22 LTS, Python 3, system tools, Chromium, s6-overlay, and all 7 AI CLIs. The full variant adds pandoc, ffmpeg, libvips-dev, Azure CLI, and 20+ additional npm/pip packages.

SOURCE: README.md lines 212-231 (accessed 2026-03-28)

### 6. Multi-Architecture Support

Builds and runs on both AMD64 and ARM64 (Raspberry Pi 4+, Oracle Cloud Ampere, AWS Graviton, Apple Silicon via Docker Desktop). Same Dockerfile, multi-stage build produces both architectures.

SOURCE: Dockerfile lines 10, 32; README.md lines 135-136 (accessed 2026-03-28)

### 7. Comprehensive Development Tooling

#### Node.js ecosystem (npm, pnpm, vite, esbuild, etc.)

| Tool | Purpose |
|------|---------|
| Node.js 22 LTS | JavaScript runtime |
| pnpm | Fast, disk-efficient package manager |
| vite, esbuild | Lightning-fast build tools |
| typescript, tsx | TypeScript compilation and execution |
| eslint, prettier | Code quality and formatting |
| serve, nodemon | Static file server, auto-restart dev server |

SOURCE: README.md lines 484-495 (accessed 2026-03-28)

#### Python ecosystem (data science, web, automation)

| Library | Purpose |
|---------|---------|
| requests, httpx | HTTP clients |
| beautifulsoup4, lxml | Web scraping and HTML parsing |
| Pillow, numpy, pandas | Image and data processing (pre-compiled) |
| matplotlib, seaborn | Data visualization (full image only) |
| fastapi, uvicorn | Python web framework (full image only) |
| jinja2, markdown | Templating and markdown rendering |
| playwright | Browser automation (pre-configured) |

SOURCE: README.md lines 498-514, 575-584 (accessed 2026-03-28)

#### System utilities

| Tool | Purpose |
|------|---------|
| git, gh | Version control + GitHub CLI (PRs, issues, releases from terminal) |
| ripgrep (`rg`), fd, fzf | Blazing-fast code search and filtering |
| bat, tree, jq | Better cat (syntax highlighting), trees, JSON processing |
| curl, wget | HTTP downloads |
| tmux | Terminal multiplexer (background processes) |
| htop, lsof, strace | Process monitoring and debugging |
| imagemagick | Image conversion (`convert`, `identify`, `mogrify`) |
| postgresql-client, redis-cli, sqlite3 | Direct database access |
| openssh-client | SSH access |

SOURCE: README.md lines 517-531 (accessed 2026-03-28)

#### Full image exclusives

| Tool | Purpose |
|------|---------|
| pandoc | Convert between document formats (md ↔ HTML ↔ PDF ↔ docx ↔ epub) |
| ffmpeg | Video and audio processing (extract, convert, transcode) |
| libvips-dev | High-performance image processing library |
| Azure CLI | Azure cloud deployment and management |
| Wrangler, Vercel, Netlify CLI | Deployment to Cloudflare Workers, Vercel, Netlify |
| Prisma, Drizzle Kit | Node.js ORMs |
| PM2 | Production process manager |
| Lighthouse | Performance auditing (Chromium included) |

SOURCE: README.md lines 551-596, Dockerfile lines 65-76 (accessed 2026-03-28)

### 8. Notifications via Apprise

Supports 100+ notification services (Discord, Telegram, Slack, Email, Pushover, Gotify, etc.). Enable by setting environment variables (e.g., `NOTIFY_DISCORD=discord://webhook_id/webhook_token`) and creating a flag file (`~/.claude/notify-on`).

SOURCE: README.md lines 383-394 (accessed 2026-03-28)

### 9. Ollama Integration (Local Models)

Alternative to Anthropic subscription: run local models via Ollama. Set `OLLAMA_HOST=http://host.docker.internal:11434` (macOS/Windows) or `http://host_machine_ip:11434` (Linux).

SOURCE: README.md lines 629-633 (accessed 2026-03-28)

---

## Technical Architecture

### Layered Process Architecture

```
Docker Container (Host: localhost:3001)
├── entrypoint.sh (container startup)
│   ├── bootstrap.sh (first boot only — installs Claude Code CLI)
│   └── s6-overlay v3.2.0.2 (PID 1 — process manager)
│       ├── CloudCLI (web UI on :3001)
│       ├── Xvfb (X11 display server on :99)
│       ├── Claude Code CLI (background, communicates with CloudCLI)
│       └── Other supervised services (dbus-system, etc.)
```

s6-overlay manages graceful shutdown, auto-restart on failure, and proper signal handling.

SOURCE: README.md lines 643-649; Dockerfile lines 15, 29-37 (accessed 2026-03-28)

### Base Image and Dependencies

| Component | Version | Source |
|-----------|---------|--------|
| Base OS | node:22-bookworm-slim | Dockerfile line 10 |
| Process manager | s6-overlay v3.2.0.2 | Dockerfile line 15 |
| X11 display server | Xvfb | Dockerfile line 58 |
| Chromium | Latest from Debian repos | Dockerfile line 46 |
| Python | 3.x (system default) | Dockerfile line 44 |
| Node.js | 22 LTS | Dockerfile line 10 |

Multi-architecture build: Dockerfile detects `$TARGETARCH` (amd64 or arm64) and downloads the correct s6-overlay binary.

SOURCE: Dockerfile lines 10, 15, 32 (accessed 2026-03-28)

### User and Permissions

The `node:22-bookworm-slim` base image includes a pre-existing `node` user (UID 1000). HolyClaude renames this to `claude` and grants passwordless sudo.

**Critical note** (from README): Claude Code CLI installer hangs if WORKDIR is root-owned. Solution: `WORKDIR /workspace` is set to be owned by `claude` user.

SOURCE: Dockerfile lines 91-100 (accessed 2026-03-28)

### Environment Variables for Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `TZ` | UTC | Container timezone |
| `PUID` / `PGID` | 1000 / 1000 | UID/GID mapping for file permissions |
| `NODE_OPTIONS` | `--max-old-space-size=4096` | Node.js heap memory limit |
| `GIT_USER_NAME` / `GIT_USER_EMAIL` | HolyClaude User / <noreply@holyclaude.local> | Git commit author |
| `CHOKIDAR_USEPOLLING` | (unset) | Set to `1` for SMB/CIFS mounts (enables polling) |
| `WATCHFILES_FORCE_POLLING` | (unset) | Set to `true` for Python polling on network mounts |
| `ANTHROPIC_API_KEY` | (unset) | Alternative to web UI OAuth |
| `ANTHROPIC_AUTH_TOKEN` | (unset) | Alternative API auth |
| `GEMINI_API_KEY`, `OPENAI_API_KEY`, `CURSOR_API_KEY` | (unset) | Additional AI provider keys |
| `OLLAMA_HOST` | (unset) | Ollama endpoint for local models |
| `NOTIFY_*` (Discord, Telegram, Slack, Email, etc.) | (unset) | Apprise notification URLs |

SOURCE: README.md lines 440-469 (accessed 2026-03-28)

### Docker Compose Requirements

Quick template (minimum viable):

```yaml
services:
  holyclaude:
    image: coderluii/holyclaude:latest
    container_name: holyclaude
    restart: unless-stopped
    shm_size: 2g                           # CRITICAL: Chromium requirement
    cap_add:
      - SYS_ADMIN                          # Chromium sandboxing
      - SYS_PTRACE                         # Debugging tools
    security_opt:
      - seccomp=unconfined                 # Chromium syscall requirements
    ports:
      - "3001:3001"
    volumes:
      - ./data/claude:/home/claude/.claude # Credentials and memory
      - ./workspace:/workspace              # Your code
    environment:
      - TZ=UTC
```

Full template with all knobs exposed: available in `docker-compose.full.yaml` in the repository.

SOURCE: README.md lines 239-289; Dockerfile (accessed 2026-03-28)

### Variant Selection

- **`coderluii/holyclaude:latest`** — Full image, all tools pre-installed
- **`coderluii/holyclaude:slim`** — Slim image, 50+ tools installable on-demand
- **`coderluii/holyclaude:X.Y.Z`** — Version pinning (full)
- **`coderluii/holyclaude:X.Y.Z-slim`** — Version pinning (slim)

Dockerfile accepts `--build-arg VARIANT=full|slim` to select which packages to install.

SOURCE: README.md lines 212-231; Dockerfile lines 6-7, 17, 65-76 (accessed 2026-03-28)

---

## Installation & Usage

### Quickest Start (5 minutes)

1. Create a folder for HolyClaude:

```bash
mkdir holyclaude && cd holyclaude
```

2. Create a `docker-compose.yaml` file:

```yaml
services:
  holyclaude:
    image: coderluii/holyclaude:latest
    container_name: holyclaude
    restart: unless-stopped
    shm_size: 2g
    cap_add:
      - SYS_ADMIN
      - SYS_PTRACE
    security_opt:
      - seccomp=unconfined
    ports:
      - "3001:3001"
    volumes:
      - ./data/claude:/home/claude/.claude
      - ./workspace:/workspace
    environment:
      - TZ=UTC
```

3. Start the container:

```bash
docker compose up -d
```

4. Open the web UI:

```
http://localhost:3001
```

5. Create a CloudCLI account and sign in with your Anthropic account.

SOURCE: README.md lines 97-124 (accessed 2026-03-28)

### Persistence and Credentials

Two bind-mounted volumes:

| Volume | Purpose | Survives rebuilds? |
|--------|---------|-------------------|
| `./data/claude:/home/claude/.claude` | Claude Code settings, credentials, API keys, Claude's memory file | YES — never delete |
| `./workspace:/workspace` | Your code and projects | YES |

Credentials are stored locally in your bind-mounted volume, not in Docker Hub, not in the cloud. You maintain full control.

SOURCE: README.md lines 265-276, 340-354 (accessed 2026-03-28)

### Using Additional AI CLIs

After starting the container, you can switch between AI CLIs:

```bash
docker compose exec holyclaude claude <command>          # Anthropic
docker compose exec holyclaude gemini <command>          # Google Gemini
docker compose exec holyclaude codex <command>           # OpenAI
docker compose exec holyclaude cursor <command>          # Cursor
docker compose exec holyclaude task-master <command>     # TaskMaster
docker compose exec holyclaude junie <command>           # JetBrains
docker compose exec holyclaude opencode <command>        # OpenCode
```

SOURCE: README.md lines 534-545 (accessed 2026-03-28)

### Upgrading

Pull the latest image and restart:

```bash
docker compose pull coderluii/holyclaude
docker compose up -d
```

Your `./data/claude/` and `./workspace/` volumes persist across upgrades. All credentials, settings, and code survive.

SOURCE: README.md lines 161-165 (discussed as comparison) (accessed 2026-03-28)

---

## Limitations and Caveats

### 1. Docker Sandboxing Requirements

HolyClaude uses standard Docker security settings (SYS_ADMIN, SYS_PTRACE, seccomp=unconfined) required by Chromium to function inside containers. These are the same settings used by Playwright, Puppeteer, and every containerized browser in CI pipelines. **Not a unique limitation of HolyClaude, but important to understand before deploying in security-sensitive environments.**

SOURCE: README.md lines 290-291 (accessed 2026-03-28)

### 2. WORKDIR Must Be Non-Root-Owned

The Claude Code CLI installer hangs if WORKDIR is root-owned. HolyClaude sets `WORKDIR /workspace` and ensures it's owned by the `claude` user (UID 1000).

**Implication**: If you modify the Dockerfile and change WORKDIR to a root-owned directory, the Claude Code installer will hang during container startup.

SOURCE: Dockerfile line 99; README.md line 39 (accessed 2026-03-28)

### 3. Shared Memory Limit

Chromium can crash if `shm_size` is < 2GB. Default Docker shared memory is 64MB. The docker-compose templates include `shm_size: 2g` to prevent this.

**If you see random tab crashes or X11 errors**: increase `shm_size` to 4GB.

SOURCE: README.md lines 293-294 (accessed 2026-03-28)

### 4. Network Mount Polling

If volumes are mounted via SMB (NAS, Samba, CIFS), standard inotify file watchers fail. Solution: enable polling-based file watching by setting:

```bash
CHOKIDAR_USEPOLLING=1        # Node.js
WATCHFILES_FORCE_POLLING=true # Python
```

**Tradeoff**: Polling uses more CPU than inotify. Only enable for network mounts.

SOURCE: README.md lines 376-381 (accessed 2026-03-28)

### 5. ChatGPT Plus Subscription Does Not Work

OpenAI Codex CLI (included in HolyClaude) requires an OpenAI API key, which is NOT provided by ChatGPT Plus subscription. ChatGPT Plus only grants access to chat.openai.com. You need a separate OpenAI API key for the Codex CLI.

SOURCE: README.md lines 188-189 (accessed 2026-03-28)

### 6. Limited Built-in Customization

HolyClaude provides environment variables for common scenarios (timezones, UID/GID, memory limits, notification services, AI provider keys). Deeper customization (adding system packages, modifying s6-overlay services, changing Node/Python versions) requires building your own Dockerfile or using the slim variant and running `apt install` / `npm install` / `pip install` at runtime.

Confidence: **medium** — Not documented as a limitation in the README, but a practical constraint of any pre-built image.

### 7. No Kubernetes Manifest (Yet)

HolyClaude currently supports Docker Compose and bare Docker only. Kubernetes support (Helm chart) is marked as "coming soon" but not yet available.

SOURCE: README.md line 140 (accessed 2026-03-28)

---

## Relevance to Claude Code Development

### 1. Pre-Tested Claude Code Integration

HolyClaude validates that Claude Code CLI works correctly inside Docker with all required dependencies. If you're building Claude Code integrations, testing them in HolyClaude confirms they work in containerized environments (CI/CD pipelines, cloud VMs, team workflows).

### 2. Browser Automation Testing

Chromium + Playwright + Xvfb are pre-configured and battle-tested. If you're developing Claude Code features that involve web scraping, screenshot generation, or headless browser testing, HolyClaude provides a proven base to validate those features.

### 3. Multi-AI-Provider Workflows

HolyClaude demonstrates how to bundle 7 AI CLIs (Claude Code, Gemini, OpenAI, Cursor, TaskMaster, Junie, OpenCode) in a single container. If you're designing workflows that compare outputs across multiple AI providers or fall back between providers, HolyClaude is a working reference.

### 4. Process Management and Graceful Shutdown

s6-overlay manages multiple long-running services (CloudCLI, Xvfb, Claude Code) with proper signal handling. If you're building Claude Code features that need to coordinate with other services, HolyClaude's architecture is a reference for proper process lifecycle management.

### 5. Containerized Development Environment

For Claude Code users developing in containers (Docker, Kubernetes, cloud VMs), HolyClaude eliminates the "why doesn't Claude Code work in Docker" troubleshooting loop. It's a ready-to-use development environment that guarantees compatibility.

---

## References

- **GitHub Repository**: <https://github.com/CoderLuii/HolyClaude> (accessed 2026-03-28)
- **Docker Hub**: <https://hub.docker.com/r/coderluii/holyclaude> (accessed 2026-03-28)
- **README.md**: Full documentation with all configuration examples
- **Dockerfile**: Multi-stage build process, package selection logic
- **docker-compose.yaml** (quick template) and **docker-compose.full.yaml** (reference): Complete container configuration
- **docs/configuration.md**: Detailed configuration guide
- **docs/ollama.md**: Ollama integration guide

---

## Freshness Tracking

| Section | Last verified | Confidence | Next review |
|---------|---------------|-----------|-------------|
| **Identity & metadata** | 2026-03-28 | high | 2026-06-28 |
| **Features** | 2026-03-28 | high | 2026-06-28 |
| **Technical architecture** | 2026-03-28 | high | 2026-06-28 |
| **Installation & usage** | 2026-03-28 | high | 2026-06-28 |
| **Limitations** | 2026-03-28 | medium | 2026-06-28 |

**Last refreshed**: 2026-03-28
**Next scheduled review**: 2026-06-28 (3 months)

**Confidence notes**:
- **high** (Identity, Features, Architecture, Usage): All data extracted from official README, Dockerfile, and GitHub API. Version verified as v1.1.4 on 2026-03-28.
- **medium** (Limitations): Limitations 1-6 are explicitly documented in README. Limitation 7 (Kubernetes) is inferred from README's "coming soon" marker; no explicit documentation of constraints.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Kernel](../agent-infrastructure/kernel-sh.md) | agent-infrastructure | browsers-as-a-service alternative to HolyClaude's Chromium + Playwright headless browser stack |
| [Gastown](../research-agent-patterns/gastown.md) | research-agent-patterns | multi-agent orchestration via tmux transport — HolyClaude provides the containerized environment for similar multi-session Claude Code coordination |
| [Claw Loop](../research-agent-patterns/claw-loop.md) | research-agent-patterns | autonomous orchestration via tmux + cron supervisor pattern — HolyClaude pre-configures tmux and cron for this workflow |
| [Everything Claude Code](../agent-frameworks/everything-claude-code.md) | agent-frameworks | 65+ skills + 16 agents for Claude Code; HolyClaude hosts this system in a ready-to-use container with all prerequisite tools pre-installed |
| [Oh My OpenCode](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | production-scale Claude Code orchestration with Sisyphus multi-agent architecture — requires containerized environment like HolyClaude |
| [Ollama + Subagents + Web Search](../research-agent-patterns/ollama-subagents-web-search-claude-code.md) | research-agent-patterns | local LLM integration with Claude Code subagents; HolyClaude includes OLLAMA_HOST environment variable support |
| [Browser MCP](../mcp-ecosystem/browsermcp-mcp.md) | mcp-ecosystem | Chrome browser automation via MCP; HolyClaude's Chromium + Playwright setup provides the underlying browser control infrastructure |
| [Using tmux with Claude Code](../developer-tools/using-tmux-with-claude-code.md) | developer-tools | practical guide for tmux-based multi-pane agent orchestration — HolyClaude includes tmux pre-configured in the container |
| [devenv](../developer-tools/devenv.md) | developer-tools | declarative dev environment alternative using Nix; HolyClaude achieves similar goal via Docker with emphasis on bundling pre-built binaries rather than building from modules |
