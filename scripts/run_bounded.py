#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# ///
"""Run one command with a timeout and terminate its process group on expiry."""

from __future__ import annotations

import argparse
import contextlib
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any, TextIO

if os.name == "nt":
    import msvcrt
else:
    import fcntl

TIMEOUT_EXIT_CODE = 124
TERMINATION_GRACE_SECONDS = 0.5
PYTEST_LOCK_PATH = Path(tempfile.gettempdir()) / "claude-skills-pytest.lock"


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line parser.

    Returns:
        A configured parser accepting ``--timeout-seconds`` and the trailing command.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="Maximum command duration before process-tree termination. Default: 5.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def terminate_windows_process_tree(pid: int) -> None:
    """Terminate a Windows process and all of its descendants.

    Args:
        pid: Process ID of the tree's root process.
    """
    taskkill = shutil.which("taskkill") or "taskkill"
    subprocess.run([taskkill, "/PID", str(pid), "/T", "/F"], check=False)


def process_group_is_alive(pgid: int) -> bool:
    """Probe whether any process remains in the given process group.

    Args:
        pgid: Process group ID to probe, typically the group leader's PID.

    Returns:
        ``True`` if at least one process in the group is still alive.
    """
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    return True


def _is_pytest_command(command: list[str]) -> bool:
    if not command:
        return False

    executable = Path(command[0]).name.lower()
    if executable in {"pytest", "pytest.exe"}:
        return True
    if command[1:3] == ["-m", "pytest"]:
        return True
    return command[:2] == ["uv", "run"] and (command[2:3] == ["pytest"] or command[2:4] == ["-m", "pytest"])


def _lock_file(lock: TextIO) -> None:
    lock.seek(0)
    lock.write("0")
    lock.flush()
    if os.name == "nt":
        msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        return

    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)


def _unlock_file(lock: TextIO) -> None:
    lock.seek(0)
    if os.name == "nt":
        msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        return

    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


@contextlib.contextmanager
def _pytest_lock(command: list[str]) -> Iterator[None]:
    if not _is_pytest_command(command):
        yield
        return

    with PYTEST_LOCK_PATH.open("a+") as lock:
        _lock_file(lock)
        try:
            yield
        finally:
            _unlock_file(lock)


def terminate_process_tree(process: subprocess.Popen[Any]) -> None:
    """Terminate the isolated process group, escalating after a short grace period."""
    if os.name != "posix":
        terminate_windows_process_tree(process.pid)
        return

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=TERMINATION_GRACE_SECONDS)

    # The leader's wait() can return before its descendants exit — a descendant
    # that ignores SIGTERM keeps the process group alive after the leader is
    # reaped. Probe the group itself rather than trusting the leader's status.
    if not process_group_is_alive(process.pid):
        return

    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    process.wait()


def run_command(command: list[str], timeout_seconds: float) -> int:
    """Run a command and return its exit status, or 124 after a timeout.

    Args:
        command: Argv of the command to run.
        timeout_seconds: Maximum duration before the process tree is terminated.

    Returns:
        The command's exit status, or ``TIMEOUT_EXIT_CODE`` if it was terminated.

    Raises:
        ValueError: If ``timeout_seconds`` is not positive or ``command`` is empty.
    """
    if timeout_seconds <= 0:
        raise ValueError("--timeout-seconds must be greater than zero")
    if not command:
        raise ValueError("A command is required after --")

    with _pytest_lock(command):
        process = subprocess.Popen(command, start_new_session=os.name == "posix")
        try:
            return process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            terminate_process_tree(process)
            print(f"timed out after {timeout_seconds:g} seconds", file=sys.stderr)
            return TIMEOUT_EXIT_CODE


def main() -> int:
    """Run the parsed command within the selected timeout.

    Returns:
        The wrapped command's exit status, ``TIMEOUT_EXIT_CODE`` on timeout, or ``2``
        on an invalid invocation.
    """
    args = create_parser().parse_args()
    try:
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        return run_command(command, args.timeout_seconds)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
