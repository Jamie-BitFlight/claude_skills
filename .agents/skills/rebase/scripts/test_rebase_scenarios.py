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
from pydantic import BaseModel, Field

from rebase_plan import RebasePlan
from rebase_test_support import capture_repository_state, commit_file, initialize_repository, run_git
from test_rebase_plan import valid_plan_data


class WorkflowEvent(StrEnum):
    """Observable events recorded by each behavioral fixture."""

    RECOVERY_VERIFIED = "RECOVERY_VERIFIED"
    PLAN_VALIDATED = "PLAN_VALIDATED"
    REBASE_STARTED = "REBASE_STARTED"
    CONFLICT = "CONFLICT"
    PLAN_REVALIDATED = "PLAN_REVALIDATED"
    REBASE_CONTINUED = "REBASE_CONTINUED"
    BLOCKED_GIT_STATE = "BLOCKED_GIT_STATE"
    BLOCKED_INVALID_REF = "BLOCKED_INVALID_REF"
    BLOCKED_WORKTREE_IN_USE = "BLOCKED_WORKTREE_IN_USE"
    NO_CHANGE = "NO_CHANGE"
    EMPTY_COMMIT_DECISION = "EMPTY_COMMIT_DECISION"
    REBASE_ABORTED_RESTORED = "REBASE_ABORTED_RESTORED"
    REPLAN_REF_DRIFT = "REPLAN_REF_DRIFT"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    COMPLETE_VERIFIED = "COMPLETE_VERIFIED"


class CandidateFixture(BaseModel):
    """One planned candidate derived from a real Git replay inventory."""

    oid: str
    parents: list[str]
    paths: list[str]
    disposition: str = "RETAIN"
    expected_conflict_paths: list[str] = Field(default_factory=list)
    equivalence_evidence: list[str] = Field(default_factory=list)


class ScenarioEvidence(BaseModel):
    """Pre/post refs, complete command transcript, and workflow states for one scenario."""

    pre_refs: str
    post_refs: str = ""
    commands: list[tuple[str, ...]] = Field(default_factory=list)
    events: list[WorkflowEvent] = Field(default_factory=list)
    recovery_verified_at: int | None = None
    plan_validated_at: int | None = None


