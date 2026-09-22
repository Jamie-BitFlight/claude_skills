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
"""Focused tests for the validated-plan to replay-command boundary."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from rebase_models import PrepareRequest
from rebase_test_support import (
    BOUNDED_RUNNER,
    SKILL_ROOT,
    capture_repository_state,
    commit_file,
    initialize_repository,
    run_git,
    supported_empty_option,
)
from test_rebase_plan import valid_plan_data

VALIDATOR_PATH = SKILL_ROOT / "scripts" / "rebase_plan.py"
TEST_COMMAND_TIMEOUT_SECONDS = 20


def live_plan_data(
    repository: Path, execution_mode: str = "CURRENT_BRANCH", *, conflict: bool = False
) -> dict[str, object]:
    """Build one schema-valid plan whose immutable bindings exist in a real repository."""
    merge_base = initialize_repository(repository)
    if conflict:
        merge_base = commit_file(repository, "shared.txt", "base\n", "add shared file")
    run_git(repository, "switch", "-c", "feature")
    candidate_path = "shared.txt" if conflict else "feature.txt"
    candidate = commit_file(repository, candidate_path, "feature\n", "feature change")
    run_git(repository, "switch", "main")
    target_path = "shared.txt" if conflict else "target.txt"
    commit_file(repository, target_path, "target\n", "target change")
    target_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    if execution_mode == "CURRENT_BRANCH":
        run_git(repository, "switch", "feature")

    transcript: list[tuple[str, ...]] = []
    repository_state, publication = capture_repository_state(
        repository, branch_ref="refs/heads/feature", target_ref="refs/heads/main", transcript=transcript
    )
    inventory = run_git(
        repository,
        "rev-list",
        "--reverse",
        "--topo-order",
        "--parents",
        f"{target_oid}..{candidate}",
        transcript=transcript,
    )
    inventory_argv = list(transcript[-1])
    empty_option = supported_empty_option(repository, transcript)
    help_result = run_git(repository, "rebase", "-h", check=False)
    recovery_ref = "refs/heads/rebase-backup/prepare-test"
    run_git(repository, "branch", recovery_ref.removeprefix("refs/heads/"), candidate)
    recovery = run_git(repository, "rev-parse", "--verify", f"{recovery_ref}^{{commit}}")

    data = valid_plan_data()
    data.update({
        "plan_id": "prepare-test",
        "branch": {"ref": "refs/heads/feature", "oid": candidate},
        "target": {"ref": "refs/heads/main", "oid": target_oid},
        "merge_base_oid": merge_base,
        "execution_worktree": str(repository.resolve()),
        "execution_mode": execution_mode,
        "repository_state": repository_state,
        "repository_preflights": [],
        "required_preflights": [],
        "publication": publication,
        "replay_inventory": {
            "source": "local-git",
            "argv": inventory_argv,
            "exit_code": inventory.returncode,
            "stdout": inventory.stdout,
            "stderr": inventory.stderr,
        },
        "candidates": [
            {
                "oid": candidate,
                "parents": [merge_base],
                "paths": [candidate_path],
                "intent": "Preserve the feature change.",
                "evidence": ["candidate patch"],
                "disposition": "RETAIN",
                "verification_commands": [["git", "status", "--porcelain=v1"]],
                "expected_conflict_paths": [],
                "equivalence_evidence": [],
            }
        ],
        "affected_paths": [
            {
                "path": candidate_path,
                "candidate_oids": [candidate],
                "target_interaction": "No target overlap.",
                "dependencies": [],
                "evidence": ["candidate patch"],
                "verification_commands": [["git", "status", "--porcelain=v1"]],
            }
        ],
        "becomes_empty_option": empty_option,
        "rebase_help": {
            "source": "installed-git",
            "argv": ["git", "rebase", "-h"],
            "exit_code": help_result.returncode,
            "stdout": help_result.stdout,
            "stderr": help_result.stderr,
        },
        "recovery_ref": recovery_ref,
        "recovery_verification": {
            "source": "local-git",
            "argv": ["git", "rev-parse", "--verify", f"{recovery_ref}^{{commit}}"],
            "exit_code": recovery.returncode,
            "stdout": recovery.stdout,
            "stderr": recovery.stderr,
        },
        "repository_checks": [["git", "status", "--porcelain=v1", "--untracked-files=all"]],
    })
    return data


def run_execute(repository: Path, plan_path: Path, expected_hash: str) -> subprocess.CompletedProcess[str]:
    """Run the single-use replay executor through the process-group owner."""
    managed_root = Path(run_git(repository, "rev-parse", "--git-path", "rebase-skill").stdout.strip())
    if not managed_root.is_absolute():
        managed_root = repository / managed_root
    managed_plan = managed_root / "plans" / f"{plan_path.stem}.json"
    managed_plan.parent.mkdir(parents=True, exist_ok=True)
    managed_plan.write_bytes(plan_path.read_bytes())
    return subprocess.run(
        [
            str(BOUNDED_RUNNER),
            "--timeout-seconds",
            str(TEST_COMMAND_TIMEOUT_SECONDS),
            "--",
            str(VALIDATOR_PATH),
            "execute",
            str(managed_plan),
            "--expected-sha256",
            expected_hash,
        ],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )


def test_execute_uses_only_the_canonical_current_branch_replay_argv(tmp_path: Path) -> None:
    """Execute one target-only replay command without exposing a free-form boundary."""
    repository = tmp_path / "repository"
    plan_path = tmp_path / "plan.json"
    data = live_plan_data(repository)
    plan_path.write_text(json.dumps(data), encoding="utf-8")
    expected_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()

    result = run_execute(repository, plan_path, expected_hash)

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    target = data["target"]
    assert isinstance(target, dict)
    assert output["sha256"] == expected_hash
    assert output["status"] == "REPLAY_FINISHED"
    assert output["argv"] == [
        "git",
        "rebase",
        "--reapply-cherry-picks",
        f"--empty={data['becomes_empty_option']}",
        target["oid"],
    ]
    assert "--onto" not in output["argv"]


def test_execute_derives_the_authorized_positional_branch_shape(tmp_path: Path) -> None:
    """Execute authorized transfer with target plus short branch and no range input."""
    repository = tmp_path / "repository"
    plan_path = tmp_path / "plan.json"
    data = live_plan_data(repository, execution_mode="AUTHORIZED_BRANCH_TRANSFER")
    plan_path.write_text(json.dumps(data), encoding="utf-8")
    expected_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()

    result = run_execute(repository, plan_path, expected_hash)

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    target = data["target"]
    branch = data["branch"]
    assert isinstance(target, dict)
    assert isinstance(branch, dict)
    assert output["argv"] == [
        "git",
        "rebase",
        "--reapply-cherry-picks",
        f"--empty={data['becomes_empty_option']}",
        target["oid"],
        "feature",
    ]
    assert "--onto" not in output["argv"]


@pytest.mark.parametrize("execution_mode", ["CURRENT_BRANCH", "AUTHORIZED_BRANCH_TRANSFER"])
def test_execute_moves_the_planned_branch_and_preserves_oracles(tmp_path: Path, execution_mode: str) -> None:
    """Prove both modes move the branch and preserve all post-replay oracles."""
    repository = tmp_path / "repository"
    plan_path = tmp_path / "plan.json"
    data = live_plan_data(repository, execution_mode=execution_mode)
    plan_path.write_text(json.dumps(data), encoding="utf-8")
    expected_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    branch = data["branch"]
    target = data["target"]
    recovery_ref = data["recovery_ref"]
    assert isinstance(branch, dict)
    assert isinstance(target, dict)
    assert isinstance(recovery_ref, str)
    old_tip = branch["oid"]
    target_oid = target["oid"]
    assert isinstance(old_tip, str)
    assert isinstance(target_oid, str)

    replay = run_execute(repository, plan_path, expected_hash)

    assert replay.returncode == 0, replay.stderr
    assert json.loads(replay.stdout)["status"] == "REPLAY_FINISHED"
    assert run_git(repository, "rev-parse", "refs/heads/feature").stdout.strip() != old_tip
    assert run_git(repository, "merge-base", "--is-ancestor", target_oid, "refs/heads/feature").returncode == 0
    assert run_git(repository, "symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip() == "feature"
    assert run_git(repository, "status", "--porcelain=v1", "--untracked-files=all").stdout == ""
    assert run_git(repository, "rev-parse", recovery_ref).stdout.strip() == old_tip


def test_execute_consumes_one_plan_hash_before_replay_and_rejects_retry(tmp_path: Path) -> None:
    """Persist single use before replay and reject a second execution for the same hash."""
    repository = tmp_path / "repository"
    plan_path = tmp_path / "plan.json"
    data = live_plan_data(repository)
    plan_path.write_text(json.dumps(data), encoding="utf-8")
    expected_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()

    first = run_execute(repository, plan_path, expected_hash)
    second = run_execute(repository, plan_path, expected_hash)

    assert first.returncode == 0, first.stderr
    first_output = json.loads(first.stdout)
    assert first_output["status"] == "REPLAY_FINISHED"
    receipt_path = Path(first_output["receipt_path"])
    assert receipt_path.is_file()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["plan_sha256"] == expected_hash
    assert receipt["state"] == "CONSUMED"
    assert second.returncode != 0
    second_output = json.loads(second.stdout)
    assert second_output["state"] == "BLOCKED_GIT_STATE"
    assert "argv" not in second_output


def test_execute_retains_consumed_receipt_when_replay_stops(tmp_path: Path) -> None:
    """Keep single-use evidence across a real conflict stop and reject another initial replay."""
    repository = tmp_path / "repository"
    plan_path = tmp_path / "plan.json"
    data = live_plan_data(repository, conflict=True)
    plan_path.write_text(json.dumps(data), encoding="utf-8")
    expected_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()

    first = run_execute(repository, plan_path, expected_hash)
    first_output = json.loads(first.stdout)
    receipt_path = Path(first_output["receipt_path"])
    second = run_execute(repository, plan_path, expected_hash)

    assert first.returncode != 0
    assert first_output["status"] == "REPLAY_STOPPED"
    assert receipt_path.is_file()
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["state"] == "CONSUMED"
    assert second.returncode != 0
    assert "argv" not in json.loads(second.stdout)


def test_execute_derives_merge_preservation_from_the_typed_policy(tmp_path: Path) -> None:
    """Add merge preservation only from the validated policy, never free-form argv."""
    repository = tmp_path / "repository"
    plan_path = tmp_path / "plan.json"
    data = live_plan_data(repository)
    data["merge_policy"] = "PRESERVE_TOPOLOGY"
    plan_path.write_text(json.dumps(data), encoding="utf-8")
    expected_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()

    result = run_execute(repository, plan_path, expected_hash)

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["argv"].count("--rebase-merges") == 1
    assert "--onto" not in output["argv"]


@pytest.mark.parametrize(
    ("mutation", "expected_state", "expected_status"),
    [
        ("dirty", "BLOCKED_GIT_STATE", "BLOCKED"),
        ("branch-missing", "REPLAN_REF_DRIFT", "BLOCKED"),
        ("branch-drift", "REPLAN_REF_DRIFT", "BLOCKED"),
        ("target-missing", "REPLAN_REF_DRIFT", "BLOCKED"),
        ("target-drift", "REPLAN_REF_DRIFT", "BLOCKED"),
        ("active-metadata", "BLOCKED_GIT_STATE", "BLOCKED"),
        ("recovery-missing", "BLOCKED_GIT_STATE", "BLOCKED"),
        ("recovery-drift", "BLOCKED_GIT_STATE", "BLOCKED"),
        ("artifact-hash-drift", "PLAN_INVALID", "INVALID"),
    ],
)
def test_execute_emits_no_argv_when_live_or_artifact_state_drifted(
    tmp_path: Path, mutation: str, expected_state: str, expected_status: str
) -> None:
    """Fail closed when any single-use live binding differs from the validated plan."""
    repository = tmp_path / "repository"
    plan_path = tmp_path / "plan.json"
    data = live_plan_data(repository)
    plan_path.write_text(json.dumps(data), encoding="utf-8")
    expected_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    branch = data["branch"]
    target = data["target"]
    assert isinstance(branch, dict)
    assert isinstance(target, dict)

    if mutation == "dirty":
        (repository / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    elif mutation == "branch-missing":
        run_git(repository, "update-ref", "-d", branch["ref"])
    elif mutation == "branch-drift":
        run_git(repository, "update-ref", branch["ref"], target["oid"])
    elif mutation == "target-missing":
        run_git(repository, "update-ref", "-d", target["ref"])
    elif mutation == "target-drift":
        run_git(repository, "update-ref", target["ref"], branch["oid"])
    elif mutation == "active-metadata":
        marker = Path(run_git(repository, "rev-parse", "--git-path", "rebase-merge").stdout.strip())
        (marker if marker.is_absolute() else repository / marker).mkdir(parents=True)
    elif mutation in {"recovery-missing", "recovery-drift"}:
        recovery_ref = data["recovery_ref"]
        target_oid = target["oid"]
        assert isinstance(recovery_ref, str)
        assert isinstance(target_oid, str)
        if mutation == "recovery-missing":
            run_git(repository, "update-ref", "-d", recovery_ref)
        else:
            run_git(repository, "update-ref", recovery_ref, target_oid)
    else:
        plan_path.write_text(plan_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    refs_before = run_git(repository, "show-ref").stdout
    result = run_execute(repository, plan_path, expected_hash)

    assert result.returncode != 0
    output = json.loads(result.stdout)
    assert output["state"] == expected_state
    assert output["status"] == expected_status
    assert "argv" not in output
    assert run_git(repository, "show-ref").stdout == refs_before


@pytest.mark.parametrize(
    ("field", "value"),
    [("execution_mode", "NOT_A_MODE"), ("merge_policy", "NOT_A_POLICY"), ("becomes_empty_option", "drop")],
)
def test_prepare_request_rejects_invalid_execution_enums(field: str, value: str) -> None:
    """Reject primitive-string construction outside the canonical execution vocabulary."""
    values = {
        "branch_ref": "refs/heads/feature",
        "branch_oid": "1" * 40,
        "target_ref": "refs/heads/main",
        "target_oid": "2" * 40,
        "execution_worktree": "/work/project",
        "execution_mode": "CURRENT_BRANCH",
        "merge_policy": "LINEAR_NO_MERGES",
        "becomes_empty_option": "stop",
        "recovery_ref": "refs/heads/rebase-backup/prepare-test",
    }
    values[field] = value

    with pytest.raises(ValidationError):
        PrepareRequest.model_validate(values)


def test_executor_rejects_the_observed_wrong_argv_and_retry_after_reset(tmp_path: Path) -> None:
    """Reject free-form --onto input and a second replay after reset under one consumed hash."""
    repository = tmp_path / "repository"
    plan_path = tmp_path / "plan.json"
    data = live_plan_data(repository)
    plan_path.write_text(json.dumps(data), encoding="utf-8")
    expected_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    branch = data["branch"]
    recovery_ref = data["recovery_ref"]
    assert isinstance(branch, dict)
    assert isinstance(recovery_ref, str)
    old_tip = branch["oid"]
    assert isinstance(old_tip, str)
    wrong_argv = json.dumps([
        "git",
        "rebase",
        "--rebase-merges",
        "--reapply-cherry-picks",
        "--empty=stop",
        "--keep-empty",
        "--onto",
        "refs/heads/main",
        "refs/heads/feature",
    ])

    rejected = subprocess.run(
        [str(VALIDATOR_PATH), "execute", str(plan_path), "--expected-sha256", expected_hash, "--argv-json", wrong_argv],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    first = run_execute(repository, plan_path, expected_hash)
    run_git(repository, "reset", "--hard", recovery_ref)
    second = run_execute(repository, plan_path, expected_hash)

    assert rejected.returncode != 0
    assert run_git(repository, "rev-parse", recovery_ref).stdout.strip() == old_tip
    assert first.returncode == 0
    assert second.returncode != 0
    second_output = json.loads(second.stdout)
    assert second_output["state"] == "BLOCKED_GIT_STATE"
    assert "argv" not in second_output
