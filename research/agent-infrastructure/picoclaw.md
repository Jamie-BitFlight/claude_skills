---
title: "PicoClaw"
---

## Overview

PicoClaw is an ultra-lightweight personal AI assistant written in Go, designed to run on $10
hardware with less than 10MB RAM. Inspired by
[nanobot](https://github.com/HKUDS/nanobot) and built via a self-bootstrapping process
(95% agent-generated code), it provides a single-binary AI agent deployable on RISC-V, ARM,
and x86 Linux devices — including decade-old Android phones via Termux — with 400× faster
startup than comparable Python-based solutions.

---

## Problem Addressed

| Problem                                                  | Solution                                                                    |
| -------------------------------------------------------- | --------------------------------------------------------------------------- |
| AI assistants require expensive hardware (Mac Mini $599) | Runs on $9.9 LicheeRV-Nano RISC-V board; <10MB RAM in production            |
| Python/TypeScript agents have slow cold starts           | Go binary boots in <1 second on a 0.6GHz single-core device                |
| AI infrastructure is hard to deploy at the edge          | Single self-contained binary for RISC-V, ARM, x86; no external runtime     |
| Personal AI agents lack messaging channel integration    | Telegram, Discord, QQ, DingTalk, LINE, WeCom built-in                      |
| AI development lacks transparency about code provenance  | 95% of core was agent-generated; self-bootstrapping methodology documented  |
| Setting up LLM providers is complex                      | Zero-code `model_list` config — add any OpenAI-compatible endpoint          |

---

## Key Statistics

| Metric           | Value               | Date Gathered |
| ---------------- | ------------------- | ------------- |
| GitHub Stars     | 18,121              | 2026-02-23    |
| GitHub Forks     | 2,164               | 2026-02-23    |
| Open Issues      | 312                 | 2026-02-23    |
| Primary Language | Go                  | 2026-02-23    |
| Repository Age   | Since 2026-02-04    | 2026-02-23    |
| Latest Release   | v0.1.2              | 2026-02-23    |
| Translations     | 6 languages (README) | 2026-02-23   |

---

## Key Features

### Runtime and Performance

- **<10MB RAM**: Core functionality fits in under 10MB; recent PR merges may push to 10–20MB
  until planned optimization pass
- **<1 second startup**: Cold-start on 0.6GHz single-core hardware
- **Single binary**: Cross-compiled for RISC-V, ARM64, x86\_64; no Node.js, Python, or JVM
- **Docker Compose support**: Optional containerized deployment with gateway and agent profiles
- **Android/Termux support**: Runs on old Android phones via Termux with `proot`

### Multi-Channel Messaging

Six built-in channel integrations with unified `allow_from` allowlist security:

- **Telegram** — token-based bot; recommended for personal use
- **Discord** — bot token + MESSAGE CONTENT INTENT; optional mention-only mode
- **QQ** — AppID + AppSecret via QQ Open Platform
- **DingTalk** — Client ID + Client Secret
- **LINE** — Channel Secret + Channel Access Token + HTTPS webhook
- **WeCom** — both Bot (webhook URL) and App (CorpID + AgentID) modes

### AI Provider Configuration

Zero-code multi-provider setup via `model_list` array in `config.json`:

- OpenRouter, Anthropic, OpenAI, Google Gemini, Zhipu — any OpenAI-compatible endpoint
- Per-model `api_key`, `max_tokens`, and `temperature` settings
- Named model aliases (e.g., `"gpt4"`, `"claude-sonnet-4.6"`) referenced by agent defaults

### Agent Workflows

- **Full-Stack Engineer**: Code generation and file operations
- **Logging & Planning Management**: Scheduling and memory-backed planning
- **Web Search & Learning**: Tavily, Brave Search, DuckDuckGo with auto-fallback

### Edge Hardware Targets

Purpose-built for Sipeed's own hardware product line:

- `$9.9` LicheeRV-Nano (RISC-V, Ethernet or WiFi6) — minimal home assistant
- `$30–$50` NanoKVM / `$100` NanoKVM-Pro — automated server maintenance
- `$50` MaixCAM / `$100` MaixCAM2 — smart camera monitoring

---

## Technical Architecture

### Stack Components

| Component        | Technology                                             |
| ---------------- | ------------------------------------------------------ |
| Core Language    | Go (single binary, `make build` / `make build-all`)   |
| Config           | JSON (`~/.picoclaw/config.json`)                       |
| Web Search       | Tavily, Brave Search, DuckDuckGo (auto-fallback)       |
| Gateway          | HTTP webhook server (channels: Telegram, Discord, etc) |
| Agent Mode       | One-shot (`-m "..."`) or interactive                   |
| Build            | Makefile (`make deps`, `make build`, `make install`)   |
| Container        | Docker Compose with `gateway` and `agent` profiles     |

### Data Flow (Agent Message Handling)

1. Inbound message via channel (Telegram, Discord, CLI, etc.)
2. `allow_from` allowlist check — deny if sender not in list
3. Agent loop: LLM provider call with context + tools
4. Tool execution (web search, file ops, code run)
5. Response dispatched back to originating channel

### AI-Bootstrapped Development

PicoClaw was built using its own predecessor (nanobot/OpenClaw) to drive the Go migration:

- 95% of core code is agent-generated
- Human-in-the-loop refinement for architecture decisions
- Self-bootstrapping methodology serves as a living demo of agentic software development

---

## Installation & Usage

### Precompiled Binary (Android/Termux example)

```bash
wget https://github.com/sipeed/picoclaw/releases/download/v0.1.2/picoclaw-linux-arm64
chmod +x picoclaw-linux-arm64
pkg install proot
termux-chroot ./picoclaw-linux-arm64 onboard
```

### Build from Source

```bash
git clone https://github.com/sipeed/picoclaw.git
cd picoclaw
make deps
make build        # single platform
make build-all    # cross-compile all platforms
make install
```

### Docker Compose

```bash
cp config/config.example.json config/config.json
# Edit config.json: set API keys, model_list, channels
docker compose --profile gateway up -d
docker compose run --rm picoclaw-agent -m "What is 2+2?"
```

### Quick Start CLI

```bash
# 1. Initialize
picoclaw onboard

# 2. Configure ~/.picoclaw/config.json with model_list and API keys

# 3. Chat
picoclaw agent -m "What is 2+2?"

# 4. Start gateway (messaging channels)
picoclaw gateway
```

### Minimal `config.json`

```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.picoclaw/workspace",
      "model": "claude-sonnet",
      "max_tokens": 8192,
      "temperature": 0.7,
      "max_tool_iterations": 20
    }
  },
  "model_list": [
    {
      "model_name": "claude-sonnet",
      "model": "anthropic/claude-sonnet-4-6",
      "api_key": "your-anthropic-key"
    }
  ],
  "tools": {
    "web": {
      "duckduckgo": { "enabled": true, "max_results": 5 }
    }
  }
}
```

---

## Relevance to Claude Code Development

### Applications

1. **Edge Deployment Reference**: PicoClaw proves a Go-native AI agent can run Claude-class
   LLMs on $10 RISC-V hardware. Relevant when designing Claude Code plugins that must run in
   resource-constrained CI environments or embedded contexts.

2. **AI-Bootstrapped Methodology**: The self-bootstrapping Go migration (95% agent-generated
   core) is a concrete example of using Claude Code agents to autonomously rewrite an existing
   codebase in a new language — a pattern directly applicable to large-scale refactoring tasks.

3. **Zero-Code Provider Config**: The `model_list` JSON array pattern for adding AI providers
   without code changes is a clean configuration pattern for skills that need to support
   multiple LLM backends.

4. **Multi-Channel Gateway Architecture**: The unified `allow_from` + channel config pattern
   is worth studying for any Claude Code plugin that needs to dispatch AI responses to multiple
   messaging platforms.

### Patterns Worth Adopting

1. **Single-binary cross-compilation**: PicoClaw's `make build-all` with goreleaser demonstrates
   how to ship a Go agent binary for ARM/RISC-V/x86 from a single CI job — applicable if
   Claude Code plugins ever ship native helper binaries.

2. **Named model aliases in config**: Referencing models by alias (`"gpt4"`, `"claude-sonnet"`)
   rather than full provider strings keeps agent config portable across provider changes.

3. **Auto-fallback web search**: The DuckDuckGo → Tavily → Brave Search fallback chain is a
   practical pattern for tool reliability without hard provider dependencies.

4. **Termux deployment pattern**: `pkg install proot && termux-chroot ./binary onboard` shows
   how to run a Linux binary on Android without root — useful for documenting install paths in
   skills targeting mobile edge devices.

### Competitive Context

PicoClaw sits between nanobot (Python, >100MB RAM) and ZeroClaw (Rust, <5MB RAM):

| Dimension        | NanoBot (Python) | PicoClaw (Go) | ZeroClaw (Rust) |
| ---------------- | ---------------- | ------------- | --------------- |
| RAM              | >100MB           | <10–20MB      | <5MB            |
| Startup (0.8GHz) | >30s             | <1s           | <10ms           |
| Language         | Python           | Go            | Rust            |
| Cost hardware    | ~$50 SBC         | $10 SBC       | $10 SBC         |
| Stars (Feb 2026) | —                | 18,121        | 14,966          |
| Channels         | Limited          | 6+            | 15+             |
| License          | MIT              | MIT           | Other           |

ZeroClaw has more channels, more providers, and lower memory usage. PicoClaw has more community
traction (18K vs. 15K stars) and is backed by Sipeed's hardware ecosystem. See
[zeroclaw.md](./zeroclaw.md) for the Rust counterpart.

### Caution: Very Early Stage

PicoClaw was created on 2026-02-04 and hit 18K stars within two weeks. The project is
in early development with known network security issues — the README explicitly warns against
production deployment before v1.0. Recent PR merges have increased RAM usage to 10–20MB;
resource optimization is scheduled post feature-stabilization. Treat as reference architecture,
not production infrastructure.

---

## References

| Source                 | URL                                                              | Accessed   |
| ---------------------- | ---------------------------------------------------------------- | ---------- |
| GitHub Repository      | <https://github.com/sipeed/picoclaw>                             | 2026-02-23 |
| GitHub README          | <https://github.com/sipeed/picoclaw/blob/main/README.md>         | 2026-02-23 |
| Official Website       | <https://picoclaw.io>                                            | 2026-02-23 |
| Sipeed Company         | <https://sipeed.com>                                             | 2026-02-23 |
| GitHub API (repo meta) | `gh api repos/sipeed/picoclaw`                                   | 2026-02-23 |
| GitHub API (release)   | `gh api repos/sipeed/picoclaw/releases/latest`                   | 2026-02-23 |
| ROADMAP.md             | <https://github.com/sipeed/picoclaw/blob/main/docs/ROADMAP.md>   | 2026-02-23 |

**Research Method**: Information gathered from GitHub web page, GitHub API (stars, forks,
issues, releases), and project README. Repository created 2026-02-04; rapidly growing community.

---
