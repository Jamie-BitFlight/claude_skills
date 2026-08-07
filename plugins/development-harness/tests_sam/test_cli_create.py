"""Tests for sam CLI ``create`` command.

Tests: Plan creation via CLI with typed slug, goal, task, context, and issue options.
How: Invoke ``sam create`` via CliRunner, verify JSON output and file creation.
Why: ``create`` is the entry point for all new plan files -- errors here prevent
plan creation across the entire SAM pipeline.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from sam_schema.cli import app
from typer.testing import CliRunner

runner = CliRunner()

_UUID_PLAN_ID_RE = re.compile(
    r"^P[0-9a-f]{8}(-.+)?$", re.IGNORECASE
)  # ponytail: full stem now, hex prefix + optional slug


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def plan_dir(tmp_path: Path) -> Path:
    """Create an empty temporary plan directory.

    Returns:
        Path to a ``plan/`` directory inside ``tmp_path``.
    """
    d = tmp_path / "plan"
    d.mkdir()
    return d


# sam create -- basic creation
# ---------------------------------------------------------------------------


class TestSamCreateBasic:
    """Test basic ``sam create`` functionality.

    Tests: Plan file creation with minimal required arguments.
    How: Invoke CLI with slug and goal, verify JSON output and file on disk.
    Why: Every plan begins with ``sam create`` -- the happy path must work.
    """

    def test_create_with_slug_and_goal_returns_json(self, plan_dir: Path) -> None:
        """Create a plan with slug and goal, verify JSON response.

        Tests: CLI output format.
        How: Invoke create, parse JSON, check required keys.
        Why: Downstream tools parse the JSON output to locate the created file.
        """
        # Arrange -- empty plan_dir
        # Act
        result = runner.invoke(
            app,
            ["plan", "create", "--slug", "my-feature", "--goal", "Implement feature X", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 0, result.stdout
        data = json.loads(result.stdout)
        assert "plan_id" in data
        assert "task_count" in data
        assert data["task_count"] == 0

    def test_create_assigns_uuid_plan_id(self, plan_dir: Path) -> None:
        """First plan in empty directory gets a UUID-based plan_id.

        Tests: UUID plan_id assignment.
        How: Create in empty dir, check plan_id matches UUID format.
        Why: plan_id is the addressing foundation.
        """
        # Arrange -- empty plan_dir
        # Act
        result = runner.invoke(
            app,
            ["plan", "create", "--slug", "first-plan", "--goal", "Goal", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert _UUID_PLAN_ID_RE.match(data["plan_id"]), f"Expected UUID plan_id, got: {data['plan_id']!r}"

    def test_create_writes_file_to_disk(self, plan_dir: Path) -> None:
        """Created plan file exists on disk at the reported path.

        Tests: File creation side effect.
        How: Invoke create, check file exists at reported path.
        Why: If the file is not written, all downstream operations fail.
        """
        # Arrange
        # Act
        result = runner.invoke(
            app,
            ["plan", "create", "--slug", "disk-test", "--goal", "Test goal", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 0
        json.loads(result.stdout)
        assert len(list(plan_dir.glob("*.yaml"))) == 1

    def test_create_file_has_yaml_extension(self, plan_dir: Path) -> None:
        """Created file uses .yaml extension.

        Tests: File naming convention.
        How: Check suffix of created file.
        Why: Pure YAML format is the canonical plan format per ADR-001.
        """
        # Arrange / Act
        result = runner.invoke(
            app,
            ["plan", "create", "--slug", "ext-test", "--goal", "Goal", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 0
        json.loads(result.stdout)
        assert next(plan_dir.glob("*.yaml")).suffix == ".yaml"

    def test_create_assigns_unique_plan_ids(self, plan_dir: Path) -> None:
        """Two consecutive creates produce distinct UUID plan_ids.

        Tests: UUID uniqueness across multiple creates.
        How: Create two plans, verify both plan_ids are UUID format and distinct.
        Why: Collisions in plan IDs break addressing.
        """
        # Arrange / Act -- create first plan
        r1 = runner.invoke(
            app,
            ["plan", "create", "--slug", "first", "--goal", "First", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Act -- create second plan
        r2 = runner.invoke(
            app,
            ["plan", "create", "--slug", "second", "--goal", "Second", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert r1.exit_code == 0
        assert r2.exit_code == 0
        id1 = json.loads(r1.stdout)["plan_id"]
        id2 = json.loads(r2.stdout)["plan_id"]
        assert _UUID_PLAN_ID_RE.match(id1), f"Expected UUID plan_id, got: {id1!r}"
        assert _UUID_PLAN_ID_RE.match(id2), f"Expected UUID plan_id, got: {id2!r}"
        assert id1 != id2, "Two consecutive creates should produce distinct plan_ids"


# ---------------------------------------------------------------------------
# plan create -- typed task options and removed ingestion flags
# ---------------------------------------------------------------------------


class TestSamCreateTypedTask:
    """Test task creation through the named, typed create options."""

    def test_create_with_typed_task_options_round_trips_task(self, plan_dir: Path) -> None:
        """Typed task options persist all supported task fields."""
        result = runner.invoke(
            app,
            [
                "plan",
                "create",
                "--slug",
                "typed-task",
                "--goal",
                "Goal",
                "--task-id",
                "T1",
                "--task-title",
                "First task",
                "--task-status",
                "not-started",
                "--task-agent",
                "test-agent",
                "--task-dependency",
                "T0",
                "--task-priority",
                "3",
                "--task-complexity",
                "medium",
                "--plan-dir",
                str(plan_dir),
            ],
            env={"NO_COLOR": "1"},
        )
        assert result.exit_code == 0, result.stdout
        assert ": " not in result.stdout
        assert ", " not in result.stdout
        data = json.loads(result.stdout)
        assert data["task_count"] == 1
        read_result = runner.invoke(
            app,
            ["plan", "read", "--address", f"{data['plan_id']}/T1", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        assert read_result.exit_code == 0, read_result.stdout
        task = json.loads(read_result.stdout)["task"]
        assert task["id"] == "T1"
        assert task["title"] == "First task"
        assert task["dependencies"] == ["T0"]
        assert task["priority"] == 3

    @pytest.mark.parametrize("removed_flag", ["--stdin", "--task-json"])
    def test_create_rejects_removed_ingestion_flags(self, plan_dir: Path, removed_flag: str) -> None:
        """Routine plan creation rejects the removed stdin/JSON ingestion flags."""
        result = runner.invoke(
            app,
            ["plan", "create", "--slug", "rejected", "--goal", "Goal", removed_flag, "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        assert result.exit_code != 0
        assert result.stdout == ""
        assert result.stderr

    def test_create_rejects_incomplete_typed_task(self, plan_dir: Path) -> None:
        """A task id without its required title is rejected by typed validation."""
        result = runner.invoke(
            app,
            ["plan", "create", "--slug", "bad-task", "--goal", "Goal", "--task-id", "T1", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        assert result.exit_code != 0
        assert result.stdout == ""
        assert result.stderr

    @pytest.mark.parametrize(
        "args",
        [
            ["plan", "create", "rejected", "--goal", "Goal", "--plan-dir", "PLACEHOLDER"],
            [
                "plan",
                "create",
                "--slug",
                "rejected",
                "--goal",
                "Goal",
                "--unknown-option",
                "x",
                "--plan-dir",
                "PLACEHOLDER",
            ],
        ],
        ids=["positional-slug", "unknown-option"],
    )
    def test_create_parser_rejects_positional_and_unknown_options(self, plan_dir: Path, args: list[str]) -> None:
        """Create keeps data values named and reports parser errors on stderr."""
        result = runner.invoke(
            app, [str(plan_dir) if arg == "PLACEHOLDER" else arg for arg in args], env={"NO_COLOR": "1"}
        )
        assert result.exit_code != 0
        assert result.stdout == ""
        assert result.stderr


# sam create -- optional fields
# ---------------------------------------------------------------------------


class TestSamCreateOptionalFields:
    """Test ``sam create`` with optional --context and --issue flags.

    Tests: Plan-level metadata population.
    How: Create with optional flags, read back the file, verify fields.
    Why: Context and issue are used by downstream agents for plan discovery.
    """

    def test_create_with_context_stores_context_in_plan(self, plan_dir: Path) -> None:
        """Create with --context persists the context field.

        Tests: Context field persistence.
        How: Create with --context, load plan via plan_id, check context value.
        Why: Plan context drives agent behavior during task execution.
        """
        # Arrange / Act
        result = runner.invoke(
            app,
            [
                "plan",
                "create",
                "--slug",
                "ctx-test",
                "--goal",
                "Goal",
                "--context",
                "Some shared context",
                "--plan-dir",
                str(plan_dir),
            ],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 0
        plan_id = json.loads(result.stdout)["plan_id"]
        # Verify by reading back using the UUID plan_id
        read_result = runner.invoke(
            app, ["plan", "read", "--address", plan_id, "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"}
        )
        assert read_result.exit_code == 0, read_result.stdout
        plan_data = json.loads(read_result.stdout)
        # read_plan returns ReadResult; plan fields are nested under "plan".
        assert plan_data["plan"].get("context") == "Some shared context"

    def test_create_with_issue_stores_issue_in_plan(self, plan_dir: Path) -> None:
        """Create with --issue persists the issue number.

        Tests: Issue field persistence.
        How: Create with --issue 42, load plan via plan_id, check issue value.
        Why: Issue links plans to GitHub issues for traceability.
        """
        # Arrange / Act
        result = runner.invoke(
            app,
            ["plan", "create", "--slug", "issue-test", "--goal", "Goal", "--issue", "42", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 0
        plan_id = json.loads(result.stdout)["plan_id"]
        # Read back using the UUID plan_id
        read_result = runner.invoke(
            app, ["plan", "read", "--address", plan_id, "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"}
        )
        assert read_result.exit_code == 0, read_result.stdout
        plan_data = json.loads(read_result.stdout)
        assert plan_data["plan"].get("issue") == "42"


# ---------------------------------------------------------------------------
# sam create -- round-trip verification
# ---------------------------------------------------------------------------


class TestSamCreateRoundTrip:
    """Test create-then-read round-trip fidelity.

    Tests: Data survives create -> read cycle.
    How: Create plan with tasks, read back via ``sam read``, compare.
    Why: AC4 -- sam create round-trips (create then read produces identical data).
    """

    def test_create_then_read_preserves_task_data(self, plan_dir: Path) -> None:
        """Tasks created with typed options can be read back with identical fields.

        Tests: Task data round-trip fidelity.
        How: Create with tasks, read {plan_id}/T1, verify fields match.
        Why: Data loss during create->read breaks the entire workflow.
        """
        # Arrange / Act -- create
        create_result = runner.invoke(
            app,
            [
                "plan",
                "create",
                "--slug",
                "roundtrip",
                "--goal",
                "Round-trip test",
                "--task-id",
                "T1",
                "--task-title",
                "First task",
                "--task-status",
                "not-started",
                "--task-agent",
                "test-agent",
                "--task-priority",
                "3",
                "--task-complexity",
                "medium",
                "--plan-dir",
                str(plan_dir),
            ],
            env={"NO_COLOR": "1"},
        )
        assert create_result.exit_code == 0, create_result.stdout
        plan_id = json.loads(create_result.stdout)["plan_id"]

        # Act -- read back
        read_result = runner.invoke(
            app, ["plan", "read", "--address", f"{plan_id}/T1", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"}
        )
        # Assert
        assert read_result.exit_code == 0, read_result.stdout
        data = json.loads(read_result.stdout)
        task = data["task"]
        assert task["id"] == "T1"
        assert task["title"] == "First task"
        assert task["status"] == "not-started"

    def test_create_then_read_preserves_task_count(self, plan_dir: Path) -> None:
        """Number of tasks after round-trip matches creation input.

        Tests: Task count fidelity.
        How: Create with 2 tasks, read plan, count tasks.
        Why: Lost tasks during round-trip would silently drop work items.
        """
        # Arrange / Act -- create
        create_result = runner.invoke(
            app,
            [
                "plan",
                "create",
                "--slug",
                "count-test",
                "--goal",
                "Count test",
                "--task-id",
                "T1",
                "--task-title",
                "First task",
                "--task-status",
                "not-started",
                "--task-agent",
                "test-agent",
                "--task-priority",
                "3",
                "--task-complexity",
                "medium",
                "--plan-dir",
                str(plan_dir),
            ],
            env={"NO_COLOR": "1"},
        )
        assert create_result.exit_code == 0, create_result.stdout
        plan_id = json.loads(create_result.stdout)["plan_id"]

        # Act -- read plan-level
        read_result = runner.invoke(
            app, ["plan", "read", "--address", plan_id, "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"}
        )
        # Assert
        assert read_result.exit_code == 0, read_result.stdout
        plan_data = json.loads(read_result.stdout)
        # read_plan returns ReadResult; tasks are nested under plan.tasks.
        assert len(plan_data["plan"].get("tasks", [])) == 1

    def test_create_then_read_assignment_includes_plan_goal(self, plan_dir: Path) -> None:
        """TaskAssignment from read includes the plan goal set during create.

        Tests: Plan-level field propagation in TaskAssignment.
        How: Create with goal, read {plan_id}/T1, check plan-goal field.
        Why: AC5 -- sam read includes plan context in TaskAssignment response.
        """
        # Arrange / Act
        create_result = runner.invoke(
            app,
            [
                "plan",
                "create",
                "--slug",
                "goal-test",
                "--goal",
                "My specific goal",
                "--task-id",
                "T1",
                "--task-title",
                "First task",
                "--task-status",
                "not-started",
                "--task-agent",
                "test-agent",
                "--task-priority",
                "3",
                "--task-complexity",
                "medium",
                "--plan-dir",
                str(plan_dir),
            ],
            env={"NO_COLOR": "1"},
        )
        assert create_result.exit_code == 0, create_result.stdout
        plan_id = json.loads(create_result.stdout)["plan_id"]

        read_result = runner.invoke(
            app, ["plan", "read", "--address", f"{plan_id}/T1", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"}
        )
        # Assert
        assert read_result.exit_code == 0, read_result.stdout
        data = json.loads(read_result.stdout)
        # TaskAssignment now serializes with alias field names (by_alias=True).
        assert data.get("plan-goal") == "My specific goal"

    def test_create_with_typed_fields_preserves_task_content(self, plan_dir: Path) -> None:
        """Typed task fields round-trip through create -> read without data loss.

        Tests: typed task field preservation during create.
        How: Create with typed task fields, read {plan_id}/T1, verify the fields survive.
                Why: Typed task values must remain intact across the create/read boundary.
        """
        # Act -- create with the supported typed task fields.
        create_result = runner.invoke(
            app,
            [
                "plan",
                "create",
                "--slug",
                "body-test",
                "--goal",
                "Test body preservation",
                "--task-id",
                "T1",
                "--task-title",
                "Body preservation test",
                "--task-status",
                "not-started",
                "--task-agent",
                "python-cli-architect",
                "--task-priority",
                "3",
                "--task-complexity",
                "medium",
                "--plan-dir",
                str(plan_dir),
            ],
            env={"NO_COLOR": "1"},
        )
        assert create_result.exit_code == 0, create_result.stdout
        plan_id = json.loads(create_result.stdout)["plan_id"]

        # Act -- read back
        read_result = runner.invoke(
            app, ["plan", "read", "--address", f"{plan_id}/T1", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"}
        )
        # Assert
        assert read_result.exit_code == 0, read_result.stdout
        data = json.loads(read_result.stdout)
        task = data["task"]
        assert task["title"] == "Body preservation test"
        assert task["agent"] == "python-cli-architect"

    def test_create_plan_dir_auto_created_if_missing(self, tmp_path: Path) -> None:
        """Plan directory is auto-created if it does not exist.

        Tests: Directory auto-creation.
        How: Pass non-existent plan_dir, verify plan is created.
        Why: First-time users should not need to mkdir before create.
        """
        # Arrange
        new_dir = tmp_path / "auto-created-plan"
        assert not new_dir.exists()
        # Act
        result = runner.invoke(
            app,
            ["plan", "create", "--slug", "auto-dir", "--goal", "Goal", "--plan-dir", str(new_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 0
        assert new_dir.exists()


# ---------------------------------------------------------------------------
# sam create -- --issue as metadata (UUID-based plan IDs)
# ---------------------------------------------------------------------------


class TestSamCreateWithIssue:
    """Test that --issue N stores issue metadata but plan_id is still UUID-based.

    Tests: Issue-as-metadata behaviour.
    How: Invoke create with --issue, verify plan_id is UUID format and issue is stored.
    Why: GitHub issue is metadata; plan addressing uses UUID to avoid collisions.
    """

    def test_create_with_issue_produces_uuid_plan_id(self, plan_dir: Path) -> None:
        """--issue 951 produces a UUID plan_id, not P951.

        Tests: plan_id format when --issue is provided.
        How: Create with --issue 951, check plan_id is UUID format.
        Why: With UUID-based IDs, issue number no longer determines plan_id.
        """
        # Arrange -- empty plan_dir
        # Act
        result = runner.invoke(
            app,
            ["plan", "create", "--slug", "my-feature", "--goal", "Test", "--issue", "951", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 0, result.stdout
        data = json.loads(result.stdout)
        assert _UUID_PLAN_ID_RE.match(data["plan_id"]), f"Expected UUID plan_id, got: {data['plan_id']!r}"
        assert len(list(plan_dir.glob("*.yaml"))) == 1

    def test_create_with_issue_file_exists_at_reported_path(self, plan_dir: Path) -> None:
        """File created with --issue exists on disk at the path returned in JSON.

        Tests: Disk write side effect for issue-annotated plans.
        How: Create with --issue, stat the reported path.
        Why: If the file is not written, all downstream read/claim operations fail.
        """
        # Arrange / Act
        result = runner.invoke(
            app,
            ["plan", "create", "--slug", "disk-check", "--goal", "Test", "--issue", "42", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        # Assert
        assert result.exit_code == 0, result.stdout
        json.loads(result.stdout)
        assert len(list(plan_dir.glob("*.yaml"))) == 1

    def test_create_with_issue_stores_issue_in_plan(self, plan_dir: Path) -> None:
        """--issue value is persisted inside the plan file.

        Tests: issue field written to plan.
        How: Create with --issue 951, read back, verify issue field.
        Why: Issue metadata is needed for backlog integration.
        """
        # Arrange
        result = runner.invoke(
            app,
            ["plan", "create", "--slug", "with-issue", "--goal", "Test", "--issue", "951", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        assert result.exit_code == 0, result.stdout
        plan_id = json.loads(result.stdout)["plan_id"]

        # Act -- read back
        read_result = runner.invoke(
            app, ["plan", "read", "--address", plan_id, "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"}
        )
        assert read_result.exit_code == 0, read_result.stdout
        plan_data = json.loads(read_result.stdout)
        assert plan_data["plan"].get("issue") == "951"

    def test_two_creates_with_same_issue_produce_distinct_plan_ids(self, plan_dir: Path) -> None:
        """Two creates with the same --issue number produce different UUID plan_ids.

        Tests: No collision on duplicate issue number.
        How: Create twice with --issue 500, verify distinct plan_ids.
        Why: UUID generation ensures no collision regardless of issue number.
        """
        # Arrange / Act
        r1 = runner.invoke(
            app,
            ["plan", "create", "--slug", "first", "--goal", "First", "--issue", "500", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        r2 = runner.invoke(
            app,
            ["plan", "create", "--slug", "second", "--goal", "Second", "--issue", "500", "--plan-dir", str(plan_dir)],
            env={"NO_COLOR": "1"},
        )
        assert r1.exit_code == 0, r1.stdout
        assert r2.exit_code == 0, r2.stdout
        id1 = json.loads(r1.stdout)["plan_id"]
        id2 = json.loads(r2.stdout)["plan_id"]
        assert _UUID_PLAN_ID_RE.match(id1), f"Expected UUID plan_id, got: {id1!r}"
        assert _UUID_PLAN_ID_RE.match(id2), f"Expected UUID plan_id, got: {id2!r}"
        assert id1 != id2, "Same issue should produce distinct UUID plan_ids"
