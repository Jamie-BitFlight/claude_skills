"""Pending owner-policy tests for exported bookend outcome models."""

from __future__ import annotations

import pytest
from sam_schema.core.models import BookendResult, BookendVerification, CriterionStatus

# ---------------------------------------------------------------------------
# CriterionStatus enum
# ---------------------------------------------------------------------------


class TestCriterionStatusEnum:
    """Verify CriterionStatus StrEnum members and values.

    Tests: Bookend criterion status values used in T0/TN comparison.
    How: Check each member name maps to the expected kebab-case value.
    Why: Status values are stored in TN-verification YAML — mismatch causes
    wrong verdict computation.
    """

    def test_passed_value(self) -> None:
        """Verify PASSED maps to 'passed'."""
        assert CriterionStatus.PASSED == "passed"

    def test_regressed_value(self) -> None:
        """Verify REGRESSED maps to 'regressed'."""
        assert CriterionStatus.REGRESSED == "regressed"

    def test_pre_existing_fail_value(self) -> None:
        """Verify PRE_EXISTING_FAIL maps to 'pre-existing-fail'."""
        assert CriterionStatus.PRE_EXISTING_FAIL == "pre-existing-fail"

    def test_newly_passing_value(self) -> None:
        """Verify NEWLY_PASSING maps to 'newly-passing'."""
        assert CriterionStatus.NEWLY_PASSING == "newly-passing"

    def test_all_members_count(self) -> None:
        """Verify the total number of status values.

        Tests: CriterionStatus completeness.
        How: Count enum members.
        Why: Adding a status without a test leaves its downstream impact uncovered.
        """
        assert len(CriterionStatus) == 4

    def test_string_serialization(self) -> None:
        """Verify CriterionStatus members serialize to their string values.

        Tests: StrEnum serialization.
        How: Cast to str and compare.
        Why: YAML writers serialize via str() — wrong output corrupts TN verification files.
        """
        assert str(CriterionStatus.REGRESSED) == "regressed"
        assert str(CriterionStatus.PRE_EXISTING_FAIL) == "pre-existing-fail"


# ---------------------------------------------------------------------------
# BookendResult model
# ---------------------------------------------------------------------------


class TestBookendResultModel:
    """Verify BookendResult model construction and serialization.

    Tests: T0/TN command execution result data model.
    How: Construct, serialize, and deserialize BookendResult instances.
    Why: BookendResult is written to T0-baseline YAML and read by TN agent.
    """

    def test_construction_with_required_fields(self) -> None:
        """Verify BookendResult with required fields constructs.

        Tests: Minimal valid BookendResult.
        How: Provide criterion_id, check_command, and exit_code.
        Why: Defaults for optional fields must be correct.
        """
        br = BookendResult(criterion_id="AC-1", check_command="pytest", exit_code=0)
        assert br.criterion_id == "AC-1"
        assert br.check_command == "pytest"
        assert br.exit_code == 0
        assert br.stdout == ""
        assert br.stderr == ""
        assert br.timestamp == ""
        assert br.duration_seconds == pytest.approx(0.0)

    def test_construction_with_all_fields(self) -> None:
        """Verify BookendResult with all fields populated.

        Tests: Full BookendResult construction.
        How: Provide every field explicitly.
        Why: T0 agent captures all fields — they must be stored correctly.
        """
        br = BookendResult(
            criterion_id="AC-1",
            check_command="uv run pytest -v",
            exit_code=1,
            stdout="FAILED 2 tests",
            stderr="error output",
            timestamp="2026-03-15T10:00:00Z",
            duration_seconds=12.5,
        )
        assert br.exit_code == 1
        assert br.stdout == "FAILED 2 tests"
        assert br.stderr == "error output"
        assert br.timestamp == "2026-03-15T10:00:00Z"
        assert br.duration_seconds == pytest.approx(12.5)

    def test_construction_via_kebab_case_aliases(self) -> None:
        """Verify BookendResult accepts kebab-case alias keys.

        Tests: YAML alias compatibility.
        How: Use model_validate with kebab-case keys.
        Why: T0-baseline YAML files use kebab-case field names.
        """
        data = {"criterion-id": "AC-2", "check-command": "basedpyright", "exit-code": 0, "duration-seconds": 3.2}
        br = BookendResult.model_validate(data)
        assert br.criterion_id == "AC-2"
        assert br.exit_code == 0
        assert br.duration_seconds == pytest.approx(3.2)

    def test_roundtrip_dump_then_validate(self) -> None:
        """Verify model_dump then model_validate roundtrip preserves data.

        Tests: Serialization/deserialization roundtrip.
        How: Dump to dict with aliases, reconstruct, compare all fields.
        Why: T0 writes and TN reads these — data loss corrupts verification.
        """
        original = BookendResult(
            criterion_id="AC-1",
            check_command="pytest -v",
            exit_code=1,
            stdout="output",
            stderr="err",
            timestamp="2026-03-15T10:00:00Z",
            duration_seconds=5.0,
        )
        dumped = original.model_dump(by_alias=True)
        restored = BookendResult.model_validate(dumped)
        assert restored.criterion_id == original.criterion_id
        assert restored.exit_code == original.exit_code
        assert restored.stdout == original.stdout
        assert restored.duration_seconds == pytest.approx(original.duration_seconds)