def scenario_plan_data(
    *, old_tip: str, target_oid: str, merge_base_oid: str, candidates: list[CandidateFixture]
) -> dict[str, object]:
    """Build one plan tied to an actual temporary Git scenario.

    Args:
        old_tip: Captured feature-branch OID.
        target_oid: Captured target OID.
        merge_base_oid: Captured merge-base OID.
        candidates: Complete ordered replay-candidate inventory.

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
    branch["ref"] = "refs/heads/feature"
    branch["oid"] = old_tip
    target["ref"] = "refs/heads/main"
    target["oid"] = target_oid
    data["merge_base_oid"] = merge_base_oid
    data["repository_preflights"] = []
    data["required_preflights"] = []
    publication["configured_upstream"] = None
    publication["remote_refs_containing_old_tip"] = []
    publication["evidence_commands"] = [
        {
            "source": "local-git",
            "argv": ["git", "for-each-ref", "--format=%(refname)", "--contains", old_tip, "refs/remotes"],
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
        }
    ]
    data["candidates"] = [
        {
            "oid": candidate.oid,
            "parents": candidate.parents,
            "paths": candidate.paths,
            "intent": "Preserve the fixture's feature behavior.",
            "evidence": ["candidate patch", "target diff"],
            "disposition": candidate.disposition,
            "verification_commands": [["git", "status", "--porcelain=v1"]],
            "expected_conflict_paths": candidate.expected_conflict_paths,
            "equivalence_evidence": candidate.equivalence_evidence,
        }
        for candidate in candidates
    ]
    all_paths = sorted({path for candidate in candidates for path in candidate.paths})
    data["affected_paths"] = [
        {
            "path": path,
            "candidate_oids": [candidate.oid for candidate in candidates if path in candidate.paths],
            "target_interaction": "Inspected against the target diff.",
            "dependencies": [],
            "evidence": ["candidate patch", "target diff"],
            "verification_commands": [["git", "status", "--porcelain=v1"]],
        }
        for path in all_paths
    ]
    data["repository_checks"] = [["git", "status", "--porcelain=v1", "--untracked-files=all"]]
    return data


def begin_scenario(repository: Path) -> ScenarioEvidence:
    """Capture immutable refs immediately before workflow invocation."""
    return ScenarioEvidence(pre_refs=run_git(repository, "show-ref").stdout)


def capture_rebase_help(
    repository: Path, transcript: list[tuple[str, ...]] | None = None
) -> tuple[dict[str, object], str]:
    """Capture installed rebase options and select its stop-on-empty spelling."""
    result = run_git(repository, "rebase", "-h", check=False, transcript=transcript)
    empty_line = next(line for line in f"{result.stdout}\n{result.stderr}".splitlines() if "--empty" in line)
    if "stop" in empty_line:
        option = "stop"
    elif "ask" in empty_line:
        option = "ask"
    else:
        raise AssertionError("installed Git help has no stop-on-empty spelling")
    return (
        {
            "source": "installed-git",
            "argv": ["git", "rebase", "-h"],
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        },
        option,
    )


def finish_scenario(repository: Path, evidence: ScenarioEvidence) -> None:
    """Capture post refs and require every rebase to follow plan and recovery gates."""
    evidence.post_refs = run_git(repository, "show-ref").stdout
    rebase_positions = [
        index
        for index, command in enumerate(evidence.commands)
        if "rebase" in command and "-h" not in command and "--help" not in command
    ]
    if rebase_positions:
        assert WorkflowEvent.PLAN_VALIDATED in evidence.events
        assert WorkflowEvent.RECOVERY_VERIFIED in evidence.events
        assert evidence.events.index(WorkflowEvent.RECOVERY_VERIFIED) < evidence.events.index(
            WorkflowEvent.PLAN_VALIDATED
        )
        assert evidence.recovery_verified_at is not None
        assert evidence.plan_validated_at is not None
        assert evidence.recovery_verified_at <= evidence.plan_validated_at
        assert all(position >= evidence.plan_validated_at for position in rebase_positions)


def validate_plan_event(repository: Path, data: dict[str, object], evidence: ScenarioEvidence) -> RebasePlan:
    """Validate a plan and record the pre-action gate event.

    Args:
        data: Plan mapping.
        evidence: Scenario refs, commands, and state transitions.

    Returns:
        Validated plan token required by the rebase helper.
    """
    branch = data["branch"]
    target = data["target"]
    assert isinstance(branch, dict)
    assert isinstance(target, dict)
    old_tip = branch["oid"]
    target_oid = target["oid"]
    assert isinstance(old_tip, str)
    assert isinstance(target_oid, str)
    branch_ref = branch["ref"]
    target_ref = target["ref"]
    assert isinstance(branch_ref, str)
    assert isinstance(target_ref, str)
    repository_state, publication = capture_repository_state(
        repository, branch_ref=branch_ref, target_ref=target_ref, transcript=evidence.commands
    )
    data["repository_state"] = repository_state
    data["publication"] = publication
    data["execution_worktree"] = str(repository.resolve())
    current_branch = repository_state["current_branch"]
    assert isinstance(current_branch, dict)
    current_branch_name = current_branch["stdout"]
    assert isinstance(current_branch_name, str)
    data["execution_mode"] = (
        "CURRENT_BRANCH"
        if current_branch_name.strip() == branch_ref.removeprefix("refs/heads/")
        else "AUTHORIZED_BRANCH_TRANSFER"
    )
    help_evidence, empty_option = capture_rebase_help(repository, evidence.commands)
    data["rebase_help"] = help_evidence
    data["becomes_empty_option"] = empty_option
    inventory = run_git(
        repository,
        "rev-list",
        "--reverse",
        "--topo-order",
        "--parents",
        f"{target_oid}..{old_tip}",
        transcript=evidence.commands,
    )
    data["replay_inventory"] = {
        "source": "local-git",
        "argv": list(evidence.commands[-1]),
        "exit_code": inventory.returncode,
        "stdout": inventory.stdout,
        "stderr": inventory.stderr,
    }
    recovery_ref = data["recovery_ref"]
    assert isinstance(recovery_ref, str)
    run_git(repository, "branch", recovery_ref.removeprefix("refs/heads/"), old_tip, transcript=evidence.commands)
    recovery = run_git(repository, "rev-parse", "--verify", f"{recovery_ref}^{{commit}}", transcript=evidence.commands)
    data["recovery_verification"] = {
        "source": "local-git",
        "argv": list(evidence.commands[-1]),
        "exit_code": recovery.returncode,
        "stdout": recovery.stdout,
        "stderr": recovery.stderr,
    }
    evidence.events.append(WorkflowEvent.RECOVERY_VERIFIED)
    evidence.recovery_verified_at = len(evidence.commands)
    plan = RebasePlan.model_validate(data)
    evidence.events.append(WorkflowEvent.PLAN_VALIDATED)
    evidence.plan_validated_at = len(evidence.commands)
    return plan


def start_rebase(
    repository: Path, plan: RebasePlan, evidence: ScenarioEvidence, *, preserve_merges: bool = False
) -> int:
    """Start a rebase only after receiving a validated plan token.

    Args:
        repository: Temporary Git repository.
        plan: Validated machine-gate artifact.
        evidence: Scenario refs, commands, and state transitions.
        preserve_merges: Include `--rebase-merges` for preserve-topology plans.

    Returns:
        Git rebase exit code.
    """
    assert evidence.events[-1] in {WorkflowEvent.PLAN_VALIDATED, WorkflowEvent.PLAN_REVALIDATED}
    arguments = [
        "-c",
        "core.editor=true",
        "rebase",
        "--reapply-cherry-picks",
        f"--empty={plan.becomes_empty_option.value}",
    ]
    if preserve_merges:
        arguments.append("--rebase-merges")
    arguments.append(plan.target.oid)
    evidence.events.append(WorkflowEvent.REBASE_STARTED)
    return run_git(repository, *arguments, check=False, transcript=evidence.commands).returncode


def assert_gate_precedes_rebase(evidence: ScenarioEvidence) -> None:
    """Assert the plan event precedes every rebase-start event.

    Args:
        evidence: Scenario refs, commands, and state transitions.
    """
    assert WorkflowEvent.RECOVERY_VERIFIED in evidence.events
    assert WorkflowEvent.PLAN_VALIDATED in evidence.events
    assert evidence.events.index(WorkflowEvent.RECOVERY_VERIFIED) < evidence.events.index(WorkflowEvent.PLAN_VALIDATED)
    assert evidence.events.index(WorkflowEvent.PLAN_VALIDATED) < evidence.events.index(WorkflowEvent.REBASE_STARTED)


@pytest.mark.parametrize("remote_url", ["git@github.com:group/project.git", "git@gitlab.example.com:group/project.git"])
def test_linear_forge_neutral_rebase_records_complete_gate_and_refs(tmp_path: Path, remote_url: str) -> None:
    """Run the universal linear path identically for GitHub- and GitLab-shaped remotes."""
    repository = tmp_path / ("github" if "github" in remote_url else "gitlab")
    merge_base = initialize_repository(repository)
    run_git(repository, "remote", "add", "origin", remote_url)
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
    evidence.events.append(WorkflowEvent.COMPLETE_VERIFIED)

    assert_gate_precedes_rebase(evidence)
    assert run_git(repository, "merge-base", "--is-ancestor", target_oid, "feature").returncode == 0
    assert run_git(repository, "status", "--porcelain=v1", "--untracked-files=all").stdout == ""
    finish_scenario(repository, evidence)


def test_abort_restores_pre_rebase_refs_after_complete_gate(tmp_path: Path) -> None:
    """Abort a gated conflict and prove exact old-tip and recovery restoration."""
    repository = tmp_path / "abort"
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
                    disposition="MANUAL_MERGE",
                    expected_conflict_paths=["shared.txt"],
                )
            ],
        ),
        evidence,
    )
    assert start_rebase(repository, plan, evidence) != 0
    run_git(repository, "rebase", "--abort", transcript=evidence.commands)
    evidence.events.append(WorkflowEvent.REBASE_ABORTED_RESTORED)

    assert run_git(repository, "rev-parse", "feature").stdout.strip() == candidate
    assert run_git(repository, "rev-parse", plan.recovery_ref).stdout.strip() == candidate
    assert run_git(repository, "status", "--porcelain=v1", "--untracked-files=all").stdout == ""
    finish_scenario(repository, evidence)


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

    evidence = begin_scenario(repository)
    data = scenario_plan_data(
        old_tip=old_tip,
        target_oid=target_oid,
        merge_base_oid=merge_base,
        candidates=[
            CandidateFixture(
                oid=candidate,
                parents=[merge_base],
                paths=["shared.py"],
                disposition="MANUAL_MERGE",
                expected_conflict_paths=["shared.py"],
            )
        ],
    )
    plan = validate_plan_event(repository, data, evidence)
    assert start_rebase(repository, plan, evidence) != 0
    evidence.events.append(WorkflowEvent.CONFLICT)
    assert (
        run_git(repository, "show", ":2:shared.py", transcript=evidence.commands).stdout == "target_value = 'target'\n"
    )
    assert run_git(repository, "show", ":3:shared.py", transcript=evidence.commands).stdout == "value = 'feature'\n"
    (repository / "shared.py").write_text("target_value = 'target'\nvalue = 'feature'\n", encoding="utf-8")
    run_git(repository, "add", "shared.py", transcript=evidence.commands)
    assert run_git(repository, "ls-files", "--unmerged", transcript=evidence.commands).stdout == ""
    run_git(repository, "-c", "core.editor=true", "rebase", "--continue", transcript=evidence.commands)
    evidence.events.append(WorkflowEvent.REBASE_CONTINUED)

    assert_gate_precedes_rebase(evidence)
    assert (repository / "shared.py").read_text(encoding="utf-8") == "target_value = 'target'\nvalue = 'feature'\n"
    assert run_git(repository, "merge-base", "--is-ancestor", target_oid, "feature").returncode == 0
    finish_scenario(repository, evidence)


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

    evidence = begin_scenario(repository)
    plan = validate_plan_event(
        repository,
        scenario_plan_data(
            old_tip=candidate,
            target_oid=target_oid,
            merge_base_oid=merge_base,
            candidates=[CandidateFixture(oid=candidate, parents=[merge_base], paths=["old.py"], disposition="ADAPT")],
        ),
        evidence,
    )
    assert start_rebase(repository, plan, evidence) == 0

    assert_gate_precedes_rebase(evidence)
    assert not (repository / "old.py").exists()
    assert (repository / "new.py").read_text(encoding="utf-8") == "value = 2\n"
    finish_scenario(repository, evidence)


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
        candidates=[
            CandidateFixture(oid=first_parent, parents=[merge_base], paths=["feature.txt"]),
            CandidateFixture(oid=side_parent, parents=[merge_base], paths=["side.txt"]),
            CandidateFixture(
                oid=merge_candidate, parents=[first_parent, side_parent], paths=["feature.txt", "side.txt"]
            ),
        ],
    )
    data["merge_policy"] = "PRESERVE_TOPOLOGY"
    evidence = begin_scenario(repository)
    plan = validate_plan_event(repository, data, evidence)
    assert start_rebase(repository, plan, evidence, preserve_merges=True) == 0

    assert_gate_precedes_rebase(evidence)
    parent_records = run_git(repository, "rev-list", "--parents", f"{target_oid}..feature").stdout.splitlines()
    assert any(len(record.split()) > 2 for record in parent_records)
    finish_scenario(repository, evidence)
