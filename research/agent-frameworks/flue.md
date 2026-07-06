---
title: "Flue — The Agent Harness Framework"
tags: ["agent-frameworks", "typescript", "ai-agents", "autonomous-agents", "workflow-orchestration", "multimodal", "deployment"]
category: agent-frameworks
source: "https://github.com/withastro/flue"
status: active
research_date: "2026-07-03"
source_url: "https://github.com/withastro/flue"
version_at_research: "1.0.0-beta.9"
license: "Apache-2.0"
last_verified: "2026-07-03"
version_at_verification: "1.0.0-beta.9"
next_review: "2026-10-03"
---

# Flue — The Agent Harness Framework

## Overview

Flue is a comprehensive TypeScript harness framework for building autonomous agents and AI workflows. Unlike traditional LLM SDKs, Flue provides a complete execution environment that gives agents the context, tools, and security they need to complete real-world tasks autonomously.

**Key positioning quote**: "Flue unlocks this new architecture for agents. Its built-in TypeScript harness gives any model the context and environment it needs for truly autonomous work: sessions, tools, skills, instructions, filesystem access, and a secure sandbox to run in. Run your agents locally via CLI or deploy them to your hosted runtime of choice."

## Problem Addressed

Traditional agent implementations relied on raw LLM API calls. This approach worked for simple chatbots and scripted tasks but was insufficient for autonomous agents. Flue addresses this gap by providing:

1. **Autonomous control flow** — Agents receive a task (not pre-defined steps) and complete it using provided context and tools
2. **Durable state management** — Agents maintain continuity across conversations and failures
3. **Secure execution** — Built-in sandboxes allow agents to safely use tools and modify files
4. **Orchestration** — Support for subagent delegation and structured workflows

**Background context**: "The first agents were built with raw LLM API calls. This worked for simple chatbots and scripted tasks, but not much else. Agents like Claude Code and Codex broke the mold. These were _real agents._ Autonomous. You give them a task — not a pre-defined series of steps — and trust them to complete it using the context and tools that you provide."

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Latest Release | 1.0.0-beta.9 | 2026-07-03 |
| License | Apache License 2.0 | 2026-07-03 |
| Package Count | 23 packages (`@flue/runtime`, `@flue/cli`, `@flue/sdk`, persistence adapters, channel integrations) | 2026-07-03 |
| GitHub Stars / Forks / Contributors | not gathered — `github.com`/`api.github.com` access for this repository was not enabled for this session's network proxy (`GitHub access to this repository is not enabled for this session`) | 2026-07-03 |

## Key Features

Flue implements the following core capabilities:

### Agents
Build agents that maintain context across conversations and events while working autonomously toward goals. Agents are defined using the `defineAgent()` API that composes models, tools, skills, instructions, and a sandbox environment.

**Example agent definition**:

```typescript
import { defineAgent, type AgentRouteHandler } from '@flue/runtime';
import { local } from '@flue/runtime/node';
import triage from '../skills/triage/SKILL.md' with { type: 'skill' };
import verify from '../skills/verify/SKILL.md' with { type: 'skill' };

export const route: AgentRouteHandler = async (_c, next) => next();

export default defineAgent(() => ({
  model: 'anthropic/claude-sonnet-4-6',
  tools: [...githubTools],
  skills: [triage, verify],
  sandbox: local(),
  instructions: `Triage a bug report end-to-end...`,
}));
```

### Workflows
Run structured automations where code guides agent reasoning from input to result. "Workflows are definitions built around Actions" — every workflow requires an agent definition and accepts input/output schemas.

### Sandboxes
Agents execute in isolated environments where they can safely use tools, modify files, and complete real work. Flue provides sandbox adapters for local execution, Cloudflare Workers, and other runtimes.

### Durable Execution
Agents preserve progress through failures and restarts. "Canonical tool outcomes are now durably recorded before one atomic commit publishes a complete tool-result batch. Recovery reuses known outcomes and materializes unknown interrupted outcomes."

### Subagents
Define specialized roles for different tasks and delegate work to the right expert. When using `task()` subagent delegation, recovery resumes in-flight, model-invoked subagents in-process from their durable conversation.

### Tools
Give agents typed actions for calling APIs, querying data, and making controlled changes. "Tool definitions now use `input`, `output`, and `run`" with optional Valibot input schemas for validation.

