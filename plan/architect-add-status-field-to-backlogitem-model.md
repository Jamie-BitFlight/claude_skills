# Architecture Spec: Add Status Field to BacklogItem Model

## Document Metadata

- **Feature**: Add `status` field to `BacklogItem` Pydantic model
- **Source**: GitHub Issue #612, feature-context-add-status-field-to-backlogitem-model.md
- **Date**: 2026-03-12
- **Scope**: Model field addition, parsing update, view helper simplification, legacy script update

---

## 1. Executive Summary

Add a `status: str = ""` field to the `BacklogItem` Pydantic model so that `parse_item_file()` preserves the raw frontmatter status string (which it already extracts but discards). This eliminates a redundant file re-read in `view_result_from_local_item()` and makes status available to all consumers of `BacklogItem` without additional I/O. The legacy `backlog.py` script has the same redundant read pattern and is updated in the same change. No behavioral changes to callers. The `status` field preserves raw frontmatter case (no normalization).

---

## 2. Architecture Overview

This is a surgical data model change, not a new system. The architecture is the existing `backlog_core` package.

### Call Flow (Before)

```text
parse_item_file()
  -> extracts status via _fm_str(fm, meta, "status")
  -> uses .lower() only for skip boolean
  -> DISCARDS raw status string

view_result_from_local_item(item)
  -> copies item fields to ViewItemResult
  -> RE-READS file from disk to extract status  <-- redundant I/O
  -> sets result.status from re-parsed frontmatter
```

### Call Flow (After)

```text
parse_item_file()
  -> extracts status via _fm_str(fm, meta, "status")
  -> stores raw string in item.status            <-- NEW
  -> uses .lower() for skip boolean (unchanged)

view_result_from_local_item(item)
  -> copies item fields to ViewItemResult
  -> sets result.status = item.status             <-- uses model field
  -> NO file re-read
```

---

## 3. Technology Stack

No new dependencies. All changes use existing Pydantic BaseModel patterns already established in `backlog_core/models.py`.

---

## 4. Component Design

### 4.1 Model Layer: `backlog_core/models.py`

**File**: `.claude/skills/backlog/backlog_core/models.py`

**Change**: Add `status: str = ""` field to `BacklogItem` class.

**Interface (field addition only -- no implementation bodies)**:

```python
class BacklogItem(BaseModel):
    # ... existing content fields ...
    title: str = ""
    description: str = ""
    source: str = "Not specified"
    added: str = ""
    priority: str = ""
    item_type: str = "Feature"
    issue: str = ""
    plan: str = ""
    research_first: str = ""
    files: str = ""
    suggested_location: str = ""

    # ... existing metadata fields ...
    section: str = ""
    file_path: str = ""
    skip: bool = False
    status: str = ""          # <-- NEW FIELD: raw frontmatter status, preserves case
    groomed: str = ""
    last_synced: str = ""
    raw_body: str = ""
```

**Placement rationale**: `status` is placed immediately after `skip` because `skip` is derived from `status`. This groups related fields together. The `skip` boolean remains for backward compatibility -- callers that check `item.skip` continue to work unchanged.

**Default value**: Empty string `""`, consistent with other string fields on the model. Items parsed from files without frontmatter (the early-return path on line 227) get the default.

**Case preservation**: The field stores whatever `_fm_str(fm, meta, "status")` returns -- raw case from frontmatter (e.g., "open", "Done", "RESOLVED"). No `.lower()` normalization. This matches the current behavior of the re-read path in `view_result_from_local_item()` (line 814), which stores `str(meta.get("status", fm.get("status", "")))` without lowercasing.

### 4.2 Parsing Layer: `backlog_core/parsing.py`

**File**: `.claude/skills/backlog/backlog_core/parsing.py`

#### 4.2.1 Change in `parse_item_file()` (line 235-247)

**Current code** (line 243):

```python
skip=_fm_str(fm, meta, "status").lower() in {"done", "resolved"},
```

**Target interface** -- add `status` field to the `BacklogItem(...)` constructor call:

```python
# In the return BacklogItem(...) call, add:
status=_fm_str(fm, meta, "status"),
skip=_fm_str(fm, meta, "status").lower() in {"done", "resolved"},
```

**Optimization note**: `_fm_str(fm, meta, "status")` is called twice. The implementer should extract it to a local variable:

