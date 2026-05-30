# Research: cyanheads/obsidian-mcp-server — Patterns for Section-Indexed, Paginated MCP Views

**Date:** 2026-05-30
**Sources:**
- README (raw): `https://raw.githubusercontent.com/cyanheads/obsidian-mcp-server/main/README.md` (fetched 2026-05-30)
- GitHub repo page: `https://github.com/cyanheads/obsidian-mcp-server` (fetched 2026-05-30)
- `server.json` manifest: `https://raw.githubusercontent.com/cyanheads/obsidian-mcp-server/main/server.json` (fetched 2026-05-30)
- `package.json`: `https://raw.githubusercontent.com/cyanheads/obsidian-mcp-server/main/package.json` (fetched 2026-05-30)
- Source tree API: GitHub API rate-limited (unauthenticated). TypeScript source files could not be read directly; all tool behaviour documented here is sourced from the README and server.json.

---

## 1. All 14 MCP Tools — Names, Parameters, and What Each Returns

SOURCE: README Tools table and per-tool sections (fetched 2026-05-30).

### 1.1 Reader Tools

#### `obsidian_get_note`

Read a note in one of **four projection formats**, addressed by vault path, active file, or periodic note (`daily`, `weekly`, `monthly`, `quarterly`, `yearly`).

| Parameter | Type | Description |
|---|---|---|
| `path` / `periodic` | string / enum | Addressing: vault-relative path, `"active"`, or periodic type |
| `format` | enum | `"content"` \| `"full"` \| `"document-map"` \| `"section"` |
| `section` | string | Required when `format: "section"`. Heading path, block reference ID, or frontmatter key |
| `includeLinks` | boolean | Only valid with `format: "full"` — parses outgoing wiki and markdown links |

**Returns by format:**

- `"content"` — raw markdown body only
- `"full"` — content + frontmatter + tags + file stat metadata; with `includeLinks: true`, also returns parsed outgoing wiki and markdown link references (vault-internal only; external URLs filtered)
- `"document-map"` — structural catalog of headings, block references, and frontmatter fields (the outline / table of contents)
- `"section"` — value of a single heading (full subtree), block reference, or frontmatter field

**No pagination parameters.** Single note reads return the full projection in one call.

---

#### `obsidian_list_notes`

List notes and subdirectories under a vault path.

| Parameter | Type | Default | Constraint |
|---|---|---|---|
| `path` | string | vault root | directory path |
| `depth` | integer | 2 | max 20 |
| `extension` | string | (all) | e.g. `"md"` |
| `nameRegex` | string | (none) | post-filter on file name |

**Returns:** directory + file listing.
**Hard cap:** 1,000 entries per call. No cursor/offset — tree walks are depth-bounded, not cursor-paginated.

---

#### `obsidian_list_tags`

List every tag across the vault with usage counts, including hierarchical tag parents. Optional `nameRegex` post-filters the result set.

---

#### `obsidian_list_commands`

List Obsidian command-palette commands, optionally filtered by `nameRegex`. **Off by default** — requires `OBSIDIAN_ENABLE_COMMANDS=true` env var. When disabled, the tool is absent from `tools/list` entirely (wrapped with `disabledTool()`).

---

#### `obsidian_search_notes`

Search the vault. Up to three modes via `mode` parameter:

| Mode | Mechanism | Key parameters |
|---|---|---|
| `"text"` | Substring match with surrounding context windows | `contextLength` (chars per side, default 100), `pathPrefix` filter |
| `"jsonlogic"` | JSONLogic tree evaluated against `path`, `content`, `frontmatter.<key>`, `tags`, `stat.{ctime,mtime,size}` | custom `glob` and `regexp` operators |
| `"omnisearch"` | BM25-ranked via community Omnisearch plugin | quoted phrases, `-exclusion`, `path:` / `ext:` filters, typo tolerance |

**Pagination:** MCP 2025-11-25 opaque cursor spec.
- First page: omit `cursor`
- Subsequent pages: pass `nextCursor` from prior response
- Every result carries `totalCount` (post-path-policy, pre-pagination)
- `nextCursor` absent on last page

**Size bounding (text mode):**
- `maxMatchesPerHit` — per-file match clip (default 10); prevents one heavily-matched file from exhausting the response budget
- Clipped hits carry `truncated: true` and `totalMatches` (total before clip)

**Omnisearch hard cap:** upstream hard-caps results at 50. Response carries `truncated: true` when the cap was likely hit. The recommended workaround is to narrow the query.

---

### 1.2 Writer Tools

#### `obsidian_write_note`

Create or surgically replace.

