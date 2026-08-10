---
title: "Stakpak Agent — Secure DevOps AI Agent"
license: "Apache-2.0"
---

# Stakpak Agent

## Overview

Stakpak is a security-hardened, multi-provider AI agent built in Rust, optimized for DevOps and infrastructure automation. The platform provides a terminal UI, REST API, and MCP server interfaces for running autonomous agents that generate infrastructure code, manage deployments, and automate operational tasks while maintaining strict credential security. Stakpak supports local execution on laptops or 24/7 autonomous operation via system services (launchd/systemd), with native integrations for Slack, Telegram, and Discord notifications.

**Core Value Proposition**: Run AI-assisted DevOps work with full control over LLM provider selection (Claude, GPT, Gemini, or custom), credential security (secret substitution), and infrastructure isolation via Docker sandboxing.

**Source**: <https://github.com/stakpak/agent> (accessed 2026-03-13)

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| DevOps agents expose production credentials to LLM APIs | Secret substitution: LLM receives variable references, credentials resolved at execution time |
| Scaling DevOps automation from local to production requires re-architecture | Single CLI works locally or scales via system services (24/7 autopilot with cron-driven scheduling) |
| AI agents lack access to infrastructure (Kubernetes, Docker, Terraform) | Secure Docker/Kubernetes runtime sandbox with shell, file system, and tool execution access |
| DevOps workflows require manual credential management for each tool | Encrypted credential storage in config; mTLS for MCP server communication; warden guardrails block destructive operations |
| Integrating AI agents into DevOps teams requires custom tooling | Native channel integrations: Slack, Telegram, Discord for notifications and command input; MCP server for IDE integration |

**Source**: <https://github.com/stakpak/agent/blob/main/README.md> and <https://github.com/stakpak/agent/blob/main/GETTING-STARTED.md> (accessed 2026-03-13)

---

## Purpose & Use Cases

Stakpak is a **security-hardened DevOps AI agent** optimized for operations and infrastructure work. Primary use cases:

- Generate infrastructure code (Terraform, Kubernetes, Dockerfile)
- Debug Kubernetes clusters and container orchestration
- Configure CI/CD pipelines (GitHub Actions, etc.)
- Automate deployments without exposing production credentials
- Run 24/7 in autonomous mode (autopilot) with scheduled tasks
- Execute long-running tasks with real-time progress streaming (Docker builds, deployments)

The agent is designed for teams that need AI assistance for DevOps without surrendering credential security or operational control.

---

## Technical Architecture

Stakpak is structured as a monolithic Rust workspace with separate subsystems:

### Workspace Organization

```
cli/                    # Main CLI binary (stakpak command)
├─ commands/
│  ├─ agent/run/        # Agent execution engine (interactive, async, streaming)
│  ├─ autopilot/        # 24/7 autonomous runtime (schedules, channels)
│  ├─ acp/              # Agent Client Protocol (Zed editor integration)
│  ├─ mcp/              # Model Context Protocol server and proxy
│  ├─ auth/             # Authentication (interactive and non-interactive)
│  └─ watch/            # Schedule runtime (cron-driven task execution)
├─ config/              # Configuration file parsing and profile management
└─ onboarding/          # Interactive setup wizard

tui/                    # Terminal UI (ratatui-based)
├─ services/handlers/   # Event handlers (tool execution, shell, output)
└─ app/events.rs        # Input/output event definitions

libs/                   # Shared libraries
├─ ai/                  # LLM provider abstraction (stakai)
│  └─ providers/
│     ├─ anthropic/     # Anthropic API client
│     ├─ openai/        # OpenAI-compatible endpoint support
│     └─ gemini/        # Google Gemini API client
├─ api/                 # API client and local processing (stakpak-api)
│  ├─ local/
│  │  ├─ context_managers/    # Message history reduction
│  │  └─ hooks/               # Scratchpad and task board context
│  └─ remote/           # Remote AI calls
├─ agent-core/          # Core agent logic (tools, streaming, hooks)
├─ server/              # HTTP API server
├─ gateway/             # Channel runtime (Slack, Telegram, Discord)
├─ shared/              # Shared type definitions
└─ mcp/                 # MCP client, server, and proxy implementations
```

### Execution Flow

1. **Configuration** → User sets profiles in `~/.stakpak/config.toml` (LLM provider, tools, system prompt)
2. **Authentication** → Provider credentials loaded from config or environment variables
3. **Agent Loop** → User input → context reduction → LLM call → tool execution → streaming response
4. **Tool Execution** → Tools run with secret substitution enabled (credentials stay encrypted)
5. **Output** → Real-time streaming to TUI or async mode

### Message Pipeline

User input → `Vec<ChatMessage>` → `ContextManager::reduce_context()` → `Vec<LLMMessage>` → Provider-specific format → LLM API call

---

## Key Features

### 1. Security-Hardened Architecture

- **Secret Substitution**: LLM receives variable references, not actual credentials. Agent resolves placeholders at execution time.
- **Mutual TLS (mTLS)**: Encrypted communication between MCP client and server by default.
- **Warden Guardrails**: Network-level policies block destructive operations before they execute.
- **Secure Password Generation**: Cryptographically secure password creation with configurable complexity rules.
- **Privacy Mode**: Redacts IP addresses, AWS account IDs, and other sensitive metadata from logs and outputs.

