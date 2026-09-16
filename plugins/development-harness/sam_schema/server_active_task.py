"""``sam_active_task``'s dispatcher body: session-scoped active task context management.

Parks a task address in session-scoped storage so subsequent operations can omit the plan/task
parameters. ``dh_core.operations`` owns the actual business rules -- this module only picks the
call.
"""

from __future__ import annotations

from dh_core import operations
from fastmcp.exceptions import ToolError

from sam_schema import server_backend
from sam_schema.core.action_models import ActiveTaskActionConfig, SetActiveTaskConfig, UpdateActiveTaskConfig
from sam_schema.core.models import (
    ActiveTaskClearResult,
    ActiveTaskGetResult,
    ActiveTaskSetResult,
    ActiveTaskUpdateResult,
)

__all__ = ["sam_active_task_impl"]


def sam_active_task_impl(
    config: ActiveTaskActionConfig, session_id: str | None
) -> ActiveTaskGetResult | ActiveTaskSetResult | ActiveTaskUpdateResult | ActiveTaskClearResult:
    """Session-scoped active task context management -- the body ``sam_schema.server.sam_active_task`` runs.

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
            name is not recognised.
    """
    try:
        resolved_session = operations.require_session_id(session_id)
    except operations.MissingSessionIdError as exc:
        raise ToolError(str(exc)) from exc
    ctx_backend = server_backend.get_context_backend()

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
            task_backend = server_backend.get_backend(active.plan_dir or "")
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
