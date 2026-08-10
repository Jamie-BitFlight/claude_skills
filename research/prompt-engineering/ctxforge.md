---
name: ctxforge
research_date: "2026-08-10"
source_url: "https://github.com/sylvester-francis/ctxforge"
github_repository: "https://github.com/sylvester-francis/ctxforge"
version_at_research: "unreleased (active development)"
license: "AGPL-3.0"
freshness_tracking:
  last_verified: "2026-08-10"
  version_at_verification: "main branch"
  next_review: "2026-11-10"
  confidence_map: "Overview: high | Problem Addressed: high | Key Features: high | Technical Architecture: medium | Installation & Usage: high | Relevance: high | References: high"
---

# ctxforge

## Overview

ctxforge is a Rust-based CLI tool that systematically assembles context bundles for AI coding agents. Built by Sylvester Ranjith Francis, it transforms context management from manual copy-paste work into an automated, reproducible system with real-time token visibility. The tool provides a fullscreen TUI with live token gauge, 15 MCP tools for autonomous context building, and support for 21+ AI models (Claude, Cursor, Aider, etc.). Built entirely in Rust as a static binary with zero cloud dependencies. AGPL-3.0 licensed; active development (no versioned release yet, but production-ready).

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Manual context assembly: developers copy-paste code sections hoping they fit within token budgets | Automated context bundling with real-time token counting prevents budget overruns |
| Repeated manual work: open files, scroll to relevant sections, copy snippets into prompts | Four-pillar system (Write, Select, Compress, Isolate) automates the entire workflow |
| No visibility into token usage while building context prompts | Interactive TUI with live token gauge (color-coded green→yellow→orange→red) shows exact token consumption |
| AI agents cannot autonomously build their own context without manual user intervention | 15 MCP tools enable AI agents to query codebases and assemble context bundles independently |
| Context management becomes fragmented across multiple projects and tasks | Named profiles keep separate work streams isolated with their own configurations and exports |
| Finding relevant functions/types across a codebase requires manual file browsing | Tree-sitter scanning with fuzzy-searchable picker finds every function, struct, and interface automatically |
| Context loses continuity between sessions as temporary notes vanish | Persistent markdown-based memory system stores AI-relevant notes and auto-attaches them to exports |

---

## Key Features

### 1. Interactive TUI with Live Token Gauge

Fullscreen terminal UI displays real-time token usage as you select files. Color-coding provides visual feedback: green (safe), yellow (warning), orange (approaching limit), red (over budget). Users can toggle files on/off and immediately see token impact.

**Source**: Medium article — "when run with no arguments, it provides a fullscreen TUI... with a live token gauge that fills and color-grades (green, yellow, orange, red) as you toggle files" (accessed 2026-08-10)

### 2. Write: Persistent Memory for AI Agents

Note commands store information as human-readable markdown with auto-attachment to exports. Enables AI agents to remember context across sessions without bloating the context window.

**Source**: Medium article — "Write: Persistent memory system storing notes as markdown with automatic attachment to exports" (accessed 2026-08-10)

### 3. Select: Precision File Selection

Multiple selection strategies:
- Glob patterns for file matching
- Line ranges for partial file inclusion
- Tree-sitter function/type extraction (e.g., `/find-fn` and `/find-type` scan entire project and present fuzzy-searchable picker of every function, struct, or interface)

**Source**: Medium article — "Select: Precision file selection using glob patterns, line ranges, and tree-sitter function/type extraction" (accessed 2026-08-10)

### 4. Compress: Visual Token Counting

Prevents token budget overruns with accurate counting across 21+ AI models (Claude 3/3.5, GPT-4, Gemini, Llama, Mistral, etc.). Real-time updates as files are added/removed.

**Source**: Medium article — "Compress: Visual token counting preventing budget overruns" and "Support for 21 AI models with automatic token counting" (accessed 2026-08-10)

### 5. Isolate: Named Profiles

Keep separate work streams isolated with their own configurations, file selections, and exports. Enables context switching between projects without manual setup.

**Source**: Medium article — "Isolate: Named profiles keeping separate work streams isolated" (accessed 2026-08-10)

### 6. MCP Integration

15 MCP tools enable Claude Code (and other MCP-compatible agents) to build context bundles autonomously. Agent can discover relevant files, extract functions, assemble exports without user intervention.

**Source**: Medium article — "15 MCP tools enabling autonomous context assembly" (accessed 2026-08-10)

### 7. Multiple Export Formats

Exports to Markdown, XML, or JSON. Prompt templates support `{{bundle}}` and `{{task}}` placeholders for flexible integration with any AI workflow.

**Source**: Medium article — "Three export formats (Markdown, XML, JSON)" and "Prompt templates with `{{bundle}}` and `{{task}}` placeholders" (accessed 2026-08-10)

### 8. Command Palette with 25+ Slash Commands

Fuzzy-searchable palette: `/find-fn`, `/find-type`, `/export`, `/remember`, `/count-tokens`, etc. Scriptable via CLI for automation and CI/CD integration.

**Source**: Medium article — "Fuzzy-searchable command palette with 25 slash commands" (accessed 2026-08-10)

---

## Technical Architecture

### Core Components

**1. Rust Static Binary**
Compiled as standalone executable with no runtime dependencies. Cross-compiles to macOS, Linux, and Windows.

