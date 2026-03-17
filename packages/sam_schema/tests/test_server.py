"""Tests for sam_schema.server — MCP tool functions.

Tests: All four MCP tools (sam_read, sam_state, sam_ready, sam_status).
How: Write real plan files to tmp_path, create a plan directory with
     tasks-{N}-{slug}.yaml naming so resolve_plan_address can find them,
     then call each MCP tool function directly and assert on returned dicts.
Why: server.py has zero test coverage; the tools are the primary interface
     used by Claude Code agents to query and mutate SAM plans.
"""
# T02: sam_read now returns TaskAssignment when task param is provided.

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sam_schema.core.models import Complexity, Plan, Priority, Task, TaskStatus
from sam_schema.server import sam_read, sam_ready, sam_state, sam_status
from sam_schema.writers.yaml_writer import write_plan

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_task(
    task_id: str,
    status: TaskStatus = TaskStatus.NOT_STARTED,
    dependencies: list[str] | None = None,
    priority: Priority = Priority.MEDIUM,
) -> Task:
    """Return a minimal Task for test use."""
    return Task(
        id=task_id,
        title=f"Task {task_id}",
        status=status,
        dependencies=dependencies or [],
        priority=priority,
        complexity=Complexity.MEDIUM,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def plan_dir(tmp_path: Path) -> Path:
    """Create a plan directory with a two-task plan file.

    Directory layout::

        tmp_path/
        └── plan/
            └── tasks-1-test-feature.yaml   (T1 complete, T2 depends on T1)

    Returns:
        Path to the plan directory (``tmp_path/plan``).
    """
    p_dir = tmp_path / "plan"
    p_dir.mkdir()

    tasks = [make_task("T1", status=TaskStatus.COMPLETE), make_task("T2", dependencies=["T1"])]
    plan = Plan(feature="test-feature", version="1.0", tasks=tasks)

    plan_file = p_dir / "tasks-1-test-feature.yaml"
    write_plan(plan, plan_file, force_single=True)
    return p_dir


@pytest.fixture
def plan_dir_str(plan_dir: Path) -> str:
    """Return plan directory as string (MCP tool signature accepts str)."""
    return str(plan_dir)


# ---------------------------------------------------------------------------
# sam_read
# ---------------------------------------------------------------------------


def test_sam_read_existing_task_returns_task_fields(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_read returns task fields dict for an existing task.

    Tests: sam_read happy path.
    How: Address 'P1', task 'T1' on a plan dir with tasks-1-test-feature.yaml.
    Why: sam_read is the primary read tool used by agents to inspect task state.
    """
    # Arrange — plan_dir fixture provides tasks-1-test-feature.yaml

    # Act
    result = sam_read(plan="P1", task="T1", plan_dir=plan_dir_str)

    # Assert — sam_read now returns TaskAssignment; task fields are under "task" key.
    assert "error" not in result
    assert "task" in result
    assert result["task"]["id"] == "T1"
    assert result["task"]["status"] == "complete"


def test_sam_read_returns_dict_with_all_required_fields(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_read result contains nested task with 'id', 'title', and 'status' keys.

    Tests: Return structure of sam_read TaskAssignment shape.
    How: Call sam_read for T2 and check task key presence.
    Why: Agents rely on these keys being present to make routing decisions.
    """
    # Act
    result = sam_read(plan="P1", task="T2", plan_dir=plan_dir_str)

    # Assert — task fields are nested under "task" in the TaskAssignment shape.
    assert "error" not in result
    assert "task" in result
    assert "id" in result["task"]
    assert "title" in result["task"]
    assert "status" in result["task"]


def test_sam_read_missing_task_returns_error_dict(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_read returns {'error': ...} for a task ID that does not exist.

    Tests: sam_read error handling for missing task.
    How: Request task 'T99' which is not in the plan.
    Why: MCP tools must never raise exceptions; they return error dicts instead.
    """
    # Act
    result = sam_read(plan="P1", task="T99", plan_dir=plan_dir_str)

    # Assert
    assert "error" in result
    assert "T99" in result["error"]


def test_sam_read_invalid_plan_address_returns_error_dict(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_read returns {'error': ...} for an unresolvable plan address.

    Tests: sam_read error handling for invalid plan address.
    How: Request plan 'P999' which has no matching file in the directory.
    Why: Agents must be able to detect addressing failures from the return value.
    """
    # Act
    result = sam_read(plan="P999", task="T1", plan_dir=plan_dir_str)

    # Assert
    assert "error" in result


def test_sam_read_nonexistent_plan_dir_returns_error_dict(tmp_path: Path) -> None:
    """sam_read returns {'error': ...} when plan_dir does not exist.

    Tests: sam_read error handling for missing plan directory.
    How: Pass a path that does not exist.
    Why: The tool must handle filesystem errors gracefully without raising.
    """
    # Act
    result = sam_read(plan="P1", task="T1", plan_dir=str(tmp_path / "missing"))

    # Assert
    assert "error" in result


# ---------------------------------------------------------------------------
# sam_state
# ---------------------------------------------------------------------------


def test_sam_state_updates_task_status(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_state writes new status and returns updated task.

    Tests: sam_state happy path for status update.
    How: Transition T2 from not-started to in-progress.
    Why: sam_state is the mutation tool agents use to advance task lifecycle.
    """
    # Act
    result = sam_state(plan="P1", task="T2", status="in-progress", plan_dir=plan_dir_str)

    # Assert
    assert "error" not in result
    assert result["id"] == "T2"
    assert result["status"] == "in-progress"


def test_sam_state_accepts_all_valid_status_values(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_state accepts every value from the TaskStatus enum.

    Tests: sam_state with each canonical status string.
    How: Cycle through valid statuses on T2.
    Why: Agents use all status values during the task lifecycle.
    """
    for status_str in ("in-progress", "blocked", "complete", "deferred", "skipped", "not-started"):
        result = sam_state(plan="P1", task="T2", status=status_str, plan_dir=plan_dir_str)
        assert "error" not in result, f"Unexpected error for status '{status_str}': {result}"
        assert result["status"] == status_str


def test_sam_state_invalid_status_returns_error_dict(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_state returns {'error': ...} for an unrecognized status string.

    Tests: sam_state error handling for invalid status values.
    How: Pass 'typo-status' which is not in TaskStatus.
    Why: Prevents agents from writing garbage status values that would corrupt
    plan files and trigger silent re-dispatch of completed tasks.
    """
    # Act
    result = sam_state(plan="P1", task="T2", status="typo-status", plan_dir=plan_dir_str)

    # Assert
    assert "error" in result


def test_sam_state_missing_task_returns_error_dict(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_state returns {'error': ...} when the task ID is not found.

    Tests: sam_state error handling for missing task.
    How: Attempt to update status on 'T99' which does not exist.
    Why: Tools must never raise; error dicts allow callers to inspect failures.
    """
    # Act
    result = sam_state(plan="P1", task="T99", status="complete", plan_dir=plan_dir_str)

    # Assert
    assert "error" in result


def test_sam_state_invalid_plan_address_returns_error_dict(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_state returns {'error': ...} for an unresolvable plan address.

    Tests: sam_state error handling for invalid plan address.
    How: Address 'P999' does not match any file in the plan directory.
    Why: Addressing failures must surface via return value, not exceptions.
    """
    # Act
    result = sam_state(plan="P999", task="T1", status="complete", plan_dir=plan_dir_str)

    # Assert
    assert "error" in result


# ---------------------------------------------------------------------------
# sam_ready
# ---------------------------------------------------------------------------


def test_sam_ready_returns_ready_tasks_list(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_ready returns tasks whose dependencies are all complete.

    Tests: sam_ready happy path.
    How: T1 is complete, T2 depends on T1 — T2 is the only ready task.
    Why: sam_ready is the tool agents poll to find their next task to execute.
    """
    # Act
    result = sam_ready(plan="P1", plan_dir=plan_dir_str)

    # Assert
    assert "error" not in result
    assert "ready_tasks" in result
    assert "count" in result
    assert result["count"] == 1
    assert result["ready_tasks"][0]["id"] == "T2"


def test_sam_ready_count_matches_ready_tasks_length(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_ready 'count' field matches len(ready_tasks).

    Tests: sam_ready return value consistency.
    How: Check count == len(ready_tasks).
    Why: Callers may use count for quick checks before iterating the list.
    """
    # Act
    result = sam_ready(plan="P1", plan_dir=plan_dir_str)

    # Assert
    assert result["count"] == len(result["ready_tasks"])


def test_sam_ready_invalid_plan_address_returns_error_dict(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_ready returns {'error': ...} for an unresolvable plan address.

    Tests: sam_ready error handling.
    How: Pass 'P999' which does not match any file.
    Why: Addressing failures must be surfaced as error dicts.
    """
    # Act
    result = sam_ready(plan="P999", plan_dir=plan_dir_str)

    # Assert
    assert "error" in result


def test_sam_ready_all_complete_plan_returns_empty_list(tmp_path: Path) -> None:
    """sam_ready returns empty ready_tasks when all tasks are complete.

    Tests: sam_ready with no ready tasks.
    How: Create a plan where all tasks are COMPLETE.
    Why: Agents must handle the empty case to know the plan is finished.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()

    tasks = [
        make_task("T1", status=TaskStatus.COMPLETE),
        make_task("T2", status=TaskStatus.COMPLETE, dependencies=["T1"]),
    ]
    plan = Plan(feature="done-feature", version="1.0", tasks=tasks)
    write_plan(plan, p_dir / "tasks-1-done-feature.yaml", force_single=True)

    # Act
    result = sam_ready(plan="P1", plan_dir=str(p_dir))

    # Assert
    assert "error" not in result
    assert result["count"] == 0
    assert result["ready_tasks"] == []


# ---------------------------------------------------------------------------
# sam_status
# ---------------------------------------------------------------------------


def test_sam_status_returns_plan_summary(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_status returns a plan-level progress summary dict.

    Tests: sam_status happy path.
    How: Call sam_status on a two-task plan (T1 complete, T2 not-started).
    Why: sam_status gives agents and orchestrators an overview of plan progress.
    """
    # Act
    result = sam_status(plan="P1", plan_dir=plan_dir_str)

    # Assert
    assert "error" not in result
    assert result["total_tasks"] == 2
    assert "by_status" in result
    assert "ready_tasks" in result
    assert "completion_pct" in result
    assert "has_cycles" in result


def test_sam_status_completion_pct_reflects_completed_tasks(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_status completion_pct equals completed/total * 100.

    Tests: sam_status completion percentage calculation.
    How: T1 is complete out of 2 tasks — expected 50.0%.
    Why: Callers use completion_pct to report plan progress.
    """
    # Act
    result = sam_status(plan="P1", plan_dir=plan_dir_str)

    # Assert
    assert result["completion_pct"] == pytest.approx(50.0)


def test_sam_status_by_status_contains_complete_and_not_started(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_status by_status dict reflects actual task statuses.

    Tests: sam_status by_status aggregation.
    How: Verify complete=1, not-started=1 for the two-task fixture plan.
    Why: Agents and dashboards rely on by_status for per-state counts.
    """
    # Act
    result = sam_status(plan="P1", plan_dir=plan_dir_str)

    # Assert
    by_status = result["by_status"]
    assert by_status.get("complete", 0) == 1
    assert by_status.get("not-started", 0) == 1


def test_sam_status_invalid_plan_address_returns_error_dict(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_status returns {'error': ...} for an unresolvable plan address.

    Tests: sam_status error handling.
    How: Pass 'P999' which does not match any file.
    Why: Tools must return error dicts, not raise exceptions.
    """
    # Act
    result = sam_status(plan="P999", plan_dir=plan_dir_str)

    # Assert
    assert "error" in result


def test_sam_status_has_cycles_false_for_acyclic_plan(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_status has_cycles is False for an acyclic dependency graph.

    Tests: sam_status cycle detection reporting.
    How: The fixture plan (T1 <- T2) has no cycles.
    Why: has_cycles must be accurate so agents do not treat valid plans as broken.
    """
    # Act
    result = sam_status(plan="P1", plan_dir=plan_dir_str)

    # Assert
    assert result["has_cycles"] is False


def test_sam_status_has_cycles_true_for_cyclic_plan(tmp_path: Path) -> None:
    """sam_status has_cycles is True when the dependency graph contains a cycle.

    Tests: sam_status cycle detection with a real cyclic plan.
    How: Create T1 -> T2 -> T1 (cycle), write to tmp dir, call sam_status.
    Why: Agents must detect cycles to avoid infinite dispatch loops.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()

    # Build a cyclic plan: T1 depends on T2 and T2 depends on T1
    tasks = [
        Task(
            id="T1",
            title="Task 1",
            status=TaskStatus.NOT_STARTED,
            dependencies=["T2"],
            complexity=Complexity.MEDIUM,
            priority=Priority.MEDIUM,
        ),
        Task(
            id="T2",
            title="Task 2",
            status=TaskStatus.NOT_STARTED,
            dependencies=["T1"],
            complexity=Complexity.MEDIUM,
            priority=Priority.MEDIUM,
        ),
    ]
    plan = Plan(feature="cyclic-feature", version="1.0", tasks=tasks)
    write_plan(plan, p_dir / "tasks-1-cyclic-feature.yaml", force_single=True)

    # Act
    result = sam_status(plan="P1", plan_dir=str(p_dir))

    # Assert
    assert "error" not in result
    assert result["has_cycles"] is True


# ---------------------------------------------------------------------------
# sam_read — TaskAssignment (T02)
# ---------------------------------------------------------------------------


def test_sam_read_with_task_returns_task_assignment_shape(plan_dir_str: str) -> None:
    """sam_read with task param returns dict with nested 'task' key (TaskAssignment)."""
    # Act
    result = sam_read(plan="P1", task="T1", plan_dir=plan_dir_str)

    # Assert
    assert "error" not in result
    assert "task" in result
    assert result["task"]["id"] == "T1"


def test_sam_read_with_task_includes_plan_goal(tmp_path: Path) -> None:
    """sam_read with task param surfaces plan_goal from the plan in TaskAssignment."""
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    tasks = [make_task("T1")]
    plan = Plan(feature="goal-feature", version="1.0", goal="Ship the goal feature", tasks=tasks)
    write_plan(plan, p_dir / "tasks-1-goal-feature.yaml", force_single=True)

    # Act
    result = sam_read(plan="P1", task="T1", plan_dir=str(p_dir))

    # Assert
    assert "error" not in result
    assert result.get("plan-goal") == "Ship the goal feature"


def test_sam_read_with_task_includes_plan_context(tmp_path: Path) -> None:
    """sam_read with task param surfaces plan_context in TaskAssignment."""
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    tasks = [make_task("T1")]
    plan = Plan(feature="ctx-feature", version="1.0", context="Shared context text here", tasks=tasks)
    write_plan(plan, p_dir / "tasks-1-ctx-feature.yaml", force_single=True)

    # Act
    result = sam_read(plan="P1", task="T1", plan_dir=str(p_dir))

    # Assert
    assert "error" not in result
    assert result.get("plan-context") == "Shared context text here"


def test_sam_read_without_task_returns_plan_fields(plan_dir_str: str) -> None:
    """sam_read without task param returns Plan fields with no TaskAssignment wrapper."""
    # Act
    result = sam_read(plan="P1", plan_dir=plan_dir_str)

    # Assert
    assert "error" not in result
    assert "feature" in result
    assert "task" not in result


def test_sam_read_with_missing_task_returns_error(plan_dir_str: str) -> None:
    """sam_read with a task ID not in the plan returns a dict with 'error' key."""
    # Act
    result = sam_read(plan="P1", task="T99", plan_dir=plan_dir_str)

    # Assert
    assert "error" in result
    assert "T99" in result["error"]


def test_sam_read_with_missing_plan_returns_error(tmp_path: Path) -> None:
    """sam_read with a plan address not found returns a dict with 'error' key."""
    # Arrange
    empty_dir = tmp_path / "plan"
    empty_dir.mkdir()

    # Act
    result = sam_read(plan="P99", task="T1", plan_dir=str(empty_dir))

    # Assert
    assert "error" in result


# ---------------------------------------------------------------------------
# sam_create
# ---------------------------------------------------------------------------


def test_sam_create_valid_tasks_yaml_returns_path_and_counts(tmp_path: Path) -> None:
    """sam_create with valid tasks_yaml creates a plan file and returns metadata.

    Tests: sam_create happy path.
    How: Pass a minimal tasks_yaml string; verify returned dict has path, plan_number, task_count.
    Why: sam_create is the MCP entry point for swarm-task-planner to persist new plans.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    tasks_yaml = (
        "tasks:\n"
        "  - task: T01\n"
        "    title: First task\n"
        "    status: not-started\n"
        "    agent: test-agent\n"
        "    dependencies: []\n"
        "    priority: 1\n"
        "    complexity: low\n"
    )

    # Act
    from sam_schema.server import sam_create

    result = sam_create(slug="test-create", goal="Test goal", tasks_yaml=tasks_yaml, plan_dir=str(p_dir))

    # Assert
    assert "error" not in result
    assert "path" in result
    assert result["task_count"] == 1
    assert result["plan_number"] == 1


def test_sam_create_file_is_readable_by_sam_read(tmp_path: Path) -> None:
    """sam_create round-trip: created file is readable by sam_read.

    Tests: AC4 round-trip (create then read produces identical data).
    How: sam_create then sam_read the T01 task; compare title.
    Why: Validates write→read consistency through the full pipeline.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    tasks_yaml = (
        "tasks:\n"
        "  - task: T01\n"
        "    title: Round-trip task\n"
        "    status: not-started\n"
        "    agent: test-agent\n"
        "    dependencies: []\n"
        "    priority: 1\n"
        "    complexity: low\n"
    )
    from sam_schema.server import sam_create

    create_result = sam_create(slug="round-trip", goal="Round-trip goal", tasks_yaml=tasks_yaml, plan_dir=str(p_dir))
    assert "error" not in create_result

    # Act — read back the task through sam_read using plan_number from create result
    plan_number = create_result["plan_number"]
    read_result = sam_read(plan=f"P{plan_number}", task="T01", plan_dir=str(p_dir))

    # Assert
    assert "error" not in read_result
    assert "task" in read_result
    assert read_result["task"]["title"] == "Round-trip task"


def test_sam_create_invalid_tasks_yaml_returns_error(tmp_path: Path) -> None:
    """sam_create returns error dict when tasks_yaml lacks 'tasks' key.

    Tests: sam_create input validation.
    How: Pass YAML without 'tasks' key.
    Why: MCP tools must never raise; all errors surface as dicts.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    from sam_schema.server import sam_create

    # Act
    result = sam_create(slug="bad", goal="Bad goal", tasks_yaml="not_tasks: []", plan_dir=str(p_dir))

    # Assert
    assert "error" in result


def test_sam_create_assigns_incrementing_plan_numbers(tmp_path: Path) -> None:
    """sam_create assigns monotonically increasing plan numbers.

    Tests: sam_create plan number assignment.
    How: Create two plans; second should have plan_number = 2.
    Why: Correct numbering is required for address resolution to work.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    minimal_yaml = (
        "tasks:\n"
        "  - task: T01\n"
        "    title: Task\n"
        "    status: not-started\n"
        "    agent: a\n"
        "    dependencies: []\n"
        "    priority: 1\n"
        "    complexity: low\n"
    )
    from sam_schema.server import sam_create

    # Act
    r1 = sam_create(slug="first", goal="First", tasks_yaml=minimal_yaml, plan_dir=str(p_dir))
    r2 = sam_create(slug="second", goal="Second", tasks_yaml=minimal_yaml, plan_dir=str(p_dir))

    # Assert
    assert "error" not in r1
    assert "error" not in r2
    assert r2["plan_number"] == r1["plan_number"] + 1


# ---------------------------------------------------------------------------
# sam_update
# ---------------------------------------------------------------------------


def test_sam_update_context_sets_plan_context(tmp_path: Path) -> None:
    """sam_update with context param updates the plan-level context field.

    Tests: AC6 — sam update sets context on plan.
    How: Create a plan via sam_create, then sam_update its context; read back to verify.
    Why: context-gathering agent uses this to persist shared context to the plan.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    minimal_yaml = (
        "tasks:\n"
        "  - task: T01\n"
        "    title: Task\n"
        "    status: not-started\n"
        "    agent: a\n"
        "    dependencies: []\n"
        "    priority: 1\n"
        "    complexity: low\n"
    )
    from sam_schema.server import sam_create, sam_update

    create_result = sam_create(slug="update-ctx", goal="Goal", tasks_yaml=minimal_yaml, plan_dir=str(p_dir))
    assert "error" not in create_result
    plan_number = create_result["plan_number"]

    # Act
    update_result = sam_update(address=f"P{plan_number}", plan_dir=str(p_dir), context="Shared context narrative.")

    # Assert
    assert "error" not in update_result
    assert update_result.get("updated") is True

    # Verify via sam_read that context is persisted
    read_result = sam_read(plan=f"P{plan_number}", task="T01", plan_dir=str(p_dir))
    assert "error" not in read_result
    assert read_result.get("plan-context") == "Shared context narrative."


def test_sam_update_append_section_adds_to_task_body(tmp_path: Path) -> None:
    """sam_update with append_section appends a markdown section to the task body.

    Tests: sam_update append-section functionality.
    How: Create plan, call sam_update with append_section + section_content; read file to verify.
    Why: context-gathering agent appends Context Manifest via this path.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    minimal_yaml = (
        "tasks:\n"
        "  - task: T01\n"
        "    title: Task\n"
        "    status: not-started\n"
        "    agent: a\n"
        "    dependencies: []\n"
        "    priority: 1\n"
        "    complexity: low\n"
    )
    from sam_schema.server import sam_create, sam_update

    create_result = sam_create(slug="append-sec", goal="Goal", tasks_yaml=minimal_yaml, plan_dir=str(p_dir))
    assert "error" not in create_result
    plan_number = create_result["plan_number"]
    plan_path = create_result["path"]

    # Act
    update_result = sam_update(
        address=f"P{plan_number}/T01",
        plan_dir=str(p_dir),
        append_section="Divergence Notes",
        section_content="No divergence observed.",
    )

    # Assert
    assert "error" not in update_result
    assert update_result.get("updated") is True

    # Verify by reading the raw file — the section should be appended to task body
    from pathlib import Path as _Path

    raw = _Path(plan_path).read_text(encoding="utf-8")
    assert "Divergence Notes" in raw
    assert "No divergence observed." in raw


def test_sam_update_invalid_address_returns_error(tmp_path: Path) -> None:
    """sam_update with non-existent plan address returns error dict.

    Tests: sam_update error handling.
    How: Update non-existent plan P99.
    Why: MCP tools must never raise exceptions.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    from sam_schema.server import sam_update

    # Act
    result = sam_update(address="P99", plan_dir=str(p_dir), context="test")

    # Assert
    assert "error" in result


# ---------------------------------------------------------------------------
# sam_claim
# ---------------------------------------------------------------------------


def test_sam_claim_not_started_task_returns_claimed_true(tmp_path: Path) -> None:
    """sam_claim transitions a not-started task to in-progress and returns claimed=true.

    Tests: sam_claim happy path (AC per T05).
    How: Create a plan with a not-started task; call sam_claim.
    Why: start-task skill uses sam_claim as the sole task-claiming mechanism.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    minimal_yaml = (
        "tasks:\n"
        "  - task: T01\n"
        "    title: Task\n"
        "    status: not-started\n"
        "    agent: a\n"
        "    dependencies: []\n"
        "    priority: 1\n"
        "    complexity: low\n"
    )
    from sam_schema.server import sam_claim, sam_create

    create_result = sam_create(slug="claim-test", goal="Goal", tasks_yaml=minimal_yaml, plan_dir=str(p_dir))
    assert "error" not in create_result
    plan_number = create_result["plan_number"]

    # Act
    result = sam_claim(plan=f"P{plan_number}", task="T01", plan_dir=str(p_dir))

    # Assert
    assert result.get("claimed") is True
    assert result.get("task_id") == "T01"
    assert "started" in result


def test_sam_claim_already_claimed_returns_claimed_false(tmp_path: Path) -> None:
    """sam_claim on an already in-progress task returns claimed=false (not an exception).

    Tests: sam_claim double-claim guard.
    How: Claim a task twice; second call returns claimed=false with error message.
    Why: Prevents duplicate agent dispatch in the implement-feature loop.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    minimal_yaml = (
        "tasks:\n"
        "  - task: T01\n"
        "    title: Task\n"
        "    status: not-started\n"
        "    agent: a\n"
        "    dependencies: []\n"
        "    priority: 1\n"
        "    complexity: low\n"
    )
    from sam_schema.server import sam_claim, sam_create

    create_result = sam_create(slug="double-claim", goal="Goal", tasks_yaml=minimal_yaml, plan_dir=str(p_dir))
    assert "error" not in create_result
    plan_number = create_result["plan_number"]

    first = sam_claim(plan=f"P{plan_number}", task="T01", plan_dir=str(p_dir))
    assert first.get("claimed") is True

    # Act — second claim
    second = sam_claim(plan=f"P{plan_number}", task="T01", plan_dir=str(p_dir))

    # Assert
    assert second.get("claimed") is False
    assert "error" in second


def test_sam_claim_missing_task_returns_claimed_false(tmp_path: Path) -> None:
    """sam_claim with a non-existent task ID returns claimed=false.

    Tests: sam_claim error handling for unknown task ID.
    How: Call sam_claim for T99 which does not exist in the plan.
    Why: MCP tools return error dicts, never raise exceptions.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    minimal_yaml = (
        "tasks:\n"
        "  - task: T01\n"
        "    title: Task\n"
        "    status: not-started\n"
        "    agent: a\n"
        "    dependencies: []\n"
        "    priority: 1\n"
        "    complexity: low\n"
    )
    from sam_schema.server import sam_claim, sam_create

    create_result = sam_create(slug="missing-task", goal="Goal", tasks_yaml=minimal_yaml, plan_dir=str(p_dir))
    assert "error" not in create_result
    plan_number = create_result["plan_number"]

    # Act
    result = sam_claim(plan=f"P{plan_number}", task="T99", plan_dir=str(p_dir))

    # Assert
    assert result.get("claimed") is False
    assert "error" in result


def test_sam_claim_invalid_plan_returns_error(tmp_path: Path) -> None:
    """sam_claim with non-existent plan address returns error dict.

    Tests: sam_claim address resolution error path.
    How: Call sam_claim on empty plan dir.
    Why: Ensures clean error dict rather than exception propagation.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    from sam_schema.server import sam_claim

    # Act
    result = sam_claim(plan="P99", task="T01", plan_dir=str(p_dir))

    # Assert — resolution failure hits the broad except block, not claimed=false
    assert "error" in result
