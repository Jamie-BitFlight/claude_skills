---
name: backlog_view offset/limit operates on body lines not entry blocks
description: The `backlog_view` tool's `offset` and `limit` parameters paginate raw body lines rather than entry blocks as the timestamped entry blocks spec (#583) intended. The spec designed offset/limit to let callers navigate entry blocks atomically — e.g., 'show entries 5–10' — so that a partial read never splits an entry mid-block. The current line-based pagination can cut through entry block HTML structure, producing malformed output for callers trying to paginate through a section's entries.
metadata:
  topic: backlogview-offsetlimit-operates-on-body-lines-not-entry-blo
  source: 'Spec gap discovered during #583 (Backlog MCP: Timestamped entry blocks) resolution — feature-researcher audit 2026-03-14'
  added: '2026-03-14'
  priority: completed
  type: Bug
  status: done
  issue: '#695'
  last_synced: '2026-03-14T04:50:39Z'
  groomed: '2026-03-14'
  plan: plan/tasks-695-backlog-view-entry-pagination.md
---

## Groomed (2026-03-14)

### Groomed

<div><sub>2026-03-14T04:50:39Z</sub>

### Reproducibility

1. Create a backlog item with a section containing two or more entry blocks (each block is a `<div><sub>timestamp</sub>\n\ncontent\n</div>` spanning multiple lines).
2. Call `backlog_view` with `offset=1` and `limit=5` on that item.
3. Observe: the returned `body` field begins mid-entry-block — e.g., the `<div>` opener or `<sub>` tag is present but the closing `</div>` is cut off, or the block starts mid-paragraph.
4. Confirm: the `sections` metadata correctly counts entries (entry-aware), but the `body` text returned is structurally broken.

### Output / Evidence

- `body` field in `backlog_view` response contains truncated HTML entry block structure when `offset > 0` or `limit > 0`.
- Callers attempting to re-parse the paginated body into entry blocks via `parse_entries()` receive malformed or missing entries.
- The `sections` key in the response IS entry-aware (computed before pagination) but `body` is not — the two are inconsistent.

### Priority

5/10 — The mismatch between the spec intent and the implementation is confirmed. The `show`/`since` parameters already provide entry-aware filtering; `offset`/`limit` remaining line-based means callers who depend on them for structural pagination get broken output. Severity is bounded because `show` and `since` cover the primary use case, but the documented API contract (from #583) is not met.

### Impact

- Blocks: Any caller using `offset`/`limit` on items with entry blocks gets structurally broken body text.
- Bottleneck: The `_paginate_body` function in `operations.py` — it splits on newlines unconditionally, unaware of block boundaries.

### Benefits

- `backlog_view` returns structurally valid body text at all offsets and limits.
- `offset`/`limit` become meaningful for callers paginating through large items with many entry blocks.
- The `body` field and `sections` metadata are consistent — both entry-aware.
- Meets the contract specified in #583 ("Pagination Change" section): entry-based, not line-based.

### Expected Behavior

When `offset=N` and `limit=M` are passed to `backlog_view`, the returned `body` contains a contiguous slice of N-through-(N+M) complete entry blocks — no block is split mid-structure. Non-entry content (section headers, legacy lines outside blocks) is treated as atomic units. The `body_total_lines` / `body_remaining_lines` response fields should report in entry-block units, not raw lines.

### Desired Structure

- `_paginate_body` in `operations.py` is replaced or superseded by an entry-block-aware pagination path.
- Entry blocks are parsed atomically via `parse_entries()` before slicing by offset/limit.
- `body_total_lines`, `body_remaining_lines`, and `body_truncated` in the response report block counts, not line counts (or the field names are updated to reflect block-based units).
- The `sections` metadata and the paginated `body` text remain structurally consistent — a caller can re-parse the returned `body` and get the same entry count as `sections[name].num_entries`.

### Acceptance Criteria

1. Call `backlog_view` with `offset=1, limit=1` on an item with 3+ entry blocks in a section; the returned `body` contains exactly one complete `<div>...</div>` entry block with no truncated HTML.
2. Call `backlog_view` with `offset=0, limit=0` (unlimited); returned `body` is identical to calling without offset/limit (no regression).
3. Call `backlog_view` on an item with legacy (non-entry-block) content plus one entry block; the call does not raise an exception and the entry block is returned intact when it falls within the requested window.
4. `body_remaining_lines` in the response, when present, accurately reflects how many entry blocks remain after the returned window (verifiable by fetching the next page and counting blocks).
5. `parse_entries(result["body"])` returns the same entries as `result["sections"][section_name]["entries"]` for the paginated window.

### Resources

| Type | Item |
|------|------|
| Prior work | `.claude/skills/backlog/backlog_core/operations.py` — `_paginate_body()` (line 1159), `view_item()` (line 1187), `_build_sections_metadata()` (line 1114) |
| Prior work | `.claude/skills/backlog/backlog_core/entry_blocks.py` — `parse_entries()` and entry block regex |
| Prior work | `.claude/skills/backlog/backlog_core/server.py` — `backlog_view` tool definition (line 109), `offset`/`limit` parameter descriptions |
| Prior work | `.claude/skills/backlog/tests/test_entry_blocks.py` — existing entry block unit tests |
| Prior work | `.claude/skills/backlog/tests/test_entry_blocks_integration.py` — integration tests |
| Spec | #583 "Pagination Change" section: entry-based offset/limit was the stated intent |

### Dependencies

- Depends on: #583 (closed — entry block implementation complete; this item addresses the remaining gap in `backlog_view` pagination)
- Blocks: None identified

### Blockers

None. All code paths are in-repo. The entry block parser (`parse_entries`) and the entry block regex (`ENTRY_RE`) already exist in `entry_blocks.py`. The fix scope is confined to `_paginate_body` and `view_item` in `operations.py`, plus corresponding `backlog_view` parameter description updates in `server.py`.

### Effort

Small — `_paginate_body` is a self-contained helper (~20 lines). Replacing line-based slicing with entry-block-aware slicing using the existing `parse_entries()` function is the core change. Test coverage exists in `test_entry_blocks.py` and `test_entry_blocks_integration.py` — new test cases for paginated `backlog_view` are additive.
</div>