#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
#   "pytest",
#   "pytest-asyncio",
#   "pytest-cov",
#   "pytest-mock",
#   "pytest-xdist",
#   "typer",
# ]
# [tool.ty.environment]
# root = ["."]
# ///
"""Tests for bounded provider subprocess execution."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import pr_review_subprocess

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_run_capture_applies_default_bound_and_isolates_process_group(mocker: MockerFixture) -> None:
    process = mocker.Mock(returncode=0)
    process.communicate.return_value = ("output", "")
    popen = mocker.patch.object(pr_review_subprocess.subprocess, "Popen", return_value=process)

    result = pr_review_subprocess.run_capture(["gh", "api", "user"])

    assert result == "output"
    process.communicate.assert_called_once_with(timeout=30.0)
    assert popen.call_args.kwargs["start_new_session"] is (os.name == "posix")


def test_run_capture_terminates_process_tree_before_raising_timeout(mocker: MockerFixture) -> None:
    process = mocker.Mock()
    process.communicate.side_effect = subprocess.TimeoutExpired(["gh"], 5)
    mocker.patch.object(pr_review_subprocess.subprocess, "Popen", return_value=process)
    terminate = mocker.patch.object(pr_review_subprocess, "terminate_process_tree")

    with pytest.raises(subprocess.TimeoutExpired):
        pr_review_subprocess.run_capture(["gh", "api", "user"], timeout=5)

    terminate.assert_called_once_with(process)


def test_terminate_windows_process_tree_uses_taskkill_for_descendants(mocker: MockerFixture) -> None:
    process = mocker.Mock(pid=4312)
    taskkill = mocker.patch.object(pr_review_subprocess.shutil, "which", return_value="C:/Windows/taskkill.exe")
    run = mocker.patch.object(pr_review_subprocess.subprocess, "run")

    pr_review_subprocess.terminate_windows_process_tree(process)

    taskkill.assert_called_once_with("taskkill")
    run.assert_called_once_with(
        ["C:/Windows/taskkill.exe", "/PID", "4312", "/T", "/F"],
        check=False,
        timeout=pr_review_subprocess.TERMINATION_GRACE_SECONDS,
    )


@pytest.mark.skipif(os.name != "posix", reason="POSIX process groups are unavailable")
def test_timeout_removes_a_live_descendant_process_group(tmp_path: Path) -> None:
    ready_file = tmp_path / "descendant-ready"
    child = (
        "import os, signal, time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"open({str(ready_file)!r}, 'w').write(f'{{os.getpid()}} {{os.getpgrp()}}'); "
        "time.sleep(30)"
    )
    parent = f"import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', {child!r}]); time.sleep(30)"

    with pytest.raises(subprocess.TimeoutExpired):
        pr_review_subprocess.run_capture([sys.executable, "-c", parent], timeout=1)

    descendant_pid, process_group_id = map(int, ready_file.read_text().split())
    deadline = time.monotonic() + 3
    while pr_review_subprocess.process_group_is_alive(process_group_id) and time.monotonic() < deadline:
        time.sleep(0.01)

    assert not pr_review_subprocess.process_group_is_alive(process_group_id)
    with pytest.raises(ProcessLookupError):
        os.kill(descendant_pid, signal.SIGCONT)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
