#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
#   "pytest",
# ]
# [tool.ty.environment]
# root = ["."]
# ///
"""Blocked, recovery, and validation scenarios for the accounted rebase workflow."""

from __future__ import annotations

from pathlib import Path

import pytest

from rebase_plan import RebasePlan, WorkflowState
from test_rebase_scenarios import (
    CandidateFixture,
    WorkflowEvent,
    begin_scenario,
    capture_rebase_help,
    finish_scenario,
    scenario_plan_data,
    start_rebase,
    validate_plan_event,
)
from test_rebase_skill import commit_file, initialize_repository, run_git


def test_existing_rebase_metadata_blocks_a_second_rebase(tmp_path: Path) -> None:
    """Detect an active rebase directory and start no second history rewrite."""
    repository = tmp_path / "existing-operation"
    initialize_repository(repository)
    commit_file(repository, "shared.txt", "base\n", "add shared")
    run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "-c", "feature")
    commit_file(repository, "shared.txt", "feature\n", "feature edit")
    run_git(repository, "switch", "main")
    commit_file(repository, "shared.txt", "target\n", "target edit")
    target_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "feature")

    _, empty_option = capture_rebase_help(repository)
    run_git(
        repository,
        "-c",
        "core.editor=true",
        "rebase",
        "--reapply-cherry-picks",
        f"--empty={empty_option}",
        target_oid,
        check=False,
    )
    evidence = begin_scenario(repository)
    rebase_merge = run_git(
        repository, "rev-parse", "--git-path", "rebase-merge", transcript=evidence.commands
    ).stdout.strip()
    rebase_apply = run_git(
        repository, "rev-parse", "--git-path", "rebase-apply", transcript=evidence.commands
    ).stdout.strip()
    active_paths = [path for path in (rebase_merge, rebase_apply) if (repository / path).is_dir()]
    evidence.events.append(WorkflowEvent.BLOCKED_GIT_STATE)

    assert active_paths
    assert WorkflowEvent.REBASE_STARTED not in evidence.events
    assert not any("rebase" in command[1:] for command in evidence.commands)
    finish_scenario(repository, evidence)
    run_git(repository, "rebase", "--abort")


def test_net_zero_inventory_accounts_for_both_source_commits(tmp_path: Path) -> None:
    """Keep both replay candidates when their combined endpoint diff is empty."""
    repository = tmp_path / "net-zero"
    merge_base = initialize_repository(repository)
    commit_file(repository, "shared.txt", "base\n", "add shared")
    merge_base = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "-c", "feature")
    changed = commit_file(repository, "shared.txt", "changed\n", "temporary change")
    reverted = commit_file(repository, "shared.txt", "base\n", "restore original")
    target_oid = merge_base

    evidence = begin_scenario(repository)
    plan = validate_plan_event(
        repository,
        scenario_plan_data(
            old_tip=reverted,
            target_oid=target_oid,
            merge_base_oid=merge_base,
            candidates=[
                CandidateFixture(oid=changed, parents=[merge_base], paths=["shared.txt"]),
                CandidateFixture(oid=reverted, parents=[changed], paths=["shared.txt"]),
            ],
        ),
        evidence,
    )

    assert [candidate.oid for candidate in plan.candidates] == [changed, reverted]
    assert run_git(repository, "diff", "--name-only", f"{merge_base}..{reverted}").stdout == ""
    finish_scenario(repository, evidence)


