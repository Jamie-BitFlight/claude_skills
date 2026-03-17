"""Tests for sam_schema.readers.normalize — format normalization and status mapping.

Tests: Status coercion, dependency parsing, gap detection, lenient normalization.
How: Construct raw dicts and normalize to Pydantic models; verify coerced values.
Why: Normalization is the bridge between arbitrary reader output and the validated
model layer. Incorrect coercion silently corrupts task state.
"""

from __future__ import annotations

import pathlib

import pytest
from sam_schema.core.models import TaskStatus
from sam_schema.readers.detect import FormatType
from sam_schema.readers.normalize import (
    _normalize_status,
    detect_gaps,
    normalize_plan,
    normalize_task,
    normalize_task_lenient,
)

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# normalize_task — required fields
# ---------------------------------------------------------------------------


def test_normalize_task_valid_dict_returns_task_model():
    raw = {"task": "T1", "title": "A task", "status": "not-started"}
    task, _gaps = normalize_task(raw, FormatType.YAML_FRONTMATTER)
    assert task.id == "T1"
    assert task.title == "A task"


def test_normalize_task_missing_task_id_raises_value_error():
    raw = {"title": "No ID", "status": "not-started"}
    with pytest.raises(ValueError, match="missing required"):
        normalize_task(raw, FormatType.YAML_FRONTMATTER)


def test_normalize_task_missing_title_raises_value_error():
    raw = {"task": "T1", "status": "not-started"}
    with pytest.raises(ValueError, match="missing required"):
        normalize_task(raw, FormatType.YAML_FRONTMATTER)


def test_normalize_task_accepts_id_key_as_alias_for_task():
    raw = {"id": "T2", "title": "Using id key", "status": "complete"}
    task, _ = normalize_task(raw, FormatType.PURE_YAML)
    assert task.id == "T2"


def test_normalize_task_accepts_task_id_key_as_alias():
    raw = {"task_id": "3", "title": "Using task_id", "status": "not-started"}
    task, _ = normalize_task(raw, FormatType.LEGACY_MARKDOWN)
    assert task.id == "3"


# ---------------------------------------------------------------------------
# normalize_task — status normalization
# ---------------------------------------------------------------------------


def test_normalize_task_canonical_status_preserved():
    raw = {"task": "T1", "title": "T", "status": "in-progress"}
    task, _ = normalize_task(raw, FormatType.PURE_YAML)
    assert task.status == TaskStatus.IN_PROGRESS


def test_normalize_task_space_separated_status_mapped():
    raw = {"task": "T1", "title": "T", "status": "NOT STARTED"}
    task, _ = normalize_task(raw, FormatType.LEGACY_MARKDOWN)
    assert task.status == TaskStatus.NOT_STARTED


def test_normalize_task_emoji_complete_status_mapped():
    raw = {"task": "T1", "title": "T", "status": ":white_check_mark: COMPLETE"}
    task, _ = normalize_task(raw, FormatType.LEGACY_MARKDOWN)
    assert task.status == TaskStatus.COMPLETE


def test_normalize_task_emoji_in_progress_status_mapped():
    raw = {"task": "T1", "title": "T", "status": ":arrows_counterclockwise: IN PROGRESS"}
    task, _ = normalize_task(raw, FormatType.LEGACY_MARKDOWN)
    assert task.status == TaskStatus.IN_PROGRESS


def test_normalize_task_unknown_status_raises_value_error():
    """Unrecognized status strings must raise ValueError, not silently default.

    Silently defaulting to not-started would cause completed tasks to be
    re-dispatched if a status value has a typo.
    """
    raw = {"task": "T1", "title": "T", "status": "INVENTED_STATUS"}
    with pytest.raises(ValueError, match="Unrecognized status"):
        normalize_task(raw, FormatType.LEGACY_MARKDOWN)


def test_normalize_task_none_status_defaults_to_not_started():
    raw = {"task": "T1", "title": "T", "status": None}
    task, _ = normalize_task(raw, FormatType.YAML_FRONTMATTER)
    assert task.status == TaskStatus.NOT_STARTED


