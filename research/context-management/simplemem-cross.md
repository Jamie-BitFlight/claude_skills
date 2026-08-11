---
title: "SimpleMem-Cross: Persistent Cross-Conversation Memory for LLM Agents"
license: "MIT (Copyright 2025 AIMING Lab)"
next_review: "2026-06-19 (3 months)"
---

# SimpleMem-Cross

## Overview

SimpleMem-Cross is a Python library that extends SimpleMem with cross-conversation memory capabilities, enabling LLM agents to retain and retrieve context across independent sessions. Built by AIMING Lab, it combines SQLite for session timeline persistence, LanceDB for semantic vector search, and heuristic observation extraction to automatically identify decisions, discoveries, and learnings from agent conversations. The system achieves 64% performance improvement over Claude-Mem on the LoCoMo benchmark (score: 48) and provides token-budgeted context injection to manage memory size within LLM context windows.

**Core Value Proposition**: Agents automatically retain learnings across conversations without manual memory management, enabling smarter, context-aware decisions in long-running projects spanning days or weeks.

**Composition-based architecture**: SimpleMem-Cross wraps the original SimpleMem library without modification, enabling independent versioning and research artifact preservation while adding cross-session functionality via a new session lifecycle management layer.

**Sources**: <https://github.com/aiming-lab/SimpleMem/blob/main/cross/README.md> — LoCoMo comparison table (SimpleMem 48, Claude-Mem 29.3, +64%), SQLite/LanceDB split, heuristic observation extraction, token-budgeted injection, composition-over-modification design. Root README announcement dated 02/09/2026: <https://github.com/aiming-lab/SimpleMem> (accessed 2026-03-19; re-verified 2026-08-11)

---

## Problem Addressed

Traditional LLM memory systems either:
- Passively accumulate redundant context across sessions, requiring expensive iterative reasoning to extract relevant information
- Lack cross-session continuity, forcing agents to re-establish context on each conversation restart
- Impose manual re-injection of context, creating friction and information loss

SimpleMem-Cross solves this by automating four key workflows:

1. **Automatic session lifecycle management** — agents do not manually manage memory session state
2. **Token-budgeted context injection** — relevant prior context is selected and injected at session start without exceeding token limits
3. **Heuristic observation extraction** — decisions, discoveries, and learnings are automatically identified and indexed from session events
4. **Memory consolidation** — old, similar, or low-importance entries are automatically merged, decayed, or pruned to maintain memory quality

---

## Key Statistics

| Metric | Value | Source |
|--------|-------|--------|
| LoCoMo Benchmark Score | 48 | cross/README.md:43 |
| Performance vs Claude-Mem | +64% | cross/README.md:43-44 |
| Test Coverage | 127 passed | cross/README.md:16 |
| Python Version Required | 3.10+ | cross/README.md:17 |
| Python Modules | 10 | cross/README.md:216-228 |
| HTTP REST Endpoints | 8 | cross/README.md:301-310 |
| MCP Tool Definitions | 8 | cross/README.md:343-352 |
| MIT License | Yes | LICENSE file |

---

## Key Features

### Session Lifecycle Management

Sessions follow a 4-stage lifecycle: `start → record → stop → end`. Each stage is tracked and timestamped in persistent storage.

- **`start_session(content_session_id, user_prompt?)`**: Initiates a new memory session and automatically injects relevant context from previous sessions (token-budgeted to default 2,000 tokens, configurable)
- **`record_message(memory_session_id, content, role?)`**: Records user or assistant messages
- **`record_tool_use(memory_session_id, tool_name, tool_input, tool_output)`**: Records tool invocations with inputs and outputs
- **`stop_session(memory_session_id)`**: Finalizes session — triggers observation extraction, generates session summary, and stores memory entries
- **`end_session(memory_session_id)`**: Marks session completed and cleans up temporary state

**Mechanism**: All session events are written to a SQLite table (`sessions`, `events`, `observations`, `summaries`). On `stop_session()`, a heuristic extractor processes the event log to identify decisions, discoveries, and learnings. Observations and session summary are stored; entries are vectorized and indexed in LanceDB for future cross-session retrieval.

### Automatic Context Injection

When `start_session()` is called, the system performs token-budgeted semantic search across all previous sessions' memory entries to build a `ContextBundle`:

