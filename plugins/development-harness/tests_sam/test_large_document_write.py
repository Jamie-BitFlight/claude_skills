"""Regression test for incremental large-plan persistence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sam_schema.core.action_models import TaskDefinition
from sam_schema.core.backends.content import ContentTaskProvider
from sam_schema.core.models import Complexity, Priority

# ---------------------------------------------------------------------------
# Task generation helpers
# ---------------------------------------------------------------------------


def _make_task_def(task_id: str, idx: int, deps: list[str] | None = None) -> TaskDefinition:
    """Produce a single TaskDefinition for use with append_task.

    Args:
        task_id: Identifier for the task (e.g. ``'T01'``).
        idx: Sequential index used to generate deterministic title/body content.
        deps: Optional list of dependency task IDs.

    Returns:
        TaskDefinition instance compatible with AppendTaskConfig.task.
    """
    return TaskDefinition(
        id=task_id,
        title=f"Task {idx:02d} title text",
        status="not-started",
        agent="test-agent",
        dependencies=list(deps or []),
        priority=Priority.HIGH,
        complexity=Complexity.LOW,
        description=f"Description for task {idx:02d}.",
    )


def _task_fields(task: Mapping[str, Any] | TaskDefinition) -> dict[str, Any]:
    """Return durable task fields in their public JSON representation."""
    if isinstance(task, TaskDefinition):
        task = task.model_dump(mode="json")
    return {
        "id": task.get("id"),
        "title": task.get("title"),
        "status": task.get("status"),
        "agent": task.get("agent"),
        "dependencies": task.get("dependencies", []),
        "priority": task.get("priority"),
        "complexity": task.get("complexity"),
        "description": task.get("description", ""),
    }


def test_incremental_large_plan_finalizes_and_persists_all_fields(memory_backend: ContentTaskProvider) -> None:
    """An incremental 50-task plan remains complete after fresh-provider hydration."""
    from sam_schema.core.action_models import AppendTaskConfig, CreatePlanConfig, FinalizePlanConfig
    from sam_schema.core.models import AppendTaskResult, CreatePlanResult, FinalizePlanResult
    from sam_schema.server import sam_plan

    expected_tasks = [_make_task_def(f"T{i:02d}", i) for i in range(1, 51)]
    create_result = sam_plan(config=CreatePlanConfig(slug="incremental-plan", goal="Incremental plan", tasks=[]))
    assert isinstance(create_result, CreatePlanResult)
    plan_id = create_result.plan_id

    for task in expected_tasks:
        append_result = sam_plan(config=AppendTaskConfig(task=task), plan=plan_id)
        assert isinstance(append_result, AppendTaskResult), f"append_task failed at {task.id}: {append_result}"

    finalized = sam_plan(config=FinalizePlanConfig(), plan=plan_id)
    assert isinstance(finalized, FinalizePlanResult), f"finalize failed: {finalized}"

    fresh_provider = ContentTaskProvider(memory_backend._provider)
    actual_tasks = fresh_provider.read_plan(plan_id)["tasks"]
    assert [_task_fields(task) for task in actual_tasks] == [_task_fields(task) for task in expected_tasks]
