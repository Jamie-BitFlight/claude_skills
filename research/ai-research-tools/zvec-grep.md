---
title: "zvec-grep — Local-First Hybrid Workspace Search"
resource_url: "https://github.com/zvec-ai/zvec-grep"
resource_npm: "@zvec/zvec-grep"
research_date: "2026-09-11"
source_url: "https://github.com/zvec-ai/zvec-grep"
version_at_research: "0.2.1"
current_version: "0.2.1"
license: "Apache 2.0"
language: "TypeScript/JavaScript"
freshness_tracking:
  last_verified: "2026-09-11"
  version_at_verification: "0.2.1"
  next_review: "2026-12-11"
  confidence:
    identity_metadata: "high"
    features: "high"
    architecture: "high"
    usage_examples: "high"
    limitations: "medium"
---

## Overview

**zvec-grep** is a local-first search layer designed for both humans and AI agents. It unifies ripgrep (exact text and regex search), BM25 (lexical ranking), and vector search (semantic retrieval) behind a single interface. The tool is published as the npm package `@zvec/zvec-grep` (v0.2.1) and is licensed under Apache 2.0. Written in TypeScript, it requires Node.js 22 or newer.

According to the README, zvec-grep is "powered by [zvec](https://github.com/alibaba/zvec), unifies ripgrep, BM25, and vector search behind one local-first interface." Users can search from the terminal directly or allow AI agents (via MCP integration) to search on their behalf.

## Problem Addressed

Agents and developers struggle to find relevant code and documentation across large workspaces using keyword search alone. The tool solves four specific problems:

1. **Keyword limitations**: Queries often fail when exact keywords are not known in advance, especially for architectural questions that cross multiple files and modules.

2. **Context bloat in agent systems**: Baseline retrieval approaches require many tool calls, produce noisy results, and consume excessive model context tokens.

3. **Format fragmentation**: Real workspaces contain source code, configuration files, documentation, and data; a single search tool should handle all formats while preserving structure.

4. **Privacy and control**: Remote-first search systems send workspace content to external services, violating data residency requirements and increasing latency.

The README states: "zg works best when evidence spans files or modules and the target location is unknown, especially for call-chain, data-flow, and architectural questions."

## Key Features

### Hybrid Search with Multiple Retrieval Paths

zvec-grep offers three search modes that can be combined:

- **Lexical (BM25)**: Ranked keyword and phrase matching via BM25. Selected with `--fts <query>`.
- **Vector (semantic)**: Embedding-based similarity search. Selected with `--vector <query>`.
- **Exact/Regex (ripgrep)**: Exhaustive text or regex matching via `@vscode/ripgrep` (managed). Invoked with `--rg`.

These modes can be mixed: `zg --fts "loadTheme" --vector "where user prefs are restored" --fuse` combines multiple groups and fuses results into a single ranked output. According to the benchmarks, this approach reduces tool calls, input tokens, and agent reasoning time compared to baseline retrieval.

### Agent Integration (MCP)

The tool exposes an MCP (Model Context Protocol) server endpoint on localhost via the local daemon. Agents (Claude Code, Codex, Qwen Code, Qoder, OpenCode, Cursor) can call `zvec_grep_search` with a query and receive ranked results. Installation is one command: `zg --install --target claude --yes`. The MCP interface supports:

- **Symbol-aware retrieval**: Prefer exact matches on function names, class names, or module identifiers with `--prefer-symbol`.
- **Symbol type filtering**: Restrict results to `module`, `class`, `interface`, `function`, `value`, or `alias`.
- **Time-based filtering**: Search files modified before or after a timestamp with `--modified-before` and `--modified-after`.

### Multi-Format Indexing and Search

The tool indexes and searches across multiple content types:

- **Source code**: Symbols (functions, classes, modules) are extracted and indexed; search results preserve line references and context.
- **Structured data**: JSON, YAML, and TOML are partially parsed; search results link to document structures.
- **Plain text and prose**: Documents are chunked and indexed for retrieval; results return focused sections with full source location.

