---
name: obsidian-mcp-server
research_date: 2026-05-30
source_url: https://github.com/cyanheads/obsidian-mcp-server
github_repository: https://github.com/cyanheads/obsidian-mcp-server
version_at_research: v3.2.3
license: Apache-2.0
freshness_tracking:
  last_verified: 2026-05-30
  version_at_verification: v3.2.3
  next_review: 2026-08-30
  confidence_map: "Overview: high, Problem Addressed: high, Key Features: high (doc-read), Technical Architecture: high (doc-read), Installation & Usage: high, Relevance to Claude Code: medium"
---

# obsidian-mcp-server

## Overview

The cyanheads `obsidian-mcp-server` (v3.2.3, Apache-2.0) is an MCP bridge for Obsidian vaults offering 14 tools spanning read, write, metadata, and search operations. It is a client of the community [Obsidian Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) plugin (v4.0.0 or later required) rather than a direct filesystem reader — it talks HTTP to a running Obsidian instance, so it has no vault-path argument. It features four-format projection modes (`content`, `full`, `document-map`, `section`), heading-level and section-level addressing for both reads and writes, and explicit progressive-disclosure patterns with opaque cursor pagination. The server enables agents to inspect document structure before reading bodies, retrieve individual sections by heading path, and perform surgical edits targeting specific sections. (Accessed: README.md, server.json, package.json, accessed 2026-05-30)

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

A section is addressed by the shared `SectionSchema`: `{ type: "heading" | "block" | "frontmatter", target: string }`.
The meaning of `target` depends on `type`:

- **Heading**: the heading's *text*, without `#` markers. Nesting uses a `::` delimiter, not `>` —
  `"Top::Sub"` walks to a heading named `Top` and then to a deeper heading named `Sub` beneath it.
  `matchHeading` splits on `::` and matches against capture group 2 of `/^(#{1,6})\s+(.*?)\s*$/`,
  so the `#` characters are never part of the target.
- **Block**: the block reference ID **without** the leading caret — the schema states
  `"block reference without leading caret (e.g. \"2d9b4a\", not \"^2d9b4a\")"`. The `^` is the
  in-document marker the extractor searches for.
- **Frontmatter**: the YAML key name directly.

The note itself is addressed separately via `TargetSchema`, a discriminated union on `type`:
`{type: "path", path}`, `{type: "active"}`, or `{type: "periodic", period, date?}`. There is no
bare `path` string parameter.

- **Workflow**: Call `obsidian_get_note` with `format: "document-map"` to discover valid targets,
  then `obsidian_patch_note` with the matching `section` object to edit. The `document-map`
  response is `{ format, path, headings: string[], blocks: string[], frontmatterFields: string[] }`.

### Pattern 3: Pagination & Size Bounding
- **Opaque cursor protocol** (MCP 2025-11-25): `cursor` omitted on first call; response carries `nextCursor` (omitted on last page)
- **Response fields**: `totalCount` (pre-pagination), `nextCursor` (next page token), `truncated` (boolean), `totalMatches` (on clipped results)
- **Per-result cap**: `maxMatchesPerHit` (default 10) prevents single highly-matched note from exhausting budget
- **Directory listing cap**: 1,000-entry hard maximum per call (no pagination — use depth/path filtering)
- **Search context windows**: `contextLength` parameter controls characters of context around each match

(Source: README.md tool sections, `src/mcp-server/tools/definitions/_shared/schemas.ts`,
`src/mcp-server/tools/definitions/obsidian-get-note.tool.ts`,
`src/services/obsidian/section-extractor.ts`, server.json manifest, accessed 2026-05-30)

---

## Installation & Usage

### Prerequisites

This server does not read the vault from disk. It requires the community
[Obsidian Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) plugin,
**v4.0.0 or later**, installed and enabled in the vault, with Obsidian running. Generate an API key
in *Settings → Community Plugins → Local REST API* and supply it as `OBSIDIAN_API_KEY`. The server
defaults to `http://127.0.0.1:27123`, which requires enabling "Non-encrypted (HTTP) Server" in the
plugin settings; set `OBSIDIAN_BASE_URL=https://127.0.0.1:27124` to use the always-on HTTPS port
instead (the plugin's self-signed certificate is accommodated by `OBSIDIAN_VERIFY_SSL=false`,
which is the default).

