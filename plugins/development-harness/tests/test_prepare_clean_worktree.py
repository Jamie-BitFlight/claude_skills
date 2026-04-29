from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

GIT_SHA1_LENGTH = 40


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, check=True)


def _init_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init"], cwd=repo)
    _run(["git", "config", "user.email", "test@example.com"], cwd=repo)
    _run(["git", "config", "user.name", "Test User"], cwd=repo)
    _run(["git", "config", "commit.gpgsign", "false"], cwd=repo)
    _run(["git", "checkout", "-b", "main"], cwd=repo)
    (repo / "tracked.txt").write_text("initial\n", encoding="utf-8")
    _run(["git", "add", "tracked.txt"], cwd=repo)
    _run(["git", "commit", "-m", "init"], cwd=repo)
    return repo


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "prepare_clean_worktree.sh"


def _repo_slug(path: Path) -> str:
    return str(path).replace("/", "-").replace("\\", "-")


def _parse_stash_ref(output: str) -> str:
    marker = "Auto-stash created: "
    if marker in output:
        return output.split(marker, maxsplit=1)[1].strip().split()[0]
    msg = f"missing stash output in: {output!r}"
    raise AssertionError(msg)


def test_prepare_clean_worktree_no_prompt_when_clean(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    state_home = tmp_path / "state"
    env = {**os.environ, "HOME": str(tmp_path), "DH_STATE_HOME": str(state_home)}

    result = subprocess.run(
        [str(_script_path()), "milestone/1-example"], cwd=repo, env=env, capture_output=True, text=True, check=False
    )

    assert result.returncode == 0
    assert "Stash uncommitted changes" not in result.stdout


def test_prepare_clean_worktree_decline_exits_non_zero(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    state_home = tmp_path / "state"
    env = {**os.environ, "HOME": str(tmp_path), "DH_STATE_HOME": str(state_home)}
    (repo / "scratch.txt").write_text("dirty\n", encoding="utf-8")

    result = subprocess.run(
        [str(_script_path()), "milestone/1-example"],
        cwd=repo,
        env=env,
        input="\n",
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Stash uncommitted changes? [y/N]" in result.stdout
    assert "Please stash or commit your changes" in result.stdout


def test_prepare_clean_worktree_eof_defaults_to_non_zero_abort(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    state_home = tmp_path / "state"
    env = {**os.environ, "HOME": str(tmp_path), "DH_STATE_HOME": str(state_home)}
    (repo / "scratch.txt").write_text("dirty\n", encoding="utf-8")

    result = subprocess.run(
        [str(_script_path()), "milestone/1-example"],
        cwd=repo,
        env=env,
        input="",
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Stash uncommitted changes? [y/N]" in result.stdout
    assert "Please stash or commit your changes" in result.stdout


def test_prepare_clean_worktree_stashes_and_records_ref(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    state_home = tmp_path / "state"
    env = {**os.environ, "HOME": str(tmp_path), "DH_STATE_HOME": str(state_home)}
    branch_name = "milestone/1-example"
    (repo / "scratch.txt").write_text("dirty\n", encoding="utf-8")

    result = subprocess.run(
        [str(_script_path()), branch_name], cwd=repo, env=env, input="y\n", capture_output=True, text=True, check=False
    )

    assert result.returncode == 0
    assert "Stash uncommitted changes? [y/N]" in result.stdout
    stash_ref = _parse_stash_ref(result.stdout)
    assert len(stash_ref) == GIT_SHA1_LENGTH

    stash_lines = _run(["git", "stash", "list", "--format=%H %gs"], cwd=repo).stdout.splitlines()
    assert stash_lines
    stash_first = stash_lines[0]
    assert stash_ref in stash_first
    assert f"dh-auto-stash: pre-run {branch_name}" in stash_first

    slug = _repo_slug(repo)
    record_file = state_home / "projects" / slug / "context" / "auto-stashes.json"
    assert record_file.exists()

    data = json.loads(record_file.read_text(encoding="utf-8"))
    assert data[branch_name] == stash_ref
