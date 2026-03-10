# Gap Analysis: `rtfp` Plugin vs `frustration-analyzer` Plugin

**Date:** 2026-03-10
**Purpose:** Identify functional gaps between the two RTFP implementations to inform consolidation strategy.

---

## Executive Summary

Both plugins implement the same core pipeline: scan Claude Code session transcripts for the strongest user emotional reaction to an instruction-following failure, reconstruct the triggering context, and render a shareable PNG. The `frustration-analyzer` plugin (v0.2.13) is an MCP-server-based redesign of the original `rtfp` plugin (v1.0.9). The MCP version exposes composable tools that can be called independently, while the original bundles all logic into monolithic CLI scripts orchestrated by a skill.

**Recommendation:** Consolidate into `frustration-analyzer` (MCP version) and retire `rtfp`. The gaps identified below show what needs to be ported or preserved.

---

## Architecture Comparison

| Dimension | `rtfp` (original) | `frustration-analyzer` (MCP) |
|-----------|-------------------|------------------------------|
| **Version** | 1.0.9 | 0.2.13 |
| **Entry point** | `/rtfp` skill → CLI scripts | `/rtfp` skill → MCP tools |
| **Data layer** | 4 standalone Python CLI scripts | 1 FastMCP server (`mcp/server.py`) with 7 tools |
| **Query engine** | DuckDB via CLI scripts | DuckDB via MCP tool functions |
| **Token counting** | tiktoken (p50k_base) | Not observed — batching may differ |
| **Rendering** | PIL/Pillow (direct PNG) | Rich → SVG → cairosvg PNG (with box-drawing fix) |
| **Agents** | 2 (reaction-detector, context-reconstructor) | 3 (frustration-analyst orchestrator, batch-detector, context-reconstructor) |
| **MCP server** | None | Yes (FastMCP >=3.0.0rc1) |
| **Composability** | Low — scripts are pipeline-coupled | High — each MCP tool is independently callable |
| **Test coverage** | Not observed | `tests/test_render_rage_receipt.py` |

---

## Functional Gap Matrix

### Capabilities present in `rtfp` but MISSING from `frustration-analyzer`

| # | Capability | `rtfp` Implementation | Gap Severity | Notes |
|---|-----------|----------------------|--------------|-------|
| G1 | **tiktoken-based batch splitting** | `extract_batches.py` uses tiktoken (p50k_base) to split messages into ~100k token batches | **Medium** | MCP version's `extract_user_messages` writes a single batch JSONL — may not handle very large sessions with token-aware splitting |
| G2 | **Configurable batch token target** | `--batch-tokens` CLI argument (default 100k) | **Low** | Easy to add as MCP tool parameter |
| G3 | **Multi-batch file output** | Writes N batch files to `$TMPDIR/rtfp-batches-<sessionid>/batch_NNN.json` | **Medium** | MCP version writes single file; orchestrator skill may handle splitting at agent level instead |
| G4 | **PIL direct rendering** | Pillow-based PNG with macOS window chrome, traffic-light dots, rounded corners | **Medium** | MCP version uses Rich→SVG→cairosvg pipeline instead. Different visual style. Original has macOS-specific chrome that may be preferred aesthetically |
| G5 | **Font fallback chain** | Explicit fallback: DejaVu → Liberation → Menlo → Consolas | **Low** | Rich handles font fallback internally; cairosvg uses system fonts |
| G6 | **Configurable image dimensions** | Width (default 900px), font size (default 15pt) as script parameters | **Low** | Easy to add as `render_rage_receipt` tool parameters |

### Capabilities present in `frustration-analyzer` but MISSING from `rtfp`

| # | Capability | `frustration-analyzer` Implementation | Gap Severity | Notes |
|---|-----------|--------------------------------------|--------------|-------|
| G7 | **MCP server architecture** | FastMCP server with 7 independently callable tools | **Critical** | Core extensibility advantage — tools usable by any MCP client, not just the skill pipeline |
| G8 | **`scan_transcripts` tool** | Paginated user message extraction with context window, offset/limit | **High** | Enables direct browsing without running full pipeline |
| G9 | **`generate_social_post` tool** | Generates social media post text + hashtags + privacy reminder | **High** | Net-new feature not in original |
| G10 | **`get_scenario` tool** | Quick message + context retrieval by file + line index | **Medium** | Convenience tool for targeted lookups |
| G11 | **SVG intermediate output** | Rich Panel → SVG export before PNG conversion | **Medium** | SVG is resolution-independent and editable |
| G12 | **Box-drawing character fix** | SVG post-processing replaces box-drawing borders with smooth `<rect>` strokes | **Medium** | Eliminates sub-pixel gap rendering artifacts |
| G13 | **Inline image delivery** | Returns base64 PNG bytes in MCP response | **Medium** | MCP clients can display inline without file I/O |
| G14 | **Dedicated orchestrator agent** | `frustration-analyst.md` — separate orchestrator agent | **Low** | Cleaner separation of orchestration from detection |
| G15 | **Privacy reminder in output** | Explicit privacy reminder after rendering + in `generate_social_post` | **Low** | Good practice; easy to add anywhere |
| G16 | **Test suite** | `tests/test_render_rage_receipt.py` | **Medium** | Original has no observed tests |

