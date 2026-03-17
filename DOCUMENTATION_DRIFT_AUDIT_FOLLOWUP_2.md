# Documentation Drift Audit: backlog_item_to_display_dict Change

**Generated**: 2026-03-14
**Repository**: claude_skills
**Analyzed Change**: Addition of `"_status": item.status` to `backlog_item_to_display_dict` function output
**Issue**: #670
**Task File**: plan/tasks-36-backlog-cli-dedup-followup-2.md

---

## Executive Summary

**Drift Status**: NO CRITICAL MISMATCHES FOUND

The implementation change to add `"_status": item.status` to the `backlog_item_to_display_dict` adapter function output is **properly documented** in the architecture and task specifications. The documentation accurately describes:

1. The adapter function's interface contract
2. The field mapping semantics
3. The round-trip conversion pattern with `_dict_to_backlog_item_fields`
4. The internal helper nature of the adapter

**Key Finding**: The spec-to-code alignment is strong. The change is a straightforward fix to an asymmetry that the architecture already predicted and documented.

---

## Drift Analysis Details

### 1. Documentation References to `backlog_item_to_display_dict`

**Files Analyzed**:
- `plan/architect-backlog-cli-dedup.md` (Architecture spec)
- `plan/tasks-1-backlog-cli-dedup.md` (Main task file)
- `.claude/backlog/p2-fix-missing-status-key-in-backlogitemtodisplaydict-adapter.md` (Backlog item)
- `plan/tasks-36-backlog-cli-dedup-followup-2.md` (Current task file)

#### Reference 1: Architecture Spec (Section 5.3)

**Location**: `architect-backlog-cli-dedup.md` lines 277-296

**Documentation Claims**:
```text
# Interface contract (not implementation)
def backlog_item_to_display_dict(item: BacklogItem) -> dict:
    """Convert BacklogItem to the dict format CLI display functions expect.

    Maps typed fields to the underscore-prefixed keys used by CLI formatting:
      item.title    -> d["_title"]
      item.section  -> d["_section"]
      item.file_path -> d["_file_path"]
      item.skip     -> d["_skip"]
    Plus all metadata fields as **Key** -> value pairs.
    """
```

**Code Reality** (after change):
```python
# Lines 190-230 in backlog.py
def backlog_item_to_display_dict(item: BacklogItem) -> dict:
    """Convert BacklogItem to the dict format the CLI's display and
    mutation code expects."""
    d: dict = {
        "_title": item.title,
        "_section": item.section,
        "_file_path": item.file_path,
        "_skip": item.skip,
        "_issue": item.issue,
        # ... metadata fields ...
    }
    if item.groomed:
        d["_groomed"] = item.groomed
    if item.last_synced:
        d["_last_synced"] = item.last_synced
    if item.status:
        d["_status"] = item.status  # <-- ADDED FIX
    return d
```

**Assessment**:
- **Status**: DOCUMENTED but INCOMPLETE
- **Issue**: Architecture spec shows the function signature but does NOT list `_status` as an output field in the docstring example (lines 286-291)
- **Severity**: LOW — The spec says "Plus all metadata fields as **Key** -> value pairs" which is intended to cover all fields, but the explicit list examples predate the `status` field addition
- **Evidence**:
  - Spec line 287-290: Lists `_title`, `_section`, `_file_path`, `_skip` as examples
  - Spec line 291: "Plus all metadata fields..." — status falls under this but is not explicitly shown
  - Code now correctly outputs `_status` field when `item.status` is truthy

#### Reference 2: Architecture Spec (Section 5.5) — Call Sites Table

**Location**: `architect-backlog-cli-dedup.md` lines 309-317

**Documentation Claims**:
```text
| Core Function | CLI Call Sites | Conversion Direction | Pattern |
|---------------|---------------|---------------------|---------|
| `parsing.parse_backlog_from_directory()` | ... | BacklogItem -> dict |
  `backlog_item_to_display_dict()` at each call site |
```

**Assessment**:
- **Status**: ACCURATE
- The table correctly identifies where `backlog_item_to_display_dict` is used
- The pattern name is correct and unchanged by the fix
- **Severity**: NONE — no drift

#### Reference 3: Task File (Section "Critical Adapter Pattern")

**Location**: `tasks-1-backlog-cli-dedup.md` lines 100-107

