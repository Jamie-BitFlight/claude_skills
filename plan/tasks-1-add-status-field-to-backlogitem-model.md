---
description: "Add status field to BacklogItem model, populate during parsing, simplify view helper"
version: "1.0"
feature: add-status-field-to-backlogitem-model
issue: 612
architecture: plan/architect-add-status-field-to-backlogitem-model.md
feature_context: plan/feature-context-add-status-field-to-backlogitem-model.md
codebase_analysis: plan/codebase/backlog-core-patterns.md
tasks:
  - T1: Add status field to BacklogItem and update parsing and view logic
  - T2: Verify all tests pass and add new test coverage for status field
---

Fixes #612

---
task: T1
title: Add status field to BacklogItem and update parsing and view logic
status: complete
completed: 2026-03-12T02:28:00Z
agent: python-cli-architect
dependencies: []
priority: 1
complexity: low
accuracy-risk: low
skills:
  - python3-development
parallelize-with: []
started: "2026-03-12T02:23:02Z"
---

## Context

`BacklogItem` in `.claude/skills/backlog/backlog_core/models.py` (line ~162) lacks a `status` field. The `parse_item_file()` function in `.claude/skills/backlog/backlog_core/parsing.py` already extracts status via `_fm_str(fm, meta, "status")` on line 243 but discards the raw string, keeping only the derived `skip` boolean. This forces `view_result_from_local_item()` (parsing.py lines 805-814) to re-read the file from disk to extract status for the `ViewItemResult`.

Architecture spec: `plan/architect-add-status-field-to-backlogitem-model.md`
Codebase analysis: `plan/codebase/backlog-core-patterns.md`

## Objective

Add `status: str = ""` to `BacklogItem`, populate it during `parse_item_file()`, and replace the redundant file re-read in `view_result_from_local_item()` with `result.status = item.status`.

## Inputs

- `.claude/skills/backlog/backlog_core/models.py` -- BacklogItem class definition
- `.claude/skills/backlog/backlog_core/parsing.py` -- `parse_item_file()` and `view_result_from_local_item()`
- `.claude/skills/backlog/scripts/backlog.py` -- legacy `_view_result_from_local_item()` (best-effort)
- Architecture spec section 4.1-4.3 for exact change specifications

## Requirements

### Model change (models.py)

1. Add `status: str = ""` field to `BacklogItem` class, placed immediately after `skip: bool = False`

### Parsing change (parsing.py -- parse_item_file)

2. Extract `_fm_str(fm, meta, "status")` into a local variable `status_raw` to avoid duplicate dict lookup
3. Use `status_raw` for both: `status=status_raw` (new) and `skip=status_raw.lower() in {"done", "resolved"}` (existing behavior preserved)

### View helper change (parsing.py -- view_result_from_local_item)

4. Replace the entire file re-read block (lines 805-814, starting with `# status is not on BacklogItem`) with `result.status = item.status`

### Legacy script (scripts/backlog.py -- best-effort)

5. Check whether the legacy `_view_result_from_local_item()` (~line 1868) item dict already carries a `_status` key. If yes, use it and remove status from the file re-read block. If no, leave unchanged and add a code comment: `# TODO(#612): status not available on item dict; re-read still needed`

## Constraints

- No behavioral changes to callers of `parse_item_file()` or `view_result_from_local_item()`
- `skip` field remains a stored `bool`, not a computed property
- `status` preserves raw frontmatter case (no `.lower()` normalization)
- Do not modify `ViewItemResult` model (it already has `status: str = ""`)
- Do not refactor or remove the `skip` field

## Expected Outputs

- File modified: `.claude/skills/backlog/backlog_core/models.py`
- File modified: `.claude/skills/backlog/backlog_core/parsing.py`
- File modified (best-effort): `.claude/skills/backlog/scripts/backlog.py`

## Acceptance Criteria

1. `BacklogItem` class has a `status: str = ""` field after the `skip` field
2. `parse_item_file()` populates `item.status` with the raw frontmatter status string
3. `parse_item_file()` uses a local variable to avoid calling `_fm_str(fm, meta, "status")` twice
4. `view_result_from_local_item()` no longer reads any file from disk -- the entire file re-read block is removed
5. `view_result_from_local_item()` sets `result.status = item.status`
6. The `skip` field behavior is unchanged: `"done"` and `"resolved"` (case-insensitive) set `skip=True`
7. All existing tests in `.claude/skills/backlog/tests/` pass without modification

