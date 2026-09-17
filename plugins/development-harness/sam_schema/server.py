"""FastMCP server for SAM task/plan operations.

Exposes the same operations as the Typer CLI as MCP tools for use by
Claude Code agents and other MCP clients.

A plan the work ledger holds — because a workflow ran ``plan import`` on it — is read and written
on the ledger by every plan-addressed ``sam_plan`` and ``sam_task`` action but ``sam_task``'s
``claim`` and ``sam_plan``'s ``list``, the same way the CLI's ``store_for`` routing does
(``sam_schema/sam_plan.py``). A plan the ledger does not hold keeps answering from the content
store, as before.

This module is the tool registration surface only: it builds the FastMCP app and gives each tool
its schema (parameter types, descriptions, and the docstring MCP clients read as the tool's own
description). The action-by-action logic lives one call away, in
:mod:`sam_schema.server_plan_ops`, :mod:`sam_schema.server_task_ops`, and
:mod:`sam_schema.server_active_task` -- each a thin adapter in its own right, over
``dh_core.ledger`` and ``dh_core.operations``, which own the actual business rules.

Tools:
    sam_plan        — Consolidated plan-level operations (read, create, list, status, ready, update)
    sam_task        — Consolidated task-level operations (read, claim, state, update)
    sam_active_task — Session-scoped active task context management (get, set, update, clear)
    sam_known_failure_types — The work-failure vocabulary an agent names when work could not proceed
"""

from __future__ import annotations

from typing import Annotated

from dh_core.known_failure_types import KnownFailureTypesPage, page as known_failure_types_page
from dh_core.ledger import PlanStatus as LedgerPlanStatus, TransitionResult
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from sam_schema.core.action_models import ActiveTaskActionConfig, PlanActionConfig, TaskActionConfig
from sam_schema.core.models import (
    ActiveTaskClearResult,
    ActiveTaskGetResult,
    ActiveTaskSetResult,
    ActiveTaskUpdateResult,
    AppendTaskResult,
    ClaimResult,
    CreatePlanResult,
    FinalizePlanResult,
    LedgerReadyResult,
    PaginatedResult,
    PlanStatus,
    ReadResult,
    ReadyTasksResult,
    StateResult,
    TaskAssignment,
    UpdatePlanResult,
    UpdateTaskResult,
)
from sam_schema.server_active_task import sam_active_task_impl
from sam_schema.server_plan_ops import sam_plan_impl
from sam_schema.server_task_ops import sam_task_impl

mcp: FastMCP = FastMCP(
    "sam",
    instructions=(
        "SAM (Structured Agent-Managed) task plan server. "
        "Use sam_task to read, claim, update state, or update fields of a specific task — "
        "set config.action to: read | claim | state | update. "
        "Use sam_plan to read a plan, create a plan, list all plans, get progress status, "
        "or list ready-to-dispatch tasks — "
        "set config.action to: read | create | list | status | ready | update | append_task | finalize. "
        "Once a plan has been imported into the work ledger, every action here but sam_task's claim "
        "and sam_plan's list reads and writes the ledger instead of the plan's original content record. "
        "Use sam_active_task to park and retrieve the task currently being worked on "
        "within an agent session — "
        "set config.action to: get | set | update | clear. "
        "Use sam_known_failure_types to read the shared vocabulary of work-failure types an agent names "
        "when work could not proceed — it returns the whole table by default."
    ),
)


def run_server() -> None:
    """Run the SAM MCP server."""
    mcp.run()


