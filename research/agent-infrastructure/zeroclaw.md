---
name: ZeroClaw
description: Lightweight Rust-based autonomous agent infrastructure supporting 28+ AI providers, 15+ messaging channels (Telegram, Discord, Slack, Matrix, Signal, WhatsApp), pluggable SQLite memory backends with FTS5 vector search, and trait-driven swappable subsystems. Use when deploying agents to resource-constrained hardware (sub-5MB RAM, $10 edge boards), integrating multi-provider AI support, connecting agents to messaging platforms, implementing deny-by-default security models, achieving near-instant cold starts, or avoiding vendor lock-in through fully configurable architecture.
license: Other (MIT per README badge; NOASSERTION per GitHub API)
metadata:
  topic: zeroclaw
  category: agent-infrastructure
  source_url: https://github.com/zeroclaw-labs/zeroclaw
  github: zeroclaw-labs/zeroclaw
  version: "v0.1.0"
  verified: "2026-02-19"
  next_review: "2026-05-19"
---

## Overview

ZeroClaw is a fully autonomous AI assistant infrastructure written in Rust, designed for minimal resource consumption and maximum portability. It runs on $10 hardware with less than 5MB peak RAM at startup, providing a single-binary deployment that supports 28+ AI providers, 15+ messaging channels, pluggable memory backends, and a trait-driven architecture where every subsystem — providers, channels, tools, memory, tunnels — can be swapped via config changes with no code modifications.

---

## Problem Addressed

| Problem                                            | Solution                                                                    |
| -------------------------------------------------- | --------------------------------------------------------------------------- |
| AI agents require expensive hardware               | Sub-5MB RAM footprint; runs on $10 ARM/RISC-V boards                        |
| Runtime startup latency exceeds user tolerance     | Near-instant cold starts (`<10ms` on edge hardware)                         |
| AI infrastructure creates vendor lock-in           | Trait-based architecture; every subsystem is swappable via config           |
| Deploying agents to messaging platforms is complex | 15+ built-in channels (Telegram, Discord, Slack, WhatsApp, Matrix, Signal)  |
| Security defaults are permissive                   | Deny-by-default allowlists, `127.0.0.1` binding, filesystem scoping         |
| Memory systems require external dependencies       | Self-contained SQLite hybrid search (FTS5 + vector cosine) with no Pinecone |
| Multi-provider AI support requires rewrites        | 28+ built-in providers + custom OpenAI-compatible endpoints                 |

---

## Key Statistics

| Metric           | Value                  | Date Gathered |
| ---------------- | ---------------------- | ------------- |
| GitHub Stars     | 14,966                 | 2026-02-19    |
| GitHub Forks     | 1,568                  | 2026-02-19    |
| Open Issues      | 71                     | 2026-02-19    |
| Contributors     | ~84 (from Link header) | 2026-02-19    |
| Primary Language | Rust                   | 2026-02-19    |
| Repository Age   | Since 2026-02-13       | 2026-02-19    |
| Latest Release   | v0.1.0 (2026-02-19)    | 2026-02-19    |

---

## Key Features

### Runtime and Performance

- **Sub-5MB RAM**: Release build peak at `~4.1MB` for `zeroclaw status`; `~3.9MB` for `--help`
- **Near-instant starts**: `<10ms` real time on release builds for CLI commands
- **Single binary**: `~8.8MB` release binary; no Node.js, Python, or JVM dependency
- **Cross-platform**: ARM, x86, RISC-V; Homebrew available for macOS/Linuxbrew
- **Docker runtime**: Optional sandboxed execution via `runtime.kind = "docker"`

### Trait-Driven Architecture

Every subsystem is a Rust trait — swap implementations with a config change:

- **AI Models** (`Provider` trait): 28+ built-ins including OpenAI, Anthropic, OpenRouter, plus custom OpenAI-compatible and Anthropic-compatible endpoints
- **Channels** (`Channel` trait): CLI, Telegram, Discord, Slack, Mattermost, iMessage, Matrix, Signal, WhatsApp, Email, IRC, Lark, DingTalk, QQ, Webhook
- **Memory** (`Memory` trait): SQLite hybrid search, PostgreSQL, Lucid bridge, Markdown files, explicit no-op backend
- **Tools** (`Tool` trait): shell/file/memory, cron/schedule, git, browser, http_request, screenshot, composio (opt-in), delegate, hardware tools
- **Tunnels** (`Tunnel` trait): None, Cloudflare, Tailscale, ngrok, Custom

