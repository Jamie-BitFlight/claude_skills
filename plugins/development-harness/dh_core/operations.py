"""Unified operations layer for the development harness.

The single entry point for all plan, task, backlog, artifact, and dispatch
operations.

Both frontends (CLI and MCP server) import from this module. No business
logic lives in the frontend files. Each operation here delegates to the
backend protocol (dh_core.protocols) for data access.

This module is built incrementally. As operations are extracted from the
frontends, they are added here with:
1. The operation function (all business logic)
2. A parity test in tests/test_frontend_parity.py
3. An entry in the progress file (.hermes/plans/unified-backend-progress.md)

During the transition, operations that have not yet been extracted will
still be called directly from the frontends. The goal is to reach zero
such calls.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sam_schema.core.dependencies import DependencyGraph
from sam_schema.core.exceptions import (
    ArtifactWriteError,
    ConcurrentClaimUnsupportedError,
    PlanNotFoundError,
    SamError,
    TaskNotFoundError,
)
from sam_schema.core.models import Plan, PlanState, Task, TaskAssignment, TaskStatus

if TYPE_CHECKING:
    from dh_core.protocols import TaskBackend

_log = logging.getLogger(__name__)

__all__ = [
    "append_task",
    "claim_task",
    "create_plan",
    "finalize_plan",
    "get_plan_status",
    "get_ready_tasks",
    "list_plans",
    "read_plan",
    "read_task",
    "update_plan_fields",
    "update_task_fields",
    "update_task_status",
]


def create_plan(
    backend: TaskBackend,
    *,
    slug: str,
    goal: str,
    tasks: list[dict[str, Any]] | list[Any],
    context: str | None = None,
    issue: int | None = None,
) -> dict[str, Any]:
    """Create a new plan with the given slug, goal, and task definitions.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation handles all business logic: plan
    creation, artifact write error handling, and response assembly.

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        slug: Human-readable identifier slug for the plan.
        goal: One-sentence goal statement for the plan.
        tasks: List of task definitions (dicts or Task models).
        context: Optional plan-level context narrative (markdown).
        issue: Optional GitHub issue number to associate with the plan.

    Returns:
        Dict with ``plan_id``, ``task_count``, and optional ``warnings``
        keys. On Gist write failure, returns a dict with ``error``,
        ``reason``, ``plan_id``, ``issue``, ``local_path``, and ``hint``
        keys (structured error so the caller knows the plan is not
        portable).

    Raises:
        ValueError: When any task definition fails schema validation.
        OSError: When the local filesystem write fails.
    """
    # Normalize tasks to Task models if they aren't already.
    # The CLI passes raw dicts (from YAML), the MCP server passes
    # TaskDefinition Pydantic models. The backend expects Task models.
    normalized_tasks: list[Task] = []
    for t in tasks:
        if isinstance(t, Task):
            normalized_tasks.append(t)
        elif isinstance(t, dict):
            # Accept "task" key as the task id (YAML frontmatter convention)
            normalized = {**t, "id": t["task"]} if "task" in t and "id" not in t else t
            normalized_tasks.append(Task.model_validate(normalized))
        elif hasattr(t, "model_dump"):
            # Pydantic models with model_dump (e.g. TaskDefinition)
            normalized_tasks.append(Task.model_validate(t.model_dump()))
        else:
            normalized_tasks.append(Task.model_validate(dict(t)))

    try:
        plan_data = backend.create_plan(slug=slug, goal=goal, tasks=normalized_tasks, context=context, issue=issue)
    except ArtifactWriteError as exc:
        # Gist write failed — return structured error (ADR-2509-5).
        # The plan may exist locally (local_backend wrote it), but it
        # is NOT durable.
        _log.error("create_plan: ArtifactWriteError for plan (issue #%s): %s", exc.issue, exc.reason)
        return {
            "error": "create_plan failed: artifact write to Gist unsuccessful",
            "reason": exc.reason,
            "plan_id": exc.plan_id,
            "issue": exc.issue,
            "local_path": None,
            "hint": "The plan was written to local disk only. Check GitHub connectivity and retry to upload to Gist.",
        }

    plan_id_str = plan_data["plan_id"]
    result: dict[str, Any] = {"plan_id": plan_id_str, "task_count": len(plan_data["tasks"])}

    # Compute plan_ref: #{issue},{plan_id} when issue is set, else plan_id.
    if issue is not None:
        result["plan_ref"] = f"#{issue},{plan_id_str}"
    else:
        result["plan_ref"] = plan_id_str

    # Collect warnings: local-only non-portability + backend-specific warnings.
    warnings: list[str] = []
    if issue is None:
        warnings.append(
            f"Plan {plan_id_str} has no associated issue — stored locally only. "
            "This plan is not portable across environments and cannot be retrieved from CI "
            "or fresh checkouts. Associate a GitHub issue to enable portability."
        )

    # GistTaskLayer-specific: surface index warnings if present.
    last_warnings = getattr(backend, "last_warnings", None)
    if last_warnings:
        warnings.extend(last_warnings)

    if warnings:
        result["warnings"] = warnings

    return result


def read_plan(backend: TaskBackend, plan: str) -> dict[str, Any]:
    """Read a plan by its address and return a serialized dict.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation handles all business logic: plan
    retrieval, Plan model conversion, dict serialization, and
    source-degradation warning surfacing.

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        plan: Plan address string (e.g. ``"P1"`` or slug).

    Returns:
        Dict with the plan fields (serialized via the Plan model with
        ``by_alias=True, exclude_none=True``). When the backend served
        the plan from local cache, a ``warnings`` key is added with a
        degraded-source message.

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
    """
    plan_data = backend.read_plan(plan)
    plan_dict = {k: v for k, v in plan_data.items() if k != "plan_id"}
    plan_model = Plan.model_validate(plan_dict)
    result = plan_model.model_dump(mode="json", by_alias=True, exclude_none=True)

    # Surface source annotation when plan was served from local cache.
    # Use getattr to stay backend-agnostic — not all backends have
    # last_read_source (only GistTaskLayer does).
    last_read_source = getattr(backend, "last_read_source", None)
    if last_read_source == "local":
        result["warnings"] = [
            f"Plan {plan} served from local cache — Gist copy may be unavailable or predates this fix."
        ]

    return result


def list_plans(
    backend: TaskBackend, *, search: str | None = None, offset: int = 0, limit: int | None = None
) -> dict[str, Any]:
    """List all plans with optional search filtering and pagination.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation handles all business logic: plan
    listing, search filtering (delegated to the backend), summary-to-dict
    mapping, and offset/limit pagination.

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        search: Optional case-insensitive substring filter applied across
            ``feature``, ``description``, and ``goal`` fields. Delegated
            to the backend's ``list_plans`` method.
        offset: Zero-based index of the first item to return.
        limit: Maximum number of items to return. ``None`` means no limit.

    Returns:
        Dict with ``items`` (list of per-plan summary dicts), ``count``
        (number of items in the current page), and ``total`` (total
        number of plans after filtering). Each item dict contains
        ``feature``, ``goal``, ``description``, ``task_count``, ``issue``,
        and ``plan_ref``.
    """
    summaries = backend.list_plans(search=search)
    all_items: list[dict[str, Any]] = [
        {
            "feature": s["feature"],
            "goal": s["goal"],
            "description": s["description"],
            "task_count": s["task_count"],
            "issue": s.get("issue"),
            "plan_ref": (f"#{s['issue']},{s['plan_id']}" if s.get("issue") else s.get("plan_id")),
        }
        for s in summaries
    ]

    total = len(all_items)
    page = all_items[offset:] if limit is None else all_items[offset : offset + limit]

    return {"items": page, "count": len(page), "total": total}


def get_plan_status(backend: TaskBackend, plan: str) -> dict[str, Any]:
    """Return plan-level progress summary including autonomy mode.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation handles all business logic: status
    retrieval, drafting-state check, and autonomy field enrichment.

    When the plan is in the ``DRAFTING`` state, a drafting marker dict
    is returned immediately (matching the MCP server's
    ``_DRAFTING_MARKER_RESPONSE`` shape). This prevents dispatching a
    partial plan.

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        plan: Plan address string (e.g. ``"P1"`` or slug).

    Returns:
        When the plan is drafting: ``{"drafting": True, "state": "drafting"}``.
        Otherwise: a dict with the status fields from
        ``backend.get_plan_status`` plus an ``autonomy`` key sourced from
        ``backend.read_plan`` (defaulting to ``"full_auto"`` when absent).

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
    """
    status = backend.get_plan_status(plan)
    if status.get("state") == PlanState.DRAFTING:
        return {"drafting": True, "state": PlanState.DRAFTING}
    plan_data = backend.read_plan(plan)
    result = dict(status)
    result["autonomy"] = plan_data.get("autonomy", "full_auto")
    return result


def get_ready_tasks(backend: TaskBackend, plan: str, *, full: bool = False) -> dict[str, Any]:
    """Return tasks ready for dispatch along with plan-level metadata.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation handles all business logic: drafting
    check, ready-task retrieval, compact/full serialization, and
    ``feature``/``issue`` enrichment from the plan record.

    When the plan is in the ``DRAFTING`` state, a drafting marker dict
    is returned immediately (matching the MCP server's
    ``_DRAFTING_MARKER_RESPONSE`` shape). This prevents dispatching a
    partial plan.

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        plan: Plan address string (e.g. ``"P1"`` or slug).
        full: When ``False`` (default), return a compact 7-field routing
            manifest per task: ``id``, ``task``, ``agent``, ``skills``,
            ``dependencies``, ``status``, ``priority``. When ``True``,
            return the full :class:`~sam_schema.core.models.Task` model
            dump (all fields).

    Returns:
        When the plan is drafting: ``{"drafting": True, "state": "drafting"}``.
        Otherwise: a dict with ``ready_tasks`` (list of task dicts),
        ``count`` (number of ready tasks), ``feature`` (plan feature
        string), and ``issue`` (plan issue number).

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
    """
    status = backend.get_plan_status(plan)
    if status.get("state") == PlanState.DRAFTING:
        return {"drafting": True, "state": PlanState.DRAFTING}
    tasks_data = backend.get_ready_tasks(plan)
    plan_data = backend.read_plan(plan)
    if full:
        ready_tasks: list[dict[str, Any]] = [Task.model_validate(t).model_dump(mode="json") for t in tasks_data]
    else:
        ready_tasks = [
            {
                "id": t["id"],
                "task": t["title"],
                "agent": t["agent"],
                "skills": t["skills"] or [],
                "dependencies": t["dependencies"] or [],
                "status": t["status"],
                "priority": int(t["priority"]),
            }
            for t in tasks_data
        ]
    feature = status["feature"]
    if not isinstance(feature, str):
        msg = f"get_plan_status must return str for 'feature', got {type(feature).__name__}"
        raise TypeError(msg)
    return {"ready_tasks": ready_tasks, "count": len(tasks_data), "feature": feature, "issue": plan_data["issue"]}


def _validated_plan_patch(backend: TaskBackend, plan_id: str, raw_fields: dict[str, Any]) -> Plan:
    """Validate raw JSON patch fields through the Pydantic Plan model.

    Reads the current plan, merges *raw_fields* into its data, then passes the
    merged dict through ``Plan.model_validate`` so field validators run (e.g.
    ``coerce_issue_to_str`` normalises the ``issue`` field).  Returns the
    fully-validated Plan model so callers use normalized field values, not the
    raw input.

    Args:
        backend: Active TaskBackend instance.
        plan_id: Backend-assigned plan identifier.
        raw_fields: JSON-decoded patch dict from ``set_fields``.

    Returns:
        Fully-validated Plan model with the patched fields applied.

    Raises:
        PlanNotFoundError: When plan_id cannot be resolved by the backend.
        pydantic.ValidationError: When a field value fails Plan model validation.
    """
    plan_data = backend.read_plan(plan_id)
    current = Plan.model_validate(plan_data)
    return Plan.model_validate({**current.model_dump(), **raw_fields})


def update_plan_fields(
    backend: TaskBackend, plan: str, *, context: str | None = None, set_fields: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Update plan-level context and/or fields on the backend.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation handles all business logic: raw field
    validation through the Plan model (when ``set_fields`` is provided),
    delegation to ``backend.update_plan_fields``, and response assembly.

    When ``set_fields`` is provided, the raw fields are validated by reading
    the current plan, merging the raw fields into its data, passing the
    merged dict through ``Plan.model_validate`` (so field validators run),
    and extracting only the requested keys from the validated model. This
    ensures the backend receives normalized field values, not raw input.

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        plan: Plan address string (e.g. ``"P1"`` or slug).
        context: Optional plan-level context narrative (markdown). When
            ``None``, the plan's existing context is not modified.
        set_fields: Optional dict of raw field-value pairs to patch onto
            the plan. Keys use kebab-case (wire convention). Values are
            normalized through the Plan model before being passed to the
            backend. When ``None``, no plan-level fields are modified.

    Returns:
        Dict with ``updated`` (``True``) and ``address`` (the plan address
        string) keys.

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
        pydantic.ValidationError: When a field value fails Plan model
            validation.
    """
    plan_fields: dict[str, Any] | None = None
    if set_fields is not None:
        validated = _validated_plan_patch(backend, plan, set_fields)
        # by_alias=True: set_fields uses kebab-case keys (wire convention);
        # alias keys must match so we extract only the requested keys.
        plan_fields = {k: v for k, v in validated.model_dump(by_alias=True, mode="json").items() if k in set_fields}
    backend.update_plan_fields(plan, context=context, set_fields=plan_fields)
    return {"updated": True, "address": plan}


