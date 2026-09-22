#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "marko>=2.2",
#   "pydantic>=2.0",
#   "pytest",
# ]
# [tool.ty.environment]
# root = ["."]
# ///
"""Behavioral package tests for the rebase skill."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator
from pathlib import Path

import marko
from marko.block import FencedCode
from marko.inline import Link
from pydantic import BaseModel

from rebase_plan import Disposition, MergePolicy, workflow_state_definitions

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
SKILL_PATH = SKILL_ROOT / "SKILL.md"
REFERENCE_PATH = SKILL_ROOT / "references" / "rebase-edge-cases.md"
EVALS_PATH = SKILL_ROOT / "evals" / "evals.json"
ACTIVATION_RESULTS_PATH = SKILL_ROOT / "evals" / "activation-results.json"
BOUNDED_RUNNER = REPOSITORY_ROOT / "scripts" / "run_bounded.py"

# Local Git fixture commands complete in milliseconds. Twenty seconds permits slow CI filesystems
# while still proving that a hung hook or descendant process is terminated by the bounded runner.
TEST_COMMAND_TIMEOUT_SECONDS = 20


class EvalCase(BaseModel):
    """One activation evaluation."""

    id: int
    prompt: str
    expected_output: str
    files: list[str]
    expectations: list[str]


class EvalPackage(BaseModel):
    """Validated activation-evaluation package."""

    skill_name: str
    evals: list[EvalCase]


class ActivationCaseResult(BaseModel):
    """One observed harness activation decision."""

    harness: str
    model: str
    proxy: str
    session_id: str
    eval_id: int
    prompt: str
    expected_activation: bool
    observed_activation: bool
    loaded_skill_path: str | None
    read_references: list[str]
    filesystem_action_events: list[str]
    provider_action_events: list[str]
    state_transitions: list[str]
    final_terminal: str
    status: str


class ActivationResults(BaseModel):
    """Persisted activation evidence for the evaluation package."""

    schema_version: int
    skill_name: str
    repository_head_before: str
    repository_head_after: str
    repository_status_before: str
    repository_status_after: str
    cases: list[ActivationCaseResult]


def walk(element: object) -> Iterator[object]:
    """Yield every Marko node below an element.

    Args:
        element: Marko AST node or scalar child.

    Yields:
        The supplied node followed by its descendants.
    """
    yield element
    children = getattr(element, "children", None)
    if isinstance(children, list):
        for child in children:
            yield from walk(child)


def node_text(element: object) -> str:
    """Return the plain text carried by one Marko AST subtree.

    Args:
        element: Marko AST node or scalar child.

    Returns:
        Concatenated text from the subtree.
    """
    if isinstance(element, str):
        return element
    children = getattr(element, "children", None)
    if isinstance(children, str):
        return children
    if isinstance(children, list):
        return "".join(node_text(child) for child in children)
    return ""


def parse_markdown(path: Path) -> object:
    """Parse a Markdown file into a Marko AST.

    Args:
        path: Markdown file to parse.

    Returns:
        Parsed Marko document.
    """
    return marko.parse(path.read_text(encoding="utf-8"))


def run_git(
    repository: Path, *arguments: str, check: bool = True, transcript: list[tuple[str, ...]] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run one bounded-by-pytest Git command in a temporary repository.

    Args:
        repository: Temporary Git repository.
        *arguments: Arguments after the `git` executable.
        check: Raise when Git exits nonzero.
        transcript: Optional command transcript to append to.

    Returns:
        Completed Git process.
    """
    command = ("git", *arguments)
    if transcript is not None:
        transcript.append(command)
    result = subprocess.run(
        [str(BOUNDED_RUNNER), "--timeout-seconds", str(TEST_COMMAND_TIMEOUT_SECONDS), "--", *command],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    if check:
        result.check_returncode()
    return result


def supported_empty_option(repository: Path, transcript: list[tuple[str, ...]] | None = None) -> str:
    """Return the installed Git spelling that stops for a commit that becomes empty."""
    result = run_git(repository, "rebase", "-h", check=False, transcript=transcript)
    empty_line = next(line for line in f"{result.stdout}\n{result.stderr}".splitlines() if "--empty" in line)
    if "stop" in empty_line:
        return "stop"
    if "ask" in empty_line:
        return "ask"
    raise AssertionError("installed Git help has no stop-on-empty spelling")


def initialize_repository(repository: Path) -> str:
    """Create a deterministic temporary repository with one base commit.

    Args:
        repository: Directory to initialize.

    Returns:
        Full OID of the base commit.
    """
    repository.mkdir(parents=True)
    run_git(repository, "init", "--initial-branch=main")
    run_git(repository, "config", "user.name", "Rebase Skill Test")
    run_git(repository, "config", "user.email", "rebase-skill@example.invalid")
    run_git(repository, "config", "commit.gpgsign", "false")
    (repository / "base.txt").write_text("base\n", encoding="utf-8")
    run_git(repository, "add", "base.txt")
    run_git(repository, "commit", "-m", "base")
    return run_git(repository, "rev-parse", "HEAD").stdout.strip()


def commit_file(repository: Path, relative_path: str, content: str, message: str) -> str:
    """Write and commit one file in a temporary repository.

    Args:
        repository: Temporary Git repository.
        relative_path: Repository-relative path to write.
        content: Complete file content.
        message: Commit message.

    Returns:
        Full OID of the created commit.
    """
    path = repository / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    run_git(repository, "add", relative_path)
    run_git(repository, "commit", "-m", message)
    return run_git(repository, "rev-parse", "HEAD").stdout.strip()


def test_canonical_package_has_relative_claude_alias() -> None:
    """Keep one canonical skill body and a tracked relative Claude alias."""
    claude_alias = REPOSITORY_ROOT / ".claude" / "skills" / "rebase"

    assert SKILL_PATH.is_file()
    assert not SKILL_ROOT.is_symlink()
    assert claude_alias.is_symlink()
    assert claude_alias.readlink() == Path("../../.agents/skills/rebase")
    assert (claude_alias / "SKILL.md").read_bytes() == SKILL_PATH.read_bytes()

    tracked = run_git(REPOSITORY_ROOT, "ls-files", "-s", ".claude/skills/rebase")
    assert tracked.stdout.startswith("120000 ")


def test_every_bundled_markdown_link_resolves() -> None:
    """Keep progressive-disclosure resources reachable from the canonical skill."""
    document = parse_markdown(SKILL_PATH)
    local_links = [node.dest for node in walk(document) if isinstance(node, Link) and not node.dest.startswith("http")]

    assert local_links
    assert all((SKILL_ROOT / destination).is_file() for destination in local_links)


def test_terminal_state_contract_covers_every_safety_branch() -> None:
    """Reject prompt state tokens absent from the typed canonical vocabulary."""
    package_text = SKILL_PATH.read_text(encoding="utf-8") + REFERENCE_PATH.read_text(encoding="utf-8")
    presented_states = set(re.findall(r"`([A-Z][A-Z_]+)`", package_text))
    canonical_states = {state.value for state in workflow_state_definitions()}
    non_state_contract_tokens = {
        *(disposition.value for disposition in Disposition),
        *(policy.value for policy in MergePolicy),
        "CHERRY_PICK_HEAD",
        "MERGE_HEAD",
        "REBASE_HEAD",
        "REBASE_SKILL_DIR",
        "STOP",
        "SURFACE",
        "VALID",
    }

    assert presented_states
    assert presented_states <= canonical_states | non_state_contract_tokens


def test_executable_instructions_are_forge_neutral() -> None:
    """Exclude provider, publication, and merge commands from runtime instructions."""
    document = parse_markdown(SKILL_PATH)
    reference = parse_markdown(REFERENCE_PATH)
    command_text = "\n".join(
        node_text(node) for tree in (document, reference) for node in walk(tree) if isinstance(node, FencedCode)
    )

    assert not re.search(r"(?m)^\s*(?:gh|glab)\s", command_text)
    assert not re.search(r"(?m)^\s*git\s+(?:push\b|merge(?:\s|$))", command_text)
    assert "scripts/rebase_plan.py" in command_text
    assert not re.search(r"uv run --script scripts/rebase_plan\.py", command_text)


def test_activation_evals_cover_explicit_rebase_and_nearby_negative_routes() -> None:
    """Cover run, continue, abort, merge-update, forge-setting, and MR-merge routes."""
    package = EvalPackage.model_validate_json(EVALS_PATH.read_text(encoding="utf-8"))

    assert package.skill_name == "rebase"
    assert len(package.evals) == 6
    assert len({case.id for case in package.evals}) == len(package.evals)
    assert all(case.expectations for case in package.evals)
    assert [case.expected_output.startswith("ACTIVATE") for case in package.evals] == [
        True,
        True,
        True,
        False,
        False,
        False,
    ]


def test_observed_activation_results_cover_every_opencode_eval_and_codex_positive() -> None:
    """Require observed harness decisions and the exact injected canonical path."""
    eval_package = EvalPackage.model_validate_json(EVALS_PATH.read_text(encoding="utf-8"))
    results = ActivationResults.model_validate_json(ACTIVATION_RESULTS_PATH.read_text(encoding="utf-8"))
    opencode_cases = {case.eval_id: case for case in results.cases if case.harness == "opencode"}
    codex_cases = [case for case in results.cases if case.harness == "codex"]

    assert results.schema_version == 2
    assert results.skill_name == eval_package.skill_name
    assert results.repository_head_before == results.repository_head_after
    assert results.repository_status_before == results.repository_status_after == ""
    assert set(opencode_cases) == {case.id for case in eval_package.evals}
    assert codex_cases
    assert all(case.observed_activation for case in codex_cases)
    assert all(case.status == "PASSED" for case in results.cases)
    for evaluation in eval_package.evals:
        observed = opencode_cases[evaluation.id]
        expected_activation = evaluation.expected_output.startswith("ACTIVATE")
        assert observed.expected_activation is expected_activation
        assert observed.observed_activation is expected_activation
        assert observed.prompt == evaluation.prompt
        assert observed.model
        assert observed.proxy == "portkey"
        assert observed.state_transitions
        assert observed.final_terminal
        assert (observed.loaded_skill_path is not None) is expected_activation
        if expected_activation:
            assert any(event.startswith("read:") for event in observed.filesystem_action_events)
            assert not any(event.startswith(("write:", "delete:")) for event in observed.filesystem_action_events)
            assert observed.provider_action_events == []
            if evaluation.id in {2, 3}:
                assert observed.read_references
        else:
            assert observed.final_terminal == "DO_NOT_ACTIVATE"


def test_git_inventory_keeps_net_zero_commits_and_rename_pairs(tmp_path: Path) -> None:
    """Prove endpoint diffs cannot replace ordered candidate and rename inventories."""
    repository = tmp_path / "inventory"
    base_oid = initialize_repository(repository)
    (repository / "old.py").write_text("value = 1\n", encoding="utf-8")
    run_git(repository, "add", "old.py")
    run_git(repository, "commit", "-m", "add old path")
    divergence_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()

    run_git(repository, "switch", "-c", "feature")
    commit_file(repository, "old.py", "value = 2\n", "temporarily change value")
    commit_file(repository, "old.py", "value = 1\n", "restore value")
    feature_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()

    run_git(repository, "switch", "main")
    run_git(repository, "mv", "old.py", "new.py")
    run_git(repository, "commit", "-m", "rename old path")
    target_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()

    candidates = run_git(repository, "rev-list", "--reverse", f"{target_oid}..{feature_oid}").stdout.splitlines()
    endpoint_paths = run_git(repository, "diff", "--name-only", f"{divergence_oid}..{feature_oid}").stdout
    target_status = run_git(repository, "diff", "--name-status", "-M", f"{divergence_oid}..{target_oid}").stdout

    assert base_oid != divergence_oid
    assert len(candidates) == 2
    assert endpoint_paths == ""
    assert target_status.strip() == "R100\told.py\tnew.py"


def test_git_inventory_surfaces_merge_and_clean_cherry_pick_candidates(tmp_path: Path) -> None:
    """Prove Git exposes topology and patch-equivalent candidates before replay."""
    merge_repository = tmp_path / "merge"
    merge_base = initialize_repository(merge_repository)
    run_git(merge_repository, "switch", "-c", "feature")
    commit_file(merge_repository, "feature.txt", "feature\n", "feature change")
    run_git(merge_repository, "switch", "-c", "side", merge_base)
    commit_file(merge_repository, "side.txt", "side\n", "side change")
    run_git(merge_repository, "switch", "feature")
    run_git(merge_repository, "merge", "--no-ff", "side", "-m", "feature topology")
    parent_records = run_git(merge_repository, "rev-list", "--parents", "main..feature").stdout.splitlines()

    cherry_repository = tmp_path / "cherry"
    initialize_repository(cherry_repository)
    run_git(cherry_repository, "switch", "-c", "feature")
    feature_change = commit_file(cherry_repository, "shared.txt", "shared\n", "feature patch")
    run_git(cherry_repository, "switch", "main")
    commit_file(cherry_repository, "target.txt", "target\n", "target-only change")
    run_git(cherry_repository, "cherry-pick", feature_change)
    cherry_evidence = run_git(cherry_repository, "cherry", "-v", "main", "feature").stdout

    assert any(len(record.split()) > 2 for record in parent_records)
    assert cherry_evidence.startswith(f"- {feature_change}")


def test_conflict_stages_have_swapped_rebase_sides_and_abort_restores(tmp_path: Path) -> None:
    """Prove conflict-side semantics and durable abort restoration with real Git."""
    repository = tmp_path / "conflict"
    initialize_repository(repository)
    commit_file(repository, "shared.txt", "original\n", "add shared file")
    run_git(repository, "switch", "-c", "feature")
    commit_file(repository, "shared.txt", "feature\n", "feature edits shared")
    old_tip = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "branch", "rebase-backup/conflict", old_tip)

    run_git(repository, "switch", "main")
    commit_file(repository, "shared.txt", "target\n", "target edits shared")
    target_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "feature")

    empty_option = supported_empty_option(repository)
    result = run_git(
        repository,
        "-c",
        "core.editor=true",
        "rebase",
        "--reapply-cherry-picks",
        f"--empty={empty_option}",
        target_oid,
        check=False,
    )

    assert result.returncode != 0
    assert run_git(repository, "show", ":2:shared.txt").stdout == "target\n"
    assert run_git(repository, "show", ":3:shared.txt").stdout == "feature\n"
    assert run_git(repository, "ls-files", "--unmerged").stdout

    run_git(repository, "rebase", "--abort")
    assert run_git(repository, "rev-parse", "feature").stdout.strip() == old_tip
    assert run_git(repository, "rev-parse", "rebase-backup/conflict").stdout.strip() == old_tip
    assert run_git(repository, "status", "--porcelain=v1", "--untracked-files=all").stdout == ""
    assert run_git(repository, "ls-files", "--unmerged").stdout == ""


