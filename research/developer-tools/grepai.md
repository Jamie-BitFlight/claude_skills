---
name: GrepAI - Semantic Code Search for AI Agents
description: GrepAI is a CLI tool written in Go that provides semantic code search and call graph analysis for AI coding agents. It indexes codebases using embedding models (locally via Ollama or cloud via...
license: MIT
metadata:
  topic: grepai
  category: developer-tools
  source_url: https://github.com/grepai
  github: yoanbernabeu/grepai
  version: "v0.31.0"
  verified: "2026-02-13"
  next_review: "2026-05-13"
---

## Overview

GrepAI is a CLI tool written in Go that provides semantic code search and call graph analysis for AI coding agents. It indexes codebases using embedding models (locally via Ollama or cloud via OpenAI) and stores vectors locally or in PostgreSQL/Qdrant, enabling natural language queries that return relevant code by meaning rather than text pattern matching. It includes a built-in MCP server for native integration with Claude Code, Cursor, and Windsurf.

---

## Problem Addressed

| Problem | GrepAI Solution |
|---------|-----------------|
| Traditional grep/ripgrep match text patterns, returning false positives for semantic queries (e.g., `grep "auth"` matches "author", "authorize string") | Embedding-based cosine similarity search returns code by meaning; query "user authentication flow" returns `handleUserLogin()` with relevance scores |
| AI agents consume excessive tokens reading entire codebases for context | Semantic search returns only relevant code chunks with file paths, line numbers, and scores; `--compact` flag reduces output by ~80% |
| Developers cannot easily determine impact of code changes | Call graph tracing (`trace callers`, `trace callees`, `trace graph`) maps function relationships across 12 languages |
| Cloud-based code search tools send proprietary code to external servers | 100% local execution with Ollama; no data leaves the machine |
| Code indexes become stale as files change during development | File watcher daemon (`grepai watch`) updates the index in real-time as files are modified |
| AI coding tools (Claude Code, Cursor) lack native semantic search capability | Built-in MCP server exposes `grepai_search`, `grepai_trace_callers`, `grepai_trace_callees`, `grepai_trace_graph`, `grepai_index_status` as native tools |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 1,222 | 2026-02-13 |
| GitHub Forks | 93 | 2026-02-13 |
| Open Issues | 19 | 2026-02-13 |
| Contributors | 19 | 2026-02-13 |
| GitHub Release Downloads | 5,166 | 2026-02-13 |
| Website-Reported Downloads | 4,284 | 2026-02-13 |
| Repository Created | 2026-01-09 | - |
| Latest Release | v0.31.0 (2026-02-13) | 2026-02-13 |
| Pull Requests | 2 | 2026-02-13 |
| Supported Languages (Trace) | 12 | 2026-02-13 |
| AI Agent Skills Available | 27 | 2026-02-13 |

---

## Key Features

### Semantic Code Search

- **Natural language queries**: Search by intent ("user authentication flow") instead of keywords
- **Cosine similarity scoring**: Results ranked by semantic relevance (0.0-1.0)
- **Configurable result limits**: `--limit N` controls result count (default: 10)
- **Output formats**: Human-readable (default), JSON (`--json`), TOON (`--toon`), compact (`--compact` saves ~80% tokens)
- **Search boost**: Configurable scoring adjustments that penalize test files and boost source directories
- **Hybrid search**: Optional combined vector similarity + text matching using Reciprocal Rank Fusion (RRF)

### Call Graph Analysis

- **Trace callers**: Find all functions that call a given symbol
- **Trace callees**: Find all functions called by a given symbol
- **Call graph**: Build complete dependency graphs with configurable depth
- **12 language support**: Go, TypeScript, JavaScript, Python, PHP, Java, C, C++, C#, Rust, Zig, Pascal/Delphi
- **Two extraction modes**: Fast (regex, no dependencies) and Precise (tree-sitter AST parsing)
- **JSON output**: Structured output for AI agent consumption

### Embedding Providers

- **Ollama (local, recommended)**: `nomic-embed-text` (768 dims), `nomic-embed-text-v2-moe` (multilingual), `bge-m3` (1024 dims), `mxbai-embed-large` (1024 dims), `all-minilm` (384 dims)
- **LM Studio (local)**: `nomic-embed-text-v1.5`, `bge-small-en-v1.5`, `bge-large-en-v1.5`
- **OpenAI (cloud)**: `text-embedding-3-small` (1536 dims), `text-embedding-3-large` (3072 dims)
- **Azure OpenAI**: Custom endpoint support for Azure-hosted OpenAI models

### Storage Backends

- **GOB (default)**: File-based storage in `.grepai/index.gob`, no external dependencies
- **PostgreSQL with pgvector**: Team-oriented, requires `CREATE EXTENSION vector`
- **Qdrant**: High-performance vector search, Docker-based deployment

### AI Agent Integration

- **MCP server**: Built-in Model Context Protocol server (`grepai mcp-serve`) exposing 5 tools
- **Claude Code**: `claude mcp add grepai -- grepai mcp-serve`; supports user-level and project-level scope
- **Cursor**: `.cursor/mcp.json` configuration
- **Windsurf**: MCP configuration support
- **Agent setup command**: `grepai agent-setup` detects and configures `.cursor/rules`, `.cursorrules`, `.windsurfrules`, `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`
- **Claude Code subagent**: `grepai agent-setup --with-subagent` creates `.claude/agents/deep-explore.md`
- **Skills package**: 27 installable skills via `npx skills add yoanbernabeu/grepai-skills`
- **Claude Code plugin**: Available via `/plugin marketplace add yoanbernabeu/grepai-skills`

### Real-Time Indexing

- **File watcher**: `grepai watch` monitors filesystem changes and updates the index automatically
- **Debounce configuration**: Configurable debounce delay (default: 500ms)
- **Gitignore-aware**: Respects `.gitignore` and external gitignore files
- **Automatic re-chunking**: Detects context length exceeded errors and splits chunks automatically

### Workspace Support

- **Multi-project workspaces**: `grepai workspace create` groups related projects
- **Cross-project search**: `--workspace` flag enables searching across all workspace projects
- **Cross-project tracing**: Call graph analysis spans workspace boundaries

---

## Technical Architecture

<eg>
┌──────────────────────────────────────────────────────────────┐
│                      grepai CLI (Go)                          │
│                                                               │
│  ┌─────────────────────┐  ┌─────────────────────────────┐   │
│  │    Commands          │  │    MCP Server (stdio)        │   │
│  │                      │  │                              │   │
│  │  init                │  │  grepai_search               │   │
│  │  watch               │  │  grepai_trace_callers        │   │
│  │  search              │  │  grepai_trace_callees        │   │
│  │  trace (callers/     │  │  grepai_trace_graph          │   │
│  │    callees/graph)    │  │  grepai_index_status         │   │
│  │  status              │  │                              │   │
│  │  agent-setup         │  │  Transport: stdio            │   │
│  │  mcp-serve           │  │  Format: JSON                │   │
│  │  workspace           │  │                              │   │
│  └──────────┬───────────┘  └──────────────┬──────────────┘   │
│             │                              │                   │
│  ┌──────────v──────────────────────────────v──────────────┐   │
│  │                  Core Engine                            │   │
│  │                                                         │   │
│  │  Chunking ──> Embedding ──> Vector Store ──> Search     │   │
│  │  (configurable   (Ollama/     (GOB/          (cosine    │   │
│  │   size/overlap)   OpenAI/      Postgres/      similarity │   │
│  │                   LM Studio)   Qdrant)        + boost)  │   │
│  │                                                         │   │
│  │  Symbol Extraction ──> Call Graph ──> Trace             │   │
│  │  (regex or              (.grepai/      (callers/         │   │
│  │   tree-sitter AST)       symbols.gob)   callees/graph)  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              File Watcher (fsnotify)                     │   │
│  │  Monitors filesystem ──> debounce ──> re-index changed  │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘

External Dependencies:
  - Ollama (local embedding server, optional)
  - OpenAI API (cloud embeddings, optional)
  - PostgreSQL + pgvector (optional backend)
  - Qdrant (optional backend)
</eg>

### Indexing Pipeline

<eg>
Source Files ──> .gitignore filter ──> Chunking (512 tokens, 50 overlap)
                                            │
                                            v
                                    Embedding Provider
                                    (Ollama / OpenAI / LM Studio)
                                            │
                                            v
                                    Vector Store
                                    (GOB / PostgreSQL / Qdrant)
                                            │
                                            v
                                    .grepai/index.gob (default)
                                    .grepai/symbols.gob (call graph)
</eg>

### Configuration File

All settings stored in `.grepai/config.yaml`:

```yaml
version: 1
embedder:
  provider: ollama
  model: nomic-embed-text
  endpoint: http://localhost:11434
  dimensions: 768
store:
  backend: gob
chunking:
  size: 512
  overlap: 50
watch:
  debounce_ms: 500
trace:
  mode: fast
  enabled_languages: [.go, .js, .ts, .py, .php, .java, .c, .cpp, .rs, .zig, .cs]
```

---

## Installation and Usage

### Installation Methods

```bash
# macOS (Homebrew)
brew install yoanbernabeu/tap/grepai

# Linux/macOS (shell script)
curl -sSL https://raw.githubusercontent.com/yoanbernabeu/grepai/main/install.sh | sh

# Windows (PowerShell)
irm https://raw.githubusercontent.com/yoanbernabeu/grepai/main/install.ps1 | iex

# From source (requires Go 1.24+)
git clone https://github.com/yoanbernabeu/grepai.git && cd grepai && make build
```

### Basic Workflow

```bash
# Initialize in project directory
cd your-project && grepai init

# Start indexing daemon (runs in foreground, watches for changes)
grepai watch

# Search (in another terminal)
grepai search "user authentication flow"
grepai search "error handling" --limit 5 --json --compact

# Call graph analysis
grepai trace callers "HandleLogin"
grepai trace callees "ProcessOrder"
grepai trace graph "AuthMiddleware" --depth 3

# Check index status
grepai status
```

### Claude Code MCP Integration

```bash
# Register as MCP server (user-level, available in all sessions)
claude mcp add grepai -s user -- grepai mcp-serve

# Or project-level with workspace
claude mcp add grepai -s project -- grepai mcp-serve --workspace my-fullstack
```

### Project-Level MCP Configuration (`.mcp.json`)

```json
{
  "mcpServers": {
    "grepai": {
      "command": "grepai",
      "args": ["mcp-serve"]
    }
  }
}
```

### Self-Update

```bash
grepai update --check   # Check for updates
grepai update           # Download and install latest
```

---

## Relevance to Claude Code Development

### Applications

1. **Context Reduction for AI Agents**: The primary value proposition is reducing token consumption when AI agents need to understand a codebase. Instead of reading entire files, agents issue semantic queries and receive only relevant code chunks with scores. The `--compact` flag further reduces output by ~80%.

2. **MCP Server Pattern Reference**: GrepAI's built-in MCP server is a production example of exposing CLI tool functionality through MCP. The 5-tool design (`search`, `trace_callers`, `trace_callees`, `trace_graph`, `index_status`) demonstrates how to decompose CLI functionality into discrete MCP tools with typed parameters.

3. **Subagent Architecture**: The `deep-explore` subagent pattern (created via `grepai agent-setup --with-subagent`) demonstrates how to provide specialized agents with access to external tools that the default Explore agent lacks.

4. **Call Graph Analysis for Refactoring**: Before refactoring, `trace callers` and `trace callees` can map impact before changes are made, complementing Claude Code's built-in Grep/Glob for understanding code relationships.

5. **Skills Distribution Model**: GrepAI ships 27 skills organized into 9 packs, distributed via `npx skills add` and as a Claude Code plugin. This is a reference implementation for how tool authors can provide AI agent guidance alongside their tools.

### Patterns Worth Adopting

1. **Semantic Search as MCP Tool**: Exposing semantic search through MCP rather than requiring agents to invoke shell commands. MCP tools inherit to subagents automatically; shell commands do not.

2. **Workspace-Aware Cross-Project Search**: The workspace abstraction that groups related projects and enables cross-project queries is a pattern for monorepo and multi-repo development workflows.

3. **Token-Efficient Output Formats**: The `--compact` and `--toon` flags demonstrate designing CLI output specifically for AI agent consumption, prioritizing information density over human readability.

4. **Agent Setup Automation**: `grepai agent-setup` auto-detects agent configuration files and appends instructions, demonstrating zero-friction integration with multiple AI tools.

### Integration Opportunities

1. **Direct MCP Integration**: Register `grepai mcp-serve` as an MCP server in Claude Code for semantic search capability during development sessions.

2. **Complement to Existing Search**: Use alongside Claude Code's built-in Grep for text pattern matching when semantic search provides higher precision for intent-based queries.

3. **Plugin Distribution Reference**: The skills marketplace integration (`/plugin marketplace add yoanbernabeu/grepai-skills`) demonstrates how third-party tools can distribute Claude Code plugins.

### Considerations

1. **Ollama Dependency**: Local mode requires Ollama running with an embedding model pulled. This adds infrastructure requirements beyond a single binary.

2. **Index Build Time**: Initial indexing requires generating embeddings for all code chunks. For large codebases, this may take significant time depending on hardware and embedding model.

3. **Go Binary Size**: Single binary distribution means no runtime dependencies, but the binary includes all supported backends and language parsers.

4. **Early Project**: Created 2026-01-09, 5 weeks old at time of research. API surface and configuration format may change rapidly.

---

## References

1. **GrepAI Website** - <https://yoanbernabeu.github.io/grepai/> (accessed 2026-02-13)
2. **GrepAI GitHub Repository** - <https://github.com/yoanbernabeu/grepai> (accessed 2026-02-13)
3. **GrepAI Installation Guide** - <https://yoanbernabeu.github.io/grepai/installation/> (accessed 2026-02-13)
4. **GrepAI MCP Integration** - <https://yoanbernabeu.github.io/grepai/mcp/> (accessed 2026-02-13)
5. **GrepAI Call Graph Analysis** - <https://yoanbernabeu.github.io/grepai/trace/> (accessed 2026-02-13)
6. **GrepAI Configuration Reference** - <https://yoanbernabeu.github.io/grepai/configuration/> (accessed 2026-02-13)
7. **GrepAI AI Agent Skills** - <https://yoanbernabeu.github.io/grepai/skills/> (accessed 2026-02-13)
8. **GrepAI Claude Code Subagent** - <https://yoanbernabeu.github.io/grepai/subagent/> (accessed 2026-02-13)
9. **GrepAI Agent Setup Command** - <https://yoanbernabeu.github.io/grepai/commands/grepai_agent-setup/> (accessed 2026-02-13)
10. **GrepAI Search Command** - <https://yoanbernabeu.github.io/grepai/commands/grepai_search/> (accessed 2026-02-13)
11. **GrepAI Quick Start** - <https://yoanbernabeu.github.io/grepai/quickstart/> (accessed 2026-02-13)
12. **GitHub API - Repository Metadata** - `gh repo view yoanbernabeu/grepai --json` (accessed 2026-02-13)
13. **GitHub API - Contributors** - `gh api repos/yoanbernabeu/grepai/contributors` (accessed 2026-02-13)
14. **GitHub API - Release Downloads** - `gh api repos/yoanbernabeu/grepai/releases` (accessed 2026-02-13)
15. **Reddit r/ollama** - <https://www.reddit.com/r/ollama/comments/1qiv7v8/> (accessed 2026-02-13)

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
| [SigMap](../developer-tools/sigmap.md) | developer-tools | Semantic code search with call graph analysis; shares SigMap's goal of AI-friendly code retrieval with embedding-based approach vs TF-IDF (bidirectional) |
