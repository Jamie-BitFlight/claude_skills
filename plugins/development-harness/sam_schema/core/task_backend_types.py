"""TypedDict boundary models for the TaskBackend Protocol.

These TypedDicts define the wire format at the boundary between the query layer
and backend implementations. Pydantic models remain the canonical validation
layer; conversion happens in the query layer, not in the backends.

All types follow the pattern established in backlog_core/backend_protocol.py:
- ``from __future__ import annotations`` for deferred evaluation
- ``typing_extensions.TypedDict`` for consistency with existing codebase
- ``NotRequired`` for optional fields that may be absent in input payloads
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired

from typing_extensions import TypedDict

if TYPE_CHECKING:
    from sam_schema.core.models import PlanState

__all__ = [
    "DocumentData",
    "DocumentHandle",
    "PlanData",
    "PlanFieldsUpdate",
    "PlanSummary",
    "TaskData",
    "TaskFieldsUpdate",
]

# TaskDefinitionDict was removed in the RC1 refactor (PR #1773).
# Backends now accept Task instances or plain dicts directly via append_task.
# This backwards-compat alias allows existing TYPE_CHECKING imports to resolve
# without errors during the migration period.
TaskDefinitionDict = dict  # backwards-compat alias; use Task or dict[str, Any] instead


class TaskData(TypedDict):
    """Full task data returned from backend implementations.

    Returned by :meth:`~sam_schema.core.task_backend.TaskBackend.read_task`
    and :meth:`~sam_schema.core.task_backend.TaskBackend.get_ready_tasks`.

    All required fields carry the canonical task state. Timestamps are ISO 8601
    strings (matching the YAML representation). Status must be one of the
    :class:`~sam_schema.core.models.TaskStatus` enum values.
    """

    # Required identification and status
    id: str
    title: str
    status: str

    # Required structural fields
    agent: str | None
    dependencies: list[str]
    blocked_by: list[str]
    parallelize_with: list[str]
    priority: int
    complexity: str
    skills: list[str]

    # Timestamp fields (ISO 8601 strings)
    created: str | None
    started: str | None
    completed: str | None
    last_activity: str | None

    # Required markdown content fields
    body: str
    description: str

    # Optional markdown content fields
    objective: NotRequired[str]
    requirements: NotRequired[str]
    constraints: NotRequired[str]
    expected_outputs: NotRequired[str]
    acceptance_criteria: NotRequired[str]
    verification_steps: NotRequired[str]
    context_notes: NotRequired[str]
    handoff: NotRequired[str]

    # Analytical metadata
    issue_classification: NotRequired[str | None]
    analysis_method: NotRequired[str]
    divergence_notes: NotRequired[int]
    accuracy_risk: NotRequired[str]
    reason: NotRequired[str]

    # Bookend metadata
    is_bookend: NotRequired[bool]
    bookend_type: NotRequired[str | None]

    # GitHub integration
    github_issue: NotRequired[int | None]


class PlanData(TypedDict):
    """Full plan data including all tasks.

    Returned by :meth:`~sam_schema.core.task_backend.TaskBackend.create_plan`
    and :meth:`~sam_schema.core.task_backend.TaskBackend.read_plan`.

    ``plan_id`` is the backend-assigned identifier (e.g. ``"P912"``).
    ``source_path`` is present for local backends and absent for remote ones.
    """

    # Required fields
    plan_id: str
    feature: str
    version: str
    description: str
    goal: str
    context: str
    acceptance_criteria: str
    issue: str | None
    tasks: list[TaskData]
    source_path: str | None

    # Drafting state (see #1770)
    state: NotRequired[PlanState]

    # Optional reference fields
    architecture: NotRequired[str | None]
    feature_context: NotRequired[str | None]
    codebase_patterns: NotRequired[str | None]
    backend_ref: NotRequired[str | None]

    # Autonomy mode for the implement-feature dispatch loop
    autonomy: NotRequired[str]


class PlanFieldsUpdate(TypedDict, total=False):
    """Mutable subset of PlanData fields for targeted plan updates.

    Passed to :meth:`~sam_schema.core.task_backend.TaskBackend.update_plan_fields`
    via ``set_fields``. All fields are optional; only provided fields are written.
    The structural ``tasks`` field is excluded — use ``append_task`` for task
    mutation. The ``plan_id`` is immutable and excluded.
    """

    feature: str
    version: str
    description: str
    goal: str
    context: str
    acceptance_criteria: str
    issue: str | None
    source_path: str | None
    state: PlanState
    architecture: str | None
    feature_context: str | None
    codebase_patterns: str | None
    backend_ref: str | None
    autonomy: str


class TaskFieldsUpdate(TypedDict, total=False):
    """Mutable subset of TaskData fields for targeted task updates.

    Passed to :meth:`~sam_schema.core.task_backend.TaskBackend.update_task_fields`
    via ``fields``. All fields are optional; only provided fields are written.
    """

    id: str
    title: str
    status: str
    agent: str | None
    dependencies: list[str]
    blocked_by: list[str]
    parallelize_with: list[str]
    priority: int
    complexity: str
    skills: list[str]
    created: str | None
    started: str | None
    completed: str | None
    last_activity: str | None
    body: str
    description: str
    objective: str
    requirements: str
    constraints: str
    expected_outputs: str
    acceptance_criteria: str
    verification_steps: str
    context_notes: str
    handoff: str
    issue_classification: str | None
    analysis_method: str
    divergence_notes: int
    accuracy_risk: str
    reason: str
    is_bookend: bool
    bookend_type: str | None
    github_issue: int | None


class PlanSummary(TypedDict):
    """Lightweight plan metadata for list operations.

    Returned as elements of the list from
    :meth:`~sam_schema.core.task_backend.TaskBackend.list_plans`.
    Does not include task bodies to keep the response compact.
    """

    # Required fields
    plan_id: str
    feature: str
    goal: str
    description: str
    task_count: int
    source_path: str | None

    # Optional fields
    issue: NotRequired[str | None]
    backend_ref: NotRequired[str | None]


class DocumentHandle(TypedDict):
    """Opaque handle returned when storing a document.

    Returned by :meth:`~sam_schema.core.task_backend.TaskBackend.store_document`
    and passed back to :meth:`~sam_schema.core.task_backend.TaskBackend.read_document`.

    ``content_ref`` is a backend-specific reference string (e.g. a file path for
    local backends, a gist ID for GitHub backends). Callers treat it as opaque.
    """

    # Required fields
    content_ref: str
    owner_type: str  # "plan" | "task"
    owner_id: str
    stage: str
    doc_type: str
    title: str
    fmt: str

    # Optional fields
    version: NotRequired[str | None]


class DocumentData(TypedDict):
    """Document content retrieved from a backend.

    Returned by :meth:`~sam_schema.core.task_backend.TaskBackend.read_document`.
    """

    content_ref: str
    title: str
    content: str
    fmt: str
    version: str | None
    owner_type: str
    owner_id: str
    stage: str
    doc_type: str
