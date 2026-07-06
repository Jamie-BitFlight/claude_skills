---
title: "OpenFang"
research_date: "2026-02-27"
source_url: "https://www.openfang.sh/"
github_url: "https://github.com/RightNow-AI/openfang"
version_at_research: "v0.1.7"
license: "Apache-2.0 OR MIT (dual-licensed)"
last_verified: "2026-02-27"
version_at_verification: "v0.1.7"
next_review: "2026-05-27"
---

## Overview

OpenFang is an open-source Agent Operating System built in Rust — a single ~32MB binary that
runs autonomous agents on schedules without requiring user prompts. Rather than a Python
framework for building chatbots, it positions itself as a full OS for autonomous agents:
scheduling, multi-channel deployment, WASM sandboxing, 40 channel adapters, 27 LLM providers,
and 7 pre-built "Hands" (autonomous capability packages). First public release was February 2026.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Agent frameworks require constant user prompting to accomplish tasks | "Hands" run autonomously on schedules (e.g. daily lead research, 6 AM competitor reports) without any user input |
| Python-based frameworks have slow cold starts (2-6 seconds) and large install footprints (100-500 MB) | Single Rust binary, 32 MB install, 180 ms cold start, 40 MB idle memory |
| Agent tool execution has no security boundaries — tools can access anything | WASM dual-metered sandbox (fuel + epoch interruption) with a watchdog thread kills runaway code |
| Connecting agents to messaging platforms requires per-platform integration work | 40 built-in channel adapters (Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Teams, etc.) |
| Agents have no audit trail for sensitive autonomous actions | Merkle hash-chain audit trail cryptographically links every action; tampering breaks the chain |
| Switching between LLM providers requires code changes | 3 native drivers (Anthropic, Gemini, OpenAI-compatible) route to 27 providers with automatic fallback |
| Migrating from existing frameworks (OpenClaw, LangChain, AutoGPT) is manual and error-prone | Built-in migration engine imports agents, memory, skills, and configuration with one command |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 3,633 | 2026-02-27 |
| GitHub Forks | 386 | 2026-02-27 |
| Open Issues | 33 | 2026-02-27 |
| Contributors | 1 | 2026-02-27 |
| Latest Release | v0.1.7 | 2026-02-27 |
| Repo Created | 2026-02-24 | 2026-02-27 |
| Codebase Size | 137,728 lines of Rust (14 crates) | 2026-02-27 |
| Test Count | 1,767+ passing | 2026-02-27 |

