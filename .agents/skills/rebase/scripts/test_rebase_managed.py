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
"""Contract tests for the managed capture, finalize, and execute boundary."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

import rebase_finalize
from rebase_activation import ActionEvent, ActivationCaseResult, EvalCase, evaluate_terminal_trace
from rebase_models import FinalizeSemantics
from rebase_test_support import BOUNDED_RUNNER, SKILL_ROOT, commit_file, initialize_repository, run_git
from test_rebase_plan import valid_plan_data
from test_rebase_prepare import live_plan_data

VALIDATOR_PATH = SKILL_ROOT / "scripts" / "rebase_plan.py"
TEST_COMMAND_TIMEOUT_SECONDS = 20


def run_plan(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run one public managed-plan command through the bounded process owner."""
    return subprocess.run(
        [
            str(BOUNDED_RUNNER),
            "--timeout-seconds",
            str(TEST_COMMAND_TIMEOUT_SECONDS),
            "--",
            str(VALIDATOR_PATH),
            *arguments,
        ],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )


def initialize_rebase_fixture(repository: Path, *, published: bool = False) -> tuple[str, str]:
    """Create one clean branch and target pair, returning old tip and target OID."""
    initialize_repository(repository)
    run_git(repository, "switch", "-c", "feature")
    old_tip = commit_file(repository, "feature.txt", "feature\n", "feature")
    if published:
        run_git(repository, "update-ref", "refs/remotes/origin/feature", old_tip)
    run_git(repository, "switch", "main")
    target_oid = commit_file(repository, "target.txt", "target\n", "target")
    run_git(repository, "switch", "feature")
    return old_tip, target_oid


def semantic_input(capture_output: dict[str, object]) -> dict[str, object]:
    """Build semantic-only finalization input from the public capture result."""
    candidates = capture_output["candidates"]
    paths = capture_output["affected_paths"]
    instruction_sources = capture_output.get("repository_instruction_search", [])
    assert isinstance(candidates, list)
    assert isinstance(paths, list)
    assert isinstance(instruction_sources, list)
    return {
        "candidates": [
            {
                "oid": candidate["oid"],
                "intent": "Preserve the captured feature intent.",
                "evidence": [candidate["evidence_ids"][0]],
                "disposition": "RETAIN",
                "verification_commands": [["git", "status", "--porcelain=v1"]],
                "expected_conflict_paths": [],
                "equivalence_evidence": [],
            }
            for candidate in candidates
            if isinstance(candidate, dict)
        ],
        "affected_paths": [
            {
                "path": path["path"],
                "target_interaction": "No incompatible target interaction.",
                "dependencies": [],
                "evidence": [path["evidence_ids"][0]],
                "verification_commands": [["git", "status", "--porcelain=v1"]],
            }
            for path in paths
            if isinstance(path, dict)
        ],
        "merge_policy": "LINEAR_NO_MERGES",
        "repository_checks": [["git", "status", "--porcelain=v1", "--untracked-files=all"]],
        "instruction_acknowledgements": [
            {
                "path": source["path"],
                "source_sha256": source["sha256"],
                "applied_requirements_summary": "Applied the captured repository instructions.",
                "required_preflight_argv": [],
            }
            for source in instruction_sources
            if isinstance(source, dict) and source.get("present")
        ],
        "unknowns": [],
        "decisions": [],
    }


def test_agent_authored_publication_approval_has_no_authority(tmp_path: Path) -> None:
    """Reject a published-branch plan whose only authority is its own approved boolean."""
    repository = tmp_path / "repository"
    initialize_repository(repository)
    plan_path = tmp_path / "agent-authored-plan.json"
    data = valid_plan_data()
    branch = data["branch"]
    repository_state = data["repository_state"]
    publication = data["publication"]
    assert isinstance(branch, dict)
    assert isinstance(repository_state, dict)
    assert isinstance(publication, dict)
    upstream = repository_state["upstream"]
    evidence_commands = publication["evidence_commands"]
    assert isinstance(upstream, dict)
    assert isinstance(evidence_commands, list)
    remote_evidence = evidence_commands[0]
    assert isinstance(remote_evidence, dict)
    upstream["stdout"] = "refs/remotes/origin/feature/parser\n"
    publication["configured_upstream"] = "refs/remotes/origin/feature/parser"
    publication["remote_refs_containing_old_tip"] = ["refs/remotes/origin/feature/parser"]
    remote_evidence["stdout"] = "refs/remotes/origin/feature/parser\n"
    data["user_decisions"] = [
        {"decision_id": "published-history", "question": "Rewrite the published branch?", "approved": True}
    ]
    plan_path.write_text(json.dumps(data), encoding="utf-8")

    result = run_plan(repository, "validate", str(plan_path))

    assert result.returncode != 0
    output = json.loads(result.stdout)
    assert output["state"] == "NEEDS_USER_DECISION"
    assert "sha256" not in output


