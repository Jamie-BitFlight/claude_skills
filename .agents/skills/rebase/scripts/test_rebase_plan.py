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
from pathlib import Path

import pytest
from pydantic import ValidationError

from rebase_plan import RebasePlan
from rebase_states import StateKind, WorkflowState, workflow_state_definitions

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
                json.dumps({"path": resolved_path, "present": False}),
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
            old_tip=old_tip,
            target_oid=target_oid,
            merge_base_oid="4" * 40,
            configured_upstream="refs/remotes/origin/feature/parser",
        ),
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
            "configured_upstream": "refs/remotes/origin/feature/parser",
            "remote_refs_containing_old_tip": ["refs/remotes/origin/feature/parser"],
            "evidence_commands": [
                {
                    "source": "local-git",
                    "argv": ["git", "for-each-ref", "--format=%(refname)", "--contains", old_tip, "refs/remotes"],
                    "exit_code": 0,
                    "stdout": "refs/remotes/origin/feature/parser\n",
                    "stderr": "",
                }
            ],
        },
        "replay_inventory": {
            "source": "local-git",
            "argv": ["git", "rev-list", "--reverse", "--topo-order", "--parents", f"{target_oid}..{old_tip}"],
            "exit_code": 0,
            "stdout": f"{candidate_oid} {'4' * 40}\n",
            "stderr": "",
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


@pytest.mark.parametrize(
    ("field_path", "replacement"),
    [
        (("repository_state", "branch_oid", "stdout"), f"{'9' * 40}\n"),
        (
            ("repository_state", "worktrees", "stdout"),
            f"worktree /work/foreign\nHEAD {'1' * 40}\nbranch refs/heads/feature/parser\n",
        ),
        (("repository_state", "merge_head", "present"), True),
        (("publication", "remote_refs_containing_old_tip"), []),
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
    schema = json.loads(result.stdout)
    assert schema["title"] == "RebasePlan"


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
    definitions = workflow_state_definitions()

    assert WorkflowState.READY_TO_ANALYZE in definitions
    assert WorkflowState.BLOCKED_COMMAND_FAILED in definitions
    assert WorkflowState.PLAN_INVALID in definitions
    assert all(state.kind in {StateKind.TRANSITION, StateKind.TERMINAL} for state in definitions.values())
