---
title: Trigger.dev
resource: trigger.dev
url: https://github.com/triggerdotdev/trigger.dev
description: Open-source platform for building AI workflows in TypeScript with long-running tasks, retries, queues, observability, and elastic scaling.
status: current
reviewed_date: 2026-04-11
---

## Overview

Trigger.dev is an open-source platform for building AI workflows in TypeScript. From README: "Trigger.dev is the open-source platform for building AI workflows in TypeScript. Long-running tasks with retries, queues, observability, and elastic scaling." The platform is designed specifically for building AI agents using all frameworks, services, and LLMs.

**Key identity**:
- License: Apache License 2.0
- Language: TypeScript (primary)
- Repository stars: 14,488 (as of April 2026)
- Repository forks: 1,145
- SDK version: @trigger.dev/sdk v4.4.3
- Created: November 30, 2022

## Problem Addressed

Trigger.dev addresses the challenge of deploying long-running AI agents and background tasks without being constrained by serverless platform timeout limits. From the README: "Long-running without timeouts: Execute your tasks with absolutely no timeouts, unlike AWS Lambda, Vercel, and other serverless platforms."

The platform solves four core problems:
1. Task timeout constraints in serverless environments (Lambda, Vercel)
2. Durability and reliability of background jobs with automatic retries and queues
3. Visibility into long-running task execution with full tracing and logs
4. Infrastructure management complexity (offers both cloud hosting and self-hosting options)

## Key Statistics

- **14,488 GitHub stars** (as of April 2026)
- **1,145 forks**
- **@trigger.dev/sdk** published on npm with monthly downloads tracked
- Monorepo structure containing 10+ packages under `packages/` directory
- Documentation site available at <https://trigger.dev/docs>
- Self-hosting options: Docker Compose and Kubernetes (Helm chart)

## Key Features

### Task Definition and Execution
From README code example:
```typescript
import { task } from "@trigger.dev/sdk";

export const helloWorld = task({
  id: "hello-world",
  run: async (payload: { message: string }) => {
    console.log(payload.message);
  },
});
```
Tasks are written in TypeScript/JavaScript in the user's codebase, version-controlled, and deployed to Trigger.dev.

### Long-running Tasks
"Execute your tasks with absolutely no timeouts, unlike AWS Lambda, Vercel, and other serverless platforms." Tasks can run indefinitely without timeout interruption.

### Durability and Retries
"Durability, retries & queues: Build rock solid agents and AI applications using our durable tasks, retries, queues and idempotency." Automatic retry mechanisms and queue management are built-in.

### Runtime Flexibility
"True runtime freedom: Customize your deployed tasks with system packages – run browsers, Python scripts, FFmpeg and more." Tasks can execute system-level operations beyond typical JavaScript constraints.

### Human-in-the-Loop
"Human-in-the-loop: Programmatically pause your tasks until a human can approve, reject or give feedback." Waitpoints allow critical decision points requiring human judgment.

### Real-time Capabilities
"Realtime apps & streaming: Move your background jobs to the foreground by subscribing to runs or streaming AI responses to your app." Trigger.dev Realtime enables real-time updates and LLM streaming support.

### Scheduled Tasks
"Durable cron schedules: Create and attach recurring schedules of up to a year." Native cron scheduling with durability guarantees.

### Structured Data Validation
"Structured inputs / outputs: Define precise data schemas for your tasks with runtime payload validation." SchemaTask provides runtime type safety for task payloads.

### Batch Operations
"Batch triggering: Use batchTrigger() to initiate multiple runs of a task with custom payloads and options." Support for triggering multiple task runs simultaneously.

### Concurrency Management
"Concurrency & queues: Set concurrency rules to manage how multiple tasks execute." Fine-grained control over task execution concurrency.

### Multiple Environments
"Multiple environments: Support for DEV, PREVIEW, STAGING, and PROD environments." Isolated environment support including preview branches (integrates with Vercel).

