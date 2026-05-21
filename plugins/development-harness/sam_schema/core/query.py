"""Query layer for SAM task/plan files.

High-level functions for loading, querying, and updating plans. All operations
route through the format detection and reader pipeline, then delegate writes to
the YAML writer. This is the primary API consumed by the CLI and MCP server.
"""

from __future__ import annotations

import io
import re
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sam_schema.core.dependencies import DependencyGraph
from sam_schema.core.models import Plan, PlanStatus, ReadResult, Task, TaskAssignment, TaskStatus
from sam_schema.readers.detect import read_plan
from sam_schema.readers.normalize import normalize_plan
from sam_schema.writers.yaml_writer import (
    _atomic_write,
    _make_yaml,
    _wrap_multiline,
    append_section,
    create_plan_file,
    update_fields,
)

if TYPE_CHECKING:
    from pathlib import Path

_LEGACY_TASKS_RE = re.compile(r"^tasks-(\d+)-")


def _new_plan_id() -> str:
    """Generate a collision-resistant plan ID using UUID4.

    Returns:
        A plan ID string of the form ``P`` + first 8 hex characters of a UUID4,
        e.g. ``"Pa1b2c3d4"``. Collision probability is negligible for any
        realistic number of plans per directory.
    """
    return "P" + uuid.uuid4().hex[:8]


def create_plan(
    slug: str,
    goal: str,
    tasks: list[dict[str, Any]],
    plan_dir: Path,
    context: str | None = None,
    issue: int | None = None,
) -> Plan:
    """Create a new plan, assign a UUID-derived plan ID, validate tasks, and write to disk.

    The output file is named ``{plan_dir}/{plan_id}-{slug}.yaml`` where
    ``plan_id`` is ``P`` + first 8 hex characters of a UUID4 (e.g. ``Pa1b2c3d4``).
    When ``issue`` is provided, it is stored in the ``issue`` field of the Plan model.
    ``plan_ref`` is computed in server responses only and is not a Plan model field;
    it does not influence the plan's own ID.

    Each dict in ``tasks`` is validated against the ``Task`` Pydantic model
    before the plan is written; invalid task dicts raise ``ValueError`` with the
    Pydantic validation error details.

    Args:
        slug: Short identifier for the plan (e.g., ``"auth-system"``).
        goal: Human-readable goal statement for the plan.
        tasks: List of task dicts to include. Each dict must satisfy the ``Task``
               model (required: ``task``/``id``, ``title``, ``status``, ``agent``,
               ``dependencies``, ``priority``, ``complexity``).
        plan_dir: Directory in which to create the plan file.
        context: Optional plan-level context string (markdown prose).
        issue: Optional GitHub issue number stored in the plan metadata.
               Does not affect the plan ID.

    Returns:
        The created ``Plan`` model (with ``source_path`` set to the written path).

    Raises:
        ValueError: If any task dict is invalid per the ``Task`` model.
        OSError: If the plan file cannot be written, or if a UUID collision
            occurs after 3 attempts (negligible in practice).
    """
    MAX_ID_ATTEMPTS = 3
    for _attempt in range(MAX_ID_ATTEMPTS):
        plan_id_str = _new_plan_id()
        file_name = f"{plan_id_str}-{slug}.yaml"
        output_path = plan_dir / file_name
        if not output_path.exists():
            break
    else:
        msg = f"UUID collision: failed to generate a unique plan ID after {MAX_ID_ATTEMPTS} attempts"
        raise OSError(msg)

    validated_tasks: list[Task] = []
    for i, raw_task in enumerate(tasks):
        # Accept "task" key as the task id (YAML frontmatter convention)
        normalized = {**raw_task, "id": raw_task["task"]} if "task" in raw_task and "id" not in raw_task else raw_task
        try:
            validated_tasks.append(Task.model_validate(normalized))
        except Exception as exc:
            msg = f"Task at index {i} failed validation: {exc}"
            raise ValueError(msg) from exc

    plan = Plan(
        plan_id=plan_id_str,
        feature=slug,
        goal=goal,
        context=context,
        issue=str(issue) if issue is not None else None,
        tasks=validated_tasks,
        source_path=output_path,
    )
    create_plan_file(output_path, plan)
    return plan


