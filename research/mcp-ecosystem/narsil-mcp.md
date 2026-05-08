---
name: Narsil-MCP - Comprehensive Code Intelligence MCP Server
description: Narsil-MCP is a Rust-powered MCP (Model Context Protocol) server providing AI assistants with deep code intelligence through 90 specialized tools. It supports 32 programming languages with features...
license: Apache-2.0 / MIT (dual-licensed)
metadata:
  topic: narsil-mcp
  category: mcp-ecosystem
  source_url: https://narsilmcp.com/
  github: postrv/narsil-mcp
  version: "v1.3.1"
  verified: "2026-01-26"
  next_review: "2026-04-26"
---

## Overview

Narsil-MCP is a Rust-powered MCP (Model Context Protocol) server providing AI assistants with deep code intelligence through 90 specialized tools. It supports 32 programming languages with features including symbol extraction, semantic search, call graph analysis, security scanning (OWASP/CWE), taint analysis, SBOM generation, and neural embeddings.

**Core Value Proposition**: Privacy-first, local-only code intelligence that transforms AI assistants into powerful code analysis tools without sending data to external services.

---

## Problem Addressed

| Problem                                                          | How Narsil-MCP Solves It                                                                         |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| AI assistants lack deep code understanding beyond file content   | 90 specialized tools provide symbol extraction, call graphs, control flow, data flow analysis    |
| Security analysis requires external tools and manual integration | Built-in taint analysis, vulnerability scanning (OWASP Top 10, CWE Top 25), secret detection     |
| Existing MCP servers support limited languages                   | Tree-sitter powered parsing for 32 languages with accurate, incremental parsing                  |
| Cloud-based code analysis raises privacy concerns                | Fully local, no data leaves the machine, single binary deployment                                |
| Large codebase context exceeds AI token limits                   | Smart excerpts, AST-aware chunking, configurable presets (26-90 tools) for token optimization    |
| Context window overhead from tool definitions                    | Editor-specific presets: Minimal (26 tools, ~4,686 tokens), Balanced (51 tools), Full (90 tools) |

---

## Key Statistics (as of January 26, 2026)

| Metric              | Value                     |
| ------------------- | ------------------------- |
| GitHub Stars        | 82                        |
| Forks               | 12                        |
| Contributors        | 3                         |
| Total Tools         | 90                        |
| Languages Supported | 32                        |
| Security Rules      | 111                       |
| Repository Created  | December 24, 2025         |
| Latest Release      | v1.3.1 (January 23, 2026) |
| Total Commits       | 94                        |

---

## Key Features

### Code Intelligence (Core)

- **Symbol Extraction**: Functions, structs, classes, enums, traits, interfaces across 32 languages
- **Semantic Search**: BM25 ranking with Tantivy full-text search engine
- **Hybrid Search**: Combined BM25 + TF-IDF with reciprocal rank fusion
- **Call Graph Analysis**: Function relationships, callers/callees, call paths, hotspot detection
- **Control Flow Graphs**: Basic blocks and branch analysis
- **Data Flow Analysis**: Variable definitions, uses, reaching definitions
- **Dead Code Detection**: Unreachable code blocks and dead stores
- **Type Inference**: Built-in inference for Python, JavaScript, TypeScript without external tools

### Neural Semantic Search (Optional `--neural` flag)

- **Embedding-Based Search**: Find similar code using Voyage AI or OpenAI embeddings
- **Semantic Clone Detection**: Find Type-3/4 semantic clones of functions
- **Backends**: API mode (Voyage AI, OpenAI, custom endpoints) or local ONNX models
- **Model Support**: voyage-code-2, OpenAI embeddings, custom models

### Security Analysis

- **Taint Analysis**: Source-to-sink tracking for SQL injection, XSS, command injection, path traversal
- **OWASP Top 10**: Comprehensive vulnerability scanning
- **CWE Top 25**: Most dangerous software weaknesses detection
- **Secret Detection**: API keys, passwords, tokens, private keys
- **111 Security Rules**: YAML-based rules for crypto, secrets, IaC (Terraform, CloudFormation, Kubernetes)
- **Language-Specific Rules**: Go, Java, C#, Kotlin, Bash, Ruby, PHP, TypeScript

