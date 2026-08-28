"""Behavioral tests for the bounded subprocess runner."""

from __future__ import annotations

import multiprocessing
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


def _run_pytest_helper(helper_path: str, timeout_seconds: float) -> None:
    raise SystemExit(run_bounded.run_command([helper_path], timeout_seconds))


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


@pytest.mark.parametrize(
    "pytest_arguments",
    [
        ("-n", "3"),
        ("-n99",),
        ("--numprocesses", "3"),
        ("--numprocesses=99",),
        ("-n", "auto"),
        ("-n",),
        ("-n", "2", "--numprocesses", "2"),
    ],
)
def test_runner_rejects_unsafe_pytest_worker_options(pytest_arguments: tuple[str, ...]) -> None:
    result = run_runner("--timeout-seconds", "1", "--", "uv", "run", "pytest", *pytest_arguments)

    assert result.returncode == 2
    assert "pytest worker count" in result.stderr


@pytest.mark.skipif(os.name != "posix", reason="pytest locking is supported on POSIX hosts")
def test_runner_serializes_concurrent_pytest_helpers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    start_file = tmp_path / "starts.txt"
    helper = tmp_path / "pytest"
    helper.write_text(
        f"#!{sys.executable}\n"
        "import os\n"
        "import time\n"
        "from pathlib import Path\n\n"
        "with Path(os.environ['PYTEST_LOCK_START_FILE']).open('a') as start_log:\n"
        "    start_log.write(f'{time.monotonic()}\\n')\n"
        "time.sleep(0.5)\n"
    )
    helper.chmod(0o700)
    monkeypatch.setattr(run_bounded, "PYTEST_LOCK_PATH", tmp_path / "pytest.lock")
    monkeypatch.setenv("PYTEST_LOCK_START_FILE", str(start_file))
    context = multiprocessing.get_context("fork")
    first = context.Process(target=_run_pytest_helper, args=(str(helper), 10))
    try:
        first.start()
        for _ in range(100):
            if start_file.exists():
                break
            time.sleep(0.01)
        second = context.Process(target=_run_pytest_helper, args=(str(helper), 10))
        try:
            second.start()
            first.join(timeout=15)
            second.join(timeout=15)
        finally:
            if second.is_alive():
                second.terminate()
                second.join()
    finally:
        if first.is_alive():
            first.terminate()
            first.join()

    assert first.exitcode == 0
    assert second.exitcode == 0
    starts = sorted(float(value) for value in start_file.read_text().splitlines())
    assert len(starts) == 2
    assert starts[1] - starts[0] >= 0.3


@pytest.mark.skipif(os.name != "posix", reason="pytest locking is supported on POSIX hosts")
def test_runner_timeout_includes_pytest_lock_wait(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    start_file = tmp_path / "starts.txt"
    helper = tmp_path / "pytest"
    helper.write_text(
        f"#!{sys.executable}\n"
        "import os\n"
        "import time\n"
        "from pathlib import Path\n\n"
        "Path(os.environ['PYTEST_LOCK_START_FILE']).touch()\n"
        "time.sleep(0.5)\n"
    )
    helper.chmod(0o700)
    monkeypatch.setattr(run_bounded, "PYTEST_LOCK_PATH", tmp_path / "pytest.lock")
    monkeypatch.setenv("PYTEST_LOCK_START_FILE", str(start_file))
    holder = multiprocessing.get_context("fork").Process(target=_run_pytest_helper, args=(str(helper), 10))
    try:
        holder.start()
        for _ in range(100):
            if start_file.exists():
                break
            time.sleep(0.01)
        start = time.monotonic()
        exit_code = run_bounded.run_command([str(helper)], 0.1)
        elapsed = time.monotonic() - start
    finally:
        if holder.is_alive():
            holder.terminate()
            holder.join()

    assert exit_code == 124
    assert elapsed < 0.3


@pytest.mark.skipif(os.name != "posix", reason="pytest locking is supported on POSIX hosts")
def test_runner_refuses_a_symlinked_pytest_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "target"
    lock_path = tmp_path / "pytest.lock"
    lock_path.symlink_to(target)
    monkeypatch.setattr(run_bounded, "PYTEST_LOCK_PATH", lock_path)

    with pytest.raises(OSError, match="Too many levels of symbolic links"):
        run_bounded.run_command([str(tmp_path / "pytest")], 1)


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
