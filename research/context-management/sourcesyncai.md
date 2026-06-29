---
title: "SourceSync.ai"
research_date: "2026-02-23"
source_url: "https://sourcesync.ai"
github_url: "<https://github.com/scmdr/sourcesyncai-mcp> (MCP server)"
version_at_research: "SaaS platform (no version; REST API v1)"
license: "Proprietary SaaS (BYOC — Bring Your Own Cloud)"
last_verified: "2026-02-23"
version_at_verification: "REST API v1 (SaaS, versioned per release)"
next_review: "2026-05-23"
---

## Overview

SourceSync.ai is a managed RAG (Retrieval-Augmented Generation) infrastructure platform that continuously syncs data from 15+ external sources into AI-ready knowledge bases. Teams configure ingestion once — connecting cloud storage, SaaS wikis, websites, or raw text — and SourceSync automatically cleans, chunks, and embeds content, keeping it fresh as sources change. It exposes the resulting knowledge base via a REST API with semantic and hybrid search, and through an MCP server for direct AI assistant integration.

**Core Value Proposition**: Eliminate custom RAG pipelines by providing auto-syncing, multi-source knowledge bases accessible over a standard API — with BYOC storage and embeddings so no data ever touches SourceSync's infrastructure.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Building RAG ingestion pipelines requires significant custom engineering | Pre-built connectors for 15+ sources (cloud storage, SaaS, websites) eliminate bespoke ingestion code |
| AI knowledge becomes stale as source documents are updated | Automatic sync keeps vector indexes fresh when upstream sources change |
| Semantic search alone misses keyword-important queries | Hybrid search combines vector similarity with keyword matching, with configurable weights |
| Multi-tenant AI apps require isolated knowledge per customer | Namespace + tenant ID model provides scoped data isolation without separate deployments |
| Storing AI data in vendor cloud creates compliance concerns | BYOC model: file storage (S3-compatible) and vector DB (Pinecone) are customer-owned; SourceSync never retains data |
| Switching embedding models requires re-indexing everything | Per-namespace embedding model config (OpenAI, Claude, Jina) allows different strategies per use case |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Pricing — Pilot | $99/month (30M chars, 30k retrievals) | 2026-02-23 |
| Pricing — Pro | $299/month (150M chars, 150k retrievals) | 2026-02-23 |
| Pricing — Team | $999/month (750M chars, 750k calls) | 2026-02-23 |
| Enterprise | Custom / unlimited | 2026-02-23 |
| Free tier | 14-day money-back on paid plans | 2026-02-23 |
| Connectors (live) | Google Drive, Dropbox, OneDrive, Box, Notion | 2026-02-23 |
| Connectors (coming soon) | Confluence, GitBook, S3, GCS, Azure Blob, Slack, Gmail, Salesforce, Zendesk, Intercom, SharePoint | 2026-02-23 |
| Scraping integrations | Firecrawl, ScrapingBee, Jina | 2026-02-23 |
| Embedding providers | OpenAI, Claude, Jina | 2026-02-23 |
| MCP Server | `sourcesyncai-mcp` v1.0.11 on npm | 2026-02-23 |
| Notable customer | SiteGPT.ai | 2026-02-23 |

---

## Key Features

### Namespace-Based Knowledge Isolation

- Each **namespace** is a fully independent knowledge base with its own storage, vector DB, and embedding model
- Namespace CRUD via REST API or MCP tools (`create_namespace`, `list_namespaces`, etc.)
- Multi-tenant isolation via `X-Tenant-ID` header — single API key can serve multiple end-users with separate data

### Multi-Source Data Ingestion

- **Direct ingestion**: raw text, URL lists, sitemap crawl, full-website deep crawl (configurable depth/page limits)
- **Cloud storage connectors (live)**: Google Drive, Dropbox, OneDrive, Box
- **SaaS connectors (live)**: Notion
- **Coming soon**: Confluence, GitBook, S3, GCS, Azure Blob, Slack, Gmail, Outlook, Salesforce, ServiceNow, Zendesk, Intercom, SharePoint
- All ingestion is asynchronous — `get_ingest_job_run_status` polls completion
- Connector reuse: system deduplicates OAuth connections across tenants automatically

