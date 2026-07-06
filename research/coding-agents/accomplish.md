---
title: "Accomplish"
research_date: "2026-02-27"
source_url: "https://www.accomplish.ai/"
github_url: "https://github.com/accomplish-ai/accomplish"
version_at_research: "@accomplish_ai/agent-core@0.4.0 / Desktop 0.3.10"
license: "MIT License"
last_verified: "2026-02-27"
version_at_verification: "@accomplish_ai/agent-core@0.4.0 / Desktop 0.3.10"
next_review: "2026-05-27"
---

## Overview

Accomplish (formerly Openwork) is an open source AI desktop agent that automates file management, document creation, and browser tasks locally on the user's machine. It uses a bring-your-own-API-key model, supporting 15 providers including Anthropic, OpenAI, Google, xAI, and local models via Ollama and LM Studio, with no subscription fees beyond API usage costs. The agent runs on macOS (Apple Silicon and Intel) and Windows 11, communicating with AI providers while keeping all user files and data on-device.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI assistants require sharing files with cloud services | Accomplish runs locally; files never leave the machine unless the user allows it |
| Subscription-based AI tools lock users into proprietary infrastructure | MIT-licensed BYOK (bring your own key) model with support for 15 providers including local Ollama/LM Studio models |
| Autonomous agents perform irreversible actions without user visibility | Permission-gated execution: each file operation, tool use, and browser action requires explicit user approval |
| No standardized way to save and reuse multi-step AI workflows | Custom Skills system allows users to define repeatable prompt-based workflows and save them as named skills |
| Desktop automation requires complex scripting or expensive tools | Natural language task input dispatched to an AI model that executes via MCP tool calls |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 9,015 | 2026-02-27 |
| Forks | 921 | 2026-02-27 |
| Contributors | 26 | 2026-02-27 |
| Open Issues | 152 | 2026-02-27 |
| Latest Release | @accomplish_ai/agent-core@0.4.0 | 2026-02-16 |
| Desktop Build | 0.3.10 | 2026-02-27 |
| Repository Created | 2026-01-14 | 2026-02-27 |
| Primary Language | TypeScript (2,241,693 bytes) | 2026-02-27 |

