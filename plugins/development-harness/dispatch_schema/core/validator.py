"""Dispatch plan integrity validation and stale plan detection.

Pure functions that accept pre-loaded DispatchPlan models and return
structured result objects. No file I/O or GitHub calls here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from backlog_core.operations import MIN_CONFLICT_GROUP_SIZE

if TYPE_CHECKING:
    from dispatch_schema.core.models import DispatchPlan


@dataclass(frozen=True)
class ValidationResult:
    """Result of plan integrity validation.

    Attributes:
        is_valid: True if all checks pass (no errors, warnings are allowed).
        errors: Fatal integrity violations that must be resolved before dispatch.
        warnings: Non-fatal issues worth investigating.
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StalePlanResult:
    """Result of stale plan detection.

    Attributes:
        is_stale: True if any added or removed issues found.
        added_issues: Issue numbers present in the milestone but absent from the plan.
        removed_issues: Issue numbers present in the plan but absent from the milestone.
        message: Human-readable summary of the staleness state.
    """

    is_stale: bool
    added_issues: list[int] = field(default_factory=list)
    removed_issues: list[int] = field(default_factory=list)
    message: str = ""


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_issue_wave_map(plan: DispatchPlan) -> tuple[dict[int, int], list[int]]:
    """Return (issue_to_wave_idx, duplicate_issues) for all waves.

    Args:
        plan: DispatchPlan to index.

    Returns:
        A tuple of:
        - Mapping from issue number to wave index (0-based, first occurrence wins).
        - List of issue numbers that appeared more than once.
    """
    issue_to_wave: dict[int, int] = {}
    duplicates: list[int] = []
    for wave_idx, wave in enumerate(plan.waves):
        for item in wave.items:
            if item.issue in issue_to_wave:
                duplicates.append(item.issue)
            else:
                issue_to_wave[item.issue] = wave_idx
    return issue_to_wave, duplicates


def _check_duplicate_issues(duplicate_issues: list[int]) -> list[str]:
    """Return errors for issues that appear in multiple waves.

    Args:
        duplicate_issues: Raw list of duplicate issue numbers (may contain repeats).

    Returns:
        One error string per unique duplicate issue number.
    """
    return [
        f"Issue #{n} appears in multiple waves — each issue must appear exactly once."
        for n in sorted(set(duplicate_issues))
    ]


def _check_conflict_group_refs(plan: DispatchPlan, valid_group_ids: set[int]) -> list[str]:
    """Return errors for WaveItems referencing nonexistent ConflictGroup ids.

    Args:
        plan: DispatchPlan to inspect.
        valid_group_ids: Set of declared ConflictGroup.group_id values.

    Returns:
        One error string per invalid reference.
    """
    errors: list[str] = []
    valid_ids_repr = sorted(valid_group_ids) if valid_group_ids else "none"
    for wave in plan.waves:
        errors.extend(
            f"WaveItem issue #{item.issue} references conflict_group "
            f"{item.conflict_group} which does not exist in conflict_groups "
            f"(valid ids: {valid_ids_repr})."
            for item in wave.items
            if item.conflict_group is not None and item.conflict_group not in valid_group_ids
        )
    return errors


def _check_depends_on_existence(plan: DispatchPlan, all_plan_issues: set[int]) -> list[str]:
    """Return errors for depends_on references to issues not in any wave.

    Args:
        plan: DispatchPlan to inspect.
        all_plan_issues: Set of all issue numbers present in the plan.

    Returns:
        One error string per unknown dependency.
    """
    errors: list[str] = []
    for wave in plan.waves:
        for item in wave.items:
            errors.extend(
                f"WaveItem issue #{item.issue} depends_on #{dep} which does not appear in any wave."
                for dep in item.depends_on
                if dep not in all_plan_issues
            )
    return errors


def _check_wave_ordering(plan: DispatchPlan, issue_to_wave: dict[int, int]) -> list[str]:
    """Return errors for depends_on references that point to the same or a later wave.

    Args:
        plan: DispatchPlan to inspect.
        issue_to_wave: Mapping from issue number to 0-based wave index.

    Returns:
        One error string per ordering violation.
    """
    errors: list[str] = []
    for wave_idx, wave in enumerate(plan.waves):
        for item in wave.items:
            for dep_issue in item.depends_on:
                dep_wave_idx = issue_to_wave.get(dep_issue)
                if dep_wave_idx is None:
                    continue  # already reported by _check_depends_on_existence
                if dep_wave_idx == wave_idx:
                    errors.append(
                        f"WaveItem issue #{item.issue} (wave {wave.wave}) depends_on "
                        f"#{dep_issue} which is in the same wave — "
                        f"dependencies must reference items in earlier waves."
                    )
                elif dep_wave_idx > wave_idx:
                    later_wave_num = plan.waves[dep_wave_idx].wave
                    errors.append(
                        f"WaveItem issue #{item.issue} (wave {wave.wave}) depends_on "
                        f"#{dep_issue} which is in a later wave {later_wave_num} — "
                        f"dependencies must reference items in earlier waves."
                    )
    return errors


