"""Tests for ``scripts/script_utils.py``, focused on ``run_gh_json`` error handling."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import script_utils

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_run_gh_json_raises_when_gh_not_on_path(mocker: MockerFixture) -> None:
    """A missing ``gh`` executable is reported before any subprocess is spawned."""
    mocker.patch.object(script_utils, "which", return_value=None)
    run = mocker.patch.object(script_utils.subprocess, "run")

    with pytest.raises(RuntimeError, match="not found on PATH"):
        script_utils.run_gh_json(["api", "repos/example/example"])

    run.assert_not_called()


def test_run_gh_json_raises_on_timeout(mocker: MockerFixture) -> None:
    """A hung ``gh`` invocation is converted into a ``RuntimeError`` naming the timeout."""
    mocker.patch.object(script_utils, "which", return_value="/usr/local/bin/gh")
    mocker.patch.object(script_utils.subprocess, "run", side_effect=subprocess.TimeoutExpired(cmd=["gh"], timeout=5))

    with pytest.raises(RuntimeError, match=r"did not complete within 5(\.0)?s"):
        script_utils.run_gh_json(["api", "repos/example/example"], timeout=5)


def test_run_gh_json_raises_on_nonzero_exit(mocker: MockerFixture) -> None:
    """A non-zero ``gh`` exit status surfaces its stderr text as the error."""
    mocker.patch.object(script_utils, "which", return_value="/usr/local/bin/gh")
    mocker.patch.object(
        script_utils.subprocess,
        "run",
        return_value=subprocess.CompletedProcess(args=["gh"], returncode=1, stdout="", stderr="HTTP 404: Not Found\n"),
    )

    with pytest.raises(RuntimeError, match="HTTP 404: Not Found"):
        script_utils.run_gh_json(["api", "repos/example/missing"])


def test_run_gh_json_raises_on_nonzero_exit_without_stderr(mocker: MockerFixture) -> None:
    """A non-zero exit with no stderr text falls back to the exit code in the message."""
    mocker.patch.object(script_utils, "which", return_value="/usr/local/bin/gh")
    mocker.patch.object(
        script_utils.subprocess,
        "run",
        return_value=subprocess.CompletedProcess(args=["gh"], returncode=7, stdout="", stderr=""),
    )

    with pytest.raises(RuntimeError, match="gh exited with 7"):
        script_utils.run_gh_json(["api", "repos/example/missing"])


def test_run_gh_json_raises_on_invalid_json(mocker: MockerFixture) -> None:
    """Non-JSON stdout from an otherwise successful ``gh`` call is rejected explicitly."""
    mocker.patch.object(script_utils, "which", return_value="/usr/local/bin/gh")
    mocker.patch.object(
        script_utils.subprocess,
        "run",
        return_value=subprocess.CompletedProcess(args=["gh"], returncode=0, stdout="not json", stderr=""),
    )

    with pytest.raises(RuntimeError, match="invalid JSON"):
        script_utils.run_gh_json(["api", "repos/example/example"])


def test_run_gh_json_returns_parsed_payload_on_success(mocker: MockerFixture) -> None:
    """A clean zero-exit ``gh`` call with valid JSON stdout returns the decoded object."""
    mocker.patch.object(script_utils, "which", return_value="/usr/local/bin/gh")
    mocker.patch.object(
        script_utils.subprocess,
        "run",
        return_value=subprocess.CompletedProcess(args=["gh"], returncode=0, stdout='{"total_count": 3}', stderr=""),
    )

    result = script_utils.run_gh_json(["api", "repos/example/example"])

    assert result == {"total_count": 3}


def test_title_case_from_kebab_converts_and_strips_empty_segments() -> None:
    """Kebab-case identifiers become title-cased display names, ignoring empty segments."""
    assert script_utils.title_case_from_kebab("cross-harness--mcp") == "Cross Harness Mcp"
