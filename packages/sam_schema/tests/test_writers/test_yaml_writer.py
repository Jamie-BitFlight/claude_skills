"""Tests for sam_schema.writers.yaml_writer — canonical YAML output writer.

Tests: write_plan (single/directory), update_field (round-trip), multiline scalar
preservation, atomic write safety, and path traversal rejection.
How: Write plans to tmp_path, read back and verify structure.
Why: The writer is the only path for persisting plan state — corruption here
causes data loss across the entire SAM pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from ruamel.yaml import YAML
from sam_schema.core.models import Complexity, Plan, Priority, Task, TaskStatus
from sam_schema.writers.yaml_writer import (
    LINE_THRESHOLD,
    _estimate_line_count,
    _task_to_dict,
    update_field,
    update_fields,
    write_plan,
)

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict:
    """Load a YAML file and return its contents as a plain dict."""
    y = YAML(typ="rt")
    return y.load(path.read_text(encoding="utf-8"))


def _make_small_plan() -> Plan:
    """Create a plan with 3 tasks (well under LINE_THRESHOLD)."""
    tasks = [
        Task(
            id="T1",
            title="First task",
            status=TaskStatus.COMPLETE,
            agent="test-agent",
            dependencies=[],
            priority=Priority.CRITICAL,
            complexity=Complexity.LOW,
        ),
        Task(
            id="T2",
            title="Second task",
            status=TaskStatus.IN_PROGRESS,
            agent="test-agent",
            dependencies=["T1"],
            priority=Priority.HIGH,
            complexity=Complexity.MEDIUM,
            description="A multiline\ndescription\nfor testing.",
        ),
        Task(
            id="T3",
            title="Third task",
            status=TaskStatus.NOT_STARTED,
            agent="test-agent",
            dependencies=["T1", "T2"],
            priority=Priority.MEDIUM,
            complexity=Complexity.HIGH,
        ),
    ]
    return Plan(feature="writer-test", version="1.0", description="Plan for writer tests.", tasks=tasks)


# ---------------------------------------------------------------------------
# write_plan — single file
# ---------------------------------------------------------------------------


class TestWritePlanSingleFile:
    """Verify write_plan produces correct single-file YAML output.

    Tests: Single-file output path for plans under LINE_THRESHOLD.
    How: Write a small plan, read back, verify structure.
    Why: Single-file is the most common output — must produce valid YAML.
    """

    def test_write_plan_creates_yaml_file(self, tmp_path: Path) -> None:
        """Verify write_plan creates a file at the expected path.

        Tests: File creation.
        How: Write plan to tmp_path, check file exists.
        Why: Missing output file is a hard failure.
        """
        plan = _make_small_plan()
        output = tmp_path / "plan.yaml"
        result = write_plan(plan, output, force_single=True)
        assert result.exists()
        assert result.suffix == ".yaml"

    def test_write_plan_single_file_contains_feature(self, tmp_path: Path) -> None:
        """Verify written YAML contains the feature field."""
        plan = _make_small_plan()
        output = tmp_path / "plan.yaml"
        write_plan(plan, output, force_single=True)
        data = _load_yaml(output)
        assert data["feature"] == "writer-test"

    def test_write_plan_single_file_contains_version(self, tmp_path: Path) -> None:
        """Verify written YAML contains the version field."""
        plan = _make_small_plan()
        output = tmp_path / "plan.yaml"
        write_plan(plan, output, force_single=True)
        data = _load_yaml(output)
        assert data["version"] == "1.0"

    def test_write_plan_single_file_contains_tasks_list(self, tmp_path: Path) -> None:
        """Verify written YAML has a tasks list with correct count."""
        plan = _make_small_plan()
        output = tmp_path / "plan.yaml"
        write_plan(plan, output, force_single=True)
        data = _load_yaml(output)
        assert "tasks" in data
        assert len(data["tasks"]) == 3

    def test_write_plan_single_file_task_has_correct_id(self, tmp_path: Path) -> None:
        """Verify first task in written YAML has correct id."""
        plan = _make_small_plan()
        output = tmp_path / "plan.yaml"
        write_plan(plan, output, force_single=True)
        data = _load_yaml(output)
        assert data["tasks"][0]["id"] == "T1"

    def test_write_plan_single_file_task_has_correct_status(self, tmp_path: Path) -> None:
        """Verify first task has correct status string."""
        plan = _make_small_plan()
        output = tmp_path / "plan.yaml"
        write_plan(plan, output, force_single=True)
        data = _load_yaml(output)
        assert data["tasks"][0]["status"] == "complete"

    def test_write_plan_single_file_omits_none_fields(self, tmp_path: Path) -> None:
        """Verify None-valued fields are omitted from output.

        Tests: Clean YAML output without null values.
        How: Check first task does not have 'started' key (it is None).
        Why: Null fields clutter YAML and confuse human readers.
        """
        plan = _make_small_plan()
        output = tmp_path / "plan.yaml"
        write_plan(plan, output, force_single=True)
        data = _load_yaml(output)
        first_task = data["tasks"][0]
        assert "created" not in first_task
        assert "github-issue" not in first_task

    def test_write_plan_single_file_omits_empty_lists(self, tmp_path: Path) -> None:
        """Verify empty list fields are omitted from output."""
        plan = _make_small_plan()
        output = tmp_path / "plan.yaml"
        write_plan(plan, output, force_single=True)
        data = _load_yaml(output)
        first_task = data["tasks"][0]
        assert "blocked-by" not in first_task
        assert "parallelize-with" not in first_task
        assert "skills" not in first_task

    def test_write_plan_single_file_omits_default_analysis_method(self, tmp_path: Path) -> None:
        """Verify analysis-method='none' is omitted (skip-if-default)."""
        plan = _make_small_plan()
        output = tmp_path / "plan.yaml"
        write_plan(plan, output, force_single=True)
        data = _load_yaml(output)
        first_task = data["tasks"][0]
        assert "analysis-method" not in first_task

    def test_write_plan_single_file_omits_default_divergence_notes(self, tmp_path: Path) -> None:
        """Verify divergence-notes=0 is omitted (skip-if-default)."""
        plan = _make_small_plan()
        output = tmp_path / "plan.yaml"
        write_plan(plan, output, force_single=True)
        data = _load_yaml(output)
        first_task = data["tasks"][0]
        assert "divergence-notes" not in first_task


# ---------------------------------------------------------------------------
# write_plan — directory output
# ---------------------------------------------------------------------------


class TestWritePlanDirectory:
    """Verify write_plan directory output for large plans.

    Tests: Directory output when plan exceeds LINE_THRESHOLD.
    How: Create plan with many tasks, verify directory structure.
    Why: Large plans must split to avoid unwieldy single files.
    """

    def test_write_plan_directory_creates_plan_yaml(self, tmp_path: Path) -> None:
        """Verify directory output includes plan.yaml.

        Tests: Plan metadata file creation.
        How: Write a plan that exceeds LINE_THRESHOLD.
        Why: plan.yaml is the discovery entry point for directory plans.
        """
        plan = _make_large_plan()
        output = tmp_path / "big-plan"
        result = write_plan(plan, output)
        plan_yaml = result / "plan.yaml"
        assert plan_yaml.exists()

    def test_write_plan_directory_creates_per_task_files(self, tmp_path: Path) -> None:
        """Verify directory output creates one file per task."""
        plan = _make_large_plan()
        output = tmp_path / "big-plan"
        result = write_plan(plan, output)
        task_files = list(result.glob("task-*.yaml"))
        assert len(task_files) == len(plan.tasks)

    def test_write_plan_directory_plan_yaml_has_task_files_list(self, tmp_path: Path) -> None:
        """Verify plan.yaml contains task_files list."""
        plan = _make_large_plan()
        output = tmp_path / "big-plan"
        result = write_plan(plan, output)
        data = _load_yaml(result / "plan.yaml")
        assert "task_files" in data
        assert len(data["task_files"]) == len(plan.tasks)

    def test_write_plan_directory_task_file_has_correct_content(self, tmp_path: Path) -> None:
        """Verify individual task file contains the task data."""
        plan = _make_large_plan()
        output = tmp_path / "big-plan"
        result = write_plan(plan, output)
        task_data = _load_yaml(result / "task-T1.yaml")
        assert task_data["id"] == "T1"
        assert task_data["status"] == "not-started"


def _make_large_plan() -> Plan:
    """Create a plan with enough tasks to exceed LINE_THRESHOLD."""
    tasks = [
        Task(
            id=f"T{i}",
            title=f"Task number {i} with a description",
            status=TaskStatus.NOT_STARTED,
            agent="test-agent",
            dependencies=[f"T{i - 1}"] if i > 1 else [],
            priority=Priority.MEDIUM,
            complexity=Complexity.MEDIUM,
            description=f"Long description for task {i}.\n" * 10,
            requirements=f"Requirements for task {i}.\n" * 5,
            acceptance_criteria=f"Criteria for task {i}.\n" * 5,
        )
        for i in range(1, 30)
    ]
    return Plan(
        feature="large-plan-test",
        version="1.0",
        description="A plan large enough to trigger directory output.",
        tasks=tasks,
    )


# ---------------------------------------------------------------------------
# write_plan — force_single
# ---------------------------------------------------------------------------


class TestWritePlanForceSingle:
    """Verify force_single bypasses the LINE_THRESHOLD check.

    Tests: force_single parameter.
    How: Write a large plan with force_single=True, verify single file.
    Why: Some callers need single-file output regardless of size.
    """

    def test_force_single_produces_file_not_directory(self, tmp_path: Path) -> None:
        """Verify force_single writes a single YAML file even for large plans."""
        plan = _make_large_plan()
        output = tmp_path / "plan.yaml"
        result = write_plan(plan, output, force_single=True)
        assert result.is_file()
        assert result.suffix == ".yaml"

    def test_force_single_adds_yaml_extension_if_missing(self, tmp_path: Path) -> None:
        """Verify force_single adds .yaml extension to pathless output."""
        plan = _make_small_plan()
        output = tmp_path / "plan"
        result = write_plan(plan, output, force_single=True)
        assert result.suffix == ".yaml"


# ---------------------------------------------------------------------------
# write_plan — path traversal rejection
# ---------------------------------------------------------------------------


class TestWritePlanPathTraversal:
    """Verify write_plan rejects path traversal attempts.

    Tests: Security check for '..' components in output_path.
    How: Pass paths with '..' and expect ValueError.
    Why: Path traversal could write files outside the intended directory.
    """

    def test_path_traversal_double_dot_raises_value_error(self, tmp_path: Path) -> None:
        """Verify '..' in path parts raises ValueError."""
        plan = _make_small_plan()
        output = tmp_path / ".." / "escaped.yaml"
        with pytest.raises(ValueError, match="Path traversal"):
            write_plan(plan, output)


# ---------------------------------------------------------------------------
# Multiline scalar preservation
# ---------------------------------------------------------------------------


class TestMultilineScalarPreservation:
    """Verify multiline content fields are written as YAML literal block scalars.

    Tests: LiteralScalarString wrapping for markdown content fields.
    How: Write plan with multiline description, verify YAML uses | syntax.
    Why: Block scalar (|) preserves line breaks in markdown content.
    """

    def test_multiline_description_uses_literal_scalar(self, tmp_path: Path) -> None:
        """Verify a multiline description is written as a YAML literal block scalar."""
        plan = _make_small_plan()
        output = tmp_path / "plan.yaml"
        write_plan(plan, output, force_single=True)
        raw = output.read_text(encoding="utf-8")
        # The second task has a multiline description — should use |
        assert "description: |" in raw or "description: |\n" in raw


# ---------------------------------------------------------------------------
# _task_to_dict
# ---------------------------------------------------------------------------


class TestTaskToDict:
    """Verify _task_to_dict conversion.

    Tests: Task model to clean dict conversion for YAML serialization.
    How: Convert a task and verify field names and omission of defaults.
    Why: Intermediate dict controls what appears in YAML output.
    """

    def test_task_to_dict_uses_kebab_case_keys(self) -> None:
        """Verify output dict uses kebab-case field names (by_alias=True)."""
        task = Task.model_validate({"id": "T1", "title": "T", "status": "not-started", "blocked_by": ["T2"]})
        d = _task_to_dict(task)
        assert "blocked-by" in d
        assert "blocked_by" not in d

    def test_task_to_dict_omits_none_fields(self) -> None:
        """Verify None fields are excluded."""
        task = Task(id="T1", title="T", status=TaskStatus.NOT_STARTED)
        d = _task_to_dict(task)
        assert "agent" not in d
        assert "created" not in d

    def test_task_to_dict_omits_empty_strings(self) -> None:
        """Verify empty string fields are excluded."""
        task = Task(id="T1", title="T", status=TaskStatus.NOT_STARTED)
        d = _task_to_dict(task)
        assert "description" not in d
        assert "objective" not in d


# ---------------------------------------------------------------------------
# _estimate_line_count
# ---------------------------------------------------------------------------


class TestEstimateLineCount:
    """Verify _estimate_line_count produces reasonable estimates.

    Tests: Line count estimation for write mode decision.
    How: Compare estimates for small vs large plans.
    Why: Wrong estimates cause inappropriate single/directory splits.
    """

    def test_small_plan_under_threshold(self) -> None:
        """Verify small plan estimate is under LINE_THRESHOLD."""
        plan = _make_small_plan()
        count = _estimate_line_count(plan)
        assert count < LINE_THRESHOLD

    def test_large_plan_over_threshold(self) -> None:
        """Verify large plan estimate exceeds LINE_THRESHOLD."""
        plan = _make_large_plan()
        count = _estimate_line_count(plan)
        assert count >= LINE_THRESHOLD


# ---------------------------------------------------------------------------
# update_field — single-task file
# ---------------------------------------------------------------------------


class TestUpdateFieldSingleTask:
    """Verify update_field modifies a single-task YAML file.

    Tests: In-place field update with comment/order preservation.
    How: Write a task file, update a field, read back and verify.
    Why: update_field is the primary mechanism for status transitions.
    """

    def test_update_field_changes_status(self, tmp_path: Path) -> None:
        """Verify update_field changes the status field.

        Tests: Status update in single-task file.
        How: Write task YAML, call update_field, read back.
        Why: Status transitions drive the entire SAM execution loop.
        """
        f = tmp_path / "task.yaml"
        f.write_text("task: T1\ntitle: A task\nstatus: not-started\n")
        update_field(f, "T1", "status", "in-progress")
        data = _load_yaml(f)
        assert data["status"] == "in-progress"

    def test_update_field_preserves_other_fields(self, tmp_path: Path) -> None:
        """Verify update_field does not alter other fields."""
        f = tmp_path / "task.yaml"
        f.write_text("task: T1\ntitle: A task\nstatus: not-started\npriority: 2\n")
        update_field(f, "T1", "status", "complete")
        data = _load_yaml(f)
        assert data["title"] == "A task"
        assert data["priority"] == 2

    def test_update_field_with_id_key(self, tmp_path: Path) -> None:
        """Verify update_field works when task uses 'id' key instead of 'task'."""
        f = tmp_path / "task.yaml"
        f.write_text("id: T1\ntitle: A task\nstatus: not-started\n")
        update_field(f, "T1", "status", "complete")
        data = _load_yaml(f)
        assert data["status"] == "complete"


# ---------------------------------------------------------------------------
# update_field — multi-task file
# ---------------------------------------------------------------------------


class TestUpdateFieldMultiTask:
    """Verify update_field modifies a specific task in a multi-task YAML file.

    Tests: Field update targeting one task in a multi-task file.
    How: Write multi-task YAML, update one task, verify only that task changed.
    Why: Multi-task files are common — updating one must not corrupt others.
    """

    def test_update_field_targets_correct_task(self, tmp_path: Path) -> None:
        """Verify update_field modifies only the targeted task."""
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
        f.write_text(content)
        update_field(f, "T2", "status", "complete")
        data = _load_yaml(f)
        assert data["tasks"][0]["status"] == "not-started"
        assert data["tasks"][1]["status"] == "complete"

    def test_update_field_round_trip_preserves_all_tasks(self, tmp_path: Path) -> None:
        """Verify round-trip update preserves all other tasks.

        Tests: Round-trip fidelity of update_field.
        How: Write 3 tasks, update middle one, verify all 3 are intact.
        Why: update_field must not lose data from non-targeted tasks.
        """
        f = tmp_path / "plan.yaml"
        content = (
            "feature: test\n"
            "tasks:\n"
            "  - task: T1\n"
            "    title: First\n"
            "    status: complete\n"
            "    priority: 1\n"
            "  - task: T2\n"
            "    title: Second\n"
            "    status: not-started\n"
            "    priority: 2\n"
            "  - task: T3\n"
            "    title: Third\n"
            "    status: not-started\n"
            "    priority: 3\n"
        )
        f.write_text(content)
        update_field(f, "T2", "status", "in-progress")
        data = _load_yaml(f)
        assert len(data["tasks"]) == 3
        assert data["tasks"][0]["task"] == "T1"
        assert data["tasks"][0]["status"] == "complete"
        assert data["tasks"][0]["priority"] == 1
        assert data["tasks"][1]["status"] == "in-progress"
        assert data["tasks"][2]["task"] == "T3"
        assert data["tasks"][2]["status"] == "not-started"

    def test_update_field_multi_task_with_id_key(self, tmp_path: Path) -> None:
        """Verify update_field works when tasks use 'id' key."""
        f = tmp_path / "plan.yaml"
        content = "feature: test\ntasks:\n  - id: T1\n    title: First\n    status: not-started\n"
        f.write_text(content)
        update_field(f, "T1", "status", "complete")
        data = _load_yaml(f)
        assert data["tasks"][0]["status"] == "complete"


# ---------------------------------------------------------------------------
# update_field — multiline content
# ---------------------------------------------------------------------------


class TestUpdateFieldMultiline:
    """Verify update_field handles multiline markdown content fields.

    Tests: Multiline values wrapped as LiteralScalarString.
    How: Update a markdown content field with newlines, verify block scalar.
    Why: Multiline content must preserve line breaks in YAML.
    """

    def test_update_field_multiline_description_uses_block_scalar(self, tmp_path: Path) -> None:
        """Verify multiline description is written as block scalar."""
        f = tmp_path / "task.yaml"
        f.write_text("task: T1\ntitle: A task\nstatus: not-started\n")
        update_field(f, "T1", "description", "Line one\nLine two\nLine three")
        raw = f.read_text(encoding="utf-8")
        assert "description: |" in raw or "description: |\n" in raw


# ---------------------------------------------------------------------------
# update_field — error handling
# ---------------------------------------------------------------------------


class TestUpdateFieldErrors:
    """Verify update_field error handling.

    Tests: FileNotFoundError, KeyError, ValueError for invalid inputs.
    How: Call with missing file, missing task ID, unknown field.
    Why: Error handling must be precise — wrong error type breaks callers.
    """

    def test_update_field_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """Verify FileNotFoundError for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            update_field(tmp_path / "missing.yaml", "T1", "status", "complete")

    def test_update_field_missing_task_id_raises_key_error(self, tmp_path: Path) -> None:
        """Verify KeyError when task ID is not in file."""
        f = tmp_path / "task.yaml"
        f.write_text("task: T1\ntitle: A task\nstatus: not-started\n")
        with pytest.raises(KeyError, match="T99"):
            update_field(f, "T99", "status", "complete")

    def test_update_field_unknown_field_name_raises_value_error(self, tmp_path: Path) -> None:
        """Verify ValueError for unrecognized field name."""
        f = tmp_path / "task.yaml"
        f.write_text("task: T1\ntitle: A task\nstatus: not-started\n")
        with pytest.raises(ValueError, match="Unknown field"):
            update_field(f, "T1", "not-a-real-field", "value")

    def test_update_field_missing_task_in_multi_task_raises_key_error(self, tmp_path: Path) -> None:
        """Verify KeyError for missing task in multi-task file."""
        f = tmp_path / "plan.yaml"
        content = "feature: test\ntasks:\n  - task: T1\n    title: First\n    status: not-started\n"
        f.write_text(content)
        with pytest.raises(KeyError, match="T99"):
            update_field(f, "T99", "status", "complete")


