# Research: Notion MCP Server — Large Content Tree Patterns

**Date**: 2026-05-30
**Sources**: makenotion/notion-mcp-server repo (v2.3.1), Notion API reference docs
**Purpose**: Identify patterns adoptable for a section-index + paginated body + token-budget pipeline

---

## 1. Architecture Overview

The `@notionhq/notion-mcp-server` (v2.3.1) is an **OpenAPI-spec-driven proxy**. It does not hand-code tool definitions. Instead:

1. `src/init-server.ts` loads a bundled OpenAPI JSON spec at startup via `fs.readFileSync`.
2. `src/openapi-mcp-server/openapi/parser.ts` (`OpenAPIToMCPConverter`) parses every `operationId` in the spec into an MCP tool definition.
3. `src/openapi-mcp-server/mcp/proxy.ts` (`MCPProxy`) registers those tools with the MCP SDK and executes them by forwarding HTTP calls to `api.notion.com`.

SOURCE: `src/init-server.ts` raw — <https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/src/init-server.ts> (accessed 2026-05-30)
SOURCE: `src/openapi-mcp-server/openapi/parser.ts` raw — <https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/src/openapi-mcp-server/openapi/parser.ts> (accessed 2026-05-30)
SOURCE: `src/openapi-mcp-server/mcp/proxy.ts` raw — <https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/src/openapi-mcp-server/mcp/proxy.ts> (accessed 2026-05-30)

> **Note**: Notion is deprecating this local MCP server in favor of a remote MCP (OAuth-based) that is described as "designed with optimized token consumption in mind." The remote MCP is closed-source. This report covers the open-source local server.
> SOURCE: README — <https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/README.md> (accessed 2026-05-30)

---

## 2. MCP Tools Exposed (22 tools, v2.0+)

Tools are derived automatically from OpenAPI `operationId` values. The README documents the following set (v2.0, confirmed from README accessed 2026-05-30):

**Search / discovery**

| Tool name | HTTP | Description |
|---|---|---|
| `search` | POST `/v1/search` | Search by title across pages and databases |

**Page operations**

| Tool name | HTTP | Description |
|---|---|---|
| `retrieve-a-page` | GET `/v1/pages/{page_id}` | Retrieve a page's properties |
| `create-a-page` | POST `/v1/pages` | Create a new page |
| `update-page-properties` | PATCH `/v1/pages/{page_id}` | Update page properties |
| `move-page` | PATCH `/v1/pages/{page_id}` | Move a page to a different parent |
| `retrieve-a-page-property` | GET `/v1/pages/{page_id}/properties/{property_id}` | Get a single property item |

**Block operations**

| Tool name | HTTP | Description |
|---|---|---|
| `retrieve-a-block` | GET `/v1/blocks/{block_id}` | Retrieve a single block |
| `retrieve-block-children` | GET `/v1/blocks/{block_id}/children` | List child blocks (paginated) |
| `append-block-children` | PATCH `/v1/blocks/{block_id}/children` | Append new blocks |
| `delete-a-block` | DELETE `/v1/blocks/{block_id}` | Delete a block |
| `update-a-block` | PATCH `/v1/blocks/{block_id}` | Update a block |

**Comment operations**

| Tool name | HTTP | Description |
|---|---|---|
| `list-comments` | GET `/v1/comments` | List comments on a block or page |
| `create-a-comment` | POST `/v1/comments` | Create a comment |

**User operations**

| Tool name | HTTP | Description |
|---|---|---|
| `list-all-users` | GET `/v1/users` | List all workspace users |
| `retrieve-a-user` | GET `/v1/users/{user_id}` | Get a single user |
| `retrieve-your-token-s-bot-user` | GET `/v1/users/me` | Get the integration bot user |

**Data source (database) operations**

| Tool name | HTTP | Description |
|---|---|---|
| `retrieve-a-database` | GET `/v1/databases/{database_id}` | Get database metadata + data source IDs |
| `query-data-source` | POST | Query a database with filters and sorts |
| `retrieve-a-data-source` | GET | Get schema and properties for a data source |
| `update-a-data-source` | PATCH | Update data source properties |
| `create-a-data-source` | POST | Create a new data source |
| `list-data-source-templates` | GET | List templates in a data source |

Total tools: **22** (as of v2.0.0).

SOURCE: README tool list — <https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/README.md> (accessed 2026-05-30)
SOURCE: Notion API intro endpoint table — <https://developers.notion.com/reference/intro> (accessed 2026-05-30)

---

## 3. Pagination Mechanism

The local MCP server applies **no pagination logic itself** — it passes `page_size` and `start_cursor` directly to the Notion REST API, which handles pagination. The agent calling the MCP tool is expected to manage cursor iteration.

### Notion API pagination fields (current as of 2026-05-30)

