---
name: 'Unlocking the Codex Harness: How We Built the App Server (OpenAI)'
description: This OpenAI engineering article (published 2026-02-04, authored by Celia Chen) documents the architecture and design decisions behind the Codex App Server -- a bidirectional JSON-RPC API that serves...
license: Apache License 2.0
metadata:
  topic: codex-harness-openai
  category: evaluation-testing
  source_url: https://openai.com/index/unlocking-the-codex-harness/
  github: openai/codex
  version: "rust-v0.104.0"
  verified: "2026-02-21"
  next_review: "2026-05-21"
---

## Overview

This OpenAI engineering article (published 2026-02-04, authored by Celia Chen) documents the architecture and design decisions behind the Codex App Server -- a bidirectional JSON-RPC API that serves as the universal integration layer connecting the Codex coding agent harness to all client surfaces (web app, CLI, VS Code extension, Desktop app, JetBrains, Xcode). The App Server exposes the full Codex agent loop, thread lifecycle management, tool execution, and authentication flows through a stable, backward-compatible protocol. It replaces ad-hoc per-surface implementations with a single "Codex core" runtime that any client can drive via JSON-RPC over stdio (JSONL).

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Agent loop re-implemented for every client surface (TUI, VS Code, web, mobile) | Single "Codex core" library hosted by the App Server process; all surfaces drive same harness via JSON-RPC |
| Request/response RPC insufficient for streaming agent progress (diffs, tool calls, approvals) | Bidirectional JSON-RPC with explicit item/turn/thread lifecycle primitives; server initiates requests for approvals |
| Breaking changes across client releases when server evolves | Backward-compatible JSON-RPC surface; older clients talk to newer servers safely; TypeScript types generated from Rust protocol definitions |
| MCP semantics insufficient for rich session interactions (diff updates, session state) | Custom JSON-RPC "lite" protocol layered over stdio (JSONL); MCP retained as a separate, narrower integration path |
| Web sessions drop agent state when tab closes or network fails | Server-side thread persistence; clients reconnect and catch up from saved event history without rebuilding state |
| IDE and desktop partners cannot decouple release cycles from agent core | Partners (Xcode, JetBrains) point to a pinned or updated App Server binary independently of their client release |
| Multi-agent orchestration requires launching many concurrent agent sessions | Thread manager spawns one Codex core session per thread; App Server process hosts all threads concurrently |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars (openai/codex) | 61,233 | 2026-02-21 |
| Forks | 8,118 | 2026-02-21 |
| Contributors | 361 | 2026-02-21 |
| Latest Release | rust-v0.104.0 | 2026-02-18 |
| Article Publication Date | 2026-02-04 | 2026-02-21 |
| Article Author | Celia Chen (Member of Technical Staff, OpenAI) | 2026-02-21 |
| Primary Language (repo) | Rust | 2026-02-21 |

---

## Key Features

### App Server Protocol Architecture

- JSON-RPC "lite" variant: retains request/response/notification shape but omits `"jsonrpc": "2.0"` header; framed as JSONL over stdio
- Fully bidirectional: clients send requests, server sends notifications, and server can also initiate requests (e.g., approval prompts) that pause agent turns until the client replies
- Protocol versioning and capability negotiation via `initialize` handshake before any other method
- TypeScript client bindings auto-generated from Rust protocol definitions via `codex app-server generate-ts`
- JSON Schema bundle exportable for any language's code generator via `codex app-server generate-json-schema`
- Clients implemented across Go, Python, TypeScript, Swift, and Kotlin by Codex surfaces and partners

### Three Conversation Primitives

- **Item**: Atomic typed unit of I/O (user message, agent message, tool execution, approval request, diff); explicit three-phase lifecycle: `item/started` → optional `item/*/delta` streaming → `item/completed`
- **Turn**: One unit of agent work from user input to final agent output; contains ordered sequence of items representing intermediate steps
- **Thread**: Durable container for an ongoing user-agent session; supports create, resume, fork, archive; history persisted for client reconnection

### Codex Core Components Exposed