def update_plan_fields(
    plan_path: Path,
    task_id: str | None = None,
    *,
    set_fields: dict[str, str | int | list[str]] | None = None,
    context: str | None = None,
    append_section_name: str | None = None,
    section_content: str | None = None,
) -> None:
    """Update plan or task fields via a unified write operation.

    Supports three non-exclusive operations that can be combined in one call:

    1. ``set_fields`` — update arbitrary plan-level or task-level fields.
    2. ``context`` — shorthand for setting the plan context field.
    3. ``append_section_name`` + ``section_content`` — append a named markdown
       section to a task's body.

    Args:
        plan_path: Path to the plan file or directory.
        task_id: Task ID to target for task-level operations. ``None`` means
                 plan-level operations only.
        set_fields: Mapping of ``field=value`` strings to update. For
                    task-level updates ``task_id`` must be provided.
        context: If provided, sets the plan-level ``context`` field. Requires
                 that ``plan_path`` points to a writable YAML file.
        append_section_name: Section heading to append. Requires
                             ``section_content`` and ``task_id``.
        section_content: Body text for the appended section.

    Raises:
        ValueError: If ``append_section_name`` is given without ``task_id`` or
                    ``section_content``.
        FileNotFoundError: If ``plan_path`` does not exist.
        KeyError: If ``task_id`` is not found in the plan.
    """
    if append_section_name is not None:
        if task_id is None:
            msg = "append_section_name requires task_id"
            raise ValueError(msg)
        if not section_content:
            msg = "append_section_name requires section_content"
            raise ValueError(msg)

    file_path = _resolve_writable_path(plan_path, task_id or "")

    if context is not None or (set_fields and task_id is None):
        # Merge context and plan-level set_fields into a single load-modify-write
        # cycle to avoid the double-write data loss bug: two sequential writes to
        # the same file would cause the first write's changes to be overwritten by
        # the second write's stale read.
        y = _make_yaml()
        raw = file_path.read_text(encoding="utf-8")
        data: dict[str, Any] = y.load(raw)
        if context is not None:
            data["context"] = _wrap_multiline(context)
        if set_fields and task_id is None:
            for key, value in set_fields.items():
                data[key] = _wrap_multiline(value) if isinstance(value, str) else value
        buf = io.StringIO()
        y.dump(data, buf)
        _atomic_write(file_path, buf.getvalue())

    if set_fields and task_id is not None:
        # Task-level field updates
        update_fields(file_path, task_id, set_fields)

    if append_section_name is not None and task_id is not None and section_content:
        append_section(file_path, task_id, append_section_name, section_content)


def load_plan(plan_path: Path) -> ReadResult:
    """Load a plan from any supported format.

    Delegates to ``readers.detect.read_plan`` for format detection and reading,
    then normalizes to Pydantic models via ``readers.normalize.normalize_plan``.

    Args:
        plan_path: Path to a task/plan file or directory.

    Returns:
        A ``ReadResult`` containing the parsed ``Plan`` and any ``SchemaGap``
        records for non-canonical fields.

    Raises:
        FileNotFoundError: If ``plan_path`` does not exist.
        FormatDetectionError: If the file format cannot be identified.
    """
    plan_meta, task_dicts, fmt = read_plan(plan_path)
    return normalize_plan(plan_meta, task_dicts, fmt, plan_path)


def get_task(plan_path: Path, task_id: str) -> Task:
    """Get a single task by ID from a plan file.

    Args:
        plan_path: Path to the plan file or directory.
        task_id: Task ID to retrieve (e.g., ``"T1"``).

    Returns:
        The matching ``Task`` model.

    Raises:
        FileNotFoundError: If ``plan_path`` does not exist.
        KeyError: If no task with ``task_id`` is found in the plan.
    """
    result = load_plan(plan_path)
    for task in result.plan.tasks:
        if task.id == task_id:
            return task
    msg = f"Task '{task_id}' not found in plan '{plan_path}'"
    raise KeyError(msg)