# ---------------------------------------------------------------------------
# _normalize_status — ValueError for unrecognized values
# ---------------------------------------------------------------------------


def test_normalize_status_raises_for_unrecognized_string() -> None:
    """_normalize_status raises ValueError for arbitrary unrecognized strings.

    Tests: Root-cause fix for silent status normalization fallback.
    How: Call _normalize_status with a value not in TaskStatus or STATUS_MAP.
    Why: Silently defaulting to not-started could cause completed tasks to be
    re-dispatched if the status field contains a typo.
    """
    with pytest.raises(ValueError, match="Unrecognized status"):
        _normalize_status("typo-value")


def test_normalize_status_raises_for_wont_fix_which_lacks_task_status_member() -> None:
    """_normalize_status raises ValueError when STATUS_MAP maps to a non-TaskStatus value.

    Tests: STATUS_MAP entries that resolve to values not in TaskStatus.
    How: 'WONT FIX' maps to 'wont-fix' which has no TaskStatus member.
    Why: The mapped value must be a valid TaskStatus, not just any string.
    """
    with pytest.raises(ValueError, match="Unrecognized status"):
        _normalize_status("WONT FIX")


def test_normalize_status_none_returns_not_started() -> None:
    """_normalize_status returns 'not-started' for None (field not provided).

    Tests: Explicit None handling in _normalize_status.
    How: Pass None, expect 'not-started'.
    Why: Absence of a status field is a valid condition meaning 'not yet started'.
    """
    result = _normalize_status(None)
    assert result == "not-started"


def test_normalize_status_valid_canonical_value_returned() -> None:
    """_normalize_status returns canonical form for known values.

    Tests: Happy-path for canonical status strings.
    How: Pass 'in-progress', expect 'in-progress'.
    Why: Validate that normal values are not disturbed by the refactor.
    """
    assert _normalize_status("in-progress") == "in-progress"
    assert _normalize_status("complete") == "complete"
    assert _normalize_status("blocked") == "blocked"


# ---------------------------------------------------------------------------
# normalize_task — dependency cleaning (legacy prefix stripping)
# ---------------------------------------------------------------------------


def test_normalize_task_strips_task_prefix_from_dependencies():
    raw = {"task": "2", "title": "T", "status": "not-started", "dependencies": ["Task 1"]}
    task, _ = normalize_task(raw, FormatType.LEGACY_MARKDOWN)
    assert task.dependencies == ["1"]


def test_normalize_task_strips_task_prefix_case_insensitive():
    raw = {"task": "3", "title": "T", "status": "not-started", "dependencies": ["task 1", "TASK 2"]}
    task, _ = normalize_task(raw, FormatType.LEGACY_MARKDOWN)
    assert task.dependencies == ["1", "2"]


def test_normalize_task_bare_id_dependencies_unchanged():
    raw = {"task": "T2", "title": "T", "status": "not-started", "dependencies": ["T1"]}
    task, _ = normalize_task(raw, FormatType.PURE_YAML)
    assert task.dependencies == ["T1"]


# ---------------------------------------------------------------------------
# normalize_task — schema gaps
# ---------------------------------------------------------------------------


def test_normalize_task_non_canonical_format_reports_gaps():
    raw = {"task": "T1", "title": "T", "status": "not-started"}
    _, gaps = normalize_task(raw, FormatType.LEGACY_MARKDOWN)
    assert len(gaps) > 0


def test_normalize_task_canonical_format_reports_no_gaps():
    raw = {"task": "T1", "title": "T", "status": "not-started"}
    _, gaps = normalize_task(raw, FormatType.PURE_YAML)
    assert gaps == []


def test_normalize_task_gap_field_names_are_canonical():
    raw = {"task": "T1", "title": "T", "status": "not-started"}
    _, gaps = normalize_task(raw, FormatType.LEGACY_MARKDOWN)
    field_names = {g.field_name for g in gaps}
    # "agent" is one of the tracked optional fields
    assert "agent" in field_names