### Memory System

Custom full-stack search with zero external dependencies:

- Vector embeddings stored as BLOB in SQLite with cosine similarity search
- FTS5 virtual tables with BM25 keyword scoring
- Custom weighted merge of vector + keyword results (`vector_weight = 0.7`, `keyword_weight = 0.3`)
- `EmbeddingProvider` trait: OpenAI, custom URL, or noop
- Optional PostgreSQL backend via `storage.provider.config`
- LRU eviction cache for embedding reuse

### Security

- Gateway binds `127.0.0.1` by default; refuses `0.0.0.0` without tunnel or explicit opt-in
- 6-digit one-time pairing code on startup; bearer token for all webhook requests
- Filesystem scoping: `workspace_only = true` by default; 14 system dirs + 4 sensitive dotfiles blocked
- Null byte injection blocking; symlink escape detection via canonicalization
- Channel allowlists are deny-by-default (empty list = deny all; `"*"` = explicit open)
- Docker sandbox for tool execution isolation

### Subscription Auth

Multi-account encrypted auth profiles at rest:

- OpenAI Codex OAuth (ChatGPT subscription) via device-code or browser callback flow
- Anthropic/Claude Code auth via `setup-token` (Authorization header mode)
- Profile ID format: `<provider>:<profile_name>` (e.g., `openai-codex:work`)
- Encrypted profile store: `~/.zeroclaw/auth-profiles.json`

### Integrations and Skills

- 70+ integrations across 9 categories
- TOML manifest + `SKILL.md` instruction system (similar to Claude Code skills)
- `HEARTBEAT.md` periodic task engine
- OpenClaw (markdown) and AIEOS v1.1 (JSON) identity format support
- Migration command: `zeroclaw migrate openclaw`

---

## Technical Architecture

### Stack Components

| Component       | Technology                                                 |
| --------------- | ---------------------------------------------------------- |
| Core Language   | Rust (stable toolchain, `codegen-units=1` for edge compat) |
| Config          | TOML (`~/.zeroclaw/config.toml`)                           |
| Memory DB       | SQLite (FTS5 + BLOB vectors), optional PostgreSQL          |
| Gateway         | HTTP webhook server (default `127.0.0.1:3000`)             |
| Runtime         | Native or Docker sandboxed                                 |
| Daemon          | Background service with `zeroclaw service install`         |
| Build           | Cargo workspace (`crates/` subdirectories)                 |

### Subsystem Trait Hierarchy

<eg>
Runtime (Native / Docker)
    |
Daemon / Gateway
    |
Agent Loop
    |
Provider (AI Model) — Channel (Messaging) — Tool (Capabilities)
    |
Memory (SQLite / Postgres / Lucid / Markdown / None)
    |
Tunnel (Cloudflare / Tailscale / ngrok / None)
</eg>

### Data Flow (Agent Message Handling)

1. Inbound message received via channel (Telegram webhook, CLI, etc.)
2. Allowlist check — deny if sender not in allowlist
3. Memory recall: hybrid FTS5 + cosine vector search against SQLite
4. Provider API call with context + recalled memories
5. Tool execution if agent requests tools (sandboxed if Docker runtime)
6. Response dispatched back to channel
7. Memory save if `auto_save = true`
8. Observability hook (Noop / Log / Multi observer)

---

## Installation and Usage

### Homebrew

```bash
brew install zeroclaw
```

### Build from Source

```bash
git clone https://github.com/zeroclaw-labs/zeroclaw.git
cd zeroclaw
cargo build --release --locked
cargo install --path . --force --locked
export PATH="$HOME/.cargo/bin:$PATH"
```

### One-click Bootstrap

```bash
./bootstrap.sh --install-system-deps --install-rust --onboard --api-key "sk-..." --provider openrouter
```

### Core CLI Commands

```bash
# Onboarding
zeroclaw onboard --api-key sk-... --provider openrouter
zeroclaw onboard --interactive

# Agent interaction
zeroclaw agent -m "Hello, ZeroClaw!"
zeroclaw agent                          # interactive mode

# Daemon and gateway
zeroclaw daemon                         # autonomous runtime
zeroclaw gateway                        # webhook server (127.0.0.1:3000)
zeroclaw service install                # background service

# Auth (Claude Code / Anthropic)
zeroclaw auth setup-token --provider anthropic --profile default

# Auth (OpenAI Codex / ChatGPT)
zeroclaw auth login --provider openai-codex --device-code

# Diagnostics
zeroclaw status
zeroclaw doctor
zeroclaw channel doctor
```

