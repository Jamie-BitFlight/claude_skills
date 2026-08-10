---
name: mcpvault
research_date: 2026-05-30
source_url: https://github.com/bitbonsai/mcpvault
github_repository: https://github.com/bitbonsai/mcpvault
version_at_research: v0.11.2
license: MIT
freshness_tracking:
  last_verified: 2026-05-30
  version_at_verification: v0.11.2
  next_review: 2026-08-30
  confidence_map: "Overview: high, Problem Addressed: high, Key Features: high, Technical Architecture: high, Installation & Usage: high, Relevance to Claude Code: medium"
---

# mcpvault

## Overview

mcpvault (`@bitbonsai/mcpvault` v0.11.2) is a lightweight MCP server that gives AI assistants safe, read/write access to Obsidian vault directories. It exposes 14 specialized tools for file operations, searching, metadata inspection, and batch operations with built-in relevance ranking via BM25 and progressive-disclosure patterns that prioritize metadata and excerpts before full content reads. (Accessed: https://raw.githubusercontent.com/bitbonsai/mcpvault/main/README.md and https://raw.githubusercontent.com/bitbonsai/mcpvault/main/package.json, 2026-05-30)

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI assistants cannot safely access and modify Obsidian vaults | mcpvault exposes 14 MCP tools for authenticated file operations with path filtering and trash mode support (accessed 2026-05-30) |
| Large note bodies exceed AI token budgets | Progressive-disclosure pattern: search returns excerpts only, metadata tools fetch sizes cheaply, full content read on demand (accessed 2026-05-30) |
| Vaults with hundreds of notes lack efficient discovery | Search-first design: BM25-ranked `search_notes` finds relevant content before any body read; `list_all_tags` provides vocabulary index (accessed 2026-05-30) |
| AI cannot assess note importance without reading full content | `get_notes_info` reads first 100 chars to detect frontmatter and expose file size; caller decides whether to fetch full body (accessed 2026-05-30) |
| Context window easily saturated by undifferentiated batch reads | Hard caps: `read_multiple_notes` max 10 files, `search_notes` max 20 results, `get_vault_stats` max 20 recent files (accessed 2026-05-30) |

---

## Key Features

### File Operations
- **read_note**: Read full note with optional pretty-print, frontmatter parsing, markdown content
- **write_note**: Create or overwrite note with frontmatter + body; append or prepend modes
- **patch_note**: Surgical string replacement with oldString/newString and replaceAll flag
- **delete_note**: Permanent delete with optional trash mode (local / system / none)
- **move_note** / **move_file**: Rename or relocate with optional overwrite
- **read_multiple_notes**: Batch read up to 10 files with per-file success/error tracking

### Search & Discovery
- **search_notes**: BM25-ranked search across all `.md` files with query, limit (default 5, max 20), context windows, and optional frontmatter/content scoping
- **list_directory**: Single-level directory listing (non-recursive) returning dirs and files
- **list_all_tags**: Vault-wide tag catalog with occurrence counts; useful for understanding vault vocabulary without reading notes

### Metadata & Inspection
- **get_notes_info**: Cheap metadata fetch (first 100 chars) returning path, size, modified date, frontmatter presence without reading body
- **get_frontmatter**: Extract frontmatter only, discarding body content
- **get_vault_stats**: Aggregate counts (total notes, folders, size) plus list of recently modified files (configurable, default 5, max 20)
- **update_frontmatter** / **manage_tags**: Atomic frontmatter key updates and tag add/remove/list operations

### Response Optimization
- **Minified field names by default**: `p` (path), `t` (title), `ex` (excerpt), `mc` (match count) reduce response size by 40-60% vs verbose names
- **prettyPrint flag**: Opt-in full field names and indentation for debugging
- **Search excerpts**: ±21 character context windows per match, never full note body in search results

---

## Technical Architecture

mcpvault exposes all 14 tools via the MCP protocol. Tools are registered in `src/createServer.ts` via `ListToolsRequestSchema` handler. The architecture follows a progressive-disclosure design where each tool class serves a specific role in the request/response lifecycle.

### Discovery & Indexing Pattern
- **No persistent index**: Tools scan filesystem on-demand using `readdir`, `stat`, and file reads
- **`list_directory`**: Single `readdir()` call per path, non-recursive (Source: src/filesystem.ts, accessed 2026-05-30)
- **`get_vault_stats`**: Full vault recursive scan counting notes, folders, sizes; recent files list maintained via `stat` on all files
- **`list_all_tags`**: Vault-wide regex scan of all `.md` files for `#tag` and YAML frontmatter `tags:` arrays
- **`search_notes`**: Async batched full-vault file reads (batch size 5) with sequential term matching and BM25 reranking (Source: src/search.ts, accessed 2026-05-30)

### Search Scoring: Okapi BM25
- Implements full BM25 with standard parameters: k1=1.2, b=0.75
- Score formula: `idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * docLength / avgDocLength))`
- Multi-word queries score both individual terms and full query string as single term
- Files read in parallel batches of 5 for throughput

### Pagination & Size Bounding
- **Hard caps, no cursors**: `search_notes` ≤20 results, `read_multiple_notes` ≤10 files, `get_vault_stats` ≤20 recent
- **`get_notes_info` gate**: Reads first 100 characters only to detect frontmatter presence; caller inspects `size` field before deciding to fetch full body (Source: src/filesystem.ts, accessed 2026-05-30)
- **Minified responses**: Field abbreviation (p, t, ex, mc, etc.) reduces JSON overhead by 40-60%; full names available via `prettyPrint: true`
- **No token budget measurement**: Caller imposes limits by choosing which tools to call and how many results to request

### Security & Path Filtering
- `src/pathfilter.ts` enforces:
  - **Ignored patterns**: `.obsidian`, `.obsidian/**`, `.git`, `node_modules`, `.DS_Store`, dot files
  - **Extension whitelist**: `.md`, `.markdown`, `.txt`, `.base`, `.canvas` (configurable)
  - **Symlink containment**: Resolves and rejects symlink targets outside vault root

---

## Installation & Usage

### Installation

mcpvault is distributed as an npm package:

```bash
npm install -g @bitbonsai/mcpvault
```

### Configuration

Configure via MCP protocol in IDE or agent `.mcp.json`:

```json
{
  "mcpServers": {
    "mcpvault": {
      "command": "mcpvault",
      "args": ["/path/to/vault"]
    }
  }
}
```

### Example Tool Calls

**Search for notes by query:**
```bash
search_notes(query="architecture", limit=5, searchContent=true)
# Returns: [{ p: "design.md", t: "Design", ex: "...architecture...system...", mc: 3, ln: 12 }]
```

**Read a specific note:**
```bash
read_note(path="design.md")
# Returns: full frontmatter + markdown body
```

**Inspect before full read:**
```bash
get_notes_info(paths=["design.md", "api.md"], prettyPrint=false)
# Returns: [{ path: "design.md", size: 8542, modified: "2026-05-30T10:00:00Z", hasFrontmatter: true }]
```

**Extract metadata only:**
```bash
get_frontmatter(path="design.md")
# Returns: parsed YAML object
```

---

## Relevance to Claude Code Development

### Applications
- **Obsidian vault as AI memory**: AI assistants can directly read, search, and update Obsidian notes as a persistent knowledge base without manual copy-paste
- **Knowledge base integration**: Progressive-disclosure pattern (search excerpts → metadata inspection → on-demand full reads) is directly applicable to large documentation systems in Claude Code
- **Token-efficient large-content access**: BM25 ranking, minified responses, and hard result caps provide tested patterns for managing context within fixed token budgets

### Patterns Worth Adopting
- **Metadata-first gate**: Expose `size` and structural info cheaply before assembling full bodies; let the caller decide whether to proceed
- **Search result caps with defaults**: Hard maximum (≤20) with conservative default (5) prevents accidental token budget overruns
- **Minified field names**: Field abbreviation saves 40-60% response size without information loss; especially valuable in list responses
- **BM25 ranking for relevance**: Priority is not filesystem order but relevance score; highest-scoring results get assembled first
- **Per-result clipping**: Explicit `totalMatches` fields on clipped results signal incomplete data

### Integration Opportunities
- Obsidian vault bridging for Claude Code projects stored in Obsidian
- Large documentation system views based on mcpvault's search-first pattern

---

## References

- [mcpvault GitHub Repository](https://github.com/bitbonsai/mcpvault) (accessed 2026-05-30)
- [README.md](https://raw.githubusercontent.com/bitbonsai/mcpvault/main/README.md) (accessed 2026-05-30)
- [package.json](https://raw.githubusercontent.com/bitbonsai/mcpvault/main/package.json) (accessed 2026-05-30)
- [src/createServer.ts — Tool registration](https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/createServer.ts) (accessed 2026-05-30)
- [src/search.ts — BM25 implementation](https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/search.ts) (accessed 2026-05-30)
- [src/filesystem.ts — File operations and vault scanning](https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/filesystem.ts) (accessed 2026-05-30)
- [src/types.ts — Data structures](https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/types.ts) (accessed 2026-05-30)
- [src/pathfilter.ts — Security and path filtering](https://raw.githubusercontent.com/bitbonsai/mcpvault/main/src/pathfilter.ts) (accessed 2026-05-30)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [notion-mcp-server](./notion-mcp-server.md) | mcp-ecosystem | Sibling pattern: Notion block tree lazy-loading vs. mcpvault metadata-first |
| [obsidian-mcp-server](./obsidian-mcp-server.md) | mcp-ecosystem | Complementary: Native Obsidian MCP with document-map format |