def test_normalize_task_present_optional_field_not_reported_as_gap():
    raw = {"task": "T1", "title": "T", "status": "not-started", "agent": "some-agent", "priority": 1}
    _, gaps = normalize_task(raw, FormatType.LEGACY_MARKDOWN)
    gap_fields = {g.field_name for g in gaps}
    assert "agent" not in gap_fields
    assert "priority" not in gap_fields


# ---------------------------------------------------------------------------
# normalize_task_lenient
# ---------------------------------------------------------------------------


def test_normalize_task_lenient_invalid_dict_returns_none_and_gap():
    """normalize_task_lenient returns a SchemaGap describing the failure, never an empty list."""
    raw = {"title": "No ID", "status": "not-started"}  # missing task id
    task, gaps = normalize_task_lenient(raw, FormatType.YAML_FRONTMATTER)
    assert task is None
    assert len(gaps) >= 1
    assert gaps[0].gap_type == "invalid_value"


def test_normalize_task_lenient_valid_dict_returns_task():
    raw = {"task": "T1", "title": "OK", "status": "complete"}
    task, _ = normalize_task_lenient(raw, FormatType.PURE_YAML)
    assert task is not None
    assert task.id == "T1"


# ---------------------------------------------------------------------------
# normalize_plan — end-to-end from fixture files
# ---------------------------------------------------------------------------


def test_normalize_plan_pure_yaml_single_produces_three_tasks():
    from sam_schema.readers.yaml_reader import read_yaml_plan

    path = _FIXTURES / "pure_yaml_single.yaml"
    plan_meta, task_dicts, fmt = read_yaml_plan(path)
    result = normalize_plan(plan_meta, task_dicts, fmt, path)
    assert len(result.plan.tasks) == 3


def test_normalize_plan_pure_yaml_single_has_no_gaps():
    from sam_schema.readers.yaml_reader import read_yaml_plan

    path = _FIXTURES / "pure_yaml_single.yaml"
    plan_meta, task_dicts, fmt = read_yaml_plan(path)
    result = normalize_plan(plan_meta, task_dicts, fmt, path)
    assert result.gaps == []


def test_normalize_plan_legacy_markdown_produces_three_tasks():
    from sam_schema.readers.legacy_reader import read_legacy_plan

    path = _FIXTURES / "legacy_markdown.md"
    plan_meta, task_dicts, fmt = read_legacy_plan(path)
    result = normalize_plan(plan_meta, task_dicts, fmt, path)
    assert len(result.plan.tasks) == 3


def test_normalize_plan_legacy_markdown_produces_schema_gaps():
    from sam_schema.readers.legacy_reader import read_legacy_plan

    path = _FIXTURES / "legacy_markdown.md"
    plan_meta, task_dicts, fmt = read_legacy_plan(path)
    result = normalize_plan(plan_meta, task_dicts, fmt, path)
    assert len(result.gaps) > 0


def test_normalize_plan_global_manifest_produces_four_tasks():
    from sam_schema.readers.manifest_reader import read_manifest_plan

    path = _FIXTURES / "global_manifest.md"
    plan_meta, task_dicts, fmt = read_manifest_plan(path)
    result = normalize_plan(plan_meta, task_dicts, fmt, path)
    assert len(result.plan.tasks) == 4


def test_normalize_plan_frontmatter_multi_produces_three_tasks():
    from sam_schema.readers.frontmatter_reader import read_frontmatter_plan

    path = _FIXTURES / "yaml_frontmatter_multi.md"
    plan_meta, task_dicts, fmt = read_frontmatter_plan(path)
    result = normalize_plan(plan_meta, task_dicts, fmt, path)
    assert len(result.plan.tasks) == 3


def test_normalize_plan_feature_set_on_plan_model():
    from sam_schema.readers.yaml_reader import read_yaml_plan

    path = _FIXTURES / "pure_yaml_single.yaml"
    plan_meta, task_dicts, fmt = read_yaml_plan(path)
    result = normalize_plan(plan_meta, task_dicts, fmt, path)
    assert result.plan.feature == "auth-system"


def test_normalize_plan_missing_feature_raises_value_error():
    raw_meta: dict = {}
    with pytest.raises(ValueError, match="feature"):
        normalize_plan(raw_meta, [], FormatType.PURE_YAML, pathlib.Path("/fake"))