### Observability
"Observability & monitoring: Monitor every aspect of your tasks' performance with comprehensive logging and visualization tools." Full tracing, logging, and monitoring with error alerts.

### Additional Features
- Waitpoints for human-in-the-loop workflows
- Versioning with atomic deployment (prevents conflicts with running tasks)
- Machine configuration for CPU/RAM customization
- Tags (up to 10 per run) for filtering and organization
- Run metadata attached and updated during execution
- Bulk actions on multiple runs (replay, cancel)
- Real-time alerts (email, Slack, etc.)
- Build extensions via extension system
- React hooks package for frontend integration
- Python SDK support

## Technical Architecture

### Repository Structure
Trigger.dev is organized as a pnpm monorepo managed with Turbo. From AGENTS.md:
- `apps/webapp` – Remix application serving as main API and dashboard
- `apps/supervisor` – Node application for executing built tasks
- `packages/*` – Published packages including `@trigger.dev/sdk`, CLI, and shared libraries
- `internal-packages/*` – Internal-only packages used by webapp and other apps
- `references/*` – Example projects for manual testing and feature development
- `ai/references` – Additional documentation (overview and testing guidelines)

### Core Components
**SDK Package** (`@trigger.dev/sdk` v4.4.3):
- Exports available at `.`, `./v3`, and `./ai`
- Supports both CommonJS and ES modules
- Contains task definition, execution, and integration APIs
- Uses TypeScript for full type safety

**Webapp** (Remix application):
- API and dashboard frontend
- Runs on localhost:3030 during development
- Integrates with PostgreSQL and Redis

**Supervisor** (Node application):
- Responsible for executing built tasks
- Manages task lifecycle and durability

**Supporting Packages**:
- `@trigger.dev/cli-v3` – Command-line interface
- `@trigger.dev/core` – Core platform functionality
- `@trigger.dev/react-hooks` – Frontend integration
- `@trigger.dev/build` – Build system components
- `@trigger.dev/redis-worker` – Redis-backed worker implementation
- `@trigger.dev/rsc` – React Server Components support
- `@trigger.dev/python` – Python SDK

### Execution Model
From README: "Trigger.dev uses a checkpoint-resume system for durability. Tasks are inherently durable, thanks to our checkpointing feature." Execution includes:
- Checkpoint-resume mechanism for fault tolerance
- Queue-based task execution
- Real-time communication via WebSocket/streaming
- Distributed worker pool with concurrency control

### Infrastructure
"No infrastructure to manage: Auto-scaling infrastructure that eliminates timeouts and server management." Platform provides:
- Auto-scaling task execution
- Automatic retries on failure
- Multiple environment isolation (DEV, PREVIEW, STAGING, PROD)
- Self-hosting options: Docker Compose and Kubernetes

## Installation & Usage

### Prerequisites
From AGENTS.md development setup:
- pnpm 10.23.0 or later (required)
- Node.js 20.20.0 or later
- Docker (for local services: PostgreSQL, Redis)

### Quick Start
From README: "The quickest way to get started is to create an account and project in our web app at <https://cloud.trigger.dev>, and follow the instructions in the onboarding. Build and deploy your first task in minutes."

### Cloud Deployment
1. Create account at <https://cloud.trigger.dev>
2. Create a project
3. Follow onboarding instructions to deploy first task

### Self-Hosting
From README:
- **Docker**: Follow Docker self-hosting guide to spin up Trigger.dev instance using Docker Compose
- **Kubernetes**: Deploy to Kubernetes cluster using official Helm chart

