"""Workflow-level regression tests for scripts/sync_codex_plugin_manifests.py.

These tests run the sync logic end to end against realistic plugin directories built under
``tmp_path`` — copying the actual on-disk shape (a Claude source manifest plus a pre-existing
Codex manifest, since ``sync_manifest`` only updates an existing file and never bootstraps one)
rather than unit-testing internal helpers in isolation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import sync_codex_plugin_manifests as sync_module

LONG_DESCRIPTION = "Widget synchronization tooling for the test suite. " * 6


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _build_plugin_dir(root: Path, name: str, *, description: str, mcp_servers: dict | None) -> Path:
    """Build a realistic plugin directory: Claude source manifest plus a seeded Codex manifest.

    Returns:
        The created plugin directory.
    """
    plugin_dir = root / name
    (plugin_dir / "skills" / "example-skill").mkdir(parents=True)
    (plugin_dir / "commands").mkdir()

    claude_manifest: dict = {
        "name": name,
        "description": description,
        "version": "1.0.0",
        "author": {"name": "Test Author"},
    }
    if mcp_servers is not None:
        claude_manifest["mcpServers"] = mcp_servers
    _write_json(plugin_dir / ".claude-plugin" / "plugin.json", claude_manifest)

    # Every committed plugin already ships a .codex-plugin/plugin.json with its own copy of
    # "description"/"author" — sync_manifest() only updates an existing file, it never creates
    # one from scratch, and it reads "description"/"author" off *this* file, not the Claude
    # source manifest (the two are kept in sync by hand when the Claude manifest changes).
    _write_json(
        plugin_dir / ".codex-plugin" / "plugin.json",
        {"name": name, "version": "0.0.0", "description": description, "author": {"name": "Test Author"}},
    )
    return plugin_dir


def test_sync_workflow_derives_manifest_and_mcp_file_from_realistic_plugin_directory(tmp_path: Path) -> None:
    """End-to-end sync produces a valid, correctly-derived Codex manifest and MCP file."""
    plugin_dir = _build_plugin_dir(
        tmp_path,
        "widget-tools",
        description=LONG_DESCRIPTION,
        mcp_servers={
            "widget-server": {
                "command": "uv",
                "args": ["run", "--script", "${CLAUDE_PLUGIN_ROOT}/scripts/run_server.py"],
            }
        },
    )

    mcp_changed = sync_module.sync_mcp_file(plugin_dir)
    manifest_changed = sync_module.sync_manifest(plugin_dir)

    assert mcp_changed is True
    assert manifest_changed is True

    mcp_config = json.loads((plugin_dir / ".mcp.json").read_text(encoding="utf-8"))
    assert mcp_config == {
        "mcpServers": {
            "widget-server": {"command": "uv", "args": ["run", "--script", "scripts/run_server.py"], "cwd": "."}
        }
    }

    manifest = json.loads((plugin_dir / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["skills"] == "./skills/"
    assert manifest["mcpServers"] == "./.mcp.json"

    interface = manifest["interface"]
    assert interface["displayName"] == "Widget Tools"
    assert interface["longDescription"] == LONG_DESCRIPTION
    assert len(interface["shortDescription"]) <= sync_module.SHORT_DESCRIPTION_LIMIT
    assert interface["shortDescription"].endswith("...")
    assert interface["developerName"] == "Test Author"
    assert interface["category"] == "Developer Tools"
    assert set(interface["capabilities"]) == {"Interactive", "Read", "Write"}


def test_rerunning_sync_is_idempotent(tmp_path: Path) -> None:
    """A second sync pass over an already-synced plugin reports no further change."""
    plugin_dir = _build_plugin_dir(tmp_path, "widget-tools", description="Widgets.", mcp_servers=None)

    sync_module.sync_manifest(plugin_dir)
    second_pass_changed = sync_module.sync_manifest(plugin_dir)

    assert second_pass_changed is False


def test_sync_mcp_file_rejects_placeholder_codex_cannot_expand(tmp_path: Path) -> None:
    """A Claude-only placeholder with no Codex expansion fails sync instead of copying verbatim."""
    plugin_dir = _build_plugin_dir(
        tmp_path,
        "widget-tools",
        description="Widgets.",
        mcp_servers={
            "widget-server": {
                "command": "uv",
                "args": ["run", "--script", "scripts/run_server.py"],
                "env": {"PROJECT_DIR": "${CLAUDE_PROJECT_DIR}"},
            }
        },
    )

    with pytest.raises(sync_module.UnexpandablePlaceholderError, match=r"CLAUDE_PROJECT_DIR"):
        sync_module.sync_mcp_file(plugin_dir)

    assert not (plugin_dir / ".mcp.json").exists()


def test_sync_manifest_preserves_hand_curated_interface_fields_on_rerun(tmp_path: Path) -> None:
    """A maintainer's hand-tuned displayName/category/defaultPrompt survive a re-sync."""
    plugin_dir = _build_plugin_dir(tmp_path, "widget-tools", description="Widgets.", mcp_servers=None)
    sync_module.sync_manifest(plugin_dir)  # first pass: populate computed defaults

    manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["interface"]["displayName"] = "Widget Tools Pro"
    manifest["interface"]["category"] = "Productivity"
    manifest["interface"]["defaultPrompt"] = ["Use widget-tools to sync a widget."]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    changed = sync_module.sync_manifest(plugin_dir)

    reread = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert reread["interface"]["displayName"] == "Widget Tools Pro"
    assert reread["interface"]["category"] == "Productivity"
    assert reread["interface"]["defaultPrompt"] == ["Use widget-tools to sync a widget."]
    # capabilities is structurally derived, not curated, and unchanged here — so nothing else
    # drifted and the re-sync is a true no-op.
    assert changed is False