SOURCE: [GitHub API — accomplish-ai/accomplish](https://api.github.com/repos/accomplish-ai/accomplish) (accessed 2026-02-27)

---

## Key Features

### Local-First Agent Execution

- All file operations, document writes, and task state stored locally in SQLite (`accomplish.db`)
- API keys encrypted at rest using AES-256-GCM via the `SecureStorage` class
- No telemetry sent to Accomplish servers; only traffic is to the user's chosen AI provider
- Folder access is permission-gated: users explicitly grant access to directories

### Multi-Provider AI Support

- 15 supported providers: Anthropic, OpenAI, Google AI, xAI, DeepSeek, Moonshot AI (Kimi), Z.AI (GLM), MiniMax, Amazon Bedrock, Azure Foundry, OpenRouter, LiteLLM, Ollama, LM Studio, and custom endpoints
- Provider configs managed via `packages/agent-core/src/providers/` with per-provider API key validation
- Supports OpenAI-compatible base URL overrides for custom deployments
- Local model support via Ollama and LM Studio requires no API key

### MCP-Based Tool Architecture

- Agent capabilities implemented as standalone MCP (Model Context Protocol) tools under `packages/agent-core/mcp-tools/`
- Built-in tools: `ask-user-question`, `complete-task`, `start-task`, `dev-browser`, `file-permission`, `safe-file-deletion`, `report-checkpoint`, `report-thought`
- Each tool is a self-contained package directory with its own `package.json`
- Browser automation via Playwright integration (`dev-browser-mcp`)

### Task and Skills Management

- `TaskManager` class handles concurrent task management and queuing
- `CompletionEnforcer` enforces task completion discipline, preventing runaway agent loops
- `needs_planning` classification in `start_task` tool: skips plan card emission and todo creation for simple conversational turns
- Custom Skills stored in SQLite `skills` table, managed by `SkillsManager` class

### Electron Desktop Shell

- Thin Electron shell (`apps/desktop`) loads the React UI built by `apps/web`
- Main process spawns [OpenCode](https://github.com/sst/opencode) CLI via `node-pty` (PTY-based spawning in `OpenCodeAdapter`)
- Three HTTP servers bridge IPC: permission requests (ports 9226, 9227), thought/checkpoint streaming (port 9228)
- Task progress streamed via `StreamParser` that parses JSON messages from OpenCode CLI stdout
- Bundled Node.js v20.18.1 included in packaged app so MCP servers work without system Node.js

### User Approval Workflow

- Every agent action (file write, browser navigation, tool call) surfaces a permission request to the renderer
- `PermissionRequestHandler` manages the approval/denial lifecycle
- Users can stop tasks at any time; task logs are persisted for audit
- Todo lists generated from task planning steps and updated as agent progresses

---

## Technical Architecture

Accomplish uses a monorepo with two apps and one shared package:

```text
apps/
  desktop/     -- Electron app (main process + preload + renderer)
packages/
  agent-core/  -- Core business logic, types, storage, MCP tools (ESM, @accomplish_ai/agent-core)
```

The data flow from user input to agent action:

```text
Renderer (React + Zustand)
    ↓ window.accomplish.* calls
Preload (contextBridge API)
    ↓ ipcRenderer.invoke
Main Process (handlers.ts)
    ↓ OpenCodeAdapter (node-pty)
OpenCode CLI (spawned subprocess)
    ↑ JSON message stream on stdout
StreamParser
    ↑ IPC events: task:update, permission:request, todo:update
Renderer (taskStore subscriptions)
```

Agent-core internal classes follow a factory pattern. Consumers call `createTaskManager()`, `createStorage()`, etc. rather than instantiating classes directly. All internal imports use ESM `.js` extensions (the package has `"type": "module"` in `package.json`).

SQLite storage uses WAL mode with foreign keys enabled. Six versioned migrations handle schema evolution from initial schema through task todos and skills tables. A `FutureSchemaError` prevents older app versions from opening newer database files.

The `CompletionEnforcer` addresses a common agent reliability problem: it tracks whether the agent has called `complete-task` and injects continuation prompts when the agent stalls without completing. The `needs_planning` flag on `start_task` (added in v0.4.0) avoids unnecessary plan card creation for conversational turns like greetings.

SOURCE: [docs/architecture.md in accomplish-ai/accomplish](https://github.com/accomplish-ai/accomplish/blob/main/docs/architecture.md) (accessed 2026-02-27)

SOURCE: [AGENTS.md in accomplish-ai/accomplish](https://github.com/accomplish-ai/accomplish/blob/main/AGENTS.md) (accessed 2026-02-27)

---

## Installation & Usage

```bash
# Download desktop app (macOS Apple Silicon)
# https://downloads.accomplish.ai/downloads/0.3.10/macos/Accomplish-0.3.10-mac-arm64.dmg

# Development setup
pnpm install
pnpm dev
```

```bash
# Build commands
pnpm build           # Build all workspaces
pnpm build:desktop   # Build desktop app only
pnpm lint            # TypeScript + ESLint checks
pnpm typecheck       # Type validation

# Run workspace-scoped tests
pnpm -F @accomplish/web test
pnpm -F @accomplish/desktop test
pnpm -F @accomplish_ai/agent-core test
pnpm -F @accomplish/desktop test:e2e   # Playwright E2E (Docker or native)
```

```typescript
// agent-core public API (factory pattern, ESM)
import { createTaskManager, createStorage } from '@accomplish_ai/agent-core';

const storage = createStorage();
const taskManager = createTaskManager({ storage });

// Start a task
const task = await taskManager.startAgent({
  prompt: 'Organize the Downloads folder by file type',
  provider: 'anthropic',
});
```

---

## Relevance to Claude Code Development

### Applications

- Accomplish is a working example of a desktop agent built on top of Claude (Anthropic provider supported), running via the same `start_task` / `complete_task` MCP tool discipline that Claude Code uses
- The `needs_planning` classification in `start_task` is directly relevant: it prevents unnecessary planning overhead for simple queries, a pattern applicable to Claude Code skill invocation
- The `CompletionEnforcer` pattern addresses agent reliability in long-running tasks — applicable to any agentic workflow that must not stall without producing output

### Patterns Worth Adopting

- **Factory pattern for agent-core classes**: `createTaskManager()` over `new TaskManager()` — decouples consumers from implementation, enables mocking in tests
- **Permission-gated tool execution**: Each MCP tool call surfaces a user-visible approval before execution — applicable to Claude Code sub-agent delegation where irreversible actions need review
- **Completion enforcement discipline**: Injecting continuation prompts when an agent stalls without calling a terminal tool prevents infinite loops in autonomous workflows
- **SQLite with versioned migrations**: Structured migration runner with `FutureSchemaError` rollback protection is a clean pattern for any tool that persists agent state locally
- **Bundled Node.js for hermetic packaging**: Ensures MCP tools work without system-level Node.js — relevant for distributing Claude Code plugins that depend on Node-based MCP servers

### Integration Opportunities

- Accomplish's MCP tool set (`ask-user-question`, `file-permission`, `safe-file-deletion`) could be adapted as reusable MCP servers for Claude Code workflows that require user approval before file system operations
- The `ThoughtStreamHandler` pattern (streaming agent reasoning to a UI via HTTP on port 9228) is a reference implementation for exposing agent thought processes to external tooling
- The `SkillsManager` concept (named, reusable prompt templates stored in SQLite) maps closely to Claude Code's skill system — the storage layer implementation is worth reviewing for the skills persistence approach

---

## References

- [Accomplish GitHub Repository](https://github.com/accomplish-ai/accomplish) (accessed 2026-02-27)
- [Accomplish Website](https://www.accomplish.ai/) (accessed 2026-02-27)
- [Architecture Documentation — docs/architecture.md](https://github.com/accomplish-ai/accomplish/blob/main/docs/architecture.md) (accessed 2026-02-27)
- [AGENTS.md — Project conventions and commands](https://github.com/accomplish-ai/accomplish/blob/main/AGENTS.md) (accessed 2026-02-27)
- [GitHub API — Repository metadata](https://api.github.com/repos/accomplish-ai/accomplish) (accessed 2026-02-27)
- [GitHub API — Latest release @accomplish_ai/agent-core@0.4.0](https://api.github.com/repos/accomplish-ai/accomplish/releases/latest) (accessed 2026-02-27)
- [OpenCode CLI — upstream dependency](https://github.com/sst/opencode) (accessed 2026-02-27)

---
