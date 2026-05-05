---
title: Pi Monorepo
description: TypeScript toolkit for building AI agents and managing LLM deployments with unified APIs, coding agent CLI, TUI/web UI libraries, and Slack bot integration
category: agent-frameworks
resource_url: https://github.com/badlogic/pi-mono
resource_author: Mario Zechner (@badlogic)
license: MIT
language: TypeScript
last_accessed: 2026-03-14
github_stars: 23805
github_forks: 2510
current_version: 0.58.1 (released 2026-03-14)
---

# Pi Monorepo: Agent Framework and LLM Toolkit

## Identity and Metadata

**Official Name**: Pi Monorepo

**Repository**: <https://github.com/badlogic/pi-mono>

**Author**: Mario Zechner (@badlogic)

**License**: MIT (extracted from LICENSE file in repo, 2026-03-14)

**Language**: TypeScript

**Package Namespace**: @mariozechner/pi-*

**Official Domain**: <https://pi.dev> (graciously donated by exe.dev)

**Latest Version**: 0.58.1 (released 2026-03-14T11:41:25Z)

**Repository Statistics** (as of 2026-03-14):
- **GitHub Stars**: 23,805 (extracted via GitHub REST API)
- **Forks**: 2,510
- **Created**: 2025-08-09T14:03:50Z
- **Last Pushed**: 2026-03-14T15:35:06Z

**Community**: Discord community at <https://discord.com/invite/3cU7Bz4UPx>

---

## Summary

Pi is a comprehensive TypeScript monorepo providing tools for building AI agents and managing LLM deployments. It exports seven npm packages with a unified multi-provider LLM API, agent runtime with tool calling, interactive coding agent CLI, TUI framework, web UI components, Slack bot integration, and vLLM pod management. The framework emphasizes minimal defaults with extensibility through prompt templates, skills, extensions, and themes, designed for workflows that require adaptation over prescriptive structure.

---

## Architecture

The monorepo is organized as a TypeScript workspace with seven interdependent packages:

### Core Layers

**Layer 1 — LLM Abstraction**: `@mariozechner/pi-ai` provides "a unified multi-provider LLM API with automatic model discovery, provider configuration, token and cost tracking, and simple context persistence and hand-off to other models mid-session" (extracted from package README, 2026-03-14). This layer handles:
- Multi-provider support (OpenAI, Anthropic, Google, Vertex AI, Mistral, Groq, Cerebras, xAI, OpenRouter, Azure OpenAI, and others) with unified interface
- Tool calling (function calling) requirement for agentic workflows — only models supporting tool calls are included
- Automatic model discovery and provider credential detection
- Token tracking and cost estimation
- Context serialization for cross-provider handoffs mid-session

**Layer 2 — Agent Runtime**: `@mariozechner/pi-agent-core` implements "a stateful agent with tool execution and event streaming. Built on @mariozechner/pi-ai" (extracted from package README, 2026-03-14). Core concepts:
- `AgentMessage` type supporting standard LLM messages (user, assistant, toolResult) plus custom app-specific message types via declaration merging
- Message flow: `AgentMessage[]` → `transformContext()` → `convertToLlm()` → `Message[]` → LLM
- Event streaming for UI updates with `message_update` events containing assistant message events (text_delta, tool_call, thinking, etc.)
- State management for system prompt, model selection, message history

**Layer 3 — User Interfaces**:
- **TUI Framework** (`@mariozechner/pi-tui`): "Minimal terminal UI framework with differential rendering and synchronized output for flicker-free interactive CLI applications" (extracted from README). Features:
  - Three-strategy differential rendering updating only changed content
  - Atomic screen updates using CSI 2026 for no flicker
  - Bracketed paste mode for large pastes
  - Component-based with built-in Text, Input, Editor, Markdown, Loader, SelectList, Image, Box, Container components
  - Theme support for customizable styling
  - Inline image rendering (Kitty/iTerm2 protocols)
  - Autocomplete for file paths and slash commands

