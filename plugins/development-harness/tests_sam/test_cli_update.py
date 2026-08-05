"""Tests for sam CLI ``update`` command.

Tests: Plan and task field updates via typed field options, --context, and --append-section.
How: Create a plan, invoke ``sam plan update`` with various flags, verify persistence.
Why: ``update`` is the primary write interface for agents modifying plan state
during execution -- field corruption here causes cascading failures.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from ruamel.yaml import YAML
from sam_schema.cli import app
from typer.testing import CliRunner

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_PLAN_YAML = """\
plan-id: P1
feature: update-test
version: "1.0"
description: Update test plan
state: ready
autonomy: checkpoint
goal: Test update functionality
context: Original context
acceptance_criteria: Update fields persist
issue: "99"
tasks:
  - id: T1
    title: First task
    status: not-started
    agent: test-agent
    dependencies: []
    blocked_by: []
    parallelize_with: []
    skills: []
    priority: 3
    complexity: medium
    created: null
    started: null
    completed: null
    last_activity: null
    body: First task body
    description: First task description
  - id: T2
    title: Second task
    status: not-started
    agent: test-agent
    dependencies:
      - T1
    blocked_by: []
    parallelize_with: []
    skills: []
    priority: 2
    complexity: high
    created: null
    started: null
    completed: null
    last_activity: null
    body: Second task body
    description: Second task description
