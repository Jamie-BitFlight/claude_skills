---
name: ctxforge
research_date: "2026-08-11"
source_url: "https://github.com/sylvester-francis/ctx-forge"
github_repository: "https://github.com/sylvester-francis/ctx-forge"
version_at_research: "2.1.0"
license: "AGPL-3.0"
freshness_tracking:
  last_verified: "2026-08-11"
  version_at_verification: "2.1.0 (released 2026-04-20)"
  next_review: "2026-11-11"
  confidence_map: "Overview: high | Problem Addressed: high | Key Features: high | Technical Architecture: high | Installation & Usage: high | Relevance: high | References: high"
---

# ctxforge

## Overview

ctxforge is a Rust-based CLI tool for prompt engineers that assembles context bundles for AI coding agents. Built by Sylvester Ranjith Francis, it implements five core context engineering strategies: library documentation detection, GitHub context mining, auto-suggest for missing imports, interactive TUI for prompt composition, and cross-session memory. The tool **never calls an LLM** — instead, it gathers, counts, and formats context for agents to consume. Version 2.1.0 (released April 2026); AGPL-3.0 licensed. Runs as a static Rust binary with zero cloud dependencies or API keys required.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Manual context assembly: developers manually copy-paste code sections into prompts, hoping they fit token budgets | Automated context bundling with real-time token counting for 15 named models prevents budget overruns |
| No visibility into token usage while building context prompts | Interactive TUI with live token gauge (color-coded green→yellow→orange→red) shows exact token consumption |
| Context management becomes fragmented across projects with no way to persist between sessions | Persistent markdown-based memory system enables cross-session note retention |
| Finding relevant code across a codebase requires manual file browsing | Tree-sitter scanning (optional, via `--features=extract`) finds every function/type and presents fuzzy-searchable picker |
| AI agents cannot autonomously build their own context without manual user intervention | 31 MCP tools enable Claude Code and other MCP clients to query and assemble context bundles independently |
| Missing documentation or stale dependencies go undetected when assembling context | Auto-suggest feature flags missing imports and stale dependencies between bundle and docs |

---

## Key Features

### 1. Five Core Context Engineering Strategies

ctxforge implements five interconnected approaches:

1. **Library docs / Project stack detection** — Scans manifests (`package.json`, `pyproject.toml`, `Cargo.toml`, etc.) and attaches canonical documentation URLs
2. **GitHub context miner** — Inlines specific issues, PRs, releases, or file bodies via `gh://` URIs with full `gh` CLI integration
3. **Auto-suggest** — Flags missing imports and stale dependencies between bundle and docs
4. **Interactive TUI** — Scenario-aware prompt composer with live preview and delivery options, built on iocraft 0.8 (replacing previous ratatui)
5. **Cross-session memory** — Persistent notes (markdown format) survive across agent interactions

**Source**: GitHub README.md — "Five Context Engineering Strategies" section (accessed 2026-08-11)

### 2. MCP Server Integration (31 Tools)

Exposes 31 tools via Model Context Protocol, enabling Claude Code and other MCP-compatible agents to assemble context autonomously.

**Transport**: Stdio JSON-RPC, protocol `2025-03-26`, no network or daemon required.

**Source**: GitHub README.md — "MCP Server" section; verified from WebFetch output "MCP server: 31 tools available" (accessed 2026-08-11)

### 3. Interactive TUI with 48 Slash Commands

Fullscreen terminal UI supports 48 slash commands accessible via `/` in interactive mode. TUI is built on **iocraft 0.8** with taffy flexbox layout.

**Source**: GitHub README.md — verified from WebFetch "TUI palette contains '48 unique entries' accessible via the `/` command" and "Built on 'iocraft 0.8'" (accessed 2026-08-11)

### 4. Token Counting for 15 Named Models

Exact token counting via **tiktoken** for OpenAI models (including claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5, gpt-4.1 family, o-series, gpt-4o family, gemini-2.5/1.5); character-based estimates (`chars / 4`) for unrecognized models. Real-time token gauge in TUI prevents budget overruns.

**Source**: GitHub README.md — "Supported models" section; verified from WebFetch "Uses 'tiktoken' for exact OpenAI model counts; character-based estimates" (accessed 2026-08-11)

### 5. Optional Tree-Sitter Function/Type Extraction

Function and type extraction available behind `--features=extract` flag. Supports Rust, Go, Python, TypeScript, and JavaScript.

**Source**: GitHub README.md — verified from WebFetch "Function/type extraction is available behind the `--features=extract` flag, supporting Rust, Go, Python, TypeScript, and JavaScript" (accessed 2026-08-11)