def test_normalize_plan_derives_slug_from_tasks_filename_when_metadata_has_no_feature() -> None:
    """Slug is extracted from filename when plan_meta lacks 'feature' and 'slug'.

    Tests: Filename-based slug derivation for auto-generated follow-up files.
    How: Pass empty plan_meta with a path matching 'tasks-N-slug.md' convention.
    Why: Code-reviewer-generated follow-up files have a tasks: list but no
    feature: key.  normalize_plan must derive the slug from the filename instead
    of raising ValueError.
    """
    # Arrange
    raw_meta: dict = {"tasks": []}  # no 'feature' or 'slug' key
    task_dicts = [{"task": "T1", "title": "A task", "status": "not-started"}]
    path = pathlib.Path("/plan/tasks-3-unified-sam-task-schema.md")

    # Act
    result = normalize_plan(raw_meta, task_dicts, FormatType.YAML_FRONTMATTER, path)

    # Assert
    assert result.plan.feature == "unified-sam-task-schema"


def test_normalize_plan_derives_slug_from_followup_filename() -> None:
    """Slug for a followup file retains the '-followup-K' suffix as part of the slug.

    Tests: Filename derivation for 'tasks-N-slug-followup-K.md' naming.
    How: Pass empty plan_meta with a followup path.
    Why: Follow-up files carry 'followup-K' in the name; the full suffix after
    'tasks-N-' is used as the feature slug to distinguish from the parent.
    """
    # Arrange
    raw_meta: dict = {}
    path = pathlib.Path("/plan/tasks-3-unified-sam-task-schema-followup-1.md")

    # Act
    result = normalize_plan(raw_meta, [], FormatType.YAML_FRONTMATTER, path)

    # Assert
    assert result.plan.feature == "unified-sam-task-schema-followup-1"


def test_normalize_plan_raises_when_filename_does_not_match_convention() -> None:
    """ValueError raised when metadata has no feature AND filename is non-standard.

    Tests: Both metadata and filename derivation fail.
    How: Pass empty plan_meta with a filename that has no 'tasks-N-' prefix.
    Why: If neither source can provide the slug, raising is correct — there is no
    safe value to default to.
    """
    # Arrange
    raw_meta: dict = {}
    path = pathlib.Path("/plan/unknown-file.md")

    # Act / Assert
    with pytest.raises(ValueError, match="feature"):
        normalize_plan(raw_meta, [], FormatType.PURE_YAML, path)


# ---------------------------------------------------------------------------
# normalize_plan — lenient invalid task ID handling
# ---------------------------------------------------------------------------


def test_normalize_plan_invalid_task_id_recorded_as_gap_not_abort():
    # Task IDs like T10a do not match ^[A-Za-z]?\d+(\.\d+)?$
    raw_meta = {"feature": "test"}
    task_dicts = [
        {"task": "T10a", "title": "Invalid ID task", "status": "not-started"},
        {"task": "T1", "title": "Valid task", "status": "not-started"},
    ]
    result = normalize_plan(raw_meta, task_dicts, FormatType.YAML_FRONTMATTER, pathlib.Path("/fake"))
    # Valid task is still included
    assert len(result.plan.tasks) == 1
    assert result.plan.tasks[0].id == "T1"
    # Invalid ID is recorded as a schema gap
    invalid_gaps = [g for g in result.gaps if g.task_id == "T10a"]
    assert len(invalid_gaps) >= 1


def test_normalize_plan_invalid_task_gap_has_invalid_value_gap_type():
    raw_meta = {"feature": "test"}
    task_dicts = [{"task": "T10b", "title": "Bad", "status": "not-started"}]
    result = normalize_plan(raw_meta, task_dicts, FormatType.YAML_FRONTMATTER, pathlib.Path("/fake"))
    gap = next(g for g in result.gaps if g.task_id == "T10b")
    assert gap.gap_type == "invalid_value"


# ---------------------------------------------------------------------------
# normalize_plan — malformed fixture: missing required title
# ---------------------------------------------------------------------------


