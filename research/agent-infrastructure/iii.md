---
title: iii — Unified Backend Composition Engine
resource: iii
url: https://github.com/iii-hq/iii
organization: iii-hq
last_updated: 2026-06-18
---

## Overview

**iii** is a unified backend composition engine that enables developers to compose, extend, and observe distributed services through three core primitives: **Worker**, **Function**, and **Trigger**. It provides "zero integration" across service boundaries by collapsing multiple integration stories (queues, cron, HTTP, state, observability, agents, sandboxes) into a single live system surface.

**GitHub repository**: [iii-hq/iii](https://github.com/iii-hq/iii)
**Current version**: v0.19.4 (released 2026-06-16)
**Author**: iii-hq (Motia LLC)
**Stars**: 18,262 (as of 2026-06-18)
**Contributors**: 30

---

## Problem Addressed

Traditional backend development requires integrating multiple disconnected systems for different concerns:

- **Queues**: vendor-specific SDKs, retry logic, timeouts
- **Observability tools**: separate integrations for each tool (Datadog, New Relic, etc.)
- **Agent harnesses**: independent configuration for traces, retries, timeouts
- **Cron/scheduling**: dedicated infrastructure
- **State management**: separate database abstractions per service
- **Stream processing**: isolated coordination logic

Each new integration imposes a separate mental model, configuration surface, and debugging experience. **iii solves this by providing a unified abstraction layer**: extending iii is a single `iii worker add` command, composing services uses uniform function calls, and observing the system means opening a single trace interface.

---

## Key Features

### 1. Three Core Primitives

The entire iii mental model consists of three abstractions:

**Workers**
- Processes that register with the iii engine and declare functions and triggers
- Can be written in any language (TypeScript, Python, Rust, Go, shell scripts)
- Discoverable in real time by other workers via a live catalog
- Can create other workers dynamically at runtime (enabling agents to extend the system)
- Source: "[Workers are processes that register with the iii engine and then register triggers and functions. A TypeScript API service is a worker. A Python data pipeline is a worker. A Rust microservice is a worker.](https://github.com/iii-hq/iii/blob/main/README.md)"

**Functions**
- Units of work with stable identifiers (e.g., `content::classify`, `orders::validate`)
- Receive typed input, perform work, optionally return output
- Exist within workers and are discoverable in the function catalog
- Can be invoked directly, via HTTP, via queue, on cron schedule, or triggered by state changes

**Triggers**
- Declarative bindings: "this function runs when this thing happens"
- Supported trigger types: HTTP endpoints, cron schedules, queue subscriptions, state changes, stream events, custom triggers
- Serialization and routing handled by iii; workers declare triggers, engine routes invocations
- Source: "[Triggers are declarative: the Worker defines 'this function runs when this thing happens,' and iii handles routing, serialization, and delivery.](https://github.com/iii-hq/iii/blob/main/README.md)"

### 2. Built-In Worker Modules

The iii engine includes 12 built-in worker modules providing infrastructure capabilities without separate integrations:

- **iii-http**: HTTP endpoint creation and invocation
- **iii-queue**: Durable job queue (supports multiple backends)
- **iii-cron**: Scheduled task execution
- **iii-state**: Key-value state store for distributed coordination
- **iii-pubsub**: Publish-subscribe messaging (pub/sub)
- **iii-stream**: Real-time event streaming
- **iii-observability**: Unified observability hooks (OpenTelemetry-integrated)
- **iii-bridge**: Service-to-service communication bridge
- **iii-exec**: Shell command execution
- **iii-configuration**: Configuration management
- **engine_fn**: Internal engine function registry
- **rest_api**: REST API surface for the engine

Source: "[The engine's built-in workers (iii-queue, iii-state, iii-pubsub, iii-stream, iii-cron, iii-http, iii-observability, iii-bridge, iii-exec, configuration) ship their skills](https://github.com/iii-hq/iii/blob/main/README.md)"

### 3. Live Extensibility

Applications and agents can add new workers to the system at runtime:

```bash
iii worker add queue
iii worker add agent
iii worker add sandbox
iii worker add <anything>
```

Each added worker joins the live catalog and is immediately discoverable and callable by other workers. Agents can discover system capabilities and add new ones dynamically during execution.

Source: "[Workers can also create other workers at runtime, so agents and applications can extend the system while it is running.](https://github.com/iii-hq/iii/blob/main/README.md)"

### 4. Real-Time Discovery and Invocation

All workers and functions are discoverable in a live catalog accessible at [workers.iii.dev](https://workers.iii.dev/). Agents and applications can:
- Query available functions
- Discover function signatures and input schemas
- Call functions immediately after discovery without static configuration

### 5. Multi-Language SDKs

Official SDKs expose a unified API surface across four languages:

| Language | Package | Installation |
|----------|---------|--------------|
| Node.js/TypeScript | `iii-sdk` (npm) | `npm install iii-sdk` |
| Python | `iii-sdk` (PyPI) | `pip install iii-sdk` |
| Rust | `iii-sdk` (crates.io) | `cargo add iii-sdk` |
| Go | `iii-sdk` (github) | `go get github.com/iii-hq/iii/sdk/packages/go/iii` |

All four SDKs expose the same operations: `registerWorker()`, `registerFunction()`, `registerTrigger()`, `trigger()` for invocation (both await and fire-and-forget modes).

### 6. Unified Observability

Traces, metrics, and logs flow through a single OpenTelemetry integration. Every function invocation, trigger, and worker lifecycle event is automatically traced. Access to observability is uniform across the entire system.

Source: "[Traces, metrics, and logs are available without creating config.yaml first.](https://github.com/iii-hq/iii/blob/main/engine/README.md)"

### 7. iii-Console — Developer and Ops Interface

Standalone console binary (React frontend + Rust backend) provides real-time visibility into:
- Registered workers and functions
- Trigger bindings
- Queue contents
- Traces and logs
- Real-time state

Connects to the iii engine via HTTP, WebSocket, and SDK connections.

Source: "[Developer and operations console for inspecting workers, functions, triggers, queues, traces, logs, and real-time state.](https://github.com/iii-hq/iii/blob/main/console/README.md)"

---

## Technical Architecture

### Engine Design

The iii engine is written in Rust and implements a WebSocket-based protocol for worker-to-engine communication:

**Core Components** (from `engine/src/`):

- **`engine/`**: Worker management, function routing, invocation lifecycle, state coordination
- **`protocol.rs`**: WebSocket message schema (RegisterFunctionRequest, TriggerAction, Message types)
- **`workers/`**: Built-in module implementations (HTTP, queue, cron, state, pubsub, stream, observability)
- **`modules/`**: Core infrastructure modules

**Protocol Layer**

Workers communicate with the engine via JSON messages over WebSocket at `ws://localhost:49134`. Key message types:

- `registerfunction`: Worker declares a function
- `invokefunction`: Request function invocation
- `invocationresult`: Result from a function execution
- `registertrigger`: Bind trigger to function
- `unregistertrigger`: Remove trigger binding
- `functionsavailable`: Catalog of available functions
- `ping`/`pong`: Keepalive

Invocations can be fire-and-forget by omitting `invocation_id` in the request.

Source: "[The engine speaks JSON messages over WebSocket. Key message types: registerfunction, invokefunction, invocationresult, registertrigger, unregistertrigger, triggerregistrationresult, registerservice, functionsavailable, ping, pong.](https://github.com/iii-hq/iii/blob/main/engine/README.md)"

**Worker Registration Flow**

1. Worker connects to engine WebSocket at `ws://localhost:49134`
2. Worker sends `RegisterFunctionMessage` for each function with:
   - Function ID (e.g., `content::classify`)
   - Handler function reference
   - Optional metadata
3. Worker sends `RegisterTriggerInput` for each trigger with:
   - Trigger type (http, cron, queue, etc.)
   - Target function ID
   - Trigger configuration (specific to trigger type)
4. Engine indexes functions and broadcasts availability to all connected workers
5. Other workers can immediately invoke the new function via `trigger()`

### Networking and Ports

| Port | Service | Purpose |
|------|---------|---------|
| 49134 | WebSocket | Worker-to-engine connections |
| 3111 | HTTP API | REST API for engine operations |
| 3112 | Stream API | Server-Sent Events and streaming |
| 9464 | Prometheus | Metrics export |

Source: "[Ports: 49134 WebSocket (worker connections), 3111 HTTP API, 3112 Stream API, 9464 Prometheus metrics](https://github.com/iii-hq/iii/blob/main/engine/README.md)"

### Data Flow

```
Worker A registers function foo::bar
  ↓
Engine indexes foo::bar in function catalog
  ↓
Engine broadcasts FunctionsAvailable to all workers
  ↓
Worker B discovers foo::bar (via live catalog or API)
  ↓
Worker B calls trigger({ function_id: "foo::bar", payload: {...} })
  ↓
Engine routes invocation to Worker A
  ↓
Worker A's handler processes payload
  ↓
Engine returns result to Worker B (if not fire-and-forget)
  ↓
Trace, metrics, logs published to OpenTelemetry collector
```

### Configuration

Engines are configured via YAML. Built-in config includes:
- Module configuration (queue backend, state store, logging)
- Security and authentication settings
- Performance tuning (worker limits, queue sizes, timeouts)

Can start with zero configuration: `iii --use-default-config` uses in-memory OpenTelemetry and sensible defaults.

Source: "[This starts the engine with the built-in modules and an in-memory OpenTelemetry configuration, so traces, metrics, and logs are available without creating config.yaml first.](https://github.com/iii-hq/iii/blob/main/engine/README.md)"

---

## Installation & Usage

### Quick Start

1. Install iii engine:

```bash
curl -fsSL https://install.iii.dev/iii/main/install.sh | sh
```

2. Scaffold a project:

```bash
iii project init myapp
cd myapp
```

3. Start the engine:

```bash
iii
```

4. Open the console:

```bash
iii console
```

The engine is immediately available at:
- WebSocket: `ws://localhost:49134` (worker connections)
- HTTP API: `http://localhost:3111` (REST operations)

Source: "[iii project init myapp scaffolds a project. iii starts the engine.](https://github.com/iii-hq/iii/blob/main/README.md)"

### Hello World Example (TypeScript)

```typescript
import { registerWorker } from 'iii-sdk';

const iii = registerWorker('ws://localhost:49134');

iii.registerFunction('hello::greet', async (input) => {
  return { message: `Hello, ${input.name}!` };
});

iii.registerTrigger({
  type: 'http',
  function_id: 'hello::greet',
  config: { api_path: '/greet', http_method: 'POST' },
});

const result = await iii.trigger({
  function_id: 'hello::greet',
  payload: { name: 'world' }
});
```

Source: "[registerWorker creates an SDK instance and auto-connects to the engine. registerFunction registers a named function. registerTrigger binds triggers (http, cron, queue, etc.) to functions.](https://github.com/iii-hq/iii/blob/main/sdk/README.md)"

### Docker Deployment

```bash
# Development
docker compose up -d

# Production with Redis + RabbitMQ + Caddy (TLS)
docker compose -f docker-compose.prod.yml up -d
```

Production image runs with:
- Read-only filesystem
- No shell (distroless runtime)
- Non-root execution
- Trivy vulnerability scanning in CI
- Build provenance attestation

Source: "[Distroless runtime (no shell), non-root execution, Trivy scanning in CI, SBOM attestation, and build provenance.](https://github.com/iii-hq/iii/blob/main/engine/README.md)"

### Agent Skills

Install iii's agent-readable reference material for all engine primitives:

```bash
npx skills add iii-hq/iii/skills
```

This provides AI-optimized documentation for HTTP endpoints, queues, cron, state, streams, custom triggers, and all built-in workers.

Source: "[npx skills add iii-hq/iii/skills covers every iii primitive: HTTP endpoints, queues, cron, state, streams, custom triggers, and more.](https://github.com/iii-hq/iii/blob/main/README.md)"

---

## Relevance to Claude Code Development

### 1. Multi-Agent Coordination and Capability Discovery

iii provides a pattern for **dynamic capability discovery and routing** that directly applies to Claude Code agent orchestration:

- Agents register their capabilities as named functions (e.g., `analysis::code-review`, `test::run-suite`)
- Other agents discover capabilities without hardcoded configuration
- Invocation is uniform across agent types and implementation languages
- This pattern eliminates the need for agent-to-agent API contracts and version negotiation

### 2. Live System Extensibility for AI Agents

The core iii pattern — agents adding new workers at runtime — maps directly to **autonomous agent self-extension**:

- An AI agent can call `iii worker add <capability>` to extend its own system
- New capabilities are immediately discoverable and callable by other agents
- No restart or redeployment required
- Enables agents to "teach" the system new capabilities during execution

### 3. Unified Observability for Agent Execution

iii's OpenTelemetry integration provides **single-pane-of-glass observability** for multi-agent systems:

- Every function invocation across all agents produces a unified trace
- Trace context flows automatically through queue invocations, async executions, and cross-agent calls
- Debugging multi-agent workflows requires inspecting a single trace, not correlating separate logs

### 4. Function Calling and Tool Discovery Pattern

iii's function catalog pattern is analogous to **Claude's function calling** and **MCP tool discovery**:

- Workers publish named functions with schemas (similar to tool definitions)
- Other workers discover and call functions without static registration (similar to MCP tool discovery)
- This pattern scales to complex agent ecosystems where tools are added dynamically

### 5. Queue-Based Agent Task Distribution

iii's queue worker provides a **durable task queue** for distributing work across agent instances:

- Agents can enqueue long-running tasks
- Other agents consume from the queue
- Automatic retry, dead-lettering, and observability
- Enables distributed AI agent systems without separate queue infrastructure

### 6. Agent Skill Packaging

iii ships **agent skills** (at `npx skills add iii-hq/iii/skills`) that document all engine primitives in AI-readable format. This pattern is directly applicable to Claude Code agent skills — documenting agent-callable infrastructure as structured reference material that agents can load and act on.

---

## Limitations and Caveats

### Deployment Scope

iii is designed as a **backend service composition engine**. It is not suitable for:
- Frontend application state management (no browser execution)
- Machine learning model serving (no GPU optimization, no ML-specific features)
- IoT edge computing (requires persistent network connection to engine)

### Operator Complexity

Running iii in production requires:
- Operator familiarity with Rust binary configuration (YAML)
- Understanding of OpenTelemetry setup and backend configuration
- Queue backend selection and maintenance (Redis, RabbitMQ, etc. for durable queues)
- Network security configuration (WebSocket port exposure)

### Architectural Dependency

Applications that adopt iii for core infrastructure become dependent on the engine's availability:
- If the engine crashes, all workers lose the ability to communicate with each other
- No built-in fallback to direct worker-to-worker communication
- Single point of failure unless deployed with high availability

### License Considerations

**Engine runtime**: Elastic License 2.0 (ELv2) — restricts commercial use without explicit license from Motia LLC
**SDKs, CLI, console, docs, website**: Apache License 2.0 — permissive open-source

Organizations using iii must obtain an ELv2 license for production deployments.

Source: "[The engine is licensed under the Elastic License 2.0 (ELv2). All SDKs, CLI, console, documentation, and the website are licensed under the Apache License 2.0.](https://github.com/iii-hq/iii/blob/main/README.md)"

---

## Repository Structure

| Directory | Purpose | Language |
|-----------|---------|----------|
| `engine/` | Core runtime, modules, routing, protocol | Rust |
| `sdk/` | Official SDKs (Node.js, Python, Rust, Go) | TypeScript, Python, Rust, Go |
| `console/` | Developer console (frontend + backend) | React, Rust |
| `skills/` | Agent-readable reference material | Markdown |
| `website/` | Public website (iii.dev) | TypeScript/Next.js |
| `docs/` | Documentation site (Mintlify/MDX) | Markdown |

Source: "[Repository Structure: engine/ (Rust), sdk/ (Node.js, Python, Rust, Go), console/ (React + Rust), skills/ (reference material), website/, docs/](https://github.com/iii-hq/iii/blob/main/README.md)"

---

## References

- **Official Documentation**: [iii.dev/docs](https://iii.dev/docs) (accessed 2026-06-18)
- **GitHub Repository**: [github.com/iii-hq/iii](https://github.com/iii-hq/iii) (accessed 2026-06-18)
- **Engine README**: [engine/README.md](https://github.com/iii-hq/iii/blob/main/engine/README.md) (accessed 2026-06-18)
- **SDK README**: [sdk/README.md](https://github.com/iii-hq/iii/blob/main/sdk/README.md) (accessed 2026-06-18)
- **Console README**: [console/README.md](https://github.com/iii-hq/iii/blob/main/console/README.md) (accessed 2026-06-18)
- **GitHub API**: Repository metadata and release information (accessed 2026-06-18)

---

## Freshness Tracking

**Last reviewed**: 2026-06-18 (v0.19.4)
**Next review**: 2026-09-18 (3 months)

### Confidence Summary

- **Identity/Metadata**: high — verified from GitHub API (stargazers: 18,262; contributors: 30; license: mixed ELv2/Apache 2.0)
- **Key Features**: high — extracted from primary README and architectural documentation
- **Technical Architecture**: high — code structure verified via Rust source files; protocol documented in protocol.rs
- **Installation & Usage**: high — commands verified against engine/README.md; examples extracted from sdk/README.md and official quickstart
- **Built-in Workers**: high — module list verified via filesystem inspection of engine/src/workers/
- **Relevance to Claude Code**: medium — patterns identified from architectural alignment; specific integration points require implementation validation
- **Limitations**: medium — licensing constraints and architectural dependencies extracted from source; operator complexity based on configuration requirements, not hands-on operational experience

### Known Gaps

- Performance characteristics (throughput, latency, scalability limits) not documented in reviewed sources
- Real-world deployment case studies not available in primary sources
- Integration points with specific cloud platforms (AWS, GCP, Azure) not covered in available documentation
- Advanced queue backend configuration (RabbitMQ clustering, Redis Sentinel) not detailed in reviewed materials

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Fly.io](./fly-io.md) | agent-infrastructure | complementary cloud platform for deploying iii-based agent infrastructure globally across 18 regions with Sprites sandbox support |
| [Plano](./plano.md) | agent-infrastructure | AI-native routing and orchestration layer for iii multi-agent deployments with model routing and observability |
| [Trigger.dev](./trigger-dev.md) | agent-infrastructure | durable task checkpoint-resume system for iii long-running agent jobs with human-in-the-loop waitpoints |
| [Zeroboot](./zeroboot.md) | agent-infrastructure | sub-millisecond VM fork sandbox infrastructure for iii worker isolation and safe execution |
| [oh-my-opencode](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | production multi-agent orchestration using worker/function delegation patterns similar to iii core primitives |
| [Ruflo](../agent-frameworks/ruflo.md) | agent-frameworks | multi-agent orchestration framework with dynamic capability discovery and MCP tool routing (parallel architecture) |
| [TAKT](../research-agent-patterns/takt.md) | research-agent-patterns | YAML-defined multi-agent state machine with faceted prompting and worker delegation model |
| [Motia](../api-frameworks/motia.md) | api-frameworks | unified backend framework combining queue/workflow/API concerns (predecessor design pattern to iii unification approach) |
