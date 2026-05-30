# Large-Content View Techniques — Adoption Assessment

**Topic**: How Notion, Obsidian, mcpvault, and Anthropic's *Code execution with MCP* present indexes / headers / pagination of large content trees to an LLM agent, and which techniques the development-harness backlog **view pipeline** should adopt.

**Consumes**: [Jamie-BitFlight/claude_skills#2498](https://github.com/Jamie-BitFlight/claude_skills/issues/2498) — *decompose `backlog_core` `operations.py`/`server.py` into cohesive modules*. These techniques are design input for the `view_assembly.py` / `view_budget.py` / `section_filter.py` extraction.

**Per-source research** (this folder):

- [Notion MCP server](./notion-mcp-server.md)
- [Obsidian MCP server (cyanheads)](./obsidian-mcp-server.md)
- [mcpvault (bitbonsai)](./mcpvault.md)

**Primary article**: Anthropic, *Code execution with MCP* (2025-11-04), <https://www.anthropic.com/engineering/code-execution-with-mcp> (accessed 2026-05-30).

---

## Convergent patterns (where ≥3 sources agree)

| # | Pattern | Notion | Obsidian | mcpvault | Anthropic |
|---|---------|--------|----------|----------|-----------|
| P1 | **Outline/index first, body on demand** | page props vs `retrieve-block-children` | `document-map` then `section` | section-index before body | progressive disclosure / detail levels |
| P2 | **One caller-controlled representation param** | — | `format: document-map\|section\|content\|full` | metadata vs frontmatter vs full | `search_tools` detail level (name / +desc / full schema) |
| P3 | **Explicit, never-silent truncation/pagination signals** | `has_more` + `next_cursor` | `truncated:true` + `totalCount`/`totalMatches` | hard caps surfaced | filter-in-code, return a slice knowingly |
| P4 | **Stable selectors that survive edits** | block IDs | heading-path `"## A > ### B"` / `^block-id` | path-based | tool files by name |
| P5 | **Per-item cap for fair budget allocation** | `page_size` | `maxMatchesPerHit` (default 10) | `Math.min(req, cap)` | slice before logging |
| P6 | **Selective-depth expansion flag** | `has_children: bool` | block refs in map | `hasFrontmatter` gate | read only needed tool files |

## Our brittle structure (observed during PR #2496 / #2495)

- **Assemble-then-measure**: the body and the whole-item `## Sections` index are built first, then the budget is checked. The index alone can exceed budget; section metadata is rebuilt in 3+ branches → desync (C3/C8/C9).
- **Fragile addressing**: `section="2"` / comma / regex / line-range. Numeric + line indices break on edits; case drift dropped metadata.
- **Silent / contradictory budget outcomes**: over-budget can replace an explicitly requested slice with a directory; the over-budget measurement blanks duplicated `entries[*].content` but returns it (`server.py:137`) → an over-budget payload can still ship.
- **Pagination**: offset/limit on entry blocks; past-end returns empty (intended contract); negative-offset accounting fixed (C5).

## Adoption proposals (mapped to #2498 phases)

### A. Make the index the primary over-budget response, not a fallback after assembly (P1, P2)

- **Now**: `_assemble_view_content` builds body + prepends `## Sections` index, then `_build_over_budget_view` may replace it.
- **Adopt** (Obsidian `document-map`, Notion metadata-first, Anthropic detail levels): a single `detail` parameter on `backlog_view` — `map` (section index only: heading-path + token/char count + `subsection_count`), `section` (one resolved section body), `full` (today's behavior, budget-gated). Default to `map` when `full` would exceed budget instead of truncating. The caller re-calls `detail=section, section=<heading-path>`.
- **Phase**: `view_assembly.py` (resolve→assemble) + `view_budget.py` (the map/full decision).

### B. Resolve → assemble → measure the delivered object once (P3, P5)

- **Now**: token measurement blanks duplicated content but the returned payload keeps it (`server.py:137` under-count); index built from unpaginated body.
- **Adopt** (Anthropic filter-in-code; mcpvault server-side caps): assemble the **exact object to return**, measure *that* serialized object, never a different shape than is delivered. Add a per-section token cap; on hit, emit `truncated:true` + `remaining_chars` for that section so one section can't crowd out others.
- **Phase**: `view_budget.py` ("measure the delivered object once" ADR principle).

### C. Replace silent truncation with explicit signals (P3)

- **Now**: over-budget directory swap; some paged paths lack total/remaining.
- **Adopt** (Notion `has_more`/`next_cursor`; Obsidian `truncated`+`totalCount`): every response that omits content carries `truncated: true`, `total_*`, and `remaining_*`. Over-budget `detail=map` responses state the omitted body size. No path returns a smaller payload without a field saying so.
- **Phase**: response schema (typed `sections_metadata` boundary, already #2498 debt).

### D. Heading-path selectors instead of numeric/line indices (P4)

- **Now**: `section="2"`, comma indices, line ranges — break on edits, drop metadata on case drift.
- **Adopt** (Obsidian heading-path, Notion IDs): the section index emits a **stable heading-path string** per section (`"## RT-ICA"`, `"## Log > ### Detail"`); the caller passes it back as the `section` selector. Keep numeric as a convenience alias resolved against the same index. Round-trips without offset state.
- **Phase**: `section_filter.py` (resolver + index emission).

### E. `subsection_count` / `has_subsections` on each index entry (P6)

- **Adopt** (Notion `has_children`): each section-index entry carries `subsection_count: int`, so the caller expands only the subtrees it needs — no full-tree pre-fetch.
- **Phase**: `section_filter.py` index builder.

### F. Cheap metadata gate before assembly (P1, mcpvault)

- **Adopt**: compute section count + per-section sizes from headers **before** rendering bodies; decide `map` vs `full` from those sizes rather than building everything then discarding.
- **Phase**: `view_assembly.py`.

## What we already do better than the references

Notion's **open-source** local MCP server has **no token-budget gate** and returns `JSON.stringify(data)` whole; the budgeted variant is closed-source/remote. Our auto-compaction gate is ahead of the open reference — the work is to make it *measure the delivered object* and *signal omissions*, not to invent the gate.

## Net

The single highest-leverage change is **A+B together**: turn "assemble everything, then maybe replace it" into "decide representation from cheap metadata, assemble only that, measure exactly what ships." That removes the whole class of bugs PR #2496 chased (index-over-budget, metadata desync, measurement-vs-delivery divergence) **by construction** rather than by patch — the stated purpose of #2498.