def test_clean_cherry_pick_is_accounted_as_evidence_backed_drop(tmp_path: Path) -> None:
    """Retain the patch-equivalent candidate in the validated inventory."""
    repository = tmp_path / "clean-cherry"
    merge_base = initialize_repository(repository)
    run_git(repository, "switch", "-c", "feature")
    candidate = commit_file(repository, "shared.txt", "shared\n", "feature patch")
    run_git(repository, "switch", "main")
    commit_file(repository, "target.txt", "target\n", "target change")
    run_git(repository, "cherry-pick", candidate)
    target_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "feature")

    evidence = begin_scenario(repository)
    plan = validate_plan_event(
        repository,
        scenario_plan_data(
            old_tip=candidate,
            target_oid=target_oid,
            merge_base_oid=merge_base,
            candidates=[
                CandidateFixture(
                    oid=candidate,
                    parents=[merge_base],
                    paths=["shared.txt"],
                    disposition="REDUNDANT_DROP",
                    equivalence_evidence=["git cherry classified the patch as equivalent"],
                )
            ],
        ),
        evidence,
    )

    assert plan.candidates[0].disposition.value == "REDUNDANT_DROP"
    finish_scenario(repository, evidence)


def test_becomes_empty_stops_after_complete_gate(tmp_path: Path) -> None:
    """Surface the exact candidate that becomes empty instead of silently dropping it."""
    repository = tmp_path / "becomes-empty"
    merge_base = initialize_repository(repository)
    run_git(repository, "switch", "-c", "feature")
    candidate = commit_file(repository, "shared.txt", "same\n", "feature outcome")
    run_git(repository, "switch", "main")
    commit_file(repository, "shared.txt", "same\n", "target outcome")
    target_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "feature")

    evidence = begin_scenario(repository)
    plan = validate_plan_event(
        repository,
        scenario_plan_data(
            old_tip=candidate,
            target_oid=target_oid,
            merge_base_oid=merge_base,
            candidates=[
                CandidateFixture(
                    oid=candidate,
                    parents=[merge_base],
                    paths=["shared.txt"],
                    disposition="REDUNDANT_DROP",
                    equivalence_evidence=["target tree already contains the candidate outcome"],
                )
            ],
        ),
        evidence,
    )
    assert start_rebase(repository, plan, evidence) != 0
    evidence.events.append(WorkflowEvent.EMPTY_COMMIT_DECISION)

    assert run_git(repository, "rev-parse", "REBASE_HEAD").stdout.strip() == candidate
    finish_scenario(repository, evidence)
    run_git(repository, "rebase", "--abort")


def test_foreign_worktree_owner_blocks_without_mutating_owner(tmp_path: Path) -> None:
    """Report foreign ownership while preserving its HEAD and uncommitted file."""
    repository = tmp_path / "worktree-owner"
    initialize_repository(repository)
    run_git(repository, "switch", "-c", "feature")
    commit_file(repository, "feature.txt", "feature\n", "feature change")
    feature_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "main")
    foreign = tmp_path / "foreign"
    run_git(repository, "worktree", "add", str(foreign), "feature")
    (foreign / "uncommitted.txt").write_text("owned\n", encoding="utf-8")

    evidence = begin_scenario(repository)
    listing = run_git(repository, "worktree", "list", "--porcelain", transcript=evidence.commands).stdout
    evidence.events.append(WorkflowEvent.BLOCKED_WORKTREE_IN_USE)

    assert str(foreign) in listing
    assert run_git(foreign, "rev-parse", "HEAD").stdout.strip() == feature_oid
    assert (foreign / "uncommitted.txt").read_text(encoding="utf-8") == "owned\n"
    finish_scenario(repository, evidence)


