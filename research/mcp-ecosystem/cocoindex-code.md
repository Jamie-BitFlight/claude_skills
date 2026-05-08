# CocoIndex Code

**Research Date**: 2026-03-10
**Source URL**: <https://github.com/cocoindex-io/cocoindex-code>
**GitHub Repository**: <https://github.com/cocoindex-io/cocoindex-code>
**Version at Research**: 0.1.0
**License**: Apache-2.0

---

## Overview

CocoIndex Code is a lightweight, embedded Model Context Protocol (MCP) server that enables semantic code search within codebases using AST-based analysis. Built on the Rust-based CocoIndex data transformation engine, it integrates directly with AI coding agents (Claude Code, Codex, Cursor) to find relevant code by meaning rather than exact text matching, achieving approximately 70% token savings for code retrieval tasks. The tool requires zero configuration and works entirely embedded without external databases.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Coding agents cannot find code through semantic meaning when exact keywords are unknown | Provides semantic code search using embeddings and AST analysis; accepts natural language queries and code snippets |
| Traditional grep-based code search fails on fuzzy, conceptual, or descriptive queries | Returns code chunks ranked by semantic similarity score (0-1 scale) rather than exact keyword matching |
| Code retrieval inflates token consumption in AI agent workflows | Optimized code indexing and retrieval reduces token usage by ~70% through efficient chunking and embedding-based retrieval |
| Exploring unfamiliar codebases requires manual navigation and reading | Agents can automatically discover related code patterns, implementations, and functionality without knowing exact names |
| Setup complexity discourages adoption in agent tooling | Single-command installation via `pipx` or `uv`; zero configuration with automatic codebase root discovery via `.git/` or `.cocoindex_code/` markers |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 337 | 2026-03-10 |
| GitHub Forks | 23 | 2026-03-10 |
| Open Issues | 7 | 2026-03-10 |
| Latest Commit | 2c038e6 (chore: upgrade cocoindex to v1.0.0a26) | 2026-03-07 |
| Project Version | 0.1.0 | 2026-03-10 |
| Python Requirement | >=3.11 | 2026-03-10 |
| License | Apache-2.0 | 2026-03-10 |

---

## Key Features

### Semantic Code Search

- **Natural language queries**: Search by description (e.g., "authentication logic", "database connection handling") rather than exact keywords
- **Code snippet matching**: Paste code snippets to find similar implementations in the codebase
- **Similarity scoring**: Returns results ranked by relevance score (0-1 scale, higher indicates better match)
- **Pagination support**: `limit` parameter (1-100) and `offset` parameter for iterating through large result sets
- **Automatic index refresh**: Default behavior refreshes index before querying to include recent changes; configurable via `refresh_index` parameter

### Multi-Language Support

Supports 30+ programming languages including: Python, JavaScript/TypeScript, Rust, Go, Java, C/C++, C#, SQL, Shell, PHP, Ruby, R, Kotlin, Scala, Swift, Fortran, Pascal, and markup languages (HTML, CSS, XML, Markdown, YAML, TOML, JSON). Automatically excludes common generated directories (`__pycache__/`, `node_modules/`, `target/`, `dist/`, `vendor/`).

### Embedding Model Flexibility

- **Default**: Local SentenceTransformers (`sentence-transformers/all-MiniLM-L6-v2`) — no API key required, completely free
- **GPU-optimized option**: `nomic-ai/CodeRankEmbed` for significantly better code retrieval (137M parameters, ~1 GB VRAM)
- **100+ cloud providers supported** via LiteLLM: OpenAI, Azure OpenAI, Gemini, Mistral, Voyage (code-optimized), Cohere, AWS Bedrock, Ollama, Nebius
- **Model switching**: Supported via environment variable `COCOINDEX_CODE_EMBEDDING_MODEL`

### Incremental Indexing

- **Change-only indexing**: Built on Rust engine that only re-indexes modified files rather than entire codebase
- **Fast updates**: Minimal latency for index refresh on subsequent queries
- **Embedded architecture**: No database required; all state stored locally in SQLite with vector extensions

### Zero-Configuration Integration

- **MCP server mode**: One-line registration with Claude Code, Codex, Cursor, or OpenCode
- **Automatic codebase discovery**: Discovers root path via nearest `.cocoindex_code/` marker, `.git/` directory, or current working directory
- **Environment-based configuration**: Three environment variables control all behavior: `COCOINDEX_CODE_ROOT_PATH`, `COCOINDEX_CODE_EMBEDDING_MODEL`, `COCOINDEX_CODE_BATCH_SIZE`, `COCOINDEX_CODE_EXTRA_EXTENSIONS`

---

## Technical Architecture

CocoIndex Code follows the MCP (Model Context Protocol) server architecture pattern, implemented as a single tool provider (`search`) that agents invoke through the protocol.