- **Without `section`** — full-file `PUT`. Refuses to clobber existing file unless `overwrite: true`. Error `file_exists` (Conflict) suggests using `obsidian_patch_note` / `obsidian_append_to_note` / `obsidian_replace_in_note` instead.
- **With `section`** — `PATCH`-with-replace against named heading/block/frontmatter field; rest of file untouched. `overwrite` flag ignored in section mode.

**Returns:** `created: true/false`, `previousSizeInBytes`, `currentSizeInBytes`.

---

#### `obsidian_append_to_note`

Combined upsert + section-append primitive.

- **Without `section`** — `POST /vault/{path}`. Creates file if missing; appends if exists. Returns `created: true` on create branch.
- **With `section`** — `PATCH`-with-append against named heading/block/frontmatter field. File must exist (`note_missing` error otherwise). Pass `createTargetIfMissing: true` to create the section inside an existing file.

Block-reference targets concatenate adjacent to block line without separator — include leading `\n` in `content` if separator is needed.

**Returns:** `created`, `previousSizeInBytes`, `currentSizeInBytes`.

---

#### `obsidian_patch_note`

Surgical `append` / `prepend` / `replace` against a single document target.

| Parameter | Values |
|---|---|
| `operation` | `"append"` \| `"prepend"` \| `"replace"` |
| `target` | heading path, block reference ID, or frontmatter field |

**Workflow recommendation:** use `obsidian_get_note` with `format: "document-map"` first to discover valid targets, then call `obsidian_patch_note`.

---

#### `obsidian_replace_in_note`

Body-wide search-replace inside a single note. Fetch → apply replacements sequentially (each sees prior output) → write back as single `PUT`.

Per-replacement options:

| Option | Type | Default | Description |
|---|---|---|---|
| `useRegex` | boolean | false | treat `search` as ECMAScript regex |
| `caseSensitive` | boolean | true | case-insensitive when false |
| `wholeWord` | boolean | false | wraps pattern in `\b…\b` |
| `flexibleWhitespace` | boolean | false | substitutes whitespace runs with `\s+`; literal mode only |
| `replaceAll` | boolean | true | when false, replaces only first match |

With `useRegex: true`, `$1` / `$&` capture-group references expand in replacement. Literal mode preserves `$1` / `$&` verbatim.

---

### 1.3 Manager / Metadata Tools

#### `obsidian_manage_frontmatter`

Atomic `get` / `set` / `delete` on a single frontmatter key.

---

#### `obsidian_manage_tags`

Add, remove, or list tags on a note.

| `location` | Description |
|---|---|
| `"frontmatter"` (default) | frontmatter `tags:` array only |
| `"inline"` | inline `#tag` syntax in body only; `add` appends `#tag` at end-of-file |
| `"both"` | opt-in reconciliation across both representations |

Inline `#tag` occurrences inside fenced code blocks are intentionally left alone.

---

#### `obsidian_delete_note`

Permanently delete a note. Elicits human confirmation when the client supports it.

---

#### `obsidian_open_in_ui`

Open a file in the Obsidian app UI. Parameters: `failIfMissing`, `newLeaf`.

---

#### `obsidian_execute_command`

Dispatch an Obsidian command-palette command by ID. Off by default (`OBSIDIAN_ENABLE_COMMANDS=true` required). When disabled, absent from `tools/list`.

---

## 2. Heading-Level / Section-Level Addressing

SOURCE: README `obsidian_get_note` and `obsidian_patch_note` sections (fetched 2026-05-30).

Yes — the server supports **full heading-level and section-level addressing** at both read and write time.

### Reading a single section

```
obsidian_get_note(path: "notes/design.md", format: "section", section: "## Architecture")
```

Returns the full subtree under that heading — the heading line plus all body content until the next same-or-higher-level heading.

### Getting the structural outline before reading

```
obsidian_get_note(path: "notes/design.md", format: "document-map")
```

Returns a catalog of:
- All headings (with their hierarchy / paths)
- All block reference IDs (Obsidian `^block-id` syntax)
- All frontmatter field keys

This is the explicit "discover before act" step recommended for patch targets.

### Writing to a specific section

`obsidian_patch_note`, `obsidian_write_note` (with `section`), and `obsidian_append_to_note` (with `section`) all accept a `section` target addressed as:
- Heading path (e.g., `"## Results > ### Table"`)
- Block reference ID (Obsidian `^id` syntax)
- Frontmatter field key

---

## 3. Pagination and Size-Bounding

SOURCE: README pagination and search sections (fetched 2026-05-30).

### Search pagination (`obsidian_search_notes`)

- **Mechanism:** MCP 2025-11-25 opaque cursor protocol
- **Params:** `cursor` (omit for first page), `nextCursor` in response
- **Response fields:** `totalCount` (post-policy, pre-page), `nextCursor` (absent on last page)
- **Per-note cap:** `maxMatchesPerHit` (default 10) — single match-heavy notes cannot exhaust response budget
- **Truncation signal:** `truncated: true` + `totalMatches` on clipped hits
- **Omnisearch absolute cap:** 50 results upstream; `truncated: true` on response when cap likely hit

