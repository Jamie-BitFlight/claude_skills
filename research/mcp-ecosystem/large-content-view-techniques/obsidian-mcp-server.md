---
name: obsidian-mcp-server
research_date: 2026-05-30
source_url: https://github.com/cyanheads/obsidian-mcp-server
github_repository: https://github.com/cyanheads/obsidian-mcp-server
version_at_research: v0.7.0
license: MIT
freshness_tracking:
  last_verified: 2026-05-30
  version_at_verification: v0.7.0
  next_review: 2026-08-30
  confidence_map: "Overview: high, Problem Addressed: high, Key Features: high (doc-read), Technical Architecture: high (doc-read), Installation & Usage: high, Relevance to Claude Code: medium"
---

# obsidian-mcp-server

## Overview

The cyanheads `obsidian-mcp-server` (v0.7.0) is an MCP bridge for Obsidian vaults offering 14 tools spanning read, write, metadata, and search operations. It features four-format projection modes (`content`, `full`, `document-map`, `section`), heading-level and section-level addressing for both reads and writes, and explicit progressive-disclosure patterns with opaque cursor pagination. The server enables agents to inspect document structure before reading bodies, retrieve individual sections by heading path, and perform surgical edits targeting specific sections. (Accessed: README.md, server.json, accessed 2026-05-30)

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI assistants cannot navigate large Obsidian documents without reading full bodies | Four-format projection enum (`content`, `full`, `document-map`, `section`) allows agents to fetch only the representation needed (accessed 2026-05-30) |
| Large document bodies exceed token budgets | `document-map` format returns structural skeleton (headings, blocks, frontmatter keys) without body content; enables binary-search descent into large docs (accessed 2026-05-30) |
| Agents cannot target edits to specific sections | Full heading-level and section-level addressing via `section` parameter in read and write tools; no line number fragility (accessed 2026-05-30) |
| Search results risk overwhelming response size | Cursor pagination with per-result clipping: `maxMatchesPerHit` caps matches per file; `truncated: true` signals incompleteness; `totalMatches` tracks original count (accessed 2026-05-30) |
| Directory listing operations pollute context with too many entries | Depth-bounded walks (configurable, max 20) with hard 1,000-entry cap; no cursor pagination — use path filtering to scope (accessed 2026-05-30) |

---

## Key Features

### Read Tools (4 formats)
- **obsidian_get_note**: Read note in four projection modes — `content` (body only), `full` (body + metadata + tags + links), `document-map` (outline only), `section` (single heading subtree)
- **obsidian_list_notes**: Directory listing with depth parameter (default 2, max 20) and hard 1,000-entry cap
- **obsidian_list_tags**: Vault-wide tag catalog with usage counts
- **obsidian_search_notes**: Three search modes — `text` (substring with context windows), `jsonlogic` (filter by frontmatter/tags/stat), `omnisearch` (BM25-ranked)

### Write Tools
- **obsidian_write_note**: Full-file or section-targeted write; refuses clobber unless `overwrite: true`
- **obsidian_append_to_note**: Upsert + section-append; creates file or appends to existing
- **obsidian_patch_note**: Surgical append/prepend/replace against heading/block/frontmatter target
- **obsidian_replace_in_note**: Body-wide search-replace with regex/literal modes

### Metadata Tools
- **obsidian_manage_frontmatter**: Atomic get/set/delete on single YAML key
- **obsidian_manage_tags**: Add/remove/list tags in frontmatter or inline `#tag` syntax
- **obsidian_delete_note**: Permanent delete with human confirmation prompt
- **obsidian_open_in_ui**: Open file in Obsidian app
- **obsidian_execute_command**: Dispatch command-palette command (requires `OBSIDIAN_ENABLE_COMMANDS=true`)

---

## Technical Architecture

The Obsidian MCP server implements three core patterns for efficient large-document handling:

### Pattern 1: Four-Format Projection Enum
- **`format` parameter**: Single tool with enum covering different representations
  - `content`: Raw markdown body only (O(body) tokens)
  - `full`: Body + frontmatter + tags + stat metadata + parsed wiki/markdown links (O(body) tokens)
  - `document-map`: Headings, block references, frontmatter keys only (O(headings) tokens)
  - `section`: Single heading subtree — full content under named heading only (O(section) tokens)
- **Caller chooses cost**: Format selection is explicit; no "always return full body" default