Per the README: "Multi-format search — search source code, documents, and structured data while preserving useful structure and source locations."

### Configurable Embedding Models

Instead of hardcoding one embedding service, zvec-grep lets users choose:

- **Local embedding**: `local/potion-retrieval-32m` and other Potion models run on CPU/GPU without sending data outside the machine. Potion models default to 2 worker threads; `--embedding-concurrency <n>` scales this.
- **Remote embedding**: Hugging Face, Qwen, and others can be configured; data is sent only when the user explicitly authorizes with `--allow-remote`.
- **Per-index model**: Each indexed workspace stores its embedding model preference; changing it requires `zg --index --rebuild --embedding <model>`.

### Index Refresh Strategies

The tool offers three refresh modes to keep search results up-to-date:

- `--refresh wait`: Block the search until pending index updates complete (default).
- `--refresh background`: Return stale results immediately while reindexing in the background.
- `--refresh off`: Skip index refresh and return only cached results.

### Command-Line Interface (CLI)

The primary `zg` command is a search interface; maintenance operations use long action flags to avoid collisions with natural query words (e.g., `zg --index`, `zg --status`, `zg --install`). Positional arguments are always interpreted as search queries.

Core commands:
- `zg <query>`: Hybrid search (lexical + vector by default).
- `zg --index [root]`: Build, update, or drop the workspace index.
- `zg --status [root]`: Inspect index state and readiness.
- `zg --install --target <agent>`: Integrate with a specific agent (claude, codex, qwen, qoder, opencode, cursor, or all).
- `zg --config provider set <name> --api-key <key>`: Store embedding provider credentials.
- `zg --server`: Manage the local MCP server (start, stop, status, logs).

Example searches from the README:

```bash
zg "theme preference persistence on startup"
zg --fts "loadTheme" -g "src/**" -t ts
zg --vector "where user preferences are restored" --limit 5
zg "plugin lifecycle" --preview full
zg --rg -i -C 2 -g "*.ts" "dark mode" src
```

### Server and Execution Modes

zvec-grep can run as:

1. **Auto mode** (default): Starts a long-running daemon if needed; subsequent commands reuse it for faster response times.
2. **Server mode**: Explicitly starts or connects to the shared MCP server.
3. **Direct mode**: Runs each search in a new process without a persistent daemon.

All three modes call the same search engine; the difference is process lifetime and coordination overhead. MCP requests always arrive through the Server.

## Technical Architecture

### System Overview

The architecture diagram from `docs/05-architecture.md` shows:

```text
Human or script → zg CLI → auto / server / direct → Local Server
Agent → MCP client →                               → Engine
        → Direct runtime

Server and Direct routes both call:
  zvec-grep engine
    ├── Indexed search (BM25 + vector + RRF)
    ├── Managed ripgrep (exact text + regex)
    └── Indexing (scan + extract + embed)

Workspace files → Managed ripgrep
                → Indexing → Workspace index (.zvec-grep/)
                Workspace index → Indexed search → Results
                Managed ripgrep → Results
```

### Core Components

**Entry points**:
- **CLI** (`src/cli/`): Parses command-line arguments, routes to the appropriate action, and formats results for terminal output.
- **MCP Server** (`src/daemon/http-server.ts`): Exposes the search interface as HTTP-based MCP tools for agent consumption.

**Daemon and execution**:
- **Daemon** (`src/daemon/`): Long-running server process that coordinates indexing, watches file changes, manages the embedding model pool, and serves MCP requests.
  - `server-controller.ts`: Lifecycle and coordination.
  - `http-server.ts`: HTTP server for MCP transport.
  - `job-scheduler.ts`: Schedules indexing and embedding jobs.
  - `watch-manager.ts`: Monitors file system changes.
  - `model-pool.ts`: Manages embedding model instances and concurrency.
  - `workspace-read-session-cache.ts`: Caches file reads to reduce disk I/O.
  - `config.ts`: Persists and loads configuration.