### Directory listing (`obsidian_list_notes`)

- **Depth param:** default 2, maximum 20
- **Hard entry cap:** 1,000 entries per call
- **No cursor pagination** — use depth + path prefix to scope walks

### Note reads (`obsidian_get_note`)

- **No pagination parameters** at the tool level
- Size management is via **format selection**: use `"document-map"` to get outline only, then `"section"` to fetch a single subtree — this is the progressive-disclosure pattern

### Search context windows (`text` mode)

- `contextLength` — characters of context on each side of a match (default 100)
- Increase to get more surrounding text per hit; no maximum documented

---

## 4. Progressive-Disclosure Patterns

SOURCE: README tool descriptions and workflow recommendations (fetched 2026-05-30).

The server implements a clear two-phase progressive-disclosure pattern:

### Phase 1 — Search / Locate

Use `obsidian_search_notes` to find candidate notes before loading any note body:
- `text` mode returns file paths + snippet windows, not full content
- `jsonlogic` mode can filter on frontmatter fields, tags, stat — zero body content returned
- `omnisearch` mode returns BM25-ranked path + excerpt list

### Phase 2 — Structured outline before body

```
obsidian_get_note(format: "document-map")  →  headings + blocks + frontmatter keys
obsidian_get_note(format: "section", section: "<target>")  →  just that subtree
```

The README explicitly states this workflow as a recommendation: **"Pair the document-map projection with `obsidian_patch_note` to discover edit targets before patching."**

### Phase 3 — Full body only when needed

```
obsidian_get_note(format: "content")  →  raw markdown body
obsidian_get_note(format: "full")     →  body + frontmatter + tags + stat
```

**Summary of progressive-disclosure ladder:**
1. `obsidian_search_notes` → file path list + snippets (no body)
2. `obsidian_get_note(format: "document-map")` → structural outline (no body)
3. `obsidian_get_note(format: "section", section: "X")` → single subtree (partial body)
4. `obsidian_get_note(format: "full")` → complete body + metadata

---

## 5. Large Vault and Long Document Representation

SOURCE: README tool table and tool descriptions (fetched 2026-05-30).

### Large vaults

- `obsidian_list_notes`: depth-bounded walk (default 2, max 20) with hard 1,000-entry cap — prevents blowing token budget on listing
- `obsidian_list_tags`: tag catalog across entire vault; usage counts allow agents to understand vault topology without reading any note
- `obsidian_search_notes`: search-first pattern returns file-path-level results, not note bodies

### Long documents

- **`format: "document-map"`** extracts only the structural skeleton (headings, block refs, frontmatter keys) — O(headings) tokens rather than O(content) tokens
- **`format: "section"`** returns one heading subtree — allows binary-search-style descent into a large document
- **Block references** (`^id` syntax) allow sub-heading granularity addressing for both reads and writes
- **Frontmatter** is a separate projection layer — agents can read/write frontmatter fields without touching the body at all

---

## 6. Techniques Worth Adopting

SOURCE: All findings above, cross-referenced with our "section index + paginated body + token-budget gate" pipeline.

### Technique 1: Four-format projection enum on a single "read" tool

Instead of separate tools for "get outline", "get section", "get full", expose a single tool with a `format` enum: `"document-map"` | `"section"` | `"content"` | `"full"`. This lets the caller explicitly opt into the cheapest representation. In our pipeline, this maps to the `resolve_sections` → `assemble_body` → token-budget gate chain — but exposed as a single tool call parameter rather than multiple round trips.

**Adoption:** Replace the implicit "always return body" default in our view pipeline with an explicit `format` param. `"document-map"` returns only section headings + their byte ranges (our `## Sections` index). `"section"` accepts a heading path and returns just that subtree. `"full"` triggers the existing pipeline with token-budget gate.

### Technique 2: `document-map` as a zero-cost prerequisite before any edit or large read

The cyanheads pattern explicitly pairs `format: "document-map"` before any patch operation to discover valid targets. In our context: before assembling a full body view for an LLM, first call the equivalent of `document-map` to return a section index (heading list + byte ranges). The LLM then selects which section(s) to read. Only selected sections enter the token budget.

**Adoption:** Add a `list_sections` step at the start of our pipeline. When the assembled body would exceed the token budget, return the section index instead of a truncated body — the caller can then re-call with `sections=[...]` to select specific ones.

### Technique 3: Opaque cursor pagination with `totalCount` + `truncated` signalling

