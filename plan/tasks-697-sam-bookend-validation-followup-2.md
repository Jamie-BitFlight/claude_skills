---
tasks:
  - task: "Add bookend field round-trip integration test for readers/writers"
    status: pending
    parent_task: "plan/tasks-5-sam-bookend-validation.md"
---

# Task: Add bookend round-trip integration test

## Parent Task
- Original: `plan/tasks-5-sam-bookend-validation.md`
- Review Date: 2026-03-15

## Status
- [ ] Pending

## Priority
Low

## Description
The writer correctly handles `is-bookend` and `bookend-type` in its default-value omit logic (`yaml_writer.py:51-52, 332-338`), and reader tests cover `acceptance-criteria-structured` parsing. However, there is no explicit integration test that writes a plan with bookend tasks and re-reads it, verifying that `is_bookend=True` and `bookend_type="t0-baseline"` survive the round trip. The existing `plan_with_bookends.yaml` fixture is used in reader tests, but a write-then-read round-trip test would catch serialization bugs (e.g., if the writer omitted the field because it matched the default, or if the reader failed to parse it back).

## Acceptance Criteria
- [ ] Integration test writes a Plan with T0 and TN bookend tasks to YAML, reads it back, and asserts `is_bookend` and `bookend_type` are preserved
- [ ] Test covers both single-file and directory write modes
- [ ] Test verifies `acceptance_criteria_structured` round-trips correctly alongside bookend tasks

## Files to Modify
- `packages/sam_schema/tests/test_writers/test_yaml_writer.py` - Add round-trip test class
- `packages/sam_schema/tests/test_readers/test_yaml_reader.py` - Optional: add complementary read-from-written-output test

## Verification Steps
1. `cd packages/sam_schema && uv run pytest tests/test_writers/test_yaml_writer.py -k bookend -v`
2. `cd packages/sam_schema && uv run pytest tests/ -v --tb=short`

## References
- Original review: SAM bookend validation code review 2026-03-15
- Writer defaults: `packages/sam_schema/sam_schema/writers/yaml_writer.py:51-52`
- Fixture: `packages/sam_schema/tests/fixtures/plan_with_bookends.yaml`
