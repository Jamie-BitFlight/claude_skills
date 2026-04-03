"""Tests for dispatch_schema.core.validator.

Covers validate_plan_integrity() and detect_stale_plan() at 95%+ line and branch coverage.

Test naming: test_{function}_{scenario}_{expected_result}
Structure: AAA (Arrange / Act / Assert)
"""

from __future__ import annotations

import pytest
from dispatch_schema.core.models import ConflictGroup, DispatchPlan, ItemPriority, MilestoneHeader, Wave, WaveItem
from dispatch_schema.core.validator import StalePlanResult, ValidationResult, detect_stale_plan, validate_plan_integrity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_plan(*, waves: list[Wave], conflict_groups: list[ConflictGroup] | None = None) -> DispatchPlan:
    """Build a DispatchPlan with the given waves and optional conflict groups."""
    return DispatchPlan(
        milestone=MilestoneHeader(number=1, title="Test Milestone", integration_branch="milestone/1-test"),
        conflict_groups=conflict_groups or [],
        waves=waves,
    )


def make_item(
    issue: int,
    *,
    title: str = "Item",
    priority: ItemPriority = ItemPriority.P2,
    conflict_group: int | None = None,
    depends_on: list[int] | None = None,
) -> WaveItem:
    """Build a WaveItem with the given properties."""
    return WaveItem(
        title=f"{title} #{issue}",
        issue=issue,
        priority=priority,
        conflict_group=conflict_group,
        depends_on=depends_on or [],
    )


# ===========================================================================
# validate_plan_integrity — happy paths
# ===========================================================================


def test_validate_plan_integrity_single_wave_no_conflicts_returns_valid(simple_plan: DispatchPlan) -> None:
    # Act
    result = validate_plan_integrity(simple_plan)

    # Assert
    assert result.is_valid is True
    assert result.errors == []


def test_validate_plan_integrity_two_waves_with_dependency_returns_valid(two_wave_plan: DispatchPlan) -> None:
    # Act
    result = validate_plan_integrity(two_wave_plan)

    # Assert
    assert result.is_valid is True
    assert result.errors == []


def test_validate_plan_integrity_conflict_group_members_in_different_waves_returns_valid() -> None:
    # Arrange — group_id 1 has issue 1 (wave 1) and issue 2 (wave 2 with dependency)
    plan = make_plan(
        conflict_groups=[ConflictGroup(group_id=1, reason="Shared file", items=["A", "B"])],
        waves=[
            Wave(wave=1, parallel=True, items=[make_item(1, conflict_group=1)]),
            Wave(wave=2, parallel=True, items=[make_item(2, conflict_group=1, depends_on=[1])]),
        ],
    )

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is True


def test_validate_plan_integrity_sequential_wave_same_conflict_group_returns_valid() -> None:
    # Arrange — parallel=False means sequential execution, no conflict violation
    plan = make_plan(
        conflict_groups=[ConflictGroup(group_id=1, reason="Shared", items=["A", "B"])],
        waves=[Wave(wave=1, parallel=False, items=[make_item(10, conflict_group=1), make_item(11, conflict_group=1)])],
    )

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is True


def test_validate_plan_integrity_no_conflict_groups_returns_valid() -> None:
    # Arrange — plan with no conflict_groups at all
    plan = make_plan(waves=[Wave(wave=1, parallel=True, items=[make_item(1), make_item(2)])])

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is True


# ===========================================================================
# Check 1: conflict_group reference to nonexistent group
# ===========================================================================


def test_validate_plan_integrity_nonexistent_conflict_group_ref_reports_error() -> None:
    # Arrange — WaveItem references group_id=99 but no such group exists
    plan = make_plan(
        conflict_groups=[ConflictGroup(group_id=1, reason="Real group", items=["A", "B"])],
        waves=[Wave(wave=1, parallel=True, items=[make_item(1, conflict_group=99)])],
    )

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is False
    assert any("conflict_group 99" in e for e in result.errors)


