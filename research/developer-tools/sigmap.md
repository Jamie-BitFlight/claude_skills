---
title: SigMap
subtitle: Zero-dependency AI context engine extracting codebase signatures for ranked file retrieval
category: developer-tools
resource_url: https://manojmallick.github.io/sigmap
github_url: https://github.com/manojmallick/sigmap
date_created: "2026-05-08"
date_last_reviewed: "2026-05-08"
status: published
---

# SigMap

**Research Date**: 2026-05-08
**Source URL**: <https://manojmallick.github.io/sigmap>
**GitHub Repository**: <https://github.com/manojmallick/sigmap>
**Version at Research**: v6.10.0 (released 2026-05-05)
**License**: MIT

---

## Overview

SigMap is a zero-dependency AI context engine that extracts function and class signatures from codebases to feed LLMs only the relevant files rather than entire repositories. It reduces token usage by 40-98% while achieving an 80% retrieval accuracy (top 5 results) compared to a 13.6% baseline, enabling faster and more accurate AI-assisted coding without embeddings, vector databases, or cloud infrastructure.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI assistants start each session with zero knowledge of codebase architecture | SigMap extracts and ranks function signatures, class hierarchies, and exported types so the AI can navigate and understand your code immediately |
| Sending full repositories to AI assistants consumes 50,000–400,000 tokens per session | SigMap compresses context to 3,800–4,000 tokens by extracting only signatures; 40–98% token reduction across real projects |
| Embeddings and RAG systems require infrastructure (vector DB, indexing, maintenance, drift over time) | SigMap uses TF-IDF ranking on plaintext signature files, runs locally, requires zero config, is deterministic, and works offline |
| Cold-start context problem: without understanding your architecture, AI assistants ask "can you share some files?" repeatedly | SigMap pre-generates ranked file lists so the AI can answer "I can see your AuthService, UserRepository, 47 API routes, and the middleware stack. Where should I add rate limiting?" |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | ~5,100 (inferred from npm popularity metrics) | 2026-05-08 |
| npm Downloads/month | High (npm badge available at package page) | 2026-05-08 |
| Latest Release | v6.10.0 | 2026-05-05 |
| Hit@5 Accuracy | 80.0% (5.9× lift over 13.6% baseline) | 2026-05-05 |
| Average Token Reduction | 40–98% (avg 96.8% across 18 real repos) | 2026-05-05 |
| Task Success Rate | 52.2% (up from 10% baseline) | 2026-05-05 |
| Prompts per Task | 1.68 (down from 2.84 baseline) | 2026-05-05 |
| Supported Languages | 29 languages (TypeScript, JavaScript, Python, Java, Go, Rust, C#, C/C++, Ruby, PHP, and 19 others) | 2026-05-05 |

---

## Key Features

### Signature Extraction

- Extracts function names, class hierarchies, method signatures, and exported types from 29 programming languages without external dependencies or language servers
- Signatures cached by modification time (mtime) for incremental extraction on large codebases, dramatically improving performance on subsequent runs
- Generated signatures are plaintext files committed to the repository for transparency and version control

### Retrieval and Ranking

- TF-IDF scoring ranks files against natural-language queries (e.g., "Where is auth handled?") in milliseconds
- Session memory with 4-hour TTL carries context across follow-up queries — previous session's top 5 files receive +0.2 score boost in next query
- 2-hop graph traversal with decay (0.40 boost for 1-hop dependencies, 0.15 for 2-hop) improves retrieval by catching cross-module architecture patterns
- Hub suppression automatically suppresses common utility files (utils/, helpers/, common/, index) and high-fanout files (>20% of codebase) to reduce false-positive boosts

### Workspace and Monorepo Support

- Detects workspace packages from `package.json` workspaces field (npm and Yarn v2 formats)
- Automatically infers target package from query tokens (e.g., "rate limiting payments" → packages/payments/)
- Files inside inferred package receive +0.30 score boost for tighter context in monorepos
- Flags: `--package <name>` (explicit scope) and `--global` (disable workspace scoping)

### Adapter System

- Outputs to AI assistant-specific context files: `.github/copilot-instructions.md` (GitHub Copilot), `CLAUDE.md` (Claude), `.cursorrules` (Cursor), `.windsurfrules` (Windsurf), `.github/openai-context.md` (OpenAI), `.github/gemini-context.md` (Google Gemini), `AGENTS.md` (OpenAI Codex)
- Single run generates context for all integrated assistants

### Strategic Context Generation

- `full` strategy (default): all files in context (~4,000 tokens always-injected, no context lost, no MCP required)
- `per-module` strategy: module overview only (~100–300 tokens, suitable for large codebases)
- `hot-cold` strategy: recent files always injected, older files on-demand via MCP (~200–800 tokens for hot files)

### IDE Integration

- VS Code extension: status bar health grade, stale context alerts, one-click regeneration
- JetBrains plugin: tool window + actions for IntelliJ IDEA, WebStorm, PyCharm, GoLand
- Neovim plugin: `:SigMap` and `:SigMapQuery` float window, statusline widget

### MCP Server

- 9 on-demand tools for Claude Code and Cursor via `sigmap --mcp`

### Analysis and Validation

- `sigmap ask "<query>"` — ranked file list for any question
- `sigmap validate --query "<query>"` — confirms right files are in scope
- `sigmap judge --response <file> --context <context>` — scores answer groundedness against retrieved context
- `sigmap --health` — text and JSON output of cache health statistics, cache file size, entry count, freshness
- `sigmap plan "<goal>"` — analyze change impact before editing; rank files by confidence level, compute impact radius using dependency graph, identify affected tests

---

## Technical Architecture

### Component Structure

SigMap decomposes into modular subsystems (based on `src/` directory structure):

1. **Discovery layer** (`src/discovery/`)
   - `language-detector.js` — identifies file language from extension
   - `source-root-resolver.js` and `source-root-scorer.js` — detects primary source directory (src/, lib/, app/) with framework-awareness
   - `framework-detector.js` — identifies project type (React, Next.js, Express, etc.)
   - `sigmapignore.js` — parses `.contextignore` file for pattern-based exclusions

2. **Signature extraction** (language-specific parsers in `src/`)
   - Zero-dependency parsers for each language: regex and AST traversal for extracting function signatures, class definitions, exports
   - Caching layer (`src/cache/sig-cache.js`) stores extracted signatures by mtime for incremental re-extraction

3. **Retrieval and ranking** (`src/retrieval/`)
   - `tokenizer.js` — tokenizes queries for TF-IDF scoring
   - TF-IDF ranking engine scores files against queries
   - Graph module (`src/graph/builder.js`, `impact.js`) — builds dependency graph for boost/suppression

4. **Configuration** (`src/config/`)
   - `loader.js` — reads `gen-context.config.json` and `.contextignore` for user settings
   - `defaults.js` — built-in defaults for all config keys

5. **Output formatting** (`src/format/`)
   - `llm-txt.js` and `llms-txt.js` — generates compact signature manifests for LLMs
   - Adapters (`packages/adapters/`) — format context for Copilot, Claude, Cursor, Windsurf, OpenAI, Gemini, Codex

6. **CLI** (`packages/cli/`, `gen-context.js`)
   - 32 commands: `ask`, `validate`, `judge`, `plan`, `weights`, `--watch`, `--health`, `--report`, `--mcp`

### Data Flow

```
Query → Tokenizer → TF-IDF Ranking → Graph Boost/Suppress → Top N Files → Format (adapter) → Output File
```

### Design Decisions

- **Zero npm dependencies** — chosen to enable `npx sigmap` with no install, zero config, works on any machine with Node.js 18+
- **Plaintext signatures** — committed to repo, version-controlled, deterministic, searchable
- **Local-only execution** — no cloud API, no network calls, works offline, no drift over time
- **Deterministic scoring** — same input always produces same ranked output (unlike embeddings which can shift with model updates)

---

## Installation & Usage

### Quick Start (No Install)

```bash
npx sigmap
npx sigmap ask "Where is auth handled?"
```

### Install Globally

```bash
npm install -g sigmap
```

### Install Per-Project

```bash
npm install --save-dev sigmap
```

### Standalone Binary (No Node.js Required)

Download from [GitHub Releases](https://github.com/manojmallick/sigmap/releases/latest):
- macOS Apple Silicon: `sigmap-darwin-arm64`
- macOS Intel: `sigmap-darwin-x64`
- Linux x64: `sigmap-linux-x64`
- Windows x64: `sigmap-win32-x64.exe`

Verify checksums: each binary ships with a `.sha256` file.

### Usage Examples

```bash
# 1. Generate context for your project
sigmap

# 2. Ask a question — get ranked files
sigmap ask "Where is auth handled?"

# 3. Validate — confirm right files are in scope
sigmap validate --query "auth login token"

# 4. Judge — score your AI's answer for groundedness
sigmap judge --response response.txt --context .context/query-context.md

# 5. Inspect health
sigmap --health

# 6. Plan changes and see impact
sigmap plan "Add rate limiting to auth flow"

# 7. Watch mode — regenerate on file changes
sigmap --watch

# 8. Setup assistant context files
sigmap --adapter copilot   # .github/copilot-instructions.md
sigmap --adapter claude    # CLAUDE.md
sigmap --adapter cursor    # .cursorrules
```

### Configuration

Create `gen-context.config.json` in project root:

```json
{
  "ignore": ["node_modules", "dist", ".git"],
  "srcDirs": ["src", "lib"],
  "strategy": "full",
  "sigCache": true,
  "tokenBudget": 8000,
  "contextIgnoreFile": ".contextignore"
}
```

---

## Relevance to Claude Code Development

### Applications

- **Context generation for agent tasks** — Extract signatures once per feature branch, reuse across all agent prompts, avoiding redundant full-repo transfers
- **MCP server for on-demand retrieval** — Enable agents to query file ranking via 9 on-demand tools (ask, validate, judge, plan, weights, health, map, impact, dependencies)
- **Baseline for codebase-understanding agents** — Use SigMap as a deterministic, reproducible baseline for measuring retrieval accuracy; compare against embedding-based approaches (RAG)
- **Token budget tracking for agents** — Auto-calculate remaining token budget based on context injected by SigMap; agents can request additional files within budget

### Patterns Worth Adopting

- **Layered context injection** — Always-injected signatures (baseline context) + on-demand file fetches via MCP (when queries exhaust signatures)
- **Deterministic ranking over embeddings** — TF-IDF is reproducible, fast, offline, and interpretable; avoids embedding model drift and vector DB maintenance
- **Session memory with intent awareness** — Carry context from previous query without over-fixating; boost relevant files by a fixed amount (+0.2 for same intent, +0.1 for topic switch)
- **Impact analysis before changes** — Compute dependency graph, rank files by change likelihood, identify affected tests before modifying (SigMap's `plan` command)
- **Incremental state with mtime caching** — Cache extracted signatures by file modification time; skip re-parsing unchanged files on subsequent runs

### Integration Opportunities

- **Agent-generated SAM task plans** — Agents could use `sigmap plan` to automatically identify which files to read before implementing a task
- **Skill context pre-generation** — Skills could run `sigmap` once per repo, then reference generated `.context/` files in skill prompts without re-scanning
- **Retrieval benchmark for agent evaluation** — Use SigMap as a stable, reproducible retrieval baseline when evaluating agent performance on real codebases (compare against 13.6% baseline)
- **MCP server for Claude Code** — Integrate SigMap's MCP server as a built-in plugin, enabling Claude Code to ask "show me all auth-related files" and get ranked results

---

## References

- [SigMap Official Documentation](https://manojmallick.github.io/sigmap) (accessed 2026-05-08)
- [SigMap GitHub Repository](https://github.com/manojmallick/sigmap) (accessed 2026-05-08)
- [SigMap README](https://github.com/manojmallick/sigmap/blob/main/README.md) (accessed 2026-05-08)
- [SigMap Getting Started Guide](https://github.com/manojmallick/sigmap/blob/main/docs/readmes/GETTING_STARTED.md) (accessed 2026-05-08)
- [SigMap Context Strategies](https://github.com/manojmallick/sigmap/blob/main/docs/readmes/CONTEXT_STRATEGIES.md) (accessed 2026-05-08)
- [SigMap Changelog](https://github.com/manojmallick/sigmap/blob/main/CHANGELOG.md) (accessed 2026-05-08)
- [SigMap Benchmark Suite](https://github.com/manojmallick/sigmap-benchmark-suite) (accessed 2026-05-08)
- [SigMap Benchmark Data (Zenodo)](https://zenodo.org/records/19898842) (accessed 2026-05-08)
- [SigMap npm Package](https://www.npmjs.com/package/sigmap) (accessed 2026-05-08)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Narsil-MCP](../mcp-ecosystem/narsil-mcp.md) | mcp-ecosystem | Rust MCP server with 90 code intelligence tools; complements SigMap's TF-IDF ranking with call graphs, taint analysis, and security scanning |
| [CocoIndex Code](../mcp-ecosystem/cocoindex-code.md) | mcp-ecosystem | Semantic code search MCP server achieving ~70% token savings; shares token optimization goal via embedding-based retrieval vs SigMap's deterministic ranking |
| [GitNexus](../mcp-ecosystem/gitnexus.md) | mcp-ecosystem | Knowledge graph-based code intelligence MCP; alternative approach to SigMap's signature extraction for codebase context generation |
| [CodeGraphContext](../mcp-ecosystem/codegraphcontext.md) | mcp-ecosystem | Graph database MCP server for code queries and impact analysis; complements SigMap's dependency tracking with semantic graph traversal |
| [GrepAI](../developer-tools/grepai.md) | developer-tools | Semantic code search with call graph analysis; shares SigMap's goal of AI-friendly code retrieval with embedding-based approach vs TF-IDF |
| [Repomix](../developer-tools/repomix.md) | developer-tools | Context compression tool using Tree-sitter that achieves ~70% reduction; parallel compression approach to SigMap's signature extraction strategy |
| [Claude Mem](../context-management/claude-mem.md) | context-management | Persistent memory compression for Claude Code agents; shares SigMap's session context pattern (4-hour TTL) and token optimization focus |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-05-08 |
| Version at Verification | v6.10.0 |
| Next Review Recommended | 2026-08-08 |
| Confidence Map | `Overview: high`, `Problem Addressed: high`, `Key Statistics: high (from official benchmarks)`, `Key Features: high (from README and CHANGELOG)`, `Technical Architecture: medium (code-read from src/ structure)`, `Installation & Usage: high (from official docs)`, `Relevance to Claude Code: medium (inferred patterns)` |