# ---------------------------------------------------------------------------
# update_field — yaml_frontmatter format
# ---------------------------------------------------------------------------


_FRONTMATTER_SINGLE = """\
---
task: T1
title: A yaml_frontmatter task
status: not-started
priority: 2
---
## Body

Some prose content here.
"""

_FRONTMATTER_SINGLE_WITH_CODE_FENCE = """\
---
task: T1
title: Task with fence in body
status: not-started
---
## Example

```yaml
---
nested: yaml
---
```

More prose.
"""


class TestUpdateFieldYamlFrontmatter:
    """Verify update_field handles yaml_frontmatter format (.md) files.

    Tests: In-place field update on files with YAML frontmatter + prose body.
    How: Write yaml_frontmatter file, call update_field, verify YAML and body.
    Why: yaml_frontmatter is the dominant task file format in the repo; update_field
         must not raise ComposerError when ruamel.yaml sees the multi-doc markers.
    """

    def test_update_field_frontmatter_changes_status(self, tmp_path: Path) -> None:
        """Verify update_field updates status in a yaml_frontmatter file.

        Tests: Status update on yaml_frontmatter format.
        How: Write frontmatter file, call update_field, re-read YAML block.
        Why: Status transitions are the primary use case; must work on .md files.
        """
        f = tmp_path / "task.md"
        f.write_text(_FRONTMATTER_SINGLE)
        update_field(f, "T1", "status", "in-progress")
        raw = f.read_text(encoding="utf-8")
        assert raw.startswith("---\n")
        # Re-parse just the frontmatter block to check status
        from ruamel.yaml import YAML as _YAML

        y = _YAML(typ="rt")
        raw.split("\n---")[1].lstrip("\n").split("\n---")[0]
        # simpler: load from between the first --- pair
        import re as _re

        after_open = raw[4:]
        close = _re.search(r"\n---", after_open)
        assert close is not None
        data = y.load(after_open[: close.start()])
        assert data["status"] == "in-progress"

    def test_update_field_frontmatter_preserves_other_fields(self, tmp_path: Path) -> None:
        """Verify update_field does not alter other YAML fields in frontmatter.

        Tests: Field preservation in yaml_frontmatter.
        How: Update status only, verify title and priority unchanged.
        Why: Round-trip must not corrupt sibling fields.
        """
        f = tmp_path / "task.md"
        f.write_text(_FRONTMATTER_SINGLE)
        update_field(f, "T1", "status", "complete")
        raw = f.read_text(encoding="utf-8")
        import re as _re

        from ruamel.yaml import YAML as _YAML

        y = _YAML(typ="rt")
        after_open = raw[4:]
        close = _re.search(r"\n---", after_open)
        assert close is not None
        data = y.load(after_open[: close.start()])
        assert data["title"] == "A yaml_frontmatter task"
        assert data["priority"] == 2
        assert data["status"] == "complete"

    def test_update_field_frontmatter_preserves_body(self, tmp_path: Path) -> None:
        """Verify update_field leaves the prose body unchanged.

        Tests: Body content preservation after frontmatter update.
        How: Write frontmatter file, update a field, check body suffix.
        Why: The prose body is user content — it must never be modified.
        """
        f = tmp_path / "task.md"
        f.write_text(_FRONTMATTER_SINGLE)
        update_field(f, "T1", "status", "complete")
        raw = f.read_text(encoding="utf-8")
        assert "## Body" in raw
        assert "Some prose content here." in raw

    def test_update_field_frontmatter_preserves_body_with_code_fence(self, tmp_path: Path) -> None:
        """Verify update_field preserves a body that contains --- inside a code fence.

        Tests: Bodies with YAML code fences are not corrupted by the split.
        How: Write file where body contains ```yaml ... --- ... ```, update field.
        Why: A naive split on --- would corrupt the body by truncating at the fence's ---.
        """
        f = tmp_path / "task.md"
        f.write_text(_FRONTMATTER_SINGLE_WITH_CODE_FENCE)
        update_field(f, "T1", "status", "complete")
        raw = f.read_text(encoding="utf-8")
        assert "nested: yaml" in raw
        assert "More prose." in raw

    def test_update_field_frontmatter_wrong_task_id_raises_key_error(self, tmp_path: Path) -> None:
        """Verify KeyError when task ID does not match the frontmatter block.

        Tests: Task ID mismatch error handling in yaml_frontmatter.
        How: Write frontmatter with task T1, request update for T99.
        Why: Must surface wrong-ID as KeyError, not silently no-op.
        """
        f = tmp_path / "task.md"
        f.write_text(_FRONTMATTER_SINGLE)
        with pytest.raises(KeyError, match="T99"):
            update_field(f, "T99", "status", "complete")

    def test_update_field_frontmatter_file_still_starts_with_delimiter(self, tmp_path: Path) -> None:
        """Verify the written file still starts with --- after update.

        Tests: Output format integrity.
        How: Update field, verify file starts with opening ---.
        Why: The file must remain valid yaml_frontmatter for downstream readers.
        """
        f = tmp_path / "task.md"
        f.write_text(_FRONTMATTER_SINGLE)
        update_field(f, "T1", "status", "complete")
        raw = f.read_text(encoding="utf-8")
        assert raw.startswith("---\n")


