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
status: not-started
agent: python-cli-architect
dependencies: []
priority: 1
complexity: low
accuracy-risk: low
skills:
  - python3-development
parallelize-with: []
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
task: T2
title: Add test coverage for BacklogItem status field population
status: not-started
agent: python-cli-architect
dependencies:
  - T1
priority: 2
complexity: low
accuracy-risk: low
skills:
  - python3-development
  - fastmcp-python-tests
parallelize-with: []
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
