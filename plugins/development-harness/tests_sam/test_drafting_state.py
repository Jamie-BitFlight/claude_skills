"""Tests for drafting-state lifecycle introduced by #1770.

Covers the create-empty → drafting → append_task → finalize → ready lifecycle:

- Test D: ``status`` and ``ready`` report ``state="drafting"`` for a mid-append plan.
- Test E: ``read`` returns the task list with ``plan.state="drafting"`` for a mid-append plan.
- Test F: after ``finalize``, ``status`` and ``ready`` report ``state="ready"``.

For the single-writer concurrency contract and the architectural rationale behind
the ``state`` field and ``finalize`` action, see
``plugins/development-harness/docs/adrs/ADR-1770-1-single-writer-task-backend.md``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
from sam_schema.core.action_models import CreatePlanConfig, TaskDefinition
from sam_schema.core.models import (
    Complexity,
    CreatePlanResult,
    PlanState,
    PlanStatus,
    Priority,
    ReadResult,
    ReadyTasksResult,
)
from sam_schema.server import sam_plan

if TYPE_CHECKING:
    from sam_schema.core.backends.memory import InMemoryTaskProvider

_MINIMAL_TASK = TaskDefinition(
    id="T1",
    title="First task",
    status="not-started",
    agent="test-agent",
    dependencies=[],
    priority=Priority.HIGH,
    complexity=Complexity.LOW,
)

_DRAFTING_PLAN_CONFIG = CreatePlanConfig(slug="test-plan", goal="Test goal", tasks=[])


# ---------------------------------------------------------------------------
# Test D — status and ready report drafting state for mid-append plan
# ---------------------------------------------------------------------------


def test_status_returns_drafting_state_on_mid_append_plan(memory_backend: InMemoryTaskProvider) -> None:
    """sam_plan(action='status') reports state='drafting' while plan is mid-append.

    AC #12: status returns a drafting state instead of dispatchable task data
    when the plan is in drafting state.

    Arrange: create a plan with empty tasks list so it enters drafting state.
    Act: call sam_plan(action='status', plan=P).
    Assert: response is a PlanStatus with state='drafting'.
    """
    from sam_schema.core.action_models import StatusPlanConfig

    # Arrange — create plan in drafting state
    result = sam_plan(config=_DRAFTING_PLAN_CONFIG)
    assert isinstance(result, CreatePlanResult)
    plan_id = result.plan_id

    # Act
    status = sam_plan(config=StatusPlanConfig(), plan=plan_id)

    # Assert — drafting state must be reported
    assert isinstance(status, PlanStatus)
    assert status.state == PlanState.DRAFTING, (
        f"Expected drafting state in status response for a mid-append plan, got: {status!r}"
    )


def test_ready_returns_drafting_state_on_mid_append_plan(memory_backend: InMemoryTaskProvider) -> None:
    """sam_plan(action='ready') reports state='drafting' while plan is mid-append.

    AC #12: ready returns a drafting state instead of dispatchable task data
    when the plan is in drafting state.

    Arrange: create empty plan; append one task so plan has content.
    Act: call sam_plan(action='ready', plan=P).
    Assert: response is a ReadyTasksResult with state='drafting' and empty ready_tasks.
    """
    from sam_schema.core.action_models import AppendTaskConfig, ReadyPlanConfig

    # Arrange
    create_result = sam_plan(config=_DRAFTING_PLAN_CONFIG)
    assert isinstance(create_result, CreatePlanResult)
    plan_id = create_result.plan_id

    sam_plan(config=AppendTaskConfig(task=_MINIMAL_TASK), plan=plan_id)

    # Act
    ready = sam_plan(config=ReadyPlanConfig(), plan=plan_id)

    # Assert
    assert isinstance(ready, ReadyTasksResult)
    assert ready.state == PlanState.DRAFTING, (
        f"Expected drafting state in ready response for a mid-append plan, got: {ready!r}"
    )
    assert ready.ready_tasks == [], f"Expected empty ready_tasks for drafting plan, got: {ready.ready_tasks!r}"


# ---------------------------------------------------------------------------
# Test E — read returns task list plus drafting state
# ---------------------------------------------------------------------------


def test_read_returns_tasks_and_drafting_state_on_mid_append_plan(memory_backend: InMemoryTaskProvider) -> None:
    """sam_plan(action='read') returns tasks with plan.state='drafting' on a drafting plan.

    AC #11: read on a drafting plan returns the plan body including all tasks
    appended so far, with the plan state set to drafting.

    Arrange: create empty plan; append one task.
    Act: call sam_plan(action='read', plan=P).
    Assert: response includes the appended task AND plan.state == 'drafting'.
    """
    from sam_schema.core.action_models import AppendTaskConfig, ReadPlanConfig

    # Arrange
    create_result = sam_plan(config=_DRAFTING_PLAN_CONFIG)
    assert isinstance(create_result, CreatePlanResult)
    plan_id = create_result.plan_id

    sam_plan(config=AppendTaskConfig(task=_MINIMAL_TASK), plan=plan_id)

    # Act
    read_result = sam_plan(config=ReadPlanConfig(), plan=plan_id)
    assert isinstance(read_result, ReadResult)

    # Assert — tasks present
    tasks = read_result.plan.tasks
    assert len(tasks) == 1, f"Expected 1 task after append, got: {len(tasks)}"
    assert tasks[0].id == "T1"

    # Assert — drafting state reported
    assert read_result.plan.state == PlanState.DRAFTING, (
        f"Expected drafting state in read response for a mid-append plan, got: {read_result!r}"
    )


# ---------------------------------------------------------------------------
# Test F — after finalize, status and ready return ready state
# ---------------------------------------------------------------------------


def test_status_returns_normal_data_after_finalize(memory_backend: InMemoryTaskProvider) -> None:
    """sam_plan(action='status') returns normal task data after finalize clears drafting.

    AC #13/#14: after finalize (or equivalent), status returns real dispatchable data.

    Arrange: create empty plan, append a task, then call finalize.
    Act: call sam_plan(action='status', plan=P).
    Assert: response state is 'ready'; total_tasks == 1.
    """
    from sam_schema.core.action_models import AppendTaskConfig, FinalizePlanConfig, StatusPlanConfig

    # Arrange
    create_result = sam_plan(config=_DRAFTING_PLAN_CONFIG)
    assert isinstance(create_result, CreatePlanResult)
    plan_id = create_result.plan_id
    sam_plan(config=AppendTaskConfig(task=_MINIMAL_TASK), plan=plan_id)
    sam_plan(config=FinalizePlanConfig(), plan=plan_id)

    # Act
    status = sam_plan(config=StatusPlanConfig(), plan=plan_id)
    assert isinstance(status, PlanStatus)

    # Assert — ready state reported
    assert status.state == PlanState.READY, f"Expected ready state in status after finalize, got: {status!r}"
    # Assert — normal data present
    assert status.total_tasks == 1


def test_ready_returns_normal_data_after_finalize(memory_backend: InMemoryTaskProvider) -> None:
    """sam_plan(action='ready') returns ready tasks after finalize clears drafting.

    AC #13/#14: after finalize, ready lists dispatchable tasks.

    Arrange: create empty plan, append a not-started task with no deps, finalize.
    Act: call sam_plan(action='ready', plan=P).
    Assert: response state is 'ready'; ready_tasks contains T1.
    """
    from sam_schema.core.action_models import AppendTaskConfig, FinalizePlanConfig, ReadyPlanConfig

    # Arrange
    create_result = sam_plan(config=_DRAFTING_PLAN_CONFIG)
    assert isinstance(create_result, CreatePlanResult)
    plan_id = create_result.plan_id
    sam_plan(config=AppendTaskConfig(task=_MINIMAL_TASK), plan=plan_id)
    sam_plan(config=FinalizePlanConfig(), plan=plan_id)

    # Act
    ready = sam_plan(config=ReadyPlanConfig(), plan=plan_id)
    assert isinstance(ready, ReadyTasksResult)

    # Assert — ready state reported
    assert ready.state == PlanState.READY, f"Expected ready state in ready response after finalize, got: {ready!r}"
    # Assert — T1 is ready
    ready_ids = [t.id for t in ready.ready_tasks]
    assert "T1" in ready_ids, f"Expected T1 in ready tasks after finalize, got: {ready_ids}"
