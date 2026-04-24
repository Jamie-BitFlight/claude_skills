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

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from sam_schema.core.models import Task

# ---------------------------------------------------------------------------
# Shared base — eliminates 17x repeated model_config boilerplate
# ---------------------------------------------------------------------------


class _ActionConfigBase(BaseModel):
    """Shared base for all MCP action-config models.

    Sets ``populate_by_name=True`` once so every subclass inherits it without
    repeating the ``model_config = ConfigDict(populate_by_name=True)`` line.
    """

    model_config = ConfigDict(populate_by_name=True)


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


class TaskDefinition(Task):
    """MCP-input projection of Task.

    Inherits all field definitions, alias conventions, and validators from
    ``sam_schema.core.models.Task``.  The ``extra='ignore'`` config allows
    callers to submit unknown fields without raising a validation error —
    unknown fields are silently discarded at the MCP boundary.

    Runtime-only fields (``created``, ``started``, ``completed``,
    ``last_activity``, ``github_issue``) are inherited but default to ``None``;
    callers should omit them when authoring a new task.

    The ID regex, status enum, priority/complexity enums, and dependency
    validators are all inherited automatically from ``Task``.

    ``status`` is given a default of ``"not-started"`` at the MCP boundary so
    callers may omit it when submitting a new task.
    """

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True, extra="ignore")

    status: str = Field(default="not-started", description="Task status. Defaults to 'not-started'.")


# ---------------------------------------------------------------------------
# Tool 1 — sam_task: single-task operations
# ---------------------------------------------------------------------------


class ReadTaskConfig(_ActionConfigBase):
    """Read a task and return a TaskAssignment (plan context + task fields)."""

    action: Literal["read"] = "read"


class ClaimTaskConfig(_ActionConfigBase):
    """Claim a task (transition from not-started to in-progress)."""

    action: Literal["claim"] = "claim"


class StateTaskConfig(_ActionConfigBase):
    """Update a task's status field."""

    action: Literal["state"] = "state"
    status: str = Field(
        ...,
        description=(
            "New status value. Canonical values: not-started, in-progress, complete, "
            "blocked, deferred, skipped. STATUS_MAP in models.py accepts additional "
            "aliases (e.g. 'done', 'pending', ':white_check_mark:')."
        ),
    )


class UpdateTaskConfig(_ActionConfigBase):
    """Update task fields or append a markdown section to the task body.

    All three sub-operations are non-exclusive and may be combined in one call.
    """

    action: Literal["update"] = "update"
    set_fields_json: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Field=value pairs to patch on the task. "
            "Fields are validated through the Task Pydantic model before writing. "
            'Example: {"priority": 1, "agent": "python-cli-architect"}'
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


class ReadPlanConfig(_ActionConfigBase):
    """Read a plan and return its Plan fields."""

    action: Literal["read"] = "read"


class CreatePlanConfig(_ActionConfigBase):
    """Create a new plan from a typed list of task definitions.

    Pass ``tasks=[]`` to create a plan in drafting state for incremental
    building via ``append_task``.  Pass a non-empty list to create a ready
    plan in a single call (monolithic path).
    """

    action: Literal["create"] = "create"
    slug: str = Field(
        ...,
        description=(
            "Short identifier for the plan (e.g., 'auth-system'). "
            "Used to compose the plan filename: P{NNN}-{slug}.yaml."
        ),
    )
    goal: str = Field(..., description="Human-readable goal statement for the plan.")
    tasks: list[TaskDefinition] = Field(
        default_factory=list,
        description=(
            "Ordered list of task definitions. "
            "Required task fields per Task model: id (str, e.g. 'T1'), title (str). "
            "Optional fields: status (default 'not-started'), agent (str), "
            "dependencies (list of task IDs), priority (int 1-5, where 1=highest), "
            "complexity ('low', 'medium', or 'high'). "
            "Pass an empty list to create a plan in drafting state for incremental "
            "building via append_task + finalize."
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


class ListPlansConfig(_ActionConfigBase):
    """List all plans with optional search and auto-pagination."""

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


class StatusPlanConfig(_ActionConfigBase):
    """Get plan-level progress summary."""

    action: Literal["status"] = "status"


class ReadyPlanConfig(_ActionConfigBase):
    """List tasks ready for dispatch (status=not-started, all dependencies terminal)."""

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


class UpdatePlanConfig(_ActionConfigBase):
    """Update plan-level fields.

    Applies field patches and/or sets the plan context field.
    """

    action: Literal["update"] = "update"
    context: str | None = Field(
        default=None,
        description=('Set the plan-level context field. Shorthand equivalent to set_fields_json={"context": "..."}.'),
    )
    set_fields_json: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Field=value pairs of plan-level fields to set. "
            "Applied via backend.update_plan_fields. "
            'Example: {"goal": "New goal statement", "issue": 42}'
        ),
    )


class AppendTaskConfig(_ActionConfigBase):
    """Append a single task to an existing plan.

    Enables incremental plan building — callers emit one task at a time rather than
    submitting the full ``tasks`` list in a single ``create`` call. Plans
    created with an empty ``tasks`` list enter a ``drafting`` state; ``append_task``
    keeps them in ``drafting`` until ``finalize`` is invoked.

    The ``task`` field accepts a :class:`TaskDefinition` instance. Pydantic validates
    and alias-normalises the payload at the MCP boundary so backends receive a
    plain snake_case dict from ``task.model_dump(by_alias=False, exclude_none=True)``.

    Single-writer contract: implementations assume a single writer per plan. Backends
    are NOT required to be atomic under concurrent writers. See #1770 for the
    architectural decision record.
    """

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


class FinalizePlanConfig(_ActionConfigBase):
    """Transition a plan out of ``drafting`` state into executable state.

    Plans created with an empty ``tasks`` list (the incremental build pattern)
    start in ``drafting``. ``sam_plan(action='read')`` returns the tasks and a
    ``drafting`` marker; ``status`` and ``ready`` return a ``drafting`` marker
    instead of dispatchable task data. ``finalize`` clears ``drafting`` after
    plan review completes (no-more-changes), making the plan available for
    execution by ``sam_plan(action='ready')`` and ``/dh:implement-feature``.

    See #1770 for the architectural decision record.
    """

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


class GetActiveTaskConfig(_ActionConfigBase):
    """Retrieve the active task context for a session."""

    action: Literal["get"] = "get"


class SetActiveTaskConfig(_ActionConfigBase):
    """Store a task address as the active task for a session."""

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
    parent_issue_number: int | None = Field(
        default=None,
        description="Optional GitHub issue number for the parent story. Used by the SubagentStop hook for GitHub sync and issue linking.",
    )


class UpdateActiveTaskConfig(_ActionConfigBase):
    """Update fields on the currently active task without repeating the address.

    Delegates to the same backend write path as sam_task(action='update').
    Raises if no active task has been set for this session.
    """

    action: Literal["update"] = "update"
    set_fields_json: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Field=value pairs of task fields to patch. Applied to the task stored by the most recent set action."
        ),
    )
    append_section: str | None = Field(
        default=None, description="Heading of the markdown section to append to the active task body."
    )
    section_content: str | None = Field(
        default=None, description="Body text for the appended section. Used with append_section."
    )


class ClearActiveTaskConfig(_ActionConfigBase):
    """Clear the active task context for a session."""

    action: Literal["clear"] = "clear"


# Discriminated union for sam_active_task — discriminator is the ``action`` field.
ActiveTaskActionConfig = Annotated[
    GetActiveTaskConfig | SetActiveTaskConfig | UpdateActiveTaskConfig | ClearActiveTaskConfig,
    Field(discriminator="action"),
]