### 2. 24/7 Autonomous Runtime (Autopilot)

Stakpak runs as a system service (launchd on macOS, systemd on Linux) with persistent scheduling and messaging:

- **Cron-Based Schedules**: Define recurring agent tasks with standard cron syntax.
- **Messaging Channels**: Slack, Telegram, Discord integration for notifications and command input.
- **Unified Configuration**: Single `~/.stakpak/autopilot.toml` file manages all schedules and channels.
- **Preflight Checks**: `stakpak autopilot doctor` validates system readiness before startup.

Commands:

```
stakpak up                      # Start autopilot
stakpak down                    # Stop autopilot
stakpak autopilot status        # View runtime health
stakpak autopilot logs          # Stream logs
stakpak autopilot schedule add  # Create new schedule
stakpak autopilot channel add   # Register messaging channel
```

### 3. Infrastructure Code Indexing & Search

- Automatic local indexing of Terraform, Kubernetes manifests, Dockerfiles, GitHub Actions workflows
- Semantic search across indexed infrastructure code
- Context-aware code generation based on existing patterns

### 4. Real-Time Progress Streaming

Long-running operations (Docker builds, Helm deployments, Terraform applies) stream progress updates in real-time instead of blocking on completion.

### 5. DevOps Knowledge (Rulebooks)

Customizable rulebooks define organizational SOPs, playbooks, and deployment procedures:

```bash
stakpak rb get                                    # List rulebooks
stakpak rb apply my-org/deployment-guide.md      # Register a rulebook
stakpak rb delete stakpak://my-org/old-guide.md  # Remove rulebook
```

Rulebooks are markdown files with YAML frontmatter, providing context-specific guidance to the agent.

### 6. Asynchronous Task Management

Background command support for port forwarding, local servers, and long-running processes with proper tracking and cancellation.

### 7. Reversible File Operations

All file modifications are automatically backed up, enabling rollback recovery if changes prove problematic.

### 8. Bulk Message Approval

Approve multiple tool calls at once for efficient workflow execution instead of individual confirmations.

### 9. Editor Integration (Agent Client Protocol)

Zed editor integration via ACP allows:
- Real-time AI chat with context-aware assistance
- Live code analysis and modification
- Tool execution from within the editor
- Session persistence across editor restarts

---

## LLM Provider Support

Stakpak abstracts LLM providers behind a unified interface, supporting:

1. **Stakpak Managed** (remote): Requires Stakpak API key (no card for trial)
2. **Anthropic**: Claude models via Anthropic API
3. **OpenAI**: GPT models via OpenAI API
4. **Gemini**: Google Gemini models
5. **Custom OpenAI-Compatible**: Local endpoints (Ollama, LM Studio) or custom inference servers

Configuration via `~/.stakpak/config.toml` with provider-prefixed model names:

```toml
model = "anthropic/claude-sonnet-4-5"
model = "openai/gpt-4"
model = "gemini/gemini-2.0-flash"
model = "offline/qwen/qwen3-coder-30b"  # Custom provider
```

---

## MCP Integration

Stakpak operates as both an MCP client and server:

### MCP Server Modes
- **Local** (`--tool-mode local`): File operations and command execution (no API key required)
- **Remote** (`--tool-mode remote`): AI-powered code generation and search tools (API key required)
- **Combined** (`--tool-mode combined`): Both local and remote tools (default)

### MCP Proxy
Multiplexes connections to multiple upstream MCP servers with unified configuration and secret redaction.

---

## Installation & Usage

### Installation

#### Homebrew (Recommended for macOS/Linux)
```bash
brew tap stakpak/stakpak
brew install stakpak
```