SOURCE: <https://developers.notion.com/reference/intro> (accessed 2026-05-30)
SOURCE: <https://developers.notion.com/reference/pagination> (deprecated page, still accurate, accessed 2026-05-30)

**Request parameters** (passed as tool arguments):

| Parameter | Type | Default | Maximum |
|---|---|---|---|
| `start_cursor` | string (opaque) | `undefined` (= start of list) | N/A |
| `page_size` | number | `100` | `100` |

**Response fields** (returned by every paginated tool):

| Field | Type | Description |
|---|---|---|
| `has_more` | boolean | `true` if more results exist after this page |
| `next_cursor` | string | Opaque cursor; only present when `has_more` is `true` |
| `object` | `"list"` | Constant |
| `results` | array | The partial list of objects |
| `type` | string enum | Type of objects in `results` (e.g., `"block"`, `"page"`, `"user"`) |

Mechanism: **cursor-based** (not offset/limit). The cursor is opaque — treat it as a token, not a number. The `page_size` cap is hard at 100; there is no way to request more per call.

**Block children endpoint** (`retrieve-block-children`, GET `/v1/blocks/{block_id}/children`):

```javascript
// TypeScript SDK example from Notion docs
const response = await notion.blocks.children.list({
  block_id: "c02fc1d3-db8b-45c5-a222-27595b15aea7",
  start_cursor: undefined,
  page_size: 50
})
// Response shape:
{
  "object": "list",
  "next_cursor": "<string>",
  "has_more": true,
  "results": [{ "object": "block", "id": "..." }]
}
```

SOURCE: <https://developers.notion.com/reference/get-block-children> (accessed 2026-05-30)

**Search endpoint** (`search`, POST `/v1/search`):

```javascript
// Response
{
  "next_cursor": "<string>",
  "has_more": true,
  "results": [{ "object": "page", "id": "...", ... }]
}
```

SOURCE: <https://developers.notion.com/reference/post-search> (accessed 2026-05-30)

---

## 4. Response-Size Bounding for LLMs

The local MCP server has **very minimal** built-in response-size protection. Findings from the source:

### 4a. Tool name truncation (proxy.ts)

Tool names are hard-truncated to 64 characters (MCP spec limit):

```typescript
// src/openapi-mcp-server/mcp/proxy.ts
private truncateToolName(name: string): string {
  if (name.length <= 64) {
    return name;
  }
  return name.slice(0, 64);
}
```

The parser also has a collision-safe variant: `name.slice(0, 64 - 5)` + 4-digit counter suffix.

SOURCE: `src/openapi-mcp-server/mcp/proxy.ts` (accessed 2026-05-30), confirmed by `src/openapi-mcp-server/openapi/parser.ts`

### 4b. Description prefix (parser.ts)

Tool descriptions get a `"Notion | "` prefix to help the LLM distinguish Notion tools from other servers:

```typescript
// src/openapi-mcp-server/openapi/parser.ts
private getDescription(description: string): string {
  if (this.openApiSpec.info.title === 'Notion API') {
    return "Notion | " + description
  }
  return description
}
```

No description length limit or truncation is applied.

SOURCE: `src/openapi-mcp-server/openapi/parser.ts` (accessed 2026-05-30)

### 4c. Tool annotations for read/write hints

GET operations receive `{ readOnlyHint: true }`; all others receive `{ destructiveHint: true }`. This helps compliant MCP clients filter or order tools in their tool-selection UI:

```typescript
// src/openapi-mcp-server/mcp/proxy.ts
annotations: {
  title: this.operationIdToTitle(method.name),
  ...(isReadOnly
    ? { readOnlyHint: true }
    : { destructiveHint: true }),
}
```

SOURCE: `src/openapi-mcp-server/mcp/proxy.ts` (accessed 2026-05-30)

### 4d. No server-side body truncation

The response body is returned as raw JSON: `JSON.stringify(response.data)`. There is no token-budget gate, no body summarizer, no truncation. Any large page body passes through in full.

SOURCE: `src/openapi-mcp-server/mcp/proxy.ts`, `CallToolRequestSchema` handler (accessed 2026-05-30)

### 4e. Remote MCP (unreachable source)

Notion's newer remote MCP server claims "optimized token consumption" and Markdown-mode editing, but its source is not public. No implementation details are citable.

SOURCE: README note section — <https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/README.md> (accessed 2026-05-30)

---

## 5. Progressive-Disclosure Patterns

### 5a. Search-first-then-fetch (agent-imposed)

The server does not enforce a search-first pattern in code, but the README example demonstrates and implicitly teaches it:

> "AI will correctly plan two API calls, `v1/search` and `v1/comments`, to achieve the task"

The agent is expected to:

1. Call `search` with a query string → receives lightweight result objects with `id`, `url`, `title`, `last_edited_time`
2. Use the `id` from results to call `retrieve-a-page` or `retrieve-block-children` for full content

Search results contain **preview metadata only** (id, title, timestamps, parent) — not page body content. This is a natural progressive-disclosure gate.

SOURCE: README Examples section — <https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/README.md> (accessed 2026-05-30)
SOURCE: Search response shape — <https://developers.notion.com/reference/post-search> (accessed 2026-05-30)

### 5b. Block tree is lazy by design — one level at a time

Notion's block model has a key structural property: **`has_children: boolean`** on each block. The MCP server reflects this faithfully.

A page's block tree is NOT returned in a single call. The agent receives top-level blocks from `retrieve-block-children(page_id)`. Each block with `has_children: true` requires an additional `retrieve-block-children(block_id)` call. This means:

- The agent sees the outline (headings, top-level structure) from the first call.
- Nested content (e.g., content inside toggles, bulleted lists with children, synced blocks) is only fetched on demand.
- Depth traversal is agent-controlled, not automatic.

Block types that carry children:

```typescript
// From proxy.test.ts — block types used in tests:
{ object: 'block', type: 'paragraph' }
{ object: 'block', type: 'heading_1' }
{ object: 'block', type: 'heading_1', heading_1: { rich_text: [...] } }
```

SOURCE: `src/openapi-mcp-server/mcp/__tests__/proxy.test.ts` (accessed 2026-05-30)
SOURCE: <https://developers.notion.com/reference/block> (accessed 2026-05-30)

### 5c. Database metadata → data source ID indirection

`retrieve-a-database` returns metadata **plus a list of data source IDs**. The agent must then call `retrieve-a-data-source(data_source_id)` for schema/properties. This two-step pattern avoids embedding all schema data in the database metadata response.

SOURCE: README migration table — <https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/README.md> (accessed 2026-05-30)

### 5d. Page properties vs. page body — separate tools

`retrieve-a-page` returns **properties only** (title, status, dates, etc.). The page body (block content) is a separate tool call: `retrieve-block-children(page_id)`. This is a fundamental Notion API design that the MCP server inherits.

SOURCE: Notion API intro — <https://developers.notion.com/reference/intro> (accessed 2026-05-30)
SOURCE: Working with page content — <https://developers.notion.com/docs/working-with-page-content> (accessed 2026-05-30)

### 5e. Search filter by object type

`search` accepts a `filter.value` of `"page"` or `"database"` to narrow result type. Sorting by `last_edited_time` / `created_time` is also available. This lets agents narrow results before fetching.

SOURCE: <https://developers.notion.com/reference/post-search> (accessed 2026-05-30)

---

## 6. Large Hierarchy Representation

Notion represents a page's content as a **flat list of sibling blocks**, each with a `type` field and an optional `has_children` flag. Headings (`heading_1`, `heading_2`, `heading_3`) are block types like any other — not special metadata. There is no table-of-contents endpoint.

To build an outline/TOC of a page:

1. Call `retrieve-block-children(page_id)` with `page_size=100`.
2. Filter `results` for blocks with `type` in `["heading_1","heading_2","heading_3"]`.
3. Extract the `rich_text[].plain_text` field from each heading block.
4. If `has_more=true`, use `next_cursor` → `start_cursor` to fetch the next page.

This pattern was used in the README example planning context: "comment on page 'Getting started'" triggers `v1/search` to find the page, then content tool calls follow.

Block types relevant to hierarchy/outline navigation:

```text
heading_1     — top-level section marker
heading_2     — subsection
heading_3     — sub-subsection
paragraph     — body text
bulleted_list_item / numbered_list_item  — lists
toggle        — collapsible; body only visible on has_children fetch
child_page    — nested page reference (ID only, body requires separate fetch)
child_database — nested database reference
```

Each block object always carries: `object`, `id`, `type`, `{type}` (type-specific data), `has_children`, `created_time`, `last_edited_time`.

SOURCE: <https://developers.notion.com/reference/block> (accessed 2026-05-30)
SOURCE: <https://developers.notion.com/docs/working-with-page-content> (accessed 2026-05-30)

---

## 7. Techniques Adoptable for a Section-Index + Paginated Body + Token-Budget Pipeline

### Technique 1 — Two-phase metadata-then-body separation

Notion separates `retrieve-a-page` (properties only) from `retrieve-block-children` (body). The agent decides whether it needs the body at all.

**Adoption**: For your "view" pipeline, return item metadata (title, status, section names, sizes) in phase 1. Only resolve and assemble section body in phase 2 when the caller requests it. Your existing `_build_over_budget_view` already follows this pattern — the Notion model validates it as the right split.

### Technique 2 — Cursor-based pagination exposed directly as tool parameters