**Retrieval and indexing**:
- **zvec library** (`@zvec/zvec` v0.7.0): Rust-based vector database with SQLite backend. Stores embeddings, metadata, and supports similarity search.
- **Ripgrep** (`@vscode/ripgrep` v1.18.0): Lexical and regex search via the VS Code ripgrep package.
- **Tree-sitter** (`web-tree-sitter` v0.20.8, `tree-sitter-wasms` v0.1.13): AST parsing for symbol extraction (functions, classes, modules).

**Ranking and fusion**:
- **Reciprocal Rank Fusion (RRF)**: When multiple search groups are queried (e.g., `--fts` + `--vector`), results are merged and re-ranked by reciprocal rank to balance diverse evidence.

**Embedding**:
- **Hugging Face Transformers** (`@huggingface/transformers` v3.8.1) and **Hugging Face Tokenizers** (`@huggingface/tokenizers` v0.1.3): Support for local embedding models (Potion, Jina) and remote providers.
- **Web Assembly (WASM)**: Local embeddings run in WASM threads to parallelize inference on multi-core systems.

**MCP Protocol**:
- **MCP Server** (`@modelcontextprotocol/server` v2.0.0), **Core** (v2.0.0), **Node** (v2.0.0): Implements the Model Context Protocol for agent communication.

**Schema and configuration**:
- **Zod** (v4.2.0): Validates configuration objects, query parameters, and MCP payloads.
- **JSONC Parser** (`jsonc-parser` v3.3.1): Reads `.zvec-grep/config.json` with comment support.

### Data Flow

1. **Indexing**: When `zg --index` runs, the engine scans workspace files (respecting `.gitignore`), extracts symbols and text chunks via tree-sitter and custom extractors, embeds them using the selected model, and stores embeddings + metadata in the `.zvec-grep/index/` directory (backed by the zvec database).

2. **Search**: A query is routed through the selected retrieval paths:
   - Lexical results are fetched from the index and ranked by BM25 score.
   - Vector results are computed by embedding the query and finding nearest neighbors in the zvec database.
   - Ripgrep results are computed by scanning the workspace with the supplied pattern.
   - Results are merged, deduplicated, and ranked by reciprocal rank fusion if multiple groups exist.

3. **Output**: Results include file paths, line ranges, snippet previews, symbol names, and relevance scores. The CLI formats them as readable text or JSON; the MCP server formats them according to the MCP response schema.

### Storage and Trust Boundary

Per `docs/05-architecture.md`:
- **Workspace index**: Stored in `.zvec-grep/` under the indexed project root. Includes embeddings, symbol metadata, and file checksums.
- **Configuration**: Stored in `~/.zvec-grep/config.json` (global). Includes provider credentials, model preferences, and per-index overrides.
- **Local by default**: Files and local embeddings stay on disk; remote embeddings require explicit user permission via `--allow-remote` or interactive confirmation.

### Extension Points

**Agent integrations**: The `--install` and `--uninstall` commands manage MCP tool registrations in agent configuration files (e.g., `.claude/config.json` for Claude Code, `coder_settings.json` for Qoder).

**Embedding provider abstraction**: New providers can be added to the configuration without code changes by setting `--config provider set <name> --api-key <key>` and referencing them as `<name>/<model>`.

**File type filtering**: The CLI accepts ripgrep-compatible file type flags (`-t`, `-T`, `-g`, `--iglob`), which are passed through to the ripgrep and indexing routines.

## Installation & Usage

### Prerequisites

- Node.js 22 or newer (checked at runtime; `npm` will warn if an older version is detected).
- For local embedding models: at least 2 GB of free disk space for model downloads and at least 4 GB of RAM.

### Installation

Install the npm package globally:

```bash
npm install -g @zvec/zvec-grep
```

The `zg` command will be available in your shell.

### Quick Start

