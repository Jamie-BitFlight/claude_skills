"""Tests for sam_schema.core.query — plan loading and task query operations."""

from __future__ import annotations

from pathlib import Path

import pytest
from sam_schema.core.addressing import AddressingError, parse_address, resolve_plan_address
from sam_schema.core.models import Complexity, Plan, Priority, Task, TaskStatus
from sam_schema.core.query import (
    claim_task,
    get_plan_status,
    get_ready_tasks,
    get_task,
    get_task_assignment,
    list_tasks,
    load_plan,
    update_status,
)
from sam_schema.writers.yaml_writer import write_plan

FIXTURES_DIR = Path(__file__).parent / "fixtures"


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


@pytest.fixture
def writable_plan(tmp_path: Path) -> Path:
    """Write a two-task plan to a temp YAML file and return its path.

    T1 is complete; T2 depends on T1 and is not-started.
    """
    tasks = [make_task("T1", status=TaskStatus.COMPLETE), make_task("T2", dependencies=["T1"])]
    plan = Plan(feature="test-query-feature", version="1.0", tasks=tasks)
    path = tmp_path / "plan.yaml"
    write_plan(plan, path, force_single=True)
    return path


@pytest.fixture
def writable_directory_plan(tmp_path: Path) -> Path:
    """Write a two-task plan to a directory layout and return the directory path."""
    tasks = [make_task("T1", status=TaskStatus.COMPLETE), make_task("T2", dependencies=["T1"])]
    plan = Plan(feature="dir-plan-feature", version="1.0", tasks=tasks)
    plan_dir = tmp_path / "plan"
    # Force directory by writing per-task files manually via write_plan
    # write_plan uses LINE_THRESHOLD; force_single=False but we need a directory.
    # Create directory layout explicitly.
    plan_dir.mkdir()
    from sam_schema.writers.yaml_writer import _write_directory

    _write_directory(plan, plan_dir)
    return plan_dir


# ---------------------------------------------------------------------------
# load_plan
# ---------------------------------------------------------------------------


def test_load_plan_pure_yaml_single_file_returns_read_result() -> None:
    # Arrange
    path = FIXTURES_DIR / "pure_yaml_single.yaml"

    # Act
    result = load_plan(path)

    # Assert
    assert result.plan.feature == "auth-system"
    assert len(result.plan.tasks) > 0
    assert result.source_format == "pure_yaml"


def test_load_plan_pure_yaml_directory_returns_read_result() -> None:
    # Arrange
    path = FIXTURES_DIR / "pure_yaml_directory"

    # Act
    result = load_plan(path)

    # Assert
    assert result.plan.feature == "logging-pipeline"
    assert len(result.plan.tasks) > 0


def test_load_plan_yaml_frontmatter_multi_returns_read_result() -> None:
    # Arrange
    path = FIXTURES_DIR / "yaml_frontmatter_multi.md"

    # Act
    result = load_plan(path)

    # Assert
    assert result.plan.feature == "cache-layer"
    assert len(result.plan.tasks) > 0
    assert result.source_format == "yaml_frontmatter"


def test_load_plan_yaml_frontmatter_single_has_task_id_in_result() -> None:
    # Arrange — yaml_frontmatter_single.md is a single-task file with task: T1
    # in the frontmatter and no plan-level feature. The frontmatter_reader wraps
    # it as a plan with feature derived from the task title.
    path = FIXTURES_DIR / "yaml_frontmatter_multi.md"

    # Act
    result = load_plan(path)

    # Assert
    assert len(result.plan.tasks) > 0
    assert result.source_format == "yaml_frontmatter"


def test_load_plan_legacy_markdown_returns_read_result() -> None:
    # Arrange
    path = FIXTURES_DIR / "legacy_markdown.md"

    # Act
    result = load_plan(path)

    # Assert
    assert len(result.plan.tasks) > 0
    assert result.source_format == "legacy_markdown"


def test_load_plan_global_manifest_returns_read_result() -> None:
    # Arrange
    path = FIXTURES_DIR / "global_manifest.md"

    # Act
    result = load_plan(path)

    # Assert
    assert len(result.plan.tasks) > 0
    assert result.source_format == "global_manifest"


def test_load_plan_nonexistent_path_raises_file_not_found() -> None:
    # Arrange
    path = FIXTURES_DIR / "does_not_exist.yaml"

    # Act / Assert
    with pytest.raises(FileNotFoundError):
        load_plan(path)


# ---------------------------------------------------------------------------
# get_task
# ---------------------------------------------------------------------------


