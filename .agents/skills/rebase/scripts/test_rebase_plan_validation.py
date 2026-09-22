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
"""Unsafe-plan rejection and public validator cases."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from rebase_plan import RebasePlan
from test_rebase_plan import (
    BOUNDED_RUNNER,
    TEST_COMMAND_TIMEOUT_SECONDS,
    VALIDATOR_PATH,
    run_validator,
    valid_plan_data,
)


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown",
        "unapproved-decision",
        "missing-path-membership",
        "active-operation",
        "failed-preflight",
        "redundant-drop-without-equivalence",
        "omitted-inventory-candidate",
        "unverified-recovery",
        "unsupported-empty-option",
    ],
)
def test_incomplete_plan_cannot_reach_ready_to_rebase(mutation: str) -> None:
    """Reject every incomplete or unsafe plan before mutation."""
    data = valid_plan_data()
    if mutation == "unknown":
        data["unknowns"] = ["Whether target behavior supersedes the candidate."]
    elif mutation == "unapproved-decision":
        data["user_decisions"] = [
            {"decision_id": "flatten", "question": "Flatten merge topology?", "operation": "FLATTEN_TOPOLOGY"}
        ]
    elif mutation == "missing-path-membership":
        affected_paths = data["affected_paths"]
        assert isinstance(affected_paths, list)
        affected_paths.pop()
    elif mutation == "active-operation":
        data["active_operations"] = ["rebase-merge"]
    elif mutation == "failed-preflight":
        preflights = data["repository_preflights"]
        assert isinstance(preflights, list)
        preflight = preflights[0]
        assert isinstance(preflight, dict)
        preflight["exit_code"] = 1
    elif mutation == "redundant-drop-without-equivalence":
        candidates = data["candidates"]
        assert isinstance(candidates, list)
        candidate = candidates[0]
        assert isinstance(candidate, dict)
        candidate["disposition"] = "REDUNDANT_DROP"
        candidate["equivalence_evidence"] = []
    elif mutation == "omitted-inventory-candidate":
        replay_inventory = data["replay_inventory"]
        assert isinstance(replay_inventory, dict)
        replay_inventory["stdout"] = f"{'5' * 40} {'4' * 40}\n{replay_inventory['stdout']}"
    elif mutation == "unverified-recovery":
        recovery = data["recovery_verification"]
        assert isinstance(recovery, dict)
        recovery["stdout"] = f"{'9' * 40}\n"
    else:
        help_evidence = data["rebase_help"]
        assert isinstance(help_evidence, dict)
        help_evidence["stderr"] = "--reapply-cherry-picks --rebase-merges --empty (drop|keep|ask)\n"
    with pytest.raises(ValidationError):
        RebasePlan.model_validate(data)


def test_publication_receipt_cannot_authorize_a_redundant_drop() -> None:
    """Keep every external approval bound to its declared destructive operation."""
    data = valid_plan_data()
    candidates = data["candidates"]
    branch = data["branch"]
    target = data["target"]
    assert isinstance(candidates, list)
    assert isinstance(branch, dict)
    assert isinstance(target, dict)
    candidate = candidates[0]
    assert isinstance(candidate, dict)
    candidate["disposition"] = "REDUNDANT_DROP"
    candidate["equivalence_evidence"] = []
    candidate["drop_approval_decision_id"] = "shared-decision"
    data["capture_id"] = "a" * 32
    data["capture_sha256"] = "b" * 64
    data["approval_receipts"] = [
        {
            "schema_version": 1,
            "source": "harness-human-gate",
            "capture_id": data["capture_id"],
            "capture_sha256": data["capture_sha256"],
            "repository_root": data["execution_worktree"],
            "branch_ref": branch["ref"],
            "old_tip_oid": branch["oid"],
            "target_ref": target["ref"],
            "target_oid": target["oid"],
            "operation": "REBASE_PUBLISHED_HISTORY",
            "decision_id": "shared-decision",
            "approved": True,
        }
    ]
    with pytest.raises(ValidationError, match="redundant drop"):
        RebasePlan.model_validate(data)


@pytest.mark.parametrize(
    ("field_path", "replacement"),
    [
        (("repository_state", "branch_oid", "stdout"), f"{'9' * 40}\n"),
        (
            ("repository_state", "worktrees", "stdout"),
            f"worktree /work/foreign\nHEAD {'1' * 40}\nbranch refs/heads/feature/parser\n",
        ),
        (("repository_state", "merge_head", "present"), True),
        (("publication", "remote_refs_containing_old_tip"), ["refs/remotes/origin/unexpected"]),
    ],
)
def test_contradictory_universal_evidence_cannot_reach_ready(field_path: tuple[str, ...], replacement: object) -> None:
    """Reject universal evidence that contradicts another bound plan field."""
    data = valid_plan_data()
    target: dict[str, object] = data
    for field in field_path[:-1]:
        nested = target[field]
        assert isinstance(nested, dict)
        target = nested
    target[field_path[-1]] = replacement
    with pytest.raises(ValidationError):
        RebasePlan.model_validate(data)


def test_current_branch_must_match_planned_branch_in_current_branch_mode() -> None:
    """Reject current-branch evidence that names a different branch."""
    data = valid_plan_data()
    repository_state = data["repository_state"]
    assert isinstance(repository_state, dict)
    current_branch = repository_state["current_branch"]
    assert isinstance(current_branch, dict)
    current_branch["stdout"] = "different-branch\n"
    with pytest.raises(ValidationError):
        RebasePlan.model_validate(data)


def test_zero_branch_owners_require_authorized_transfer_mode() -> None:
    """Reject a current-branch plan whose branch has no owning worktree."""
    data = valid_plan_data()
    repository_state = data["repository_state"]
    assert isinstance(repository_state, dict)
    worktrees = repository_state["worktrees"]
    assert isinstance(worktrees, dict)
    worktrees["stdout"] = f"worktree /work/project\nHEAD {'1' * 40}\ndetached\n"
    with pytest.raises(ValidationError):
        RebasePlan.model_validate(data)


def test_path_marker_present_must_match_command_backed_existence() -> None:
    """Reject a marker presence value that contradicts its existence evidence."""
    data = valid_plan_data()
    repository_state = data["repository_state"]
    assert isinstance(repository_state, dict)
    rebase_merge = repository_state["rebase_merge"]
    assert isinstance(rebase_merge, dict)
    command = rebase_merge["command"]
    assert isinstance(command, dict)
    command["stdout"] = "/tmp/claude-skills-3784-rebase/.git\n"
    rebase_merge["present"] = False
    with pytest.raises(ValidationError):
        RebasePlan.model_validate(data)


def test_git_243_ask_spelling_satisfies_the_logical_stop_policy() -> None:
    """Accept Git 2.43's `ask` spelling when captured help advertises it."""
    data = valid_plan_data()
    data["becomes_empty_option"] = "ask"
    help_evidence = data["rebase_help"]
    assert isinstance(help_evidence, dict)
    help_evidence["stderr"] = "--reapply-cherry-picks --rebase-merges --empty (drop|keep|ask)\n"
    plan = RebasePlan.model_validate(data)
    assert plan.becomes_empty_option.value == "ask"