```python
status_raw = _fm_str(fm, meta, "status")
# Then use status_raw for both:
#   status=status_raw,
#   skip=status_raw.lower() in {"done", "resolved"},
```

This avoids the double dict lookup and makes the relationship between `status` and `skip` explicit in the code.

#### 4.2.2 Change in `view_result_from_local_item()` (line 784-815)

**Current code** (lines 805-814) -- the redundant file re-read block:

```python
# status is not on BacklogItem — extract from frontmatter metadata if file exists
fp = item.file_path
if fp and Path(fp).exists():
    raw = Path(fp).read_text(encoding="utf-8")
    post = loads_frontmatter(raw)
    fm_raw = post.metadata if hasattr(post, "metadata") else (post[0] if isinstance(post, tuple) else {})
    fm: dict[str, str] = dict(fm_raw) if isinstance(fm_raw, dict) else {}
    meta_raw = fm.get("metadata", {})
    meta: dict[str, str] = dict(meta_raw) if isinstance(meta_raw, dict) else {}
    result.status = str(meta.get("status", fm.get("status", "")))
```

**Target interface** -- replace entire block with:

```python
result.status = item.status
```

This is the core simplification. The comment `# status is not on BacklogItem` becomes obsolete.

### 4.3 Legacy Script: `scripts/backlog.py`

**File**: `.claude/skills/backlog/scripts/backlog.py`

#### 4.3.1 Change in `_view_result_from_local_item()` (line 1868-1895)

The legacy script uses untyped dicts, not the `BacklogItem` model. Its `_view_result_from_local_item()` (lines 1883-1894) has the same redundant file re-read pattern.

**Current code** (lines 1883-1894):

```python
fp = item.get("_file_path")
if fp and Path(fp).exists():
    raw = Path(fp).read_text(encoding="utf-8")
    post = loads_frontmatter(raw)
    fm_raw = post.metadata if hasattr(post, "metadata") else (post[0] if isinstance(post, tuple) else {})
    fm: dict = dict(fm_raw) if isinstance(fm_raw, dict) else {}
    meta_raw = fm.get("metadata", {})
    meta: dict = dict(meta_raw) if isinstance(meta_raw, dict) else {}
    result["description"] = str(fm.get("description", ""))
    result["source"] = str(meta.get("source", fm.get("source", "")))
    result["added"] = str(meta.get("added", fm.get("added", "")))
    result["status"] = str(meta.get("status", fm.get("status", "")))
```

**Analysis**: The legacy script re-reads the file to extract four fields: `description`, `source`, `added`, and `status`. Unlike the core module (where `description`, `source`, and `added` are already on `BacklogItem` and the re-read is only for `status`), the legacy script's dict-based items do not carry these parsed fields.

**Target approach**: The legacy script should populate `_status` on the item dict during its parsing phase (wherever it builds the item dict), then use `item.get("_status", "")` in `_view_result_from_local_item()`. However, the legacy script's parsing is more complex and uses a different code path.

**Minimum viable change**: Since the legacy script re-reads for four fields (not just status), and three of those (description, source, added) are not available on the dict, the file re-read cannot be fully eliminated without a larger refactor. The implementer should:

1. Add `result["status"] = item.get("_status", "")` as the primary path
2. Keep the file re-read block but only for `description`, `source`, and `added`
3. Remove `status` extraction from the file re-read block

This partially eliminates the redundancy (status no longer needs the re-read) while keeping the re-read for fields that genuinely are not on the dict.

**Alternative** (if `_status` is not populated during legacy parsing): Leave the legacy script unchanged and document it as a known inconsistency. The legacy script is a parallel implementation being gradually replaced by `backlog_core`. A separate backlog item can track full elimination of the legacy re-read pattern.

**Decision**: Implementer should check whether the legacy script's item dict already has `_status` populated during parsing. If yes, use it. If no, leave the legacy function unchanged and add a code comment noting the gap.

---

## 5. Data Architecture

### 5.1 BacklogItem Model Schema (After Change)

```text
BacklogItem(BaseModel)
  Content fields:
    title: str = ""
    description: str = ""
    source: str = "Not specified"
    added: str = ""
    priority: str = ""
    item_type: str = "Feature"
    issue: str = ""
    plan: str = ""
    research_first: str = ""
    files: str = ""
    suggested_location: str = ""

  Metadata fields:
    section: str = ""
    file_path: str = ""
    skip: bool = False
    status: str = ""           <-- NEW
    groomed: str = ""
    last_synced: str = ""
    raw_body: str = ""
```

