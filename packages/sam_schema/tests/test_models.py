"""Tests for sam_schema.core.models — Pydantic model validation and enums.

Tests: Pydantic model validation, alias handling, enum coercion, field validators.
How: Construct models with valid/invalid data, verify validation and coercion.
Why: The Task and Plan models are the canonical data layer — all readers normalize
to them. Incorrect validation rules silently corrupt data downstream.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from sam_schema.core.models import (
    STATUS_MAP,
    TASK_ID_PATTERN,
    AcceptanceCriterion,
    AnalysisMethod,
    BookendResult,
    BookendVerification,
    Complexity,
    CriterionStatus,
    IssueClassification,
    Plan,
    PlanStatus,
    Priority,
    ReadResult,
    SchemaGap,
    Task,
    TaskStatus,
)

# ---------------------------------------------------------------------------
# TaskStatus enum
# ---------------------------------------------------------------------------


class TestTaskStatusEnum:
    """Verify TaskStatus StrEnum members and values.

    Tests: Canonical status values used throughout the SAM pipeline.
    How: Check each member name maps to the expected kebab-case value.
    Why: Status values are stored on disk — mismatch causes silent failures.
    """

    def test_not_started_value(self) -> None:
        """Verify NOT_STARTED maps to 'not-started'."""
        assert TaskStatus.NOT_STARTED == "not-started"

    def test_in_progress_value(self) -> None:
        """Verify IN_PROGRESS maps to 'in-progress'."""
        assert TaskStatus.IN_PROGRESS == "in-progress"

    def test_complete_value(self) -> None:
        """Verify COMPLETE maps to 'complete'."""
        assert TaskStatus.COMPLETE == "complete"

    def test_blocked_value(self) -> None:
        """Verify BLOCKED maps to 'blocked'."""
        assert TaskStatus.BLOCKED == "blocked"

    def test_deferred_value(self) -> None:
        """Verify DEFERRED maps to 'deferred'."""
        assert TaskStatus.DEFERRED == "deferred"

    def test_skipped_value(self) -> None:
        """Verify SKIPPED maps to 'skipped'."""
        assert TaskStatus.SKIPPED == "skipped"

    def test_all_members_count(self) -> None:
        """Verify the total number of status values.

        Tests: TaskStatus completeness.
        How: Count enum members.
        Why: Adding a status without a test means no coverage of its downstream impact.
        """
        assert len(TaskStatus) == 6


# ---------------------------------------------------------------------------
# Complexity enum
# ---------------------------------------------------------------------------


class TestComplexityEnum:
    """Verify Complexity StrEnum values."""

    def test_low_value(self) -> None:
        """Verify LOW maps to 'low'."""
        assert Complexity.LOW == "low"

    def test_medium_value(self) -> None:
        """Verify MEDIUM maps to 'medium'."""
        assert Complexity.MEDIUM == "medium"

    def test_high_value(self) -> None:
        """Verify HIGH maps to 'high'."""
        assert Complexity.HIGH == "high"


# ---------------------------------------------------------------------------
# Priority enum
# ---------------------------------------------------------------------------


class TestPriorityEnum:
    """Verify Priority IntEnum values."""

    def test_critical_value(self) -> None:
        """Verify CRITICAL is 1."""
        assert Priority.CRITICAL == 1

    def test_high_value(self) -> None:
        """Verify HIGH is 2."""
        assert Priority.HIGH == 2

    def test_medium_value(self) -> None:
        """Verify MEDIUM is 3."""
        assert Priority.MEDIUM == 3

    def test_low_value(self) -> None:
        """Verify LOW is 4."""
        assert Priority.LOW == 4

    def test_lowest_value(self) -> None:
        """Verify LOWEST is 5."""
        assert Priority.LOWEST == 5

    def test_priority_ordering(self) -> None:
        """Verify CRITICAL < LOWEST for sort ordering.

        Tests: Priority comparison semantics.
        How: Compare int values directly.
        Why: DependencyGraph sorts by priority — wrong ordering produces wrong dispatch order.
        """
        assert Priority.CRITICAL < Priority.LOWEST


# ---------------------------------------------------------------------------
# IssueClassification and AnalysisMethod enums
# ---------------------------------------------------------------------------


class TestIssueClassification:
    """Verify IssueClassification StrEnum values."""

    def test_procedural_value(self) -> None:
        """Verify PROCEDURAL maps to 'procedural'."""
        assert IssueClassification.PROCEDURAL == "procedural"

    def test_defect_value(self) -> None:
        """Verify DEFECT maps to 'defect'."""
        assert IssueClassification.DEFECT == "defect"

    def test_recurring_pattern_value(self) -> None:
        """Verify RECURRING_PATTERN maps to 'recurring-pattern'."""
        assert IssueClassification.RECURRING_PATTERN == "recurring-pattern"


class TestAnalysisMethod:
    """Verify AnalysisMethod StrEnum values."""

    def test_none_value(self) -> None:
        """Verify NONE maps to 'none'."""
        assert AnalysisMethod.NONE == "none"

    def test_five_whys_value(self) -> None:
        """Verify FIVE_WHYS maps to '5-whys'."""
        assert AnalysisMethod.FIVE_WHYS == "5-whys"


# ---------------------------------------------------------------------------
# TASK_ID_PATTERN
# ---------------------------------------------------------------------------


class TestTaskIdPattern:
    """Verify the TASK_ID_PATTERN regex matches expected patterns.

    Tests: Task ID validation pattern.
    How: Test match/non-match for valid/invalid ID strings.
    Why: Invalid task IDs silently break dependency graph lookups.
    """

    @pytest.mark.parametrize(
        "valid_id",
        [
            # Simple numeric
            "1",
            "42",
            "1.1",
            # Letter-prefixed
            "T1",
            "T2.3",
            "t99",
            # Letter-suffixed (compound IDs with letter suffix)
            "T10a",
            "T10b",
            # Slash-separated compound IDs
            "P1/T3",
            "T10a/T10b",
            "P1/T10a",
        ],
    )
    def test_valid_task_ids_match(self, valid_id: str) -> None:
        """Verify valid task IDs match the pattern."""
        assert TASK_ID_PATTERN.match(valid_id)

    @pytest.mark.parametrize("invalid_id", ["", "TT1", "abc", "T", "1.2.3", "T-1"])
    def test_invalid_task_ids_do_not_match(self, invalid_id: str) -> None:
        """Verify invalid task IDs do not match the pattern."""
        assert not TASK_ID_PATTERN.match(invalid_id)


# ---------------------------------------------------------------------------
# STATUS_MAP
# ---------------------------------------------------------------------------


class TestStatusMap:
    """Verify STATUS_MAP contains expected normalization mappings."""

    def test_not_started_mapping(self) -> None:
        """Verify 'NOT STARTED' maps to 'not-started'."""
        assert STATUS_MAP["NOT STARTED"] == "not-started"

    def test_in_progress_mapping(self) -> None:
        """Verify 'IN PROGRESS' maps to 'in-progress'."""
        assert STATUS_MAP["IN PROGRESS"] == "in-progress"

    def test_complete_mapping(self) -> None:
        """Verify 'COMPLETE' maps to 'complete'."""
        assert STATUS_MAP["COMPLETE"] == "complete"

    def test_emoji_complete_mapping(self) -> None:
        """Verify ':white_check_mark:' emoji maps to 'complete'."""
        assert STATUS_MAP[":white_check_mark:"] == "complete"

    def test_emoji_not_started_mapping(self) -> None:
        """Verify ':x:' emoji maps to 'not-started'."""
        assert STATUS_MAP[":x:"] == "not-started"

    def test_deferred_marker_mapping(self) -> None:
        """Verify '[DEFERRED]' title marker maps to 'deferred'."""
        assert STATUS_MAP["[DEFERRED]"] == "deferred"

    def test_skipped_marker_mapping(self) -> None:
        """Verify '[SKIPPED]' title marker maps to 'skipped'."""
        assert STATUS_MAP["[SKIPPED]"] == "skipped"


# ---------------------------------------------------------------------------
# Task model — required fields
# ---------------------------------------------------------------------------


class TestTaskRequiredFields:
    """Verify Task model required field validation.

    Tests: id, title, status are mandatory and validated.
    How: Construct with valid/missing fields, check ValidationError.
    Why: Missing required fields must fail loud, not silently produce bad models.
    """

    def test_minimal_valid_task(self) -> None:
        """Verify Task with only required fields constructs successfully."""
        task = Task(id="T1", title="A task", status=TaskStatus.NOT_STARTED)
        assert task.id == "T1"
        assert task.title == "A task"
        assert task.status == TaskStatus.NOT_STARTED

    def test_missing_id_raises_validation_error(self) -> None:
        """Verify missing 'id' raises ValidationError."""
        with pytest.raises(ValidationError):
            Task(title="No ID", status=TaskStatus.NOT_STARTED)

    def test_missing_title_raises_validation_error(self) -> None:
        """Verify missing 'title' raises ValidationError."""
        with pytest.raises(ValidationError):
            Task(id="T1", status=TaskStatus.NOT_STARTED)

    def test_missing_status_raises_validation_error(self) -> None:
        """Verify missing 'status' raises ValidationError."""
        with pytest.raises(ValidationError):
            Task(id="T1", title="No status")  # type: ignore[call-arg]

    def test_empty_title_raises_validation_error(self) -> None:
        """Verify empty string title fails min_length=1 validation."""
        with pytest.raises(ValidationError):
            Task(id="T1", title="", status=TaskStatus.NOT_STARTED)

    def test_title_max_length_200_accepts_boundary(self) -> None:
        """Verify a 200-char title is accepted."""
        task = Task(id="T1", title="x" * 200, status=TaskStatus.NOT_STARTED)
        assert len(task.title) == 200

    def test_title_over_max_length_raises_validation_error(self) -> None:
        """Verify a 201-char title is rejected."""
        with pytest.raises(ValidationError):
            Task(id="T1", title="x" * 201, status=TaskStatus.NOT_STARTED)

    def test_invalid_id_pattern_raises_validation_error(self) -> None:
        """Verify an ID not matching the regex pattern is rejected."""
        with pytest.raises(ValidationError):
            Task(id="invalid-id", title="Bad ID", status=TaskStatus.NOT_STARTED)


# ---------------------------------------------------------------------------
# Task model — alias handling
# ---------------------------------------------------------------------------


class TestTaskAliasHandling:
    """Verify Task model populate_by_name and alias behavior.

    Tests: Kebab-case YAML aliases accepted alongside snake_case Python names.
    How: Construct via model_validate with alias keys.
    Why: Readers produce kebab-case dicts from YAML; model must accept both forms.
    """

    def test_populate_by_alias_blocked_by(self) -> None:
        """Verify 'blocked-by' alias populates blocked_by."""
        data = {"id": "T1", "title": "T", "status": "not-started", "blocked-by": ["T2"]}
        task = Task.model_validate(data)
        assert task.blocked_by == ["T2"]

    def test_populate_by_name_blocked_by(self) -> None:
        """Verify 'blocked_by' Python name also works."""
        task = Task.model_validate({"id": "T1", "title": "T", "status": "not-started", "blocked_by": ["T2"]})
        assert task.blocked_by == ["T2"]

    def test_populate_by_alias_last_activity(self) -> None:
        """Verify 'last-activity' alias populates last_activity."""
        ts = datetime.now(UTC)
        data = {"id": "T1", "title": "T", "status": "not-started", "last-activity": ts.isoformat()}
        task = Task.model_validate(data)
        assert task.last_activity is not None

    def test_populate_by_alias_github_issue(self) -> None:
        """Verify 'github-issue' alias populates github_issue."""
        data = {"id": "T1", "title": "T", "status": "not-started", "github-issue": 42}
        task = Task.model_validate(data)
        assert task.github_issue == 42

    def test_populate_by_alias_issue_classification(self) -> None:
        """Verify 'issue-classification' alias populates issue_classification."""
        data = {"id": "T1", "title": "T", "status": "not-started", "issue-classification": "defect"}
        task = Task.model_validate(data)
        assert task.issue_classification == IssueClassification.DEFECT

    def test_populate_by_alias_analysis_method(self) -> None:
        """Verify 'analysis-method' alias populates analysis_method."""
        data = {"id": "T1", "title": "T", "status": "not-started", "analysis-method": "5-whys"}
        task = Task.model_validate(data)
        assert task.analysis_method == AnalysisMethod.FIVE_WHYS

    def test_populate_by_alias_expected_outputs(self) -> None:
        """Verify 'expected-outputs' alias populates expected_outputs."""
        data = {"id": "T1", "title": "T", "status": "not-started", "expected-outputs": "file.py"}
        task = Task.model_validate(data)
        assert task.expected_outputs == "file.py"

    def test_populate_by_alias_divergence_notes(self) -> None:
        """Verify 'divergence-notes' alias populates divergence_notes."""
        data = {"id": "T1", "title": "T", "status": "not-started", "divergence-notes": 3}
        task = Task.model_validate(data)
        assert task.divergence_notes == 3


# ---------------------------------------------------------------------------
# Task model — enum coercion
# ---------------------------------------------------------------------------


class TestTaskEnumCoercion:
    """Verify Task model coerces string values to enum values.

    Tests: use_enum_values in model_config.
    How: Construct with string status, check the stored value type.
    Why: YAML readers pass strings, not enum members — coercion must work.
    """

    def test_status_string_coerced_to_enum_value(self) -> None:
        """Verify 'not-started' string is accepted as TaskStatus."""
        task = Task(id="T1", title="T", status="not-started")  # type: ignore[arg-type]
        assert task.status == TaskStatus.NOT_STARTED

    def test_priority_int_coerced_to_enum_value(self) -> None:
        """Verify integer priority is accepted as Priority."""
        task = Task(id="T1", title="T", status=TaskStatus.NOT_STARTED, priority=Priority(1))
        assert task.priority == Priority.CRITICAL

    def test_complexity_string_coerced_to_enum_value(self) -> None:
        """Verify 'high' string is accepted as Complexity."""
        task = Task(id="T1", title="T", status=TaskStatus.NOT_STARTED, complexity="high")  # type: ignore[arg-type]
        assert task.complexity == Complexity.HIGH


# ---------------------------------------------------------------------------
# Task model — field validators
# ---------------------------------------------------------------------------


class TestTaskFieldValidators:
    """Verify Task.validate_task_id_list field validator.

    Tests: dependencies and parallelize_with accept various input formats.
    How: Pass lists, comma-separated strings, None, and empty markers.
    Why: Legacy and YAML formats produce different dependency representations.
    """

    def test_dependencies_list_input(self) -> None:
        """Verify list of task IDs accepted."""
        task = Task(id="T2", title="T", status=TaskStatus.NOT_STARTED, dependencies=["T1"])
        assert task.dependencies == ["T1"]

    def test_dependencies_comma_separated_string(self) -> None:
        """Verify comma-separated string parsed into list."""
        data = {"id": "T3", "title": "T", "status": "not-started", "dependencies": "T1, T2"}
        task = Task.model_validate(data)
        assert task.dependencies == ["T1", "T2"]

    def test_dependencies_none_returns_empty_list(self) -> None:
        """Verify None dependency returns empty list."""
        data = {"id": "T1", "title": "T", "status": "not-started", "dependencies": None}
        task = Task.model_validate(data)
        assert task.dependencies == []

    def test_dependencies_none_string_returns_empty_list(self) -> None:
        """Verify 'none' string returns empty list."""
        data = {"id": "T1", "title": "T", "status": "not-started", "dependencies": "none"}
        task = Task.model_validate(data)
        assert task.dependencies == []

    def test_dependencies_na_string_returns_empty_list(self) -> None:
        """Verify 'n/a' string returns empty list."""
        data = {"id": "T1", "title": "T", "status": "not-started", "dependencies": "n/a"}
        task = Task.model_validate(data)
        assert task.dependencies == []

    def test_dependencies_dash_string_returns_empty_list(self) -> None:
        """Verify '-' string returns empty list."""
        data = {"id": "T1", "title": "T", "status": "not-started", "dependencies": "-"}
        task = Task.model_validate(data)
        assert task.dependencies == []

    def test_dependencies_empty_string_returns_empty_list(self) -> None:
        """Verify empty string returns empty list."""
        data = {"id": "T1", "title": "T", "status": "not-started", "dependencies": ""}
        task = Task.model_validate(data)
        assert task.dependencies == []

    def test_dependencies_invalid_task_id_raises_validation_error(self) -> None:
        """Verify invalid task ID in dependency list raises ValueError."""
        data = {"id": "T1", "title": "T", "status": "not-started", "dependencies": ["invalid-id"]}
        with pytest.raises(ValidationError):
            Task.model_validate(data)

    def test_dependencies_non_list_non_string_returns_empty(self) -> None:
        """Verify non-list, non-string input returns empty list."""
        data = {"id": "T1", "title": "T", "status": "not-started", "dependencies": 42}
        task = Task.model_validate(data)
        assert task.dependencies == []

    def test_parallelize_with_comma_separated(self) -> None:
        """Verify parallelize_with accepts comma-separated string."""
        data = {"id": "T1", "title": "T", "status": "not-started", "parallelize-with": "T2,T3"}
        task = Task.model_validate(data)
        assert task.parallelize_with == ["T2", "T3"]

    def test_dependencies_list_with_none_items_filtered(self) -> None:
        """Verify None items in dependency list are filtered out."""
        data = {"id": "T1", "title": "T", "status": "not-started", "dependencies": [None, "T2", None]}
        task = Task.model_validate(data)
        assert task.dependencies == ["T2"]


# ---------------------------------------------------------------------------
# Task model — optional field defaults
# ---------------------------------------------------------------------------


class TestTaskDefaults:
    """Verify Task model optional field defaults.

    Tests: Default values for all optional fields.
    How: Construct minimal Task, check defaults.
    Why: Readers may omit fields — defaults must match schema expectations.
    """

    def test_default_agent_is_none(self) -> None:
        """Verify agent defaults to None."""
        task = Task(id="T1", title="T", status=TaskStatus.NOT_STARTED)
        assert task.agent is None

    def test_default_dependencies_is_empty_list(self) -> None:
        """Verify dependencies defaults to empty list."""
        task = Task(id="T1", title="T", status=TaskStatus.NOT_STARTED)
        assert task.dependencies == []

    def test_default_priority_is_medium(self) -> None:
        """Verify priority defaults to MEDIUM (3)."""
        task = Task(id="T1", title="T", status=TaskStatus.NOT_STARTED)
        assert task.priority == Priority.MEDIUM

    def test_default_complexity_is_medium(self) -> None:
        """Verify complexity defaults to MEDIUM."""
        task = Task(id="T1", title="T", status=TaskStatus.NOT_STARTED)
        assert task.complexity == Complexity.MEDIUM

    def test_default_skills_is_empty_list(self) -> None:
        """Verify skills defaults to empty list."""
        task = Task(id="T1", title="T", status=TaskStatus.NOT_STARTED)
        assert task.skills == []

    def test_default_analysis_method_is_none(self) -> None:
        """Verify analysis_method defaults to NONE."""
        task = Task(id="T1", title="T", status=TaskStatus.NOT_STARTED)
        assert task.analysis_method == AnalysisMethod.NONE

    def test_default_divergence_notes_is_zero(self) -> None:
        """Verify divergence_notes defaults to 0."""
        task = Task(id="T1", title="T", status=TaskStatus.NOT_STARTED)
        assert task.divergence_notes == 0

    def test_default_description_is_empty_string(self) -> None:
        """Verify description defaults to empty string."""
        task = Task(id="T1", title="T", status=TaskStatus.NOT_STARTED)
        assert task.description == ""

    def test_default_github_issue_is_none(self) -> None:
        """Verify github_issue defaults to None."""
        task = Task(id="T1", title="T", status=TaskStatus.NOT_STARTED)
        assert task.github_issue is None

    def test_default_started_is_none(self) -> None:
        """Verify started defaults to None."""
        task = Task(id="T1", title="T", status=TaskStatus.NOT_STARTED)
        assert task.started is None


# ---------------------------------------------------------------------------
# Plan model
# ---------------------------------------------------------------------------


class TestPlanModel:
    """Verify Plan model construction and field defaults.

    Tests: Plan-level metadata model.
    How: Construct with valid/minimal data, check fields.
    Why: Plan wraps task lists — wrong defaults break plan-level queries.
    """

    def test_minimal_plan(self) -> None:
        """Verify Plan with only feature field constructs."""
        plan = Plan(feature="test-feature")
        assert plan.feature == "test-feature"
        assert plan.version == "1.0"
        assert plan.tasks == []

    def test_plan_with_tasks(self, sample_plan: Plan) -> None:
        """Verify Plan contains its tasks.

        Tests: Plan task list population.
        How: Use sample_plan fixture.
        Why: Empty task list is a regression indicator.
        """
        assert len(sample_plan.tasks) == 4

    def test_plan_default_description_is_empty(self) -> None:
        """Verify Plan description defaults to empty string."""
        plan = Plan(feature="test")
        assert plan.description == ""

    def test_plan_source_path_default_is_none(self) -> None:
        """Verify source_path defaults to None."""
        plan = Plan(feature="test")
        assert plan.source_path is None


# ---------------------------------------------------------------------------
# SchemaGap model
# ---------------------------------------------------------------------------


class TestSchemaGapModel:
    """Verify SchemaGap model construction.

    Tests: SchemaGap data model for gap reporting.
    How: Construct with valid data, check fields.
    Why: Gap reports are consumed by the normalizer to flag missing fields.
    """

    def test_schema_gap_construction(self) -> None:
        """Verify SchemaGap with all fields."""
        gap = SchemaGap(task_id="T1", field_name="agent", gap_type="missing", expected="Agent name")
        assert gap.task_id == "T1"
        assert gap.field_name == "agent"
        assert gap.gap_type == "missing"
        assert gap.actual is None

    def test_schema_gap_with_actual(self) -> None:
        """Verify SchemaGap with actual value populated."""
        gap = SchemaGap(task_id="T1", field_name="status", gap_type="invalid_type", expected="str", actual="42")
        assert gap.actual == "42"


# ---------------------------------------------------------------------------
# ReadResult model
# ---------------------------------------------------------------------------


class TestReadResultModel:
    """Verify ReadResult model construction.

    Tests: ReadResult wrapping a Plan with gaps and source info.
    How: Construct from Plan, verify all fields.
    Why: ReadResult is the return type from all load operations.
    """

    def test_read_result_construction(self, sample_plan: Plan) -> None:
        """Verify ReadResult wraps a Plan correctly."""
        result = ReadResult(plan=sample_plan, gaps=[], source_format="pure_yaml", source_path=Path("/fake/plan.yaml"))
        assert result.plan.feature == "test-feature"
        assert result.gaps == []
        assert result.source_format == "pure_yaml"

    def test_read_result_with_gaps(self) -> None:
        """Verify ReadResult includes schema gaps."""
        plan = Plan(feature="test")
        gap = SchemaGap(task_id="T1", field_name="agent", gap_type="missing", expected="Agent")
        result = ReadResult(plan=plan, gaps=[gap], source_format="legacy_markdown", source_path=Path("/fake"))
        assert len(result.gaps) == 1


# ---------------------------------------------------------------------------
# PlanStatus model
# ---------------------------------------------------------------------------


class TestPlanStatusModel:
    """Verify PlanStatus model construction.

    Tests: PlanStatus summary model.
    How: Construct with realistic data.
    Why: PlanStatus is consumed by CLI and MCP server for status output.
    """

    def test_plan_status_construction(self) -> None:
        """Verify PlanStatus with all fields."""
        status = PlanStatus(
            feature="test",
            total_tasks=3,
            by_status={"not-started": 1, "complete": 2},
            ready_tasks=["T2"],
            blocked_tasks=[],
            completion_pct=66.7,
            has_cycles=False,
        )
        assert status.feature == "test"
        assert status.total_tasks == 3
        assert abs(status.completion_pct - 66.7) < 0.1
        assert not status.has_cycles


# ---------------------------------------------------------------------------
# CriterionStatus enum
# ---------------------------------------------------------------------------


class TestCriterionStatusEnum:
    """Verify CriterionStatus StrEnum members and values.

    Tests: Bookend criterion status values used in T0/TN comparison.
    How: Check each member name maps to the expected kebab-case value.
    Why: Status values are stored in TN-verification YAML — mismatch causes
    wrong verdict computation.
    """

    def test_passed_value(self) -> None:
        """Verify PASSED maps to 'passed'."""
        assert CriterionStatus.PASSED == "passed"

    def test_regressed_value(self) -> None:
        """Verify REGRESSED maps to 'regressed'."""
        assert CriterionStatus.REGRESSED == "regressed"

    def test_pre_existing_fail_value(self) -> None:
        """Verify PRE_EXISTING_FAIL maps to 'pre-existing-fail'."""
        assert CriterionStatus.PRE_EXISTING_FAIL == "pre-existing-fail"

    def test_newly_passing_value(self) -> None:
        """Verify NEWLY_PASSING maps to 'newly-passing'."""
        assert CriterionStatus.NEWLY_PASSING == "newly-passing"

    def test_all_members_count(self) -> None:
        """Verify the total number of status values.

        Tests: CriterionStatus completeness.
        How: Count enum members.
        Why: Adding a status without a test leaves its downstream impact uncovered.
        """
        assert len(CriterionStatus) == 4

    def test_string_serialization(self) -> None:
        """Verify CriterionStatus members serialize to their string values.

        Tests: StrEnum serialization.
        How: Cast to str and compare.
        Why: YAML writers serialize via str() — wrong output corrupts TN verification files.
        """
        assert str(CriterionStatus.REGRESSED) == "regressed"
        assert str(CriterionStatus.PRE_EXISTING_FAIL) == "pre-existing-fail"


# ---------------------------------------------------------------------------
# AcceptanceCriterion model
# ---------------------------------------------------------------------------


class TestAcceptanceCriterionModel:
    """Verify AcceptanceCriterion Pydantic model construction and aliases.

    Tests: Structured acceptance criteria data model.
    How: Construct with valid/invalid data, verify alias handling and defaults.
    Why: AcceptanceCriterion is parsed from plan YAML — incorrect validation
    silently skips criteria during T0/TN execution.
    """

    def test_construction_with_required_fields(self) -> None:
        """Verify AcceptanceCriterion with only required fields constructs.

        Tests: Minimal valid AcceptanceCriterion.
        How: Provide criterion_id and check_command only.
        Why: Defaults must be correct for optional fields.
        """
        ac = AcceptanceCriterion(criterion_id="AC-1", check_command="uv run pytest -v")
        assert ac.criterion_id == "AC-1"
        assert ac.check_command == "uv run pytest -v"
        assert ac.description == ""
        assert ac.expected_baseline == "any"
        assert ac.expected_final == "pass"

    def test_construction_with_all_fields(self) -> None:
        """Verify AcceptanceCriterion with all fields populated.

        Tests: Full AcceptanceCriterion construction.
        How: Provide every field explicitly.
        Why: All fields must be stored and retrievable.
        """
        ac = AcceptanceCriterion(
            criterion_id="AC-2",
            description="Type checking passes",
            check_command="uv run basedpyright src/",
            expected_baseline="pass",
            expected_final="pass",
        )
        assert ac.criterion_id == "AC-2"
        assert ac.description == "Type checking passes"
        assert ac.expected_baseline == "pass"

    def test_construction_via_kebab_case_aliases(self) -> None:
        """Verify AcceptanceCriterion accepts kebab-case alias keys.

        Tests: YAML kebab-case alias to Python snake_case mapping.
        How: Use model_validate with alias keys from YAML.
        Why: YAML files use kebab-case — model must accept both forms.
        """
        data = {
            "criterion-id": "AC-3",
            "check-command": "uv run ruff check .",
            "expected-baseline": "fail",
            "expected-final": "pass",
        }
        ac = AcceptanceCriterion.model_validate(data)
        assert ac.criterion_id == "AC-3"
        assert ac.check_command == "uv run ruff check ."
        assert ac.expected_baseline == "fail"
        assert ac.expected_final == "pass"

    def test_missing_criterion_id_raises_validation_error(self) -> None:
        """Verify missing criterion_id raises ValidationError.

        Tests: Required field enforcement.
        How: Omit criterion_id from construction.
        Why: Criteria without IDs cannot be tracked across T0/TN.
        """
        with pytest.raises(ValidationError):
            AcceptanceCriterion(check_command="uv run pytest")

    def test_missing_check_command_raises_validation_error(self) -> None:
        """Verify missing check_command raises ValidationError.

        Tests: Required field enforcement.
        How: Omit check_command from construction.
        Why: Criteria without commands cannot be executed by T0/TN agents.
        """
        with pytest.raises(ValidationError):
            AcceptanceCriterion(criterion_id="AC-1")

    def test_model_dump_by_alias(self) -> None:
        """Verify model_dump with by_alias=True produces kebab-case keys.

        Tests: Serialization to YAML-compatible format.
        How: Dump with aliases and check key names.
        Why: YAML writer uses model_dump(by_alias=True) for kebab-case output.
        """
        ac = AcceptanceCriterion(criterion_id="AC-1", check_command="pytest")
        dumped = ac.model_dump(by_alias=True)
        assert "criterion-id" in dumped
        assert "check-command" in dumped
        assert "expected-baseline" in dumped
        assert "expected-final" in dumped

    def test_roundtrip_dump_then_validate(self) -> None:
        """Verify model_dump then model_validate roundtrip preserves data.

        Tests: Serialization/deserialization roundtrip.
        How: Dump to dict, reconstruct from dict, compare.
        Why: Readers and writers compose dump+validate — data loss here is silent.
        """
        original = AcceptanceCriterion(
            criterion_id="AC-5",
            description="Lint clean",
            check_command="uv run ruff check .",
            expected_baseline="pass",
            expected_final="pass",
        )
        dumped = original.model_dump(by_alias=True)
        restored = AcceptanceCriterion.model_validate(dumped)
        assert restored.criterion_id == original.criterion_id
        assert restored.check_command == original.check_command
        assert restored.expected_baseline == original.expected_baseline
        assert restored.expected_final == original.expected_final


# ---------------------------------------------------------------------------
# BookendResult model
# ---------------------------------------------------------------------------


class TestBookendResultModel:
    """Verify BookendResult model construction and serialization.

    Tests: T0/TN command execution result data model.
    How: Construct, serialize, and deserialize BookendResult instances.
    Why: BookendResult is written to T0-baseline YAML and read by TN agent.
    """

    def test_construction_with_required_fields(self) -> None:
        """Verify BookendResult with required fields constructs.

        Tests: Minimal valid BookendResult.
        How: Provide criterion_id, check_command, and exit_code.
        Why: Defaults for optional fields must be correct.
        """
        br = BookendResult(criterion_id="AC-1", check_command="pytest", exit_code=0)
        assert br.criterion_id == "AC-1"
        assert br.check_command == "pytest"
        assert br.exit_code == 0
        assert br.stdout == ""
        assert br.stderr == ""
        assert br.timestamp == ""
        assert br.duration_seconds == pytest.approx(0.0)

    def test_construction_with_all_fields(self) -> None:
        """Verify BookendResult with all fields populated.

        Tests: Full BookendResult construction.
        How: Provide every field explicitly.
        Why: T0 agent captures all fields — they must be stored correctly.
        """
        br = BookendResult(
            criterion_id="AC-1",
            check_command="uv run pytest -v",
            exit_code=1,
            stdout="FAILED 2 tests",
            stderr="error output",
            timestamp="2026-03-15T10:00:00Z",
            duration_seconds=12.5,
        )
        assert br.exit_code == 1
        assert br.stdout == "FAILED 2 tests"
        assert br.stderr == "error output"
        assert br.timestamp == "2026-03-15T10:00:00Z"
        assert br.duration_seconds == pytest.approx(12.5)

    def test_construction_via_kebab_case_aliases(self) -> None:
        """Verify BookendResult accepts kebab-case alias keys.

        Tests: YAML alias compatibility.
        How: Use model_validate with kebab-case keys.
        Why: T0-baseline YAML files use kebab-case field names.
        """
        data = {"criterion-id": "AC-2", "check-command": "basedpyright", "exit-code": 0, "duration-seconds": 3.2}
        br = BookendResult.model_validate(data)
        assert br.criterion_id == "AC-2"
        assert br.exit_code == 0
        assert br.duration_seconds == pytest.approx(3.2)

    def test_roundtrip_dump_then_validate(self) -> None:
        """Verify model_dump then model_validate roundtrip preserves data.

        Tests: Serialization/deserialization roundtrip.
        How: Dump to dict with aliases, reconstruct, compare all fields.
        Why: T0 writes and TN reads these — data loss corrupts verification.
        """
        original = BookendResult(
            criterion_id="AC-1",
            check_command="pytest -v",
            exit_code=1,
            stdout="output",
            stderr="err",
            timestamp="2026-03-15T10:00:00Z",
            duration_seconds=5.0,
        )
        dumped = original.model_dump(by_alias=True)
        restored = BookendResult.model_validate(dumped)
        assert restored.criterion_id == original.criterion_id
        assert restored.exit_code == original.exit_code
        assert restored.stdout == original.stdout
        assert restored.duration_seconds == pytest.approx(original.duration_seconds)


# ---------------------------------------------------------------------------
# BookendVerification model
# ---------------------------------------------------------------------------


class TestBookendVerificationModel:
    """Verify BookendVerification model construction for all 4 status values.

    Tests: Per-criterion T0/TN comparison result model.
    How: Construct with each CriterionStatus value, verify fields.
    Why: BookendVerification drives the TN verdict — wrong status means
    wrong PASS/FAIL decision.
    """

    def test_passed_status(self) -> None:
        """Verify BookendVerification with status=passed.

        Tests: T0 pass + TN pass = passed.
        How: Construct with exit_code 0 for both T0 and TN.
        Why: Passed criteria must not block completion.
        """
        bv = BookendVerification(
            criterion_id="AC-1", check_command="pytest", t0_exit_code=0, tn_exit_code=0, status=CriterionStatus.PASSED
        )
        assert bv.status == CriterionStatus.PASSED
        assert bv.t0_exit_code == 0
        assert bv.tn_exit_code == 0
        assert bv.stdout_diff_summary == ""

    def test_regressed_status(self) -> None:
        """Verify BookendVerification with status=regressed.

        Tests: T0 pass + TN fail = regressed.
        How: Construct with T0 exit 0, TN exit 1.
        Why: Regressed criteria block completion — must be detectable.
        """
        bv = BookendVerification(
            criterion_id="AC-2",
            check_command="basedpyright",
            t0_exit_code=0,
            tn_exit_code=1,
            status=CriterionStatus.REGRESSED,
            stdout_diff_summary="3 new type errors introduced",
        )
        assert bv.status == CriterionStatus.REGRESSED
        assert bv.stdout_diff_summary == "3 new type errors introduced"

    def test_pre_existing_fail_status(self) -> None:
        """Verify BookendVerification with status=pre-existing-fail.

        Tests: T0 fail + TN fail = pre-existing-fail.
        How: Construct with non-zero exit codes for both.
        Why: Pre-existing failures should not block completion.
        """
        bv = BookendVerification(
            criterion_id="AC-3",
            check_command="ruff check",
            t0_exit_code=1,
            tn_exit_code=1,
            status=CriterionStatus.PRE_EXISTING_FAIL,
        )
        assert bv.status == CriterionStatus.PRE_EXISTING_FAIL

    def test_newly_passing_status(self) -> None:
        """Verify BookendVerification with status=newly-passing.

        Tests: T0 fail + TN pass = newly-passing.
        How: Construct with T0 exit 1, TN exit 0.
        Why: Newly passing is a positive signal — must not be confused with regression.
        """
        bv = BookendVerification(
            criterion_id="AC-4",
            check_command="pytest -k integration",
            t0_exit_code=1,
            tn_exit_code=0,
            status=CriterionStatus.NEWLY_PASSING,
        )
        assert bv.status == CriterionStatus.NEWLY_PASSING

    def test_construction_via_kebab_case_aliases(self) -> None:
        """Verify BookendVerification accepts kebab-case alias keys.

        Tests: YAML alias compatibility.
        How: Use model_validate with kebab-case keys.
        Why: TN-verification YAML files use kebab-case field names.
        """
        data = {
            "criterion-id": "AC-1",
            "check-command": "pytest",
            "t0-exit-code": 0,
            "tn-exit-code": 0,
            "status": "passed",
            "stdout-diff-summary": "",
        }
        bv = BookendVerification.model_validate(data)
        assert bv.criterion_id == "AC-1"
        assert bv.t0_exit_code == 0
        assert bv.tn_exit_code == 0
        assert bv.status == CriterionStatus.PASSED

    def test_roundtrip_dump_then_validate(self) -> None:
        """Verify model_dump then model_validate roundtrip preserves data.

        Tests: Serialization/deserialization roundtrip.
        How: Dump to dict with aliases, reconstruct, compare all fields.
        Why: Data integrity across write/read cycles is critical for TN verdict.
        """
        original = BookendVerification(
            criterion_id="AC-1",
            check_command="pytest",
            t0_exit_code=0,
            tn_exit_code=1,
            status=CriterionStatus.REGRESSED,
            stdout_diff_summary="diff content",
        )
        dumped = original.model_dump(by_alias=True)
        restored = BookendVerification.model_validate(dumped)
        assert restored.criterion_id == original.criterion_id
        assert restored.status == original.status
        assert restored.stdout_diff_summary == original.stdout_diff_summary


# ---------------------------------------------------------------------------
# Task bookend fields
# ---------------------------------------------------------------------------


class TestTaskBookendFields:
    """Verify Task model bookend field defaults and construction.

    Tests: is_bookend and bookend_type fields on Task.
    How: Construct tasks with and without bookend fields, verify defaults.
    Why: Bookend fields must default correctly to preserve backward compatibility
    for existing plans without bookend tasks.
    """

    def test_is_bookend_defaults_to_false(self) -> None:
        """Verify is_bookend defaults to False on a minimal Task.

        Tests: Backward compatibility for existing tasks.
        How: Construct minimal Task, check is_bookend default.
        Why: Existing plans must not accidentally become bookend tasks.
        """
        task = Task(id="T1", title="Normal task", status=TaskStatus.NOT_STARTED)
        assert task.is_bookend is False

    def test_bookend_type_defaults_to_none(self) -> None:
        """Verify bookend_type defaults to None on a minimal Task.

        Tests: Backward compatibility for existing tasks.
        How: Construct minimal Task, check bookend_type default.
        Why: None bookend_type means the task is not a bookend.
        """
        task = Task(id="T1", title="Normal task", status=TaskStatus.NOT_STARTED)
        assert task.bookend_type is None

    def test_t0_bookend_task_construction(self) -> None:
        """Verify Task with is_bookend=True and bookend_type='t0-baseline'.

        Tests: T0 baseline task construction.
        How: Construct with bookend fields set for T0.
        Why: T0 tasks must be identifiable by bookend_type field.
        """
        task = Task(
            id="T0",
            title="T0: Capture baseline state",
            status=TaskStatus.NOT_STARTED,
            dependencies=[],
            priority=Priority.CRITICAL,
            complexity=Complexity.LOW,
            is_bookend=True,
            bookend_type="t0-baseline",
        )
        assert task.is_bookend is True
        assert task.bookend_type == "t0-baseline"
        assert task.id == "T0"
        assert task.dependencies == []

    def test_tn_bookend_task_construction(self) -> None:
        """Verify Task with is_bookend=True and bookend_type='tn-verification'.

        Tests: TN verification task construction.
        How: Construct with bookend fields set for TN.
        Why: TN tasks must be identifiable by bookend_type field.
        """
        task = Task(
            id="T99",
            title="TN: Verify implementation",
            status=TaskStatus.NOT_STARTED,
            dependencies=["T1", "T2"],
            priority=Priority.LOWEST,
            complexity=Complexity.LOW,
            is_bookend=True,
            bookend_type="tn-verification",
        )
        assert task.is_bookend is True
        assert task.bookend_type == "tn-verification"
        assert task.dependencies == ["T1", "T2"]

    def test_bookend_fields_via_kebab_case_aliases(self) -> None:
        """Verify bookend fields accept kebab-case alias keys.

        Tests: YAML kebab-case alias mapping for bookend fields.
        How: Use model_validate with kebab-case keys.
        Why: YAML files use kebab-case — both forms must work.
        """
        data = {
            "id": "T0",
            "title": "Baseline",
            "status": "not-started",
            "is-bookend": True,
            "bookend-type": "t0-baseline",
        }
        task = Task.model_validate(data)
        assert task.is_bookend is True
        assert task.bookend_type == "t0-baseline"

    def test_model_dump_excludes_default_bookend_fields(self) -> None:
        """Verify model_dump(exclude_defaults=True) omits default bookend fields.

        Tests: Serialization excludes bookend defaults.
        How: Dump a non-bookend task with exclude_defaults and check keys.
        Why: YAML writer omits default-valued fields — bookend fields must not
        appear in output for non-bookend tasks.
        """
        task = Task(id="T1", title="Normal", status=TaskStatus.NOT_STARTED)
        dumped = task.model_dump(by_alias=True, exclude_defaults=True)
        assert "is-bookend" not in dumped
        assert "bookend-type" not in dumped

    def test_model_dump_includes_set_bookend_fields(self) -> None:
        """Verify model_dump includes bookend fields when explicitly set.

        Tests: Serialization preserves explicitly set bookend fields.
        How: Dump a bookend task and check keys are present.
        Why: YAML writer must output bookend fields for T0/TN tasks.
        """
        task = Task(
            id="T0", title="Baseline", status=TaskStatus.NOT_STARTED, is_bookend=True, bookend_type="t0-baseline"
        )
        dumped = task.model_dump(by_alias=True, exclude_defaults=True)
        assert dumped["is-bookend"] is True
        assert dumped["bookend-type"] == "t0-baseline"

    def test_invalid_bookend_type_raises_validation_error(self) -> None:
        """Verify that an invalid bookend_type value raises ValidationError.

        Tests: BookendType enum constraint on Task.bookend_type.
        How: Construct Task with bookend_type set to an arbitrary string not
             in the enum.
        Why: The Pydantic model must reject values outside the two allowed enum
             members so that a typo cannot create a task invisible to the
             BookendValidator (neither T0 nor TN).
        """
        with pytest.raises(ValidationError):
            Task(id="T0", title="Bad bookend", status=TaskStatus.NOT_STARTED, is_bookend=True, bookend_type="foo")

    def test_bookend_type_enum_member_t0_accepted(self) -> None:
        """Verify BookendType.T0_BASELINE is accepted for bookend_type.

        Tests: Enum member round-trip for T0_BASELINE.
        How: Construct Task using enum member directly.
        Why: Callers using the enum must get the same acceptance as passing
             the string value.
        """
        from sam_schema.core.models import BookendType

        task = Task(
            id="T0",
            title="Baseline",
            status=TaskStatus.NOT_STARTED,
            is_bookend=True,
            bookend_type=BookendType.T0_BASELINE,
        )
        assert task.bookend_type == BookendType.T0_BASELINE

    def test_bookend_type_enum_member_tn_accepted(self) -> None:
        """Verify BookendType.TN_VERIFICATION is accepted for bookend_type.

        Tests: Enum member round-trip for TN_VERIFICATION.
        How: Construct Task using enum member directly.
        Why: Callers using the enum must get the same acceptance as passing
             the string value.
        """
        from sam_schema.core.models import BookendType

        task = Task(
            id="T99",
            title="Verification",
            status=TaskStatus.NOT_STARTED,
            is_bookend=True,
            bookend_type=BookendType.TN_VERIFICATION,
        )
        assert task.bookend_type == BookendType.TN_VERIFICATION


# ---------------------------------------------------------------------------
# Plan.acceptance_criteria_structured
# ---------------------------------------------------------------------------


class TestPlanAcceptanceCriteriaStructured:
    """Verify Plan.acceptance_criteria_structured field behavior.

    Tests: Structured acceptance criteria coexistence with prose field.
    How: Construct Plan with both fields, verify independence.
    Why: The two acceptance criteria fields serve different consumers and
    must not interfere with each other.
    """

    def test_default_is_empty_list(self) -> None:
        """Verify acceptance_criteria_structured defaults to empty list.

        Tests: Backward compatibility for plans without structured criteria.
        How: Construct Plan with no structured criteria.
        Why: Existing plans must not fail when the field is absent.
        """
        plan = Plan(feature="test")
        assert plan.acceptance_criteria_structured == []

    def test_coexistence_with_prose_acceptance_criteria(self) -> None:
        """Verify both acceptance criteria fields can be set independently.

        Tests: Prose and structured criteria independence.
        How: Set both fields, verify both are accessible.
        Why: Prose is for human/agent reading; structured is for T0/TN execution.
        """
        ac = AcceptanceCriterion(criterion_id="AC-1", check_command="pytest")
        plan = Plan(
            feature="test", acceptance_criteria="Tests pass and coverage > 80%", acceptance_criteria_structured=[ac]
        )
        assert plan.acceptance_criteria == "Tests pass and coverage > 80%"
        assert len(plan.acceptance_criteria_structured) == 1
        assert plan.acceptance_criteria_structured[0].criterion_id == "AC-1"

    def test_populated_from_kebab_case_alias(self) -> None:
        """Verify acceptance-criteria-structured alias works via model_validate.

        Tests: YAML alias for structured criteria.
        How: Use model_validate with kebab-case key and list of dicts.
        Why: YAML reader passes raw dicts with kebab-case keys.
        """
        data = {
            "feature": "test",
            "acceptance-criteria-structured": [
                {"criterion-id": "AC-1", "check-command": "pytest"},
                {"criterion-id": "AC-2", "check-command": "ruff check ."},
            ],
        }
        plan = Plan.model_validate(data)
        assert len(plan.acceptance_criteria_structured) == 2
        assert plan.acceptance_criteria_structured[0].criterion_id == "AC-1"
        assert plan.acceptance_criteria_structured[1].check_command == "ruff check ."

    def test_multiple_criteria_preserved(self) -> None:
        """Verify multiple AcceptanceCriterion objects are stored correctly.

        Tests: List population with multiple items.
        How: Construct Plan with 3 criteria, verify all are present.
        Why: Plans may have many criteria — none should be lost.
        """
        criteria = [AcceptanceCriterion(criterion_id=f"AC-{i}", check_command=f"cmd-{i}") for i in range(1, 4)]
        plan = Plan(feature="test", acceptance_criteria_structured=criteria)
        assert len(plan.acceptance_criteria_structured) == 3
        assert plan.acceptance_criteria_structured[2].criterion_id == "AC-3"
