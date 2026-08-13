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

import asyncio
import collections
import contextlib
import dataclasses
import json
import logging
import os
import re
import sqlite3
import sys
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar, cast

import dispatch_schema as _ds
from backlog_core.artifact_manifest_store import (
    artifact_content_reference,
    load_manifest as _load_manifest_record,
    publish_artifact,
)
from backlog_core.artifact_registry import ArtifactRegistry
from backlog_core.backend_protocol import get_config
from backlog_core.backend_types import ContentProvider, GitHubExtras
from backlog_core.dispatch_state import DispatchStateManager
from backlog_core.models import (
    ArtifactContent,
    ArtifactEntry,
    ArtifactManifest,
    ArtifactStatus,
    ArtifactType,
    BacklogError,
    ContentConflictError,
    ContentKind,
    ContentNotFoundError,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
    DispatchItemRecord,
    DispatchSpawnSummary,
    DispatchWaveSummary,
    GitHubUnavailableError,
    Output,
    UnsupportedCapabilityError,
    get_repo_root,
)
from dispatch_schema import Wave
from github import GithubException
from pydantic import BaseModel
from sam_schema.core.dependencies import DependencyGraph
from sam_schema.core.exceptions import ConcurrentClaimUnsupportedError, PlanNotFoundError, SamError, TaskNotFoundError
from sam_schema.core.models import (
    AcceptanceCriterion,
    ActiveTaskClearResult,
    ActiveTaskGetResult,
    ActiveTaskSetResult,
    ActiveTaskUpdateResult,
    AppendTaskResult,
    ClaimResult,
    CreatePlanResult,
    FinalizePlanResult,
    Plan,
    PlanState,
    PlanStatus,
    PlanSummaryModel,
    ReadResult,
    ReadyTasksResult,
    SchemaGap,
    StateResult,
    Task,
    TaskAssignment,
    TaskStatus,
    UpdatePlanResult,
    UpdateTaskResult,
)

if TYPE_CHECKING:
    from backlog_core.operations import ImpactRadiusItem
    from sam_schema.core.context_backend import ContextBackend

    from dh_core.protocols import TaskBackend

_log = logging.getLogger(__name__)

__all__ = [
    # --- Backlog operations re-exports ---
    "add_item",
    "analyze_impact_radius_conflicts",
    "append_task",
    "apply_status_groomed",
    "apply_status_in_progress",
    "apply_status_verified",
    "artifact_get",
    "artifact_list",
    "artifact_read",
    # --- Artifact operations ---
    "artifact_register",
    "batch_fetch_statuses",
    "check_open_prs_for_issue",
    "claim_task",
    "clear_active_task",
    "close_github_issue",
    "close_item",
    "comment_issue",
    "create_issue_for_item",
    "create_milestone",
    "create_plan",
    "create_project",
    "create_sam_task",
    "create_task_issue",
    "dispatch_conflicts",
    "dispatch_create_plan",
    "dispatch_item_status",
    "dispatch_read_plan",
    "dispatch_spawn",
    "dispatch_stale_check",
    "dispatch_validate_plan",
    "dispatch_wave_start",
    "dispatch_wave_status",
    "fetch_github_issue_body",
    "fetch_open_issues_by_title",
    "finalize_plan",
    "find_or_create_issue",
    "get_active_task",
    "get_github",
    "get_plan_status",
    "get_ready_sam_tasks",
    "get_ready_tasks",
    "get_sam_tasks",
    "get_soonest_milestone",
    "get_task_issues",
    "groom_item",
    "issue_to_local_fields",
    "link_followup",
    "list_comments",
    "list_followups",
    "list_issues",
    "list_items",
    "list_labels",
    "list_merged_prs",
    "list_milestones",
    "list_plans",
    "list_projects",
    "merge_item_models",
    "narrow_body_to_named_sections",
    "normalize_items",
    "parse_issue_body_sync",
    "pull_by_selector",
    "pull_items",
    "pull_single_issue",
    "read_comment",
    "read_plan",
    "read_task",
    "refresh_local_cache_from_github",
    "render_issue_body",
    "render_sections_as_body",
    "resolve_github_issue",
    "resolve_item",
    "set_active_task",
    "strike_entry",
    "sync_create_missing_issues",
    "sync_issues_graphql",
    "sync_items",
    "try_get_github",
    "unknown_key_to_heading",
    "update_active_task",
    "update_issue_task_status",
    "update_item",
    "update_item_metadata",
    "update_plan_fields",
    "update_sam_task_status",
    "update_task_fields",
    "update_task_status",
    "view_enrich_from_github",
    "view_item",
]


