---
feature: backlog-view-entry-pagination
fixes: '#695'
effort: small
stack: Python, FastMCP, backlog_core
---

## Root Cause

`_paginate_body` in `operations.py` calls `body.splitlines()` unconditionally and slices the resulting line array. Entry blocks are multi-line HTML structures — a line-based slice cuts through them arbitrarily.

The `show`/`since` parameters on the same `backlog_view` tool ARE correctly entry-aware (via `_build_sections_metadata` → `parse_entries`). `offset`/`limit` are the only parameters still operating on lines.

`parse_entries` in `entry_blocks.py` already exists and correctly parses entry blocks from section content.

## Files to change

- `.claude/skills/backlog/backlog_core/operations.py` — `_paginate_body`, `view_item`
- `.claude/skills/backlog/backlog_core/server.py` — `backlog_view` parameter docstrings for `offset`/`limit`
- `.claude/skills/backlog/tests/test_entry_blocks.py` or `test_entry_blocks_integration.py`

---

---
task: '2.1'
title: Replace _paginate_body with entry-aware pagination
status: complete
agent: python-cli-architect
priority: 1
complexity: low
started: "2026-03-14T15:33:07Z"
completed: "2026-03-14T15:36:30Z"
---

**Acceptance criteria**:

- `_paginate_body` (or its replacement) uses `parse_entries` to split body into entry blocks before slicing
- `offset=N` skips the first N entry blocks (not lines)
- `limit=N` returns at most N entry blocks (not lines)
- A body with no entry blocks falls back to line-based pagination (backward compatibility for non-entry content)
- Result is concatenated entry block text (not a list), so callers receive a string as before

---

---
task: '2.2'
title: Update server docstrings for offset/limit
status: complete
agent: python-cli-architect
dependencies:
- '2.1'
priority: 2
complexity: low
started: "2026-03-14T15:37:01Z"
completed: "2026-03-14T15:39:30Z"
---

**Acceptance criteria**:

- `backlog_view` tool in `server.py` — `offset` docstring updated from "body lines" to "entry blocks"
- `backlog_view` tool in `server.py` — `limit` docstring updated from "body lines" to "entry blocks"
- No functional changes in this task

---

---
task: '2.3'
title: Add tests for entry-based pagination
status: complete
agent: python-cli-architect
dependencies:
- '2.1'
priority: 2
complexity: low
started: "2026-03-14T15:37:07Z"
completed: "2026-03-14T15:40:15Z"
---

**Acceptance criteria**:

- Test: body containing 5 entry blocks with `offset=2, limit=2` returns blocks 3 and 4 intact (not split)
- Test: body with no entry blocks with `offset=1, limit=2` falls back to line-based behaviour (no regression)
- Test: entry block boundary is never broken mid-block by pagination
- All 582+ existing tests continue to pass

---

## Context Manifest

### Discovered During Implementation

_Session Date: 2026-03-14_

During implementation, we discovered that `parse_entries` and `ENTRY_RE` from `entry_blocks.py` were already imported into `operations.py` (lines 18–24) and could be called directly inside `_paginate_body` with no new parsing logic required. The existing import was sufficient — no new module, function, or utility needed to be written.

The grooming output for #695 stated that `body_remaining_lines` should "report in entry-block units." The implementation chose a different key — `body_remaining_entries` — for the entry-aware path, while preserving `body_remaining_lines` for the line-based fallback path. This produces two distinct keys depending on whether entry blocks were detected, which is a cleaner API contract than reusing the same key with changed semantics.

A pre-existing, independent line-based pagination path exists in `scripts/backlog.py` (the CLI layer). This path is separate from `operations.view_item` and was explicitly left out of scope — it operates only when the CLI is invoked directly, not through the MCP server.

**Key Discoveries:**

1. **`parse_entries` reuse — no new parsing code needed**: `parse_entries` was already imported in `operations.py` at the time of this fix. Future implementations that need entry-block awareness inside `operations.py` can call it directly without adding imports.

2. **Distinct response keys for entry-based vs line-based pagination**: The implementation returns `body_remaining_entries` (int) when the body contains entry blocks, and `body_remaining_lines` (int) when it falls back to line-based pagination. These are mutually exclusive in a given response. Callers can use key presence to detect which mode was active.

3. **CLI pagination is a separate, unrelated code path**: `scripts/backlog.py` contains its own line-based slice logic distinct from `operations._paginate_body`. Fixing `_paginate_body` has no effect on CLI invocations. The CLI path was out of scope and remains line-based.

#### Updated Technical Details

- `_paginate_body` signature: `(data: dict, body: str, offset: int, limit: int) -> None` — mutates `data` in-place, unchanged
- Entry-aware path: calls `parse_entries(body, show="all")`, slices the resulting list, joins back to string; sets `data["body_remaining_entries"]`
- Line-based fallback path: original `body.splitlines()` slice logic; sets `data["body_remaining_lines"]`
- Fallback trigger: `parse_entries` returns an empty list (no entry blocks detected in body)

#### Gotchas for Future Developers

- Do not assume `body_remaining_lines` is always present in a `backlog_view` response — it is absent when the entry-based path runs. Check for `body_remaining_entries` first.
- The CLI path in `scripts/backlog.py` does not share `_paginate_body`. Changes to entry-based pagination in `operations.py` will not propagate to the CLI automatically.