class TestUpdateFieldsYamlFrontmatter:
    """Verify update_fields handles yaml_frontmatter format files.

    Tests: Multi-field update on files with YAML frontmatter + prose body.
    How: Write yaml_frontmatter file, call update_fields with multiple fields.
    Why: update_fields is the batch form used by the hook; must handle .md files.
    """

    def test_update_fields_frontmatter_updates_multiple_fields(self, tmp_path: Path) -> None:
        """Verify update_fields sets multiple fields in a frontmatter file.

        Tests: Multi-field write in yaml_frontmatter format.
        How: Call update_fields with status and last-activity, verify both set.
        Why: Hook calls update_fields to set status + timestamp atomically.
        """
        f = tmp_path / "task.md"
        f.write_text(_FRONTMATTER_SINGLE)
        update_fields(f, "T1", {"status": "complete", "last-activity": "2026-01-01T00:00:00"})
        raw = f.read_text(encoding="utf-8")
        import re as _re

        from ruamel.yaml import YAML as _YAML

        y = _YAML(typ="rt")
        after_open = raw[4:]
        close = _re.search(r"\n---", after_open)
        assert close is not None
        data = y.load(after_open[: close.start()])
        assert data["status"] == "complete"
        assert data["last-activity"] == "2026-01-01T00:00:00"

    def test_update_fields_frontmatter_preserves_body(self, tmp_path: Path) -> None:
        """Verify update_fields leaves the prose body unchanged.

        Tests: Body preservation in multi-field update.
        How: Update fields, verify body content in raw output.
        Why: Body is user content — multi-field update must not touch it.
        """
        f = tmp_path / "task.md"
        f.write_text(_FRONTMATTER_SINGLE)
        update_fields(f, "T1", {"status": "in-progress"})
        raw = f.read_text(encoding="utf-8")
        assert "## Body" in raw
        assert "Some prose content here." in raw

    def test_update_fields_frontmatter_wrong_task_id_raises_key_error(self, tmp_path: Path) -> None:
        """Verify KeyError when task ID does not match in yaml_frontmatter file.

        Tests: Task ID mismatch in update_fields for frontmatter format.
        How: Write frontmatter with T1, call update_fields for T99.
        Why: Must raise KeyError, not silently succeed with no update.
        """
        f = tmp_path / "task.md"
        f.write_text(_FRONTMATTER_SINGLE)
        with pytest.raises(KeyError, match="T99"):
            update_fields(f, "T99", {"status": "complete"})
