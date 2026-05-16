"""Unit tests for validators.py — each public function tested in isolation.

Tests: All six validator functions in validators.py.
Strategy: Pure-function validators are called directly with controlled inputs.
  File-based validators write content to tmp_path before calling.
  Each test exercises one discrete behavior (valid input passes, invalid input fails
  with the expected error code).
Coverage target: >=95% of validators.py.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest
from models import ArtefactIntegrity, StepDefinition, ValidationRule
from validators import (
    CONTENT_VALIDATION_FAILED,
    EMPTY_ARTEFACT,
    FILE_NOT_FOUND,
    FROZEN_ARTEFACT_MODIFIED,
    INCOMPLETE_RUBRIC_SCORES,
    MISSING_ITERATION_OUTPUT,
    MISSING_RUBRIC_SCORES,
    TERMINAL_STATE,
    UNKNOWN_RUBRIC_CRITERIA,
    validate_artefact_content,
    validate_file_existence,
    validate_freeze_integrity,
    validate_iteration_output,
    validate_rubric_scores,
    validate_terminal_state,
)

if TYPE_CHECKING:
    from pathlib import Path

# ===========================================================================
# Helpers
# ===========================================================================


def _make_step(
    *,
    step_id: str = "hypothesis",
    required_artefacts: list[str] | None = None,
    validation_rules: list[ValidationRule] | None = None,
    frozen_artefacts: list[str] | None = None,
) -> StepDefinition:
    """Build a StepDefinition with sensible defaults for testing.

    Args:
        step_id: Step identifier.
        required_artefacts: List of required artefact keys.
        validation_rules: Validation rules to apply.
        frozen_artefacts: Artefact keys frozen when this step completes.

    Returns:
        StepDefinition ready for use in validator tests.
    """
    return StepDefinition(
        id=step_id,
        name=step_id.title(),
        required_artefacts=required_artefacts or [],
        validation_rules=validation_rules or [],
        frozen_artefacts=frozen_artefacts or [],
    )


# ===========================================================================
# validate_terminal_state
# ===========================================================================


class TestValidateTerminalState:
    """Tests for validate_terminal_state().

    Tests: Experiment status gating — terminal states reject further steps.
    How: Construct ExperimentState with each status and call the validator.
    Why: Prevents double-completion or post-completion mutations of experiment state.
    """

    def test_in_progress_status_passes(self, make_state) -> None:
        """Validate that in_progress status produces no errors.

        Tests: validate_terminal_state with status='in_progress'
        How: Construct state, call validator, assert empty error list.
        Why: Active experiments must be allowed to proceed.
        """
        state = make_state(status="in_progress")
        errors = validate_terminal_state(state)
        assert errors == []

    def test_complete_status_returns_terminal_state_error(self, make_state) -> None:
        """Validate that complete status returns TERMINAL_STATE error.

        Tests: validate_terminal_state with status='complete'
        How: Construct state, call validator, assert error code.
        Why: Completed experiments must not accept further step completions.
        """
        state = make_state(status="complete")
        errors = validate_terminal_state(state)
        assert len(errors) == 1
        assert errors[0]["code"] == TERMINAL_STATE
        assert errors[0]["status"] == "complete"

    def test_inconclusive_status_returns_terminal_state_error(self, make_state) -> None:
        """Validate that inconclusive status returns TERMINAL_STATE error.

        Tests: validate_terminal_state with status='inconclusive'
        How: Construct state, call validator, assert error code.
        Why: Inconclusive experiments have reached max iterations and must not advance.
        """
        state = make_state(status="inconclusive")
        errors = validate_terminal_state(state)
        assert len(errors) == 1
        assert errors[0]["code"] == TERMINAL_STATE
        assert errors[0]["status"] == "inconclusive"

    def test_error_includes_experiment_id_in_message(self, make_state) -> None:
        """Validate that TERMINAL_STATE error message references the experiment ID.

        Tests: validate_terminal_state error message content
        How: Create state with known ID and status=complete, check message.
        Why: Error messages must be actionable — agent needs to know which experiment.
        """
        state = make_state(experiment_id="exp-2026-01-01-007", status="complete")
        errors = validate_terminal_state(state)
        assert "exp-2026-01-01-007" in errors[0]["message"]


# ===========================================================================
# validate_file_existence
# ===========================================================================


class TestValidateFileExistence:
    """Tests for validate_file_existence().

    Tests: File path resolution and existence checking for artefact files.
    How: Write real files to tmp_path; test present, absent, and inline-value cases.
    Why: Artefact values are file paths per architecture D1; missing files must be reported.
    """

    def test_existing_file_passes(self, experiment_dir: Path) -> None:
        """Validate that an existing file produces no error.

        Tests: validate_file_existence with a file that exists on disk
        How: Write the file to experiment_dir, call validator with relative path.
        Why: Valid artefact submissions must not be rejected.
        """
        (experiment_dir / "hypothesis.md").write_text("content", encoding="utf-8")
        artefacts = {"hypothesis.md": "hypothesis.md"}
        errors = validate_file_existence(artefacts, experiment_dir)
        assert errors == []

    def test_missing_file_returns_file_not_found(self, experiment_dir: Path) -> None:
        """Validate that a missing file returns FILE_NOT_FOUND error.

        Tests: validate_file_existence with a non-existent file path
        How: Provide an artefact path pointing to a non-existent file.
        Why: Agents must not claim artefacts they did not produce.
        """
        artefacts = {"hypothesis.md": "hypothesis.md"}
        errors = validate_file_existence(artefacts, experiment_dir)
        assert len(errors) == 1
        assert errors[0]["code"] == FILE_NOT_FOUND
        assert errors[0]["artefact"] == "hypothesis.md"

    def test_key_without_dot_is_skipped(self, experiment_dir: Path) -> None:
        """Validate that inline-value keys (no dot in name) are skipped.

        Tests: validate_file_existence D1 convention — keys without '.' are inline values
        How: Provide a key without a file extension; expect no error even though no file exists.
        Why: Architecture D1: keys without '.' are inline values, not file paths.
        """
        artefacts = {"criteria_passed": "true"}
        errors = validate_file_existence(artefacts, experiment_dir)
        assert errors == []

    def test_absolute_path_resolved_correctly(self, experiment_dir: Path) -> None:
        """Validate that an absolute artefact path is used as-is.

        Tests: validate_file_existence with an absolute path value
        How: Write file, supply its absolute path as the artefact value.
        Why: Architecture D1 supports both relative and absolute paths.
        """
        file_path = experiment_dir / "fixture.md"
        file_path.write_text("fixture content", encoding="utf-8")
        artefacts = {"fixture.md": str(file_path)}
        errors = validate_file_existence(artefacts, experiment_dir)
        assert errors == []

    def test_multiple_missing_files_accumulates_errors(self, experiment_dir: Path) -> None:
        """Validate that multiple missing files each generate a separate error.

        Tests: validate_file_existence error accumulation
        How: Submit two artefacts neither of which exists on disk.
        Why: All missing artefacts must be reported so the agent can fix all at once.
        """
        artefacts = {"output-iter0.md": "output-iter0.md", "log.md": "log.md"}
        errors = validate_file_existence(artefacts, experiment_dir)
        assert len(errors) == 2
        codes = {e["code"] for e in errors}
        assert codes == {FILE_NOT_FOUND}


# ===========================================================================
# validate_artefact_content — rule evaluators
# ===========================================================================


class TestValidateArtefactContentNonEmpty:
    """Tests for the non_empty rule via validate_artefact_content.

    Tests: _eval_non_empty rule evaluator through the public interface.
    How: Write files with valid/invalid content; verify error code.
    Why: Empty artefacts provide no scientific value and must be rejected at submission time.
    """

    def test_non_empty_content_passes(self, experiment_dir: Path) -> None:
        """Validate that non-empty file content produces no error.

        Tests: non_empty rule with content that has visible characters
        How: Write a file with text, build step_def, call validate_artefact_content.
        Why: Valid submissions must be accepted without false positives.
        """
        (experiment_dir / "hypothesis.md").write_text(
            "HYPOTHESIS: something\nCURRENT BEHAVIOUR: something\nSUCCESS CRITERION: something", encoding="utf-8"
        )
        step_def = _make_step(
            required_artefacts=["hypothesis.md"], validation_rules=[ValidationRule(type="non_empty", params={})]
        )
        errors = validate_artefact_content(step_def, {"hypothesis.md": "hypothesis.md"}, experiment_dir)
        assert errors == []

    def test_empty_file_returns_empty_artefact_error(self, experiment_dir: Path) -> None:
        """Validate that an empty file returns EMPTY_ARTEFACT error.

        Tests: non_empty rule with a file that is empty after stripping whitespace
        How: Write a file with only whitespace, call validate_artefact_content.
        Why: Whitespace-only files are functionally empty and must be rejected.
        """
        (experiment_dir / "hypothesis.md").write_text("   \n   ", encoding="utf-8")
        step_def = _make_step(
            required_artefacts=["hypothesis.md"], validation_rules=[ValidationRule(type="non_empty", params={})]
        )
        errors = validate_artefact_content(step_def, {"hypothesis.md": "hypothesis.md"}, experiment_dir)
        assert len(errors) == 1
        assert errors[0]["code"] == EMPTY_ARTEFACT
        assert errors[0]["artefact"] == "hypothesis.md"

    def test_truly_empty_file_returns_empty_artefact_error(self, experiment_dir: Path) -> None:
        """Validate that a zero-byte file returns EMPTY_ARTEFACT error.

        Tests: non_empty rule with a file that is completely empty
        How: Write an empty file, call validate_artefact_content.
        Why: Zero-byte files are always invalid artefacts.
        """
        (experiment_dir / "hypothesis.md").write_text("", encoding="utf-8")
        step_def = _make_step(
            required_artefacts=["hypothesis.md"], validation_rules=[ValidationRule(type="non_empty", params={})]
        )
        errors = validate_artefact_content(step_def, {"hypothesis.md": "hypothesis.md"}, experiment_dir)
        assert len(errors) == 1
        assert errors[0]["code"] == EMPTY_ARTEFACT


class TestValidateArtefactContentRequiredSections:
    """Tests for the required_sections rule via validate_artefact_content.

    Tests: _eval_required_sections rule evaluator.
    How: Write files with/without required section headers.
    Why: Hypothesis files without proper structure cannot be scientifically evaluated.
    """

    def test_all_sections_present_passes(self, experiment_dir: Path) -> None:
        """Validate that a file with all required sections produces no error.

        Tests: required_sections rule with all expected headers present
        How: Write file containing all section strings, call validate_artefact_content.
        Why: Compliant submissions must pass without false positives.
        """
        content = "HYPOTHESIS: something\nCURRENT BEHAVIOUR: observed\nSUCCESS CRITERION: criterion"
        (experiment_dir / "hypothesis.md").write_text(content, encoding="utf-8")
        step_def = _make_step(
            required_artefacts=["hypothesis.md"],
            validation_rules=[
                ValidationRule(
                    type="required_sections",
                    params={"sections": ["HYPOTHESIS:", "CURRENT BEHAVIOUR:", "SUCCESS CRITERION:"]},
                )
            ],
        )
        errors = validate_artefact_content(step_def, {"hypothesis.md": "hypothesis.md"}, experiment_dir)
        assert errors == []

    def test_missing_section_returns_content_validation_failed(self, experiment_dir: Path) -> None:
        """Validate that a missing required section returns CONTENT_VALIDATION_FAILED.

        Tests: required_sections rule with one section absent
        How: Write file missing the SUCCESS CRITERION section, call validate_artefact_content.
        Why: Incomplete hypothesis structure signals the agent has not followed the protocol.
        """
        (experiment_dir / "hypothesis.md").write_text(
            "HYPOTHESIS: something\nCURRENT BEHAVIOUR: observed", encoding="utf-8"
        )
        step_def = _make_step(
            required_artefacts=["hypothesis.md"],
            validation_rules=[
                ValidationRule(
                    type="required_sections",
                    params={"sections": ["HYPOTHESIS:", "CURRENT BEHAVIOUR:", "SUCCESS CRITERION:"]},
                )
            ],
        )
        errors = validate_artefact_content(step_def, {"hypothesis.md": "hypothesis.md"}, experiment_dir)
        assert len(errors) == 1
        assert errors[0]["code"] == CONTENT_VALIDATION_FAILED
        assert "SUCCESS CRITERION:" in errors[0]["message"]


class TestValidateArtefactContentNoForbiddenContent:
    """Tests for the no_forbidden_content rule via validate_artefact_content.

    Tests: _eval_no_forbidden_content rule evaluator (case-insensitive).
    How: Write files with and without forbidden strings.
    Why: Fixture files must not embed criteria or model answers to ensure blind testing.
    """

    def test_clean_content_passes(self, experiment_dir: Path) -> None:
        """Validate that content without forbidden patterns produces no error.

        Tests: no_forbidden_content rule with compliant fixture content
        How: Write a plain fixture file, call validate_artefact_content.
        Why: Valid fixtures must not be rejected.
        """
        (experiment_dir / "fixture.md").write_text("# Task\nPerform the following operation.", encoding="utf-8")
        step_def = _make_step(
            required_artefacts=["fixture.md"],
            validation_rules=[
                ValidationRule(
                    type="no_forbidden_content", params={"patterns": ["EXPECTED:", "CORRECT ANSWER:", "RUBRIC:"]}
                )
            ],
        )
        errors = validate_artefact_content(step_def, {"fixture.md": "fixture.md"}, experiment_dir)
        assert errors == []

    def test_forbidden_content_returns_error(self, experiment_dir: Path) -> None:
        """Validate that a file containing a forbidden string returns CONTENT_VALIDATION_FAILED.

        Tests: no_forbidden_content rule with EXPECTED: in the fixture file
        How: Write file embedding EXPECTED: pattern, call validate_artefact_content.
        Why: Fixtures embedding criteria invalidate the blinding requirement.
        """
        (experiment_dir / "fixture.md").write_text("# Task\nDo this.\nEXPECTED: correct answer here", encoding="utf-8")
        step_def = _make_step(
            required_artefacts=["fixture.md"],
            validation_rules=[
                ValidationRule(type="no_forbidden_content", params={"patterns": ["EXPECTED:", "CORRECT ANSWER:"]})
            ],
        )
        errors = validate_artefact_content(step_def, {"fixture.md": "fixture.md"}, experiment_dir)
        assert len(errors) == 1
        assert errors[0]["code"] == CONTENT_VALIDATION_FAILED

    def test_forbidden_content_check_is_case_insensitive(self, experiment_dir: Path) -> None:
        """Validate that forbidden pattern check is case-insensitive.

        Tests: no_forbidden_content rule with lowercase 'expected:' in content
        How: Write file with lowercase version, call validate_artefact_content.
        Why: Case-insensitive matching prevents trivial bypass via mixed case.
        """
        (experiment_dir / "fixture.md").write_text("# Task\nexpected: answer here", encoding="utf-8")
        step_def = _make_step(
            required_artefacts=["fixture.md"],
            validation_rules=[ValidationRule(type="no_forbidden_content", params={"patterns": ["EXPECTED:"]})],
        )
        errors = validate_artefact_content(step_def, {"fixture.md": "fixture.md"}, experiment_dir)
        assert len(errors) == 1
        assert errors[0]["code"] == CONTENT_VALIDATION_FAILED


class TestValidateArtefactContentMinCriteriaCount:
    """Tests for the min_criteria_count rule via validate_artefact_content.

    Tests: _eval_min_criteria_count rule evaluator.
    How: Write rubric files with varying checkbox counts.
    Why: Rubrics must contain at least one binary criterion to be scoreable.
    """

    def test_single_criterion_passes(self, experiment_dir: Path) -> None:
        """Validate that a rubric with exactly one criterion passes.

        Tests: min_criteria_count rule with count == minimum
        How: Write rubric with one '- [ ]' item, call validate_artefact_content.
        Why: A single criterion satisfies the minimum requirement.
        """
        (experiment_dir / "rubric.md").write_text("- [ ] output is correct\n", encoding="utf-8")
        step_def = _make_step(
            required_artefacts=["rubric.md"],
            validation_rules=[ValidationRule(type="min_criteria_count", params={"min": 1})],
        )
        errors = validate_artefact_content(step_def, {"rubric.md": "rubric.md"}, experiment_dir)
        assert errors == []

    def test_checked_criterion_passes(self, experiment_dir: Path) -> None:
        """Validate that a rubric with an already-checked criterion passes.

        Tests: min_criteria_count rule recognises '- [x]' as a valid criterion
        How: Write rubric with '- [x]' item, call validate_artefact_content.
        Why: Both empty and checked checkboxes count as valid criteria.
        """
        (experiment_dir / "rubric.md").write_text("- [x] criterion passed\n", encoding="utf-8")
        step_def = _make_step(
            required_artefacts=["rubric.md"],
            validation_rules=[ValidationRule(type="min_criteria_count", params={"min": 1})],
        )
        errors = validate_artefact_content(step_def, {"rubric.md": "rubric.md"}, experiment_dir)
        assert errors == []

    def test_empty_rubric_returns_content_validation_failed(self, experiment_dir: Path) -> None:
        """Validate that a rubric with no checkboxes returns CONTENT_VALIDATION_FAILED.

        Tests: min_criteria_count rule with zero criteria found
        How: Write a rubric file without any checkbox items, call validate_artefact_content.
        Why: A rubric with no criteria cannot be scored.
        """
        (experiment_dir / "rubric.md").write_text("# Rubric\nThis rubric has no criteria defined.", encoding="utf-8")
        step_def = _make_step(
            required_artefacts=["rubric.md"],
            validation_rules=[ValidationRule(type="min_criteria_count", params={"min": 1})],
        )
        errors = validate_artefact_content(step_def, {"rubric.md": "rubric.md"}, experiment_dir)
        assert len(errors) == 1
        assert errors[0]["code"] == CONTENT_VALIDATION_FAILED


class TestValidateArtefactContentMultipleErrors:
    """Tests for multi-error accumulation in validate_artefact_content.

    Tests: validate_artefact_content collects all errors without short-circuiting.
    How: Use a step with two rules; write content that violates both.
    Why: Agents need the full error list to fix all issues in one pass.
    """

    def test_empty_and_missing_sections_both_reported(self, experiment_dir: Path) -> None:
        """Validate that empty content accumulates errors from all applicable rules.

        Tests: validate_artefact_content with non_empty + required_sections rules
        How: Write an empty file (violates non_empty); the required_sections rule
          also fires because the empty content lacks all sections.
        Why: All failures must be reported — not just the first one.
        """
        (experiment_dir / "hypothesis.md").write_text("", encoding="utf-8")
        step_def = _make_step(
            required_artefacts=["hypothesis.md"],
            validation_rules=[
                ValidationRule(type="non_empty", params={}),
                ValidationRule(type="required_sections", params={"sections": ["HYPOTHESIS:"]}),
            ],
        )
        errors = validate_artefact_content(step_def, {"hypothesis.md": "hypothesis.md"}, experiment_dir)
        # Both rules fire: EMPTY_ARTEFACT from non_empty and CONTENT_VALIDATION_FAILED
        # from required_sections
        assert len(errors) == 2
        codes = {e["code"] for e in errors}
        assert EMPTY_ARTEFACT in codes
        assert CONTENT_VALIDATION_FAILED in codes

    def test_no_validation_rules_returns_empty(self, experiment_dir: Path) -> None:
        """Validate that a step with no rules returns no errors regardless of content.

        Tests: validate_artefact_content short-circuit when validation_rules is empty
        How: Build step with empty validation_rules list, call with any artefacts.
        Why: Steps without rules must never block artefact submission.
        """
        (experiment_dir / "fixture.md").write_text("", encoding="utf-8")
        step_def = _make_step(required_artefacts=["fixture.md"], validation_rules=[])
        errors = validate_artefact_content(step_def, {"fixture.md": "fixture.md"}, experiment_dir)
        assert errors == []


# ===========================================================================
# validate_freeze_integrity
# ===========================================================================


class TestValidateFreezeIntegrity:
    """Tests for validate_freeze_integrity().

    Tests: SHA-256 hash verification of previously frozen artefacts.
    How: Write files, compute expected hashes, populate state.artefact_integrity,
      modify files to simulate tampering, then call the validator.
    Why: Frozen artefacts (fixture.md, rubric.md) must not be modified post-freeze
      to preserve pre-registration integrity.
    """

    def test_empty_integrity_dict_passes(self, make_state, experiment_dir: Path) -> None:
        """Validate that no artefact_integrity records produce no errors.

        Tests: validate_freeze_integrity with empty state.artefact_integrity
        How: Create state with no integrity records, call validator.
        Why: Experiments in early steps have no frozen artefacts yet — must not block.
        """
        state = make_state(artefact_integrity={})
        errors = validate_freeze_integrity(state, experiment_dir)
        assert errors == []

    def test_matching_hash_passes(self, make_state, experiment_dir: Path) -> None:
        """Validate that an unchanged file produces no integrity error.

        Tests: validate_freeze_integrity when file hash matches stored hash
        How: Write fixture.md, compute its SHA-256, store in state, call validator.
        Why: Unmodified frozen artefacts must be allowed through validation.
        """
        content = b"fixture content unchanged"
        fixture_path = experiment_dir / "fixture.md"
        fixture_path.write_bytes(content)
        expected_hash = hashlib.sha256(content).hexdigest()

        state = make_state(
            artefacts={"fixture.md": "fixture.md"},
            artefact_integrity={
                "fixture.md": ArtefactIntegrity(
                    sha256=expected_hash, frozen_at="2026-01-01T00:00:00+00:00", frozen_by_step="fixture"
                )
            },
        )
        errors = validate_freeze_integrity(state, experiment_dir)
        assert errors == []

    def test_modified_file_returns_frozen_artefact_modified(self, make_state, experiment_dir: Path) -> None:
        """Validate that a modified frozen file returns FROZEN_ARTEFACT_MODIFIED.

        Tests: validate_freeze_integrity when file content has changed since freeze
        How: Store hash of original content, then overwrite file with new content.
        Why: Post-freeze modification of fixture or rubric invalidates the experiment.
        """
        original_content = b"original fixture content"
        fixture_path = experiment_dir / "fixture.md"
        fixture_path.write_bytes(original_content)
        original_hash = hashlib.sha256(original_content).hexdigest()

        state = make_state(
            artefacts={"fixture.md": "fixture.md"},
            artefact_integrity={
                "fixture.md": ArtefactIntegrity(
                    sha256=original_hash, frozen_at="2026-01-01T00:00:00+00:00", frozen_by_step="fixture"
                )
            },
        )

        # Simulate modification after freeze
        fixture_path.write_bytes(b"TAMPERED fixture content")

        errors = validate_freeze_integrity(state, experiment_dir)
        assert len(errors) == 1
        assert errors[0]["code"] == FROZEN_ARTEFACT_MODIFIED
        assert errors[0]["artefact"] == "fixture.md"
        assert errors[0]["expected_hash"] == original_hash
        assert errors[0]["actual_hash"] != original_hash

    def test_missing_frozen_file_returns_frozen_artefact_modified(self, make_state, experiment_dir: Path) -> None:
        """Validate that a deleted frozen file returns FROZEN_ARTEFACT_MODIFIED.

        Tests: validate_freeze_integrity when frozen file no longer exists
        How: Store a hash for fixture.md without writing the file to disk.
        Why: Deletion of a frozen artefact is equivalent to modification — must be detected.
        """
        state = make_state(
            artefacts={"fixture.md": "fixture.md"},
            artefact_integrity={
                "fixture.md": ArtefactIntegrity(
                    sha256="abc123", frozen_at="2026-01-01T00:00:00+00:00", frozen_by_step="fixture"
                )
            },
        )
        errors = validate_freeze_integrity(state, experiment_dir)
        assert len(errors) == 1
        assert errors[0]["code"] == FROZEN_ARTEFACT_MODIFIED
        assert errors[0]["actual_hash"] is None


# ===========================================================================
# validate_rubric_scores
# ===========================================================================


class TestValidateRubricScores:
    """Tests for validate_rubric_scores().

    Tests: Rubric score completeness validation for the iterate step.
    How: Create states in iterate step with varying rubric_scores inputs.
    Why: Per-criterion scoring prevents self-reported pass/fail (architecture D3).
    """

    def test_non_iterate_step_always_passes(self, make_state, experiment_dir: Path) -> None:
        """Validate that rubric score validation is skipped for non-iterate steps.

        Tests: validate_rubric_scores with current_step != 'iterate'
        How: Create state in 'hypothesis' step, pass None for rubric_scores.
        Why: Rubric scores are only required during iterate; other steps must not block.
        """
        state = make_state(current_step="hypothesis")
        errors = validate_rubric_scores(None, state, experiment_dir)
        assert errors == []

    def test_none_rubric_scores_for_iterate_returns_missing(self, make_state) -> None:
        """Validate that None rubric_scores returns MISSING_RUBRIC_SCORES.

        Tests: validate_rubric_scores with rubric_scores=None on iterate step
        How: Create state in iterate step, pass None.
        Why: rubric_scores is mandatory for iterate — omitting it is a protocol violation.
        """
        state = make_state(current_step="iterate")
        errors = validate_rubric_scores(None, state)
        assert len(errors) == 1
        assert errors[0]["code"] == MISSING_RUBRIC_SCORES

    def test_empty_rubric_scores_returns_missing(self, make_state) -> None:
        """Validate that empty dict rubric_scores returns MISSING_RUBRIC_SCORES.

        Tests: validate_rubric_scores with rubric_scores={}
        How: Create state in iterate step, pass empty dict.
        Why: An empty scoring dict is functionally equivalent to no scores.
        """
        state = make_state(current_step="iterate")
        errors = validate_rubric_scores({}, state)
        assert len(errors) == 1
        assert errors[0]["code"] == MISSING_RUBRIC_SCORES

    def test_complete_scores_with_no_rubric_file_passes(self, make_state, experiment_dir: Path) -> None:
        """Validate that non-empty scores pass when no rubric.md exists for criteria discovery.

        Tests: validate_rubric_scores when rubric.md is not available for parsing
        How: Create iterate state with no rubric.md in artefacts, pass a non-empty scores dict.
        Why: When criteria cannot be discovered, presence of scores is sufficient.
        """
        state = make_state(current_step="iterate", artefacts={})
        scores = {"criterion_1": True}
        errors = validate_rubric_scores(scores, state, experiment_dir)
        assert errors == []

    def test_missing_criteria_returns_incomplete_rubric_scores(self, make_state, experiment_dir: Path) -> None:
        """Validate that omitting a known criterion returns INCOMPLETE_RUBRIC_SCORES.

        Tests: validate_rubric_scores completeness check against parsed rubric.md
        How: Write rubric.md with heading '## criterion_1', submit scores missing it.
        Why: Every rubric criterion must be scored — partial scoring is invalid.
        """
        rubric_path = experiment_dir / "rubric.md"
        rubric_path.write_text("## criterion_1\n- [ ] passes\n## criterion_2\n- [ ] also passes\n", encoding="utf-8")

        state = make_state(current_step="iterate", artefacts={"rubric.md": str(rubric_path)})
        scores = {"criterion_1": True}  # criterion_2 missing
        errors = validate_rubric_scores(scores, state, experiment_dir)
        assert len(errors) >= 1
        codes = {e["code"] for e in errors}
        assert INCOMPLETE_RUBRIC_SCORES in codes

    def test_extra_criteria_returns_unknown_rubric_criteria(self, make_state, experiment_dir: Path) -> None:
        """Validate that extra criteria beyond those in rubric.md returns UNKNOWN_RUBRIC_CRITERIA.

        Tests: validate_rubric_scores unknown criteria check
        How: Write rubric.md with one criterion, submit scores for two criteria.
        Why: Unknown criteria indicate a mismatch between scores and the registered rubric.
        """
        rubric_path = experiment_dir / "rubric.md"
        rubric_path.write_text("## criterion_1\n- [ ] passes\n", encoding="utf-8")

        state = make_state(current_step="iterate", artefacts={"rubric.md": str(rubric_path)})
        scores = {"criterion_1": True, "phantom_criterion": False}
        errors = validate_rubric_scores(scores, state, experiment_dir)
        assert len(errors) >= 1
        codes = {e["code"] for e in errors}
        assert UNKNOWN_RUBRIC_CRITERIA in codes

    def test_complete_matching_scores_passes(self, make_state, experiment_dir: Path) -> None:
        """Validate that scores exactly matching rubric.md criteria produce no errors.

        Tests: validate_rubric_scores with complete, matching scores dict
        How: Write rubric.md with two criteria; provide scores for exactly both.
        Why: A perfectly complete score submission must be accepted.
        """
        rubric_path = experiment_dir / "rubric.md"
        rubric_path.write_text("## criterion_1\n- [ ] passes\n## criterion_2\n- [ ] also passes\n", encoding="utf-8")
        state = make_state(current_step="iterate", artefacts={"rubric.md": str(rubric_path)})
        scores = {"criterion_1": True, "criterion_2": False}
        errors = validate_rubric_scores(scores, state, experiment_dir)
        assert errors == []


# ===========================================================================
# validate_iteration_output
# ===========================================================================


class TestValidateIterationOutput:
    """Tests for validate_iteration_output().

    Tests: Per-iteration output file key enforcement.
    How: Construct states at different iteration_count values and check the
      expected 'output-iterN.md' key requirement.
    Why: Per-iteration output enables retrospective analysis and prevents selective reporting.
    """

    def test_non_iterate_step_always_passes(self, make_state) -> None:
        """Validate that iteration output check is skipped for non-iterate steps.

        Tests: validate_iteration_output with current_step != 'iterate'
        How: Create state in 'baseline' step (which already has output-iter0.md).
        Why: Iteration output is only required during iterate steps.
        """
        state = make_state(current_step="baseline", iteration_count=0)
        errors = validate_iteration_output(state, {"log.md": "log.md"})
        assert errors == []

    def test_iterate_with_correct_output_key_passes(self, make_state) -> None:
        """Validate that providing output-iter1.md on first iterate call passes.

        Tests: validate_iteration_output on first iterate call (iteration_count=0)
        How: Create iterate state with iteration_count=0; provide output-iter1.md.
        Why: After baseline (iter0), first iterate must produce output-iter1.md.
        """
        state = make_state(current_step="iterate", iteration_count=0)
        artefacts = {"log.md": "log.md", "output-iter1.md": "output-iter1.md"}
        errors = validate_iteration_output(state, artefacts)
        assert errors == []

    def test_iterate_missing_output_key_returns_error(self, make_state) -> None:
        """Validate that missing output-iter1.md returns MISSING_ITERATION_OUTPUT.

        Tests: validate_iteration_output when output key is absent from artefacts
        How: Create iterate state, omit output-iter1.md from artefacts dict.
        Why: Each iteration must capture its output for the experiment audit trail.
        """
        state = make_state(current_step="iterate", iteration_count=0)
        artefacts = {"log.md": "log.md"}
        errors = validate_iteration_output(state, artefacts)
        assert len(errors) == 1
        assert errors[0]["code"] == MISSING_ITERATION_OUTPUT
        assert errors[0]["expected"] == "output-iter1.md"

    def test_boundary_iteration_count_zero_expects_iter1(self, make_state) -> None:
        """Validate expected key is output-iter1.md when iteration_count=0.

        Tests: validate_iteration_output boundary: iteration_count=0 → expects iter1
        How: Create state with iteration_count=0; verify expected key in error.
        Why: Iteration numbering: after baseline (iter0), validation increments to iter1.
        """
        state = make_state(current_step="iterate", iteration_count=0)
        errors = validate_iteration_output(state, {"log.md": "log.md"})
        assert errors[0]["expected"] == "output-iter1.md"

    def test_third_iteration_expects_iter3(self, make_state) -> None:
        """Validate that iteration_count=2 produces expected key output-iter3.md.

        Tests: validate_iteration_output with non-zero iteration_count
        How: Create state with iteration_count=2; verify expected key is output-iter3.md.
        Why: The expected key is always iteration_count + 1 (next iteration's output).
        """
        state = make_state(current_step="iterate", iteration_count=2)
        errors = validate_iteration_output(state, {"log.md": "log.md"})
        assert errors[0]["expected"] == "output-iter3.md"

    @pytest.mark.parametrize(
        ("iteration_count", "expected_key"),
        [(0, "output-iter1.md"), (1, "output-iter2.md"), (5, "output-iter6.md"), (9, "output-iter10.md")],
    )
    def test_iteration_key_formula(self, make_state, iteration_count: int, expected_key: str) -> None:
        """Validate that expected output key = output-iter{iteration_count+1}.md.

        Tests: validate_iteration_output key formula across multiple iteration counts
        How: Parametrized test covering boundary and mid-range values.
        Why: Key formula must be consistent across all iteration counts.
        """
        state = make_state(current_step="iterate", iteration_count=iteration_count)
        errors = validate_iteration_output(state, {"log.md": "log.md"})
        assert errors[0]["expected"] == expected_key


# ===========================================================================
# Additional validators coverage — edge cases and private helper paths
# ===========================================================================


class TestValidateArtefactContentEdgeCases:
    """Tests: Edge cases in validate_artefact_content not covered by main test classes.

    Tests: Unknown rule type (silently skipped), artefact key without dot skipped.
    How: Construct ValidationRule with an unknown type; verify no error is raised.
    Why: Forward compatibility — unknown rule types must be ignored to allow future extension.
    """

    def test_unknown_rule_type_is_skipped_silently(self, experiment_dir: Path) -> None:
        """Validate that an unrecognised rule type produces no error and does not crash.

        Tests: _apply_rule with unknown rule type (line 169 — evaluator is None)
        How: Build a step with a ValidationRule using a made-up type string.
          The rule evaluator dict will have no entry for it; it must return None.
        Why: Forward compatibility — new rule types added to JSON must not break
          existing deployments running older validator code.
        """
        from models import ValidationRule as VR

        (experiment_dir / "hypothesis.md").write_text("content", encoding="utf-8")

        # Use a custom ValidationRule type that is not in _RULE_EVALUATORS
        unknown_rule = VR.model_construct(type="future_rule_type_not_yet_implemented", params={"some": "param"})
        step_def = _make_step(required_artefacts=["hypothesis.md"], validation_rules=[unknown_rule])
        errors = validate_artefact_content(step_def, {"hypothesis.md": "hypothesis.md"}, experiment_dir)
        assert errors == []

    def test_key_without_dot_skipped_in_content_validation(self, experiment_dir: Path) -> None:
        """Validate that artefact keys without a file extension are skipped in content validation.

        Tests: validate_artefact_content skip for keys without '.' (inline values)
        How: Build step with 'criteria_passed' as required_artefact (no dot);
          call with matching artefact; expect no file read attempt.
        Why: Inline artefact keys are not file paths; content validation must not apply to them.
        """
        step_def = _make_step(
            required_artefacts=["criteria_passed"], validation_rules=[ValidationRule(type="non_empty", params={})]
        )
        # No file written — if the validator tries to read it, it would get a missing-file error
        errors = validate_artefact_content(step_def, {"criteria_passed": "true"}, experiment_dir)
        assert errors == []


class TestValidateFreezeIntegrityEdgeCases:
    """Tests: Edge cases in validate_freeze_integrity — OSError on file read.

    Tests: validate_freeze_integrity gracefully handles unreadable files.
    How: Use pytest-mock to patch Path.read_bytes to raise OSError.
    Why: Filesystem errors during hash comparison must be reported, not crash the validator.
    """

    def test_oserror_on_read_returns_frozen_artefact_modified(self, make_state, experiment_dir: Path, mocker) -> None:
        """Validate that an OSError when reading a frozen file returns FROZEN_ARTEFACT_MODIFIED.

        Tests: validate_freeze_integrity OSError branch (lines 412-420)
        How: Write fixture.md; patch Path.read_bytes to raise OSError;
          call validate_freeze_integrity; expect FROZEN_ARTEFACT_MODIFIED.
        Why: If a file exists but cannot be read, this is treated as a tamper event.
        """
        fixture_path = experiment_dir / "fixture.md"
        fixture_path.write_text("some content", encoding="utf-8")

        state = make_state(
            artefacts={"fixture.md": "fixture.md"},
            artefact_integrity={
                "fixture.md": ArtefactIntegrity(
                    sha256="abc123", frozen_at="2026-01-01T00:00:00+00:00", frozen_by_step="fixture"
                )
            },
        )

        mocker.patch("pathlib.Path.read_bytes", side_effect=OSError("Permission denied"))

        errors = validate_freeze_integrity(state, experiment_dir)
        assert len(errors) == 1
        assert errors[0]["code"] == FROZEN_ARTEFACT_MODIFIED
        assert errors[0]["actual_hash"] is None


class TestValidateArtefactContentOSError:
    """Tests: OSError when reading artefact content in validate_artefact_content.

    Tests: validate_artefact_content error handling on file read failure.
    How: Use pytest-mock to patch Path.read_text to raise OSError.
    Why: File read failures must be caught and reported rather than propagated.
    """

    def test_oserror_on_content_read_returns_content_validation_failed(self, experiment_dir: Path, mocker) -> None:
        """Validate that an OSError when reading artefact content returns CONTENT_VALIDATION_FAILED.

        Tests: validate_artefact_content OSError branch (lines 361-368)
        How: Write a file to disk; patch Path.read_text to raise OSError;
          call validate_artefact_content; expect CONTENT_VALIDATION_FAILED.
        Why: The validator must degrade gracefully and report the error rather than crashing.
        """
        (experiment_dir / "hypothesis.md").write_text("content", encoding="utf-8")
        step_def = _make_step(
            required_artefacts=["hypothesis.md"], validation_rules=[ValidationRule(type="non_empty", params={})]
        )

        mocker.patch("pathlib.Path.read_text", side_effect=OSError("Permission denied"))

        errors = validate_artefact_content(step_def, {"hypothesis.md": "hypothesis.md"}, experiment_dir)
        assert len(errors) == 1
        assert errors[0]["code"] == CONTENT_VALIDATION_FAILED
        assert errors[0]["rule"] == "file_read"


class TestExtractRubricCriteriaBoldFormat:
    """Tests: _extract_rubric_criteria_from_markdown bold list item format.

    Tests: Bold criterion format '- **criterion_name**:' parsed when no headings found.
    How: Build rubric.md with bold-format criteria; call validate_rubric_scores.
    Why: Rubric files may use bold list format instead of markdown headings.
    """

    def test_bold_format_criteria_parsed_correctly(self, make_state, experiment_dir: Path) -> None:
        """Validate that bold format '- **criterion_name**:' is parsed as criterion names.

        Tests: _extract_rubric_criteria_from_markdown bold pattern (lines 203-207)
        How: Write rubric.md using only bold list items; submit matching scores.
        Why: Rubric templates often use bold list format; the parser must handle both formats.
        """
        rubric_path = experiment_dir / "rubric.md"
        rubric_path.write_text(
            "- **accuracy**: must be accurate\n- **completeness**: must be complete\n", encoding="utf-8"
        )
        state = make_state(current_step="iterate", artefacts={"rubric.md": str(rubric_path)})
        scores = {"accuracy": True, "completeness": True}
        errors = validate_rubric_scores(scores, state, experiment_dir)
        assert errors == []

    def test_oserror_on_rubric_read_returns_empty_criteria(self, make_state, experiment_dir: Path, mocker) -> None:
        """Validate that an OSError reading rubric.md falls back to empty criteria list.

        Tests: _get_rubric_criteria OSError branch (lines 250-251)
        How: Write rubric.md; patch read_text to raise OSError for that path;
          call validate_rubric_scores with non-empty scores.
        Why: When rubric cannot be read, scores cannot be verified — accept any non-empty dict.
        """
        rubric_path = experiment_dir / "rubric.md"
        rubric_path.write_text("## criterion_1\n", encoding="utf-8")

        state = make_state(current_step="iterate", artefacts={"rubric.md": str(rubric_path)})

        mocker.patch("pathlib.Path.read_text", side_effect=OSError("Permission denied"))

        # With empty criteria list, any non-empty scores are accepted
        scores = {"criterion_1": True}
        errors = validate_rubric_scores(scores, state, experiment_dir)
        assert errors == []

    def test_missing_rubric_path_in_artefacts_returns_empty_criteria(self, make_state, experiment_dir: Path) -> None:
        """Validate that missing rubric.md artefact key results in empty criteria list.

        Tests: _get_rubric_criteria empty artefact value branch (line 246)
        How: Create iterate state with no rubric.md in artefacts; pass non-empty scores.
        Why: When rubric.md path is not in artefacts, criteria discovery returns [].
        """
        state = make_state(
            current_step="iterate",
            artefacts={},  # No rubric.md key at all
        )
        scores = {"any_criterion": True}
        errors = validate_rubric_scores(scores, state, experiment_dir)
        assert errors == []