### Search

- **Semantic search**: vector similarity via `topK` retrieval
- **Hybrid search**: configurable `semanticWeight` + `keywordWeight` for precision/recall balance
- Retrieved documents include parsed text content URLs for downstream full-text access

### Document Lifecycle Management

- Filter, update metadata, delete, and force-resync individual documents
- `fetchUrlContent` retrieves raw parsed text from document content URLs

### Bring Your Own Cloud (BYOC) Model

- Customer provides S3-compatible bucket, Pinecone index, and embedding API keys
- SourceSync processes and routes data but does not retain it
- Supports enterprise security and compliance requirements

### MCP Integration

- Full MCP server (`sourcesyncai-mcp`) maps all REST API operations to 28 MCP tools
- Drop-in for Claude Desktop, Cursor, Windsurf, Claude Code — zero SDK required
- See `research/mcp-ecosystem/sourcesyncai-mcp.md` for detailed MCP tool inventory

---

## Technical Architecture

### Data Flow

<eg>
┌──────────────────────────────────────────────────────────────────┐
│                    SourceSync.ai Platform                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Source Connectors          Processing Pipeline                  │
│  ┌─────────────────┐        ┌───────────────────────────┐        │
│  │ Google Drive    │        │ 1. Clean & extract text   │        │
│  │ Dropbox / Box   │──────► │ 2. Chunk content          │        │
│  │ OneDrive        │        │ 3. Embed (BYOE model)     │        │
│  │ Notion          │        │ 4. Store in BYOC storage  │        │
│  │ URLs / Sitemaps │        └───────────┬───────────────┘        │
│  │ Raw Text        │                    │                        │
│  └─────────────────┘                    ▼                        │
│                              ┌─────────────────────┐            │
│  Customer Infrastructure:    │  Namespace Index     │            │
│  ┌──────────────────────┐    │  (Customer Pinecone) │            │
│  │ S3-compatible bucket │◄───│                     │            │
│  │ Pinecone index       │    └──────────┬──────────┘            │
│  │ Embedding model keys │               │                        │
│  └──────────────────────┘               ▼                        │
│                              ┌─────────────────────┐            │
│  Consumer Layer:             │  REST API / MCP      │            │
│  ┌──────────────────────┐    │  - semantic_search   │            │
│  │ Claude / Cursor / AI │◄───│  - hybrid_search     │            │
│  │ Custom app via API   │    │  - getDocuments      │            │
│  └──────────────────────┘    └─────────────────────┘            │
└──────────────────────────────────────────────────────────────────┘
</eg>

### Namespace Configuration Stack

| Layer | Customer-Provided |
|-------|------------------|
| File Storage | S3-compatible endpoint + credentials |
| Vector Store | Pinecone API key, environment, index |
| Embedding Model | OpenAI / Claude / Jina API key + model |

### Authentication Model

- **API Key**: Bearer token in `Authorization` header (per subscription)
- **Tenant ID**: Optional `X-Tenant-ID` header for multi-tenant data isolation
- **OAuth Connections**: Per-connector OAuth flows for cloud storage / SaaS, with automatic connection reuse across tenants

---

## Installation & Usage

### REST API (No SDK)

```bash
# Semantic search against a namespace
curl -X POST https://api.sourcesync.ai/v1/search \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "X-Tenant-ID: tenant_XXX" \
  -H "Content-Type: application/json" \
  -d '{
    "namespaceId": "namespace_XXX",
    "query": "how do I configure embeddings?",
    "topK": 5
  }'
```

### MCP Server (for AI assistants)

```bash
# Claude Desktop / Claude Code config
env SOURCESYNC_API_KEY=your_key npx -y sourcesyncai-mcp
```

