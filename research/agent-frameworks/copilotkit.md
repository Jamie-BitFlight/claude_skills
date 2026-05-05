# CopilotKit

**Research Date**: 2026-02-23
**Source URL**: <https://copilotkit.ai/>
**GitHub Repository**: <https://github.com/CopilotKit/CopilotKit>
**npm**: <https://www.npmjs.com/package/@copilotkit/runtime>
**Version at Research**: v1.51.4 (released 2026-02-17)
**License**: MIT
**Docs**: <https://docs.copilotkit.ai>

---

## Overview

CopilotKit is an open-source TypeScript/React framework for building AI copilots, agentic frontends, and generative UIs directly inside web applications. It provides React components and hooks that connect frontend state bi-directionally with AI agents and LLMs, enabling agents to read and mutate application state in real time. The framework supports the AG-UI protocol, making it interoperable with LangChain, CrewAI, Google ADK, Microsoft Agent Framework, and other agent backends.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI chat is isolated in sidebars, disconnected from app state | Bi-directional state sync lets agents read and mutate live application state |
| Building agent UI from scratch is repetitive | Prebuilt CopilotSidebar, CopilotPopup, and CopilotChat React components |
| Vendor lock-in to specific LLMs or agent frameworks | AG-UI protocol provides framework-agnostic backend integration |
| Agents lack awareness of frontend context | `useCopilotReadable` exposes app state and context to the agent |
| Agents can't trigger application actions | `useCopilotAction` lets agents call frontend functions and mutations |
| No standardized human-in-the-loop for React apps | Built-in approval checkpoints and confirmation flows |
| Generative UI requires custom rendering logic | `useCopilotAction` supports rendering React components mid-stream |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 28,930 | 2026-02-23 |
| GitHub Forks | 3,757 | 2026-02-23 |
| Open Issues | 569 | 2026-02-23 |
| Contributors | ~151 | 2026-02-23 |
| @copilotkit/react-core (monthly DL) | 434,617 | 2026-02-23 |
| @copilotkit/react-ui (monthly DL) | 408,184 | 2026-02-23 |
| @copilotkit/runtime (monthly DL) | 317,370 | 2026-02-23 |
| Latest Release | v1.51.4 | 2026-02-17 |
| Primary Language | TypeScript | 2026-02-23 |

---

## Key Features

### React UI Components

- **CopilotSidebar**: Drop-in chat sidebar with streaming, tool call rendering, and agent action display
- **CopilotPopup**: Floating chat popup for non-intrusive agent interactions
- **CopilotChat**: Embeddable chat panel for custom layout integration
- **Headless hooks**: `useCopilotChat`, `useCopilotKit` for fully custom UI implementations

### Bi-Directional State Integration

- **`useCopilotReadable`**: Expose arbitrary application state and context to the agent as readable context
- **`useCopilotAction`**: Register frontend functions the agent can invoke to mutate state or trigger UI events
- **`useCopilotAdditionalInstructions`**: Dynamically append instructions to the agent based on current app context
- **Real-time streaming**: Agent responses and actions stream directly into the UI

### Generative UI

- **Render components from actions**: `useCopilotAction` can return React components rendered inline in the chat
- **Mixed controlled/generative UI**: Developer-driven and AI-driven UI coexist in the same flow
- **Streaming render**: Components render progressively as the agent streams output

### Agentic Capabilities

- **Human-in-the-loop**: Approval checkpoints and confirmation dialogs before agent actions execute
- **Shared state**: Persistent, synchronized state between agent and application across turns
- **Long-lived workflows**: Support for multi-step agentic tasks that span multiple interactions
- **Agentic intents**: Agent expresses intent to the frontend before executing mutations

### AG-UI Protocol

- **Framework agnostic**: Connect to LangChain, CrewAI, Google ADK, Microsoft Agent Framework, and more
- **LLM agnostic**: Works with OpenAI, Anthropic, Google, and other model providers via the runtime
- **Standardized event stream**: Structured event protocol between frontend and agent backend
- **Open specification**: Protocol is open and extensible for custom agent frameworks

### Backend Runtime (`@copilotkit/runtime`)

- **CopilotRuntime**: Express/Next.js middleware handling agent communication and LLM calls
- **Multi-LLM support**: OpenAI, Anthropic, Google Gemini, Groq, and others
- **Tool execution**: Manages tool call routing between frontend and backend
- **Self-hosted or cloud**: Deploy runtime on own infrastructure or use CopilotKit cloud

---

## Technical Architecture

### Three-Layer Stack

<eg>
Frontend Layer
  ├── React components (CopilotSidebar, CopilotPopup, CopilotChat)
  ├── Hooks (useCopilotReadable, useCopilotAction, useCopilotChat)
  └── State management (bi-directional sync with agent)
        |
        | HTTP / AG-UI event stream
        |
Transport Layer
  └── AG-UI protocol (structured event stream)
        |
Backend Layer
  ├── CopilotRuntime (Express/Next.js middleware)
  ├── LLM adapters (OpenAI, Anthropic, Google, etc.)
  └── Agent framework integration (LangChain, CrewAI, etc.)
</eg>

### Data Flow

1. App state exposed to agent via `useCopilotReadable` hooks (injected as context)
2. User message sent to CopilotRuntime via AG-UI event stream
3. Runtime forwards context + message to LLM or agent framework
4. Agent streams response and/or tool calls back via event stream
5. Frontend receives tool call → executes registered `useCopilotAction` handler
6. Action handler can mutate state, render React components, or request human approval
7. Updated state is re-exposed to agent for subsequent turns

### Package Structure