def create_plan(
    backend: TaskBackend,
    *,
    slug: str,
    goal: str,
    tasks: list[dict[str, Any]] | list[Any],
    context: str | None = None,
    issue: int | None = None,
    owner_reference: str | None = None,
    acceptance_criteria_structured: list[AcceptanceCriterion] | None = None,
) -> CreatePlanResult:
    """Create a new plan with the given slug, goal, and task definitions.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the configured backend and pass it here. The
    operation handles plan creation and response assembly.

    Args:
        backend: The configured task backend.
        slug: Human-readable identifier slug for the plan.
        goal: One-sentence goal statement for the plan.
        tasks: List of task definitions (dicts or Task models).
        context: Optional plan-level context narrative (markdown).
        issue: Optional GitHub issue number to associate with the plan.
        owner_reference: Optional opaque provider-native owner reference.
        acceptance_criteria_structured: Optional executable acceptance criteria.

    Returns:
        :class:`~sam_schema.core.models.CreatePlanResult` on success with
        ``plan_id``, ``task_count``, and ``plan_ref``.

    Raises:
        ValueError: When any task definition fails schema validation.
        ArtifactWriteError: When the configured provider cannot persist the plan.
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

    plan_data = backend.create_plan(
        slug=slug,
        goal=goal,
        tasks=normalized_tasks,
        context=context,
        issue=issue,
        owner_reference=owner_reference,
        acceptance_criteria_structured=acceptance_criteria_structured,
    )

    plan_id_str = plan_data["plan_id"]

    # Compute plan_ref: #{issue},{plan_id} when issue is set, else plan_id.
    plan_ref = f"#{issue},{plan_id_str}" if issue is not None else plan_id_str

    return CreatePlanResult(plan_id=plan_id_str, task_count=len(plan_data["tasks"]), plan_ref=plan_ref)


def read_plan(backend: TaskBackend, plan: str) -> ReadResult:
    """Read a plan by its address and return a :class:`ReadResult`.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the configured backend and pass it here. The
    operation handles plan retrieval and model conversion.

    Args:
        backend: The configured task backend.
        plan: Plan address string (e.g. ``"P1"`` or slug).

    Returns:
        A :class:`~sam_schema.core.models.ReadResult` containing the
        parsed :class:`~sam_schema.core.models.Plan` and any
        :class:`~sam_schema.core.models.SchemaGap` records.

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
    """
    plan_data = backend.read_plan(plan)
    plan_model = Plan.model_validate(plan_data)

    source_path_str = plan_data.get("source_path") or ""
    source_path = Path(source_path_str) if source_path_str else Path()

    # Preserve schema gaps from the backend (populated by LocalYamlTaskProvider
    # from the reader/normalizer pipeline). Other backends (e.g. GitHub) don't
    # detect gaps, so the key is absent and we default to an empty list.
    raw_gaps = plan_data.get("gaps") or []
    gaps = [SchemaGap.model_validate(g) for g in raw_gaps]

    return ReadResult(plan=plan_model, gaps=gaps, source_format="backend", source_path=source_path)


def list_plans(
    backend: TaskBackend,
    *,
    search: str | None = None,
    offset: int = 0,
    limit: int | None = None,
    filter_by_key: dict[str, str] | None = None,
) -> list[PlanSummaryModel]:
    """List all plans with optional search filtering and pagination.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation handles all business logic: plan
    listing, search filtering (delegated to the backend), summary
    enrichment, and offset/limit pagination.

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        search: Optional case-insensitive substring filter applied across
            ``feature``, ``description``, and ``goal`` fields. Delegated
            to the backend's ``list_plans`` method.
        offset: Zero-based index of the first item to return.
        limit: Maximum number of items to return. ``None`` means no limit.
        filter_by_key: Generic Jira-style key filter. Each ``key=value``
            pair matches items where the item's value for ``key`` equals
            ``value`` (string comparison). All pairs compose with AND
            logic. A key the item does not carry returns no match (a
            no-op, not an error). Applied after backend listing and
            summary enrichment, so any key in the returned summary models
            (e.g. ``feature``, ``goal``, ``issue``, ``plan_id``) is
            addressable. Existing ``search`` and offset/limit filters are
            unaffected.

    Returns:
        List of :class:`~sam_schema.core.models.PlanSummaryModel`
        instances, each containing ``feature``, ``goal``, ``description``,
        ``task_count``, ``issue``, and ``plan_ref``.
    """
    summaries = backend.list_plans(search=search)
    all_items: list[PlanSummaryModel] = [
        PlanSummaryModel(
            plan_id=s["plan_id"],
            feature=s["feature"],
            goal=s["goal"],
            description=s["description"],
            task_count=s["task_count"],
            source_path=s.get("source_path"),
            issue=s.get("issue"),
            plan_ref=(f"#{s['issue']},{s['plan_id']}" if s.get("issue") else s.get("plan_id")),
        )
        for s in summaries
    ]

    if filter_by_key:
        all_items = _apply_key_filter(all_items, filter_by_key)

    total = len(all_items)
    page = all_items[offset:] if limit is None else all_items[offset : offset + limit]
    _log.debug("list_plans: %d of %d plans returned", len(page), total)
    return page


_T = TypeVar("_T")


def _apply_key_filter(items: list[_T], filter_by_key: dict[str, str]) -> list[_T]:
    """Filter ``items`` by generic key=value pairs (AND logic).

    An item matches when every ``key`` in ``filter_by_key`` is present on
    the item AND the item's value for that key equals the requested value
    (string comparison). Items missing any requested key are excluded —
    a no-op for absent keys, not an error.

    Args:
        items: List of mapping or Pydantic-model items to filter.
        filter_by_key: Mapping of key names to required string values.

    Returns:
        Filtered list of items matching all key=value pairs.
    """
    if not filter_by_key:
        return items
    return [it for it in items if all(str(_item_value(it, k)) == v for k, v in filter_by_key.items())]


def _item_value(item: object, key: str) -> object:
    """Return the value for *key* from a mapping or Pydantic model.

    Supports both ``dict.get`` and model-attribute access so callers can
    filter mixed or uniformly-typed item lists without branching.
    """
    if isinstance(item, BaseModel):
        return getattr(item, key, None)
    if isinstance(item, Mapping):
        mapping = cast("Mapping[str, object]", item)
        return mapping.get(key)
    return getattr(item, key, None)


def get_plan_status(backend: TaskBackend, plan: str) -> PlanStatus:
    """Return plan-level progress summary including autonomy mode.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation handles all business logic: status
    retrieval, drafting-state check, and autonomy field enrichment.

    When the plan is in the ``DRAFTING`` state, the returned model carries
    ``state=PlanState.DRAFTING`` instead of raising an exception.

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        plan: Plan address string (e.g. ``"P1"`` or slug).

    Returns:
        A :class:`~sam_schema.core.models.PlanStatus` model with task
        counts, ready/blocked task lists, completion percentage, cycle
        detection result, and plan ``state``. The ``autonomy`` field is
        sourced from ``backend.read_plan`` (defaulting to ``"full_auto"``
        when absent).

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
    """
    result = read_plan(backend, plan)
    plan_model = result.plan
    graph = DependencyGraph(plan_model.tasks)
    by_status: dict[str, int] = {}
    for task in plan_model.tasks:
        by_status[task.status] = by_status.get(task.status, 0) + 1
    total = len(plan_model.tasks)
    complete_count = by_status.get(TaskStatus.COMPLETE, 0)
    completion_pct = (complete_count / total * 100.0) if total > 0 else 0.0
    return PlanStatus(
        feature=plan_model.feature,
        total_tasks=total,
        by_status=by_status,
        ready_tasks=[t.id for t in graph.get_ready_tasks()],
        blocked_tasks=[{t.id: missing} for t, missing in graph.get_blocked_tasks()],
        completion_pct=completion_pct,
        has_cycles=graph.has_cycles(),
        issue=plan_model.issue,
        autonomy=plan_model.autonomy,
        state=plan_model.state,
    )


def get_ready_tasks(backend: TaskBackend, plan: str, *, full: bool = False) -> ReadyTasksResult:
    """Return tasks ready for dispatch along with plan-level metadata.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation handles all business logic: drafting
    check, ready-task retrieval, and ``feature``/``issue`` enrichment
    from the plan record.

    When the plan is in the ``DRAFTING`` state, the returned model carries
    ``state=PlanState.DRAFTING`` and an empty ``ready_tasks`` list.

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        plan: Plan address string (e.g. ``"P1"`` or slug).
        full: When ``False`` (default), return a compact 7-field routing
            manifest per task: ``id``, ``task``, ``agent``, ``skills``,
            ``dependencies``, ``status``, ``priority``. When ``True``,
            return the full :class:`~sam_schema.core.models.Task` model.

    Returns:
        A :class:`~sam_schema.core.models.ReadyTasksResult` model with
        ``feature``, ``ready_tasks`` (list of Task models), ``count``,
        ``issue``, and ``state`` fields.

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
    """
    status = get_plan_status(backend, plan)
    if status.state == PlanState.DRAFTING:
        tasks_data: list[dict[str, Any]] = []
    else:
        tasks_data = backend.get_ready_tasks(plan)
    tasks = [Task.model_validate(t) for t in tasks_data]
    return ReadyTasksResult(
        feature=status.feature, ready_tasks=tasks, count=len(tasks), issue=status.issue, state=status.state
    )


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
    backend: TaskBackend,
    plan: str,
    *,
    context: str | None = None,
    set_fields: dict[str, Any] | None = None,
    task_id: str | None = None,
    append_section_name: str | None = None,
    section_content: str | None = None,
) -> UpdatePlanResult:
    """Update plan-level context/fields and/or task-level fields on the backend.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation handles all business logic: raw field
    validation through the Plan model (when ``set_fields`` is provided),
    task-level field updates, section appends, and response assembly.

    When ``set_fields`` is provided without ``task_id``, the raw fields are
    validated by reading the current plan, merging the raw fields into its
    data, passing the merged dict through ``Plan.model_validate`` (so field
    validators run), and extracting only the requested keys from the
    validated model. This ensures the backend receives normalized field
    values, not raw input.

    When ``task_id`` is provided, task-level operations are delegated to
    ``backend.update_task_fields`` (for ``set_fields``) and
    ``backend.append_task_section`` (for ``append_section_name``).

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        plan: Plan address string (e.g. ``"P1"`` or slug).
        context: Optional plan-level context narrative (markdown). When
            ``None``, the plan's existing context is not modified.
        set_fields: Optional dict of raw field-value pairs to patch onto
            the plan or task. Keys use kebab-case (wire convention). Values
            are normalized through the Plan model before being passed to
            the backend. When ``None``, no fields are modified.
        task_id: Task ID to target for task-level operations. ``None`` means
            plan-level operations only.
        append_section_name: Section heading to append. Requires
            ``section_content`` and ``task_id``.
        section_content: Body text for the appended section.

    Returns:
        :class:`~sam_schema.core.models.UpdatePlanResult` with ``updated``
        (``True``) and ``address`` (the plan address string) fields.

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
        pydantic.ValidationError: When a field value fails Plan model
            validation.
        ValueError: When ``append_section_name`` is given without ``task_id``
            or ``section_content``.
    """
    if append_section_name is not None:
        if task_id is None:
            msg = "append_section_name requires task_id"
            raise ValueError(msg)
        if not section_content:
            msg = "append_section_name requires section_content"
            raise ValueError(msg)

    plan_fields: dict[str, Any] | None = None
    if set_fields is not None and task_id is None:
        validated = _validated_plan_patch(backend, plan, set_fields)
        # by_alias=True: set_fields uses kebab-case keys (wire convention);
        # alias keys must match so we extract only the requested keys.
        plan_fields = {k: v for k, v in validated.model_dump(by_alias=True, mode="json").items() if k in set_fields}
        if "acceptance-criteria-structured" in plan_fields:
            plan_fields["acceptance-criteria-structured"] = [
                criterion.model_dump(mode="json") for criterion in validated.acceptance_criteria_structured
            ]

    # Only call the plan-level update when there is something to write at the
    # plan level (context narrative or validated plan-level fields). Task-only
    # writes should not trigger a no-op plan update.
    if context is not None or plan_fields is not None:
        backend.update_plan_fields(plan, context=context, set_fields=plan_fields)

    if set_fields is not None and task_id is not None:
        backend.update_task_fields(plan, task_id, set_fields)

    if append_section_name is not None and task_id is not None and section_content:
        backend.append_task_section(plan, task_id, append_section_name, section_content)

    return UpdatePlanResult(updated=True, address=plan)


def append_task(backend: TaskBackend, plan: str, task: Task | dict[str, Any]) -> AppendTaskResult:
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
        :class:`~sam_schema.core.models.AppendTaskResult` with ``appended``
        (``True``), ``task_id``, and optional ``github_issue`` fields.

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
        TaskValidationError: When the task ID duplicates an existing
            task in the plan.
        pydantic.ValidationError: When a dict task fails model validation.
    """
    if not isinstance(task, Task):
        if isinstance(task, dict) and "task" in task and "id" not in task:
            # Accept "task" key as the task id (YAML frontmatter convention)
            task = {**task, "id": task.pop("task")}
        task = Task.model_validate(task)
    result = backend.append_task(plan, task)
    return AppendTaskResult(
        appended=result["appended"], task_id=result["task_id"], github_issue=result.get("github_issue")
    )