def test_sync_manifest_always_resyncs_derived_description_and_developer_fields(tmp_path: Path) -> None:
    """shortDescription/longDescription/developerName are pure derivations, never preserved stale.

    Unlike displayName/category, these fields have no independent curated meaning — they are a
    truncated/verbatim copy of "description" and a mirror of "author.name". A prior sync run
    (before SHORT_DESCRIPTION_LIMIT truncation existed, or after a source description edit) may
    have left a stale, non-empty value on disk; that must not be mistaken for a hand-curated
    override and preserved forever.
    """
    plugin_dir = _build_plugin_dir(tmp_path, "widget-tools", description="Widgets.", mcp_servers=None)
    sync_module.sync_manifest(plugin_dir)

    manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["interface"]["shortDescription"] = "Stale short description from an earlier run."
    manifest["interface"]["longDescription"] = "Stale long description from an earlier run."
    manifest["interface"]["developerName"] = "Stale Developer"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    changed = sync_module.sync_manifest(plugin_dir)

    reread = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert changed is True
    assert reread["interface"]["shortDescription"] == "Widgets."
    assert reread["interface"]["longDescription"] == "Widgets."
    assert reread["interface"]["developerName"] == "Test Author"


def test_check_mode_reports_stale_manifest_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """--check reports a stale manifest and exits non-zero without mutating any file."""
    plugin_dir = _build_plugin_dir(tmp_path, "widget-tools", description="Widgets.", mcp_servers=None)
    monkeypatch.setattr(sync_module, "PLUGINS_DIR", tmp_path)

    exit_code = sync_module.main(["--check"])

    assert exit_code == 1
    assert "widget-tools" in capsys.readouterr().out
    manifest = json.loads((plugin_dir / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert "interface" not in manifest


def test_check_mode_passes_once_manifests_are_synced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--check exits zero once a prior write-mode pass has caught the manifest up."""
    _build_plugin_dir(tmp_path, "widget-tools", description="Widgets.", mcp_servers=None)
    monkeypatch.setattr(sync_module, "PLUGINS_DIR", tmp_path)
    sync_module.main([])

    exit_code = sync_module.main(["--check"])

    assert exit_code == 0


def test_check_mode_matches_repository_codex_manifests() -> None:
    """CI gate: the repository's checked-in Codex manifests must already match the sync output.

    Mirrors the precedent in test_generate_codex_skill_activation_matrix.py — this repo gates
    generated/derived artifacts via a pytest assertion against the checked-in files rather than a
    dedicated CI job, reusing the existing required test-python job.
    """
    assert sync_module.main(["--check"]) == 0