def test_validate_plan_integrity_multiple_bad_refs_reports_all_errors() -> None:
    # Arrange — two items with bad refs
    plan = make_plan(
        waves=[Wave(wave=1, parallel=True, items=[make_item(1, conflict_group=5), make_item(2, conflict_group=6)])]
    )

    # Act
    result = validate_plan_integrity(plan)

    # Assert — both bad refs reported
    assert result.is_valid is False
    assert len([e for e in result.errors if "conflict_group" in e]) == 2


# ===========================================================================
# Check 2: depends_on referencing unknown issues
# ===========================================================================


def test_validate_plan_integrity_depends_on_unknown_issue_reports_error() -> None:
    # Arrange — issue 2 depends on 999 which doesn't exist anywhere
    plan = make_plan(
        waves=[
            Wave(wave=1, parallel=True, items=[make_item(1)]),
            Wave(wave=2, parallel=True, items=[make_item(2, depends_on=[999])]),
        ]
    )

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is False
    assert any("#999" in e for e in result.errors)


# ===========================================================================
# Check 3: forward / same-wave dependencies
# ===========================================================================


def test_validate_plan_integrity_same_wave_dependency_reports_error() -> None:
    # Arrange — issue 2 and issue 1 are in the same wave but 2 depends on 1
    plan = make_plan(waves=[Wave(wave=1, parallel=True, items=[make_item(1), make_item(2, depends_on=[1])])])

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is False
    assert any("same wave" in e for e in result.errors)


def test_validate_plan_integrity_forward_wave_dependency_reports_error() -> None:
    # Arrange — issue 1 in wave 1 depends on issue 2 in wave 2 (forward ref)
    plan = make_plan(
        waves=[
            Wave(wave=1, parallel=True, items=[make_item(1, depends_on=[2])]),
            Wave(wave=2, parallel=True, items=[make_item(2)]),
        ]
    )

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is False
    assert any("later wave" in e for e in result.errors)


# ===========================================================================
# Check 4: duplicate issues
# ===========================================================================


def test_validate_plan_integrity_duplicate_issue_in_two_waves_reports_error() -> None:
    # Arrange — issue 5 appears in both wave 1 and wave 2
    plan = make_plan(
        waves=[Wave(wave=1, parallel=True, items=[make_item(5)]), Wave(wave=2, parallel=True, items=[make_item(5)])]
    )

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is False
    assert any("#5" in e for e in result.errors)


def test_validate_plan_integrity_duplicate_issue_same_wave_reports_error() -> None:
    # Arrange — issue 7 appears twice within the same wave
    plan = make_plan(waves=[Wave(wave=1, parallel=True, items=[make_item(7), make_item(7)])])

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is False
    assert any("#7" in e for e in result.errors)


# ===========================================================================
# Check 5: conflicting items in same parallel wave
# ===========================================================================


def test_validate_plan_integrity_conflict_group_parallel_no_dependency_reports_error() -> None:
    # Arrange — issues 10 and 11 share conflict_group=1, same parallel wave, no depends_on
    plan = make_plan(
        conflict_groups=[ConflictGroup(group_id=1, reason="Overlap", items=["A", "B"])],
        waves=[Wave(wave=1, parallel=True, items=[make_item(10, conflict_group=1), make_item(11, conflict_group=1)])],
    )

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is False
    assert any("conflict group" in e.lower() and "1" in e for e in result.errors)


def test_validate_plan_integrity_conflict_group_parallel_with_chain_returns_valid() -> None:
    # Arrange — issues 10 and 11 share group, same wave (sequential), no deps needed
    # A sequential wave (parallel=False) guarantees order — no conflict violation
    plan = make_plan(
        conflict_groups=[ConflictGroup(group_id=1, reason="Overlap", items=["A", "B"])],
        waves=[
            Wave(
                wave=1,
                parallel=False,  # sequential — no violation even without explicit deps
                items=[make_item(10, conflict_group=1), make_item(11, conflict_group=1)],
            )
        ],
    )

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is True


def test_validate_plan_integrity_three_items_partial_dependency_reports_error() -> None:
    # Arrange — issues 20,21,22 all in group 1, same parallel wave.
    # 21 depends on 20, but 22 depends on nobody → violation
    plan = make_plan(
        conflict_groups=[ConflictGroup(group_id=1, reason="Overlap", items=["A", "B", "C"])],
        waves=[
            Wave(
                wave=1,
                parallel=True,
                items=[
                    make_item(20, conflict_group=1),
                    make_item(21, conflict_group=1, depends_on=[20]),
                    make_item(22, conflict_group=1),
                ],
            )
        ],
    )

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is False