def finalize_plan(backend: TaskBackend, plan: str) -> FinalizePlanResult:
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
        :class:`~sam_schema.core.models.FinalizePlanResult` with
        ``finalized`` (``True``) and ``state`` (``"ready"``) fields.

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
    """
    result = backend.finalize_plan(plan)
    return FinalizePlanResult(finalized=result["finalized"], state=result["state"])


def read_task(backend: TaskBackend, plan: str, task: str) -> TaskAssignment:
    """Read a single task with its full plan context and return a TaskAssignment.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation handles all business logic: plan
    retrieval, task retrieval, Task model conversion, and
    TaskAssignment construction.

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        plan: Plan address string (e.g. ``"P1"`` or slug).
        task: Task ID within the plan (e.g. ``"T3"``).

    Returns:
        A :class:`~sam_schema.core.models.TaskAssignment` model containing
        the plan number, slug, goal, context, acceptance criteria, and
        the full task model.

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
        TaskNotFoundError: When the task ID cannot be resolved in the plan.
    """
    plan_data = backend.read_plan(plan)
    task_data = backend.read_task(plan, task)
    task_model = Task.model_validate(task_data)
    return TaskAssignment(
        plan_number=plan_data.get("plan_id", plan),
        plan_slug=plan_data.get("feature") or None,
        plan_goal=plan_data.get("goal") or None,
        plan_context=plan_data.get("context") or None,
        plan_acceptance_criteria=plan_data.get("acceptance_criteria") or plan_data.get("acceptance-criteria") or None,
        task=task_model,
    )


def claim_task(backend: TaskBackend, plan: str, task: str) -> ClaimResult:
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
        A :class:`~sam_schema.core.models.ClaimResult` model with
        ``claimed`` (``True``), ``task_id``, ``started`` timestamp, and
        optional ``warnings`` (e.g. local-only plan notice).

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
        TaskNotFoundError: When the task ID cannot be resolved in the plan.
        ValueError: When the task is not in ``not-started`` status (already
            claimed or in a terminal state).
    """
    warnings: list[str] = []
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

    if claim_warning is not None:
        warnings.append(claim_warning)

    if not claimed:
        try:
            task_data = backend.read_task(plan, task)
            current_status = task_data["status"]
        except (PlanNotFoundError, TaskNotFoundError, SamError):
            msg = f"Cannot claim task '{task}': task is not available for claiming."
            raise ValueError(msg) from None
        return ClaimResult(
            claimed=False,
            task_id=task,
            started=None,
            warnings=[f"Task is '{current_status}', not 'not-started' — already claimed or in a terminal state."],
        )

    # Re-read the task to get the updated model with started timestamp.
    task_data = backend.read_task(plan, task)
    task_model = Task.model_validate(task_data)
    started_str: str | None = None
    if task_model.started is not None:
        started_str = task_model.started.isoformat()
    return ClaimResult(claimed=True, task_id=task_model.id, started=started_str, warnings=warnings or None)


def update_task_status(backend: TaskBackend, plan: str, task: str, status: str) -> StateResult:
    """Update the status of a task, cascading SKIPPED to downstream tasks on failure.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation delegates to
    ``backend.update_task_status`` and returns a typed result model.

    When *status* is ``FAILED``, a :class:`DependencyGraph` is built from
    the plan's tasks and all downstream tasks are marked ``SKIPPED`` via
    ``backend.update_task_status`` and ``backend.update_task_fields`` (to
    record a reason). The list of skipped task IDs is returned in the
    ``skipped_downstream`` field.

    Args:
        backend: The resolved TaskBackend instance (e.g. GistTaskLayer,
            LocalYamlTaskProvider). The caller is responsible for
            backend selection — this function is backend-agnostic.
        plan: Plan address string (e.g. ``"P1"`` or slug).
        task: Task ID within the plan (e.g. ``"T3"``).
        status: New status string. When equal to
            :attr:`TaskStatus.FAILED`, downstream tasks are skipped.

    Returns:
        :class:`~sam_schema.core.models.StateResult` with ``id``,
        ``status``, and optional ``skipped_downstream`` fields.

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
        return StateResult(id=task, status=status, skipped_downstream=skipped)
    return StateResult(id=task, status=status)


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
) -> UpdateTaskResult:
    """Update fields and/or append a section to a task.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the backend (local YAML, GistTaskLayer, etc.)
    and pass it here. The operation handles all business logic: raw field
    validation through the Task model (when ``set_fields_json`` is
    provided), delegation to ``backend.update_task`` and
    ``backend.append_task_section``, and returns a typed result model.

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
        :class:`~sam_schema.core.models.UpdateTaskResult` with
        ``updated`` (``True``) and ``address`` (``"{plan}/{task}"``)
        fields.

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
    return UpdateTaskResult(updated=True, address=f"{plan}/{task}")


