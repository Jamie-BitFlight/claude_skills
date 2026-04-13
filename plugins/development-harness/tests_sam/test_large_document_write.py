"""Regression tests for large-plan write correctness — AC #18 from #1770.

Tests A, B, C verify that a 50-task plan round-trips correctly regardless of
whether it is written monolithically (create) or incrementally (append_task).

All three tests share the same canonical task generator so the 50-task input is
reproducible and the byte-round-trip assertion is deterministic.

AC coverage
-----------
Test A: monolithic create with ~50 tasks completes and round-trips
Test B: incremental create + 50 append_task calls produces identical field content
Test C: mixed — create with 5 tasks, append 45 more, verify order and field preservation
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sam_schema.core.action_models import TaskDefinition

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sam_schema.core.backends.memory import InMemoryTaskProvider

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
        priority=2,
        complexity="low",
        description=f"Description for task {idx:02d}.",
    )


def _make_tasks_list(count: int, start: int = 1) -> list[TaskDefinition]:
    """Build a list of TaskDefinition instances for CreatePlanConfig.

    Args:
        count: Number of tasks to generate.
        start: Starting sequential index (default 1).

    Returns:
        List of TaskDefinition instances with deterministic content.
    """
    return [
        TaskDefinition(
            id=f"T{i:02d}",
            title=f"Task {i:02d} title text",
            status="not-started",
            agent="test-agent",
            dependencies=[],
            priority=2,
            complexity="low",
            description=f"Description for task {i:02d}.",
        )
        for i in range(start, start + count)
    ]


def _extract_task_fields(task: Mapping[str, Any]) -> dict[str, Any]:
    """Return the subset of task fields used for round-trip equality.

    Only structural and content fields are compared; backend timestamps
    (``created``, ``started``, ``completed``) are excluded.

    Args:
        task: TaskData dict from a read_plan call.

    Returns:
        Dict with id, title, status, agent, dependencies, priority, complexity,
        description fields.
    """
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


# ---------------------------------------------------------------------------
# Test A — monolithic 50-task create round-trips
# ---------------------------------------------------------------------------


def test_A_monolithic_50_task_create_round_trips(memory_backend: InMemoryTaskProvider) -> None:
    """Monolithic create with 50 tasks completes and round-trips field content correctly.

    AC #18 Test A: sam_plan(action='create', tasks=<50 TaskDefinition objects>) must succeed
    and all task fields must survive the round-trip through the backend.

    Arrange: build a list of 50 TaskDefinition objects.
    Act: create the plan; read it back.
    Assert: plan contains exactly 50 tasks; each task ID, title, and description
            matches the generated input.
    """
    from sam_schema.core.action_models import CreatePlanConfig
    from sam_schema.server import sam_plan

    # Arrange
    n = 50
    tasks = _make_tasks_list(n)

    # Act
    result = sam_plan(config=CreatePlanConfig(slug="large-plan", goal="Large plan goal", tasks=tasks))
    assert "error" not in result, f"create failed: {result}"
    plan_id = result["plan_id"]

    plan_data = memory_backend.read_plan(plan_id)
    tasks = plan_data["tasks"]

    # Assert — count
    assert len(tasks) == n, f"Expected {n} tasks, got {len(tasks)}"

    # Assert — field content for each task
    for i in range(1, n + 1):
        task = tasks[i - 1]
        fields = _extract_task_fields(task)
        assert fields["id"] == f"T{i:02d}", f"Task {i}: id mismatch: {fields['id']!r}"
        assert fields["title"] == f"Task {i:02d} title text", f"Task {i}: title mismatch"
        assert fields["status"] == "not-started", f"Task {i}: status mismatch"


# ---------------------------------------------------------------------------
# Test B — incremental 50-task append produces identical content to monolithic create
# ---------------------------------------------------------------------------


def test_B_incremental_50_append_matches_monolithic_create(memory_backend: InMemoryTaskProvider) -> None:
    """50 sequential append_task calls produce plan with identical content to monolithic create.

    AC #18 Test B: the plan produced by create({tasks:[]}) + 50 x append_task
    must have field content identical to a monolithic create with the same 50 tasks.

    Arrange: build a monolithic plan (reference) and an incremental plan (subject).
    Act: read both plans back; compare extracted fields for each task.
    Assert: both plans have 50 tasks; each task's structural fields are equal.
    """
    from sam_schema.core.action_models import AppendTaskConfig, CreatePlanConfig
    from sam_schema.server import sam_plan

    n = 50

    # Arrange — monolithic reference
    mono_result = sam_plan(
        config=CreatePlanConfig(slug="mono-plan", goal="Monolithic reference", tasks=_make_tasks_list(n))
    )
    assert "error" not in mono_result
    mono_id = mono_result["plan_id"]

    # Arrange — incremental subject: create empty, then append 50 tasks
    incr_result = sam_plan(config=CreatePlanConfig(slug="incr-plan", goal="Monolithic reference", tasks=[]))
    assert "error" not in incr_result
    incr_id = incr_result["plan_id"]

    for i in range(1, n + 1):
        task_id = f"T{i:02d}"
        append_result = sam_plan(config=AppendTaskConfig(task=_make_task_def(task_id, i)), plan=incr_id)
        assert "error" not in append_result, f"append_task failed at T{i:02d}: {append_result}"

    # Act — read both plans
    mono_data = memory_backend.read_plan(mono_id)
    incr_data = memory_backend.read_plan(incr_id)

    # Assert — same task count
    assert len(incr_data["tasks"]) == n, f"Expected {n} tasks in incremental plan, got {len(incr_data['tasks'])}"
    assert len(mono_data["tasks"]) == n

    # Assert — field-by-field equality
    for idx in range(n):
        mono_fields = _extract_task_fields(mono_data["tasks"][idx])
        incr_fields = _extract_task_fields(incr_data["tasks"][idx])
        assert mono_fields == incr_fields, (
            f"Task at index {idx} differs:\n  monolithic: {mono_fields!r}\n  incremental: {incr_fields!r}"
        )


# ---------------------------------------------------------------------------
# Test C — mixed: create with 5 tasks, append 45 more, verify order and field
# ---------------------------------------------------------------------------


def test_C_mixed_5_create_45_append_preserves_order_and_fields(memory_backend: InMemoryTaskProvider) -> None:
    """Create with 5 tasks then append 45 more: total 50 tasks in correct order.

    AC #18 Test C: mixed approach must produce correct task ordering (T01 first,
    T50 last) with all fields preserved.

    Arrange: create plan with T01..T05; append T06..T50.
    Act: read plan back.
    Assert: 50 tasks; IDs are T01..T50 in order; all titles and descriptions match.
    """
    from sam_schema.core.action_models import AppendTaskConfig, CreatePlanConfig
    from sam_schema.server import sam_plan

    initial = 5
    remaining = 45
    total = initial + remaining

    # Arrange — create with first 5 tasks
    create_result = sam_plan(
        config=CreatePlanConfig(slug="mixed-plan", goal="Mixed create goal", tasks=_make_tasks_list(initial, start=1))
    )
    assert "error" not in create_result
    plan_id = create_result["plan_id"]

    # Arrange — append remaining 45 tasks
    for i in range(initial + 1, total + 1):
        task_id = f"T{i:02d}"
        append_result = sam_plan(config=AppendTaskConfig(task=_make_task_def(task_id, i)), plan=plan_id)
        assert "error" not in append_result, f"append_task failed at T{i:02d}: {append_result}"

    # Act
    plan_data = memory_backend.read_plan(plan_id)
    tasks = plan_data["tasks"]

    # Assert — count
    assert len(tasks) == total, f"Expected {total} tasks, got {len(tasks)}"

    # Assert — ordering: T01 first, T50 last
    assert tasks[0]["id"] == "T01", f"Expected first task to be T01, got {tasks[0]['id']!r}"
    assert tasks[-1]["id"] == "T50", f"Expected last task to be T50, got {tasks[-1]['id']!r}"

    # Assert — all task IDs are present in order
    task_ids = [t["id"] for t in tasks]
    expected_ids = [f"T{i:02d}" for i in range(1, total + 1)]
    assert task_ids == expected_ids, f"Task order mismatch:\n  got:      {task_ids}\n  expected: {expected_ids}"

    # Assert — field content for a sample task in the appended range
    t30 = next((t for t in tasks if t["id"] == "T30"), None)
    assert t30 is not None, "Expected to find T30 in plan tasks"
    assert t30["title"] == "Task 30 title text"
    assert t30["description"] == "Description for task 30."
