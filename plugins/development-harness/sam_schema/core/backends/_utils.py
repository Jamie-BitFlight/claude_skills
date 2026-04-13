"""Shared utilities for SAM backend implementations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sam_schema.core.exceptions import TaskValidationError

if TYPE_CHECKING:
    from sam_schema.core.models import Task


def _now_iso() -> str:
    """Return current UTC time as an ISO 8601 string."""
    return datetime.now(tz=UTC).isoformat()


def validate_appended_task(task: Task, existing_ids: set[str], plan_id: str) -> None:
    """Assert that a task can safely be appended to a plan.

    Centralises the duplicate-ID guard that all three backends share.
    Call before persisting the task to storage.

    Single-writer contract (ADR-1770-1): backends are NOT required to be
    atomic under concurrent writers. Callers must serialise writes to the
    same plan. Behavior under concurrent writes is undefined.

    Args:
        task: Validated Task model to append.
        existing_ids: Set of task IDs already present in the plan.
        plan_id: Plan identifier used in the error message.

    Raises:
        TaskValidationError: When ``task.id`` is already present in
            ``existing_ids``.
    """
    if task.id in existing_ids:
        raise TaskValidationError(0, f"Task ID {task.id!r} already exists in plan {plan_id!r}")
