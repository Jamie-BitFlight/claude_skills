---
title: "json-render"
research_date: "2026-02-26"
source_url: "https://json-render.dev"
github_url: "https://github.com/vercel-labs/json-render"
version_at_research: "v0.10.0 (all packages, released 2026-02-25)"
license: "Apache-2.0"
last_verified: "2026-02-26"
version_at_verification: "v0.10.0"
next_review: "2026-05-26"
---

## Overview

json-render is a TypeScript Generative UI framework by Vercel Labs that enables AI to generate dynamic, personalized user interfaces from natural language prompts while constraining output to a developer-defined component catalog. The framework uses a flat JSON spec format (element map keyed by ID) as the interface contract between LLM and renderer, with built-in streaming support for progressive rendering as the model responds. It targets React (web), Vue, React Native (mobile), Remotion (video), and React PDF (documents) from a shared catalog definition, with an optional pre-built shadcn/ui component library of 39 components.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI-generated UIs are unpredictable and can use arbitrary components | Catalog system constrains AI output to only developer-defined components and actions |
| Building custom Generative UI requires complex ad-hoc JSON parsing | Structured flat spec format (`root` + `elements` map) with Zod schema validation via `@json-render/core` |
| LLM responses arrive incrementally but UIs wait for completion | `SpecStream` compiler processes chunks progressively; `Renderer` updates as JSON streams in |
| Same catalog cannot target web and mobile | Shared `defineCatalog` abstraction with platform-specific renderer packages (`@json-render/react`, `@json-render/react-native`) |
| Dynamic UI behavior (conditionals, data binding) requires custom logic | Built-in expression system (`$state`, `$cond`, `$template`, `$computed`) evaluated at render time |
| State management for AI-driven UIs is undefined | `StateStore` abstraction with adapters for Redux, Zustand, Jotai, and XState |
| Generating system prompts for structured output is repetitive | `catalog.prompt()` auto-generates LLM system prompts from catalog definition |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 11,359 | 2026-02-26 |
| GitHub Forks | 609 | 2026-02-26 |
| Open Issues | 52 | 2026-02-26 |
| Contributors | ~10 | 2026-02-26 |
| @json-render/core (monthly DL) | 167,273 | 2026-02-26 |
| @json-render/react (monthly DL) | 107,079 | 2026-02-26 |
| Latest Release | v0.10.0 (all packages) | 2026-02-25 |
| Repository Created | 2026-01-14 | 2026-02-26 |
| Primary Language | TypeScript | 2026-02-26 |

SOURCE: GitHub API (stars, forks, issues, contributors, created date), npm downloads API (2026-02-26)

---

## Key Features

### Component Catalog System

- **`defineCatalog`**: Single function accepting a schema and component/action definitions with Zod prop schemas and string descriptions used to generate LLM prompts
- **Type-safe prop schemas**: Each component declares props via `z.object(...)` — invalid AI output is caught at the schema boundary
- **Action definitions**: Named actions (e.g., `export_report`, `refresh_data`) defined in the catalog alongside components, giving AI a typed vocabulary for triggering side effects
- **`catalog.prompt()`**: Generates a system prompt from the catalog for use with any LLM — no manual schema documentation required

### Multi-Platform Renderers

- **`@json-render/react`**: React renderer with `defineRegistry` and `<Renderer>` component; supports flat spec format
- **`@json-render/vue`**: Vue 3 renderer with composables and `<Renderer>` component
- **`@json-render/shadcn`**: 39 pre-built shadcn/ui components (Radix UI + Tailwind CSS) ready to use with the React renderer
- **`@json-render/react-native`**: React Native renderer with 25+ standard mobile components included via `standardComponentDefinitions`
- **`@json-render/remotion`**: Remotion video renderer with timeline spec format (composition, tracks, clips, audio)
- **`@json-render/react-pdf`**: React PDF renderer; `renderToBuffer` converts spec to PDF bytes

### Streaming

- **`createSpecStreamCompiler`** in `@json-render/core`: Processes LLM output chunks incrementally, emitting JSON patches as each element resolves
- **Progressive render**: Pass partial `result` to `<Renderer>` on each `push()` to update UI before the full spec arrives
- **Patch-based updates**: `newPatches` from `compiler.push(chunk)` enables targeted DOM updates rather than full re-renders

### Expression System (Dynamic Props)

- **`{ "$state": "/path" }`**: Reads a value from the state model at a JSON Pointer path
- **`{ "$cond": condition, "$then": value, "$else": value }`**: Conditional prop resolution evaluated at render time
- **`{ "$template": "Hello, ${/user/name}!" }`**: String interpolation with state values
- **`{ "$computed": "fn", "args": {...} }`**: Calls a registered function with resolved args
- **`{ "$bindState": "/path" }`**: Two-way binding — reads from and writes to state path

