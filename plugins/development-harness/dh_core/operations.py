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
from typing import TYPE_CHECKING, Any

from sam_schema.core.exceptions import ArtifactWriteError
from sam_schema.core.models import Plan, PlanState, Task

if TYPE_CHECKING:
    from dh_core.protocols import TaskBackend

_log = logging.getLogger(__name__)

__all__ = ["create_plan", "get_plan_status", "get_ready_tasks", "list_plans", "read_plan"]


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