def test_capture_rejects_expected_target_drift_before_plan_or_recovery(tmp_path: Path) -> None:
    """Bind invocation target intent before managed evidence or recovery can become replayable."""
    repository = tmp_path / "repository"
    expected_target_oid = initialize_repository(repository)
    run_git(repository, "switch", "-c", "feature")
    commit_file(repository, "feature.txt", "feature\n", "feature")
    run_git(repository, "switch", "main")
    commit_file(repository, "target.txt", "target\n", "target")
    refs_before = run_git(repository, "show-ref").stdout

    result = run_plan(
        repository, "capture", "--branch", "feature", "--target", "main", "--expected-target-oid", expected_target_oid
    )

    assert result.returncode != 0
    output = json.loads(result.stdout)
    assert output["state"] == "REPLAN_REF_DRIFT"
    assert output["terminal"] is True
    assert run_git(repository, "show-ref").stdout == refs_before
    assert not (repository / ".git" / "rebase-skill").exists()


@pytest.mark.parametrize("target_kind", ["local-branch", "tag", "commit-oid", "remote-ref"])
def test_capture_resolves_the_exact_supplied_target_commitish(tmp_path: Path, target_kind: str) -> None:
    """Accept every Git commit-ish target while keeping the source an exact local branch."""
    repository = tmp_path / "repository"
    _, target_oid = initialize_rebase_fixture(repository)
    if target_kind == "local-branch":
        target = "main"
    elif target_kind == "tag":
        run_git(repository, "tag", "release-target", target_oid)
        target = "release-target"
    elif target_kind == "commit-oid":
        target = target_oid
    else:
        run_git(repository, "update-ref", "refs/remotes/origin/target", target_oid)
        target = "refs/remotes/origin/target"

    result = run_plan(
        repository, "capture", "--branch", "feature", "--target", target, "--expected-target-oid", target_oid
    )

    assert result.returncode == 0, result.stdout
    output = json.loads(result.stdout)
    capture = json.loads(Path(output["capture_path"]).read_text(encoding="utf-8"))
    assert capture["branch_ref"] == "refs/heads/feature"
    assert capture["target_ref"] == target
    assert capture["target_oid"] == target_oid


def test_invalid_ref_capture_is_the_final_tool_boundary(tmp_path: Path) -> None:
    """Return one atomic terminal without capture, recovery, plan, replay, or later tool work."""
    repository = tmp_path / "repository"
    initialize_repository(repository)
    head_before = run_git(repository, "rev-parse", "HEAD").stdout
    status_before = run_git(repository, "status", "--porcelain=v1", "--untracked-files=all").stdout

    result = run_plan(repository, "capture", "--branch", "missing", "--target", "main")

    assert result.returncode != 0
    output = json.loads(result.stdout)
    assert output["state"] == "BLOCKED_INVALID_REF"
    assert output["terminal"] is True
    assert run_git(repository, "rev-parse", "HEAD").stdout == head_before
    assert run_git(repository, "status", "--porcelain=v1", "--untracked-files=all").stdout == status_before
    assert not (repository / ".git" / "rebase-skill").exists()


