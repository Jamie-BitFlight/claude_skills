---
name: Local Memory - Persistent Memory Infrastructure for AI Agents
description: Local Memory is an AI-powered persistent memory system that provides MCP, REST API, and CLI interfaces for storing, retrieving, and analyzing memories across AI agent sessions. It ships as a single...
license: Commercial (see <https://localmemory.co/terms>)
metadata:
  topic: local-memory
  category: context-management
  source_url: https://github.com/local-memory
  version: "1.4.0"
  verified: "2026-02-07"
  next_review: "2026-05-07"
---

## Overview

Local Memory is an AI-powered persistent memory system that provides MCP, REST API, and CLI interfaces for storing, retrieving, and analyzing memories across AI agent sessions. It ships as a single Go binary with embedded Qdrant vector search, enabling semantic search with 10-57ms response times. Version 1.4.0 introduces a multi-provider AI backend allowing split configurations (e.g., local Ollama embeddings + cloud Anthropic chat).

---

## Problem Addressed

| Problem | Local Memory Solution |
|---------|-----------------------|
| AI agents lose context between sessions ("context amnesia") | Persistent memory store survives across sessions, agents, and `/clear` commands |
| Repeated explanations of codebase architecture and conventions | Store once, retrieve via semantic search in future sessions |
| No cross-agent knowledge sharing (Claude Desktop vs Claude Code vs Codex) | Unified memory accessible by any MCP-compatible agent on the machine |
| RAG systems store text but do not evolve understanding | Four-level knowledge hierarchy (L0 Observations -> L1 Learnings -> L2 Patterns -> L3 Schemas) with promotion/decay |
| Context windows waste tokens on redundant background info | Token optimization claimed up to 97.5% response size reduction via targeted retrieval |
| No contradiction detection in accumulated AI knowledge | Five-layer heuristic contradiction detection with resolution workflow |
| Embedding-only search misses keyword matches | Hybrid search combining semantic similarity and keyword matching |
| Cloud-only AI dependencies create privacy and cost concerns | Local-first architecture with optional cloud providers; embeddings can run fully local via Ollama |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| NPM Downloads (lifetime) | 4,227 | 2026-02-07 |
| NPM Downloads (last month) | 785 | 2026-02-07 |
| NPM Downloads (last week) | 221 | 2026-02-07 |
| GitHub Stars (releases repo) | 5 | 2026-02-07 |
| GitHub Binary Downloads (all releases) | 1,315 | 2026-02-07 |
| Total Releases | 33 | 2026-02-07 |
| First Release | 2025-08-27 | - |
| Latest Release | v1.4.0 (2026-02-07) | 2026-02-07 |

Note: The main source repository (`danieleugenewilliams/local-memory-golang`) is private. Only the binary releases repository is public.

---

## Key Features

### Memory Storage and Retrieval

- **Semantic Search**: Vector similarity search via embedded Qdrant with 10-57ms response times
- **Hybrid Search**: Combines semantic, keyword, tag-based, and date-range queries
- **Memory Importance**: Configurable importance levels (1-10) for memory prioritization
- **Domain Filtering**: Organize memories by project domain with cascade detection from agent config files
- **Session Filtering**: Access memories across sessions or within specific session scopes
- **Cursor Pagination**: Enterprise-grade pagination for large memory sets (1,100+ memories)

### Knowledge Evolution (v1.3.0+)

- **Four-Level Hierarchy**:
  - L0 Observations: Raw intake, ephemeral
  - L1 Learnings: Candidate insights, volatile
  - L2 Patterns: Validated generalizations, durable
  - L3 Schemas: Theoretical frameworks, permanent
- **Contradiction Detection**: Five-layer heuristic identification of conflicting knowledge
- **Epistemic Gap Tracking**: Tracks unknown unknowns via dedicated questions system
- **Knowledge Validation**: Promotion, decay, and evolution mechanisms

### Multi-Provider AI Backend (v1.4.0)

- **Split Architecture**: Independent `EmbeddingProvider` and `ChatProvider` interfaces
- **Provider Mixing**: Different providers for embeddings vs chat (e.g., Ollama embeddings + Anthropic chat)
- **Fallback Chains**: Optional fallback providers for resilience
- **Circuit Breaker Pattern**: Prevents cascade failures across providers
- **Supported Providers**:

| Provider | Embeddings | Chat | Type |
|----------|------------|------|------|
| Ollama | Yes (768 dims) | Yes | Local |
| OpenAI Compatible | Yes | Yes | Local/Remote |
| OpenAI | Yes (1536 dims) | Yes | Cloud |
| Anthropic | No | Yes | Cloud |
| claude CLI | No | Yes | Local subprocess |

### Interfaces

- **MCP Server**: stdio transport, 8+ unified tools for Claude Desktop, Claude Code, and other MCP-compatible agents
- **REST API**: Full HTTP API on `localhost:3002` for programmatic access
- **CLI**: `local-memory` command for shell scripting and manual operations
- **Desktop App**: Electron-based GUI for memory browsing and settings

### MCP Tools

**Core Tools**:

- `observe` - Record observations with knowledge level support (L0-L3)
- `search` - Semantic, tag, date range, and hybrid search
- `bootstrap` - Initialize sessions with knowledge context

**Knowledge Evolution**:

- `reflect` - Process observations into learnings
- `evolve` - Validate, promote, or decay knowledge
- `question` - Track epistemic gaps and contradictions
- `resolve` - Resolve contradictions and answer questions

**Reasoning Tools**:

- `predict` - Generate predictions from patterns
- `explain` - Trace causal paths between states
- `counterfactual` - Explore "what if" scenarios
- `validate` - Check knowledge graph integrity

**Relationship Tools**:

- `relate` - Create typed relationships between memories

### Agent Attribution (v1.4.0)

- Automatic agent type detection (Claude Desktop, Claude Code, REST API)
- Hostname tracking for multi-device memory attribution
- HTTP headers for custom agent identification (`X-Agent-Type`, `X-Agent-Context`, `X-Access-Scope`, `X-Agent-Hostname`)

---

## Technical Architecture

### System Components

<eg>
┌─────────────────────────────────────────────────────────────┐
│                     Local Memory Binary (Go)                │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ MCP      │  │ REST API │  │ CLI      │  │ Desktop   │  │
│  │ Server   │  │ :3002    │  │ Commands │  │ App       │  │
│  │ (stdio)  │  │          │  │          │  │ (Electron)│  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬──────┘  │
│       │              │             │              │         │
│       └──────────────┼─────────────┼──────────────┘         │
│                      v             v                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   ServiceAdapter                     │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐   │   │
│  │  │  EmbeddingProvider  │  │    ChatProvider      │   │   │
│  │  │  (Ollama/OpenAI/    │  │ (Anthropic/OpenAI/   │   │   │
│  │  │   Compatible)       │  │  claude CLI/Ollama)  │   │   │
│  │  └─────────────────────┘  └─────────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│                      │                                      │
│  ┌───────────────────v──────────────────────────────────┐   │
│  │              Qdrant Vector Database                  │   │
│  │              (Embedded, local storage)               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
</eg>

### Knowledge Evolution Pipeline

<eg>
L0 Observation    ->  reflect  ->  L1 Learning
L1 Learning       ->  evolve   ->  L2 Pattern (if validated)
L2 Pattern        ->  evolve   ->  L3 Schema (if generalized)
Any Level         ->  evolve   ->  Decay (if invalidated)
Contradiction     ->  resolve  ->  Updated knowledge + audit trail
</eg>

### Domain Cascade Resolution

<eg>
Explicit domain (in MCP args) > Agent config file detection > Config default
                                     |
                          ┌──────────┼──────────┐
                          v          v          v
                     CLAUDE.md   AGENTS.md   GEMINI.md
                     (HTML comment, Markdown header, or YAML frontmatter)
</eg>

---

## Installation and Usage

### Installation

```bash
npm install -g local-memory-mcp
```

### License Activation

```bash
# Get license from https://localmemory.co
local-memory license activate LM-XXXX-XXXX-XXXX-XXXX-XXXX
local-memory license status
```

### Service Management

```bash
local-memory start       # Start daemon
local-memory status      # Check status
local-memory stop        # Stop daemon
local-memory doctor      # System diagnostics
```

### CLI Usage

```bash
# Store memories
local-memory remember "Go channels are like pipes between goroutines"
local-memory remember "Redis is excellent for caching" --importance 8 --tags caching,database

# Search
local-memory search "concurrency patterns"
local-memory search "neural networks" --use_ai --limit 5

# Relationships
local-memory relate "channels" to "goroutines" --type enables
```

### MCP Configuration (Claude Desktop)

```json
{
  "mcpServers": {
    "local-memory": {
      "command": "/path/to/local-memory",
      "args": ["--mcp"],
      "transport": "stdio"
    }
  }
}
```

### Multi-Provider Configuration (v1.4.0)

```yaml
# ~/.local-memory/config.yaml
ai_provider:
  embedding_provider: "ollama"      # Local embeddings
  chat_provider: "anthropic"        # Cloud reasoning
  chat_fallback: "ollama"           # Fallback if cloud unavailable

  anthropic:
    enabled: true
    api_key: "sk-ant-xxxxx"
    model: "claude-sonnet-4-20250514"
    max_tokens: 4096
    timeout: 60s
```

### REST API

```bash
# Search
curl "http://localhost:3002/api/memories/search?query=python&limit=5"

# Store
curl -X POST "http://localhost:3002/api/memories" \
  -H "Content-Type: application/json" \
  -d '{"content": "Python dict comprehensions are powerful", "importance": 7}'

# Health
curl "http://localhost:3002/api/v1/health"
```

---

## Relevance to Claude Code Development

### Applications

1. **Cross-Session Context Persistence**: Store architectural decisions, debugging wisdom, and project conventions that Claude Code can retrieve in future sessions without re-explanation.

2. **Multi-Agent Knowledge Sharing**: Memories stored by Claude Desktop (during design) are accessible to Claude Code (during implementation) via the shared memory store.

3. **MCP Server Pattern Reference**: Local Memory's MCP implementation demonstrates patterns for building MCP servers with multiple tool categories, knowledge hierarchies, and agent detection.

4. **Knowledge Evolution Model**: The L0-L3 hierarchy (Observations -> Learnings -> Patterns -> Schemas) provides a structured approach to building cumulative AI knowledge that this repository's skill system could adopt.

### Patterns Worth Adopting

1. **Split Provider Architecture**: The separation of embedding and chat providers into independent interfaces with fallback chains is a pattern applicable to any system integrating multiple AI backends.

2. **Agent Attribution**: Tracking which agent stored information and from which machine provides auditability for multi-agent workflows.

3. **Domain Cascade**: The hierarchical domain resolution (explicit > config file > default) pattern is useful for organizing context by project.

4. **Circuit Breaker Pattern**: Provider-level circuit breakers prevent cascade failures when external AI services are unavailable.

5. **Contradiction Detection**: Automated identification of conflicting information prevents knowledge corruption in persistent stores.

### Integration Opportunities

1. **Claude Code Session Memory**: Use Local Memory as a persistent knowledge backend for Claude Code sessions to accumulate project understanding over time.

2. **Skill Knowledge Store**: Skills could store and retrieve reference information via Local Memory's semantic search rather than loading entire reference files.

3. **Agent Orchestration Context**: Multi-agent workflows could use Local Memory to share intermediate results and context between specialized agents.

### Considerations

1. **Commercial License Required**: All use cases require a paid license from localmemory.co. This is not open source.

2. **Ollama Dependency**: Default configuration requires Ollama running locally for embeddings. Alternative providers (OpenAI, OpenAI Compatible) require additional setup or API keys.

3. **Early-Stage Project**: With 4,227 total NPM downloads and 5 GitHub stars on the releases repo, this is a relatively new and niche project (first release August 2025). The main source code repository is private.

4. **Go Binary Distribution**: Ships as a compiled Go binary (not inspectable source), with the Qdrant vector database embedded. The NPM package is a 135MB wrapper that downloads the binary at install time.

---

## References

1. **Local Memory Website** - <https://www.localmemory.co/> (accessed 2026-02-07)
2. **Local Memory v1.4.0 Blog Post** - <https://www.localmemory.co/blog/local-memory-1.4-multi-provider-ai> (accessed 2026-02-07, SPA - content extracted from structured data)
3. **NPM Package** - <https://www.npmjs.com/package/local-memory-mcp> (accessed 2026-02-07)
4. **NPM Package JSON Metadata** - `npm view local-memory-mcp --json` (accessed 2026-02-07)
5. **GitHub Releases Repository** - <https://github.com/danieleugenewilliams/local-memory-releases> (accessed 2026-02-07)
6. **GitHub v1.4.0 Release Notes** - <https://github.com/danieleugenewilliams/local-memory-releases/releases/tag/v1.4.0> (accessed 2026-02-07)
7. **NPM README** - `npm view local-memory-mcp readme` (accessed 2026-02-07, version shown as 1.3.3)
8. **NPM Download Statistics** - <https://api.npmjs.org/downloads/> endpoints (accessed 2026-02-07)
9. **Website Structured Data (JSON-LD)** - Extracted from HTML `<script type="application/ld+json">` at localmemory.co (accessed 2026-02-07, shows softwareVersion "v1.3.0" and dateModified "2025-11-13", lagging behind current NPM version 1.4.0)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [empirica](../agent-infrastructure/empirica.md) | agent-infrastructure | referenced by empirica (agent-infrastructure) |
| [compression-monitor](../ai-observability/compression-monitor.md) | ai-observability | referenced by compression-monitor (ai-observability) |
| [claude-brain](./claude-brain.md) | context-management | referenced by claude-brain (context-management) |
| [mempalace](./mempalace.md) | context-management | referenced by mempalace (context-management) |
| [mex](./mex.md) | context-management | referenced by mex (context-management) |
| [simplemem-cross](./simplemem-cross.md) | context-management | referenced by simplemem-cross (context-management) |
| [slimcontext](./slimcontext.md) | context-management | referenced by slimcontext (context-management) |
| [unblocked](./unblocked.md) | context-management | referenced by unblocked (context-management) |
| [chroma](../data-infrastructure/chroma.md) | data-infrastructure | referenced by chroma (data-infrastructure) |
| [helix-db](../data-infrastructure/helix-db.md) | data-infrastructure | referenced by helix-db (data-infrastructure) |
| [pocketbase](../data-infrastructure/pocketbase.md) | data-infrastructure | referenced by pocketbase (data-infrastructure) |