def append_task(backend: TaskBackend, plan: str, task: Task | dict[str, Any]) -> dict[str, Any]:
    """Append a single task to an existing plan.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation handles all business logic: task
    normalization (accepting either a Task model or a dict) and
    delegation to ``backend.append_task``.

    Pydantic handles alias normalisation (kebab-case → snake_case) at the
    MCP boundary when the frontend passes a ``TaskDefinition`` (subclass of
    ``Task``); no YAML parsing or re-normalisation is required downstream.

    See the single-writer contract in ADR-1770-1: callers MUST serialize
    writes to the same plan.

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        plan: Plan address string (e.g. ``"P1"`` or slug).
        task: Task model or dict to append. When a dict is provided, it
            is normalized through ``Task.model_validate`` before being
            passed to the backend. When a ``Task`` (or ``TaskDefinition``)
            is provided, it is passed through unchanged.

    Returns:
        Dict with ``appended`` (``True``) and ``task_id`` keys, matching
        the shape returned by ``backend.append_task``.

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
        TaskValidationError: When the task ID duplicates an existing
            task in the plan.
        pydantic.ValidationError: When a dict task fails model validation.
    """
    if not isinstance(task, Task):
        task = Task.model_validate(task)
    return backend.append_task(plan, task)


def finalize_plan(backend: TaskBackend, plan: str) -> dict[str, Any]:
    """Transition a plan from drafting state to ready state.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation delegates to
    ``backend.finalize_plan``.

    The backend resolves the issue association internally from the plan
    index; no caller-provided issue is needed at finalize time. After
    finalize, the plan transitions from ``state="drafting"`` to
    ``state="ready"`` and becomes available for execution via
    ``sam_plan(action='ready')`` and ``/dh:implement-feature``.

    See ADR-1770-1 for the single-writer contract (callers must serialize
    writes to the same plan).

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        plan: Plan address string (e.g. ``"P1"`` or slug).

    Returns:
        Dict with ``finalized`` (``True``) and ``state`` (``"ready"``)
        keys, matching the shape returned by
        ``backend.finalize_plan``.

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
    """
    return backend.finalize_plan(plan)