- Thread lifecycle and persistence: create, resume, fork, archive; event history enables consistent UI re-rendering across reconnects
- Config and auth: loads configuration, manages defaults, runs `Sign in with ChatGPT` authentication flows including credential state
- Tool execution and extensions: executes shell/file tools in sandbox; wires MCP servers and skills under a consistent policy model
- Core agent loop: orchestrates interaction between user, model, and tools

### App Server Process Architecture

- Four components: stdio reader, Codex message processor, thread manager, core threads
- Thread manager spins up one `CodexCore` session per thread
- Codex message processor translates client JSON-RPC requests into Codex core operations and transforms low-level events into stable, UI-ready JSON-RPC notifications
- One client request produces many event update notifications; enables rich UI rendering

### Integration Patterns for Clients

- **Local apps and IDEs** (VS Code, Desktop App, JetBrains, Xcode): bundle or fetch platform-specific App Server binary, launch as long-lived child process, communicate over stdio
- **Codex Web**: worker provisions container with checked-out workspace, launches App Server binary inside container; web app uses HTTP and SSE; stdio streams tunneled over persistent network connection (WebSocket-like) inside container
- **TUI/CLI**: planned refactor to use App Server as standard client rather than native direct Rust type access (enables remote machine execution)

### Integration Method Selection Guide

| Method | Best For | Limitation |
|--------|----------|------------|
| Codex App Server | Full harness, stable UI-ready event stream, rich session semantics | Client-side JSON-RPC binding implementation required |
| Codex as MCP server (`codex mcp-server`) | Existing MCP-based workflows, invoking Codex as a callable tool | MCP subset only; Codex-specific interactions (diff updates) may not map cleanly |
| Codex Exec | One-off tasks, CI pipelines, non-interactive automation | Single command only, not interactive |
| Codex SDK (TypeScript) | Native library interface without JSON-RPC client | Fewer languages, smaller surface area than App Server |
| Cross-provider agent harness protocols | Multi-provider agent coordination | Converges on common subset; provider-specific semantics lost |

---

## Technical Architecture

The Codex codebase is split into two main directories:

<eg>
openai/codex/
  codex-rs/          # Rust implementation
    app-server/      # App Server long-lived process
    app-server-protocol/  # JSON-RPC protocol type definitions
    app-server-test-client/  # Test client for debugging
    core/            # Codex core agent loop library
    cli/             # CLI binary
    config/          # Configuration handling
    chatgpt/         # ChatGPT auth integration
    mcp-server/      # MCP server integration
  codex-cli/         # TypeScript CLI components
  sdk/               # TypeScript SDK
</eg>

Agent execution flow:

<eg>
Client (VS Code / Desktop / Web / TUI)
    |
    | JSON-RPC over stdio (JSONL)
    v
App Server Process
    ├── stdio reader          (reads JSONL from client)
    ├── Codex message processor  (translates JSON-RPC ↔ Codex core events)
    ├── Thread manager        (one CodexCore session per thread)
    └── Core threads          (agent loop, tool execution, persistence)
</eg>

For web sessions, stdio is tunneled:

<eg>
Browser (HTTP + SSE) → Codex Backend → Worker → Container (App Server binary over stdio)
</eg>

The protocol uses `initialize` as a mandatory first message. Subsequent agent interactions follow this pattern:

