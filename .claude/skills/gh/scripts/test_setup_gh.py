#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.21.0",
#   "httpx>=0.28.1",
#   "ruamel.yaml>=0.18.0",
# ]
# ///
"""Tests for setup_gh.py — verifies --detect-only exit codes."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

import setup_gh
from setup_gh import app


@pytest.fixture
def runner() -> CliRunner:
    """Provide a Typer CliRunner for invoke calls."""
    return CliRunner()


class TestDetectOnlyExitCodes:
    """--detect-only exits 0 on full success and 1 on any partial failure."""

    def test_detect_only_success(self, runner: CliRunner) -> None:
        """Exit 0 when detection returns a valid slug and template renders successfully.

        Both _apply_repo_detection and _render_template succeed — the full
        happy path through _run_detect_only returns True, so the CLI raises
        typer.Exit(code=0).
        """
        with (
            patch.object(setup_gh, "_apply_repo_detection", return_value="owner/repo"),
            patch.object(setup_gh, "_render_template", return_value="gh -R owner/repo issue list"),
        ):
            result = runner.invoke(app, ["--detect-only"])

        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}. Output:\n{result.output}"

    def test_detect_only_failure_no_detection(self, runner: CliRunner) -> None:
        """Exit 1 when _apply_repo_detection returns None (no git remote detected).

        _run_detect_only returns False when owner/repo cannot be determined,
        so the CLI raises typer.Exit(code=1).
        """
        with patch.object(setup_gh, "_apply_repo_detection", return_value=None):
            result = runner.invoke(app, ["--detect-only"])

        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}. Output:\n{result.output}"

    def test_detect_only_failure_no_template(self, runner: CliRunner) -> None:
        """Exit 1 when detection succeeds but the template file is missing.

        _apply_repo_detection returns a valid slug, but _render_template
        returns None (template not found) — _run_detect_only returns False,
        so the CLI raises typer.Exit(code=1).
        """
        with (
            patch.object(setup_gh, "_apply_repo_detection", return_value="owner/repo"),
            patch.object(setup_gh, "_render_template", return_value=None),
        ):
            result = runner.invoke(app, ["--detect-only"])

        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}. Output:\n{result.output}"