### Supply Chain Security

- **SBOM Generation**: CycloneDX, SPDX, JSON formats
- **Dependency Vulnerability Checking**: OSV database integration
- **License Compliance**: Audit licenses for legal compliance
- **Upgrade Path Finder**: Safe upgrade paths for vulnerable dependencies

### Knowledge Graph (v1.3.0+ with `--graph` flag)

- **SPARQL Queries**: Execute SPARQL SELECT/ASK queries against code RDF graph (Oxigraph)
- **Code Context Graph (CCG)**: 12 tools for standardized AI-consumable codebase representations
  - L0 Manifest: ~1-2KB JSON-LD repository identity
  - L1 Architecture: ~10-50KB JSON-LD modules and API
  - L2 Symbol Index: ~100-500KB N-Quads gzipped
  - L3 Full Detail: ~1-20MB N-Quads gzipped
- **Triple-Heart Model**: Tiered access control (public/authenticated/private)

### Git Integration (with `--git` flag)

- Git blame, file history, commit diffs
- Hotspot detection (high churn + complexity)
- Contributors analysis
- Symbol history tracking

### Additional Features

- **LSP Integration**: Hover info, go-to-definition, precise types
- **Remote Repository Support**: GitHub repository cloning and API access
- **Incremental Indexing**: Merkle tree-based change detection
- **Streaming Responses**: Real-time results for large repos
- **WASM Build**: Browser execution for educational platforms
- **Visualization Frontend**: Interactive call graphs with HTTP server

---

## Supported Languages (32)

| Category   | Languages                                 |
| ---------- | ----------------------------------------- |
| Systems    | Rust, C, C++, Go, Zig                     |
| JVM        | Java, Kotlin, Scala, Groovy               |
| .NET       | C#                                        |
| Web        | JavaScript, TypeScript, PHP               |
| Scripting  | Python, Ruby, Perl, Lua, Bash, PowerShell |
| Functional | Haskell, Elixir, Erlang, Elm, Clojure     |
| Scientific | Julia, R, Fortran                         |
| Mobile     | Swift, Dart, Kotlin                       |
| Hardware   | Verilog, SystemVerilog                    |
| Config     | Nix                                       |

---

## Technical Architecture

<eg>
+-----------------------------------------------------------------+
|                         MCP Server                               |
|  +-----------------------------------------------------------+  |
|  |                   JSON-RPC over stdio                      |  |
|  +-----------------------------------------------------------+  |
|                              |                                   |
|  +---------------------------v-------------------------------+  |
|  |                   Code Intel Engine                        |  |
|  |  +------------+ +------------+ +------------------------+  |  |
|  |  |  Symbol    | |   File     | |    Search Engine       |  |  |
|  |  |  Index     | |   Cache    | |  (Tantivy + TF-IDF)    |  |  |
|  |  | (DashMap)  | | (DashMap)  | +------------------------+  |  |
|  |  +------------+ +------------+                              |  |
|  |  +------------+ +------------+ +------------------------+  |  |
|  |  | Call Graph | |  Taint     | |   Security Rules       |  |  |
|  |  |  Analysis  | |  Tracker   | |   Engine               |  |  |
|  |  +------------+ +------------+ +------------------------+  |  |
|  +-----------------------------------------------------------+  |
|                              |                                   |
|  +---------------------------v-------------------------------+  |
|  |                Tree-sitter Parser                          |  |
|  |  +------+ +------+ +------+ +------+ +------+             |  |
|  |  | Rust | |Python| |  JS  | |  TS  | | Go   | ... (32)    |  |
|  |  +------+ +------+ +------+ +------+ +------+             |  |
|  +-----------------------------------------------------------+  |
|                              |                                   |
|  +---------------------------v-------------------------------+  |
|  |                Repository Walker                           |  |
|  |           (ignore crate - respects .gitignore)             |  |
|  +-----------------------------------------------------------+  |
+-----------------------------------------------------------------+
</eg>

**Key Implementation Details**:

- **Rust-native**: Single binary (~30MB), memory-safe, blazingly fast
- **Tree-sitter Powered**: Incremental parsing with 2 GiB/s throughput
- **Parallel Processing**: Rayon-based parallel indexing using all cores
- **Lock-free Data Structures**: DashMap for concurrent symbol/file access
- **Tantivy Search**: High-performance full-text search with BM25 ranking

