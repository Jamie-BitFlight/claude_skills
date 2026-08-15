---
title: "Motia"
---

## Overview

Motia is a unified backend framework built around a single primitive called the **Step** — a file with a `config` (defining how and when it runs) and a `handler` (business logic). Inspired by the same paradigm shift React brought to frontend, Motia eliminates runtime fragmentation by replacing separate frameworks for APIs, background jobs, queues, workflows, and AI agents with one cohesive system. It supports JavaScript, TypeScript, and Python (Ruby in beta, Go coming), and ships with a visual Workbench for real-time flow debugging and tracing.

---

## Problem Addressed

| Problem                                                     | Solution                                                                           |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Backend uses 5+ separate frameworks (API, queue, cron, AI) | One Step primitive handles every backend pattern via a `type` field in config      |
| Wiring services together requires manual glue code          | Steps auto-discovered by filename; Motia connects them via emit/subscribe          |
| AI agents need separate orchestration runtime               | Agent workflows are just Steps with `queue` or `event` triggers chained via emit  |
| Observability requires third-party integrations             | Built-in Workbench UI at `localhost:3000` with flow diagrams, traces, state viewer |
| Multi-language backends require polyglot service meshes     | Native JS/TS/Python support in a single project with shared state and topics       |
| AI coding tools lack framework-specific context             | Ships with Cursor `.mdc` rules and AGENTS.md support for 20K+ compatible projects  |

---

## Key Statistics

| Metric           | Value                    | Date Gathered |
| ---------------- | ------------------------ | ------------- |
| GitHub Stars     | 15,107                   | 2026-02-23    |
| GitHub Forks     | 1,006                    | 2026-02-23    |
| Open Issues      | 55                       | 2026-02-23    |
| Contributors     | ~40                      | 2026-02-23    |
| npm Monthly DL   | 9,837                    | 2026-02-23    |
| Latest Release   | v0.17.14-beta.196        | 2026-02-23    |
| Repository Age   | Since January 2025       | 2026-02-23    |
| Primary Language | TypeScript/Python        | 2026-02-23    |

---

## Key Features

### The Step Primitive

- **config** defines trigger type (`http`, `queue`, `cron`, `state`, `stream`), subscribed topics, emitted topics, and flow membership
- **handler** receives input + context object with `emit`, `logger`, `state`, `streams` helpers
- Auto-discovered by filename: `*.step.ts`, `*.step.js`, `*_step.py`
- Change the `type` field to convert between API endpoint, background worker, cron job, or stream processor — same pattern

### Trigger Types

| Type     | When It Runs     | Primary Use Case          |
| -------- | ---------------- | ------------------------- |
| `http`   | HTTP request     | REST API endpoints        |
| `queue`  | Topic message    | Background job processing |
| `cron`   | Schedule         | Recurring jobs            |
| `state`  | State change     | Reactive state workflows  |
| `stream` | Stream event     | Real-time streaming       |

### Multi-Language Support

- **JavaScript** — stable, CommonJS module exports
- **TypeScript** — stable, fully typed with `ApiRouteConfig`, `EventConfig`, `CronConfig` interfaces
- **Python** — stable, module-level `config` dict + `async def handler`
- **Ruby** — beta
- **Go** — planned

### Built-in State Management

- `state.set(key, value)` / `state.get(key)` / `state.getGroup(prefix)` in handlers
- Shared across Steps within a flow — no external database needed for workflow state
- Ideal for tracking progress in multi-step pipelines

### Workbench (Visual Debugger)

- Runs at `http://localhost:3000` during development
- Flow diagrams showing Step connections and topic wiring
- Real-time log streaming with trace IDs
- State inspector and stream monitoring
- Workbench plugins for extensibility (shipped v0.17)

### AI Development Support

- Bundled Cursor IDE `.mdc` rules with context-aware suggestions for Steps
- Compatible with AGENTS.md standard (used by 20K+ projects) for OpenCode, Codex, Jules, Aider, Amp, GitHub Copilot
- Architecture blueprints and AI dev guides included in every `npx motia create` project

### Core Architecture

- Core runtime rewritten in Rust (shipped) for performance
- `iii` engine integration for infrastructure provisioning (`iii-config.yaml`)
- Motia Cloud for production deployment

---

## Technical Architecture

### Step File Structure

<eg>
steps/
  *.step.ts    # TypeScript Steps (auto-discovered)
  *.step.js    # JavaScript Steps (auto-discovered)
  *_step.py    # Python Steps (auto-discovered)
</eg>

### Data Flow Between Steps

<eg>
HTTP POST /messages
  → SendMessage.step (http trigger)
      → enqueue({ topic: 'message.sent', data: {...} })
          → ProcessMessage.step (queue trigger, subscribes: ['message.sent'])
              → logger.info / state.set / enqueue(...)
</eg>

### Context Object (handler second argument)

| Property  | Purpose                                       |
| --------- | --------------------------------------------- |
| `enqueue` | Publish event to a topic for other Steps      |
| `logger`  | Structured logging with auto trace context    |
| `state`   | Key-value storage shared across the flow      |
| `streams` | Real-time stream updates (SSE/WebSocket)      |

### Stack

| Component      | Technology                             |
| -------------- | -------------------------------------- |
| Core Runtime   | Rust (rewritten from Node.js)          |
| Step Runtimes  | Node.js (TS/JS), Python                |
| Infrastructure | `iii` engine (iii.dev)                 |
| Deployment     | Motia Cloud                            |
| Dev UI         | Workbench (React, localhost:3000)      |

