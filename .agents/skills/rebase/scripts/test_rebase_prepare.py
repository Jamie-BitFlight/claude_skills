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

from rebase_prepare import audit_single_use_trace
from rebase_states import WorkflowState
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


def live_plan_data(repository: Path, execution_mode: str = "CURRENT_BRANCH") -> dict[str, object]:
    """Build one schema-valid plan whose immutable bindings exist in a real repository."""
    merge_base = initialize_repository(repository)
    run_git(repository, "switch", "-c", "feature")
    candidate = commit_file(repository, "feature.txt", "feature\n", "feature change")
    run_git(repository, "switch", "main")
    commit_file(repository, "target.txt", "target\n", "target change")
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
                "paths": ["feature.txt"],
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
                "path": "feature.txt",
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


def run_prepare(repository: Path, plan_path: Path, expected_hash: str) -> subprocess.CompletedProcess[str]:
    """Run the live preparation gate through the process-group owner."""
    return subprocess.run(
        [
            str(BOUNDED_RUNNER),
            "--timeout-seconds",
            str(TEST_COMMAND_TIMEOUT_SECONDS),
            "--",
            str(VALIDATOR_PATH),
            "prepare",
            str(plan_path),
            "--expected-sha256",
            expected_hash,
        ],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )


def test_prepare_emits_only_the_canonical_current_branch_replay_argv(tmp_path: Path) -> None:
    """Bind a validated plan to one target-only replay command instead of free-form Git syntax."""
    repository = tmp_path / "repository"
    plan_path = tmp_path / "plan.json"
    data = live_plan_data(repository)
    plan_path.write_text(json.dumps(data), encoding="utf-8")
    expected_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()

    result = run_prepare(repository, plan_path, expected_hash)

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    target = data["target"]
    assert isinstance(target, dict)
    assert output["sha256"] == expected_hash
    assert output["argv"] == [
        "git",
        "rebase",
        "--reapply-cherry-picks",
        f"--empty={data['becomes_empty_option']}",
        target["oid"],
    ]
    assert "--onto" not in output["argv"]


def test_prepare_derives_the_authorized_positional_branch_shape(tmp_path: Path) -> None:
    """Bind authorized transfer to target plus planned branch without accepting a range."""
    repository = tmp_path / "repository"
    plan_path = tmp_path / "plan.json"
    data = live_plan_data(repository, execution_mode="AUTHORIZED_BRANCH_TRANSFER")
    plan_path.write_text(json.dumps(data), encoding="utf-8")
    expected_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()

    result = run_prepare(repository, plan_path, expected_hash)

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
        branch["ref"],
    ]
    assert "--onto" not in output["argv"]


def test_prepare_derives_merge_preservation_from_the_typed_policy(tmp_path: Path) -> None:
    """Add merge preservation only from the validated policy, never free-form argv."""
    repository = tmp_path / "repository"
    plan_path = tmp_path / "plan.json"
    data = live_plan_data(repository)
    data["merge_policy"] = "PRESERVE_TOPOLOGY"
    plan_path.write_text(json.dumps(data), encoding="utf-8")
    expected_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()

    result = run_prepare(repository, plan_path, expected_hash)

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["argv"].count("--rebase-merges") == 1
    assert "--onto" not in output["argv"]


@pytest.mark.parametrize(
    "mutation", ["dirty", "branch-drift", "target-drift", "active-metadata", "recovery-drift", "artifact-hash-drift"]
)
def test_prepare_emits_no_argv_when_live_or_artifact_state_drifted(tmp_path: Path, mutation: str) -> None:
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
    elif mutation == "branch-drift":
        run_git(repository, "update-ref", branch["ref"], target["oid"])
    elif mutation == "target-drift":
        run_git(repository, "update-ref", target["ref"], branch["oid"])
    elif mutation == "active-metadata":
        marker = Path(run_git(repository, "rev-parse", "--git-path", "rebase-merge").stdout.strip())
        (marker if marker.is_absolute() else repository / marker).mkdir(parents=True)
    elif mutation == "recovery-drift":
        recovery_ref = data["recovery_ref"]
        target_oid = target["oid"]
        assert isinstance(recovery_ref, str)
        assert isinstance(target_oid, str)
        run_git(repository, "update-ref", recovery_ref, target_oid)
    else:
        plan_path.write_text(plan_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    result = run_prepare(repository, plan_path, expected_hash)

    assert result.returncode != 0
    output = json.loads(result.stdout)
    assert "argv" not in output


@pytest.mark.parametrize(
    "commands",
    [
        [["git", "rebase", "--reapply-cherry-picks", "--empty=stop", "--keep-empty", "2" * 40]],
        [
            [
                "git",
                "rebase",
                "--rebase-merges",
                "--reapply-cherry-picks",
                "--empty=stop",
                "--keep-empty",
                "--onto",
                "refs/heads/main",
                "refs/heads/feature",
            ]
        ],
        [
            ["git", "rebase", "--reapply-cherry-picks", "--empty=stop", "2" * 40],
            ["git", "rebase", "--reapply-cherry-picks", "--empty=stop", "2" * 40],
        ],
        [
            ["git", "rebase", "--reapply-cherry-picks", "--empty=stop", "2" * 40],
            ["git", "reset", "--hard", "refs/heads/rebase-backup/prepare-test"],
        ],
        [
            ["git", "rebase", "--reapply-cherry-picks", "--empty=stop", "2" * 40],
            ["git", "update-ref", "refs/heads/feature", "refs/heads/rebase-backup/prepare-test"],
        ],
    ],
)
def test_single_use_trace_rejects_altered_replay_retry_and_ref_rewrite(commands: list[list[str]]) -> None:
    """Reject the observed --onto shape and every reset/retry under one validated hash."""
    prepared = ["git", "rebase", "--reapply-cherry-picks", "--empty=stop", "2" * 40]

    failures = audit_single_use_trace(prepared, commands, WorkflowState.REBASE_COMPLETE_VALIDATION_FAILED)

    assert failures


def test_single_use_trace_accepts_one_exact_replay_followed_by_nonmutating_oracles() -> None:
    """Allow one prepared replay followed only by verification evidence."""
    prepared = ["git", "rebase", "--reapply-cherry-picks", "--empty=stop", "2" * 40]
    commands = [
        prepared,
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        ["git", "range-diff", "4" * 40 + ".." + "1" * 40, "2" * 40 + ".." + "3" * 40],
    ]

    assert audit_single_use_trace(prepared, commands, WorkflowState.REBASE_COMPLETE_VERIFIED) == []
