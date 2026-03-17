"""FastMCP server for SAM task/plan operations.

Exposes the same operations as the Typer CLI as MCP tools for use by
Claude Code agents and other MCP clients.

Tools:
    sam_read    — Read a task by address (returns TaskAssignment when task provided)
    sam_state   — Update a task's status
    sam_ready   — List ready tasks for a plan
    sam_status  — Get plan-level progress summary
    sam_create  — Create a new plan from YAML task definitions
    sam_update  — Update plan or task fields, or append a section
    sam_claim   — Claim a task (transition to in-progress)
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field
from ruamel.yaml import YAML

from sam_schema.core.addressing import resolve_plan_address
from sam_schema.core.models import TaskStatus
from sam_schema.core.query import (
    claim_task,
    create_plan,
    get_plan_status,
    get_ready_tasks,
    get_task_assignment,
    load_plan,
    update_plan_fields,
    update_status,
)

mcp: FastMCP = FastMCP(
    "sam",
    instructions=(
        "SAM (Structured Agent-Managed) task plan server. "
        "Use sam_read to inspect a plan or task. "
        "Use sam_claim to take ownership of a task before starting work. "
        "Use sam_state to update task status. "
        "Use sam_ready to list tasks ready for dispatch. "
        "Use sam_status for a plan-level progress summary. "
        "Use sam_create to create a new plan from YAML task definitions. "
        "Use sam_update to set fields or append a markdown section to a task body."
    ),
)


def run_server() -> None:
    """Entry point for ``sam-mcp`` console script."""
    mcp.run()


@mcp.tool
def sam_read(
    plan: Annotated[str, Field(description="Plan address (e.g., 'P1' or slug)")],
    task: Annotated[str | None, Field(description="Task ID (e.g., 'T3'). Omit to read plan-level fields only.")] = None,
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
) -> dict:
    """Read a plan or task and return its fields as a dict.

    When ``task`` is provided, returns a ``TaskAssignment`` dict that includes
    both plan-level context (``plan_goal``, ``plan_context``,
    ``plan_acceptance_criteria``) and the nested ``task`` object.  This gives
    agents everything they need in one call.

    When ``task`` is omitted, returns the ``Plan`` fields only.

    Args:
        plan: Plan address component (numeric index or slug).
        task: Task ID component (e.g., ``T3``). Optional.
        plan_dir: Path to the directory containing plan files.

    Returns:
        ``TaskAssignment`` fields as a JSON-serializable dict when ``task`` is
        provided, or ``Plan`` fields when ``task`` is omitted.  Returns a dict
        with an ``error`` key on failure.
    """
    try:
        plan_path = resolve_plan_address(plan, Path(plan_dir))
        if task is not None:
            result = get_task_assignment(plan_path, task)
            return result.model_dump(mode="json", by_alias=True, exclude_none=True)
        # Plan-only read: return Plan metadata without TaskAssignment wrapper.
        read_result = load_plan(plan_path)
        return read_result.plan.model_dump(mode="json", by_alias=True, exclude_none=True)
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


@mcp.tool
def sam_state(
    plan: Annotated[str, Field(description="Plan address")],
    task: Annotated[str, Field(description="Task ID")],
    status: Annotated[str, Field(description="New status value")],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
) -> dict:
    """Update a task's status.

    Args:
        plan: Plan address component.
        task: Task ID component.
        status: New status string (e.g., ``complete``, ``in-progress``).
        plan_dir: Path to the directory containing plan files.

    Returns:
        Updated task fields as a JSON-serializable dict, or a dict with an
        ``error`` key on failure.
    """
    try:
        new_status = TaskStatus(status)
        plan_path = resolve_plan_address(plan, Path(plan_dir))
        result = update_status(plan_path, task, new_status)
        return result.model_dump(mode="json")
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


@mcp.tool
def sam_ready(
    plan: Annotated[str, Field(description="Plan address")],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
) -> dict:
    """List tasks ready for dispatch.

    Args:
        plan: Plan address component.
        plan_dir: Path to the directory containing plan files.

    Returns:
        Dict with ``ready_tasks`` list of task field dicts and ``count``, or
        a dict with an ``error`` key on failure.
    """
    try:
        plan_path = resolve_plan_address(plan, Path(plan_dir))
        tasks = get_ready_tasks(plan_path)
        return {"ready_tasks": [t.model_dump(mode="json") for t in tasks], "count": len(tasks)}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


@mcp.tool
def sam_status(
    plan: Annotated[str, Field(description="Plan address")],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
) -> dict:
    """Get plan-level progress summary.

    Args:
        plan: Plan address component.
        plan_dir: Path to the directory containing plan files.

    Returns:
        ``PlanStatus`` fields as a JSON-serializable dict including
        ``total_tasks``, ``by_status``, ``ready_tasks``, ``blocked_tasks``,
        ``completion_pct``, and ``has_cycles``, or a dict with an ``error``
        key on failure.
    """
    try:
        plan_path = resolve_plan_address(plan, Path(plan_dir))
        result = get_plan_status(plan_path)
        return result.model_dump(mode="json")
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


@mcp.tool
def sam_create(
    slug: Annotated[str, Field(description="Short identifier for the plan (e.g., 'auth-system')")],
    goal: Annotated[str, Field(description="Human-readable goal statement for the plan")],
    tasks_yaml: Annotated[str, Field(description="YAML string with a 'tasks' key containing a list of task dicts")],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
    context: Annotated[str | None, Field(description="Optional plan-level context (markdown prose)")] = None,
    issue: Annotated[int | None, Field(description="Optional GitHub issue number to associate with the plan")] = None,
) -> dict:
    """Create a new plan from YAML task definitions.

    Parses ``tasks_yaml`` (a YAML string containing a ``tasks:`` list), validates
    each task dict against the ``Task`` Pydantic model, assigns the next available
    plan number, and writes the plan file to ``{plan_dir}/P{NNN}-{slug}.yaml``.

    Mirrors ``sam create`` CLI behaviour. All write operations are atomic.

    Args:
        slug: Short identifier for the plan.
        goal: Human-readable goal statement.
        tasks_yaml: YAML string whose top-level key is ``tasks`` — a list of task
                    dicts (required fields per ``Task`` model: ``task``, ``title``,
                    ``status``, ``agent``, ``dependencies``, ``priority``,
                    ``complexity``).
        plan_dir: Directory in which to create the plan file.
        context: Optional plan-level context string.
        issue: Optional GitHub issue number.

    Returns:
        ``{"path": str, "plan_number": int, "task_count": int}`` on success, or
        ``{"error": str}`` on failure.
    """
    try:
        yaml: Any = YAML()
        parsed: dict[str, Any] = yaml.load(tasks_yaml)
        if not isinstance(parsed, dict) or "tasks" not in parsed:
            return {"error": "tasks_yaml must be a YAML string with a top-level 'tasks' key"}
        task_list: list[dict[str, Any]] = parsed["tasks"]
        plan = create_plan(slug=slug, goal=goal, tasks=task_list, plan_dir=Path(plan_dir), context=context, issue=issue)
        # Derive plan_number from source_path stem (e.g. "P003-auth-system" -> 3).
        plan_number: int | None = None
        if plan.source_path is not None:
            stem = plan.source_path.stem
            if stem.startswith("P") and "-" in stem:
                with contextlib.suppress(ValueError):
                    plan_number = int(stem.split("-", 1)[0][1:])
        return {"path": str(plan.source_path), "plan_number": plan_number, "task_count": len(plan.tasks)}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


@mcp.tool
def sam_update(
    address: Annotated[str, Field(description="Plan address (e.g., 'P1') or task address (e.g., 'P1/T2')")],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
    set_fields_json: Annotated[
        str | None, Field(description="JSON object of field=value pairs to set on the plan or task")
    ] = None,
    context: Annotated[str | None, Field(description="Set the plan-level context field")] = None,
    append_section: Annotated[
        str | None, Field(description="Name of the markdown section to append to the task body")
    ] = None,
    section_content: Annotated[str | None, Field(description="Body content for the appended section")] = None,
) -> dict:
    """Update plan or task fields, or append a markdown section to a task body.

    Supports three non-exclusive operations that can be combined in one call:

    1. ``set_fields_json`` — a JSON object of ``{field: value}`` pairs to update.
    2. ``context`` — shorthand for setting the plan-level ``context`` field.
    3. ``append_section`` + ``section_content`` — append a named markdown section
       to a task's body (task address required for this operation).

    Mirrors ``sam update`` CLI behaviour.

    Args:
        address: Plan or task address. Task address required for
                 ``append_section`` and task-level ``set_fields_json``.
        plan_dir: Directory containing plan files.
        set_fields_json: JSON string ``{"field": "value", ...}`` to set.
        context: If provided, sets the plan-level ``context`` field.
        append_section: Section heading to append to the task body.
        section_content: Body text for the appended section.

    Returns:
        ``{"updated": true, "address": str}`` on success, or ``{"error": str}``
        on failure.
    """
    try:
        # Split address into plan and optional task components.
        if "/" in address:
            plan_part, task_id = address.split("/", 1)
        else:
            plan_part = address
            task_id = None

        plan_path = resolve_plan_address(plan_part, Path(plan_dir))

        set_fields: dict[str, str] | None = None
        if set_fields_json is not None:
            raw_fields: Any = json.loads(set_fields_json)
            if not isinstance(raw_fields, dict):
                return {"error": "set_fields_json must be a JSON object"}
            set_fields = {str(k): str(v) for k, v in raw_fields.items()}

        update_plan_fields(
            plan_path,
            task_id=task_id,
            set_fields=set_fields,
            context=context,
            append_section_name=append_section,
            section_content=section_content,
        )
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
    else:
        return {"updated": True, "address": address}


@mcp.tool
def sam_claim(
    plan: Annotated[str, Field(description="Plan address (e.g., 'P1' or slug)")],
    task: Annotated[str, Field(description="Task ID to claim (e.g., 'T3')")],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
) -> dict:
    """Claim a task by transitioning it from ``not-started`` to ``in-progress``.

    Guards against double-claiming: returns an error dict (not an exception) if
    the task is already in-progress or in a terminal state. Mirrors ``sam claim``
    CLI behaviour.

    Args:
        plan: Plan address component (numeric index or slug).
        task: Task ID to claim (e.g., ``T3``).
        plan_dir: Path to the directory containing plan files.

    Returns:
        ``{"claimed": true, "task_id": str, "started": str}`` on success, or
        ``{"claimed": false, "error": str}`` if the task cannot be claimed.
    """
    try:
        plan_path = resolve_plan_address(plan, Path(plan_dir))
        updated_task = claim_task(plan_path, task)
    except (ValueError, KeyError) as exc:
        return {"claimed": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
    else:
        return {"claimed": True, "task_id": updated_task.id, "started": updated_task.started}
