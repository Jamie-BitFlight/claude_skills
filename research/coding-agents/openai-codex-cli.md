---
title: "OpenAI Codex CLI - OpenAI's Terminal Coding Agent"
research_date: "2026-03-01"
source_url: "https://developers.openai.com/codex/cli"
github_url: "https://github.com/openai/codex"
documentation_url: "https://developers.openai.com/codex"
version_at_research: "v0.106.0 (rust-v0.106.0)"
license: "Apache-2.0"
last_verified: "2026-03-01"
version_at_verification: "v0.106.0"
next_review: "2026-06-01 (3 months)"
---

## Overview

OpenAI Codex CLI is a lightweight, terminal-native coding agent that runs locally on the developer's machine and connects to OpenAI's models (including the `codex-1` and `gpt-5.1-codex` family) via the Responses API. Written in Rust with a TypeScript CLI wrapper, it provides a full-screen TUI (terminal user interface), a headless `exec` mode for CI/CD automation, and can function as both an MCP client (connecting to external tools) and an experimental MCP server (exposing Codex's capabilities to other agents). It is the direct counterpart to Claude Code from OpenAI's perspective.

**Core Value Proposition**: A locally-executing, open-source coding agent tightly integrated with OpenAI's model ecosystem, offering OS-enforced sandbox isolation, a layered approval policy system, declarative project instructions via `AGENTS.md`, and extensibility via MCP and Skills.

---

## Problem Addressed

| Problem | Solution |
| ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Coding agents with no local execution — cloud-only round-trips add latency | Runs as a native local process; only LLM calls go to OpenAI's API |
| Unrestricted file system and network access by default | Two-layer security model: OS sandbox (Landlock/seccomp on Linux, Seatbelt on macOS) plus approval policies |
| Agents that apply changes without explicit human sign-off | `on-request` approval policy pauses before every edit outside workspace or network call |
| Per-project context that can't travel with the codebase | `AGENTS.md` file hierarchy (global → git root → current dir) with merge semantics |
| AI coding tools locked to one provider's model | Config-level model switching; custom providers via `model_provider` in `config.toml` |
| No path from interactive use to CI/CD automation | `codex exec` headless mode with `--json`, `--ephemeral`, `--output-schema`, and `CODEX_API_KEY` env var |
| Extensibility gaps — no way to add domain-specific tools | MCP client support (any MCP server configurable in `config.toml`) and Skills (`SKILL.md` files) |

---

## Key Statistics (as of 2026-03-01)

| Metric | Value | Date Gathered |
| --------------------- | ------------ | -------------- |
| GitHub Stars | 62,506 | 2026-03-01 |
| GitHub Forks | 8,314 | 2026-03-01 |
| Contributors | 366 | 2026-03-01 |
| Open Issues | 1,411 | 2026-03-01 |
| Latest Release | v0.106.0 | 2026-02-26 |
| Primary Language | Rust (96.1%) | 2026-03-01 |
| Secondary Language | TypeScript (2.3%) | 2026-03-01 |
| License | Apache-2.0 | — |
| Created | 2025-04-13 | — |

---

## Key Features

### Terminal UI (TUI) and Interactive Mode

- Full-screen terminal interface built with Ratatui (Rust TUI framework)
- Keyboard-first slash command palette: `/model`, `/plan`, `/permissions`, `/fork`, `/resume`, `/diff`, `/review`, `/mcp`, `/agent`, `/apps`, `/compact`, `/status`, `/init`, `/debug-config`
- `/fork` creates a parallel conversation branch from the current turn's `response_id` bookmark
- `/compact` summarizes earlier turns to reclaim context window space
- `/plan` enters a distinct planning mode with a configurable `plan_mode_reasoning_effort` setting
- Personality modes switchable via `/personality`: `friendly`, `pragmatic`, or `none`
- Image and screenshot inputs via `local_image` item type in user turns

### Headless / Non-Interactive Execution (`codex exec`)

- `codex exec "<prompt>"` runs a task without the TUI, streaming progress to stderr and final message to stdout
- `--json` outputs JSON Lines with events: `thread.started`, `turn.completed`, `item.completed`, `error`
- `--ephemeral` prevents persisting session files to disk
- `--full-auto` enables automatic edits without approval prompts
- `--output-schema <path>` constrains the final response to a supplied JSON Schema
- `-o <path>` writes the final message to a file
- `--skip-git-repo-check` allows running outside a Git repository
- `codex exec resume --last "<next-task>"` resumes the last session; target by session ID for specific threads
- `CODEX_API_KEY` environment variable for CI/CD authentication without interactive login

### Permission and Approval Model

Codex implements a two-layer security model:

**Layer 1 — OS Sandbox** (technical enforcement):

| Platform | Mechanism |
| -------- | --------- |
| macOS | `sandbox-exec` with Seatbelt policies |
| Linux | Landlock + seccomp |
| Windows | WSL implementation or native Windows sandbox |

**Sandbox modes** (configured via `--sandbox` flag or `sandbox_mode` in `config.toml`):

| Mode | Filesystem | Network |
| ---- | ---------- | ------- |
| `read-only` (default) | Read-only outside workspace | Disabled |
| `workspace-write` | Writable within workspace roots; `.git`, `.agents`, `.codex` remain read-only | Disabled by default; opt-in via `network_access = true` |
| `danger-full-access` | Unrestricted | Unrestricted |

**Layer 2 — Approval Policy** (behavioral control):

| Policy | Behavior |
| ------ | -------- |
| `on-request` | Prompts before edits outside workspace or network access |
| `untrusted` | Auto-approves known-safe read ops; prompts before any state-mutating command |
| `never` | Disables all approval prompts |
| `{ reject = {...} }` | Auto-rejects specific categories (sandbox escalations, exec-policy triggers, MCP elicitations) while keeping others interactive |

### Execution Policy System (exec policy)

- Rules stored in `.rules` files under `~/.codex/rules/` using Starlark syntax (Python-like)
- `prefix_rule()` function matches command prefixes with `allow`, `prompt`, or `forbidden` decisions
- Shell chains (`bash -lc "cmd1 && cmd2"`) are split via tree-sitter before rule evaluation
- `codex execpolicy check --rules ~/.codex/rules/default.rules -- <command>` for testing rules
- User-approved commands are automatically persisted to the user layer for future executions
- Admins enforce restrictions via `requirements.toml` (cannot be overridden by user `config.toml`)

### AGENTS.md Instruction Hierarchy

- Three-tier merge system: global (`~/.codex/`) → git root → current working directory
- Each tier checks `AGENTS.md.override` first, then `AGENTS.md`; at most one file per directory is included
- Files concatenate root-downward; closer directories take precedence
- Default size cap: `project_doc_max_bytes = 32 KiB`; configurable per session
- `project_doc_fallback_filenames` recognizes alternative naming conventions
- `child_agents_md` feature flag (experimental) enables hierarchical scope and precedence guidance
- Verify active instructions: `codex --ask-for-approval never "Summarize the current instructions."`
- Generate a scaffold: `/init` command writes a starter `AGENTS.md` to the current directory

### Skills (`SKILL.md` Files)

- Skills are reusable instruction modules discovered from the working directory and its ancestors
- Each skill is a `SKILL.md` file; the `/agent` command and explicit `skill` item type in user turns load them
- `Op::ListSkills` (via MCP or internal API) enumerates available skills for one or more `cwd` values
- `EventMsg::ListSkillsResponse` returns per-cwd skill entries with `skills` and `errors`

### MCP Integration

**MCP Client Mode** (stable):

- Configured in `~/.codex/config.toml` under `[mcp_servers.<id>]`
- Each server entry supports: `command`, `args`, `env`, `env_vars`, `http_headers`, `enabled_tools`, `disabled_tools`, `startup_timeout_sec`, `tool_timeout_sec`, `required`
- `/mcp` slash command lists configured tools in the active session
- `requirements.toml` (admin-layer) can allowlist MCP servers with identity verification

**MCP Server Mode** (experimental):

- `codex mcp-server` launches Codex as a JSON-RPC 2.0 MCP server over stdio
- Exposes methods: `newConversation`, `sendUserMessage`, `sendUserTurn`, `interruptConversation`, `listConversations`, `resumeConversation`, `archiveConversation`, `model/list`, `collaborationMode/list`, `gitDiffToRemote`, `execOneOffCommand`
- Server sends `codex/event` notifications with live agent output and auth state
- Approval prompts flow as server→client requests: `applyPatchApproval` and `execCommandApproval`; client must reply `{ decision: "allow" | "deny" }`
- Inspect with: `npx @modelcontextprotocol/inspector codex mcp-server`

### Model and Reasoning Options

- Default model: `gpt-5.1-codex` (also referenced as `codex-1` in some contexts)
- Available models fetched at runtime via `model/list` MCP method with pagination
- Each model exposes `supportedReasoningEfforts`: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`
- `model_reasoning_effort` and `model_reasoning_summary` configurable in `config.toml`
- `/model` slash command switches model inline without restarting the session
- Plan mode has a separate `plan_mode_reasoning_effort` config key (defaults to `medium`)
- `model_verbosity` for GPT-5 Responses API: `low`, `medium`, `high`

### Multi-Agent Support (Experimental)

- Enable via `/experimental` slash command or `[features]` in `config.toml`
- Parallel tasks recommended via separate `Codex` engine instances per thread (one task per engine at a time by design)
- `/agent` command switches between active agent threads in the TUI
- `response_id` bookmarks allow forking from earlier conversation states: store the `TurnComplete` bookmark and pass it in a future `Op::UserTurn` with `last_response_id`
- Task interruption and resumption via `Op::Interrupt` and new `Op::UserTurn` with the bookmark

### Collaboration Modes

- `collaborationMode/list` returns built-in preset masks (partial settings applied over a base mode)
- Each preset can override `reasoning_effort`, `developer_instructions`, sandbox, and approval settings
- Passing `collaborationMode` in `sendUserTurn` applies the preset for that turn
- Setting `developer_instructions: null` in a preset uses built-in instructions for the mode

### Web Search

- Configurable via `web_search` in `config.toml`: `disabled`, `cached` (OpenAI-maintained index), `live` (real-time)
- Defaults to `cached` to reduce prompt injection exposure
- Admin-enforced via `allowed_web_search_modes` in `requirements.toml`

---

## Technical Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│                       Codex CLI (Rust)                               │
│                                                                      │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  TUI (Ratatui)  │  │  exec (CLI)  │  │  mcp-server          │   │
│  │                 │  │              │  │  (MCP JSON-RPC)       │   │
│  │ - Slash cmds    │  │ - Headless   │  │                       │   │
│  │ - Approval UI   │  │ - --json     │  │ - newConversation     │   │
│  │ - Plan mode     │  │ - --ephemeral│  │ - sendUserTurn        │   │
│  │ - Multi-agent   │  │ - CI/CD      │  │ - applyPatchApproval  │   │
│  └─────────────────┘  └──────────────┘  └──────────────────────┘   │
│                     │                                                │
│                     ▼                                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Codex Core Engine                          │   │
│  │                                                               │   │
│  │  Session → Task → Turn (Submission Queue / Event Queue)       │   │
│  │                                                               │   │
│  │  Tools: shell exec | apply_patch | web_search | MCP client   │   │
│  │                                                               │   │
│  │  Approval gates: OS sandbox + approval policy + exec policy  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                     │                                                │
└─────────────────────┼────────────────────────────────────────────── ┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
┌──────────────┐ ┌─────────┐ ┌────────────────────────────────────┐
│OpenAI         │ │   MCP   │ │   Workspace                         │
│Responses API  │ │ Servers │ │                                     │
│               │ │         │ │ ~/.codex/config.toml               │
│ - codex-1     │ │ (any    │ │ ~/.codex/AGENTS.md                 │
│ - gpt-5.1     │ │  MCP    │ │ .codex/config.toml (project)       │
│ - gpt-4.1     │ │  server)│ │ AGENTS.md (per-directory)          │
│               │ │         │ │ SKILL.md files                     │
│ reasoning:    │ │         │ │ ~/.codex/rules/*.rules             │
│ none→xhigh    │ │         │ │                                    │
└──────────────┘ └─────────┘ └────────────────────────────────────┘
```

**Key architectural decisions**:

- **Rust core as reusable library**: `codex-rs/core/` contains business logic intended for arbitrary UI implementations — the TUI, exec CLI, and MCP server all drive the same engine via the `SQ`/`EQ` queue-pair protocol
- **SQ/EQ protocol**: `Op` variants sent on the Submission Queue; `EventMsg` variants received on the Event Queue; transport-agnostic (threads, IPC, stdin/stdout, TCP, HTTP/2, gRPC)
- **Single task per engine**: By design, one `Codex` engine runs at most one `Task` at a time; parallelism is achieved by running multiple engine instances
- **response_id bookmarking**: Each `TurnComplete` event returns the OpenAI `response_id`, enabling conversation forking and resumption from any point
- **Zero-dependency binary**: Distributed as a standalone native executable (no Node.js runtime required for the Rust build; npm install wraps the binary)
- **SQLite state**: Conversation history and session state stored in SQLite under `CODEX_SQLITE_HOME` or `CODEX_HOME`

---

## Installation & Usage

### Installation

```bash
# npm (installs npm wrapper + Rust binary)
npm install -g @openai/codex

# Homebrew (macOS)
brew install --cask codex

# Direct binary download (Linux x86_64)
curl -L https://github.com/openai/codex/releases/latest/download/codex-x86_64-unknown-linux-musl.tar.gz | tar xz
mv codex-x86_64-unknown-linux-musl codex
chmod +x codex
```

### Authentication

```bash
# Interactive: sign in with ChatGPT account (opens browser)
codex  # select "Sign in with ChatGPT" on first run

# API key (recommended for CI/CD)
export CODEX_API_KEY="sk-..."
codex exec --json "Run all tests and report failures"
```

### Interactive Mode

```bash
# Launch TUI
codex

# With initial prompt
codex "Refactor the auth module to use JWT"

# Generate AGENTS.md scaffold
codex  # then type /init
```

### Non-Interactive / CI Mode

```bash
# Basic headless execution
codex exec "Add docstrings to all public functions in src/"

# Full automation with sandboxing
codex exec --full-auto --sandbox workspace-write "Fix all TypeScript errors"

# JSON output for machine parsing
codex exec --json "Summarize recent git changes" | jq .

# Output to file with JSON Schema constraint
codex exec --output-schema schema.json -o result.json "Generate API spec"

# Resume last session
codex exec resume --last "Now run the tests"

# No session persistence
codex exec --ephemeral "Quick one-off check"
```

### MCP Server

```bash
# Run Codex as an MCP server
codex mcp-server

# Inspect available tools
npx @modelcontextprotocol/inspector codex mcp-server

# Test exec policy rules
codex execpolicy check --rules ~/.codex/rules/default.rules -- git push
```

### Configuration (`~/.codex/config.toml`)

```toml
model = "gpt-5.1-codex"
model_reasoning_effort = "high"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = false

[mcp_servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_TOKEN = "GITHUB_TOKEN" }
enabled = true

[features]
child_agents_md = true
```

### AGENTS.md Example

```markdown
# Project Instructions

## Testing
- Always run `npm test` before marking a task complete
- Write unit tests for all new public functions

## Code Style
- Use TypeScript strict mode
- Follow ESLint rules; do not disable rules without justification

## Security
- Never log secrets or API keys
- All external inputs must be validated before use
```

---

## Modes of Operation

### Interactive TUI Mode (default `codex`)

Full-screen terminal interface. Human reviews and approves each agent action. Supports conversation branching (`/fork`), planning mode (`/plan`), multi-agent threads (`/agent`), and session resumption (`/resume`).

### Exec Mode (`codex exec`)

Headless automation for scripting and CI/CD. Outputs structured JSON Lines when `--json` is set. Integrates with GitHub Actions via `CODEX_API_KEY` environment variable.

### MCP Server Mode (`codex mcp-server`)

Exposes Codex as a tool for other AI agents or orchestrators. The entire conversation lifecycle (create, send, approve, interrupt, archive) is controllable via JSON-RPC 2.0 over stdio. Enables agent-to-agent coordination where a parent agent delegates coding tasks to Codex.

### Desktop App Mode (`codex app`)

Launches the Electron-based desktop application UI (available at `chatgpt.com/codex`). Same underlying engine as the CLI.

---

## Relevance to Claude Code Development

### Applications

- **Direct Competitor Analysis**: Codex CLI is the primary direct competitor to Claude Code — same terminal-native paradigm, same AGENTS.md/SKILL.md pattern names, similar MCP integration. Feature-by-feature comparison is high-value for product decisions
- **Architecture Reference**: The `SQ`/`EQ` queue-pair protocol and transport-agnostic core engine design is a mature pattern for separating agent logic from UI implementations
- **MCP Server Pattern**: Codex's MCP server mode (exposing an agent as an MCP tool) demonstrates a powerful composability pattern — Claude Code could similarly expose itself as an MCP server for orchestration by other agents
- **Exec Policy DSL**: The Starlark-based `.rules` system with `prefix_rule()`, tree-sitter shell parsing, and admin-enforced `requirements.toml` is a sophisticated approach to execution governance worth studying
- **response_id Bookmarking**: The `TurnComplete` response_id bookmark pattern enables deterministic conversation forking and resumption — relevant for multi-agent coordination in this repo's research
- **Skills Pattern Validation**: Codex independently implemented a `SKILL.md`-based Skills system with `Op::ListSkills` and `EventMsg::ListSkillsResponse` — strong validation that this repo's skill architecture is the correct abstraction

### Patterns Worth Adopting

- **`requirements.toml` admin layer**: Immutable security constraints that user `config.toml` cannot override — useful for enterprise and team deployments
- **Collaboration mode presets**: Named presets that bundle reasoning effort + approval policy + developer instructions into a single toggle
- **Exec policy with tree-sitter shell parsing**: Evaluating each command in a shell chain separately prevents dangerous commands from hiding alongside safe ones
- **Output schema for structured output**: `--output-schema` / `outputSchema` in `sendUserTurn` enables type-safe agent output for downstream processing
- **`codex exec` to `codex exec resume`**: Stateful non-interactive sessions that can be continued with additional prompts — better than single-shot invocations for complex workflows

### Competitive Analysis

| Feature | OpenAI Codex CLI | Claude Code |
| ----------------------------- | ----------------------------------- | ------------------------------------------ |
| Open Source | Yes (Apache-2.0) | No |
| Primary Language | Rust (core) + TypeScript (wrapper) | TypeScript |
| Model Support | OpenAI models (codex-1, gpt-5.1+) | Claude models only |
| Sandbox Enforcement | OS-level (Landlock, Seatbelt) | Process-level |
| Approval Policies | 4 named levels + custom reject rules | Approve/auto modes |
| Exec Policy DSL | Yes (Starlark `.rules` files) | No direct equivalent |
| AGENTS.md | Yes (hierarchical, 3-tier) | Yes (CLAUDE.md) |
| Skills System | Yes (SKILL.md + ListSkills API) | Yes (this repo) |
| MCP Client | Yes | Yes |
| MCP Server Mode | Yes (experimental) | No |
| Non-Interactive / CI Mode | `codex exec` with JSON output | Supported |
| Multi-Agent | Experimental (parallel engines) | Supported (Agent tool) |
| Conversation Bookmarking | response_id per turn | Session-based |
| Web Search | Yes (cached or live) | Dependent on tools |
| Image Input | Yes | Yes |
| Authentication | ChatGPT OAuth + API key | API key |
| Pricing | Included in Plus/Pro/Team plans; API at standard rates | Subscription |
| IDE Integration | VS Code, Cursor, Windsurf extensions | Terminal only |
| Desktop App | Yes (`codex app`) | No |

---

## References

- [GitHub Repository: openai/codex](https://github.com/openai/codex) (accessed 2026-03-01)
- [Codex CLI Documentation](https://developers.openai.com/codex/cli) (accessed 2026-03-01)
- [Codex Docs — Main](https://developers.openai.com/codex) (accessed 2026-03-01)
- [Codex Security and Sandbox](https://developers.openai.com/codex/security) (accessed 2026-03-01)
- [Codex Non-Interactive Mode](https://developers.openai.com/codex/noninteractive) (accessed 2026-03-01)
- [Codex AGENTS.md Guide](https://developers.openai.com/codex/guides/agents-md) (accessed 2026-03-01)
- [Codex Auth](https://developers.openai.com/codex/auth) (accessed 2026-03-01)
- [Codex Exec Policy](https://developers.openai.com/codex/exec-policy) (accessed 2026-03-01)
- [Codex Configuration Reference](https://developers.openai.com/codex/config-reference) (accessed 2026-03-01)
- [Codex Slash Commands](https://developers.openai.com/codex/cli/slash-commands) (accessed 2026-03-01)
- [GitHub: codex-rs/docs/protocol_v1.md](https://github.com/openai/codex/blob/main/codex-rs/docs/protocol_v1.md) (accessed 2026-03-01)
- [GitHub: codex-rs/docs/codex_mcp_interface.md](https://github.com/openai/codex/blob/main/codex-rs/docs/codex_mcp_interface.md) (accessed 2026-03-01)
- [GitHub Releases: openai/codex](https://github.com/openai/codex/releases) (accessed 2026-03-01)

---
