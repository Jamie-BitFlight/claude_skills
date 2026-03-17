# Plan: backlog_pull single-item path does not return diff output

**Fixes**: #694
**Effort**: Small
**Stack**: Python, FastMCP, backlog_core

## Root Cause (from groomer)

Three gaps in two files:

1. `backlog_core/operations.py` line ~1802 — `pull_single_issue` has no `diff_mode` parameter and never calls `generate_diff`
2. `backlog_core/operations.py` line ~1869 — `pull_by_selector` has no `diff` parameter and never calls `generate_diff`
3. `backlog_core/server.py` line ~454 — `backlog_pull` handler already accepts `diff` argument but does not forward it to `pull_by_selector`

The bulk path (`pull_items` → `_pull_item` → `_pull_item_update_existing`) already implements the full diff pattern with `generate_diff`. The fix threads `diff_mode` through the single-item call chain and returns `result["diff"]` from the server handler.

## Files to change

- `.claude/skills/backlog/backlog_core/operations.py`
- `.claude/skills/backlog/backlog_core/server.py`
- `.claude/skills/backlog/tests/test_backlog_core_server.py` (or relevant test file)

---

## Task 1.1: Add diff_mode to pull_single_issue

**Status**: NOT STARTED
**Priority**: 1
**Complexity**: Low
**Agent**: python-cli-architect
**Dependencies**: none

**Acceptance criteria**:

- `pull_single_issue` in `operations.py` gains `diff_mode: bool = False` parameter
- When `diff_mode=True`, calls `generate_diff` on old vs new content and includes result in return value under `"diff"` key
- When `diff_mode=False`, behaviour is identical to current (no diff computed)
- Existing callers pass no argument and are unaffected

---

## Task 1.2: Add diff parameter to pull_by_selector

**Status**: NOT STARTED
**Priority**: 1
**Complexity**: Low
**Agent**: python-cli-architect
**Dependencies**: Task 1.1

**Acceptance criteria**:

- `pull_by_selector` in `operations.py` gains `diff: bool = False` parameter
- Passes `diff_mode=diff` to `pull_single_issue`
- Returns `"diff"` key from `pull_single_issue` result when present

---

## Task 1.3: Forward diff argument in server handler

**Status**: NOT STARTED
**Priority**: 1
**Complexity**: Low
**Agent**: python-cli-architect
**Dependencies**: Task 1.2

**Acceptance criteria**:

- `backlog_pull` handler in `server.py` passes its `diff` argument to `pull_by_selector`
- When `diff=True` and diff output is non-empty, includes `"diff"` in the tool response
- When `diff=False` (default), response is identical to current

---

## Task 1.4: Add tests for single-item diff output

**Status**: NOT STARTED
**Priority**: 2
**Complexity**: Low
**Agent**: python-cli-architect
**Dependencies**: Task 1.3

**Acceptance criteria**:

- Test: `backlog_pull` with `diff=True` on a single item that has changed content returns non-empty `"diff"` field
- Test: `backlog_pull` with `diff=False` (default) returns no `"diff"` field (no regression)
- All 582+ existing tests continue to pass
