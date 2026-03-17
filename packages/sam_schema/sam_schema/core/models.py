"""Pydantic models for SAM task/plan schema.

Canonical data model for SAM (Structured Agent-Managed) task/plan files.
All format-specific readers normalize to these models.
"""

from __future__ import annotations

import re
from enum import IntEnum, StrEnum
from typing import TYPE_CHECKING

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

# Task ID pattern: supports numeric (1, 1.1), alphanumeric (T1, T2.3),
# letter-suffixed (T10a, T10b), and slash-separated compound IDs (P1/T3, T10a/T10b).
TASK_ID_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z]?\d+(\.\d+)?[A-Za-z]?(/[A-Za-z]?\d+(\.\d+)?[A-Za-z]?)?$")

# Status normalization map — maps human-readable and emoji variants to canonical values.
# Sourced from task_format.py:28-45 (plugins/python3-development/skills/implementation-manager/scripts/)
STATUS_MAP: dict[str, str] = {
    # Space-separated variants
    "NOT STARTED": "not-started",
    "IN PROGRESS": "in-progress",
    "COMPLETE": "complete",
    "BLOCKED": "blocked",
    "DEFERRED": "deferred",
    "SKIPPED": "skipped",
    "WONT FIX": "wont-fix",
    # Lowercase single-word variants (used in follow-up task files)
    "pending": "not-started",
    "todo": "not-started",
    "done": "complete",
    "in_progress": "in-progress",
    # Emoji token variants (Rich emoji names)
    ":x:": "not-started",
    ":white_check_mark:": "complete",
    ":arrows_counterclockwise:": "in-progress",
    # Legacy title-marker variants (uppercase)
    "[DEFERRED]": "deferred",
    "[SKIPPED]": "skipped",
}


class TaskStatus(StrEnum):
    """Lifecycle status values for a SAM task."""

    NOT_STARTED = "not-started"
    IN_PROGRESS = "in-progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    DEFERRED = "deferred"
    SKIPPED = "skipped"


