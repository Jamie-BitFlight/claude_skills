---
name: notion-mcp-server
research_date: 2026-05-30
source_url: https://github.com/makenotion/notion-mcp-server
github_repository: https://github.com/makenotion/notion-mcp-server
version_at_research: v2.3.1
license: MIT
freshness_tracking:
  last_verified: 2026-05-30
  version_at_verification: v2.3.1
  next_review: 2026-08-30
  confidence_map: "Overview: high, Problem Addressed: high, Key Features: high, Technical Architecture: high, Installation & Usage: high, Relevance to Claude Code: medium"
---

# notion-mcp-server

## Overview

The `@notionhq/notion-mcp-server` (v2.3.1) is an OpenAPI-spec-driven proxy that exposes 22 MCP tools for interacting with Notion workspaces. It automatically converts Notion's OpenAPI specification into MCP tool definitions and forwards tool calls as HTTP requests to `api.notion.com`. The server implements cursor-based pagination, block tree lazy-loading, and metadata-first access patterns for large hierarchies. (Accessed: https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/README.md, 2026-05-30)

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI assistants lack structured access to Notion workspaces | notion-mcp-server exposes 22 MCP tools covering search, pages, blocks, comments, users, and database operations (accessed 2026-05-30) |
| Large page bodies and block trees exceed AI token budgets | Lazy-loading design: `retrieve-a-page` returns properties only; `retrieve-block-children` fetches content separately; agents control depth traversal (accessed 2026-05-30) |
| Notion's nested hierarchies require multiple API calls to discover structure | Block model carries `has_children: boolean` flag enabling selective tree traversal without pre-fetching all children (accessed 2026-05-30) |
| Result pagination requires manual cursor iteration | Cursor-based pagination exposed directly: `start_cursor`/`page_size` as tool parameters; `has_more`/`next_cursor` in responses enable agent-controlled iteration (accessed 2026-05-30) |
| Confusing tool selection in search-before-fetch workflows | `search` returns lightweight result objects (id, title, timestamps) without page body; agents identify targets before calling content tools (accessed 2026-05-30) |

---

## Key Features

### Search & Discovery Tools
- **search**: Semantic search across pages and databases by title with optional type filtering and sorting by `last_edited_time` / `created_time`

### Page Operations
- **retrieve-a-page**: Fetch page properties (title, status, dates, etc.) — not body content
- **create-a-page**: Create new page with properties
- **update-page-properties**: Modify page metadata
- **move-page**: Relocate page in hierarchy
- **retrieve-a-page-property**: Get single property item

### Block Operations (Content Access)
- **retrieve-a-block**: Fetch single block metadata
- **retrieve-block-children**: List child blocks (paginated, max 100 per call) with `has_more`/`next_cursor`
- **append-block-children**: Add new blocks
- **delete-a-block**: Remove block
- **update-a-block**: Modify block content

### Database & Data Source Operations
- **retrieve-a-database**: Get database metadata plus data source IDs
- **query-data-source**: Query database with filters and sorts
- **retrieve-a-data-source**: Get schema and properties
- **update-a-data-source**: Modify data source properties
- **create-a-data-source**: Create new data source
- **list-data-source-templates**: List templates in data source

### Comment & User Operations
- **list-comments**: List comments on block or page
- **create-a-comment**: Add new comment
- **list-all-users**: List workspace users
- **retrieve-a-user**: Get single user details
- **retrieve-your-token-s-bot-user**: Get integration bot user

Total: **22 tools** exposing Notion REST API v1 (accessed 2026-05-30)

---

## Technical Architecture

The server is built as an **OpenAPI-spec-driven proxy** rather than hand-coded tool definitions.

### Tooling Pipeline
1. **Startup**: `src/init-server.ts` loads bundled OpenAPI JSON spec via `fs.readFileSync`
2. **Parsing**: `src/openapi-mcp-server/openapi/parser.ts` (`OpenAPIToMCPConverter`) parses every `operationId` into an MCP tool definition
3. **Registration**: `src/openapi-mcp-server/mcp/proxy.ts` (`MCPProxy`) registers tools with MCP SDK
4. **Execution**: Tool calls forwarded as HTTP requests to `api.notion.com` with Bearer token auth

(Source: src/init-server.ts, src/openapi-mcp-server/openapi/parser.ts, src/openapi-mcp-server/mcp/proxy.ts, accessed 2026-05-30)