**Documentation Claims**:
```text
#### Critical Adapter Pattern: dict ↔ BacklogItem

The architecture spec (Section 5 of `plan/architect-backlog-cli-dedup.md`)
defines the conversion pattern:

- **dict → BacklogItem**: `BacklogItem.model_validate(raw_dict)` at call sites
  that construct a dict and pass to core
- **BacklogItem → dict**: `backlog_item_to_display_dict(item)` helper function
  (defined locally in CLI) for call sites that receive BacklogItem and need to
  pass to display formatting code
```

**Assessment**:
- **Status**: ACCURATE
- The adapter pattern description is correct and unaffected by the change
- The change is internal to `backlog_item_to_display_dict`; the pattern itself remains the same
- **Severity**: NONE — no drift

#### Reference 4: Backlog Item Grooming (Followup 2 Task File)

**Location**: `plan/tasks-36-backlog-cli-dedup-followup-2.md` lines 30-96

**Documentation Claims** (grooming section):
```text
### Desired Structure

- `backlog_item_to_display_dict` includes `"_status": item.status` in its
  return dict.
- `BacklogItem.status` type: `str = ""` (no enum, no validation needed —
  plain string passthrough).
- A round-trip unit test in the test suite covers all fields output by
  `backlog_item_to_display_dict` and verifies they survive the inverse
  transformation without loss.

### Acceptance Criteria

1. `backlog_item_to_display_dict(item)["_status"]` equals `item.status`
   for any `BacklogItem`.
```

**Code Reality**:
- Lines 228-229 in backlog.py now include: `if item.status: d["_status"] = item.status`
- BacklogItem.status is `str = ""` per models.py line 164 (verified)
- No round-trip test documented or implemented yet (separate from this fix)

**Assessment**:
- **Status**: PARTIALLY IMPLEMENTED
- **Finding 1**: IMPLEMENTED — `backlog_item_to_display_dict` correctly includes `"_status": item.status`
- **Finding 2**: IMPLEMENTED — BacklogItem.status is the correct type
- **Finding 3**: NOT YET DONE — Round-trip unit test not mentioned as completed in task file
- **Severity**: MEDIUM for acceptance criterion #3 (test coverage) — the fix itself is complete and correct

### 2. Inverse Adapter Function Documentation

**Function**: `_dict_to_backlog_item_fields` (lines 156-187 in backlog.py)

**Location in Architecture Spec**: Section 5.4, lines 298-307

**Documentation Claims**:
```text
### 5.4 dict to BacklogItem Conversion

For CLI code that constructs a dict and needs to pass it to core functions:

```python
# Pydantic's model_validate handles this directly
item = BacklogItem.model_validate(raw_dict)
```

This is used at call sites where the CLI has a dict (e.g., from user input
assembly in an `add` command) and needs to call a core function. No wrapper
needed -- Pydantic's constructor handles the mapping.
```

**Assessment**:
- **Status**: INCOMPLETE DOCUMENTATION
- **Issue**: The spec shows a simple `BacklogItem.model_validate(raw_dict)` pattern, but the actual implementation includes a helper function `_dict_to_backlog_item_fields` (lines 156-187) that does field mapping before calling `model_validate`
- **Evidence**:
  - Spec says "No wrapper needed -- Pydantic's constructor handles the mapping"
  - Code shows a 31-line helper function that explicitly maps fields: `d.get("_title", "")` → `"title"`, etc.
  - The helper exists because the CLI's dict format uses keys like `_title` and `**Key**` that don't directly match Pydantic field names
- **Severity**: MEDIUM — Documentation predates the actual implementation helper, creating a gap between "what the spec says" and "what the code does"
- **Impact**: Developers reading Section 5.4 alone would not understand that a field-mapping helper exists and is required

---

## Detailed Findings by Category

### Finding 1: `backlog_item_to_display_dict` Spec Example Incomplete

**Category**: Documented but Outdated Example
**Priority**: Low
**File**: `plan/architect-backlog-cli-dedup.md`
**Lines**: 283-293

**Evidence**:
- Spec shows example output fields: `_title`, `_section`, `_file_path`, `_skip`
- Code now outputs additional fields: `_issue`, `_raw_body`, `_groomed`, `_last_synced`, `_status`
- Spec says "Plus all metadata fields as **Key** -> value pairs" but does not explicitly list the underscore-prefixed fields that are conditionally added

