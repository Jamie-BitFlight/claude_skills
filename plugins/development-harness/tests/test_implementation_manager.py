"""Behavioral tests for implementation_manager.get_ready_tasks().

Regression coverage for the dependency-satisfaction path.

Regression: commit 806e945f fixed a case-sensitivity bug where
_SUCCESSFUL_STATUSES membership check always returned False because
TaskStatus enum values are uppercase (e.g. "COMPLETE") but the comparison
operated on lowercased strings.  These tests guard against recurrence.
"""

from __future__ import annotations

import json
from pathlib import Path

from sam_schema.core.models import Plan, Task as SamTask, TaskStatus as SamTaskStatus
from sam_schema.writers.yaml_writer import _write_directory, write_plan
from typer.testing import CliRunner

from implementation_manager import Task, TaskPriority, TaskStatus, app, get_ready_tasks

runner = CliRunner()


def _task(task_id: str, status: TaskStatus, dependencies: list[str] | None = None, name: str | None = None) -> Task:
    """Minimal Task factory for test fixtures."""
    return Task(
        id=task_id,
        name=name or f"Task {task_id}",
        status=status,
        dependencies=dependencies or [],
        priority=TaskPriority.MEDIUM,
    )


def _sam_task(task_id: str) -> SamTask:
    """Create a minimal claimable SAM task."""
    return SamTask(id=task_id, title=f"Task {task_id}", status=SamTaskStatus.NOT_STARTED)


# ---------------------------------------------------------------------------
# Dependency-satisfaction path — the regression guard
# ---------------------------------------------------------------------------