### Local Development Setup
From AGENTS.md:
1. Install dependencies: `pnpm i`
2. Copy `.env.example` to `.env` and generate encryption key: `openssl rand -hex 16`
3. Start local services: `pnpm run docker`
4. Run database migrations: `pnpm run db:migrate`
5. Build packages: `pnpm run build --filter webapp && pnpm run build --filter trigger.dev && pnpm run build --filter @trigger.dev/sdk`
6. Launch development server: `pnpm run dev --filter webapp` (webapp runs on <http://localhost:3030>)

### Basic Task Example
```typescript
import { task } from "@trigger.dev/sdk";

export const helloWorld = task({
  id: "hello-world",
  run: async (payload: { message: string }) => {
    console.log(payload.message);
  },
});
```

### Testing
- **Unit tests**: Use vitest, run with `pnpm run test`
- **Run specific workspace tests**: `pnpm run test --filter webapp`
- **Run single test file**: Navigate to directory and run `pnpm run test ./path/to/test.ts`
- **E2E tests**: Use Playwright, run with `pnpm run test:e2e`

## Relevance to Claude Code Development

Trigger.dev is highly relevant for autonomous AI agents and multi-step workflows:

1. **Agent Task Execution**: The SDK is specifically designed for "building AI agents" with long-running task support, making it ideal for autonomous agents that perform complex, time-intensive operations.

2. **Workflow Orchestration**: Human-in-the-loop waitpoints and task chaining enable interactive agent workflows where agents can pause for human feedback at critical decision points.

3. **Agent Observability**: The "full trace view of every task run" and comprehensive logging provide visibility into agent execution flows, essential for debugging autonomous behavior.

4. **Durable Agent Sequences**: Checkpointing and automatic retries ensure reliability in multi-step agent sequences that might span hours or days.

5. **Real-time Agent Responses**: The Realtime API with LLM streaming support enables agents to stream responses back to frontend applications in real-time.

6. **Environment Isolation**: Multiple environment support (DEV, PREVIEW, STAGING, PROD) supports agent development workflows from local testing through production deployment.

7. **Integration Platform**: The extensible SDK and integration system allow agents to trigger external services, connect to APIs, and coordinate with other systems.

## Limitations and Caveats

1. **TypeScript/JavaScript Primary**: The platform is built for TypeScript/JavaScript; Python SDK exists but is secondary. Agents primarily using Python may require additional integration work.

2. **Cloud Vendor Lock-in (Cloud Hosted)**: While self-hosting is available, the cloud platform may create dependency on Trigger.dev infrastructure. Self-hosting requires Kubernetes or Docker Compose setup.

3. **Concurrency Limits**: Concurrency rules require configuration; default limits exist but may require tuning for high-throughput agent scenarios.

4. **Task Size Constraints**: Payload schemas and task execution have constraints (not explicitly documented in reviewed sources but typical for distributed task systems).

5. **Cold Start Overhead**: First task execution in an environment may have initialization overhead not documented in reviewed sources.

6. **Learning Curve**: The checkpoint-resume execution model and distributed task semantics differ from simple function calls and require understanding of fault tolerance patterns.

## References

- [Trigger.dev GitHub Repository](https://github.com/triggerdotdev/trigger.dev) — Source code, README, AGENTS.md, CONTRIBUTING.md (accessed 2026-04-11)
- [Trigger.dev Website](https://trigger.dev) — Cloud platform, documentation, product pages (accessed 2026-04-11)
- [Trigger.dev Documentation](https://trigger.dev/docs) — Quick start, how it works, guides, self-hosting (accessed 2026-04-11)
- [npm: @trigger.dev/sdk](https://www.npmjs.com/package/@trigger.dev/sdk) — SDK package registry (accessed 2026-04-11)
- GitHub API: Repository metadata — stars, forks, language, license (accessed 2026-04-11)

## Freshness Tracking

**Next review**: 2026-07-11 (3 months)

**Confidence Summary**:
- Identity/Metadata: high — extracted from repository package.json and GitHub API
- Features: high — extracted verbatim from official README and documentation links
- Architecture: high — extracted from AGENTS.md repository structure guide
- Usage Examples: high — extracted from official README code examples and AGENTS.md setup instructions
- Limitations: medium — common patterns inferred for distributed task systems; not all constraints explicitly documented in reviewed sources

**Known gaps**:
- Specific performance benchmarks not documented in reviewed sources
- Detailed pricing information for cloud platform not included in repository
- Advanced integration patterns beyond SDK documentation scope
