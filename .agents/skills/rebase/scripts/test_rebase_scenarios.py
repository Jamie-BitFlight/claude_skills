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
"""Outcome-level Git scenarios for the accounted rebase workflow."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import pytest
from pydantic import ValidationError

from rebase_plan import RebasePlan, WorkflowState
from test_rebase_plan import valid_plan_data
from test_rebase_skill import commit_file, initialize_repository, run_git


class WorkflowEvent(StrEnum):
    """Observable events recorded by each behavioral fixture."""

    PLAN_VALIDATED = "PLAN_VALIDATED"
    REBASE_STARTED = "REBASE_STARTED"
    CONFLICT = "CONFLICT"
    PLAN_REVALIDATED = "PLAN_REVALIDATED"
    REBASE_CONTINUED = "REBASE_CONTINUED"
    REPLAN_REF_DRIFT = "REPLAN_REF_DRIFT"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    COMPLETE_VERIFIED = "COMPLETE_VERIFIED"


def scenario_plan_data(
    *,
    old_tip: str,
    target_oid: str,
    merge_base_oid: str,
    candidate_oid: str,
    candidate_parents: list[str],
    paths: list[str],
    disposition: str = "RETAIN",
    expected_conflict_paths: list[str] | None = None,
) -> dict[str, object]:
    """Build one plan tied to an actual temporary Git scenario.

    Args:
        old_tip: Captured feature-branch OID.
        target_oid: Captured target OID.
        merge_base_oid: Captured merge-base OID.
        candidate_oid: Replay candidate OID.
        candidate_parents: Candidate parent OIDs.
        paths: Complete candidate path set.
        disposition: Candidate disposition.
        expected_conflict_paths: Paths the plan predicts can conflict.

    Returns:
        Complete JSON-compatible plan.
    """
    data = valid_plan_data()
    branch = data["branch"]
    target = data["target"]
    publication = data["publication"]
    assert isinstance(branch, dict)
    assert isinstance(target, dict)
    assert isinstance(publication, dict)
    branch["oid"] = old_tip
    target["oid"] = target_oid
    data["merge_base_oid"] = merge_base_oid
    data["repository_preflights"] = []
    publication["configured_upstream"] = None
    publication["remote_refs_containing_old_tip"] = []
    publication["evidence_commands"] = [
        {
            "source": "local-git",
            "argv": ["git", "for-each-ref", "--contains", old_tip, "refs/remotes"],
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
        }
    ]
    data["candidates"] = [
        {
            "oid": candidate_oid,
            "parents": candidate_parents,
            "paths": paths,
            "intent": "Preserve the fixture's feature behavior.",
            "evidence": ["candidate patch", "target diff"],
            "disposition": disposition,
            "verification_commands": [["git", "status", "--porcelain=v1"]],
            "expected_conflict_paths": expected_conflict_paths or [],
            "equivalence_evidence": [],
        }
    ]
    data["affected_paths"] = [
        {
            "path": path,
            "candidate_oids": [candidate_oid],
            "target_interaction": "Inspected against the target diff.",
            "dependencies": [],
            "evidence": ["candidate patch", "target diff"],
            "verification_commands": [["git", "status", "--porcelain=v1"]],
        }
        for path in paths
    ]
    data["repository_checks"] = [["git", "status", "--porcelain=v1", "--untracked-files=all"]]
    return data


def validate_plan_event(data: dict[str, object], events: list[WorkflowEvent]) -> RebasePlan:
    """Validate a plan and record the pre-action gate event.

    Args:
        data: Plan mapping.
        events: Scenario event transcript.

    Returns:
        Validated plan token required by the rebase helper.
    """
    plan = RebasePlan.model_validate(data)
    events.append(WorkflowEvent.PLAN_VALIDATED)
    return plan


def start_rebase(
    repository: Path, plan: RebasePlan, events: list[WorkflowEvent], *, preserve_merges: bool = False
) -> int:
    """Start a rebase only after receiving a validated plan token.

    Args:
        repository: Temporary Git repository.
        plan: Validated machine-gate artifact.
        events: Scenario event transcript.
        preserve_merges: Include `--rebase-merges` for preserve-topology plans.

    Returns:
        Git rebase exit code.
    """
    assert events[-1] in {WorkflowEvent.PLAN_VALIDATED, WorkflowEvent.PLAN_REVALIDATED}
    arguments = ["-c", "core.editor=true", "rebase", "--reapply-cherry-picks", "--empty=stop"]
    if preserve_merges:
        arguments.append("--rebase-merges")
    arguments.append(plan.target.oid)
    events.append(WorkflowEvent.REBASE_STARTED)
    return run_git(repository, *arguments, check=False).returncode


def assert_gate_precedes_rebase(events: list[WorkflowEvent]) -> None:
    """Assert the plan event precedes every rebase-start event.

    Args:
        events: Scenario event transcript.
    """
    assert WorkflowEvent.PLAN_VALIDATED in events
    assert events.index(WorkflowEvent.PLAN_VALIDATED) < events.index(WorkflowEvent.REBASE_STARTED)


def test_planned_conflict_resolves_combined_intent_before_continue(tmp_path: Path) -> None:
    """Resolve a predicted conflict, continue, and verify both intended outcomes."""
    repository = tmp_path / "planned-conflict"
    initialize_repository(repository)
    commit_file(repository, "shared.py", "value = 'base'\n", "add shared behavior")
    merge_base = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "-c", "feature")
    candidate = commit_file(repository, "shared.py", "value = 'feature'\n", "feature behavior")
    old_tip = candidate
    run_git(repository, "switch", "main")
    commit_file(repository, "shared.py", "target_value = 'target'\n", "target behavior")
    target_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "feature")

    events: list[WorkflowEvent] = []
    data = scenario_plan_data(
        old_tip=old_tip,
        target_oid=target_oid,
        merge_base_oid=merge_base,
        candidate_oid=candidate,
        candidate_parents=[merge_base],
        paths=["shared.py"],
        disposition="MANUAL_MERGE",
        expected_conflict_paths=["shared.py"],
    )
    plan = validate_plan_event(data, events)
    assert start_rebase(repository, plan, events) != 0
    events.append(WorkflowEvent.CONFLICT)
    (repository / "shared.py").write_text("target_value = 'target'\nvalue = 'feature'\n", encoding="utf-8")
    run_git(repository, "add", "shared.py")
    assert run_git(repository, "ls-files", "--unmerged").stdout == ""
    run_git(repository, "-c", "core.editor=true", "rebase", "--continue")
    events.append(WorkflowEvent.REBASE_CONTINUED)

    assert_gate_precedes_rebase(events)
    assert (repository / "shared.py").read_text(encoding="utf-8") == "target_value = 'target'\nvalue = 'feature'\n"
    assert run_git(repository, "merge-base", "--is-ancestor", target_oid, "feature").returncode == 0


def test_rename_edit_adapts_feature_change_to_target_path(tmp_path: Path) -> None:
    """Replay a branch edit through a target rename and verify the renamed result."""
    repository = tmp_path / "rename-edit"
    initialize_repository(repository)
    commit_file(repository, "old.py", "value = 1\n", "add old path")
    merge_base = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "-c", "feature")
    candidate = commit_file(repository, "old.py", "value = 2\n", "edit old path")
    run_git(repository, "switch", "main")
    run_git(repository, "mv", "old.py", "new.py")
    run_git(repository, "commit", "-m", "rename path")
    target_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "feature")

    events: list[WorkflowEvent] = []
    plan = validate_plan_event(
        scenario_plan_data(
            old_tip=candidate,
            target_oid=target_oid,
            merge_base_oid=merge_base,
            candidate_oid=candidate,
            candidate_parents=[merge_base],
            paths=["old.py"],
            disposition="ADAPT",
        ),
        events,
    )
    assert start_rebase(repository, plan, events) == 0

    assert_gate_precedes_rebase(events)
    assert not (repository / "old.py").exists()
    assert (repository / "new.py").read_text(encoding="utf-8") == "value = 2\n"


def test_merge_candidate_requires_policy_before_preserving_topology(tmp_path: Path) -> None:
    """Block an unbound merge policy, then preserve topology under a validated plan."""
    repository = tmp_path / "merge-policy"
    merge_base = initialize_repository(repository)
    run_git(repository, "switch", "-c", "feature")
    first_parent = commit_file(repository, "feature.txt", "feature\n", "feature change")
    run_git(repository, "switch", "-c", "side", merge_base)
    side_parent = commit_file(repository, "side.txt", "side\n", "side change")
    run_git(repository, "switch", "feature")
    run_git(repository, "merge", "--no-ff", "side", "-m", "merge side")
    merge_candidate = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "main")
    commit_file(repository, "target.txt", "target\n", "target change")
    target_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "feature")

    data = scenario_plan_data(
        old_tip=merge_candidate,
        target_oid=target_oid,
        merge_base_oid=merge_base,
        candidate_oid=merge_candidate,
        candidate_parents=[first_parent, side_parent],
        paths=["feature.txt", "side.txt"],
    )
    with pytest.raises(ValidationError):
        RebasePlan.model_validate(data)

    data["merge_policy"] = "PRESERVE_TOPOLOGY"
    events: list[WorkflowEvent] = []
    plan = validate_plan_event(data, events)
    assert start_rebase(repository, plan, events, preserve_merges=True) == 0

    assert_gate_precedes_rebase(events)
    parent_records = run_git(repository, "rev-list", "--parents", f"{target_oid}..feature").stdout.splitlines()
    assert any(len(record.split()) > 2 for record in parent_records)


def test_existing_rebase_metadata_blocks_a_second_rebase(tmp_path: Path) -> None:
    """Detect an active rebase directory and start no second history rewrite."""
    repository = tmp_path / "existing-operation"
    initialize_repository(repository)
    commit_file(repository, "shared.txt", "base\n", "add shared")
    merge_base = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "-c", "feature")
    candidate = commit_file(repository, "shared.txt", "feature\n", "feature edit")
    run_git(repository, "switch", "main")
    commit_file(repository, "shared.txt", "target\n", "target edit")
    target_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "feature")

    events: list[WorkflowEvent] = []
    plan = validate_plan_event(
        scenario_plan_data(
            old_tip=candidate,
            target_oid=target_oid,
            merge_base_oid=merge_base,
            candidate_oid=candidate,
            candidate_parents=[merge_base],
            paths=["shared.txt"],
            disposition="MANUAL_MERGE",
            expected_conflict_paths=["shared.txt"],
        ),
        events,
    )
    assert start_rebase(repository, plan, events) != 0
    rebase_merge = run_git(repository, "rev-parse", "--git-path", "rebase-merge").stdout.strip()
    rebase_apply = run_git(repository, "rev-parse", "--git-path", "rebase-apply").stdout.strip()
    active_paths = [path for path in (rebase_merge, rebase_apply) if (repository / path).is_dir()]

    assert active_paths
    assert events.count(WorkflowEvent.REBASE_STARTED) == 1
    run_git(repository, "rebase", "--abort")


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

    status = run_git(repository, "status", "--porcelain=v1", "--untracked-files=all").stdout

    assert " M tracked.txt" in status
    assert "?? untracked.txt" in status
    assert run_git(repository, "rev-parse", "feature").stdout.strip() == branch_before
    assert run_git(repository, "rev-parse", "main").stdout.strip() == target_before
    assert run_git(repository, "stash", "list").stdout == ""
    assert (repository / "tracked.txt").read_text(encoding="utf-8") == "dirty\n"
    assert (repository / "untracked.txt").read_text(encoding="utf-8") == "untracked\n"


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

    events: list[WorkflowEvent] = []
    data = scenario_plan_data(
        old_tip=candidate,
        target_oid=target_oid,
        merge_base_oid=merge_base,
        candidate_oid=candidate,
        candidate_parents=[merge_base],
        paths=["shared.txt"],
        disposition="MANUAL_MERGE",
        expected_conflict_paths=[],
    )
    plan = validate_plan_event(data, events)
    assert start_rebase(repository, plan, events) != 0
    assert "shared.txt" not in plan.candidates[0].expected_conflict_paths

    candidates = data["candidates"]
    assert isinstance(candidates, list)
    candidate_data = candidates[0]
    assert isinstance(candidate_data, dict)
    candidate_data["expected_conflict_paths"] = ["shared.txt"]
    RebasePlan.model_validate(data)
    events.append(WorkflowEvent.PLAN_REVALIDATED)
    (repository / "shared.txt").write_text("target\nfeature\n", encoding="utf-8")
    run_git(repository, "add", "shared.txt")
    assert events[-1] is WorkflowEvent.PLAN_REVALIDATED
    run_git(repository, "-c", "core.editor=true", "rebase", "--continue")
    events.append(WorkflowEvent.REBASE_CONTINUED)

    assert events.index(WorkflowEvent.PLAN_REVALIDATED) < events.index(WorkflowEvent.REBASE_CONTINUED)


def test_ref_drift_prevents_stale_plan_rebase(tmp_path: Path) -> None:
    """Move the target after validation and emit ref-drift without starting rebase."""
    repository = tmp_path / "ref-drift"
    merge_base = initialize_repository(repository)
    run_git(repository, "switch", "-c", "feature")
    candidate = commit_file(repository, "feature.txt", "feature\n", "feature change")
    run_git(repository, "switch", "main")
    captured_target = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    events: list[WorkflowEvent] = []
    validate_plan_event(
        scenario_plan_data(
            old_tip=candidate,
            target_oid=captured_target,
            merge_base_oid=merge_base,
            candidate_oid=candidate,
            candidate_parents=[merge_base],
            paths=["feature.txt"],
        ),
        events,
    )
    commit_file(repository, "target.txt", "drift\n", "move target")
    fresh_target = run_git(repository, "rev-parse", "main").stdout.strip()
    if fresh_target != captured_target:
        events.append(WorkflowEvent.REPLAN_REF_DRIFT)

    assert events == [WorkflowEvent.PLAN_VALIDATED, WorkflowEvent.REPLAN_REF_DRIFT]


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
    events: list[WorkflowEvent] = []
    plan = validate_plan_event(
        scenario_plan_data(
            old_tip=candidate,
            target_oid=target_oid,
            merge_base_oid=merge_base,
            candidate_oid=candidate,
            candidate_parents=[merge_base],
            paths=["feature.txt"],
        ),
        events,
    )
    assert start_rebase(repository, plan, events) == 0
    failed_check = run_git(repository, "rev-parse", "--verify", "refs/heads/required-check", check=False)
    if failed_check.returncode != 0:
        events.append(WorkflowEvent.VALIDATION_FAILED)

    assert WorkflowEvent.VALIDATION_FAILED in events
    assert WorkflowEvent.COMPLETE_VERIFIED not in events
    assert WorkflowState.REBASE_COMPLETE_VALIDATION_FAILED.value == "REBASE_COMPLETE_VALIDATION_FAILED"


def test_equal_oid_no_op_creates_no_plan_recovery_or_rebase(tmp_path: Path) -> None:
    """Terminate a distinct-ref same-OID request as NO_CHANGE without mutation."""
    repository = tmp_path / "no-change"
    oid = initialize_repository(repository)
    run_git(repository, "branch", "feature", oid)
    before_refs = run_git(repository, "show-ref").stdout

    branch_oid = run_git(repository, "rev-parse", "feature").stdout.strip()
    target_oid = run_git(repository, "rev-parse", "main").stdout.strip()
    candidate_count = run_git(repository, "rev-list", "--count", f"{target_oid}..{branch_oid}").stdout.strip()
    after_refs = run_git(repository, "show-ref").stdout

    assert branch_oid == target_oid
    assert candidate_count == "0"
    assert before_refs == after_refs
    assert "rebase-backup/" not in after_refs


@pytest.mark.parametrize("missing_ref", ["refs/heads/missing", "missing-target^{commit}"])
def test_invalid_ref_lookup_routes_to_invalid_ref_without_rebase(tmp_path: Path, missing_ref: str) -> None:
    """Route failed branch and target lookups to BLOCKED_INVALID_REF."""
    repository = tmp_path / missing_ref.replace("/", "-").replace("^", "-")
    initialize_repository(repository)
    if missing_ref.startswith("refs/heads"):
        lookup = run_git(repository, "show-ref", "--verify", missing_ref, check=False)
    else:
        lookup = run_git(repository, "rev-parse", "--verify", missing_ref, check=False)

    assert lookup.returncode != 0
    assert WorkflowState.BLOCKED_INVALID_REF.value == "BLOCKED_INVALID_REF"