## Verification Steps

1. Read the modified `models.py` and confirm `status: str = ""` exists on `BacklogItem` after `skip`
2. Read the modified `parsing.py` and confirm `parse_item_file()` assigns `status=status_raw` and no file I/O exists in `view_result_from_local_item()`
3. Run: `uv run python -c "from backlog_core.models import BacklogItem; b = BacklogItem(); assert b.status == ''; print('OK')"`
4. Run: `uv run pytest .claude/skills/backlog/tests/ -x -q`

## Handoff

Return:
- Summary of lines changed in each file
- Whether the legacy script was updated or left unchanged (and why)
- Test run output (pass/fail)

---

## Context Manifest

_Generated by context-gathering agent on 2026-03-12_

### How BacklogItem Parsing and Status Extraction Currently Work

**User Invocation:** When a user calls `backlog_view` (CLI) or `mcp__backlog__backlog_view` (MCP), the flow is:

1. **Lookup:** The item is located by selector (title, issue number, or file path) via `find_item()` in `parsing.py:312-335`
2. **Parse:** The item file is parsed with `parse_item_file(text: str, path: Path)` (parsing.py:220-247), which:
   - Returns early with empty `BacklogItem` if the file doesn't start with `---` (plain text files)
   - Otherwise calls `_parse_frontmatter(text)` (parsing.py:200-217) to extract frontmatter and metadata dicts
   - Extracts all string fields using the `_fm_str()` helper (parsing.py:191-197), which follows a fallback chain: nested `metadata` dict first, then flat frontmatter, then empty string
   - At line 243, extracts status: `skip=_fm_str(fm, meta, "status").lower() in {"done", "resolved"}` — the raw status value is computed but ONLY the derived boolean `skip` is stored
   - Returns a `BacklogItem` instance with all fields populated EXCEPT the raw status string

3. **View:** The `view_result_from_local_item(item: BacklogItem)` function (parsing.py:784-815) converts the parsed item to a viewable result:
   - Lines 791-804: Copies fields already on `BacklogItem` to the `ViewItemResult` (title, priority, issue, plan, file_path, groomed, description, source, added, raw_body)
   - **Lines 805-814 (THE PROBLEM):** Because `BacklogItem` has no `status` field, the function re-reads the file from disk, re-parses frontmatter with `_parse_frontmatter()`, and extracts `metadata.status` or `frontmatter.status` — the exact same operation that `parse_item_file()` already did
   - Returns `ViewItemResult` with all fields populated

**Current Redundancy:** The file is read and parsed twice. The first read extracts status but discards the raw string (storing only `skip`). The second read (lines 806-814) re-parses the file to get the status string back out.

**Architectural Decision:** The status field preserves raw frontmatter case (e.g., "open", "Done", "RESOLVED"). The `skip` field (boolean) is case-insensitive: `"done"` and `"resolved"` in any case set `skip=True`. This separation exists to avoid behavioral changes — existing callers of `view_result_from_local_item()` expect the raw case to be preserved (matching current line 814 behavior).

**Field Organization on BacklogItem (models.py:140-166):**

Fields are grouped into three logical sections:
1. **Content fields:** title, description, source, added, priority, item_type, issue, plan, research_first, files, suggested_location (lines 148-158)
2. **Metadata fields:** section, file_path, skip, groomed, last_synced (lines 160-164)
3. **Raw body:** raw_body (line 165)

The `status` field will be inserted in the metadata group immediately after `skip` because `skip` is derived from `status`, so grouping them together makes the relationship explicit.

### For Task T1 Implementation: What Needs to Connect

The implementation touches three code paths:

**Path 1: Model Definition (models.py)**
- Add one field: `status: str = ""` after line 162 (`skip: bool = False`)
- No other changes to the model
- All existing consumers of `BacklogItem` automatically get the new field with default value `""`

**Path 2: Parsing (parsing.py, parse_item_file function)**
- Current line 243 calls `_fm_str(fm, meta, "status")` but discards the result
- Requirement: Extract the result into a local variable `status_raw` to avoid double lookup
- Use `status_raw` for both:
  - New: `status=status_raw` in the `BacklogItem(...)` constructor call
  - Existing: `skip=status_raw.lower() in {"done", "resolved"}` (replace the current line 243)
- This is a pure refactoring — no behavioral change, just optimization + persistence