### Pagination Model: Cursor-Based
- **Request parameters**: `start_cursor` (opaque token, default undefined), `page_size` (default 100, max 100)
- **Response fields**: `has_more` (boolean), `next_cursor` (string, present only when `has_more: true`), `results` (array of objects), `type` (e.g., "block", "page", "user")
- **Mechanism**: Opaque cursor token — treat as black box, not offset arithmetic (Source: https://developers.notion.com/reference/pagination, accessed 2026-05-30)

### Block Tree Lazy-Loading
- **`has_children` flag**: Every block carries boolean indicating whether children exist
- **One level at a time**: Agent receives top-level blocks from `retrieve-block-children(page_id)`. Each block with `has_children: true` requires separate `retrieve-block-children(block_id)` call
- **Structural types**: Headings, paragraphs, lists, toggles, child pages (accessed 2026-05-30)

### Progressive-Disclosure Workflow
1. **Search first**: `search` returns lightweight result objects (id, title, timestamps) without body
2. **Fetch metadata**: `retrieve-a-page` returns properties only, not body
3. **Fetch body separately**: `retrieve-block-children` for content
4. **Traverse conditionally**: Use `has_children` to decide which blocks to expand

### Response Optimization
- **Tool name truncation**: Hard-truncated to 64 characters (MCP spec limit) with collision-safe suffix (Source: src/openapi-mcp-server/mcp/proxy.ts, accessed 2026-05-30)
- **Description prefix**: All tools get `"Notion | "` prefix for disambiguation in multi-server contexts (Source: src/openapi-mcp-server/openapi/parser.ts, accessed 2026-05-30)
- **Tool annotations**: `readOnlyHint: true` for GET, `destructiveHint: true` for write operations
- **No body truncation**: Responses returned in full; caller manages budget via tool selection

---

## Installation & Usage

### Installation

The Notion MCP server is available via npm:

```bash
npm install -g @notionhq/notion-mcp-server
```

### Configuration

Configure in `.mcp.json` or IDE MCP settings with Notion integration token:

```json
{
  "mcpServers": {
    "notion": {
      "command": "notion-mcp-server",
      "env": {
        "NOTION_API_TOKEN": "secret_your_token_here"
      }
    }
  }
}
```

### Example Workflow

**Search for a page:**
```bash
search(query="My Project", filter={value: "page"})
# Returns: [{ id: "abc123", title: "My Project", url: "...", last_edited_time: "2026-05-30T..." }]
```

**Fetch page properties:**
```bash
retrieve-a-page(page_id="abc123")
# Returns: { id, properties: { title, status, dates, ... }, parent: ... }
```

**List child blocks (first page):**
```bash
retrieve-block-children(block_id="abc123", page_size=50)
# Returns: { object: "list", results: [...], has_more: true, next_cursor: "opaque_token" }
```

**Paginate to next block batch:**
```bash
retrieve-block-children(block_id="abc123", page_size=50, start_cursor="opaque_token")
# Returns: next batch of blocks
```

---

## Relevance to Claude Code Development

### Applications
- **Notion workspace integration**: AI assistants can search, navigate, and read Notion documents as project context
- **Large hierarchy traversal**: Block tree lazy-loading pattern is directly applicable to large documentation systems and code repositories
- **Progressive-disclosure for complex structures**: Metadata-first approach (fetch properties, then body, then nested content) reduces token consumption on large workspaces

### Patterns Worth Adopting
- **Two-phase separation of metadata and body**: `retrieve-a-page` (properties only) vs. `retrieve-block-children` (body) allows agents to decide whether body fetch is necessary
- **Cursor-based pagination with explicit `has_more` signalling**: Opaque cursor tokens prevent agent misuse; `has_more` flag enables lazy iteration
- **`has_children` flag for selective traversal**: Structural hints allow agents to navigate hierarchies without blind recursion
- **Search-before-fetch discipline**: Lightweight search results (id, title, timestamps) force agents to identify targets before fetching large bodies
- **Tool naming conventions**: Prefix (e.g., "Notion | ") disambiguates tools in multi-server contexts

### Integration Opportunities
- Notion workspace as project documentation source for Claude Code
- Cross-reference Notion databases with codebase analysis
- Block tree navigation patterns for other hierarchical systems

---

## References

- [notion-mcp-server GitHub Repository](https://github.com/makenotion/notion-mcp-server) (accessed 2026-05-30)
- [README.md](https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/README.md) (accessed 2026-05-30)
- [src/init-server.ts — Spec loading](https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/src/init-server.ts) (accessed 2026-05-30)
- [src/openapi-mcp-server/openapi/parser.ts — Tool generation](https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/src/openapi-mcp-server/openapi/parser.ts) (accessed 2026-05-30)
- [src/openapi-mcp-server/mcp/proxy.ts — Tool registration and execution](https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/src/openapi-mcp-server/mcp/proxy.ts) (accessed 2026-05-30)
- [Notion API Pagination Reference](https://developers.notion.com/reference/pagination) (accessed 2026-05-30)
- [Notion API Block Reference](https://developers.notion.com/reference/block) (accessed 2026-05-30)
- [Notion API Search Reference](https://developers.notion.com/reference/post-search) (accessed 2026-05-30)
- [Notion API Get Block Children](https://developers.notion.com/reference/get-block-children) (accessed 2026-05-30)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [mcpvault](./mcpvault.md) | mcp-ecosystem | Sibling pattern: Notion block lazy-loading vs. mcpvault BM25 search |
| [obsidian-mcp-server](./obsidian-mcp-server.md) | mcp-ecosystem | Complementary: Obsidian local-first vs. Notion cloud-native |