### 6. Multi-Language Installation Options

Three build profiles available:

- `cargo install ctxforge` — Latest features (recommended)
- `cargo install ctxforge --features=extract` — Includes tree-sitter extraction
- `cargo install ctxforge --no-default-features` — Minimal CLI-only (~6 MB static binary)

Requires Rust 1.85+; no runtime dependencies.

**Source**: GitHub README.md — Installation section (accessed 2026-08-11)

### 7. Core Property: Never Calls an LLM

**This is central to ctxforge's design**: ctxforge does not invoke or call any LLM itself. The tool exclusively handles prompt engineering tasks — context gathering, token counting, and formatting. LLMs consume the output; ctxforge does not call them.

**Source**: GitHub Cargo.toml description — verified from WebFetch "Deterministic prompt engineer for AI coding agents... never calls an LLM" (accessed 2026-08-11)

---

## Technical Architecture

### Core Components

**1. CLI & MCP Server**
Dual-mode binary: runs as CLI tool or MCP server. MCP mode exposes 31 tools via stdio JSON-RPC (protocol `2025-03-26`).

**2. TUI Engine**
Built on iocraft 0.8 with taffy flexbox layout. Supports 48 slash commands, live token counting, and scenario-aware prompt composition. No external daemon required.

**3. Token Counter**
Dual backend: tiktoken (OpenAI models, exact) or character-based estimates (4 chars per token) for other models.

**4. GitHub Integration**
Native `gh` CLI integration. Inlines GitHub resources (issues, PRs, files) via `gh://` URIs.

**5. Manifest Scanner**
Detects and attaches documentation URLs from project manifests: `package.json`, `pyproject.toml`, `Cargo.toml`, etc.

**6. Tree-Sitter Extraction (Optional)**
Enabled via `--features=extract`. Finds functions and types across Rust, Go, Python, TypeScript, JavaScript.

**7. Persistent Memory Store**
Markdown-based notes stored locally; no cloud sync required.

**Source**: GitHub README.md and Cargo.toml (accessed 2026-08-11)

---

## Installation & Usage

### Installation

```bash
# Latest features (recommended)
cargo install ctxforge

# With tree-sitter extraction
cargo install ctxforge --features=extract

# Minimal CLI-only
cargo install ctxforge --no-default-features
```

Requirements: Rust 1.85+, no external dependencies.

**Source**: GitHub README.md — Installation section (accessed 2026-08-11)

### Launch Interactive TUI

```bash
ctxforge
```

Starts fullscreen TUI with 48 available slash commands accessible via `/`.

**Source**: GitHub README.md — Usage section (accessed 2026-08-11)

### MCP Server Mode

```bash
# Launch as MCP server on stdio
ctxforge mcp
```

Exposes 31 MCP tools via stdio JSON-RPC (protocol `2025-03-26`).

**Source**: GitHub README.md — MCP Server section (accessed 2026-08-11)

### Token Counting (CLI)

Example: query exact token counts for your context bundle across multiple AI models. Tree-sitter extraction (if enabled) finds functions/types across supported languages.

**Source**: GitHub README.md (accessed 2026-08-11)

---

## Relevance to Claude Code Development

### Applications

1. **Autonomous Context Bundling**: Claude Code and other MCP clients can invoke ctxforge's 31 tools to query codebases, assemble context bundles, and pipe them to prompts without user intervention.

2. **Token Budget Visibility**: Real-time token counting prevents context window overruns across 15 named models.

3. **Cross-Session Context Persistence**: Persistent markdown memory enables AI agents to store learnings and patterns across sessions.

### Patterns Worth Adopting

- **Five-strategy context engineering**: The layered approach (manifest detection, GitHub mining, auto-suggest, TUI composition, persistent memory) provides a model for building context management systems.

- **MCP-driven automation**: Exposing 31 tools via MCP enables autonomous context assembly without manual user steps.

- **CLI + MCP dual mode**: Demonstrates how a single binary can serve both interactive and automated workflows.

---

## References

- [GitHub Repository: sylvester-francis/ctx-forge](https://github.com/sylvester-francis/ctx-forge) (accessed 2026-08-11)
- Cargo.toml, version 2.1.0 (released 2026-04-20) (accessed 2026-08-11)
- GitHub README.md — Five Context Engineering Strategies, MCP Server, Installation, Usage (accessed 2026-08-11)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude Code Prompt Improver](./claude-code-prompt-improver.md) | prompt-engineering | Both enhance Claude Code's prompt handling; Prompt Improver focuses on vagueness detection while ctxforge focuses on context assembly |