def test_normalize_plan_malformed_missing_title_records_gap():
    from sam_schema.readers.yaml_reader import read_yaml_plan

    path = _FIXTURES / "malformed" / "missing_required.yaml"
    plan_meta, task_dicts, fmt = read_yaml_plan(path)
    result = normalize_plan(plan_meta, task_dicts, fmt, path)
    # T1 has no title — must be recorded as gap, not abort
    assert result.plan.tasks == []
    assert len(result.gaps) >= 1


# ---------------------------------------------------------------------------
# normalize_plan — malformed fixture: invalid status falls back, not abort
# ---------------------------------------------------------------------------


def test_normalize_plan_malformed_invalid_status_recorded_as_gap():
    """Invalid status values are recorded as gaps, not silently defaulted.

    Silently defaulting 'started' to 'not-started' could cause a running task
    to be re-dispatched. The correct behavior is to reject the task and report
    a schema gap so the caller can inspect and fix the data.
    """
    from sam_schema.readers.yaml_reader import read_yaml_plan

    path = _FIXTURES / "malformed" / "invalid_status.yaml"
    plan_meta, task_dicts, fmt = read_yaml_plan(path)
    result = normalize_plan(plan_meta, task_dicts, fmt, path)
    # "started" is not in TaskStatus — task is rejected and recorded as gap
    assert result.plan.tasks == []
    assert len(result.gaps) >= 1
    assert any("T1" in g.task_id for g in result.gaps)


# ---------------------------------------------------------------------------
# detect_gaps — public API (unconditional gap analysis)
# ---------------------------------------------------------------------------


def test_detect_gaps_reports_missing_agent() -> None:
    """Verify detect_gaps reports missing 'agent' field unconditionally.

    Tests: Public detect_gaps function.
    How: Pass a raw dict without 'agent', check gap list.
    Why: detect_gaps is the public API for unconditional gap analysis,
    distinct from the internal _detect_gaps that filters by format.
    """
    raw: dict = {"task": "T1", "title": "T", "status": "not-started"}
    gaps = detect_gaps(raw, "T1")
    field_names = {g.field_name for g in gaps}
    assert "agent" in field_names


def test_detect_gaps_does_not_report_present_field() -> None:
    """Verify detect_gaps skips fields that are present.

    Tests: detect_gaps with fields populated.
    How: Include 'agent' in raw dict, verify it is not in gaps.
    Why: Correct gap detection must not flag present fields.
    """
    raw: dict = {"task": "T1", "title": "T", "status": "not-started", "agent": "some-agent"}
    gaps = detect_gaps(raw, "T1")
    field_names = {g.field_name for g in gaps}
    assert "agent" not in field_names


def test_detect_gaps_accepts_snake_case_variant() -> None:
    """Verify detect_gaps recognizes snake_case field names.

    Tests: detect_gaps snake_case alias handling.
    How: Include 'blocked_by' instead of 'blocked-by', verify not flagged.
    Why: Some readers produce snake_case keys; both must be accepted.
    """
    raw: dict = {"task": "T1", "title": "T", "status": "not-started", "blocked_by": []}
    gaps = detect_gaps(raw, "T1")
    field_names = {g.field_name for g in gaps}
    assert "blocked-by" not in field_names


# ---------------------------------------------------------------------------
# normalize_task — title alias via 'name' key
# ---------------------------------------------------------------------------


def test_normalize_task_accepts_name_as_title_alias() -> None:
    """Verify 'name' key is accepted as alias for 'title'.

    Tests: Backward compatibility alias for title field.
    How: Pass raw dict with 'name' instead of 'title'.
    Why: Some legacy formats use 'name' instead of 'title'.
    """
    raw: dict = {"task": "T1", "name": "Named task", "status": "not-started"}
    task, _ = normalize_task(raw, FormatType.LEGACY_MARKDOWN)
    assert task.title == "Named task"


# ---------------------------------------------------------------------------
# normalize_task — title-based status override ([DEFERRED], [SKIPPED])
# ---------------------------------------------------------------------------