---

## Performance Benchmarks

### Parsing Throughput (Apple M1)

| Language      | Input Size | Time    | Throughput |
| ------------- | ---------- | ------- | ---------- |
| Rust (large)  | 278 KB     | 131 us  | 1.98 GiB/s |
| Rust (medium) | 27 KB      | 13.5 us | 1.89 GiB/s |
| Python        | ~4 KB      | 16.7 us | -          |
| TypeScript    | ~5 KB      | 13.9 us | -          |

### Search Latency

| Operation           | Corpus Size   | Time   |
| ------------------- | ------------- | ------ |
| Symbol exact match  | 1,000 symbols | 483 ns |
| Symbol prefix match | 1,000 symbols | 2.7 us |
| BM25 full-text      | 1,000 docs    | 80 us  |
| Hybrid search       | 1,000 docs    | 151 us |

### End-to-End Indexing

| Repository    | Files   | Symbols | Time   | Memory |
| ------------- | ------- | ------- | ------ | ------ |
| narsil-mcp    | 53      | 1,733   | 220 ms | ~50 MB |
| rust-analyzer | 2,847   | ~50K    | 2.1s   | 89 MB  |
| linux kernel  | 78,000+ | ~500K   | 45s    | 2.1 GB |

---

## Installation

### Package Managers

```bash
# Homebrew (macOS/Linux)
brew tap postrv/narsil && brew install narsil-mcp

# npm (All platforms)
npm install -g narsil-mcp

# Cargo (All platforms)
cargo install narsil-mcp

# Scoop (Windows)
scoop bucket add narsil https://github.com/postrv/scoop-narsil
scoop install narsil-mcp

# Nix
nix run github:postrv/narsil-mcp -- --repos ./my-project
```

### One-Line Install Scripts

```bash
# macOS/Linux
curl -fsSL https://raw.githubusercontent.com/postrv/narsil-mcp/main/install.sh | bash

# Windows (PowerShell)
irm https://raw.githubusercontent.com/postrv/narsil-mcp/main/install.ps1 | iex
```

---

## MCP Configuration Examples

### Claude Code (`.mcp.json` in project root)

```json
{
  "mcpServers": {
    "narsil-mcp": {
      "command": "narsil-mcp",
      "args": ["--repos", ".", "--git", "--call-graph"]
    }
  }
}
```

