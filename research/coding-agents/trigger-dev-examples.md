---
title: Trigger.dev Examples Repository
slug: trigger-dev-examples
resource-url: https://github.com/triggerdotdev/examples
primary-language: TypeScript
license: Apache-2.0
created: "2024-08-21"
last-updated: "2026-03-23"
---

# Trigger.dev Examples Repository

## Overview

The Trigger.dev examples repository is a curated collection of full-stack and headless project templates demonstrating practical implementations of Trigger.dev's job scheduling, task orchestration, and real-time communication capabilities. The repository serves as a learning resource and starting point for developers building applications with background jobs, AI agents, and event-driven workflows.

**Repository**: <https://github.com/triggerdotdev/examples>
**License**: Apache License 2.0
**Primary Language**: TypeScript
**Repository Stats** (as of 2026-04-11):
- 103 GitHub stars
- 25 forks
- 1 open issue
- Created: August 21, 2024
- Last code push: March 23, 2026

## Key Statistics

- **29 example projects** covering web frameworks, AI agents, data processing, and integrations
- **Main platforms featured**: Next.js, Remix, Supabase Edge Functions, Vercel, and standalone Node.js
- **AI framework integrations**: Claude Agent SDK, OpenAI Agents SDK, Vercel AI SDK, Mastra agents
- **Repository size**: 4.8 MB (shallow clone)

## Key Features

### 1. Comprehensive Example Coverage

The repository showcases Trigger.dev usage across multiple domains:

**Web Framework Integration** (How it works: Examples demonstrate trigger patterns through frontend and API route integration)
- Next.js examples: hello world, server actions, webhooks
- Remix webhooks example
- Supabase Edge Functions integration

**AI Agent Patterns** (Mechanism: Implementations use Trigger.dev tasks as agent orchestration backbone)
- Building effective agents: 5 patterns (prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer)
- Claude Agent SDK integration with Trigger.dev
- OpenAI Agents SDK with TypeScript playground
- Mastra agents framework integration

