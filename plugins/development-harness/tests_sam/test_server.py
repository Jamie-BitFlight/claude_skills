"""Tests for sam_schema.server — MCP tool functions.

Tests: sam_task and sam_plan (new consolidated tools).
How: Write real plan files to tmp_path, create a plan directory with
     tasks-{N}-{slug}.yaml naming so resolve_plan_address can find them,
     then call each MCP tool function directly and assert on returned dicts.
Why: server.py has zero test coverage; the tools are the primary interface
     used by Claude Code agents to query and mutate SAM plans.
"""
# T07: sam_read/sam_state/sam_ready/sam_status/sam_create/sam_update/sam_claim replaced
# with sam_task/sam_plan consolidated tools.

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sam_schema.core.action_models import (
    ClaimTaskConfig,
    CreatePlanConfig,
    ReadPlanConfig,
    ReadTaskConfig,
    ReadyPlanConfig,
    StateTaskConfig,
    StatusPlanConfig,
    TaskDefinition,
    UpdatePlanConfig,
    UpdateTaskConfig,
)
from sam_schema.core.exceptions import PlanNotFoundError, TaskNotFoundError, TaskValidationError
from sam_schema.core.models import Complexity, Plan, Priority, Task, TaskStatus
from sam_schema.server import sam_plan, sam_task
from sam_schema.writers.yaml_writer import write_plan

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers (shared — see conftest.py)
# ---------------------------------------------------------------------------

from tests_sam.conftest import make_task

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
# sam_task — read action (replaces sam_read with task)
# ---------------------------------------------------------------------------


