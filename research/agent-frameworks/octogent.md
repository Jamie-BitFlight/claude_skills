---
title: Octogent
subtitle: Web dashboard for orchestrating parallel Claude Code agent sessions
category: agent-frameworks
resource_url: https://github.com/hesamsheikh/octogent
github_url: https://github.com/hesamsheikh/octogent
date_created: "2026-05-10"
date_last_reviewed: "2026-05-10"
status: published
---

# Octogent

## Overview

Octogent is a web-first orchestration dashboard for managing multiple Claude Code agent sessions in parallel on a single codebase. The project provides a unified interface for coordinating coding agents, tracking task context, and delegating work across multiple scoped jobs ("tentacles"), preventing the cognitive overhead of switching between dozens of independent terminal sessions.

**Tagline**: "too many terminals, not enough tentacles"

## Problem Addressed

Developers working with Claude Code often need to run multiple coding agents simultaneously—one for documentation, another for database work, another for API changes, and another for frontend work. This creates context fragmentation: each terminal session maintains its own chat history, and switching between them requires manually reconstructing what each agent was supposed to be doing.

Octogent addresses this by:

- Creating **tentacles** as scoped context layers, so agents work with durable markdown files (`CONTEXT.md`, `todo.md`, notes) instead of reconstructing context from chat history
- Using `todo.md` as an execution surface so tasks stay visible, trackable, and ready for delegation
- Enabling one Claude Code agent to coordinate other Claude Code agents, assign them specific jobs, and exchange messages while the developer stays at the orchestration layer
- Treating terminal coding agents as building blocks inside an orchestration layer, not as standalone applications

## Key Statistics

- **Version**: 0.1.0 (pre-release, released 2026-04-20)
- **Stars**: 921 (as of 2026-05-10)
- **Forks**: 139 (as of 2026-05-10)
- **Contributors**: 1 (as of 2026-05-10)
- **License**: MIT
- **Repository**: <https://github.com/hesamsheikh/octogent>
- **Language**: TypeScript 5.8
- **Runtime**: Node.js 22+
- **Package Manager**: pnpm 10.4.1

## Key Features

### Tentacle Model

A **tentacle** is a folder (`.octogent/tentacles/<tentacle-id>/`) containing agent-readable markdown files. Each tentacle represents one scoped job or area of work (API runtime, frontend shell, prompt system, etc.). Minimum files: `CONTEXT.md` and `todo.md`.

**Extracted behavior**: "A tentacle is a folder under `.octogent/tentacles/<tentacle-id>/` that stores agent-readable markdown files. The important part is that the folder is agent-facing. It is the durable context that a terminal agent can read, edit, and hand off to another terminal." (tentacles.md)

### Todo-Driven Delegation

`todo.md` contains markdown checkbox items. The runtime parses these items and generates worker prompts from them. Incomplete items automatically become worker assignments in swarm runs, and terminal IDs like `<tentacle-id>-swarm-0` are derived from parsed item indices.

### Multi-Agent Orchestration

Claude Code can spawn other Claude Code agent sessions, assign them work from todo items, and coordinate their execution. Workers report status through short in-memory channel messages and durable notes in tentacle files. A parent agent can supervise multiple workers simultaneously.

### Workspace Isolation Options

Terminals can operate in two modes:
- **Shared mode**: Multiple terminals in the main workspace, with context boundaries being procedural
- **Worktree mode**: Each terminal gets its own git checkout under `.octogent/worktrees/<worktree-id>` on branch `octogent/<worktree-id>`, with isolated code changes but shared tentacle context

### Web UI (Deck)

Octogent provides a local web interface called "Deck and Canvas" that:
- Displays tentacles by reading `.octogent/tentacles/` directly (no separate database)
- Parses the first heading and paragraph from `CONTEXT.md` as display name and description
- Renders checkbox lines from `todo.md` as progress indicators and worker assignment inputs
- Shows terminal lifecycle state, working status, and transcript output
- Supports creating new tentacles, editing todos, and managing terminal sessions

### Local API and WebSocket Transport

- **HTTP routes**: CRUD operations, snapshots, prompt resolution, setup checks, file-backed operations
- **WebSocket `/api/terminals/:terminalId/ws`**: Attaches a browser terminal to a PTY session for streaming IO
- **WebSocket `/api/terminal-events/ws`**: Broadcasts terminal-created, terminal-updated, terminal-deleted, and state-change events
- **File-backed state**: Terminal records, UI state, transcripts, Deck metadata, and monitor/cache data survive API restarts