### Configuration (`~/.zeroclaw/config.toml`)

```toml
api_key = "sk-..."
default_provider = "openrouter"
default_model = "anthropic/claude-sonnet-4-6"
default_temperature = 0.7

[memory]
backend = "sqlite"
auto_save = true
embedding_provider = "none"
vector_weight = 0.7
keyword_weight = 0.3

[gateway]
port = 3000
host = "127.0.0.1"
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Claude Code Auth Integration**: ZeroClaw explicitly supports `zeroclaw auth setup-token --provider anthropic` for Claude Code subscription auth. The README includes a critical notice that Anthropic updated Authentication and Credential Use terms on 2026-02-19 — OAuth tokens from Claude Free/Pro/Max are exclusively for Claude.ai and Claude Code; using them in other products may violate Consumer Terms of Service.

2. **Skill Architecture Parallel**: ZeroClaw's `SKILL.md` + TOML manifest system is structurally analogous to the claude_skills repository. Reference for alternative skill loading patterns.

3. **HEARTBEAT.md Pattern**: ZeroClaw's `HEARTBEAT.md` periodic task engine is a named-file-based task scheduling pattern directly comparable to Claude Code's memory system.

4. **Agent Infrastructure Reference**: ZeroClaw's trait-based swappable architecture (`Provider`, `Channel`, `Memory`, `Tool`) documents design patterns for building agent infrastructure that avoids vendor lock-in.

5. **Edge Deployment**: The sub-5MB RAM, single-binary model demonstrates deployment requirements for Claude Code skills on resource-constrained environments.

### Patterns Worth Examining

1. **Deny-by-default channel allowlists**: Empty allowlist = deny all is a clean security default pattern for multi-channel AI systems.

2. **Observability trait**: Noop → Log → Multi observer hierarchy is a minimal, extensible observability pattern for agents.

3. **Hybrid memory without external deps**: FTS5 + SQLite vector search with weighted merge shows how to build hybrid search without Pinecone or Elasticsearch.

4. **Explicit no-op backends**: `backend = "none"` for memory provides a named, explicit off-switch rather than implicit null behavior.

### Caution: Very Early Stage

ZeroClaw was created on 2026-02-13 and reached v0.1.0 on 2026-02-19 — it is six days old at time of research. The 14,966 stars likely reflect viral social media attention rather than production validation. The project is also actively dealing with impersonation forks (`openagen/zeroclaw`, `zeroclaw.org`). Treat architectural patterns as reference material; do not treat the project as production-stable.

---

## References

| Source                  | URL                                                                  | Accessed   |
| ----------------------- | -------------------------------------------------------------------- | ---------- |
| GitHub Repository       | <https://github.com/zeroclaw-labs/zeroclaw>                          | 2026-02-19 |
| GitHub README           | <https://github.com/zeroclaw-labs/zeroclaw/blob/main/README.md>      | 2026-02-19 |
| GitHub API (repo meta)  | `gh api repos/zeroclaw-labs/zeroclaw`                                | 2026-02-19 |
| GitHub API (release)    | `gh api repos/zeroclaw-labs/zeroclaw/releases/latest`                | 2026-02-19 |
| GitHub API (contrib)    | `gh api repos/zeroclaw-labs/zeroclaw/contributors?per_page=1&anon=true` | 2026-02-19 |
| Anthropic Auth Notice   | <https://code.claude.com/docs/en/legal-and-compliance#authentication-and-credential-use> | 2026-02-19 |

**Research Method**: Information gathered from GitHub API (stars, forks, issues, releases, contributors via Link header pagination), and README decoded from base64 GitHub contents API response. No external web search required — all data sourced from primary GitHub repository.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [esp-claw](../agent-frameworks/esp-claw.md) | agent-frameworks | referenced by esp-claw (agent-frameworks) |
| [happycapy](./happycapy.md) | agent-infrastructure | referenced by happycapy (agent-infrastructure) |
| [nemoclaw](./nemoclaw.md) | agent-infrastructure | referenced by nemoclaw (agent-infrastructure) |
