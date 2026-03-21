"""Quality gate executor for dispatch plan commands.

Executes a list of shell command strings via subprocess, captures results, and
returns a structured GateResult. No shell=True; commands are tokenised with
shlex.split and resolved via shutil.which before execution.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from functools import cache
from typing import TYPE_CHECKING

from dispatch_schema.core.models import CommandResult, GateResult, GateRunMode

if TYPE_CHECKING:
    from pathlib import Path


@cache
def _resolve_executable(name: str) -> str | None:
    """Return the full path of *name* on PATH, or None if not found.

    Result is cached so repeated gate runs do not re-stat the filesystem for
    the same executable name.

    Args:
        name: Bare executable name (e.g. ``"uv"`` or ``"ruff"``).

    Returns:
        Absolute path string from shutil.which, or None when not found.
    """
    return shutil.which(name)


def run_quality_gates(
    commands: list[str], *, mode: GateRunMode = GateRunMode.FAIL_FAST, cwd: Path | None = None, timeout: float = 300.0
) -> GateResult:
    """Execute a list of gate command strings and return an aggregate result.

    Each command string is tokenised with shlex.split, resolved via shutil.which,
    and executed via subprocess.run with captured output. No shell=True is used.

    When a command executable is not found on PATH, a CommandResult with
    exit_code=127 and passed=False is recorded — no exception is raised — and
    mode logic applies as normal.

    When a command exceeds the timeout, subprocess.TimeoutExpired is caught (not
    propagated) and converted to a CommandResult with exit_code=124 and
    passed=False, following the Unix timeout(1) convention. Mode logic applies as
    normal.

    OSError raised by subprocess.run after a successful which() lookup propagates
    to the caller; that indicates a runtime environment failure, not a gate check
    failure.

    Args:
        commands: List of shell-style command strings to execute in order.
        mode: GateRunMode.FAIL_FAST stops after the first failing command.
            GateRunMode.RUN_ALL collects all results regardless of failure.
        cwd: Working directory for subprocess execution. None inherits the
            current process working directory.
        timeout: Per-command timeout in seconds. Default 300.0. When a command
            exceeds this limit, subprocess.run raises TimeoutExpired, which is
            caught and recorded as exit_code=124.

    Returns:
        GateResult with passed=True iff every CommandResult.passed is True,
        plus the list of CommandResult values collected under the given mode.
    """
    results: list[CommandResult] = []

    for command in commands:
        tokens = shlex.split(command)
        executable = _resolve_executable(tokens[0])

        if executable is None:
            result = CommandResult(command=command, exit_code=127, stdout="", stderr=f"command not found: {tokens[0]}")
        else:
            resolved_tokens = [executable, *tokens[1:]]
            try:
                completed = subprocess.run(
                    resolved_tokens, capture_output=True, text=True, cwd=cwd, check=False, timeout=timeout
                )
                result = CommandResult(
                    command=command, exit_code=completed.returncode, stdout=completed.stdout, stderr=completed.stderr
                )
            except subprocess.TimeoutExpired:
                result = CommandResult(
                    command=command,
                    exit_code=124,
                    stdout="",
                    stderr=f"command timed out after {timeout:.0f}s: {command}",
                )

        results.append(result)

        if mode is GateRunMode.FAIL_FAST and not result.passed:
            break

    return GateResult(passed=all(r.passed for r in results), results=results, mode=mode)
