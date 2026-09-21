---
name: Docs MCP Server (Grounded Docs) - Local Documentation Index for AI Assistants
description: Docs MCP Server (branded as "Grounded Docs") is an open-source MCP server that solves AI hallucinations and outdated knowledge by providing a personal, always-current documentation index. It fetches...
license: MIT
metadata:
  topic: docs-mcp-server
  category: mcp-ecosystem
  source_url: https://grounded.tools
  github: arabold/docs-mcp-server
  version: "v1.36.0"
  verified: "2026-01-26"
  next_review: "2026-04-26"
---

## Overview

Docs MCP Server (branded as "Grounded Docs") is an open-source MCP server that solves AI hallucinations and outdated knowledge by providing a personal, always-current documentation index. It fetches official docs from websites, GitHub, npm, PyPI, and local files, allowing AI assistants to query the exact library versions being used in a project.

**Core Value Proposition**: Open-source alternative to Context7, Nia, and Ref.Tools that runs entirely on your machine with full privacy.

---

## Problem Addressed

| Problem                                       | How Docs MCP Server Solves It                                           |
| --------------------------------------------- | ----------------------------------------------------------------------- |
| AI models have outdated training data         | Fetches documentation directly from official sources on demand          |
| AI hallucinations about APIs and features     | Grounds LLMs in real, current documentation                             |
| Context window limitations for large docs     | Semantic vector search retrieves only relevant chunks                   |
| Version mismatches (AI knows v1, user has v3) | Version-specific queries target exact library versions in project       |
| Privacy concerns with cloud services          | Runs entirely on local machine; code never leaves your network          |
| Single-format documentation sources           | Processes HTML, Markdown, PDF, Word, Excel, PowerPoint, and source code |

---

## Key Statistics (as of January 26, 2026)

| Metric           | Value                    |
| ---------------- | ------------------------ |
| GitHub Stars     | 954                      |
| Forks            | 113                      |
| Contributors     | 8                        |
| Open Issues      | 33                       |
| Primary Language | TypeScript (99%)         |
| npm Package      | @arabold/docs-mcp-server |
| Latest Version   | v1.36.0 (Jan 15, 2026)   |
| Created          | March 17, 2025           |

---

## Key Features

### 1. Multi-Source Documentation Indexing

- **Web Scraping**: Index any documentation website using Playwright
- **GitHub Repositories**: Index README, docs folders, source code
- **Package Registries**: Fetch from npm and PyPI
- **Local Files**: Index local folders and zip archives
- **llms.txt Support**: Automatic detection of LLM-ready documentation files

### 2. Rich File Format Support

- HTML and Markdown
- PDF documents
- Microsoft Office (Word .docx, Excel, PowerPoint)
- Source code files
- Password-protected PDFs

### 3. Semantic Vector Search

- **Multiple Embedding Providers**: OpenAI, Ollama, Google Gemini, Azure, AWS
- **Hybrid Search**: Combines vector similarity and full-text search
- **Reciprocal Rank Fusion (RRF)**: Configurable weights for optimal ranking
- **Dual-Mode FTS**: Exact phrase and keyword matching for improved recall

### 4. Version-Specific Queries

- Index multiple versions of the same library
- Query targets exact version in use
- Version tracking with re-indexing capability
- Change detection for documentation updates

### 5. Privacy-First Architecture

- Runs entirely on local machine
- No code or queries sent to external servers
- SQLite database with schema migrations
- Optional telemetry (privacy-first design)

### 6. Multiple Access Interfaces

- **Web UI**: Add/manage documentation at <http://localhost:6280>
- **CLI**: Command-line management
- **MCP Protocol**: Integration with Claude, Cline, Roo, etc.
- **SSE Endpoint**: Server-Sent Events for real-time updates

---

## Technical Architecture

<eg>
Documentation Sources
         |
         v
+---------------------------+
|    Scraper Strategies     |
|  - Web (Playwright)       |
|  - Local filesystem       |
|  - Package registries     |
+---------------------------+
         |
         v
+---------------------------+
|    Content Fetchers       |
|  - HTTP                   |
|  - Filesystem             |
|  - Registry APIs          |
+---------------------------+
         |
         v
+---------------------------+
|  Processing Pipelines     |
|  - Middleware chains      |
|  - Content-type handling  |
+---------------------------+
         |
         v
+---------------------------+
|   Document Splitters      |
|  - SemanticMarkdown       |
|  - JsonDocument           |
|  - TextDocument           |
|  - GreedySplitter (size)  |
+---------------------------+
         |
         v
+---------------------------+
|   Embedding Generation    |
|  - OpenAI, Gemini         |
|  - Ollama (local)         |
|  - Azure, AWS             |
+---------------------------+
         |
         v
+---------------------------+
|   SQLite Storage          |
|  - libraries table        |
|  - versions table         |
|  - documents table        |
+---------------------------+
         |
         v
+---------------------------+
|   Hybrid Search           |
|  - Vector similarity      |
|  - Full-text search       |
|  - RRF ranking            |
+---------------------------+
</eg>

### Deployment Modes

**Unified Mode (Default)**:

- Single process with MCP server, web interface, embedded worker
- Suitable for development and simple deployments
- Direct method calls between components
- Local event propagation via EventBus

**Distributed Mode (Docker Compose)**:

- Separate coordinator and worker processes
- Hub (shared worker) + Spokes (Web, MCP, CLI)
- tRPC for inter-process communication
- WebSocket for real-time events
- Scalable processing across containers

### Protocol Auto-Detection

- No TTY: stdio transport for direct MCP communication
- Has TTY: HTTP transport with Server-Sent Events
- Manual override: `--protocol stdio|http`

