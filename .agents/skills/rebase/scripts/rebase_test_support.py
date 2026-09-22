"""Shared bounded Git fixtures for rebase skill tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
BOUNDED_RUNNER = REPOSITORY_ROOT / "scripts" / "run_bounded.py"

# Local Git fixture commands complete in milliseconds. Twenty seconds permits slow CI filesystems
# while still proving that a hung hook or descendant process is terminated by the bounded runner.
TEST_COMMAND_TIMEOUT_SECONDS = 20


def run_git(
    repository: Path, *arguments: str, check: bool = True, transcript: list[tuple[str, ...]] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run one Git command through the repository's bounded process-group owner.

    Returns:
        Completed bounded Git process.
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

    Returns:
        Full OID of the created commit.
    """
    path = repository / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    run_git(repository, "add", relative_path)
    run_git(repository, "commit", "-m", message)
    return run_git(repository, "rev-parse", "HEAD").stdout.strip()


def capture_repository_state(
    repository: Path, *, branch_ref: str, target_ref: str, transcript: list[tuple[str, ...]]
) -> tuple[dict[str, object], dict[str, object]]:
    """Capture all universal Step 1 commands plus publication evidence from Git.

    Returns:
        Repository-state and publication evidence mappings.
    """
    repository_root = capture_command(repository, transcript, "rev-parse", "--show-toplevel")
    root = Path(str(repository_root["stdout"]).strip())
    branch_oid = capture_command(repository, transcript, "rev-parse", "--verify", f"{branch_ref}^{{commit}}")
    upstream = capture_command(repository, transcript, "for-each-ref", "--format=%(upstream)", branch_ref)

    repository_state = {
        "repository_root": repository_root,
        "branch_ref": capture_command(repository, transcript, "show-ref", "--verify", branch_ref),
        "branch_oid": branch_oid,
        "target_oid": capture_command(repository, transcript, "rev-parse", "--verify", f"{target_ref}^{{commit}}"),
        "merge_base": capture_command(repository, transcript, "merge-base", branch_ref, target_ref),
        "worktrees": capture_command(repository, transcript, "worktree", "list", "--porcelain"),
        "status": capture_command(repository, transcript, "status", "--porcelain=v1", "--untracked-files=all"),
        "current_branch": capture_command(repository, transcript, "symbolic-ref", "--quiet", "--short", "HEAD"),
        "rebase_merge": capture_path_marker(repository, transcript, root, "rebase-merge"),
        "rebase_apply": capture_path_marker(repository, transcript, root, "rebase-apply"),
        "merge_head": capture_ref_marker(repository, transcript, "MERGE_HEAD"),
        "cherry_pick_head": capture_ref_marker(repository, transcript, "CHERRY_PICK_HEAD"),
        "upstream": upstream,
    }
    return repository_state, capture_publication(repository, transcript, upstream, str(branch_oid["stdout"]).strip())


def capture_command(
    repository: Path, transcript: list[tuple[str, ...]], *arguments: str, check: bool = True
) -> dict[str, object]:
    """Capture one complete bounded Git command record.

    Returns:
        JSON-compatible command evidence.
    """
    result = run_git(repository, *arguments, check=check, transcript=transcript)
    return {
        "source": "local-git",
        "argv": list(transcript[-1]),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def capture_path_marker(
    repository: Path, transcript: list[tuple[str, ...]], root: Path, name: str
) -> dict[str, object]:
    """Capture one Git-path lookup and filesystem-presence observation.

    Returns:
        JSON-compatible marker evidence.
    """
    command = capture_command(repository, transcript, "rev-parse", "--git-path", name)
    return {"command": command, "present": (root / str(command["stdout"]).strip()).exists()}


def capture_ref_marker(repository: Path, transcript: list[tuple[str, ...]], name: str) -> dict[str, object]:
    """Capture one optional Git operation-ref lookup.

    Returns:
        JSON-compatible marker evidence.
    """
    command = capture_command(repository, transcript, "rev-parse", "--verify", "--quiet", name, check=False)
    return {"command": command, "present": command["exit_code"] == 0}


def capture_publication(
    repository: Path, transcript: list[tuple[str, ...]], upstream: dict[str, object], old_tip: str
) -> dict[str, object]:
    """Capture upstream and remote-containment evidence.

    Returns:
        JSON-compatible publication evidence.
    """
    remote_refs = capture_command(
        repository, transcript, "for-each-ref", "--format=%(refname)", "--contains", old_tip, "refs/remotes"
    )
    return {
        "configured_upstream": str(upstream["stdout"]).strip() or None,
        "remote_refs_containing_old_tip": str(remote_refs["stdout"]).splitlines(),
        "evidence_commands": [remote_refs],
    }
