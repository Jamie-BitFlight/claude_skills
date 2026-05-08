---
name: Claude-Mem - Persistent Memory Compression for Claude Code
description: Claude-Mem is a Claude Code plugin that automatically captures tool usage observations during coding sessions, compresses them with AI using Claude's Agent SDK, and injects relevant context back into...
license: AGPL-3.0
metadata:
  topic: claude-mem
  category: context-management
  source_url: https://claude-mem.ai
  github: thedotmack/claude-mem
  version: "v6.5.0"
  verified: "2026-01-31"
  next_review: "2026-04-30"
---

## Overview

Claude-Mem is a Claude Code plugin that automatically captures tool usage observations during coding sessions, compresses them with AI using Claude's Agent SDK, and injects relevant context back into future sessions. It provides persistent memory that survives across sessions through a combination of SQLite storage, FTS5 full-text search, and Chroma vector database for hybrid semantic search.

**Core Value Proposition**: Enable Claude Code to maintain continuity of knowledge about projects even after sessions end, with token-efficient progressive disclosure that minimizes context window usage.

---

## Problem Addressed

| Problem                                           | How Claude-Mem Solves It                                                          |
| ------------------------------------------------- | --------------------------------------------------------------------------------- |
| Claude Code loses context between sessions        | Automatically captures observations and injects relevant context at session start |
| Large context histories overwhelm context windows | Progressive disclosure pattern with 3-layer workflow (~10x token savings)         |
| Manual context management is tedious              | Fully automatic operation via lifecycle hooks - no manual intervention            |
| Searching past sessions is difficult              | 4 MCP tools with hybrid semantic + keyword search for natural language queries    |
| No visibility into what Claude remembers          | Web viewer UI at localhost:37777 shows real-time memory stream                    |
| Sensitive content exposure concerns               | Privacy control via `<private>` tags to exclude content from storage              |

---

## Key Statistics (as of January 31, 2026)

| Metric              | Value      |
| ------------------- | ---------- |
| GitHub Stars        | 15,681     |
| Forks               | 1,094      |
| Open Issues         | 169        |
| Primary Language    | TypeScript |
| Node.js Requirement | >= 18.0.0  |
| MCP Tools Provided  | 4          |
| Lifecycle Hooks     | 5          |
| Worker Port         | 37777      |

---

## Key Features

### 1. Automatic Memory Capture

- **Zero Configuration**: Works immediately after plugin installation
- **Tool Usage Observation**: Captures what Claude does during sessions
- **Session Boundaries**: Tracks SessionStart, UserPromptSubmit, PostToolUse, Stop, SessionEnd
- **Smart Compression**: AI-generated semantic summaries reduce storage overhead

### 2. Progressive Disclosure Pattern

Token-efficient 3-layer workflow for context retrieval:

<eg>
Layer 1: search() -> Compact index (~50-100 tokens/result)
Layer 2: timeline() -> Chronological context around observations
Layer 3: get_observations() -> Full details ONLY for filtered IDs (~500-1000 tokens/result)
</eg>

**Result**: ~10x token savings by filtering before fetching details.

### 3. MCP Search Tools

Four MCP tools for intelligent memory search:

| Tool               | Purpose                                            |
| ------------------ | -------------------------------------------------- |
| `search`           | Full-text queries with filters (type/date/project) |
| `timeline`         | Chronological context around specific observations |
| `get_observations` | Fetch full details by observation IDs              |
| `__IMPORTANT`      | Workflow documentation (always visible to Claude)  |

### 4. Hybrid Search Architecture

- **SQLite + FTS5**: Full-text search for keyword matching
- **Chroma Vector Database**: Semantic similarity search
- **Hybrid Ranking**: Combines both for intelligent retrieval

### 5. Web Viewer UI

- **Real-time Stream**: View memory as it's captured at `http://localhost:37777`
- **Observation Browser**: Search and browse all stored observations
- **Citation System**: Reference past observations with IDs
- **Settings Management**: Configure beta features and version switching

### 6. Privacy Controls

- **`<private>` Tags**: Exclude sensitive content from storage
- **Local Storage**: All data stays on your machine
- **Fine-grained Config**: Control what context gets injected

### 7. Beta Features

- **Endless Mode**: Biomimetic memory architecture for extended sessions
- **Version Switching**: Toggle between stable and beta from web UI

---

## Technical Architecture

<eg>
Claude Code Session
        |
        v
+-------------------+
|  Lifecycle Hooks  |
|  (6 hook scripts) |
+-------------------+
        |
        v
+-------------------+     +-------------------+
|  Worker Service   |<--->|   Web Viewer UI   |
|  (Bun on :37777)  |     | (localhost:37777) |
+-------------------+     +-------------------+
        |
        v