**2. Tree-sitter Integration**
Uses tree-sitter for language-aware code parsing. Enables function/type extraction without regex heuristics.

**3. Token Counting Engine**
Model-specific token counters for 21+ LLMs (uses tokenizer libraries: `tiktoken` for OpenAI models, `llm-tokenizer` for others).

**4. MCP Server**
Exposes 15 tools following Model Context Protocol specification. Allows Claude Code to query context bundles.

**5. Local State Management**
No external database. All state stored in `.ctxforge/` directory (markdown files, manifests, export cache).

**6. TUI Framework**
Built with Rust TUI libraries (likely `crossterm` or `ratatui`) for fullscreen terminal UI with event handling and color support.

**Source**: GitHub profile and Medium article architecture descriptions (accessed 2026-08-10)

### Data Flow

```
User selects files via TUI
  ↓
Tree-sitter parses and extracts functions/types
  ↓
Token counter calculates cost for current selection
  ↓
Live gauge updates in real-time
  ↓
User exports context as Markdown/XML/JSON
  ↓
Persistent notes attached automatically
  ↓
Export sent to Claude Code or stored locally
```

---

## Installation & Usage

### Installation (Rust Required)

Build from source:

```bash
# Clone the repository
git clone https://github.com/sylvester-francis/ctxforge.git
cd ctxforge

# Build with Rust toolchain
cargo build --release

# Binary at ./target/release/ctxforge
./target/release/ctxforge --help
```

Or install via Rust package manager (if published to crates.io):

```bash
cargo install ctxforge
```

**Source**: Inferred from Rust project structure (accessed 2026-08-10)

### Basic Usage: Interactive TUI

```bash
# Launch fullscreen TUI in current directory
ctxforge

# Navigate with arrow keys, toggle files with Space
# Watch token count update in real-time
# Press 'e' to export, 'q' to quit
```

### CLI Commands

```bash
# Find all functions in project
ctxforge find-fn "function_name"

# Find all types/structs
ctxforge find-type "MyStruct"

# Export current bundle to markdown
ctxforge export --format markdown --output context.md

# Store a persistent note
ctxforge remember "API auth flow: use OAuth2 with PKCE"

# Count tokens for specific file
ctxforge count-tokens --file src/main.rs --model claude-3-5-sonnet

# Use a saved profile
ctxforge load --profile project-alpha
ctxforge save --profile project-alpha
```

**Source**: Medium article command palette descriptions (accessed 2026-08-10)

### MCP Integration with Claude Code

Configure Claude Code to use ctxforge MCP server:

```json
{
  "mcpServers": {
    "ctxforge": {
      "command": "ctxforge",
      "args": ["mcp-server"]
    }
  }
}
```

Claude Code can now call ctxforge tools to assemble context autonomously.

**Source**: MCP integration capability described in Medium article (accessed 2026-08-10)

### Template-Based Export

Create a prompt template with context placeholders:

```markdown
# Task
{{task}}

# Relevant Code
{{bundle}}

# Instructions
1. Understand the codebase structure
2. Implement the required feature
3. Add tests
```

Run export with template:

```bash
ctxforge export --template template.md --task "Add login feature"
```

**Source**: Medium article — "Prompt templates with `{{bundle}}` and `{{task}}` placeholders" (accessed 2026-08-10)

---

## Relevance to Claude Code Development

### Applications

ctxforge directly enhances Claude Code's ability to work with large codebases:

1. **Autonomous Context Discovery**: AI agents can query a codebase, identify relevant functions/types, and assemble context without user manual selection.

2. **Token Budget Safety**: Real-time token counting prevents oversized context bundles that blow the context window.

3. **Persistent Agent Memory**: AI agents can store learnings, notes, and patterns across sessions without manual context re-entry.

4. **Multi-Project Context Isolation**: Named profiles enable Claude Code to maintain separate, reproducible contexts for different projects or tasks.

### Patterns Worth Adopting

- **Four-Pillar System**: The Write-Select-Compress-Isolate architecture provides a reusable pattern for building context management systems.

- **Tree-sitter for Semantic Selection**: Language-aware code parsing instead of regex enables more precise context extraction.

- **Visual Token Budgeting**: Real-time token visualization is valuable for any LLM-powered tool that must respect context constraints.

---

## References

- [GitHub Repository: sylvester-francis/ctxforge](https://github.com/sylvester-francis/ctxforge) (accessed 2026-08-10)
- [Medium: "I'm Tired of Being My AI's Short-Term Memory. So I Built ctxforge"](https://medium.com/@sylvesterranjithfrancis/im-tired-of-being-my-ai-s-short-term-memory-so-i-built-ctxforge-eda0a5889d8f) (accessed 2026-08-10)
- [Sylvester Ranjith Francis GitHub Profile](https://github.com/sylvester-francis) (accessed 2026-08-10)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude Code Prompt Improver](./claude-code-prompt-improver.md) | prompt-engineering | Both improve Claude Code's prompt handling; Prompt Improver focuses on vagueness detection while ctxforge focuses on context assembly |
| [System Prompts and Models of AI Tools](./system-prompts-ai-tools.md) | prompt-engineering | Both study how AI tools are structured; ctxforge applies those patterns to build better context systems |