**Real-time Features** (Configuration: Uses Trigger.dev's Realtime API for progressive updates)
- Article summary workflow with human-in-the-loop
- Batch LLM evaluator with progress tracking
- CSV importer with real-time progress
- FAL.ai image generation with live updates
- Claude changelog generator with streaming

**Data Processing & Integration**
- Image generation (OpenAI DALL-E, FAL.ai, Replicate)
- Web scraping (Anchor Browser, Crawl4AI, Playwright)
- PDF processing (form extraction with PyMuPDF)
- CSV/document processing and conversion
- Company enrichment with Supabase and Exa

### 2. Multiple Technology Stacks

**JavaScript/TypeScript** (Primary language for most examples)
- Node.js task definitions
- React for frontends with Trigger.dev hooks
- Next.js, Remix, and custom server implementations

**Python Examples**
- Crawl4AI web scraper
- PyMuPDF-based PDF form extractor
- Pillow-based image processing
- MarkItDown document-to-markdown converter

**Infrastructure & Deployment**
- Monorepo examples (Turborepo, Prisma)
- Supabase integration patterns
- Edge functions on Supabase

### 3. AI-Focused Capabilities

The repository emphasizes AI agent patterns with concrete implementations:

- **Prompt Chaining**: Sequential LLM calls with gate logic (word count validation)
- **Routing**: Dynamic task dispatcher that classifies queries and routes to appropriate models
- **Parallelization**: `batch.triggerByTaskAndWait()` for simultaneous task execution
- **Orchestrator-Workers**: Hierarchical task coordination for complex workflows
- **Evaluator-Optimizer**: Quality control with recursive feedback loops
- **Human-in-the-Loop**: ReactFlow-based UI with Trigger.dev Realtime and waitpoints

## Technical Architecture

### Core Components

**Task Definition** (Component: Trigger.dev SDK tasks)
- Exported as `trigger` subdirectories in each example
- Decorated with `@trigger.io/sdk` for metadata
- Example: `hello-world.ts` (~20 lines for basic task)

**Integration Points** (Data flow: Frontend → API route → Trigger.dev SDK → Task execution → Infrastructure)
1. Frontend dispatches event (button click, form submission)
2. API route calls Trigger.dev SDK methods to trigger tasks
3. Task executes on Trigger.dev infrastructure
4. Results streamed back via Realtime API or webhooks

**Real-time Communication** (Extension point: Trigger.dev Realtime API)
- Socket.io-based bidirectional communication
- Progress updates during long-running tasks
- Waitpoints for human intervention (article summary workflow)

**Orchestration Patterns**
- `batch.triggerByTaskAndWait()`: Run multiple tasks in parallel, wait for all to complete
- Recursive task calling for evaluator-optimizer pattern
- Event-driven triggering from webhooks and Edge Functions

### Data Flow Example (Building Effective Agents)

```
User Question
  ↓ [Routing task - classify]
  ├→ Simple Query → Fast Model (GPT-4o mini)
  └→ Complex Query → Powerful Model (GPT-4 Turbo)
       ↓ [Parallelization example]
       ├→ Generate Response (task 1)
       ├→ Check Safety (task 2) [parallel]
       ↓ [batch.triggerByTaskAndWait]
  Orchestrate Results → Return Answer
```

## Installation & Usage

### Prerequisites

- Node.js 18+ or Python 3.8+ (depending on example)
- Trigger.dev account at <https://cloud.trigger.dev>
- API key from Trigger.dev dashboard (`TRIGGER_SECRET_KEY`)

### Local Development Pattern (Next.js Example)

```bash
# 1. Clone and install
git clone https://github.com/triggerdotdev/examples.git
cd trigger-nextjs-hello-world
cp .env.example .env.local
pnpm install

# 2. Start development servers (two terminals)
pnpm dev              # Next.js on :3000
npx trigger dev       # Trigger.dev local dev server

# 3. Access frontend at localhost:3000 and trigger tasks
```

### Key Environment Configuration

- `TRIGGER_SECRET_KEY`: API key for task authentication
- Framework-specific env vars (OpenAI API key, model selection, etc.)
- Integration credentials (Supabase, S3, external APIs)

### Running Examples

Each example directory includes its own README with specific setup instructions. All follow the pattern:

1. Copy `.env.example` to `.env.local` (or `.env`)
2. Add Trigger.dev secret key and example-specific credentials
3. Install dependencies (`pnpm install` or `pip install -r requirements.txt`)
4. Run local dev server and Trigger.dev CLI

## Limitations and Caveats

### Documented Limitations

1. **Local Development Required**: All examples require local dev setup; no hosted playground for most (except OpenAI Agents SDK playground)
2. **Dependency on Trigger.dev Cloud**: Examples assume a Trigger.dev cloud account for production; local CLI for development
3. **API Key Management**: Requires managing multiple API keys (Trigger.dev, OpenAI, etc.) in environment files
4. **Python Examples Limited**: Only a subset of examples support Python; most are TypeScript/Node.js
5. **Framework Coverage**: Examples focus on Next.js, Remix, and Node.js; other frameworks (Express, Fastify, etc.) require custom integration

### Implementation Constraints

- **Real-time Examples**: Require Trigger.dev Realtime API (paid feature on Trigger.dev Cloud)
- **AI Examples**: Depend on external LLM providers (OpenAI, Anthropic) and their API availability
- **Monorepo Examples**: Specific to Turborepo; other monorepo tools would require adaptation
- **Webhook Timing**: Webhook examples depend on internet-accessible endpoints for local testing

### Known Gaps

- No documented limitations found in README files — suggests either comprehensive documentation or limited known issues as of March 2026
- Edge case: Windows compatibility not explicitly covered in examples (all use `pnpm`, bash scripts)

## Relevance to Claude Code Development

### Direct Applicability

1. **Agent Orchestration Patterns**: The five AI agent patterns (prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer) map directly to Claude Agent patterns and can inform agent workflow design in Claude Code

2. **Task Coordination Architecture**: `batch.triggerByTaskAndWait()` pattern demonstrates how to parallelize independent Claude agent tasks — applicable to multi-agent orchestration in Claude Code

3. **Real-time Streaming Architecture**: Trigger.dev's Realtime API pattern (Socket.io-based bidirectional updates) parallels Claude Code's progress streaming and interactive updates

4. **Human-in-the-Loop Workflows**: Article summary example with ReactFlow demonstrates state-machine UI for asynchronous agent workflows — useful for Claude Code feature planning

### Integration Scenarios

1. **Building Claude Code Skills**: Examples of task triggering patterns could inform how to design Trigger.dev-based skills that delegate long-running work
2. **Multi-Step Feature Implementation**: Orchestrator-workers pattern applicable to coordinating Claude agents across implementation phases
3. **Real-time Agent Feedback**: Realtime CSV importer and image generation examples show progress UI patterns for long-running Claude agent sessions
4. **Error Recovery**: Trigger.dev's built-in retry and error handling patterns could inform Claude Code agent resilience design

### Learning Value

- Practical examples of integrating third-party AI services (OpenAI, Anthropic, etc.) with task infrastructure
- Monorepo project structure for managing multiple agent/skill definitions
- Environment management and configuration patterns for multi-tenant agent systems

## References

- **Main Repository**: <https://github.com/triggerdotdev/examples>
- **Trigger.dev Main Repository**: <https://github.com/triggerdotdev/trigger.dev>
- **Trigger.dev Documentation**: <https://trigger.dev/docs>
- **Trigger.dev Quick Start**: <https://trigger.dev/docs/quick-start>
- **Building Effective Agents Guide**: <https://trigger.dev/blog/ai-agents-with-trigger>
- **Trigger.dev Realtime Docs**: <https://trigger.dev/docs/realtime/overview>
- **Batch Trigger API**: <https://trigger.dev/docs/triggering>
- **React Hooks Reference**: <https://trigger.dev/docs/frontend/react-hooks>
- **GitHub API Response** (accessed 2026-04-11): Repository statistics, created date, license
- **README Content** (accessed 2026-04-11): Project descriptions, feature summaries, example directory listing
- **Building Effective Agents README**: <https://github.com/triggerdotdev/examples/tree/main/building-effective-agents>
- **Next.js Hello World README**: <https://github.com/triggerdotdev/examples/tree/main/trigger-nextjs-hello-world>

## Freshness Tracking

**Last Research**: 2026-04-11
**Next Review**: 2026-07-11 (3 months)

### Confidence by Section

- **Identity/Metadata**: high — GitHub API provides authoritative stats, created date, license
- **Key Statistics**: high — GitHub API data as of 2026-04-11
- **Key Features**: high — extracted from README.md (main source) and individual example READMEs
- **Technical Architecture**: medium-high — documented in READMEs and inferred from example code patterns; no architecture diagram in source
- **Installation & Usage**: high — extracted from local example READMEs and repo root README
- **Limitations**: medium — no explicit limitations section found; conclusion is based on absence of documented limitations
- **Relevance to Claude Code**: medium — inferred from feature analysis and agent pattern documentation; not explicitly stated in source

### Change Tracking

- Repository has 103 stars (growth from creation in Aug 2024)
- Last code commit: March 23, 2026 (recent, active maintenance)
- 29 example projects as of March 2026 (repo growth indicates ongoing additions)
- New examples since original publishing suggest expanding AI agent pattern coverage

### Validation Notes

- All example projects verified to be present in cloned worktree
- README table of 29 projects cross-checked with directory listing
- GitHub API confirms Apache 2.0 license and repository metadata
- Example code patterns confirmed by reading sample READMEs (trigger-nextjs-hello-world, building-effective-agents)