### 5.2 Field Value Examples

| Frontmatter Value | `item.status` | `item.skip` |
|---|---|---|
| `status: open` | `"open"` | `False` |
| `status: Done` | `"Done"` | `True` |
| `status: RESOLVED` | `"RESOLVED"` | `True` |
| `status: in-progress` | `"in-progress"` | `False` |
| (no status key) | `""` | `False` |

### 5.3 Relationship Between `status` and `skip`

`skip` is a derived boolean: `skip = status.lower() in {"done", "resolved"}`. With `status` now on the model, `skip` could theoretically become a `@computed_field` or `@property`. This is explicitly **out of scope** for this change to avoid behavioral risk. The `skip` field remains a stored `bool` populated during parsing.

---

## 6. Security Architecture

No security implications. This change adds a field to an in-memory model populated from local filesystem files that the process already reads. No new I/O, no new attack surface, no credential handling.

---

## 7. Testing Architecture

### 7.1 Existing Tests to Verify (Must Pass)

**File**: `.claude/skills/backlog/tests/test_backlog_core_parsing.py`

- `test_parse_item_file_flat_done_status_sets_skip_true` -- verifies `skip=True` for "done" status
- `test_parse_item_file_flat_open_status_sets_skip_false` -- verifies `skip=False` for other statuses
- All `test_view_result_from_local_item_*` tests (lines 1072-1148) -- verify view result construction

These tests must continue to pass without modification. The `skip` behavior is unchanged.

### 7.2 New Tests Required

#### Test Category: `parse_item_file` status field population

| Test Name | Input | Assert |
|---|---|---|
| `test_parse_item_file_nested_meta_status_populated` | Nested metadata with `status: open` | `item.status == "open"` |
| `test_parse_item_file_flat_status_populated` | Flat frontmatter with `status: Done` | `item.status == "Done"` (case preserved) |
| `test_parse_item_file_no_frontmatter_status_empty` | Plain text (no `---`) | `item.status == ""` |
| `test_parse_item_file_no_status_key_status_empty` | Frontmatter without status key | `item.status == ""` |
| `test_parse_item_file_status_and_skip_consistent` | `status: resolved` | `item.status == "resolved"` AND `item.skip is True` |

#### Test Category: `view_result_from_local_item` uses model status

| Test Name | Input | Assert |
|---|---|---|
| `test_view_result_status_from_model` | `BacklogItem(status="open")` | `result.status == "open"`, no file I/O |
| `test_view_result_status_empty_default` | `BacklogItem()` (no status) | `result.status == ""` |
| `test_view_result_no_file_read_for_status` | `BacklogItem(status="open", file_path="/nonexistent")` | `result.status == "open"`, no `FileNotFoundError` |

The third test is a regression test: the old code would fail or return `""` for a nonexistent file path. The new code uses the model field regardless of file existence.

### 7.3 Test Fixtures

Use the existing `_NESTED_META_FRONTMATTER` and `_FLAT_FRONTMATTER` fixtures already defined in the test file. Both contain `status: open`.

### 7.4 Coverage Requirements

- All new code paths (status field assignment in `parse_item_file`, status read in `view_result_from_local_item`) must be covered
- Existing coverage must not decrease

---

## 8. Distribution Architecture

Not applicable. This is an internal model change within the `backlog_core` package. No distribution changes.

---

## 9. Architectural Decisions

### ADR-001: Preserve Raw Case in `status` Field

**Decision**: `BacklogItem.status` stores the raw frontmatter value without case normalization.

**Context**: `parse_item_file()` already lowercases status for the `skip` check. Two options: store raw (matching current `view_result_from_local_item` behavior) or store normalized lowercase.

**Rationale**: The current `view_result_from_local_item()` (line 814) stores `str(meta.get("status", fm.get("status", "")))` -- raw case. Changing to normalized would alter the value returned by `backlog_view` operations, which is a behavioral change. The design decision stated in the requirements says: "preserve raw frontmatter case to avoid behavioral changes."

**Consequence**: Callers comparing status strings must handle case themselves (e.g., `.lower() == "done"`). This is already the pattern used for the `skip` derivation.

### ADR-002: Keep `skip` as Stored Field (Do Not Convert to Computed Property)

**Decision**: `skip` remains a stored `bool` field on `BacklogItem`, not a computed property derived from `status`.