```json
{
  "mcpServers": {
    "sourcesyncai-mcp": {
      "command": "npx",
      "args": ["-y", "sourcesyncai-mcp"],
      "env": {
        "SOURCESYNC_API_KEY": "your_api_key",
        "SOURCESYNC_NAMESPACE_ID": "your_namespace_id"
      }
    }
  }
}
```

### Example: Ingest a website, then search it

```bash
# 1. Ingest a website (async)
curl -X POST https://api.sourcesync.ai/v1/ingest \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"namespaceId":"ns_XXX","ingestConfig":{"source":"WEBSITE","config":{"url":"https://docs.example.com","maxDepth":3}}}'

# 2. Poll for completion
curl https://api.sourcesync.ai/v1/ingest/job/run_XXX -H "Authorization: Bearer YOUR_API_KEY"

# 3. Hybrid search when complete
curl -X POST https://api.sourcesync.ai/v1/search/hybrid \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"namespaceId":"ns_XXX","query":"getting started","hybridConfig":{"semanticWeight":0.7,"keywordWeight":0.3}}'
```

---

## Relevance to Claude Code Development

### Applications

- **Skill reference grounding**: Ingest all `SKILL.md` files and `references/` directories into a SourceSync namespace; query via MCP during skill execution for evidence-based answers
- **Research directory search**: Ingest `./research/**/*.md` for semantic search across all research entries — surface relevant prior art when creating new entries
- **Plugin documentation RAG**: Index plugin README files and `plugin.json` manifests for grounded plugin discovery and comparison

### Patterns Worth Adopting

- **BYOC / BYOE separation**: The model of "we process, you own the data" cleanly separates vendor responsibility from data sovereignty — applicable pattern for plugin designs that handle user secrets
- **Namespace isolation maps to plugin scope**: SourceSync namespaces parallel Claude Code's plugin-scoped contexts; one namespace per project keeps retrieval signals clean
- **Async ingestion with polling**: `get_ingest_job_run_status` pattern is reusable for any long-running knowledge base operation in agent workflows

### Integration Opportunities

- **Drop-in MCP context layer**: Add `sourcesyncai-mcp` to Claude Code's MCP server config to give all skills a live, searchable knowledge base without any RAG code
- **Auto-synced research entries**: Connect GitHub repository (via webhook or scheduled job) to SourceSync, so `./research/` changes are automatically indexed and searchable
- **Competitive context grounding**: Index competitor docs / changelogs in a namespace; query during skill creation to surface integration opportunities

### Comparison with Related Tools

| Feature | SourceSync.ai | Microsoft GraphRAG | Local Memory (`local-memory`) |
|---------|--------------|-------------------|-------------------------------|
| Hosted/managed | Yes (SaaS) | No (self-hosted) | No (local) |
| Auto-sync from sources | Yes | No | No |
| Multi-source connectors | Yes (15+) | No (files only) | No |
| Hybrid search | Yes | No (graph-based) | No |
| BYOC storage | Yes (required) | No | Yes |
| Knowledge graph | No | Yes | No |
| Free tier | No (paid only) | Yes (open source) | Yes (open source) |
| MCP server | Yes | No | No |
| Multi-tenant | Yes (X-Tenant-ID) | No | No |

---

## References

- [SourceSync.ai Website](https://sourcesync.ai) (accessed 2026-02-23)
- [SourceSync.ai Pricing](https://sourcesync.ai/pricing) (accessed 2026-02-23)
- [SourceSync.ai Connectors](https://sourcesync.ai/connectors) (accessed 2026-02-23)
- [API Reference — Authentication](https://sourcesync.ai/api-reference/authentication) (accessed 2026-02-23)
- [MCP Server Repository](https://github.com/scmdr/sourcesyncai-mcp) (accessed 2026-02-23)
- [MCP Server on Smithery](https://smithery.ai/server/@pbteja1998/sourcesyncai-mcp) (accessed 2026-02-23)

---
