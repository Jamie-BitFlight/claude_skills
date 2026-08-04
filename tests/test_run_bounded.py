"""Behavioral tests for the bounded subprocess runner."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


RUNNER = Path(__file__).parents[1] / "scripts" / "run_bounded.py"


def run_runner(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Invoke the standalone runner under the current test interpreter."""
    return subprocess.run(
        [sys.executable, str(RUNNER), *arguments],
        capture_output=True,
        check=False,
        text=True,
    )


def test_runner_relays_a_successful_childs_output_and_status() -> None:
    """A completed command retains its stdout and exit status."""
    result = run_runner(
        "--timeout-seconds",
        "1",
        "--",
        sys.executable,
        "-c",
        "print('bounded-success')",
    )

    assert result.returncode == 0
    assert result.stdout == "bounded-success\n"
    assert result.stderr == ""


def test_runner_times_out_and_returns_the_timeout_status() -> None:
    """A hung command is terminated instead of inheriting an unbounded wait."""
    start = time.monotonic()
    result = run_runner(
        "--timeout-seconds",
        "0.1",
        "--",
        sys.executable,
        "-c",
        "import time; time.sleep(30)",
    )
    elapsed = time.monotonic() - start

    assert result.returncode == 124
    assert elapsed < 3
    assert "timed out after 0.1 seconds" in result.stderr


def test_runner_timeout_terminates_a_sleeping_grandchild() -> None:
    """Timeout cleanup reaches descendants that inherit the child process group."""
    child_program = (
        "import subprocess, sys, time; "
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
        "time.sleep(30)"
    )
    start = time.monotonic()
    result = run_runner(
        "--timeout-seconds",
        "0.1",
        "--",
        sys.executable,
        "-c",
        child_program,
    )
    elapsed = time.monotonic() - start

    assert result.returncode == 124
    assert elapsed < 3