def get_active_task(ctx_backend: ContextBackend, session_id: str) -> ActiveTaskGetResult:
    """Retrieve the active task context for a session.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the context backend (LocalContextBackend,
    GitHubContextBackend, etc.) and pass it here. The operation delegates
    to ``ctx_backend.get_active_task`` and returns a typed result model.

    Args:
        ctx_backend: The resolved ContextBackend instance. The caller is
            responsible for backend selection — this function is
            backend-agnostic.
        session_id: Session identifier to scope the lookup. Callers
            should resolve the ``None`` sentinel to ``"_default"`` before
            calling (matching the MCP server convention).

    Returns:
        :class:`~sam_schema.core.models.ActiveTaskGetResult` with an
        ``active_task`` field. When a context exists, the value is the
        :class:`~sam_schema.core.models.ActiveTaskContext` model. When no
        context exists, the value is ``None``.
    """
    active = ctx_backend.get_active_task(session_id)
    return ActiveTaskGetResult(active_task=active)


def set_active_task(
    ctx_backend: ContextBackend,
    session_id: str,
    plan: str,
    task: str,
    plan_dir: str,
    parent_issue_number: str | int | None = None,
) -> ActiveTaskSetResult:
    """Store a task address as the active task for a session.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the context backend (LocalContextBackend,
    GitHubContextBackend, etc.) and pass it here. The operation delegates
    to ``ctx_backend.set_active_task`` and returns a typed result model.

    Args:
        ctx_backend: The resolved ContextBackend instance. The caller is
            responsible for backend selection — this function is
            backend-agnostic.
        session_id: Session identifier to scope the storage. Callers
            should resolve the ``None`` sentinel to ``"_default"`` before
            calling (matching the MCP server convention).
        plan: Plan address to register (e.g., ``"P1"`` or slug).
        task: Task ID within the plan (e.g., ``"T3"``).
        plan_dir: Plan directory path sentinel or absolute path. Stored
            alongside plan/task so retrieval uses the same backend.
        parent_issue_number: Optional GitHub issue number (int) or beads
            nanoid (str, e.g. ``"bd-a3f8"``) for the parent story.

    Returns:
        :class:`~sam_schema.core.models.ActiveTaskSetResult` with an
        ``active_task`` field containing the stored
        :class:`~sam_schema.core.models.ActiveTaskContext` model.
    """
    active = ctx_backend.set_active_task(session_id, plan, task, plan_dir, parent_issue_number)
    return ActiveTaskSetResult(active_task=active)


def update_active_task(
    ctx_backend: ContextBackend,
    session_id: str,
    task_backend: TaskBackend,
    *,
    set_fields_json: dict[str, Any] | None = None,
    append_section: str | None = None,
    section_content: str | None = None,
) -> ActiveTaskUpdateResult:
    """Update fields and/or append a section on the active task.

    This is the unified operation called by both the CLI and MCP server.
    It reads the active task context from *ctx_backend* to recover the
    plan address and task ID, then delegates field/section updates to
    *task_backend* via :func:`update_task_fields`.

    The active task context stores structured ``plan`` and ``task``
    fields (the plan address and task ID). These are used directly —
    no filesystem path derivation is performed in the operations layer.
    The caller resolves the *task_backend* from the active task's
    ``plan_dir`` field before calling this function.

    Args:
        ctx_backend: The resolved ContextBackend instance used to read
            the active task context. The caller is responsible for
            backend selection — this function is backend-agnostic.
        session_id: Session identifier to scope the lookup. Callers
            should resolve the ``None`` sentinel to ``"_default"`` before
            calling (matching the MCP server convention).
        task_backend: The resolved TaskBackend instance used to apply
            field/section updates. The caller is responsible for
            resolving it from the active task's ``plan_dir`` field
            (matching the MCP server's ``_get_backend`` lookup).
        set_fields_json: Optional dict of raw field-value pairs to
            patch onto the task. Keys use kebab-case (wire convention).
            Values are normalized through the Task model before being
            passed to the backend. When ``None``, no task-level fields
            are modified.
        append_section: Optional section name to append to the task's
            content. When ``None``, no section is appended.
        section_content: Content for the appended section. Ignored when
            ``append_section`` is ``None``. Defaults to an empty string
            when ``append_section`` is set but this is ``None``.

    Returns:
        :class:`~sam_schema.core.models.ActiveTaskUpdateResult` with
        ``updated`` (``True``) and ``address`` (``"{plan}/{task}"``)
        fields.

    Raises:
        ValueError: When no active task has been set for *session_id*,
            or when the context lacks structured ``plan``/``task``
            fields (pre-additive-schema contexts).
        PlanNotFoundError: When the plan address cannot be resolved.
        TaskNotFoundError: When the task ID cannot be resolved in the
            plan.
        pydantic.ValidationError: When a field value fails Task model
            validation.
    """
    active = ctx_backend.get_active_task(session_id)
    if active is None:
        msg = "update_active_task: no active task set for this session. Call set_active_task(...) first."
        raise ValueError(msg)
    if active.plan is None or active.task is None:
        msg = (
            "update_active_task: active task context lacks structured plan/task fields. "
            "Call set_active_task(...) again to populate them."
        )
        raise ValueError(msg)
    update_result = update_task_fields(
        task_backend,
        active.plan,
        active.task,
        set_fields_json=set_fields_json,
        append_section=append_section,
        section_content=section_content,
    )
    return ActiveTaskUpdateResult(updated=update_result.updated, address=update_result.address)


def clear_active_task(ctx_backend: ContextBackend, session_id: str) -> ActiveTaskClearResult:
    """Remove the active task context for a session.

    This is the unified operation called by both the CLI and MCP server.
    Both frontends resolve the context backend (LocalContextBackend,
    GitHubContextBackend, etc.) and pass it here. The operation delegates
    to ``ctx_backend.clear_active_task``.

    Args:
        ctx_backend: The resolved ContextBackend instance. The caller is
            responsible for backend selection — this function is
            backend-agnostic.
        session_id: Session identifier to scope the removal. Callers
            should resolve the ``None`` sentinel to ``"_default"`` before
            calling (matching the MCP server convention).

    Returns:
        :class:`~sam_schema.core.models.ActiveTaskClearResult` with a
        ``cleared`` field (``True`` when a context existed and was
        removed, ``False`` when no context was found).
    """
    removed = ctx_backend.clear_active_task(session_id)
    return ActiveTaskClearResult(cleared=removed)


# --- Backlog operations re-export ---
# Re-export all public functions from backlog_core.operations so both
# frontends have a single import surface (dh_core.operations).
from backlog_core.operations import (
    add_item,
    analyze_impact_radius_conflicts,
    apply_status_groomed,
    apply_status_in_progress,
    apply_status_verified,
    batch_fetch_statuses,
    check_open_prs_for_issue,
    close_github_issue,
    close_item,
    comment_issue,
    create_issue_for_item,
    create_milestone,
    create_project,
    create_sam_task,
    create_task_issue,
    fetch_github_issue_body,
    fetch_open_issues_by_title,
    find_or_create_issue,
    get_github,
    get_ready_sam_tasks,
    get_sam_tasks,
    get_soonest_milestone,
    get_task_issues,
    groom_item,
    issue_to_local_fields,
    link_followup,
    list_comments,
    list_followups,
    list_issues,
    list_items,
    list_labels,
    list_merged_prs,
    list_milestones,
    list_projects,
    merge_item_models,
    narrow_body_to_named_sections,
    normalize_items,
    parse_issue_body_sync,
    pull_by_selector,
    pull_items,
    pull_single_issue,
    read_comment,
    refresh_local_cache_from_github,
    render_issue_body,
    render_sections_as_body,
    resolve_github_issue,
    resolve_item,
    strike_entry,
    sync_create_missing_issues,
    sync_issues_graphql,
    sync_items,
    try_get_github,
    unknown_key_to_heading,
    update_item,
    update_item_metadata,
    update_sam_task_status,
    update_task_status as update_issue_task_status,
    view_enrich_from_github,
    view_item,
)


