"""Regression tests for isolated Codex plugin validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import validate_codex_plugin_isolated as validator


@pytest.mark.parametrize(
    "arguments, expected_message",
    [
        (("--package-only",), "--package-only requires --run"),
        (
            ("--package-only", "--run", "--copy-auth-from-current-home"),
            "--package-only cannot be combined with --copy-auth-from-current-home",
        ),
    ],
)
def test_package_only_rejects_incompatible_arguments(
    arguments: tuple[str, ...], expected_message: str
) -> None:
    """Package-only mode rejects dry runs and temporary auth copying."""
    args = validator.create_parser().parse_args(arguments)

    with pytest.raises(validator.HarnessError, match=expected_message):
        validator.validate_args(args)


def test_package_only_run_skips_exec_stage(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Package-only mode registers and installs the plugin without invoking a model."""
    commands: list[list[str]] = []

    def fake_run_command(
        argv: list[str], *, cwd: Path, env: dict[str, str], label: str
    ) -> None:
        del cwd, env
        commands.append(argv)
        assert label in {"marketplace", "install"}

    monkeypatch.setattr(validator, "run_command", fake_run_command)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_codex_plugin_isolated.py",
            "--distribution-mode",
            "copy",
            "--zip-unzip",
            "--run",
            "--package-only",
            "--plugin",
            "development-harness",
        ],
    )

    assert validator.main() == 0

    assert [command[1:4] for command in commands] == [
        ["plugin", "marketplace", "add"],
        ["plugin", "add", "dh@isolated-codex-plugin-validation"],
    ]
    assert all("exec" not in command for command in commands)
    assert "Package-only validation complete" in capsys.readouterr().out


def test_copy_distribution_uses_manifest_id_for_development_harness() -> None:
    """Copy mode separates a plugin manifest ID from its source directory name."""
    workspace = validator.create_temp_workspace("development-harness")
    try:
        marketplace = json.loads(workspace.marketplace_path.read_text(encoding="utf-8"))
        entry = marketplace["plugins"][0]
        commands = validator.build_command_strings(
            workspace,
            "test prompt",
            Path("/tmp/output.txt"),
            "",
        )

        assert workspace.plugin_id == "dh"
        assert entry["name"] == "dh"
        assert entry["source"]["path"] == "./plugins/development-harness"
        assert "codex plugin add dh@isolated-codex-plugin-validation" in commands[1]
    finally:
        validator.cleanup_workspace(workspace)


def test_copy_distribution_preserves_same_name_plugin_behavior() -> None:
    """Copy mode keeps the existing selector when directory and manifest names match."""
    workspace = validator.create_temp_workspace("xdg-base-directory")
    try:
        marketplace = json.loads(workspace.marketplace_path.read_text(encoding="utf-8"))
        entry = marketplace["plugins"][0]
        commands = validator.build_command_strings(
            workspace,
            "test prompt",
            Path("/tmp/output.txt"),
            "",
        )

        assert workspace.plugin_id == "xdg-base-directory"
        assert entry["name"] == "xdg-base-directory"
        assert entry["source"]["path"] == "./plugins/xdg-base-directory"
        assert "codex plugin add xdg-base-directory@isolated-codex-plugin-validation" in commands[1]
    finally:
        validator.cleanup_workspace(workspace)