- **Web UI** (`@mariozechner/pi-web-ui`): Reusable web components for chat interfaces built on mini-lit web components and Tailwind CSS v4. Includes chat UI, streaming, tool execution panels, artifact rendering (HTML/SVG/Markdown), document extraction from PDFs/DOCX/XLSX/PPTX, IndexedDB-backed storage, and CORS proxy handling.

**Layer 4 — Applications**:
- **Coding Agent CLI** (`@mariozechner/pi-coding-agent`): "Interactive coding harness. Adapt pi to your workflows, not the other way around, without having to fork and modify pi internals" (extracted from README). Ships with four built-in tools: `read`, `write`, `edit`, `bash`. Extends via TypeScript extensions, skills, prompt templates, themes, and Pi Packages. Supports interactive mode, print/JSON output, RPC for process integration, and SDK embedding.

- **Slack Bot** (`@mariozechner/pi-mom`): "Master Of Mischief" — Slack bot powered by LLM with bash execution, file read/write, self-managing tool installation, skill programming, and credential configuration. Operates in Docker sandbox (recommended) or host mode with persistent workspace.

- **vLLM Pod Manager** (`@mariozechner/pi-pods`): "Deploy and manage LLMs on GPU pods with automatic vLLM configuration for agentic workloads" (extracted from README). Supports DataCrunch, RunPod, Vast.ai, and other GPU providers with automatic vLLM setup, multi-model GPU allocation, OpenAI-compatible endpoints, and interactive agent testing.

### Dependency Graph

```
@mariozechner/pi-ai (LLM abstraction)
    ↓
@mariozechner/pi-agent-core (Agent runtime)
    ↓
┌─────────────────┬────────────────┬────────────┐
│                 │                │            │
▼                 ▼                ▼            ▼
pi-tui      pi-coding-agent   pi-web-ui    pi-mom
            (uses agent)       (uses agent)  (uses agent + ai)

pi-pods (standalone — uses ai only)
```

---

## Features

### 1. Multi-Provider LLM API (`pi-ai`)

- **Provider Support**: "OpenAI, Azure OpenAI (Responses), OpenAI Codex (OAuth), Anthropic, Google, Vertex AI, Mistral, Groq, Cerebras, xAI, OpenRouter" (extracted from pi-ai README table, 2026-03-14)
- **Tool Calling**: Unified tool definition and invocation across providers
- **Streaming Support**: Event-based streaming with partial JSON for streaming tool calls
- **Thinking/Reasoning**: Unified interface for provider-specific thinking capabilities (claude-3.5-sonnet, deepseek-r1, etc.)
- **Image Input**: Support for image attachments across providers
- **OAuth Providers**: Vertex AI and OpenAI Codex support OAuth flows; includes CLI login
- **Context Persistence**: Serializable context for hand-offs between models mid-session

### 2. Agent Runtime (`pi-agent-core`)

- **Event-Driven Architecture**: Agents emit structured events (message_update, assistant_message_created, tool_result_added, thinking_delta) for UI integration
- **Custom Message Types**: Agents support standard LLM messages plus app-specific custom types via TypeScript declaration merging
- **Tool Execution**: Built-in tool execution with validation and result streaming
- **Message Transformation**: `transformContext()` for pruning/injecting external context before LLM calls; `convertToLlm()` for filtering UI-only messages before API submission

### 3. Coding Agent CLI (`pi-coding-agent`)

**Core Capabilities**:
- Four built-in tools: `read`, `write`, `edit`, `bash`
- Interactive, JSON, print, and RPC modes
- Session branching and history compaction
- File context extraction via `.pi` config directory

**Extensibility**:
- **Prompt Templates**: Customizable system prompts
- **Skills**: Reusable, parameterizable tool-like functions
- **Extensions**: TypeScript hooks for augmenting agent behavior
- **Themes**: UI styling and color schemes
- **Pi Packages**: Shareable npm packages bundling templates, skills, extensions, themes

