---
name: Repomix - Pack Codebase into AI-Friendly Formats
description: Repomix is a powerful tool that packs entire repositories into a single, AI-friendly file optimized for consumption by Large Language Models (LLMs) such as Claude, ChatGPT, DeepSeek, Perplexity,...
license: MIT
metadata:
  topic: repomix
  category: developer-tools
  source_url: https://repomix.com
  github: yamadashy/repomix
  version: "v1.11.1"
  verified: "2026-01-31"
  next_review: "2026-04-30"
---

## Overview

Repomix is a powerful tool that packs entire repositories into a single, AI-friendly file optimized for consumption by Large Language Models (LLMs) such as Claude, ChatGPT, DeepSeek, Perplexity, Gemini, Llama, Grok, and others. It provides intelligent token counting, code compression using Tree-sitter, security scanning via Secretlint, and multiple output formats (XML, Markdown, JSON, Plain Text).

**Core Value Proposition**: Transform any codebase into a single file that AI can understand and analyze, with built-in token optimization, security checks, and format options tailored for different AI tool requirements.

---

## Problem Addressed

| Problem                                                                 | How Repomix Solves It                                                                              |
| ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Manually copying code files to share with AI is tedious and error-prone | Single command (`npx repomix`) packs entire repository into one AI-optimized file                  |
| Large codebases exceed AI context window limits                         | Token counting per file, Tree-sitter compression (~70% reduction), and split output options        |
| AI struggles to understand unstructured code dumps                      | XML/Markdown structure with file separators, directory trees, and metadata designed for AI parsing |
| Sensitive information may leak when sharing code with AI                | Built-in Secretlint security scanning detects API keys, passwords, and credentials                 |
| Need to analyze remote repositories without cloning                     | `--remote` option fetches and packs any GitHub repository directly                                 |
| Different AI tools have different format preferences                    | Multiple output styles: XML (Claude-optimized), Markdown, JSON, Plain Text                         |

---

## Key Statistics (as of January 31, 2026)

| Metric           | Value                           |
| ---------------- | ------------------------------- |
| GitHub Stars     | 21,597                          |
| Forks            | 1,004                           |
| Open Issues      | 142                             |
| Watchers         | 58                              |
| Primary Language | TypeScript                      |
| Contributors     | 50+ (5 top contributors listed) |
| npm Downloads    | Available via npm/npx           |
| Created          | July 13, 2024                   |
| Last Updated     | January 31, 2026                |

---

## Key Features

### Core Functionality

- **AI-Optimized Output**: Formats codebase for easy AI comprehension with structured separators
- **Token Counting**: Per-file and total token counts with configurable encoding (o200k_base, cl100k_base)
- **Token Count Tree**: Visual hierarchy showing token distribution across directories (`--token-count-tree`)
- **Git-Aware**: Respects `.gitignore`, `.ignore`, and `.repomixignore` files
- **Security Scanning**: Secretlint integration detects sensitive information before sharing

### Code Compression (Tree-sitter)

- **Intelligent Extraction**: Extracts function signatures, class definitions, and interfaces
- **Implementation Removal**: Strips function bodies while preserving structure
- **~70% Token Reduction**: Significantly reduces context usage while maintaining semantic meaning
- **Multi-Language Support**: TypeScript, JavaScript, Python, and more via Tree-sitter parsers

### Output Formats

| Format        | Command            | Best For                               |
| ------------- | ------------------ | -------------------------------------- |
| XML (default) | `--style xml`      | Claude (optimized for XML tag parsing) |
| Markdown      | `--style markdown` | Human readability, GitHub              |
| JSON          | `--style json`     | Programmatic processing, APIs          |
| Plain Text    | `--style plain`    | Universal compatibility                |

### Remote Repository Processing

```bash
# Full URL
repomix --remote https://github.com/yamadashy/repomix

# Shorthand
repomix --remote yamadashy/repomix

# Specific branch/commit
repomix --remote yamadashy/repomix --remote-branch main
repomix --remote https://github.com/yamadashy/repomix/tree/main
```

### MCP Server Integration

- **Model Context Protocol**: Native MCP server mode (`--mcp`)
- **7 MCP Tools**: pack_codebase, pack_remote_repository, attach_packed_output, read_repomix_output, grep_repomix_output, file_system_read_file, file_system_read_directory
- **AI Assistant Integration**: Works with Claude Code, Cursor, Cline, Claude Desktop

### Claude Code Plugins

Three official plugins available via `/plugin marketplace add yamadashy/repomix`:

1. **repomix-mcp**: Foundation plugin with MCP server integration
2. **repomix-commands**: Slash commands for quick operations
3. **repomix-explorer**: AI-powered repository analysis agent

### Agent Skills Generation

```bash
# Generate Claude Agent Skills from local directory
repomix --skill-generate

# Generate from remote repository
repomix --remote user/repo --skill-generate
```

Generated structure:

<eg>
.claude/skills/<skill-name>/
├── SKILL.md                 # Main metadata
└── references/
    ├── summary.md           # Purpose and statistics
    ├── project-structure.md # Directory tree
    ├── files.md             # All file contents
    └── tech-stack.md        # Auto-detected stack
</eg>

### Additional Features

- **Split Output**: `--split-output 1mb` for large codebases exceeding AI limits
- **Git Logs/Diffs**: `--include-logs` and `--include-diffs` for code evolution context
- **Comment Removal**: `--remove-comments` for supported languages
- **Stdin Support**: Pipe file lists from `find`, `git ls-files`, `fzf`
- **Docker Support**: `ghcr.io/yamadashy/repomix` container image
- **GitHub Actions**: Official action for CI/CD workflows
- **Browser Extension**: Chrome and Firefox extensions for GitHub
- **VSCode Extension**: Community-maintained Repomix Runner

