# Feature Context: Backlog MCP Timestamped Entry Blocks

## Document Metadata

- **Generated**: 2026-03-14
- **Input Type**: existing_document
- **Source**: `docs/superpowers/specs/2026-03-10-backlog-mcp-timestamped-entry-blocks-design.md` + `docs/superpowers/plans/2026-03-10-backlog-mcp-timestamped-entry-blocks.md`
- **GitHub Issue**: #583
- **Status**: DISCOVERY_COMPLETE — feature is **fully implemented**

---

## Original Request

Add timestamped, addressable entry blocks to backlog GitHub issue section content. Each piece of section content is wrapped in `<div><sub>ISO-timestamp</sub>` blocks. Entries are never deleted — they are struck through with a reason and collapsed. Multiple updates to the same section append new blocks rather than silently replacing previous content.

---

## Core Intent Analysis

### WHO (Target Users)

Agents (orchestrator and subagents) that call `backlog_update` / `backlog_groom` to add grooming notes, decisions, analysis, or investigation results to backlog items. Human reviewers auditing the history of a backlog item's decision trail.

### WHAT (Desired Outcome)

Every write to a backlog item section produces a timestamped, uniquely addressable entry block. The full history of a section is preserved — earlier entries remain accessible (in struck/collapsed form). Agents can target specific entries by ID for overwrite. Sections can be fully replaced with a reason recorded.

### WHEN (Trigger Conditions)

- Agent calls `backlog_update(section="...", content="...")` — new entry appended
- Agent calls `backlog_groom(section="...", content="...", entry_id="...")` — specific entry overwritten
- Agent calls `backlog_strike_entry(entry_id="...")` — entry struck (retracted with reason)
- Agent calls `backlog_view(show="last", since="2026-03-10")` — filtered view of entries
- Agent calls `backlog_pull(diff=True)` — merge from GitHub with entry-level diff

### WHY (Problem Being Solved)

Before this feature, `backlog_update` and `backlog_groom` silently replaced section content on each call — no timestamp, no audit trail, no way to see what changed or when. A grooming session could destroy prior analysis with no record. The feature ensures every write is auditable and no content is permanently lost.

---

## Codebase Research

### Implementation Status

All 15 tasks in the plan are checked `[x]`. The full test suite passes: **582 tests, 0 failures** (verified 2026-03-14 via `uv run pytest .claude/skills/backlog/tests/`).

### Similar Patterns Found

#### Pattern 1: Pydantic BaseModel throughout backlog_core

- **Location**: `.claude/skills/backlog/backlog_core/models.py:130-138`
- **Relevance**: `Entry` model is a Pydantic `BaseModel` consistent with all other models in the package (`BacklogItem`, `Output`, `ViewItemResult`, `SamTask`). The new `sections` field on `ViewItemResult` (line 232) follows the same pattern.
- **Reusable**: The `Output` model for collecting messages/warnings is already wired into all operations.

#### Pattern 2: FastMCP `asyncio.to_thread` dispatch in server.py

- **Location**: `.claude/skills/backlog/backlog_core/server.py:580-604`
- **Relevance**: `backlog_strike_entry` follows the exact same pattern as all other tools — `asyncio.to_thread(operations.strike_entry, ...)` wrapped in try/except returning `{"error": ...}` on `BacklogError`.
- **Reusable**: Pattern is consistent throughout; no deviation.

#### Pattern 3: Regex-based section parsing in parsing.py

- **Location**: `.claude/skills/backlog/backlog_core/parsing.py:28-29`
- **Relevance**: `ENTRY_RE` and `STRUCK_RE` in `entry_blocks.py` extend the existing regex pattern approach used for `SECTION_RE` and `GITHUB_ISSUE_URL_RE` in `models.py`.
- **Reusable**: `now_iso()` from `parsing.py` is imported into `entry_blocks.py` for timestamp generation.

### Existing Infrastructure