def test_reapply_cherry_pick_with_empty_stop_surfaces_exact_candidate(tmp_path: Path) -> None:
    """Prove the selected options stop instead of silently dropping an empty replay."""
    repository = tmp_path / "empty"
    initialize_repository(repository)
    run_git(repository, "switch", "-c", "feature")
    candidate_oid = commit_file(repository, "shared.txt", "same outcome\n", "feature outcome")
    old_tip = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "branch", "rebase-backup/empty", old_tip)

    run_git(repository, "switch", "main")
    commit_file(repository, "shared.txt", "same outcome\n", "target outcome")
    target_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "feature")

    empty_option = supported_empty_option(repository)
    result = run_git(
        repository,
        "-c",
        "core.editor=true",
        "rebase",
        "--reapply-cherry-picks",
        f"--empty={empty_option}",
        target_oid,
        check=False,
    )

    assert result.returncode != 0
    assert run_git(repository, "rev-parse", "REBASE_HEAD").stdout.strip() == candidate_oid
    assert "same outcome" in run_git(repository, "rebase", "--show-current-patch").stdout
    run_git(repository, "rebase", "--abort")
    assert run_git(repository, "rev-parse", "feature").stdout.strip() == old_tip


def test_preflight_evidence_exposes_dirty_foreign_worktree_and_ref_drift(tmp_path: Path) -> None:
    """Prove each no-mutation preflight blocker has an observable Git signal."""
    repository = tmp_path / "preflight"
    initialize_repository(repository)
    original_feature = run_git(repository, "rev-parse", "main").stdout.strip()
    foreign_worktree = tmp_path / "foreign-worktree"
    run_git(repository, "worktree", "add", "-b", "feature", str(foreign_worktree), original_feature)
    (foreign_worktree / "untracked.txt").write_text("foreign work\n", encoding="utf-8")

    worktrees = run_git(repository, "worktree", "list", "--porcelain").stdout
    foreign_status = run_git(foreign_worktree, "status", "--porcelain=v1", "--untracked-files=all").stdout
    captured_target = run_git(repository, "rev-parse", "main").stdout.strip()
    commit_file(repository, "target.txt", "target drift\n", "move target")
    fresh_target = run_git(repository, "rev-parse", "main").stdout.strip()

    assert f"worktree {foreign_worktree}" in worktrees
    assert "branch refs/heads/feature" in worktrees
    assert foreign_status == "?? untracked.txt\n"
    assert captured_target != fresh_target
    assert run_git(repository, "rev-parse", "feature").stdout.strip() == original_feature
    assert (foreign_worktree / "untracked.txt").read_text(encoding="utf-8") == "foreign work\n"


