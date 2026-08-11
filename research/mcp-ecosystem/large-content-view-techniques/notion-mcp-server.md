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
| Large page bodies and block trees exceed AI token budgets | Lazy-loading design: `API-retrieve-a-page` returns properties only; `API-get-block-children` fetches content separately; agents control depth traversal (accessed 2026-05-30) |
| Notion's nested hierarchies require multiple API calls to discover structure | Block model carries `has_children: boolean` flag enabling selective tree traversal without pre-fetching all children (accessed 2026-05-30) |
| Result pagination requires manual cursor iteration | Cursor-based pagination exposed directly: `start_cursor`/`page_size` as tool parameters; `has_more`/`next_cursor` in responses enable agent-controlled iteration (accessed 2026-05-30) |
| Confusing tool selection in search-before-fetch workflows | `API-post-search` returns lightweight result objects (id, title, timestamps) without page body; agents identify targets before calling content tools (accessed 2026-05-30) |

---

## Key Features

Tool names are not hand-written. `OpenAPIToMCPConverter.convertToMCPTools()` groups every operation
under the single API name `'API'` and registers each as `` `${apiName}-${operationId}` `` — so the
name an MCP client sees is `API-` followed by the `operationId` verbatim from
`scripts/notion-openapi.json`. Listing the operationIds below with their HTTP bindings, taken from
that spec file (do not assume the REST endpoint's colloquial name matches the operationId — several
do not).

### Search & Discovery
- **`API-post-search`** (POST `/v1/search`): Search pages and databases by title, with optional
  `filter.value` of `page`/`database` and sorting by `last_edited_time`

### Page Operations
- **`API-retrieve-a-page`** (GET `/v1/pages/{page_id}`): Fetch page properties — not body content
- **`API-post-page`** (POST `/v1/pages`): Create new page with properties
- **`API-patch-page`** (PATCH `/v1/pages/{page_id}`): Update page properties
- **`API-move-page`** (POST `/v1/pages/{page_id}/move`): Relocate page in hierarchy
- **`API-retrieve-a-page-property`** (GET `/v1/pages/{page_id}/properties/{property_id}`): Get a
  single property item

### Block Operations (Content Access)
- **`API-retrieve-a-block`** (GET `/v1/blocks/{block_id}`): Fetch single block metadata
- **`API-get-block-children`** (GET `/v1/blocks/{block_id}/children`): List child blocks, paginated
  (`page_size` default 100, maximum 100) with `has_more`/`next_cursor`
- **`API-patch-block-children`** (PATCH `/v1/blocks/{block_id}/children`): Append new blocks
- **`API-delete-a-block`** (DELETE `/v1/blocks/{block_id}`): Remove block
- **`API-update-a-block`** (PATCH `/v1/blocks/{block_id}`): Modify block content

### Database & Data Source Operations
- **`API-retrieve-a-database`** (GET `/v1/databases/{database_id}`): Get database metadata plus data
  source IDs
- **`API-query-data-source`** (POST `/v1/data_sources/{data_source_id}/query`): Query with filters
  and sorts
- **`API-retrieve-a-data-source`** (GET `/v1/data_sources/{data_source_id}`): Get schema and
  properties
- **`API-update-a-data-source`** (PATCH `/v1/data_sources/{data_source_id}`): Modify data source
- **`API-create-a-data-source`** (POST `/v1/data_sources`): Create new data source
- **`API-list-data-source-templates`** (GET `/v1/data_sources/{data_source_id}/templates`): List
  templates

### Comment & User Operations
- **`API-retrieve-a-comment`** (GET `/v1/comments`): List comments on a block or page — the
  operationId reads as singular but the endpoint returns a paginated list
- **`API-create-a-comment`** (POST `/v1/comments`): Add new comment
- **`API-get-users`** (GET `/v1/users`): List workspace users
- **`API-get-user`** (GET `/v1/users/{user_id}`): Get single user details
- **`API-get-self`** (GET `/v1/users/me`): Get the integration's bot user

Total: **22 operationIds** in `scripts/notion-openapi.json`, each becoming one MCP tool
(accessed 2026-05-30)

---

## Technical Architecture

The server is built as an **OpenAPI-spec-driven proxy** rather than hand-coded tool definitions.

### Tooling Pipeline
1. **Startup**: `src/init-server.ts` loads bundled OpenAPI JSON spec via `fs.readFileSync`
2. **Parsing**: `src/openapi-mcp-server/openapi/parser.ts` (`OpenAPIToMCPConverter`) parses every `operationId` into an MCP tool definition, keyed as `` `${apiName}-${uniqueName}` `` with `apiName` hard-coded to `'API'`
3. **Registration**: `src/openapi-mcp-server/mcp/proxy.ts` (`MCPProxy`) registers tools with MCP SDK
4. **Execution**: Tool calls forwarded as HTTP requests to `api.notion.com` with Bearer token auth