@mcp.tool(
    annotations=ToolAnnotations(
        title="SAM Plan Operations",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
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
        Response model whose shape depends on the action (see individual action docs).

    Raises:
        ToolError: When ``plan`` is None for an action that requires it.
    """
    return sam_plan_impl(config, plan_dir, plan)


@mcp.tool(
    annotations=ToolAnnotations(
        title="SAM Task Operations",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
def sam_task(
    plan: Annotated[str, Field(description="Plan address (e.g., 'P1' or slug)")],
    task: Annotated[str, Field(description="Task ID within the plan (e.g., 'T3')")],
    config: Annotated[
        TaskActionConfig, Field(description="Action config. Set 'action' to: read | claim | state | update")
    ],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
) -> TaskAssignment | ClaimResult | StateResult | UpdateTaskResult | TransitionResult:
    """Read, claim, update state, or update fields for a specific task.

    Once the ledger holds the task's plan, every action but ``claim`` reads or writes the ledger
    the way the CLI's ledger-backed commands do (``sam_plan.py``); ``claim`` stays on the content
    path, because it is retired everywhere except there until a later slice removes it too.

    Args:
        plan: Plan address component (numeric index or slug).
        task: Task ID component (e.g., ``T3``).
        config: Discriminated union selecting the action and its parameters.
        plan_dir: Path to the directory containing plan files.

    Returns:
        Action-specific Pydantic model. See individual action descriptions.
    """
    return sam_task_impl(plan, task, config, plan_dir)


@mcp.tool(
    annotations=ToolAnnotations(
        title="SAM Active Task Context",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
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
                "Caller-specific session identifier for scoping the active task "
                "context. Required — omitting it, or passing the empty string, "
                "is a hard error. Never pass the reserved '_default' sentinel."
            )
        ),
    ] = None,
) -> ActiveTaskGetResult | ActiveTaskSetResult | ActiveTaskUpdateResult | ActiveTaskClearResult:
    """Session-scoped active task context management.

    Parks a task address in session-scoped storage so subsequent operations
    can omit the plan/task parameters.

    Actions:

    - ``get``: Return the active task context, or ``{"active_task": null}`` if not set.
    - ``set``: Store a plan/task address as the active task for this session.
    - ``update``: Update fields on the active task without repeating its address.
    - ``clear``: Remove the active task context for this session.

    Args:
        config: Discriminated union selecting the action and its parameters.
        session_id: Caller-specific session identifier. Required.

    Returns:
        Action-specific Pydantic model. See individual action descriptions.

    Raises:
        ToolError: When ``session_id`` is missing, empty, or the reserved
            ``"_default"`` sentinel. Also when ``action="update"`` and no
            active task has been set, and when the configured context backend
            cannot be built -- an unrecognised ``CONTEXTBACKEND`` name, or
            ``"github"``, which is recognised but has no implementation yet.
    """
    return sam_active_task_impl(config, session_id)


@mcp.tool(
    annotations=ToolAnnotations(
        title="SAM Known Failure Types",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
def sam_known_failure_types(
    offset: Annotated[int, Field(description="Skip this many rows. 0 (the default) starts at the beginning.")] = 0,
    limit: Annotated[
        int | None,
        Field(
            description=(
                "Return at most this many rows. Omitted (the default) returns every remaining row; "
                "the table is never truncated on the caller's behalf."
            )
        ),
    ] = None,
) -> KnownFailureTypesPage:
    """Return the shared vocabulary of work-failure types, as data.

    A Worker names one of these codes when work could not proceed, so the reason is routable rather
    than reinvented as prose in each status report. The table is
    ``dh_core.known_failure_types.KNOWN_FAILURE_TYPES``; the ``sam known-failure-types`` CLI command
    returns the same rows from the same source.

    This vocabulary is deliberately separate from the ledger's own reason codes
    (``dh_core.ledger_spec.REASONS``, why a command refused) and from ``reclaim --reason`` (what the
    Orchestrator says when it sends a task back). If the ledger already refuses a condition with a
    ``REASONS`` code, name that code instead of a failure type.

    Args:
        offset: How many rows to skip before the window starts.
        limit: How many rows the window holds at most; omitted returns every remaining row.

    Returns:
        :class:`~dh_core.known_failure_types.KnownFailureTypesPage` — the window, plus ``total`` so
        a caller reading a window knows how much it did not read.

    Raises:
        ToolError: When ``offset`` or ``limit`` is negative.
    """
    try:
        return known_failure_types_page(offset=offset, limit=limit)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