## Technical Architecture

Octogent is a TypeScript monorepo with three core packages:

### Domain Layer (`packages/core`)

- Framework-agnostic domain types and application logic (ports-and-adapters pattern)
- Does not depend on React, HTTP, PTY, or filesystem orchestration
- Pure business logic: terminal registry, tentacle parsing, todo item parsing, prompt resolution

### API Application (`apps/api`)

- Node.js HTTP/WebSocket server using native Node primitives
- **PTY Session Runtime**: spawns PTY sessions through `node-pty`, manages lifecycle, maintains scrollback
- **Terminal Registry**: tracks terminal identity, lifecycle state, workspace mode, and worktree associations
- **Hook Integration**: injects Claude hooks into `.claude/settings.json` to receive state transitions (agent activity, tool use, idle waits, stops)
- **Transcript Persistence**: captures agent conversations to `.octogent/projects/<project-id>/state/transcripts/*.jsonl`
- **Worktree Lifecycle**: creates and cleans up git worktrees for isolated terminals
- **Channel Queue**: in-memory inter-agent messaging system that injects messages when targets become idle

### Web Application (`apps/web`)

- Vite + React single-page application (SPA)
- **Tentacle Pod UI**: renders tentacles with context, todos, and vault files
- **Terminal Wheel**: circular UI for managing many terminals at once
- **Canvas Terminal Panel**: dedicated terminal session display with scrollback
- **Swarm Coordinator**: UI for spawning and monitoring multi-agent swarms
- Modular CSS architecture, UI orchestration over HTTP/WebSocket contracts

### Data Model

- **Tentacle Files** (`.octogent/tentacles/<id>/`): agent-readable markdown—`CONTEXT.md`, `todo.md`, and additional vault files
- **Runtime State** (`~/.octogent/projects/<project-id>/state/`): terminal records (`tentacles.json`), transcripts, Deck metadata, monitor cache
- **Worktrees** (`.octogent/worktrees/<id>/`): isolated git checkouts for worktree-backed terminals
- **Project Scaffold** (`.octogent/`): assigned stable project ID, API port assignment, configured agent bootstrap

## Installation & Usage

### Install from Local Clone

```bash
pnpm install
pnpm build
npm install -g .
octogent
```

### Start Locally (Development)

```bash
pnpm install
pnpm dev
```

This starts both the API and web app for development.

### Initialize a Project

```bash
octogent init [project-name]
```

Creates the `.octogent/` scaffold in the current directory without starting the dashboard.

### Start the Dashboard

```bash
octogent
```

Starts the local API and opens the UI (unless `OCTOGENT_NO_OPEN=1` is set). On first run, automatically creates the `.octogent/` scaffold, assigns a stable project ID, picks an available local API port starting at `8787`.

### CLI Commands

**Tentacles**:
```bash
octogent tentacle create <name> --description "API runtime and routes"
octogent tentacle list
```

**Terminals**:
```bash
octogent terminal create --name "API runtime" --tentacle-id api-runtime
octogent terminal list
octogent terminal stop <terminal-id>
octogent terminal kill <terminal-id>
octogent terminal prune
```

**Inter-Agent Messaging**:
```bash
octogent channel send <terminal-id> "message"
octogent channel list <terminal-id>
```

## Relevance to Claude Code Development

Octogent is directly relevant to Claude Code development workflows in several ways:

1. **Multi-Agent Coordination**: Demonstrates how Claude Code agents can be treated as orchestrable building blocks, spawning and managing child agents instead of operating as isolated sessions.

2. **Context Management**: Solves the context fragmentation problem by using durable, agent-readable markdown files as the source of truth instead of chat history, enabling agents to hand off work reliably.

3. **Delegation Patterns**: Provides a concrete implementation of parent-worker orchestration through todo-driven task assignment, worktree isolation, and inter-agent messaging.

4. **Local Development Infrastructure**: Shows how to implement a local orchestration API with WebSocket transport, PTY lifecycle management, and hook-based state integration.

5. **Testing Multi-Agent Workflows**: Useful for developing and testing features that involve multiple Claude Code sessions coordinating on shared codebases.

## Limitations and Caveats

- **Not Published to npm**: "Octogent is not published to the npm registry yet." Local development and global CLI installation require building from source.

- **Pre-Release Status**: Version 0.1.0 is marked as a pre-release. The project is described as "an experimental personal project" in CONTRIBUTING.md, and pull requests are not actively reviewed.