def test_dirty_owning_worktree_blocks_without_stash_or_ref_change(tmp_path: Path) -> None:
    """Observe tracked and untracked dirt while preserving refs and filesystem state."""
    repository = tmp_path / "dirty-worktree"
    initialize_repository(repository)
    run_git(repository, "switch", "-c", "feature")
    commit_file(repository, "tracked.txt", "committed\n", "add tracked file")
    branch_before = run_git(repository, "rev-parse", "feature").stdout.strip()
    target_before = run_git(repository, "rev-parse", "main").stdout.strip()
    (repository / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    (repository / "untracked.txt").write_text("untracked\n", encoding="utf-8")

    evidence = begin_scenario(repository)
    status = run_git(
        repository, "status", "--porcelain=v1", "--untracked-files=all", transcript=evidence.commands
    ).stdout
    evidence.events.append(WorkflowEvent.BLOCKED_GIT_STATE)

    assert " M tracked.txt" in status
    assert "?? untracked.txt" in status
    assert run_git(repository, "rev-parse", "feature").stdout.strip() == branch_before
    assert run_git(repository, "rev-parse", "main").stdout.strip() == target_before
    assert run_git(repository, "stash", "list").stdout == ""
    assert (repository / "tracked.txt").read_text(encoding="utf-8") == "dirty\n"
    assert (repository / "untracked.txt").read_text(encoding="utf-8") == "untracked\n"
    finish_scenario(repository, evidence)


def test_unexpected_conflict_requires_plan_revalidation_before_continue(tmp_path: Path) -> None:
    """Record an unpredicted conflict and revalidate the plan before continuation."""
    repository = tmp_path / "unexpected-conflict"
    initialize_repository(repository)
    commit_file(repository, "shared.txt", "base\n", "add shared")
    merge_base = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "-c", "feature")
    candidate = commit_file(repository, "shared.txt", "feature\n", "feature edit")
    run_git(repository, "switch", "main")
    commit_file(repository, "shared.txt", "target\n", "target edit")
    target_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "feature")

    evidence = begin_scenario(repository)
    data = scenario_plan_data(
        old_tip=candidate,
        target_oid=target_oid,
        merge_base_oid=merge_base,
        candidates=[
            CandidateFixture(oid=candidate, parents=[merge_base], paths=["shared.txt"], disposition="MANUAL_MERGE")
        ],
    )
    plan = validate_plan_event(repository, data, evidence)
    assert start_rebase(repository, plan, evidence) != 0
    assert "shared.txt" not in plan.candidates[0].expected_conflict_paths

    candidates = data["candidates"]
    assert isinstance(candidates, list)
    candidate_data = candidates[0]
    assert isinstance(candidate_data, dict)
    candidate_data["expected_conflict_paths"] = ["shared.txt"]
    RebasePlan.model_validate(data)
    evidence.events.append(WorkflowEvent.PLAN_REVALIDATED)
    (repository / "shared.txt").write_text("target\nfeature\n", encoding="utf-8")
    run_git(repository, "add", "shared.txt", transcript=evidence.commands)
    assert evidence.events[-1] is WorkflowEvent.PLAN_REVALIDATED
    run_git(repository, "-c", "core.editor=true", "rebase", "--continue", transcript=evidence.commands)
    evidence.events.append(WorkflowEvent.REBASE_CONTINUED)

    assert evidence.events.index(WorkflowEvent.PLAN_REVALIDATED) < evidence.events.index(WorkflowEvent.REBASE_CONTINUED)
    finish_scenario(repository, evidence)


def test_ref_drift_prevents_stale_plan_rebase(tmp_path: Path) -> None:
    """Move the target after validation and emit ref-drift without starting rebase."""
    repository = tmp_path / "ref-drift"
    merge_base = initialize_repository(repository)
    run_git(repository, "switch", "-c", "feature")
    candidate = commit_file(repository, "feature.txt", "feature\n", "feature change")
    run_git(repository, "switch", "main")
    captured_target = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    evidence = begin_scenario(repository)
    validate_plan_event(
        repository,
        scenario_plan_data(
            old_tip=candidate,
            target_oid=captured_target,
            merge_base_oid=merge_base,
            candidates=[CandidateFixture(oid=candidate, parents=[merge_base], paths=["feature.txt"])],
        ),
        evidence,
    )
    commit_file(repository, "target.txt", "drift\n", "move target")
    fresh_target = run_git(repository, "rev-parse", "main").stdout.strip()
    if fresh_target != captured_target:
        evidence.events.append(WorkflowEvent.REPLAN_REF_DRIFT)

    assert evidence.events == [
        WorkflowEvent.RECOVERY_VERIFIED,
        WorkflowEvent.PLAN_VALIDATED,
        WorkflowEvent.REPLAN_REF_DRIFT,
    ]
    finish_scenario(repository, evidence)