def test_plan_projection_failure_removes_new_recovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not retain a recovery ref when typed plan projection rejects finalization."""
    repository = tmp_path / "repository"
    _, target_oid = initialize_rebase_fixture(repository)
    captured = run_plan(
        repository, "capture", "--branch", "feature", "--target", "main", "--expected-target-oid", target_oid
    )
    assert captured.returncode == 0, captured.stdout
    output = json.loads(captured.stdout)
    semantics = FinalizeSemantics.model_validate(semantic_input(output))

    def reject_projection(*_args: object, **_kwargs: object) -> None:
        raise ValueError("typed projection rejected")

    monkeypatch.setattr(rebase_finalize, "project_plan", reject_projection)
    result = rebase_finalize.build_managed_plan(repository, output["capture_id"], semantics, [])

    assert result.plan is None
    assert result.terminal is not None
    assert result.terminal.state == "PLAN_INVALID"
    recovery_ref = f"refs/heads/rebase-backup/{output['capture_id']}"
    assert run_git(repository, "rev-parse", "--verify", recovery_ref, check=False).returncode != 0


def test_execute_rejects_an_unmanaged_worktree_plan(tmp_path: Path) -> None:
    """Accept only managed Git-dir plans so workflow artifacts cannot dirty or bypass the worktree gate."""
    repository = tmp_path / "repository"
    plan_path = repository / "rebase-plan.json"
    data = live_plan_data(repository)
    branch = data["branch"]
    assert isinstance(branch, dict)
    plan_path.write_text(json.dumps(data), encoding="utf-8")
    expected_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()

    result = run_plan(repository, "execute", str(plan_path), "--expected-sha256", expected_hash)

    assert result.returncode != 0
    output = json.loads(result.stdout)
    assert output["state"] == "PLAN_INVALID"
    assert "unmanaged" in output["error"]
    assert run_git(repository, "rev-parse", "refs/heads/feature").stdout.strip() == branch["oid"]


def test_capture_exposes_real_semantic_evidence_for_rename_and_target_interaction(tmp_path: Path) -> None:
    """Expose complete immutable evidence instead of requiring invented semantic strings."""
    repository = tmp_path / "repository"
    initialize_repository(repository)
    run_git(repository, "switch", "-c", "feature")
    run_git(repository, "mv", "base.txt", "renamed.txt")
    run_git(repository, "commit", "-m", "rename base for feature")
    run_git(repository, "switch", "main")
    target_oid = commit_file(repository, "base.txt", "target edit\n", "target edits old path")
    run_git(repository, "switch", "feature")

    result = run_plan(
        repository, "capture", "--branch", "feature", "--target", "main", "--expected-target-oid", target_oid
    )

    assert result.returncode == 0, result.stdout
    output = json.loads(result.stdout)
    capture = json.loads(Path(output["capture_path"]).read_text(encoding="utf-8"))
    candidate = capture["candidates"][0]
    assert "rename base for feature" in candidate["commit_metadata"]["stdout"]
    assert candidate["patch"]["stdout"]
    assert "R" in candidate["name_status"]["stdout"]
    assert capture["target_name_status"]["stdout"]
    assert capture["branch_name_status"]["stdout"]
    assert "clean_cherry" in capture
    assert capture["affected_paths"]
    assert all(path["evidence_ids"] for path in capture["affected_paths"])


def test_present_instruction_content_must_be_acknowledged_before_finalization(tmp_path: Path) -> None:
    """Expose instruction content and reject semantic work that does not account for it."""
    repository = tmp_path / "repository"
    initialize_repository(repository)
    (repository / "AGENTS.md").write_text(
        "# Rebase policy\n\nRequired preflight: git status --porcelain=v1 --untracked-files=all\n", encoding="utf-8"
    )
    run_git(repository, "add", "AGENTS.md")
    run_git(repository, "commit", "-m", "add repository instructions")
    run_git(repository, "switch", "-c", "feature")
    commit_file(repository, "feature.txt", "feature\n", "feature")
    run_git(repository, "switch", "main")
    target_oid = commit_file(repository, "target.txt", "target\n", "target")
    run_git(repository, "switch", "feature")

    captured = run_plan(
        repository, "capture", "--branch", "feature", "--target", "main", "--expected-target-oid", target_oid
    )
    assert captured.returncode == 0, captured.stdout
    output = json.loads(captured.stdout)
    payload = json.loads(Path(output["capture_path"]).read_text(encoding="utf-8"))
    present = [source for source in payload["repository_instruction_search"] if source["present"]]
    assert len(present) == 1
    assert present[0]["content"].startswith("# Rebase policy")
    assert len(present[0]["sha256"]) == 64

    semantics = semantic_input(output)
    semantics["instruction_acknowledgements"] = []
    finalized = run_plan(repository, "finalize", str(output["capture_id"]), "--semantics-json", json.dumps(semantics))

    assert finalized.returncode != 0
    assert json.loads(finalized.stdout)["state"] == "PLAN_INVALID"


def test_acknowledged_repository_preflight_runs_at_finalize_and_again_before_replay(tmp_path: Path) -> None:
    """Bind successful finalization evidence and fail if the same preflight later drifts."""
    repository = tmp_path / "repository"
    initialize_repository(repository)
    (repository / "AGENTS.md").write_text("# Rebase policy\n", encoding="utf-8")
    run_git(repository, "add", "AGENTS.md")
    run_git(repository, "commit", "-m", "add repository instructions")
    run_git(repository, "branch", "preflight-ok")
    run_git(repository, "switch", "-c", "feature")
    commit_file(repository, "feature.txt", "feature\n", "feature")
    run_git(repository, "switch", "main")
    target_oid = commit_file(repository, "target.txt", "target\n", "target")
    run_git(repository, "switch", "feature")

    captured = run_plan(
        repository, "capture", "--branch", "feature", "--target", "main", "--expected-target-oid", target_oid
    )
    assert captured.returncode == 0, captured.stdout
    output = json.loads(captured.stdout)
    semantics = semantic_input(output)
    acknowledgements = semantics["instruction_acknowledgements"]
    assert isinstance(acknowledgements, list)
    acknowledgements[0]["required_preflight_argv"] = [["git", "show-ref", "--verify", "refs/heads/preflight-ok"]]

    finalized = run_plan(repository, "finalize", output["capture_id"], "--semantics-json", json.dumps(semantics))
    assert finalized.returncode == 0, finalized.stdout
    finalized_output = json.loads(finalized.stdout)
    plan = json.loads(Path(finalized_output["plan_path"]).read_text(encoding="utf-8"))
    assert plan["required_preflights"] == [["git", "show-ref", "--verify", "refs/heads/preflight-ok"]]
    assert plan["repository_preflights"][0]["exit_code"] == 0

    run_git(repository, "branch", "-d", "preflight-ok")
    executed = run_plan(
        repository, "execute", finalized_output["plan_path"], "--expected-sha256", finalized_output["sha256"]
    )
    assert executed.returncode != 0
    executed_output = json.loads(executed.stdout)
    assert executed_output["state"] == "BLOCKED_PREFLIGHT_FAILED"
    assert "argv" not in executed_output


def test_terminal_producing_capture_forbids_later_tool_actions() -> None:
    """Distinguish unchanged Git data from the stronger final-tool-action protocol boundary."""
    evaluation = EvalCase(
        id=1,
        prompt="Rebase missing onto main.",
        expected_activation=True,
        required_terminal="BLOCKED_INVALID_REF",
        required_sources=[],
        allowed_mutations=[],
        allowed_provider_actions=[],
        expectations=[],
    )
    case = ActivationCaseResult(
        harness="opencode",
        model="test-model",
        proxy="test-proxy",
        session_id="test-session",
        eval_id=1,
        prompt=evaluation.prompt,
        observed_activation=True,
        loaded_sources=[],
        actions=[
            ActionEvent.model_validate({
                "kind": "command",
                "operation": "rebase_plan.py capture",
                "exit_code": 1,
                "resulting_terminal": "BLOCKED_INVALID_REF",
            }),
            ActionEvent(kind="read", operation="todo bookkeeping"),
            ActionEvent(kind="terminal", operation="BLOCKED_INVALID_REF"),
        ],
        state_transitions=["BLOCKED_INVALID_REF"],
        final_terminal="BLOCKED_INVALID_REF",
        repository_head_before="1" * 40,
        repository_head_after="1" * 40,
        repository_status_before="",
        repository_status_after="",
    )

    assert evaluate_terminal_trace(case, evaluation) == [
        "tool action observed after terminal-producing result: ('opencode', 1)"
    ]