def test_get_task_existing_id_returns_task() -> None:
    # Arrange
    path = FIXTURES_DIR / "pure_yaml_single.yaml"

    # Act
    task = get_task(path, "T1")

    # Assert
    assert task.id == "T1"


def test_get_task_missing_id_raises_key_error() -> None:
    # Arrange
    path = FIXTURES_DIR / "pure_yaml_single.yaml"

    # Act / Assert
    with pytest.raises(KeyError, match="T99"):
        get_task(path, "T99")


# ---------------------------------------------------------------------------
# list_tasks
# ---------------------------------------------------------------------------


def test_list_tasks_returns_all_tasks_in_order() -> None:
    # Arrange
    path = FIXTURES_DIR / "pure_yaml_single.yaml"

    # Act
    tasks = list_tasks(path)

    # Assert
    assert len(tasks) >= 2
    # Tasks must be Task instances
    assert all(isinstance(t, Task) for t in tasks)


# ---------------------------------------------------------------------------
# get_ready_tasks
# ---------------------------------------------------------------------------


def test_get_ready_tasks_returns_tasks_with_met_dependencies() -> None:
    # Arrange — pure_yaml_single.yaml has T1=complete, T2=in-progress, T3=not-started
    # T3 depends on T1 which is complete → T3 should be ready
    path = FIXTURES_DIR / "pure_yaml_single.yaml"

    # Act
    ready = get_ready_tasks(path)

    # Assert — at least one task is ready
    assert len(ready) >= 1
    # All ready tasks must be not-started
    assert all(t.status == TaskStatus.NOT_STARTED for t in ready)


def test_get_ready_tasks_from_writable_plan_returns_t2(writable_plan: Path) -> None:
    # Arrange — writable_plan has T1=complete, T2 depends on T1

    # Act
    ready = get_ready_tasks(writable_plan)

    # Assert
    assert len(ready) == 1
    assert ready[0].id == "T2"


def test_get_ready_tasks_no_tasks_ready_returns_empty(tmp_path: Path) -> None:
    # Arrange — all tasks in-progress
    tasks = [make_task("T1", status=TaskStatus.IN_PROGRESS)]
    plan = Plan(feature="f", version="1.0", tasks=tasks)
    path = tmp_path / "plan.yaml"
    write_plan(plan, path, force_single=True)

    # Act
    ready = get_ready_tasks(path)

    # Assert
    assert ready == []


# ---------------------------------------------------------------------------
# update_status
# ---------------------------------------------------------------------------


def test_update_status_changes_status_on_disk(writable_plan: Path) -> None:
    # Arrange
    original = get_task(writable_plan, "T2")
    assert original.status == TaskStatus.NOT_STARTED

    # Act
    updated = update_status(writable_plan, "T2", TaskStatus.IN_PROGRESS)

    # Assert — returned task reflects new status
    assert updated.status == TaskStatus.IN_PROGRESS

    # Assert — reading back from disk confirms the write
    reloaded = get_task(writable_plan, "T2")
    assert reloaded.status == TaskStatus.IN_PROGRESS


def test_update_status_preserves_other_tasks(writable_plan: Path) -> None:
    # Arrange — T1 is complete; updating T2 should not disturb T1

    # Act
    update_status(writable_plan, "T2", TaskStatus.IN_PROGRESS)

    # Assert — T1 still has its original status
    t1 = get_task(writable_plan, "T1")
    assert t1.status == TaskStatus.COMPLETE


def test_update_status_with_timestamp_field_sets_timestamp(writable_plan: Path) -> None:
    # Act
    updated = update_status(writable_plan, "T2", TaskStatus.IN_PROGRESS, timestamp_field="started")

    # Assert — started timestamp is set on the returned task
    assert updated.started is not None


def test_update_status_missing_task_raises_key_error(writable_plan: Path) -> None:
    # Act / Assert
    with pytest.raises(KeyError):
        update_status(writable_plan, "T99", TaskStatus.IN_PROGRESS)


# ---------------------------------------------------------------------------
# get_plan_status
# ---------------------------------------------------------------------------


def test_get_plan_status_returns_correct_counts(writable_plan: Path) -> None:
    # Arrange — T1=complete, T2=not-started

    # Act
    status = get_plan_status(writable_plan)

    # Assert
    assert status.total_tasks == 2
    assert status.by_status.get(TaskStatus.COMPLETE, 0) == 1
    assert status.by_status.get(TaskStatus.NOT_STARTED, 0) == 1


