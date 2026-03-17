---
tasks:
  - task: "Add MCP server tests and fix silent status normalization fallback"
    status: pending
    parent_task: "plan/tasks-2-unified-sam-task-schema.md"
---

# Task: Add MCP Server Tests and Fix Silent Status Normalization

## Parent Task
- Original: `plan/tasks-2-unified-sam-task-schema.md`
- Review Date: 2026-03-14

## Status
- [ ] Pending

## Priority
Medium

## Description
Two issues found during code review of the `sam_schema` package:

1. **MCP server has zero test coverage** — `server.py` (42 statements) is entirely untested. While it delegates to the tested query layer, the error handling pattern (`except Exception: return {"error": ...}`) and parameter routing are unverified.

2. **Silent status normalization fallback** — `_normalize_status()` in `readers/normalize.py:88-89` silently defaults unrecognized status strings to `"not-started"`. This violates the project's silent failure prevention rule and could cause completed tasks to be re-dispatched if a status value has a typo. The function should either raise `ValueError` for unrecognized values or emit a `SchemaGap` record.

3. **`normalize_task_lenient` returns empty gaps on failure** — When `normalize_task_lenient()` catches a `ValueError`, it returns `(None, [])` with no gap information. It should return at least one `SchemaGap` documenting the failure reason.

## Acceptance Criteria
- [ ] `tests/test_server.py` exists with tests for all four MCP tools (`sam_read`, `sam_state`, `sam_ready`, `sam_status`)
- [ ] MCP server error handling is tested: invalid plan addresses, missing tasks, invalid status values
- [ ] `_normalize_status()` raises `ValueError` or returns a `SchemaGap` for unrecognized status strings instead of silently defaulting
- [ ] `normalize_task_lenient()` includes failure information in the returned `SchemaGap` list
- [ ] Existing 358 tests continue to pass
- [ ] Coverage on `server.py` reaches at least 80%

## Files to Modify
- `packages/sam_schema/tests/test_server.py` — new file with MCP server tests
- `packages/sam_schema/sam_schema/readers/normalize.py:43-89` — fix `_normalize_status` fallback
- `packages/sam_schema/sam_schema/readers/normalize.py:245-261` — fix `normalize_task_lenient` gap reporting
- `packages/sam_schema/tests/test_readers/test_normalize.py` — add tests for unrecognized status values

## Verification Steps
1. `cd packages/sam_schema && uv run pytest tests/ -v --tb=short` — all tests pass
2. `cd packages/sam_schema && uv run pytest tests/test_server.py -v` — server tests exist and pass
3. `cd packages/sam_schema && uv run pytest --cov=sam_schema --cov-report=term-missing` — server.py coverage >= 80%
4. `uv run python -c "from sam_schema.readers.normalize import _normalize_status; _normalize_status('typo-value')"` — should raise ValueError or return with gap

## References
- Review report: `.claude/reports/review-unified-sam-task-schema-2026-03-14.md`
- Silent failure prevention rule: `.claude/rules/silent-failure-prevention.md`
- Architecture spec security section: `plan/architect-unified-sam-task-schema.md` section 6