- **Single-Contributor Project**: Currently maintained by one developer (Hesam Sheikh). No formal governance or maintenance commitments.

- **PTY Sessions Do Not Survive API Restart**: When the API process restarts, live PTY sessions are terminated. Terminal records marked as `running` are reconciled to `stale` on startup. This means long-lived orchestration workflows must be aware of restart boundaries.

- **No Persistence for Channel Messages**: Inter-agent messages are stored in memory. For durable handoffs, agents must write to tentacle markdown files instead of relying on channel message history.

- **Limited Browser Support**: Security defaults bind to `127.0.0.1` and enforce loopback `Host` and `Origin` checks. Remote access requires explicit `OCTOGENT_ALLOW_REMOTE_ACCESS=1` environment variable.

- **Maximum 32 Live Terminal Sessions**: Octogent caps live PTY sessions at 32 by default (tunable via `OCTOGENT_MAX_TERMINAL_SESSIONS`) to protect the host from resource exhaustion.

- **Requires External Tools**: Depends on `claude` CLI, `git`, `gh`, and `curl` being available in the environment.

## References

- **Repository**: <https://github.com/hesamsheikh/octogent>
- **README**: Accessed from `.worktrees/octogent/README.md` on 2026-05-10
- **Documentation Index**: `docs/index.md` (accessed 2026-05-10)
- **Mental Model**: `docs/concepts/mental-model.md` (accessed 2026-05-10)
- **Tentacles Concept**: `docs/concepts/tentacles.md` (accessed 2026-05-10)
- **Runtime and API**: `docs/concepts/runtime-and-api.md` (accessed 2026-05-10)
- **CLI Reference**: `docs/reference/cli.md` (accessed 2026-05-10)
- **Contributing Guide**: `CONTRIBUTING.md` (accessed 2026-05-10)
- **Repository Guidelines**: `AGENTS.md` (accessed 2026-05-10)
- **package.json**: Root project manifest (accessed 2026-05-10)
- **GitHub API**: Repository metadata including stars, forks, contributors, license (accessed 2026-05-10 via `gh api repos/hesamsheikh/octogent`)

## Freshness Tracking

- **Last Reviewed**: 2026-05-10
- **Next Review**: 2026-08-10 (90 days)
- **Confidence Summary**:
  - **Identity/Metadata**: high — official package.json, GitHub API, official repository
  - **Features**: high — comprehensive documentation in `docs/`, code examples in CLI reference and guides
  - **Architecture**: high — full read of mental model, tentacles, runtime/API, and AGENTS.md
  - **Usage Examples**: high — extracted from official CLI reference and documentation guides
  - **Limitations**: high — documented in official CONTRIBUTING.md and runtime/API docs
- **Changes Detected Since Last Update**: None (initial entry)
- **Data Accuracy Notes**: All version strings, counts, and command syntax verified from primary sources. Repository is 76 days old as of assessment date. Pre-release status and single-contributor status confirmed via GitHub API and CONTRIBUTING.md.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Orchestra](./orchestra.md) | agent-frameworks | DAG-based task orchestration with worktree isolation and parallel wave execution complements tentacle-based context layering |
| [Mission Control](./mission-control.md) | agent-frameworks | Autonomous product engine combining research, ideation, and build phases shares orchestration patterns for multi-agent workflows |
| [Oh My Claude Code](../agent-orchestration/oh-my-claudecode.md) | agent-orchestration | TypeScript multi-agent orchestration with smart routing and parallelism uses similar context coordination as Octogent's tentacle model |
| [The Claw Loop](../research-agent-patterns/claw-loop.md) | research-agent-patterns | Supervisor-worker orchestration via tmux/cron demonstrates alternative polling pattern to Octogent's webhook/channel approach |
| [Gas Town](../research-agent-patterns/gastown.md) | research-agent-patterns | Multi-agent workspace manager coordinating multiple Claude Code sessions via tmux shares terminal lifecycle and context management concerns |
| [Oh My OpenCode](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | Production-scale multi-agent architecture with category-based routing extends orchestration patterns demonstrated in Octogent |
| [TAKT](../research-agent-patterns/takt.md) | research-agent-patterns | YAML-defined multi-agent workflows with state transitions and faceted prompting align with todo-driven delegation concept |
| [Plano](../agent-infrastructure/plano.md) | agent-infrastructure | AI-native orchestration proxy provides infrastructure layer that could complement Octogent's local API |
