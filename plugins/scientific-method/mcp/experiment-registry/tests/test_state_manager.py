"""Unit and integration tests for state_manager.py.

Tests: StateManager.complete_step() — validation failure isolation, hash storage,
  backward compatibility deserialization, and rubric_scores audit trail.
Strategy: Mock RegistryLoader to isolate state_manager from JSON file changes.
  Use real StateManager with tmp_path-backed filesystem.
  Verify state file on disk rather than only the return value.
Coverage target: >=80% of state_manager.py.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest
from models import ArtefactIntegrity, ExperimentState, StepDefinition, ValidationRule
from state_manager import StateManager

if TYPE_CHECKING:
    from pathlib import Path

# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def step_hypothesis() -> StepDefinition:
    """Return the hypothesis StepDefinition with validation rules.

    Returns:
        StepDefinition for the hypothesis step.
    """
    return StepDefinition(
        id="hypothesis",
        name="State hypothesis",
        required_artefacts=["hypothesis.md"],
        validation_rules=[
            ValidationRule(type="non_empty", params={}),
            ValidationRule(
                type="required_sections",
                params={"sections": ["HYPOTHESIS:", "CURRENT BEHAVIOUR:", "SUCCESS CRITERION:"]},
            ),
        ],
        frozen_artefacts=[],
    )


@pytest.fixture
def step_fixture_def() -> StepDefinition:
    """Return the fixture StepDefinition with freeze.

    Returns:
        StepDefinition for the fixture step (freezes fixture.md).
    """
    return StepDefinition(
        id="fixture",
        name="Build fixture",
        required_artefacts=["fixture.md"],
        validation_rules=[ValidationRule(type="non_empty", params={})],
        frozen_artefacts=["fixture.md"],
    )


@pytest.fixture
def step_rubric_def() -> StepDefinition:
    """Return the rubric StepDefinition with freeze and min_criteria_count.

    Returns:
        StepDefinition for the rubric step (freezes rubric.md).
    """
    return StepDefinition(
        id="rubric",
        name="Write rubric",
        required_artefacts=["rubric.md"],
        validation_rules=[
            ValidationRule(type="non_empty", params={}),
            ValidationRule(type="min_criteria_count", params={"min": 1}),
        ],
        frozen_artefacts=["rubric.md"],
    )


@pytest.fixture
def step_baseline_def() -> StepDefinition:
    """Return the baseline StepDefinition.

    Returns:
        StepDefinition for the baseline step.
    """
    return StepDefinition(
        id="baseline",
        name="Run baseline",
        required_artefacts=["output-iter0.md", "log.md"],
        validation_rules=[ValidationRule(type="non_empty", params={})],
        frozen_artefacts=[],
    )


@pytest.fixture
def step_iterate_def() -> StepDefinition:
    """Return the iterate StepDefinition.

    Returns:
        StepDefinition for the iterate step.
    """
    return StepDefinition(
        id="iterate",
        name="Iterate",
        required_artefacts=["log.md"],
        validation_rules=[
            ValidationRule(type="non_empty", params={}),
            ValidationRule(type="required_sections", params={"sections": ["## Iteration"]}),
        ],
        frozen_artefacts=[],
    )


@pytest.fixture
def all_steps(
    step_hypothesis, step_fixture_def, step_rubric_def, step_baseline_def, step_iterate_def
) -> list[StepDefinition]:
    """Return all five experiment steps in protocol order.

    Returns:
        Ordered list of all StepDefinition objects.
    """
    return [step_hypothesis, step_fixture_def, step_rubric_def, step_baseline_def, step_iterate_def]


@pytest.fixture
def state_manager(tmp_path: Path, mock_loader, all_steps) -> StateManager:
    """Construct a StateManager backed by tmp_path with a mock RegistryLoader.

    The loader is pre-configured to return all_steps from merge_type.

    Args:
        tmp_path: Pytest tmp_path fixture.
        mock_loader: MagicMock RegistryLoader.
        all_steps: Full ordered step list.

    Returns:
        Configured StateManager instance.
    """
    mock_loader.merge_type.return_value = all_steps
    return StateManager(project_root=tmp_path, loader=mock_loader)


def _write_valid_state(
    tmp_path: Path,
    experiment_id: str,
    current_step: str,
    steps: list[StepDefinition],
    *,
    artefacts: dict[str, str] | None = None,
    artefact_integrity: dict[str, ArtefactIntegrity] | None = None,
    status: str = "in_progress",
    iteration_count: int = 0,
) -> ExperimentState:
    """Write an ExperimentState to disk and return it.

    Args:
        tmp_path: Base project root directory.
        experiment_id: Unique experiment identifier.
        current_step: Current active step ID.
        steps: Merged step definitions.
        artefacts: Existing artefacts dict (default empty).
        artefact_integrity: Integrity records (default empty).
        status: Experiment status string.
        iteration_count: Number of completed iterate steps.

    Returns:
        The ExperimentState that was written.
    """
    state = ExperimentState(
        id=experiment_id,
        base="experiment_core",
        current_step=current_step,
        status=status,
        iteration_count=iteration_count,
        merged_steps=steps,
        artefacts=artefacts or {},
        artefact_integrity=artefact_integrity or {},
    )
    state_path = tmp_path / ".claude" / "experiments" / experiment_id / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    return state


def _read_state(tmp_path: Path, experiment_id: str) -> dict:
    """Read the persisted state JSON from disk and return it as a dict.

    Args:
        tmp_path: Base project root directory.
        experiment_id: Unique experiment identifier.

    Returns:
        Raw state dict loaded from JSON.
    """
    state_path = tmp_path / ".claude" / "experiments" / experiment_id / "state.json"
    return json.loads(state_path.read_text(encoding="utf-8"))


# ===========================================================================
# Validation failure does not mutate state
# ===========================================================================


class TestValidationFailureIsolation:
    """Tests: Validation errors must not mutate the state file.

    Tests: StateManager.complete_step() isolation on validation failure.
    How: Read state file before and after a failed complete_step; assert unchanged.
    Why: Atomic validation ensures partial failures leave no corrupted state behind.
    """

    def test_empty_artefact_rejection_leaves_state_unchanged(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that state file is unchanged after a validation failure.

        Tests: complete_step with empty hypothesis.md (non_empty rule violation)
        How: Write state, write empty artefact file, call complete_step,
          compare state JSON before and after.
        Why: Validation failures must be atomic — no partial state changes allowed.
        """
        experiment_id = "exp-test-iso-001"
        _write_valid_state(tmp_path, experiment_id, "hypothesis", all_steps)

        # Write an empty file as the artefact
        exp_dir = tmp_path / ".claude" / "experiments" / experiment_id
        empty_file = exp_dir / "hypothesis.md"
        empty_file.write_text("", encoding="utf-8")

        before = _read_state(tmp_path, experiment_id)

        result = state_manager.complete_step(experiment_id, "hypothesis", {"hypothesis.md": str(empty_file)})

        after = _read_state(tmp_path, experiment_id)

        assert result["success"] is False
        assert "validation_errors" in result
        # State file content must be identical before and after failure
        assert before == after

    def test_validation_errors_returned_in_response(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that validation_errors key is present in failure response.

        Tests: complete_step returns structured validation_errors on content failure
        How: Submit an empty hypothesis.md; verify response structure.
        Why: Callers need structured errors to present actionable feedback.
        """
        experiment_id = "exp-test-iso-002"
        _write_valid_state(tmp_path, experiment_id, "hypothesis", all_steps)

        exp_dir = tmp_path / ".claude" / "experiments" / experiment_id
        empty_file = exp_dir / "hypothesis.md"
        empty_file.write_text("   ", encoding="utf-8")

        result = state_manager.complete_step(experiment_id, "hypothesis", {"hypothesis.md": str(empty_file)})

        assert result["success"] is False
        errors = result["validation_errors"]
        assert isinstance(errors, list)
        assert len(errors) >= 1
        # Each error must have at minimum 'code' and 'message' keys
        for error in errors:
            assert isinstance(error, dict)
            assert "code" in error
            assert "message" in error


# ===========================================================================
# Frozen artefact hash storage
# ===========================================================================


class TestFrozenArtefactHashStorage:
    """Tests: SHA-256 hashes of frozen artefacts are stored in state after step completion.

    Tests: _compute_frozen_hashes via complete_step success path.
    How: Complete the fixture step with a valid file; verify artefact_integrity in persisted state.
    Why: Freeze hashes enable integrity verification on subsequent steps (AC3).
    """

    def test_frozen_artefact_hash_stored_after_step_completes(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that completing a freezing step stores the artefact hash.

        Tests: complete_step stores SHA-256 for frozen_artefacts after success
        How: Complete fixture step with valid fixture.md; read state from disk;
          verify artefact_integrity['fixture.md'] has correct sha256.
        Why: The hash must be stored at freeze-point for later integrity verification.
        """
        experiment_id = "exp-test-hash-001"

        # Start at fixture step (hypothesis already done)
        _write_valid_state(tmp_path, experiment_id, "fixture", all_steps, artefacts={}, artefact_integrity={})

        exp_dir = tmp_path / ".claude" / "experiments" / experiment_id
        fixture_content = b"this is the fixture content"
        fixture_file = exp_dir / "fixture.md"
        fixture_file.write_bytes(fixture_content)
        expected_hash = hashlib.sha256(fixture_content).hexdigest()

        result = state_manager.complete_step(experiment_id, "fixture", {"fixture.md": str(fixture_file)})

        assert result["success"] is True

        state_dict = _read_state(tmp_path, experiment_id)
        integrity = state_dict.get("artefact_integrity", {})
        assert "fixture.md" in integrity
        assert integrity["fixture.md"]["sha256"] == expected_hash
        assert integrity["fixture.md"]["frozen_by_step"] == "fixture"

    def test_non_frozen_step_does_not_store_integrity(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that completing a non-freezing step does not add integrity records.

        Tests: _compute_frozen_hashes is a no-op when frozen_artefacts is empty
        How: Complete hypothesis step (no frozen_artefacts); verify artefact_integrity stays empty.
        Why: Non-freezing steps must not pollute the integrity dict.
        """
        experiment_id = "exp-test-hash-002"
        _write_valid_state(tmp_path, experiment_id, "hypothesis", all_steps)

        exp_dir = tmp_path / ".claude" / "experiments" / experiment_id
        hyp_content = "HYPOTHESIS: something\nCURRENT BEHAVIOUR: observed\nSUCCESS CRITERION: criterion"
        hyp_file = exp_dir / "hypothesis.md"
        hyp_file.write_text(hyp_content, encoding="utf-8")

        result = state_manager.complete_step(experiment_id, "hypothesis", {"hypothesis.md": str(hyp_file)})

        assert result["success"] is True
        state_dict = _read_state(tmp_path, experiment_id)
        assert state_dict.get("artefact_integrity", {}) == {}


# ===========================================================================
# Backward compatibility
# ===========================================================================


class TestBackwardCompatibility:
    """Tests: ExperimentState with no artefact_integrity field deserializes correctly.

    Tests: Pydantic default_factory for artefact_integrity field.
    How: Write state JSON without the artefact_integrity key; load via StateManager.
    Why: Existing persisted states pre-dating this feature must still be loadable.
    """

    def test_state_without_artefact_integrity_loads_with_empty_dict(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that a state file missing artefact_integrity defaults to empty dict.

        Tests: ExperimentState backward compatibility deserialization
        How: Write a state JSON without artefact_integrity key; load it via load_experiment;
          assert artefact_integrity is an empty dict.
        Why: Any existing experiments in the field will lack this field; they must not crash.
        """
        experiment_id = "exp-test-compat-001"
        state = ExperimentState(
            id=experiment_id, base="experiment_core", current_step="hypothesis", merged_steps=all_steps
        )

        # Write state without artefact_integrity (simulate pre-feature state)
        raw = json.loads(state.model_dump_json())
        raw.pop("artefact_integrity", None)

        state_path = tmp_path / ".claude" / "experiments" / experiment_id / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

        loaded = state_manager.load_experiment(experiment_id)
        assert loaded.artefact_integrity == {}

    def test_state_with_empty_artefact_integrity_dict_loads_correctly(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that a state file with an explicit empty artefact_integrity dict loads.

        Tests: ExperimentState backward compatibility with explicit empty dict
        How: Write state JSON with artefact_integrity={}; load via load_experiment;
          assert artefact_integrity is an empty dict.
        Why: States written after the feature ships will have an explicit empty dict;
          this is the canonical backward-compatible on-disk format.

        Note: Pydantic v2 with Field(default_factory=dict) does NOT accept null/None
        for a dict-typed field. That is intentional strict validation. States written
        by experiment_core.json always include artefact_integrity as an object (empty
        or populated), never as null.
        """
        experiment_id = "exp-test-compat-002"
        raw = {
            "id": experiment_id,
            "base": "experiment_core",
            "current_step": "hypothesis",
            "artefact_integrity": {},  # Explicit empty dict — the canonical format
            "merged_steps": [s.model_dump() for s in all_steps],
            "extensions": [],
            "inline_extensions": {},
            "completed_steps": [],
            "artefacts": {},
            "context": "",
            "iteration_count": 0,
            "max_iterations": 10,
            "status": "in_progress",
            "created": "2026-01-01T00:00:00+00:00",
            "last_updated": "2026-01-01T00:00:00+00:00",
        }
        state_path = tmp_path / ".claude" / "experiments" / experiment_id / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

        loaded = state_manager.load_experiment(experiment_id)
        assert loaded.artefact_integrity == {}


# ===========================================================================
# rubric_scores storage
# ===========================================================================


class TestRubricScoresStorage:
    """Tests: rubric_scores are stored as JSON under rubric_scores_iterN in state.artefacts.

    Tests: _complete_iterate_step rubric audit trail.
    How: Complete the iterate step with valid artefacts and scores; verify persisted artefacts.
    Why: Audit trail of per-iteration scores prevents post-hoc score manipulation.
    """

    def test_rubric_scores_stored_as_json_in_artefacts(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that rubric_scores are stored as JSON string in state.artefacts.

        Tests: complete_step with iterate step stores rubric_scores_iter1 in artefacts
        How: Advance experiment to iterate step; complete it with scores;
          read state JSON and verify rubric_scores_iter1 key.
        Why: Stored scores form an immutable audit trail of each iteration's evaluation.
        """
        experiment_id = "exp-test-rubric-001"
        exp_dir = tmp_path / ".claude" / "experiments" / experiment_id

        # Write rubric.md content for criteria discovery
        rubric_file = exp_dir / "rubric.md"
        rubric_file.parent.mkdir(parents=True, exist_ok=True)
        rubric_file.write_text("## criterion_1\n- [ ] passes\n", encoding="utf-8")

        # Set up state at iterate step with iteration_count=0
        _write_valid_state(
            tmp_path, experiment_id, "iterate", all_steps, artefacts={"rubric.md": str(rubric_file)}, iteration_count=0
        )

        # Write required artefacts
        log_file = exp_dir / "log.md"
        log_file.write_text("## Iteration 1\nSome log entry.", encoding="utf-8")
        iter1_file = exp_dir / "output-iter1.md"
        iter1_file.write_text("Output content for iteration 1.", encoding="utf-8")

        scores = {"criterion_1": True}

        result = state_manager.complete_step(
            experiment_id,
            "iterate",
            {"log.md": str(log_file), "output-iter1.md": str(iter1_file)},
            rubric_scores=scores,
        )

        assert result["success"] is True

        state_dict = _read_state(tmp_path, experiment_id)
        artefacts = state_dict["artefacts"]
        assert "rubric_scores_iter1" in artefacts
        stored_scores = json.loads(artefacts["rubric_scores_iter1"])
        assert stored_scores == scores

    def test_rubric_scores_key_increments_with_iteration_count(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that second iterate call stores rubric_scores_iter2.

        Tests: rubric_scores audit key uses incremented iteration_count
        How: Set iteration_count=1 (second iterate call); complete iterate;
          verify rubric_scores_iter2 key in persisted state.
        Why: Each iteration's scores must be stored separately and not overwrite previous.
        """
        experiment_id = "exp-test-rubric-002"
        exp_dir = tmp_path / ".claude" / "experiments" / experiment_id

        rubric_file = exp_dir / "rubric.md"
        rubric_file.parent.mkdir(parents=True, exist_ok=True)
        rubric_file.write_text("## criterion_1\n- [ ] passes\n", encoding="utf-8")

        _write_valid_state(
            tmp_path,
            experiment_id,
            "iterate",
            all_steps,
            artefacts={"rubric.md": str(rubric_file), "rubric_scores_iter1": json.dumps({"criterion_1": False})},
            iteration_count=1,  # Second iteration
        )

        log_file = exp_dir / "log.md"
        log_file.write_text("## Iteration 2\nSome log entry.", encoding="utf-8")
        iter2_file = exp_dir / "output-iter2.md"
        iter2_file.write_text("Output content for iteration 2.", encoding="utf-8")

        scores = {"criterion_1": True}

        result = state_manager.complete_step(
            experiment_id,
            "iterate",
            {"log.md": str(log_file), "output-iter2.md": str(iter2_file)},
            rubric_scores=scores,
        )

        assert result["success"] is True
        state_dict = _read_state(tmp_path, experiment_id)
        # Both iterations' scores are present
        assert "rubric_scores_iter1" in state_dict["artefacts"]
        assert "rubric_scores_iter2" in state_dict["artefacts"]
        stored = json.loads(state_dict["artefacts"]["rubric_scores_iter2"])
        assert stored == scores


# ===========================================================================
# Additional StateManager API coverage
# ===========================================================================


class TestStateManagerAdditionalAPI:
    """Tests: create_experiment, load_experiment error, get_current_step, list_experiments,
    get_experiment_summary, complete_step error branches.

    Tests: StateManager public API surface not covered by other test classes.
    How: Construct real StateManager against tmp_path; exercise each public method.
    Why: Comprehensive coverage ensures all public contracts are verified.
    """

    def test_load_experiment_raises_for_missing_id(self, tmp_path: Path, state_manager: StateManager) -> None:
        """Validate that load_experiment raises ValueError when state file does not exist.

        Tests: StateManager.load_experiment() missing file error path (lines 274-275)
        How: Call load_experiment with an ID that has no state.json on disk.
        Why: Missing experiment must raise, not return None or a corrupt object.
        """
        with pytest.raises(ValueError, match="not found"):
            state_manager.load_experiment("nonexistent-exp-999")

    def test_complete_step_raises_for_wrong_step_id(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that complete_step raises ValueError when step_id != current_step.

        Tests: StateManager.complete_step() step mismatch ValueError (lines 334-338)
        How: Persist state at 'hypothesis'; call complete_step with 'fixture'.
        Why: Step ordering is enforced strictly; wrong step ID is a programming error.
        """
        experiment_id = "exp-test-api-001"
        _write_valid_state(tmp_path, experiment_id, "hypothesis", all_steps)

        with pytest.raises(ValueError, match="current step"):
            state_manager.complete_step(experiment_id, "fixture", {"fixture.md": "fixture.md"})

    def test_complete_step_returns_missing_artefacts_on_incomplete_submission(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that missing required artefacts return success=False with missing_artefacts key.

        Tests: StateManager.complete_step() missing artefacts branch (lines 355-362)
        How: Persist state at hypothesis; call complete_step without hypothesis.md.
        Why: Missing artefacts must be reported so the agent knows what to provide.
        """
        experiment_id = "exp-test-api-002"
        _write_valid_state(tmp_path, experiment_id, "hypothesis", all_steps)

        result = state_manager.complete_step(
            experiment_id,
            "hypothesis",
            {},  # no artefacts at all
        )

        assert result["success"] is False
        assert "missing_artefacts" in result
        missing = result["missing_artefacts"]
        assert isinstance(missing, list)
        assert "hypothesis.md" in missing

    def test_complete_step_advances_to_next_step_on_success(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that complete_step advances current_step to the next step in the list.

        Tests: StateManager.complete_step() standard step advancement
        How: Complete hypothesis step with valid content; verify next_step is 'fixture'.
        Why: Experiment must progress through the ordered step sequence.
        """
        experiment_id = "exp-test-api-003"
        exp_dir = tmp_path / ".claude" / "experiments" / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        _write_valid_state(tmp_path, experiment_id, "hypothesis", all_steps)

        hyp_file = exp_dir / "hypothesis.md"
        hyp_file.write_text(
            "HYPOTHESIS: something\nCURRENT BEHAVIOUR: observed\nSUCCESS CRITERION: criterion", encoding="utf-8"
        )

        result = state_manager.complete_step(experiment_id, "hypothesis", {"hypothesis.md": str(hyp_file)})

        assert result["success"] is True
        assert result["next_step"] == "fixture"

    def test_get_current_step_returns_step_definition(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that get_current_step returns the StepDefinition for current_step.

        Tests: StateManager.get_current_step() (lines 292-299)
        How: Persist state at 'fixture'; call get_current_step; verify returned step.
        Why: get_current_step is used by the MCP server to show the active step to agents.
        """
        experiment_id = "exp-test-api-004"
        _write_valid_state(tmp_path, experiment_id, "fixture", all_steps)

        step = state_manager.get_current_step(experiment_id)
        assert step.id == "fixture"

    def test_list_experiments_returns_empty_when_no_experiments_exist(
        self, tmp_path: Path, state_manager: StateManager
    ) -> None:
        """Validate that list_experiments returns empty list when no experiments exist.

        Tests: StateManager.list_experiments() empty case (lines 405-411)
        How: Ensure no state.json files exist; call list_experiments.
        Why: Fresh project must handle empty experiment list gracefully.
        """
        experiments = state_manager.list_experiments()
        assert experiments == []

    def test_list_experiments_returns_all_persisted_experiments(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that list_experiments returns one entry per persisted state file.

        Tests: StateManager.list_experiments() populated case
        How: Persist two state files; call list_experiments; verify count.
        Why: list_experiments drives the MCP list-experiments tool.
        """
        _write_valid_state(tmp_path, "exp-list-001", "hypothesis", all_steps)
        _write_valid_state(tmp_path, "exp-list-002", "fixture", all_steps)

        experiments = state_manager.list_experiments()
        assert len(experiments) == 2
        ids = {e.id for e in experiments}
        assert "exp-list-001" in ids
        assert "exp-list-002" in ids

    def test_get_experiment_summary_returns_expected_keys(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that get_experiment_summary returns a dict with all expected keys.

        Tests: StateManager.get_experiment_summary() (lines 427-428)
        How: Persist a state; call get_experiment_summary; verify key set.
        Why: Summary is returned to MCP clients for experiment status display.
        """
        experiment_id = "exp-test-summary-001"
        _write_valid_state(tmp_path, experiment_id, "hypothesis", all_steps)

        summary = state_manager.get_experiment_summary(experiment_id)

        expected_keys = {
            "id",
            "base",
            "status",
            "context",
            "created",
            "last_updated",
            "completed_steps",
            "artefacts",
            "iteration_count",
        }
        assert expected_keys.issubset(summary.keys())
        assert summary["id"] == experiment_id
        assert summary["status"] == "in_progress"

    def test_iterate_step_loops_when_criteria_not_all_passed(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that iterate step loops back when not all rubric criteria pass.

        Tests: _complete_iterate_step loop branch (lines 214-217)
        How: Complete iterate with all criteria failing; verify next_step is 'iterate'.
        Why: Experiment must remain in iterate when criteria are not all passing.
        """
        experiment_id = "exp-test-loop-001"
        exp_dir = tmp_path / ".claude" / "experiments" / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)

        _write_valid_state(tmp_path, experiment_id, "iterate", all_steps, iteration_count=0)

        log_file = exp_dir / "log.md"
        log_file.write_text("## Iteration 1\nLog entry.", encoding="utf-8")
        iter1_file = exp_dir / "output-iter1.md"
        iter1_file.write_text("Output.", encoding="utf-8")

        result = state_manager.complete_step(
            experiment_id,
            "iterate",
            {"log.md": str(log_file), "output-iter1.md": str(iter1_file)},
            rubric_scores={"criterion_1": False},  # All fail — loop back
        )

        assert result["success"] is True
        assert result["next_step"] == "iterate"
        assert result["status"] == "in_progress"

    def test_iterate_step_marks_inconclusive_at_max_iterations(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that iterate step marks experiment inconclusive at max_iterations.

        Tests: _complete_iterate_step inconclusive branch (lines 208-212)
        How: Set iteration_count to max_iterations-1; complete iterate with fail scores.
        Why: Experiments must not loop indefinitely; max_iterations enforces a ceiling.
        """
        experiment_id = "exp-test-inconclusive-001"
        exp_dir = tmp_path / ".claude" / "experiments" / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)

        # iteration_count = max_iterations - 1 so after increment it equals max
        _write_valid_state(
            tmp_path,
            experiment_id,
            "iterate",
            all_steps,
            iteration_count=9,  # max_iterations default is 10
        )

        log_file = exp_dir / "log.md"
        log_file.write_text("## Iteration 10\nFinal log.", encoding="utf-8")
        iter10_file = exp_dir / "output-iter10.md"
        iter10_file.write_text("Final output.", encoding="utf-8")

        result = state_manager.complete_step(
            experiment_id,
            "iterate",
            {"log.md": str(log_file), "output-iter10.md": str(iter10_file)},
            rubric_scores={"criterion_1": False},
        )

        assert result["success"] is True
        assert result["next_step"] is None
        assert result["status"] == "inconclusive"

    def test_create_experiment_persists_state_and_returns_experiment_state(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition]
    ) -> None:
        """Validate that create_experiment writes a state file and returns ExperimentState.

        Tests: StateManager.create_experiment() (lines 242-258) and _generate_id (84-90)
        How: Call create_experiment with 'experiment_core'; verify state file exists.
        Why: create_experiment is the entry point for starting a new experiment.
        """
        state = state_manager.create_experiment(base="experiment_core", context="Testing experiment creation")

        assert state.id.startswith("exp-")
        assert state.base == "experiment_core"
        assert state.status == "in_progress"

        state_path = tmp_path / ".claude" / "experiments" / state.id / "state.json"
        assert state_path.exists()

    def test_complete_step_marks_complete_after_last_step(
        self, tmp_path: Path, state_manager: StateManager, all_steps: list[StepDefinition], mock_loader
    ) -> None:
        """Validate that completing the last non-iterate step marks experiment complete.

        Tests: StateManager.complete_step() last step → status=complete (lines 390-391)
        How: Use a two-step custom step list; complete the second step.
        Why: Experiments without an iterate step must complete after the final step.
        """
        # Build a minimal two-step list: only hypothesis and fixture
        two_steps = all_steps[:2]  # hypothesis, fixture
        mock_loader.merge_type.return_value = two_steps

        experiment_id = "exp-test-last-step-001"
        exp_dir = tmp_path / ".claude" / "experiments" / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)

        _write_valid_state(
            tmp_path,
            experiment_id,
            "fixture",
            two_steps,  # Only two steps — fixture is last
            artefacts={},
        )

        fixture_file = exp_dir / "fixture.md"
        fixture_file.write_text("Clean fixture content.", encoding="utf-8")

        result = state_manager.complete_step(experiment_id, "fixture", {"fixture.md": str(fixture_file)})

        assert result["success"] is True
        assert result["next_step"] is None
        state_dict = _read_state(tmp_path, experiment_id)
        assert state_dict["status"] == "complete"

    def test_complete_step_human_input_required_returns_blocked(
        self, tmp_path: Path, all_steps: list[StepDefinition], mock_loader
    ) -> None:
        """Validate that a step with human_input_required returns blocked response.

        Tests: StateManager.complete_step() human_input_required branch (lines 355-362)
        How: Create a step with human_input_required=True; call complete_step with no artefacts.
        Why: Steps requiring human input must signal this rather than returning missing artefacts.
        """
        human_step = StepDefinition(
            id="human_step",
            name="Human Required Step",
            required_artefacts=["human_artefact.md"],
            validation_rules=[],
            frozen_artefacts=[],
            human_input_required=True,
            human_input_description="Provide the human artefact",
        )
        custom_steps = [human_step]

        mock_loader.merge_type.return_value = custom_steps
        manager = StateManager(project_root=tmp_path, loader=mock_loader)

        experiment_id = "exp-test-human-001"
        _write_valid_state(tmp_path, experiment_id, "human_step", custom_steps)

        result = manager.complete_step(
            experiment_id,
            "human_step",
            {},  # Empty artefacts → triggers missing
        )

        assert result["success"] is False
        assert result.get("blocked_on_human_input") is True
