---
title: Cursor Cookbook
subtitle: 5 production-ready Cursor SDK examples for AI coding agent integration
category: agent-frameworks
resource_url: https://github.com/cursor/cookbook
github_url: https://github.com/cursor/cookbook
date_created: "2026-05-05"
date_last_reviewed: "2026-05-05"
status: published
---

# Cursor Cookbook

**Research Date**: 2026-05-05
**Source URL**: <https://github.com/cursor/cookbook>
**GitHub Repository**: <https://github.com/cursor/cookbook>
**Version at Research**: No versioned releases (development repository)
**License**: Not specified in repository metadata

---

## Overview

The Cursor Cookbook is a collection of production-ready examples demonstrating how to build applications using the Cursor SDK — a TypeScript API for integrating Cursor's AI-powered coding agent into custom applications, scripts, and workflows. The repository provides practical implementations spanning local agent execution, cloud-based agent management, task decomposition with DAGs, and interactive development environments.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Developers need concrete examples for integrating AI coding agents into their own applications | Provides 5 fully functional examples (Quickstart, Kanban Board, Coding Agent CLI, DAG Task Runner, App Builder) demonstrating progressively complex use cases |
| Complex tasks require decomposition into subtasks with dependency management | DAG Task Runner implements topological sorting (Kahn's algorithm) for parallel execution of independent tasks across multiple subagents |
| Understanding how to stream agent output and manage conversation state | Multiple examples demonstrate real-time streaming patterns, artifact handling, and session management |
| Managing multiple agents in a cloud environment with visual organization | Agent Kanban provides a Linear-inspired dashboard for filtering, creating, and previewing cloud agents |
| Building interactive development tools with live code preview | App Builder demonstrates end-to-end app scaffolding with hot-reloading React preview and streamed agent responses |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 3,407 | 2026-05-05 |
| GitHub Forks | 392 | 2026-05-05 |
| Open Issues | 21 | 2026-05-05 |
| Primary Language | TypeScript | 2026-05-05 |
| Contributors | 1+ | 2026-05-05 |
| Repository Created | 2026-04-27 | 2026-05-05 |
| Last Pushed | 2026-05-05T00:54:15Z | 2026-05-05 |

---

## Key Features

### Quickstart Example

- Minimal Node.js implementation demonstrating foundational Cursor SDK functionality
- Creates single agent instance, sends hard-coded prompt, streams assistant text to stdout
- Requires Node.js 22+, demonstrates environment configuration and dependency management with pnpm
- Serves as entry point for understanding basic agent creation and prompt handling

### Coding Agent CLI

- Terminal-based tool for spawning agents from command line against workspace
- Supports one-shot execution mode for immediate tasks and interactive TUI mode for dynamic work
- Provides in-terminal model selection and execution environment switching (local vs. cloud)
- TUI menu system (accessed via `/`) allows runtime configuration changes and session reset
- Requires Bun 1.3+ due to OpenTUI native rendering via Bun FFI interface

### Agent Kanban Dashboard

- Linear-inspired board interface for managing Cursor Cloud Agents
- Organizational filtering by status, repository, branch, or created date
- Agent cards display status, repo/branch metadata, latest activity, PR link, and artifact previews
- Artifact previews proxied through local API routes for authenticated media access
- Built with Next.js, API key authentication required before loading cloud agent data
- Supports creating new cloud agents through `Agent.create()` method with repository configurations
- Implements rate-limit management with in-memory caching of repository listings

### DAG Task Runner

- Decomposes complex projects into JSON-based directed acyclic graphs (DAGs) with explicit dependency declarations
- Supports task-level complexity assignment (HIGH/MED/LOW) mapped to specific AI models
- Implements topological sorting using Kahn's algorithm for parallel execution of independent tasks
- Automatically stitches upstream output into child task prompts (2,000-char snippet of parent results)
- Streams real-time progress to Cursor Canvas with hot-reloading, displaying task state transitions (PENDING → RUNNING → FINISHED/ERROR)
- Token-by-token output streaming to canvas during execution
- Includes timeout protection, automatic downstream task skipping on parent failure, graceful signal handling
- Supports per-task model overrides and configuration file customization for working directories, timeouts, and streaming intervals

### App Builder (Prototyping Tool)

- End-to-end app-building loop demonstrating interactive development with AI agents
- Accepts Cursor API key, stores credentials locally for agent sessions
- Creates isolated workspace with hot-reloading React preview in iframe
- Streams agent responses and tool activity through chat interface
- Supports multiple concurrent app-building conversations
- Demonstrates live preview of generated user interfaces with real-time feedback
- Intended as local development demo; warns against public deployment without authentication infrastructure

---

## Technical Architecture

The Cursor Cookbook implements the Cursor SDK across five architectural patterns:

**1. Simple Local Agent Pattern (Quickstart)**
- Minimal initialization of `Agent` instance
- Single-turn prompt submission with streaming output
- Demonstrates environment-based API key configuration

**2. CLI-Based Interactive Pattern (Coding Agent CLI)**
- Terminal UI layer (OpenTUI) managing user input and state transitions
- Runtime environment selection (local agent vs. cloud-based)
- Model selection and session lifecycle management
- Bun FFI integration for native terminal rendering

**3. Cloud Agent Management Pattern (Kanban Board)**
- REST API authentication flow for Cursor Cloud Agents
- In-memory caching of repository metadata to manage rate limits
- Media proxying through local routes for artifact preview authentication
- Next.js as the host application framework

**4. Task Decomposition Pattern (DAG Task Runner)**
- JSON DAG structure with explicit dependency declarations
- Kahn's algorithm implementation for topological sorting and parallel execution
- Parent result injection (2,000-char snippets) into child task prompts
- Canvas streaming integration with real-time state visualization
- Error propagation with automatic downstream task skipping

**5. Interactive Development Pattern (App Builder)**
- Multi-turn conversation management with persistent agent sessions
- React component rendering in isolated iframe
- Hot-reloading preview refresh on state changes
- Streamed agent output with intermediate artifact handling

All patterns leverage the Cursor SDK's core capabilities:
- Real-time streaming of agent activity during execution
- Code-level management of prompts, models, task cancellation, and artifacts
- Support for both local (workspace) and cloud-based agent execution
- Conversation state persistence across multiple turns

---

## Installation & Usage

### Quickstart

```bash
cd sdk/quickstart
npm install
export CURSOR_API_KEY="your-api-key"
npm run dev
```

Basic agent creation and streaming:

```typescript
import Cursor from '@cursor/sdk';

const agent = new Cursor.Agent();
const response = await agent.run('Your prompt here');
response.on('stream', (text) => process.stdout.write(text));
```

### Coding Agent CLI

```bash
cd sdk/coding-agent-cli
bun install
bun run dev  # Interactive mode
bun run dev -- "your prompt"  # One-shot mode
```

Features accessible via `/` command in interactive mode: model selection, environment switching, session reset.

### Agent Kanban

```bash
cd sdk/agent-kanban
npm install
npm run dev
# Navigate to http://localhost:3000
# Enter API key via dashboard UI
```

Filtering options: status, repository, branch, created date.

### DAG Task Runner

```bash
cd sdk/dag-task-runner
npm install
export CURSOR_API_KEY="your-api-key"

# Run with default configuration
node run.js

# Override model for complexity level
node run.js --model-high claude-opus-4

# View DAG in verbose mode
node run.js --verbose
```

DAG JSON format:

```json
{
  "tasks": [
    {
      "id": "task-1",
      "prompt": "Describe the project structure",
      "complexity": "HIGH",
      "dependencies": []
    },
    {
      "id": "task-2",
      "prompt": "Analyze architecture",
      "complexity": "MED",
      "dependencies": ["task-1"]
    }
  ]
}
```

### App Builder

```bash
cd sdk/app-builder
npm install
npm run dev
# Navigate to http://localhost:3000
# Enter API key to start building
```

Note: This example is for local development only. Public deployment requires authentication infrastructure and per-user storage.

---

## Relevance to Claude Code Development

### Applications

- **Multi-Agent Orchestration Patterns**: The DAG Task Runner demonstrates production-grade task decomposition and parallel execution patterns applicable to Claude Code's multi-agent scenarios
- **Streaming and Canvas Integration**: All examples showcase real-time streaming of agent output and Cursor Canvas updates, relevant to live progress visualization in Claude Code workflows
- **Interactive Development Loops**: The App Builder and Coding Agent CLI patterns demonstrate effective UX for interactive agent-driven development
- **Artifact Management**: The Agent Kanban's artifact preview and media proxying patterns show how to handle generated code/artifacts securely

### Patterns Worth Adopting

1. **DAG-based Task Decomposition**: Explicit dependency declaration with topological sorting enables optimal parallel execution — applicable to Claude Code's task planning and execution phases
2. **Parent Result Injection**: Stitching upstream output (2,000-char snippets) into child prompts provides context without full re-description — reduces token overhead in multi-turn scenarios
3. **Streaming to Canvas**: Real-time visualization of task progression (PENDING → RUNNING → FINISHED) with token-by-token output creates better UX for long-running operations
4. **CLI Model Selection**: Runtime model selection via TUI commands provides flexibility for cost-performance trade-offs within interactive sessions
5. **Error Propagation**: Automatic downstream task skipping on parent failure prevents cascading failures and wasted computation

### Integration Opportunities

- **Task Planning Integration**: Export Claude Code's feature plans as DAG JSON and execute via DAG Task Runner pattern
- **Artifact Preview**: Integrate Kanban board artifact preview patterns for displaying generated code in Claude Code workflows
- **Interactive Agent Mode**: Adopt Coding Agent CLI's interactive TUI pattern for extended Claude Code agent sessions
- **Streaming Output Display**: Apply streaming-to-canvas patterns to real-time display of agent analysis, code generation, and test output
- **Multi-Workspace Support**: Extend Agent Kanban patterns to manage Claude Code agents across multiple repositories/workspaces

---

## References

- [Cursor Cookbook GitHub Repository](https://github.com/cursor/cookbook) (accessed 2026-05-05)
- [Cursor Cookbook Quickstart Example](https://raw.githubusercontent.com/cursor/cookbook/main/sdk/quickstart/README.md) (accessed 2026-05-05)
- [Cursor Cookbook DAG Task Runner](https://raw.githubusercontent.com/cursor/cookbook/main/sdk/dag-task-runner/README.md) (accessed 2026-05-05)
- [Cursor Cookbook Agent Kanban](https://raw.githubusercontent.com/cursor/cookbook/main/sdk/agent-kanban/README.md) (accessed 2026-05-05)
- [Cursor Cookbook Coding Agent CLI](https://raw.githubusercontent.com/cursor/cookbook/main/sdk/coding-agent-cli/README.md) (accessed 2026-05-05)
- [Cursor Cookbook App Builder](https://raw.githubusercontent.com/cursor/cookbook/main/sdk/app-builder/README.md) (accessed 2026-05-05)
- GitHub API Repository Metadata (accessed 2026-05-05)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Orchestra](./orchestra.md) | agent-frameworks | shares DAG task decomposition with Kahn's algorithm, parallel sub-agent execution, and context curation patterns |
| [Tersa](./tersa.md) | agent-frameworks | visual workflow canvas for multi-LLM pipelines; complements Cookbook's programmatic DAG approach with drag-drop UI |
| [CopilotKit](./copilotkit.md) | agent-frameworks | bi-directional state sync and streaming patterns for agent-driven UI; applicable to App Builder's interactive architecture |
| [Pi Monorepo](./pi-mono.md) | agent-frameworks | TypeScript agent runtime with unified LLM API and CLI framework; shares multi-interface patterns (TUI, web, Slack) with Cookbook examples |
| [Browser Harness JS](./browser-harness-js.md) | agent-frameworks | provides full Chrome DevTools Protocol surface for agent interaction; complements Cookbook's CDP method for browser automation workflows |
| [Get Shit Done](./get-shit-done.md) | agent-frameworks | multi-agent orchestration with context engineering and execution planning; provides meta-prompting patterns for Cookbook's subagent dispatch |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-05-05 |
| Version at Verification | development (no releases) |
| Next Review Recommended | 2026-08-05 |
| Confidence Map | `Overview: high (doc-read)`, `Key Features: high (doc-read)`, `Architecture: high (doc-read)`, `Installation & Usage: high (doc-read)`, `Statistics: high (API-sourced)`, `Relevance Assessment: medium (inferred from pattern analysis)` |

