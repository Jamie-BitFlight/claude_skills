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
from collections.abc import Iterator
from pathlib import Path

import marko
from marko.block import FencedCode
from marko.inline import Link

from rebase_activation import ActivationResults, EvalPackage, evaluate_activation_results
from rebase_evidence import ExecutionMode
from rebase_plan import Disposition, MergePolicy
from rebase_states import workflow_state_definitions
from rebase_test_support import (
    REPOSITORY_ROOT,
    SKILL_ROOT,
    commit_file,
    initialize_repository,
    run_git,
    supported_empty_option,
)

SKILL_PATH = SKILL_ROOT / "SKILL.md"
START_REFERENCE_PATH = SKILL_ROOT / "references" / "start-rebase.md"
ACTIVE_REFERENCE_PATH = SKILL_ROOT / "references" / "active-rebase.md"
ACTIVE_OPERATION_REFERENCE_PATH = SKILL_ROOT / "references" / "active-rebase-operation.md"
EDGE_REFERENCE_PATH = SKILL_ROOT / "references" / "rebase-edge-cases.md"
STEP_BY_STEP_PATH = SKILL_ROOT / "references" / "step-by-step.md"
EXAMPLE_PLAN_PATH = SKILL_ROOT / "references" / "example-plan.json"
EVALS_PATH = SKILL_ROOT / "evals" / "evals.json"
ACTIVATION_RESULTS_PATH = SKILL_ROOT / "evals" / "activation-results.json"


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
    source_paths = (SKILL_PATH, *sorted((SKILL_ROOT / "references").glob("*.md")))
    local_links = []
    for source_path in source_paths:
        document = parse_markdown(source_path)
        local_links.extend(
            (source_path.parent / node.dest.split("#", maxsplit=1)[0]).resolve()
            for node in walk(document)
            if isinstance(node, Link) and not node.dest.startswith("http")
        )

    assert local_links
    assert all(destination.is_file() for destination in local_links)


