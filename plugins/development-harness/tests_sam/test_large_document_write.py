"""Regression test for incremental large-plan persistence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
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


def _task_definitions(start: int, stop: int) -> list[TaskDefinition]:
    return [_make_task_def(f"T{index:02d}", index) for index in range(start, stop)]


def _assert_task_fields(actual_tasks: Sequence[Mapping[str, Any]], expected_tasks: Sequence[TaskDefinition]) -> None:
    assert [_task_fields(task) for task in actual_tasks] == [_task_fields(task) for task in expected_tasks]


def test_batch_created_large_plan_is_immediately_ready() -> None:
    """A supported nonempty batch create exposes every task through ready."""
    from sam_schema.core.action_models import CreatePlanConfig, ReadyPlanConfig
    from sam_schema.core.models import CreatePlanResult, PlanState, ReadyTasksResult
    from sam_schema.server import sam_plan

    expected_tasks = _task_definitions(1, 51)
    created = sam_plan(config=CreatePlanConfig(slug="batch-plan", goal="Batch plan", tasks=expected_tasks))

    assert isinstance(created, CreatePlanResult)
    ready = sam_plan(config=ReadyPlanConfig(), plan=created.plan_id)
    assert isinstance(ready, ReadyTasksResult)
    assert ready.state == PlanState.READY
    assert [task.id for task in ready.ready_tasks] == [task.id for task in expected_tasks]


def test_mixed_batch_create_and_append_persists_all_fields(memory_backend: ContentTaskProvider) -> None:
    """Batch-created and appended tasks survive one shared content-store readback."""
    from sam_schema.core.action_models import AppendTaskConfig, CreatePlanConfig
    from sam_schema.core.models import AppendTaskResult, CreatePlanResult
    from sam_schema.server import sam_plan

    initial_tasks = _task_definitions(1, 6)
    appended_tasks = _task_definitions(6, 51)
    created = sam_plan(config=CreatePlanConfig(slug="mixed-plan", goal="Mixed plan", tasks=initial_tasks))

    assert isinstance(created, CreatePlanResult)
    for task in appended_tasks:
        appended = sam_plan(config=AppendTaskConfig(task=task), plan=created.plan_id)
        assert isinstance(appended, AppendTaskResult), f"append_task failed at {task.id}: {appended}"

    fresh_provider = ContentTaskProvider(memory_backend._provider)
    _assert_task_fields(fresh_provider.read_plan(created.plan_id)["tasks"], initial_tasks + appended_tasks)


def test_incremental_large_plan_finalizes_and_is_ready_after_hydration(
    memory_backend: ContentTaskProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An incremental 50-task plan finalizes and becomes ready after fresh hydration."""
    from sam_schema.core.action_models import AppendTaskConfig, CreatePlanConfig, FinalizePlanConfig, ReadyPlanConfig
    from sam_schema.core.models import (
        AppendTaskResult,
        CreatePlanResult,
        FinalizePlanResult,
        PlanState,
        ReadyTasksResult,
    )
    from sam_schema.server import sam_plan

    expected_tasks = _task_definitions(1, 51)
    create_result = sam_plan(config=CreatePlanConfig(slug="incremental-plan", goal="Incremental plan", tasks=[]))
    assert isinstance(create_result, CreatePlanResult)
    plan_id = create_result.plan_id

    for task in expected_tasks:
        append_result = sam_plan(config=AppendTaskConfig(task=task), plan=plan_id)
        assert isinstance(append_result, AppendTaskResult), f"append_task failed at {task.id}: {append_result}"

    finalized = sam_plan(config=FinalizePlanConfig(), plan=plan_id)
    assert isinstance(finalized, FinalizePlanResult), f"finalize failed: {finalized}"
    assert finalized.finalized is True
    assert finalized.state == "ready"

    fresh_provider = ContentTaskProvider(memory_backend._provider)
    _assert_task_fields(fresh_provider.read_plan(plan_id)["tasks"], expected_tasks)
    monkeypatch.setattr("sam_schema.server_backend.get_backend", lambda _plan_dir: fresh_provider)

    ready = sam_plan(config=ReadyPlanConfig(), plan=plan_id)
    assert isinstance(ready, ReadyTasksResult)
    assert ready.state == PlanState.READY
    assert [task.id for task in ready.ready_tasks] == [task.id for task in expected_tasks]