# ---------------------------------------------------------------------------
# BookendVerification model
# ---------------------------------------------------------------------------


class TestBookendVerificationModel:
    """Verify BookendVerification model construction for all 4 status values.

    Tests: Per-criterion T0/TN comparison result model.
    How: Construct with each CriterionStatus value, verify fields.
    Why: BookendVerification drives the TN verdict — wrong status means
    wrong PASS/FAIL decision.
    """

    def test_passed_status(self) -> None:
        """Verify BookendVerification with status=passed.

        Tests: T0 pass + TN pass = passed.
        How: Construct with exit_code 0 for both T0 and TN.
        Why: Passed criteria must not block completion.
        """
        bv = BookendVerification(
            criterion_id="AC-1", check_command="pytest", t0_exit_code=0, tn_exit_code=0, status=CriterionStatus.PASSED
        )
        assert bv.status == CriterionStatus.PASSED
        assert bv.t0_exit_code == 0
        assert bv.tn_exit_code == 0
        assert bv.stdout_diff_summary == ""

    def test_regressed_status(self) -> None:
        """Verify BookendVerification with status=regressed.

        Tests: T0 pass + TN fail = regressed.
        How: Construct with T0 exit 0, TN exit 1.
        Why: Regressed criteria block completion — must be detectable.
        """
        bv = BookendVerification(
            criterion_id="AC-2",
            check_command="basedpyright",
            t0_exit_code=0,
            tn_exit_code=1,
            status=CriterionStatus.REGRESSED,
            stdout_diff_summary="3 new type errors introduced",
        )
        assert bv.status == CriterionStatus.REGRESSED
        assert bv.stdout_diff_summary == "3 new type errors introduced"

    def test_pre_existing_fail_status(self) -> None:
        """Verify BookendVerification with status=pre-existing-fail.

        Tests: T0 fail + TN fail = pre-existing-fail.
        How: Construct with non-zero exit codes for both.
        Why: Pre-existing failures should not block completion.
        """
        bv = BookendVerification(
            criterion_id="AC-3",
            check_command="ruff check",
            t0_exit_code=1,
            tn_exit_code=1,
            status=CriterionStatus.PRE_EXISTING_FAIL,
        )
        assert bv.status == CriterionStatus.PRE_EXISTING_FAIL

    def test_newly_passing_status(self) -> None:
        """Verify BookendVerification with status=newly-passing.

        Tests: T0 fail + TN pass = newly-passing.
        How: Construct with T0 exit 1, TN exit 0.
        Why: Newly passing is a positive signal — must not be confused with regression.
        """
        bv = BookendVerification(
            criterion_id="AC-4",
            check_command="pytest -k integration",
            t0_exit_code=1,
            tn_exit_code=0,
            status=CriterionStatus.NEWLY_PASSING,
        )
        assert bv.status == CriterionStatus.NEWLY_PASSING

    def test_construction_via_kebab_case_aliases(self) -> None:
        """Verify BookendVerification accepts kebab-case alias keys.

        Tests: YAML alias compatibility.
        How: Use model_validate with kebab-case keys.
        Why: TN-verification YAML files use kebab-case field names.
        """
        data = {
            "criterion-id": "AC-1",
            "check-command": "pytest",
            "t0-exit-code": 0,
            "tn-exit-code": 0,
            "status": "passed",
            "stdout-diff-summary": "",
        }
        bv = BookendVerification.model_validate(data)
        assert bv.criterion_id == "AC-1"
        assert bv.t0_exit_code == 0
        assert bv.tn_exit_code == 0
        assert bv.status == CriterionStatus.PASSED

    def test_roundtrip_dump_then_validate(self) -> None:
        """Verify model_dump then model_validate roundtrip preserves data.

        Tests: Serialization/deserialization roundtrip.
        How: Dump to dict with aliases, reconstruct, compare all fields.
        Why: Data integrity across write/read cycles is critical for TN verdict.
        """
        original = BookendVerification(
            criterion_id="AC-1",
            check_command="pytest",
            t0_exit_code=0,
            tn_exit_code=1,
            status=CriterionStatus.REGRESSED,
            stdout_diff_summary="diff content",
        )
        dumped = original.model_dump(by_alias=True)
        restored = BookendVerification.model_validate(dumped)
        assert restored.criterion_id == original.criterion_id
        assert restored.status == original.status
        assert restored.stdout_diff_summary == original.stdout_diff_summary