### Pattern 2: Section-Level Addressing
- **Heading path syntax**: `"## Results > ### Table"` uniquely addresses heading hierarchy
- **Block reference syntax**: `^block-id` addresses Obsidian block reference IDs
- **Frontmatter field syntax**: Direct key addressing for YAML frontmatter
- **Workflow**: Call `obsidian_get_note(format: "document-map")` to discover valid targets, then `obsidian_patch_note(section: "<target>")` to edit

### Pattern 3: Pagination & Size Bounding
- **Opaque cursor protocol** (MCP 2025-11-25): `cursor` omitted on first call; response carries `nextCursor` (omitted on last page)
- **Response fields**: `totalCount` (pre-pagination), `nextCursor` (next page token), `truncated` (boolean), `totalMatches` (on clipped results)
- **Per-result cap**: `maxMatchesPerHit` (default 10) prevents single highly-matched note from exhausting budget
- **Directory listing cap**: 1,000-entry hard maximum per call (no pagination — use depth/path filtering)
- **Search context windows**: `contextLength` parameter controls characters of context around each match

(Source: README.md tool sections, server.json manifest, accessed 2026-05-30)

---

## Installation & Usage

### Installation

Install via npm:

```bash
npm install -g obsidian-mcp-server
```

### Configuration

Configure in `.mcp.json` pointing to vault directory:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "obsidian-mcp-server",
      "args": ["/path/to/vault"]
    }
  }
}
```

### Example Workflow

**Step 1: Discover structure without reading body:**
```bash
obsidian_get_note(path="notes/design.md", format="document-map")
# Returns: { headings: ["## Overview", "## Architecture", "## API"], 
#            blockRefs: ["^overview", "^arch"], 
#            frontmatterKeys: ["title", "status"] }
```

**Step 2: Read single section:**
```bash
obsidian_get_note(path="notes/design.md", format="section", section="## Architecture")
# Returns: full subtree under that heading only
```

**Step 3: Patch specific section:**
```bash
obsidian_patch_note(path="notes/design.md", 
                    target="## Architecture", 
                    operation="append", 
                    content="\n### New subsection\nDetails here")
```

**Step 4: Search with results clipping:**
```bash
obsidian_search_notes(mode="text", query="component", maxMatchesPerHit=5)
# Returns: [{ path: "...", excerpt: "...component...", truncated: false, totalMatches: 2 }]
```

---

## Relevance to Claude Code Development

### Applications
- **Large markdown files in Claude projects**: Using `document-map` and `section` formats enables navigation of large documentation or design notes without token budget overruns
- **Obsidian as Claude knowledge base**: Direct integration with Obsidian for project context and requirements management
- **Surgical documentation edits**: Section-targeting enables precise edits (e.g., update a specific section without touching the rest of the file)

### Patterns Worth Adopting
- **Format enum for cost control**: Explicit caller-driven format selection rather than implicit "always full" default
- **Heading paths as stable section IDs**: Structural addresses are more robust than line numbers or byte offsets across edits
- **Document structure discovery before body read**: `document-map` prerequisite for any large read ensures agents understand scope before paying token cost
- **Per-result clipping with truncation signals**: `truncated: true` + `totalMatches` fields make incomplete data explicit
- **Opaque cursor pagination**: Prevents caller arithmetic errors and supports arbitrary server-side pagination strategies

### Integration Opportunities
- Support for obsidian-mcp-server as Claude Code knowledge base interface
- Heading-path-based section targeting for other documentation systems
- Document-map pattern for large codebase exploration

---

## References

- [obsidian-mcp-server GitHub Repository](https://github.com/cyanheads/obsidian-mcp-server) (accessed 2026-05-30)
- [README.md](https://raw.githubusercontent.com/cyanheads/obsidian-mcp-server/main/README.md) (accessed 2026-05-30)
- [server.json](https://raw.githubusercontent.com/cyanheads/obsidian-mcp-server/main/server.json) (accessed 2026-05-30)
- [package.json](https://raw.githubusercontent.com/cyanheads/obsidian-mcp-server/main/package.json) (accessed 2026-05-30)

**Note**: GitHub API and TypeScript source files were rate-limited or inaccessible during verification. Tool behaviors documented above derive from README and server.json manifest. Implementation details not verified from source.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [mcpvault](./mcpvault.md) | mcp-ecosystem | Sibling: Both Obsidian vaults; different approaches (native plugin vs. thin bridge) |
| [notion-mcp-server](./notion-mcp-server.md) | mcp-ecosystem | Sibling: Both block-based hierarchies; Notion lazy-loads, Obsidian maps structure first |