**Recommendation**:
Update the example docstring in the spec to show all fields, or replace the exhaustive list with a clearer categorization:

```python
# SUGGESTED REVISION
def backlog_item_to_display_dict(item: BacklogItem) -> dict:
    """Convert BacklogItem to the dict format CLI display functions expect.

    Returns a dict with:
    - Underscore-prefixed system fields: _title, _section, _file_path, _skip,
      _issue, _raw_body (always present)
    - Conditional underscore-prefixed metadata: _groomed, _last_synced, _status
      (only if truthy)
    - Bold-star metadata fields: **Description**, **Priority**, **Type**, etc.
    """
```

**Status**: Audit only; no fix applied per instructions.

---

### Finding 2: `_dict_to_backlog_item_fields` Helper Missing from Architecture Spec

**Category**: Implemented but Undocumented (Internal Helper)
**Priority**: Medium
**File**: `plan/architect-backlog-cli-dedup.md`
**Gap**: Section 5.4 (dict to BacklogItem Conversion)

**Evidence**:
- Spec (lines 302-307) states: "Pydantic's model_validate handles this directly... No wrapper needed"
- Code (backlog.py lines 156-187) includes a 31-line helper function that is **required** to bridge the gap between CLI dict format (`_title`, `**Key**`) and Pydantic field names (`title`, `priority`)
- All 7 CLI call sites use the helper before calling `model_validate` (confirmed via grep of backlog.py lines 336, 366, 388, 404, 425, 436, 450)

**Documentation Claim**: "No wrapper needed -- Pydantic's constructor handles the mapping"

**Code Reality**:
```python
def _dict_to_backlog_item_fields(d: dict) -> dict:
    """Convert a CLI display dict back to BacklogItem field kwargs for model_validate.

    This is the inverse of backlog_item_to_display_dict."""
    return {
        "title": d.get("_title", ""),
        "section": d.get("_section", ""),
        "status": d.get("_status", ""),  # <-- Uses _status if present
        # ... 14 more field mappings ...
    }
```