class TestGetReadyTasksDependencySatisfaction:
    """get_ready_tasks() must treat COMPLETE, DEFERRED, and SKIPPED deps as satisfied."""

    def test_all_deps_complete_returns_task_as_ready(self) -> None:
        """Task whose dependency is COMPLETE is returned as ready."""
        dep = _task("T1", TaskStatus.COMPLETE)
        dependent = _task("T2", TaskStatus.NOT_STARTED, dependencies=["T1"])

        result = get_ready_tasks([dep, dependent])

        assert dependent in result

    def test_all_deps_deferred_returns_task_as_ready(self) -> None:
        """Task whose dependency is DEFERRED is returned as ready."""
        dep = _task("T1", TaskStatus.DEFERRED)
        dependent = _task("T2", TaskStatus.NOT_STARTED, dependencies=["T1"])

        result = get_ready_tasks([dep, dependent])

        assert dependent in result

    def test_all_deps_skipped_returns_task_as_ready(self) -> None:
        """Task whose dependency is SKIPPED is returned as ready."""
        dep = _task("T1", TaskStatus.SKIPPED)
        dependent = _task("T2", TaskStatus.NOT_STARTED, dependencies=["T1"])

        result = get_ready_tasks([dep, dependent])

        assert dependent in result

    def test_dep_in_progress_blocks_dependent_task(self) -> None:
        """Task whose dependency is IN_PROGRESS is NOT returned as ready."""
        dep = _task("T1", TaskStatus.IN_PROGRESS)
        dependent = _task("T2", TaskStatus.NOT_STARTED, dependencies=["T1"])

        result = get_ready_tasks([dep, dependent])

        assert dependent not in result

    def test_no_dependencies_returns_task_as_ready(self) -> None:
        """Task with no dependencies is ready for execution."""
        standalone = _task("T1", TaskStatus.NOT_STARTED, dependencies=[])

        result = get_ready_tasks([standalone])

        assert standalone in result

    # -----------------------------------------------------------------------
    # Additional correctness assertions
    # -----------------------------------------------------------------------

    def test_dep_not_started_blocks_dependent_task(self) -> None:
        """Task whose dependency is NOT_STARTED is NOT returned as ready."""
        dep = _task("T1", TaskStatus.NOT_STARTED)
        dependent = _task("T2", TaskStatus.NOT_STARTED, dependencies=["T1"])

        result = get_ready_tasks([dep, dependent])

        assert dependent not in result

    def test_dep_blocked_blocks_dependent_task(self) -> None:
        """Task whose dependency is BLOCKED is NOT returned as ready."""
        dep = _task("T1", TaskStatus.BLOCKED)
        dependent = _task("T2", TaskStatus.NOT_STARTED, dependencies=["T1"])

        result = get_ready_tasks([dep, dependent])

        assert dependent not in result

    def test_dep_failed_blocks_dependent_task(self) -> None:
        """FAILED is not a satisfying status — downstream tasks must not be dispatched."""
        dep = _task("T1", TaskStatus.FAILED)
        dependent = _task("T2", TaskStatus.NOT_STARTED, dependencies=["T1"])

        result = get_ready_tasks([dep, dependent])

        assert dependent not in result

    def test_mixed_deps_all_satisfied_returns_ready(self) -> None:
        """Task with multiple deps — each in a different satisfying status — is ready."""
        dep_complete = _task("T1", TaskStatus.COMPLETE)
        dep_deferred = _task("T2", TaskStatus.DEFERRED)
        dep_skipped = _task("T3", TaskStatus.SKIPPED)
        dependent = _task("T4", TaskStatus.NOT_STARTED, dependencies=["T1", "T2", "T3"])

        result = get_ready_tasks([dep_complete, dep_deferred, dep_skipped, dependent])

        assert dependent in result

    def test_mixed_deps_one_unsatisfied_blocks_task(self) -> None:
        """Task is blocked if even one dependency is not in a satisfying status."""
        dep_complete = _task("T1", TaskStatus.COMPLETE)
        dep_in_progress = _task("T2", TaskStatus.IN_PROGRESS)
        dependent = _task("T3", TaskStatus.NOT_STARTED, dependencies=["T1", "T2"])

        result = get_ready_tasks([dep_complete, dep_in_progress, dependent])

        assert dependent not in result

    def test_already_in_progress_task_excluded(self) -> None:
        """Tasks that are already IN_PROGRESS are not in the ready list."""
        running = _task("T1", TaskStatus.IN_PROGRESS, dependencies=[])

        result = get_ready_tasks([running])

        assert running not in result

    def test_complete_task_excluded_from_ready_list(self) -> None:
        """Completed tasks are not returned as ready — they are already done."""
        done = _task("T1", TaskStatus.COMPLETE, dependencies=[])

        result = get_ready_tasks([done])

        assert done not in result

    def test_empty_task_list_returns_empty(self) -> None:
        """Empty input returns empty list without error."""
        result = get_ready_tasks([])

        assert result == []

    def test_only_ready_tasks_are_returned(self) -> None:
        """Result contains exactly the tasks that satisfy the ready criteria."""
        dep = _task("T1", TaskStatus.COMPLETE)
        ready = _task("T2", TaskStatus.NOT_STARTED, dependencies=["T1"])
        blocked = _task("T3", TaskStatus.NOT_STARTED, dependencies=["T2"])  # T2 not done

        result = get_ready_tasks([dep, ready, blocked])

        assert result == [ready]


def test_claim_task_returns_started_string_and_persists(tmp_path: Path) -> None:
    """claim-task returns ClaimResult.started and persists the state transition."""
    task_file = tmp_path / "tasks-001-claimable.yaml"
    write_plan(Plan(feature="claimable", tasks=[_sam_task("T1")]), task_file, force_single=True)

    result = runner.invoke(app, ["claim-task", str(task_file), "T1"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["claimed"] is True
    assert payload["task_id"] == "T1"
    assert isinstance(payload["started"], str)
    assert payload["started"]
    assert "in-progress" in task_file.read_text(encoding="utf-8")


def test_claim_task_directory_plan_uses_parent_backend_root(tmp_path: Path) -> None:
    """claim-task resolves a directory-layout plan from its parent directory."""
    plan_dir = tmp_path / "tasks-directory-claim"
    _write_directory(Plan(feature="directory-claim", tasks=[_sam_task("T1")]), plan_dir)

    result = runner.invoke(app, ["claim-task", str(plan_dir), "T1"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["claimed"] is True
    assert "in-progress" in (plan_dir / "task-T1.yaml").read_text(encoding="utf-8")
