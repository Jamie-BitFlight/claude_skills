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
import subprocess
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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