def _parallel_conflict_group_has_violation(issues_in_wave: list[int], dep_lookup: dict[int, set[int]]) -> bool:
    """Return True if any pair of conflict-group members lacks a dependency.

    Args:
        issues_in_wave: Issue numbers from the same conflict group in one wave.
        dep_lookup: Mapping from issue number to its depends_on set.

    Returns:
        True if at least one unlinked pair exists (violation). False otherwise.
    """
    issue_list = sorted(issues_in_wave)
    for i in range(len(issue_list)):
        for j in range(i + 1, len(issue_list)):
            a, b = issue_list[i], issue_list[j]
            if b not in dep_lookup.get(a, set()) and a not in dep_lookup.get(b, set()):
                return True
    return False


def _check_conflict_group_wave_placement(plan: DispatchPlan) -> list[str]:
    """Return errors for conflict-group members co-located in a parallel wave.

    Items in the same conflict group must not share a parallel wave unless
    every pair has at least one depending on the other (sequential chain).

    Args:
        plan: DispatchPlan to inspect.

    Returns:
        One error string per violating group/wave combination.
    """
    errors: list[str] = []

    # Build group_id → [(issue, wave_idx)]
    group_members: dict[int, list[tuple[int, int]]] = {}
    for wave_idx, wave in enumerate(plan.waves):
        for item in wave.items:
            if item.conflict_group is not None:
                group_members.setdefault(item.conflict_group, []).append((item.issue, wave_idx))

    # Pre-build full depends_on lookup (issue → set of deps) across all waves
    dep_lookup: dict[int, set[int]] = {item.issue: set(item.depends_on) for wave in plan.waves for item in wave.items}

    for group_id, members in group_members.items():
        wave_to_issues: dict[int, list[int]] = {}
        for issue_num, wave_idx in members:
            wave_to_issues.setdefault(wave_idx, []).append(issue_num)

        for wave_idx, issues_in_wave in wave_to_issues.items():
            if len(issues_in_wave) < MIN_CONFLICT_GROUP_SIZE:
                continue
            actual_wave = plan.waves[wave_idx]
            if not actual_wave.parallel:
                continue  # sequential wave — safe without explicit deps
            if _parallel_conflict_group_has_violation(issues_in_wave, dep_lookup):
                errors.append(
                    f"Conflict group {group_id} has issues {sorted(issues_in_wave)} in "
                    f"the same parallel wave {actual_wave.wave} without a dependency chain — "
                    f"conflicting items must be in different waves or linked by depends_on."
                )

    return errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_plan_integrity(plan: DispatchPlan) -> ValidationResult:
    """Validate structural integrity of a dispatch plan.

    Runs five independent checks:

    1. All conflict_group references in WaveItems point to existing
       ConflictGroup.group_id values.
    2. All depends_on issue numbers exist somewhere in the plan waves.
    3. Wave ordering is consistent: depends_on references only point to
       items in earlier waves (no forward or same-wave dependencies).
    4. No issue number appears in multiple waves.
    5. Items sharing a conflict_group are never in the same wave when
       that wave has parallel=True, unless they have an explicit
       dependency chain forcing sequential execution.

    Args:
        plan: DispatchPlan model to validate.

    Returns:
        ValidationResult with is_valid=True if no errors were found.
        Warnings are recorded but do not affect is_valid.
    """
    issue_to_wave, duplicates = _build_issue_wave_map(plan)
    all_plan_issues: set[int] = set(issue_to_wave.keys())
    valid_group_ids: set[int] = {cg.group_id for cg in plan.conflict_groups}

    errors: list[str] = []
    errors.extend(_check_duplicate_issues(duplicates))
    errors.extend(_check_conflict_group_refs(plan, valid_group_ids))
    errors.extend(_check_depends_on_existence(plan, all_plan_issues))
    errors.extend(_check_wave_ordering(plan, issue_to_wave))
    errors.extend(_check_conflict_group_wave_placement(plan))

    return ValidationResult(is_valid=not errors, errors=errors, warnings=[])


def detect_stale_plan(plan: DispatchPlan, current_issue_numbers: list[int]) -> StalePlanResult:
    """Detect whether a dispatch plan matches the current milestone state.

    Compares issue numbers in the plan's waves against the caller-provided
    current milestone issue numbers. The caller is responsible for fetching
    current state from GitHub; this function only performs the comparison.

    Args:
        plan: DispatchPlan loaded from disk.
        current_issue_numbers: Issue numbers currently in the milestone,
            pre-fetched by the caller from GitHub or another source.

    Returns:
        StalePlanResult with is_stale=True if any added or removed issues
        are found. is_stale=False means the plan and milestone match exactly.
    """
    plan_issues: set[int] = {item.issue for wave in plan.waves for item in wave.items}
    current_issues: set[int] = set(current_issue_numbers)

    added = sorted(current_issues - plan_issues)
    removed = sorted(plan_issues - current_issues)
    is_stale = bool(added or removed)

    if not is_stale:
        message = "Plan is current — no issues added or removed."
    else:
        parts: list[str] = []
        if added:
            parts.append(f"{len(added)} issue(s) added to milestone but not in plan: {added}")
        if removed:
            parts.append(f"{len(removed)} issue(s) in plan but no longer in milestone: {removed}")
        message = "; ".join(parts) + "."

    return StalePlanResult(is_stale=is_stale, added_issues=added, removed_issues=removed, message=message)
