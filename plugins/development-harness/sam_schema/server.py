"""FastMCP server for SAM task/plan operations.

Exposes the same operations as the Typer CLI as MCP tools for use by
Claude Code agents and other MCP clients.

Tools:
    sam_plan        — Consolidated plan-level operations (read, create, list, status, ready, update)
    sam_task        — Consolidated task-level operations (read, claim, state, update)
    sam_active_task — Session-scoped active task context management (get, set, update, clear)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import tiktoken
from dh_core import operations
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from sam_schema.core.action_models import (
    ActiveTaskActionConfig,
    AppendTaskConfig,
    CreatePlanConfig,
    FinalizePlanConfig,
    ListPlansConfig,
    PlanActionConfig,
    ReadyPlanConfig,
    SetActiveTaskConfig,
    StateTaskConfig,
    TaskActionConfig,
    UpdateActiveTaskConfig,
    UpdatePlanConfig,
    UpdateTaskConfig,
)
from sam_schema.core.context_config import ContextConfig, create_context_backend, get_context_config, set_context_config
from sam_schema.core.models import ClaimResult, Plan, PlanState, PlanStatus, ReadyTasksResult, Task, TaskAssignment
from sam_schema.core.task_config import TaskConfig, create_task_backend, get_backend, get_task_config, set_task_config

if TYPE_CHECKING:
    from sam_schema.core.task_backend import TaskBackend

_log = logging.getLogger(__name__)

# Sentinel session key used when session_id is omitted from sam_active_task calls.
# Single-agent scenarios do not require explicit session isolation.
_DEFAULT_SESSION_ID = "_default"

# Returned by _sam_plan_status and _sam_plan_ready when the plan is in drafting state.
# Defined once here to ensure both handlers return an identical shape.
_DRAFTING_MARKER_RESPONSE: dict[str, object] = {"drafting": True, "state": PlanState.DRAFTING}

# Stem parsing thresholds used in _build_task_assignment.
_STEM_MIN_PARTS_FOR_NUMBER: int = 2
_STEM_MIN_PARTS_FOR_SLUG: int = 3

# Initialize the default backend at module import time.
# Tests may call set_task_config() before importing this module to inject a custom backend.
try:
    get_task_config()
except RuntimeError:
    set_task_config(TaskConfig(backend=create_task_backend()))

# Initialize the context backend at module import time.
# Tests may call set_context_config() before importing this module to inject a custom backend.
try:
    get_context_config()
except RuntimeError:
    set_context_config(ContextConfig(backend=create_context_backend()))


def _get_backend(plan_dir_str: str) -> TaskBackend:
    """Return the appropriate TaskBackend for the given plan_dir.

    Delegates to the shared :func:`sam_schema.core.task_config.get_backend` so that
    both the MCP server and the CLI use the same backend-resolution logic.

    The MCP server always passes ``wrap_gist=True`` so that explicit plan
    directories are also wrapped in ``GistTaskLayer`` for write-through to
    GitHub Gist (matching pre-refactor MCP behaviour).

    Args:
        plan_dir_str: The ``plan_dir`` parameter from the MCP tool call.

    Returns:
        :class:`~sam_schema.core.task_backend.TaskBackend` instance to use for
        this tool call.
    """
    return get_backend(plan_dir_str, wrap_gist=True)


# Token budget for auto-pagination: 4400 tokens (cl100k_base encoding).
_TOKEN_BUDGET: int = 4_400
_enc: tiktoken.Encoding = tiktoken.get_encoding("cl100k_base")

mcp: FastMCP = FastMCP(
    "sam",
    instructions=(
        "SAM (Structured Agent-Managed) task plan server. "
        "Use sam_task to read, claim, update state, or update fields of a specific task — "
        "set config.action to: read | claim | state | update. "
        "Use sam_plan to read a plan, create a plan, list all plans, get progress status, "
        "or list ready-to-dispatch tasks — "
        "set config.action to: read | create | list | status | ready | update | append_task | finalize. "
        "Use sam_active_task to park and retrieve the task currently being worked on "
        "within an agent session — "
        "set config.action to: get | set | update | clear."
    ),
)


def run_server() -> None:
    """Entry point for ``sam-mcp`` console script."""
    mcp.run()


def _paginate_results(
    all_items: list[dict[str, Any]],
    *,
    offset: int,
    limit: int | None,
    messages: list[str],
    warnings: list[str],
    errors: list[str],
    tool_name: str,
) -> dict[str, Any]:
    """Paginate ``all_items`` within the token budget and return the response dict.

    Returns:
        Dict with ``items``, ``count``, ``pagination``, ``messages``, ``warnings``, ``errors``,
        and optionally ``next_call``.
    """
    total = len(all_items)
    page_items = all_items[offset:]

    if limit is not None:
        effective_limit = limit
    else:
        effective_limit = len(page_items)
        if page_items:
            # Binary search for the largest k such that f(k) = len(_enc.encode(
            # json.dumps(page_items[:k]))) <= _TOKEN_BUDGET.  f is monotonically
            # non-decreasing, so binary search is valid and evaluates the *same*
            # function as the original loop, preserving exact pagination boundaries.
            # Total serialisation work: O(N) across all probes (N/2 + N/4 + … ≈ N)
            # versus O(N²) for the original prefix-from-scratch iteration.
            # lo never falls below 1, so a single item that exceeds the budget still
            # returns effective_limit=1 — identical to the original max(1, …) guard.
            lo, hi = 1, len(page_items)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if len(_enc.encode(json.dumps(page_items[:mid]))) <= _TOKEN_BUDGET:
                    lo = mid
                else:
                    hi = mid - 1
            effective_limit = lo

    page = page_items[:effective_limit]
    has_more = (offset + len(page)) < total
    result: dict[str, Any] = {
        "items": page,
        "count": len(page),
        "pagination": {"offset": offset, "limit": effective_limit, "total": total, "has_more": has_more},
        "messages": messages,
        "warnings": warnings,
        "errors": errors,
    }
    if has_more:
        next_offset = offset + len(page)
        result["next_call"] = f"{tool_name}(offset={next_offset}, limit={effective_limit})"
    return result


# Actions that require the ``plan`` parameter to be supplied.
_SAM_PLAN_REQUIRED_ACTIONS: frozenset[str] = frozenset({"read", "status", "ready", "update", "append_task", "finalize"})


def _require_plan(plan: str | None, action: str) -> str:
    """Return *plan* as str, raising ToolError when it is None.

    Used by ``sam_plan`` to narrow ``plan: str | None`` to ``str`` for
    actions that require it, without relying on ``cast()`` or assert.
    """
    if plan is None:
        msg = (
            f"sam_plan: action='{action}' requires the 'plan' parameter "
            f"(e.g., plan='P1'). Actions that do not need 'plan': list, create."
        )
        raise ToolError(msg)
    return plan


def _sam_plan_read(plan: str, plan_dir: str) -> Plan:
    """Return Plan fields for the given plan address.

    Thin adapter: resolves the backend and delegates to dh_core.operations.
    The operation handles plan retrieval, Plan model conversion, and
    source-degradation warning surfacing. Returns ``result.plan`` (the
    :class:`~sam_schema.core.models.Plan` model) so MCP clients receive
    flat plan fields (feature, goal, context, …) rather than a nested
    ``ReadResult`` envelope.
    """
    backend = _get_backend(plan_dir)
    return operations.read_plan(backend, plan).plan


def _sam_plan_create(config: CreatePlanConfig, plan_dir: str) -> dict:
    """Create a new plan from a typed list of task definitions.

    Thin adapter: resolves the backend and delegates to dh_core.operations.

    Returns:
        Dict from dh_core.operations.create_plan().
    """
    backend = _get_backend(plan_dir)
    return operations.create_plan(
        backend, slug=config.slug, goal=config.goal, tasks=config.tasks, context=config.context, issue=config.issue
    )


def _sam_plan_list(config: ListPlansConfig, plan_dir: str) -> dict[str, Any]:
    """List all plans with optional search and auto-pagination.

    Thin adapter: delegates business logic to ``dh_core.operations.list_plans``
    via a resolved backend, then applies MCP-specific token-budget
    pagination via ``_paginate_results``.

    Returns:
        Paginated dict with ``items``, ``count``, ``pagination``, ``messages``,
        ``warnings``, and ``errors`` keys. Each item contains ``feature``,
        ``goal``, ``description``, ``task_count``, ``issue``, and ``plan_ref``.
    """
    backend = _get_backend(plan_dir)
    # Operations layer returns a list of PlanSummary dicts; pagination is
    # deferred to _paginate_results which applies offset/limit + token-budget
    # paging.
    summaries = operations.list_plans(backend, search=config.search, offset=0, limit=None)
    all_items: list[dict[str, Any]] = [{**s} for s in summaries]  # Spread TypedDict into plain dict at this boundary
    return _paginate_results(
        all_items, offset=config.offset, limit=config.limit, messages=[], warnings=[], errors=[], tool_name="sam_plan"
    )


def _sam_plan_status(plan: str, plan_dir: str) -> PlanStatus | dict[str, object]:
    """Return plan-level progress summary including autonomy mode.

    Thin adapter that resolves the backend via ``_get_backend`` and
    delegates to ``dh_core.operations.get_plan_status``. When the plan
    is in drafting state, returns a drafting marker dict.
    """
    backend = _get_backend(plan_dir)
    try:
        return operations.get_plan_status(backend, plan)
    except ValueError:
        return _DRAFTING_MARKER_RESPONSE


def _sam_plan_ready(plan: str, config: ReadyPlanConfig, plan_dir: str) -> dict[str, object] | ReadyTasksResult:
    """List tasks ready for dispatch.

    Thin adapter: resolves the backend via ``_get_backend`` and delegates
    to ``dh_core.operations.get_ready_tasks``. The operation handles the
    drafting check and ready-task retrieval, and returns a
    :class:`~sam_schema.core.models.ReadyTasksResult` envelope.

    Returns:
        A ``ReadyTasksResult`` model with ``feature``, ``ready_tasks``,
        ``count``, and ``issue`` fields. When the plan is drafting,
        returns a drafting marker dict.
    """
    backend = _get_backend(plan_dir)
    try:
        return operations.get_ready_tasks(backend, plan)
    except ValueError:
        return _DRAFTING_MARKER_RESPONSE


def _sam_plan_update(plan: str, config: UpdatePlanConfig, plan_dir: str) -> dict:
    """Update plan-level context and/or fields.

    Thin adapter: resolves the backend via ``_get_backend`` and delegates to
    ``dh_core.operations.update_plan_fields``. The operation handles raw field
    validation through the Plan model, backend delegation, and response assembly.

    Returns:
        Dict with ``updated`` (bool) and ``address`` (plan identifier) keys.
    """
    backend = _get_backend(plan_dir)
    return operations.update_plan_fields(
        backend,
        plan,
        context=config.context,
        set_fields=config.set_fields_json,
        task_id=config.task_id,
        append_section_name=config.append_section_name,
        section_content=config.section_content,
    )


def _sam_plan_append_task(plan: str, config: AppendTaskConfig, plan_dir: str) -> dict:
    """Append a single task to an existing plan.

    Thin adapter: resolves the backend via ``_get_backend`` and delegates
    to ``dh_core.operations.append_task``. The operation handles
    ``config.task`` conversion and ``backend.append_task`` delegation.

    See AppendTaskConfig for the single-writer contract and #1770 for the ADR.

    Args:
        plan: Plan address (e.g., ``P1`` or slug).
        config: AppendTaskConfig carrying the validated TaskDefinition.
        plan_dir: Plan directory path passed through to ``_get_backend``.

    Returns:
        Result dict from ``dh_core.operations.append_task`` — shape:
        ``{"appended": True, "task_id": ...}``.

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
        TaskValidationError: When the task definition fails model validation.
    """
    backend = _get_backend(plan_dir)
    return operations.append_task(backend, plan, config.task)


def _sam_plan_finalize(plan: str, plan_dir: str) -> dict:
    """Transition a plan from drafting state to ready state.

    Thin adapter: resolves the backend via ``_get_backend`` and delegates
    to ``dh_core.operations.finalize_plan``. The operation handles the
    drafting → ready state transition via ``backend.finalize_plan``.

    See FinalizePlanConfig and #1770 for the ADR.

    The backend resolves the issue association internally from the plan index;
    no caller-provided issue is needed at finalize time.

    Returns:
        Result dict from ``dh_core.operations.finalize_plan`` — shape:
        ``{"finalized": True, "state": "ready"}``.
    """
    backend = _get_backend(plan_dir)
    return operations.finalize_plan(backend, plan)


def _require_plan(plan: str | None, action: str) -> str:
    """Narrow ``plan: str | None`` to ``str`` for actions that require it.

    The ``_SAM_PLAN_REQUIRED_ACTIONS`` guard in ``sam_plan`` raises ``ToolError``
    before the match statement when ``plan`` is ``None`` for a required action,
    so this branch is unreachable in normal execution.  It is retained to satisfy
    the type checker without using ``cast`` or ``assert``.

    Args:
        plan: The optional plan address from the tool call.
        action: Action name, used only in the error message.

    Returns:
        The validated non-None plan address string.

    Raises:
        ToolError: If ``plan`` is ``None`` (unreachable after the outer guard).
    """
    if plan is None:  # pragma: no cover
        msg = f"sam_plan: action='{action}' requires the 'plan' parameter (e.g., plan='P1')."
        raise ToolError(msg)
    return plan


@mcp.tool(
    annotations=ToolAnnotations(
        title="SAM Plan Operations", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False
    )
)
def sam_plan(
    config: Annotated[
        PlanActionConfig,
        Field(
            description="Action config. Set 'action' to: read | create | list | status | ready | update | append_task | finalize"
        ),
    ],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
    plan: Annotated[
        str | None,
        Field(
            description=(
                "Plan address (e.g., 'P1' or slug). "
                "Required for: read, status, ready, update, append_task, finalize. "
                "Not used for: list, create."
            )
        ),
    ] = None,
) -> dict[str, object] | list[Task] | PlanStatus | Plan | TaskAssignment | ReadyTasksResult:
    """Consolidated plan-level operations for SAM.

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
        Response dict whose shape depends on the action (see individual action docs).

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


