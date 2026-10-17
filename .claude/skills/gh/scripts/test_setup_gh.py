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

from pathlib import Path
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


def test_configure_repo_persists_config_without_release_lookup_when_gh_is_installed(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit local configuration does not depend on release metadata."""
    config_path = tmp_path / ".dh" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text("backend:\n  name: github\ncustom: preserved\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPO", "octo/example")

    with (
        patch.object(setup_gh.shutil, "which", return_value="/isolated/bin/gh"),
        patch.object(setup_gh, "get_installed_version", return_value="9.0.0"),
        patch.object(setup_gh, "resolve_release", side_effect=AssertionError("release lookup must not run")),
        patch.object(setup_gh, "detect_platform", side_effect=AssertionError("platform detection must not run")),
    ):
        result = runner.invoke(app, ["--configure-repo"])

    assert result.exit_code == 0, result.output
    config = config_path.read_text(encoding="utf-8")
    assert "name: github" in config
    assert "custom: preserved" in config
    assert "repo: octo/example" in config


def test_configure_repo_fails_without_detectable_repository(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Installed configuration refuses success when no repository can be detected."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_REPO", raising=False)

    with (
        patch.object(setup_gh.shutil, "which", return_value="/isolated/bin/gh"),
        patch.object(setup_gh, "get_installed_version", return_value="9.0.0"),
        patch.object(setup_gh, "resolve_release", side_effect=AssertionError("release lookup must not run")),
        patch.object(setup_gh, "detect_platform", side_effect=AssertionError("platform detection must not run")),
    ):
        result = runner.invoke(app, ["--configure-repo"])

    assert result.exit_code == 1, result.output
    assert not (tmp_path / ".dh" / "config.yaml").exists()
    assert "Configured repository for installed gh" not in result.output


def test_configure_repo_fails_when_configuration_cannot_be_persisted(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Installed configuration refuses success when the target cannot be written."""
    config_parent = tmp_path / ".dh"
    config_parent.write_text("not a directory", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPO", "octo/example")

    with (
        patch.object(setup_gh.shutil, "which", return_value="/isolated/bin/gh"),
        patch.object(setup_gh, "get_installed_version", return_value="9.0.0"),
        patch.object(setup_gh, "resolve_release", side_effect=AssertionError("release lookup must not run")),
        patch.object(setup_gh, "detect_platform", side_effect=AssertionError("platform detection must not run")),
    ):
        result = runner.invoke(app, ["--configure-repo"])

    assert result.exit_code == 1, result.output
    assert config_parent.read_text(encoding="utf-8") == "not a directory"
    assert "Configured repository for installed gh" not in result.output


def test_configure_repo_dry_run_leaves_existing_config_unchanged(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dry-run remains non-mutating even when a repository can be detected."""
    config_path = tmp_path / ".dh" / "config.yaml"
    config_path.parent.mkdir()
    before = "backend:\n  name: github\ncustom: preserved\n"
    config_path.write_text(before, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPO", "octo/example")
    asset = setup_gh.ReleaseAsset(name="gh.tar.gz", url="https://example.invalid/gh.tar.gz", size=1)

    with (
        patch.object(setup_gh.shutil, "which", return_value="/isolated/bin/gh"),
        patch.object(setup_gh, "get_installed_version", return_value="9.0.0"),
        patch.object(setup_gh, "detect_platform", return_value=("linux", "amd64")),
        patch.object(setup_gh, "find_install_dir", return_value=tmp_path / "bin"),
        patch.object(setup_gh, "resolve_release", return_value=("v1.0.0", asset, "checksum")),
    ):
        result = runner.invoke(app, ["--configure-repo", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert config_path.read_text(encoding="utf-8") == before