**Path 3: View Helper (parsing.py, view_result_from_local_item function)**
- Current lines 805-814 re-read the file from disk
- Requirement: Replace the entire file-re-read block with a single line: `result.status = item.status`
- This is the core simplification: assume the item was parsed by `parse_item_file()` and status is already on the model
- The file re-read becomes unnecessary

**Path 4: Legacy Script (scripts/backlog.py, _view_result_from_local_item function) — Best-Effort Only**
- Lines 1883-1894 in `backlog.py` use untyped dicts and re-read the file for FOUR fields: description, source, added, status
- Unlike the core module (where description/source/added are already on BacklogItem), the legacy script's dict-based items don't carry these fields
- **Decision logic per requirements:** Check whether the legacy script's item dict already has `_status` populated during its parsing phase
  - If YES: Use `item.get("_status", "")` instead of the file re-read for status only
  - If NO: Leave the function unchanged and add a comment: `# TODO(#612): status not available on item dict; re-read still needed`

**Test Impact:** Existing tests (test_backlog_core_parsing.py) must pass unchanged. The `skip` field behavior is preserved exactly. Two existing test fixtures already have `status: open` in their frontmatter (lines 273 and 286 in the codebase analysis), so new status field tests can reuse them.

### Technical Reference Details

#### Field Resolution Pattern (The _fm_str Helper)

```python
def _fm_str(fm: dict[str, object], meta: dict[str, str], key: str, fm_key: str = "") -> str:
    """Resolve a string field from metadata dict with frontmatter fallback.

    Returns:
        Resolved string value, or empty string if not found.
    """
    return str(meta.get(key) or fm.get(fm_key or key) or "")
```

This pattern is used for all optional string fields. The lookup order is:
1. Nested `metadata` dict: `meta.get(key)`
2. Flat frontmatter: `fm.get(fm_key or key)` (uses provided key or falls back to same key)
3. Empty string: `or ""`

**For status:** Call is `_fm_str(fm, meta, "status")` with no alternate key, so it checks `meta.get("status")`, then `fm.get("status")`, then `""`.

#### Frontmatter Parsing Structure

The `_parse_frontmatter(text)` function returns a tuple:

```python
(fm_dict, meta_dict, body_text)
```

Where:
- `fm_dict`: The flat frontmatter (YAML keys at top level)
- `meta_dict`: The nested metadata block (if present in `fm["metadata"]`)
- `body_text`: The markdown body after the `---` delimiters

**Example nested-metadata format** (produced by `build_backlog_frontmatter`):

```yaml
---
name: My Item
description: My description
metadata:
  source: test-source
  added: '2026-01-01'
  priority: P1
  status: open
---
Body content
```

**Example flat format** (legacy):

```yaml
---
title: My Item
source: test-source
added: '2026-01-01'
priority: P1
status: open
---
Body content
```

Both formats are supported by `_fm_str()` fallback chain. The `status` field uses the same resolution logic.

#### BacklogItem and ViewItemResult Models

**BacklogItem (models.py:140-166)** — internal parsed representation:
- All fields default to empty/falsy for incremental construction
- Used by parsing functions, item search, and internal operations
- Will gain: `status: str = ""`

**ViewItemResult (models.py:212-230)** — external view representation:
- Already has `status: str = ""` field (line 224)
- Returned by `view_result_from_local_item()` and consumed by MCP/CLI
- No changes needed; just needs to be populated from `item.status` instead of file re-read

#### Caller Contracts

**Callers of parse_item_file()** (parsing.py:220-247):
- Primary caller: `parse_backlog_from_directory()` (line 250)
- Secondary callers: test fixtures
- All receive a `BacklogItem` instance; the new `status` field is populated automatically
- No changes to function signature or return type — new field is transparent to callers

**Callers of view_result_from_local_item()** (parsing.py:784-815):
- Primary caller: `operations.py:1196` (from backlog MCP server)
- Consumes the returned `ViewItemResult`
- The `status` field value is identical before/after (same frontmatter source) — only the I/O path changes
- No behavioral changes visible to callers

**Callers of parse_backlog_from_directory()** (parsing.py:250+):
- Functions like `find_item()`, `find_fuzzy_duplicates()`, `items_with_issues()`, etc.
- All consume the parsed `BacklogItem` list
- The new `status` field is available to all; existing callers that don't use it are unaffected (field defaults to `""`)

