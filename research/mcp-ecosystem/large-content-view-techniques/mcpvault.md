# Research: mcpvault (bitbonsai) — MCP Content Presentation Patterns

**Date**: 2026-05-30
**Sources**: All claims cite exact file paths or URLs. No training-data recall used.

---

## 1. What mcpvault IS

mcpvault (`@bitbonsai/mcpvault` v0.11.2) is a lightweight MCP server that gives any MCP-compatible AI assistant safe, read/write access to an Obsidian vault directory. It is **not** a content chunking, RAG, or token-budgeting platform — it is a file-system bridge with relevance ranking on search.

SOURCE: `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/README.md` — "A universal AI bridge for Obsidian vaults using the Model Context Protocol (MCP) standard."
SOURCE: `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/package.json` — name `@bitbonsai/mcpvault`, version `0.11.2`.

---

## 2. MCP Tools Exposed (14 tools)

All tool definitions are in `src/createServer.ts` (registered via `ListToolsRequestSchema` handler).

SOURCE: `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/createServer.ts`

### File operations

| Tool | Key parameters | Returns |
|---|---|---|
| `read_note` | `path` (required), `prettyPrint` | Full frontmatter + content of one note |
| `write_note` | `path`, `content`, `frontmatter?`, `mode` (`overwrite`/`append`/`prepend`) | Success result |
| `patch_note` | `path`, `oldString`, `newString`, `replaceAll?` | Success + matchCount |
| `delete_note` | `path`, `confirmPath` (must equal `path`), `trashMode` (`none`/`local`/`system`) | Success result |
| `move_note` | `oldPath`, `newPath`, `overwrite?` | Success result |
| `move_file` | `oldPath`, `newPath`, `confirmOldPath`, `confirmNewPath`, `overwrite?` | Success result |

### Directory / listing operations

| Tool | Key parameters | Returns |
|---|---|---|
| `list_directory` | `path` (default `/`), `prettyPrint` | `{ dirs: string[], files: string[] }` — one level only, no pagination |

### Batch operations

| Tool | Key parameters | Returns |
|---|---|---|
| `read_multiple_notes` | `paths` (array, **max 10**), `includeContent?`, `includeFrontmatter?`, `prettyPrint` | `{ ok: [...], err: [...] }` — minified field names |

### Search

| Tool | Key parameters | Returns |
|---|---|---|
| `search_notes` | `query` (required), `limit` (default 5, **max 20**), `searchContent` (default true), `searchFrontmatter` (default false), `caseSensitive` (default false), `prettyPrint` | Array of minified result objects |

Search result fields (minified):
- `p` = path, `t` = title, `ex` = excerpt (±21 chars context window), `mc` = match count, `ln` = line number, `uri` = Obsidian deep link

### Metadata tools (no body read)

| Tool | Key parameters | Returns |
|---|---|---|
| `get_notes_info` | `paths` (array), `prettyPrint` | `NoteInfo[]`: `{ path, size, modified, hasFrontmatter, obsidianUri? }` — **reads first 100 chars only** to detect frontmatter |
| `get_frontmatter` | `path`, `prettyPrint` | Frontmatter only, no content |
| `get_vault_stats` | `recentCount` (default 5, **max 20**), `prettyPrint` | `{ notes, folders, size, recent[] }` — no content, scan only |
| `manage_tags` | `path`, `operation` (`add`/`remove`/`list`), `tags?` | Tag result |
| `list_all_tags` | `prettyPrint` | All tags vault-wide with occurrence counts |
| `update_frontmatter` | `path`, `frontmatter`, `merge?` | Success result |

SOURCE: `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/createServer.ts` — full `ListToolsRequestSchema` handler.
SOURCE: `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/types.ts` — `NoteInfo`, `SearchResult`, `VaultStats` interfaces.

---

## 3. Content Indexing / Cataloguing / Manifest Mechanism

mcpvault has **no pre-built index, catalog, or manifest**. There is no index file, no SQLite, no vector store. Discovery works by:

1. **`list_directory`** — single-level directory listing (non-recursive). Returns `dirs[]` and `files[]` at a given path. Agent must recurse manually.
2. **`get_vault_stats`** — returns aggregate counts (`totalNotes`, `totalFolders`, `totalSize`) plus a sorted list of `recentlyModified` files (controlled by `recentCount`, max 20). Useful for understanding scope before operations.
3. **`list_all_tags`** — full-vault tag scan returning `{ tag, count }[]` sorted by frequency. Provides a vocabulary index but not a note index.
4. **Search-based discovery** — `search_notes` scans all `.md` files recursively on each call (no cached index). It is the primary "find a note" primitive.

SOURCE: `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/filesystem.ts` — `listDirectory` does one `readdir` call; `getVaultStats` scans recursively with `stat` per file; `listAllTags` does a full-vault regex scan.
SOURCE: `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/createServer.ts` — `list_directory` handler returns `{ dirs: listing.directories, files: listing.files }`.

