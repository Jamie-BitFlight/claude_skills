"""Tests for new writer functions -- create_plan_file, append_section, and atomic write safety.

Tests: Plan file creation via create_plan_file, section appending via append_section,
and atomic write behavior that preserves originals on failure.
How: Write plans and tasks to tmp_path, exercise writer functions, read back and verify.
Why: Writers are the persistence layer -- corruption, partial writes, or data loss
here causes irreversible plan state damage.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from ruamel.yaml import YAML
from sam_schema.core.models import Complexity, Plan, Priority, Task, TaskStatus
from sam_schema.core.query import create_plan, load_plan
from sam_schema.writers.yaml_writer import _atomic_write, append_section, create_plan_file, write_plan

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file and return its contents as a dict."""
    y = YAML(typ="rt")
    return y.load(path.read_text(encoding="utf-8"))


def _make_plan(num_tasks: int = 2) -> Plan:
    """Create a plan with the specified number of tasks.

    Args:
        num_tasks: Number of tasks to include.

    Returns:
        A ``Plan`` model with the specified tasks.
    """
    tasks = [
        Task(
            id=f"T{i}",
            title=f"Task {i}",
            status=TaskStatus.NOT_STARTED,
            agent="test-agent",
            dependencies=[f"T{i - 1}"] if i > 1 else [],
            priority=Priority.MEDIUM,
            complexity=Complexity.MEDIUM,
        )
        for i in range(1, num_tasks + 1)
    ]
    return Plan(
        feature="writer-new-test",
        goal="Test new writer functions",
        context="Test context for writer tests",
        tasks=tasks,
    )


# ---------------------------------------------------------------------------
# create_plan_file
# ---------------------------------------------------------------------------


class TestCreatePlanFile:
    """Test create_plan_file writes valid YAML that round-trips through load_plan.

    Tests: Plan creation via create_plan_file.
    How: Write plan to tmp_path, load back via load_plan, compare fields.
    Why: create_plan_file is called by ``sam create`` -- output must be loadable.
    """

    def test_create_plan_file_writes_valid_yaml(self, tmp_path: Path) -> None:
        """Created file is valid YAML readable by load_plan.

        Tests: YAML validity.
        How: Write plan, load back, check no exceptions.
        Why: Invalid YAML breaks all downstream operations.
        """
        # Arrange
        plan = _make_plan()
        output = tmp_path / "P001-test.yaml"
        # Act
        create_plan_file(output, plan)
        # Assert
        result = load_plan(output)
        assert result.plan.feature == "writer-new-test"

    def test_create_plan_file_preserves_task_count(self, tmp_path: Path) -> None:
        """Written plan has the same number of tasks as the input.

        Tests: Task count fidelity.
        How: Write plan with 2 tasks, load back, count.
        Why: Lost tasks during serialization is silent data loss.
        """
        # Arrange
        plan = _make_plan(num_tasks=3)
        output = tmp_path / "P001-test.yaml"
        # Act
        create_plan_file(output, plan)
        # Assert
        result = load_plan(output)
        assert len(result.plan.tasks) == 3

    def test_create_plan_file_preserves_goal(self, tmp_path: Path) -> None:
        """Written plan preserves the goal field.

        Tests: Goal field round-trip.
        How: Write plan with goal, load back, compare.
        Why: Goal drives agent behavior during execution.
        """
        # Arrange
        plan = _make_plan()
        output = tmp_path / "P001-test.yaml"
        # Act
        create_plan_file(output, plan)
        # Assert
        result = load_plan(output)
        assert result.plan.goal == "Test new writer functions"

    def test_create_plan_file_preserves_context(self, tmp_path: Path) -> None:
        """Written plan preserves the context field.

        Tests: Context field round-trip.
        How: Write plan with context, load back, compare.
        Why: Context is shared across all tasks.
        """
        # Arrange
        plan = _make_plan()
        output = tmp_path / "P001-test.yaml"
        # Act
        create_plan_file(output, plan)
        # Assert
        result = load_plan(output)
        assert result.plan.context == "Test context for writer tests"

    def test_create_plan_file_preserves_task_ids(self, tmp_path: Path) -> None:
        """Written tasks have correct IDs matching the input.

        Tests: Task ID fidelity.
        How: Write plan, load back, check each task ID.
        Why: Wrong task IDs break addressing and dependency resolution.
        """
        # Arrange
        plan = _make_plan(num_tasks=3)
        output = tmp_path / "P001-test.yaml"
        # Act
        create_plan_file(output, plan)
        # Assert
        result = load_plan(output)
        ids = [t.id for t in result.plan.tasks]
        assert ids == ["T1", "T2", "T3"]

    def test_create_plan_file_preserves_dependencies(self, tmp_path: Path) -> None:
        """Written tasks preserve dependency lists.

        Tests: Dependency field round-trip.
        How: Write plan with deps, load back, compare T2 deps.
        Why: Lost dependencies break task ordering.
        """
        # Arrange
        plan = _make_plan(num_tasks=3)
        output = tmp_path / "P001-test.yaml"
        # Act
        create_plan_file(output, plan)
        # Assert
        result = load_plan(output)
        t2 = next(t for t in result.plan.tasks if t.id == "T2")
        assert t2.dependencies == ["T1"]

    def test_create_plan_file_adds_yaml_extension(self, tmp_path: Path) -> None:
        """Path without extension gets .yaml added automatically.

        Tests: Extension handling.
        How: Pass path without suffix, check written file has .yaml.
        Why: Canonical format requires .yaml extension.
        """
        # Arrange
        plan = _make_plan()
        output = tmp_path / "P001-test"
        # Act
        create_plan_file(output, plan)
        # Assert
        assert (tmp_path / "P001-test.yaml").exists()

    def test_create_plan_file_creates_parent_directories(self, tmp_path: Path) -> None:
        """Parent directories are created if they do not exist.

        Tests: Directory auto-creation.
        How: Pass path in nonexistent subdirectory.
        Why: First-time plan creation should not require manual mkdir.
        """
        # Arrange
        plan = _make_plan()
        output = tmp_path / "sub" / "dir" / "P001-test.yaml"
        # Act
        create_plan_file(output, plan)
        # Assert
        assert output.exists()