#### Error Handling and Edge Cases

**Nonexistent file paths:** The old code in `view_result_from_local_item()` (line 807) checks `if fp and Path(fp).exists()` before reading. If the file doesn't exist, `result.status` remains `""` (default). The new code (`result.status = item.status`) doesn't read the file at all, so nonexistent paths are handled automatically — no `FileNotFoundError` can occur. This is a regression-fix benefit.

**Missing status key in frontmatter:** `_fm_str()` returns `""` if the key is not found in either nested metadata or flat frontmatter. So `item.status` will be `""` for items without a status key.

**Empty frontmatter:** If a file starts with `---` but has no metadata, `_parse_frontmatter()` returns empty dicts, and `_fm_str()` returns `""`, so `item.status = ""`.

**Plain text files (no frontmatter):** `parse_item_file()` returns early on line 227 with an empty `BacklogItem`, so `status` defaults to `""`.

#### Test Fixtures and Patterns

**Existing test fixtures** (test_backlog_core_parsing.py):

```python
_NESTED_META_FRONTMATTER = """---
name: My Test Item
description: A test description
metadata:
  source: test-source
  added: '2026-01-01'
  priority: P1
  type: Feature
  status: open
  topic: my-test-item
---
Body content here.
"""

_FLAT_FRONTMATTER = """---
title: Legacy Title
source: legacy-source
added: '2025-12-01'
priority: P0
status: open
---
Legacy body.
"""
```

Both fixtures have `status: open`. New tests can reuse these fixtures to verify status field population.

**Test naming convention** (from codebase analysis):
- Pattern: `test_[function]_[scenario]_[expected_outcome]`
- Examples: `test_parse_item_file_nested_meta_sets_title`, `test_parse_item_file_flat_done_status_sets_skip_true`

#### Configuration and File Paths

- **Model definition:** `.claude/skills/backlog/backlog_core/models.py` (line ~162, after `skip` field)
- **Parsing functions:** `.claude/skills/backlog/backlog_core/parsing.py` (lines 220-247 for `parse_item_file`, lines 784-815 for `view_result_from_local_item`)
- **Legacy script (best-effort):** `.claude/skills/backlog/scripts/backlog.py` (line ~1868, function `_view_result_from_local_item`)
- **Tests:** `.claude/skills/backlog/tests/test_backlog_core_parsing.py` (add new test cases after existing status/skip tests)
- **Test fixtures:** `.claude/skills/backlog/tests/test_backlog_core_parsing.py` (lines ~1072-1148, use existing fixtures)

---

### Discovered During Implementation

_Session Date: 2026-03-12_

During implementation, we discovered that `view_result_from_local_item()` had a slightly different structure than what the architect spec described. The spec characterized the old function as having two distinct phases: lines 791-804 copying fields already on `BacklogItem`, followed by lines 805-814 re-reading the file only for `status`. In reality, the pre-existing function also populated `description`, `source`, `added`, and `raw_body` via direct field copies in the same block — not through a file re-read. The file re-read covered status exclusively.

The implementation cleaned up the entire function body as a coherent unit rather than making a minimal line-splice, resulting in a simpler function that reads naturally from top to bottom with no conditional block. This went slightly beyond the minimum viable change described in section 4.2.2, but achieved the same goal with a cleaner result.

The legacy script (`backlog.py`) confirmed the `_status` key was NOT pre-populated on item dicts during parsing, so the file re-read block was retained for description/source/added/status with only a `# TODO(#612)` comment added for status. This matched the "if NO: leave unchanged" path in the requirements.

**Key Discoveries:**

1. **`view_result_from_local_item()` cleanup scope**: The spec described a minimal splice (replace lines 805-814 with one line). The actual implementation simplified the entire function body. The end state is functionally identical but structurally cleaner. Future changes to this function do not need to work around intermediate block boundaries — the function is now a flat sequence of field assignments.

2. **Legacy script item dict gaps**: The `backlog.py` untyped dict items do not carry `_status` (or `_description`, `_source`, `_added`). The file re-read in `_view_result_from_local_item()` is load-bearing for all four fields. Full elimination requires either backfilling these keys during item dict construction (in the legacy parse path) or migrating callers to the `backlog_core` module. This is tracked by the `# TODO(#612)` comment at line 1894.