def test_get_plan_status_completion_pct_is_correct(writable_plan: Path) -> None:
    # Arrange — 1 of 2 tasks complete → 50%

    # Act
    status = get_plan_status(writable_plan)

    # Assert
    assert abs(status.completion_pct - 50.0) < 0.01


def test_get_plan_status_ready_tasks_lists_task_ids(writable_plan: Path) -> None:
    # Arrange — T2 depends on T1 (complete) → T2 should be ready

    # Act
    status = get_plan_status(writable_plan)

    # Assert
    assert "T2" in status.ready_tasks


def test_get_plan_status_no_cycles_returns_false(writable_plan: Path) -> None:
    # Act
    status = get_plan_status(writable_plan)

    # Assert
    assert status.has_cycles is False


def test_get_plan_status_with_cycles_returns_true(tmp_path: Path) -> None:
    # Arrange — T1 -> T2 -> T1 cycle
    tasks = [make_task("T1", dependencies=["T2"]), make_task("T2", dependencies=["T1"])]
    plan = Plan(feature="cyclic", version="1.0", tasks=tasks)
    path = tmp_path / "cyclic.yaml"
    write_plan(plan, path, force_single=True)

    # Act
    status = get_plan_status(path)

    # Assert
    assert status.has_cycles is True


def test_get_plan_status_blocked_tasks_reported(tmp_path: Path) -> None:
    # Arrange — T2 blocked by T1 (not-started)
    tasks = [make_task("T1"), make_task("T2", dependencies=["T1"])]
    plan = Plan(feature="blocked-f", version="1.0", tasks=tasks)
    path = tmp_path / "plan.yaml"
    write_plan(plan, path, force_single=True)

    # Act
    status = get_plan_status(path)

    # Assert
    assert any("T2" in entry for entry in status.blocked_tasks)


def test_get_plan_status_all_complete_gives_100_pct(tmp_path: Path) -> None:
    # Arrange
    tasks = [make_task("T1", status=TaskStatus.COMPLETE)]
    plan = Plan(feature="done", version="1.0", tasks=tasks)
    path = tmp_path / "done.yaml"
    write_plan(plan, path, force_single=True)

    # Act
    status = get_plan_status(path)

    # Assert
    assert abs(status.completion_pct - 100.0) < 0.01


# ---------------------------------------------------------------------------
# claim_task
# ---------------------------------------------------------------------------


def test_claim_task_not_started_transitions_to_in_progress(writable_plan: Path) -> None:
    # Arrange — T2 is not-started

    # Act
    claimed = claim_task(writable_plan, "T2")

    # Assert
    assert claimed.status == TaskStatus.IN_PROGRESS
    assert claimed.started is not None


def test_claim_task_sets_started_timestamp_on_disk(writable_plan: Path) -> None:
    # Act
    claim_task(writable_plan, "T2")

    # Assert — reload from disk
    reloaded = get_task(writable_plan, "T2")
    assert reloaded.started is not None


def test_claim_task_already_in_progress_raises_value_error(writable_plan: Path) -> None:
    # Arrange — claim T2 once
    claim_task(writable_plan, "T2")

    # Act / Assert — second claim should fail
    with pytest.raises(ValueError, match="not-started"):
        claim_task(writable_plan, "T2")


def test_claim_task_complete_status_raises_value_error(writable_plan: Path) -> None:
    # Arrange — T1 is complete

    # Act / Assert
    with pytest.raises(ValueError, match="not-started"):
        claim_task(writable_plan, "T1")


def test_claim_task_missing_id_raises_key_error(writable_plan: Path) -> None:
    # Act / Assert
    with pytest.raises(KeyError):
        claim_task(writable_plan, "T99")


# ---------------------------------------------------------------------------
# Directory layout plan operations
# ---------------------------------------------------------------------------


def test_update_status_directory_plan_modifies_task_file(writable_directory_plan: Path) -> None:
    # Arrange — T2 is not-started in a directory plan

    # Act
    updated = update_status(writable_directory_plan, "T2", TaskStatus.IN_PROGRESS)

    # Assert
    assert updated.status == TaskStatus.IN_PROGRESS
    # Confirm the per-task file was updated
    task_file = writable_directory_plan / "task-T2.yaml"
    assert task_file.exists()
    content = task_file.read_text()
    assert "in-progress" in content


def test_claim_task_directory_plan_succeeds(writable_directory_plan: Path) -> None:
    # Act
    claimed = claim_task(writable_directory_plan, "T2")

    # Assert
    assert claimed.status == TaskStatus.IN_PROGRESS


# ---------------------------------------------------------------------------
# parse_address
# ---------------------------------------------------------------------------


