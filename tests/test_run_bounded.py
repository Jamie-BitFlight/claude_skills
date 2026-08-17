"""Behavioral tests for the bounded subprocess runner."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from scripts import run_bounded

RUNNER = Path(__file__).parents[1] / "scripts" / "run_bounded.py"


def run_runner(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Invoke the standalone runner under the current test interpreter."""
    return subprocess.run([sys.executable, str(RUNNER), *arguments], capture_output=True, check=False, text=True)


def test_runner_relays_a_successful_childs_output_and_status() -> None:
    """A completed command retains its stdout and exit status."""
    result = run_runner("--timeout-seconds", "1", "--", sys.executable, "-c", "print('bounded-success')")

    assert result.returncode == 0
    assert result.stdout == "bounded-success\n"
    assert result.stderr == ""


def test_runner_times_out_and_returns_the_timeout_status() -> None:
    """A hung command is terminated instead of inheriting an unbounded wait."""
    start = time.monotonic()
    result = run_runner("--timeout-seconds", "0.1", "--", sys.executable, "-c", "import time; time.sleep(30)")
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
    result = run_runner("--timeout-seconds", "0.1", "--", sys.executable, "-c", child_program)
    elapsed = time.monotonic() - start

    assert result.returncode == 124
    assert elapsed < 3


@pytest.mark.skipif(os.name != "posix", reason="process-group SIGKILL escalation is POSIX-only")
def test_runner_reaps_a_descendant_that_ignores_sigterm(tmp_path: Path) -> None:
    """A descendant that survives the leader's SIGTERM is still reaped via group SIGKILL.

    Regression test for the gap where ``terminate_process_tree`` trusted the leader's
    ``wait()`` outcome: if the leader dies from the default SIGTERM action while a
    descendant traps and ignores SIGTERM, the leader's ``wait()`` returns before the
    process group is actually empty, and the old code returned without ever escalating
    to SIGKILL. The descendant inherits this runner's stdout/stderr pipes, so an
    un-reaped descendant is observable as ``run_runner`` blocking until the descendant's
    sleep elapses on its own, rather than returning within the grace period — confirmed
    by running this exact assertion against the pre-fix implementation, where it
    consistently takes ~5s (the descendant's full sleep) instead of failing outright.

    The descendant writes a readiness marker only after installing its SIGTERM handler,
    and the leader waits for that marker before its own sleep, so the runner's short
    timeout cannot fire before the descendant is actually ignoring SIGTERM — without
    this rendezvous, a fast timeout can race the descendant's signal-handler
    installation and mask the regression.
    """
    ready_file = tmp_path / "descendant.ready"
    descendant_program = (
        "import signal, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        f"open({str(ready_file)!r}, 'w').close()\n"
        "time.sleep(5)\n"
    )
    leader_program = (
        "import os, subprocess, sys, time\n"
        f"subprocess.Popen([sys.executable, '-c', {descendant_program!r}])\n"
        f"ready_file = {str(ready_file)!r}\n"
        "while not os.path.exists(ready_file): time.sleep(0.01)\n"
        "time.sleep(5)\n"
    )

    start = time.monotonic()
    result = run_runner("--timeout-seconds", "1", "--", sys.executable, "-c", leader_program)
    elapsed = time.monotonic() - start

    assert result.returncode == 124
    assert elapsed < 3


def test_runner_uses_taskkill_to_terminate_the_windows_process_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows timeout cleanup terminates descendants as well as the direct child."""
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert check is False
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(run_bounded.subprocess, "run", fake_run)

    run_bounded.terminate_windows_process_tree(4242)

    assert commands == [["taskkill", "/PID", "4242", "/T", "/F"]]