**Root Cause**: The adapter function was added during implementation (per architecture spec annotation #3, line 707-710 in tasks-1-backlog-cli-dedup.md: "Second adapter function `_dict_to_backlog_item_fields` added — not in spec"). The spec was written before this helper was recognized as necessary.

**Impact on Current Fix**:
- The fix adds `_status` to `backlog_item_to_display_dict` output
- The inverse function `_dict_to_backlog_item_fields` already reads `d.get("_status", "")` at line 186
- The round-trip is now symmetric: both adapters handle `_status` correctly

**Recommendation**:
Add a section to the architecture spec documenting both adapters as a pair:

```markdown
### 5.4 Revised: Dict ↔ BacklogItem Conversion Strategy

**Two adapters work in tandem at the CLI boundary:**

1. **BacklogItem → dict**: `backlog_item_to_display_dict(item)`
   - Converts typed fields to underscore-prefixed keys
   - Maps optional fields conditionally if truthy
   - Used by CLI commands that display parsed items

2. **dict → BacklogItem**: `_dict_to_backlog_item_fields(d)`
   - Converts underscore-prefixed keys back to typed field names
   - Used at call sites that construct a dict and pass to core functions
   - Relies on Pydantic's `BacklogItem.model_validate()` for final validation

Together, these ensure symmetric round-trip conversion:
`BacklogItem → dict → BacklogItem` preserves all fields.
```

**Status**: Audit only; spec not modified per instructions.

---

### Finding 3: Round-Trip Test Not Yet Documented as Completed

**Category**: Acceptance Criterion Incomplete
**Priority**: Medium
**File**: `plan/tasks-36-backlog-cli-dedup-followup-2.md`
**Lines**: 91-96 (Acceptance Criteria #3)

**Evidence**:
- Criterion #3 requires: "A new test in `.claude/skills/backlog/tests/` covers the full round-trip for all fields including `_status` / `status`"
- Grooming section (line 62) states: "No existing tests cover either adapter function (grep of test directory returned zero matches)"
- Task file does not document completion of the test requirement

**Assessment**:
- The implementation fix is complete (`_status` added to output dict)
- The mirror-side (reading `_status` in `_dict_to_backlog_item_fields`) was already present
- The acceptance test requirement remains pending

**Recommendation**:
Create a follow-up task or extend the current task to ensure the round-trip test is written and included in the commit.

**Status**: Audit only; no action per instructions.

---

### Finding 4: Silent Data Loss Prevention Requirement — SATISFIED

**Category**: Architecture Principle
**Priority**: High (but verified as satisfied)
**Reference**: `.claude/rules/silent-failure-prevention.md`

**Requirement**: "Write operations must return a value indicating what changed... Branching on input values requires explicit fallback"

**Evidence**:
- Architecture spec (Section 5.7) and task file both reference "silent failure prevention rule"
- The `backlog_item_to_display_dict` function uses conditional inclusion:
  ```python
  if item.status:
      d["_status"] = item.status
  ```
- This is intentional: empty status (`""`) is not written to output dict
- The inverse function handles this with `d.get("_status", "")` — safely reads and defaults

**Assessment**:
- **Status**: CORRECT
- The conditional write is appropriate for optional string fields
- No data loss occurs: round-trip preserves `status=""` via the default in the inverse function
- **No drift found** — the implementation aligns with the principle

---

## Verification Checklist

| Aspect | Status | Evidence |
|--------|--------|----------|
| `backlog_item_to_display_dict` documented | ✓ Documented | architect-backlog-cli-dedup.md Section 5.3 |
| Function signature in code matches spec | ✓ Match | Code at lines 190-230 matches intent |
| `_status` field addition needed | ✓ Verified | Symmetry with `_dict_to_backlog_item_fields` line 186 |
| Implementation adds `_status` correctly | ✓ Correct | Lines 228-229: conditional write of `item.status` |
| Call sites correctly use adapter | ✓ Verified | All 7 call sites use the function (grep confirmed) |
| Inverse adapter also handles `_status` | ✓ Verified | `_dict_to_backlog_item_fields` line 186 reads it |
| Silent failure prevention satisfied | ✓ Verified | Conditional write + safe default in inverse |
| Test coverage requirement documented | ⚠ Pending | Acceptance criterion #3 not marked complete |

---

## Summary: No Critical Drift Found

The change to add `"_status": item.status` to `backlog_item_to_display_dict` output is:

1. **Fully documented** in the architecture spec and task files
2. **Correctly implemented** with symmetric handling in both adapters
3. **Well-motivated** by the silent failure prevention principle
4. **Tested-ready** (round-trip test requirement exists but not yet completed)

### Minor Documentation Gaps (Low Priority)

1. **Example fields in spec**: The docstring example in Section 5.3 predates the full field list and does not explicitly show `_status` (and other underscore-prefixed fields)
2. **Missing helper documentation**: The architecture spec (Section 5.4) does not document `_dict_to_backlog_item_fields` helper, which was added during implementation
3. **Test completion not documented**: The round-trip test requirement is listed in acceptance criteria but not marked as completed

**None of these gaps represent a functional mismatch between documentation and code.** They are opportunities for documentation refresh as the codebase evolves.

---

## Recommendations for Drift Resolution

**If this task is being completed:**

1. **Before committing**: Ensure the round-trip unit test (Acceptance Criterion #3) is written and passing
2. **Document the test**: Add a test file path to the task's completion notes
3. **Verify adapter symmetry**: Confirm that both adapters (forward and inverse) are tested together
4. **Optional spec update**: Consider updating `architect-backlog-cli-dedup.md` Section 5.4 to document `_dict_to_backlog_item_fields` as a companion adapter

**If this is a retrospective audit:**

1. **No immediate action required** — the code is correct and aligned with the documented intent
2. **Defer spec clarifications** to a separate documentation refresh task
3. **Track test coverage** as a follow-up item in backlog

---

## Files Examined

**Documentation Files**:
- `plan/architect-backlog-cli-dedup.md` (Lines: 1-730, relevant sections: 5.2-5.6)
- `plan/tasks-1-backlog-cli-dedup.md` (Lines: 1-731, full file)
- `plan/tasks-36-backlog-cli-dedup-followup-2.md` (Lines: 1-190, full file)
- `.claude/backlog/p2-fix-missing-status-key-in-backlogitemtodisplaydict-adapter.md` (Lines: 1-166, full file)

**Implementation Files**:
- `.claude/skills/backlog/scripts/backlog.py` (Lines: 150-230, adapter functions)

**Audit Scope**: Internal adapter functions only; no changes to CLI commands, core API, or test suite examined outside of acceptance criteria documentation.