1. Semantic search using 1024-d vector embeddings returns candidate entries ranked by relevance
2. Token counter budgets entries by their serialized length, starting with highest-relevance matches
3. Stop adding entries when token budget (default 2,000) is exhausted
4. Bundle is rendered into a formatted string for injection into the system prompt

The injected context is returned in the `start_session()` response dict: `result["context"]`

**Configuration**: `max_context_tokens` parameter (default 2000) is set via `create_orchestrator(max_context_tokens=N)`

### Smart Event Collection with 3-Tier Redaction

Event recording applies automatic redaction to remove secrets and sensitive data before storage:

- **Tier 1 (Regex-based)**: Detects and redacts API keys, tokens, email addresses, phone numbers (20+ patterns)
- **Tier 2 (Named Entity Recognition)**: Detects redactable persons, emails, and financial info
- **Tier 3 (Heuristic)**: Detects files containing `.env`, credentials, keys, or password in name/content

**Implementation**: `RedactionFilter` class in collectors.py applies all tiers thread-safely before `EventCollector.add_event()` writes to storage.

### Observation Extraction

Observations are generated by heuristic analysis of the session event log:

- **Decisions**: Agent choices extracted from assistant messages containing "decided", "chosen", "will use", "implemented"
- **Discoveries**: Facts extracted from tool output that appear novel relative to the memory index
- **Learnings**: Insights extracted from assistant messages that begin with "learned", "realized", "discovered"

**Mechanism**: During `stop_session()`, the `SessionManager.finalize()` method scans the event log and produces structured `Observation` records. Each observation is tagged with type (decision/discovery/learning), source event ID, and generated timestamp.

### Provenance Tracking

Every memory entry stored in LanceDB includes fields linking back to its source:

- `source_session_id`: Which session generated this memory
- `source_event_id`: Which event within that session (for traceability)
- `timestamp`: When the entry was created
- `topic`: Categorical tagging for grouped retrieval

**Mechanism**: `CrossMemoryEntry` Pydantic model (in types.py) embeds provenance fields. When `stop_session()` yields observations, each is converted to a `CrossMemoryEntry` with source tracking before vector embedding and LanceDB insertion.

### Memory Consolidation

A background `ConsolidationWorker` maintains memory quality by:

1. **Decay**: Entries older than `max_age_days` (default 90) have their importance multiplied by `decay_factor` (default 0.9)
2. **Merge**: Entries with similarity > `merge_similarity_threshold` (default 0.95) are merged into a single entry with combined provenance
3. **Prune**: Entries with importance < `min_importance` (default 0.05) are deleted

**Configuration**: Via `ConsolidationPolicy` class. Worker is invoked manually via `worker.run(tenant_id)`.

---

## Technical Architecture

### Core Design Principles

| Principle | Implementation | Rationale |
|-----------|-----------------|-----------|
| **Composition over modification** | Original SimpleMem wrapped via duck typing, never subclassed or edited | Preserves research artifact; enables independent versioning |
| **Multi-stage storage** | SQLite for session timeline; LanceDB for cross-session vectors | SQLite handles relational session data; LanceDB handles semantic search |
| **Hook-based lifecycle** | Abstract `SessionHooks` with 5 async methods; no polling | Enables integration with agent frameworks via callbacks |
| **Progressive disclosure** | Context injected at session start, not during execution | Reduces token overhead; enables agent to request additional context if needed |
| **Provenance-first design** | Every vector entry links to source evidence | Enables audit, debugging, and citation of memory decisions |

### Module Structure

| Module | Lines | Purpose | Key Classes |
|--------|-------|---------|-------------|
| `types.py` | 227 | Pydantic models and enums | `SessionStatus`, `EventType`, `ObservationType`, `CrossMemoryEntry`, `ContextBundle`, `FinalizationReport` |
| `storage_sqlite.py` | 805 | SQLite backend with 6 tables | `SessionManager`, schema: sessions, events, observations, summaries, consolidated_entries, provenance_index |
| `storage_lancedb.py` | 542 | LanceDB vector store and search | `VectorStore`, hybrid search (semantic/keyword/structured) |
| `hooks.py` | 401 | Lifecycle hook interface | `SessionHooks` abstract base class; 5 async methods: on_session_start, on_message, on_tool_use, on_session_stop, on_session_end |
| `collectors.py` | 413 | Event collection and redaction | `RedactionFilter` (3-tier), `EventCollector` (thread-safe queue) |
| `session_manager.py` | 755 | Full lifecycle orchestration | `SessionManager` — start/record/finalize/end state machine |
| `context_injector.py` | 385 | Token-budgeted context builder | `ContextInjector`, `ContextBundle` rendering |
| `orchestrator.py` | 530 | Top-level facade | `CrossMemOrchestrator`, `create_orchestrator()` factory |
| `api_http.py` | 556 | FastAPI REST router | `create_app()`, `create_cross_router()` |
| `api_mcp.py` | 620 | MCP tool registry | `MCPToolRegistry`, JSON Schema definitions |
| `consolidation.py` | 390 | Memory maintenance | `ConsolidationWorker`, `ConsolidationPolicy` |