---

## Technical Architecture

<eg>
User Input (Local Path / Remote URL / Stdin File List)
                        │
                        ▼
┌───────────────────────────────────────────────────────┐
│                   Input Processing                     │
│  - Path resolution and validation                      │
│  - Remote repository cloning (if --remote)             │
│  - Stdin file list parsing (if --stdin)                │
└───────────────────────────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────┐
│                   File Discovery                       │
│  - Glob pattern matching (--include)                   │
│  - Ignore pattern application                          │
│  - .gitignore / .ignore / .repomixignore parsing       │
│  - Default pattern filtering                           │
└───────────────────────────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────┐
│                 Security Scanning                      │
│  - Secretlint integration                              │
│  - API key / password detection                        │
│  - Sensitive file flagging                             │
└───────────────────────────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────┐
│                 Content Processing                     │
│  - File content extraction                             │
│  - Character encoding detection (jschardet)            │
│  - Comment removal (if enabled)                        │
│  - Tree-sitter compression (if --compress)             │
└───────────────────────────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────┐
│                  Token Counting                        │
│  - tiktoken tokenizer (o200k_base / cl100k_base)       │
│  - Per-file token counts                               │
│  - Directory aggregation for token tree                │
└───────────────────────────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────┐
│                  Output Generation                     │
│  - Format selection (XML/Markdown/JSON/Plain)          │
│  - Directory structure visualization                   │
│  - File content embedding with separators              │
│  - Custom header/instruction injection                 │
│  - Split output (if configured)                        │
└───────────────────────────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────┐
│                   Final Output                         │
│  - File writing (repomix-output.xml)                   │
│  - Clipboard copy (if --copy)                          │
│  - Stdout (if --stdout)                                │
│  - Skills directory (if --skill-generate)              │
└───────────────────────────────────────────────────────┘
</eg>

---

## Installation & Usage

### CLI Installation

```bash
# Instant use without installation (recommended)
npx repomix@latest

# Global installation
npm install -g repomix
yarn global add repomix
bun add -g repomix

# Homebrew (macOS/Linux)
brew install repomix
```

### Basic Usage

```bash
# Pack current directory
repomix

# Pack specific directory
repomix path/to/directory

# Pack with compression
repomix --compress

# Pack remote repository
repomix --remote yamadashy/repomix

# Pack specific files
repomix --include "src/**/*.ts,**/*.md"

# Output to stdout and pipe to LLM
repomix --stdout | llm "Please explain this code"
```

### Configuration

Create `repomix.config.json` via `repomix --init`:

```json
{
  "$schema": "https://repomix.com/schemas/latest/schema.json",
  "output": {
    "filePath": "repomix-output.xml",
    "style": "xml",
    "compress": false,
    "removeComments": false
  },
  "include": ["**/*"],
  "ignore": {
    "useGitignore": true,
    "useDefaultPatterns": true,
    "customPatterns": ["**/node_modules/**"]
  },
  "security": {
    "enableSecurityCheck": true
  }
}
```

TypeScript configuration also supported (`repomix.config.ts`) with `defineConfig` helper.

---

## Relevance to Claude Code Development

### Direct Applications

1. **Codebase Context Injection**: Pack entire projects as context for Claude Code sessions
2. **Remote Repository Analysis**: Analyze any GitHub repository without cloning locally
3. **Skills Generation**: Auto-generate Claude Agent Skills from any codebase
4. **MCP Integration**: Use as MCP server for direct AI assistant integration
5. **Token Budget Planning**: Understand token distribution to optimize what to include

### Patterns Worth Adopting

1. **XML Tag Structure**: Follows Anthropic's recommendation for using XML tags with Claude
2. **Security-First Design**: Secretlint integration prevents accidental credential exposure
3. **Configurable Compression**: Tree-sitter-based extraction for when full code is unnecessary
4. **Multi-Format Output**: Different formats for different AI tool preferences
5. **Split Output Strategy**: Handling large codebases that exceed context limits

### Integration Opportunities

1. **Claude Code MCP Server**: Already available via `repomix --mcp` or `/plugin install repomix-mcp@repomix`
2. **Skills Creation Pipeline**: `--skill-generate` produces Claude-ready skills directories
3. **Research Agent Pattern**: Use with research agents to analyze external codebases
4. **CI/CD Integration**: GitHub Action for automated codebase packaging
5. **Cursor/Cline/VSCode**: Broad IDE support through MCP protocol

### Competitive Alternatives

- **Gitingest**: Python-focused alternative for data science workflows
- **Skill Seekers**: Documentation-to-skill converter (complementary, different focus)

---

## References

1. **Official Website**: <https://repomix.com> (accessed 2026-01-31)
2. **GitHub Repository**: <https://github.com/yamadashy/repomix> (accessed 2026-01-31)
3. **npm Package**: <https://www.npmjs.com/package/repomix> (accessed 2026-01-31)
4. **Discord Community**: <https://discord.gg/wNYzTwZFku> (accessed 2026-01-31)
5. **Chrome Extension**: <https://chromewebstore.google.com/detail/repomix/fimfamikepjgchehkohedilpdigcpkoa>
6. **Firefox Add-on**: <https://addons.mozilla.org/firefox/addon/repomix/>
7. **VSCode Extension**: <https://marketplace.visualstudio.com/items?itemName=DorianMassoulier.repomix-runner>
8. **Anthropic XML Tags Guide**: <https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags>
9. **Tree-sitter**: <https://github.com/tree-sitter/tree-sitter>
10. **Secretlint**: <https://github.com/secretlint/secretlint>

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