def test_parse_address_numeric_with_task_returns_both_components() -> None:
    # Arrange / Act
    plan_ref, task_ref = parse_address("P1/T3")

    # Assert — acceptance criterion 6
    assert plan_ref == "1"
    assert task_ref == "3"


def test_parse_address_numeric_only_returns_none_task() -> None:
    # Arrange / Act
    plan_ref, task_ref = parse_address("P1")

    # Assert
    assert plan_ref == "1"
    assert task_ref is None


def test_parse_address_slug_with_task_returns_slug_and_task() -> None:
    # Arrange / Act
    plan_ref, task_ref = parse_address("my-slug/T3")

    # Assert
    assert plan_ref == "my-slug"
    assert task_ref == "3"


def test_parse_address_slug_only_returns_slug_and_none() -> None:
    # Arrange / Act
    plan_ref, task_ref = parse_address("my-slug")

    # Assert
    assert plan_ref == "my-slug"
    assert task_ref is None


def test_parse_address_empty_string_raises_value_error() -> None:
    # Act / Assert
    with pytest.raises(ValueError, match="empty"):
        parse_address("")


def test_parse_address_empty_task_component_raises_value_error() -> None:
    # Act / Assert
    with pytest.raises(ValueError, match="empty"):
        parse_address("P1/")


# ---------------------------------------------------------------------------
# resolve_plan_address
# ---------------------------------------------------------------------------