### Data Flow

```
User/Agent Framework
         ↓
┌─────────────────────────┐
│  HTTP/MCP API           │
│  (FastAPI / MCP)        │
└────┬────────────────────┘
     ↓
┌─────────────────────────┐
│  CrossMemOrchestrator   │  ← Facade for all operations
│  (start/record/stop)    │
└────┬────────────────────┘
     ├─→ SessionManager        ← Session lifecycle (SQLite)
     ├─→ ContextInjector       ← Token-budgeted retrieval
     └─→ ConsolidationWorker   ← Memory maintenance
         ↓
┌─────────────────────────┐
│  Cross-Session          │  ← Semantic + keyword search
│  Vector Store (LanceDB) │
└─────────────────────────┘
         ↓
┌─────────────────────────┐
│  SimpleMem Pipeline     │  ← Reused composition
│  (wrapped, unmodified)  │
└─────────────────────────┘
```

### Integration with SimpleMem

SimpleMem-Cross does not modify SimpleMem. Instead:

1. `CrossMemOrchestrator` orchestrates session management and vector operations independently
2. When context retrieval is needed, `ContextInjector` performs searches on the LanceDB vector store
3. The injected context is passed to SimpleMem's existing `HybridRetriever` and `AnswerGenerator` for the current session's intra-session memory operations
4. New observations and summaries generated during `stop_session()` are indexed in LanceDB as cross-session memory entries

This compositional architecture ensures SimpleMem's core algorithm (semantic structured compression, online synthesis, intent-aware retrieval) is unaffected.

---

## Installation & Usage

### Requirements

- Python 3.10+
- Dependencies bundled with SimpleMem: lancedb, pydantic, SQLAlchemy, openai (or compatible API), anthropic

### Quick Start

```python
import asyncio
from cross.orchestrator import create_orchestrator

async def main():
    # Create orchestrator
    orch = create_orchestrator(project="my-project")

    # Start session with automatic context injection
    result = await orch.start_session(
        content_session_id="session-001",
        user_prompt="Continue building the REST API authentication",
    )
    memory_session_id = result["memory_session_id"]
    print(result["context"])  # Previous context automatically injected

    # Record events during session
    await orch.record_message(memory_session_id, "User asked about JWT auth")
    await orch.record_tool_use(
        memory_session_id,
        tool_name="read_file",
        tool_input="auth/jwt.py",
        tool_output="class JWTHandler: ...",
    )

    # Finalize and persist observations
    report = await orch.stop_session(memory_session_id)
    print(f"Stored {report.entries_stored} entries, {report.observations_count} observations")

    await orch.end_session(memory_session_id)
    orch.close()

asyncio.run(main())
```

### HTTP API