@mcp.tool(
    annotations=ToolAnnotations(
        title="SAM Task Operations", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False
    )
)
def sam_task(
    plan: Annotated[str, Field(description="Plan address (e.g., 'P1' or slug)")],
    task: Annotated[str, Field(description="Task ID within the plan (e.g., 'T3')")],
    config: Annotated[
        TaskActionConfig, Field(description="Action config. Set 'action' to: read | claim | state | update")
    ],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
) -> TaskAssignment | Task | dict[str, Any] | ClaimResult:
    """Read, claim, update state, or update fields for a specific task.

    # TRADE-OFF: readonly annotation loss
    # sam_read (replaced by action="read") was annotated readonly=True in FastMCP,
    # meaning it did not require a confirmation prompt from Claude Code.
    # sam_task cannot be readonly because it includes write actions (claim, state,
    # update). Consequence: Claude Code will show a confirmation prompt for read
    # operations that previously did not require one. This is a known, accepted
    # trade-off — a clean 3-tool interface outweighs the read UX regression.
    # If read-without-prompt becomes required, extract a separate readonly
    # sam_task_read tool in a future iteration.

    Args:
        plan: Plan address component (numeric index or slug).
        task: Task ID component (e.g., ``T3``).
        config: Discriminated union selecting the action and its parameters.
        plan_dir: Path to the directory containing plan files.

    Returns:
        Action-specific dict. See individual action descriptions.
    """
    backend = _get_backend(plan_dir)

    match config.action:
        case "read":
            return operations.read_task(backend, plan, task)

        case "claim":
            return operations.claim_task(backend, plan, task)

        case "state":
            if not isinstance(config, StateTaskConfig):
                raise TypeError(f"Expected StateTaskConfig, got {type(config).__name__}")
            return operations.update_task_status(backend, plan, task, config.status)

        case "update":
            if not isinstance(config, UpdateTaskConfig):
                raise TypeError(f"Expected UpdateTaskConfig, got {type(config).__name__}")
            return operations.update_task_fields(
                backend,
                plan,
                task,
                set_fields_json=config.set_fields_json,
                append_section=config.append_section,
                section_content=config.section_content,
            )

        case _:  # pragma: no cover
            msg = f"sam_task: unhandled action '{config.action}'"
            raise ValueError(msg)


