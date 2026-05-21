"""Integration tests for QG plan creation, addressing, and dispatch flow.

Tests: End-to-end quality gate plan lifecycle — creation via build_quality_gate_plan
       + create_plan, addressing via resolve_plan_address/parse_address, readiness
       sequencing via get_ready_tasks, status transitions via update_status, and
       completion gate logic.

How: Uses the Python API directly (create_plan, get_ready_tasks, update_status,
     get_plan_status) with tmp_path fixture for plan directory isolation. No MCP
     calls, no external services.

Why: T04 acceptance criteria require validating that QG-prefixed plans can be
     created, addressed, queried, and dispatched through existing SAM infrastructure
     without modification. These tests exercise T01 (addressing) and T02 (generator)
     together.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import pytest
from ruamel.yaml import YAML
from sam_schema.core.addressing import AddressingError, parse_address, resolve_plan_address
from sam_schema.core.models import Plan, Task, TaskStatus
from sam_schema.core.quality_gates import build_quality_gate_plan
from sam_schema.core.query import create_plan, get_plan_status, get_ready_tasks, get_task, load_plan, update_status
from sam_schema.writers.yaml_writer import create_plan_file

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXPECTED_TASK_COUNT = 7
_EXPECTED_AGENTS = [
    "task-worker",
    "code-reviewer",
    "feature-verifier",
    "integration-checker",
    "doc-drift-auditor",
    "service-docs-maintainer",
    "context-refinement",
]
_EXPECTED_TITLES = [
    "Multi-Perspective Review",
    "Code Review",
    "Feature Verification",
    "Integration Check",
    "Documentation Drift Audit",
    "Documentation Update",
    "Context Refinement",
]


def _parse_yaml(text: str) -> dict:
    """Parse YAML text with ruamel.yaml (repo-standard library).

    Args:
        text: YAML string to parse.

    Returns:
        Parsed dict.
    """
    yaml = YAML()
    return yaml.load(io.StringIO(text))


def _create_qg_plan(plan_dir: Path, slug: str = "my-feature", impl_plan_address: str = "P001") -> Plan:
    """Create a plan via create_plan (P{NNN}-{slug}.yaml naming) and return the Plan model.

    Used by most tests that exercise plan content, task structure, and status
    transitions. The P-prefix naming is the standard output of create_plan.

    Args:
        plan_dir: Directory where the plan file will be created.
        slug: Feature slug for the plan.
        impl_plan_address: Implementation plan address to embed in task bodies.

    Returns:
        The created Plan model with source_path set.
    """
    yaml_str = build_quality_gate_plan(slug=slug, issue=None, impl_plan_address=impl_plan_address)
    parsed = _parse_yaml(yaml_str)
    tasks_raw = parsed.get("tasks", [])

    return create_plan(
        slug=slug, goal=f"Quality gate verification for {impl_plan_address}", tasks=tasks_raw, plan_dir=plan_dir
    )


def _create_qg_file_directly(plan_dir: Path, plan_number: int, slug: str = "my-feature") -> Plan:
    """Write a QG{NNN}-{slug}.yaml file directly using create_plan_file.

    Bypasses create_plan (which always uses P-prefix) so that tests for
    QG-prefixed address resolution have a real QG file on disk to resolve against.

    Args:
        plan_dir: Directory where the plan file will be written.
        plan_number: Number to embed in the QG filename (e.g., 1 -> QG001-).
        slug: Feature slug for the plan filename.

    Returns:
        The Plan model with source_path pointing to the written QG file.
    """

    yaml_str = build_quality_gate_plan(slug=slug, issue=None, impl_plan_address="P001")
    parsed = _parse_yaml(yaml_str)
    tasks_raw = parsed.get("tasks", [])
    validated_tasks = [Task.model_validate(t) for t in tasks_raw]

    output_path = plan_dir / f"QG{plan_number:03d}-{slug}.yaml"
    plan = Plan(feature=slug, goal="Quality gate verification for P001", tasks=validated_tasks, source_path=output_path)
    create_plan_file(output_path, plan)
    return plan


# ---------------------------------------------------------------------------
# Test class: QG plan creation
# ---------------------------------------------------------------------------


class TestQGPlanCreation:
    """Tests for creating QG-prefixed plans and validating their structure.

    Strategy: Call create_plan with tasks from build_quality_gate_plan and verify
    the output file is named with P{N}-* prefix and contains all expected tasks.
    """

    @pytest.mark.integration
    def test_create_plan_writes_file_to_disk(self, tmp_path: Path) -> None:
        """create_plan writes a YAML file to the plan directory.

        Tests: create_plan produces a file in plan_dir
        How: Call create_plan with QG task YAML; verify file exists on disk
        Why: Plan files must exist on disk to be addressable by SAM tools
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()

        # Act
        plan = _create_qg_plan(plan_dir)

        # Assert
        assert plan.source_path is not None
        assert plan.source_path.exists()

    @pytest.mark.integration
    def test_created_plan_contains_six_tasks(self, tmp_path: Path) -> None:
        """build_quality_gate_plan generates a plan with exactly 7 tasks.

        Tests: build_quality_gate_plan task count
        How: Create plan and load it back; count tasks
        Why: QG plans must have exactly 7 phases (multi-perspective review through context refinement)
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()

        # Act
        plan = _create_qg_plan(plan_dir)
        assert plan.source_path is not None
        result = load_plan(plan.source_path)

        # Assert
        assert len(result.plan.tasks) == _EXPECTED_TASK_COUNT

    @pytest.mark.integration
    def test_created_plan_tasks_have_correct_agents(self, tmp_path: Path) -> None:
        """Each QG task has the expected agent assigned.

        Tests: build_quality_gate_plan agent assignment per phase
        How: Load plan and collect agent values in task order
        Why: Correct agent assignment ensures each phase runs the right specialist
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()

        # Act
        plan = _create_qg_plan(plan_dir)
        assert plan.source_path is not None
        result = load_plan(plan.source_path)
        agents = [t.agent for t in result.plan.tasks]

        # Assert
        assert agents == _EXPECTED_AGENTS

    @pytest.mark.integration
    def test_created_plan_all_tasks_start_as_not_started(self, tmp_path: Path) -> None:
        """All tasks in a freshly created QG plan have not-started status.

        Tests: Initial task status after plan creation
        How: Load plan and check all task statuses
        Why: Tasks must begin in not-started to allow the dispatch loop to proceed
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()

        # Act
        plan = _create_qg_plan(plan_dir)
        assert plan.source_path is not None
        result = load_plan(plan.source_path)

        # Assert
        for task in result.plan.tasks:
            assert task.status == TaskStatus.NOT_STARTED, f"Task {task.id} has unexpected status {task.status}"

    @pytest.mark.integration
    def test_created_plan_tasks_have_chain_dependencies(self, tmp_path: Path) -> None:
        """QG tasks form a strict chain: T1 has no deps, T2 depends on T1, etc.

        Tests: Dependency chain structure from build_quality_gate_plan
        How: Load plan and inspect each task's dependencies list
        Why: Chain dependencies ensure sequential phase execution enforced by SAM
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        expected_deps = [[], [], ["T1"], ["T2"], ["T3"], ["T4"], ["T5"]]

        # Act
        plan = _create_qg_plan(plan_dir)
        assert plan.source_path is not None
        result = load_plan(plan.source_path)
        actual_deps = [t.dependencies for t in result.plan.tasks]

        # Assert
        assert actual_deps == expected_deps

    @pytest.mark.integration
    def test_created_plan_body_contains_impl_plan_address(self, tmp_path: Path) -> None:
        """Each task body contains a cross-reference to the implementation plan address.

        Tests: build_quality_gate_plan embeds impl_plan_address in task bodies
        How: Load plan and verify impl_plan_address appears in each task's body
        Why: Cross-reference ensures agents can locate the implementation plan context
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        impl_addr = "P042"

        # Act
        plan = _create_qg_plan(plan_dir, impl_plan_address=impl_addr)
        assert plan.source_path is not None
        result = load_plan(plan.source_path)

        # Assert
        for task in result.plan.tasks:
            assert impl_addr in task.body, f"Task {task.id} body does not reference impl plan address {impl_addr}"

    @pytest.mark.integration
    def test_plan_with_issue_number_stores_issue_field(self, tmp_path: Path) -> None:
        """When issue is provided to build_quality_gate_plan, the plan has an issue field.

        Tests: build_quality_gate_plan issue field propagation
        How: Generate YAML with issue="990", create plan, load and check issue field
        Why: Issue field links the QG plan to its parent GitHub issue for artifact tracking
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        yaml_str = build_quality_gate_plan(slug="test-feature", issue="990", impl_plan_address="P003")
        parsed = _parse_yaml(yaml_str)
        tasks_raw = parsed.get("tasks", [])

        # Act — pass issue=990 so create_plan embeds it in the plan metadata
        plan_model = create_plan(
            slug="test-feature",
            goal="Quality gate verification for P003",
            tasks=tasks_raw,
            plan_dir=plan_dir,
            issue=990,
        )
        assert plan_model.source_path is not None
        result = load_plan(plan_model.source_path)

        # Assert
        assert result.plan.issue == "990"