| Package | Purpose |
|---------|---------|
| `@copilotkit/react-core` | Hooks and context provider |
| `@copilotkit/react-ui` | Prebuilt chat components |
| `@copilotkit/runtime` | Backend middleware |
| `@copilotkit/runtime-client-gql` | GraphQL transport client |

---

## Installation & Usage

```bash
# Install frontend packages
npm install @copilotkit/react-core @copilotkit/react-ui

# Install backend runtime
npm install @copilotkit/runtime
```

```tsx
// pages/_app.tsx — Wrap app with CopilotKit provider
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";

export default function App({ Component, pageProps }) {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit">
      <CopilotSidebar>
        <Component {...pageProps} />
      </CopilotSidebar>
    </CopilotKit>
  );
}
```

```tsx
// In a component — expose state and register actions
import { useCopilotReadable, useCopilotAction } from "@copilotkit/react-core";

function TodoList({ todos, setTodos }) {
  // Make todos visible to the agent
  useCopilotReadable({
    description: "The current list of todos",
    value: todos,
  });

  // Let the agent add todos
  useCopilotAction({
    name: "addTodo",
    description: "Add a new todo item",
    parameters: [{ name: "text", type: "string", description: "Todo text" }],
    handler: ({ text }) => setTodos((prev) => [...prev, { text, done: false }]),
  });

  return <ul>{todos.map(t => <li key={t.text}>{t.text}</li>)}</ul>;
}
```

```ts
// pages/api/copilotkit.ts — Backend runtime
import { CopilotRuntime, OpenAIAdapter, copilotRuntimeNextJSAppRouterEndpoint } from "@copilotkit/runtime";
import OpenAI from "openai";

const openai = new OpenAI();
const runtime = new CopilotRuntime();

export const POST = copilotRuntimeNextJSAppRouterEndpoint({
  runtime,
  serviceAdapter: new OpenAIAdapter({ openai }),
  endpoint: "/api/copilotkit",
});
```

---

## Relevance to Claude Code Development

### Applications

- **Agentic frontend patterns**: CopilotKit's bi-directional state model shows how agents can be deeply integrated into UIs rather than isolated in chat boxes — applicable to building Claude Code web UIs.
- **Generative UI reference**: The `useCopilotAction` render pattern for streaming React components is a strong reference for any project building AI-driven frontend experiences.
- **AG-UI protocol adoption**: The AG-UI open protocol provides a standard interface for connecting Claude-based agent backends to React frontends.

### Patterns Worth Adopting

- **Readable context injection**: `useCopilotReadable` pattern of declaratively exposing component state as agent context is clean and composable — could be adapted for CLI tool context injection.
- **Action registry pattern**: Registering named, typed actions that agents can invoke mirrors Claude Code's tool use pattern and validates the approach.
- **Human-in-the-loop checkpoints**: Explicit approval flows before agent mutations is a safety pattern applicable to any agentic system.
- **Layered architecture**: Clean separation of UI components, hooks, transport, and runtime reduces coupling and eases testing.

### Integration Opportunities

- **Claude backend adapter**: CopilotKit's `CopilotRuntime` supports Anthropic — Claude models can power CopilotKit-based UIs directly.
- **AG-UI + Claude Code agents**: Claude Code agents could expose AG-UI-compatible event streams to enable frontend integration with CopilotKit apps.
- **Skill showcase UI**: CopilotKit could serve as the frontend framework for a web UI demonstrating Claude Code skills and agents.
- **MCP bridge**: A CopilotKit backend adapter connecting to MCP servers could expose MCP tools to React frontends via CopilotKit's action system.

### Comparison with Other Frameworks

| Aspect | CopilotKit | LangChain | CrewAI |
|--------|-----------|-----------|--------|
| Primary target | React/frontend | Python backend | Python multi-agent |
| UI components | Built-in | None | None |
| State sync | Bi-directional | N/A | N/A |
| Protocol | AG-UI | Custom | Custom |
| Language | TypeScript | Python | Python |
| Generative UI | First-class | Via integrations | Via integrations |

---

## References

- [Official Website](https://copilotkit.ai/) (accessed 2026-02-23)
- [GitHub Repository](https://github.com/CopilotKit/CopilotKit) (accessed 2026-02-23)
- [Official Documentation](https://docs.copilotkit.ai) (accessed 2026-02-23)
- [@copilotkit/runtime on npm](https://www.npmjs.com/package/@copilotkit/runtime) (accessed 2026-02-23)
- [@copilotkit/react-core on npm](https://www.npmjs.com/package/@copilotkit/react-core) (accessed 2026-02-23)
- [DeepWiki — CopilotKit Architecture](https://deepwiki.com/CopilotKit/CopilotKit) (accessed 2026-02-23)
- [LogRocket — Build agentic frontend applications with CopilotKit](https://blog.logrocket.com/build-agentic-frontend-applications-copilotkit/) (accessed 2026-02-23)

**Research Method**: Information gathered from GitHub API (stars, forks, issues, releases, contributors), npm downloads API, official documentation, and web search for architecture and feature details.

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-02-23 |
| Version at Verification | v1.51.4 |
| Next Review Recommended | 2026-05-23 |

**Review Triggers**:

- Major version release (v2.x)
- AG-UI protocol specification changes
- New agent framework integrations (beyond LangChain, CrewAI, Google ADK)
- GitHub stars milestone (30K, 35K)
- New generative UI patterns or components
- Breaking changes to `useCopilotAction` or `useCopilotReadable` API

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Cursor Cookbook](cursor-cookbook.md) | agent-frameworks | referenced by Cursor Cookbook (agent-frameworks) |
