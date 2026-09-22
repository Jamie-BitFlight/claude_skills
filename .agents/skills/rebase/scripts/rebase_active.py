#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# ///
"""Inspect an active-rebase entry route without mutating the repository."""

from __future__ import annotations

import json
import os
import signal
import subprocess
from pathlib import Path

COMMAND_TIMEOUT_SECONDS = 20
TERMINATION_GRACE_SECONDS = 2


def run_git(*arguments: str) -> dict[str, object]:
    """Run one bounded Git inspection.

    Returns:
        Complete command evidence.
    """
    argv = ["git", *arguments]
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=COMMAND_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        terminate_process_group(process)
        stdout, stderr = process.communicate()
        return {"argv": argv, "exit_code": 124, "stdout": stdout, "stderr": stderr, "timed_out": True}
    return {"argv": argv, "exit_code": process.returncode, "stdout": stdout, "stderr": stderr}


def terminate_process_group(process: subprocess.Popen[str]) -> None:
    """Terminate a timed-out command and its process group where supported."""
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGTERM)
    else:
        process.terminate()
    try:
        process.wait(timeout=TERMINATION_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()


def command_exit(command: dict[str, object]) -> int:
    """Return a command evidence record's integer exit code."""
    exit_code = command["exit_code"]
    if not isinstance(exit_code, int):
        raise TypeError("command exit code is not an integer")
    return exit_code


def command_stdout(command: dict[str, object]) -> str:
    """Return a command evidence record's complete standard output."""
    stdout = command["stdout"]
    if not isinstance(stdout, str):
        raise TypeError("command stdout is not text")
    return stdout


def resolve_git_path(repository_root: Path, command: dict[str, object]) -> Path:
    """Resolve one successful `git rev-parse --git-path` result.

    Returns:
        Absolute path for the Git-managed location.
    """
    path = Path(command_stdout(command).strip())
    return path if path.is_absolute() else repository_root / path


def inspect_active_rebase() -> tuple[dict[str, object], int]:
    """Inspect active-rebase evidence.

    Returns:
        Structured route evidence and the process exit code.
    """
    commands: list[dict[str, object]] = []
    repository_root_command = run_git("rev-parse", "--show-toplevel")
    commands.append(repository_root_command)
    if command_exit(repository_root_command) != 0:
        return blocked_result(commands, "repository root inspection failed"), 1

    repository_root = Path(command_stdout(repository_root_command).strip())
    captured = capture_active_commands()
    commands.extend(captured.values())

    required_success = (captured["rebase_merge"], captured["rebase_apply"], captured["status"])
    expected_optional = (captured["rebase_head"], captured["current_branch"])
    if any(command_exit(command) != 0 for command in required_success) or any(
        command_exit(command) not in {0, 1} for command in expected_optional
    ):
        return blocked_result(commands, "active-rebase inspection failed"), 1

    rebase_merge_present = resolve_git_path(repository_root, captured["rebase_merge"]).is_dir()
    rebase_apply_present = resolve_git_path(repository_root, captured["rebase_apply"]).is_dir()
    rebase_head_present = command_exit(captured["rebase_head"]) == 0
    current_branch = command_stdout(captured["current_branch"]).strip() or None
    active = rebase_merge_present or rebase_apply_present or rebase_head_present
    route = "active" if active else "NO_ACTIVE_REBASE"
    return (
        {
            "commands": commands,
            "current_branch": current_branch,
            "head_detached": current_branch is None,
            "rebase_apply_present": rebase_apply_present,
            "rebase_head_present": rebase_head_present,
            "rebase_merge_present": rebase_merge_present,
            "repository_root": str(repository_root),
            "route": route,
            "status": command_stdout(captured["status"]),
        },
        0,
    )


def capture_active_commands() -> dict[str, dict[str, object]]:
    """Capture the operation markers, branch attachment, and status.

    Returns:
        Named complete command-evidence records.
    """
    return {
        "rebase_merge": run_git("rev-parse", "--git-path", "rebase-merge"),
        "rebase_apply": run_git("rev-parse", "--git-path", "rebase-apply"),
        "rebase_head": run_git("rev-parse", "--verify", "--quiet", "REBASE_HEAD"),
        "current_branch": run_git("symbolic-ref", "--quiet", "--short", "HEAD"),
        "status": run_git("status", "--porcelain=v1", "--branch", "--untracked-files=all"),
    }


def blocked_result(commands: list[dict[str, object]], reason: str) -> dict[str, object]:
    """Build a complete failed-preflight result.

    Returns:
        Structured failed-preflight evidence.
    """
    return {"commands": commands, "reason": reason, "route": "BLOCKED_PREFLIGHT_FAILED"}


def main() -> int:
    """Emit the active-operation route as compact JSON.

    Returns:
        Process exit code for the selected route.
    """
    result, exit_code = inspect_active_rebase()
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
