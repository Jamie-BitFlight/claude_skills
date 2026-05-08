# GitNexus

**Identity**: GitNexus: Code Intelligence Engine

**Version**: 1.4.6 (CLI/npm package); latest commit 2026-03-18

**Repository**: <https://github.com/abhigyanpatwari/GitNexus>

**Live Demo**: <https://gitnexus.vercel.app>

**License**: PolyForm Noncommercial 1.0.0

**Primary Language**: TypeScript

**GitHub Statistics** (accessed 2026-03-19):
- **Stars**: 17,498
- **Forks**: 1,999
- **Open Issues**: 156
- **Contributors**: Not queried
- **First Commit**: 2025-08-02
- **Last Update**: 2026-03-19

---

## Overview

GitNexus is a **client-side code intelligence platform** that indexes codebases into knowledge graphs and exposes them through MCP (Model Context Protocol) tools and a web UI. It is designed to give AI agents deep architectural awareness of codebases without relying on external services—all processing happens locally (CLI) or in-browser (web UI).

The core value proposition is **precomputed relational intelligence**: instead of forcing LLMs to explore graphs through multiple queries, GitNexus precomputes clustering, tracing, and scoring at index time, returning complete context in a single tool call. This makes smaller LLMs competitive by moving heavy reasoning from the LLM to the indexing pipeline.

**TL;DR (from README)**: The Web UI is a quick way to chat with any repo. The CLI + MCP is how you make your AI agent actually reliable—it gives Cursor, Claude Code, and friends a deep architectural view of your codebase so they stop missing dependencies, breaking call chains, and shipping blind edits.

---

## Problem Addressed

AI coding assistants (Cursor, Claude Code, Cline, Roo Code, Windsurf) are powerful but lack true codebase structure awareness. Typical scenario:

1. AI edits `UserService.validate()`
2. Does not know 47 functions depend on its return type
3. Breaking changes ship undetected

Traditional graph RAG approaches give LLMs raw graph edges and hope they explore sufficiently. GitNexus **precomputes structure at index time**—clustering, tracing, scoring—so tools return complete context in one call.

---

## Key Statistics

| Metric | Value | Source |
|--------|-------|--------|
| **GitHub Stars** | 17,498 | GitHub API (2026-03-19) |
| **Forks** | 1,999 | GitHub API (2026-03-19) |
| **Open Issues** | 156 | GitHub API (2026-03-19) |
| **Current CLI Version** | 1.4.6 | package.json, gitnexus package |
| **Languages Supported** | 13+ | README language support matrix |
| **MCP Tools Exposed** | 7 | README section "What Your AI Agent Gets" |
| **Age** | ~7 months (Aug 2025 - Mar 2026) | Git history (created_at field) |

---

## Key Features

### 1. Dual Interface: CLI + MCP and Web UI

**CLI + MCP (Recommended)**:
- Index repositories locally via `npx gitnexus analyze`
- Runs an MCP server that connects AI agents (Claude Code, Cursor, Windsurf, OpenCode, Codex)
- Full codebase support—any size, any language
- Storage: LadybugDB native (fast, persistent)
- Parsing: Tree-sitter native bindings
- Privacy: Everything local, no network calls
- Mechanism: CLI indexes the repo, stores index in `.gitnexus/` (gitignored), registers in global registry `~/.gitnexus/registry.json`. MCP server reads registry and serves all indexed repos via connection pool with lazy open/evict logic (max 5 concurrent, 5-minute idle eviction).