The feature is wired into the existing infrastructure at every layer:

- `operations.py` imports `rewrite_section`, `parse_entries`, `strike_entry_block`, `generate_diff`, `ENTRY_RE` from `entry_blocks.py` (lines 18-24)
- `groom_item()` and `update_item()` in `operations.py` accept `entry_id`, `replace_section`, `reason` params and pass them through to `rewrite_section()`
- `view_item()` builds `sections` metadata with `num_entries`, `num_struck`, `entries` list per-section
- `pull_items()` uses `generate_diff()` for entry-level merge output
- `operations.strike_entry()` locates a specific entry by ID in the raw file text and rewrites it

### Code References

- `.claude/skills/backlog/backlog_core/entry_blocks.py:1-293` — full module: `wrap_entry`, `wrap_entry_with_timestamp`, `parse_entries`, `strike_entry`, `rewrite_section`, `generate_diff`, internal helpers
- `.claude/skills/backlog/backlog_core/models.py:130-138` — `Entry` model
- `.claude/skills/backlog/backlog_core/models.py:214-232` — `ViewItemResult.sections` field
- `.claude/skills/backlog/backlog_core/server.py:271-337` — `backlog_update` with `entry_id`, `replace_section`, `reason`
- `.claude/skills/backlog/backlog_core/server.py:340-390` — `backlog_groom` with same params
- `.claude/skills/backlog/backlog_core/server.py:580-604` — `backlog_strike_entry` tool
- `.claude/skills/backlog/tests/test_entry_blocks.py:1-392` — 35 unit tests covering all functions
- `.claude/skills/backlog/tests/test_entry_blocks_integration.py:1-75` — lifecycle integration test

---

## Use Scenarios

### Scenario 1: Agent appends grooming notes over multiple sessions

**Actor**: Orchestrator agent
**Trigger**: Multiple grooming sessions on the same backlog item over days
**Goal**: Each session's analysis is preserved, not overwritten
**Expected Outcome**: `backlog_view(selector="#583", show="all")` returns all entries in chronological order; `show="last"` returns only the most recent

### Scenario 2: Agent retracts a decision that was based on wrong information

**Actor**: Agent that discovers prior analysis was incorrect
**Trigger**: New evidence contradicts an existing entry
**Goal**: Retract the entry with an explanation, keep the original for audit
**Expected Outcome**: `backlog_strike_entry(selector="#583", entry_id="2026-03-10T22:18:04Z", reason="based on incorrect assumption")` — entry becomes collapsed `<details>` block, visible but not active

### Scenario 3: Full section replacement during re-grooming

**Actor**: Agent that needs to discard all prior analysis and start fresh
**Trigger**: Significant scope change makes prior entries misleading
**Goal**: Strike all existing entries with a reason, write new content
**Expected Outcome**: `backlog_groom(selector="#583", section="Decision", content="New analysis.", replace_section=True, reason="scope changed after user clarification")` — all prior entries struck, one new active entry

### Scenario 4: Pull from GitHub with diff review

**Actor**: Orchestrator checking for remote changes
**Trigger**: Remote GitHub issue body may have been updated by another agent or human
**Goal**: Merge remote changes without losing local entries
**Expected Outcome**: `backlog_pull(selector="#583", diff=True)` returns merge result plus entry-level diff showing which entries were added, kept, or differed

---

## Gap Analysis

### Identified Gaps

All gaps from the spec are resolved. The implementation is complete. The following observations are relevant for any future work:

| # | Category | Observation | Impact |
|---|----------|-------------|--------|
| 1 | Behavior | Duplicate-timestamp suffix deduplication is parse-time only (not write-time) — two entries written at the same second get `T08:00:00Z-0`, `-1` IDs assigned at parse, not stored literally | The raw file always stores the bare timestamp; `strike_entry` in operations.py locates entries by position-count match, which handles this correctly |
| 2 | Behavior | `groomed_content` parameter was removed from `backlog_update` and `backlog_groom` per spec — this is a breaking API change for any caller using the old parameter name | No callers using `groomed_content` were found in the codebase; the old parameter was the predecessor to `section`+`content` |
| 3 | Integration | `backlog_pull` `diff` parameter is supported in `pull_items()` (bulk pull) but `pull_by_selector()` (single-item pull) does not currently expose `diff` | `diff=True` with a `selector` falls through to `pull_by_selector()` which does not return diff output |

---

## Questions Requiring Resolution

No questions requiring user input were identified. The spec is approved, the design is fully articulated, and the implementation is complete and passing.

---

## Goals (Resolved)

1. Every write to a backlog section produces a uniquely addressable, timestamped entry block — **DONE**
2. Entries are never deleted; struck entries preserve original content in a collapsed `<details>` block — **DONE**
3. `backlog_view` returns per-section entry metadata (`num_entries`, `num_struck`, entries list) — **DONE**
4. `backlog_strike_entry` MCP tool allows targeted retraction of a specific entry — **DONE**
5. `backlog_pull` performs entry-aware merge (keeps longer, preserves strikes) with optional diff output — **DONE**
6. Legacy section content (unwrapped plain text) is auto-migrated to an entry block on first append — **DONE**
7. `backlog_update` and `backlog_groom` expose `entry_id`, `replace_section`, `reason` params — **DONE**
8. CLI (`scripts/backlog.py`) has parity with all MCP tool changes — **DONE**

---

## Implementation Completeness

The feature is **fully implemented**. All 15 plan tasks are complete, all 582 tests pass, and all spec-described behaviors are wired into `entry_blocks.py`, `models.py`, `operations.py`, `server.py`, and `scripts/backlog.py`.

The one observable divergence from the spec: `backlog_view` pagination via `offset`/`limit` was not changed to entry-based (it remains line-based). The `show`/`since` entry filter parameters were added as a complement. This divergence is not flagged in the plan and may warrant a follow-up task if entry-based pagination for `offset`/`limit` is still desired.

---

## Next Steps

No implementation steps remain. If proceeding to architecture review:

1. Confirm whether entry-based `offset`/`limit` in `backlog_view` is still required (vs. the existing `show`/`since` filters)
2. Confirm whether `pull_by_selector` (single-item pull) should also support `diff=True`
3. Proceed directly to code review or `/complete-implementation` quality gates

---

## Post-Implementation Annotations

_Added by context-refinement agent on 2026-03-14_

### Design Refinements

1. **Entry-based `offset`/`limit` pagination now implemented**: The divergence noted in "Implementation Completeness" (line 161) — that `backlog_view` `offset`/`limit` remained line-based — is resolved. Issue #695 was created, groomed, and implemented. `_paginate_body` in `operations.py` now calls `parse_entries` to detect entry blocks and slices them atomically before falling back to line-based behaviour.
   - Original: "`backlog_view` pagination via `offset`/`limit` was not changed to entry-based (it remains line-based)."
   - Actual: Entry-aware path added. Non-entry bodies still use line-based fallback. Two distinct response keys: `body_remaining_entries` (entry-aware path) and `body_remaining_lines` (line-based fallback).
   - Recorded in: `plan/tasks-695-backlog-view-entry-pagination.md`

2. **Response key renamed rather than repurposed**: The grooming output for #695 stated `body_remaining_lines` "should report in entry-block units." The implementation uses a new key `body_remaining_entries` instead of changing the semantics of `body_remaining_lines`. This avoids a silent breaking change for callers that already consume `body_remaining_lines` expecting line counts.
   - Original plan: "The `body_total_lines` / `body_remaining_lines` response fields should report in block-based units"
   - Actual: `body_remaining_entries` is a new key; `body_remaining_lines` retains its original line-based meaning on the fallback path.
   - Recorded in: `plan/tasks-695-backlog-view-entry-pagination.md`