def test_validator_emits_compact_valid_result(tmp_path: Path) -> None:
    """Emit one compact JSON result for an agent consumer."""
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(valid_plan_data()), encoding="utf-8")
    result = run_validator(plan_path)
    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.count("\n") == 1
    output = json.loads(result.stdout)
    assert output["status"] == "VALID"
    assert output["state"] == "READY_TO_REBASE"
    assert output["plan_id"] == "feature-parser-onto-main"
    assert len(output["sha256"]) == 64


def test_bundled_validator_runs_from_unrelated_consuming_directory(tmp_path: Path) -> None:
    """Resolve the bundled executable by skill path instead of consuming-repository cwd."""
    result = subprocess.run(
        [
            str(BOUNDED_RUNNER),
            "--timeout-seconds",
            str(TEST_COMMAND_TIMEOUT_SECONDS),
            "--",
            str(VALIDATOR_PATH),
            "schema",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["title"] == "RebasePlan"


def test_validator_fails_closed_with_structured_errors(tmp_path: Path) -> None:
    """Return machine-readable validation errors without a ready state."""
    plan_data = valid_plan_data()
    plan_data["unknowns"] = ["Unresolved semantic overlap."]
    plan_path = tmp_path / "invalid-plan.json"
    plan_path.write_text(json.dumps(plan_data), encoding="utf-8")
    result = run_validator(plan_path)
    assert result.returncode == 1
    output = json.loads(result.stdout)
    assert output["status"] == "INVALID"
    assert output["state"] == "PLAN_INVALID"
    assert output["errors"]