Notion passes `start_cursor`/`page_size` as first-class tool parameters. The agent controls the window. `has_more`/`next_cursor` in the response tell the agent whether to continue.

**Adoption**: In your paginated body tool, expose `offset`/`limit` (or `cursor`/`page_size`) as explicit parameters with documented defaults. Return `has_more: bool` and `next_cursor` in every response so the caller can iterate without guessing. Avoid hiding pagination behind silent truncation.

### Technique 3 — `has_children` flag enables selective depth traversal without pre-fetching

Every Notion block carries `has_children: bool`. The agent sees the full sibling list first, then decides which subtrees to expand based on relevance.

**Adoption**: When returning a section index, include a `has_subsections: bool` (or `subsection_count: int`) per section. The caller can request only the sections it needs, rather than receiving the entire assembled body. Your `_build_over_budget_view` already emits counts — extend it with a flag indicating whether subsections exist.

### Technique 4 — Search-first scoping before full fetch

Notion's example workflow uses `search` to obtain an ID before calling content tools. Search results are lightweight — id, title, timestamps only. This avoids fetching large content trees for the wrong page.

**Adoption**: For your "section index → body" pipeline, add a search/filter phase that returns section headers and IDs only (your current `sections_index`). The caller selects a section ID and requests the body for that section specifically. This is exactly the `selector` mechanism in your backlog `backlog_view` — the Notion model confirms the pattern is sound.

### Technique 5 — Tool annotations (readOnlyHint / destructiveHint) to reduce LLM confusion

GET tools receive `readOnlyHint: true`; write tools receive `destructiveHint: true`. This allows MCP clients and LLMs to filter safe exploration from state-changing operations, reducing accidental writes during read-only browsing.

**Adoption**: Annotate your MCP view tool with `readOnlyHint: true` and any write/update tool with `destructiveHint: true`. This is a one-line addition per tool registration and requires no schema changes.

### Technique 6 — Description prefix for tool disambiguation in multi-server contexts

All Notion tools get `"Notion | "` prepended to their description. This is a deliberate pattern to help LLMs route tool selection when multiple MCP servers are active.

**Adoption**: Prefix your backlog view tools consistently (e.g., `"Backlog | "` or your plugin name) so tool descriptions are unambiguous in a multi-server Claude session. Costs zero tokens in tool calls; pays dividends in routing accuracy.

---

## 8. What the Notion MCP Server Does NOT Do (notable gaps)

These are patterns the remote Notion MCP likely implements but the open-source server does not:

- **No token-budget gate**: Responses are returned in full regardless of size.
- **No automatic pagination chaining**: The agent must loop manually using `has_more`/`next_cursor`.
- **No outline/TOC endpoint**: The agent must filter heading blocks itself from the block list.
- **No Markdown rendering**: Raw JSON block objects are returned (the remote MCP claims Markdown output).
- **No depth-limited subtree fetch**: Each level of nesting requires a separate tool call.
- **No summary/preview mode**: Full block object JSON is always returned; no short-form representation.

---

## Sources Summary

| Source | URL | Accessed |
|---|---|---|
| Repo README (raw) | <https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/README.md> | 2026-05-30 |
| `src/init-server.ts` | <https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/src/init-server.ts> | 2026-05-30 |
| `src/openapi-mcp-server/openapi/parser.ts` | <https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/src/openapi-mcp-server/openapi/parser.ts> | 2026-05-30 |
| `src/openapi-mcp-server/mcp/proxy.ts` | <https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/src/openapi-mcp-server/mcp/proxy.ts> | 2026-05-30 |
| `src/openapi-mcp-server/mcp/__tests__/proxy.test.ts` | <https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/src/openapi-mcp-server/mcp/__tests__/proxy.test.ts> | 2026-05-30 |
| Notion API intro + pagination | <https://developers.notion.com/reference/intro> | 2026-05-30 |
| Notion API block children | <https://developers.notion.com/reference/get-block-children> | 2026-05-30 |
| Notion API block types | <https://developers.notion.com/reference/block> | 2026-05-30 |
| Notion API search | <https://developers.notion.com/reference/post-search> | 2026-05-30 |
| Working with page content | <https://developers.notion.com/docs/working-with-page-content> | 2026-05-30 |
| Notion MCP docs (remote) | <https://developers.notion.com/docs/mcp> | 2026-05-30 |

### Unreachable sources

- `https://api.github.com/repos/makenotion/notion-mcp-server/contents/src` — HTTP 403 (rate-limited without token)
- `openapi.yaml` at several candidate paths — not present in repo root or `src/` (bundled at build time into the binary, not committed as a standalone file)
- `src/openapi-mcp-server/openapi/schema-converter.ts`, `operation-parser.ts` — HTTP 404 (these files do not exist; the single `parser.ts` handles all conversion)
- Remote Notion MCP source — closed-source, not publicly accessible