1. **Index a workspace**:

   ```bash
   cd /path/to/my/workspace
   zg --index --embedding local/potion-retrieval-32m
   ```

   This scans the workspace, downloads the embedding model (if not cached), and builds the index in `.zvec-grep/`.

2. **Search from the terminal**:

   ```bash
   zg "theme preference persistence on startup"
   ```

   Results are printed with file paths, line numbers, snippets, and relevance scores.

3. **Integrate with an agent** (e.g., Claude Code):

   ```bash
   zg --install --target claude --yes
   ```

   The MCP server is registered in `~/.claude/config.json` and will start automatically when Claude Code needs it.

4. **Use from an agent prompt**:
   Once installed, agents automatically decide when and how to search. For example:

   ```text
   # In Claude Code or OpenCode
   "An unseen creature left a few marks. What did the detective infer? Cite local evidence."
   ```

   The agent calls `zvec_grep_search` and receives ranked results from the indexed workspace.

### Configuration Examples

**Configure a remote embedding provider**:

```bash
zg --config provider set qwen --api-key "$DASHSCOPE_API_KEY"
zg --config model set qwen/text-embedding-v4 --default
zg --index --embedding qwen/text-embedding-v4
```

**Search with multiple query groups**:

```bash
zg --fts "loadTheme" --vector "where theme is restored" --fuse --limit 10
```

**Search only recent changes**:

```bash
zg "plugin lifecycle" --modified-after "2 weeks ago"
```

**Use ripgrep directly (no index)**:

```bash
zg --rg -i -C 2 -g "*.ts" "dark mode" src/
```

### Help and Debugging

The CLI is self-documenting:

```bash
zg --help                    # General help
zg --help search             # Search command help
zg --help index              # Indexing help
zg --help models             # List available embedding models
zg --help file-types         # List supported file types
```

If a command fails, rerun it with `--debug` to see detailed diagnostics:

```bash
zg "query" --debug
zg --index --debug
zg --server status --debug
```

## Relevance to Claude Code Development

zvec-grep is directly relevant to Claude Code development in several ways:

1. **Agent information retrieval**: Claude Code agents need to search large codebases efficiently. zvec-grep's ranked, multi-modal retrieval reduces token consumption and improves answer quality compared to naive keyword search or baseline RAG.

2. **MCP integration example**: zvec-grep demonstrates how to build a production-grade MCP server that exposes domain-specific tools (search, indexing, status) to agents. The implementation includes HTTP transport, tool schemas, error handling, and authentication—useful patterns for other MCP integrations.

3. **Hybrid retrieval patterns**: The combination of BM25, vector search, and ripgrep in a single tool shows how to layer different retrieval strategies. This is applicable to other domains (documentation search, issue tracking, configuration management).

4. **Local-first architecture**: The design keeps data on the user's machine by default, with optional remote services. This pattern is valuable for privacy-sensitive agent workflows.

5. **Multi-agent compatibility**: zvec-grep supports Claude Code, Codex, Qwen Code, Qoder, OpenCode, and Cursor. This demonstrates how to build tooling that works across the agent ecosystem, relevant for plugin developers.

## Limitations and Caveats

**Work-in-progress status**: The README and docs explicitly state: "zvec-grep is a work in progress. Commands and configuration may change before the first stable release." This means the CLI, configuration format, and MCP tool interface may break between versions before v1.0.

**Version 0.2.1 current as of 2026-09-11**: The published version is `0.2.1`. Checking `npm view @zvec/zvec-grep versions` or the GitHub releases page will show the latest available version.

**Node.js 22 requirement**: The tool requires Node.js 22 or newer. This is a hard requirement checked at runtime. Users on Node.js 20 or 21 cannot use it without upgrading.

**Embedding model downloads**: Local embedding models are downloaded on demand (e.g., Potion models are 10–100 MB each depending on size). First-run indexing on a large workspace may take several minutes while embedding tasks run on worker threads.

