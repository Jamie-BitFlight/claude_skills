---
tasks:
  - task: "Replace remaining duplicated dict-based functions in backlog.py with core imports plus adapters"
    status: pending
    parent_task: "plan/tasks-1-backlog-cli-dedup.md"
---

# Task: Replace Remaining Duplicated Functions in backlog.py

## Parent Task
- Original: `plan/tasks-1-backlog-cli-dedup.md`
- Review Date: 2026-03-12

## Status
- [ ] Pending

## Priority
Medium

## Description

The initial dedup pass (Issue #611) successfully replaced 12 constants and 6 Category A functions with imports from `backlog_core/`. However, several functions in `backlog.py` remain as local reimplementations rather than delegating to their core equivalents. These represent continued duplication that undermines the dedup goal.

**Functions still locally reimplemented (should be adapter wrappers around core imports):**

1. `_find_fuzzy_duplicates` (line 359) -- The architecture spec classified this as Category A (direct import), but the implementation is a full local reimplementation operating on `list[dict]`. It should import `find_fuzzy_duplicates` from `backlog_core.parsing` and wrap it with dict-to-BacklogItem conversion, consistent with how `find_item` was handled.

2. `_build_issue_body_from_file` (line 438) -- ADR-004 specified a one-line re-export alias (`_build_issue_body_from_file = _build_issue_body`), but the implementation is a standalone local function reading dict keys. It should delegate to `backlog_core.parsing.build_issue_body_from_file` with a dict-to-BacklogItem adapter.

3. `items_needing_issues` (line 416) and `items_with_issues` (line 425) -- Both have core equivalents in `backlog_core/parsing.py` that accept `list[BacklogItem]`. The CLI versions accept `list[dict]`. These should follow the same adapter pattern as `find_item`.

4. `_parse_issue_selector` (line 305) -- Identical logic to `backlog_core.parsing.parse_issue_selector`. This is a pure Category A function that can be replaced with a direct import alias.

5. `_issue_to_local_fields` (line 512) and `_fetch_open_issues_by_title` (line 398) -- These have core equivalents in `backlog_core/github.py` (`issue_to_local_fields`, `fetch_open_issues_by_title`). The CLI versions should be replaced with imports plus thin wrappers if signature differences exist.

## Acceptance Criteria
- [ ] `_find_fuzzy_duplicates` in backlog.py delegates to `backlog_core.parsing.find_fuzzy_duplicates` with dict/BacklogItem conversion
- [ ] `_build_issue_body_from_file` in backlog.py delegates to `backlog_core.parsing.build_issue_body_from_file` with dict/BacklogItem conversion
- [ ] `items_needing_issues` and `items_with_issues` in backlog.py delegate to core equivalents
- [ ] `_parse_issue_selector` replaced with import alias from `backlog_core.parsing.parse_issue_selector`
- [ ] `_issue_to_local_fields` and `_fetch_open_issues_by_title` delegate to core equivalents
- [ ] All 582 tests continue to pass
- [ ] No behavioral changes (adapter wrappers preserve dict interface for CLI callers)

## Files to Modify
- `.claude/skills/backlog/scripts/backlog.py:305-395` -- Replace `_parse_issue_selector`, `_find_fuzzy_duplicates` with core imports/adapters
- `.claude/skills/backlog/scripts/backlog.py:416-431` -- Replace `items_needing_issues`, `items_with_issues` with core imports/adapters
- `.claude/skills/backlog/scripts/backlog.py:438-457` -- Replace `_build_issue_body_from_file` with core delegation
- `.claude/skills/backlog/scripts/backlog.py:512-545` -- Replace `_issue_to_local_fields` with core import/adapter

## Verification Steps
1. `uv run pytest .claude/skills/backlog/tests/ -x -q` -- all 582+ tests pass
2. `uv run .claude/skills/backlog/scripts/backlog.py list` -- CLI smoke test
3. `grep -c "def _find_fuzzy_duplicates\|def _parse_issue_selector\|def _build_issue_body_from_file\|def items_needing_issues\|def items_with_issues\|def _issue_to_local_fields\|def _fetch_open_issues_by_title" .claude/skills/backlog/scripts/backlog.py` -- should be 0 (all replaced with imports)

## References
- Original review: code-reviewer phase of `/complete-implementation`
- Architecture spec: `plan/architect-backlog-cli-dedup.md` (Section 4.3, ADR-004)
- Related code: `.claude/skills/backlog/scripts/backlog.py`, `.claude/skills/backlog/backlog_core/parsing.py`