class Complexity(StrEnum):
    """Complexity estimate for a task."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Priority(IntEnum):
    """Priority ordering for a task. Lower value = higher priority."""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    LOWEST = 5


class IssueClassification(StrEnum):
    """Root-cause classification for issues tracked as tasks."""

    PROCEDURAL = "procedural"
    DEFECT = "defect"
    RECURRING_PATTERN = "recurring-pattern"
    MISSING_GUARDRAIL = "missing-guardrail"
    UNBOUNDED_DESIGN = "unbounded-design"


class AnalysisMethod(StrEnum):
    """Analysis method applied during investigation."""

    NONE = "none"
    FIVE_WHYS = "5-whys"
    SIX_SIGMA = "6-sigma"
    DESIGN_FRAMING = "design-framing"


class BookendType(StrEnum):
    """Bookend task type — constrains the two allowed values for ``Task.bookend_type``.

    Values mirror the JSON schema enum defined in TASK_FILE_FORMAT.md §490.
    """

    T0_BASELINE = "t0-baseline"
    TN_VERIFICATION = "tn-verification"


class Task(BaseModel):
    """Canonical task model. All format-specific readers normalize to this.

    Field aliases map YAML kebab-case names to Python snake_case attributes.
    Both the alias and the Python name are accepted during construction because
    ``populate_by_name=True`` is set in ``model_config``.
    """

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    # Required fields
    id: str = Field(..., pattern=r"^[A-Za-z]?\d+(\.\d+)?$")
    title: str = Field(..., min_length=1, max_length=200)
    status: TaskStatus

    # Optional structural fields
    agent: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    priority: Priority = Priority.MEDIUM
    complexity: Complexity = Complexity.MEDIUM
    skills: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("blocked-by", "blocked_by"),
        serialization_alias="blocked-by",
    )
    parallelize_with: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("parallelize-with", "parallelize_with"),
        serialization_alias="parallelize-with",
    )

    # Timestamps
    created: datetime | None = None
    started: datetime | None = None
    completed: datetime | None = None
    last_activity: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("last-activity", "last_activity"),
        serialization_alias="last-activity",
    )

    # Analytical metadata
    issue_classification: IssueClassification | None = Field(
        default=None,
        validation_alias=AliasChoices("issue-classification", "issue_classification"),
        serialization_alias="issue-classification",
    )
    scenario_target: str | None = Field(
        default=None,
        validation_alias=AliasChoices("scenario-target", "scenario_target"),
        serialization_alias="scenario-target",
    )
    analysis_method: AnalysisMethod = Field(
        default=AnalysisMethod.NONE,
        validation_alias=AliasChoices("analysis-method", "analysis_method"),
        serialization_alias="analysis-method",
    )
    divergence_notes: int = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices("divergence-notes", "divergence_notes"),
        serialization_alias="divergence-notes",
    )

    # Markdown content fields (stored as YAML multiline scalars in canonical format)
    description: str = ""
    objective: str = ""
    requirements: str = ""
    constraints: str = ""
    expected_outputs: str = Field(
        default="",
        validation_alias=AliasChoices("expected-outputs", "expected_outputs"),
        serialization_alias="expected-outputs",
    )
    acceptance_criteria: str = Field(
        default="",
        validation_alias=AliasChoices("acceptance-criteria", "acceptance_criteria"),
        serialization_alias="acceptance-criteria",
    )
    verification_steps: str = Field(
        default="",
        validation_alias=AliasChoices("verification-steps", "verification_steps"),
        serialization_alias="verification-steps",
    )
    context_notes: str = Field(
        default="", validation_alias=AliasChoices("context-notes", "context_notes"), serialization_alias="context-notes"
    )
    handoff: str = ""

    # Bookend metadata
    is_bookend: bool = Field(
        default=False, validation_alias=AliasChoices("is-bookend", "is_bookend"), serialization_alias="is-bookend"
    )
    bookend_type: BookendType | None = Field(
        default=None, validation_alias=AliasChoices("bookend-type", "bookend_type"), serialization_alias="bookend-type"
    )

    # GitHub integration
    github_issue: int | None = Field(
        default=None, validation_alias=AliasChoices("github-issue", "github_issue"), serialization_alias="github-issue"
    )

    @field_validator("dependencies", "parallelize_with", mode="before")
    @classmethod
    def validate_task_id_list(cls, v: object) -> list[str]:
        r"""Validate that each item in a task ID list matches the task ID pattern.

        Args:
            v: Raw value from YAML or constructor. Accepts list[str], comma-separated
               string, or None.

        Returns:
            Normalized list of validated task ID strings.

        Raises:
            ValueError: If any item does not match ``^[A-Za-z]?\\d+(\\.\\d+)?$``.
        """
        if v is None:
            return []
        if isinstance(v, str):
            if not v or v.lower() in {"none", "n/a", "-"}:
                return []
            items = [item.strip() for item in v.split(",") if item.strip()]
        elif isinstance(v, list):
            items = [str(item) for item in v if item is not None]
        else:
            return []

        for item in items:
            if not TASK_ID_PATTERN.match(item):
                msg = f"Invalid task ID '{item}': must match pattern {TASK_ID_PATTERN.pattern}"
                raise ValueError(msg)
        return items


class Plan(BaseModel):
    """Canonical plan model containing metadata and all tasks.

    A plan corresponds to a single SAM task/plan file (or directory).

    Field aliases map YAML kebab-case names to Python snake_case attributes.
    Both the alias and the Python name are accepted during construction because
    ``populate_by_name=True`` is set in ``model_config``.
    """

    model_config = ConfigDict(populate_by_name=True)

    feature: str
    version: str = "1.0"
    description: str = ""

    # Plan-level context fields (multiline markdown)
    goal: str | None = None
    context: str | None = None
    acceptance_criteria: str | None = Field(
        default=None,
        validation_alias=AliasChoices("acceptance-criteria", "acceptance_criteria"),
        serialization_alias="acceptance-criteria",
    )
    acceptance_criteria_structured: list[AcceptanceCriterion] = Field(
        default_factory=list,
        validation_alias=AliasChoices("acceptance-criteria-structured", "acceptance_criteria_structured"),
        serialization_alias="acceptance-criteria-structured",
    )

    # Plan-level reference fields
    issue: str | None = None
    architecture: str | None = None
    feature_context: str | None = Field(
        default=None,
        validation_alias=AliasChoices("feature-context", "feature_context"),
        serialization_alias="feature-context",
    )
    codebase_patterns: str | None = Field(
        default=None,
        validation_alias=AliasChoices("codebase-patterns", "codebase_patterns"),
        serialization_alias="codebase-patterns",
    )

    tasks: list[Task] = Field(default_factory=list)
    source_path: Path | None = None
    source_format: str | None = None  # FormatType value

    @field_validator("issue", mode="before")
    @classmethod
    def coerce_issue_to_str(cls, v: object) -> str | None:
        """Coerce the ``issue`` field to a string.

        YAML parses bare integers (e.g. ``issue: 42``) as ``int``.  The field
        is semantically a GitHub issue reference such as ``"#42"`` or ``"42"``,
        so any non-None value is coerced to ``str`` here.

        Args:
            v: Raw value from YAML or constructor.

        Returns:
            String representation, or ``None`` if the input is ``None``.
        """
        if v is None:
            return None
        return str(v)


class CriterionStatus(StrEnum):
    """Status of a single acceptance criterion after T0/TN comparison."""

    PASSED = "passed"
    REGRESSED = "regressed"
    PRE_EXISTING_FAIL = "pre-existing-fail"
    NEWLY_PASSING = "newly-passing"


class AcceptanceCriterion(BaseModel):
    """A single structured acceptance criterion with an executable check command.

    Stored in ``Plan.acceptance_criteria_structured``.  The T0 and TN bookend
    agents iterate over this list to capture and compare baseline vs. final state.
    """

    model_config = ConfigDict(populate_by_name=True)

    criterion_id: str = Field(
        ..., validation_alias=AliasChoices("criterion-id", "criterion_id"), serialization_alias="criterion-id"
    )
    description: str = ""
    check_command: str = Field(
        ..., validation_alias=AliasChoices("check-command", "check_command"), serialization_alias="check-command"
    )
    expected_baseline: str = Field(
        default="any",
        validation_alias=AliasChoices("expected-baseline", "expected_baseline"),
        serialization_alias="expected-baseline",
    )
    expected_final: str = Field(
        default="pass",
        validation_alias=AliasChoices("expected-final", "expected_final"),
        serialization_alias="expected-final",
    )


class BookendResult(BaseModel):
    """Result of running a single acceptance criterion check command.

    Written to ``plan/T0-baseline-{slug}.yaml`` by the T0 bookend agent, and
    re-captured to ``plan/TN-verification-{slug}.yaml`` by the TN bookend agent.
    """

    model_config = ConfigDict(populate_by_name=True)

    criterion_id: str = Field(
        ..., validation_alias=AliasChoices("criterion-id", "criterion_id"), serialization_alias="criterion-id"
    )
    check_command: str = Field(
        ..., validation_alias=AliasChoices("check-command", "check_command"), serialization_alias="check-command"
    )
    exit_code: int = Field(
        ..., validation_alias=AliasChoices("exit-code", "exit_code"), serialization_alias="exit-code"
    )
    stdout: str = ""
    stderr: str = ""
    timestamp: str = ""
    duration_seconds: float = Field(
        default=0.0,
        validation_alias=AliasChoices("duration-seconds", "duration_seconds"),
        serialization_alias="duration-seconds",
    )


class BookendVerification(BaseModel):
    """Per-criterion comparison between T0 baseline and TN final results.

    Written to ``plan/TN-verification-{slug}.yaml``.  The ``status`` field
    encodes the 4-cell matrix: passed / regressed / pre-existing-fail /
    newly-passing.
    """

    model_config = ConfigDict(populate_by_name=True)

    criterion_id: str = Field(
        ..., validation_alias=AliasChoices("criterion-id", "criterion_id"), serialization_alias="criterion-id"
    )
    check_command: str = Field(
        ..., validation_alias=AliasChoices("check-command", "check_command"), serialization_alias="check-command"
    )
    t0_exit_code: int = Field(
        ..., validation_alias=AliasChoices("t0-exit-code", "t0_exit_code"), serialization_alias="t0-exit-code"
    )
    tn_exit_code: int = Field(
        ..., validation_alias=AliasChoices("tn-exit-code", "tn_exit_code"), serialization_alias="tn-exit-code"
    )
    status: CriterionStatus
    stdout_diff_summary: str = Field(
        default="",
        validation_alias=AliasChoices("stdout-diff-summary", "stdout_diff_summary"),
        serialization_alias="stdout-diff-summary",
    )


class SchemaGap(BaseModel):
    """A missing or invalid field detected during legacy format reading.

    Schema gaps are reported when reading non-canonical formats (legacy markdown,
    YAML frontmatter in markdown, global manifest) to indicate fields that are
    absent or have unexpected types compared to the canonical schema.
    """

    task_id: str
    field_name: str
    gap_type: str  # "missing" | "invalid_type" | "invalid_value"
    expected: str  # description of expected value/type
    actual: str | None = None  # what was found (None if field is missing)


class ReadResult(BaseModel):
    """Result of reading a plan file. Contains the parsed plan and any schema gaps.

    Schema gaps are populated when reading legacy or non-canonical formats.
    An empty ``gaps`` list indicates the file is in canonical format with all
    expected fields present.
    """

    plan: Plan
    gaps: list[SchemaGap] = Field(default_factory=list)
    source_format: str  # FormatType value
    source_path: Path


class TaskAssignment(BaseModel):
    """Composite response returned by ``sam read P{N}/T{M}``.

    Combines plan-level context (goal, shared context, acceptance criteria)
    with the specific task details, so agents receive everything needed in a
    single call without separate plan-level lookups.

    Per ADR-003: all task dispatches return this shape when a task address is
    provided. Plan-only reads (``sam read P{N}``) continue to return ``Plan``.
    """

    model_config = ConfigDict(populate_by_name=True)

    # Plan-level context fields
    plan_number: str | None = Field(
        default=None,
        validation_alias=AliasChoices("plan-number", "plan_number"),
        serialization_alias="plan-number",
        description="Plan identifier (e.g., 'P1', '719').",
    )
    plan_slug: str | None = Field(
        default=None,
        validation_alias=AliasChoices("plan-slug", "plan_slug"),
        serialization_alias="plan-slug",
        description="Plan slug derived from the feature name.",
    )
    plan_goal: str | None = Field(
        default=None,
        validation_alias=AliasChoices("plan-goal", "plan_goal"),
        serialization_alias="plan-goal",
        description="One-sentence goal statement for the plan.",
    )
    plan_context: str | None = Field(
        default=None,
        validation_alias=AliasChoices("plan-context", "plan_context"),
        serialization_alias="plan-context",
        description="Shared context narrative written by the context-gathering agent.",
    )
    plan_acceptance_criteria: str | None = Field(
        default=None,
        validation_alias=AliasChoices("plan-acceptance-criteria", "plan_acceptance_criteria"),
        serialization_alias="plan-acceptance-criteria",
        description="Plan-level acceptance criteria (free-form markdown string).",
    )

    # The task being assigned
    task: Task = Field(description="The specific task to execute.")


class PlanStatus(BaseModel):
    """Summary of plan execution progress.

    Used by the CLI ``sam status`` command and the ``sam_status`` MCP tool.
    """

    feature: str
    total_tasks: int
    by_status: dict[str, int]  # status value -> count
    ready_tasks: list[str]  # task IDs ready for dispatch
    blocked_tasks: list[dict[str, list[str]]]  # [{task_id: [missing_dep_ids]}]
    completion_pct: float
    has_cycles: bool


# Rebuild models that reference TYPE_CHECKING-guarded types (datetime, Path).
# `from __future__ import annotations` defers annotation evaluation; Pydantic needs
# to resolve these types at model-build time. Pass the types explicitly so Pydantic
# can resolve forward references without requiring runtime imports at the top level.
import datetime as _dt
from pathlib import Path as _Path

Task.model_rebuild(_types_namespace={"datetime": _dt.datetime, "Path": _Path})
Plan.model_rebuild(_types_namespace={"Path": _Path, "Task": Task, "AcceptanceCriterion": AcceptanceCriterion})
ReadResult.model_rebuild(_types_namespace={"Path": _Path, "Plan": Plan, "SchemaGap": SchemaGap})
TaskAssignment.model_rebuild(_types_namespace={"Task": Task})
