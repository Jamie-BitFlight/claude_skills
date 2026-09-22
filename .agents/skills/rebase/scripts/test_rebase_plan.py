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
"""Contract tests for the machine-validatable rebase plan gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from rebase_plan import RebasePlan
from rebase_states import WorkflowState

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
VALIDATOR_PATH = SKILL_ROOT / "scripts" / "rebase_plan.py"
BOUNDED_RUNNER = REPOSITORY_ROOT / "scripts" / "run_bounded.py"
EXAMPLE_PLAN_PATH = SKILL_ROOT / "references" / "example-plan.json"

# Validator fixtures complete in milliseconds. Twenty seconds permits slow CI filesystems while
# still proving that a hung dependency resolver or descendant is terminated by the bounded runner.
TEST_COMMAND_TIMEOUT_SECONDS = 20


def valid_repository_state_data(
    *, old_tip: str, target_oid: str, merge_base_oid: str, configured_upstream: str | None
) -> dict[str, object]:
    """Return complete universal preflight evidence bound to a valid fixture."""

    def command(argv: list[str], stdout: str = "", exit_code: int = 0) -> dict[str, object]:
        return {"source": "local-git", "argv": argv, "exit_code": exit_code, "stdout": stdout, "stderr": ""}

    def path_marker(name: str) -> dict[str, object]:
        resolved_path = f"/work/project/.git/{name}"
        return {
            "command": command(["git", "rev-parse", "--git-path", name], f".git/{name}\n"),
            "existence": command(
                ["uv", "run", "--script", "/skills/rebase/scripts/rebase_plan.py", "path-state", resolved_path],
                json.dumps({"response_kind": "path-state", "path": resolved_path, "present": False}),
            ),
            "present": False,
        }

    return {
        "repository_root": command(["git", "rev-parse", "--show-toplevel"], "/work/project\n"),
        "branch_ref": command(
            ["git", "show-ref", "--verify", "refs/heads/feature/parser"], f"{old_tip} refs/heads/feature/parser\n"
        ),
        "branch_oid": command(["git", "rev-parse", "--verify", "refs/heads/feature/parser^{commit}"], f"{old_tip}\n"),
        "target_oid": command(["git", "rev-parse", "--verify", "refs/heads/main^{commit}"], f"{target_oid}\n"),
        "merge_base": command(
            ["git", "merge-base", "refs/heads/feature/parser", "refs/heads/main"], f"{merge_base_oid}\n"
        ),
        "worktrees": command(
            ["git", "worktree", "list", "--porcelain"],
            "worktree /work/project\nHEAD " + old_tip + "\nbranch refs/heads/feature/parser\n",
        ),
        "status": command(["git", "status", "--porcelain=v1", "--untracked-files=all"]),
        "current_branch": command(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], "feature/parser\n"),
        "rebase_merge": path_marker("rebase-merge"),
        "rebase_apply": path_marker("rebase-apply"),
        "merge_head": {
            "command": command(["git", "rev-parse", "--verify", "--quiet", "MERGE_HEAD"], exit_code=1),
            "present": False,
        },
        "cherry_pick_head": {
            "command": command(["git", "rev-parse", "--verify", "--quiet", "CHERRY_PICK_HEAD"], exit_code=1),
            "present": False,
        },
        "upstream": command(
            ["git", "for-each-ref", "--format=%(upstream)", "refs/heads/feature/parser"],
            f"{configured_upstream or ''}\n",
        ),
    }


def valid_instruction_data() -> dict[str, object]:
    """Return bound instruction and preflight fixture data.

    Returns:
        Instruction-related plan fields.
    """
    return {
        "repository_instruction_search": [
            {
                "path": "AGENTS.md",
                "present": True,
                "content": "# Agent rules\n",
                "sha256": "d2e2a32d37b83ebbcdbbfea0d86642516dc5010642ec2a404c626c1c0bf1e068",
            },
            {"path": ".claude/CLAUDE.md", "present": False},
        ],
        "repository_instruction_sources": ["AGENTS.md"],
        "repository_preflights": [
            {
                "source": "AGENTS.md",
                "argv": ["uv", "run", "scripts/audit_branch_transfer.py"],
                "exit_code": 0,
                "stdout": '{"ok":true}',
                "stderr": "",
            }
        ],
        "required_preflights": [["uv", "run", "scripts/audit_branch_transfer.py"]],
    }


def valid_candidate_data(candidate_oid: str) -> dict[str, object]:
    """Return candidate and affected-path fixture data.

    Returns:
        Candidate-related plan fields.
    """
    verification = [["uv", "run", "pytest", "tests/test_parser.py", "-q"]]
    return {
        "candidates": [
            {
                "oid": candidate_oid,
                "parents": ["4" * 40],
                "paths": ["parser.py", "tests/test_parser.py"],
                "intent": "Add parser validation and tests.",
                "evidence": ["candidate patch", "target rename diff"],
                "disposition": "ADAPT",
                "verification_commands": verification,
                "expected_conflict_paths": [],
                "equivalence_evidence": [],
            }
        ],
        "affected_paths": [
            {
                "path": "parser.py",
                "candidate_oids": [candidate_oid],
                "target_interaction": "Target renamed the API used by this path.",
                "dependencies": ["tests/test_parser.py"],
                "evidence": ["candidate patch", "target diff"],
                "verification_commands": verification,
            },
            {
                "path": "tests/test_parser.py",
                "candidate_oids": [candidate_oid],
                "target_interaction": "Tests depend on the adapted parser path.",
                "dependencies": ["parser.py"],
                "evidence": ["candidate patch"],
                "verification_commands": verification,
            },
        ],
    }


def valid_replay_data(old_tip: str, target_oid: str, candidate_oid: str) -> dict[str, object]:
    """Return replay, capability, and recovery fixture data.

    Returns:
        Replay-related plan fields.
    """
    return {
        "replay_inventory": {
            "source": "local-git",
            "argv": ["git", "rev-list", "--reverse", "--topo-order", "--parents", f"{target_oid}..{old_tip}"],
            "exit_code": 0,
            "stdout": f"{candidate_oid} {'4' * 40}\n",
            "stderr": "",
        },
        "becomes_empty_option": "stop",
        "rebase_help": {
            "source": "installed-git",
            "argv": ["git", "rebase", "-h"],
            "exit_code": 129,
            "stdout": "",
            "stderr": "--reapply-cherry-picks --rebase-merges --empty (drop|keep|stop)\n",
        },
        "recovery_ref": "refs/heads/rebase-backup/feature-parser-onto-main",
        "recovery_verification": {
            "source": "local-git",
            "argv": ["git", "rev-parse", "--verify", "refs/heads/rebase-backup/feature-parser-onto-main^{commit}"],
            "exit_code": 0,
            "stdout": f"{old_tip}\n",
            "stderr": "",
        },
    }


def valid_plan_data() -> dict[str, object]:
    """Return one complete plan satisfying every pre-action invariant.

    Returns:
        JSON-compatible plan mapping.
    """
    old_tip = "1" * 40
    target_oid = "2" * 40
    candidate_oid = "3" * 40
    return {
        "schema_version": 1,
        "plan_id": "feature-parser-onto-main",
        "branch": {"ref": "refs/heads/feature/parser", "oid": old_tip},
        "target": {"ref": "refs/heads/main", "oid": target_oid},
        "merge_base_oid": "4" * 40,
        "execution_worktree": "/work/project",
        "execution_mode": "CURRENT_BRANCH",
        "worktree_authorized": True,
        "status_porcelain": "",
        "active_operations": [],
        "repository_state": valid_repository_state_data(
            old_tip=old_tip, target_oid=target_oid, merge_base_oid="4" * 40, configured_upstream=None
        ),
        **valid_instruction_data(),
        "publication": {
            "configured_upstream": None,
            "remote_refs_containing_old_tip": [],
            "evidence_commands": [
                {
                    "source": "local-git",
                    "argv": ["git", "for-each-ref", "--format=%(refname)", "--contains", old_tip, "refs/remotes"],
                    "exit_code": 0,
                    "stdout": "",
                    "stderr": "",
                }
            ],
        },
        **valid_replay_data(old_tip, target_oid, candidate_oid),
        **valid_candidate_data(candidate_oid),
        "merge_policy": "LINEAR_NO_MERGES",
        "clean_cherry_pick_policy": "SURFACE",
        "becomes_empty_policy": "STOP",
        "repository_checks": [["uv", "run", "pytest", "tests/test_parser.py", "-q"]],
        "unknowns": [],
        "user_decisions": [],
    }


def run_validator(plan_path: Path) -> subprocess.CompletedProcess[str]:
    """Run the validator through the repository's process-group owner.

    Args:
        plan_path: JSON plan path.

    Returns:
        Completed bounded subprocess.
    """
    return subprocess.run(
        [
            str(BOUNDED_RUNNER),
            "--timeout-seconds",
            str(TEST_COMMAND_TIMEOUT_SECONDS),
            "--",
            sys.executable,
            str(VALIDATOR_PATH),
            "validate",
            str(plan_path),
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_complete_plan_reaches_ready_to_rebase() -> None:
    """Accept one exact-cover plan with observable preflight evidence."""
    plan = RebasePlan.model_validate(valid_plan_data())

    assert plan.plan_id == "feature-parser-onto-main"
    assert plan.ready_state is WorkflowState.READY_TO_REBASE


def test_bundled_example_is_a_valid_ready_to_rebase_plan() -> None:
    """Keep the disclosed example synchronized with the typed validator."""
    plan = RebasePlan.model_validate_json(EXAMPLE_PLAN_PATH.read_bytes())

    assert plan.ready_state is WorkflowState.READY_TO_REBASE


@pytest.mark.parametrize(
    "missing_field",
    [
        "repository_root",
        "branch_ref",
        "branch_oid",
        "target_oid",
        "merge_base",
        "worktrees",
        "status",
        "current_branch",
        "rebase_merge",
        "rebase_apply",
        "merge_head",
        "cherry_pick_head",
        "upstream",
    ],
)
def test_universal_preflight_evidence_is_required_without_repository_specific_checks(missing_field: str) -> None:
    """Reject a plan missing any universal Step 1 observation."""
    data = valid_plan_data()
    data["repository_preflights"] = []
    repository_state = data["repository_state"]
    assert isinstance(repository_state, dict)
    repository_state.pop(missing_field)

    with pytest.raises(ValidationError):
        RebasePlan.model_validate(data)


def test_start_empty_commit_passes_as_preserve_empty_without_path_impacts() -> None:
    """Represent an intentionally empty commit without inventing an affected path."""
    data = valid_plan_data()
    candidates = data["candidates"]
    assert isinstance(candidates, list)
    candidate = candidates[0]
    assert isinstance(candidate, dict)
    candidate["paths"] = []
    candidate["disposition"] = "PRESERVE_EMPTY"
    data["affected_paths"] = []

    plan = RebasePlan.model_validate(data)

    assert plan.candidates[0].paths == []
    assert plan.candidates[0].disposition.value == "PRESERVE_EMPTY"
    assert plan.affected_paths == []


def test_zero_path_candidate_without_preserve_empty_is_rejected() -> None:
    """Keep zero-path candidates exclusive to the intentional-empty disposition."""
    data = valid_plan_data()
    candidates = data["candidates"]
    assert isinstance(candidates, list)
    candidate = candidates[0]
    assert isinstance(candidate, dict)
    candidate["paths"] = []
    data["affected_paths"] = []

    with pytest.raises(ValidationError, match="zero-path candidates require PRESERVE_EMPTY"):
        RebasePlan.model_validate(data)