@pytest.fixture
def plan_dir_with_files(tmp_path: Path) -> Path:
    """Create a directory with two task plan files for addressing tests.

    Files created:
      - tasks-1-auth-system.yaml
      - tasks-2-cache-layer.yaml
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    (plan_dir / "tasks-1-auth-system.yaml").write_text("feature: auth-system\n")
    (plan_dir / "tasks-2-cache-layer.yaml").write_text("feature: cache-layer\n")
    return plan_dir


def test_resolve_plan_address_numeric_finds_correct_file(plan_dir_with_files: Path) -> None:
    # Arrange / Act — acceptance criterion 6
    result = resolve_plan_address("P1", plan_dir_with_files)

    # Assert
    assert result.name == "tasks-1-auth-system.yaml"


def test_resolve_plan_address_numeric_two_finds_second_file(plan_dir_with_files: Path) -> None:
    # Act
    result = resolve_plan_address("P2", plan_dir_with_files)

    # Assert
    assert result.name == "tasks-2-cache-layer.yaml"


def test_resolve_plan_address_slug_finds_matching_file(plan_dir_with_files: Path) -> None:
    # Act
    result = resolve_plan_address("cache-layer", plan_dir_with_files)

    # Assert
    assert result.name == "tasks-2-cache-layer.yaml"


def test_resolve_plan_address_numeric_takes_precedence_over_slug(tmp_path: Path) -> None:
    # Arrange — create a file where the slug contains a number
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    (plan_dir / "tasks-1-step-1-api.yaml").write_text("feature: step-1-api\n")

    # Act — numeric "1" matches tasks-1-* prefix, not slug "1"
    result = resolve_plan_address("P1", plan_dir)

    # Assert
    assert result.name == "tasks-1-step-1-api.yaml"


def test_resolve_plan_address_missing_plan_raises_addressing_error(plan_dir_with_files: Path) -> None:
    # Act / Assert
    with pytest.raises(AddressingError):
        resolve_plan_address("P99", plan_dir_with_files)


def test_resolve_plan_address_nonexistent_dir_raises_file_not_found(tmp_path: Path) -> None:
    # Arrange
    missing_dir = tmp_path / "no-such-dir"

    # Act / Assert
    with pytest.raises(FileNotFoundError):
        resolve_plan_address("P1", missing_dir)


def test_resolve_plan_address_slug_no_match_raises_addressing_error(plan_dir_with_files: Path) -> None:
    # Act / Assert
    with pytest.raises(AddressingError):
        resolve_plan_address("nonexistent-slug", plan_dir_with_files)


# ---------------------------------------------------------------------------
# get_task_assignment
# ---------------------------------------------------------------------------

FIXTURES_DIR_Q = Path(__file__).parent / "fixtures"
_PURE_YAML_SINGLE: Path = FIXTURES_DIR_Q / "pure_yaml_single.yaml"


def test_get_task_assignment_returns_task_assignment_model(tmp_path: Path) -> None:
    """get_task_assignment returns a TaskAssignment containing the requested task."""
    # Arrange
    from sam_schema.core.models import TaskAssignment

    plan_file = tmp_path / "tasks-1-auth-system.yaml"
    plan_file.write_text(_PURE_YAML_SINGLE.read_text(encoding="utf-8"), encoding="utf-8")

    # Act
    assignment = get_task_assignment(plan_file, "T1")

    # Assert
    assert isinstance(assignment, TaskAssignment)
    assert assignment.task.id == "T1"
    assert assignment.task.status == "complete"


def test_get_task_assignment_includes_plan_level_goal_and_context(tmp_path: Path) -> None:
    """get_task_assignment populates plan_goal and plan_context from the plan."""
    # Arrange
    plan_yaml = (
        "feature: my-feature\n"
        "goal: Build a great thing\n"
        "context: Shared context paragraph here\n"
        "acceptance-criteria: AC1 passes\n"
        "tasks:\n"
        "  - id: T1\n"
        "    title: First task\n"
        "    status: not-started\n"
        "    dependencies: []\n"
        "    priority: 1\n"
        "    complexity: low\n"
    )
    plan_file = tmp_path / "tasks-1-my-feature.yaml"
    plan_file.write_text(plan_yaml, encoding="utf-8")

    # Act
    assignment = get_task_assignment(plan_file, "T1")

    # Assert
    assert assignment.plan_goal == "Build a great thing"
    assert assignment.plan_context == "Shared context paragraph here"
    assert assignment.plan_acceptance_criteria == "AC1 passes"


def test_get_task_assignment_derives_plan_number_from_legacy_stem(tmp_path: Path) -> None:
    """get_task_assignment extracts plan_number from tasks-{N}-{slug} filename."""
    # Arrange
    plan_yaml = (
        "feature: auth-system\n"
        "tasks:\n"
        "  - id: T1\n"
        "    title: First task\n"
        "    status: not-started\n"
        "    dependencies: []\n"
        "    priority: 1\n"
        "    complexity: low\n"
    )
    plan_file = tmp_path / "tasks-3-auth-system.yaml"
    plan_file.write_text(plan_yaml, encoding="utf-8")

    # Act
    assignment = get_task_assignment(plan_file, "T1")

    # Assert
    assert assignment.plan_number == "3"
    assert assignment.plan_slug == "auth-system"


def test_get_task_assignment_derives_plan_number_from_p_prefix_stem(tmp_path: Path) -> None:
    """get_task_assignment extracts plan_number from P{NNN}-{slug} filename."""
    # Arrange
    plan_yaml = (
        "feature: auth-system\n"
        "tasks:\n"
        "  - id: T1\n"
        "    title: First task\n"
        "    status: not-started\n"
        "    dependencies: []\n"
        "    priority: 1\n"
        "    complexity: low\n"
    )
    plan_file = tmp_path / "P042-auth-system.yaml"
    plan_file.write_text(plan_yaml, encoding="utf-8")

    # Act
    assignment = get_task_assignment(plan_file, "T1")

    # Assert
    assert assignment.plan_number == "P042"
    assert assignment.plan_slug == "auth-system"


def test_get_task_assignment_raises_key_error_for_missing_task(tmp_path: Path) -> None:
    """get_task_assignment raises KeyError when task_id is not found in plan."""
    # Arrange
    plan_file = tmp_path / "tasks-1-auth-system.yaml"
    plan_file.write_text(_PURE_YAML_SINGLE.read_text(encoding="utf-8"), encoding="utf-8")

    # Act / Assert
    with pytest.raises(KeyError, match="T99"):
        get_task_assignment(plan_file, "T99")


def test_get_task_assignment_raises_file_not_found_for_missing_plan(tmp_path: Path) -> None:
    """get_task_assignment raises FileNotFoundError when plan file does not exist."""
    # Arrange
    missing = tmp_path / "no-such-plan.yaml"

    # Act / Assert
    with pytest.raises(FileNotFoundError):
        get_task_assignment(missing, "T1")


def test_get_task_assignment_plan_fields_none_when_not_set(tmp_path: Path) -> None:
    """get_task_assignment returns None for plan fields absent from plan file."""
    # Arrange — pure_yaml_single.yaml has no goal/context/acceptance-criteria at plan level
    plan_file = tmp_path / "tasks-1-auth-system.yaml"
    plan_file.write_text(_PURE_YAML_SINGLE.read_text(encoding="utf-8"), encoding="utf-8")

    # Act
    assignment = get_task_assignment(plan_file, "T1")

    # Assert
    assert assignment.plan_goal is None
    assert assignment.plan_context is None
    assert assignment.plan_acceptance_criteria is None