### Configuration

There is no vault path argument — configuration is entirely by environment variable. The README's
`npx` form:

```json
{
  "mcpServers": {
    "obsidian": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "obsidian-mcp-server@latest"],
      "env": {
        "MCP_TRANSPORT_TYPE": "stdio",
        "MCP_LOG_LEVEL": "info",
        "OBSIDIAN_API_KEY": "your-local-rest-api-key"
      }
    }
  }
}
```

The README gives an equivalent `bunx` form with `args: ["obsidian-mcp-server@latest"]`.

Notable optional environment variables from `server.json`: `OBSIDIAN_ENABLE_COMMANDS` (default
`false` — gates the `obsidian_list_commands` / `obsidian_execute_command` pair),
`OBSIDIAN_READ_PATHS` / `OBSIDIAN_WRITE_PATHS` (comma-separated folder allowlists),
`OBSIDIAN_READ_ONLY` (global write kill switch), and `OBSIDIAN_OMNISEARCH_URL` (probed once at
startup; the `omnisearch` mode is omitted from the `obsidian_search_notes` schema when unreachable).

### Example Workflow

Argument shapes below are from the Zod schemas in
`src/mcp-server/tools/definitions/`. Note that the note is addressed by a `target` object and the
section by a `section` object — neither is a bare string.

**Step 1: Discover structure without reading body:**

```text
obsidian_get_note(target={type: "path", path: "notes/design.md"}, format="document-map")
→ { format: "document-map", path: "notes/design.md",
    headings: [...], blocks: [...], frontmatterFields: [...] }
```

**Step 2: Read a single section (heading text, no `#`):**

```text
obsidian_get_note(target={type: "path", path: "notes/design.md"},
                  format="section",
                  section={type: "heading", target: "Architecture"})
→ the full subtree under that heading
```

**Step 3: Patch that section:**

```text
obsidian_patch_note(target={type: "path", path: "notes/design.md"},
                    section={type: "heading", target: "Architecture"},
                    operation="append",
                    content="\n### New subsection\nDetails here")
```

**Step 4: Search with per-file clipping:**

```text
obsidian_search_notes(mode="text", query="component", maxMatchesPerHit=5)
→ results carry totalCount; clipped hits carry truncated: true and totalMatches
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
- [package.json — version and license](https://raw.githubusercontent.com/cyanheads/obsidian-mcp-server/main/package.json) (accessed 2026-05-30)
- [src/mcp-server/tools/definitions/_shared/schemas.ts — `TargetSchema`, `SectionSchema`, `PatchOptionsSchema`](https://raw.githubusercontent.com/cyanheads/obsidian-mcp-server/main/src/mcp-server/tools/definitions/_shared/schemas.ts) (accessed 2026-05-30)
- [src/mcp-server/tools/definitions/obsidian-get-note.tool.ts — four-format projection output schemas](https://raw.githubusercontent.com/cyanheads/obsidian-mcp-server/main/src/mcp-server/tools/definitions/obsidian-get-note.tool.ts) (accessed 2026-05-30)
- [src/services/obsidian/section-extractor.ts — `::` heading-path matching and block-reference extraction](https://raw.githubusercontent.com/cyanheads/obsidian-mcp-server/main/src/services/obsidian/section-extractor.ts) (accessed 2026-05-30)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [mcpvault](./mcpvault.md) | mcp-ecosystem | Sibling: both target Obsidian vaults, by opposite means — mcpvault reads the vault directory directly from disk; this server proxies HTTP to the Local REST API plugin inside a running Obsidian |
| [notion-mcp-server](./notion-mcp-server.md) | mcp-ecosystem | Sibling: Both block-based hierarchies; Notion lazy-loads, Obsidian maps structure first |