### Capabilities present in BOTH (functional parity)

| Capability | Notes |
|-----------|-------|
| Session listing from `~/.claude/projects/` | Both use DuckDB JSONL querying |
| User-only message extraction | Both filter to user role messages |
| Parallel subagent detection | Both spawn per-batch detection agents |
| Context window reconstruction | Both retrieve N messages before/after flagged index |
| Winner selection by emotional intensity | Both use LLM judgment with similar criteria |
| Terminal-style dark PNG output | Both produce dark-background cards (different rendering pipelines) |
| 3-field artifact (task/assistant/user) | Identical output schema |
| Complex content text extraction | Both handle nested content blocks, tool_use, tool_result |
| System noise filtering | Both exclude system reminders, tool errors, etc. |

---

## Dependency Comparison

| Dependency | `rtfp` | `frustration-analyzer` | Delta |
|-----------|--------|----------------------|-------|
| duckdb | >=1.0.0 | >=0.10.0 | rtfp requires newer version |
| tiktoken | >=0.7.0 | not used | Token counting gap (G1) |
| pillow | >=10.0.0 | not used | Different rendering pipeline |
| rich | not used | >=13.0 | Different rendering pipeline |
| cairosvg | not used | >=2.7.0 | SVG→PNG conversion |
| fastmcp | not used | >=3.0.0rc1,<4 | MCP server framework |

**Dependency trade-off:** `frustration-analyzer` trades tiktoken+pillow for rich+cairosvg+fastmcp. The MCP version has a heavier framework dependency (fastmcp) but gains composability. The rendering trade (PIL→Rich+cairosvg) loses fine-grained pixel control but gains SVG intermediate output.

---

## Consolidation Recommendations

### Must-port from `rtfp` → `frustration-analyzer`

| Priority | Gap | Action |
|----------|-----|--------|
| **P1** | G1 — Token-aware batch splitting | Add tiktoken-based splitting to `extract_user_messages` or create a `split_batches` tool. Large sessions (>100k tokens of user messages) will fail without this. |
| **P2** | G4 — Visual style parity | Evaluate whether macOS window chrome (traffic-light dots, rounded corners) should be ported to Rich/SVG rendering, or if current Rich Panel style is sufficient. User preference decision. |
| **P3** | G6 — Configurable dimensions | Add `width`, `font_size` parameters to `render_rage_receipt` tool. |

### Already superior in `frustration-analyzer` (no action needed)

| Gap | Why it's fine |
|-----|--------------|
| G7 — MCP architecture | Core design advantage |
| G8 — `scan_transcripts` | Net-new capability |
| G9 — `generate_social_post` | Net-new capability |
| G11–G13 — SVG pipeline | Better than PIL for resolution independence and inline delivery |
| G16 — Test suite | Already exists |

### Post-consolidation: retire `rtfp` plugin

1. Verify all G1–G6 gaps are addressed in `frustration-analyzer`
2. Update marketplace.json — remove `rtfp` entry
3. Delete `plugins/rtfp/` directory
4. Update any backlog items referencing `rtfp` plugin paths

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Large session failure without token splitting (G1) | High — sessions routinely exceed 100k tokens | Pipeline produces incomplete results | Port tiktoken batching before retiring `rtfp` |
| Visual regression from rendering change (G4) | Medium — different rendering pipeline | User-facing aesthetic change | Side-by-side comparison before cutover |
| cairosvg system dependency | Low — requires libcairo | PNG rendering fails silently | Add fallback to SVG-only output with warning |
| fastmcp RC dependency | Medium — `>=3.0.0rc1` is pre-release | API breaking changes possible | Pin to specific RC or wait for stable release |