### Conditional Visibility and State Watchers

- **`visible` field**: Array of conditions (using `$state` references, optional `not` flag) controlling element visibility
- **`watch` field**: Map of state paths to action triggers; fires when watched value changes, not on initial render — enables reactive side effects without component code

### State Management Adapters

- **`StateStore` abstraction**: Platform-agnostic interface for reading/writing state
- **Adapters**: `@json-render/redux`, `@json-render/zustand`, `@json-render/jotai`, `@json-render/xstate` — plug any existing store into the renderer
- **Built-in `setState` action**: Standard action available in all renderers for updating state paths from component interactions

### Monorepo and Tooling

- **Turborepo** build orchestration across 15+ packages
- **Changesets** for coordinated versioning and changelogs across packages
- **pnpm workspaces** for dependency management
- **Vitest** for testing
- **tsup** for TypeScript builds with ESM + CJS dual output

---

## Technical Architecture

### Spec Format (Flat Element Map)

<eg>
Spec
  root: "card-1"                    -- entry point element ID
  elements:
    "card-1":
      type: "Card"                   -- matches a catalog component name
      props: { title: "Hello" }      -- validated against Zod schema
      children: ["button-1"]         -- ordered list of child element IDs
    "button-1":
      type: "Button"
      props: { label: "Click me" }
      children: []
      visible: [{ "$state": "/form/active" }]   -- optional visibility
      watch: { "/form/tab": { action: "load" } } -- optional watchers
</eg>

### System Layers

<eg>
AI Layer
  └── LLM generates JSON spec constrained by catalog.prompt() system prompt
        |
        | JSON chunks (streaming)
        |
Compilation Layer
  └── createSpecStreamCompiler() processes chunks -> emits patches + partial result
        |
        | Zod-validated Spec object (partial or complete)
        |
Render Layer
  ├── <Renderer spec={spec} registry={registry} /> (React / Vue)
  ├── State model (via StateStore adapter: Redux, Zustand, Jotai, XState)
  ├── Expression evaluator ($state, $cond, $template, $computed)
  └── Event emitter (emit("press") -> action handler)
        |
Platform Layer
  ├── React DOM (web via @json-render/react)
  ├── React Native (mobile via @json-render/react-native)
  ├── Remotion (video via @json-render/remotion)
  └── React PDF (documents via @json-render/react-pdf)
</eg>

### Package Dependency Graph

<eg>
@json-render/core           -- shared: schemas, catalog, prompt gen, SpecStream
    ^
    |--- @json-render/react          -- React renderer
    |--- @json-render/vue            -- Vue 3 renderer
    |--- @json-render/react-native   -- React Native renderer
    |--- @json-render/remotion       -- Remotion video renderer
    |--- @json-render/react-pdf      -- React PDF renderer
    |--- @json-render/redux          -- StateStore adapter
    |--- @json-render/zustand        -- StateStore adapter
    |--- @json-render/jotai          -- StateStore adapter
    |--- @json-render/xstate         -- StateStore adapter

@json-render/shadcn         -- pre-built components (depends on @json-render/react)
</eg>

### Monorepo Structure

<eg>
vercel-labs/json-render/
  packages/          -- library packages (core, react, vue, shadcn, ...)
  apps/              -- documentation/playground web app
  examples/          -- runnable examples (chat, vue, vite-renderers, react-native)
  tests/             -- e2e tests (uses Vercel AI SDK + AI Gateway for live tests)
  skills/            -- Claude Code skills for agents working in this repo
  opensrc/           -- source snapshots of key dependencies for agent reference
  turbo.json         -- Turborepo pipeline configuration
  pnpm-workspace.yaml
</eg>

---

## Installation & Usage

```bash
# Core + React renderer
npm install @json-render/core @json-render/react

# With pre-built shadcn/ui components (39 components)
npm install @json-render/shadcn

# React Native
npm install @json-render/core @json-render/react-native

# Video (Remotion)
npm install @json-render/core @json-render/remotion

# PDF
npm install @json-render/core @json-render/react-pdf

# Vue
npm install @json-render/core @json-render/vue
```

```typescript
// 1. Define catalog (shared across platforms)
import { defineCatalog } from "@json-render/core";
import { schema } from "@json-render/react/schema";
import { z } from "zod";

const catalog = defineCatalog(schema, {
  components: {
    Card: {
      props: z.object({ title: z.string() }),
      description: "A card container",
    },
    Button: {
      props: z.object({ label: z.string(), action: z.string() }),
      description: "Clickable button",
    },
  },
  actions: {
    submit_form: { description: "Submit the form data" },
  },
});
```

