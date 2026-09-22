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

from rebase_plan import RebasePlan, StateKind, WorkflowState, workflow_state_names

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
VALIDATOR_PATH = SKILL_ROOT / "scripts" / "rebase_plan.py"
BOUNDED_RUNNER = REPOSITORY_ROOT / "scripts" / "run_bounded.py"
EXAMPLE_PLAN_PATH = SKILL_ROOT / "references" / "example-plan.json"


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
        "worktree_authorized": True,
        "status_porcelain": "",
        "active_operations": [],
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
        "publication": {
            "configured_upstream": "origin/feature/parser",
            "remote_refs_containing_old_tip": ["refs/remotes/origin/feature/parser"],
            "evidence_commands": [
                {
                    "source": "local-git",
                    "argv": ["git", "for-each-ref", "--contains", old_tip, "refs/remotes"],
                    "exit_code": 0,
                    "stdout": "refs/remotes/origin/feature/parser\n",
                    "stderr": "",
                }
            ],
        },
        "candidates": [
            {
                "oid": candidate_oid,
                "parents": ["4" * 40],
                "paths": ["parser.py", "tests/test_parser.py"],
                "intent": "Add parser validation and tests.",
                "evidence": ["candidate patch", "target rename diff"],
                "disposition": "ADAPT",
                "verification_commands": [["uv", "run", "pytest", "tests/test_parser.py", "-q"]],
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
                "verification_commands": [["uv", "run", "pytest", "tests/test_parser.py", "-q"]],
            },
            {
                "path": "tests/test_parser.py",
                "candidate_oids": [candidate_oid],
                "target_interaction": "Tests depend on the adapted parser path.",
                "dependencies": ["parser.py"],
                "evidence": ["candidate patch"],
                "verification_commands": [["uv", "run", "pytest", "tests/test_parser.py", "-q"]],
            },
        ],
        "merge_policy": "LINEAR_NO_MERGES",
        "clean_cherry_pick_policy": "SURFACE",
        "becomes_empty_policy": "STOP",
        "recovery_ref": "refs/heads/rebase-backup/feature-parser-onto-main",
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
            sys.executable,
            str(BOUNDED_RUNNER),
            "--timeout-seconds",
            "20",
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
    "mutation",
    [
        "unknown",
        "unapproved-decision",
        "missing-path-membership",
        "active-operation",
        "failed-preflight",
        "redundant-drop-without-equivalence",
    ],
)
def test_incomplete_plan_cannot_reach_ready_to_rebase(mutation: str) -> None:
    """Reject every incomplete or unsafe plan before mutation."""
    data = valid_plan_data()
    if mutation == "unknown":
        data["unknowns"] = ["Whether target behavior supersedes the candidate."]
    elif mutation == "unapproved-decision":
        data["user_decisions"] = [{"decision_id": "flatten", "question": "Flatten merge topology?", "approved": False}]
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
    else:
        candidates = data["candidates"]
        assert isinstance(candidates, list)
        candidate = candidates[0]
        assert isinstance(candidate, dict)
        candidate["disposition"] = "REDUNDANT_DROP"
        candidate["equivalence_evidence"] = []

    with pytest.raises(ValidationError):
        RebasePlan.model_validate(data)


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


def test_validator_fails_closed_with_structured_errors(tmp_path: Path) -> None:
    """Return machine-readable validation errors without a ready state."""
    plan_data = valid_plan_data()
    plan_data["unknowns"] = ["Unresolved semantic overlap."]
    plan_path = tmp_path / "invalid-plan.json"
    plan_path.write_text(json.dumps(plan_data), encoding="utf-8")

    result = run_validator(plan_path)

    assert result.returncode == 1
    assert result.stderr == ""
    output = json.loads(result.stdout)
    assert output["status"] == "INVALID"
    assert output["state"] == "PLAN_INVALID"
    assert output["errors"]


def test_workflow_state_source_includes_every_reviewed_state() -> None:
    """Keep one typed state vocabulary for prompts, tests, and CLI output."""
    names = workflow_state_names()

    assert WorkflowState.READY_TO_ANALYZE in names
    assert WorkflowState.BLOCKED_COMMAND_FAILED in names
    assert WorkflowState.PLAN_INVALID in names
    assert all(state.kind in {StateKind.TRANSITION, StateKind.TERMINAL} for state in names.values())
