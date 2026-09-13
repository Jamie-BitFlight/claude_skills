---
name: Vibe Kanban - Orchestrate AI Coding Agents with a Kanban Board
description: Vibe Kanban is an open-source Kanban-style orchestration UI for managing multiple AI coding agents (Claude Code, Gemini CLI, Codex, Amp) in parallel, with git worktree isolation, task tracking, and integrated code review.
license: Apache-2.0
metadata:
  topic: vibe-kanban
  category: task-management
  source_url: https://vibekanban.com
  github: BloopAI/vibe-kanban
  version: "0.1.22"
  verified: "2026-03-03"
  next_review: "2026-06-03"
---

## Overview

Vibe Kanban is an open-source, Kanban-style orchestration tool designed to help engineers plan, delegate, and review work across multiple AI coding agents simultaneously. It provides a unified dashboard for spawning and monitoring agents like Claude Code, Gemini CLI, OpenAI Codex, and Amp, with each task running in an isolated git worktree to prevent conflicts. The primary value proposition is shifting the human engineer's role from manual coding to high-level orchestration — reviewing and merging agent-produced code rather than writing it line by line.

**Core Value Proposition**: Give individual developers (and teams) a 10× productivity boost by allowing them to run many AI coding agent sessions in parallel, with a visual Kanban interface to track progress, review diffs, and iterate on results.

---

## Problem Addressed

| Problem                                                                        | How Vibe Kanban Solves It                                                                       |
| ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| Running multiple AI agents requires constant terminal context-switching        | Single Kanban UI shows all agent sessions with live status (Running, Needs Attention, Idle)     |
| Parallel agent sessions conflict on the same working directory                 | Each task runs in an isolated git worktree so branches never step on each other                 |
| Reviewing AI-generated code requires manual git diff workflows                 | Integrated diff viewer and one-click merge/discard inside the UI                                |
| Configuring MCP servers differs per agent CLI                                  | Centralised MCP config management that distributes to all supported coding agents               |
| Remote servers require SSH tunnelling to access an IDE on the local machine    | Remote SSH editor-open integration with VS Code Remote-SSH and tunnel support (Cloudflare, etc) |
| No visibility into which agent tasks need human intervention                   | Accordion task list sorted by status — "Needs Attention" surfaced before "Running" and "Idle"   |

---

## Key Statistics (as of March 3, 2026)

| Metric          | Value      |
| --------------- | ---------- |
| GitHub Stars    | ~22,000    |
| Forks           | ~2,100     |
| Contributors    | 38+        |
| Commits         | 1,871+     |
| Open Issues     | ~181       |
| Latest Release  | v0.1.22    |
| npm Package     | vibe-kanban |
| License         | Apache-2.0 |

---

## Key Features

### Multi-Agent Orchestration

- Run Claude Code, Gemini CLI, OpenAI Codex, Amp, and other coding agents side-by-side
- Spawn sequential or parallel agent sessions from a single project board
- Live streaming status updates per task (running, needs attention, idle, complete)

### Git Worktree Isolation

- Each task automatically creates and manages a dedicated git worktree
- Agent sessions work on isolated branches — no merge conflicts between concurrent tasks
- Automatic worktree cleanup with configurable `DISABLE_WORKTREE_CLEANUP` override for debugging

### Integrated Code Review

- View diffs, accept or discard changes, and merge branches without leaving the UI
- Side-by-side file diff viewer scoped to each agent task
- Streamable historical log output for replay and debugging

### Centralised MCP Configuration

- Manage MCP server configs for all supported agents from one settings page
- Avoid duplicating per-agent JSON config files across multiple CLI tools

### Remote SSH Deployment

- Run Vibe Kanban on a remote server, expose via Cloudflare Tunnel / ngrok
- "Open in VSCode" buttons generate `vscode://vscode-remote/ssh-remote+…` URLs for seamless local editor access
- Relay tunnel mode for cloud-hosted instances (`VK_TUNNEL`, `VK_SHARED_RELAY_API_BASE`)

### Self-Hosting / Cloud

- Docker-ready with `.dockerignore` and environment variable configuration
- Reverse-proxy support via `VK_ALLOWED_ORIGINS` to whitelist custom domains
- Relay API architecture allows multi-user cloud deployments

---

## Technical Architecture

Vibe Kanban uses a Rust + TypeScript monorepo:

```text
vibe-kanban/
├── crates/
│   ├── server/          # Axum HTTP API + binaries
│   ├── db/              # SQLx models & migrations (SQLite)
│   ├── executors/       # Per-agent execution adapters
│   ├── services/        # Business logic
│   ├── git/             # Git worktree lifecycle management
│   ├── api-types/       # Shared Rust types (TS bindings generated via ts-rs)
│   └── review/          # PR review tooling
├── packages/
│   ├── local-web/       # Vite + React + Tailwind (local desktop frontend)
│   ├── remote-web/      # Remote deployment frontend
│   └── web-core/        # Shared React component library
├── shared/              # Generated TypeScript types (do not edit directly)
└── npx-cli/             # npm CLI package entrypoint
```

**Key design decisions**:

- **ts-rs** generates TypeScript types from Rust structs, ensuring type safety across the stack
- **SQLite** for local state persistence; Postgres for remote/cloud deployments
- **SSE (Server-Sent Events)** for streaming agent log output to the browser
- Separate `local-deployment` and `remote` Rust crates to handle different hosting modes

---

## Installation & Usage

```bash
# Quickstart (no install required)
npx vibe-kanban

# Or install globally
npm install -g vibe-kanban
vibe-kanban
```

```bash
# Self-hosted with custom domain
VK_ALLOWED_ORIGINS=https://vk.example.com vibe-kanban

# Remote server with relay tunnel
VK_TUNNEL=1 VK_SHARED_RELAY_API_BASE=https://relay.example.com vibe-kanban
```

**Development setup**:

```bash
pnpm i
pnpm run dev        # Start Rust backend + Vite frontend
cargo test --workspace
pnpm run lint       # ESLint + cargo clippy
pnpm run format     # Prettier + cargo fmt
```

---

## Relevance to Claude Code Development

### Applications

- Directly applicable as a workflow layer on top of Claude Code CLI sessions — creates the planning/review loop that Claude Code alone lacks
- The git worktree isolation pattern could be adopted in Claude Code plugin design to prevent multi-session conflicts
- Status accordion UI (Running → Needs Attention → Idle) is a useful mental model for surfacing agent tasks that require human input

### Patterns Worth Adopting

- **Worktree-per-task isolation**: Each Claude Code task in its own git worktree prevents cross-session file conflicts
- **SSE streaming logs**: Streaming agent output as Server-Sent Events is a lightweight, browser-native pattern for real-time log delivery
- **ts-rs type sharing**: Deriving TypeScript types from Rust structs is a clean approach for any Rust + TypeScript project needing shared API types
- **Status grouping by urgency**: Sorting by "Needs Attention" before "Running" and "Idle" is a sensible default for reducing human cognitive load

### Integration Opportunities

- Vibe Kanban's MCP config centralisation could be surfaced as a Claude Code plugin that writes to multiple agent config files from a single source of truth
- The task board model aligns with Claude Code's backlog/task system — a bridge plugin could sync vibe-kanban tasks with `.claude/backlog/` entries
- The SSH remote editor integration pattern is reusable for any Claude Code skill that needs to open files in a local editor from a remote session

---

## References

- [GitHub Repository](https://github.com/BloopAI/vibe-kanban) (accessed 2026-03-03)
- [Official Website & Docs](https://vibekanban.com) (accessed 2026-03-03)
- [npm Package](https://www.npmjs.com/package/vibe-kanban) (accessed 2026-03-03)
- [DeepWiki Architecture Overview](https://deepwiki.com/BloopAI/vibe-kanban) (accessed 2026-03-03)
- [VirtusLab Blog — vibe-kanban: a Kanban board for AI agents](https://virtuslab.com/blog/ai/vibe-kanban/) (accessed 2026-03-03)
- [Video Overview](https://youtu.be/TFT3KnZOOAk) (accessed 2026-03-03)

---

## Freshness Tracking

| Field                    | Value      |
| ------------------------ | ---------- |
| Last Verified            | 2026-03-03 |
| Version at Verification  | v0.1.22    |
| Next Review Recommended  | 2026-06-03 |

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [the-delegation](../research-agent-patterns/the-delegation.md) | research-agent-patterns | referenced by the-delegation (research-agent-patterns) |
| [xyops](./xyops.md) | task-management | referenced by xyops (task-management) |