# ---------------------------------------------------------------------------
# create_plan (query layer -- uses create_plan_file internally)
# ---------------------------------------------------------------------------


class TestCreatePlanRoundTrip:
    """Test create_plan round-trip via the query layer.

    Tests: create_plan writes a file that load_plan can read back identically.
    How: Call create_plan with tasks, load back, compare.
    Why: AC4 -- sam create round-trips (create then read produces identical data).
    """

    def test_create_then_load_preserves_all_fields(self, tmp_path: Path) -> None:
        """Plan created via create_plan loads back with all fields intact.

        Tests: Full round-trip fidelity.
        How: Create plan with tasks, load back, compare each field.
        Why: Any field loss breaks the SAM execution pipeline.
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        tasks: list[dict[str, Any]] = [
            {
                "task": "T1",
                "title": "First task",
                "status": "not-started",
                "agent": "test-agent",
                "dependencies": [],
                "priority": 3,
                "complexity": "medium",
            },
            {
                "task": "T2",
                "title": "Second task",
                "status": "not-started",
                "agent": "test-agent",
                "dependencies": ["T1"],
                "priority": 2,
                "complexity": "high",
            },
        ]
        # Act
        plan = create_plan(slug="roundtrip", goal="Round-trip test", tasks=tasks, plan_dir=plan_dir)
        result = load_plan(plan.source_path)
        # Assert
        assert result.plan.feature == "roundtrip"
        assert result.plan.goal == "Round-trip test"
        assert len(result.plan.tasks) == 2
        assert result.plan.tasks[0].id == "T1"
        assert result.plan.tasks[1].id == "T2"
        assert result.plan.tasks[1].dependencies == ["T1"]


# ---------------------------------------------------------------------------
# append_section
# ---------------------------------------------------------------------------


class TestAppendSection:
    """Test append_section adds markdown sections to task bodies.

    Tests: Section appending to task context-notes field.
    How: Write a task file, call append_section, read back and verify.
    Why: Agents append divergence notes, context manifests, and review findings
    during task execution -- content must be preserved.
    """

    def test_append_section_adds_heading_and_content(self, tmp_path: Path) -> None:
        """append_section creates a section with heading and body text.

        Tests: Section creation.
        How: Append section to empty task, check heading and content.
        Why: Section must include both heading and body.
        """
        # Arrange
        f = tmp_path / "task.yaml"
        f.write_text("task: T1\ntitle: A task\nstatus: not-started\n", encoding="utf-8")
        # Act
        append_section(f, "T1", "Notes", "Some important notes.")
        # Assert
        data = _load_yaml(f)
        notes = str(data.get("context-notes", ""))
        assert "## Notes" in notes
        assert "Some important notes." in notes

    def test_append_section_preserves_existing_content(self, tmp_path: Path) -> None:
        """Appending a second section preserves the first.

        Tests: Additive appending.
        How: Append two sections, verify both present.
        Why: Multiple agents append sections during task lifecycle.
        """
        # Arrange
        f = tmp_path / "task.yaml"
        f.write_text("task: T1\ntitle: A task\nstatus: not-started\n", encoding="utf-8")
        append_section(f, "T1", "First", "First content.")
        # Act
        append_section(f, "T1", "Second", "Second content.")
        # Assert
        data = _load_yaml(f)
        notes = str(data.get("context-notes", ""))
        assert "First content." in notes
        assert "Second content." in notes
        assert "## First" in notes
        assert "## Second" in notes

    def test_append_section_in_multi_task_file(self, tmp_path: Path) -> None:
        """append_section targets the correct task in a multi-task file.

        Tests: Task targeting in multi-task file.
        How: Write 2-task file, append to T2, verify T1 unaffected.
        Why: Wrong-task append is silent data corruption.
        """
        # Arrange
        f = tmp_path / "plan.yaml"
        content = (
            "feature: test\n"
            "tasks:\n"
            "  - task: T1\n"
            "    title: First\n"
            "    status: not-started\n"
            "  - task: T2\n"
            "    title: Second\n"
            "    status: not-started\n"
        )
        f.write_text(content, encoding="utf-8")
        # Act
        append_section(f, "T2", "Context", "Context for T2.")
        # Assert
        data = _load_yaml(f)
        assert data["tasks"][0].get("context-notes") is None
        t2_notes = str(data["tasks"][1].get("context-notes", ""))
        assert "Context for T2." in t2_notes

    def test_append_section_missing_task_raises_key_error(self, tmp_path: Path) -> None:
        """append_section raises KeyError for nonexistent task.

        Tests: Task ID validation.
        How: Call with T99 which does not exist.
        Why: Missing task must raise, not silently no-op.
        """
        # Arrange
        f = tmp_path / "task.yaml"
        f.write_text("task: T1\ntitle: A task\nstatus: not-started\n", encoding="utf-8")
        # Act / Assert
        with pytest.raises(KeyError, match="T99"):
            append_section(f, "T99", "Notes", "Content.")

    def test_append_section_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """append_section raises FileNotFoundError for nonexistent file.

        Tests: File existence check.
        How: Call with nonexistent path.
        Why: Must raise, not create file.
        """
        # Arrange
        missing = tmp_path / "missing.yaml"
        # Act / Assert
        with pytest.raises(FileNotFoundError):
            append_section(missing, "T1", "Notes", "Content.")

    def test_append_section_in_frontmatter_file(self, tmp_path: Path) -> None:
        """append_section works on yaml_frontmatter (.md) files.

        Tests: Frontmatter format support.
        How: Write frontmatter file, append section, verify.
        Why: Many task files use frontmatter format.
        """
        # Arrange
        f = tmp_path / "task.md"
        f.write_text(
            "---\ntask: T1\ntitle: A task\nstatus: not-started\n---\n\n## Body\n\nSome prose.\n", encoding="utf-8"
        )
        # Act
        append_section(f, "T1", "Notes", "New section content.")
        # Assert
        data_raw = f.read_text(encoding="utf-8")
        # The frontmatter file should still start with ---
        assert data_raw.startswith("---\n")
        # The body should be preserved
        assert "## Body" in data_raw
        assert "Some prose." in data_raw


# ---------------------------------------------------------------------------
# Atomic write safety
# ---------------------------------------------------------------------------


class TestAtomicWriteSafety:
    """Test _atomic_write preserves original file on write failure.

    Tests: Atomic write failure handling.
    How: Mock a write failure, verify original file is preserved.
    Why: Partial writes corrupt plan files -- atomic write prevents this.
    """

    def test_atomic_write_creates_file(self, tmp_path: Path) -> None:
        """_atomic_write creates a new file with correct content.

        Tests: Basic atomic write.
        How: Write content, read back, compare.
        Why: Atomic write must produce the expected output.
        """
        # Arrange
        target = tmp_path / "output.yaml"
        # Act
        _atomic_write(target, "key: value\n")
        # Assert
        assert target.read_text(encoding="utf-8") == "key: value\n"

    def test_atomic_write_replaces_existing_file(self, tmp_path: Path) -> None:
        """_atomic_write replaces existing file content.

        Tests: Overwrite behavior.
        How: Write twice, verify second content wins.
        Why: Update operations use atomic write.
        """
        # Arrange
        target = tmp_path / "output.yaml"
        _atomic_write(target, "old content\n")
        # Act
        _atomic_write(target, "new content\n")
        # Assert
        assert target.read_text(encoding="utf-8") == "new content\n"

    def test_atomic_write_creates_parent_directories(self, tmp_path: Path) -> None:
        """_atomic_write creates parent directories if missing.

        Tests: Directory creation side effect.
        How: Write to path in nonexistent subdirectory.
        Why: First-time writes should not require manual mkdir.
        """
        # Arrange
        target = tmp_path / "sub" / "dir" / "output.yaml"
        # Act
        _atomic_write(target, "content\n")
        # Assert
        assert target.exists()

    def test_atomic_write_preserves_original_on_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Original file is preserved if atomic write fails during rename.

        Tests: Failure recovery.
        How: Write original content, mock Path.replace to raise, verify original intact.
        Why: AC -- original file preserved if write fails mid-operation.
        """
        # Arrange
        target = tmp_path / "output.yaml"
        target.write_text("original content\n", encoding="utf-8")

        # Mock Path.replace to raise an error (simulating rename failure)
        mocker.patch.object(Path, "replace", side_effect=OSError("Mock rename failure"))

        # Act
        with pytest.raises(OSError, match="Mock rename failure"):
            _atomic_write(target, "new content that should not persist\n")

        # Assert -- original content preserved
        assert target.read_text(encoding="utf-8") == "original content\n"

    def test_atomic_write_cleans_up_temp_file_on_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Temporary file is cleaned up after a failed atomic write.

        Tests: Temp file cleanup.
        How: Mock Path.replace to raise, verify no .tmp files remain.
        Why: Leftover temp files pollute the plan directory.
        """
        # Arrange
        target = tmp_path / "output.yaml"
        target.write_text("original\n", encoding="utf-8")

        mocker.patch.object(Path, "replace", side_effect=OSError("Mock failure"))

        # Act
        with pytest.raises(PermissionError):
            _atomic_write(target, "new content\n")

        # Assert -- no .tmp files left behind
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0


# ---------------------------------------------------------------------------
# write_plan security
# ---------------------------------------------------------------------------


class TestWritePlanSecurity:
    """Test write_plan rejects path traversal.

    Tests: Security check for '..' components in output_path.
    How: Pass paths with '..' and expect ValueError.
    Why: Path traversal could write files outside the intended directory.
    """

    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        """write_plan raises ValueError for paths containing '..'.

        Tests: Path traversal rejection.
        How: Pass path with '..' component.
        Why: Security boundary enforcement.
        """
        # Arrange
        plan = _make_plan()
        output = tmp_path / ".." / "escaped.yaml"
        # Act / Assert
        with pytest.raises(ValueError, match="Path traversal"):
            write_plan(plan, output)