# ---------------------------------------------------------------------------
# Dispatch operations (Task 2.31)
# ---------------------------------------------------------------------------
def _get_content_provider() -> ContentProvider:
    provider = get_config().backend
    if not isinstance(provider, ContentProvider):
        raise ContentUnavailableError("Active backend does not support content")
    return provider


def _dispatch_reference(milestone_number: int) -> ContentRef:
    return ContentRef(kind=ContentKind.DISPATCH_PLAN, name=f"dispatch-milestone-{milestone_number}")


def _read_dispatch_plan(milestone_number: int) -> _ds.DispatchPlan:
    record = _get_content_provider().get_content(_dispatch_reference(milestone_number))
    return _ds.DispatchPlan.model_validate_json(record.content)


def dispatch_read_plan(milestone_number: int) -> dict[str, Any]:
    """Read a dispatch plan for the given milestone.

    Returns:
        Dict with ``milestone_number`` and ``plan``, or ``error`` on failure.
    """
    try:
        plan = _read_dispatch_plan(milestone_number)
    except ContentUnavailableError:
        return {"error": "Dispatch plan not found", "milestone_number": milestone_number}
    except ValueError as exc:
        return {"error": str(exc), "milestone_number": milestone_number}
    return {"milestone_number": milestone_number, "plan": plan.model_dump()}


def dispatch_validate_plan(milestone_number: int) -> dict[str, Any]:
    """Validate an existing dispatch plan's structural integrity.

    Returns:
        Dict with ``is_valid``, ``errors``, ``warnings``, or ``error``.
    """
    try:
        plan = _read_dispatch_plan(milestone_number)
    except (ContentUnavailableError, ValueError) as exc:
        return {"error": str(exc), "milestone_number": milestone_number}
    result = _ds.validate_plan_integrity(plan)
    return {"milestone_number": milestone_number, **dataclasses.asdict(result)}


def dispatch_stale_check(milestone_number: int, repo: str = "") -> dict[str, Any]:
    """Check whether a dispatch plan is stale relative to the current milestone.

    Returns:
        Dict with ``is_stale``, ``added_issues``, ``removed_issues``,
        ``message``, or ``error`` on failure.
    """
    try:
        plan = _read_dispatch_plan(milestone_number)
    except (ContentUnavailableError, ValueError) as exc:
        return {"error": str(exc), "milestone_number": milestone_number}

    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        return {"error": "dispatch_stale_check requires a GitHub-backed backend", "milestone_number": milestone_number}
    try:
        gh_repo = backend.get_github(repo)
        owner, repo_name = gh_repo.full_name.split("/", 1)
        open_issues = backend.sync_issues_graphql(
            gh_repo, owner, repo_name, state="OPEN", milestone_number=milestone_number
        )
        closed_issues = backend.sync_issues_graphql(
            gh_repo, owner, repo_name, state="CLOSED", milestone_number=milestone_number
        )
        current_numbers = [issue["number"] for issue in open_issues + closed_issues]
    except GitHubUnavailableError as exc:
        return {"error": str(exc), "milestone_number": milestone_number}
    except (BacklogError, GithubException) as exc:
        return {"error": f"GitHub API error: {exc}", "milestone_number": milestone_number}

    result = _ds.detect_stale_plan(plan, current_numbers)
    return {"milestone_number": milestone_number, **dataclasses.asdict(result)}


def dispatch_create_plan(
    milestone_number: int,
    plan: dict[str, Any],
    overwrite: bool = False,
    validate: bool = True,
    issue: int | None = None,
) -> dict[str, Any]:
    """Create or overwrite a provider-owned dispatch plan for a milestone.

    Returns:
        Dict with ``wave_count``, ``item_count``, ``is_valid``, ``errors``,
        ``warnings``, or ``error`` on failure.
    """
    plan_model = _ds.DispatchPlan.model_validate(plan)

    if plan_model.milestone.number != milestone_number:
        return {
            "error": (
                f"Milestone number mismatch: parameter is {milestone_number} "
                f"but plan.milestone.number is {plan_model.milestone.number}"
            ),
            "milestone_number": milestone_number,
        }

    provider = _get_content_provider()
    reference = _dispatch_reference(milestone_number)
    try:
        current = provider.get_content(reference)
    except ContentNotFoundError:
        write = ContentWrite(reference=reference, content=plan_model.model_dump_json(), create_only=True)
    else:
        if not overwrite:
            return {
                "error": "Dispatch plan already exists. Pass overwrite=True to replace it.",
                "milestone_number": milestone_number,
            }
        write = ContentWrite(
            reference=reference, content=plan_model.model_dump_json(), expected_revision=current.revision
        )

    try:
        provider.put_content(write)
    except (BacklogError, ContentConflictError, UnsupportedCapabilityError) as exc:
        return {"error": str(exc), "milestone_number": milestone_number}

    is_valid: bool | None = None
    val_errors: list[str] = []
    val_warnings: list[str] = []
    if validate:
        val_result = _ds.validate_plan_integrity(plan_model)
        is_valid = val_result.is_valid
        val_errors = list(val_result.errors)
        val_warnings = list(val_result.warnings)

    # Register the dispatch-plan artifact (best-effort) when an issue is provided.
    if issue is not None:
        registration = artifact_register(
            issue,
            ArtifactType.DISPATCH_PLAN.value,
            reference.name,
            content=plan_model.model_dump_json(),
            agent="dispatch_create_plan",
        )
        if "error" in registration:
            _log.warning(
                "dispatch_create_plan: artifact registration failed for item %s (artifact=%s): %s",
                issue,
                reference.name,
                registration["error"],
            )

    wave_count = len(plan_model.waves)
    item_count = sum(len(wave.items) for wave in plan_model.waves)

    return {
        "milestone_number": milestone_number,
        "wave_count": wave_count,
        "item_count": item_count,
        "is_valid": is_valid,
        "errors": val_errors,
        "warnings": val_warnings,
    }


def dispatch_conflicts(milestone_number: int, repo: str = "") -> dict[str, Any]:
    """Analyze Impact Radius conflicts for items in a milestone.

    Returns:
        Dict with ``conflict_groups``, ``count``, ``milestone_number``,
        or ``error`` on failure.
    """
    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        return {"error": "dispatch_conflicts requires a GitHub-backed backend", "milestone_number": milestone_number}
    try:
        gh_repo = backend.get_github(repo)
        owner, repo_name = gh_repo.full_name.split("/", 1)
        issue_nodes = backend.sync_issues_graphql(
            gh_repo, owner, repo_name, state="OPEN", milestone_number=milestone_number
        )
    except GitHubUnavailableError as exc:
        return {"error": str(exc), "milestone_number": milestone_number}
    except (BacklogError, GithubException) as exc:
        return {"error": f"GitHub API error: {exc}", "milestone_number": milestone_number}

    ir_re = re.compile(r"##\s+Impact\s+Radius\b(.*?)(?=\n##|\Z)", re.IGNORECASE | re.DOTALL)
    items: list[ImpactRadiusItem] = []
    for issue in issue_nodes:
        body = issue["body"] or ""
        match = ir_re.search(body)
        impact_radius = match.group(1).strip() if match else ""
        items.append({"title": issue["title"], "issue": issue["number"], "impact_radius": impact_radius})

    conflict_groups = analyze_impact_radius_conflicts(items)
    return {
        "milestone_number": milestone_number,
        "conflict_groups": [cg.model_dump() for cg in conflict_groups],
        "count": len(conflict_groups),
    }


