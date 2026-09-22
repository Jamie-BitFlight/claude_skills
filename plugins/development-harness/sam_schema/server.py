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
        "SAM task plans. Once a plan is imported into the work ledger, every action but "
        "sam_task's claim and sam_plan's list reads and writes the ledger instead of the "
        "plan's original record, so the two can report different content for the same plan. "
        "sam_active_task is scoped to one session: what it parks is invisible to every "
        "other session."
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
    - ``append_task``: Append a single task to an existing plan, one task per call.
    - ``finalize``: Move a plan from drafting to ready.

    Actions that do not use ``plan``:

    - ``create``: Create a new plan from a typed list of task definitions.
    - ``list``: List all plans with optional search and auto-pagination.
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

    Once the ledger holds the task's plan, every action but ``claim`` reads and writes the
    ledger. ``claim`` still reads the plan's original record.
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

    ``action="update"`` fails when no task has been set for this session. Set one first.

    The call also fails when the configured context backend cannot be built. Correct
    whichever of these names it: the ``CONTEXTBACKEND`` environment variable,
    ``context.backend`` or ``backend.name`` in ``.dh/config.yaml``, or a
    ``.beads/dh-backend`` marker file, which selects ``beads``.
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

    Name one of these codes when work could not proceed, so the reason is routable rather than
    reinvented as prose in each status report. The ``sam known-failure-types`` CLI command
    returns the same rows.

    These codes are separate from the reason a ledger command gives for refusing a call, and
    from what ``reclaim --reason`` records when a task is sent back. When a ledger command
    already refuses the condition with its own code, name that code instead.

    ``total`` reports the size of the whole table, so a caller reading one window knows how
    much it did not read.
    """
    try:
        return known_failure_types_page(offset=offset, limit=limit)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
