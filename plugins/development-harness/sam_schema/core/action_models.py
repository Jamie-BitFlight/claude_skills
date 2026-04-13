"""Pydantic discriminated union config models for the 3 consolidated SAM MCP tools.

Each tool (sam_task, sam_plan, sam_active_task) accepts a single ``config`` parameter
typed as a discriminated union. The ``action`` literal field on each model acts as the
discriminator, routing to the correct operation at runtime.

Naming rationale
----------------
The union type aliases are intentionally named ``TaskActionConfig``, ``PlanActionConfig``,
and ``ActiveTaskActionConfig`` — NOT ``TaskConfig`` / ``PlanConfig`` / ``ActiveTaskConfig``.
``TaskConfig`` is already a dataclass in ``sam_schema.core.task_config`` (dependency
injection container for the active backend). Using the same name would cause import
collisions and silent shadowing.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

__all__ = [
    "ActiveTaskActionConfig",
    "AppendTaskConfig",
    "ClaimTaskConfig",
    "ClearActiveTaskConfig",
    "CreatePlanConfig",
    "FinalizePlanConfig",
    # Active-task action models
    "GetActiveTaskConfig",
    "ListPlansConfig",
    "PlanActionConfig",
    # Plan action models
    "ReadPlanConfig",
    # Task action models
    "ReadTaskConfig",
    "ReadyPlanConfig",
    "SetActiveTaskConfig",
    "StateTaskConfig",
    "StatusPlanConfig",
    # Discriminated union type aliases
    "TaskActionConfig",
    "TaskDefinition",
    "UpdateActiveTaskConfig",
    "UpdatePlanConfig",
    "UpdateTaskConfig",
]

# ---------------------------------------------------------------------------
# MCP input boundary model for task authoring
# ---------------------------------------------------------------------------


class TaskDefinition(BaseModel):
    """Typed input model for defining a task at the MCP boundary.

    This is the **MCP-input boundary model** — it carries the fields a caller
    sets when authoring a new task.  It is distinct from two other types with
    similar names:

    - ``sam_schema.core.models.Task`` — the *persisted entity* model that
      includes all runtime fields (``created``, ``started``, ``completed``,
      ``last_activity``, ``body``, ``description``, ``github_issue``, etc.).
    - ``sam_schema.core.task_backend_types.TaskDefinition`` — the *backend
      contract* TypedDict used internally between the query layer and backend
      implementations.

    By using a typed ``BaseModel`` at the MCP boundary, Pydantic handles field
    validation and alias normalization (kebab-case → snake_case) automatically,
    eliminating the need for alias-normalization helpers downstream.

    Alias conventions mirror ``Task``: ``populate_by_name=True``,
    ``AliasChoices("kebab-case", "snake_case")`` for multi-word fields, and
    ``serialization_alias="kebab-case"`` for round-trip fidelity.
    """

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    # Required fields
    id: str = Field(..., description="Task identifier (e.g. 'T1').")
    title: str = Field(..., min_length=1, max_length=200, description="Human-readable task title.")
    status: str = Field(default="not-started", description="Task status. Defaults to 'not-started'.")

    # Optional structural fields
    agent: str | None = Field(default=None, description="Agent or specialist responsible for this task.")
    dependencies: list[str] = Field(default_factory=list, description="List of task IDs this task depends on.")
    priority: int = Field(default=3, ge=1, le=5, description="Priority (1=highest, 5=lowest). Default: 3 (MEDIUM).")
    complexity: str = Field(
        default="medium", pattern=r"^(low|medium|high)$", description="Complexity estimate: 'low', 'medium', or 'high'."
    )
    skills: list[str] = Field(default_factory=list, description="Skill tags required to complete this task.")
    blocked_by: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("blocked-by", "blocked_by"),
        serialization_alias="blocked-by",
        description="Task IDs that are blocking this task.",
    )
    parallelize_with: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("parallelize-with", "parallelize_with"),
        serialization_alias="parallelize-with",
        description="Task IDs that can safely run in parallel with this task.",
    )

    # Markdown content fields (authoring inputs — no runtime timestamps)
    body: str = Field(default="", description="Raw markdown body for the task.")
    description: str = Field(default="", description="Short prose description of the task.")
    objective: str = Field(default="", description="One-paragraph objective statement.")
    requirements: str = Field(default="", description="Functional requirements for this task.")
    constraints: str = Field(default="", description="Constraints and limitations.")
    expected_outputs: str = Field(
        default="",
        validation_alias=AliasChoices("expected-outputs", "expected_outputs"),
        serialization_alias="expected-outputs",
        description="Deliverables and success artifacts.",
    )
    acceptance_criteria: str = Field(
        default="",
        validation_alias=AliasChoices("acceptance-criteria", "acceptance_criteria"),
        serialization_alias="acceptance-criteria",
        description="Acceptance criteria for this task.",
    )
    verification_steps: str = Field(
        default="",
        validation_alias=AliasChoices("verification-steps", "verification_steps"),
        serialization_alias="verification-steps",
        description="Steps to verify the task is complete.",
    )
    context_notes: str = Field(
        default="",
        validation_alias=AliasChoices("context-notes", "context_notes"),
        serialization_alias="context-notes",
        description="Additional context notes.",
    )
    handoff: str = Field(default="", description="Handoff notes for the next task or agent.")
    reason: str = Field(default="", description="Reason for this task's inclusion in the plan.")

    # Analytical metadata
    issue_classification: str | None = Field(
        default=None,
        validation_alias=AliasChoices("issue-classification", "issue_classification"),
        serialization_alias="issue-classification",
        description="Root-cause classification: procedural, defect, recurring-pattern, etc.",
    )
    scenario_target: str | None = Field(
        default=None,
        validation_alias=AliasChoices("scenario-target", "scenario_target"),
        serialization_alias="scenario-target",
        description="Target scenario for this task.",
    )
    analysis_method: str = Field(
        default="none",
        validation_alias=AliasChoices("analysis-method", "analysis_method"),
        serialization_alias="analysis-method",
        description="Analysis method applied: none, 5-whys, 6-sigma, design-framing.",
    )

    # Bookend metadata
    is_bookend: bool = Field(
        default=False,
        validation_alias=AliasChoices("is-bookend", "is_bookend"),
        serialization_alias="is-bookend",
        description="True when this task is a bookend (T0 baseline or TN verification).",
    )
    bookend_type: str | None = Field(
        default=None,
        validation_alias=AliasChoices("bookend-type", "bookend_type"),
        serialization_alias="bookend-type",
        description="Bookend type: 't0-baseline' or 'tn-verification'.",
    )


# ---------------------------------------------------------------------------
# Tool 1 — sam_task: single-task operations
# ---------------------------------------------------------------------------


class ReadTaskConfig(BaseModel):
    """Read a task and return a TaskAssignment (plan context + task fields)."""

    model_config = ConfigDict(populate_by_name=True)

    action: Literal["read"] = "read"


class ClaimTaskConfig(BaseModel):
    """Claim a task (transition from not-started to in-progress)."""

    model_config = ConfigDict(populate_by_name=True)

    action: Literal["claim"] = "claim"


class StateTaskConfig(BaseModel):
    """Update a task's status field."""

    model_config = ConfigDict(populate_by_name=True)

    action: Literal["state"] = "state"
    status: str = Field(
        ...,
        description=(
            "New status value. Canonical values: not-started, in-progress, complete, "
            "blocked, deferred, skipped. STATUS_MAP in models.py accepts additional "
            "aliases (e.g. 'done', 'pending', ':white_check_mark:')."
        ),
    )