**Session Management**:
- Branching: Create alternate conversation branches
- Compaction: Trim old messages while preserving context
- Context Files: `.pi` directory for agent configuration, workspace state, settings

### 4. TUI Framework (`pi-tui`)

- **Differential Rendering**: Three-strategy system (full redraw, partial updates, CSI 2026 atomic writes)
- **Flicker-Free**: Synchronized output using CSI 2026 escape sequences
- **Component System**: Composable components with simple render() method
- **Built-in Components**: Text, TruncatedText, Input, Editor, Markdown, Loader, SelectList, SettingsList, Spacer, Image, Box, Container
- **Theme Support**: Components accept theme interfaces for styling
- **Inline Images**: Kitty and iTerm2 graphics protocol support
- **Terminal Paste**: Bracketed paste mode for large multi-line inputs
- **Autocomplete**: File path and slash command completion

### 5. Web UI Components (`pi-web-ui`)

- **Chat Interface**: Complete UI with message history, streaming, and tool panels
- **Artifacts**: Interactive rendering of HTML, SVG, Markdown with sandboxed execution
- **Document Tools**: JavaScript REPL, PDF/DOCX/XLSX/PPTX extraction with text preview
- **Storage**: IndexedDB-backed persistent storage for sessions, API keys, settings
- **CORS Proxy**: Automatic proxy for browser environments
- **Provider Flexibility**: Built-in support for Ollama, LM Studio, vLLM, OpenAI-compatible APIs

### 6. Slack Bot (`pi-mom`)

- **Self-Managing**: Automatically installs tools (apk, npm), writes scripts, configures credentials
- **Bash Execution**: Full shell access for commands, automation, workflows
- **File Operations**: Read/write with persistent workspace
- **Skills**: Creates workflow-specific CLI tools (custom commands)
- **Docker Sandbox**: Runs in isolated container (recommended) or host mode
- **Thread Management**: Main messages clean, verbose details in threads
- **Working Memory**: Context and custom tools persist across sessions

### 7. vLLM Pod Manager (`pi-pods`)

- **Provider Support**: DataCrunch, RunPod, Vast.ai, Prime Intellect, AWS EC2, any Ubuntu+NVIDIA machine
- **Automatic Setup**: vLLM installation and configuration with smart GPU allocation
- **Model Management**: Start, list, stop models with OpenAI-compatible API endpoints
- **Interactive Agent**: Test with file system tools on deployed models
- **Multi-Model**: Run multiple models on same pod with intelligent resource allocation

---

## Installation and Usage

### Quick Start

```bash
# Install coding agent globally
npm install -g @mariozechner/pi-coding-agent

# Authenticate with API key
export ANTHROPIC_API_KEY=sk-ant-...
pi

# Or use login command for interactive provider selection
pi
/login  # Select provider from UI
```

After startup, the model has four default tools: `read`, `write`, `edit`, `bash`. Extend with skills, templates, extensions, or packages.

### Development Setup

```bash
npm install          # Install all workspace dependencies
npm run build        # Build all packages
npm run check        # Lint, format, type check (requires build first)
./test.sh            # Run tests (skips LLM-dependent tests without API keys)
./pi-test.sh         # Run pi from sources (from repo root)
```

### As a Library

```typescript
import { Agent } from "@mariozechner/pi-agent-core";
import { getModel } from "@mariozechner/pi-ai";

const agent = new Agent({
  initialState: {
    systemPrompt: "You are a helpful assistant.",
    model: getModel("anthropic", "claude-sonnet-4-20250514"),
  },
});

agent.subscribe((event) => {
  if (event.type === "message_update" &&
      event.assistantMessageEvent.type === "text_delta") {
    process.stdout.write(event.assistantMessageEvent.delta);
  }
});

await agent.prompt("Hello!");
```

---

## Limitations and Constraints

