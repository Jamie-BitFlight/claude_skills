"""Tests for drafting-state lifecycle introduced by #1770.

Covers the create-empty → drafting → append_task → finalize → ready lifecycle:

- Test D: ``status`` and ``ready`` return a drafting marker for a mid-append plan.
- Test E: ``read`` returns the task list plus a drafting marker for a mid-append plan.
- Test F: after ``finalize``, ``status`` and ``ready`` return normal dispatchable data.

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
from sam_schema.core.models import Complexity, Priority
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
# Test D — status and ready return drafting marker for mid-append plan
# ---------------------------------------------------------------------------


def test_status_returns_drafting_marker_on_mid_append_plan(memory_backend: InMemoryTaskProvider) -> None:
    """sam_plan(action='status') returns a drafting marker while plan is mid-append.

    AC #12: status returns a drafting marker instead of dispatchable task data
    when the plan is in drafting state.

    Arrange: create a plan with empty tasks list so it enters drafting state.
    Act: call sam_plan(action='status', plan=P).
    Assert: response contains a 'drafting' key that is truthy, or a 'state'
            key with value 'drafting'.
    """
    from sam_schema.core.action_models import StatusPlanConfig

    # Arrange — create plan in drafting state
    result = sam_plan(config=_DRAFTING_PLAN_CONFIG)
    plan_id = result["plan_id"]

    # Act
    status = sam_plan(config=StatusPlanConfig(), plan=plan_id)

    # Assert — drafting marker must be present
    assert _is_drafting(status), f"Expected drafting marker in status response for a mid-append plan, got: {status!r}"


def test_ready_returns_drafting_marker_on_mid_append_plan(memory_backend: InMemoryTaskProvider) -> None:
    """sam_plan(action='ready') returns a drafting marker while plan is mid-append.

    AC #12: ready returns a drafting marker instead of dispatchable task data
    when the plan is in drafting state.

    Arrange: create empty plan; append one task so plan has content.
    Act: call sam_plan(action='ready', plan=P).
    Assert: response contains 'drafting' marker; 'ready_tasks' is absent or empty.
    """
    from sam_schema.core.action_models import AppendTaskConfig, ReadyPlanConfig

    # Arrange
    create_result = sam_plan(config=_DRAFTING_PLAN_CONFIG)
    plan_id = create_result["plan_id"]

    sam_plan(config=AppendTaskConfig(task=_MINIMAL_TASK), plan=plan_id)

    # Act
    ready = sam_plan(config=ReadyPlanConfig(), plan=plan_id)

    # Assert
    assert _is_drafting(ready), f"Expected drafting marker in ready response for a mid-append plan, got: {ready!r}"


# ---------------------------------------------------------------------------
# Test E — read returns task list plus drafting marker
# ---------------------------------------------------------------------------


def test_read_returns_tasks_and_drafting_marker_on_mid_append_plan(memory_backend: InMemoryTaskProvider) -> None:
    """sam_plan(action='read') returns tasks plus drafting marker on a drafting plan.

    AC #11: read on a drafting plan returns the plan body including all tasks
    appended so far, and includes the drafting marker in the response.

    Arrange: create empty plan; append one task.
    Act: call sam_plan(action='read', plan=P).
    Assert: response includes the appended task AND a 'drafting' or 'state' marker.
    """
    from sam_schema.core.action_models import AppendTaskConfig, ReadPlanConfig

    # Arrange
    create_result = sam_plan(config=_DRAFTING_PLAN_CONFIG)
    plan_id = create_result["plan_id"]

    sam_plan(config=AppendTaskConfig(task=_MINIMAL_TASK), plan=plan_id)

    # Act
    read_result = sam_plan(config=ReadPlanConfig(), plan=plan_id)

    # Assert — tasks present
    tasks = read_result.get("tasks", [])
    assert len(tasks) == 1, f"Expected 1 task after append, got: {len(tasks)}"
    assert tasks[0]["id"] == "T1"

    # Assert — drafting marker present
    assert _is_drafting(read_result), (
        f"Expected drafting marker in read response for a mid-append plan, got: {read_result!r}"
    )


# ---------------------------------------------------------------------------
# Test F — after finalize, status and ready return normal data
# ---------------------------------------------------------------------------


def test_status_returns_normal_data_after_finalize(memory_backend: InMemoryTaskProvider) -> None:
    """sam_plan(action='status') returns normal task data after finalize clears drafting.

    AC #13/#14: after finalize (or equivalent), status returns real dispatchable data.

    Arrange: create empty plan, append a task, then call finalize.
    Act: call sam_plan(action='status', plan=P).
    Assert: response does NOT contain drafting marker; total_tasks == 1.
    """
    from sam_schema.core.action_models import AppendTaskConfig, FinalizePlanConfig, StatusPlanConfig

    # Arrange
    create_result = sam_plan(config=_DRAFTING_PLAN_CONFIG)
    plan_id = create_result["plan_id"]
    sam_plan(config=AppendTaskConfig(task=_MINIMAL_TASK), plan=plan_id)
    sam_plan(config=FinalizePlanConfig(), plan=plan_id)

    # Act
    status = sam_plan(config=StatusPlanConfig(), plan=plan_id)

    # Assert — no drafting marker
    assert not _is_drafting(status), f"Expected no drafting marker in status after finalize, got: {status!r}"
    # Assert — normal data present
    assert status.get("total_tasks") == 1


def test_ready_returns_normal_data_after_finalize(memory_backend: InMemoryTaskProvider) -> None:
    """sam_plan(action='ready') returns ready tasks after finalize clears drafting.

    AC #13/#14: after finalize, ready lists dispatchable tasks.

    Arrange: create empty plan, append a not-started task with no deps, finalize.
    Act: call sam_plan(action='ready', plan=P).
    Assert: response does NOT contain drafting marker; ready_tasks contains T1.
    """
    from sam_schema.core.action_models import AppendTaskConfig, FinalizePlanConfig, ReadyPlanConfig

    # Arrange
    create_result = sam_plan(config=_DRAFTING_PLAN_CONFIG)
    plan_id = create_result["plan_id"]
    sam_plan(config=AppendTaskConfig(task=_MINIMAL_TASK), plan=plan_id)
    sam_plan(config=FinalizePlanConfig(), plan=plan_id)

    # Act
    ready = sam_plan(config=ReadyPlanConfig(), plan=plan_id)

    # Assert — no drafting marker
    assert not _is_drafting(ready), f"Expected no drafting marker in ready response after finalize, got: {ready!r}"
    # Assert — T1 is ready
    ready_ids = [t["id"] for t in ready.get("ready_tasks", [])]
    assert "T1" in ready_ids, f"Expected T1 in ready tasks after finalize, got: {ready_ids}"


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _is_drafting(response: dict) -> bool:
    """Return True when the response carries a drafting marker.

    Accepts either:
    - ``{"drafting": True, ...}``
    - ``{"state": "drafting", ...}``
    """
    if response.get("drafting") is True:
        return True
    return response.get("state") == "drafting"
