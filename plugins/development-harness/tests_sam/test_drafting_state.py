"""Tests for drafting-state semantics introduced by #1770.

DESIGN DECISIONS (binding for the green phase implementer)
==========================================================

1. Drafting-state representation
   --------------------------------
   CHOICE: ``state: Literal["drafting", "ready"]`` field on the Plan Pydantic model
   (option b from the backlog item).

   Rationale: A two-value StrEnum-style field is more explicit than a bare bool
   and maps cleanly to the existing Plan model pattern (see ``TaskStatus``,
   ``Complexity`` etc.).  A ``state`` field also allows additional future states
   without a breaking field rename.

   Consequence: ``Plan.state`` must exist and default to ``"ready"`` so all
   existing tests continue to pass without change.  Plans created with an empty
   ``tasks_yaml='{tasks: []}'`` payload receive ``state="drafting"`` from
   ``create_plan``.  ``append_task`` calls do NOT change ``state`` — it stays
   ``"drafting"`` until ``finalize`` is called.

2. Finalize mechanism
   --------------------
   CHOICE: New ``sam_plan(action='finalize', plan=P)`` routing (option a from
   the backlog item).

   Rationale: A dedicated action is self-documenting at the MCP call-site,
   makes the state transition explicit in server logs, and avoids the risk of
   a raw ``set_fields_json='{"state": "ready"}'`` call accidentally clearing
   a drafting plan before the review step.

   Consequence: A new ``FinalizePlanConfig`` model with ``action: Literal["finalize"]``
   must be added to ``action_models.py`` and wired into the ``sam_plan`` match
   block in ``server.py``.

3. AppendTaskConfig shape
   -----------------------
   CHOICE: New ``AppendTaskConfig(action="append_task", plan_id=..., task_yaml=...)``
   where:
   - ``action: Literal["append_task"]``
   - ``task_yaml: str`` — single-task YAML string with the same schema as one
     element of the ``tasks`` list in ``CreatePlanConfig.tasks_yaml``.
     Example: ``"id: T3\\ntitle: My task\\nstatus: not-started\\n..."``
   - The ``plan`` parameter on the MCP tool wrapper carries the plan address
     (same pattern as ``read``, ``status``, ``ready``).

   ``task_yaml`` mirrors the ``tasks_yaml`` naming convention of ``CreatePlanConfig``
   (singular form for a single task).

AC coverage
-----------
Test D — ``status`` and ``ready`` return ``drafting`` marker for mid-append plan
Test E — ``read`` returns task list plus ``drafting`` marker for mid-append plan
Test F — after ``finalize``, ``status`` and ``ready`` return normal dispatchable data
Test G — (deferred to agent plan-validator tests; plan-validator is out of scope here)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sam_schema.core.backends.memory import InMemoryTaskProvider
from sam_schema.core.task_config import TaskConfig, reset_task_config, set_task_config
from sam_schema.server import sam_plan

if TYPE_CHECKING:
    from collections.abc import Generator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_TASK_DEF = {
    "id": "T1",
    "title": "First task",
    "status": "not-started",
    "agent": "test-agent",
    "dependencies": [],
    "priority": 2,
    "complexity": "low",
}

_MINIMAL_TASK_YAML = (
    "id: T1\n"
    "title: First task\n"
    "status: not-started\n"
    "agent: test-agent\n"
    "dependencies: []\n"
    "priority: 2\n"
    "complexity: low\n"
)

_EMPTY_TASKS_YAML = "tasks: []"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def memory_backend() -> Generator[InMemoryTaskProvider, None, None]:
    """Inject a fresh InMemoryTaskProvider via set_task_config.

    Calls reset_task_config() in teardown to prevent cross-test contamination.

    Yields:
        Configured InMemoryTaskProvider instance.
    """
    backend = InMemoryTaskProvider()
    set_task_config(TaskConfig(backend=backend))
    yield backend
    reset_task_config()


# ---------------------------------------------------------------------------
# Test D — status and ready return drafting marker for mid-append plan
# ---------------------------------------------------------------------------


def test_status_returns_drafting_marker_on_mid_append_plan(memory_backend: InMemoryTaskProvider) -> None:
    """sam_plan(action='status') returns a drafting marker while plan is mid-append.

    AC #12: status returns a drafting marker instead of dispatchable task data
    when the plan is in drafting state.

    Arrange: create a plan with empty tasks_yaml so it enters drafting state.
    Act: call sam_plan(action='status', plan=P).
    Assert: response contains a 'drafting' key that is truthy, or a 'state'
            key with value 'drafting'.
    """
    from sam_schema.core.action_models import CreatePlanConfig, StatusPlanConfig

    # Arrange — create plan in drafting state
    result = sam_plan(config=CreatePlanConfig(slug="test-plan", goal="Test goal", tasks_yaml=_EMPTY_TASKS_YAML))
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
    from sam_schema.core.action_models import AppendTaskConfig, CreatePlanConfig, ReadyPlanConfig

    # Arrange
    create_result = sam_plan(config=CreatePlanConfig(slug="test-plan", goal="Test goal", tasks_yaml=_EMPTY_TASKS_YAML))
    plan_id = create_result["plan_id"]

    sam_plan(config=AppendTaskConfig(task_yaml=_MINIMAL_TASK_YAML), plan=plan_id)

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
    from sam_schema.core.action_models import AppendTaskConfig, CreatePlanConfig, ReadPlanConfig

    # Arrange
    create_result = sam_plan(config=CreatePlanConfig(slug="test-plan", goal="Test goal", tasks_yaml=_EMPTY_TASKS_YAML))
    plan_id = create_result["plan_id"]

    sam_plan(config=AppendTaskConfig(task_yaml=_MINIMAL_TASK_YAML), plan=plan_id)

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
    from sam_schema.core.action_models import AppendTaskConfig, CreatePlanConfig, FinalizePlanConfig, StatusPlanConfig

    # Arrange
    create_result = sam_plan(config=CreatePlanConfig(slug="test-plan", goal="Test goal", tasks_yaml=_EMPTY_TASKS_YAML))
    plan_id = create_result["plan_id"]
    sam_plan(config=AppendTaskConfig(task_yaml=_MINIMAL_TASK_YAML), plan=plan_id)
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
    from sam_schema.core.action_models import AppendTaskConfig, CreatePlanConfig, FinalizePlanConfig, ReadyPlanConfig

    # Arrange
    create_result = sam_plan(config=CreatePlanConfig(slug="test-plan", goal="Test goal", tasks_yaml=_EMPTY_TASKS_YAML))
    plan_id = create_result["plan_id"]
    sam_plan(config=AppendTaskConfig(task_yaml=_MINIMAL_TASK_YAML), plan=plan_id)
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