FastAPI REST server with 8 endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/cross/sessions/start` | POST | Start session |
| `/cross/sessions/{id}/message` | POST | Record message |
| `/cross/sessions/{id}/tool-use` | POST | Record tool use |
| `/cross/sessions/{id}/stop` | POST | Finalize session |
| `/cross/sessions/{id}/end` | POST | End session |
| `/cross/search` | POST | Search across sessions |
| `/cross/stats` | GET | Memory statistics |
| `/cross/health` | GET | Health check |

### MCP Integration

8 MCP tools available for Model Context Protocol clients:

1. `cross_session_start` — Start new session
2. `cross_session_message` — Record message
3. `cross_session_tool_use` — Record tool invocation
4. `cross_session_stop` — Finalize session
5. `cross_session_end` — End session
6. `cross_session_search` — Search memories
7. `cross_session_context` — Get context bundle
8. `cross_session_stats` — Memory statistics

### Configuration

```python
orch = create_orchestrator(
    project="my-project",          # Project identifier
    tenant_id="team-alpha",        # Multi-tenant isolation
    db_path="~/.simplemem-cross/cross_memory.db",  # SQLite location
    lancedb_path="~/.simplemem-cross/lancedb_cross",  # Vector DB location
    max_context_tokens=2000,       # Token budget for injection
)
```

**Default paths**:
- SQLite: `~/.simplemem-cross/cross_memory.db`
- LanceDB: `~/.simplemem-cross/lancedb_cross`

---

## Relevance to Claude Code Development

SimpleMem-Cross is directly applicable to Claude Code's agent systems:

1. **Multi-turn agent workflows**: Agents can retain context across independent skill invocations or backlog-linked tasks without manual re-seeding
2. **Skill integration**: Memory can be injected via lifecycle hooks into skill contexts, reducing context window pressure
3. **Research and planning agents**: Decisions, discoveries, and learnings from prior planning phases can be retrieved during implementation, improving task coherence
4. **Long-running projects**: Cross-session consolidation (decay/merge/prune) maintains memory quality as projects span weeks or months

**Specific use case in this codebase**: The research-curator agent (which produces entries like this one) could leverage SimpleMem-Cross to retain findings about libraries, tools, and patterns across multiple research sessions, reducing redundant research and enabling pattern-based recommendations.

---

## Limitations and Caveats

1. **No built-in conflict resolution**: When duplicate or conflicting observations are merged, the consolidation worker applies similarity-based merging, but does not expose conflict-resolution APIs. Manual review of merged entries is recommended for critical domains.

2. **Heuristic-based observation extraction**: The extraction mechanism relies on regex and keyword matching for decision/discovery/learning identification. This may miss implicit decisions or contextual insights not explicitly verbalized.

3. **Decay factor is global**: All entries decay uniformly regardless of importance or domain. High-value entries (e.g., security decisions) cannot be marked as "no decay" without custom consolidation policy implementation.

4. **No explicit memory queries by type**: The search API does not expose filtering by `source_event_type` (e.g., "only return decisions, not discoveries"). Type-based queries require post-filtering of search results.

5. **Provenance tracking depends on correct session_id**: If an agent falsifies `content_session_id` or `memory_session_id`, provenance links become untrustworthy. Multi-tenant isolation relies on correct tenant_id parameter.

6. **No lifecycle validation hooks**: The framework does not expose hooks to validate or reject observations before storage. All observations generated by `finalize()` are stored unconditionally.

---

## References

- **Repository**: <https://github.com/aiming-lab/SimpleMem> (accessed 2026-03-19)
- **Cross-Session README**: <https://github.com/aiming-lab/SimpleMem/blob/main/cross/README.md> (accessed 2026-03-19)
- **SimpleMem Paper**: <https://arxiv.org/abs/2601.02553> (accessed 2026-03-19)
- **License**: MIT (Copyright 2025 AIMING Lab) — <https://github.com/aiming-lab/SimpleMem/blob/main/LICENSE> (accessed 2026-03-19)
- **PyPI Package**: <https://pypi.org/project/simplemem/> (referenced in README)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude-Mem - Persistent Memory Compression for Claude Code](./claude-mem.md) | context-management | Alternative cross-session memory approach using AI compression and tool observation capture instead of heuristic observation extraction |
| [Local Memory - Persistent Memory Infrastructure for AI Agents](./local-memory.md) | context-management | Parallel persistent memory system with four-level knowledge hierarchy (L0–L3) and contradiction detection instead of memory consolidation |
| [Microsoft GraphRAG](./microsoft-graphrag.md) | context-management | Knowledge graph extraction and retrieval for RAG; complements SimpleMem-Cross's vector-based cross-session retrieval with structured knowledge representation |
| [Agno](../agent-frameworks/agno.md) | agent-frameworks | Multi-agent framework with built-in learning system persisting user profiles and knowledge across sessions using Agno's storage backends (Postgres, SQLite, DynamoDB, etc.) |
| [LiteAgents - Multi-Tool AI Development Toolkit](../agent-frameworks/liteagents.md) | agent-frameworks | Hot Memory pipeline (`/stash` → `/friction` → `/remember`) consolidates session context and learning into persistent `MEMORY.md`, sharing SimpleMem-Cross's session lifecycle and consolidation approach |

---