The search tool returns `totalCount` (pre-pagination total), `nextCursor` (omitted on last page), and per-hit `truncated: true` + `totalMatches` when clipping occurs. This gives the caller full situational awareness without exposing internal offset arithmetic. `truncated: true` is cleaner than a silent clip — the caller knows content was omitted and `totalMatches` tells them how much.

**Adoption:** In our paginated body view, replace the current token-budget truncation (which returns a partial body without signalling incompleteness) with explicit `truncated: true`, `total_sections`, and `next_cursor`/`offset` fields. Never silently truncate — always signal.

### Technique 4: Per-result match cap (`maxMatchesPerHit`) to prevent single-document budget exhaustion

A single highly-matched note in `text` search mode is clipped at `maxMatchesPerHit` (default 10). This prevents one document from consuming the entire result budget at the expense of all others. The pattern is "fair budget allocation across results" rather than "return everything until full".

**Adoption:** In our section filter pipeline, when a `sections=[...]` filter returns one very large section, apply a character/token cap per section and carry `truncated: true` + `remaining_chars` on that section's entry. Do not let one large section crowd out others in a multi-section response.

### Technique 5: Explicit `section` addressing via heading path + block reference ID

The server uses a unified `section` parameter that accepts a heading path string (e.g., `"## Results > ### Table"`) or a block reference ID (`^block-id`). This makes section addressing deterministic and composable — the LLM doesn't need to count lines or maintain byte offsets; it uses the structural address discovered from `document-map`.

**Adoption:** In our pipeline, the `## Sections` index should emit heading paths (the full heading hierarchy as a string, not just the heading text) so callers can pass them back as stable section selectors. This is more robust than numeric index or line-range addressing when the document is edited between calls.

### Technique 6 (bonus): `previousSizeInBytes` / `currentSizeInBytes` on every mutating response

Every write tool returns both pre- and post-write byte sizes. This lets callers detect: accidental clobbers (sizes diverge unexpectedly), concurrent writers (pre-size doesn't match expected), and auto-newline injection (delta > `len(content)`).

**Adoption:** In our MCP view pipeline's write path, return before/after byte sizes on any operation that modifies the underlying document. This is a low-cost integrity signal that prevents silent data loss bugs.

---

## Appendix: Full Tool List Reference

SOURCE: README Tools table (fetched 2026-05-30).

| Tool | Category | Key size/pagination constraint |
|---|---|---|
| `obsidian_get_note` | Read | No pagination; use `format` enum to bound response size |
| `obsidian_list_notes` | Read | depth 2–20; hard 1,000-entry cap; no cursor |
| `obsidian_list_tags` | Read | No cap documented |
| `obsidian_list_commands` | Read | Opt-in only; `nameRegex` filter |
| `obsidian_search_notes` | Read | Opaque cursor; `maxMatchesPerHit` 10; omnisearch cap 50 |
| `obsidian_write_note` | Write | Section or full-file mode |
| `obsidian_append_to_note` | Write | Section or full-file mode |
| `obsidian_patch_note` | Write | Single target: heading / block ref / frontmatter field |
| `obsidian_replace_in_note` | Write | Sequential replacements; regex + literal modes |
| `obsidian_manage_frontmatter` | Metadata | Atomic single-key get/set/delete |
| `obsidian_manage_tags` | Metadata | frontmatter / inline / both |
| `obsidian_delete_note` | Destructive | Human confirmation when client supports it |
| `obsidian_open_in_ui` | UI | No data returned |
| `obsidian_execute_command` | Escape hatch | Opt-in only |

### 3 Resources

| URI | Description |
|---|---|
| `obsidian://vault/{+path}` | Note content, frontmatter, tags, stat metadata |
| `obsidian://tags` | All tags across vault with usage counts |
| `obsidian://status` | Server reachability, auth status, plugin/Obsidian version |

Resources mirror `obsidian_get_note` and `obsidian_list_tags` tool functionality — exist for clients that prefer attaching a specific note snapshot directly to a conversation rather than calling a tool.

---

## Source Fetch Status

| Source | Status |
|---|---|
| `github.com/cyanheads/obsidian-mcp-server` (README, HTML) | Fetched successfully |
| `raw.githubusercontent.com/.../README.md` | Fetched successfully |
| `raw.githubusercontent.com/.../server.json` | Fetched successfully |
| `raw.githubusercontent.com/.../package.json` | Fetched successfully |
| GitHub API tree (file listing) | Rate-limited (unauthenticated) — no source TS files read |
| `src/mcp-server/tools/**/*.ts` (raw files) | HTTP 404 / rate-limited — not read |

All tool behaviours documented above derive from the README and server.json manifest, not from TypeScript source inspection. Exact Zod schema field names and internal implementation details (e.g., the precise `section` string syntax accepted, any undocumented query fields) could not be verified from source.