### Skills
Package reusable expertise and workflows that agents can load whenever needed. Skills are loaded as markdown files with embedded expertise and can be packaged for distribution.

### MCP Servers
Connect agents to authenticated tools and services through the open Model Context Protocol ecosystem.

### Observability
Monitor agents and export telemetry via OpenTelemetry, Braintrust, Sentry, or custom observers. Session persistence moves to version 8 with structured child session references.

### Channels
Receive verified events from Slack, Teams, Discord, GitHub, and more. Flue validates channel event signatures and routes them to agent workflows.

## Technical Architecture

### Core Components

**Runtime** (`@flue/runtime`): The foundational package providing:
- Agent harness and execution model (`defineAgent()`)
- Session management with durable persistence
- Tool calling and result handling
- Sandbox interfaces for execution environments
- Event streaming and durable recovery

**CLI** (`@flue/cli`): Build and development tooling including:
- `flue` binary for local development and deployment
- Vite-based build graph
- Target integration (Node.js, Cloudflare, etc.)
- Agent and workflow discovery
- Configuration management

**SDK** (`@flue/sdk`): Client library for consuming deployed agents and workflows programmatically.

**Database Adapters**: Persistence for execution state:
- `@flue/postgres` — PostgreSQL persistence
- `@flue/libsql` — LibSQL/Turso
- `@flue/mongodb` — MongoDB
- `@flue/mysql` — MySQL
- `@flue/redis` — Redis caching

**Channel Adapters**: Event integration (23+ channels including Slack, Teams, Discord, GitHub, Stripe, Shopify, etc.)

**Observability**: `@flue/opentelemetry` for structured tracing and telemetry export.

### Data Flow

1. **Agent initialization** — Agent receives task/input with model, tools, skills, and instructions
2. **Conversation loop** — Agent processes context, calls tools, receives results
3. **Tool execution** — Each tool call is validated against input schema, executed, and durable-recorded
4. **Recovery** — On interruption, durable state allows resumption from last known point
5. **Output** — Structured data returned and persisted per output schema

### Key Design Decisions

- **Durable-first architecture** — All significant state is durably recorded before continuing, enabling recovery from any failure point
- **Type-safe contracts** — Tools and workflows use Valibot schemas for input/output validation
- **Sandbox isolation** — Agents execute in restricted environments with explicit capability grants
- **HTTP-native** — Agents and workflows expose HTTP endpoints; CLI invocation goes through the same HTTP layer
- **Skill packaging** — Expertise is markdown-based and composable, allowing agents to load specialized knowledge

## Installation & Usage

### From Package Manager

Flue packages are available on npm:

```bash
npm install @flue/runtime @flue/cli @flue/sdk
# or with pnpm
pnpm add @flue/runtime @flue/cli @flue/sdk
```

### Local Development

Clone the repository and build:

```bash
git clone https://github.com/withastro/flue.git
cd flue
pnpm install
pnpm run build  # in packages/runtime/
pnpm run build  # in packages/cli/
```

### Creating an Agent

1. Define an agent file (e.g., `agents/triage.ts`)
2. Export a `defineAgent()` definition with model, tools, skills, sandbox
3. Run with `flue dev` for local testing
4. Deploy to your chosen platform (Node.js, Cloudflare, GitHub Actions, etc.)

### Minimal Example

```typescript
import { defineAgent } from '@flue/runtime';
import { local } from '@flue/runtime/node';

export default defineAgent(() => ({
  model: 'anthropic/claude-opus-4',
  tools: [],
  skills: [],
  sandbox: local(),
  instructions: 'You are a helpful assistant.',
}));
```

## Deployment Options

Flue agents run on:

- **Node.js** — Standard server deployment
- **Cloudflare Workers** — Serverless edge runtime
- **GitHub Actions** — CI/CD automation
- **GitLab CI/CD** — GitLab pipeline integration
- **Daytona** — Development environment platform
- **Render** — Platform-as-a-service hosting

All deployments follow the same agent definition API; platform-specific configuration is handled by adapters.

## Relevance to Claude Code Development

Flue is directly relevant to Claude Code's agent architecture:

1. **Autonomous agent execution model** — Flue implements the same "give task, trust completion" paradigm that powers Claude Code
2. **Tool and skill composition** — Skill packaging and tool definition mechanisms align with Claude Code's skill ecosystem
3. **Durable state management** — Session persistence and recovery patterns mirror Claude Code's session continuity
4. **Sandbox execution** — Safe, isolated agent execution with explicit capability grants
5. **Multi-model support** — While Flue examples use Anthropic Claude models, the framework supports model-agnostic agent definition
6. **Observable agent behavior** — OpenTelemetry integration enables the same observability patterns needed for agent debugging and monitoring

Flue serves as a production-grade reference implementation for building autonomous agents at scale, suitable for study and potential integration patterns.

## Limitations and Caveats

### Documented Limitations

1. **API stability** — Flue is currently in `1.0.0-beta` (latest: 1.0.0-beta.9 as of 2026-06-29), with frequent breaking changes across beta releases
2. **Workflow definition requirements** — Every workflow must have an associated agent definition; workflows cannot function independently
3. **Sandbox capability grants** — Agents cannot access capabilities not explicitly granted by their sandbox adapter
4. **Session schema versioning** — Custom persistence adapters must implement schema versioning and migration logic
5. **Durable segment size limit** — Interrupted stream recovery rejects segments larger than 1.9 MB

### Undocumented Considerations

- No documented limitations on concurrent agent execution or connection pooling
- Absence of documented performance benchmarks for agent startup latency, tool-call throughput, or memory footprint
- Limited public examples of complex multi-level subagent delegation in production
- Model provider integration relies on client implementation (e.g., Anthropic SDK) rather than built-in adapters

## References

- **Official Documentation** — <https://flueframework.com/docs/> (accessed 2026-07-03)
- **GitHub Repository** — <https://github.com/withastro/flue> (accessed 2026-07-03)
- **Packages** — Published on npm under `@flue/` namespace
- **License** — Apache License 2.0
- **Latest Release** — 1.0.0-beta.9 (2026-06-29)

**Sources**:
- README.md — Project overview and feature summary (accessed 2026-07-03)
- CHANGELOG.md — Version history and API changes (1.0.0-beta.1 through unreleased) (accessed 2026-07-03)
- CONTRIBUTING.md — Development and testing guidelines (accessed 2026-07-03)
- AGENTS.md — Agent terminology, project structure, and testing conventions (accessed 2026-07-03)
- Package structure — 23 packages including runtime, CLI, SDK, observability, database adapters, and 20+ channel integrations (accessed 2026-07-03)

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [pi-mono](./pi-mono.md) | agent-frameworks | TypeScript agent runtime monorepo with unified LLM API and skill composition |
| [everything-claude-code](./everything-claude-code.md) | agent-frameworks | Comprehensive agent+skill ecosystem optimization system with 16 agents and 65+ skills |
| [openfang](./openfang.md) | agent-frameworks | Rust Agent OS with SKILL.md native support, 40 channel adapters, and WASM sandbox |
| [micro-agent](./micro-agent.md) | agent-frameworks | Lightweight ReAct agent framework with MCP multi-server support and token budgeting |
| [liteagents](./liteagents.md) | agent-frameworks | Multi-tool AI toolkit with session memory (durable state pattern) and Hot Memory pipeline |
| [claude-code-harness](./claude-code-harness.md) | agent-frameworks | Agent harness framework for Claude Code with guardrails and execution model |
| [oh-my-claudecode](../agent-orchestration/oh-my-claudecode.md) | agent-orchestration | TypeScript multi-agent orchestration with skill system and model routing |
| [mission-control](./mission-control.md) | agent-frameworks | Autonomous product engine with durable workflows and structured task execution |

---

## Freshness Tracking

| Section | Confidence | Last Verified |
|---------|------------|---------------|
| Identity/Metadata | high | 2026-07-03 |
| Problem Addressed | high | 2026-07-03 |
| Key Features | high | 2026-07-03 |
| Technical Architecture | medium | 2026-07-03 |
| Installation & Usage | high | 2026-07-03 |
| Deployment Options | high | 2026-07-03 |
| Relevance to Claude Code | medium | 2026-07-03 |
| Limitations | medium | 2026-07-03 |

**Confidence notes**:
- **High confidence** sections: Based on official README, CHANGELOG, and package structure directly from source repository
- **Medium confidence** sections: Inferred from API design and architectural patterns; no explicit limitations documentation found in public sources

**Next review**: 2026-10-03 (3 months from creation)

---

*Entry created 2026-07-03 from primary sources via git clone and direct README/CHANGELOG analysis*
