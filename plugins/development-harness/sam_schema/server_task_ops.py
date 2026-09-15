"""``sam_task``'s dispatcher body and its ledger-backed action handler.

Once the ledger holds the task's plan, every action but ``claim`` reads or writes the ledger the
way the CLI's ledger-backed commands do (``sam_schema/sam_plan.py``); ``claim`` stays on the
content path, because it is retired everywhere except there until a later slice removes it too.
``dh_core.ledger`` and ``dh_core.operations`` own the actual business rules -- this module only
picks the call and, via :func:`~sam_schema.server_ledger_routing.route`, which store answers it.
"""

from __future__ import annotations

from dh_core import ledger, operations
from dh_core.ledger import LedgerConnection, TransitionResult
from fastmcp.exceptions import ToolError

from sam_schema import server_backend
from sam_schema.core.action_models import ReadTaskConfig, StateTaskConfig, TaskActionConfig, UpdateTaskConfig
from sam_schema.core.addressing import resolve_provider_plan_address
from sam_schema.core.models import ClaimResult, StateResult, TaskAssignment, UpdateTaskResult
from sam_schema.server_ledger_routing import route

__all__ = ["sam_task_impl"]


def _sam_task_ledger(plan: str, task: str, config: TaskActionConfig, conn: LedgerConnection) -> TransitionResult:
    """Read, move, or update a task the ledger holds, the way the CLI's ledger-backed commands do.

    Called only for ``read``, ``state`` and ``update`` -- ``sam_task_impl`` routes ``claim`` to the
    content backend unconditionally, because ``claim`` is retired everywhere except the content
    path until a later slice removes it there too. Runs inside the connection
    :func:`~sam_schema.server_ledger_routing.route` already opened, so a ledger error it raises
    reaches that call's own translation into ``ToolError`` rather than this function's.

    Args:
        plan: The canonical plan id (see ``sam_schema.core.addressing.canonical_plan_id``).
        task: The task id.
        config: The action's discriminated-union config, already narrowed to one of ``read``,
            ``state`` or ``update`` by the caller's ``match``.
        conn: The open ledger connection ``route`` provides.

    Returns:
        The ledger transition's result.

    Raises:
        ToolError: When ``config.action`` is not one this function handles. The ledger's own
            refusals (e.g. ``reason-required`` for ``state`` with no reason) surface through the
            caller's :func:`~sam_schema.server_ledger_routing.route`, not from here.
    """
    match config.action:
        case "read":
            if not isinstance(config, ReadTaskConfig):
                raise TypeError(f"Expected ReadTaskConfig, got {type(config).__name__}")
            return ledger.read(conn, plan, task, attempt=config.attempt)

        case "state":
            if not isinstance(config, StateTaskConfig):
                raise TypeError(f"Expected StateTaskConfig, got {type(config).__name__}")
            return ledger.state(conn, plan, task, new_status=config.status, reason=config.reason, force=config.force)

        case "update":
            if not isinstance(config, UpdateTaskConfig):
                raise TypeError(f"Expected UpdateTaskConfig, got {type(config).__name__}")
            return ledger.update(
                conn,
                plan,
                task,
                attempt=config.attempt,
                section=config.append_section,
                section_content=config.section_content,
                values=config.set_fields_json,
            )

        case _:  # pragma: no cover
            msg = f"sam_task: action='{config.action}' is not available once the ledger holds the plan"
            raise ToolError(msg)


def sam_task_impl(
    plan: str, task: str, config: TaskActionConfig, plan_dir: str
) -> TaskAssignment | ClaimResult | StateResult | UpdateTaskResult | TransitionResult:
    """Read, claim, update state, or update fields for a specific task -- the body ``sam_schema.server.sam_task`` runs.

    Once the ledger holds the task's plan, every action but ``claim`` reads or writes the ledger
    the way the CLI's ledger-backed commands do (``sam_plan.py``); ``claim`` stays on the content
    path, because it is retired everywhere except there until a later slice removes it too.

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
        Action-specific Pydantic model. See individual action descriptions.
    """

    def _from_content() -> TaskAssignment | ClaimResult | StateResult | UpdateTaskResult:
        backend = server_backend.get_backend(plan_dir)
        resolved, _ = resolve_provider_plan_address(plan, backend)

        match config.action:
            case "read":
                return operations.read_task(backend, resolved, task)

            case "claim":
                return operations.claim_task(backend, resolved, task)

            case "state":
                if not isinstance(config, StateTaskConfig):
                    raise TypeError(f"Expected StateTaskConfig, got {type(config).__name__}")
                return operations.update_task_status(backend, resolved, task, config.status)

            case "update":
                if not isinstance(config, UpdateTaskConfig):
                    raise TypeError(f"Expected UpdateTaskConfig, got {type(config).__name__}")
                return operations.update_task_fields(
                    backend,
                    resolved,
                    task,
                    set_fields_json=config.set_fields_json,
                    append_section=config.append_section,
                    section_content=config.section_content,
                )

            case _:  # pragma: no cover
                msg = f"sam_task: unhandled action '{config.action}'"
                raise ValueError(msg)

    if config.action == "claim":
        return _from_content()

    return route(
        plan,
        on_ledger_call=lambda canonical, conn: _sam_task_ledger(canonical, task, config, conn),
        on_content=_from_content,
    )