+-------------------+     +-------------------+
|  SQLite + FTS5    |     |  Chroma Vector DB |
|  (observations,   |     |  (semantic search)|
|   sessions,       |     +-------------------+
|   summaries)      |
+-------------------+
        |
        v
+-------------------+
|  4 MCP Tools      |
|  (search,         |
|   timeline,       |
|   get_observations|
|   __IMPORTANT)    |
+-------------------+
</eg>

**Component Details**:

1. **Lifecycle Hooks**: 5 hooks capture session events (SessionStart, UserPromptSubmit, PostToolUse, Stop, SessionEnd)
2. **Pre-Hook Script**: Cached dependency checker for smart installation
3. **Worker Service**: HTTP API managed by Bun runtime with 10 search endpoints
4. **SQLite Database**: Stores sessions, observations, and AI-generated summaries
5. **Chroma Vector DB**: Provides semantic search capabilities
6. **mem-search Skill**: Natural language queries with progressive disclosure

---

## Installation and Usage

### Installation

```bash
# In Claude Code terminal
> /plugin marketplace add thedotmack/claude-mem

> /plugin install claude-mem
```

Restart Claude Code. Context from previous sessions will automatically appear.

### Usage - Search Workflow

```typescript
// Step 1: Search for compact index
search(query="authentication bug", type="bugfix", limit=10)

// Step 2: Review index, identify relevant observation IDs (e.g., #123, #456)

// Step 3: Get timeline context around interesting results
timeline(observation_id=123)

// Step 4: Fetch full details only for relevant IDs
get_observations(ids=[123, 456])
```

### Configuration

Settings are managed in `~/.claude-mem/settings.json`:

- AI model selection
- Worker port configuration
- Data directory location
- Log level settings
- Context injection preferences

---

## Relevance to Claude Code Development

### Direct Applications

1. **Context Persistence**: Enables long-running projects to maintain state across sessions
2. **Token Optimization**: Progressive disclosure pattern demonstrates efficient context management
3. **Plugin Architecture**: Reference implementation for Claude Code plugin with lifecycle hooks
4. **MCP Integration**: Shows how to expose search functionality via MCP tools

### Patterns Worth Adopting

1. **Progressive Disclosure**: 3-layer workflow (index -> timeline -> details) minimizes token usage
2. **Lifecycle Hook Architecture**: 5 hooks + pre-hook for dependency management
3. **Hybrid Search**: Combining FTS5 + vector embeddings for comprehensive retrieval
4. **Privacy Tags**: `<private>` tag pattern for user-controlled content exclusion
5. **Web Viewer Pattern**: Local UI for debugging and visibility into system state
6. **Citation System**: Observation IDs for referencing past context

### Integration Opportunities

1. Could inform design of skill-based context injection strategies
2. Progressive disclosure pattern applicable to any context-heavy skill
3. Lifecycle hook patterns could enhance other Claude Code plugins
4. Hybrid search architecture could improve skill and agent search capabilities

---

## Dependencies

| Dependency    | Purpose                                                   |
| ------------- | --------------------------------------------------------- |
| Node.js >= 18 | Runtime environment                                       |
| Bun           | JavaScript runtime and process manager (auto-installed)   |
| uv            | Python package manager for vector search (auto-installed) |
| SQLite 3      | Persistent storage (bundled)                              |
| Chroma        | Vector database for semantic search                       |

---

## References

1. **Official Website**: <https://claude-mem.ai> (accessed 2026-01-31)
2. **GitHub Repository**: <https://github.com/thedotmack/claude-mem> (accessed 2026-01-31)
3. **Documentation Site**: <https://docs.claude-mem.ai> (accessed 2026-01-31)
4. **Architecture Overview**: <https://docs.claude-mem.ai/architecture/overview> (accessed 2026-01-31)
5. **Progressive Disclosure Philosophy**: <https://docs.claude-mem.ai/progressive-disclosure> (accessed 2026-01-31)
6. **Search Architecture**: <https://docs.claude-mem.ai/architecture/search-architecture> (accessed 2026-01-31)
7. **Hooks Architecture**: <https://docs.claude-mem.ai/hooks-architecture> (accessed 2026-01-31)
8. **Configuration Guide**: <https://docs.claude-mem.ai/configuration> (accessed 2026-01-31)
9. **Author Twitter/X**: <https://x.com/Claude_Memory>
10. **Discord Community**: <https://discord.com/invite/J4wttp9vDu>

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-05-08 |
| Next Review Recommended | TBD |

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [SigMap](../developer-tools/sigmap.md) | developer-tools | referenced by SigMap (developer-tools) |