### LLM API Scope

**Tool Calling Requirement**: "This library only includes models that support tool calling (function calling), as this is essential for agentic workflows" (extracted from pi-ai README, 2026-03-14). Models without tool support are excluded.

### Agent Scope

**Deliberate Exclusions**: "Pi ships with powerful defaults but skips features like sub agents and plan mode. Instead, you can ask pi to build what you want or install a third party pi package that matches your workflow" (extracted from pi-coding-agent README, 2026-03-14). The design prioritizes adaptability over feature completeness.

### TUI Framework

**Terminal Dependencies**: Inline image rendering requires terminal support for Kitty or iTerm2 graphics protocols; other terminals render text fallbacks.

**CSI 2026 Dependency**: Atomic screen updates via CSI 2026 require terminal support; older terminals fall back to standard ANSI rendering.

### Slack Bot

**Sandbox Mode Recommended**: "Mom is self-managing. She installs her own tools, programs CLI tools (aka 'skills') she can use to help with your workflows and tasks, configures credentials, and maintains her workspace autonomously" (extracted from pi-mom README, 2026-03-14). Host mode runs tools directly on the system; Docker sandbox (recommended) isolates execution but requires Docker availability.

### vLLM Pod Manager

**Provider-Specific Limitations**:
- **DataCrunch**: NFS volumes sharable within same region; best for shared model storage
- **RunPod**: Network volumes persist independently but cannot share between running pods simultaneously
- **Vast.ai**: Volumes locked to specific machine; no cross-pod sharing
- **Prime Intellect**: No persistent storage

(Extracted from pi-pods README pod management section, 2026-03-14)

### Releasing and Versioning

**Lockstep Versioning**: "All packages always share the same version number. Every release updates all packages together" (extracted from AGENTS.md development rules, 2026-03-14). Version semantics: patch for bug fixes and new features, minor for API breaking changes; no major releases.

---

## Relevance to Claude Code Development

**Direct Alignment**:

1. **Coding Agent Pattern**: Pi's coding agent architecture closely parallels Claude Code's agent-tool interaction model. The `read`, `write`, `edit`, `bash` tool set matches the core tool paradigm Claude Code uses, making pi-mono relevant for researching agent framework design, tool execution patterns, and session management.

2. **Agent Runtime Architecture**: The `pi-agent-core` design — separating message transformation, tool execution, and event streaming — offers patterns applicable to Claude Code's agent lifecycle and state management.

3. **TUI Framework for Interactive Agents**: The `pi-tui` differential rendering strategy and flicker-free synchronized output are directly applicable to terminal-based agent UIs. The bracketed paste mode and autocomplete patterns solve problems Claude Code agents encounter in interactive sessions.

4. **Multi-Provider LLM Abstraction**: The unified API across OpenAI, Anthropic, Google, etc., with provider credential detection and model discovery, demonstrates reusable patterns for Claude Code's multi-model orchestration.

5. **Extension System**: Pi's architecture for plugins (prompt templates, skills, extensions, themes, packages) provides a model for Claude Code skill extensibility and third-party integration.

6. **Session Persistence and Branching**: Session branching and message compaction strategies are applicable to Claude Code's context window management and long-running session handling.

**Development Challenges Referenced**:

- The AGENTS.md file documents collaborative multi-agent development on a monorepo with strict rules for preventing work collision — directly relevant to Claude Code's multi-agent orchestration patterns
- Changelog management per-package with shared versioning constraints mirrors challenges in CloudCode's cross-plugin dependency management

---

## Freshness Tracking

**Last Accessed**: 2026-03-14

**Next Review**: 2026-06-14 (3 months from access date)

### Confidence Levels by Section