def _dispatch_db_path() -> Path:
    """Return the dispatch state database path for the current project."""
    project_root = get_repo_root()
    project_stub = str(project_root).lstrip("/").replace("/", "-")
    db_path = Path.home() / ".dh" / "projects" / project_stub / "dispatch-state.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def dispatch_wave_start(milestone: int, wave_num: int, items: list[dict[str, object]]) -> dict[str, Any]:
    """Record the start of a dispatch wave.

    Returns:
        Dict with ``milestone``, ``wave_num``, ``items_count``, ``status``,
        or ``error`` if the wave already exists.
    """
    mgr = DispatchStateManager(_dispatch_db_path())
    item_records = [
        DispatchItemRecord(
            milestone=milestone, wave_num=wave_num, issue=int(str(item["issue"])), title=str(item.get("title", ""))
        )
        for item in items
    ]
    try:
        wave = mgr.create_wave(milestone, wave_num, item_records)
    except sqlite3.IntegrityError:
        return {
            "error": f"Wave {wave_num} already exists for milestone {milestone}",
            "milestone": milestone,
            "wave_num": wave_num,
        }
    return {
        "milestone": wave.milestone,
        "wave_num": wave.wave_num,
        "items_count": len(wave.items),
        "status": wave.status,
        "messages": [f"Wave {wave_num} created with {len(wave.items)} items"],
        "warnings": [],
        "errors": [],
    }


def dispatch_item_status(
    milestone: int, issue: int, status: str, result: str = "", error: str = "", cost: float | None = None
) -> dict[str, Any]:
    """Record completion or failure of a dispatch item.

    Returns:
        Dict with ``milestone``, ``issue``, ``wave_num``, ``status``,
        or ``error`` if the item is not found.
    """
    mgr = DispatchStateManager(_dispatch_db_path())
    waves = mgr.get_all_waves(milestone)
    for wave in waves:
        for item in wave.items:
            if item.issue == issue:
                match status:
                    case "complete":
                        mgr.set_item_complete(
                            milestone=milestone, wave_num=wave.wave_num, issue=issue, result=result, cost=cost
                        )
                    case "failed":
                        mgr.set_item_failed(milestone=milestone, wave_num=wave.wave_num, issue=issue, error=error)
                    case "skipped":
                        mgr.set_item_failed(
                            milestone=milestone, wave_num=wave.wave_num, issue=issue, error=error or "skipped"
                        )
                    case _:
                        return {
                            "error": f"Invalid status '{status}': must be 'complete', 'failed', or 'skipped'",
                            "milestone": milestone,
                            "issue": issue,
                        }
                return {
                    "milestone": milestone,
                    "issue": issue,
                    "wave_num": wave.wave_num,
                    "status": status,
                    "messages": [f"Item #{issue} marked {status} in wave {wave.wave_num}"],
                    "warnings": [],
                    "errors": [],
                }
    return {
        "error": f"Item #{issue} not found in any wave for milestone {milestone}",
        "milestone": milestone,
        "issue": issue,
    }


def dispatch_wave_status(milestone: int, wave_num: int) -> dict[str, Any]:
    """Query the current status of a dispatch wave.

    Returns:
        Dict with wave summary fields, or ``error`` if wave not found.
    """
    mgr = DispatchStateManager(_dispatch_db_path())
    stale = mgr.check_stale_pids()
    warnings = [
        f"PID {stale_item.pid} for issue #{stale_item.issue} is dead — marked failed"
        for stale_item in stale
        if stale_item.milestone == milestone and stale_item.wave_num == wave_num
    ]
    wave = mgr.get_wave(milestone, wave_num)

    if wave is None:
        return {
            "error": f"Wave {wave_num} not found for milestone {milestone}",
            "milestone": milestone,
            "wave_num": wave_num,
        }

    items = wave.items
    status_counts = collections.Counter(i.status for i in items)
    elapsed: float | None = None
    if wave.started_at:
        with contextlib.suppress(ValueError):
            start = datetime.fromisoformat(wave.started_at)
            end = datetime.fromisoformat(wave.completed_at) if wave.completed_at else datetime.now(UTC)
            elapsed = (end - start).total_seconds()

    accumulated_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "estimated_cost_usd": 0.0,
        "events_with_usage": 0,
    }

    summary = DispatchWaveSummary(
        milestone=milestone,
        wave_num=wave_num,
        status=wave.status,
        total_items=len(items),
        pending=status_counts.get("pending", 0),
        in_progress=status_counts.get("in-progress", 0),
        complete=status_counts.get("complete", 0),
        failed=status_counts.get("failed", 0),
        skipped=status_counts.get("skipped", 0),
        started_at=wave.started_at,
        completed_at=wave.completed_at,
        elapsed_seconds=elapsed,
        items=items,
    )
    return {
        **summary.model_dump(),
        "messages": [],
        "warnings": warnings,
        "errors": [],
        "accumulated_usage": accumulated_usage,
    }


# ---------------------------------------------------------------------------
# Dispatch spawn (Task 2.32) — CLI-compatible async spawn orchestration
# ---------------------------------------------------------------------------

#: Path to spawn.py, resolved once at module level (same as server.py).
_SPAWN_SCRIPT: Path = Path(__file__).parent.parent / "skills" / "kage-bunshin" / "scripts" / "spawn.py"


@dataclasses.dataclass
class _WaveCounters:
    """Mutable counters shared across concurrent item coroutines in one wave."""

    completed: int = 0
    failed: int = 0
    skipped: int = 0
    total_done: int = 0


def _build_spawn_cmd(
    milestone: int,
    issue_num: int,
    item_title: str,
    model: str,
    phase: str,
    integration_branch: str,
    effort: str | None = None,
) -> list[str]:
    """Construct the spawn.py subprocess command for one dispatch item.

    Returns:
        List of strings suitable for ``asyncio.create_subprocess_exec``.
    """
    cmd: list[str] = ["uv", "run", str(_SPAWN_SCRIPT), "--model", model, "--name", f"dispatch-{milestone}-{issue_num}"]
    if effort is not None:
        cmd += ["--effort", effort]
    if phase == "work":
        cmd.append("--worktree")
    if integration_branch:
        cmd += ["--branch", integration_branch]
    cmd.append(f"Work on issue #{issue_num}: {item_title}")
    return cmd


async def _poll_until_done(
    mgr: DispatchStateManager, milestone: int, wave_num: int, issue_num: int, pid: int, result_file: str
) -> tuple[bool, float | None]:
    """Poll until a spawned item completes or its PID dies.

    Returns:
        ``(succeeded, cost)`` — ``succeeded`` is ``True`` when the result
        file was found; ``cost`` is the USD amount or ``None``.
    """
    rf_path = Path(result_file) if result_file else None
    while True:
        await asyncio.sleep(2)
        if rf_path is not None:
            result_ready = await asyncio.to_thread(lambda: rf_path.exists() and rf_path.stat().st_size > 0)
            if result_ready:
                item_cost = await _read_result_cost(rf_path, mgr, milestone, wave_num, issue_num)
                return True, item_cost
        pid_alive = _check_pid_alive(pid)
        if not pid_alive:
            await asyncio.to_thread(
                mgr.set_item_failed, milestone, wave_num, issue_num, f"Process died unexpectedly (PID {pid})"
            )
            return False, None