---

## Installation and Usage

### Quick Start

```bash
# Start server (requires Node.js 20+)
npx @arabold/docs-mcp-server@latest

# Open Web UI
# http://localhost:6280

# Add to MCP client config
{
  "mcpServers": {
    "docs-mcp-server": {
      "type": "sse",
      "url": "http://localhost:6280/sse"
    }
  }
}
```

### Docker Deployment

```bash
docker run --rm \
  -v docs-mcp-data:/data \
  -v docs-mcp-config:/config \
  -p 6280:6280 \
  ghcr.io/arabold/docs-mcp-server:latest \
  --protocol http --host 0.0.0.0 --port 6280
```

### Enable Embeddings (Recommended)

```bash
# OpenAI
OPENAI_API_KEY="sk-proj-..." npx @arabold/docs-mcp-server@latest

# Or Ollama (local, free)
OLLAMA_BASE_URL="http://localhost:11434" npx @arabold/docs-mcp-server@latest
```

---

## MCP Tools Provided

The server exposes tools via MCP protocol:

| Tool             | Description                                |
| ---------------- | ------------------------------------------ |
| `scrape_docs`    | Index documentation from URL or local path |
| `search_docs`    | Semantic search across indexed content     |
| `list_libraries` | Show all indexed libraries                 |
| `list_versions`  | Show versions for a library                |
| `get_job_status` | Check indexing job progress                |
| `cancel_job`     | Cancel running indexing job                |
| `fetch_url`      | Fetch URL and convert to markdown          |

---

## Configuration System

Configuration resolves via Zod schema with four layers:
Defaults < Config File < Environment Variables < CLI Arguments

**Key Settings**:

```yaml
# config.yaml
embedding:
  provider: openai  # or ollama, gemini, azure, aws
  model: text-embedding-3-small

storage:
  path: ~/.local/share/docs-mcp-server

server:
  port: 6280
  protocol: auto  # stdio, http, or auto
```

### Supported Embedding Providers

| Provider      | Local/Cloud | Cost |
| ------------- | ----------- | ---- |
| OpenAI        | Cloud       | Paid |
| Ollama        | Local       | Free |
| Google Gemini | Cloud       | Paid |
| Azure OpenAI  | Cloud       | Paid |
| AWS Bedrock   | Cloud       | Paid |

---

## Comparison with Alternatives

| Feature                   | Docs MCP Server   | Context7     | Nia          | Ref.Tools    |
| ------------------------- | ----------------- | ------------ | ------------ | ------------ |
| Open Source               | Yes (MIT)         | No           | No           | No           |
| Self-Hosted               | Yes               | No           | No           | No           |
| Privacy                   | Full (local)      | Cloud        | Cloud        | Cloud        |
| Custom Sources            | Yes               | Limited      | Limited      | Limited      |
| Multi-Provider Embeddings | Yes               | No           | No           | No           |
| Version-Specific          | Yes               | Yes          | Yes          | Yes          |
| Cost                      | Free + embeddings | Subscription | Subscription | Subscription |

---

## Relevance to Claude Code Development

### Direct Applications

1. **Documentation Grounding**: Eliminate hallucinations when coding with unfamiliar libraries
2. **Version-Specific Context**: Query docs for exact versions in project dependencies
3. **Local Privacy**: Keep proprietary documentation indexed locally
4. **Multi-Format Support**: Index internal docs in various formats (PDF, Word, etc.)

### Patterns Worth Adopting

1. **Semantic Chunking**: Two-phase splitting (semantic structure + size optimization)
2. **Hybrid Search**: Combining vector similarity with full-text for better recall
3. **Protocol Auto-Detection**: Automatic transport selection based on environment
4. **Write-Through Architecture**: Immediate persistence for recovery capability
5. **Distributed Mode Design**: Hub-spoke pattern for scalable processing

### Integration Opportunities

1. **Claude Code Plugin**: Create plugin that auto-indexes project dependencies
2. **Skill Enhancement**: Ground skills in current documentation automatically
3. **RAG Pattern**: Apply hybrid search approach to existing context systems
4. **Multi-Source Truth**: Pattern for combining documentation from multiple sources

### Complementary to Existing MCP Ecosystem

This fills a gap in the research directory's MCP ecosystem coverage:

- **Narsil MCP**: Code intelligence and security scanning
- **OctoCode MCP**: Research Driven Development with GitHub search
- **Docs MCP Server**: Documentation grounding and version-specific retrieval

---

## References

1. **GitHub Repository**: <https://github.com/arabold/docs-mcp-server> (accessed 2026-01-26)
2. **Official Website**: <https://grounded.tools> (accessed 2026-01-26)
3. **npm Package**: <https://www.npmjs.com/package/@arabold/docs-mcp-server> (accessed 2026-01-26)
4. **Architecture Documentation**: <https://github.com/arabold/docs-mcp-server/blob/main/ARCHITECTURE.md> (accessed 2026-01-26)
5. **Installation Guide**: <https://github.com/arabold/docs-mcp-server/blob/main/docs/setup/installation.md>
6. **MCP Protocol Specification**: <https://modelcontextprotocol.io/>

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [tolaria](../ai-design-tools/tolaria.md) | ai-design-tools | referenced by tolaria (ai-design-tools) |
| [repowise](./repowise.md) | mcp-ecosystem | referenced by repowise (mcp-ecosystem) |
| [claude-scientific-skills](../skill-generation-tools/claude-scientific-skills.md) | skill-generation-tools | referenced by claude-scientific-skills (skill-generation-tools) |
| [wigolo](./wigolo.md) | mcp-ecosystem | referenced by wigolo (mcp-ecosystem) |
