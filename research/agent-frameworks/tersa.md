# Tersa

**Research Date**: 2026-03-06
**Source URL**: <https://vercel.com/templates/next.js/tersa-ai-workflow-canvas>
**GitHub Repository**: <https://github.com/vercel-labs/tersa>
**Version at Research**: v2.0.0
**License**: MIT

---

## Overview

Tersa is an open-source visual canvas for building AI workflows, created by Hayden Bleasel under Vercel Labs. It provides a drag-and-drop node editor (built on ReactFlow) where users connect typed nodes — text, image, video, audio, code — to form multi-step AI pipelines, routing data through 25+ providers via the Vercel AI SDK Gateway. Canvas state persists in browser local storage; no backend storage is required for basic use.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Chaining multiple AI models requires writing custom glue code for each provider | ReactFlow canvas lets users drag-drop nodes and draw edges to define data flow visually, eliminating integration code |
| Switching providers requires API-level rewrites | Vercel AI SDK Gateway normalizes all providers behind a single `creator/model-name` string format |
| No visibility into model pricing when selecting from 25+ providers | Cost Indicators display relative pricing across models directly on each node's model picker |
| Debugging streaming AI pipelines is opaque | Reasoning Extraction surface per-request model thinking steps where supported (e.g., o1, Claude 3.7 Sonnet extended thinking) |
| Sharing AI experiments requires sharing code repos | Local Storage persistence means the canvas state is serialized in the browser; no server or account needed to save work |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 927 | 2026-03-06 |
| Forks | 164 | 2026-03-06 |
| Human Contributors | 3 | 2026-03-06 |
| Latest Release | v2.0.0 | 2026-02-20 |
| Open Issues | 10 | 2026-03-06 |
| Releases (total) | 82 | 2026-03-06 |
| Primary Language | TypeScript (97.6%) | 2026-03-06 |

---

## Key Features

### Visual Workflow Canvas

- Drag-and-drop node editor built on ReactFlow — nodes represent discrete AI tasks (generate text, generate image, transcribe audio, generate video, transform code)
- Edges represent data flow: output handle of one node connects to input handle of the next
- Node toolbar for adding new nodes; canvas supports pan, zoom, and multi-select
- Canvas state serialized to browser `localStorage` automatically — no sign-in required to persist work

### Multi-Model Support via AI SDK Gateway

- Single normalized API for 25+ providers: OpenAI, Anthropic, Google, Meta, xAI, Stability AI, Replicate, and more
- Model string format follows `creator/model-name` convention (e.g., `anthropic/claude-sonnet-4-5`, `openai/gpt-5`)
- Vercel AI Gateway handles authentication, routing, retries, and provider fallbacks
- Bring-your-own-key (BYOK) mode: zero token markup versus direct provider pricing

### Cost Indicators

- Each model picker shows relative cost tier (input/output token pricing) sourced from the AI Gateway models endpoint
- Enables cost-aware model selection without leaving the canvas
- Dynamic — pricing pulled from `https://ai-gateway.vercel.sh/v1/models` at runtime

### Streaming and Reasoning

- Real-time streaming responses: text generation nodes stream token-by-token into output handles
- Reasoning Extraction: for models that expose chain-of-thought (e.g., DeepSeek R1, Claude extended thinking, OpenAI o-series), the reasoning trace is surfaced separately from the final output
- TipTap rich-text editor handles text node input and output rendering

### AI Agent Mode (Tersa Agent)

- Added in PR #111: natural-language chat interface that interprets user instructions and performs canvas operations autonomously
- Understands canvas state (selected nodes, existing connections)
- Translates prompts like "Create a workflow that transcribes audio and summarizes it" into node creation and wiring operations
- Destructive operations guarded by confirmation before execution

### Media Handling

- Vercel Blob storage backend for image, video, and audio file uploads
- Drop files directly onto the canvas as input nodes
- Image generation nodes: output is a Blob URL rendered inline in the canvas
- Video generation nodes connect to supported video model providers

---

## Technical Architecture

Tersa is a Next.js 15 application with App Router and Turbopack, deployed as a Vercel template.

```text
Browser
  └─ React 19 + Next.js 15 (App Router)
       ├─ ReactFlow  — canvas, node/edge state management
       │    ├─ Custom node components per modality
       │    │    (TextNode, ImageNode, VideoNode, AudioNode, CodeNode)
       │    └─ Edge routing — typed handles enforce compatible connections
       ├─ TipTap — rich text editing inside TextNode inputs/outputs
       ├─ shadcn/ui + Kibo UI + Radix UI — component primitives
       ├─ Tailwind CSS — styling
       └─ localStorage — canvas state persistence (no user account required)

Server (Next.js API Routes)
  ├─ Vercel AI SDK (generateText, streamText, generateImage)
  │    └─ AI SDK Gateway — unified provider routing
  │         provider string: "creator/model-name"
  │         providers: OpenAI, Anthropic, Google, xAI, Meta, Stability, Replicate...
  └─ Vercel Blob — stores uploaded and generated media assets
```