def test_validation_failure_never_emits_complete_verified(tmp_path: Path) -> None:
    """Finish a rebase, fail a named check, and retain the failure terminal."""
    repository = tmp_path / "validation-failure"
    merge_base = initialize_repository(repository)
    run_git(repository, "switch", "-c", "feature")
    candidate = commit_file(repository, "feature.txt", "feature\n", "feature change")
    run_git(repository, "switch", "main")
    commit_file(repository, "target.txt", "target\n", "target change")
    target_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "feature")
    evidence = begin_scenario(repository)
    plan = validate_plan_event(
        repository,
        scenario_plan_data(
            old_tip=candidate,
            target_oid=target_oid,
            merge_base_oid=merge_base,
            candidates=[CandidateFixture(oid=candidate, parents=[merge_base], paths=["feature.txt"])],
        ),
        evidence,
    )
    assert start_rebase(repository, plan, evidence) == 0
    failed_check = run_git(
        repository, "rev-parse", "--verify", "refs/heads/required-check", check=False, transcript=evidence.commands
    )
    if failed_check.returncode != 0:
        evidence.events.append(WorkflowEvent.VALIDATION_FAILED)

    assert WorkflowEvent.VALIDATION_FAILED in evidence.events
    assert WorkflowEvent.COMPLETE_VERIFIED not in evidence.events
    assert WorkflowState.REBASE_COMPLETE_VALIDATION_FAILED.value == "REBASE_COMPLETE_VALIDATION_FAILED"
    finish_scenario(repository, evidence)


def test_equal_oid_no_op_creates_no_plan_recovery_or_rebase(tmp_path: Path) -> None:
    """Terminate a distinct-ref same-OID request as NO_CHANGE without mutation."""
    repository = tmp_path / "no-change"
    oid = initialize_repository(repository)
    run_git(repository, "branch", "feature", oid)
    evidence = begin_scenario(repository)
    before_refs = evidence.pre_refs

    branch_oid = run_git(repository, "rev-parse", "feature").stdout.strip()
    target_oid = run_git(repository, "rev-parse", "main").stdout.strip()
    candidate_count = run_git(repository, "rev-list", "--count", f"{target_oid}..{branch_oid}").stdout.strip()
    after_refs = run_git(repository, "show-ref").stdout
    evidence.events.append(WorkflowEvent.NO_CHANGE)

    assert branch_oid == target_oid
    assert candidate_count == "0"
    assert before_refs == after_refs
    assert "rebase-backup/" not in after_refs
    finish_scenario(repository, evidence)


@pytest.mark.parametrize("missing_ref", ["refs/heads/missing", "missing-target^{commit}"])
def test_invalid_ref_lookup_routes_to_invalid_ref_without_rebase(tmp_path: Path, missing_ref: str) -> None:
    """Route failed branch and target lookups to BLOCKED_INVALID_REF."""
    repository = tmp_path / missing_ref.replace("/", "-").replace("^", "-")
    initialize_repository(repository)
    evidence = begin_scenario(repository)
    if missing_ref.startswith("refs/heads"):
        lookup = run_git(repository, "show-ref", "--verify", missing_ref, check=False, transcript=evidence.commands)
    else:
        lookup = run_git(repository, "rev-parse", "--verify", missing_ref, check=False, transcript=evidence.commands)
    evidence.events.append(WorkflowEvent.BLOCKED_INVALID_REF)

    assert lookup.returncode != 0
    assert WorkflowState.BLOCKED_INVALID_REF.value == "BLOCKED_INVALID_REF"
    finish_scenario(repository, evidence)