<eg>
Client → thread/create
Client → turn/submit (user input)
Server → thread/started
Server → turn/started
Server → item/started (user message)
Server → item/completed (user message)
Server → item/started (tool call)
... (tool execution)
Server → [approval request] (pauses turn)
Client → approval response
Server → item/started (agent message)
Server → item/*/delta (streaming)
Server → item/completed (agent message)
Server → turn/completed
</eg>

---

## Installation & Usage

The App Server is part of the Codex CLI binary. Install via npm:

```bash
npm install -g @openai/codex
```

Or from source (Rust):

```bash
git clone https://github.com/openai/codex
cd openai/codex/codex-rs
cargo build --release
```

Debug the App Server with the built-in test client:

```bash
codex debug app-server send-message-v2 "run tests and summarize failures"
```

Generate TypeScript client bindings from Rust protocol definitions:

```bash
codex app-server generate-ts
```

Generate JSON Schema bundle for any language's code generator:

```bash
codex app-server generate-json-schema
```

Run Codex as an MCP server (narrower integration path):

```bash
codex mcp-server
```

Run Codex non-interactively for CI pipelines:

```bash
codex exec "run tests and summarize failures"
```

Initialize handshake example (JSON-RPC):

```json
{
  "method": "initialize",
  "id": 0,
  "params": {
    "clientInfo": {
      "name": "codex_vscode",
      "title": "Codex VS Code Extension",
      "version": "0.1.0"
    }
  }
}
```

---

## Relevance to Claude Code Development

### Applications

- **Reference architecture for multi-surface agent deployment**: The App Server pattern directly applies to any agent (including Claude Code) that needs to serve multiple client surfaces (CLI, web, IDE) from a single harness without duplicating agent logic
- **Agent loop protocol design**: The item/turn/thread primitives provide a proven vocabulary for streaming agent interactions that map cleanly to UI rendering needs; applicable to designing Claude Code's own conversation streaming API
- **Approval flow patterns**: The bidirectional approval-pause-resume mechanism (server initiates approval request, turn pauses, client responds) is directly applicable to Claude Code's permission and approval UX
- **Thread persistence for reconnect**: The server-side event history pattern enabling client reconnect without state rebuild is relevant to Claude Code's long-running task management

### Patterns Worth Adopting

- **Three-level conversation hierarchy** (item → turn → thread): Clean separation of concerns; items stream incrementally, turns bound a unit of agent work, threads provide durable session context
- **Backward-compatible protocol evolution**: Designing JSON-RPC surfaces with versioning and capability negotiation from the start prevents breaking changes as the protocol evolves
- **Schema-first protocol generation**: Defining the protocol in a typed language (Rust) and generating client bindings (TypeScript, JSON Schema) eliminates hand-written client boilerplate and keeps protocol definitions as the single source of truth
- **Explicit item lifecycle events** (`started`/`delta`/`completed`): Enables clients to begin rendering immediately on `started`, stream incremental updates, and finalize on `completed` -- directly applicable to Claude Code streaming output
- **Stdio as universal transport**: JSON-RPC over stdio (JSONL) works for local processes, can be tunneled over WebSocket for remote/container sessions, and requires no HTTP server infrastructure for local integrations

### Integration Opportunities

- **Claude Code App Server**: Claude Code could adopt an analogous App Server architecture to expose its agent loop to multiple surfaces (Cursor, Windsurf, JetBrains, web UIs) without re-implementing the agent logic per integration
- **MCP interoperability**: The article explicitly positions MCP as a narrower "callable tool" integration path while the App Server handles richer session semantics -- Claude Code skill development should account for the same distinction when designing MCP vs. native integration APIs
- **Protocol generation tooling**: The `codex app-server generate-ts` / `generate-json-schema` commands are a pattern worth replicating in Claude Code skills for any protocol that needs multi-language clients
- **Remote agent execution**: The planned TUI refactor to App Server enables remote machine execution (agent close to compute, client displays locally) -- same pattern applicable to Claude Code remote development scenarios

---

## References

- [Unlocking the Codex harness: how we built the App Server](https://openai.com/index/unlocking-the-codex-harness/) (accessed 2026-02-21)
- [openai/codex GitHub repository](https://github.com/openai/codex) (accessed 2026-02-21)
- [Codex CLI README](https://github.com/openai/codex/blob/main/README.md) (accessed 2026-02-21)
- [Codex app-server-protocol source](https://github.com/openai/codex/tree/main/codex-rs/app-server-protocol) (accessed 2026-02-21)
- [Codex app-server source](https://github.com/openai/codex/tree/main/codex-rs/app-server) (accessed 2026-02-21)
- [Harness engineering: leveraging Codex in an agent-first world (companion post)](https://openai.com/index/harness-engineering-leveraging-codex-in-an-agent-first-world/) (accessed 2026-02-21)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [meta-harness](../ai-research-tools/meta-harness.md) | ai-research-tools | referenced by meta-harness (ai-research-tools) |
| [agent-skills-eval](./agent-skills-eval.md) | evaluation-testing | referenced by agent-skills-eval (evaluation-testing) |