def test_terminal_state_contract_covers_every_safety_branch() -> None:
    """Reject prompt state tokens absent from the typed canonical vocabulary."""
    package_text = "\n".join(
        path.read_text(encoding="utf-8") for path in (SKILL_PATH, *sorted((SKILL_ROOT / "references").glob("*.md")))
    )
    presented_states = set(re.findall(r"`([A-Z][A-Z_]+)`", package_text))
    canonical_states = {state.value for state in workflow_state_definitions()}
    non_state_contract_tokens = {
        *(disposition.value for disposition in Disposition),
        *(policy.value for policy in MergePolicy),
        *(mode.value for mode in ExecutionMode),
        "CHERRY_PICK_HEAD",
        "HEAD",
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
    documents = [parse_markdown(path) for path in (SKILL_PATH, *sorted((SKILL_ROOT / "references").glob("*.md")))]
    command_text = "\n".join(
        node_text(node) for tree in documents for node in walk(tree) if isinstance(node, FencedCode)
    )

    assert not re.search(r"(?m)^\s*(?:gh|glab)\s", command_text)
    assert not re.search(r"(?m)^\s*git\s+(?:push\b|merge(?:\s|$))", command_text)
    assert "scripts/rebase_plan.py" in command_text
    assert not re.search(r"uv run --script scripts/rebase_plan\.py", command_text)


def test_activation_evals_cover_explicit_rebase_and_nearby_negative_routes() -> None:
    """Cover run, continue, abort, merge-update, forge-setting, and MR-merge routes."""
    package = EvalPackage.model_validate_json(EVALS_PATH.read_text(encoding="utf-8"))

    assert package.skill_name == "rebase"
    assert package.schema_version == 3
    assert len(package.evals) == 6
    assert len({case.id for case in package.evals}) == len(package.evals)
    assert all(case.expectations for case in package.evals)
    assert [case.expected_activation for case in package.evals] == [True, True, True, False, False, False]


def test_invocation_routes_disclose_only_the_selected_workflow() -> None:
    """Keep each routine route within its context budget."""
    package = EvalPackage.model_validate_json(EVALS_PATH.read_text(encoding="utf-8"))
    cases = {case.id: case for case in package.evals}

    assert cases[1].required_sources == ["SKILL.md", "references/start-rebase.md"]
    assert cases[2].required_sources == ["SKILL.md", "references/active-rebase.md"]
    assert cases[3].required_sources == ["SKILL.md", "references/active-rebase.md"]
    assert START_REFERENCE_PATH.is_file()
    assert ACTIVE_REFERENCE_PATH.is_file()
    assert ACTIVE_OPERATION_REFERENCE_PATH.is_file()
    assert EDGE_REFERENCE_PATH.is_file()

    active_bytes = len(SKILL_PATH.read_bytes()) + len(ACTIVE_REFERENCE_PATH.read_bytes())
    active_operation_bytes = active_bytes + len(ACTIVE_OPERATION_REFERENCE_PATH.read_bytes())
    start_bytes = len(SKILL_PATH.read_bytes()) + len(START_REFERENCE_PATH.read_bytes())
    assert len(SKILL_PATH.read_bytes()) <= 1_307
    assert start_bytes <= 8_000
    assert active_bytes <= 2_240
    assert active_operation_bytes <= 5_000
    assert len(EDGE_REFERENCE_PATH.read_bytes()) <= 2_500


def test_optional_walkthrough_is_never_a_routine_route_dependency() -> None:
    """Keep tutorials and the worked artifact outside routine execution context."""
    package = EvalPackage.model_validate_json(EVALS_PATH.read_text(encoding="utf-8"))
    required_sources = {source for case in package.evals for source in case.required_sources}
    routine_paths = (START_REFERENCE_PATH, ACTIVE_REFERENCE_PATH, ACTIVE_OPERATION_REFERENCE_PATH, EDGE_REFERENCE_PATH)

    skill_links = {node.dest for node in walk(parse_markdown(SKILL_PATH)) if isinstance(node, Link)}
    routine_links = {
        node.dest for path in routine_paths for node in walk(parse_markdown(path)) if isinstance(node, Link)
    }
    walkthrough_links = {node.dest for node in walk(parse_markdown(STEP_BY_STEP_PATH)) if isinstance(node, Link)}

    assert STEP_BY_STEP_PATH.is_file()
    assert EXAMPLE_PLAN_PATH.is_file()
    assert "./references/step-by-step.md" in skill_links
    assert "./example-plan.json" in walkthrough_links
    assert "references/step-by-step.md" not in required_sources
    assert "references/example-plan.json" not in required_sources
    assert all("step-by-step.md" not in link and "example-plan.json" not in link for link in routine_links)


def test_routine_contract_retains_non_intrinsic_safety_interfaces() -> None:
    """Pin typed gates and exceptional branches without pinning prose wording."""
    routine_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            SKILL_PATH,
            START_REFERENCE_PATH,
            ACTIVE_REFERENCE_PATH,
            ACTIVE_OPERATION_REFERENCE_PATH,
            EDGE_REFERENCE_PATH,
        )
    )
    required_tokens = {
        "rebase_plan.py",
        "rebase_active.py",
        "repository_state",
        "repository_instruction_search",
        "CURRENT_BRANCH",
        "AUTHORIZED_BRANCH_TRANSFER",
        *(disposition.value for disposition in Disposition),
        MergePolicy.PRESERVE_TOPOLOGY.value,
        MergePolicy.APPROVED_FLATTEN.value,
        "BLOCKED_INVALID_REF",
        "BLOCKED_WORKTREE_IN_USE",
        "NO_ACTIVE_REBASE",
        "PLAN_INVALID",
        "NEEDS_USER_DECISION",
        "REPLAN_REF_DRIFT",
        "EMPTY_COMMIT_DECISION",
        "REBASE_ABORTED_RESTORED",
        "BLOCKED_ABORT_FAILED",
        "BLOCKED_COMMAND_FAILED",
        "REBASE_COMPLETE_VALIDATION_FAILED",
        "REBASE_COMPLETE_VERIFIED",
        "not published",
    }

    assert required_tokens <= set(re.findall(r"not published|[A-Za-z_][A-Za-z0-9_.-]*", routine_text))


def test_observed_activation_results_derive_pass_from_current_sources_and_actions() -> None:
    """Reject stale, incomplete, unsafe, or self-attested activation evidence."""
    eval_package = EvalPackage.model_validate_json(EVALS_PATH.read_text(encoding="utf-8"))
    results = ActivationResults.model_validate_json(ACTIVATION_RESULTS_PATH.read_text(encoding="utf-8"))

    assert results.schema_version == 4
    assert evaluate_activation_results(SKILL_ROOT, eval_package, results) == []


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