#### Binary Release
Download from [GitHub Releases](https://github.com/stakpak/agent/releases)

#### Docker
```bash
docker pull ghcr.io/stakpak/agent:latest

# For containerization tasks
docker run -it \
  -v "/var/run/docker.sock":"/var/run/docker.sock" \
  -v "{your app path}":"/agent/" \
  --entrypoint stakpak ghcr.io/stakpak/agent:latest
```

#### From Source
```bash
git clone https://github.com/stakpak/agent.git
cd agent
cargo build --release
```

### Usage

#### Interactive TUI Mode
```bash
stakpak                    # Open interactive terminal UI
stakpak -c <checkpoint>    # Resume from checkpoint
```

#### Async Mode (Headless)
```bash
stakpak --async "Help me understand this codebase"
```

#### Authentication Setup
```bash
# Stakpak managed API key (no card required)
stakpak auth login --api-key $STAKPAK_API_KEY

# Bring your own key
stakpak auth login --provider anthropic --api-key $ANTHROPIC_API_KEY
stakpak auth login --provider openai --api-key $OPENAI_API_KEY

# Or via environment variables
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
```

#### Autopilot Initialization
```bash
# Preflight checks (required on remote machines)
stakpak autopilot doctor

# Interactive setup wizard
stakpak autopilot init
# Or via one-command setup
stakpak onboard

# Start 24/7 runtime
stakpak up
```

#### Schedule Management (Non-Interactive)
```bash
stakpak autopilot schedule add health \
  --cron '*/5 * * * *' \
  --prompt 'Check system health' \
  --profile monitoring

stakpak autopilot schedule list
stakpak autopilot schedule trigger health  # Manual execution
```

#### Channel Setup
```bash
stakpak autopilot channel add slack \
  --bot-token $SLACK_BOT_TOKEN \
  --app-token $SLACK_APP_TOKEN

stakpak autopilot channel test
```

---

## Context Management & History Reduction

Stakpak implements multiple context reduction strategies for long conversations:

1. **Task Board Context Manager**: Preserves individual messages with semantic threading
2. **Simple Context Manager**: Flattens conversation history to summary text
3. **File Scratchpad Manager**: Maintains working notes in a temporary scratchpad file

Reduction is budget-aware—when conversation exceeds the LLM's context window threshold, the agent automatically trims history while preserving recent interactions and key context.

---

## Limitations & Caveats

- **Autopilot System Requirements**: Requires Docker to be installed and accessible to the current user; 2GB+ RAM recommended for reliable autopilot + sandbox execution; Linux user services may require linger to survive logout.
- **TTY Requirement**: Interactive TUI mode requires a terminal. Headless/async modes work in non-TTY environments.
- **Credential Management**: While secrets are substituted at execution time, they must be available in the local environment or config file — Stakpak does not manage credential storage beyond what the OS provides.
- **Network Access**: Tool operations (git, docker, API calls) require network access from the agent's execution context. Firewalled environments may require proxy configuration.
- **mTLS Certificate Management**: Default mTLS uses auto-generated certificates valid for local connections only; production deployments should use custom certificate chains.

---

## Relevance to Claude Code Development

**High relevance** — Stakpak demonstrates several patterns applicable to Claude Code agent work:

1. **Multi-Provider LLM Abstraction**: Template for unified LLM provider interface supporting multiple backends (Anthropic, OpenAI, custom)
2. **Security-First Credential Handling**: Secret substitution pattern ensures sensitive data never enters the LLM context
3. **Message Context Management**: Reusable context reduction strategies for long-running conversations
4. **Autonomous Scheduling**: 24/7 task execution model suitable for background agents
5. **DevOps Knowledge Encoding**: Rulebook approach for encoding organizational procedures and SOPs
6. **MCP Integration**: Reference implementation of MCP client/server with security hardening
7. **Editor Integration**: ACP protocol for embedding agents in code editors
8. **Real-Time Progress Streaming**: Pattern for streaming long-running operation updates without blocking

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [OpenAI Codex CLI](../openai-codex-cli.md) | coding-agents | Rust-based coding agent with sandbox security, MCP client/server support, and headless execution modes |
| [Cline](../cline.md) | coding-agents | Human-in-the-loop coding agent supporting multiple providers with MCP extensibility and approval workflows |
| [Accomplish](../accomplish.md) | coding-agents | Local-first agent with permission-gated execution, multi-provider support, and MCP tool integration |
| [ZeroClaw](../../agent-infrastructure/zeroclaw.md) | agent-infrastructure | Ultra-lightweight Rust infrastructure for autonomous agents with 28+ providers and deny-by-default security |
| [TinyClaw](../../research-agent-patterns/tinyclaw.md) | research-agent-patterns | Multi-agent 24/7 orchestration with cron scheduling, isolated workspaces, and peer-to-peer handoffs |
| [Narsil-MCP](../../mcp-ecosystem/narsil-mcp.md) | mcp-ecosystem | Rust MCP server providing code intelligence and security scanning tools for AI assistants |

---

## References

- [README.md](https://github.com/stakpak/agent/blob/main/README.md) (accessed 2026-03-13)
- [GETTING-STARTED.md](https://github.com/stakpak/agent/blob/main/GETTING-STARTED.md) (accessed 2026-03-13)
- [AGENTS.md](https://github.com/stakpak/agent/blob/main/AGENTS.md) (accessed 2026-03-13)
- [Cargo.toml — Workspace Definition](https://github.com/stakpak/agent/blob/main/Cargo.toml) (version 0.3.68, accessed 2026-03-13)
- [Dockerfile](https://github.com/stakpak/agent/blob/main/Dockerfile) (accessed 2026-03-13)
- [GitHub Repository](https://github.com/stakpak/agent) — 872 stars, 98 forks (as of 2026-03-13)

---

## Repository Structure Notes

The agent uses a modular Rust workspace with clear separation of concerns:
- CLI binaries (`cli/`) and TUI (`tui/`) are user-facing
- Libraries (`libs/`) are internal and versioned together
- Configuration is file-based (`~/.stakpak/config.toml`, `~/.stakpak/autopilot.toml`)
- Docker image uses aqua for lazy-loading CLI tools (reduces image from ~2GB to ~600MB)
- Dockerfile target: Rust 1.91.0 (slim), runtime: Python 3.13 with Docker CLI and cloud tooling