---

## 4. Pagination / Size-Bounding Mechanism

mcpvault has **no cursor-based pagination, no offset/page parameter, and no token budget**. The bounding mechanisms that exist are:

| Mechanism | Where | Hard cap |
|---|---|---|
| `search_notes` result count | `limit` param (default 5) | **Max 20** — enforced by `const maxLimit = Math.min(limit, 20)` in `SearchService.search()` |
| `read_multiple_notes` batch size | `paths` array | **Max 10 files** — stated in README and tool description |
| `get_vault_stats` recent files | `recentCount` param (default 5) | **Max 20** — enforced by `Math.min(trimmedArgs.recentCount \|\| 5, 20)` in the handler |
| `list_directory` depth | Always single-level | No pagination — entire directory returned in one response |
| `read_note` / `get_frontmatter` | Single file per call | No truncation — entire file content is returned |

There is **no cursor, no `nextPage`, no `offset`, no token budget, no content truncation** on any tool. `read_note` returns the full file regardless of size.

SOURCE: `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/search.ts` — line `const maxLimit = Math.min(limit, 20);`
SOURCE: `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/createServer.ts` — `const recentCount = Math.min(trimmedArgs.recentCount || 5, 20);`
SOURCE: README — "`read_multiple_notes` Read multiple notes in a batch (maximum 10 files)"

---

## 5. Progressive-Disclosure Patterns

mcpvault does implement a disciplined **search/metadata-first, full-read-on-demand** pattern — though it is a design choice, not an explicit pagination system.

### Pattern A: Shallow listing → targeted reads

`list_directory` → navigate to folder → `read_note` by path. The agent only loads content for notes it explicitly selects.

### Pattern B: Metadata gate before content fetch

`get_notes_info` takes an array of paths and returns `{ path, size, modified, hasFrontmatter }` **without reading the full body** — it reads only the first 100 characters to detect frontmatter. The agent can check `size` before deciding whether to call `read_note`.

```typescript
// From src/filesystem.ts — getNotesInfo reads first 100 chars only:
const firstChunk = file.slice(0, 100);
const hasFrontmatter = firstChunk.startsWith('---\n');
```

SOURCE: `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/filesystem.ts` — `getNotesInfo` implementation.

### Pattern C: Frontmatter-only fetch

`get_frontmatter` reads the full note but returns only the parsed frontmatter object, discarding body content. Agents use this to inspect note metadata (title, tags, created date) without paying the cost of body content in the response.

### Pattern D: Search → excerpt → selective full reads

`search_notes` returns only `{ p, t, ex, mc, ln, uri }` — a compact manifest with a ±21 character excerpt window per match. The agent reads this ranked list, identifies which notes are relevant, then calls `read_note` on only the ones it wants. Full content is never sent speculatively.

Excerpt extraction (from `src/search.ts`):
```typescript
const excerptStart = Math.max(0, firstIndex - 21);
const excerptEnd = Math.min(searchableText.length, firstIndex + firstTerm.length + 21);
excerpt = searchableText.slice(excerptStart, excerptEnd).trim();
if (excerptStart > 0) excerpt = '...' + excerpt;
if (excerptEnd < searchableText.length) excerpt = excerpt + '...';
```

SOURCE: `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/search.ts`

### Pattern E: Minified response field names (token compression)

All responses use abbreviated JSON field names when `prettyPrint: false` (the default). Example: `p` instead of `path`, `t` instead of `title`, `ex` instead of `excerpt`, `ok`/`err` instead of `successful`/`failed`. README claims 40-60% smaller responses.

SOURCE: `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/types.ts` — `SearchResult` interface comments: `p: string; // path`, `t: string; // title`, etc.
SOURCE: README — "Token-optimized responses: 40-60% smaller responses with minified field names and compact JSON (v0.6.3+)"

---

## 6. Token/Size Budgeting

**mcpvault has no token budget gate.** It does not measure response size, does not count tokens, and does not truncate `read_note` output. The only size controls are:

- Hard caps on result counts (search ≤ 20, batch ≤ 10, recent ≤ 20)
- `get_notes_info` exposes `size` (bytes) so the **caller** can decide whether to proceed to a full read
- `prettyPrint: false` (default) reduces JSON whitespace

The philosophy is: return the exact data requested, compress the JSON field names, let the caller impose the budget by choosing which tools to call.

---

## 7. Relevance Ranking: BM25

`search_notes` implements full Okapi BM25 via `SearchService.rerank()` in `src/search.ts`:

```typescript
// k1=1.2, b=0.75 — standard BM25 parameters
const idf = Math.log(1 + (docCount - df + 0.5) / (df + 0.5));
score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * c.docLength / avgdl));
```

