"""Bounded subprocess execution with process-tree cleanup."""

from __future__ import annotations

import contextlib
import os
import shutil
import signal
import subprocess
from typing import Any

DEFAULT_COMMAND_TIMEOUT_SECONDS = 30.0
TERMINATION_GRACE_SECONDS = 0.5


def terminate_windows_process_tree(process: subprocess.Popen[Any]) -> None:
    """Terminate a Windows process and its descendants.

    Args:
        process: Root process of the tree to terminate.
    """
    taskkill = shutil.which("taskkill") or "taskkill"
    try:
        subprocess.run([taskkill, "/PID", str(process.pid), "/T", "/F"], check=False, timeout=TERMINATION_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()


def process_group_is_alive(process_group_id: int) -> bool:
    """Probe a POSIX process group.

    Args:
        process_group_id: Group ID to probe.

    Returns:
        Whether any process remains in the group.
    """
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    return True


def terminate_process_tree(process: subprocess.Popen[Any]) -> None:
    """Terminate an isolated process tree and escalate after a short grace.

    Args:
        process: Root process launched in its own POSIX session where supported.
    """
    if os.name != "posix":
        terminate_windows_process_tree(process)
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=TERMINATION_GRACE_SECONDS)
    if not process_group_is_alive(process.pid):
        return
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)
    process.wait()


def run_capture(command: list[str], *, timeout: float | None = None) -> str:
    """Run a command with a mandatory bound and capture its complete output.

    Args:
        command: Command argv without shell interpretation.
        timeout: Positive caller bound; the default is 30 seconds.

    Returns:
        Complete standard output.

    Raises:
        ValueError: If the command is empty or the timeout is not positive.
        subprocess.CalledProcessError: If the command exits nonzero.
        subprocess.TimeoutExpired: If the bound expires after process-tree cleanup.
    """
    timeout_seconds = DEFAULT_COMMAND_TIMEOUT_SECONDS if timeout is None else timeout
    if not command:
        raise ValueError("command must not be empty")
    if timeout_seconds <= 0:
        raise ValueError("command timeout must be greater than zero")
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=os.name == "posix"
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        terminate_process_tree(process)
        raise subprocess.TimeoutExpired(command, timeout_seconds, output=exc.output, stderr=exc.stderr) from exc
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, command, output=stdout, stderr=stderr)
    return stdout