class UpdateTaskConfig(BaseModel):
    """Update task fields or append a markdown section to the task body.

    All three sub-operations are non-exclusive and may be combined in one call.
    """

    model_config = ConfigDict(populate_by_name=True)

    action: Literal["update"] = "update"
    set_fields_json: str | None = Field(
        default=None,
        description=(
            'JSON object {"field": "value", ...} of task fields to patch. '
            "Fields are validated through the Task Pydantic model before writing. "
            'Example: \'{"priority": 1, "agent": "python-cli-architect"}\''
        ),
    )
    append_section: str | None = Field(
        default=None,
        description=(
            "Heading of the markdown section to append to the task body. "
            "Requires section_content. Task address (task param on the tool) is required."
        ),
    )
    section_content: str | None = Field(
        default=None, description="Body text for the appended section. Used with append_section."
    )


# Discriminated union for sam_task — discriminator is the ``action`` field.
TaskActionConfig = Annotated[
    ReadTaskConfig | ClaimTaskConfig | StateTaskConfig | UpdateTaskConfig, Field(discriminator="action")
]

# ---------------------------------------------------------------------------
# Tool 2 — sam_plan: plan-level operations
# ---------------------------------------------------------------------------


class ReadPlanConfig(BaseModel):
    """Read a plan and return its Plan fields."""

    model_config = ConfigDict(populate_by_name=True)

    action: Literal["read"] = "read"