def test_normalize_task_deferred_title_prefix_overrides_status() -> None:
    """Verify [DEFERRED] title prefix overrides stored status.

    Tests: Title-marker-based status override.
    How: Pass raw dict with title starting with '[DEFERRED]'.
    Why: Legacy tasks may mark status only in the title prefix.
    """
    raw: dict = {"task": "T1", "title": "[DEFERRED] Some task", "status": "not-started"}
    task, _ = normalize_task(raw, FormatType.LEGACY_MARKDOWN)
    assert task.status == TaskStatus.DEFERRED


def test_normalize_task_skipped_title_prefix_overrides_status() -> None:
    """Verify [SKIPPED] title prefix overrides stored status.

    Tests: Title-marker-based status override.
    How: Pass raw dict with title starting with '[SKIPPED]'.
    Why: Legacy tasks may mark status only in the title prefix.
    """
    raw: dict = {"task": "T1", "title": "[SKIPPED] Obsolete task", "status": "in-progress"}
    task, _ = normalize_task(raw, FormatType.LEGACY_MARKDOWN)
    assert task.status == TaskStatus.SKIPPED


# ---------------------------------------------------------------------------
# normalize_task — status map edge cases (lowercase after mapping)
# ---------------------------------------------------------------------------


def test_normalize_task_status_direct_emoji_token_mapped() -> None:
    """Verify bare emoji token in STATUS_MAP is mapped correctly.

    Tests: Direct STATUS_MAP key lookup for emoji tokens.
    How: Pass ':x:' as status value.
    Why: Emoji tokens like ':x:' are direct STATUS_MAP keys.
    """
    raw: dict = {"task": "T1", "title": "T", "status": ":x:"}
    task, _ = normalize_task(raw, FormatType.LEGACY_MARKDOWN)
    assert task.status == TaskStatus.NOT_STARTED


def test_normalize_task_case_insensitive_blocked_mapped() -> None:
    """Verify case-insensitive status like 'blocked' works.

    Tests: Case-insensitive status normalization.
    How: Pass lowercase 'blocked' (already canonical).
    Why: YAML readers may produce lowercase strings directly.
    """
    raw: dict = {"task": "T1", "title": "T", "status": "blocked"}
    task, _ = normalize_task(raw, FormatType.YAML_FRONTMATTER)
    assert task.status == TaskStatus.BLOCKED


def test_normalize_task_deferred_space_separated_mapped() -> None:
    """Verify 'DEFERRED' (uppercase space-separated variant) is mapped.

    Tests: STATUS_MAP uppercase lookup.
    How: Pass 'DEFERRED' as status.
    Why: Legacy markdown uses uppercase status labels.
    """
    raw: dict = {"task": "T1", "title": "T", "status": "DEFERRED"}
    task, _ = normalize_task(raw, FormatType.LEGACY_MARKDOWN)
    assert task.status == TaskStatus.DEFERRED


def test_normalize_task_wont_fix_status_raises_value_error() -> None:
    """Verify 'WONT FIX' raises ValueError because 'wont-fix' is not in TaskStatus.

    Tests: STATUS_MAP entry that maps to an unrecognized final status.
    How: Pass 'WONT FIX' as status, expect ValueError.
    Why: 'WONT FIX' maps to 'wont-fix' via STATUS_MAP but TaskStatus has no
    WONT_FIX member. The function must raise rather than silently falling back.
    """
    raw: dict = {"task": "T1", "title": "T", "status": "WONT FIX"}
    with pytest.raises(ValueError, match="Unrecognized status"):
        normalize_task(raw, FormatType.LEGACY_MARKDOWN)


# ---------------------------------------------------------------------------
# normalize_plan — slug key accepted for feature
# ---------------------------------------------------------------------------


def test_normalize_plan_slug_key_accepted_as_feature() -> None:
    """Verify 'slug' key in plan_meta is accepted as 'feature'.

    Tests: Feature name from 'slug' key.
    How: Pass plan_meta with 'slug' instead of 'feature'.
    Why: Global manifest format uses 'slug' field.
    """
    raw_meta: dict = {"slug": "my-feature"}
    task_dicts = [{"task": "T1", "title": "A task", "status": "not-started"}]
    result = normalize_plan(raw_meta, task_dicts, FormatType.GLOBAL_MANIFEST, pathlib.Path("/fake"))
    assert result.plan.feature == "my-feature"