| Section | Confidence | Notes |
|---------|-----------|-------|
| Identity/Metadata | high | GitHub API and local repo inspection; verified 2026-03-14 |
| Architecture | high | Read all seven package README files; local codebase inspection |
| Features | high | Extracted from package READMEs and official docs; current as of latest commit |
| Installation/Usage | high | Verified against README.md and package.json scripts |
| Limitations | medium | Sourced from README extracts; no exhaustive feature testing performed |
| Relevance | medium | Assessment based on architectural review; not validated through extended usage |

### Sources of Potential Drift

- **Version Pins**: Latest version 0.58.1 released 2026-03-14; future releases may change API surfaces, especially for agent-core, TUI, or web-ui packages
- **Provider List**: Supported LLM providers in pi-ai subject to addition/deprecation; review `packages/ai/src/types.ts` and stream.ts for current list
- **Feature Completeness**: Extensibility surface (prompt templates, skills, extensions, themes) documented minimally; inspect AGENTS.md development rules and package-level docs for current patterns

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Dify](../dify.md) | agent-frameworks | visual workflow builder with multi-provider LLM routing and tool integration; complements pi-mono's programmatic agent API with low-code canvas approach |
| [CopilotKit](../copilotkit.md) | agent-frameworks | TypeScript React framework for agent UI; addresses frontend state sync problem pi-mono solves server-side with pi-web-ui |
| [Micro-Agent](../micro-agent.md) | agent-frameworks | Python ReAct agent with MCP tool ecosystem; shares agent runtime architecture and token budget management patterns with pi-agent-core |
| [OpenFang](../openfang.md) | agent-frameworks | Rust agent OS with 27 LLM providers and 40 channel adapters; parallel architecture to pi-mono's multi-provider SDK approach |
| [Tersa](../tersa.md) | agent-frameworks | Visual node-based AI workflow with Vercel AI SDK multi-provider support; shares provider abstraction layer concept with pi-ai |
| [LiteAgents](../liteagents.md) | agent-frameworks | TypeScript multi-tool AI development toolkit with 11 specialized agents; shares extensibility and session management patterns with pi-coding-agent |
| [Everything Claude Code](../everything-claude-code.md) | agent-frameworks | Comprehensive agent harness toolkit; parallel toolkit ecosystem approach to pi-mono for agent development and orchestration |
| [Byobu](../../developer-tools/byobu.md) | developer-tools | terminal multiplexer wrapper with session persistence; complements pi-tui's differential rendering with terminal session management |
| [surf-cli](../../developer-tools/surf-cli.md) | developer-tools | agent-agnostic Chrome control via CLI; extends pi-coding-agent and pi-web-ui with browser automation capability |
| [Cursor Cookbook](cursor-cookbook.md) | agent-frameworks | TypeScript agent runtime with unified LLM API and CLI framework; shares multi-interface patterns (TUI, web, Slack) with Cookbook examples (bidirectional) |

---

## References

- **Official Repository**: <https://github.com/badlogic/pi-mono> (accessed 2026-03-14)
- **Official Website**: <https://pi.dev>
- **Discord Community**: <https://discord.com/invite/3cU7Bz4UPx>
- **GitHub API Metadata**: Queried via `curl https://api.github.com/repos/badlogic/pi-mono` (accessed 2026-03-14)
- **Package READMEs** (verified in cloned repo 2026-03-14):
  - `packages/ai/README.md` — LLM API documentation
  - `packages/agent/README.md` — Agent runtime documentation
  - `packages/coding-agent/README.md` — Coding agent CLI documentation
  - `packages/tui/README.md` — TUI framework documentation
  - `packages/web-ui/README.md` — Web UI components documentation
  - `packages/mom/README.md` — Slack bot documentation
  - `packages/pods/README.md` — vLLM pod manager documentation
- **Development Rules**: `AGENTS.md` (accessed 2026-03-14) — collaborative development patterns, changelog format, provider addition workflow, releasing procedures
- **Main README**: `README.md` (accessed 2026-03-14) — project overview, package table, development commands
- **Contributing Guide**: `CONTRIBUTING.md` (accessed 2026-03-14) — contribution requirements and approval gate