SOURCE: [GitHub API — RightNow-AI/openfang](https://api.github.com/repos/RightNow-AI/openfang) (accessed 2026-02-27)

---

## Key Features

### Autonomous Hands (Pre-built Agent Packages)

Each Hand bundles a HAND.toml manifest, a multi-phase system prompt (500+ words), a SKILL.md
domain reference, and approval guardrails. All compiled into the binary — no downloads at
runtime.

- **Clip** — YouTube-to-shorts pipeline: downloads video, identifies moments, cuts vertical
  clips with captions, thumbnails, optional AI voice-over; publishes to Telegram/WhatsApp.
  8-phase pipeline using FFmpeg + yt-dlp + 5 STT backends.
- **Lead** — Daily prospect discovery: matches ICP, enriches with web research, scores 0-100,
  deduplicates against existing database, delivers qualified leads in CSV/JSON/Markdown.
- **Collector** — OSINT-grade continuous intelligence: target monitoring, change detection,
  sentiment tracking, knowledge graph construction, critical-event alerts.
- **Predictor** — Superforecasting engine: collects signals, builds calibrated reasoning chains,
  makes predictions with confidence intervals, tracks accuracy with Brier scores; contrarian
  mode argues against consensus deliberately.
- **Researcher** — Deep autonomous research: cross-references sources, evaluates credibility
  using CRAAP criteria, generates cited APA-format reports, supports multiple languages.
- **Twitter** — Autonomous X account manager: 7 rotating content formats, optimal scheduling,
  mention responses, performance tracking; approval queue required before any post.
- **Browser** — Web automation via Playwright bridge: navigation, form filling, multi-step
  workflows; mandatory purchase approval gate — will never spend money without confirmation.

### Security Architecture (16 Layers)

- **WASM Dual-Metered Sandbox** — tool code runs in WebAssembly with fuel metering + epoch
  interruption; watchdog thread kills runaway processes.
- **Merkle Hash-Chain Audit Trail** — every action cryptographically linked; tamper detection
  breaks the entire chain on modification.
- **Information Flow Taint Tracking** — labels propagate through execution, secrets tracked
  source-to-sink.
- **Ed25519 Signed Agent Manifests** — every agent identity and capability set signed.
- **SSRF Protection** — blocks private IPs, cloud metadata endpoints (including Alibaba/Azure),
  IPv6 localhost, 0.0.0.0, DNS rebinding attacks.
- **Secret Zeroization** — `Zeroizing<String>` auto-wipes API keys from memory immediately.
- **OFP Mutual Authentication** — HMAC-SHA256 nonce-based, constant-time verification for P2P.
- **Capability Gates** — RBAC; agents declare required tools, kernel enforces access.
- **Prompt Injection Scanner** — detects override attempts, data exfiltration patterns, shell
  reference injection in skills.
- **Loop Guard** — SHA256-based tool call loop detection with circuit breaker.
- **Path Traversal Prevention** — canonicalization with symlink escape prevention.
- **GCRA Rate Limiter** — cost-aware token bucket rate limiting with per-IP tracking.

### LLM Provider Routing

- 3 native drivers: Anthropic, Google Gemini, OpenAI-compatible
- 27 providers: Anthropic, Gemini, OpenAI, Groq, DeepSeek, OpenRouter, Together, Mistral,
  Fireworks, Cohere, Perplexity, xAI, AI21, Cerebras, SambaNova, HuggingFace, Replicate,
  Ollama, vLLM, LM Studio, Qwen, MiniMax, Zhipu, Moonshot, Qianfan, Bedrock, and more.
- Intelligent routing with task complexity scoring, automatic fallback, cost tracking, and
  per-model pricing. 123+ models in catalog.

### Channel Adapters (40 Total)

Core: Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Email (IMAP/SMTP)
Enterprise: Microsoft Teams, Mattermost, Google Chat, Webex, Feishu/Lark, Zulip
Social: LINE, Viber, Facebook Messenger, Mastodon, Bluesky, Reddit, LinkedIn, Twitch
Community: IRC, XMPP, Guilded, Revolt, Keybase, Discourse, Gitter
Privacy: Threema, Nostr, Mumble, Nextcloud Talk, Rocket.Chat, Ntfy, Gotify
Workplace: Pumble, Flock, Twist, DingTalk, Zalo, Webhooks

Each adapter supports per-channel model overrides, DM/group policies, rate limiting, and output
formatting. Per-channel RBAC enforcement is applied at the bridge layer.

### Skills Ecosystem

- 60 bundled skills across 14 categories
- 4 skill runtimes: Python, Node.js, WASM, PromptOnly
- FangHub marketplace with search/install
- ClawHub client for OpenClaw skill compatibility (reads SKILL.md natively)
- SHA256 checksum verification on all skill content
- Prompt injection scanning on skill content at load time

### API and Integration

- 140+ REST/WS/SSE endpoints using axum 0.8
- OpenAI-compatible `/v1/chat/completions` and `/v1/models` drop-in API
- Google A2A protocol support (agent card, task send/get/cancel)
- MCP client (JSON-RPC 2.0 over stdio/SSE) and MCP server mode
- Prometheus text-format `/api/metrics` endpoint
- Client SDKs: JavaScript (`@openfang/sdk`) and Python (`openfang_client`, `openfang_sdk`)

### Memory and Context Management

- SQLite-backed persistent memory with vector embeddings
- LLM-based session compaction triggered at 70% context capacity
- In-loop emergency trimming at 70%/90% thresholds with summary injection
- Tool profile filtering: reduces 41 tools to 4-10 for chat agents, saves 15-20K tokens
- Cross-channel canonical sessions with session repair (7-phase validation)

---

## Technical Architecture

14 Rust crates in a Cargo workspace (resolver = "2"), minimum Rust 1.75:

```text
openfang-kernel      Orchestration, workflows, metering, RBAC, scheduler, budget tracking
openfang-runtime     Agent loop, 3 LLM drivers, 53 tools, WASM sandbox, MCP, A2A
openfang-api         140+ REST/WS/SSE endpoints, OpenAI-compatible API, dashboard
openfang-channels    40 messaging adapters with rate limiting, DM/group policies
openfang-memory      SQLite persistence, vector embeddings, canonical sessions, compaction
openfang-types       Core types, taint tracking, Ed25519 manifest signing, model catalog
openfang-skills      60 bundled skills, SKILL.md parser, FangHub marketplace
openfang-hands       7 autonomous Hands, HAND.toml parser, lifecycle management
openfang-extensions  25 MCP templates, AES-256-GCM credential vault, OAuth2 PKCE
openfang-wire        OFP P2P protocol with HMAC-SHA256 mutual authentication
openfang-cli         CLI with daemon management, TUI dashboard, MCP server mode
openfang-desktop     Tauri 2.0 native app (system tray, notifications, global shortcuts)
openfang-migrate     OpenClaw, LangChain, AutoGPT migration engine
xtask                Build automation
```

Key dependency choices (from Cargo.toml):

- Async runtime: Tokio with `full` features
- HTTP server: axum 0.8 with WebSocket support
- WASM sandbox: wasmtime 41
- Database: rusqlite 0.31 with bundled SQLite
- Security: ed25519-dalek, zeroize, aes-gcm, argon2, hmac, sha2
- TUI: ratatui 0.29
- Desktop: Tauri 2.0
- Rate limiting: governor 0.8 (GCRA)

Build profile uses LTO, single codegen unit, symbol stripping, and opt-level 3 for minimal
binary size (resulting ~32 MB).

---

## Installation & Usage

```bash
# macOS/Linux — single-line install
curl -fsSL https://openfang.sh/install | sh

# Initialize (walks through provider setup)
openfang init

# Start the daemon
openfang start
# Dashboard live at http://localhost:4200
```

```powershell
# Windows
irm https://openfang.sh/install.ps1 | iex
openfang init
openfang start
```

```bash
# Activate a Hand — starts autonomous operation immediately
openfang hand activate researcher
openfang hand activate lead

# Check progress
openfang hand status researcher

# Pause without losing state
openfang hand pause lead

# Chat with an agent
openfang chat researcher

# Spawn a pre-built agent
openfang agent spawn coder

# OpenAI-compatible API drop-in
curl -X POST localhost:4200/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "researcher",
    "messages": [{"role": "user", "content": "Analyze Q4 market trends"}],
    "stream": true
  }'

# Migrate from OpenClaw
openfang migrate --from openclaw --dry-run
openfang migrate --from openclaw
```

```bash
# Development
cargo build --workspace --lib
cargo test --workspace    # 1,767+ tests
cargo clippy              # 0 warnings enforced
```

---

## Relevance to Claude Code Development

### Applications

- OpenFang reads SKILL.md natively — the same format used in this repository for Claude Code
  skills. Skills created in this repo could be directly consumed by OpenFang agents without
  format conversion.
- The HAND.toml format (bundling manifest, system prompt, SKILL.md reference, guardrails) is a
  concrete production implementation of the skill-packaging patterns this repository develops.
- OpenFang's FangHub marketplace is a working reference implementation of a skill distribution
  system, comparable to the Claude Code marketplace plugin this repo targets.
- ClawHub compatibility means OpenFang can consume skills from OpenClaw's existing marketplace,
  establishing cross-ecosystem portability as a design goal worth tracking.

### Patterns Worth Adopting

- **Approval gates at capability boundaries** — the Browser Hand's mandatory purchase
  confirmation gate is a concrete, auditable pattern for human-in-the-loop guardrails on
  sensitive agent actions. Applies directly to any skill that takes irreversible actions.
- **SKILL.md as runtime-injected context** — OpenFang injects SKILL.md domain knowledge into
  agent context at runtime rather than baking it into system prompts. This is observable
  evidence that the SKILL.md format has operational value beyond documentation.
- **Multi-phase system prompts for Hands** — 500+ word expert procedures (not one-liners)
  as the standard for autonomous agent instructions. Relevant to skill quality standards.
- **Tool profile filtering** — reducing 41 available tools to 4-10 per agent type saves 15-20K
  tokens per session. Applicable to how Claude Code skills manage tool visibility.
- **Token-aware session compaction** — 70% threshold trigger with summary injection is a
  specific, implementable pattern for context window management in long-running skill sessions.

### Integration Opportunities

- OpenFang exposes an MCP server mode (`openfang mcp`), enabling Claude Code to treat a running
  OpenFang instance as an MCP tool provider — bridging Claude Code's skill system to OpenFang's
  40 channel adapters and 7 autonomous Hands.
- The OpenAI-compatible API means any Claude Code skill using HTTP-based LLM calls could route
  through a local OpenFang instance for provider abstraction, cost tracking, and fallback.
- Skills from this repository could be published to FangHub (OpenFang's marketplace) given
  native SKILL.md support, expanding the distribution surface without format conversion.
- OpenFang's Python SDK (`openfang_sdk`) supports decorator-based agent authoring, which could
  integrate with Python-runtime skills in this repository.

---

## References

- [OpenFang GitHub Repository](https://github.com/RightNow-AI/openfang) (accessed 2026-02-27)
- [OpenFang Official Website](https://www.openfang.sh/) (accessed 2026-02-27)
- [GitHub API — Repository Metadata](https://api.github.com/repos/RightNow-AI/openfang) (accessed 2026-02-27)
- [GitHub API — Latest Release v0.1.7](https://api.github.com/repos/RightNow-AI/openfang/releases/latest) (accessed 2026-02-27)
- [OpenFang CHANGELOG.md](https://github.com/RightNow-AI/openfang/blob/main/CHANGELOG.md) (accessed 2026-02-27)
- [OpenFang Cargo.toml](https://github.com/RightNow-AI/openfang/blob/main/Cargo.toml) (accessed 2026-02-27)

---
