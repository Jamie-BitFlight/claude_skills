# SlimContext

## Overview

**SlimContext** is a lightweight, model-agnostic TypeScript library for compressing chat history in AI assistants while preserving conversational context. It provides two compression strategies—token-aware trimming and AI-powered summarization—both operating under a "Bring Your Own Model" (BYOM) architecture with zero runtime dependencies in the core library.

**Repository**: <https://github.com/agentailor/slimcontext>
**Current Version**: 2.1.3 (released 2025-09-14)
**License**: MIT
**Language**: TypeScript
**Package Manager**: pnpm 10.14.0

---

## Problem Addressed

LLM-based chat applications face a fundamental constraint: context windows are finite. As conversations grow longer, token usage increases, raising operational costs and pushing against model limits. Naive solutions like dropping old messages lose important context; keeping everything is unsustainable.

SlimContext solves this by providing pluggable compression strategies that reduce token usage while retaining conversation semantics. The library preserves system instructions (which frame the assistant's behavior) and recent messages (which maintain conversational coherence), compressing only the middle historical portion that can be safely condensed without loss of user intent.

---

## Key Statistics

- **22 GitHub stars** (as of 2026-03-17)
- **0 forks** — early-stage project
- **1 open issue** — active maintenance
- **Repository age**: Created 2025-08-22; last activity 2025-09-14 (6 months old)
- **Downloads**: Distribution via npm; no public download metrics available
- **Topics**: ai, ai-agents, context-engineering, llms, memory

---

## Key Features

### Trimming Strategy

Token-based compression that removes oldest non-system messages when cumulative tokens exceed a configurable threshold.

**How it works**: Messages are estimated for token count using a built-in heuristic (message length ÷ 4, customizable). When total tokens exceed `maxModelTokens × thresholdPercent`, the oldest messages are dropped first—except system messages and a configurable tail of recent messages (`minRecentMessages`, default 2) which are always preserved. Trimming continues until token count falls below threshold.

**Configuration** (defaults shown):
```typescript
new TrimCompressor({
  maxModelTokens: 8192,        // model's context window
  thresholdPercent: 0.7,       // trigger compression at 70% of window
  minRecentMessages: 2,         // keep last 2 messages verbatim
  estimateTokens: (msg) => ... // optional custom token counter
})
```

**Strengths**: Simple, predictable, no API calls. **Tradeoff**: Older context is permanently lost.

### Summarization Strategy

AI-powered compression that condenses older conversation segments into a concise system message, preserving full semantic content.

**How it works**: When token usage exceeds threshold, the library extracts all messages before the preserved tail, formats them as a conversation transcript, sends them to a user-provided chat model with a structured summarization prompt, receives the summary, and injects it as a new system message before the preserved recent messages. The summary preserves facts, decisions, user goals, and constraints while omitting small talk.

**Configuration** (defaults shown):
```typescript
new SummarizeCompressor({
  model: yourChatModel,        // SlimContextChatModel instance (required)
  maxModelTokens: 8192,
  thresholdPercent: 0.7,
  minRecentMessages: 4,         // preserve more recent messages for summarization
  prompt: '...custom instructions...' // optional; defaults to library prompt
})
```

**Default summarization prompt includes**:
- Instruction to capture facts, decisions, goals, constraints
- Guidance to omit filler and small talk
- Example input/output format for clarity

**Strengths**: Lossless semantic compression; context is preserved in narrative form. **Tradeoff**: Requires additional API calls to summarization model; introduces latency.

### Framework Integration

**LangChain Adapter**: Provides seamless integration with LangChain chat models via `toSlimModel()` wrapper and one-call helper `compressLangChainHistory()`. Optional peer dependency (`@langchain/core >=0.3.71 <1.0`).

**Example** (LangChain integration):
```typescript
import { langchain } from 'slimcontext';
const lc = new ChatOpenAI({ model: 'gpt-4-mini', temperature: 0 });
const compact = await langchain.compressLangChainHistory(history, {
  strategy: 'summarize',
  llm: lc,
  maxModelTokens: 8192,
  thresholdPercent: 0.8,
  minRecentMessages: 4
});
```

---

## Technical Architecture

### Core Components

**Interfaces** (src/interfaces.ts):
- `SlimContextMessage`: Standard message shape with role (`system | user | assistant | tool | human`) and `content` (string).
- `SlimContextChatModel`: Extension interface requiring a single `invoke(messages) => Promise<response>` method. Allows any LLM provider (OpenAI, Anthropic, local) to be plugged in.
- `SlimContextCompressor`: Strategy interface with `compress(messages) => Promise<messages>` method.
- `TokenBudgetConfig`: Shared configuration tuple (`maxModelTokens`, `thresholdPercent`, `estimateTokens`, `minRecentMessages`).

**Compression Strategies** (src/strategies/):
- `TrimCompressor` (trim.ts): Stateless token-aware message dropping. Implements keepMask iteration over message array; preserves system messages via role check, then drops oldest non-protected messages until under threshold.
- `SummarizeCompressor` (summarize.ts): Stateful AI-based compression. Identifies leading system message (re-inserted unchanged), formats middle portion as transcript (`role: content\n---\n...`), invokes chat model via `model.invoke()`, injects summary as new system message, appends preserved tail.
- Common utilities (common.ts): Token estimation defaults (`len / 4` heuristic), threshold computation, compression guard to prevent compression mid-tool-use (checks if last message is user message).

### Message Flow (Summarization Example)

```
User conversation grows
           ↓
SummarizeCompressor.compress() called
           ↓
Estimate tokens for each message
           ↓
Total > threshold? → No: return unchanged
           ↓ Yes
Identify system message (if first message, role='system')
           ↓
Extract messages to summarize (exclude system, exclude recent tail)
           ↓
Format as transcript: "user: {content}\nassistant: {content}\n..."
           ↓
Invoke user's model with [system prompt, user request containing transcript]
           ↓
Receive summary response
           ↓
Build result: [original system?, summary message, ...recent messages]
           ↓
Return compressed history
```

### Design Decisions

1. **Zero runtime dependencies in core**: Library has no production npm dependencies, ensuring portability and minimal bundle impact. LangChain is an optional peer dependency for adapters only.

2. **BYOM (Bring Your Own Model)**: Rather than hard-coding API calls, library accepts a `SlimContextChatModel` interface. Users provide their own model instance (OpenAI SDK, Anthropic SDK, local LLM wrapper, etc.), enabling full flexibility and cost control.

3. **Message preservation rules**:
   - System messages never dropped (they frame assistant behavior)
   - Recent messages always preserved (configurable count)
   - Compression triggers only after user messages (prevents disruption of tool-use cycles)

4. **Shared token budget pattern**: Both strategies use same `TokenBudgetConfig` interface, enabling easy strategy swapping or chaining based on token levels.

5. **No side effects**: Both compressors are stateless; compress method is pure (given a message array, returns a new array; no external state mutation).

---

## Installation & Usage

### Installation

```bash
npm install slimcontext
```

Exports:
- Main: `import { TrimCompressor, SummarizeCompressor } from 'slimcontext'`
- LangChain: `import { langchain } from 'slimcontext'` or `import * as langchain from 'slimcontext/adapters/langchain'`

### Basic Usage: Trim Strategy

```typescript
import { TrimCompressor, SlimContextMessage } from 'slimcontext';

const compressor = new TrimCompressor({
  maxModelTokens: 8192,
  thresholdPercent: 0.7,
  minRecentMessages: 2
});

let history: SlimContextMessage[] = [
  { role: 'system', content: 'You are a helpful assistant.' },
  { role: 'user', content: 'What is TypeScript?' },
  { role: 'assistant', content: '...' },
  // ... conversation grows
];

history = await compressor.compress(history);
```

### Basic Usage: Summarize Strategy

```typescript
import { SummarizeCompressor, SlimContextChatModel } from 'slimcontext';

class MyModel implements SlimContextChatModel {
  async invoke(messages) {
    // Call your LLM provider
    return { content: 'Generated summary...' };
  }
}

const compressor = new SummarizeCompressor({
  model: new MyModel(),
  maxModelTokens: 8192,
  thresholdPercent: 0.7,
  minRecentMessages: 4
});

history = await compressor.compress(history);
```

### OpenAI Integration (BYOM Pattern)

Users can wrap OpenAI's SDK without adding slimcontext as a dependency:

```typescript
import OpenAI from 'openai';

class OpenAIModel implements SlimContextChatModel {
  private client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

  async invoke(messages) {
    const response = await this.client.chat.completions.create({
      model: 'gpt-4-mini',
      messages: messages.map(m => ({ role: m.role, content: m.content }))
    });
    return { content: response.choices[0].message.content };
  }
}

const compressor = new SummarizeCompressor({ model: new OpenAIModel() });
```

See [examples/OPENAI_EXAMPLE.md](https://github.com/agentailor/slimcontext/blob/main/examples/OPENAI_EXAMPLE.md) and [examples/LANGCHAIN_COMPRESS_HISTORY.md](https://github.com/agentailor/slimcontext/blob/main/examples/LANGCHAIN_COMPRESS_HISTORY.md) in the repository for detailed copy-paste snippets.

---

## Relevance to Claude Code Development

### Primary Use Cases for Claude Code Sessions

1. **Long Multi-Turn Planning Sessions**: `/add-new-feature` and `/implement-feature` workflows generate large context artifacts (feature specs, task plans, codebase analysis). SlimContext could compress session history before running `/complete-implementation` quality gates to stay within LLM context windows.

2. **Agent Memory Management**: Multi-agent workflows (orchestrator + sub-agents) accumulate conversation history. SlimContext's BYOM model pattern aligns with Claude Code's ability to dispatch sub-agents with shared token budgets.

3. **Integration with Context-Gathering Agents**: The `context-gathering` agent in `/add-new-feature` reads and summarizes codebase artifacts. SlimContext's summarization strategy mirrors this pattern—extracting narrative from structured content while preserving semantic fidelity.

4. **Selective Trimming for Task Files**: SAM task execution generates `LastActivity` timestamps and divergence notes over many tasks. SlimContext's trimming strategy could prune stale task context while preserving recent task state.

### Specific Integration Points

- **Prompt Compression**: SummarizeCompressor could reduce agent delegation prompts by summarizing prior agent outputs (e.g., feature-researcher findings condensed into a summary before passing to python-cli-design-spec).
- **Memory Budget Allocation**: Token budget config aligns with Claude Code's token accounting for sub-agent work—both require explicit token thresholds and preservation rules.
- **Framework Agnosticism**: SlimContext's BYOM model is compatible with Claude SDK sub-agent delegation; no additional API clients needed beyond existing Claude integration.

### Caveats for Claude Code Context

- **Summarization Latency**: SummarizeCompressor requires an additional LLM call per compression event; may increase task execution time in time-sensitive workflows.
- **Context Preservation Risk**: Trimming strategy permanently loses old messages; may be unsuitable for audit-trail features (e.g., task history, compliance logs).
- **Summary Quality**: Summarization quality depends on the model used; using a lower-cost model (GPT-4-mini) risks semantic loss in complex technical discussions.

---

## Limitations and Caveats

### Documented Limitations

- **Token Estimation Heuristic**: Default token estimator uses `message.content.length / 4`, which is a rough approximation. Actual token counts vary by tokenizer and model. Users must provide custom `estimateTokens` for accuracy with specific models.

- **Compression Guard**: Both strategies only compress when the last message is from a user role (to avoid disrupting assistant-assistant or tool-use cycles). Long tool-use sequences (assistant ↔ tool → assistant ↔ tool) may accumulate tokens without triggering compression if final message is not user message.

- **Single Summarization Point**: SummarizeCompressor injects one synthetic summary message before the preserved recent tail. Multiple compression cycles add more summaries, potentially creating summary-of-summary chains. No built-in deduplication or summary merging.

- **No Semantic Deduplication**: Neither strategy removes duplicate or near-duplicate messages within the preserved tail. Redundant recent context is kept verbatim.

- **LangChain Peer Dependency**: LangChain adapter requires `@langchain/core >=0.3.71 <1.0`. Version constraints may lag behind LangChain releases; users on newer LangChain versions may encounter compatibility issues.

### Undocumented Limitations (Inferred from Code)

- **Immutable Message Objects**: Library assumes `SlimContextMessage` objects are not mutated during compression; no deep cloning is performed. Custom `metadata` fields are preserved but not validated.

- **No Async Batching**: SummarizeCompressor invokes the model once per compression call. If compression is triggered frequently (e.g., every few messages), this creates serial API calls with no batching optimization.

- **No Rollback**: If summarization model fails or returns empty content, the compressor does not fall back to trimming; it raises or returns the summary verbatim. Error handling is minimal.

---

## References

- **Official Repository**: <https://github.com/agentailor/slimcontext> (accessed 2026-03-17)
- **README**: <https://github.com/agentailor/slimcontext/blob/main/README.md> (accessed 2026-03-17)
- **Package Manifest**: package.json v2.1.3 (accessed 2026-03-17)
- **Project Metadata**: CLAUDE.md in repository (accessed 2026-03-17)
- **GitHub API Data**: Repository metadata query (accessed 2026-03-17)
- **Examples**: examples/OPENAI_EXAMPLE.md, examples/LANGCHAIN_COMPRESS_HISTORY.md (accessed 2026-03-17)

---

## Freshness Tracking

| Section | Confidence | Last Verified | Notes |
|---------|-----------|---------------|-------|
| Identity/Metadata | high | 2026-03-17 | Package manifest and GitHub API consistent; version 2.1.3 confirmed |
| Key Statistics | high | 2026-03-17 | Repository statistics from GitHub API; 6-month-old project |
| Key Features | high | 2026-03-17 | README and source code (interfaces.ts, trim.ts, summarize.ts) aligned; feature behavior extracted verbatim |
| Technical Architecture | high | 2026-03-17 | Source files read: interfaces.ts, strategies/trim.ts, strategies/summarize.ts; component names and data flows documented |
| Usage Examples | high | 2026-03-17 | Code examples extracted from README verbatim; copy-paste accuracy verified |
| Limitations | medium | 2026-03-17 | Documented limitations from code comments and CLAUDE.md; undocumented limitations inferred from source inspection. No explicit limitation statement in README. |
| Relevance to Claude Code | medium | 2026-03-17 | Assessment based on SlimContext architecture alignment with Claude Code SAM workflow; no direct integration evidence yet. Requires validation through prototype. |

**Next Review**: 2026-06-17 (3 months)
**Review Trigger**: New major release, significant dependency updates (LangChain peer version bump), or adoption in Claude Code workflows.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Local Memory](./local-memory.md) | context-management | persistent memory layer with token-optimized multi-provider backend and knowledge hierarchy evolution |
| [Claude-Mem](./claude-mem.md) | context-management | AI-powered chat history compression with progressive disclosure and MCP tool integration |
| [Unblocked](./unblocked.md) | context-management | context engine for token optimization with 48% reduction, unified multi-source knowledge synthesis |
| [Microsoft GraphRAG](./microsoft-graphrag.md) | context-management | hierarchical summarization of unstructured text via knowledge graph community detection |
| [Jina AI](./jina-ai.md) | context-management | multimodal embeddings and Reader API for semantic retrieval and URL-to-Markdown extraction |
| [SourceSync.ai](./sourcesyncai.md) | context-management | multi-source RAG platform with hybrid search and namespace-based knowledge isolation |
| [Straion](./straion.md) | context-management | dynamic context injection with task-scoped rules and token budget awareness |
| [ctxforge](../prompt-engineering/ctxforge.md) | prompt-engineering | context engineering framework with protocol-based token budget management and discovery workflows |