**Core Components** (extracted from source):

1. **Server Module** (`server.py`): FastMCP server initialization with tool registration and async index refresh locking
2. **Indexer Module** (`indexer.py`): Manages index creation and updates via the CocoIndex Rust engine
3. **Query Module** (`query.py`): Executes semantic searches against indexed codebase
4. **Config Module** (`config.py`): Reads environment variables and constructs configuration
5. **Schema Module** (`schema.py`): Pydantic models for tool inputs and structured outputs

**Data Flow**:

```
Agent Query (natural language or code snippet)
    ↓
MCP Tool: search(query, limit, offset, refresh_index)
    ↓
[Optional] Refresh Index (_refresh_index async function with lock)
    ├─ CocoIndex Rust engine detects changed files
    ├─ Re-indexes only modified code chunks
    └─ Writes updated embeddings to SQLite with vector extensions
    ↓
Query Execution (query_codebase function)
    ├─ Embed query string using configured embedding model
    ├─ Vector similarity search in SQLite
    └─ Return top K results (CodeChunkResult: file_path, language, content, line numbers, score)
    ↓
Agent receives structured SearchResultModel
    ├─ success: bool
    ├─ results: list[CodeChunkResult]
    ├─ total_returned: int
    ├─ offset: int
    └─ message: str | None
```

**Storage**: SQLite with `sqlite-vec` extension for efficient vector similarity search. No separate database server required.

**Concurrency Model**: Async-based with asyncio.Lock for preventing concurrent index updates during refresh operations.

---

## Installation & Usage

### Installation

Using `pipx` (recommended for isolated tool installation):

```bash
pipx install cocoindex-code       # first install
pipx upgrade cocoindex-code       # upgrade
```

Using `uv` (Astral tool manager):

```bash
uv tool install --upgrade cocoindex-code --prerelease explicit --with "cocoindex>=1.0.0a24"
```

### MCP Server Registration

**Claude Code**:

```bash
claude mcp add cocoindex-code -- cocoindex-code
```

**Codex**:

```bash
codex mcp add cocoindex-code -- cocoindex-code
```

**OpenCode**:

```bash
opencode mcp add
# Then select: type=local, command=cocoindex-code
```

Or via `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "cocoindex-code": {
      "type": "local",
      "command": ["cocoindex-code"]
    }
  }
}
```

### Optional Index Management

```bash
# Explicitly create or update the index (optional; MCP auto-refreshes)
cocoindex-code index
```

### Usage in Agent Prompts

Once registered, agents automatically decide when semantic search is useful. Explicit hints can be added to `AGENTS.md` or `CLAUDE.md`:

```markdown
Use the cocoindex-code MCP server for semantic code search when:
- Searching for code by meaning or description rather than exact text
- Exploring unfamiliar parts of the codebase
- Looking for implementations without knowing exact names
- Finding similar code patterns or related functionality
```

### Configuration via Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `COCOINDEX_CODE_ROOT_PATH` | Root path of codebase to index | Auto-discovered (`.git/`, `.cocoindex_code/`, or CWD) | `/path/to/project` |
| `COCOINDEX_CODE_EMBEDDING_MODEL` | Embedding model identifier | `sbert/sentence-transformers/all-MiniLM-L6-v2` | `ollama/nomic-embed-text` |
| `COCOINDEX_CODE_BATCH_SIZE` | Max batch size for local embedding model | `16` | `32` |
| `COCOINDEX_CODE_EXTRA_EXTENSIONS` | Additional file extensions to index (comma-separated) | _(none)_ | `inc:php,yaml,toml` |

### Setting Custom Embedding Model (Example with Ollama)

```bash
claude mcp add cocoindex-code \
  -e COCOINDEX_CODE_EMBEDDING_MODEL=ollama/nomic-embed-text \
  -- cocoindex-code
```

Set `OLLAMA_API_BASE=http://localhost:11434` if Ollama is not at default location.

### API Tool Schema (from source code)

The `search` tool accepts:

```python
async def search(
    query: str,              # Natural language or code snippet
    limit: int = 5,          # Results to return (1-100)
    offset: int = 0,         # Pagination offset
    refresh_index: bool = True  # Refresh before search
) -> SearchResultModel
```

Returns:

```python
{
    "success": bool,
    "results": [
        {
            "file_path": str,      # Relative file path
            "language": str,       # Detected language
            "content": str,        # Code snippet
            "start_line": int,     # 1-indexed start line
            "end_line": int,       # 1-indexed end line
            "score": float         # Similarity score (0-1)
        }
    ],
    "total_returned": int,
    "offset": int,
    "message": str | None
}
```

---

## Limitations and Caveats

### Platform / Environment Limitations

