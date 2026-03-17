"""Tests for sam CLI ``claim`` command.

Tests: Task claiming (transition to in-progress) via ``sam claim``.
How: Invoke ``sam claim`` via CliRunner on tasks in various states, verify
JSON output, exit codes, and file mutation.
Why: ``claim`` is the concurrency guard -- double-claiming a task causes
duplicate execution, wasted compute, and conflicting file edits.
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
feature: claim-test
goal: Test claim functionality
tasks:
  - id: T1
    title: Ready task
    status: not-started
    agent: test-agent
    dependencies: []
    priority: 1
    complexity: low
  - id: T2
    title: In-progress task
    status: in-progress
    agent: test-agent
    dependencies: []
    priority: 2
    complexity: medium
    started: "2026-03-10T10:00:00Z"
  - id: T3
    title: Complete task
    status: complete
    agent: test-agent
    dependencies: []
    priority: 3
    complexity: low
    completed: "2026-03-10T14:00:00Z"
"""


@pytest.fixture
def plan_dir(tmp_path: Path) -> Path:
    """Create a plan directory with a plan containing tasks in various states.

    Layout:
        plan/P001-claim-test.yaml -- T1 (not-started), T2 (in-progress), T3 (complete)

    Returns:
        Path to a ``plan/`` directory.
    """
    d = tmp_path / "plan"
    d.mkdir()
    (d / "P001-claim-test.yaml").write_text(_PLAN_YAML, encoding="utf-8")
    return d


def _load_yaml(path: Path) -> dict:
    """Load a YAML file and return its contents."""
    y = YAML(typ="rt")
    return y.load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# sam claim -- success case
# ---------------------------------------------------------------------------