# ===========================================================================
# Multiple simultaneous violations
# ===========================================================================


def test_validate_plan_integrity_multiple_violations_reports_all_errors() -> None:
    # Arrange — bad conflict group ref AND forward dependency
    plan = make_plan(
        waves=[
            Wave(wave=1, parallel=True, items=[make_item(1, conflict_group=99, depends_on=[2])]),
            Wave(wave=2, parallel=True, items=[make_item(2)]),
        ]
    )

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is False
    # Both violations must be reported (not fail-fast after first)
    assert len(result.errors) >= 2


# ===========================================================================
# detect_stale_plan
# ===========================================================================


def test_detect_stale_plan_exact_match_returns_not_stale(simple_plan: DispatchPlan) -> None:
    # Arrange — simple_plan has issue 10
    current_issues = [10]

    # Act
    result = detect_stale_plan(simple_plan, current_issues)

    # Assert
    assert result.is_stale is False
    assert result.added_issues == []
    assert result.removed_issues == []
    assert "current" in result.message.lower()


def test_detect_stale_plan_added_issue_detected(simple_plan: DispatchPlan) -> None:
    # Arrange — milestone now has issue 10 AND 11, plan only has 10
    current_issues = [10, 11]

    # Act
    result = detect_stale_plan(simple_plan, current_issues)

    # Assert
    assert result.is_stale is True
    assert 11 in result.added_issues
    assert result.removed_issues == []


def test_detect_stale_plan_removed_issue_detected(simple_plan: DispatchPlan) -> None:
    # Arrange — milestone now has NO issues, plan still has issue 10
    current_issues: list[int] = []

    # Act
    result = detect_stale_plan(simple_plan, current_issues)

    # Assert
    assert result.is_stale is True
    assert 10 in result.removed_issues
    assert result.added_issues == []


def test_detect_stale_plan_added_and_removed_both_detected(two_wave_plan: DispatchPlan) -> None:
    # Arrange — two_wave_plan has issues 100, 101, 102
    # Current milestone: 101 stays, 100 and 102 gone, 999 added
    current_issues = [101, 999]

    # Act
    result = detect_stale_plan(two_wave_plan, current_issues)

    # Assert
    assert result.is_stale is True
    assert 999 in result.added_issues
    assert 100 in result.removed_issues
    assert 102 in result.removed_issues


def test_detect_stale_plan_empty_current_all_items_removed(two_wave_plan: DispatchPlan) -> None:
    # Arrange — milestone is now empty
    current_issues: list[int] = []

    # Act
    result = detect_stale_plan(two_wave_plan, current_issues)

    # Assert
    assert result.is_stale is True
    assert set(result.removed_issues) == {100, 101, 102}
    assert result.added_issues == []


def test_detect_stale_plan_message_contains_added_count_when_added() -> None:
    # Arrange
    plan = make_plan(waves=[Wave(wave=1, parallel=True, items=[make_item(1)])])

    # Act
    result = detect_stale_plan(plan, [1, 2, 3])

    # Assert
    assert "2" in result.message  # 2 added issues
    assert result.is_stale is True


def test_detect_stale_plan_message_contains_removed_count_when_removed() -> None:
    # Arrange
    plan = make_plan(waves=[Wave(wave=1, parallel=True, items=[make_item(1), make_item(2), make_item(3)])])

    # Act
    result = detect_stale_plan(plan, [1])

    # Assert
    assert "2" in result.message  # 2 removed issues
    assert result.is_stale is True


def test_detect_stale_plan_added_issues_list_is_sorted() -> None:
    # Arrange
    plan = make_plan(waves=[Wave(wave=1, parallel=True, items=[make_item(10)])])

    # Act
    result = detect_stale_plan(plan, [10, 30, 20])

    # Assert — added list must be sorted ascending
    assert result.added_issues == sorted(result.added_issues)