def read_task(backend: TaskBackend, plan: str, task: str) -> dict[str, Any]:
    """Read a single task with its full plan context and return a serialized assignment.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation handles all business logic: plan
    retrieval, task retrieval, Task model conversion, TaskAssignment
    construction, and dict serialization.

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        plan: Plan address string (e.g. ``"P1"`` or slug).
        task: Task ID within the plan (e.g. ``"T3"``).

    Returns:
        Dict serialized from a :class:`~sam_schema.core.models.TaskAssignment`
        model via ``model_dump(mode="json", by_alias=True, exclude_none=True)``.
        Contains the plan number, slug, goal, context, acceptance
        criteria, and the full task model.

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
        TaskNotFoundError: When the task ID cannot be resolved in the plan.
    """
    plan_data = backend.read_plan(plan)
    task_data = backend.read_task(plan, task)
    task_model = Task.model_validate(task_data)
    assignment = TaskAssignment(
        plan_number=plan_data.get("plan_id", plan),
        plan_slug=plan_data.get("feature") or None,
        plan_goal=plan_data.get("goal") or None,
        plan_context=plan_data.get("context") or None,
        plan_acceptance_criteria=plan_data.get("acceptance_criteria") or plan_data.get("acceptance-criteria") or None,
        task=task_model,
    )
    return assignment.model_dump(mode="json", by_alias=True, exclude_none=True)