---

## Installation & Usage

```bash
# Bootstrap a new Motia project (interactive)
npx motia@latest create

# Start development server with Workbench
npm run dev
# → Workbench: http://localhost:3000
```

### TypeScript Step (API + Queue)

```typescript
// steps/send-message.step.ts
import { Handlers } from 'motia'

export const config = {
  name: 'SendMessage',
  triggers: [
    {
      type: 'http',
      method: 'POST',
      path: '/messages',
    }
  ],
  enqueues: ['message.sent'],
  flows: ['messaging']
}

export const handler: Handlers['SendMessage'] = async (req, { enqueue, state }) => {
  const { text, userId } = req.body
  await state.set(`msg:${userId}`, { text, status: 'queued' })
  await enqueue({ topic: 'message.sent', data: { text, userId } })
  return { status: 200, body: { ok: true } }
}
```

### Python Step (Event consumer)

```python
# steps/process_step.py
config = {
    "name": "ProcessMessage",
    "type": "event",
    "subscribes": ["message.sent"],
    "emits": ["message.processed"],
    "flows": ["messaging"],
}


async def handler(input_data, context):
    text = input_data.get("text")
    await context.logger.info("Processing", {"text": text})
    await context.enqueue({"topic": "message.processed", "data": {"status": "done"}})
```

### Cron Step

```typescript
// steps/daily-summary.step.ts
import { Handlers } from 'motia'

export const config = {
  name: 'DailySummary',
  triggers: [
    {
      type: 'cron',
      cron: '0 9 * * *',
    }
  ],
  enqueues: ['summary.generated'],
  flows: ['reporting']
}

export const handler: Handlers['DailySummary'] = async ({ state, enqueue }) => {
  const messages = await state.getGroup('msg:')
  await enqueue({ topic: 'summary.generated', data: { total: messages.length } })
}
```

---

## Relevance to Claude Code Development

### Applications

- **Skill pipeline backend**: Motia Steps could back multi-step skill orchestration workflows (e.g., research → validate → format → commit) with built-in state tracking and queue retry.
- **Agent workflow infrastructure**: The enqueue/subscribe model mirrors Claude Code's Task-tool delegation pattern; Motia provides a durable, observable runtime for the same pattern.
- **Multi-language skill execution**: Python and TypeScript Steps in the same project align with this repo's mixed Python scripts + TypeScript hooks architecture.
- **AI development guides in project scaffolding**: The `.mdc` rules bundled with `npx motia create` demonstrate a pattern for embedding AI coding context directly in project templates — applicable to plugin/skill scaffolding.

### Patterns Worth Adopting

1. **Single primitive over multiple integrations**: Motia's "one Step for everything" philosophy parallels the skill system's goal of reducing tooling sprawl. A single SKILL.md format for all agent behaviors is analogous.
2. **Config + handler separation**: Separating declarative config (when/how) from imperative handler (what) is a clean pattern for agent step definitions — the SKILL.md frontmatter mirrors this.
3. **Auto-discovery by filename convention**: `*.step.ts` auto-loading is analogous to the skill directory auto-loading pattern; explicit registration can be replaced by naming convention.
4. **AGENTS.md for AI tool context**: Bundling AI coding context files in scaffolded projects (like Motia's `.mdc` Cursor rules) is directly applicable to the `plugin-creator` skill's project initialization.
5. **Built-in observability from day one**: Shipping the Workbench UI as an integral dev experience (not optional add-on) demonstrates that observability should be a first-class concern in agent frameworks.

### Integration Opportunities

1. **Motia as skill pipeline executor**: Complex multi-phase skill workflows (groom → research → implement) could be expressed as Motia flows, gaining durable execution, retry, and visual debugging.
2. **MCP server wrapping Motia Steps**: Expose Motia workflows as MCP tools so Claude Code agents can trigger multi-step backend operations with state tracking and streaming progress.
3. **Research pipeline**: The AI Research Agent example (`examples/ai-deep-research-agent`) is directly relevant — a Motia-based research pipeline could back the `research-curator` skill with observable steps.
4. **Workbench pattern for skill debugging**: The visual flow diagram + trace approach in Workbench could inspire a debugging view for multi-agent skill orchestration.

---

## References

| Source                 | URL                                                                   | Accessed   |
| ---------------------- | --------------------------------------------------------------------- | ---------- |
| Official Website       | <https://www.motia.dev/>                                              | 2026-02-23 |
| GitHub Repository      | <https://github.com/MotiaDev/motia>                                   | 2026-02-23 |
| Documentation          | <https://www.motia.dev/docs>                                          | 2026-02-23 |
| Quick Start Guide      | <https://www.motia.dev/docs/getting-started/quick-start>             | 2026-02-23 |
| Steps Concept          | <https://www.motia.dev/docs/concepts/steps>                          | 2026-02-23 |
| Manifesto              | <https://www.motia.dev/manifesto>                                     | 2026-02-23 |
| Motia Examples         | <https://github.com/MotiaDev/motia-examples>                         | 2026-02-23 |
| npm Package            | <https://www.npmjs.com/package/motia>                                 | 2026-02-23 |
| Vercel OSS 2025        | <https://vercel.com/blog/summer-2025-oss-program#motia>              | 2026-02-23 |

**Research Method**: Information gathered from official website, GitHub repository README, GitHub API (stars, forks, issues, contributors), npm downloads API, and official documentation.

---