class TestSamClaimSuccess:
    """Test ``sam claim`` on a claimable (not-started) task.

    Tests: Successful task claiming.
    How: Claim an unclaimed task, verify JSON output and file mutation.
    Why: Claiming is the only safe way to transition a task to in-progress.
    """

    def test_claim_unclaimed_task_exits_0(self, plan_dir: Path) -> None:
        """Claiming a not-started task exits 0.

        Tests: Exit code for successful claim.
        How: Claim T1 (not-started), check exit code.
        Why: Exit 0 signals success to the calling orchestrator.
        """
        # Arrange / Act
        result = runner.invoke(app, ["claim", "P1/T1", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"})
        # Assert
        assert result.exit_code == 0, result.output

    def test_claim_returns_json_with_claimed_true(self, plan_dir: Path) -> None:
        """Successful claim returns JSON with ``claimed: true``.

        Tests: JSON output structure.
        How: Parse JSON output, check ``claimed`` key.
        Why: Orchestrator checks ``claimed`` to confirm acquisition.
        """
        # Arrange / Act
        result = runner.invoke(app, ["claim", "P1/T1", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"})
        # Assert
        data = json.loads(result.output)
        assert data["claimed"] is True

    def test_claim_returns_task_id_in_output(self, plan_dir: Path) -> None:
        """Successful claim includes the task_id in JSON output.

        Tests: Task ID echo.
        How: Check ``task_id`` field in JSON.
        Why: Callers need task_id for subsequent operations.
        """
        # Arrange / Act
        result = runner.invoke(app, ["claim", "P1/T1", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"})
        # Assert
        data = json.loads(result.output)
        assert data["task_id"] == "T1"

    def test_claim_returns_started_timestamp(self, plan_dir: Path) -> None:
        """Successful claim includes a ``started`` ISO timestamp.

        Tests: Timestamp generation.
        How: Check ``started`` field is a non-null ISO string.
        Why: Started timestamp is used for SLA tracking and hook operations.
        """
        # Arrange / Act
        result = runner.invoke(app, ["claim", "P1/T1", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"})
        # Assert
        data = json.loads(result.output)
        assert data["started"] is not None
        assert "T" in data["started"]  # ISO format contains T separator

    def test_claim_updates_status_on_disk(self, plan_dir: Path) -> None:
        """Claiming writes ``in-progress`` status to the plan file.

        Tests: Disk mutation.
        How: Claim T1, read back YAML, check status.
        Why: Status must persist -- in-memory-only claim is useless.
        """
        # Arrange / Act
        runner.invoke(app, ["claim", "P1/T1", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"})
        # Assert
        plan_data = _load_yaml(plan_dir / "P001-claim-test.yaml")
        assert plan_data["tasks"][0]["status"] == "in-progress"

    def test_claim_writes_started_timestamp_on_disk(self, plan_dir: Path) -> None:
        """Claiming writes a ``started`` timestamp to the task on disk.

        Tests: Timestamp persistence.
        How: Claim T1, read back YAML, check started field.
        Why: Started timestamp drives activity tracking.
        """
        # Arrange / Act
        runner.invoke(app, ["claim", "P1/T1", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"})
        # Assert
        plan_data = _load_yaml(plan_dir / "P001-claim-test.yaml")
        assert plan_data["tasks"][0].get("started") is not None

    def test_claim_does_not_alter_other_tasks(self, plan_dir: Path) -> None:
        """Claiming T1 does not change T2 or T3 status.

        Tests: Task isolation during claim.
        How: Claim T1, verify T2 and T3 unchanged.
        Why: Cross-task mutation is a critical data corruption bug.
        """
        # Arrange / Act
        runner.invoke(app, ["claim", "P1/T1", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"})
        # Assert
        plan_data = _load_yaml(plan_dir / "P001-claim-test.yaml")
        assert plan_data["tasks"][1]["status"] == "in-progress"  # T2 was already in-progress
        assert plan_data["tasks"][2]["status"] == "complete"  # T3 was already complete


# ---------------------------------------------------------------------------
# sam claim -- already claimed (exit 1)
# ---------------------------------------------------------------------------


class TestSamClaimAlreadyClaimed:
    """Test ``sam claim`` on a task already in ``in-progress`` state.

    Tests: Double-claim prevention.
    How: Attempt to claim T2 (already in-progress), expect exit 1.
    Why: Double-claiming causes duplicate agent dispatch.
    """

    def test_claim_in_progress_task_exits_1(self, plan_dir: Path) -> None:
        """Claiming an in-progress task exits 1.

        Tests: Guard against double-claim.
        How: Claim T2 (in-progress), check exit code.
        Why: Non-zero exit tells orchestrator to skip this task.
        """
        # Arrange / Act
        result = runner.invoke(app, ["claim", "P1/T2", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"})
        # Assert
        assert result.exit_code == 1

    def test_claim_complete_task_exits_1(self, plan_dir: Path) -> None:
        """Claiming a complete task exits 1.

        Tests: Guard against claiming finished tasks.
        How: Claim T3 (complete), check exit code.
        Why: Re-claiming completed tasks restarts finished work.
        """
        # Arrange / Act
        result = runner.invoke(app, ["claim", "P1/T3", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"})
        # Assert
        assert result.exit_code == 1

    def test_claim_in_progress_task_shows_error_message(self, plan_dir: Path) -> None:
        """Claiming an in-progress task prints an error message to stderr.

        Tests: Error message clarity.
        How: Check stderr contains the expected status.
        Why: Agent needs to understand why the claim failed.
        """
        # Arrange / Act
        result = runner.invoke(app, ["claim", "P1/T2", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"})
        # Assert
        combined = result.output or ""
        assert "in-progress" in combined.lower() or "Error" in combined

    def test_double_claim_same_task_exits_1(self, plan_dir: Path) -> None:
        """Claiming the same task twice -- second attempt exits 1.

        Tests: Sequential double-claim.
        How: Claim T1 (success), then claim T1 again (failure).
        Why: Race condition simulation -- must reject second claim.
        """
        # Arrange -- first claim succeeds
        first = runner.invoke(app, ["claim", "P1/T1", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"})
        assert first.exit_code == 0

        # Act -- second claim fails
        second = runner.invoke(app, ["claim", "P1/T1", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"})
        # Assert
        assert second.exit_code == 1


# ---------------------------------------------------------------------------
# sam claim -- nonexistent task (exit 1)
# ---------------------------------------------------------------------------


class TestSamClaimNonexistent:
    """Test ``sam claim`` on nonexistent plan or task.

    Tests: Error handling for invalid addresses.
    How: Attempt to claim nonexistent plans and tasks, expect exit 1.
    Why: Silent failure on wrong address would leave tasks unclaimed.
    """

    def test_claim_nonexistent_plan_exits_1(self, plan_dir: Path) -> None:
        """Claim P99/T1 (no such plan) exits 1.

        Tests: Missing plan error.
        How: Address nonexistent plan number.
        Why: Must surface error for wrong plan.
        """
        # Arrange / Act
        result = runner.invoke(app, ["claim", "P99/T1", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"})
        # Assert
        assert result.exit_code == 1

    def test_claim_nonexistent_task_exits_1(self, plan_dir: Path) -> None:
        """Claim P1/T99 (task not in plan) exits 1.

        Tests: Missing task error.
        How: Address valid plan but nonexistent task.
        Why: Must surface error for wrong task ID.
        """
        # Arrange / Act
        result = runner.invoke(app, ["claim", "P1/T99", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"})
        # Assert
        assert result.exit_code == 1

    def test_claim_plan_only_address_exits_1(self, plan_dir: Path) -> None:
        """Claim P1 (no task component) exits 1.

        Tests: Address format validation.
        How: Provide plan-only address.
        Why: Claiming requires a task -- plan-only is invalid.
        """
        # Arrange / Act
        result = runner.invoke(app, ["claim", "P1", "--plan-dir", str(plan_dir)], env={"NO_COLOR": "1"})
        # Assert
        assert result.exit_code == 1

    def test_claim_missing_plan_dir_exits_1(self, tmp_path: Path) -> None:
        """Claim with non-existent plan_dir exits 1.

        Tests: Missing directory handling.
        How: Point to nonexistent directory.
        Why: Must surface error, not traceback.
        """
        # Arrange
        missing = tmp_path / "no-such-dir"
        # Act
        result = runner.invoke(app, ["claim", "P1/T1", "--plan-dir", str(missing)], env={"NO_COLOR": "1"})
        # Assert
        assert result.exit_code == 1