def claim_task(backend: TaskBackend, plan: str, task: str) -> dict[str, Any]:
    """Claim a task for dispatch, with local-backend fallback for local-only plans.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation handles all business logic: claim
    attempt, ``ConcurrentClaimUnsupportedError`` fallback to the local
    backend for local-only plans (ADR-2509-3), and the "not claimed"
    status-check error path.

    When the backend raises :class:`ConcurrentClaimUnsupportedError`
    (indicating a local-only plan with no GitHub issue), the operation
    falls back to ``backend.local`` when available (GistTaskLayer), or
    to ``backend`` itself otherwise. This uses
    ``getattr(backend, "local", backend)`` to stay backend-agnostic.

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        plan: Plan address string (e.g. ``"P1"`` or slug).
        task: Task ID within the plan (e.g. ``"T3"``).

    Returns:
        On success: dict with ``claimed`` (``True``), ``task_id``, and
        ``started`` (ISO 8601 UTC timestamp). When the claim fell back
        to the local backend, a ``warnings`` key is added with a
        non-portability notice. On failure: dict with ``claimed``
        (``False``) and an ``error`` message describing why the task
        could not be claimed.

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
        TaskNotFoundError: When the task ID cannot be resolved in the plan.
    """
    try:
        claimed, claim_warning = backend.claim_task(plan, task), None
    except ConcurrentClaimUnsupportedError:
        # Local-only plan (issue=None): fall back to local backend claim.
        local_backend = getattr(backend, "local", backend)
        claimed = local_backend.claim_task(plan, task)
        claim_warning = (
            f"Plan '{plan}' has no associated GitHub issue — claimed locally only. "
            "Parallel dispatch is not supported for local-only plans. "
            "Associate a GitHub issue with this plan for multi-agent dispatch support."
        )
        _log.warning("claim_task: %s", claim_warning)

    if not claimed:
        try:
            task_data = backend.read_task(plan, task)
            current_status = task_data["status"]
        except (PlanNotFoundError, TaskNotFoundError, SamError):
            return {"claimed": False, "error": f"Cannot claim task '{task}': task is not available for claiming."}
        return {
            "claimed": False,
            "error": (f"Cannot claim task '{task}': expected status 'not-started' but found '{current_status}'."),
        }

    result: dict[str, Any] = {"claimed": True, "task_id": task, "started": datetime.now(UTC).isoformat()}
    if claim_warning is not None:
        result["warnings"] = [claim_warning]
    return result


