# Feature Context: Add Status Field to BacklogItem Model

## Document Metadata

- **Generated**: 2026-03-12
- **Input Type**: simple_description
- **Source**: GitHub Issue #612, Code review 2026-03-11
- **Status**: DISCOVERY_COMPLETE

---

## Original Request

BacklogItem model (models.py:140) lacks a status field. The `view_result_from_local_item()` function in parsing.py must re-read the file from disk to extract status from frontmatter metadata, even though all other fields are already on the model. Add `status: str = ""` to BacklogItem and populate it during `parse_item_file()` to eliminate the redundant file read.

Acceptance criteria:
- BacklogItem has `status: str = ""` field
- `parse_item_file()` populates status from frontmatter `metadata.status`
- `view_result_from_local_item()` uses `item.status` instead of re-reading file
- All existing tests pass
- No behavioral changes to callers

---

## Core Intent Analysis

### WHO (Target Users)

Developers and agents that call `view_result_from_local_item()` or consume `BacklogItem` instances from `parse_item_file()`. This includes the backlog MCP server, CLI tool, and orchestration agents that query backlog item status.

### WHAT (Desired Outcome)

The `BacklogItem` model carries the `status` field in memory after parsing, eliminating a redundant disk read in `view_result_from_local_item()`. The status value (e.g., "open", "done", "resolved") is available on the model like every other frontmatter field.

### WHEN (Trigger Conditions)

Every time `view_result_from_local_item()` is called -- currently on every `backlog_view` operation. The redundant file read happens on each invocation because status is not on the model.

### WHY (Problem Being Solved)

1. **Redundant I/O**: `view_result_from_local_item()` (parsing.py:784-815) re-reads the file from disk, re-parses frontmatter, and extracts `metadata.status` -- even though `parse_item_file()` already parsed the same file and extracted all other fields.
2. **Inconsistency**: `parse_item_file()` already reads `status` from frontmatter (parsing.py:243) but only uses it to set the boolean `skip` field. The raw status string is discarded.
3. **Model incompleteness**: `BacklogItem` has fields for title, description, source, added, priority, issue, plan, groomed, last_synced, etc. -- but not status. This is the only frontmatter field that requires a separate file read to access.

---

## Codebase Research

### Similar Patterns Found

#### Pattern 1: Existing field population in parse_item_file

- **Location**: `.claude/skills/backlog/backlog_core/parsing.py:235-247`
- **Relevance**: `parse_item_file()` already extracts status via `_fm_str(fm, meta, "status")` on line 243, but only uses it for the `skip` boolean check (`.lower() in {"done", "resolved"}`). The raw status string value is computed but discarded.
- **Reusable**: The exact same `_fm_str(fm, meta, "status")` call already exists. The value just needs to be assigned to a new `status` field on `BacklogItem`.

#### Pattern 2: The redundant file read in view_result_from_local_item

- **Location**: `.claude/skills/backlog/backlog_core/parsing.py:805-814`
- **Relevance**: Lines 806-814 re-read the file, re-parse frontmatter, and extract `metadata.status` -- the exact code that becomes unnecessary once `item.status` is populated during parsing. This is the code to be replaced with `result.status = item.status`.
- **Reusable**: The comment on line 805 (`# status is not on BacklogItem`) documents the gap explicitly.

#### Pattern 3: Legacy script has the same gap

- **Location**: `.claude/skills/backlog/scripts/backlog.py:1868` (`_view_result_from_local_item` function)
- **Relevance**: The legacy CLI script (`backlog.py`) has its own copy of this function using untyped dicts. It may have the same redundant read pattern. This is a separate concern but worth noting for completeness.

### Existing Infrastructure

- `BacklogItem` (models.py:140-166) is a Pydantic `BaseModel` with 16 fields, all defaulting to empty/falsy values.
- `parse_item_file()` (parsing.py:220-247) is the single entry point for parsing per-item backlog files. All fields on `BacklogItem` are populated here.
- `_fm_str()` helper (parsing.py:191-197) resolves string fields from metadata with frontmatter fallback -- already used for status extraction.
- `ViewItemResult` (models.py:212-230) already has a `status: str = ""` field -- the target model for the view layer.

### Code References

- `models.py:140-166` - BacklogItem class definition, missing status field
- `parsing.py:220-247` - parse_item_file function, already extracts status but discards it
- `parsing.py:243` - `skip=_fm_str(fm, meta, "status").lower() in {"done", "resolved"}` -- status extracted here
- `parsing.py:784-815` - view_result_from_local_item, contains redundant file read
- `parsing.py:805-814` - The specific block that re-reads file to get status
- `operations.py:1196` - Caller of view_result_from_local_item
- `tests/test_backlog_core_parsing.py:1072-1148` - Existing tests for view_result_from_local_item

---

## Use Scenarios

### Scenario 1: Viewing a Backlog Item

**Actor**: Developer or agent calling `backlog_view`
**Trigger**: Running `backlog view "some item"` or calling `mcp__backlog__backlog_view`
**Goal**: See all item details including status
**Expected Outcome**: Status is returned in the view result without any redundant file I/O. The `BacklogItem` parsed during initial load already carries the status value.

### Scenario 2: Filtering or Querying by Status

