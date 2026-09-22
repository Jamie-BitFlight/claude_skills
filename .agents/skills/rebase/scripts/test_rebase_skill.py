#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "marko>=2.2",
#   "pydantic>=2.0",
#   "pytest",
# ]
# ///
"""Behavioral package tests for the rebase skill."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator
from pathlib import Path

import marko
from marko.block import FencedCode, Heading, Paragraph
from marko.inline import Link
from pydantic import BaseModel

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
SKILL_PATH = SKILL_ROOT / "SKILL.md"
REFERENCE_PATH = SKILL_ROOT / "references" / "rebase-edge-cases.md"
EVALS_PATH = SKILL_ROOT / "evals" / "evals.json"


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
    return subprocess.run(command, cwd=repository, check=check, capture_output=True, text=True, timeout=20)


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

    tracked = subprocess.run(
        ["git", "ls-files", "-s", ".claude/skills/rebase"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert tracked.stdout.startswith("120000 ")


def test_each_universal_step_has_an_observable_completion_criterion() -> None:
    """Require every numbered main-path step to expose a completion gate."""
    document = parse_markdown(SKILL_PATH)
    top_level = getattr(document, "children", [])
    assert isinstance(top_level, list)

    numbered_headings = [
        (index, node)
        for index, node in enumerate(top_level)
        if isinstance(node, Heading) and node.level == 2 and re.match(r"^[1-6]\. ", node_text(node))
    ]
    assert len(numbered_headings) == 6
    all_headings = [node_text(node) for node in top_level if isinstance(node, Heading)]
    assert "Rules" not in all_headings
    assert not any(heading.startswith("Step ") for heading in all_headings)

    for position, (start, heading) in enumerate(numbered_headings):
        end = numbered_headings[position + 1][0] if position + 1 < len(numbered_headings) else len(top_level)
        section_nodes = top_level[start + 1 : end]
        criteria = [
            node_text(node)
            for node in section_nodes
            if isinstance(node, Paragraph) and node_text(node).startswith("Completion criterion:")
        ]
        assert len(criteria) == 1, node_text(heading)


def test_conditional_references_are_routable_and_exist() -> None:
    """Expose each branch-only reference through a condition-bearing pointer."""
    document = parse_markdown(SKILL_PATH)
    pointers: list[tuple[str, str]] = []

    for node in walk(document):
        if not isinstance(node, Paragraph):
            continue
        paragraph_text = node_text(node)
        links = [child for child in walk(node) if isinstance(child, Link)]
        pointers.extend((paragraph_text, link.dest) for link in links)

    edge_pointers = [(text, destination) for text, destination in pointers if destination.startswith("./references/")]
    assert len(edge_pointers) == 3
    for text, destination in edge_pointers:
        assert text.startswith("When ")
        assert (SKILL_ROOT / destination).is_file()


def test_terminal_state_contract_covers_every_safety_branch() -> None:
    """Keep all required observable terminals available to the workflow."""
    package_text = SKILL_PATH.read_text(encoding="utf-8") + REFERENCE_PATH.read_text(encoding="utf-8")
    required_states = {
        "BLOCKED_INVALID_REF",
        "BLOCKED_GIT_STATE",
        "BLOCKED_WORKTREE_IN_USE",
        "NO_CHANGE",
        "READY_TO_REBASE",
        "NEEDS_USER_DECISION",
        "REPLAN_REF_DRIFT",
        "CONFLICT",
        "UNEXPECTED_CONFLICT",
        "EMPTY_COMMIT_DECISION",
        "REBASE_ABORTED_RESTORED",
        "BLOCKED_ABORT_FAILED",
        "REBASE_COMPLETE_VALIDATION_FAILED",
        "REBASE_COMPLETE_VERIFIED",
    }
    missing = {state for state in required_states if f"`{state}`" not in package_text}
    assert not missing


def test_executable_instructions_are_forge_neutral_and_plan_gated() -> None:
    """Exclude forge/publication commands and order local rebase after the plan gate."""
    document = parse_markdown(SKILL_PATH)
    reference = parse_markdown(REFERENCE_PATH)
    command_text = "\n".join(
        node_text(node) for tree in (document, reference) for node in walk(tree) if isinstance(node, FencedCode)
    )

    assert not re.search(r"(?m)^\s*(?:gh|glab)\s", command_text)
    assert not re.search(r"(?m)^\s*git\s+(?:push\b|merge(?:\s|$))", command_text)

    skill_text = SKILL_PATH.read_text(encoding="utf-8")
    plan_gate = skill_text.index("READY_TO_REBASE")
    rebase_execution = skill_text.index("git rebase --reapply-cherry-picks")
    assert plan_gate < rebase_execution


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

    result = run_git(
        repository,
        "-c",
        "core.editor=true",
        "rebase",
        "--reapply-cherry-picks",
        "--empty=stop",
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

    result = run_git(
        repository,
        "-c",
        "core.editor=true",
        "rebase",
        "--reapply-cherry-picks",
        "--empty=stop",
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
    run_git(repository, "rebase", "--reapply-cherry-picks", "--empty=stop", target_oid, transcript=transcript)
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