def update_task_status(backend: TaskBackend, plan: str, task: str, status: str) -> dict[str, Any]:
    """Update the status of a task, cascading SKIPPED to downstream tasks on failure.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation delegates to
    ``backend.update_task_status`` and assembles the response dict.

    When *status* is ``FAILED``, a :class:`DependencyGraph` is built from
    the plan's tasks and all downstream tasks are marked ``SKIPPED`` via
    ``backend.update_task_status`` and ``backend.update_task_fields`` (to
    record a reason). The list of skipped task IDs is returned in the
    ``skipped_downstream`` key.

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        plan: Plan address string (e.g. ``"P1"`` or slug).
        task: Task ID within the plan (e.g. ``"T3"``).
        status: New status string. When equal to
            :attr:`TaskStatus.FAILED`, downstream tasks are skipped.

    Returns:
        Dict with ``id`` (the task ID) and ``status`` keys. When
        *status* is ``FAILED``, also includes ``skipped_downstream`` (a
        list of task IDs that were marked ``SKIPPED``).

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
        TaskNotFoundError: When the task ID cannot be resolved in the plan.
    """
    backend.update_task_status(plan, task, status)
    if status == TaskStatus.FAILED:
        plan_data = backend.read_plan(plan)
        tasks = [Task.model_validate(task_data) for task_data in plan_data.get("tasks", [])]
        graph = DependencyGraph(tasks)
        skipped: list[str] = graph.mark_downstream_skipped(task)
        for skipped_task_id in skipped:
            backend.update_task_status(plan, skipped_task_id, TaskStatus.SKIPPED)
            backend.update_task_fields(plan, skipped_task_id, {"reason": f"skipped: upstream {task} failed"})
        return {"id": task, "status": status, "skipped_downstream": skipped}
    return {"id": task, "status": status}