@mcp.tool(
    annotations=ToolAnnotations(
        title="SAM Active Task Context",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def sam_active_task(
    config: Annotated[
        ActiveTaskActionConfig, Field(description="Action config. Set 'action' to: get | set | update | clear")
    ],
    session_id: Annotated[
        str | None,
        Field(
            description=(
                "Session identifier for scoping the active task context. "
                "When None, uses the '_default' sentinel for single-agent scenarios."
            )
        ),
    ] = None,
) -> dict:
    """Session-scoped active task context management.

    Parks a task address in session-scoped storage so subsequent operations
    can omit the plan/task parameters. Useful in single-agent workflows where
    repeatedly passing the same address is noise.

    Actions:

    - ``get``: Return the active task context, or ``{"active_task": null}`` if not set.
    - ``set``: Store a plan/task address as the active task for this session.
    - ``update``: Update fields on the active task without repeating its address.
    - ``clear``: Remove the active task context for this session.

    Args:
        config: Discriminated union selecting the action and its parameters.
        session_id: Claude Code session identifier. When ``None``, uses the
            ``"_default"`` sentinel (suitable for single-agent scenarios that
            do not need explicit session isolation).

    Returns:
        Action-specific dict. See individual action descriptions.

    Raises:
        ToolError: When ``action="update"`` and no active task has been set.
    """
    resolved_session = session_id if session_id is not None else _DEFAULT_SESSION_ID
    ctx_backend = get_context_config().backend

    match config.action:
        case "get":
            return operations.get_active_task(ctx_backend, resolved_session)

        case "set":
            if not isinstance(config, SetActiveTaskConfig):
                raise TypeError(f"Expected SetActiveTaskConfig, got {type(config).__name__}")
            return operations.set_active_task(
                ctx_backend, resolved_session, config.plan, config.task, config.plan_dir, config.parent_issue_number
            )

        case "update":
            if not isinstance(config, UpdateActiveTaskConfig):
                raise TypeError(f"Expected UpdateActiveTaskConfig, got {type(config).__name__}")
            active = ctx_backend.get_active_task(resolved_session)
            if active is None:
                msg = (
                    "sam_active_task: no active task set for this session. "
                    "Call sam_active_task(action='set', plan=..., task=...) first."
                )
                raise ToolError(msg)
            if active.plan_dir is None:
                task_backend = _get_backend(str(Path(active.task_file_path).parent))
            else:
                task_backend = _get_backend(active.plan_dir)
            return operations.update_active_task(
                ctx_backend,
                resolved_session,
                task_backend,
                set_fields_json=config.set_fields_json,
                append_section=config.append_section,
                section_content=config.section_content,
            )

        case "clear":
            return operations.clear_active_task(ctx_backend, resolved_session)

        case _:  # pragma: no cover
            msg = f"sam_active_task: unhandled action '{config.action}'"
            raise ValueError(msg)