(Source: src/init-server.ts, src/openapi-mcp-server/openapi/parser.ts, src/openapi-mcp-server/mcp/proxy.ts, accessed 2026-05-30)

### Pagination Model: Cursor-Based
- **Request parameters**: `start_cursor` (opaque token, default undefined), `page_size` (default 100, max 100)
- **Response fields**: `has_more` (boolean), `next_cursor` (string, present only when `has_more: true`), `results` (array of objects), `type` (e.g., "block", "page", "user")
- **Mechanism**: Opaque cursor token — treat as black box, not offset arithmetic (Source: https://developers.notion.com/reference/pagination, accessed 2026-05-30)

### Block Tree Lazy-Loading
- **`has_children` flag**: Every block carries boolean indicating whether children exist
- **One level at a time**: Agent receives top-level blocks from `API-get-block-children(block_id=page_id)`. Each block with `has_children: true` requires a separate `API-get-block-children(block_id)` call
- **Structural types**: Headings, paragraphs, lists, toggles, child pages (accessed 2026-05-30)

### Progressive-Disclosure Workflow
1. **Search first**: `API-post-search` returns lightweight result objects (id, title, timestamps) without body
2. **Fetch metadata**: `API-retrieve-a-page` returns properties only, not body
3. **Fetch body separately**: `API-get-block-children` for content
4. **Traverse conditionally**: Use `has_children` to decide which blocks to expand

### Response Optimization
- **Tool name truncation**: Hard-truncated to 64 characters (MCP spec limit) with collision-safe suffix (Source: src/openapi-mcp-server/mcp/proxy.ts, accessed 2026-05-30)
- **Description prefix**: All tools get `"Notion | "` prefix for disambiguation in multi-server contexts (Source: src/openapi-mcp-server/openapi/parser.ts, accessed 2026-05-30)
- **Tool annotations**: `readOnlyHint: true` for GET, `destructiveHint: true` for write operations
- **No body truncation**: Responses returned in full; caller manages budget via tool selection

---

## Installation & Usage

### Installation

The README documents no global-install step. The server is run through `npx` directly from the
client configuration, published as `@notionhq/notion-mcp-server` with bin name
`notion-mcp-server`.

Before configuring, the README's setup requires creating a Notion internal integration and
connecting the target pages/databases to it — an integration token alone grants no content access.

### Configuration

Two authentication options, both from the README. Option 1 is the one the README marks
recommended. Note the variable is `NOTION_TOKEN` (not `NOTION_API_TOKEN`) and the token prefix
is `ntn_`:

```json
{
  "mcpServers": {
    "notionApi": {
      "command": "npx",
      "args": ["-y", "@notionhq/notion-mcp-server"],
      "env": {
        "NOTION_TOKEN": "ntn_****"
      }
    }
  }
}
```

Option 2 passes raw headers instead, for advanced use (e.g. pinning the API version):

```json
{
  "mcpServers": {
    "notionApi": {
      "command": "npx",
      "args": ["-y", "@notionhq/notion-mcp-server"],
      "env": {
        "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer ntn_****\", \"Notion-Version\": \"2025-09-03\" }"
      }
    }
  }
}
```

### Example Workflow

Tool arguments are the OpenAPI operation's own parameter names, since the parser copies each
`paramObj.name` straight into the tool `inputSchema`.

**Search for a page:**

```text
API-post-search(query="My Project", filter={"value": "page", "property": "object"})
```

**Fetch page properties (not body):**

```text
API-retrieve-a-page(page_id="abc123")
```

**List child blocks (first page):**

```text
API-get-block-children(block_id="abc123", page_size=50)
→ { "object": "list", "results": [...], "has_more": true, "next_cursor": "<opaque>" }
```

**Paginate to next block batch:**

```text
API-get-block-children(block_id="abc123", page_size=50, start_cursor="<opaque>")
```

---

## Relevance to Claude Code Development

### Applications
- **Notion workspace integration**: AI assistants can search, navigate, and read Notion documents as project context
- **Large hierarchy traversal**: Block tree lazy-loading pattern is directly applicable to large documentation systems and code repositories
- **Progressive-disclosure for complex structures**: Metadata-first approach (fetch properties, then body, then nested content) reduces token consumption on large workspaces

### Patterns Worth Adopting
- **Two-phase separation of metadata and body**: `API-retrieve-a-page` (properties only) vs. `API-get-block-children` (body) allows agents to decide whether body fetch is necessary
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
- [scripts/notion-openapi.json — bundled OpenAPI spec; source of every `operationId` and of the `page_size` default/maximum](https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/scripts/notion-openapi.json) (accessed 2026-05-30)
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