Data flow when a workflow runs:

1. User clicks Run on a root node
2. Node sends its inputs to the Next.js API route via `fetch`
3. API route calls `streamText` / `generateImage` via AI SDK Gateway with the configured provider string
4. Streaming response flows back to the node's output handle
5. Downstream connected nodes receive the output as their input and execute in turn

---

## Installation & Usage

```bash
# Clone and install
git clone https://github.com/vercel-labs/tersa.git
cd tersa
pnpm install
```

```bash
# Configure credentials
cp .env.example .env.local
# Add AI_GATEWAY_API_KEY and optionally per-provider API keys
```

```bash
# Run development server (Node.js v20+ required)
pnpm dev
# Open http://localhost:3000
```

```typescript
// AI SDK Gateway call pattern used by Tersa nodes (from Vercel docs)
import { generateText } from 'ai';

const { text } = await generateText({
  model: 'anthropic/claude-sonnet-4-5',
  prompt: 'Summarize the following text: ...',
});
```

```bash
# One-click deploy to Vercel (production)
# Use Vercel template: https://vercel.com/templates/next.js/tersa-ai-workflow-canvas
```

---

## Relevance to Claude Code Development

### Applications

- Tersa is a reference implementation for how to build a visual node-based interface on top of the Vercel AI SDK — directly applicable when designing canvas-style UIs for agent workflow visualization
- The pattern of routing heterogeneous AI tasks through a single gateway with a unified model-string format (`creator/model-name`) is reusable in any multi-provider orchestration system
- The Tersa Agent feature (PR #111) demonstrates how to build a natural-language-to-canvas operator that understands graph state — a pattern applicable to Claude Code sub-agent orchestration UIs

### Patterns Worth Adopting

- **Typed node handles**: enforcing connection compatibility at the UI layer (e.g., text output cannot connect to image input without a transform node) prevents silent type mismatches in pipelines
- **Cost Indicators on model selection**: exposing pricing at selection time, not after API call, is an ergonomic improvement any multi-model tool should adopt
- **Reasoning Extraction as a first-class output**: surfacing chain-of-thought separately from the final answer gives users transparency without polluting the main output stream — relevant for Claude extended thinking workflows
- **Canvas state in localStorage**: deferring persistence to local storage eliminates auth-gating for initial experimentation, lowering barrier to entry for new users

### Integration Opportunities

- Tersa could serve as a front-end for visualizing Claude Code sub-agent orchestration graphs: each agent maps to a node, edges represent task handoffs
- The Vercel AI SDK Gateway authentication pattern (`AI_GATEWAY_API_KEY` + `creator/model-name`) could replace per-provider API key management in Claude Code plugin environments
- Tersa's open-source node component library (TextNode, ImageNode, etc.) could be forked to build a workflow visualization panel for the `implement-feature` / `swarm-task-planner` skill stack

---

## References

- [Tersa GitHub Repository — vercel-labs/tersa](https://github.com/vercel-labs/tersa) (accessed 2026-03-06)
- [Tersa Vercel Template Page](https://vercel.com/templates/next.js/tersa-ai-workflow-canvas) (accessed 2026-03-06)
- [Vercel AI Gateway Documentation](https://vercel.com/docs/ai-gateway) (accessed 2026-03-06)
- [AI SDK Gateway Provider Reference](https://ai-sdk.dev/providers/ai-sdk-providers/ai-gateway) (accessed 2026-03-06)
- [Vercel AI Gateway Models and Providers](https://vercel.com/docs/ai-gateway/models-and-providers) (accessed 2026-03-06)
- [Tersa Agent PR #111 — feat: add Tersa Agent](https://github.com/vercel-labs/tersa/pull/111) (accessed 2026-03-06)
- [Tersa v2.0.0 Release Notes](https://github.com/vercel-labs/tersa/releases/tag/v2.0.0) (accessed 2026-03-06)
- [BrightCoding — Tersa: The Visual AI Playground Every Developer Needs](https://www.blog.brightcoding.dev/2026/02/15/tersa-the-visual-ai-playground-every-developer-needs) (accessed 2026-03-06)

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-06 |
| Version at Verification | v2.0.0 |
| Next Review Recommended | 2026-06-06 |

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Cursor Cookbook](cursor-cookbook.md) | agent-frameworks | referenced by Cursor Cookbook (agent-frameworks) |