# ---------------------------------------------------------------------------
# normalize_plan — acceptance_criteria list coercion
# ---------------------------------------------------------------------------


def test_normalize_plan_acceptance_criteria_as_list_joined_with_newlines() -> None:
    """acceptance-criteria YAML list is joined into a single string.

    Tests: List -> str coercion for acceptance_criteria Plan field.
    How: Pass plan_meta with 'acceptance-criteria' as a list; verify the
         resulting Plan.acceptance_criteria is a newline-joined string.
    Why: Some task files store acceptance-criteria as a YAML bullet list.
         Plan.acceptance_criteria is str | None; passing a list raises
         ValidationError without this coercion.
    """
    # Arrange
    raw_meta: dict = {
        "feature": "test-feature",
        "acceptance-criteria": ["Criterion one", "Criterion two", "Criterion three"],
    }

    # Act
    result = normalize_plan(raw_meta, [], FormatType.PURE_YAML, pathlib.Path("/fake/tasks-1-test-feature.md"))

    # Assert
    assert result.plan.acceptance_criteria == "Criterion one\nCriterion two\nCriterion three"


def test_normalize_plan_acceptance_criteria_as_string_preserved() -> None:
    """acceptance-criteria plain string is passed through unchanged.

    Tests: No regression for string acceptance_criteria values.
    How: Pass plan_meta with 'acceptance-criteria' as a plain string.
    Why: Coercion must not corrupt existing string values.
    """
    # Arrange
    raw_meta: dict = {"feature": "test-feature", "acceptance-criteria": "Single criterion as plain string."}

    # Act
    result = normalize_plan(raw_meta, [], FormatType.PURE_YAML, pathlib.Path("/fake/tasks-1-test-feature.md"))

    # Assert
    assert result.plan.acceptance_criteria == "Single criterion as plain string."


def test_normalize_plan_acceptance_criteria_snake_case_list_coerced() -> None:
    """acceptance_criteria (snake_case) list is joined with newlines.

    Tests: Snake-case variant of acceptance_criteria coercion.
    How: Pass 'acceptance_criteria' (underscore) as a list.
    Why: Both kebab-case and snake_case keys must be handled.
    """
    # Arrange
    raw_meta: dict = {"feature": "test-feature", "acceptance_criteria": ["Item A", "Item B"]}

    # Act
    result = normalize_plan(raw_meta, [], FormatType.PURE_YAML, pathlib.Path("/fake/tasks-1-test-feature.md"))

    # Assert
    assert result.plan.acceptance_criteria == "Item A\nItem B"


def test_normalize_plan_acceptance_criteria_empty_list_becomes_none() -> None:
    """Empty acceptance-criteria list is normalised to None.

    Tests: Empty list -> None coercion for acceptance_criteria.
    How: Pass plan_meta with 'acceptance-criteria' as an empty list.
    Why: An empty list is semantically equivalent to no criteria and must not
         result in an empty string being stored on the Plan model.
    """
    # Arrange
    raw_meta: dict = {"feature": "test-feature", "acceptance-criteria": []}

    # Act
    result = normalize_plan(raw_meta, [], FormatType.PURE_YAML, pathlib.Path("/fake/tasks-1-test-feature.md"))

    # Assert
    assert result.plan.acceptance_criteria is None


def test_normalize_plan_goal_as_list_coerced() -> None:
    """goal YAML list is joined into a single string.

    Tests: List -> str coercion for goal Plan field.
    How: Pass plan_meta with 'goal' as a list.
    Why: goal is str | None and can appear as a YAML list in task files.
    """
    # Arrange
    raw_meta: dict = {"feature": "test-feature", "goal": ["Deliver X", "Deliver Y"]}

    # Act
    result = normalize_plan(raw_meta, [], FormatType.PURE_YAML, pathlib.Path("/fake/tasks-1-test-feature.md"))

    # Assert
    assert result.plan.goal == "Deliver X\nDeliver Y"