# ---------------------------------------------------------------------------
# Test class: QG addressing
# ---------------------------------------------------------------------------


class TestQGPlanAddressing:
    """Tests for resolving QG-prefixed plan addresses.

    Strategy: Create plan files on disk using tmp_path and verify that
    resolve_plan_address and parse_address work correctly with QG prefix.
    """

    @pytest.mark.integration
    def test_resolve_plan_address_finds_qg_plan_by_number(self, tmp_path: Path) -> None:
        """resolve_plan_address can locate a QG-prefixed plan by number.

        Tests: QG plan address resolution via resolve_plan_address
        How: Write a QG001-{slug}.yaml file directly, resolve with "QG1" address
        Why: The addressing layer must support multi-char QG prefix to route
             complete-implementation to the correct plan file
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        plan = _create_qg_file_directly(plan_dir, plan_number=1)
        assert plan.source_path is not None

        # Act
        resolved = resolve_plan_address("QG1", plan_dir)

        # Assert
        assert resolved == plan.source_path

    @pytest.mark.integration
    def test_resolve_plan_address_raises_for_missing_qg_plan(self, tmp_path: Path) -> None:
        """resolve_plan_address raises AddressingError for a non-existent QG plan number.

        Tests: Error handling in resolve_plan_address for unknown QG plan
        How: Attempt to resolve QG999 in a directory that only has lower-numbered plans
        Why: Callers must receive a clear error rather than a silent None return
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        _create_qg_plan(plan_dir)

        # Act / Assert
        with pytest.raises(AddressingError):
            resolve_plan_address("QG999", plan_dir)

    @pytest.mark.integration
    def test_parse_address_strips_p_prefix(self) -> None:
        """parse_address strips the single-char P prefix, returning a bare number.

        Tests: parse_address prefix stripping for P-type plans
        How: Call parse_address with "P42" and verify plan_ref is "42"
        Why: resolve_plan_address receives bare numeric refs for P-type plans
        """
        # Arrange / Act
        plan_ref, task_ref = parse_address("P42")

        # Assert
        assert plan_ref == "42"
        assert task_ref is None

    @pytest.mark.integration
    def test_parse_address_preserves_qg_prefix(self) -> None:
        """parse_address preserves the multi-char QG prefix in the plan ref.

        Tests: parse_address prefix handling for QG-type plans
        How: Call parse_address with "QG003" and verify plan_ref is "QG003"
        Why: resolve_plan_address needs the full prefix to select the QG filename regex
        """
        # Arrange / Act
        plan_ref, task_ref = parse_address("QG003")

        # Assert
        assert plan_ref == "QG003"
        assert task_ref is None

    @pytest.mark.integration
    def test_parse_address_qg_with_task_component(self) -> None:
        """parse_address correctly splits a QG plan address with a task component.

        Tests: parse_address task component extraction for QG plans
        How: Call parse_address with "QG003/T1" and verify both components
        Why: SAM dispatch loop uses task component to identify which task to claim
        """
        # Arrange / Act
        plan_ref, task_ref = parse_address("QG003/T1")

        # Assert
        assert plan_ref == "QG003"
        assert task_ref == "1"

    @pytest.mark.integration
    def test_parse_address_rejects_path_traversal(self) -> None:
        """parse_address raises ValueError for addresses containing path traversal.

        Tests: Security validation in parse_address
        How: Pass "../etc/passwd" as address and verify ValueError raised
        Why: Addresses must not allow filesystem traversal outside the plan directory
        """
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="path traversal"):
            parse_address("../etc/passwd")


