"""``sam_plan``'s eight action adapters and its dispatcher body.

Each adapter is a thin translation: once the ledger holds the plan, it reads or writes the ledger
the way the CLI's ledger-backed ``plan`` command does (``sam_schema/sam_plan.py``); otherwise it
resolves the content backend and delegates to ``dh_core.operations``. ``dh_core.ledger`` and
``dh_core.operations`` own the actual business rules -- this module only picks the call and, via
:func:`~sam_schema.server_ledger_routing.route`, which store answers it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import tiktoken
from dh_core import ledger, operations
from dh_core.ledger import LedgerConnection, PlanStatus as LedgerPlanStatus, TransitionResult
from fastmcp.exceptions import ToolError

from sam_schema import server_backend
from sam_schema.core.action_models import (
    AppendTaskConfig,
    CreatePlanConfig,
    FinalizePlanConfig,
    ListPlansConfig,
    PlanActionConfig,
    ReadyPlanConfig,
    UpdatePlanConfig,
)
from sam_schema.core.addressing import resolve_provider_plan_address
from sam_schema.core.models import (
    AppendTaskResult,
    CreatePlanError,
    CreatePlanResult,
    FinalizePlanResult,
    LedgerReadyResult,
    PaginatedResult,
    PaginationMeta,
    Plan,
    PlanStatus,
    PlanSummaryModel,
    ReadResult,
    ReadyTasksResult,
    UpdatePlanResult,
)
from sam_schema.server_ledger_routing import route

__all__ = ["sam_plan_impl"]

# Actions that require the ``plan`` parameter to be supplied.
_SAM_PLAN_REQUIRED_ACTIONS: frozenset[str] = frozenset({"read", "status", "ready", "update", "append_task", "finalize"})

# Token budget for auto-pagination: 4400 tokens (cl100k_base encoding).
_TOKEN_BUDGET: int = 4_400
_enc: tiktoken.Encoding = tiktoken.get_encoding("cl100k_base")


def _require_plan(plan: str | None, action: str) -> str:
    """Return *plan* as str, raising ToolError when it is None.

    Used to narrow ``plan: str | None`` to ``str`` for actions that require it, without relying on
    ``cast()`` or assert.
    """
    if plan is None:
        msg = (
            f"sam_plan: action='{action}' requires the 'plan' parameter "
            f"(e.g., plan='P1'). Actions that do not need 'plan': list, create."
        )
        raise ToolError(msg)
    return plan


def _sam_plan_read(plan: str, plan_dir: str) -> ReadResult:
    """Return Plan fields for the given plan address.

    Thin adapter: once the ledger holds the plan, reads its projection the way the CLI's
    ledger-backed ``plan read`` command does (``sam_plan.py``). Otherwise resolves the content
    backend and delegates to dh_core.operations. The operation handles plan retrieval, Plan model
    conversion, and source-degradation warning surfacing. Returns flat plan fields (feature, goal,
    context, …) rather than a nested ``ReadResult`` envelope. Warnings are added at the top level
    when present.
    """

    def _from_ledger(canonical: str, conn: LedgerConnection) -> ReadResult:
        return ReadResult(
            plan=Plan.model_validate(ledger.projection(conn, canonical)), source_format="ledger", source_path=Path()
        )

    def _from_content() -> ReadResult:
        backend = server_backend.get_backend(plan_dir)
        resolved, _ = resolve_provider_plan_address(plan, backend)
        return operations.read_plan(backend, resolved)

    return route(plan, on_ledger_call=_from_ledger, on_content=_from_content)


def _sam_plan_create(config: CreatePlanConfig, plan_dir: str) -> CreatePlanResult:
    """Create a new plan from a typed list of task definitions.

    Thin adapter: resolves the backend and delegates to dh_core.operations.
    On artifact write failure, the operations layer returns a
    :class:`~sam_schema.core.models.CreatePlanError`; this boundary function
    converts it to :class:`fastmcp.exceptions.ToolError` so the consolidated
    ``sam_plan`` tool exposes only the success model in its return schema.

    Returns:
        :class:`~sam_schema.core.models.CreatePlanResult` on success.

    Raises:
        ToolError: When plan creation's artifact write fails. The error
            message includes ``error``, ``reason``, and ``hint`` from the
            structured failure model.
    """
    backend = server_backend.get_backend(plan_dir)
    result = operations.create_plan(
        backend,
        slug=config.slug,
        goal=config.goal,
        tasks=config.tasks,
        context=config.context,
        issue=config.issue,
        owner_reference=config.owner_reference,
        acceptance_criteria_structured=config.acceptance_criteria_structured,
    )
    if isinstance(result, CreatePlanError):
        raise ToolError(f"{result.error}: {result.reason} (hint: {result.hint})")
    return result


def _paginate_results(
    all_items: list[PlanSummaryModel],
    *,
    offset: int,
    limit: int | None,
    messages: list[str],
    warnings: list[str],
    errors: list[str],
    tool_name: str,
) -> PaginatedResult:
    """Paginate ``all_items`` within the token budget and return the response envelope.

    Returns:
        :class:`~sam_schema.core.models.PaginatedResult` with ``items``, ``count``,
        ``pagination``, ``messages``, ``warnings``, ``errors``, and optionally
        ``next_call``.
    """
    total = len(all_items)
    page_items = all_items[offset:]

    if limit is not None:
        effective_limit = limit
    else:
        effective_limit = len(page_items)
        if page_items:
            # Pre-serialize to plain dicts once; token counting only needs the
            # wire representation, and model_dump(mode="json") is idempotent
            # across binary-search probes.  This preserves the O(N) total
            # serialization work of the original refactor.
            serialized_items = [item.model_dump(mode="json") for item in page_items]
            # Binary search for the largest k such that f(k) = len(_enc.encode(
            # json.dumps(serialized_items[:k]))) <= _TOKEN_BUDGET.  f is monotonically
            # non-decreasing, so binary search is valid and evaluates the *same*
            # function as the original loop, preserving exact pagination boundaries.
            # Total serialisation work: O(N) across all probes (N/2 + N/4 + … ≈ N)
            # versus O(N²) for the original prefix-from-scratch iteration.
            # lo never falls below 1, so a single item that exceeds the budget still
            # returns effective_limit=1 — identical to the original max(1, …) guard.
            lo, hi = 1, len(page_items)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if len(_enc.encode(json.dumps(serialized_items[:mid]))) <= _TOKEN_BUDGET:
                    lo = mid
                else:
                    hi = mid - 1
            effective_limit = lo

    page = page_items[:effective_limit]
    has_more = (offset + len(page)) < total
    result = PaginatedResult(
        items=page,
        count=len(page),
        pagination=PaginationMeta(offset=offset, limit=effective_limit, total=total, has_more=has_more),
        messages=messages,
        warnings=warnings,
        errors=errors,
    )
    if has_more:
        next_offset = offset + len(page)
        result.next_call = f"{tool_name}(offset={next_offset}, limit={effective_limit})"
    return result


def _sam_plan_list(config: ListPlansConfig, plan_dir: str) -> PaginatedResult:
    """List all plans with optional search and auto-pagination.

    Thin adapter: delegates business logic to ``dh_core.operations.list_plans``
    via a resolved backend, then applies MCP-specific token-budget
    pagination via ``_paginate_results``.

    Returns:
        Paginated dict with ``items``, ``count``, ``pagination``, ``messages``,
        ``warnings``, and ``errors`` keys. Each item contains ``feature``,
        ``goal``, ``description``, ``task_count``, ``issue``, and ``plan_ref``.
    """
    backend = server_backend.get_backend(plan_dir)
    # Operations layer returns typed PlanSummaryModel instances; pagination is
    # deferred to _paginate_results which applies offset/limit + token-budget
    # paging.
    all_items = operations.list_plans(backend, search=config.search, offset=0, limit=None)
    return _paginate_results(
        all_items, offset=config.offset, limit=config.limit, messages=[], warnings=[], errors=[], tool_name="sam_plan"
    )


def _sam_plan_status(plan: str, plan_dir: str) -> PlanStatus | LedgerPlanStatus:
    """Return plan-level progress summary including autonomy mode.

    Thin adapter: once the ledger holds the plan, reads its progress the way the CLI's
    ledger-backed ``plan status`` command does. Otherwise resolves the content backend via
    ``get_backend`` and delegates to ``dh_core.operations.get_plan_status``. The content-store
    result carries ``state`` so callers can detect drafting plans.
    """

    def _from_content() -> PlanStatus:
        backend = server_backend.get_backend(plan_dir)
        resolved, _ = resolve_provider_plan_address(plan, backend)
        return operations.get_plan_status(backend, resolved)

    return route(plan, on_ledger_call=lambda canonical, conn: ledger.status(conn, canonical), on_content=_from_content)


def _sam_plan_ready(plan: str, config: ReadyPlanConfig, plan_dir: str) -> ReadyTasksResult | LedgerReadyResult:
    """List tasks ready for dispatch.

    Thin adapter: once the ledger holds the plan, reads its dependency-resolved queue the way the
    CLI's ledger-backed ``plan ready`` command does, forwarding ``config.full`` to
    ``dh_core.ledger.ready`` the same way it reaches ``dh_core.operations.get_ready_tasks`` below.
    Otherwise resolves the content backend via ``get_backend`` and delegates to
    ``dh_core.operations.get_ready_tasks``, which handles the drafting check and ready-task
    retrieval and returns a :class:`~sam_schema.core.models.ReadyTasksResult` envelope.

    Returns:
        A ``ReadyTasksResult`` model with ``feature``, ``ready_tasks``, ``count``, ``issue``, and
        ``state`` fields for a plan the ledger does not hold. When the content-store plan is
        drafting, ``state`` is ``"drafting"`` and ``ready_tasks`` is empty. A plan the ledger holds
        returns a :class:`~sam_schema.core.models.LedgerReadyResult` instead.
    """

    def _from_ledger(canonical: str, conn: LedgerConnection) -> LedgerReadyResult:
        rows = ledger.ready(conn, canonical, full=config.full)
        return LedgerReadyResult(items=rows, count=len(rows))

    def _from_content() -> ReadyTasksResult:
        backend = server_backend.get_backend(plan_dir)
        resolved, _ = resolve_provider_plan_address(plan, backend)
        return operations.get_ready_tasks(backend, resolved, full=config.full)

    return route(plan, on_ledger_call=_from_ledger, on_content=_from_content)


def _sam_plan_update(plan: str, config: UpdatePlanConfig, plan_dir: str) -> UpdatePlanResult | TransitionResult:
    """Update plan-level context and/or fields.

    Thin adapter: once the ledger holds the plan, writes it the way the CLI's ledger-backed
    ``plan update`` command does -- ``context`` and ``owner_reference`` join ``set_fields_json``
    as ``--set`` values (``owner_reference`` under the ledger's own field name, ``issue``).
    Otherwise resolves the content backend via ``get_backend`` and delegates to
    ``dh_core.operations.update_plan_fields``, which handles raw field validation through the Plan
    model, backend delegation, and response assembly.

    Returns:
        :class:`~sam_schema.core.models.UpdatePlanResult` with ``updated`` (bool) and ``address``
        (plan identifier) fields for a plan the ledger does not hold. A plan the ledger holds
        returns a :class:`~dh_core.ledger.TransitionResult` instead.
    """

    def _from_ledger(canonical: str, conn: LedgerConnection) -> TransitionResult:
        values: dict[str, Any] = dict(config.set_fields_json or {})
        if config.context is not None:
            values["context"] = config.context
        if config.owner_reference is not None:
            values["issue"] = config.owner_reference
        return ledger.update(
            conn,
            canonical,
            config.task_id,
            section=config.append_section_name,
            section_content=config.section_content,
            values=values,
        )

    def _from_content() -> UpdatePlanResult:
        backend = server_backend.get_backend(plan_dir)
        resolved, _ = resolve_provider_plan_address(plan, backend)
        return operations.update_plan_fields(
            backend,
            resolved,
            context=config.context,
            set_fields=config.set_fields_json,
            owner_reference=config.owner_reference,
            task_id=config.task_id,
            append_section_name=config.append_section_name,
            section_content=config.section_content,
        )

    return route(plan, on_ledger_call=_from_ledger, on_content=_from_content)


def _sam_plan_append_task(plan: str, config: AppendTaskConfig, plan_dir: str) -> AppendTaskResult | TransitionResult:
    """Append a single task to an existing plan.

    Thin adapter: once the ledger holds the plan, appends the task the way the CLI's ledger-backed
    ``plan append-task`` command does, carrying every ``TaskDefinition`` field beyond ``id`` and
    ``title`` through as the ledger's ``definition``. Otherwise resolves the content backend via
    ``get_backend`` and delegates to ``dh_core.operations.append_task``, which handles
    ``config.task`` conversion and ``backend.append_task`` delegation.

    See AppendTaskConfig for the single-writer contract and #1770 for the ADR.

    Args:
        plan: Plan address (e.g., ``P1`` or slug).
        config: AppendTaskConfig carrying the validated TaskDefinition.
        plan_dir: Plan directory path passed through to ``get_backend``.

    Returns:
        :class:`~sam_schema.core.models.AppendTaskResult` — shape:
        ``appended=True``, ``task_id=...`` — for a plan the ledger does not hold. A plan the ledger
        holds returns a :class:`~dh_core.ledger.TransitionResult` instead.

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
        TaskValidationError: When the task definition fails model validation.
        ToolError: When the ledger holds the plan and refuses the append, e.g. an archived plan.
    """

    def _from_ledger(canonical: str, conn: LedgerConnection) -> TransitionResult:
        definition = config.task.model_dump(mode="json", by_alias=False, exclude={"id", "title"}, exclude_none=True)
        return ledger.append_task(
            conn,
            canonical,
            task_id=config.task.id,
            task_title=config.task.title,
            conflict_group=config.conflict_group,
            definition=definition,
        )

    def _from_content() -> AppendTaskResult:
        backend = server_backend.get_backend(plan_dir)
        resolved, _ = resolve_provider_plan_address(plan, backend)
        return operations.append_task(backend, resolved, config.task)

    return route(plan, on_ledger_call=_from_ledger, on_content=_from_content)


def _sam_plan_finalize(plan: str, plan_dir: str) -> FinalizePlanResult | TransitionResult:
    """Transition a plan from drafting state to ready state.

    Thin adapter: once the ledger holds the plan, finalizes it the way the CLI's ledger-backed
    ``plan finalize`` command does. Otherwise resolves the content backend via ``get_backend`` and
    delegates to ``dh_core.operations.finalize_plan``, which handles the drafting → ready state
    transition via ``backend.finalize_plan``.

    See FinalizePlanConfig and #1770 for the ADR.

    The backend resolves the issue association internally from the plan index;
    no caller-provided issue is needed at finalize time.

    Returns:
        :class:`~sam_schema.core.models.FinalizePlanResult` — shape: ``finalized=True``,
        ``state="ready"`` — for a plan the ledger does not hold. A plan the ledger holds returns a
        :class:`~dh_core.ledger.TransitionResult` instead.
    """

    def _from_content() -> FinalizePlanResult:
        backend = server_backend.get_backend(plan_dir)
        resolved, _ = resolve_provider_plan_address(plan, backend)
        return operations.finalize_plan(backend, resolved)

    return route(
        plan, on_ledger_call=lambda canonical, conn: ledger.finalize(conn, canonical), on_content=_from_content
    )


def sam_plan_impl(
    config: PlanActionConfig, plan_dir: str, plan: str | None
) -> (
    CreatePlanResult
    | PlanStatus
    | LedgerPlanStatus
    | ReadyTasksResult
    | LedgerReadyResult
    | ReadResult
    | UpdatePlanResult
    | AppendTaskResult
    | FinalizePlanResult
    | PaginatedResult
    | TransitionResult
):
    """Consolidated plan-level operations for SAM -- the body ``sam_schema.server.sam_plan`` runs.

    Delegates to the appropriate plan operation based on ``config.action``.

    Actions requiring the ``plan`` parameter:

    - ``read``: Return Plan fields for the given plan address.
    - ``status``: Return plan-level progress summary (task counts, completion %).
    - ``ready``: List tasks ready for dispatch (not-started, all deps resolved).
    - ``update``: Set plan-level context and/or patch plan fields.
    - ``append_task``: Append a single task to an existing plan (incremental build; see #1770).
    - ``finalize``: Transition a plan from drafting state to ready state (see #1770).

    Actions that do not use ``plan``:

    - ``create``: Create a new plan from a typed list of task definitions.
    - ``list``: List all plans with optional search and auto-pagination.

    Args:
        config: Discriminated union config. The ``action`` field selects the operation.
        plan_dir: Path to the directory containing plan files.
        plan: Plan address component. Required for read, status, ready, update, append_task, finalize actions.

    Returns:
        Response model whose shape depends on the action (see individual action docs).

    Raises:
        ToolError: When ``plan`` is None for an action that requires it.
    """
    if config.action in _SAM_PLAN_REQUIRED_ACTIONS and plan is None:
        msg = (
            f"sam_plan: action='{config.action}' requires the 'plan' parameter "
            f"(e.g., plan='P1'). Actions that do not need 'plan': list, create."
        )
        raise ToolError(msg)

    match config.action:
        case "read":
            return _sam_plan_read(_require_plan(plan, "read"), plan_dir)
        case "create":
            if not isinstance(config, CreatePlanConfig):
                raise TypeError(f"Expected CreatePlanConfig, got {type(config).__name__}")
            return _sam_plan_create(config, plan_dir)
        case "list":
            if not isinstance(config, ListPlansConfig):
                raise TypeError(f"Expected ListPlansConfig, got {type(config).__name__}")
            return _sam_plan_list(config, plan_dir)
        case "status":
            return _sam_plan_status(_require_plan(plan, "status"), plan_dir)
        case "ready":
            if not isinstance(config, ReadyPlanConfig):
                raise TypeError(f"Expected ReadyPlanConfig, got {type(config).__name__}")
            return _sam_plan_ready(_require_plan(plan, "ready"), config, plan_dir)
        case "update":
            if not isinstance(config, UpdatePlanConfig):
                raise TypeError(f"Expected UpdatePlanConfig, got {type(config).__name__}")
            return _sam_plan_update(_require_plan(plan, "update"), config, plan_dir)
        case "append_task":
            if not isinstance(config, AppendTaskConfig):
                raise TypeError(f"Expected AppendTaskConfig, got {type(config).__name__}")
            return _sam_plan_append_task(_require_plan(plan, "append_task"), config, plan_dir)
        case "finalize":
            if not isinstance(config, FinalizePlanConfig):
                raise TypeError(f"Expected FinalizePlanConfig, got {type(config).__name__}")
            return _sam_plan_finalize(_require_plan(plan, "finalize"), plan_dir)
        case _:  # pragma: no cover
            msg = f"sam_plan: unhandled action '{config.action}'"
            raise ValueError(msg)