class CreatePlanConfig(BaseModel):
    """Create a new plan from YAML task definitions."""

    model_config = ConfigDict(populate_by_name=True)

    action: Literal["create"] = "create"
    slug: str = Field(
        ...,
        description=(
            "Short identifier for the plan (e.g., 'auth-system'). "
            "Used to compose the plan filename: P{NNN}-{slug}.yaml."
        ),
    )
    goal: str = Field(..., description="Human-readable goal statement for the plan.")
    tasks_yaml: str = Field(
        ...,
        description=(
            "YAML string with a top-level 'tasks' key containing a list of task dicts. "
            "Required task fields per Task model: id (str, e.g. 'T1'), title (str), "
            "status ('not-started'), agent (str, e.g. 'dh:code-reviewer'), "
            "dependencies (list of task IDs, e.g. ['T1', 'T2']), "
            "priority (int 1-5, where 1=highest), "
            "complexity ('low', 'medium', or 'high'). "
            "All other Task fields are optional."
        ),
    )
    context: str | None = Field(
        default=None, description="Optional plan-level context (markdown prose). Stored as Plan.context."
    )
    issue: int | None = Field(
        default=None,
        description=(
            "Optional GitHub issue number. When provided, auto-registers the created plan "
            "file as a task-plan artifact on the issue."
        ),
    )


class ListPlansConfig(BaseModel):
    """List all plans with optional search and auto-pagination."""

    model_config = ConfigDict(populate_by_name=True)

    action: Literal["list"] = "list"
    search: str | None = Field(
        default=None,
        description=(
            "Case-insensitive substring filter applied across feature, description, and goal fields simultaneously."
        ),
    )
    offset: int = Field(default=0, ge=0, description="Zero-based index of the first item to return.")
    limit: int | None = Field(
        default=None,
        description=(
            "Maximum number of items to return. When None, auto-calculates a limit "
            "that keeps the response within the 4400-token budget (cl100k_base encoding)."
        ),
    )


class StatusPlanConfig(BaseModel):
    """Get plan-level progress summary."""

    model_config = ConfigDict(populate_by_name=True)

    action: Literal["status"] = "status"


class ReadyPlanConfig(BaseModel):
    """List tasks ready for dispatch (status=not-started, all dependencies terminal)."""

    model_config = ConfigDict(populate_by_name=True)

    action: Literal["ready"] = "ready"
    full: bool = Field(
        default=False,
        description=(
            "When False (default), return a compact 7-field routing manifest per task: "
            "id, task, agent, skills, dependencies, status, priority. "
            "When True, return the full Task model dump (all 30+ fields). "
            "Use False for orchestrator dispatch decisions; True for agents needing full context."
        ),
    )


class UpdatePlanConfig(BaseModel):
    """Update plan-level fields.

    Applies field patches and/or sets the plan context field.
    """

    model_config = ConfigDict(populate_by_name=True)

    action: Literal["update"] = "update"
    context: str | None = Field(
        default=None,
        description=('Set the plan-level context field. Shorthand equivalent to set_fields_json={"context": "..."}.'),
    )
    set_fields_json: str | None = Field(
        default=None,
        description=(
            'JSON object {"field": "value", ...} of plan-level fields to set. '
            "Applied via backend.update_plan_fields. "
            'Example: \'{"goal": "New goal statement", "issue": 42}\''
        ),
    )