"""


@pytest.fixture
def plan_dir(tmp_path: Path) -> Path:
    """Create a directory-layout plan for update tests."""
    d = tmp_path / "plan"
    d.mkdir()
    plan = d / "P001-update-test.yaml"
    plan.mkdir()
    data = YAML(typ="safe").load(_PLAN_YAML)
    tasks = data.pop("tasks")
    data["task_files"] = [f"task-{task['id']}.yaml" for task in tasks]
    y = YAML()
    y.dump(data, (plan / "plan.yaml").open("w", encoding="utf-8"))
    for task in tasks:
        y.dump(task, (plan / f"task-{task['id']}.yaml").open("w", encoding="utf-8"))
    return d


def _load_yaml(path: Path) -> dict:
    """Load a canonical YAML plan file or directory."""
    y = YAML(typ="rt")
    if not path.exists() and path.suffix == ".yaml":
        path = path.with_suffix("")
    if path.is_dir():
        data = y.load((path / "plan.yaml").read_text(encoding="utf-8"))
        data["tasks"] = [
            y.load(task_path.read_text(encoding="utf-8")) for task_path in sorted(path.glob("task-*.yaml"))
        ]
        return data
    return y.load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# sam plan update -- plan-level context
# ---------------------------------------------------------------------------


class TestSamUpdateContext:
    """Test ``sam plan update`` with --context flag for plan-level context.

    Tests: Plan-level context field update.
    How: Invoke update --context, read back and verify.
    Why: AC6 -- sam plan update sets context on plan.
    """

    def test_update_context_changes_plan_context(self, plan_dir: Path) -> None:
        """Update --context replaces the plan-level context field.

        Tests: Context field replacement.
        How: Update with new context, read back plan file.
        Why: Agents update plan context during execution.
        """
        # Arrange / Act
        result = runner.invoke(
            app,
            [
                "plan",
                "update",
                "--plan-address",
                "P1",
                "--context",
                "Updated context text",
                "--plan-dir",
                str(plan_dir),
            ],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 0, result.stdout
        data = json.loads(result.stdout)
        assert data["updated"] is True

        # Verify persistence
        plan_data = _load_yaml(plan_dir / "P001-update-test.yaml")
        assert plan_data["context"] == "Updated context text"

    def test_update_context_preserves_other_plan_fields(self, plan_dir: Path) -> None:
        """Update --context does not alter feature, goal, or tasks.

        Tests: Field isolation during context update.
        How: Update context, verify feature and task count unchanged.
        Why: Context update must not corrupt sibling fields.
        """
        # Arrange / Act
        runner.invoke(
            app,
            ["plan", "update", "--plan-address", "P1", "--context", "New context", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        plan_data = _load_yaml(plan_dir / "P001-update-test.yaml")
        assert plan_data["feature"] == "update-test"
        assert plan_data["goal"] == "Test update functionality"
        assert len(plan_data["tasks"]) == 2

    def test_update_returns_json_confirmation(self, plan_dir: Path) -> None:
        """Update returns JSON with ``updated: true`` and the address.

        Tests: CLI output format.
        How: Parse JSON output, check keys.
        Why: Callers check the JSON response for success confirmation.
        """
        # Arrange / Act
        result = runner.invoke(
            app,
            ["plan", "update", "--plan-address", "P1", "--context", "ctx", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["updated"] is True
        assert data["address"] == "1"

    def test_update_mixed_task_and_context_applies_both(self, plan_dir: Path) -> None:
        """A task-address update combined with --context applies both changes.

        Tests: Plan-level context is not silently dropped by a task-scoped update.
        How: Update P1/T1's title and --context in one invocation, verify both persisted.
        Why: ``--task-id T1 --title New --context Shared`` must update the task AND
            apply the plan-level context in the same operation, not exit successfully
            while silently discarding the context.
        """
        # Arrange / Act
        result = runner.invoke(
            app,
            [
                "plan",
                "update",
                "--plan-address",
                "P1/T1",
                "--title",
                "New title",
                "--context",
                "Shared context text",
                "--plan-dir",
                str(plan_dir),
            ],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 0, result.stdout
        plan_data = _load_yaml(plan_dir / "P001-update-test.yaml")
        assert plan_data["context"] == "Shared context text"
        assert plan_data["tasks"][0]["title"] == "New title"


# ---------------------------------------------------------------------------
# sam plan update -- task-level field updates
# ---------------------------------------------------------------------------


class TestSamUpdateSetField:
    """Test ``sam plan update`` with typed field options flag for arbitrary field updates.

    Tests: Task-level field updates via typed field options field=value.
    How: Invoke update P1/T1 typed field options priority=1, verify task field changed.
    Why: Agents need to update arbitrary task fields during execution.
    """

    def test_update_set_task_priority(self, plan_dir: Path) -> None:
        """Update typed field options priority=1 on a task changes priority value.

        Tests: Single field update on task.
        How: Update T1 priority, read back.
        Why: Priority changes drive task dispatch ordering.
        """
        # Arrange / Act
        result = runner.invoke(
            app,
            ["plan", "update", "--plan-address", "P1/T1", "--priority", "1", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 0
        plan_data = _load_yaml(plan_dir / "P001-update-test.yaml")
        # typed field options passes values as strings; ruamel.yaml may store as str or int
        assert str(plan_data["tasks"][0]["priority"]) == "1"

    def test_update_set_task_status(self, plan_dir: Path) -> None:
        """Update typed field options status=in-progress changes the task status.

        Tests: Status field update via typed field options.
        How: Set T1 status, read back and verify.
        Why: Status is the most frequently updated field.
        """
        # Arrange / Act
        result = runner.invoke(
            app,
            ["plan", "update", "--plan-address", "P1/T1", "--task-status", "in-progress", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 0
        plan_data = _load_yaml(plan_dir / "P001-update-test.yaml")
        assert plan_data["tasks"][0]["status"] == "in-progress"

    def test_update_set_preserves_other_task_fields(self, plan_dir: Path) -> None:
        """Update typed field options on one field does not alter other task fields.

        Tests: Field isolation during task update.
        How: Update priority, verify title and agent unchanged.
        Why: Sibling field corruption would silently break task dispatch.
        """
        # Arrange / Act
        runner.invoke(
            app,
            ["plan", "update", "--plan-address", "P1/T1", "--priority", "1", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        plan_data = _load_yaml(plan_dir / "P001-update-test.yaml")
        assert plan_data["tasks"][0]["title"] == "First task"
        assert plan_data["tasks"][0]["agent"] == "test-agent"

    def test_update_set_targets_correct_task(self, plan_dir: Path) -> None:
        """Update P1/T2 typed field options priority=1 only updates T2, not T1.

        Tests: Task targeting accuracy.
        How: Update T2, verify T1 is unchanged.
        Why: Wrong-task update is a silent data corruption bug.
        """
        # Arrange / Act
        runner.invoke(
            app,
            ["plan", "update", "--plan-address", "P1/T2", "--priority", "1", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        plan_data = _load_yaml(plan_dir / "P001-update-test.yaml")
        assert plan_data["tasks"][0]["priority"] == 3  # T1 unchanged
        assert str(plan_data["tasks"][1]["priority"]) == "1"  # T2 updated

    def test_update_removed_set_option_is_rejected(self, plan_dir: Path) -> None:
        """The obsolete --set syntax is rejected by the grouped command.

        Tests: Removed arbitrary field syntax.
        How: Pass the former --set option, expect parser rejection.
        Why: Updates must use typed field options.
        """
        result = runner.invoke(
            app,
            ["plan", "update", "--plan-address", "P1/T1", "--set", "priority1", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        assert result.exit_code != 0
        assert result.stdout == ""
        assert "--set" in result.stderr

    def test_update_positional_address_is_rejected(self, plan_dir: Path) -> None:
        """A positional plan address is rejected by ``plan update``."""
        result = runner.invoke(
            app, ["plan", "update", "P1/T1", "--priority", "1", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"}
        )
        assert result.exit_code != 0
        assert result.stdout == ""
        assert "plan-address" in result.stderr

    def test_update_unknown_option_is_rejected(self, plan_dir: Path) -> None:
        """Unknown update options fail before plan mutation."""
        result = runner.invoke(
            app,
            ["plan", "update", "--plan-address", "P1/T1", "--unknown", "value", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        assert result.exit_code != 0
        assert result.stdout == ""
        assert "--unknown" in result.stderr


# ---------------------------------------------------------------------------
# sam plan update -- append-section
# ---------------------------------------------------------------------------


class TestSamUpdateAppendSection:
    """Test ``sam plan update`` with --append-section and --section-content.

    Tests: Markdown section appending to task body.
    How: Invoke update with section flags, verify content in task file.
    Why: Agents append divergence notes and context manifests during execution.
    """

    def test_append_section_adds_content_to_task(self, plan_dir: Path) -> None:
        """Append section adds a named markdown section to the task.

        Tests: Section creation.
        How: Append a section, read back file, verify section heading present.
        Why: Section content drives quality gate decisions.
        """
        # Arrange / Act
        result = runner.invoke(
            app,
            [
                "plan",
                "update",
                "--plan-address",
                "P1/T1",
                "--append-section",
                "Divergence Notes",
                "--section-content",
                "Found a deviation in the architecture.",
                "--plan-dir",
                str(plan_dir),
            ],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 0, result.stdout
        plan_data = _load_yaml(plan_dir / "P001-update-test.yaml")
        context_notes = str(plan_data["tasks"][0].get("context-notes", ""))
        assert "Divergence Notes" in context_notes
        assert "Found a deviation" in context_notes

    def test_append_section_preserves_existing_content(self, plan_dir: Path) -> None:
        """Appending a second section preserves the first section.

        Tests: Additive section appending.
        How: Append two sections, verify both are in the output.
        Why: Multiple agents may append sections during task lifecycle.
        """
        # Arrange -- append first section
        runner.invoke(
            app,
            [
                "plan",
                "update",
                "--plan-address",
                "P1/T1",
                "--append-section",
                "Notes",
                "--section-content",
                "First note.",
                "--plan-dir",
                str(plan_dir),
            ],
            env={"NO_COLOR": "1"},
        )
        # Act -- append second section
        runner.invoke(
            app,
            [
                "plan",
                "update",
                "--plan-address",
                "P1/T1",
                "--append-section",
                "More Notes",
                "--section-content",
                "Second note.",
                "--plan-dir",
                str(plan_dir),
            ],
            env={"NO_COLOR": "1"},
        )
        # Assert
        plan_data = _load_yaml(plan_dir / "P001-update-test.yaml")
        context_notes = str(plan_data["tasks"][0].get("context-notes", ""))
        assert "First note." in context_notes
        assert "Second note." in context_notes

    def test_append_section_without_task_address_exits_1(self, plan_dir: Path) -> None:
        """Append section on plan-only address (no task) exits 1.

        Tests: Address validation for section append.
        How: Invoke with P1 (no /T{M}), expect error.
        Why: Sections are task-level -- plan-only address is invalid.
        """
        # Arrange / Act
        result = runner.invoke(
            app,
            [
                "plan",
                "update",
                "--plan-address",
                "P1",
                "--append-section",
                "Notes",
                "--section-content",
                "Content.",
                "--plan-dir",
                str(plan_dir),
            ],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 1

    def test_append_section_without_content_exits_1(self, plan_dir: Path) -> None:
        """Append section with --append-section but no --section-content exits 1.

        Tests: Missing content validation.
        How: Provide section name but omit content.
        Why: Empty sections are pointless and indicate caller error.
        """
        # Arrange / Act
        result = runner.invoke(
            app,
            ["plan", "update", "--plan-address", "P1/T1", "--append-section", "Notes", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# sam plan update -- error handling
# ---------------------------------------------------------------------------


class TestSamUpdateErrors:
    """Test ``sam plan update`` error handling.

    Tests: Error cases for invalid addresses, missing plans, no-op invocations.
    How: Invoke with various invalid inputs, verify exit codes and error messages.
    Why: Clear error handling prevents agents from silently failing.
    """

    def test_update_no_operation_flags_exits_1(self, plan_dir: Path) -> None:
        """Update with no typed field options, --context, or --append-section exits 1.

        Tests: No-op rejection.
        How: Invoke with just an address and no update flags.
        Why: No-op updates indicate caller error.
        """
        # Arrange / Act
        result = runner.invoke(
            app, ["plan", "update", "--plan-address", "P1", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"}
        )
        # Assert
        assert result.exit_code == 1

    def test_update_nonexistent_plan_exits_1(self, plan_dir: Path) -> None:
        """Update on nonexistent plan P99 exits 1.

        Tests: Missing plan handling.
        How: Address P99 which does not exist.
        Why: Must surface error, not silently succeed.
        """
        # Arrange / Act
        result = runner.invoke(
            app,
            ["plan", "update", "--plan-address", "P99", "--context", "ctx", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 1

    def test_update_nonexistent_task_exits_1(self, plan_dir: Path) -> None:
        """Update on nonexistent task T99 exits 1.

        Tests: Missing task handling.
        How: Address P1/T99 which does not exist.
        Why: Must surface error for wrong task ID.
        """
        # Arrange / Act
        result = runner.invoke(
            app,
            ["plan", "update", "--plan-address", "P1/T99", "--task-status", "complete", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 1