**Web UI**:
- Browser-based graph explorer + AI chat
- No install required: [gitnexus.vercel.app](https://gitnexus.vercel.app)
- Drag & drop GitHub repos or ZIP files
- Storage: LadybugDB WASM (in-memory per session)
- Parsing: Tree-sitter WASM
- Browser memory limit: ~5k files (or unlimited via backend mode)
- Privacy: Everything in-browser, no server
- Mechanism: Same indexing pipeline as CLI, runs entirely in WebAssembly

**Bridge Mode** ("Local Backend Mode"):
- Run `gitnexus serve` to start local HTTP server
- Web UI auto-detects the server and can browse all CLI-indexed repos without re-uploading or re-indexing
- Agent tools (Cypher queries, search, code navigation) route through backend HTTP API automatically

---

### 2. Multi-Language Support (13 languages)

Extracted from README language support matrix:

| Language | Coverage | Details |
|----------|----------|---------|
| **TypeScript** | Complete | Imports, named bindings, exports, heritage, type annotations, constructor inference, config, frameworks, entry points |
| **JavaScript** | Complete | Imports, named bindings, exports, heritage, constructor inference, config, frameworks, entry points (no type annotations) |
| **Python** | Complete | Imports, named bindings, exports, heritage, type annotations, constructor inference, config, frameworks, entry points |
| **Java** | Complete | Imports, named bindings, exports, heritage, type annotations, constructor inference, frameworks, entry points (no config) |
| **Kotlin** | Complete | Imports, named bindings, exports, heritage, type annotations, constructor inference, frameworks, entry points (no config) |
| **C#** | Complete | Imports, named bindings, exports, heritage, type annotations, constructor inference, config, frameworks, entry points |
| **Go** | High | Imports, exports, heritage, type annotations, constructor inference, config, frameworks, entry points (no named bindings) |
| **Rust** | Complete | Imports, named bindings, exports, heritage, type annotations, constructor inference, frameworks, entry points (no config) |
| **PHP** | High | Imports, named bindings, exports, type annotations, constructor inference, config, frameworks, entry points (no heritage) |
| **Ruby** | Medium | Imports, exports, heritage, constructor inference, frameworks, entry points (no named bindings, no type annotations) |
| **Swift** | Medium | Exports, heritage, type annotations, constructor inference, config, frameworks, entry points (no imports, no named bindings) |
| **C** | Low | Exports, type annotations, constructor inference, frameworks, entry points (no imports, no named bindings, no heritage, no config) |
| **C++** | Low | Exports, heritage, type annotations, constructor inference, frameworks, entry points (no imports, no named bindings, no config) |

Feature coverage legend:
- **Imports** — cross-file import resolution
- **Named Bindings** — `import { X as Y }` / re-export tracking
- **Exports** — public/exported symbol detection
- **Heritage** — class inheritance, interfaces, mixins
- **Type Annotations** — explicit type extraction for receiver resolution
- **Constructor Inference** — infer receiver type from constructor calls (`self`/`this` resolution for all languages)
- **Config** — language toolchain config parsing (tsconfig, go.mod, etc.)
- **Frameworks** — AST-based framework pattern detection
- **Entry Points** — entry point scoring heuristics

---

### 3. Seven MCP Tools for AI Agents

Extracted from README "What Your AI Agent Gets":

| Tool | Purpose | Repo Param |
|------|---------|-----------|
| `list_repos` | Discover all indexed repositories | — (required) |
| `query` | Process-grouped hybrid search (BM25 + semantic + RRF) | Optional (when multiple repos indexed) |
| `context` | 360-degree symbol view—categorized refs, process participation | Optional |
| `impact` | Blast radius analysis with depth grouping and confidence | Optional |
| `detect_changes` | Git-diff impact—maps changed lines to affected processes | Optional |
| `rename` | Multi-file coordinated rename with graph + text search | Optional |
| `cypher` | Raw Cypher graph queries (for custom analysis) | Optional |

When only one repo is indexed, the `repo` parameter is optional on all tools.

**Tool Mechanisms**:
- **query**: Hybrid search combining BM25 (lexical), semantic (embedding-based), and RRF (reciprocal rank fusion) ranking. Returns results grouped by execution process.
- **context**: 360-degree view of a single symbol showing all incoming callers/importers, outgoing call/import targets, and which execution flows it participates in.
- **impact**: Traces upstream/downstream dependencies with confidence scoring and depth-grouped results (Depth 1 = direct callers/importers that WILL BREAK; Depth 2 = indirect deps that are LIKELY AFFECTED; Depth 3+ = transitive deps).
- **detect_changes**: Accepts git diffs and maps changed lines to affected symbols and execution flows, used for pre-commit impact analysis.
- **rename**: Performs multi-file coordinated renames using both graph-based edits (high confidence) and text-search edits (requires review).
- **cypher**: Accepts raw Neo4j-style Cypher queries against the knowledge graph for custom analysis.

---

### 4. Multi-Phase Indexing Pipeline

The README describes indexing in 6 phases:

1. **Structure** — Walks the file tree and maps folder/file relationships
2. **Parsing** — Extracts functions, classes, methods, and interfaces using Tree-sitter ASTs
3. **Resolution** — Resolves imports, function calls, heritage, constructor inference, and `self`/`this` receiver types across files with language-aware logic
4. **Clustering** — Groups related symbols into functional communities (via Leiden community detection)
5. **Processes** — Traces execution flows from entry points through call chains
6. **Search** — Builds hybrid search indexes (BM25 + semantic + RRF) for fast retrieval

---

### 5. Editor Integrations

Extracted from README editor support matrix:

| Editor | MCP | Skills | Hooks (auto-augment) | Support Level |
|--------|-----|--------|----------------------|---------------|
| **Claude Code** | Yes | Yes | Yes (PreToolUse + PostToolUse) | **Full** |
| **Cursor** | Yes | Yes | — | MCP + Skills |
| **Windsurf** | Yes | — | — | MCP |
| **OpenCode** | Yes | Yes | — | MCP + Skills |
| **Codex** | Yes | — | — | MCP |

Claude Code receives deepest integration: MCP tools + agent skills + PreToolUse hooks (enrich searches with graph context) + PostToolUse hooks (auto-reindex after commits).

**Community Integrations**:
- [pi](https://pi.dev): `pi install npm:pi-gitnexus`

---

### 6. Generated Skills and Prompts

**Four agent skills** installed to `.claude/skills/` automatically:
- **Exploring** — Navigate unfamiliar code using the knowledge graph
- **Debugging** — Trace bugs through call chains
- **Impact Analysis** — Analyze blast radius before changes
- **Refactoring** — Plan safe refactors using dependency mapping

**Repo-specific skills** generated via `gitnexus analyze --skills`:
- Detects functional areas of the codebase via Leiden community detection
- Generates a `SKILL.md` file for each community under `.claude/skills/generated/`
- Each skill describes module's key files, entry points, execution flows, and cross-area connections
- Skills are regenerated on each `--skills` run to stay current

**Two MCP prompts** for guided workflows:
- `detect_impact` — Pre-commit change analysis: scope, affected processes, risk level
- `generate_map` — Architecture documentation from the knowledge graph with Mermaid diagrams

---

### 7. CLI Commands

Extracted from README CLI commands section:

```bash
gitnexus setup                    # Configure MCP for your editors (one-time)
gitnexus analyze [path]           # Index a repository (or update stale index)
gitnexus analyze --force          # Force full re-index
gitnexus analyze --skills         # Generate repo-specific skill files from detected communities
gitnexus analyze --skip-embeddings  # Skip embedding generation (faster)
gitnexus analyze --embeddings     # Enable embedding generation (slower, better search)
gitnexus analyze --verbose        # Log skipped files when parsers are unavailable
gitnexus mcp                      # Start MCP server (stdio)—serves all indexed repos
gitnexus serve                    # Start local HTTP server (multi-repo) for web UI connection
gitnexus list                     # List all indexed repositories
gitnexus status                   # Show index status for current repo
gitnexus clean                    # Delete index for current repo
gitnexus clean --all --force      # Delete all indexes
gitnexus wiki [path]              # Generate repository wiki from knowledge graph
gitnexus wiki --model <model>     # Wiki with custom LLM model (default: gpt-4o-mini)
gitnexus wiki --base-url <url>    # Wiki with custom LLM API base URL
```

---

### 8. Wiki Generation

CLI command `gitnexus wiki` generates LLM-powered documentation from the knowledge graph. Mechanism:
1. Reads indexed graph structure
2. Groups files into modules via LLM
3. Generates per-module documentation pages
4. Creates overview page with cross-references to the knowledge graph

Requires LLM API key (OPENAI_API_KEY, etc.). Default model: gpt-4o-mini. Supports custom models/providers via `--model` and `--base-url` flags. Can force full regeneration via `--force`.

---

## Technical Architecture

### Stack: CLI

| Layer | Technology |
|-------|-----------|
| **Runtime** | Node.js (native) |
| **Parsing** | Tree-sitter native bindings (13 languages) |
| **Database** | LadybugDB native (embedded graph database with vector support) |
| **Embeddings** | HuggingFace transformers.js (GPU/CPU) |
| **Search** | BM25 + semantic + RRF |
| **Agent Interface** | MCP (stdio) |
| **Clustering** | Graphology + Leiden community detection algorithm |
| **Concurrency** | Worker threads + async |

### Stack: Web UI

| Layer | Technology |
|-------|-----------|
| **Runtime** | Browser (WebAssembly) |
| **Parsing** | Tree-sitter WASM |
| **Database** | LadybugDB WASM (in-memory per session) |
| **Embeddings** | transformers.js (WebGPU/WASM) |
| **Search** | BM25 + semantic + RRF |
| **Agent Interface** | LangChain ReAct agent |
| **Visualization** | Sigma.js + Graphology (WebGL graph rendering) |
| **Frontend** | React 18, TypeScript, Vite, Tailwind v4 |
| **Clustering** | Graphology |
| **Concurrency** | Web Workers + Comlink |

### Key Dependencies (CLI, from package.json v1.4.6)

- `@modelcontextprotocol/sdk` (^1.0.0) — MCP protocol implementation
- `@ladybugdb/core` (^0.15.1) — Embedded graph database
- `tree-sitter` (^0.21.0) + language bindings (c, c-sharp, cpp, go, java, javascript, php, python, ruby, rust, typescript)
- `graphology` (^0.25.4) + utilities — graph data structures and algorithms
- `@huggingface/transformers` (^3.0.0) — embedding generation
- `express` (^4.19.2) — HTTP server for web UI backend
- `commander` (^12.0.0) — CLI argument parsing
- `uuid` (^13.0.0) — unique identifier generation

---

## Installation & Usage

### Quick Start (CLI)

```bash
# Install globally (recommended)
npm install -g gitnexus

# From repo root, index your codebase
npx gitnexus analyze
```

This command:
1. Indexes the codebase
2. Installs agent skills to `.claude/skills/`
3. Registers Claude Code hooks
4. Creates `AGENTS.md` / `CLAUDE.md` context files

### MCP Configuration (One-Time)

**Automatic**:
```bash
npx gitnexus setup
```

This auto-detects your editors and writes the correct global MCP config. Only needs to run once.

**Manual Configuration**:

**Claude Code**:
```bash
claude mcp add gitnexus -- npx -y gitnexus@latest mcp
```

**Cursor** (`~/.cursor/mcp.json` — global, works for all projects):
```json
{
  "mcpServers": {
    "gitnexus": {
      "command": "npx",
      "args": ["-y", "gitnexus@latest", "mcp"]
    }
  }
}
```

**OpenCode** (`~/.config/opencode/config.json`):
```json
{
  "mcp": {
    "gitnexus": {
      "command": "npx",
      "args": ["-y", "gitnexus@latest", "mcp"]
    }
  }
}
```

**Codex** (`~/.codex/config.toml` for system scope, or `.codex/config.toml` for project scope):
```toml
[mcp_servers.gitnexus]
command = "npx"
args = ["-y", "gitnexus@latest", "mcp"]
```

### Web UI

**Live**: No install—visit [gitnexus.vercel.app](https://gitnexus.vercel.app) and drag & drop a ZIP or GitHub repo URL.

**Local Development**:
```bash
git clone https://github.com/abhigyanpatwari/GitNexus.git
cd gitnexus/gitnexus-web
npm install
npm run dev
```

**Local Backend Mode** (connect CLI-indexed repos to web UI):
```bash
gitnexus serve
# Opens http://localhost with auto-detection of local indexed repos
```

---

## Relevance to Claude Code Development

GitNexus is **directly relevant** to Claude Code in three ways:

1. **MCP Integration**: GitNexus implements the MCP protocol, enabling deep codebase awareness in Claude Code. When indexed, AI agents get `query`, `context`, `impact`, and `detect_changes` tools that understand execution flows and symbol dependencies—not just raw file/symbol search.

2. **Agent Skills**: Generates agent skills (`.claude/skills/generated/`) describing functional areas (communities) of a codebase. These are readable by Claude Code workflows and support exploration, debugging, impact analysis, and refactoring.

3. **Claude Code Hooks**: Full integration with Claude Code's PreToolUse and PostToolUse hooks:
   - **PreToolUse**: Enrich searches with graph context (e.g., auto-expand queries to include related functions in same execution flow)
   - **PostToolUse**: Auto-reindex after commits to keep the knowledge graph fresh

4. **Edge Case Prevention**: Addresses the core problem that motivated Claude Code enhancements around context and tool reliability—smaller models competing with larger ones by having structured, precomputed context rather than raw exploratory chains.

---

## Limitations and Caveats

### Documented Limitations

1. **Web UI Browser Memory**: Limited to ~5k files without backend mode. Larger repos require either CLI mode or `gitnexus serve` local backend connection.

2. **Embeddings Overhead**: Embedding generation is optional (`--embeddings` flag) but adds significant time to indexing. Default is to skip embeddings for speed.

3. **Language Coverage Variance**: While 13 languages are supported, coverage varies—TypeScript/Python/Java/C# have complete coverage; C/C++ have partial coverage (no imports, no named bindings, no heritage/config for C++).

4. **Constructor Inference Limits**: Inferred receiver types depend on constructor call patterns. May miss non-standard initialization patterns.

5. **Framework Detection Limitations**: AST-based framework detection may not catch all framework-specific patterns, especially in less common frameworks.

6. **Index Staleness**: Index becomes stale after code changes. Requires re-running `gitnexus analyze` to update—though Claude Code hooks automate this after commits.

7. **Named Binding Re-export Tracking**: Not all languages support equivalent complexity in tracking re-exports and aliased imports (e.g., Ruby lacks named binding extraction).

### Undocumented Limitations (Not Mentioned in Reviewed Sources)

No limitations were documented in the official documentation or README beyond the above. The project does not document:
- Performance benchmarks or indexing time expectations for large repos
- Memory usage profiles for the CLI or Web UI
- Accuracy rates for any analysis (impact analysis confidence scoring is documented, but overall accuracy is not)
- Known parsing bugs or language-specific AST extraction issues

---

## References

| Source | URL | Accessed |
|--------|-----|----------|
| Repository README | <https://github.com/abhigyanpatwari/GitNexus/blob/main/README.md> | 2026-03-19 |
| GitHub API Metadata | <https://api.github.com/repos/abhigyanpatwari/GitNexus> | 2026-03-19 |
| CLI package.json (v1.4.6) | gitnexus/package.json in local clone | 2026-03-19 |
| Web UI package.json | gitnexus-web/package.json in local clone | 2026-03-19 |
| CLAUDE.md (GitNexus index docs) | .worktrees/GitNexus/CLAUDE.md | 2026-03-19 |
| GitHub Releases | <https://github.com/abhigyanpatwari/GitNexus/releases> | Not fetched (latest via API) |

---

## Freshness Tracking

**Last Reviewed**: 2026-03-19

**Next Review Recommended**: 2026-06-19 (3 months)

**Index Last Commit**: 2026-03-18 (feature-phase7-type-resolution branch, 2075 symbols, 4935 relationships, 157 execution flows)

### Confidence by Section

| Section | Confidence | Notes |
|---------|-----------|-------|
| **Identity/Metadata** | high | GitHub API + package.json verified; version string confirmed |
| **Problem Addressed** | high | README explicitly describes problem scenario and traditional vs GitNexus approach |
| **Key Statistics** | high | GitHub API (stars, forks, issues) as of 2026-03-19; version from package.json |
| **Key Features** | high | README sections directly extracted (interfaces, tools, CLI commands, language matrix) |
| **Technical Architecture** | high | Tech stack table directly from README; dependencies verified in package.json |
| **Installation & Usage** | high | CLI commands and MCP setup extracted verbatim from official docs |
| **Relevance to Claude Code** | medium | Based on documented MCP integration + hooks + skills generation; integration depth inferred from CLAUDE.md but not fully tested in this session |
| **Limitations** | medium | Documented limitations from README extracted; undocumented limitations listed as "not mentioned" with explicit acknowledgment that absence is not confirmation |

**Confidence Rationale**:
- High-confidence sections rely on official documentation (README, API, package.json), which are authoritative sources.
- Medium-confidence sections infer integration depth from CLAUDE.md and Hook implementation names without testing actual agent behavior.
- Limitations section distinguishes documented vs undocumented gaps, avoiding false certainty about absence of issues.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Octocode-MCP](./octocode-mcp.md) | mcp-ecosystem | Alternative MCP-based code research platform using semantic search and RDD methodology for agent-driven development |
| [CocoIndex Code](./cocoindex-code.md) | mcp-ecosystem | Lightweight MCP server providing semantic code search via AST analysis and embeddings; similar zero-config indexing approach |
| [Ultra MCP](./ultra-mcp.md) | mcp-ecosystem | Multi-provider MCP server with integrated vector search capability for codebase indexing and semantic retrieval |
| [Cline](../coding-agents/cline.md) | coding-agents | Open-source autonomous coding agent that integrates GitNexus MCP tools and skills for deep codebase awareness |
| [Kythe](../developer-tools/kythe.md) | developer-tools | Language-agnostic code indexing ecosystem using graph-based semantic model; foundational approach to cross-language codebase analysis |
| [GrepAI](../developer-tools/grepai.md) | developer-tools | Semantic code search and call graph analysis tool with MCP integration; complementary embedding-based approach to code understanding |
| [Repomix](../developer-tools/repomix.md) | developer-tools | Codebase packaging and compression tool using Tree-sitter; generates agent skills and supports MCP server interface |
| [CodeWiki (Google)](../ai-research-tools/codewiki-google.md) | ai-research-tools | AI-powered repository documentation system generating architecture diagrams and hyperlinked symbol navigation from code analysis |
| [SigMap](../developer-tools/sigmap.md) | developer-tools | referenced by SigMap (developer-tools) |

---

## Category

**mcp-ecosystem** — GitNexus is an MCP server implementation enabling deep codebase awareness for AI agents through a knowledge graph interface.