def test_detect_stale_plan_removed_issues_list_is_sorted() -> None:
    # Arrange
    plan = make_plan(waves=[Wave(wave=1, parallel=True, items=[make_item(30), make_item(10), make_item(20)])])

    # Act
    result = detect_stale_plan(plan, [])

    # Assert — removed list must be sorted ascending
    assert result.removed_issues == sorted(result.removed_issues)


# ===========================================================================
# ValidationResult and StalePlanResult dataclass contracts
# ===========================================================================


def test_validation_result_is_frozen() -> None:
    """Verify ValidationResult raises when a field assignment is attempted.

    Tests: ValidationResult frozen dataclass contract.
    How: Construct a result, then use setattr() to attempt mutation; assert FrozenInstanceError.
    Why: Callers must not mutate results after construction; frozen enforcement is the guarantee.
    """
    result = ValidationResult(is_valid=True, errors=[], warnings=[])
    with pytest.raises(AttributeError):
        result.is_valid = False


def test_stale_plan_result_is_frozen() -> None:
    """Verify StalePlanResult raises when a field assignment is attempted.

    Tests: StalePlanResult frozen dataclass contract.
    How: Construct a result, then use setattr() to attempt mutation; assert FrozenInstanceError.
    Why: Callers must not mutate results after construction; frozen enforcement is the guarantee.
    """
    result = StalePlanResult(is_stale=False, added_issues=[], removed_issues=[], message="ok")
    with pytest.raises(AttributeError):
        result.is_stale = True


def test_validation_result_warnings_default_empty() -> None:
    """Verify ValidationResult.warnings defaults to empty list.

    Tests: ValidationResult dataclass contract.
    How: Construct with only is_valid; assert warnings field is present and empty.
    Why: Callers rely on the field always being iterable, never None.
    """
    result = ValidationResult(is_valid=True)
    assert result.warnings == []


def test_stale_plan_result_default_fields_empty() -> None:
    """Verify StalePlanResult default fields are empty lists and empty string.

    Tests: StalePlanResult dataclass contract.
    How: Construct with only is_stale; verify field defaults.
    Why: Callers iterate added_issues and removed_issues unconditionally.
    """
    result = StalePlanResult(is_stale=False)
    assert result.added_issues == []
    assert result.removed_issues == []
    assert result.message == ""


# ===========================================================================
# Edge cases: empty plan / zero waves
# ===========================================================================


def test_dispatch_plan_requires_at_least_one_wave() -> None:
    """Verify DispatchPlan enforces the minimum-one-wave constraint at construction.

    Tests: DispatchPlan Pydantic model validation for waves list.
    How: Attempt to build a DispatchPlan with waves=[] and assert ValidationError.
    Why: The model schema requires at least one wave; callers must not be able to
    construct an empty-wave plan. This test documents and guards that constraint.
    """
    import pytest
    from dispatch_schema.core.models import MilestoneHeader
    from pydantic import ValidationError

    # Arrange / Act / Assert
    with pytest.raises(ValidationError, match="at least 1 item"):
        DispatchPlan(milestone=MilestoneHeader(number=1, title="T", integration_branch="milestone/1-t"), waves=[])


def test_validate_plan_integrity_single_item_plan_returns_valid() -> None:
    """Validate a single-item plan with no dependencies or conflict groups.

    Tests: validate_plan_integrity minimal happy path.
    How: One wave, one item, no conflict groups, no depends_on.
    Why: Confirms the pass-through path when all checks find nothing to report.
    """
    # Arrange
    plan = make_plan(waves=[Wave(wave=1, parallel=True, items=[make_item(1)])])

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []


# ===========================================================================
# Edge cases: conflict_group ref validation with no declared groups
# ===========================================================================


def test_validate_plan_integrity_item_refs_group_when_no_groups_declared_reports_error() -> None:
    """Validate that referencing a conflict_group when none are declared is an error.

    Tests: _check_conflict_group_refs with valid_group_ids=empty set.
    How: Wave item references conflict_group=1 but conflict_groups=[] in the plan.
         This exercises the 'valid_ids_repr = "none"' branch in _check_conflict_group_refs.
    Why: The empty-groups case is a distinct branch from the case where groups exist
    but the referenced id is simply wrong.
    """
    # Arrange
    plan = make_plan(conflict_groups=[], waves=[Wave(wave=1, parallel=True, items=[make_item(1, conflict_group=1)])])

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is False
    assert any("conflict_group 1" in e for e in result.errors)
    assert any("none" in e.lower() for e in result.errors)