**Actor**: Agent or script iterating over parsed backlog items
**Trigger**: Calling `parse_backlog()` or `parse_backlog_from_directory()` to get all items
**Goal**: Access `item.status` on each `BacklogItem` without additional file reads
**Expected Outcome**: Each `BacklogItem` in the returned list has its `status` field populated from frontmatter metadata (e.g., "open", "done", "resolved", "in-progress").

### Scenario 3: Backward Compatibility

**Actor**: Any existing caller of `parse_item_file()` or `view_result_from_local_item()`
**Trigger**: Existing code paths that consume BacklogItem or ViewItemResult
**Goal**: No behavioral change -- same outputs, same field values
**Expected Outcome**: The `skip` field continues to work identically. The new `status` field defaults to `""` so items parsed from files without frontmatter are unaffected. `view_result_from_local_item()` returns the same `ViewItemResult` with the same `status` value -- just sourced from the model instead of a file re-read.

---

## Gap Analysis

### Identified Gaps

| # | Category | Gap Description | Impact |
|---|----------|-----------------|--------|
| 1 | Scope | Legacy `backlog.py` script (line 1868) has its own `_view_result_from_local_item` using untyped dicts -- unclear if it needs the same fix | Inconsistency between core module and legacy script |
| 2 | Behavior | `parse_item_file()` line 243 already computes status but only for the `skip` check -- should the new `status` field store the raw string or normalized (lowercased) value? | Downstream consumers may expect specific casing |
| 3 | Integration | The `skip` field derives from status (`done`/`resolved` -> `skip=True`). With status now on the model, should `skip` become a computed property instead of a stored field? | Scope creep risk, but worth flagging for future cleanup |

---

## Questions Requiring Resolution

### Q1: Should the legacy backlog.py script be updated too?

- **Category**: Scope
- **Gap**: `.claude/skills/backlog/scripts/backlog.py:1868` has `_view_result_from_local_item()` using untyped dicts. It may have the same redundant file read.
- **Question**: Is the legacy `backlog.py` script in scope for this change, or should it be a separate follow-up?
- **Options**:
  - A) In scope -- fix both core module and legacy script
  - B) Out of scope -- create a separate backlog item for the legacy script
- **Why It Matters**: The legacy script is a parallel implementation. Fixing only the core module leaves inconsistency.
- **Resolution**: _pending_

### Q2: Should status store raw or normalized value?

- **Category**: Behavior
- **Gap**: `parse_item_file()` line 243 lowercases status for the `skip` check. The frontmatter may contain "Open", "Done", "RESOLVED" etc. The re-read in `view_result_from_local_item` (line 814) stores whatever `meta.get("status")` returns (not lowercased).
- **Question**: Should `BacklogItem.status` store the raw frontmatter value (preserving case) or a normalized lowercase value?
- **Options**:
  - A) Raw value (matches current view_result_from_local_item behavior)
  - B) Normalized lowercase (matches how skip uses it)
- **Why It Matters**: Callers comparing status strings need consistent casing. Current behavior in `view_result_from_local_item` preserves raw case.
- **Resolution**: _pending_

---

## Goals (Pending Resolution)

_These goals will be finalized after questions are resolved._

1. Add `status: str = ""` field to `BacklogItem` model
2. Populate `status` in `parse_item_file()` from frontmatter metadata
3. Simplify `view_result_from_local_item()` to use `item.status` instead of re-reading file
4. Maintain backward compatibility -- no behavioral changes to callers
5. All existing tests pass; new tests cover the status field population

---

## Next Steps

After questions are resolved:

1. Update "Resolution" fields in Questions section
2. Finalize Goals section
3. Proceed to RT-ICA assessment
4. Then proceed to architecture design

---

## Post-Implementation Annotations

_Added by context-refinement agent on 2026-03-12_

### Design Refinements

1. **`view_result_from_local_item()` full function cleanup**: The implementation simplified the entire function body rather than making only the minimal splice described in the original request. The result is a flat sequence of field assignments with no conditional blocks or file I/O.
   - Original: "Replace `view_result_from_local_item()` file re-read block with `result.status = item.status`"
   - Actual: The entire function was rewritten as a clean flat assignment block — `ViewItemResult(...)` constructor plus direct `item.*` assignments for description, source, added, raw_body, and status. No file I/O anywhere in the function.
   - Recorded in: plan/tasks-1-add-status-field-to-backlogitem-model.md

2. **Legacy script left unchanged (best-effort path taken)**: The `_status` key is not present on item dicts in `backlog.py`'s untyped parse path, so the file re-read in `_view_result_from_local_item()` was retained with a `# TODO(#612)` comment. Q1 ("Should the legacy backlog.py script be updated too?") resolved as: partial — comment added, full fix deferred.
   - Original: "Q1 resolution: pending"
   - Actual: Legacy function unchanged; `# TODO(#612): status not available on item dict; re-read still needed` comment added at backlog.py line 1894
   - Recorded in: plan/tasks-1-add-status-field-to-backlogitem-model.md

3. **Q2 resolved as raw case preservation**: The `status` field stores the raw frontmatter value without lowercasing, matching the existing behavior of the old file re-read path.
   - Original: "Q2 resolution: pending"
   - Actual: `status=status_raw` (no `.lower()`); `skip=status_raw.lower() in {"done", "resolved"}` — separation preserved
   - Recorded in: plan/tasks-1-add-status-field-to-backlogitem-model.md
