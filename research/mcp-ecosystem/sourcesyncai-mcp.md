---
title: "SourceSync.ai MCP Server"
research_date: "2026-02-23"
source_url: "https://sourcesync.ai"
github_url: "https://github.com/scmdr/sourcesyncai-mcp"
version_at_research: "v1.0.11"
license: "ISC"
last_verified: "2026-02-23"
version_at_verification: "v1.0.11"
next_review: "2026-05-23"
---

## Overview

SourceSync.ai MCP Server is a Model Context Protocol server that bridges AI models with SourceSync.ai's knowledge management platform. It enables AI assistants to ingest, search, and manage documents from diverse data sources (websites, cloud storage, SaaS tools) through a unified MCP interface. The server supports both semantic and hybrid search against AI-ready knowledge bases that are automatically kept in sync.

**Core Value Proposition**: Give AI models live access to a continuously-synced, multi-source knowledge base without custom retrieval pipelines — ingest once, search always-fresh.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI models lack access to up-to-date organizational knowledge | MCP interface exposes SourceSync.ai's auto-syncing knowledge base directly to AI tools |
| Building RAG pipelines requires complex custom ingestion code | 10 pre-built ingest tools cover text, URLs, sitemaps, websites, and 5 cloud storage connectors |
| Searching large document sets requires balancing recall vs. precision | Hybrid search combines semantic (vector) and keyword search with configurable weights |
| Keeping AI context fresh as source documents change | SourceSync.ai automatically resyncs connected sources; `resyncDocuments` tool forces refresh |
| Connecting multiple external data sources is bespoke work | Connection management tools (Google Drive, Notion, Dropbox, OneDrive, Box) via OAuth flows |
| Namespace isolation for multi-tenant or multi-project AI apps | Namespace CRUD tools allow scoped knowledge bases per project or tenant |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Repository | scmdr/sourcesyncai-mcp | 2026-02-23 |
| npm Package | sourcesyncai-mcp | 2026-02-23 |
| Latest Version | v1.0.11 | 2026-02-23 |
| Primary Language | TypeScript | 2026-02-23 |
| Node.js Requirement | >=18.0.0 | 2026-02-23 |
| MCP SDK Version | @modelcontextprotocol/sdk 1.6.1 | 2026-02-23 |
| Smithery Listing | @pbteja1998/sourcesyncai-mcp | 2026-02-23 |

---

## Key Features

### Authentication & Validation

- `validate_api_key`: Verify SourceSync.ai API key validity before making other calls

### Namespace Management

- `create_namespace`: Create a scoped knowledge base with configurable file storage (S3-compatible), vector store (Pinecone), and embedding model (OpenAI, Claude, Jina)
- `list_namespaces` / `get_namespace` / `update_namespace` / `delete_namespace`: Full CRUD lifecycle for namespace isolation

### Data Ingestion (10 Tools)

- `ingest_text`: Directly ingest raw text content with metadata tagging
- `ingest_urls`: Batch ingest from a list of web URLs
- `ingest_sitemap`: Crawl and ingest all pages listed in a sitemap XML
- `ingest_website`: Deep crawl with configurable `maxDepth` and `maxPages`
- `ingest_notion`: Pull from Notion workspaces via OAuth connection
- `ingest_google_drive`: Ingest files from Google Drive via OAuth connection
- `ingest_dropbox` / `ingest_onedrive` / `ingest_box`: Cloud storage connectors
- `get_ingest_job_run_status`: Poll async ingestion job progress

### Document Management

- `getDocuments`: Retrieve documents with type filters and optional parsed-text URL inclusion
- `updateDocuments`: Patch document metadata (status, category, custom fields)
- `deleteDocuments` / `resyncDocuments`: Remove or force-refresh selected documents
- `fetchUrlContent`: Retrieve raw parsed text from a document's content URL

### Search

- `semantic_search`: Vector similarity search with configurable `topK` results
- `hybrid_search`: Combined semantic + keyword search with `semanticWeight` / `keywordWeight` tuning

### Connection Management

- `create_connection` / `list_connections` / `get_connection` / `update_connection` / `revoke_connection`: OAuth connection lifecycle for all supported external services

---

## Technical Architecture

### MCP Tool Categories

<eg>
SourceSync.ai MCP Server (sourcesyncai-mcp v1.0.11)
├── Authentication (1 tool)
│   └── validate_api_key
├── Namespaces (5 tools)
│   └── create / list / get / update / delete
├── Data Ingestion (10 tools)
│   ├── Direct: ingest_text, ingest_urls, ingest_sitemap, ingest_website
│   ├── Cloud Storage: ingest_google_drive, ingest_dropbox, ingest_onedrive, ingest_box
│   ├── SaaS: ingest_notion
│   └── Status: get_ingest_job_run_status
├── Documents (5 tools)
│   └── getDocuments / updateDocuments / deleteDocuments / resyncDocuments / fetchUrlContent
├── Search (2 tools)
│   └── semantic_search / hybrid_search
└── Connections (5 tools)
    └── create / list / get / update / revoke
