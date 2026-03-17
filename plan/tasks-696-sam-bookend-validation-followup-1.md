---
tasks:
  - task: "Constrain Task.bookend_type to enum instead of bare str"
    status: pending
    parent_task: "plan/tasks-5-sam-bookend-validation.md"
---

# Task: Constrain bookend_type to enum values

## Parent Task
- Original: `plan/tasks-5-sam-bookend-validation.md`
- Review Date: 2026-03-15

## Status
- [ ] Pending

## Priority
Medium

## Description
`Task.bookend_type` is typed as `str | None` in `packages/sam_schema/sam_schema/core/models.py:141`, but the TASK_FILE_FORMAT.md JSON schema (line 490) specifies `"enum": ["t0-baseline", "tn-verification"]`. The Pydantic model accepts any arbitrary string, so an invalid value like `bookend_type="foo"` passes validation silently. `BookendValidator.validate()` checks for exact string matches (`"t0-baseline"`, `"tn-verification"`), meaning a typo would create a task that is invisible to the validator — neither detected as a T0 nor as a TN — producing no validation error but also no bookend behavior.

The fix is to create a `BookendType(StrEnum)` with members `T0_BASELINE = "t0-baseline"` and `TN_VERIFICATION = "tn-verification"`, and change the field type to `BookendType | None`. This aligns the runtime validation with the documented schema.

## Acceptance Criteria
- [ ] `BookendType` StrEnum exists in `models.py` with values `t0-baseline` and `tn-verification`
- [ ] `Task.bookend_type` field type changed from `str | None` to `BookendType | None`
- [ ] `BookendValidator` uses enum members instead of string literals for comparisons
- [ ] Invalid `bookend_type` values raise `ValidationError` during model construction
- [ ] Existing tests pass; new test added for invalid bookend_type rejection
- [ ] `BookendType` exported from `__init__.py` and added to `__all__`

## Files to Modify
- `packages/sam_schema/sam_schema/core/models.py:141` - Change field type, add enum class
- `packages/sam_schema/sam_schema/core/dependencies.py:250,261` - Use enum members instead of string literals
- `packages/sam_schema/sam_schema/__init__.py` - Export `BookendType`
- `packages/sam_schema/tests/test_models.py` - Add test for invalid bookend_type
- `packages/sam_schema/tests/test_dependencies.py` - Verify enum usage in validator helpers

## Verification Steps
1. `cd packages/sam_schema && uv run pytest tests/test_core/test_models.py -k bookend -v`
2. `cd packages/sam_schema && uv run pytest tests/test_dependencies.py -k bookend -v`
3. `cd packages/sam_schema && uv run ruff check sam_schema/`
4. `python -c "from sam_schema import BookendType; print(BookendType.T0_BASELINE)"`

## References
- Original review: SAM bookend validation code review 2026-03-15
- Related code: `packages/sam_schema/sam_schema/core/models.py`
- Schema spec: `.claude/docs/TASK_FILE_FORMAT.md` line 490