Multi-word queries add the full query string as an additional scoring term alongside individual terms (`scoringTerms = terms.length > 1 ? [...terms, searchQuery] : terms`). Files are read in parallel batches of 5 (`BATCH_SIZE = 5`).

SOURCE: `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/search.ts` — `rerank()` private method.

---

## 8. Security / Path Filtering

`PathFilter` (in `src/pathfilter.ts`) enforces:
- **Ignored patterns**: `.obsidian`, `.obsidian/**`, `.git`, `.git/**`, `node_modules`, `node_modules/**`, `.DS_Store`, and dot files
- **Extension whitelist** (configurable): `.md`, `.markdown`, `.txt`, `.base`, `.canvas` by default
- **Symlink containment**: `listDirectory` resolves symlinks and rejects targets outside the vault root

SOURCE: `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/pathfilter.ts`

---

## 9. Techniques Adoptable for a "Section Index + Paginated Body + Token-Budget Gate" Pipeline

mcpvault provides **partial but genuine patterns**. Its core philosophy (metadata first, full content on demand, result count caps) is directly applicable. What it does NOT provide: cursor pagination, token counting, section-level addressing, or lazy-loading of individual note sections.

### Technique 1: Metadata gate before content assembly

mcpvault's `get_notes_info` pattern: fetch `{ path, size, modified, hasFrontmatter }` cheaply (first 100 chars) and let the caller decide whether the size warrants a full read.

**Adoption**: Add a `view_index` mode to your view tool that returns `{ section_slug, byte_count, line_count, heading_text }[]` per section without assembling the body. The caller checks sizes and requests only the sections it needs by slug.

### Technique 2: Search → ranked excerpt → selective fetch

mcpvault returns a ±21-char excerpt per search match as the only content in the search response. The agent never gets body content until it calls `read_note` with a specific path.

**Adoption**: In your pipeline, a `search_sections` tool could return `{ section_slug, heading, excerpt, match_count, score }[]` capped at N results — no assembled body. The agent identifies which sections to expand and calls `view_section(slug=...)` for only those.

### Technique 3: Hard result caps with explicit defaults

mcpvault enforces `Math.min(limit, 20)` and `Math.min(recentCount, 20)` at the server layer — the agent cannot accidentally request unlimited data. Defaults are conservative (5).

**Adoption**: Your `view` tool's `section` parameter should default to returning 1-3 sections max when no explicit section is named, with a hard cap on total assembled bytes (e.g., 8,000 chars). If the full body would exceed the cap, return the section index and ask the caller to pick.

### Technique 4: Abbreviated field names in responses

mcpvault's minified field names (`p`, `t`, `ex`, `mc`) save 40-60% response size vs verbose names with no information loss. This is especially significant when returning lists of many items.

**Adoption**: In your section-index response, use short field names: `s` (slug), `h` (heading), `b` (byte_count), `l` (line_count). Document the mapping in the tool description.

### Technique 5: BM25 scoring to prioritize section delivery

mcpvault ranks all matching notes by BM25 before applying the `limit` cap. The agent receives the most relevant K results, not the first K in filesystem order.

**Adoption**: When a query accompanies a `view` call, rank sections by BM25 score rather than document order before applying the token budget. Sections that match the query closely get assembled first; low-scoring sections are deferred to on-demand fetch.

---

## 10. Relevance Assessment: What mcpvault Lacks for the Target Pipeline

| Required capability | mcpvault status |
|---|---|
| Cursor/offset pagination | ABSENT — no pagination primitives at all |
| Token budget measurement | ABSENT — no token counting, no truncation gate |
| Section-level addressing | ABSENT — `read_note` returns the full file; no heading-based subsetting |
| Progressive disclosure of large single files | ABSENT — one file = one atomic read |
| On-demand section fetch by ID | ABSENT — no section ID concept |

**Plain statement**: mcpvault is a thin MCP file-system bridge. Its relevance to the target pipeline is limited to the discipline of its API surface (metadata-first tools, search-before-read pattern, result count caps, minified response fields). The actual pagination, token budgeting, and section-index mechanisms must be built from scratch. mcpvault does not demonstrate them.

---

## Sources

| Artifact | URL |
|---|---|
| README | `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/README.md` |
| GitHub homepage | `https://github.com/bitbonsai/mcpvault` |
| `package.json` | `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/package.json` |
| `src/index.ts` | `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/index.ts` |
| `src/createServer.ts` | `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/createServer.ts` |
| `src/filesystem.ts` | `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/filesystem.ts` |
| `src/search.ts` | `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/search.ts` |
| `src/types.ts` | `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/types.ts` |
| `src/pathfilter.ts` | `https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/pathfilter.ts` |

All URLs verified reachable 2026-05-30. `src/tools.ts` returned HTTP 404 — tool definitions are in `src/createServer.ts`.