</eg>

### Namespace Configuration (Pluggable Backends)

Each namespace independently configures:

| Layer | Supported Providers |
|-------|---------------------|
| File Storage | S3-compatible (any endpoint) |
| Vector Store | Pinecone |
| Embedding Model | OpenAI, Claude, Jina |

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `SOURCESYNC_API_KEY` | Yes | Authentication token |
| `SOURCESYNC_NAMESPACE_ID` | No | Default namespace for all operations |
| `SOURCESYNC_TENANT_ID` | No | Multi-tenant isolation identifier |

---

## Installation & Usage

### Quick Start (npx)

```bash
env SOURCESYNC_API_KEY=your_api_key npx -y sourcesyncai-mcp
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "sourcesyncai-mcp": {
      "command": "npx",
      "args": ["-y", "sourcesyncai-mcp"],
      "env": {
        "SOURCESYNC_API_KEY": "your_api_key",
        "SOURCESYNC_NAMESPACE_ID": "your_namespace_id",
        "SOURCESYNC_TENANT_ID": "your_tenant_id"
      }
    }
  }
}
```

### Install via Smithery

```bash
npx -y @smithery/cli install @pbteja1998/sourcesyncai-mcp --client claude
```

### Document Retrieval Workflow

```json
// Step 1: Get document with content URL
{ "name": "getDocuments", "arguments": {
    "namespaceId": "namespace_XXX",
    "includeConfig": { "parsedTextFileUrl": true }
}}

// Step 2: Fetch actual text content
{ "name": "fetchUrlContent", "arguments": {
    "url": "https://api.sourcesync.ai/v1/documents/doc_XXX/content?format=text",
    "apiKey": "your_api_key"
}}
```

---

## Relevance to Claude Code Development

### Applications

- **Knowledge Base for Claude Skills**: Ingest Claude Code plugin documentation, skill references, and research entries into a SourceSync namespace; query via MCP during skill execution for grounded responses
- **Automatic Research Freshness**: Connect the research directory (exported to cloud storage) to SourceSync for auto-syncing; use hybrid search to surface relevant entries
- **Multi-source Context Assembly**: Aggregate Notion wikis, Google Drive docs, and web pages into a single searchable namespace for Claude Code sessions

### Patterns Worth Adopting

- **Pluggable Backend Pattern**: Namespaces decouple the knowledge graph from storage/embedding specifics — same API regardless of Pinecone vs. other vector stores; mirrors Claude Code's plugin-agnostic tool design
- **Async Ingestion with Status Polling**: `get_ingest_job_run_status` decouples long-running ingestion from immediate results — useful pattern for skills that process large documents
- **Namespace Isolation**: Per-project or per-tenant namespaces map well to Claude Code's scoped plugin/skill contexts

### Integration Opportunities

- **MCP Server Drop-in**: Add `sourcesyncai-mcp` to Claude Code's MCP config to give skills live knowledge base access without custom RAG code
- **Research Directory Sync**: Automate ingestion of `./research/**/*.md` into a SourceSync namespace for semantic search across all research entries
- **Skill Reference Grounding**: Ingest skill `SKILL.md` files and `references/` directories into SourceSync; query during skill creation to surface relevant prior art

### Competitive Context

| Feature | sourcesyncai-mcp | docs-mcp-server | mimir-mcp |
|---------|-----------------|-----------------|-----------|
| Cloud storage connectors | Yes (5) | No | No |
| SaaS connectors (Notion, etc.) | Yes | No | No |
| Semantic search | Yes | Yes | No |
| Hybrid search | Yes | No | No |
| Auto-sync | Yes (platform) | No | No |
| Self-hosted | No (SaaS) | Yes | Yes |
| Git-backed memory | No | No | Yes |
| Free tier | Yes | Yes (open source) | Yes (open source) |

---

## References

- [GitHub Repository](https://github.com/scmdr/sourcesyncai-mcp) (accessed 2026-02-23)
- [SourceSync.ai Website](https://sourcesync.ai) (accessed 2026-02-23)
- [SourceSync.ai API Reference](https://sourcesync.ai/api-reference/authentication) (accessed 2026-02-23)
- [Smithery Server Listing](https://smithery.ai/server/@pbteja1998/sourcesyncai-mcp) (accessed 2026-02-23)
- [npm Package](https://www.npmjs.com/package/sourcesyncai-mcp) (accessed 2026-02-23)
- [Model Context Protocol](https://modelcontextprotocol.io/introduction) (accessed 2026-02-23)

---