# ===========================================================================
# Edge cases: valid cross-wave dependency (backward reference)
# ===========================================================================


def test_validate_plan_integrity_valid_cross_wave_dependency_returns_valid() -> None:
    """Validate that a dependency pointing to an earlier wave is accepted.

    Tests: _check_wave_ordering backward reference (dep_wave_idx < wave_idx).
    How: Issue 2 in wave 2 depends on issue 1 in wave 1 — a correct dependency.
    Why: This is the canonical valid use of depends_on. Confirms the checker
    does not flag correct back-references.
    """
    # Arrange
    plan = make_plan(
        waves=[
            Wave(wave=1, parallel=True, items=[make_item(1)]),
            Wave(wave=2, parallel=True, items=[make_item(2, depends_on=[1])]),
        ]
    )

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is True
    assert result.errors == []


def test_validate_plan_integrity_multiple_valid_deps_across_three_waves_returns_valid() -> None:
    """Validate a three-wave plan where each wave depends on all previous issues.

    Tests: _check_wave_ordering with chained cross-wave dependencies.
    How: Wave 3 item depends on wave 2, which depends on wave 1.
    Why: Multi-hop dependency chains are common in milestone plans.
    """
    # Arrange
    plan = make_plan(
        waves=[
            Wave(wave=1, parallel=True, items=[make_item(1)]),
            Wave(wave=2, parallel=True, items=[make_item(2, depends_on=[1])]),
            Wave(wave=3, parallel=True, items=[make_item(3, depends_on=[2])]),
        ]
    )

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is True


# ===========================================================================
# Edge cases: detect_stale_plan deduplication and message format
# ===========================================================================


def test_detect_stale_plan_duplicate_current_issue_numbers_deduplicated() -> None:
    """Verify detect_stale_plan deduplicates duplicate issue numbers in current_issue_numbers.

    Tests: detect_stale_plan set-conversion of current_issue_numbers.
    How: Pass current_issue_numbers with a repeated entry; result must not double-count.
    Why: Callers sourcing issues from GitHub pagination may occasionally produce
    duplicates. The function should treat the input as a set of unique identifiers.
    """
    # Arrange
    plan = make_plan(waves=[Wave(wave=1, parallel=True, items=[make_item(10), make_item(20)])])

    # Act — issue 10 appears twice in current list
    result = detect_stale_plan(plan, [10, 10, 20])

    # Assert
    assert result.is_stale is False
    assert result.added_issues == []
    assert result.removed_issues == []


def test_detect_stale_plan_message_format_both_added_and_removed() -> None:
    """Verify message format contains semicolon-joined parts and trailing period.

    Tests: detect_stale_plan message construction when both added and removed.
    How: Plan has issue 1, current has issue 2 only — produces both added and removed.
    Why: The message is user-visible output; its format must be predictable for
    downstream display and logging.
    """
    # Arrange
    plan = make_plan(waves=[Wave(wave=1, parallel=True, items=[make_item(1)])])

    # Act
    result = detect_stale_plan(plan, [2])

    # Assert
    assert result.is_stale is True
    assert ";" in result.message
    assert result.message.endswith(".")
    assert "added" in result.message
    assert "no longer" in result.message


def test_detect_stale_plan_collects_issues_across_all_waves() -> None:
    """Verify detect_stale_plan collects issue numbers from every wave in the plan.

    Tests: detect_stale_plan plan_issues set comprehension across multiple waves.
    How: Use a three-wave plan; assert that an exact match with all wave issues
    returns is_stale=False.
    Why: A bug that only reads the first wave would incorrectly flag later-wave
    issues as removed.
    """
    # Arrange — three waves, six issues total
    plan = make_plan(
        waves=[
            Wave(wave=1, parallel=True, items=[make_item(1), make_item(2)]),
            Wave(wave=2, parallel=True, items=[make_item(3), make_item(4)]),
            Wave(wave=3, parallel=True, items=[make_item(5), make_item(6)]),
        ]
    )

    # Act
    result = detect_stale_plan(plan, [1, 2, 3, 4, 5, 6])

    # Assert
    assert result.is_stale is False