def get_task_assignment(plan_path: Path, task_id: str) -> TaskAssignment:
    """Get a task combined with plan-level context as a ``TaskAssignment``.

    Composes a ``TaskAssignment`` by loading the plan and embedding the
    plan-level fields (goal, context, acceptance criteria) alongside the
    requested task.  This gives agents everything they need in one call
    per ADR-003.

    Args:
        plan_path: Path to the plan file or directory.
        task_id: Task ID to retrieve (e.g., ``"T1"``).

    Returns:
        A ``TaskAssignment`` containing plan metadata and the nested ``Task``.

    Raises:
        FileNotFoundError: If ``plan_path`` does not exist.
        KeyError: If no task with ``task_id`` is found in the plan.
    """
    result = load_plan(plan_path)
    plan = result.plan

    task: Task | None = None
    for t in plan.tasks:
        if t.id == task_id:
            task = t
            break
    if task is None:
        msg = f"Task '{task_id}' not found in plan '{plan_path}'"
        raise KeyError(msg)

    # Derive plan_number from source_path stem if available.
    plan_number: str | None = None
    plan_slug: str | None = None
    if plan.source_path is not None:
        stem = plan.source_path.stem  # e.g. "P001-auth-system" or "tasks-1-auth-system"
        if stem.startswith("P") and "-" in stem:
            parts = stem.split("-", 1)
            plan_number = parts[0]
            plan_slug = parts[1]
        elif stem.startswith("tasks-"):
            # Legacy naming: tasks-{N}-{slug}
            parts = stem.split("-", 2)
            MIN_PARTS_FOR_NUMBER = 2
            MIN_PARTS_FOR_SLUG = 3
            if len(parts) >= MIN_PARTS_FOR_NUMBER:
                plan_number = parts[1]
            if len(parts) >= MIN_PARTS_FOR_SLUG:
                plan_slug = parts[2]

    return TaskAssignment(
        plan_number=plan_number,
        plan_slug=plan_slug,
        plan_goal=plan.goal,
        plan_context=plan.context,
        plan_acceptance_criteria=plan.acceptance_criteria,
        task=task,
    )


def list_tasks(plan_path: Path) -> list[Task]:
    """List all tasks in a plan.

    Args:
        plan_path: Path to the plan file or directory.

    Returns:
        All ``Task`` models in the plan, in file order.

    Raises:
        FileNotFoundError: If ``plan_path`` does not exist.
    """
    result = load_plan(plan_path)
    return result.plan.tasks


def get_ready_tasks(plan_path: Path) -> list[Task]:
    """Get tasks that are ready for dispatch.

    A task is ready when its status is ``not-started`` and all tasks it
    depends on are in a terminal status (``complete``, ``deferred``,
    ``skipped``).

    Args:
        plan_path: Path to the plan file or directory.

    Returns:
        Tasks ready for dispatch, sorted by priority then numeric ID.

    Raises:
        FileNotFoundError: If ``plan_path`` does not exist.
    """
    result = load_plan(plan_path)
    graph = DependencyGraph(result.plan.tasks)
    return graph.get_ready_tasks()


def update_status(plan_path: Path, task_id: str, new_status: TaskStatus, timestamp_field: str | None = None) -> Task:
    """Update a task's status and optional timestamp.

    Uses ``writers.yaml_writer.update_field`` for atomic field updates that
    preserve comments and field order.

    Args:
        plan_path: Path to the plan file or directory.
        task_id: ID of the task to update (e.g., ``"T1"``).
        new_status: New status value.
        timestamp_field: If provided, also set this timestamp field to the
                         current UTC time (e.g., ``"started"``, ``"completed"``).

    Returns:
        The updated ``Task`` model after the write.

    Raises:
        FileNotFoundError: If ``plan_path`` does not exist.
        KeyError: If ``task_id`` is not found in the plan.
    """
    # Read the current task state once, before writing.
    current = get_task(plan_path, task_id)

    # Resolve to the concrete file path for the writer.
    file_path = _resolve_writable_path(plan_path, task_id)

    # Build all field updates and write them in a single read-modify-write cycle.
    ts = datetime.now(UTC).isoformat()
    field_updates: dict[str, str | int | list[str]] = {"status": str(new_status)}
    if timestamp_field is not None:
        field_updates[timestamp_field] = ts
    update_fields(file_path, task_id, field_updates)

    # Reconstruct the updated Task from what we already know — no second file read.
    kwargs = current.model_dump(by_alias=False)
    kwargs["status"] = new_status
    if timestamp_field == "started":
        from datetime import datetime as _dt  # noqa: PLC0415

        kwargs["started"] = _dt.fromisoformat(ts)
    elif timestamp_field == "completed":
        from datetime import datetime as _dt  # noqa: PLC0415

        kwargs["completed"] = _dt.fromisoformat(ts)
    return Task.model_validate(kwargs)


