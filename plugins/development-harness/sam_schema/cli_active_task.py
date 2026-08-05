"""Active-task CLI commands — session-scoped task context (get/set/update/clear).

Mirrors the ``sam_active_task`` MCP tool in ``sam_schema/server.py`` so both
transports expose the same logical operations against the same session-scoped
context store (T-P5-ACTIVE-TASK). Both frontends delegate to the shared
``dh_core.operations`` functions; neither owns a parallel implementation.

Commands are declared on the module-level ``app`` Typer and attached to the
root CLI by ``cli.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from dh_core import operations

from sam_schema.cli_output import err, output_json
from sam_schema.core.addressing import AddressingError, parse_address
from sam_schema.core.context_backend import ContextBackend
from sam_schema.core.context_config import ContextConfig, create_context_backend, get_context_config, set_context_config
from sam_schema.core.task_config import get_backend

__all__ = ["DEFAULT_SESSION_ID", "app"]

#: Sentinel session key used when --session-id is omitted. Mirrors the MCP
#: server convention in sam_schema/server.py so both transports resolve the
#: same session-scoped context.
DEFAULT_SESSION_ID = "_default"

app = typer.Typer(help="Session-scoped active task context.", no_args_is_help=True, rich_markup_mode=None)

_SESSION_OPTION = typer.Option("--session-id", help="Session identifier (default: '_default')")


def _context_backend() -> ContextBackend:
    """Return the active ContextBackend, initialising it on first use.

    ``get_context_config()`` deliberately raises when no config has been
    registered — the MCP server sets one at import time (``server.py``), but
    the CLI is a fresh process on every invocation and has no such hook.
    Mirror the server's lazy-init pattern so both transports resolve the
    backend through the same chain: ``CONTEXTBACKEND`` env var →
    ``context.backend`` in ``.dh/config.yaml`` → default ``local``.

    The CLI is therefore backend-agnostic, not local-only. Note that
    ``memory`` is per-process and so is not meaningful across separate CLI
    invocations; ``local`` and ``beads`` are durable.

    Returns:
        The active ContextBackend implementation.
    """
    try:
        return get_context_config().backend
    except RuntimeError:
        try:
            backend = create_context_backend()
        except (ValueError, NotImplementedError) as exc:
            # Surface misconfiguration as a clean CLI error rather than a
            # raw traceback from the factory.
            err(str(exc))
        set_context_config(ContextConfig(backend=backend))
        return get_context_config().backend


@app.command(name="get")
def active_task_get(session_id: Annotated[str | None, _SESSION_OPTION] = None) -> None:
    """Show the active task context for a session."""
    result = operations.get_active_task(_context_backend(), session_id or DEFAULT_SESSION_ID)
    # Preserve explicit `active_task: null` when no context is set.
    output_json(result, exclude_none=False)


@app.command(name="set")
def active_task_set(
    address: Annotated[str, typer.Option("--address", help="Task address: P{plan}/T{task}")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir", help="Plan directory")] = None,
    parent_issue_number: Annotated[
        str | None, typer.Option("--parent-issue", help="Parent issue number or beads nanoid")
    ] = None,
    session_id: Annotated[str | None, _SESSION_OPTION] = None,
) -> None:
    """Park a task address as the active task for a session."""
    try:
        plan_ref, task_id = parse_address(address)
    except AddressingError as exc:
        err(str(exc))
    if not task_id:
        err(f"Address '{address}' must include a task ID (e.g. P1/T3).")
    # Typer hands every option through as str, but ActiveTaskContext accepts
    # int (GitHub issue number) or a beads-ID str. Coerce digit-only input to
    # int so `--parent-issue 42` behaves the same as the MCP tool, which is
    # typed `str | int`.
    resolved_parent: str | int | None = parent_issue_number
    if parent_issue_number is not None and parent_issue_number.isdigit():
        resolved_parent = int(parent_issue_number)
    result = operations.set_active_task(
        _context_backend(),
        session_id or DEFAULT_SESSION_ID,
        plan_ref,
        task_id,
        str(plan_dir) if plan_dir is not None else "plan",
        resolved_parent,
    )
    output_json(result)


@app.command(name="update")
def active_task_update(
    set_fields: Annotated[
        str | None, typer.Option("--set-fields-json", help="JSON object of task fields to set")
    ] = None,
    append_section: Annotated[str | None, typer.Option("--append-section", help="Section name to append to")] = None,
    section_content: Annotated[str | None, typer.Option("--section-content", help="Content for the section")] = None,
    session_id: Annotated[str | None, _SESSION_OPTION] = None,
) -> None:
    """Update fields or append a section on the active task."""
    resolved_session = session_id or DEFAULT_SESSION_ID
    ctx_backend = _context_backend()
    active = ctx_backend.get_active_task(resolved_session)
    if active is None:
        err("No active task set for this session. Run 'active-task set P1/T3' first.")
    parsed_fields: dict[str, object] | None = None
    if set_fields is not None:
        try:
            parsed_fields = json.loads(set_fields)
        except json.JSONDecodeError as exc:
            err(f"Invalid --set-fields-json: {exc}")
        if not isinstance(parsed_fields, dict):
            err("--set-fields-json must be a JSON object.")
    task_dir = active.plan_dir if active.plan_dir is not None else str(Path(active.task_file_path).parent)
    result = operations.update_active_task(
        ctx_backend,
        resolved_session,
        get_backend(task_dir),
        set_fields_json=parsed_fields,
        append_section=append_section,
        section_content=section_content,
    )
    output_json(result)


@app.command(name="clear")
def active_task_clear(session_id: Annotated[str | None, _SESSION_OPTION] = None) -> None:
    """Clear the active task context for a session."""
    result = operations.clear_active_task(_context_backend(), session_id or DEFAULT_SESSION_ID)
    output_json(result)
