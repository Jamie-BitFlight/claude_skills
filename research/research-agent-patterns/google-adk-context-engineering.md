---
title: "Architecting Efficient, Context-Aware Multi-Agent Frameworks for Production (Google ADK)"
research_date: "2026-02-23"
source_url: "https://developers.googleblog.com/architecting-efficient-context-aware-multi-agent-framework-for-production/"
github_url: "https://github.com/google/adk-python"
version_at_research: "v1.25.1"
license: "Apache-2.0"
last_verified: "2026-02-23"
version_at_verification: "v1.25.1"
next_review: "2026-05-23"
---

## Overview

Google's engineering blog post describes the context engineering architecture behind the **Agent Development Kit (ADK)**, an open-source Python framework for building production-grade multi-agent systems. The article introduces "context engineering" — treating context as a first-class system with its own architecture, lifecycle, and constraints — as the key discipline required to scale agents beyond prototypes. ADK implements this discipline through a tiered storage model, a compiler-style pipeline, and explicit multi-agent handoff semantics.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Naive "append everything" context strategy causes cost/latency spirals | Tiered storage model separates durable state from per-call working context |
| Signal degradation ("lost in the middle") from irrelevant context | Explicit processor pipeline filters and compacts before reaching the model |
| Fixed context windows overflow for long-running agents | Async context compaction summarizes older events and prunes raw history |
| Context coupling to model API format prevents portability | Session stores typed Events; working context is a derived, model-agnostic view |
| Large data payloads permanently bloat conversation history | Artifact handle pattern externalizes large objects; loaded on demand only |
| Sub-agents inherit full ancestor history causing context explosion | Scoped handoffs via `include_contents` knob; sub-agents see minimum needed |
| Role ambiguity when agent A's outputs look like agent B's own history | Narrative casting and action attribution during handoff reframe prior turns |
| Memory-less agents repeat past mistakes across sessions | Long-term `MemoryService` with reactive and proactive recall patterns |
| Cache invalidation from unstable context prefixes | `static_instruction` primitive guarantees immutable prefix for prefix caching |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 17,915 | 2026-02-23 |
| GitHub Forks | 2,958 | 2026-02-23 |
| Latest Release | v1.25.1 | 2026-02-18 |
| License | Apache-2.0 | 2026-02-23 |
| Language | Python | 2026-02-23 |
| Repository Created | April 2025 | 2026-02-23 |

---

## Key Features

### 1. Tiered Context Model

ADK organizes context into four distinct layers, each with a specific responsibility:

- **Working Context** — ephemeral per-call prompt: system instructions, selected history, tool outputs, memory results, artifact references
- **Session** — durable log of all interactions as strongly-typed `Event` objects (user messages, agent replies, tool calls, tool results, control signals, errors)
- **Memory** — long-lived, searchable knowledge persisting across sessions (user preferences, past decisions, domain facts) via `MemoryService`
- **Artifacts** — large binary or text objects (files, CSVs, PDFs) stored by name/version via `ArtifactService`; never pasted into the prompt by default

### 2. Context as a Compiled View

Core design thesis: context is not a mutable string buffer but a **compiled view over stateful storage**:

- Sessions and Memory are the *sources* — full structured state
- LLM Flows with ordered Processors are the *compiler pipeline*
- Working Context is the *compiled output* — ephemeral, configurable, model-agnostic

This separation allows storage schemas and prompt formats to evolve independently.

### 3. LLM Flow Processor Pipeline

Every LLM-backed agent uses a named, ordered processor list to build Working Context:

- **`instructions` processor** — injects system instructions and agent identity
- **`contents` processor** — transforms Session Events into model-ready history (select → transform → inject)
- **`memory` processor** — optionally attaches retrieved memory snippets
- **`artifacts` processor** — injects lightweight artifact references (not raw data)
- Custom processors can be inserted for filtering, compaction, caching, and routing

### 4. Context Compaction and Filtering

