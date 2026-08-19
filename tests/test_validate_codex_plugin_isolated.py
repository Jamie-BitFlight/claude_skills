"""Regression tests for isolated Codex plugin validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import validate_codex_plugin_isolated as validator


@pytest.mark.parametrize(
    ("arguments", "expected_message"),
    [
        (("--package-only",), "--package-only requires --run"),
        (
            ("--package-only", "--run", "--copy-auth-from-current-home"),
            "--package-only cannot be combined with --copy-auth-from-current-home",
        ),
    ],
)
def test_package_only_rejects_incompatible_arguments(arguments: tuple[str, ...], expected_message: str) -> None:
    """Package-only mode rejects dry runs and temporary auth copying."""
    args = validator.create_parser().parse_args(arguments)

    with pytest.raises(validator.HarnessError, match=expected_message):
        validator.validate_args(args)


def test_package_only_run_skips_exec_stage(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Package-only mode registers and installs the plugin without invoking a model."""
    commands: list[list[str]] = []

    def fake_run_command(argv: list[str], *, cwd: Path, env: dict[str, str], label: str) -> None:
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
        commands = validator.build_command_strings(workspace, "test prompt", Path("/tmp/output.txt"), "")

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
        commands = validator.build_command_strings(workspace, "test prompt", Path("/tmp/output.txt"), "")

        assert workspace.plugin_id == "xdg-base-directory"
        assert entry["name"] == "xdg-base-directory"
        assert entry["source"]["path"] == "./plugins/xdg-base-directory"
        expected_install = "codex plugin add xdg-base-directory@isolated-codex-plugin-validation"
        assert expected_install in commands[1]
    finally:
        validator.cleanup_workspace(workspace)


def test_relative_output_file_is_resolved_before_temp_project_cwd() -> None:
    output_file = validator._resolve_output_file(Path("reports/smoke.txt"), "plugin")

    assert output_file == (Path.cwd() / "reports/smoke.txt").resolve()


def test_git_project_fixture_creates_repository() -> None:
    workspace = validator.create_temp_workspace("development-harness")
    try:
        validator._initialize_git_project(workspace)

        assert (workspace.project_dir / ".git").is_dir()
    finally:
        validator.cleanup_workspace(workspace)


# ---------------------------------------------------------------------------
# copy_auth_from_current_home
# ---------------------------------------------------------------------------


def test_copy_auth_from_current_home_copies_only_auth_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Only auth.json is copied from a realistic Codex home; sibling files are left behind."""
    fake_home = tmp_path / "fake-codex-home"
    fake_home.mkdir()
    (fake_home / "auth.json").write_text('{"token": "secret"}', encoding="utf-8")
    (fake_home / "config.toml").write_text('model = "gpt"\n', encoding="utf-8")
    history_dir = fake_home / "history"
    history_dir.mkdir()
    (history_dir / "session.jsonl").write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("CODEX_HOME", str(fake_home))

    workspace = validator.create_temp_workspace("development-harness")
    try:
        copied = validator.copy_auth_from_current_home(workspace)

        assert copied == workspace.codex_home / "auth.json"
        assert copied.read_text(encoding="utf-8") == '{"token": "secret"}'
        assert (copied.stat().st_mode & 0o777) == 0o600
        assert [entry.name for entry in workspace.codex_home.iterdir()] == ["auth.json"]
    finally:
        validator.cleanup_workspace(workspace)


def test_copy_auth_from_current_home_missing_auth_raises_harness_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A source Codex home without auth.json raises an actionable HarnessError."""
    fake_home = tmp_path / "fake-codex-home-empty"
    fake_home.mkdir()
    monkeypatch.setenv("CODEX_HOME", str(fake_home))

    workspace = validator.create_temp_workspace("development-harness")
    try:
        with pytest.raises(validator.HarnessError, match="does not exist"):
            validator.copy_auth_from_current_home(workspace)
    finally:
        validator.cleanup_workspace(workspace)


# ---------------------------------------------------------------------------
# create_temp_workspace — symlink-escape guard
# ---------------------------------------------------------------------------


def test_create_temp_workspace_rejects_plugin_with_escaping_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A plugin tree containing a symlink pointing outside its own directory is rejected."""
    plugins_root = tmp_path / "plugins"
    plugin_dir = plugins_root / "escaping-plugin"
    (plugin_dir / ".codex-plugin").mkdir(parents=True)
    (plugin_dir / ".codex-plugin" / "plugin.json").write_text(json.dumps({"name": "escaping-plugin"}), encoding="utf-8")
    outside_target = tmp_path / "outside-target"
    outside_target.mkdir()
    (plugin_dir / "escape").symlink_to(outside_target)
    monkeypatch.setattr(validator, "PLUGINS_ROOT", plugins_root)

    with pytest.raises(validator.HarnessError, match="symlink outside its distribution"):
        validator.create_temp_workspace("escaping-plugin")


def test_create_temp_workspace_allows_symlink_within_plugin_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A symlink that stays inside its own plugin directory is not rejected.

    ``shutil.copytree`` dereferences symlinks into regular files by default
    (no ``symlinks=True``), so the copied tree has no symlink to inspect —
    this test only asserts the guard itself does not raise for an in-tree
    symlink, and that the pointed-to content survives the copy.
    """
    plugins_root = tmp_path / "plugins"
    plugin_dir = plugins_root / "internal-symlink-plugin"
    (plugin_dir / ".codex-plugin").mkdir(parents=True)
    (plugin_dir / ".codex-plugin" / "plugin.json").write_text(
        json.dumps({"name": "internal-symlink-plugin"}), encoding="utf-8"
    )
    real_file = plugin_dir / "real.txt"
    real_file.write_text("content", encoding="utf-8")
    (plugin_dir / "alias.txt").symlink_to(real_file)
    monkeypatch.setattr(validator, "PLUGINS_ROOT", plugins_root)

    workspace = validator.create_temp_workspace("internal-symlink-plugin")
    try:
        assert (workspace.plugin_dir / "alias.txt").read_text(encoding="utf-8") == "content"
    finally:
        validator.cleanup_workspace(workspace)


# ---------------------------------------------------------------------------
# main() — malformed JSON handling
# ---------------------------------------------------------------------------


def test_main_reports_clean_error_for_malformed_plugin_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Malformed JSON in a plugin manifest surfaces a clean error, not a raw traceback."""
    plugins_root = tmp_path / "plugins"
    plugin_dir = plugins_root / "broken-plugin"
    (plugin_dir / ".codex-plugin").mkdir(parents=True)
    (plugin_dir / ".codex-plugin" / "plugin.json").write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(validator, "PLUGINS_ROOT", plugins_root)
    monkeypatch.setattr(
        sys, "argv", ["validate_codex_plugin_isolated.py", "--distribution-mode", "copy", "--plugin", "broken-plugin"]
    )

    exit_code = validator.main()

    assert exit_code == 1
    assert capsys.readouterr().err.startswith("error:")