def get_plan_status(plan_path: Path) -> PlanStatus:
    """Get a plan-level status summary.

    Computes task counts by status, identifies ready and blocked tasks, and
    checks for dependency cycles.

    Args:
        plan_path: Path to the plan file or directory.

    Returns:
        A ``PlanStatus`` summary with counts, ready/blocked task lists,
        completion percentage, and cycle detection result.

    Raises:
        FileNotFoundError: If ``plan_path`` does not exist.
    """
    result = load_plan(plan_path)
    plan = result.plan
    graph = DependencyGraph(plan.tasks)

    by_status: dict[str, int] = {}
    for task in plan.tasks:
        by_status[task.status] = by_status.get(task.status, 0) + 1

    ready_tasks = [t.id for t in graph.get_ready_tasks()]
    blocked_tasks = [{t.id: missing_deps} for t, missing_deps in graph.get_blocked_tasks()]

    total = len(plan.tasks)
    complete_count = by_status.get(TaskStatus.COMPLETE, 0)
    completion_pct = (complete_count / total * 100.0) if total > 0 else 0.0

    return PlanStatus(
        feature=plan.feature,
        total_tasks=total,
        by_status=by_status,
        ready_tasks=ready_tasks,
        blocked_tasks=blocked_tasks,
        completion_pct=completion_pct,
        has_cycles=graph.has_cycles(),
    )


def claim_task(plan_path: Path, task_id: str) -> Task:
    """Atomically claim a task by transitioning it to ``in-progress``.

    Guards against double-claiming by verifying the task is currently
    ``not-started`` before updating. Raises if the task is already claimed
    or in a terminal state.

    Args:
        plan_path: Path to the plan file or directory.
        task_id: ID of the task to claim.

    Returns:
        The updated ``Task`` model with status ``in-progress`` and ``started``
        timestamp set.

    Raises:
        FileNotFoundError: If ``plan_path`` does not exist.
        KeyError: If ``task_id`` is not found.
        ValueError: If the task is not in ``not-started`` status.
    """
    task = get_task(plan_path, task_id)
    if task.status != TaskStatus.NOT_STARTED:
        msg = f"Cannot claim task '{task_id}': expected status 'not-started' but found '{task.status}'."
        raise ValueError(msg)

    return update_status(plan_path, task_id, TaskStatus.IN_PROGRESS, timestamp_field="started")


def _resolve_writable_path(plan_path: Path, task_id: str) -> Path:
    """Resolve the concrete YAML file path that contains ``task_id``.

    For a single ``.yaml`` file, returns ``plan_path`` directly.
    For a directory layout, searches ``task-{task_id}.yaml`` inside it.

    Args:
        plan_path: Plan path as provided by the caller.
        task_id: Task ID whose file should be located.

    Returns:
        Path to the ``.yaml`` file containing the task.

    Raises:
        FileNotFoundError: If the resolved path does not exist.
        KeyError: If no file containing ``task_id`` can be found in a
                  directory layout.
    """
    if plan_path.is_file():
        return plan_path

    # Directory layout: look for per-task file first
    per_task = plan_path / f"task-{task_id}.yaml"
    if per_task.exists():
        return per_task

    # Fall back to plan.yaml (tasks embedded in plan file)
    plan_yaml = plan_path / "plan.yaml"
    if plan_yaml.exists():
        return plan_yaml

    msg = f"Cannot find writable file for task '{task_id}' in directory '{plan_path}'"
    raise KeyError(msg)


# Re-export Plan and TaskAssignment for callers that only need the models
__all__ = [
    "Plan",
    "TaskAssignment",
    "claim_task",
    "create_plan",
    "get_plan_status",
    "get_ready_tasks",
    "get_task",
    "get_task_assignment",
    "list_tasks",
    "load_plan",
    "update_plan_fields",
    "update_status",
]
