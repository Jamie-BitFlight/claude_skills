"""Typed, eagerly validated inputs for the SAM CLI boundary."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from sam_schema.core.action_models import AppendTaskConfig, CreatePlanConfig, TaskDefinition
from sam_schema.core.models import (
    TASK_ID_PATTERN,
    AnalysisMethod,
    BookendType,
    Complexity,
    IssueClassification,
    PlanState,
    Priority,
    TaskStatus,
)

TaskId = Annotated[str, StringConstraints(pattern=TASK_ID_PATTERN.pattern)]


class _CliInput(BaseModel):
    """Strict base for CLI input adapters."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class CreatePlanInput(_CliInput):
    """Validated options for ``plan create``."""

    slug: str = Field(..., min_length=1)
    goal: str = Field(..., min_length=1)
    tasks: list[TaskDefinition] = Field(default_factory=list)
    context: str | None = None
    issue: int | None = Field(default=None, ge=1)

    def to_config(self) -> CreatePlanConfig:
        """Build the canonical plan action config.

        Returns:
            Canonical create-plan configuration.
        """
        return CreatePlanConfig(
            slug=self.slug, goal=self.goal, tasks=self.tasks, context=self.context, issue=self.issue
        )


class AppendTaskInput(_CliInput):
    """Validated options for ``plan append-task``."""

    plan_address: str = Field(..., min_length=1)
    task: TaskDefinition

    def to_config(self) -> AppendTaskConfig:
        """Build the canonical append-task action config.

        Returns:
            Canonical append-task configuration.
        """
        return AppendTaskConfig(task=self.task)


class TaskUpdateFields(_CliInput):
    """Explicitly supported task patch fields."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    status: TaskStatus | None = None
    agent: str | None = None
    dependencies: list[TaskId] | None = None
    priority: Priority | None = None
    complexity: Complexity | None = None
    skills: list[str] | None = None
    blocked_by: list[TaskId] | None = Field(
        default=None, validation_alias=AliasChoices("blocked-by", "blocked_by"), serialization_alias="blocked-by"
    )
    parallelize_with: list[TaskId] | None = Field(
        default=None,
        validation_alias=AliasChoices("parallelize-with", "parallelize_with"),
        serialization_alias="parallelize-with",
    )
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
    analysis_method: AnalysisMethod | None = Field(
        default=None,
        validation_alias=AliasChoices("analysis-method", "analysis_method"),
        serialization_alias="analysis-method",
    )
    divergence_notes: int | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("divergence-notes", "divergence_notes"),
        serialization_alias="divergence-notes",
    )
    accuracy_risk: Annotated[str, Field(pattern=r"^(low|medium|high)$")] | None = Field(
        default=None,
        validation_alias=AliasChoices("accuracy-risk", "accuracy_risk"),
        serialization_alias="accuracy-risk",
    )
    reason: str | None = None
    body: str | None = None
    description: str | None = None
    objective: str | None = None
    requirements: str | None = None
    constraints: str | None = None
    expected_outputs: str | None = Field(
        default=None,
        validation_alias=AliasChoices("expected-outputs", "expected_outputs"),
        serialization_alias="expected-outputs",
    )
    acceptance_criteria: str | None = Field(
        default=None,
        validation_alias=AliasChoices("acceptance-criteria", "acceptance_criteria"),
        serialization_alias="acceptance-criteria",
    )
    verification_steps: str | None = Field(
        default=None,
        validation_alias=AliasChoices("verification-steps", "verification_steps"),
        serialization_alias="verification-steps",
    )
    context_notes: str | None = Field(
        default=None,
        validation_alias=AliasChoices("context-notes", "context_notes"),
        serialization_alias="context-notes",
    )
    handoff: str | None = None
    is_bookend: bool | None = None
    bookend_type: BookendType | None = None
    github_issue: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def require_patch(self) -> TaskUpdateFields:
        """Reject an empty update before any operation is called.

        Returns:
            The validated update fields.
        """
        if not any(value is not None for value in self.model_dump().values()):
            raise ValueError("at least one task update field is required")
        return self

    def as_operation_fields(self) -> dict[str, object]:
        """Return only explicitly supplied fields using wire aliases."""
        return self.model_dump(by_alias=True, mode="json", exclude_unset=True, exclude_none=True)


class PlanUpdateFields(_CliInput):
    """Explicitly supported plan patch fields."""

    feature: str | None = Field(default=None, min_length=1)
    version: str | None = None
    description: str | None = None
    state: PlanState | None = None
    goal: str | None = None
    context: str | None = None
    acceptance_criteria: str | None = Field(
        default=None,
        validation_alias=AliasChoices("acceptance-criteria", "acceptance_criteria"),
        serialization_alias="acceptance-criteria",
    )
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
    autonomy: Literal["full_auto", "checkpoint", "per_task"] | None = None

    @model_validator(mode="after")
    def require_patch(self) -> PlanUpdateFields:
        """Reject an empty update before any operation is called.

        Returns:
            The validated update fields.
        """
        if not any(value is not None for value in self.model_dump().values()):
            raise ValueError("at least one plan update field is required")
        return self

    def as_operation_fields(self) -> dict[str, object]:
        """Return only explicitly supplied fields using wire aliases."""
        return self.model_dump(by_alias=True, mode="json", exclude_unset=True, exclude_none=True)


class TaskUpdateInput(_CliInput):
    """Validated options for a task field update."""

    plan_address: str = Field(..., min_length=1)
    task_id: str = Field(..., min_length=1)
    fields: TaskUpdateFields | None = None
    append_section: str | None = None
    section_content: str | None = None

    @model_validator(mode="after")
    def validate_section(self) -> TaskUpdateInput:
        """Require complete section options when appending content.

        Returns:
            The validated task update input.
        """
        if (self.append_section is None) != (self.section_content is None):
            raise ValueError("append_section and section_content must be provided together")
        if self.fields is None and self.append_section is None:
            raise ValueError("at least one task update field or a section append is required")
        return self


class PlanUpdateInput(_CliInput):
    """Validated options for a plan or task update."""

    plan_address: str = Field(..., min_length=1)
    fields: PlanUpdateFields | None = None
    task_id: str | None = None
    append_section_name: str | None = None
    section_content: str | None = None

    @model_validator(mode="after")
    def validate_operations(self) -> PlanUpdateInput:
        """Require a patch or a complete task-section operation.

        Returns:
            The validated plan update input.
        """
        has_section = self.append_section_name is not None or self.section_content is not None
        if has_section and (self.task_id is None or self.append_section_name is None or self.section_content is None):
            raise ValueError("task_id, append_section_name, and section_content are required together")
        if self.fields is None and not has_section:
            raise ValueError("at least one plan update field or a section append is required")
        return self


__all__ = [
    "AppendTaskInput",
    "CreatePlanInput",
    "PlanUpdateFields",
    "PlanUpdateInput",
    "TaskUpdateFields",
    "TaskUpdateInput",
]