class AppendTaskConfig(BaseModel):
    """Append a single task to an existing plan.

    Enables incremental plan building — callers emit one task at a time rather than
    submitting the full ``tasks_yaml`` payload in a single ``create`` call. Plans
    created with an empty ``tasks_yaml`` enter a ``drafting`` state; ``append_task``
    keeps them in ``drafting`` until ``finalize`` is invoked.

    The ``task`` field accepts a :class:`TaskDefinition` instance. Pydantic validates
    and alias-normalises the payload at the MCP boundary so backends receive a
    plain snake_case dict from ``task.model_dump(by_alias=False, exclude_none=True)``.

    Single-writer contract: implementations assume a single writer per plan. Backends
    are NOT required to be atomic under concurrent writers. See #1770 for the
    architectural decision record.
    """

    model_config = ConfigDict(populate_by_name=True)

    action: Literal["append_task"] = "append_task"
    task: TaskDefinition = Field(
        ...,
        description=(
            "Typed task definition. Required fields: id (str, e.g. 'T1'), "
            "title (str). Optional fields include status (default 'not-started'), "
            "agent (str), dependencies (list of task IDs), priority (int 1-5), "
            "and complexity ('low', 'medium', or 'high'). All other TaskDefinition "
            "fields are optional and use their model defaults when omitted."
        ),
    )


class FinalizePlanConfig(BaseModel):
    """Transition a plan out of ``drafting`` state into executable state.

    Plans created with an empty ``tasks_yaml`` (the incremental build pattern)
    start in ``drafting``. ``sam_plan(action='read')`` returns the tasks and a
    ``drafting`` marker; ``status`` and ``ready`` return a ``drafting`` marker
    instead of dispatchable task data. ``finalize`` clears ``drafting`` after
    plan review completes (no-more-changes), making the plan available for
    execution by ``sam_plan(action='ready')`` and ``/dh:implement-feature``.

    See #1770 for the architectural decision record.
    """

    model_config = ConfigDict(populate_by_name=True)

    action: Literal["finalize"] = "finalize"


# Discriminated union for sam_plan — discriminator is the ``action`` field.
PlanActionConfig = Annotated[
    ReadPlanConfig
    | CreatePlanConfig
    | ListPlansConfig
    | StatusPlanConfig
    | ReadyPlanConfig
    | UpdatePlanConfig
    | AppendTaskConfig
    | FinalizePlanConfig,
    Field(discriminator="action"),
]

# ---------------------------------------------------------------------------
# Tool 3 — sam_active_task: session execution context (NEW)
# ---------------------------------------------------------------------------


class GetActiveTaskConfig(BaseModel):
    """Retrieve the active task context for a session."""

    model_config = ConfigDict(populate_by_name=True)

    action: Literal["get"] = "get"


class SetActiveTaskConfig(BaseModel):
    """Store a task address as the active task for a session."""

    model_config = ConfigDict(populate_by_name=True)

    action: Literal["set"] = "set"
    plan: str = Field(..., description="Plan address to register as the active task's plan (e.g., 'P1').")
    task: str = Field(..., description="Task ID to register as the active task (e.g., 'T3').")
    plan_dir: str = Field(
        default="plan",
        description=(
            "Plan directory path for the active task's backend. "
            "Stored alongside plan/task so retrieval uses the same backend."
        ),
    )


class UpdateActiveTaskConfig(BaseModel):
    """Update fields on the currently active task without repeating the address.

    Delegates to the same backend write path as sam_task(action='update').
    Raises if no active task has been set for this session.
    """

    model_config = ConfigDict(populate_by_name=True)

    action: Literal["update"] = "update"
    set_fields_json: str | None = Field(
        default=None,
        description=(
            'JSON object {"field": "value", ...} of task fields to patch. '
            "Applied to the task stored by the most recent set action."
        ),
    )
    append_section: str | None = Field(
        default=None, description="Heading of the markdown section to append to the active task body."
    )
    section_content: str | None = Field(
        default=None, description="Body text for the appended section. Used with append_section."
    )


class ClearActiveTaskConfig(BaseModel):
    """Clear the active task context for a session."""

    model_config = ConfigDict(populate_by_name=True)

    action: Literal["clear"] = "clear"


# Discriminated union for sam_active_task — discriminator is the ``action`` field.
ActiveTaskActionConfig = Annotated[
    GetActiveTaskConfig | SetActiveTaskConfig | UpdateActiveTaskConfig | ClearActiveTaskConfig,
    Field(discriminator="action"),
]