**macOS SQLite issue**: Pre-installed Python on macOS ships with a SQLite library that does not enable extensions (required for vector search). Documented workaround: install Python via Homebrew (`brew install python3`), then reinstall cocoindex-code. This is a known platform limitation documented in the project's troubleshooting section.

### Model Switching Requires Re-indexing

When switching embedding models, the codebase must be re-indexed because vector dimensions differ between models. This incurs a one-time re-indexing cost.

### Batch Size Configuration

Local embedding models require explicit `COCOINDEX_CODE_BATCH_SIZE` tuning for GPU-optimized models. Default of `16` is conservative; larger batches improve throughput but require sufficient VRAM.

### File Extension Coverage

Common generated directories are automatically excluded (`node_modules/`, `__pycache__/`, etc.), but custom exclusions or extensions require environment variable configuration (`COCOINDEX_CODE_EXTRA_EXTENSIONS`).

### Enterprise Scale

The project documentation references large codebase and enterprise scenarios handled by the parent CocoIndex project (which operates on "XXX G" codebases with features like branch deduplication), suggesting the current cocoindex-code MCP may have practical limits on codebase size not explicitly documented. Contact <linghua@cocoindex.io> for enterprise guidance.

---

## Relevance to Claude Code Development

### Applications

- **Code navigation in unfamiliar modules**: When Claude Code encounters a new or complex module, cocoindex-code enables semantic exploration without reading entire files or relying on grep patterns
- **Pattern discovery**: Agents can find implementations of similar patterns (error handling, database queries, API calls) across the codebase, supporting code generation with consistency
- **API/interface discovery**: Search natural language descriptions (e.g., "how are users authenticated?" or "database connection setup") to locate relevant implementations without knowing module names
- **Refactoring assistance**: Identify all usages and variations of a pattern or data structure through semantic similarity, not just text search
- **Documentation-free exploration**: For poorly documented codebases, semantic search fills gaps that grep-based exploration cannot address

### Patterns Worth Adopting

- **Zero-configuration MCP servers**: CocoIndex Code's approach to automatic root discovery and environment-based configuration (no YAML config files) minimizes setup friction for users
- **Incremental indexing with change detection**: Only re-processing changed files rather than full re-indexing is a scalability pattern applicable to other code analysis tools
- **Flexible embedding models**: Supporting both free local models and paid cloud providers via a single environment variable balances cost and quality without forcing a single approach
- **Structured return types**: Using Pydantic models for tool outputs ensures type safety and clear schema documentation for agents

### Integration Opportunities

- **Claude Code marketplace skill**: A skill wrapping cocoindex-code's search tool could provide higher-level abstractions (e.g., "find all error handlers", "locate database queries") atop the raw semantic search
- **Context-aware code embedding**: Integration with Claude Code's context management system could cache code embeddings across sessions, avoiding re-indexing on repeated agent runs
- **MCP tool composition**: Combining cocoindex-code with other MCP tools (file reading, grep-based search) in a multi-tool skill could provide both semantic and text-based search capabilities
- **Agent skill library**: Publishing cocoindex-code as a Claude Code skill would make semantic code search available to all agents in the Claude ecosystem without per-project installation

---

## References

- [CocoIndex Code GitHub Repository](https://github.com/cocoindex-io/cocoindex-code) (accessed 2026-03-10)
- [CocoIndex Code README](https://github.com/cocoindex-io/cocoindex-code/blob/main/README.md) (accessed 2026-03-10)
- [CocoIndex Code pyproject.toml](https://github.com/cocoindex-io/cocoindex-code/blob/main/pyproject.toml) (accessed 2026-03-10)
- [CocoIndex Parent Project](https://github.com/cocoindex-io/cocoindex) (referenced as parent data transformation engine, accessed 2026-03-10)
- [GitHub API: cocoindex-io/cocoindex-code Repository](https://api.github.com/repos/cocoindex-io/cocoindex-code) (accessed 2026-03-10)

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-10 |
| Version at Verification | 0.1.0 (pyproject.toml) / cocoindex dependency 1.0.0a26 |
| Next Review Recommended | 2026-06-10 |
| Confidence: Identity/Metadata | high |
| Confidence: Features | high |
| Confidence: Architecture | high |
| Confidence: Installation/Usage | high |
| Confidence: Limitations | medium |

**Confidence Rationale**:

- **High confidence** for identity, features, and installation: Full README read, pyproject.toml specifications verified, official documentation accessed
- **High confidence** for architecture: Source code structure examined (`server.py`, core module organization) and MCP protocol documentation available
- **Medium confidence** for limitations: SQLite issue on macOS documented; enterprise-scale limitations referenced but not detailed. Absence of documented limitations for other scenarios does not confirm absence of limitations

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [SigMap](../developer-tools/sigmap.md) | developer-tools | referenced by SigMap (developer-tools) |