def run_linear_rebase_fixture(repository: Path, remote_url: str) -> tuple[list[tuple[str, ...]], str]:
    """Run the same local rebase with an arbitrary forge-shaped remote.

    Args:
        repository: Temporary repository path.
        remote_url: Remote URL recorded but never contacted.

    Returns:
        Git command transcript and final tree listing.
    """
    transcript: list[tuple[str, ...]] = []
    initialize_repository(repository)
    run_git(repository, "remote", "add", "origin", remote_url, transcript=transcript)
    run_git(repository, "switch", "-c", "feature", transcript=transcript)
    commit_file(repository, "feature.txt", "feature\n", "feature change")
    old_tip = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "branch", "rebase-backup/linear", old_tip, transcript=transcript)
    run_git(repository, "switch", "main", transcript=transcript)
    commit_file(repository, "target.txt", "target\n", "target change")
    target_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "feature", transcript=transcript)
    empty_option = supported_empty_option(repository, transcript)
    run_git(
        repository, "rebase", "--reapply-cherry-picks", f"--empty={empty_option}", target_oid, transcript=transcript
    )
    assert run_git(repository, "merge-base", "--is-ancestor", target_oid, "feature").returncode == 0
    assert run_git(repository, "status", "--porcelain=v1", "--untracked-files=all").stdout == ""
    tree = run_git(repository, "ls-tree", "-r", "--name-only", "HEAD").stdout
    return transcript, tree