# ---------------------------------------------------------------------------
# normalize_task — task-level list coercion for str fields
# Regression tests for: tasks containing acceptance_criteria /
# verification_steps as YAML lists being silently dropped.
# ---------------------------------------------------------------------------


def test_normalize_task_acceptance_criteria_as_list_coerced_to_str():
    """acceptance_criteria YAML list is joined into a newline-separated string.

    Tests: list -> str coercion for Task.acceptance_criteria.
    How: Pass raw dict with acceptance_criteria as list[str].
    Why: Plan files authored by agents write acceptance_criteria as YAML bullet
    lists. Before the fix, Pydantic raised ValidationError on list input for a
    str field, causing the task to be silently dropped in normalize_plan().
    """
    # Arrange
    raw = {
        "id": "T1",
        "title": "A task",
        "status": "not-started",
        "acceptance_criteria": ["Criterion A", "Criterion B"],
    }

    # Act
    task, gaps = normalize_task(raw, FormatType.PURE_YAML)

    # Assert
    assert task.id == "T1"
    assert task.acceptance_criteria == "Criterion A\nCriterion B"
    assert gaps == []


def test_normalize_task_verification_steps_as_list_coerced_to_str():
    """verification_steps YAML list is joined into a newline-separated string.

    Tests: list -> str coercion for Task.verification_steps.
    How: Pass raw dict with verification_steps as list[str].
    Why: Same silent-drop root cause as acceptance_criteria.
    """
    # Arrange
    raw = {"id": "T1", "title": "A task", "status": "not-started", "verification_steps": ["Step 1", "Step 2", "Step 3"]}

    # Act
    task, gaps = normalize_task(raw, FormatType.PURE_YAML)

    # Assert
    assert task.id == "T1"
    assert task.verification_steps == "Step 1\nStep 2\nStep 3"
    assert gaps == []


def test_normalize_task_list_fields_do_not_cause_task_drop_in_plan():
    """Tasks with acceptance_criteria / verification_steps as lists are not dropped.

    Tests: normalize_plan() retains all tasks when str fields arrive as lists.
    How: Feed normalize_plan() two task dicts with list-valued str fields.
    Why: Root cause of P699 — normalize_plan() silently continued on
    ValidationError, yielding tasks=[] instead of tasks=[T1, T2].
    """
    # Arrange
    task_dicts = [
        {
            "id": "T1",
            "title": "Task one",
            "status": "not-started",
            "acceptance_criteria": ["AC1", "AC2"],
            "verification_steps": ["VS1"],
        },
        {
            "id": "T2",
            "title": "Task two",
            "status": "not-started",
            "acceptance_criteria": ["AC3"],
            "verification_steps": ["VS2", "VS3"],
        },
    ]
    plan_meta: dict = {"feature": "regression-test"}

    # Act
    result = normalize_plan(plan_meta, task_dicts, FormatType.PURE_YAML, pathlib.Path("/fake/P699-regression.yaml"))

    # Assert — both tasks must be present, not silently dropped
    assert len(result.plan.tasks) == 2
    assert result.plan.tasks[0].id == "T1"
    assert result.plan.tasks[0].acceptance_criteria == "AC1\nAC2"
    assert result.plan.tasks[1].id == "T2"
    assert result.plan.tasks[1].verification_steps == "VS2\nVS3"


def test_normalize_task_kebab_case_acceptance_criteria_as_list_coerced_to_str():
    """acceptance-criteria (kebab-case key) YAML list is coerced to str.

    Tests: list -> str coercion honours the kebab-case alias.
    How: Pass raw dict with 'acceptance-criteria' (not snake_case) as list[str].
    Why: YAML files use kebab-case keys; both forms must be coerced before
    Pydantic validation.
    """
    # Arrange
    raw = {
        "id": "T1",
        "title": "A task",
        "status": "not-started",
        "acceptance-criteria": ["Criterion A", "Criterion B"],
        "verification-steps": ["Step 1"],
    }

    # Act
    task, _gaps = normalize_task(raw, FormatType.PURE_YAML)

    # Assert
    assert task.acceptance_criteria == "Criterion A\nCriterion B"
    assert task.verification_steps == "Step 1"