**Context**: With `status` now on the model, `skip` is technically redundant -- it could be `@property` returning `self.status.lower() in {"done", "resolved"}`.

**Rationale**: Converting `skip` to a property changes its serialization behavior (Pydantic computed fields behave differently from stored fields in `model_dump()`), affects `parse_backlog_from_directory()` which sets `item.skip = True` for "Completed" sections (line 293), and risks breaking callers. This is explicitly out of scope per requirements.

### ADR-003: Legacy Script Best-Effort Update

**Decision**: Update the legacy `backlog.py` script's `_view_result_from_local_item()` only if the item dict already carries a `_status` key from its parsing phase. Otherwise, leave unchanged with a comment.

**Context**: The legacy script uses untyped dicts and re-reads files for four fields (description, source, added, status). The core module only re-reads for status.

**Rationale**: The legacy script cannot eliminate the file re-read entirely (it needs description, source, added from the re-read too). Partially fixing it (removing only the status extraction) yields minimal benefit and adds risk to a deprecated code path. The implementer should assess and apply judgment.

---

## 10. Scalability Strategy

Not applicable for this change. The change reduces I/O (eliminates one file read per `backlog_view` call), which is a minor scalability improvement for repositories with many backlog items.

---

## Module Boundaries Affected

| Module | File | Change Type | Lines Affected |
|---|---|---|---|
| `backlog_core.models` | `.claude/skills/backlog/backlog_core/models.py` | Field addition | ~line 162 (add 1 line) |
| `backlog_core.parsing` | `.claude/skills/backlog/backlog_core/parsing.py` | Parse update + view simplification | lines 235-247 (add status), lines 805-814 (replace with 1 line) |
| `backlog scripts` | `.claude/skills/backlog/scripts/backlog.py` | Best-effort update | lines 1883-1894 (conditional) |
| `backlog tests` | `.claude/skills/backlog/tests/test_backlog_core_parsing.py` | New test cases | append ~30 lines |

---

## Callers of Changed Interfaces

### `BacklogItem` Consumers (unaffected -- new field defaults to `""`)

- `parse_backlog_from_directory()` -- parsing.py:250
- `find_item()` -- parsing.py:312
- `find_fuzzy_duplicates()` -- parsing.py:338
- `items_needing_issues()` -- parsing.py:381
- `items_with_issues()` -- parsing.py:386
- `view_result_from_local_item()` -- parsing.py:784
- `operations.py:1196` -- caller of view_result_from_local_item

### `view_result_from_local_item()` Consumers (unaffected -- same return type and values)

- `operations.py:1196` -- the only caller in backlog_core

All callers receive the same data. The only difference: `ViewItemResult.status` is now populated from the model field instead of a file re-read. The value is identical.

---

## Post-Implementation Annotations

_Added by context-refinement agent on 2026-03-12_

### Design Refinements

1. **`view_result_from_local_item()` scope of change**: Section 4.2.2 specified replacing only lines 805-814 (the status re-read block) with `result.status = item.status`, keeping the earlier block at lines 791-804 intact. The actual implementation rewrote the entire function body as a single coherent flat block with no conditional sections.
   - Original: "Replace entire block [lines 805-814] with `result.status = item.status`"
   - Actual: Full function rewrite — `ViewItemResult(...)` constructor plus sequential `result.* = item.*` assignments for description, source, added, raw_body, status. The intermediate block structure at lines 791-804 (described in section 4.2.2 as "copies fields already on BacklogItem") was absorbed into the new flat structure. Observable behavior is identical.
   - Recorded in: plan/tasks-1-add-status-field-to-backlogitem-model.md

2. **ADR-003 outcome — legacy script left with comment**: Section 4.3.1 described a "minimum viable change" path: add `result["status"] = item.get("_status", "")` and keep the file re-read only for description/source/added. The implementer found `_status` is not populated on item dicts (confirming the "Alternative" path in ADR-003), so the function was left unchanged with a `# TODO(#612)` comment. The "minimum viable change" path was not taken.
   - Original: "Add `result['status'] = item.get('_status', '')` as primary path, keep re-read for description/source/added"
   - Actual: Function left completely unchanged; comment `# TODO(#612): status not available on item dict; re-read still needed` added at line 1894 before the status assignment
   - Recorded in: plan/tasks-1-add-status-field-to-backlogitem-model.md