def _validated_task_patch(backend: TaskBackend, plan: str, task: str, raw_fields: dict[str, Any]) -> Task:
    """Validate raw JSON patch fields through the Pydantic Task model.

    Reads the current task, merges *raw_fields* into its data, then passes
    the merged dict through ``Task.model_validate`` so field validators run
    (e.g. ``validate_task_id_list`` normalises ``dependencies``).  Returns
    the fully-validated Task model for the caller to write via
    ``backend.update_task``.

    Args:
        backend: Active TaskBackend instance.
        plan: Plan address string.
        task: Task identifier within the plan.
        raw_fields: JSON-decoded patch dict from ``set_fields_json``.

    Returns:
        Fully-validated Task model with the patched fields applied.

    Raises:
        PlanNotFoundError: When *plan* cannot be resolved by the backend.
        TaskNotFoundError: When *task* does not exist within the plan.
        pydantic.ValidationError: When a field value fails Task model
            validation.
    """
    task_data = backend.read_task(plan, task)
    current = Task.model_validate(task_data)
    return Task.model_validate({**current.model_dump(by_alias=True, mode="json"), **raw_fields})


def update_task_fields(
    backend: TaskBackend,
    plan: str,
    task: str,
    *,
    set_fields_json: dict[str, Any] | None = None,
    append_section: str | None = None,
    section_content: str | None = None,
) -> dict[str, Any]:
    """Update fields and/or append a section to a task.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation handles all business logic: raw field
    validation through the Task model (when ``set_fields_json`` is
    provided), delegation to ``backend.update_task`` and
    ``backend.append_task_section``, and response assembly.

    When ``set_fields_json`` is provided, the raw fields are validated by
    reading the current task, merging the raw fields into its data,
    passing the merged dict through ``Task.model_validate`` (so field
    validators run), and passing the validated Task model to
    ``backend.update_task``. This ensures the backend receives normalized
    field values, not raw input.

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        plan: Plan address string (e.g. ``"P1"`` or slug).
        task: Task ID within the plan (e.g. ``"T3"``).
        set_fields_json: Optional dict of raw field-value pairs to patch
            onto the task. Keys use kebab-case (wire convention). Values
            are normalized through the Task model before being passed to
            the backend. When ``None``, no task-level fields are modified.
        append_section: Optional section name to append to the task's
            content. When ``None``, no section is appended.
        section_content: Content for the appended section. Ignored when
            ``append_section`` is ``None``. Defaults to an empty string
            when ``append_section`` is set but this is ``None``.

    Returns:
        Dict with ``updated`` (``True``) and ``address``
        (``"{plan}/{task}"``) keys.

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
        TaskNotFoundError: When the task ID cannot be resolved in the
            plan.
        pydantic.ValidationError: When a field value fails Task model
            validation.
    """
    if set_fields_json is not None:
        validated_task = _validated_task_patch(backend, plan, task, set_fields_json)
        backend.update_task(plan, validated_task)
    if append_section is not None:
        backend.append_task_section(plan, task, append_section, section_content or "")
    return {"updated": True, "address": f"{plan}/{task}"}