**Index storage and space**: The `.zvec-grep/index/` directory contains embeddings and metadata. For a typical large repository (e.g., Django or Matplotlib), this can range from 100 MB to several GB depending on the embedding model and indexing settings. The index is stored in SQLite and is not human-readable.

**Ripgrep compatibility**: The `--rg` mode is managed ripgrep (not a shell invocation), so shell-specific features (pipes, redirects, subshells) are not supported. However, standard ripgrep flags (`-i`, `-C`, `-g`, `--type`, etc.) work as expected.

**No limitations documented regarding**: search accuracy per query type, maximum workspace size, or minimum performance guarantees. The benchmarks show improvements over baseline on three large codebases (Pylint, Matplotlib, Django), but generalization to other domains is not guaranteed.

## References

- **GitHub Repository**: <https://github.com/zvec-ai/zvec-grep> (accessed 2026-09-11)
- **npm Package**: <https://www.npmjs.com/package/@zvec/zvec-grep> (accessed 2026-09-11)
- **Official Documentation**:
  - [Agent integrations](https://github.com/zvec-ai/zvec-grep/blob/main/docs/01-agents.md) (accessed 2026-09-11)
  - [CLI guide](https://github.com/zvec-ai/zvec-grep/blob/main/docs/02-cli.md) (accessed 2026-09-11)
  - [MCP guide](https://github.com/zvec-ai/zvec-grep/blob/main/docs/03-mcp.md) (accessed 2026-09-11)
  - [Retrieval pipeline](https://github.com/zvec-ai/zvec-grep/blob/main/docs/04-pipeline.md) (accessed 2026-09-11)
  - [Architecture](https://github.com/zvec-ai/zvec-grep/blob/main/docs/05-architecture.md) (accessed 2026-09-11)
  - [Server and execution modes](https://github.com/zvec-ai/zvec-grep/blob/main/docs/06-server.md) (accessed 2026-09-11)
  - [Embedding models](https://github.com/zvec-ai/zvec-grep/blob/main/docs/07-embedding.md) (accessed 2026-09-11)
  - [Roadmap](https://github.com/zvec-ai/zvec-grep/blob/main/docs/08-roadmap.md) (accessed 2026-09-11)
- **Benchmarks**:
  - [SWE-QA-Bench](https://github.com/zvec-ai/zvec-grep/tree/main/benchmarks/swe-qa-bench) (accessed 2026-09-11) — Claude Code + Opus 5 retrieval evaluation
  - [BrowseComp-Plus](https://github.com/zvec-ai/zvec-grep/tree/main/benchmarks/browse-comp-plus) (accessed 2026-09-11) — Codex gpt-5.6-sol retrieval evaluation
- **Contributing Guide**: <https://github.com/zvec-ai/zvec-grep/blob/main/CONTRIBUTING.md> (accessed 2026-09-11)
- **License**: Apache License 2.0 (<https://github.com/zvec-ai/zvec-grep/blob/main/LICENSE>) (accessed 2026-09-11)

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [zvec](../ml-infrastructure/zvec.md) | ml-infrastructure | vector database library used as the underlying embedding storage layer |
| [CocoIndex Code](../mcp-ecosystem/cocoindex-code.md) | mcp-ecosystem | competing MCP-based semantic code search with AST-based symbol extraction |
| [Grepai](../developer-tools/grepai.md) | developer-tools | alternative semantic code search tool with call graph analysis for agents |
| [Samuraizer](./samuraizer.md) | ai-research-tools | full-stack knowledge base with semantic search and RAG chat patterns |
| [SourceSync.ai](../context-management/sourcesyncai.md) | context-management | managed RAG platform using hybrid search with multi-source retrieval |
| [Chroma](../data-infrastructure/chroma.md) | data-infrastructure | vector database with HNSW/Spann indices and hybrid search support |
| [Jina AI](../context-management/jina-ai.md) | context-management | embeddings and reranking infrastructure supporting multi-modal search systems |
| [Kythe](../developer-tools/kythe.md) | developer-tools | code intelligence platform with language-agnostic AST-based symbol extraction |