async def _read_result_cost(
    rf_path: Path, mgr: DispatchStateManager, milestone: int, wave_num: int, issue_num: int
) -> float | None:
    """Read the result file, record completion, and return cost.

    Returns:
        USD cost extracted from result JSON, or ``None``.
    """
    try:
        content = await asyncio.to_thread(lambda: rf_path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        content = ""
    item_cost: float | None = None
    try:
        rj = json.loads(content)
        item_cost = float(rj.get("cost", 0)) or None
    except (ValueError, KeyError, TypeError):
        pass
    await asyncio.to_thread(mgr.set_item_complete, milestone, wave_num, issue_num, content, item_cost)
    return item_cost


def _check_pid_alive(pid: int) -> bool:
    """Return True if *pid* is still running (or unknown)."""
    if pid <= 0:
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    return True


def _report_progress(total_done: int, total_items: int, counters: _WaveCounters, wave_num: int) -> None:
    """Print progress to stderr (CLI replacement for ctx.report_progress)."""
    print(
        f"Wave {wave_num}: {total_done}/{total_items} items — {counters.completed} done, {counters.failed} failed",
        file=sys.stderr,
    )


async def _run_spawn_item(
    mgr: DispatchStateManager,
    semaphore: asyncio.Semaphore,
    counters: _WaveCounters,
    warnings: list[str],
    milestone: int,
    wave_num: int,
    issue_num: int,
    item_title: str,
    total_items: int,
    model: str,
    phase: str,
    integration_branch: str,
    effort: str | None = None,
) -> None:
    """Spawn one dispatch item, monitor it, and update shared counters."""
    async with semaphore:
        cmd = _build_spawn_cmd(milestone, issue_num, item_title, model, phase, integration_branch, effort=effort)
        try:
            await _execute_spawn_item(mgr, cmd, counters, warnings, milestone, wave_num, issue_num)
        except (OSError, sqlite3.Error) as exc:
            await asyncio.to_thread(mgr.set_item_failed, milestone, wave_num, issue_num, f"Spawn error: {exc}")
            counters.failed += 1
            warnings.append(f"Item #{issue_num} failed: Spawn error: {exc}")
        counters.total_done += 1
        _report_progress(counters.total_done, total_items, counters, wave_num)


async def _execute_spawn_item(
    mgr: DispatchStateManager,
    cmd: list[str],
    counters: _WaveCounters,
    warnings: list[str],
    milestone: int,
    wave_num: int,
    issue_num: int,
) -> None:
    """Run the spawn subprocess and poll for completion.

    Raises:
        OSError: If the subprocess cannot be created.
        sqlite3.Error: If a state database operation fails.
    """
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout_bytes, _ = await proc.communicate()
    stdout_text = stdout_bytes.decode(errors="replace").strip()
    spawn_data = _parse_spawn_data(stdout_text)
    if spawn_data is None:
        await asyncio.to_thread(
            mgr.set_item_failed, milestone, wave_num, issue_num, f"spawn.py non-JSON output: {stdout_text}"
        )
        counters.failed += 1
        warnings.append(f"Item #{issue_num} failed: spawn.py non-JSON output")
        return
    pid, result_file, session_id = spawn_data
    if pid > 0:
        await asyncio.to_thread(mgr.set_item_in_progress, milestone, wave_num, issue_num, pid)
    if session_id:
        await asyncio.to_thread(mgr.set_item_session_id, milestone, wave_num, issue_num, session_id)
    succeeded, _ = await _poll_until_done(mgr, milestone, wave_num, issue_num, pid, result_file)
    if succeeded:
        counters.completed += 1
    else:
        counters.failed += 1
        warnings.append(f"Item #{issue_num} failed: process exited with no result")


def _parse_spawn_data(stdout_text: str) -> tuple[int, str, str] | None:
    """Parse spawn.py JSON output, returning (pid, result_file, session_id).

    Returns:
        Tuple of (pid, result_file, session_id) if valid JSON, else None.
    """
    try:
        spawn_data = json.loads(stdout_text)
        return (
            int(spawn_data.get("pid", -1)),
            str(spawn_data.get("result_file", "")),
            str(spawn_data.get("session_id", "")),
        )
    except (ValueError, KeyError, TypeError):
        return None


async def _run_dispatch_spawn(
    milestone: int, wave_num: int, max_concurrent: int, model: str, phase: str, effort: str | None
) -> dict[str, Any]:
    """Async core of dispatch_spawn — reads plan, spawns waves, returns summary.

    Returns:
        Dict with DispatchSpawnSummary fields, or error dict on failure.
    """
    try:
        plan = await asyncio.to_thread(_read_dispatch_plan, milestone)
    except ContentUnavailableError:
        return {"error": f"Dispatch plan not found for milestone {milestone}", "milestone": milestone}
    except ValueError as exc:
        return {"error": f"Invalid dispatch plan: {exc}", "milestone": milestone}

    mgr = DispatchStateManager(_dispatch_db_path())
    await asyncio.to_thread(mgr.check_stale_pids)

    start_time = time.monotonic()
    integration_branch = plan.milestone.integration_branch
    all_waves = [w for w in plan.waves if w.wave >= wave_num]
    total_items = sum(len(w.items) for w in all_waves)
    per_wave_summaries: list[DispatchWaveSummary] = []
    warnings: list[str] = []
    semaphore = asyncio.Semaphore(max_concurrent)
    overall = _WaveCounters()

    for wave in all_waves:
        with contextlib.suppress(sqlite3.IntegrityError):
            await asyncio.to_thread(
                mgr.create_wave,
                milestone,
                wave.wave,
                [
                    DispatchItemRecord(milestone=milestone, wave_num=wave.wave, issue=i.issue, title=i.title)
                    for i in wave.items
                ],
            )
        wave_counters = _WaveCounters(total_done=overall.total_done)
        await asyncio.gather(*[
            _run_spawn_item(
                mgr=mgr,
                semaphore=semaphore,
                counters=wave_counters,
                warnings=warnings,
                milestone=milestone,
                wave_num=wave.wave,
                issue_num=item.issue,
                item_title=item.title,
                total_items=total_items,
                model=model,
                phase=phase,
                integration_branch=integration_branch,
                effort=effort,
            )
            for item in wave.items
        ])
        overall.completed += wave_counters.completed
        overall.failed += wave_counters.failed
        overall.total_done = wave_counters.total_done
        per_wave_summaries.append(_build_wave_summary(mgr, milestone, wave, wave_counters))

    elapsed_seconds = time.monotonic() - start_time
    total_cost = await asyncio.to_thread(_sum_costs, mgr, milestone, wave_num)
    summary = DispatchSpawnSummary(
        milestone=milestone,
        waves_executed=len(all_waves),
        total_items=total_items,
        completed=overall.completed,
        failed=overall.failed,
        skipped=overall.skipped,
        elapsed_seconds=elapsed_seconds,
        per_wave=per_wave_summaries,
        total_cost=total_cost,
    )
    return {
        **summary.model_dump(),
        "messages": [f"Dispatch complete: {overall.completed}/{total_items} items succeeded"],
        "warnings": warnings,
        "errors": [],
    }


def _build_wave_summary(
    mgr: DispatchStateManager, milestone: int, wave: Wave, wave_counters: _WaveCounters
) -> DispatchWaveSummary:
    """Build a DispatchWaveSummary for one completed wave.

    Returns:
        DispatchWaveSummary with wave execution results.
    """
    fetched = mgr.get_wave(milestone, wave.wave)
    return DispatchWaveSummary(
        milestone=milestone,
        wave_num=wave.wave,
        status=fetched.status if fetched else "complete",
        total_items=len(wave.items),
        pending=0,
        in_progress=0,
        complete=wave_counters.completed,
        failed=wave_counters.failed,
        skipped=wave_counters.skipped,
    )


def _sum_costs(mgr: DispatchStateManager, milestone: int, wave_num: int) -> float | None:
    """Sum all item costs for waves >= wave_num.

    Returns:
        Total cost as float, or None if no items have cost data.
    """
    all_w = mgr.get_all_waves(milestone)
    costs = [i.cost for w in all_w if w.wave_num >= wave_num for i in w.items if i.cost is not None]
    return sum(costs) if costs else None


def dispatch_spawn(
    milestone: int,
    wave_num: int,
    max_concurrent: int = 3,
    model: str = "sonnet",
    phase: str = "work",
    effort: str | None = None,
) -> dict[str, Any]:
    """Spawn and monitor kage-bunshin sessions for a dispatch wave.

    Synchronous wrapper that runs the async dispatch logic via
    :func:`asyncio.run`.  Progress is printed to stderr instead of
    MCP Context.  Returns the same dict structure as the MCP version.

    Args:
        milestone: GitHub milestone number.
        wave_num: Starting wave number (1-based); all subsequent waves run too.
        max_concurrent: Maximum number of sessions running in parallel.
        model: Model identifier forwarded to each spawned session.
        phase: ``'work'`` adds ``--worktree``; ``'groom'`` omits it.
        effort: Effort level (``low``, ``medium``, ``high``, ``max``) or ``None``.

    Returns:
        Dict with :class:`DispatchSpawnSummary` fields, or ``error`` on failure.
    """
    return asyncio.run(_run_dispatch_spawn(milestone, wave_num, max_concurrent, model, phase, effort))


# ---------------------------------------------------------------------------
# Artifact operations (Task 2.30)
# ---------------------------------------------------------------------------

_artifact_registry = ArtifactRegistry()


def _manifest_reference(item_id: int | str) -> ContentRef:
    return ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace=str(item_id), name="manifest")