```tsx
// 2. Register implementations and render
import { defineRegistry, Renderer } from "@json-render/react";

const { registry } = defineRegistry(catalog, {
  components: {
    Card: ({ props, children }) => (
      <div className="card">
        <h3>{props.title}</h3>
        {children}
      </div>
    ),
    Button: ({ props, emit }) => (
      <button onClick={() => emit("press")}>{props.label}</button>
    ),
  },
});

function AIDashboard({ spec }) {
  return <Renderer spec={spec} registry={registry} />;
}
```

```typescript
// 3. Streaming from an LLM
import { createSpecStreamCompiler } from "@json-render/core";

const compiler = createSpecStreamCompiler();

for await (const chunk of llmStream) {
  const { result, newPatches } = compiler.push(chunk);
  setSpec(result); // Update UI progressively
}
```

```typescript
// 4. Generate system prompt from catalog
const systemPrompt = catalog.prompt();
// Pass to LLM alongside user message to constrain output to catalog schema
```

---

## Relevance to Claude Code Development

### Applications

- **Generative UI for Claude-powered tools**: json-render provides a ready-made system for building AI-driven dashboards, reports, and interactive UIs where Claude generates the layout from a prompt — directly applicable to any Claude Code skill that needs a UI output layer.
- **Structured output pattern**: The catalog + Zod schema approach is a concrete implementation of constrained structured output from LLMs, relevant to any Claude skill that needs typed, validated JSON responses.
- **AI skill co-location**: The repository ships `skills/` directory with Claude Code skills for agents working in the repo — a direct model for how Claude Code skills can be co-located with the codebase they support.
- **Cross-platform from shared spec**: The single-spec, multiple-renderer architecture is a pattern applicable to Claude Code output that needs to target multiple surfaces (web, mobile, PDF, video) from one definition.

### Patterns Worth Adopting

- **Catalog-constrained generation**: Defining a schema of allowed outputs before prompting the LLM prevents hallucinated component names and invalid structures — directly applicable to any Claude skill that generates structured content.
- **`catalog.prompt()` auto-generation**: Deriving the system prompt from the schema definition (rather than hand-writing it) keeps prompt and validation in sync — a pattern worth adopting in skills that use Zod or similar for structured output.
- **SpecStream incremental compilation**: Processing LLM output chunk-by-chunk with patch emission is a clean streaming pattern applicable to any tool that streams structured JSON from Claude.
- **`opensrc/` source snapshots**: Co-locating dependency source code for agent reference (via `npx opensrc`) improves agent accuracy when working with unfamiliar library internals — a pattern applicable to Claude Code skill documentation.
- **`AGENTS.md` as agent instructions**: The repository uses `AGENTS.md` to give AI coding agents project-specific rules (package management, code style, AI SDK usage) — matches the `CLAUDE.md` pattern used in this repository.

### Integration Opportunities

- **Claude as the LLM backend**: `catalog.prompt()` generates a system prompt compatible with any LLM including Claude via Anthropic API — plug directly into Claude-powered backend for structured UI generation.
- **MCP tool output rendering**: A json-render catalog could define the output schema for MCP tool results, allowing Claude to generate structured visual responses rendered by a json-render frontend.
- **Skill output layer**: Claude Code skills that produce reports, dashboards, or structured data outputs could use json-render as the rendering target instead of markdown — enabling richer interactive output.
- **Agent-generated forms and workflows**: json-render's action system (named actions + `setState`) maps cleanly onto Claude tool use — AI selects actions from a catalog, which corresponds directly to Claude function calling.
- **React Native / mobile for Claude Code**: The `@json-render/react-native` package enables Claude-driven mobile UIs, relevant if Claude Code needs a mobile companion app surface.

---

## References

- [GitHub Repository](https://github.com/vercel-labs/json-render) (accessed 2026-02-26)
- [Documentation and Playground](https://json-render.dev) (accessed 2026-02-26)
- [@json-render/core on npm](https://www.npmjs.com/package/@json-render/core) (accessed 2026-02-26)
- [@json-render/react on npm](https://www.npmjs.com/package/@json-render/react) (accessed 2026-02-26)
- [GitHub API — repo metadata](https://api.github.com/repos/vercel-labs/json-render) (accessed 2026-02-26)
- [GitHub API — releases](https://api.github.com/repos/vercel-labs/json-render/releases) (accessed 2026-02-26)
- [npm downloads API — @json-render/core](https://api.npmjs.org/downloads/point/last-month/@json-render/core) (accessed 2026-02-26)
- [npm downloads API — @json-render/react](https://api.npmjs.org/downloads/point/last-month/@json-render/react) (accessed 2026-02-26)

**Research Method**: GitHub API (stars, forks, issues, contributors, releases, file contents), npm downloads API, documentation site fetch, README and AGENTS.md source analysis.

---