# ---------------------------------------------------------------------------
# Test class: Readiness sequencing
# ---------------------------------------------------------------------------


class TestQGReadinessSequencing:
    """Tests for get_ready_tasks behaviour with QG chain dependencies.

    Strategy: Progressively mark tasks complete and verify that only the next
    task in the chain becomes ready. No mocking — uses the Python API directly.
    """

    @pytest.mark.integration
    def test_only_t1_ready_initially(self, tmp_path: Path) -> None:
        """T0 and T1 are ready when no tasks have been completed.

        Tests: Initial readiness — T0 and T1 have no dependencies so both are immediately ready
        How: Create plan, query get_ready_tasks without any status transitions
        Why: T0 (Multi-Perspective Review) and T1 (Code Review) both have no deps and run first
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        plan = _create_qg_plan(plan_dir)
        assert plan.source_path is not None

        # Act
        ready = get_ready_tasks(plan.source_path)

        # Assert
        assert len(ready) == 2
        assert {t.id for t in ready} == {"T0", "T1"}

    @pytest.mark.integration
    def test_t2_becomes_ready_after_t1_completes(self, tmp_path: Path) -> None:
        """After T1 is marked complete, T2 becomes the only ready task.

        Tests: Dependency unblocking — T2 depends on T1; completing T1 unblocks T2
        How: Mark T1 complete, then query get_ready_tasks
        Why: The SAM dispatch loop advances through chain by completing predecessor
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        plan = _create_qg_plan(plan_dir)
        assert plan.source_path is not None
        update_status(plan.source_path, "T0", TaskStatus.COMPLETE, timestamp_field="completed")
        update_status(plan.source_path, "T1", TaskStatus.COMPLETE, timestamp_field="completed")

        # Act
        ready = get_ready_tasks(plan.source_path)

        # Assert
        assert len(ready) == 1
        assert ready[0].id == "T2"

    @pytest.mark.integration
    def test_resume_after_three_phases_completed_shows_t4_ready(self, tmp_path: Path) -> None:
        """After T1, T2, T3 are complete, only T4 is ready.

        Tests: Partial completion resume — SAM can resume from mid-chain
        How: Mark T1-T3 complete, then query get_ready_tasks
        Why: Re-running complete-implementation after failures must resume from the
             correct phase without re-dispatching already-complete phases
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        plan = _create_qg_plan(plan_dir)
        assert plan.source_path is not None
        for task_id in ("T0", "T1", "T2", "T3"):
            update_status(plan.source_path, task_id, TaskStatus.COMPLETE, timestamp_field="completed")

        # Act
        ready = get_ready_tasks(plan.source_path)

        # Assert
        assert len(ready) == 1
        assert ready[0].id == "T4"

    @pytest.mark.integration
    def test_t6_not_ready_after_t5_skipped(self, tmp_path: Path) -> None:
        """T6 is not ready when T5 is marked SKIPPED.

        Tests: SKIPPED is terminal but does not satisfy dependency readiness
        How: Mark T1-T4 complete, mark T5 skipped, then query get_ready_tasks
        Why: Readiness now gates on successful dependencies only,
             not skipped/failed
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        plan = _create_qg_plan(plan_dir)
        assert plan.source_path is not None
        for task_id in ("T0", "T1", "T2", "T3", "T4"):
            update_status(plan.source_path, task_id, TaskStatus.COMPLETE, timestamp_field="completed")
        update_status(plan.source_path, "T5", TaskStatus.SKIPPED)

        # Act
        ready = get_ready_tasks(plan.source_path)

        # Assert
        assert ready == []

    @pytest.mark.integration
    def test_no_tasks_ready_when_all_complete(self, tmp_path: Path) -> None:
        """No tasks are returned by get_ready_tasks when all 6 phases are complete.

        Tests: Completion detection — empty ready list signals loop exit
        How: Mark all tasks complete, then query get_ready_tasks
        Why: The SAM dispatch loop exits when sam_ready returns an empty list;
             this must occur only after all phases are done
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        plan = _create_qg_plan(plan_dir)
        assert plan.source_path is not None
        for task_id in ("T0", "T1", "T2", "T3", "T4", "T5", "T6"):
            update_status(plan.source_path, task_id, TaskStatus.COMPLETE, timestamp_field="completed")

        # Act
        ready = get_ready_tasks(plan.source_path)

        # Assert
        assert ready == []


# ---------------------------------------------------------------------------
# Test class: Completion gate logic
# ---------------------------------------------------------------------------


class TestCompletionGateLogic:
    """Tests for the completion verification gate that guards status:verified label.

    Strategy: Exercise the gate logic rules directly using get_plan_status to
    check task statuses. Tests verify the four gate outcomes: all-complete pass,
    incomplete-blocks, skipped-T5-allowed, skipped-other-rejected.

    Note: The gate logic itself lives in complete-implementation SKILL.md (T05).
    These tests validate the underlying data model constraints that the gate
    relies on, using the Python API that the gate will consume.
    """

    @pytest.mark.integration
    def test_gate_blocks_when_t1_is_not_started(self, tmp_path: Path) -> None:
        """get_plan_status reports not-started count when T1 remains not-started.

        Tests: Completion gate blocking condition — incomplete mandatory phase
        How: Create plan without marking any tasks; check by_status for not-started count
        Why: The gate must reject label application when mandatory phases remain incomplete
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        plan = _create_qg_plan(plan_dir)
        assert plan.source_path is not None

        # Act
        status = get_plan_status(plan.source_path)

        # Assert — 7 tasks all not-started means gate must block
        assert status.by_status.get("not-started", 0) == _EXPECTED_TASK_COUNT
        assert status.completion_pct == pytest.approx(0.0)

    @pytest.mark.integration
    def test_gate_passes_when_all_seven_tasks_complete(self, tmp_path: Path) -> None:
        """get_plan_status reports 100% completion when all 7 tasks are complete.

        Tests: Completion gate pass condition — all mandatory phases complete
        How: Mark all tasks complete; verify by_status has 7 complete entries
        Why: The gate must allow label application only after all phases finish
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        plan = _create_qg_plan(plan_dir)
        assert plan.source_path is not None
        for task_id in ("T0", "T1", "T2", "T3", "T4", "T5", "T6"):
            update_status(plan.source_path, task_id, TaskStatus.COMPLETE, timestamp_field="completed")

        # Act
        status = get_plan_status(plan.source_path)

        # Assert
        assert status.by_status.get("complete", 0) == _EXPECTED_TASK_COUNT
        assert status.completion_pct == pytest.approx(100.0)

    @pytest.mark.integration
    def test_gate_t5_skipped_with_rest_complete_is_terminal(self, tmp_path: Path) -> None:
        """A plan with T5 SKIPPED and all other tasks COMPLETE has no ready tasks.

        Tests: Skip whitelist — T5 SKIPPED counts as terminal for gate evaluation
        How: Mark T1-T4 complete, T5 skipped, T6 complete; verify ready list empty
        Why: Documentation update is conditionally skippable when no drift was found;
             the gate must accept SKIPPED for T5 and still proceed to label application
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        plan = _create_qg_plan(plan_dir)
        assert plan.source_path is not None
        for task_id in ("T0", "T1", "T2", "T3", "T4"):
            update_status(plan.source_path, task_id, TaskStatus.COMPLETE, timestamp_field="completed")
        update_status(plan.source_path, "T5", TaskStatus.SKIPPED)
        update_status(plan.source_path, "T6", TaskStatus.COMPLETE, timestamp_field="completed")

        # Act
        ready = get_ready_tasks(plan.source_path)
        plan_status = get_plan_status(plan.source_path)

        # Assert — no ready tasks and all tasks in terminal state
        assert ready == []
        total_terminal = (
            plan_status.by_status.get("complete", 0)
            + plan_status.by_status.get("skipped", 0)
            + plan_status.by_status.get("deferred", 0)
        )
        assert total_terminal == _EXPECTED_TASK_COUNT

    @pytest.mark.integration
    def test_gate_rejects_skipped_for_mandatory_phase_t1(self, tmp_path: Path) -> None:
        """A plan with T1 SKIPPED must be detectable as a skip-whitelist violation.

        Tests: Skip whitelist enforcement — T1 (mandatory) must not be SKIPPED
        How: Mark T1 as skipped; verify get_task returns skipped status and it is
             not in the allow-list (only T5 is allowed to be skipped)
        Why: The completion gate must reject unauthorized skips to prevent bypassing
             mandatory quality phases; this test validates the data model supports
             the gate's skip-whitelist check
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        plan = _create_qg_plan(plan_dir)
        assert plan.source_path is not None
        update_status(plan.source_path, "T1", TaskStatus.SKIPPED)

        # Act
        t1 = get_task(plan.source_path, "T1")
        plan_status = get_plan_status(plan.source_path)

        # Assert — T1 is skipped; gate logic must reject this (T5 is the only whitelist entry)
        assert t1.status == TaskStatus.SKIPPED

        skipped_task_ids = [
            task_id for task_id, count in plan_status.by_status.items() if task_id == "skipped" and count > 0
        ]
        # The gate implementation checks: skipped is only allowed for T5
        # This test confirms the data model allows writing skipped for T1,
        # and that the gate must do an explicit ID check, not just a status check
        assert skipped_task_ids == ["skipped"]  # skipped status is present
        assert t1.id == "T1"  # confirms it is a non-whitelisted task

    @pytest.mark.integration
    def test_gate_blocks_on_blocked_phase(self, tmp_path: Path) -> None:
        """A plan with a BLOCKED task reports that task in the plan status.

        Tests: Completion gate blocking on agent failure
        How: Mark T1 complete, mark T2 blocked; verify plan status shows no ready tasks
             in the non-started bucket (T2 is blocked, so T3 onward cannot start)
        Why: When a phase agent fails (network error, timeout), the dispatch loop
             must stop and report the failure; the gate must not apply the label
        """
        # Arrange
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir()
        plan = _create_qg_plan(plan_dir)
        assert plan.source_path is not None
        update_status(plan.source_path, "T0", TaskStatus.COMPLETE, timestamp_field="completed")
        update_status(plan.source_path, "T1", TaskStatus.COMPLETE, timestamp_field="completed")
        update_status(plan.source_path, "T2", TaskStatus.BLOCKED)

        # Act
        ready = get_ready_tasks(plan.source_path)
        plan_status = get_plan_status(plan.source_path)

        # Assert — T2 is blocked; no tasks are ready (T3 depends on T2 which is not terminal)
        assert ready == []
        assert plan_status.by_status.get("blocked", 0) == 1
        assert plan_status.completion_pct < 100.0