def _load_manifest(provider: ContentProvider, item_id: int | str) -> ArtifactManifest:
    return _load_manifest_record(provider, _manifest_reference(item_id), item_id)[0]


def artifact_register(
    item_id: int | str, artifact_type: str, artifact_id: str, content: str, status: str = "current", agent: str = ""
) -> dict[str, Any]:
    """Upsert an artifact entry in the manifest for a backlog item.

    Returns:
        Dict with ``registered``, ``artifact_count``, ``action``,
        ``content_stored``, or ``error`` on failure.
    """
    out = Output()
    try:
        if not content:
            return {"error": "Artifact content must not be empty.", **out.to_dict()}
        provider = _get_content_provider()
        artifact_type_enum = ArtifactType(artifact_type)
        status_enum = ArtifactStatus(status)
        entry = ArtifactEntry(
            artifact_type=artifact_type_enum,
            artifact_id=artifact_id,
            status=status_enum,
            created_at=datetime.now(UTC).isoformat(),
            agent=agent,
        )

        updated_manifest, existed = publish_artifact(provider, _manifest_reference(item_id), item_id, entry, content)
        action = "updated" if existed else "added"

        return {
            "registered": True,
            "artifact_count": len(updated_manifest.artifacts),
            "action": action,
            "content_stored": True,
            **out.to_dict(),
        }
    except (ValueError, KeyError) as exc:
        return {"error": f"Invalid parameter: {exc}", **out.to_dict()}
    except BacklogError as exc:
        return {"error": str(exc), **out.to_dict()}


def artifact_list(item_id: int | str, artifact_type: str | None = None) -> dict[str, Any]:
    """Return all artifacts registered for a backlog item.

    Returns:
        Dict with ``artifacts`` (list of dicts), ``count``, or ``error``.
    """
    out = Output()
    try:
        provider = _get_content_provider()
        type_filter: ArtifactType | None = ArtifactType(artifact_type) if artifact_type else None
        manifest = _load_manifest(provider, item_id)
        entries = (
            _artifact_registry.get_by_type(manifest, type_filter) if type_filter is not None else manifest.artifacts
        )
        artifacts = [e.model_dump(mode="json") for e in entries]
        return {"artifacts": artifacts, "count": len(artifacts), **out.to_dict()}
    except (ValueError, KeyError) as exc:
        return {"error": f"Invalid parameter: {exc}", **out.to_dict()}
    except BacklogError as exc:
        return {"error": str(exc), **out.to_dict()}


def artifact_get(item_id: int | str, artifact_type: str, artifact_id: str | None = None) -> dict[str, Any]:
    """Return metadata for artifacts of a specific type on a backlog item.

    Returns:
        Dict with ``artifacts`` (list of dicts), ``count``, or ``error``.
    """
    out = Output()
    try:
        provider = _get_content_provider()
        type_enum = ArtifactType(artifact_type)
        manifest = _load_manifest(provider, item_id)
        entries = _artifact_registry.get_by_type(manifest, type_enum)
        if artifact_id is not None:
            entries = [entry for entry in entries if entry.artifact_id == artifact_id]
        artifacts = [e.model_dump(mode="json") for e in entries]
        if not artifacts:
            return {"error": f"No artifacts of type '{artifact_type}' found for item #{item_id}", **out.to_dict()}
        return {"artifacts": artifacts, "count": len(artifacts), **out.to_dict()}
    except (ValueError, KeyError) as exc:
        return {"error": f"Invalid parameter: {exc}", **out.to_dict()}
    except BacklogError as exc:
        return {"error": str(exc), **out.to_dict()}


def artifact_read(item_id: int | str, artifact_type: str, artifact_id: str | None = None) -> dict[str, Any]:
    """Read the file content for an artifact registered on a backlog item.

    Returns:
        Dict with ``type``, ``path``, ``content``, ``status``, or ``error``.
    """
    out = Output()
    try:
        provider = _get_content_provider()
        type_enum = ArtifactType(artifact_type)
        manifest = _load_manifest(provider, item_id)
        entries = _artifact_registry.get_by_type(manifest, type_enum)
        if not entries:
            return {"error": f"No artifacts of type '{artifact_type}' found for item #{item_id}", **out.to_dict()}
        if artifact_id is not None:
            entries = [e for e in entries if e.artifact_id == artifact_id]
            if not entries:
                return {
                    "error": f"No artifact with id '{artifact_id}' of type '{artifact_type}' found for item #{item_id}",
                    **out.to_dict(),
                }
        entries_sorted = sorted(entries, key=lambda e: e.created_at or "", reverse=True)
        entry = entries_sorted[0]
        if len(entries_sorted) > 1:
            skipped = [e.artifact_id for e in entries_sorted[1:]]
            out.warnings.append(
                f"Multiple {artifact_type!r} artifacts found ({len(entries_sorted)}); "
                f"returning most recent ({entry.artifact_id!r}). Skipped: {skipped}"
            )

        content = provider.get_content(artifact_content_reference(item_id, entry)).content
        result = ArtifactContent(
            artifact_type=entry.artifact_type, path=entry.artifact_id, content=content, status=entry.status
        )
        return {**result.model_dump(mode="json"), **out.to_dict()}
    except (ValueError, KeyError) as exc:
        return {"error": f"Invalid parameter: {exc}", **out.to_dict()}
    except BacklogError as exc:
        return {"error": str(exc), **out.to_dict()}