def test_sam_read_existing_task_returns_task_fields(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_task(read) returns task fields dict for an existing task.

    Tests: sam_task read happy path.
    How: Address 'P1', task 'T1' on a plan dir with tasks-1-test-feature.yaml.
    Why: sam_task read is the primary read tool used by agents to inspect task state.
    """
    # Arrange — plan_dir fixture provides tasks-1-test-feature.yaml

    # Act
    result = sam_task(plan="P1", task="T1", config=ReadTaskConfig(), plan_dir=plan_dir_str)

    # Assert — returns TaskAssignment; task fields are under "task" key.
    assert "error" not in result
    assert "task" in result
    assert result["task"]["id"] == "T1"
    assert result["task"]["status"] == "complete"


def test_sam_read_returns_dict_with_all_required_fields(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_task(read) result contains nested task with 'id', 'title', and 'status' keys.

    Tests: Return structure of sam_task read TaskAssignment shape.
    How: Call sam_task read for T2 and check task key presence.
    Why: Agents rely on these keys being present to make routing decisions.
    """
    # Act
    result = sam_task(plan="P1", task="T2", config=ReadTaskConfig(), plan_dir=plan_dir_str)

    # Assert — task fields are nested under "task" in the TaskAssignment shape.
    assert "error" not in result
    assert "task" in result
    assert "id" in result["task"]
    assert "title" in result["task"]
    assert "status" in result["task"]


def test_sam_read_missing_task_returns_error_dict(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_task(read) raises TaskNotFoundError for a task ID that does not exist.

    Tests: sam_task read error handling for missing task.
    How: Request task 'T99' which is not in the plan.
    Why: Exceptions propagate from the tool function; FastMCP converts them to
         isError=true MCP responses. Direct callers must handle TaskNotFoundError.
    """
    # Act / Assert
    with pytest.raises(TaskNotFoundError, match="T99"):
        sam_task(plan="P1", task="T99", config=ReadTaskConfig(), plan_dir=plan_dir_str)


def test_sam_read_invalid_plan_address_returns_error_dict(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_task(read) raises PlanNotFoundError for an unresolvable plan address.

    Tests: sam_task read error handling for invalid plan address.
    How: Request plan 'P999' which has no matching file in the directory.
    Why: Exceptions propagate from the tool function; direct callers must handle
         PlanNotFoundError. MCP clients receive ToolError via FastMCP conversion.
    """
    # Act / Assert
    with pytest.raises(PlanNotFoundError):
        sam_task(plan="P999", task="T1", config=ReadTaskConfig(), plan_dir=plan_dir_str)


def test_sam_read_nonexistent_plan_dir_returns_error_dict(tmp_path: Path) -> None:
    """sam_task(read) raises PlanNotFoundError when plan_dir does not exist.

    Tests: sam_task read error handling for missing plan directory.
    How: Pass a path that does not exist.
    Why: The backend converts FileNotFoundError to PlanNotFoundError. Direct
         callers must handle it; MCP clients receive ToolError.
    """
    # Act / Assert
    with pytest.raises(PlanNotFoundError):
        sam_task(plan="P1", task="T1", config=ReadTaskConfig(), plan_dir=str(tmp_path / "missing"))


# ---------------------------------------------------------------------------
# sam_task — state action (replaces sam_state)
# ---------------------------------------------------------------------------


def test_sam_state_updates_task_status(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_task(state) writes new status and returns updated task.

    Tests: sam_task state happy path for status update.
    How: Transition T2 from not-started to in-progress.
    Why: sam_task state is the mutation tool agents use to advance task lifecycle.
    """
    # Act
    result = sam_task(plan="P1", task="T2", config=StateTaskConfig(status="in-progress"), plan_dir=plan_dir_str)

    # Assert
    assert "error" not in result
    assert result["id"] == "T2"
    assert result["status"] == "in-progress"


def test_sam_state_accepts_all_valid_status_values(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_task(state) accepts every value from the TaskStatus enum.

    Tests: sam_task state with each canonical status string.
    How: Cycle through valid statuses on T2.
    Why: Agents use all status values during the task lifecycle.
    """
    for status_str in ("in-progress", "blocked", "complete", "deferred", "skipped", "failed", "not-started"):
        result = sam_task(plan="P1", task="T2", config=StateTaskConfig(status=status_str), plan_dir=plan_dir_str)
        assert "error" not in result, f"Unexpected error for status '{status_str}': {result}"
        assert result["status"] == status_str


def test_sam_state_failed_auto_skips_transitive_downstream(tmp_path: Path) -> None:
    """sam_task(state=failed) auto-skips transitive downstream dependencies."""
    # Arrange
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    plan = Plan(
        feature="failed-cascade",
        version="1.0",
        tasks=[
            make_task("T1", status=TaskStatus.IN_PROGRESS),
            make_task("T2", dependencies=["T1"]),
            make_task("T3", dependencies=["T2"]),
        ],
    )
    write_plan(plan, plan_dir / "tasks-1-failed-cascade.yaml", force_single=True)

    # Act
    result = sam_task(plan="P1", task="T1", config=StateTaskConfig(status="failed"), plan_dir=str(plan_dir))
    t2 = sam_task(plan="P1", task="T2", config=ReadTaskConfig(), plan_dir=str(plan_dir))
    t3 = sam_task(plan="P1", task="T3", config=ReadTaskConfig(), plan_dir=str(plan_dir))
    ready = sam_plan(config=ReadyPlanConfig(), plan="P1", plan_dir=str(plan_dir))

    # Assert
    assert result["status"] == "failed"
    assert result["skipped_downstream"] == ["T2", "T3"]
    assert t2["task"]["status"] == "skipped"
    assert t3["task"]["status"] == "skipped"
    assert "skipped: upstream T1 failed" in (t2["task"].get("reason") or "")
    assert "skipped: upstream T1 failed" in (t3["task"].get("reason") or "")
    assert ready["count"] == 0


def test_sam_state_invalid_status_returns_error_dict(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_task(state) raises TaskValidationError for an unrecognized status string.

    Tests: sam_task state error handling for invalid status values.
    How: Pass 'typo-status' which is not in TaskStatus.
    Why: Invalid status raises TaskValidationError. FastMCP converts it to
         isError=true; direct callers must handle it.
    """
    # Act / Assert
    with pytest.raises(TaskValidationError):
        sam_task(plan="P1", task="T2", config=StateTaskConfig(status="typo-status"), plan_dir=plan_dir_str)


def test_sam_state_missing_task_returns_error_dict(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_task(state) raises TaskNotFoundError when the task ID is not found.

    Tests: sam_task state error handling for missing task.
    How: Attempt to update status on 'T99' which does not exist.
    Why: Exceptions propagate from the tool function. Direct callers must handle
         TaskNotFoundError; MCP clients receive ToolError.
    """
    # Act / Assert
    with pytest.raises(TaskNotFoundError, match="T99"):
        sam_task(plan="P1", task="T99", config=StateTaskConfig(status="complete"), plan_dir=plan_dir_str)


def test_sam_state_invalid_plan_address_returns_error_dict(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_task(state) raises PlanNotFoundError for an unresolvable plan address.

    Tests: sam_task state error handling for invalid plan address.
    How: Address 'P999' does not match any file in the plan directory.
    Why: Exceptions propagate from the tool function. Direct callers must handle
         PlanNotFoundError; MCP clients receive ToolError.
    """
    # Act / Assert
    with pytest.raises(PlanNotFoundError):
        sam_task(plan="P999", task="T1", config=StateTaskConfig(status="complete"), plan_dir=plan_dir_str)


# ---------------------------------------------------------------------------
# sam_plan — ready action (replaces sam_ready)
# ---------------------------------------------------------------------------


def test_sam_ready_returns_ready_tasks_list(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_plan(ready) returns tasks whose dependencies are all complete.

    Tests: sam_plan ready happy path.
    How: T1 is complete, T2 depends on T1 — T2 is the only ready task.
    Why: sam_plan ready is the tool agents poll to find their next task to execute.
    """
    # Act
    result = sam_plan(config=ReadyPlanConfig(), plan="P1", plan_dir=plan_dir_str)

    # Assert
    assert "error" not in result
    assert "ready_tasks" in result
    assert "count" in result
    assert result["count"] == 1
    assert result["ready_tasks"][0]["id"] == "T2"


def test_sam_ready_count_matches_ready_tasks_length(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_plan(ready) 'count' field matches len(ready_tasks).

    Tests: sam_plan ready return value consistency.
    How: Check count == len(ready_tasks).
    Why: Callers may use count for quick checks before iterating the list.
    """
    # Act
    result = sam_plan(config=ReadyPlanConfig(), plan="P1", plan_dir=plan_dir_str)

    # Assert
    assert result["count"] == len(result["ready_tasks"])


def test_sam_ready_invalid_plan_address_returns_error_dict(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_plan(ready) raises PlanNotFoundError for an unresolvable plan address.

    Tests: sam_plan ready error handling.
    How: Pass 'P999' which does not match any file.
    Why: Exceptions propagate from the tool function. Direct callers must handle
         PlanNotFoundError; MCP clients receive ToolError.
    """
    # Act / Assert
    with pytest.raises(PlanNotFoundError):
        sam_plan(config=ReadyPlanConfig(), plan="P999", plan_dir=plan_dir_str)


def test_sam_ready_all_complete_plan_returns_empty_list(tmp_path: Path) -> None:
    """sam_plan(ready) returns empty ready_tasks when all tasks are complete.

    Tests: sam_plan ready with no ready tasks.
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
    result = sam_plan(config=ReadyPlanConfig(), plan="P1", plan_dir=str(p_dir))

    # Assert
    assert "error" not in result
    assert result["count"] == 0
    assert result["ready_tasks"] == []


# ---------------------------------------------------------------------------
# sam_plan — status action (replaces sam_status)
# ---------------------------------------------------------------------------


def test_sam_status_returns_plan_summary(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_plan(status) returns a plan-level progress summary dict.

    Tests: sam_plan status happy path.
    How: Call sam_plan status on a two-task plan (T1 complete, T2 not-started).
    Why: sam_plan status gives agents and orchestrators an overview of plan progress.
    """
    # Act
    result = sam_plan(config=StatusPlanConfig(), plan="P1", plan_dir=plan_dir_str)

    # Assert
    assert "error" not in result
    assert result["total_tasks"] == 2
    assert "by_status" in result
    assert "ready_tasks" in result
    assert "completion_pct" in result
    assert "has_cycles" in result


def test_sam_status_completion_pct_reflects_completed_tasks(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_plan(status) completion_pct equals completed/total * 100.

    Tests: sam_plan status completion percentage calculation.
    How: T1 is complete out of 2 tasks — expected 50.0%.
    Why: Callers use completion_pct to report plan progress.
    """
    # Act
    result = sam_plan(config=StatusPlanConfig(), plan="P1", plan_dir=plan_dir_str)

    # Assert
    assert result["completion_pct"] == pytest.approx(50.0)


def test_sam_status_by_status_contains_complete_and_not_started(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_plan(status) by_status dict reflects actual task statuses.

    Tests: sam_plan status by_status aggregation.
    How: Verify complete=1, not-started=1 for the two-task fixture plan.
    Why: Agents and dashboards rely on by_status for per-state counts.
    """
    # Act
    result = sam_plan(config=StatusPlanConfig(), plan="P1", plan_dir=plan_dir_str)

    # Assert
    by_status = result["by_status"]
    assert by_status.get("complete", 0) == 1
    assert by_status.get("not-started", 0) == 1


def test_sam_status_invalid_plan_address_returns_error_dict(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_plan(status) raises PlanNotFoundError for an unresolvable plan address.

    Tests: sam_plan status error handling.
    How: Pass 'P999' which does not match any file.
    Why: Exceptions propagate from the tool function. Direct callers must handle
         PlanNotFoundError; MCP clients receive ToolError.
    """
    # Act / Assert
    with pytest.raises(PlanNotFoundError):
        sam_plan(config=StatusPlanConfig(), plan="P999", plan_dir=plan_dir_str)


def test_sam_status_has_cycles_false_for_acyclic_plan(plan_dir: Path, plan_dir_str: str) -> None:
    """sam_plan(status) has_cycles is False for an acyclic dependency graph.

    Tests: sam_plan status cycle detection reporting.
    How: The fixture plan (T1 <- T2) has no cycles.
    Why: has_cycles must be accurate so agents do not treat valid plans as broken.
    """
    # Act
    result = sam_plan(config=StatusPlanConfig(), plan="P1", plan_dir=plan_dir_str)

    # Assert
    assert result["has_cycles"] is False


def test_sam_status_has_cycles_true_for_cyclic_plan(tmp_path: Path) -> None:
    """sam_plan(status) has_cycles is True when the dependency graph contains a cycle.

    Tests: sam_plan status cycle detection with a real cyclic plan.
    How: Create T1 -> T2 -> T1 (cycle), write to tmp dir, call sam_plan status.
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
    result = sam_plan(config=StatusPlanConfig(), plan="P1", plan_dir=str(p_dir))

    # Assert
    assert "error" not in result
    assert result["has_cycles"] is True


# ---------------------------------------------------------------------------
# sam_task — read action (TaskAssignment shape, T02)
# ---------------------------------------------------------------------------


def test_sam_read_with_task_returns_task_assignment_shape(plan_dir_str: str) -> None:
    """sam_task(read) with task param returns dict with nested 'task' key (TaskAssignment)."""
    # Act
    result = sam_task(plan="P1", task="T1", config=ReadTaskConfig(), plan_dir=plan_dir_str)

    # Assert
    assert "error" not in result
    assert "task" in result
    assert result["task"]["id"] == "T1"


def test_sam_read_with_task_includes_plan_goal(tmp_path: Path) -> None:
    """sam_task(read) with task param surfaces plan_goal from the plan in TaskAssignment."""
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    tasks = [make_task("T1")]
    plan = Plan(feature="goal-feature", version="1.0", goal="Ship the goal feature", tasks=tasks)
    write_plan(plan, p_dir / "tasks-1-goal-feature.yaml", force_single=True)

    # Act
    result = sam_task(plan="P1", task="T1", config=ReadTaskConfig(), plan_dir=str(p_dir))

    # Assert
    assert "error" not in result
    assert result.get("plan-goal") == "Ship the goal feature"


def test_sam_read_with_task_includes_plan_context(tmp_path: Path) -> None:
    """sam_task(read) with task param surfaces plan_context in TaskAssignment."""
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    tasks = [make_task("T1")]
    plan = Plan(feature="ctx-feature", version="1.0", context="Shared context text here", tasks=tasks)
    write_plan(plan, p_dir / "tasks-1-ctx-feature.yaml", force_single=True)

    # Act
    result = sam_task(plan="P1", task="T1", config=ReadTaskConfig(), plan_dir=str(p_dir))

    # Assert
    assert "error" not in result
    assert result.get("plan-context") == "Shared context text here"


def test_sam_read_without_task_returns_plan_fields(plan_dir_str: str) -> None:
    """sam_plan(read) without task param returns Plan fields with no TaskAssignment wrapper."""
    # Act
    result = sam_plan(config=ReadPlanConfig(), plan="P1", plan_dir=plan_dir_str)

    # Assert
    assert "error" not in result
    assert "feature" in result
    assert "task" not in result


def test_sam_read_with_missing_task_returns_error(plan_dir_str: str) -> None:
    """sam_task(read) with a task ID not in the plan raises TaskNotFoundError."""
    # Act / Assert
    with pytest.raises(TaskNotFoundError, match="T99"):
        sam_task(plan="P1", task="T99", config=ReadTaskConfig(), plan_dir=plan_dir_str)


def test_sam_read_with_missing_plan_returns_error(tmp_path: Path) -> None:
    """sam_task(read) with a plan address not found raises PlanNotFoundError."""
    # Arrange
    empty_dir = tmp_path / "plan"
    empty_dir.mkdir()

    # Act / Assert
    with pytest.raises(PlanNotFoundError):
        sam_task(plan="P99", task="T1", config=ReadTaskConfig(), plan_dir=str(empty_dir))


# ---------------------------------------------------------------------------
# sam_plan — create action (replaces sam_create)
# ---------------------------------------------------------------------------


def test_sam_create_valid_tasks_yaml_returns_path_and_counts(tmp_path: Path) -> None:
    """sam_plan(create) with typed task list creates a plan file and returns metadata.

    Tests: sam_plan create happy path.
    How: Pass a minimal tasks list; verify returned dict has path, plan_number, task_count.
    Why: sam_plan create is the MCP entry point for swarm-task-planner to persist new plans.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    task = TaskDefinition(
        id="T01", title="First task", status="not-started", agent="test-agent", priority=1, complexity="low"
    )

    # Act
    result = sam_plan(config=CreatePlanConfig(slug="test-create", goal="Test goal", tasks=[task]), plan_dir=str(p_dir))

    import re

    # Assert
    assert "error" not in result
    assert result["task_count"] == 1
    assert re.match(r"^P[0-9a-f]{8}$", result["plan_id"]), f"Expected UUID plan_id, got: {result['plan_id']!r}"


def test_sam_create_file_is_readable_by_sam_task(tmp_path: Path) -> None:
    """sam_plan(create) round-trip: created file is readable by sam_task(read).

    Tests: AC4 round-trip (create then read produces identical data).
    How: sam_plan create then sam_task read the T01 task; compare title.
    Why: Validates write→read consistency through the full pipeline.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    task = TaskDefinition(
        id="T01", title="Round-trip task", status="not-started", agent="test-agent", priority=1, complexity="low"
    )

    create_result = sam_plan(
        config=CreatePlanConfig(slug="round-trip", goal="Round-trip goal", tasks=[task]), plan_dir=str(p_dir)
    )
    assert "error" not in create_result

    # Act — read back the task through sam_task using plan_id from create result
    plan_id = create_result["plan_id"]
    read_result = sam_task(plan=plan_id, task="T01", config=ReadTaskConfig(), plan_dir=str(p_dir))

    # Assert
    assert "error" not in read_result
    assert "task" in read_result
    assert read_result["task"]["title"] == "Round-trip task"


def test_sam_create_empty_tasks_creates_drafting_plan(tmp_path: Path) -> None:
    """sam_plan(create) with empty tasks list creates a drafting plan.

    Tests: sam_plan create with empty tasks list enters drafting state.
    How: Pass tasks=[] and verify plan_id returned; plan is in drafting state.
    Why: Drafting plans support incremental building via append_task + finalize.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()

    # Act
    result = sam_plan(config=CreatePlanConfig(slug="empty-plan", goal="Drafting goal", tasks=[]), plan_dir=str(p_dir))

    # Assert
    import re

    assert "error" not in result
    assert re.match(r"^P[0-9a-f]{8}$", result["plan_id"]), f"Expected UUID plan_id, got: {result['plan_id']!r}"
    assert result["task_count"] == 0


def test_sam_create_assigns_unique_plan_ids(tmp_path: Path) -> None:
    """sam_plan(create) assigns unique UUID-derived plan IDs for each plan.

    Tests: sam_plan create plan ID uniqueness.
    How: Create two plans; each must have a distinct UUID-format plan_id.
    Why: UUID IDs prevent collisions regardless of filesystem state.
    """
    import re

    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    minimal_task = TaskDefinition(id="T01", title="Task", status="not-started", agent="a", priority=1, complexity="low")

    # Act
    r1 = sam_plan(config=CreatePlanConfig(slug="first", goal="First", tasks=[minimal_task]), plan_dir=str(p_dir))
    r2 = sam_plan(config=CreatePlanConfig(slug="second", goal="Second", tasks=[minimal_task]), plan_dir=str(p_dir))

    # Assert
    assert "error" not in r1
    assert "error" not in r2
    assert re.match(r"^P[0-9a-f]{8}$", r1["plan_id"]), f"Expected UUID plan_id, got: {r1['plan_id']!r}"
    assert re.match(r"^P[0-9a-f]{8}$", r2["plan_id"]), f"Expected UUID plan_id, got: {r2['plan_id']!r}"
    assert r1["plan_id"] != r2["plan_id"], "Each plan must get a unique plan_id"


# ---------------------------------------------------------------------------
# sam_plan / sam_task — update actions (replaces sam_update)
# ---------------------------------------------------------------------------


def test_sam_update_context_sets_plan_context(tmp_path: Path) -> None:
    """sam_plan(update) with context param updates the plan-level context field.

    Tests: AC6 — sam update sets context on plan.
    How: Create a plan via sam_plan create, then sam_plan update its context; read back to verify.
    Why: context-gathering agent uses this to persist shared context to the plan.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    minimal_task = TaskDefinition(id="T01", title="Task", status="not-started", agent="a", priority=1, complexity="low")

    create_result = sam_plan(
        config=CreatePlanConfig(slug="update-ctx", goal="Goal", tasks=[minimal_task]), plan_dir=str(p_dir)
    )
    assert "error" not in create_result
    plan_id = create_result["plan_id"]

    # Act
    update_result = sam_plan(
        config=UpdatePlanConfig(context="Shared context narrative."), plan=plan_id, plan_dir=str(p_dir)
    )

    # Assert
    assert "error" not in update_result
    assert update_result.get("updated") is True

    # Verify via sam_task that context is persisted
    read_result = sam_task(plan=plan_id, task="T01", config=ReadTaskConfig(), plan_dir=str(p_dir))
    assert "error" not in read_result
    assert read_result.get("plan-context") == "Shared context narrative."


def test_sam_update_append_section_adds_to_task_body(tmp_path: Path) -> None:
    """sam_task(update) with append_section appends a markdown section to the task body.

    Tests: sam_task update append-section functionality.
    How: Create plan, call sam_task update with append_section + section_content; read file to verify.
    Why: context-gathering agent appends Context Manifest via this path.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    minimal_task = TaskDefinition(id="T01", title="Task", status="not-started", agent="a", priority=1, complexity="low")

    create_result = sam_plan(
        config=CreatePlanConfig(slug="append-sec", goal="Goal", tasks=[minimal_task]), plan_dir=str(p_dir)
    )
    assert "error" not in create_result
    plan_id = create_result["plan_id"]
    plan_path = p_dir / f"{plan_id}-append-sec.yaml"

    # Act
    update_result = sam_task(
        plan=plan_id,
        task="T01",
        config=UpdateTaskConfig(append_section="Divergence Notes", section_content="No divergence observed."),
        plan_dir=str(p_dir),
    )

    # Assert
    assert "error" not in update_result
    assert update_result.get("updated") is True

    # Verify by reading the raw file — the section should be appended to task body
    raw = plan_path.read_text(encoding="utf-8")
    assert "Divergence Notes" in raw
    assert "No divergence observed." in raw


def test_sam_update_invalid_address_returns_error(tmp_path: Path) -> None:
    """sam_plan(update) with non-existent plan address raises PlanNotFoundError.

    Tests: sam_plan update error handling.
    How: Update non-existent plan P99.
    Why: Exceptions propagate from the tool function. Direct callers must handle
         PlanNotFoundError; MCP clients receive ToolError.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()

    # Act / Assert
    with pytest.raises(PlanNotFoundError):
        sam_plan(config=UpdatePlanConfig(context="test"), plan="P99", plan_dir=str(p_dir))


# ---------------------------------------------------------------------------
# sam_task — claim action (replaces sam_claim)
# ---------------------------------------------------------------------------


def test_sam_claim_not_started_task_returns_claimed_true(tmp_path: Path) -> None:
    """sam_task(claim) transitions a not-started task to in-progress and returns claimed=true.

    Tests: sam_task claim happy path (AC per T05).
    How: Create a plan with a not-started task; call sam_task claim.
    Why: start-task skill uses sam_task claim as the sole task-claiming mechanism.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    minimal_task = TaskDefinition(id="T01", title="Task", status="not-started", agent="a", priority=1, complexity="low")

    create_result = sam_plan(
        config=CreatePlanConfig(slug="claim-test", goal="Goal", tasks=[minimal_task]), plan_dir=str(p_dir)
    )
    assert "error" not in create_result
    plan_id = create_result["plan_id"]

    # Act
    result = sam_task(plan=plan_id, task="T01", config=ClaimTaskConfig(), plan_dir=str(p_dir))

    # Assert
    assert result.get("claimed") is True
    assert result.get("task_id") == "T01"
    assert "started" in result


def test_sam_claim_already_claimed_returns_claimed_false(tmp_path: Path) -> None:
    """sam_task(claim) on an already in-progress task returns claimed=false (not an exception).

    Tests: sam_task claim double-claim guard.
    How: Claim a task twice; second call returns claimed=false with error message.
    Why: Prevents duplicate agent dispatch in the implement-feature loop.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    minimal_task = TaskDefinition(id="T01", title="Task", status="not-started", agent="a", priority=1, complexity="low")

    create_result = sam_plan(
        config=CreatePlanConfig(slug="double-claim", goal="Goal", tasks=[minimal_task]), plan_dir=str(p_dir)
    )
    assert "error" not in create_result
    plan_id = create_result["plan_id"]

    first = sam_task(plan=plan_id, task="T01", config=ClaimTaskConfig(), plan_dir=str(p_dir))
    assert first.get("claimed") is True

    # Act — second claim
    second = sam_task(plan=plan_id, task="T01", config=ClaimTaskConfig(), plan_dir=str(p_dir))

    # Assert
    assert second.get("claimed") is False
    assert "error" in second


def test_sam_claim_missing_task_returns_claimed_false(tmp_path: Path) -> None:
    """sam_task(claim) with a non-existent task ID raises TaskNotFoundError.

    Tests: sam_task claim error handling for unknown task ID.
    How: Call sam_task claim for T99 which does not exist in the plan.
    Why: backend.claim_task raises TaskNotFoundError when the task is absent.
         FastMCP converts it to isError=true; direct callers must handle it.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    minimal_task = TaskDefinition(id="T01", title="Task", status="not-started", agent="a", priority=1, complexity="low")

    create_result = sam_plan(
        config=CreatePlanConfig(slug="missing-task", goal="Goal", tasks=[minimal_task]), plan_dir=str(p_dir)
    )
    assert "error" not in create_result
    plan_id = create_result["plan_id"]

    # Act / Assert
    with pytest.raises(TaskNotFoundError, match="T99"):
        sam_task(plan=plan_id, task="T99", config=ClaimTaskConfig(), plan_dir=str(p_dir))


def test_sam_claim_invalid_plan_returns_error(tmp_path: Path) -> None:
    """sam_task(claim) with non-existent plan address raises PlanNotFoundError.

    Tests: sam_task claim address resolution error path.
    How: Call sam_task claim on empty plan dir.
    Why: Exceptions propagate from the tool function. Direct callers must handle
         PlanNotFoundError; MCP clients receive ToolError.
    """
    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()

    # Act / Assert
    with pytest.raises(PlanNotFoundError):
        sam_task(plan="P99", task="T01", config=ClaimTaskConfig(), plan_dir=str(p_dir))


def test_sam_create_returns_plan_ref_without_issue(tmp_path: Path) -> None:
    """sam_plan(create) without issue returns plan_ref as plain UUID-format identifier.

    Tests: plan_ref field in create response — no-issue path.
    How: Create a plan with no issue; verify plan_ref matches P[hex8] pattern.
    Why: plan_ref must be globally addressable; without issue it is the plan_id itself.
    """
    import re

    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    task = TaskDefinition(
        id="T01", title="First task", status="not-started", agent="test-agent", priority=1, complexity="low"
    )

    # Act
    result = sam_plan(config=CreatePlanConfig(slug="ref-no-issue", goal="Test goal", tasks=[task]), plan_dir=str(p_dir))

    # Assert
    assert "error" not in result
    assert re.match(r"^P[0-9a-f]{8}$", result["plan_ref"]), f"Expected UUID plan_ref, got: {result['plan_ref']!r}"


def test_sam_create_returns_plan_ref_with_issue(tmp_path: Path) -> None:
    """sam_plan(create) with issue returns plan_ref as '#<issue>,P<hex8>' composite identifier.

    Tests: plan_ref field in create response — issue-scoped path.
    How: Create a plan with issue=42; verify plan_ref is "#42,P<hex8>".
    Why: plan_ref must be globally unique when an issue is associated; UUID IDs prevent collisions.
    """
    import re

    # Arrange
    p_dir = tmp_path / "plan"
    p_dir.mkdir()
    task = TaskDefinition(
        id="T01", title="First task", status="not-started", agent="test-agent", priority=1, complexity="low"
    )

    # Act
    result = sam_plan(
        config=CreatePlanConfig(slug="ref-with-issue", goal="Test goal", tasks=[task], issue=42), plan_dir=str(p_dir)
    )

    # Assert — plan_ref includes issue number and UUID plan_id
    assert "error" not in result
    assert re.match(r"^#42,P[0-9a-f]{8}$", result["plan_ref"]), f"Expected '#42,P<hex8>', got: {result['plan_ref']!r}"


# ---------------------------------------------------------------------------
# sam_plan — append_task action (#1770)
# ---------------------------------------------------------------------------


def test_sam_append_task_routes_through_backend_append_task(tmp_path: Path) -> None:
    """sam_plan action=append_task calls backend.append_task for the given plan.

    AC #2: sam_plan(action='append_task', plan=P, task=<TaskDefinition>) must append
    a single task and return a success acknowledgment.

    Arrange: create a plan with empty tasks list; inject mock backend.
    Act: call sam_plan with action=append_task.
    Assert: backend.append_task was called exactly once with the plan_id and a
            parsed task definition.
    """
    from unittest.mock import MagicMock

    from sam_schema.core.action_models import AppendTaskConfig
    from sam_schema.core.task_config import TaskConfig, reset_task_config, set_task_config

    # Arrange
    mock_backend = MagicMock()
    mock_backend.read_plan.return_value = {
        "plan_id": "P1",
        "feature": "test-plan",
        "version": "1",
        "description": "",
        "goal": "Test goal",
        "context": "",
        "acceptance_criteria": "",
        "issue": None,
        "tasks": [],
        "source_path": None,
        "state": "drafting",
    }
    mock_backend.append_task.return_value = {"appended": True, "task_id": "T1"}
    mock_backend.create_plan.return_value = {
        "plan_id": "P1",
        "feature": "test-plan",
        "version": "1",
        "description": "",
        "goal": "Test goal",
        "context": "",
        "acceptance_criteria": "",
        "issue": None,
        "tasks": [],
        "source_path": str(tmp_path / "P1-test-plan.yaml"),
        "state": "drafting",
    }
    set_task_config(TaskConfig(backend=mock_backend))

    try:
        task_def = TaskDefinition(
            id="T1",
            title="First task",
            status="not-started",
            agent="test-agent",
            dependencies=[],
            priority=2,
            complexity="low",
        )

        # Act
        result = sam_plan(config=AppendTaskConfig(task=task_def), plan="P1")

        # Assert — backend.append_task called once
        assert "error" not in result, f"append_task returned error: {result}"
        mock_backend.append_task.assert_called_once()
        call_args = mock_backend.append_task.call_args
        plan_id_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("plan_id")
        assert plan_id_arg == "P1"
    finally:
        reset_task_config()


def test_sam_append_task_returns_success_acknowledgment(tmp_path: Path) -> None:
    """sam_plan action=append_task returns a success acknowledgment dict.

    AC #2: the response must not be an error dict; it must contain a truthy
    success indicator (e.g. 'appended': True or 'task_id': 'T1').

    Arrange: create plan via InMemoryTaskProvider; append one task.
    Act: call sam_plan(action='append_task', plan=P, task=<TaskDefinition>).
    Assert: result contains 'appended': True or 'task_id': 'T1' and no 'error' key.
    """
    from sam_schema.core.action_models import AppendTaskConfig, CreatePlanConfig
    from sam_schema.core.backends.memory import InMemoryTaskProvider
    from sam_schema.core.task_config import TaskConfig, reset_task_config, set_task_config

    backend = InMemoryTaskProvider()
    set_task_config(TaskConfig(backend=backend))

    try:
        create_result = sam_plan(config=CreatePlanConfig(slug="append-test", goal="Append goal", tasks=[]))
        plan_id = create_result["plan_id"]

        task_def = TaskDefinition(
            id="T1",
            title="First task",
            status="not-started",
            agent="test-agent",
            dependencies=[],
            priority=2,
            complexity="low",
        )

        # Act
        result = sam_plan(config=AppendTaskConfig(task=task_def), plan=plan_id)

        # Assert
        assert "error" not in result, f"Expected success but got error: {result}"
        success = result.get("appended") is True or result.get("task_id") is not None
        assert success, f"Expected success indicator in append_task response, got: {result!r}"
    finally:
        reset_task_config()


def test_sam_append_task_plan_not_found_raises(tmp_path: Path) -> None:
    """sam_plan action=append_task raises PlanNotFoundError when plan does not exist.

    AC #6: backend must raise PlanNotFoundError for unknown plan_id.
    FastMCP converts this to a ToolError (isError=true) at the MCP transport.

    Arrange: inject fresh InMemoryTaskProvider (no plans).
    Act: call sam_plan(action='append_task', plan='P99999').
    Assert: PlanNotFoundError or ToolError is raised containing 'P99999'.
    """
    from sam_schema.core.action_models import AppendTaskConfig
    from sam_schema.core.backends.memory import InMemoryTaskProvider
    from sam_schema.core.exceptions import PlanNotFoundError
    from sam_schema.core.task_config import TaskConfig, reset_task_config, set_task_config

    backend = InMemoryTaskProvider()
    set_task_config(TaskConfig(backend=backend))

    try:
        task_def = TaskDefinition(id="T1", title="Task", agent="a")

        # Act / Assert
        with pytest.raises(PlanNotFoundError, match="P99999"):
            sam_plan(config=AppendTaskConfig(task=task_def), plan="P99999")
    finally:
        reset_task_config()


def test_sam_append_task_duplicate_task_id_raises(tmp_path: Path) -> None:
    """sam_plan action=append_task raises an error when duplicate task ID is appended.

    AC #6: backend raises TaskValidationError when a duplicate task ID is appended.

    Arrange: create a plan with T1; append T1 a second time.
    Act: second append_task call.
    Assert: TaskValidationError is raised.
    """
    from sam_schema.core.action_models import AppendTaskConfig, CreatePlanConfig
    from sam_schema.core.backends.memory import InMemoryTaskProvider
    from sam_schema.core.exceptions import TaskValidationError
    from sam_schema.core.task_config import TaskConfig, reset_task_config, set_task_config

    backend = InMemoryTaskProvider()
    set_task_config(TaskConfig(backend=backend))

    try:
        create_result = sam_plan(config=CreatePlanConfig(slug="dup-task", goal="Goal", tasks=[]))
        plan_id = create_result["plan_id"]

        task_def = TaskDefinition(id="T1", title="Task", agent="a")

        # First append succeeds
        sam_plan(config=AppendTaskConfig(task=task_def), plan=plan_id)

        # Act / Assert — second append with same ID must raise TaskValidationError
        with pytest.raises(TaskValidationError):
            sam_plan(config=AppendTaskConfig(task=task_def), plan=plan_id)
    finally:
        reset_task_config()


# ---------------------------------------------------------------------------
# sam_plan — finalize action (#1770)
# ---------------------------------------------------------------------------


def test_sam_finalize_routes_through_backend_finalize_plan(tmp_path: Path) -> None:
    """sam_plan action=finalize calls backend.finalize_plan (or update_plan_fields).

    AC #14: finalize must clear the drafting state via a dedicated backend call.

    Arrange: inject mock backend.
    Act: call sam_plan(action='finalize', plan='P1').
    Assert: backend.finalize_plan (or update_plan_fields with state='ready') called once.
    """
    from unittest.mock import MagicMock

    from sam_schema.core.action_models import FinalizePlanConfig
    from sam_schema.core.task_config import TaskConfig, reset_task_config, set_task_config

    mock_backend = MagicMock()
    mock_backend.finalize_plan.return_value = {"finalized": True, "state": "ready"}
    mock_backend.update_plan_fields.return_value = {"updated": True}
    set_task_config(TaskConfig(backend=mock_backend))

    try:
        # Act
        result = sam_plan(config=FinalizePlanConfig(), plan="P1")

        # Assert — either finalize_plan OR update_plan_fields called to transition state
        assert "error" not in result, f"Expected success, got: {result!r}"
        state_transitioned = mock_backend.finalize_plan.called or mock_backend.update_plan_fields.called
        assert state_transitioned, (
            "Expected either backend.finalize_plan or backend.update_plan_fields to be called to clear drafting state"
        )
    finally:
        reset_task_config()