3. **No `Intent Source` metadata in plan artifacts**: The feature-context and architect spec for this feature do not contain `Intent Source` headers (pre-policy artifacts). Per the plan artifact lifecycle policy, intent-divergence classification is skipped — all divergences default to design-refinement.

#### Updated Technical Details

- `view_result_from_local_item()` final shape (parsing.py lines 786-808): single `ViewItemResult(...)` constructor call followed by direct field assignments for description, source, added, raw_body, status — no conditional blocks, no file I/O
- Legacy `_view_result_from_local_item()` (backlog.py lines 1883-1896): file re-read block retained intact; `# TODO(#612): status not available on item dict; re-read still needed` added at line 1894 before the status assignment

#### Gotchas for Future Developers

- The architect spec's line number references for `view_result_from_local_item()` (lines 791-804 and 805-814) do not correspond to the post-implementation line numbers. The function body is now shorter. Use grep/search to locate the function, not line numbers.
- The legacy `backlog.py` script has a parallel `_view_result_from_local_item()` that is architecturally decoupled from `backlog_core`. Any future cleanup of the file re-read pattern there requires modifying the item dict construction phase in the legacy parse path, not just the view function.

---
task: T2
title: Add test coverage for BacklogItem status field population
status: complete
completed: 2026-03-12T02:35:00Z
agent: python-pytest-architect
dependencies:
  - T1
priority: 2
complexity: low
accuracy-risk: low
skills:
  - python3-development
  - fastmcp-python-tests
parallelize-with: []
started: "2026-03-12T02:29:10Z"
---

## Context

Task T1 adds the `status` field to `BacklogItem` and updates `parse_item_file()` and `view_result_from_local_item()`. This task adds test coverage for the new behavior. Existing test fixtures (`_NESTED_META_FRONTMATTER` and `_FLAT_FRONTMATTER` in `test_backlog_core_parsing.py`) already contain `status: open` in their frontmatter.

Architecture spec: `plan/architect-add-status-field-to-backlogitem-model.md` (section 7)

## Objective

Add tests that verify `BacklogItem.status` is populated correctly during parsing and used correctly in `view_result_from_local_item()`.

## Inputs

- `.claude/skills/backlog/tests/test_backlog_core_parsing.py` -- existing test file with fixtures and conventions
- Architecture spec section 7.2 for required test cases
- Existing test naming pattern: `test_[function]_[scenario]_[expected_outcome]`

## Requirements

### parse_item_file status tests

1. Test that nested-metadata frontmatter with `status: open` produces `item.status == "open"`
2. Test that flat frontmatter with `status: Done` produces `item.status == "Done"` (case preserved)
3. Test that plain text input (no frontmatter) produces `item.status == ""`
4. Test that frontmatter without a status key produces `item.status == ""`
5. Test that `status: resolved` produces both `item.status == "resolved"` and `item.skip is True` (consistency check)

### view_result_from_local_item status tests

6. Test that `BacklogItem(status="open")` produces `result.status == "open"` without file I/O
7. Test that `BacklogItem()` (default) produces `result.status == ""`
8. Test that `BacklogItem(status="open", file_path="/nonexistent/path")` produces `result.status == "open"` (regression: old code would fail on nonexistent file)

## Constraints

- Follow existing test naming convention: `test_[function]_[scenario]_[expected_outcome]`
- Use existing test fixtures where applicable (`_NESTED_META_FRONTMATTER`, `_FLAT_FRONTMATTER`)
- Do not modify existing tests
- Place new tests after existing related tests in the file

## Expected Outputs

- File modified: `.claude/skills/backlog/tests/test_backlog_core_parsing.py`

## Acceptance Criteria

1. At least 5 new tests for `parse_item_file` status field behavior exist
2. At least 3 new tests for `view_result_from_local_item` status behavior exist
3. All new tests pass
4. All pre-existing tests continue to pass
5. Test for nonexistent file path confirms no `FileNotFoundError` is raised (regression test)

## Verification Steps

1. Run: `uv run pytest .claude/skills/backlog/tests/test_backlog_core_parsing.py -x -q`
2. Run: `uv run pytest .claude/skills/backlog/tests/test_backlog_core_parsing.py -k "status" -v` (confirm new tests are discovered and pass)
3. Run: `uv run pytest .claude/skills/backlog/tests/ -x -q` (full test suite)

## Handoff

Return:
- List of test function names added
- Full pytest output showing all tests pass
- Any pre-existing test failures found (report as-is, do not fix unless directly related)