- **Compaction**: When a configurable invocation threshold is reached, an async process uses an LLM to summarize older events over a sliding window and writes the summary back as a new `compaction` Event. Raw events are then pruned/de-prioritized.
- **Filtering**: Deterministic rule-based plugins that globally drop or trim context before it reaches the model.
- Benefits: sessions remain physically manageable; the `contents` processor works over already-compacted history; compaction strategies are tunable without touching agent code.

### 5. Context Caching (Prefix Caching)

- ADK's storage/view separation creates natural stable prefixes (system instructions, agent identity, long-lived summaries) and variable suffixes (latest user turn, new tool outputs).
- `static_instruction` primitive guarantees immutability for system prompts, keeping cache prefixes valid across invocations.
- Processor ordering can be designed explicitly for cache-friendliness.

### 6. Artifact Handle Pattern

- Large payloads live in `ArtifactService`, not the prompt.
- Agents see only a lightweight reference (name + summary) by default via the request processor.
- `LoadArtifactsTool` loads raw data into Working Context on demand; data is offloaded after the call (ephemeral expansion).
- Turns "5MB of noise in every prompt" into a precise, on-demand resource.

### 7. Memory Service

- `MemoryService` ingests data from finished Sessions into a vector/keyword corpus.
- **Reactive recall**: Agent explicitly calls `load_memory_tool` when it recognizes a knowledge gap.
- **Proactive recall**: Pre-processor runs similarity search on latest user input and injects likely-relevant snippets via `preload_memory_tool` before model invocation.

### 8. Multi-Agent Context Scoping

Two interaction patterns:

- **Agents as Tools**: Caller treats sub-agent as a function — sub-agent sees only focused prompt and specific artifacts, no history.
- **Agent Transfer (Hierarchy)**: Full handoff; sub-agent inherits a *scoped* view of the Session and can drive the workflow.

Scoping is controlled by `include_contents` on the callee: `full` (default), `none` (new prompt only), or custom selection.

### 9. Narrative Casting for Agent Handoffs

When transferring control between agents, ADK actively reframes conversation context:

- Prior "Assistant" messages from the upstream agent are re-cast as narrative context (e.g., tagged as `[For context]: Agent B said...`) to prevent the new agent from misattributing those actions to itself.
- Tool calls from other agents are marked/summarized so the new agent acts on results without confusing execution with its own capabilities.

---

## Technical Architecture

<eg>
┌─────────────────────────────────────────────────────────────────┐
│                      ADK Context Architecture                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   STORAGE LAYER (durable)                                         │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│   │   Session    │  │    Memory    │  │      Artifacts       │  │
│   │  (Events[])  │  │  (vector/kw) │  │  (name+version blobs)│  │
│   └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│          │                 │                      │               │
│   COMPILATION LAYER (LLM Flow Processors)                         │
│          ▼                 ▼                      ▼               │
│   ┌─────────────────────────────────────────────────────────┐    │
│   │  instructions → contents → memory → artifacts → custom  │    │
│   │   (system)      (history)  (recall)  (refs)   (filter)  │    │
│   └──────────────────────────┬──────────────────────────────┘    │
│                               │                                   │
│   WORKING CONTEXT (ephemeral) ▼                                   │
│   ┌─────────────────────────────────────────────────────────┐    │
│   │  [Instructions] [Selected History] [Memory Snippets]    │    │
│   │  [Artifact Refs] [Tool Results] → LLM Invocation        │    │
│   └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│   MULTI-AGENT LAYER                                               │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │  Root Agent ──[scoped handoff]──► Sub-Agent              │   │
│   │  include_contents: full | none | custom                  │   │
│   │  Narrative casting prevents role misattribution          │   │
│   └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
</eg>

### Session Event Lifecycle

<eg>
User Input → Event(role=user)
     │
     ▼
Agent LLM Call → contents processor (select → transform → inject)
     │
     ▼
Tool Call → Event(type=tool_call)
     │
     ▼
Tool Result → Event(type=tool_result)
     │
     ▼
[Compaction threshold reached?]
     ├─ Yes → async LLM summary → Event(type=compaction) → prune raw events
     └─ No  → continue appending