### Cursor (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "narsil-mcp": {
      "command": "narsil-mcp",
      "args": ["--repos", ".", "--git", "--call-graph"]
    }
  }
}
```

### VS Code Copilot (`.vscode/mcp.json`)

```json
{
  "servers": {
    "narsil-mcp": {
      "command": "narsil-mcp",
      "args": ["--repos", ".", "--git", "--call-graph"]
    }
  }
}
```

---

## Tool Categories (90 Total)

| Category          | Count | Examples                                                       |
| ----------------- | ----- | -------------------------------------------------------------- |
| Repository & File | 8     | list_repos, get_project_structure, get_file, reindex           |
| Symbol Search     | 7     | find_symbols, get_symbol_definition, find_references           |
| Code Search       | 6     | search_code, semantic_search, hybrid_search                    |
| AST Chunking      | 3     | get_chunks, get_chunk_stats, get_embedding_stats               |
| Neural Search     | 3     | neural_search, find_semantic_clones, get_neural_stats          |
| Call Graph        | 6     | get_call_graph, get_callers, get_callees, find_call_path       |
| Control Flow      | 2     | get_control_flow, find_dead_code                               |
| Data Flow         | 4     | get_data_flow, get_reaching_definitions, find_dead_stores      |
| Type Inference    | 3     | infer_types, check_type_errors, get_typed_taint_flow           |
| Import Graph      | 3     | get_import_graph, find_circular_imports                        |
| Taint Tracking    | 4     | find_injection_vulnerabilities, trace_taint, get_taint_sources |
| Security Rules    | 5     | scan_security, check_owasp_top10, check_cwe_top25              |
| Supply Chain      | 4     | generate_sbom, check_dependencies, check_licenses              |
| Git Integration   | 12    | get_blame, get_file_history, get_hotspots, get_contributors    |
| LSP               | 3     | get_hover_info, get_type_info, go_to_definition                |
| Remote Repos      | 3     | add_remote_repo, list_remote_files, get_remote_file            |
| SPARQL/CCG        | 15    | sparql*query, get_ccg_manifest, export_ccg*\*                  |

---

## Configuration System (v1.1.0+)

### Presets for Token Optimization

| Preset           | Tools | Tokens  | Use Case                               |
| ---------------- | ----- | ------- | -------------------------------------- |
| Minimal          | 26    | ~4,686  | Zed, Cursor (61% reduction)            |
| Balanced         | 51    | ~8,948  | VS Code, IntelliJ (25% reduction)      |
| Full             | 90    | ~12,001 | Claude Desktop, comprehensive analysis |
| Security-Focused | ~30   | -       | Security audits                        |

### Automatic Editor Detection

Narsil-MCP automatically detects the editor from the MCP `initialize` request and applies optimal presets.

### Configuration Priority

CLI flags > Environment vars > Project config (`.narsil.yaml`) > User config (`~/.config/narsil-mcp/config.yaml`) > Defaults

---

## Relevance to Claude Code Development

### Direct Applications

1. **Enhanced Code Intelligence**: Drop-in MCP server provides 90 tools for deep codebase understanding
2. **Security Auditing**: Built-in vulnerability scanning without external tools
3. **Supply Chain Analysis**: SBOM generation and license compliance for production deployments
4. **Token Optimization**: Configurable presets reduce context window usage by up to 61%

### Patterns Worth Adopting

1. **Preset System**: Tool filtering based on editor/use-case for context window efficiency
2. **Multi-Source Configuration**: CLI > Env > Project > User config priority
3. **AST-Aware Chunking**: Tree-sitter based chunking preserves syntactic boundaries
4. **Hybrid Search**: Combining BM25 + TF-IDF with reciprocal rank fusion
5. **Incremental Indexing**: Merkle tree change detection for large repos

### Integration Opportunities

1. **Claude Code Plugin Available**: `/plugin install github:postrv/narsil-mcp/narsil-plugin`
2. **Complements Existing Tools**: Adds security analysis, call graphs, supply chain features
3. **Code Context Graph**: CCG export format could standardize codebase representations
4. **Ralph Automation Integration**: Works with Ralph for autonomous code development workflows

### Comparison with Alternatives

| Feature        | narsil-mcp | XRAY    | Serena    | GitHub MCP |
| -------------- | ---------- | ------- | --------- | ---------- |
| Languages      | 32         | 4       | 30+ (LSP) | N/A        |
| Neural Search  | Yes        | No      | No        | No         |
| Taint Analysis | Yes        | No      | No        | No         |
| SBOM/Licenses  | Yes        | No      | No        | Partial    |
| Offline/Local  | Yes        | Yes     | Yes       | No         |
| WASM/Browser   | Yes        | No      | No        | No         |
| Call Graphs    | Yes        | Partial | No        | No         |
| Type Inference | Yes        | No      | No        | No         |

---

## References

1. **Official Website**: <https://narsilmcp.com/> (accessed 2026-01-26)
2. **GitHub Repository**: <https://github.com/postrv/narsil-mcp> (accessed 2026-01-26)
3. **CHANGELOG**: <https://github.com/postrv/narsil-mcp/blob/main/CHANGELOG.md> (accessed 2026-01-26)
4. **Configuration Guide**: <https://github.com/postrv/narsil-mcp/blob/main/docs/configuration.md>
5. **Installation Guide**: <https://github.com/postrv/narsil-mcp/blob/main/docs/INSTALL.md>
6. **Neural Search Documentation**: <https://github.com/postrv/narsil-mcp/blob/main/docs/neural-search.md>
7. **Claude Code Integration Playbook**: <https://github.com/postrv/narsil-mcp/blob/main/docs/playbooks/integrations/claude-code.md>
8. **npm Package**: <https://www.npmjs.com/package/narsil-mcp>
9. **Crates.io**: <https://crates.io/crates/narsil-mcp>

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