def test_detect_stale_plan_single_wave_all_removed_current_empty() -> None:
    """Verify detect_stale_plan reports all plan issues as removed when current list is empty.

    Tests: detect_stale_plan with no current issues for a non-empty plan.
    How: Plan has one wave with two items; current list is empty.
    Why: A fully-cleared milestone must be detected as stale with all issues removed.
    """
    # Arrange
    plan = make_plan(waves=[Wave(wave=1, parallel=True, items=[make_item(5), make_item(10)])])

    # Act
    result = detect_stale_plan(plan, [])

    # Assert
    assert result.is_stale is True
    assert set(result.removed_issues) == {5, 10}
    assert result.added_issues == []


# ===========================================================================
# Cross-module integration: validator + stale detection on same plan
# ===========================================================================


def test_valid_plan_passes_both_integrity_and_stale_checks() -> None:
    """Verify a well-formed plan passes both validate_plan_integrity and detect_stale_plan.

    Tests: Integration between validate_plan_integrity and detect_stale_plan.
    How: Build a valid two-wave plan with dependency; run both checks.
    Why: The two functions are independent pure functions that callers invoke
    together. A regression in one must not silently affect the other.
    """
    # Arrange
    plan = make_plan(
        waves=[
            Wave(wave=1, parallel=True, items=[make_item(100)]),
            Wave(wave=2, parallel=True, items=[make_item(101, depends_on=[100])]),
        ]
    )
    current_issues = [100, 101]

    # Act
    integrity = validate_plan_integrity(plan)
    staleness = detect_stale_plan(plan, current_issues)

    # Assert
    assert integrity.is_valid is True
    assert staleness.is_stale is False


def test_validate_plan_integrity_conflict_group_members_split_across_waves_with_dep_valid() -> None:
    """Validate conflict-group members in different waves with a cross-wave dependency.

    Tests: _check_conflict_group_wave_placement — members separated across waves.
    How: Issue 10 in wave 1, issue 11 in wave 2 (depends on 10); same conflict group.
         The dependency is backward (wave 1 → wave 2), which is valid.
    Why: Splitting conflict-group members across waves with a sequential dependency
    is the canonical correct resolution of a conflict. This test confirms the
    checker accepts it.
    """
    # Arrange
    plan = make_plan(
        conflict_groups=[ConflictGroup(group_id=1, reason="Overlap", items=["A", "B"])],
        waves=[
            Wave(wave=1, parallel=True, items=[make_item(10, conflict_group=1)]),
            Wave(wave=2, parallel=True, items=[make_item(11, conflict_group=1, depends_on=[10])]),
        ],
    )

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is True
    assert result.errors == []


@pytest.mark.parametrize(
    ("parallel", "expected_valid"),
    [
        (True, False),  # parallel wave — co-location without dep chain is a violation
        (False, True),  # sequential wave — execution order guaranteed, no violation
    ],
)
def test_validate_plan_integrity_conflict_group_wave_type_parametrized(parallel: bool, expected_valid: bool) -> None:
    """Parametrize wave.parallel flag for conflict-group co-location validation.

    Tests: _check_conflict_group_wave_placement parallel vs sequential distinction.
    How: Two items share a conflict group in the same wave; vary the parallel flag.
    Why: The checker only flags parallel waves; sequential execution is safe
    regardless of depends_on. This test documents that boundary.
    """
    # Arrange
    plan = make_plan(
        conflict_groups=[ConflictGroup(group_id=1, reason="Overlap", items=["A", "B"])],
        waves=[
            Wave(wave=1, parallel=parallel, items=[make_item(10, conflict_group=1), make_item(11, conflict_group=1)])
        ],
    )

    # Act
    result = validate_plan_integrity(plan)

    # Assert
    assert result.is_valid is expected_valid