</eg>

---

## Installation & Usage

```bash
pip install google-adk
# or
uv add google-adk
```

```python
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.artifacts import InMemoryArtifactService

# Agents use LLM Flows with ordered processors by default
agent = LlmAgent(
    model="gemini-2.0-flash",
    name="my_agent",
    description="A context-aware production agent",
    instruction="You are a helpful assistant.",
)

# Context compaction: configure threshold for automatic summarization
# Artifacts: use ArtifactService for large data, LoadArtifactsTool on demand
# Memory: MemoryService for cross-session knowledge with reactive/proactive recall
```

---

## Relevance to Claude Code Development

### Applications

- **Context budget management**: The tiered storage / compiled view pattern directly applies to Claude Code agent design — separate what is stored from what the model sees each turn.
- **Multi-agent handoff discipline**: The `include_contents` scoping and narrative casting principles apply to Claude Code Agent tool delegation; sub-agents should receive minimal, purpose-built context, not full ancestor history.
- **Artifact handle pattern**: Large files or tool outputs should be referenced by name and loaded on demand, not passed inline in every prompt. Directly applicable to skills that process large codebases or documents.
- **Processor pipeline design**: LLM Flows' ordered processor model mirrors how Claude Code skills chain prompt-building steps; explicit ordering enables testability and cache-friendliness.

### Patterns Worth Adopting

- **Static instructions for cache stability**: Keeping system prompts immutable across invocations (equivalent of `static_instruction`) maximizes prefix cache hits in Claude API calls.
- **Proactive memory recall pre-processor**: Before invoking Claude, run a similarity search against prior session summaries and inject relevant snippets — analogous to our skill's context pre-loading patterns.
- **Compaction strategy**: For long-running Claude Code sessions, periodically summarize older tool results and chat history into a compact summary event rather than appending indefinitely.
- **Narrative casting on handoff**: When chaining agents via Agent tool, reframe upstream agent outputs as context annotations (`[Context from previous agent]: ...`) rather than passing them as raw `assistant` role messages.
- **Scope by default**: New agent spawns in Claude Code should receive only the minimum context needed; additional context should require explicit tool calls or prompt arguments.

### Integration Opportunities

- **Research-curator skill**: Apply the artifact handle pattern — store large research documents as artifacts and load on demand rather than embedding in the prompt.
- **Orchestrating-swarms skill**: ADK's two interaction patterns (Agents as Tools vs. Agent Transfer) map directly to Claude Code's Agent tool invocation vs. full agent handoff; document which to use when.
- **Session historian skill**: Implement proactive recall by running similarity search on prior session summaries before generating responses.
- **Context engineering guide**: Create a new skill or reference doc documenting Claude Code–specific context engineering patterns derived from ADK's architecture.

### Competitive Analysis

| Aspect | Google ADK | LangGraph | AutoGen |
|--------|-----------|-----------|---------|
| Context model | Tiered (Session/Memory/Artifact/Working) | Graph state dict | Conversation history list |
| Compilation | Explicit processor pipeline | Node functions | Message transformation hooks |
| Compaction | Built-in async LLM summarization | Manual | Manual |
| Multi-agent scoping | `include_contents` knob | Graph edge data | GroupChat manager |
| Handoff reframing | Narrative casting built-in | Manual | Manual |
| Prefix caching | `static_instruction` primitive | Manual | Not documented |
| License | Apache-2.0 | MIT | CC-BY-4.0 |

---

## References

- [Architecting Efficient, Context-Aware Multi-Agent Frameworks for Production](https://developers.googleblog.com/architecting-efficient-context-aware-multi-agent-framework-for-production/) — Google Developers Blog (accessed 2026-02-23)
- [google/adk-python — GitHub Repository](https://github.com/google/adk-python) (accessed 2026-02-23)
- [ADK Documentation](https://google.github.io/adk-docs/) (accessed 2026-02-23)
- [Google ADK in AI Agents Frameworks Benchmark](./../../agent-frameworks/ai-agents-frameworks.md) — existing research entry

---