def normalize_git_transcript(transcript: list[tuple[str, ...]]) -> list[tuple[str, ...]]:
    """Remove repository-specific OIDs and remote declarations from a transcript.

    Args:
        transcript: Recorded Git argument vectors.

    Returns:
        Forge-neutral local command sequence.
    """
    return [
        tuple("<oid>" if re.fullmatch(r"[0-9a-f]{40,64}", argument) else argument for argument in command)
        for command in transcript
        if command[:3] != ("git", "remote", "add")
    ]


def test_forge_shaped_remotes_produce_identical_local_rebase_behavior(tmp_path: Path) -> None:
    """Keep the rebase command path independent of GitHub- or GitLab-shaped remotes."""
    github_transcript, github_tree = run_linear_rebase_fixture(
        tmp_path / "github-shaped", "git@github.com:example/project.git"
    )
    gitlab_transcript, gitlab_tree = run_linear_rebase_fixture(
        tmp_path / "gitlab-shaped", "git@gitlab.example.com:group/project.git"
    )

    normalized_github = normalize_git_transcript(github_transcript)
    normalized_gitlab = normalize_git_transcript(gitlab_transcript)
    assert normalized_github == normalized_gitlab
    assert github_tree == gitlab_tree
    assert all(command[0] == "git" for command in (*github_transcript, *gitlab_transcript))
