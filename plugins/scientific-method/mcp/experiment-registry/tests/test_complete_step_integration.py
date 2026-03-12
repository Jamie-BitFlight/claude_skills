"""Integration tests for complete_step — one test per acceptance criterion.

Tests: AC1-AC6 end-to-end validation through the real StateManager pipeline.
Strategy: Use real validators (not mocked); mock only RegistryLoader to avoid
  JSON file dependency. Each test exercises one acceptance criterion in isolation.
Coverage goal: Each AC test must pass with a real StateManager + real filesystem.

AC1: Empty artefact content is rejected (EMPTY_ARTEFACT).
AC3: Frozen artefact modification is detected (FROZEN_ARTEFACT_MODIFIED).
AC4: Missing per-iteration output is rejected (MISSING_ITERATION_OUTPUT).
AC5: criteria_passed without rubric_scores is rejected (MISSING_RUBRIC_SCORES).
AC6: Completed experiments reject further steps (TERMINAL_STATE).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from models import ArtefactIntegrity, ExperimentState, StepDefinition, ValidationRule
from state_manager import StateManager
from validators import (
    EMPTY_ARTEFACT,
    FROZEN_ARTEFACT_MODIFIED,
    MISSING_ITERATION_OUTPUT,
    MISSING_RUBRIC_SCORES,
    TERMINAL_STATE,
)

if TYPE_CHECKING:
    from pathlib import Path

# ===========================================================================
# Shared helpers
# ===========================================================================


def _error_codes(result: dict[str, object]) -> set[str]:
    """Extract error code strings from a complete_step failure result.

    Args:
        result: The dict returned by StateManager.complete_step().

    Returns:
        Set of error code strings from the validation_errors list.
    """
    errors = result["validation_errors"]
    assert isinstance(errors, list)
    codes: set[str] = set()
    for e in errors:
        assert isinstance(e, dict)
        code = e["code"]  # type: ignore[index]
        assert isinstance(code, str)
        codes.add(code)
    return codes


def _build_steps() -> list[StepDefinition]:
    """Return the full five-step experiment_core step list with validation rules.

    Returns:
        Ordered list of StepDefinition objects matching experiment_core.json structure.
    """
    return [
        StepDefinition(
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
        ),
        StepDefinition(
            id="fixture",
            name="Build fixture",
            required_artefacts=["fixture.md"],
            validation_rules=[
                ValidationRule(type="non_empty", params={}),
                ValidationRule(
                    type="no_forbidden_content",
                    params={"patterns": ["EXPECTED:", "CORRECT ANSWER:", "SUCCESS CRITERION:", "RUBRIC:"]},
                ),
            ],
            frozen_artefacts=["fixture.md"],
        ),
        StepDefinition(
            id="rubric",
            name="Write rubric",
            required_artefacts=["rubric.md"],
            validation_rules=[
                ValidationRule(type="non_empty", params={}),
                ValidationRule(type="min_criteria_count", params={"min": 1}),
            ],
            frozen_artefacts=["rubric.md"],
        ),
        StepDefinition(
            id="baseline",
            name="Run baseline",
            required_artefacts=["output-iter0.md", "log.md"],
            validation_rules=[ValidationRule(type="non_empty", params={})],
            frozen_artefacts=[],
        ),
        StepDefinition(
            id="iterate",
            name="Iterate",
            required_artefacts=["log.md"],
            validation_rules=[
                ValidationRule(type="non_empty", params={}),
                ValidationRule(type="required_sections", params={"sections": ["## Iteration"]}),
            ],
            frozen_artefacts=[],
        ),
    ]


def _persist_state(
    tmp_path: Path,
    experiment_id: str,
    current_step: str,
    *,
    artefacts: dict[str, str] | None = None,
    artefact_integrity: dict[str, ArtefactIntegrity] | None = None,
    status: str = "in_progress",
    iteration_count: int = 0,
) -> ExperimentState:
    """Write an ExperimentState with the full five-step list to disk.

    Args:
        tmp_path: Base project root.
        experiment_id: Unique experiment identifier.
        current_step: Active step ID.
        artefacts: Existing artefacts (default empty).
        artefact_integrity: Integrity records (default empty).
        status: Lifecycle status string.
        iteration_count: Completed iteration count.

    Returns:
        The ExperimentState written to disk.
    """
    state = ExperimentState(
        id=experiment_id,
        base="experiment_core",
        current_step=current_step,
        status=status,
        iteration_count=iteration_count,
        merged_steps=_build_steps(),
        artefacts=artefacts or {},
        artefact_integrity=artefact_integrity or {},
    )
    state_path = tmp_path / ".claude" / "experiments" / experiment_id / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    return state


def _make_manager(tmp_path: Path, mock_loader) -> StateManager:
    """Construct a StateManager for the given tmp_path with a mock loader.

    Args:
        tmp_path: Pytest tmp_path fixture value.
        mock_loader: MagicMock RegistryLoader.

    Returns:
        Configured StateManager.
    """
    mock_loader.merge_type.return_value = _build_steps()
    return StateManager(project_root=tmp_path, loader=mock_loader)


def _exp_dir(tmp_path: Path, experiment_id: str) -> Path:
    """Return the experiment directory path, creating it if absent.

    Args:
        tmp_path: Base project root.
        experiment_id: Unique experiment identifier.

    Returns:
        Path to the experiment directory.
    """
    path = tmp_path / ".claude" / "experiments" / experiment_id
    path.mkdir(parents=True, exist_ok=True)
    return path


# ===========================================================================
# AC1 — Empty artefact rejected
# ===========================================================================


class TestAC1EmptyArtefactRejected:
    """AC1: Submitting an empty artefact file is rejected with EMPTY_ARTEFACT.

    Tests: complete_step rejects empty hypothesis.md
    Why: Empty artefacts provide no scientific value; enforcement ensures protocol compliance.
    """

    def test_ac1_empty_artefact_rejected(self, tmp_path: Path, mock_loader) -> None:
        """Write empty hypothesis.md; call complete_step; assert success=False and EMPTY_ARTEFACT.

        Tests: AC1 — empty artefact content rejection
        How: Persist state at hypothesis step; write an empty hypothesis.md;
          call complete_step; assert validation_errors contains EMPTY_ARTEFACT.
        Why: Agents must be prevented from submitting empty artefacts to advance the protocol.
        """
        manager = _make_manager(tmp_path, mock_loader)
        experiment_id = "exp-ac1-001"
        exp_dir = _exp_dir(tmp_path, experiment_id)
        _persist_state(tmp_path, experiment_id, "hypothesis")

        # Empty hypothesis.md
        hyp_file = exp_dir / "hypothesis.md"
        hyp_file.write_text("", encoding="utf-8")

        result = manager.complete_step(experiment_id, "hypothesis", {"hypothesis.md": str(hyp_file)})

        assert result["success"] is False
        codes = _error_codes(result)
        assert EMPTY_ARTEFACT in codes

    def test_ac1_whitespace_only_artefact_rejected(self, tmp_path: Path, mock_loader) -> None:
        """Validate that whitespace-only hypothesis.md is also rejected.

        Tests: AC1 — whitespace-only content is treated as empty
        How: Write hypothesis.md with only spaces/newlines; expect EMPTY_ARTEFACT.
        Why: Whitespace-only files circumvent trivial length checks; content must be non-empty after strip.
        """
        manager = _make_manager(tmp_path, mock_loader)
        experiment_id = "exp-ac1-002"
        exp_dir = _exp_dir(tmp_path, experiment_id)
        _persist_state(tmp_path, experiment_id, "hypothesis")

        hyp_file = exp_dir / "hypothesis.md"
        hyp_file.write_text("   \n\n   ", encoding="utf-8")

        result = manager.complete_step(experiment_id, "hypothesis", {"hypothesis.md": str(hyp_file)})

        assert result["success"] is False
        codes = _error_codes(result)
        assert EMPTY_ARTEFACT in codes


# ===========================================================================
# AC3 — Frozen artefact modification detected
# ===========================================================================


class TestAC3FrozenArtefactModifiedRejected:
    """AC3: Modifying a frozen artefact between steps is detected and rejected.

    Tests: complete_step detects fixture.md modification after fixture step completed.
    Why: Pre-registration integrity requires frozen artefacts to remain unchanged.
    """

    def test_ac3_frozen_artefact_modified_rejected(self, tmp_path: Path, mock_loader) -> None:
        """Complete fixture step, modify fixture.md, attempt rubric step, assert rejection.

        Tests: AC3 — FROZEN_ARTEFACT_MODIFIED error when frozen file is tampered
        How: Write valid fixture.md; complete fixture step (stores hash);
          overwrite fixture.md; attempt rubric step; assert FROZEN_ARTEFACT_MODIFIED.
        Why: The integrity check runs on every complete_step after freeze;
          even modifications between unrelated steps are caught.
        """
        manager = _make_manager(tmp_path, mock_loader)
        experiment_id = "exp-ac3-001"
        exp_dir = _exp_dir(tmp_path, experiment_id)

        _persist_state(tmp_path, experiment_id, "fixture")

        # Write and complete the fixture step
        fixture_content = b"This is the clean fixture. No criteria embedded."
        fixture_file = exp_dir / "fixture.md"
        fixture_file.write_bytes(fixture_content)

        fixture_result = manager.complete_step(experiment_id, "fixture", {"fixture.md": str(fixture_file)})
        assert fixture_result["success"] is True

        # Now tamper with fixture.md after it was frozen
        fixture_file.write_bytes(b"TAMPERED fixture content with EXPECTED: embedded")

        # Attempt to complete the rubric step — should detect the tampering
        rubric_file = exp_dir / "rubric.md"
        rubric_file.write_text("- [ ] output is correct\n", encoding="utf-8")

        rubric_result = manager.complete_step(experiment_id, "rubric", {"rubric.md": str(rubric_file)})

        assert rubric_result["success"] is False
        codes = _error_codes(rubric_result)
        assert FROZEN_ARTEFACT_MODIFIED in codes

    def test_ac3_unmodified_frozen_artefact_passes(self, tmp_path: Path, mock_loader) -> None:
        """Validate that an unmodified frozen artefact does not block the next step.

        Tests: AC3 negative case — hash matches, step proceeds normally
        How: Complete fixture step; do NOT modify fixture.md; attempt rubric step.
        Why: The positive case ensures the validator does not produce false positives.
        """
        manager = _make_manager(tmp_path, mock_loader)
        experiment_id = "exp-ac3-002"
        exp_dir = _exp_dir(tmp_path, experiment_id)

        _persist_state(tmp_path, experiment_id, "fixture")

        fixture_file = exp_dir / "fixture.md"
        fixture_file.write_text("Clean fixture content.", encoding="utf-8")

        fixture_result = manager.complete_step(experiment_id, "fixture", {"fixture.md": str(fixture_file)})
        assert fixture_result["success"] is True

        # Do NOT modify fixture.md — attempt rubric step
        rubric_file = exp_dir / "rubric.md"
        rubric_file.write_text("- [ ] output is correct\n", encoding="utf-8")

        rubric_result = manager.complete_step(experiment_id, "rubric", {"rubric.md": str(rubric_file)})
        assert rubric_result["success"] is True


# ===========================================================================
# AC4 — Missing iteration output rejected
# ===========================================================================


class TestAC4MissingIterationOutputRejected:
    """AC4: Submitting the iterate step without output-iterN.md is rejected.

    Tests: complete_step rejects iterate submission missing output-iter1.md.
    Why: Per-iteration output captures the experiment's progress for retrospective analysis.
    """

    def test_ac4_missing_iteration_output_rejected(self, tmp_path: Path, mock_loader) -> None:
        """Call complete_step(iterate) with only log.md; assert MISSING_ITERATION_OUTPUT.

        Tests: AC4 — missing output-iter1.md from iterate artefacts
        How: Set state to iterate step with iteration_count=0;
          provide only log.md; assert MISSING_ITERATION_OUTPUT error.
        Why: Each iteration must capture its output to prevent selective reporting.
        """
        manager = _make_manager(tmp_path, mock_loader)
        experiment_id = "exp-ac4-001"
        exp_dir = _exp_dir(tmp_path, experiment_id)

        _persist_state(tmp_path, experiment_id, "iterate", iteration_count=0)

        log_file = exp_dir / "log.md"
        log_file.write_text("## Iteration 1\nSome changes.", encoding="utf-8")

        result = manager.complete_step(
            experiment_id, "iterate", {"log.md": str(log_file)}, rubric_scores={"criterion_1": True}
        )

        assert result["success"] is False
        codes = _error_codes(result)
        assert MISSING_ITERATION_OUTPUT in codes

    def test_ac4_with_correct_output_key_passes(self, tmp_path: Path, mock_loader) -> None:
        """Validate that providing output-iter1.md allows the iterate step to proceed.

        Tests: AC4 negative case — output key present, step is not blocked
        How: Provide both log.md and output-iter1.md with valid content.
        Why: Confirms the validator does not block compliant submissions.
        """
        manager = _make_manager(tmp_path, mock_loader)
        experiment_id = "exp-ac4-002"
        exp_dir = _exp_dir(tmp_path, experiment_id)

        _persist_state(tmp_path, experiment_id, "iterate", iteration_count=0)

        log_file = exp_dir / "log.md"
        log_file.write_text("## Iteration 1\nSome changes.", encoding="utf-8")
        iter1_file = exp_dir / "output-iter1.md"
        iter1_file.write_text("Iteration 1 output.", encoding="utf-8")

        result = manager.complete_step(
            experiment_id,
            "iterate",
            {"log.md": str(log_file), "output-iter1.md": str(iter1_file)},
            rubric_scores={"criterion_1": True},
        )

        assert result["success"] is True


# ===========================================================================
# AC5 — criteria_passed without rubric_scores rejected
# ===========================================================================


class TestAC5CriteriaPassedWithoutRubricScoresRejected:
    """AC5: Calling iterate with criteria_passed but no rubric_scores is rejected.

    Tests: complete_step rejects iterate step when rubric_scores is None.
    Why: Self-reported criteria_passed is replaced by MCP-verified rubric_scores (architecture D3).
    """

    def test_ac5_criteria_passed_without_rubric_scores_rejected(self, tmp_path: Path, mock_loader) -> None:
        """Submit iterate with criteria_passed artefact but no rubric_scores; assert MISSING_RUBRIC_SCORES.

        Tests: AC5 — rubric_scores=None rejected for iterate step
        How: Set state to iterate; include criteria_passed in artefacts dict (old format);
          pass rubric_scores=None; assert MISSING_RUBRIC_SCORES.
        Why: The old criteria_passed self-reporting mechanism must be rejected in favour of
          per-criterion rubric_scores verified by the MCP server.
        """
        manager = _make_manager(tmp_path, mock_loader)
        experiment_id = "exp-ac5-001"
        exp_dir = _exp_dir(tmp_path, experiment_id)

        _persist_state(tmp_path, experiment_id, "iterate", iteration_count=0)

        log_file = exp_dir / "log.md"
        log_file.write_text("## Iteration 1\nSome changes.", encoding="utf-8")
        iter1_file = exp_dir / "output-iter1.md"
        iter1_file.write_text("Iteration 1 output.", encoding="utf-8")

        # Old protocol: include criteria_passed as an artefact string, no rubric_scores
        result = manager.complete_step(
            experiment_id,
            "iterate",
            {
                "log.md": str(log_file),
                "output-iter1.md": str(iter1_file),
                "criteria_passed": "true",  # Old self-reported format — not a file
            },
            rubric_scores=None,  # No structured scores provided
        )

        assert result["success"] is False
        codes = _error_codes(result)
        assert MISSING_RUBRIC_SCORES in codes

    def test_ac5_rubric_scores_accepted(self, tmp_path: Path, mock_loader) -> None:
        """Validate that providing rubric_scores allows the iterate step to proceed.

        Tests: AC5 negative case — proper rubric_scores are accepted
        How: Provide both artefacts and rubric_scores dict.
        Why: The new rubric_scores mechanism must be the accepted path.
        """
        manager = _make_manager(tmp_path, mock_loader)
        experiment_id = "exp-ac5-002"
        exp_dir = _exp_dir(tmp_path, experiment_id)

        _persist_state(tmp_path, experiment_id, "iterate", iteration_count=0)

        log_file = exp_dir / "log.md"
        log_file.write_text("## Iteration 1\nSome changes.", encoding="utf-8")
        iter1_file = exp_dir / "output-iter1.md"
        iter1_file.write_text("Iteration 1 output.", encoding="utf-8")

        result = manager.complete_step(
            experiment_id,
            "iterate",
            {"log.md": str(log_file), "output-iter1.md": str(iter1_file)},
            rubric_scores={"criterion_1": True},
        )

        assert result["success"] is True


# ===========================================================================
# AC6 — Terminal state rejection
# ===========================================================================


class TestAC6TerminalStateRejected:
    """AC6: Calling complete_step on a completed or inconclusive experiment is rejected.

    Tests: complete_step returns TERMINAL_STATE for experiments not in_progress.
    Why: Terminal experiments must be immutable; further mutations corrupt the audit trail.
    """

    def test_ac6_complete_experiment_rejects_next_step(self, tmp_path: Path, mock_loader) -> None:
        """Mark experiment as complete; call complete_step again; assert TERMINAL_STATE.

        Tests: AC6 — complete status blocks further step completions
        How: Persist state with status='complete'; attempt complete_step on iterate;
          assert validation_errors contains TERMINAL_STATE.
        Why: A completed experiment should never accept further modifications.
        """
        manager = _make_manager(tmp_path, mock_loader)
        experiment_id = "exp-ac6-001"
        exp_dir = _exp_dir(tmp_path, experiment_id)

        _persist_state(tmp_path, experiment_id, "iterate", status="complete")

        log_file = exp_dir / "log.md"
        log_file.write_text("## Iteration\nSome changes.", encoding="utf-8")
        iter1_file = exp_dir / "output-iter1.md"
        iter1_file.write_text("Output.", encoding="utf-8")

        result = manager.complete_step(
            experiment_id,
            "iterate",
            {"log.md": str(log_file), "output-iter1.md": str(iter1_file)},
            rubric_scores={"criterion_1": True},
        )

        assert result["success"] is False
        codes = _error_codes(result)
        assert TERMINAL_STATE in codes

    def test_ac6_inconclusive_experiment_rejects_next_step(self, tmp_path: Path, mock_loader) -> None:
        """Mark experiment as inconclusive; call complete_step again; assert TERMINAL_STATE.

        Tests: AC6 — inconclusive status also blocks further step completions
        How: Persist state with status='inconclusive'; attempt complete_step;
          assert TERMINAL_STATE.
        Why: Both complete and inconclusive are terminal states with identical rejection behaviour.
        """
        manager = _make_manager(tmp_path, mock_loader)
        experiment_id = "exp-ac6-002"
        exp_dir = _exp_dir(tmp_path, experiment_id)

        _persist_state(tmp_path, experiment_id, "iterate", status="inconclusive")

        log_file = exp_dir / "log.md"
        log_file.write_text("## Iteration\nSome changes.", encoding="utf-8")
        iter1_file = exp_dir / "output-iter1.md"
        iter1_file.write_text("Output.", encoding="utf-8")

        result = manager.complete_step(
            experiment_id,
            "iterate",
            {"log.md": str(log_file), "output-iter1.md": str(iter1_file)},
            rubric_scores={"criterion_1": True},
        )

        assert result["success"] is False
        codes = _error_codes(result)
        assert TERMINAL_STATE in codes

    def test_ac6_in_progress_experiment_is_not_blocked(self, tmp_path: Path, mock_loader) -> None:
        """Validate that an in_progress experiment is not blocked by terminal state check.

        Tests: AC6 negative case — in_progress status allows step completion
        How: Persist state with status='in_progress'; submit valid iterate artefacts.
        Why: Active experiments must not be incorrectly blocked by the terminal state check.
        """
        manager = _make_manager(tmp_path, mock_loader)
        experiment_id = "exp-ac6-003"
        exp_dir = _exp_dir(tmp_path, experiment_id)

        _persist_state(tmp_path, experiment_id, "iterate", status="in_progress", iteration_count=0)

        log_file = exp_dir / "log.md"
        log_file.write_text("## Iteration 1\nSome changes.", encoding="utf-8")
        iter1_file = exp_dir / "output-iter1.md"
        iter1_file.write_text("Output.", encoding="utf-8")

        result = manager.complete_step(
            experiment_id,
            "iterate",
            {"log.md": str(log_file), "output-iter1.md": str(iter1_file)},
            rubric_scores={"criterion_1": True},
        )

        assert result["success"] is True
