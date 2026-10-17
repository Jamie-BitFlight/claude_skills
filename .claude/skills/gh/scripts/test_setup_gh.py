#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.21.0",
#   "httpx>=0.28.1",
#   "ruamel.yaml>=0.18.0",
#   "pytest>=9.1.1",
# ]
#
# [tool.ty.environment]
# extra-paths = ["."]
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


def test_configure_repo_dry_run_does_not_write_when_gh_is_current(runner: CliRunner) -> None:
    """--configure-repo --dry-run must not persist config on the up-to-date branch."""
    with (
        patch.object(setup_gh.shutil, "which", return_value="/usr/bin/gh"),
        patch.object(setup_gh, "get_installed_version", return_value="9.0.0"),
        patch.object(setup_gh, "detect_platform", return_value=("linux", "amd64")),
        patch.object(setup_gh, "find_install_dir", return_value=setup_gh.Path("/tmp/bin")),
        patch.object(setup_gh, "resolve_release", return_value=("v1.0.0", object(), "checksum")),
        patch.object(setup_gh, "_configure_repo_if_requested") as configure,
    ):
        result = runner.invoke(app, ["--configure-repo", "--dry-run"])

    assert result.exit_code == 0, result.output
    configure.assert_not_called()
