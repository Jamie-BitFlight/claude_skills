"""Tests for auto_sync_manifests.py pre-commit hook.

Observed symptom: When a commit attempt fails (e.g., ruff errors on other files) and the
user retries ``git commit``, prek reports::

    Stashed changes conflicted with changes made by hook, rolling back the hook changes

The conflict involves ``plugins/*/.claude-plugin/plugin.json`` files.

Bug areas tested:
1. Idempotency -- running the same update functions twice must produce identical output
   without double-bumping versions.
2. The version-comparison guard -- ``_version_already_bumped`` compares the working copy
   version against HEAD to skip bumping when a bump already occurred.

Test isolation strategy:
- The version-comparison guard is tested by mocking ``_read_head_json`` to control
  what HEAD returns, avoiding real git subprocess calls.
- All file I/O uses pytest tmp_path fixtures with monkeypatch.chdir.
- Each test is fully independent with no shared state.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Mapping

# ---------------------------------------------------------------------------
# Module import -- script has a hyphen in the filename so we use importlib
# ---------------------------------------------------------------------------
_SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "auto_sync_manifests.py"
_spec = importlib.util.spec_from_file_location("auto_sync_manifests", _SCRIPT_PATH)
if _spec and _spec.loader:
    auto_sync = importlib.util.module_from_spec(_spec)
    sys.modules["auto_sync_manifests"] = auto_sync
    _spec.loader.exec_module(auto_sync)
else:
    msg = f"Could not load module from {_SCRIPT_PATH}"
    raise ImportError(msg)


# Type aliases matching the module's TypedDicts -- defined locally so mypy
# resolves them without needing the dynamic module's types at analysis time.
_ComponentChangesDict = dict[str, list[dict[str, str]]]
_MarketplaceChangesDict = dict[str, Any]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plugin_json(base: Path, plugin_name: str, data: Mapping[str, Any]) -> Path:
    """Create plugins/<plugin_name>/.claude-plugin/plugin.json under *base*.

    Returns the path to plugin.json.
    """
    plugin_dir = base / "plugins" / plugin_name / ".claude-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_json = plugin_dir / "plugin.json"
    plugin_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return plugin_json


def _make_marketplace_json(base: Path, data: Mapping[str, Any]) -> Path:
    """Create .claude-plugin/marketplace.json under *base*.

    Returns the path to marketplace.json.
    """
    claude_dir = base / ".claude-plugin"
    claude_dir.mkdir(parents=True, exist_ok=True)
    marketplace_json = claude_dir / "marketplace.json"
    marketplace_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return marketplace_json


def _changes_with_modified_skill() -> _ComponentChangesDict:
    """Return component changes with a single modified skill."""
    return {
        "added": [],
        "deleted": [],
        "modified": [{"component_type": "skill", "component_path": "skills/my-skill/SKILL.md"}],
    }


def _changes_with_added_skill() -> _ComponentChangesDict:
    """Return component changes with a single added, standard-path skill (no modified entries)."""
    return {"added": [{"component_type": "skill", "component_path": "skills/new-skill"}], "deleted": [], "modified": []}


def _changes_with_added_skill() -> _ComponentChangesDict:
    """Return component changes with a single added skill."""
    return {
        "added": [{"component_type": "skill", "component_path": "skills/new-skill/SKILL.md"}],
        "deleted": [],
        "modified": [],
    }


# ============================================================================
# Area 2: Idempotency
# ============================================================================


class TestIdempotency:
    """Test that running update functions twice produces the same result.

    When a commit fails (e.g., ruff errors) and the user retries, the hook runs
    again on the same staged changes.  The version must not double-bump, and the
    file content must be stable.
    """

    def test_bump_version_is_not_idempotent_by_design(self) -> None:
        """Verify bump_version increments on every call -- it is NOT idempotent.

        Tests: bump_version function
        How: Call bump_version("1.0.0", "patch") twice in sequence
        Why: Demonstrates that without the staged guard, versions would double-bump
        """
        # Arrange
        version = "1.0.0"

        # Act
        first_bump = auto_sync.bump_version(version, "patch")
        second_bump = auto_sync.bump_version(first_bump, "patch")

        # Assert -- each call increments
        assert first_bump == "1.0.1"
        assert second_bump == "1.0.2"
        assert first_bump != second_bump

    def test_update_plugin_json_same_output_when_run_twice_from_same_state(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Verify running update_plugin_json twice from the same initial state is idempotent.

        Tests: Idempotency of update_plugin_json
        How: Create plugin.json, run update, reset to original, run update again,
             compare outputs
        Why: If the hook runs twice from the same file state, it should produce
             identical output
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        plugin_name = "test-plugin"
        original_data = {"name": "test-plugin", "version": "1.0.0", "skills": ["./skills/existing/"]}
        original_content = json.dumps(original_data, indent=2) + "\n"
        plugin_json = _make_plugin_json(tmp_path, plugin_name, original_data)

        changes = _changes_with_modified_skill()

        # Act -- Run 1: from original state
        updated_1, version_1 = auto_sync.update_plugin_json(plugin_name, changes)
        content_after_run1 = plugin_json.read_text(encoding="utf-8")

        # Reset to original state
        plugin_json.write_text(original_content, encoding="utf-8")

        # Act -- Run 2: from same original state
        updated_2, version_2 = auto_sync.update_plugin_json(plugin_name, changes)
        content_after_run2 = plugin_json.read_text(encoding="utf-8")

        # Assert -- both runs produced identical results
        assert updated_1 == updated_2
        assert version_1 == version_2
        assert content_after_run1 == content_after_run2

    def test_update_plugin_json_no_double_bump_on_retry(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify version does NOT double-bump when update runs twice.

        Tests: Idempotent version bumping via version comparison guard
        How: Run update_plugin_json twice; second run sees version already > HEAD
        Why: On retry after a failed commit, the version in the file is already
             bumped, so the version comparison guard prevents re-processing
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        plugin_name = "test-plugin"
        original_data = {"name": "test-plugin", "version": "1.0.0", "skills": ["./skills/existing/"]}
        _make_plugin_json(tmp_path, plugin_name, original_data)

        changes = _changes_with_modified_skill()

        # Simulate HEAD having the original version
        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: dict(original_data))

        # Act -- Run 1: HEAD version == file version, hook updates it
        updated_1, version_1 = auto_sync.update_plugin_json(plugin_name, changes)

        # Act -- Run 2: file version (1.0.1) > HEAD version (1.0.0), guard blocks
        updated_2, version_2 = auto_sync.update_plugin_json(plugin_name, changes)

        # Assert -- version bumped only once: 1.0.0 -> 1.0.1, second run blocked
        assert updated_1 is True
        assert version_1 == "1.0.1"
        assert updated_2 is False
        assert version_2 == "1.0.1"

    def test_update_plugin_json_bumps_all_harness_manifests(self, tmp_path: Path, monkeypatch: Any) -> None:
        # Arrange
        monkeypatch.chdir(tmp_path)

        plugin_name = "test-plugin"
        original_data = {"name": plugin_name, "version": "1.0.0", "skills": ["./skills/existing/"]}
        claude_manifest = _make_plugin_json(tmp_path, plugin_name, original_data)
        codex_manifest = tmp_path / "plugins" / plugin_name / ".codex-plugin" / "plugin.json"
        codex_manifest.parent.mkdir(parents=True)
        codex_manifest.write_text(json.dumps({"name": plugin_name, "version": "1.0.1"}, indent=2) + "\n")
        cursor_manifest = tmp_path / "plugins" / plugin_name / ".cursor-plugin" / "plugin.json"
        cursor_manifest.parent.mkdir(parents=True)
        cursor_manifest.write_text(json.dumps({"name": plugin_name, "version": "1.0.2"}, indent=2) + "\n")

        def read_head(path: str) -> dict[str, object]:
            if ".codex-plugin" in path:
                return {"name": plugin_name, "version": "1.0.1"}
            if ".cursor-plugin" in path:
                return {"name": plugin_name, "version": "1.0.2"}
            return dict(original_data)

        monkeypatch.setattr(auto_sync, "_read_head_json", read_head)

        # Act
        updated, version = auto_sync.update_plugin_json(plugin_name, _changes_with_modified_skill())

        # Assert
        assert updated is True
        assert version == "1.0.1"
        assert json.loads(claude_manifest.read_text(encoding="utf-8"))["version"] == "1.0.1"
        assert json.loads(codex_manifest.read_text(encoding="utf-8"))["version"] == "1.0.2"
        assert json.loads(cursor_manifest.read_text(encoding="utf-8"))["version"] == "1.0.3"

    def test_update_plugin_json_bumps_secondary_manifest_on_added_only_changes(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """A standard-path addition (no modified entries) still bumps a secondary manifest.

        Tests: the `if modified or any(changes.values())` branch in _update_from_base_ref /
               _update_from_head, specifically the widening from the earlier
               `if modified or changes["modified"]` check
        How: Pass changes with only "added" populated (no "modified") against a plugin that
             has both a primary (.claude-plugin) and secondary (.codex-plugin) manifest
        Why: For a secondary manifest, sync_components=False so _update_component_arrays never
             runs and `modified` stays False -- before this branch widened to any(changes.values()),
             an added-only change (e.g. a new standard-path skill, auto-discovered so never written
             to the array) produced NO version bump for secondary manifests at all. Only the
             primary manifest was covered by the pre-existing modified-only test above.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        plugin_name = "test-plugin"
        original_data = {"name": plugin_name, "version": "1.0.0"}
        claude_manifest = _make_plugin_json(tmp_path, plugin_name, original_data)
        codex_manifest = tmp_path / "plugins" / plugin_name / ".codex-plugin" / "plugin.json"
        codex_manifest.parent.mkdir(parents=True)
        codex_manifest.write_text(json.dumps({"name": plugin_name, "version": "1.0.0"}, indent=2) + "\n")

        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: dict(original_data))

        # Act
        updated, _version = auto_sync.update_plugin_json(plugin_name, _changes_with_added_skill())

        # Assert -- both manifests bumped even though only "added" was populated
        # (minor bump, since _determine_bump_type treats a non-empty "added" as a new feature)
        assert updated is True
        assert json.loads(claude_manifest.read_text(encoding="utf-8"))["version"] == "1.1.0"
        assert json.loads(codex_manifest.read_text(encoding="utf-8"))["version"] == "1.1.0"

    def test_update_plugin_json_reports_manifest_version_divergence(
        self, tmp_path: Path, monkeypatch: Any, capsys: Any
    ) -> None:
        """Verify divergent per-manifest versions are surfaced, not silent.

        Tests: update_plugin_json's post-bump divergence report
        How: Reuse the harness-manifest fixture where .claude-plugin, .codex-plugin,
             and .cursor-plugin bump to three different final versions, then check stdout
        Why: Each manifest bumps from its own base version by design (see
             test_update_plugin_json_bumps_all_harness_manifests) -- they are not forced
             into agreement -- but a widening gap must be visible in hook/CI output rather
             than silently accumulating
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        plugin_name = "test-plugin"
        original_data = {"name": plugin_name, "version": "1.0.0", "skills": ["./skills/existing/"]}
        _make_plugin_json(tmp_path, plugin_name, original_data)
        codex_manifest = tmp_path / "plugins" / plugin_name / ".codex-plugin" / "plugin.json"
        codex_manifest.parent.mkdir(parents=True)
        codex_manifest.write_text(json.dumps({"name": plugin_name, "version": "1.0.1"}, indent=2) + "\n")

        def read_head(path: str) -> dict[str, object]:
            if ".codex-plugin" in path:
                return {"name": plugin_name, "version": "1.0.1"}
            return dict(original_data)

        monkeypatch.setattr(auto_sync, "_read_head_json", read_head)

        # Act
        updated, _version = auto_sync.update_plugin_json(plugin_name, _changes_with_modified_skill())
        out = capsys.readouterr().out

        # Assert -- divergence reported by path, with each manifest's own final version
        assert updated is True
        assert ".claude-plugin/plugin.json=1.0.1" in out
        assert ".codex-plugin/plugin.json=1.0.2" in out
        assert "diverge" in out.lower()

    def test_update_marketplace_json_no_double_bump_on_retry(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify marketplace version does NOT double-bump on retry.

        Tests: Idempotent version bumping for marketplace.json via version guard
        How: Run update_marketplace_json twice; second run sees version > HEAD
        Why: On retry, marketplace.json version is already bumped from run 1
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        original_data = {
            "metadata": {"version": "1.0.0"},
            "plugins": [{"name": "existing", "source": "./plugins/existing"}],
        }
        _make_marketplace_json(tmp_path, original_data)

        plugin_changes: _MarketplaceChangesDict = {
            "added": set(),
            "deleted": set(),
            "modified": [("existing", "1.0.1")],
        }

        # Simulate HEAD having the original version
        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: dict(original_data))

        # Act -- Run 1: HEAD version == file version
        updated_1 = auto_sync.update_marketplace_json(plugin_changes)

        # Act -- Run 2: file version (1.0.1) > HEAD version (1.0.0), guard blocks
        updated_2 = auto_sync.update_marketplace_json(plugin_changes)

        # Assert -- version bumped only once
        assert updated_1 is True
        assert updated_2 is False

        marketplace_json = tmp_path / ".claude-plugin" / "marketplace.json"
        final_data = json.loads(marketplace_json.read_text(encoding="utf-8"))
        assert final_data["metadata"]["version"] == "1.0.1"

    def test_bump_version_handles_invalid_input_gracefully(self) -> None:
        """Verify bump_version returns default for malformed version strings.

        Tests: bump_version error handling
        How: Pass invalid version strings
        Why: Ensure robustness during edge cases
        """
        # Arrange / Act / Assert
        assert auto_sync.bump_version("invalid", "patch") == "0.1.0"
        assert auto_sync.bump_version("", "minor") == "0.1.0"
        assert auto_sync.bump_version("1.2", "patch") == "0.1.0"

    def test_bump_version_all_bump_types(self) -> None:
        """Verify each bump type increments the correct segment.

        Tests: bump_version correctness for major, minor, patch
        How: Call with each bump type from the same base version
        Why: Ensure version bumping logic is correct
        """
        # Arrange
        base = "2.3.4"

        # Act / Assert
        assert auto_sync.bump_version(base, "major") == "3.0.0"
        assert auto_sync.bump_version(base, "minor") == "2.4.0"
        assert auto_sync.bump_version(base, "patch") == "2.3.5"


# ============================================================================
# Area 3: The "already staged" guard
# ============================================================================


class TestVersionComparisonGuard:
    """Test the version-comparison guard via _version_already_bumped.

    The guard compares the working copy version against the HEAD version.
    If the working version is strictly greater, the bump is skipped.
    """

    def test_update_plugin_json_skips_when_version_already_bumped(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify update_plugin_json skips when file version > HEAD version.

        Tests: Version guard in update_plugin_json
        How: Set file version > HEAD version via _read_head_json mock
        Why: On retry after failed commit, file already has bumped version
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        plugin_name = "test-plugin"
        # File has version 1.5.0, HEAD has 1.4.0 -> already bumped
        data = {"name": "test-plugin", "version": "1.5.0", "skills": []}
        plugin_json = _make_plugin_json(tmp_path, plugin_name, data)

        head_data = {"name": "test-plugin", "version": "1.4.0", "skills": []}
        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: dict(head_data))

        changes = _changes_with_modified_skill()

        # Act
        updated, version = auto_sync.update_plugin_json(plugin_name, changes)

        # Assert -- guard triggered: returns False with current version
        assert updated is False
        assert version == "1.5.0"

        # File was NOT modified
        assert json.loads(plugin_json.read_text(encoding="utf-8"))["version"] == "1.5.0"

    def test_update_marketplace_json_skips_when_version_already_bumped(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify update_marketplace_json skips when version already > HEAD.

        Tests: Version guard in update_marketplace_json
        How: Set marketplace version > HEAD version via mock
        Why: Same pattern as plugin.json guard
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        data = {"metadata": {"version": "2.1.0"}, "plugins": [{"name": "p1", "source": "./plugins/p1"}]}
        marketplace_json = _make_marketplace_json(tmp_path, data)

        head_data = {"metadata": {"version": "2.0.0"}, "plugins": [{"name": "p1", "source": "./plugins/p1"}]}
        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: dict(head_data))

        plugin_changes: _MarketplaceChangesDict = {"added": {"new-plugin"}, "deleted": set(), "modified": []}

        # Act
        updated = auto_sync.update_marketplace_json(plugin_changes)

        # Assert -- guard triggered, no modifications
        assert updated is False
        loaded = json.loads(marketplace_json.read_text(encoding="utf-8"))
        assert loaded["metadata"]["version"] == "2.1.0"

    def test_guard_returns_current_version_not_zero(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify the guard returns the actual current version, not "0.0.0".

        Tests: Return value fidelity of the version guard
        How: Set up plugin.json with version already bumped, inspect return
        Why: Unlike the old staged guard, the new guard returns the real version
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        plugin_name = "my-plugin"
        data = {"name": "my-plugin", "version": "3.2.1", "skills": []}
        _make_plugin_json(tmp_path, plugin_name, data)

        head_data = {"name": "my-plugin", "version": "3.2.0", "skills": []}
        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: dict(head_data))

        changes = _changes_with_added_skill()

        # Act
        updated, version = auto_sync.update_plugin_json(plugin_name, changes)

        # Assert -- returns actual version "3.2.1", not "0.0.0"
        assert updated is False
        assert version == "3.2.1"

    def test_guard_allows_bump_when_version_equals_head(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify update proceeds when file version == HEAD version.

        Tests: Guard pass-through when no prior bump
        How: Set file and HEAD to same version
        Why: Normal case -- user hasn't manually bumped
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        plugin_name = "test"
        data = {"name": "test", "version": "1.0.0"}
        _make_plugin_json(tmp_path, plugin_name, data)

        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: dict(data))

        changes = _changes_with_modified_skill()

        # Act
        updated, version = auto_sync.update_plugin_json(plugin_name, changes)

        # Assert -- guard did NOT trigger, update proceeds
        assert updated is True
        assert version == "1.0.1"

    def test_guard_allows_bump_when_file_not_in_head(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify update proceeds when HEAD has no version of the file.

        Tests: Guard pass-through for new files
        How: Mock _read_head_json to return None (file not in HEAD)
        Why: New plugin.json files should always be bumped
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        plugin_name = "my-plugin"
        data = {"name": "my-plugin", "version": "1.0.0", "skills": []}
        _make_plugin_json(tmp_path, plugin_name, data)

        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: None)

        changes = _changes_with_modified_skill()

        # Act
        updated, version = auto_sync.update_plugin_json(plugin_name, changes)

        # Assert -- guard did NOT trigger, update proceeds
        assert updated is True
        assert version == "1.0.1"


# ============================================================================
# Area 2+3 combined: Retry scenario simulation
# ============================================================================


class TestRetryScenario:
    """Simulate the full retry scenario that triggers the stash conflict.

    Scenario:
    1. User runs ``git commit``
    2. auto-sync-manifests hook runs, modifies plugin.json, stages it
    3. Another hook (e.g., ruff) fails
    4. prek stashes hook changes, restores original
    5. User runs ``git commit`` again
    6. auto-sync-manifests hook runs AGAIN
    7. File version (1.0.1) > HEAD version (1.0.0), guard kicks in
    8. The version-comparison guard skips processing

    But between steps 4 and 6, prettier may have also modified the file,
    creating a conflict.
    """

    def test_retry_scenario_guard_prevents_double_bump(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Simulate the retry: first run bumps, second run is blocked by guard.

        Tests: Complete retry flow
        How: Run update twice; second run sees version already > HEAD
        Why: Verify the guard prevents double-bumping on commit retry
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        plugin_name = "my-plugin"
        original_data = {"name": "my-plugin", "version": "1.0.0", "skills": ["./skills/existing/"]}
        plugin_json = _make_plugin_json(tmp_path, plugin_name, original_data)

        changes = _changes_with_modified_skill()

        # Simulate HEAD having the original version
        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: dict(original_data))

        # --- Run 1: HEAD version == file version, hook modifies it ---
        updated_1, version_1 = auto_sync.update_plugin_json(plugin_name, changes)

        assert updated_1 is True
        assert version_1 == "1.0.1"
        content_after_run1 = plugin_json.read_text(encoding="utf-8")

        # --- Run 2: file version (1.0.1) > HEAD (1.0.0), guard blocks ---
        updated_2, version_2 = auto_sync.update_plugin_json(plugin_name, changes)

        assert updated_2 is False
        assert version_2 == "1.0.1"

        # File content unchanged from run 1
        assert plugin_json.read_text(encoding="utf-8") == content_after_run1

    def test_retry_guard_version_propagates_to_marketplace_changes(self) -> None:
        """Verify that guard's return propagates correctly to marketplace tracking.

        Tests: Interaction between guard return value and main() flow
        How: Simulate the code in main() that appends (plugin_name, new_version)
             to marketplace_changes when updated is True, and skips when False
        Why: When the guard returns (False, current_version), main() correctly
             skips appending to marketplace_changes["modified"]
        """
        # Arrange -- simulate what main() does
        marketplace_changes: _MarketplaceChangesDict = {"added": set(), "deleted": set(), "modified": []}

        # Run 1 result: hook updated plugin
        updated_run1 = True
        version_run1 = "1.0.1"

        if updated_run1:
            marketplace_changes["modified"].append(("my-plugin", version_run1))

        # Run 2 result: guard blocked
        updated_run2 = False
        version_run2 = "1.0.1"  # Guard now returns actual version, not "0.0.0"

        if updated_run2:
            marketplace_changes["modified"].append(("my-plugin", version_run2))

        # Assert -- only run 1's version appears (run 2 was blocked)
        assert len(marketplace_changes["modified"]) == 1
        assert marketplace_changes["modified"][0] == ("my-plugin", "1.0.1")


# ============================================================================
# Supporting function tests
# ============================================================================


class TestParsePluginPath:
    """Test parse_plugin_path for correct categorisation of file paths."""

    def test_non_plugin_path_returns_none(self) -> None:
        """Verify paths outside plugins/ directory return None.

        Tests: parse_plugin_path boundary
        How: Pass a path not starting with plugins/
        Why: Ensure non-plugin files are ignored
        """
        result = auto_sync.parse_plugin_path("src/main.py")
        assert result is None

    def test_plugin_json_path_parsed(self) -> None:
        """Verify plugin.json path is parsed with no component type.

        Tests: parse_plugin_path for manifest files
        How: Pass plugins/foo/.claude-plugin/plugin.json
        Why: Plugin.json is detected as a plugin-level change, not a component
        """
        result = auto_sync.parse_plugin_path("plugins/my-plugin/.claude-plugin/plugin.json")
        assert result is not None
        assert result["plugin"] == "my-plugin"

    def test_skill_path_parsed(self) -> None:
        """Verify skill SKILL.md path is correctly categorised.

        Tests: parse_plugin_path for skill files
        How: Pass a skills/name/SKILL.md path
        Why: Ensure skills are detected as component_type "skill"
        """
        result = auto_sync.parse_plugin_path("plugins/my-plugin/skills/my-skill/SKILL.md")
        assert result is not None
        assert result["plugin"] == "my-plugin"
        assert result["component_type"] == "skill"
        # parse_plugin_path registers the skill directory, not the full file path
        assert result["component_path"] == "skills/my-skill"

    def test_agent_path_parsed(self) -> None:
        """Verify agent .md path is correctly categorised.

        Tests: parse_plugin_path for agent files
        How: Pass an agents/name.md path
        Why: Ensure agents are detected as component_type "agent"
        """
        result = auto_sync.parse_plugin_path("plugins/my-plugin/agents/my-agent.md")
        assert result is not None
        assert result["component_type"] == "agent"

    def test_mcp_substring_in_non_mcp_path_is_not_mcp(self) -> None:
        """Verify 'mcp' as a substring in a non-mcp directory does not match as mcp.

        Tests: parse_plugin_path false-positive prevention for mcp detection
        How: Pass a script path containing 'mcp' as a substring in the filename
        Why: Previously ``"mcp" in filepath`` matched any path containing 'mcp',
             e.g. plugins/demo/scripts/mcp-utils.py was incorrectly typed as mcp
        """
        result = auto_sync.parse_plugin_path("plugins/demo/scripts/mcp-utils.py")
        assert result is not None
        assert result["plugin"] == "demo"
        # scripts/ is not a recognised component directory, so no component_type
        assert result["component_type"] is None

    def test_mcp_directory_is_detected(self) -> None:
        """Verify files in the mcp/ directory are correctly detected as mcp type.

        Tests: parse_plugin_path for mcp files
        How: Pass a path with mcp as the component directory
        Why: Ensure the mcp detection still works for actual mcp components
        """
        result = auto_sync.parse_plugin_path("plugins/my-plugin/mcp/my-server.json")
        assert result is not None
        assert result["component_type"] == "mcp"
        assert result["component_path"] == "mcp/my-server.json"


class TestProcessFileChanges:
    """Test _process_file_changes for correct categorisation."""

    def test_new_skill_detected_as_component_add(self) -> None:
        """Verify a new skill file triggers component addition.

        Tests: _process_file_changes with added skill
        How: Pass status with an added skill path
        Why: Ensure added skills are tracked for plugin.json update
        """
        # Arrange
        status: dict[str, list[str]] = {
            "added": ["plugins/my-plugin/skills/new-skill/SKILL.md"],
            "deleted": [],
            "modified": [],
        }

        # Act
        component_changes, _marketplace_changes = auto_sync._process_file_changes(status)

        # Assert
        assert "my-plugin" in component_changes
        assert len(component_changes["my-plugin"]["added"]) == 1
        assert component_changes["my-plugin"]["added"][0]["component_type"] == "skill"

    def test_new_plugin_json_detected_as_marketplace_add(self) -> None:
        """Verify a new plugin.json triggers marketplace addition.

        Tests: _process_file_changes with new plugin
        How: Pass status with added .claude-plugin/plugin.json
        Why: Ensure new plugins are tracked for marketplace.json update
        """
        # Arrange
        status: dict[str, list[str]] = {
            "added": ["plugins/new-plugin/.claude-plugin/plugin.json"],
            "deleted": [],
            "modified": [],
        }

        # Act
        _, marketplace_changes = auto_sync._process_file_changes(status)

        # Assert
        assert "new-plugin" in marketplace_changes["added"]

    def test_deleted_plugin_json_detected_as_marketplace_delete(self) -> None:
        """Verify a deleted plugin.json triggers marketplace removal.

        Tests: _process_file_changes with deleted plugin
        How: Pass status with deleted .claude-plugin/plugin.json
        Why: Ensure deleted plugins are tracked for marketplace.json update
        """
        # Arrange
        status: dict[str, list[str]] = {
            "added": [],
            "deleted": ["plugins/old-plugin/.claude-plugin/plugin.json"],
            "modified": [],
        }

        # Act
        _, marketplace_changes = auto_sync._process_file_changes(status)

        # Assert
        assert "old-plugin" in marketplace_changes["deleted"]


class TestUpdateComponentArrays:
    """Test _update_component_arrays for correct array manipulation."""

    def test_add_new_skill_to_empty_skills_array(self) -> None:
        """Verify adding a skill creates the skills array if absent.

        Tests: _update_component_arrays with missing skills field
        How: Pass data without skills field, add a skill component
        Why: Ensure the function creates the field when needed
        """
        # Arrange
        data: dict[str, list[str] | str] = {"name": "test"}
        changes: _ComponentChangesDict = {
            "added": [{"component_type": "skill", "component_path": "skills/new/SKILL.md"}],
            "deleted": [],
            "modified": [],
        }

        # Act
        modified = auto_sync._update_component_arrays(data, changes)

        # Assert
        assert modified is True
        assert "skills" in data
        assert "./skills/new/SKILL.md" in data["skills"]

    def test_add_duplicate_skill_is_noop(self) -> None:
        """Verify adding an already-present skill does not duplicate it.

        Tests: _update_component_arrays deduplication
        How: Pass data with existing skill path, try to add same path
        Why: Ensure idempotent component addition
        """
        # Arrange
        data: dict[str, list[str] | str] = {"name": "test", "skills": ["./skills/existing/SKILL.md"]}
        changes: _ComponentChangesDict = {
            "added": [{"component_type": "skill", "component_path": "skills/existing/SKILL.md"}],
            "deleted": [],
            "modified": [],
        }

        # Act
        modified = auto_sync._update_component_arrays(data, changes)

        # Assert
        assert modified is False
        skills = data["skills"]
        assert isinstance(skills, list)
        assert len(skills) == 1

    def test_delete_skill_removes_from_array(self) -> None:
        """Verify deleting a skill removes it from the array.

        Tests: _update_component_arrays deletion
        How: Pass data with a skill, delete that skill
        Why: Ensure component removal works correctly
        """
        # Arrange
        data: dict[str, list[str] | str] = {
            "name": "test",
            "skills": ["./skills/old/SKILL.md", "./skills/keep/SKILL.md"],
        }
        changes: _ComponentChangesDict = {
            "added": [],
            "deleted": [{"component_type": "skill", "component_path": "skills/old/SKILL.md"}],
            "modified": [],
        }

        # Act
        modified = auto_sync._update_component_arrays(data, changes)

        # Assert
        assert modified is True
        skills = data["skills"]
        assert isinstance(skills, list)
        assert "./skills/old/SKILL.md" not in skills
        assert "./skills/keep/SKILL.md" in skills


class TestAgentAutoDiscoveryRegression:
    """Regression guard for the 2026-03-17 / 2026-04-12 auto-discovery masking bug.

    Adding a new agent file to ``agents/`` MUST NOT cause _update_component_arrays
    to introduce an ``agents`` array in plugin.json. Doing so overrides Claude
    Code's auto-discovery and silently masks every other agent in the plugin.

    See:
        - .claude/rules/plugin-development.md (canonical rule)
        - plugins/plugin-creator/scripts/auto_sync_manifests.py docstring of
          _is_standard_path_component (incident history)
    """

    def test_new_agent_does_not_create_agents_key_when_absent(self) -> None:
        """The pre-commit fix: new default-path agents must not introduce the array.

        Tests: _update_component_arrays for default-path agents in Mode A
        How: Plugin.json has no agents key; add a new agents/foo.md component
        Why: 2026-04-12 commit 30260566 introduced an agents array containing
            only the new file, masking 21 of 23 dh agents. The fix is to leave
            plugin.json untouched and rely on Claude Code's auto-discovery.
        """
        # Arrange
        data: dict[str, list[str] | str] = {"name": "dh", "version": "7.9.6"}
        changes: _ComponentChangesDict = {
            "added": [
                {"component_type": "agent", "component_path": "agents/classifier.md"},
                {"component_type": "agent", "component_path": "agents/rtica-assessor.md"},
            ],
            "deleted": [],
            "modified": [],
        }

        # Act
        modified = auto_sync._update_component_arrays(data, changes)

        # Assert
        assert modified is True, "modified flag should be True so the version still bumps"
        assert "agents" not in data, (
            "default-path agents must NOT introduce an agents key — auto-discovery handles them"
        )

    def test_new_agent_appends_to_existing_array_in_mode_b(self) -> None:
        """Mode B: when the array already exists, new entries are appended.

        Tests: _update_component_arrays for default-path agents in Mode B
        How: Plugin.json already has an agents key (manual allowlist mode);
             add a new agents/foo.md component
        Why: When the user has explicitly opted into the manual allowlist
            (e.g. for non-default agent paths), every new agent must be
            carried forward or it becomes invisible.
        """
        # Arrange
        data: dict[str, list[str] | str] = {"name": "dh", "version": "7.9.6", "agents": ["./custom/agents/legacy.md"]}
        changes: _ComponentChangesDict = {
            "added": [{"component_type": "agent", "component_path": "agents/new-agent.md"}],
            "deleted": [],
            "modified": [],
        }

        # Act
        modified = auto_sync._update_component_arrays(data, changes)

        # Assert
        assert modified is True
        agents = data["agents"]
        assert isinstance(agents, list)
        assert "./custom/agents/legacy.md" in agents, "existing entries must be carried forward"
        assert "./agents/new-agent.md" in agents, "new entries must be appended in Mode B"

    def test_new_default_path_command_does_not_create_commands_key(self) -> None:
        """Same auto-discovery rule applies to commands/*.md.

        Tests: _update_component_arrays for default-path commands in Mode A
        How: Plugin.json has no commands key; add a new commands/foo.md
        Why: Commands obey the same auto-discovery semantics as agents and
            skills. The original bug only manifested for agents because the
            agent branch lacked the standard-path guard, but the same fix
            now covers all three component types.
        """
        # Arrange
        data: dict[str, list[str] | str] = {"name": "p", "version": "1.0.0"}
        changes: _ComponentChangesDict = {
            "added": [{"component_type": "command", "component_path": "commands/cmd.md"}],
            "deleted": [],
            "modified": [],
        }

        # Act
        modified = auto_sync._update_component_arrays(data, changes)

        # Assert
        assert modified is True
        assert "commands" not in data

    def test_non_default_path_agent_still_registered(self) -> None:
        """Sanity check: agents in non-default paths still get explicit registration.

        Tests: _update_component_arrays for non-default-path agents
        How: Add an agent at custom/agents/foo.md (not under agents/)
        Why: Auto-discovery only covers the default location. Agents in custom
            paths must still be registered explicitly or Claude Code cannot
            see them.
        """
        # Arrange
        data: dict[str, list[str] | str] = {"name": "p", "version": "1.0.0"}
        changes: _ComponentChangesDict = {
            "added": [{"component_type": "agent", "component_path": "custom/agents/special.md"}],
            "deleted": [],
            "modified": [],
        }

        # Act
        modified = auto_sync._update_component_arrays(data, changes)

        # Assert
        assert modified is True
        assert "agents" in data
        agents = data["agents"]
        assert isinstance(agents, list)
        assert "./custom/agents/special.md" in agents

    def test_is_standard_path_component_classification(self) -> None:
        """The classifier must recognise default locations for all three types.

        Tests: _is_standard_path_component coverage
        How: Exercise every (field, path) shape that pre-commit detection emits
        Why: Lock in the contract so future changes cannot accidentally
            re-enable the auto-discovery override bug.
        """
        # Standard-path agents — the regression we are fixing
        assert auto_sync._is_standard_path_component("agents", "agents/foo.md") is True
        assert auto_sync._is_standard_path_component("agents", "agents/bar.md") is True
        # Non-default agents — must remain explicit
        assert auto_sync._is_standard_path_component("agents", "custom/agents/foo.md") is False
        assert auto_sync._is_standard_path_component("agents", "agents/sub/nested.md") is False
        # Standard-path commands
        assert auto_sync._is_standard_path_component("commands", "commands/cmd.md") is True
        assert auto_sync._is_standard_path_component("commands", "custom/commands/cmd.md") is False
        # Standard-path skills (preserves prior behaviour)
        assert auto_sync._is_standard_path_component("skills", "skills/my-skill") is True
        assert auto_sync._is_standard_path_component("skills", "skills/my-skill/SKILL.md") is False
        # Unknown field
        assert auto_sync._is_standard_path_component("hooks", "hooks/foo.json") is False


class TestUpdatePluginJsonFileNotFound:
    """Test update_plugin_json when plugin.json does not exist."""

    def test_returns_false_when_plugin_json_missing(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify update_plugin_json returns (False, "0.0.0") for missing file.

        Tests: update_plugin_json with non-existent plugin.json
        How: Call with a plugin name that has no .claude-plugin/plugin.json
        Why: Ensure graceful handling of missing files
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        changes = _changes_with_modified_skill()

        # Act
        updated, version = auto_sync.update_plugin_json("nonexistent", changes)

        # Assert
        assert updated is False
        assert version == "0.0.0"


# ============================================================================
# New behaviour: _parse_version_tuple helper
# ============================================================================


class TestParseVersionTuple:
    """Test the _parse_version_tuple helper for semantic version parsing."""

    def test_valid_version_string(self) -> None:
        """Verify _parse_version_tuple parses a valid semantic version.

        Tests: _parse_version_tuple basic parsing
        How: Pass a "1.2.3" string and check the returned tuple
        Why: Ensure correct extraction of major, minor, patch integers
        """
        assert auto_sync._parse_version_tuple("1.2.3") == (1, 2, 3)

    def test_zero_version(self) -> None:
        """Verify _parse_version_tuple handles all-zero version.

        Tests: _parse_version_tuple edge case
        How: Pass "0.0.0"
        Why: Initial versions must parse correctly
        """
        assert auto_sync._parse_version_tuple("0.0.0") == (0, 0, 0)

    def test_large_version_numbers(self) -> None:
        """Verify _parse_version_tuple handles large integers.

        Tests: _parse_version_tuple large values
        How: Pass "100.200.300"
        Why: No arbitrary upper limit on version components
        """
        assert auto_sync._parse_version_tuple("100.200.300") == (100, 200, 300)

    def test_non_numeric_returns_none(self) -> None:
        """Verify _parse_version_tuple returns None for non-numeric input.

        Tests: _parse_version_tuple malformed input
        How: Pass "a.b.c"
        Why: Non-integer components are invalid
        """
        assert auto_sync._parse_version_tuple("a.b.c") is None

    def test_too_few_parts_returns_none(self) -> None:
        """Verify _parse_version_tuple returns None for incomplete version.

        Tests: _parse_version_tuple insufficient parts
        How: Pass "1.2"
        Why: Semantic version requires exactly three components
        """
        assert auto_sync._parse_version_tuple("1.2") is None

    def test_too_many_parts_returns_none(self) -> None:
        """Verify _parse_version_tuple returns None for extra parts.

        Tests: _parse_version_tuple excess parts
        How: Pass "1.2.3.4"
        Why: Only major.minor.patch is accepted
        """
        assert auto_sync._parse_version_tuple("1.2.3.4") is None

    def test_empty_string_returns_none(self) -> None:
        """Verify _parse_version_tuple returns None for empty string.

        Tests: _parse_version_tuple empty input
        How: Pass ""
        Why: Edge case for missing version field
        """
        assert auto_sync._parse_version_tuple("") is None


# ============================================================================
# New behaviour: extract_version_from_json helper
# ============================================================================


class TestExtractVersionFromJson:
    """Test the extract_version_from_json helper for nested key traversal."""

    def test_top_level_version(self) -> None:
        """Verify extract_version_from_json extracts a top-level version.

        Tests: extract_version_from_json single-key path
        How: Pass {"version": "1.2.3"} with key_path ["version"]
        Why: plugin.json stores version at top level
        """
        data: dict[str, object] = {"version": "1.2.3"}
        assert auto_sync.extract_version_from_json(data, ["version"]) == (1, 2, 3)

    def test_nested_version(self) -> None:
        """Verify extract_version_from_json traverses nested keys.

        Tests: extract_version_from_json multi-key path
        How: Pass {"metadata": {"version": "2.0.1"}} with key_path ["metadata", "version"]
        Why: marketplace.json stores version under metadata.version
        """
        data: dict[str, object] = {"metadata": {"version": "2.0.1"}}
        assert auto_sync.extract_version_from_json(data, ["metadata", "version"]) == (2, 0, 1)

    def test_missing_key_returns_none(self) -> None:
        """Verify extract_version_from_json returns None for missing key.

        Tests: extract_version_from_json missing path
        How: Pass data without the requested key
        Why: Graceful handling when JSON structure differs from expected
        """
        data: dict[str, object] = {"name": "test"}
        assert auto_sync.extract_version_from_json(data, ["version"]) is None

    def test_non_dict_intermediate_returns_none(self) -> None:
        """Verify extract_version_from_json returns None for non-dict intermediate.

        Tests: extract_version_from_json type mismatch in path
        How: Pass {"metadata": "not-a-dict"} with path ["metadata", "version"]
        Why: Cannot traverse into a string value
        """
        data: dict[str, object] = {"metadata": "not-a-dict"}
        assert auto_sync.extract_version_from_json(data, ["metadata", "version"]) is None

    def test_non_string_version_returns_none(self) -> None:
        """Verify extract_version_from_json returns None when version is not a string.

        Tests: extract_version_from_json wrong value type
        How: Pass {"version": 123} with path ["version"]
        Why: Version must be a string to parse
        """
        data: dict[str, object] = {"version": 123}
        assert auto_sync.extract_version_from_json(data, ["version"]) is None

    def test_non_dict_root_returns_none(self) -> None:
        """Verify extract_version_from_json returns None for non-dict root.

        Tests: extract_version_from_json invalid root type
        How: Pass a list instead of dict
        Why: JSON root must be traversable as dict
        """
        assert auto_sync.extract_version_from_json(["not", "a", "dict"], ["version"]) is None


# ============================================================================
# New behaviour: _version_already_bumped helper
# ============================================================================


class TestVersionAlreadyBumped:
    """Test the _version_already_bumped helper for version comparison logic."""

    def test_returns_true_when_current_greater(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify _version_already_bumped returns True when file version > HEAD.

        Tests: _version_already_bumped positive detection
        How: Write file with version 1.1.0, mock HEAD with 1.0.0
        Why: Core guard logic -- skip bump when already bumped
        """
        monkeypatch.chdir(tmp_path)
        plugin_json = tmp_path / "plugin.json"
        plugin_json.write_text(json.dumps({"version": "1.1.0"}))

        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: {"version": "1.0.0"})

        assert auto_sync._version_already_bumped(str(plugin_json), ["version"]) is True

    def test_returns_false_when_versions_equal(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify _version_already_bumped returns False when versions match.

        Tests: _version_already_bumped equal versions
        How: Write file with version 1.0.0, mock HEAD with 1.0.0
        Why: Equal versions mean no bump has occurred yet
        """
        monkeypatch.chdir(tmp_path)
        plugin_json = tmp_path / "plugin.json"
        plugin_json.write_text(json.dumps({"version": "1.0.0"}))

        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: {"version": "1.0.0"})

        assert auto_sync._version_already_bumped(str(plugin_json), ["version"]) is False

    def test_returns_false_when_head_none(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify _version_already_bumped returns False when file not in HEAD.

        Tests: _version_already_bumped new file
        How: Mock _read_head_json returning None
        Why: New files not yet committed should allow bumping
        """
        monkeypatch.chdir(tmp_path)
        plugin_json = tmp_path / "plugin.json"
        plugin_json.write_text(json.dumps({"version": "1.0.0"}))

        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: None)

        assert auto_sync._version_already_bumped(str(plugin_json), ["version"]) is False

    def test_returns_false_when_file_missing(self, monkeypatch: Any) -> None:
        """Verify _version_already_bumped returns False when file does not exist.

        Tests: _version_already_bumped missing file
        How: Pass non-existent path with valid HEAD data
        Why: Graceful handling when file is deleted
        """
        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: {"version": "1.0.0"})

        assert auto_sync._version_already_bumped("/nonexistent/plugin.json", ["version"]) is False

    def test_nested_key_path(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify _version_already_bumped works with nested key paths.

        Tests: _version_already_bumped marketplace-style path
        How: Use ["metadata", "version"] key path for marketplace.json
        Why: marketplace.json stores version under metadata.version
        """
        monkeypatch.chdir(tmp_path)
        marketplace_json = tmp_path / "marketplace.json"
        marketplace_json.write_text(json.dumps({"metadata": {"version": "2.1.0"}}))

        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: {"metadata": {"version": "2.0.0"}})

        assert auto_sync._version_already_bumped(str(marketplace_json), ["metadata", "version"]) is True


# ============================================================================
# New behaviour: _format_json formatter
# ============================================================================


class TestFormatJson:
    """Test the _format_json formatter."""

    def test_format_json_produces_valid_json(self) -> None:
        """Verify _format_json output parses as valid JSON.

        Tests: JSON validity of _format_json output
        How: Round-trip through json.loads
        Why: Formatting changes must not break JSON syntax
        """
        data = {
            "name": "test-plugin",
            "version": "2.3.4",
            "skills": ["./skills/a/", "./skills/b/"],
            "metadata": {"author": "test"},
        }
        result = auto_sync._format_json(data)
        parsed = json.loads(result)
        assert parsed == data

    def test_format_json_includes_trailing_newline(self) -> None:
        """Verify _format_json output ends with a newline.

        Tests: Trailing newline in _format_json output
        How: Check last character
        Why: POSIX text files require trailing newline
        """
        data = {"name": "test"}
        result = auto_sync._format_json(data)
        assert result.endswith("\n")

    def test_format_json_uses_two_space_indent(self) -> None:
        """Verify _format_json uses json.dumps(indent=2) format exactly.

        Tests: Format matches json.dumps(indent=2) + newline
        How: Compare output with expected json.dumps output
        Why: _format_json is now a thin wrapper around json.dumps
        """
        data = {"name": "test", "version": "1.0.0"}
        result = auto_sync._format_json(data)
        expected = json.dumps(data, indent=2) + "\n"
        assert result == expected


# ============================================================================
# New behaviour: Idempotent writes (Bug 2 fix)
# ============================================================================


class TestIdempotentWrites:
    """Test that the version-comparison guard prevents double-bumping on retry.

    The primary defence against double-bumping is ``_version_already_bumped``.
    When run 1 writes a bumped version, run 2 (retry) sees the file version >
    HEAD version and returns early.  An additional ``new_content == existing_content``
    check provides a secondary safety net.
    """

    def test_update_plugin_json_is_noop_on_second_run(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify second run is blocked by version comparison guard.

        Tests: Version guard prevents double-bump for plugin.json
        How: Run update twice; second run detects version already > HEAD
        Why: Prevents version double-bump when commit fails and user retries
        """
        monkeypatch.chdir(tmp_path)

        plugin_name = "test-plugin"
        original_data = {"name": "test-plugin", "version": "1.0.0", "skills": ["./skills/existing/"]}
        _make_plugin_json(tmp_path, plugin_name, original_data)

        changes = _changes_with_modified_skill()

        # Simulate HEAD having the original version
        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: dict(original_data))

        # Run 1: should update (1.0.0 == HEAD 1.0.0, so bump proceeds)
        updated_1, version_1 = auto_sync.update_plugin_json(plugin_name, changes)
        assert updated_1 is True
        assert version_1 == "1.0.1"

        # Run 2: version guard blocks (1.0.1 > HEAD 1.0.0)
        updated_2, version_2 = auto_sync.update_plugin_json(plugin_name, changes)
        assert updated_2 is False
        assert version_2 == "1.0.1"

    def test_update_marketplace_json_is_noop_on_second_run(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify second run is blocked by version comparison guard.

        Tests: Version guard prevents double-bump for marketplace.json
        How: Run update twice; second run detects version already > HEAD
        Why: Prevents version double-bump in marketplace manifest
        """
        monkeypatch.chdir(tmp_path)

        original_data = {
            "metadata": {"version": "1.0.0"},
            "plugins": [{"name": "existing", "source": "./plugins/existing"}],
        }
        _make_marketplace_json(tmp_path, original_data)

        plugin_changes: _MarketplaceChangesDict = {
            "added": set(),
            "deleted": set(),
            "modified": [("existing", "1.0.1")],
        }

        # Simulate HEAD having the original version
        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: dict(original_data))

        # Run 1: should update
        updated_1 = auto_sync.update_marketplace_json(plugin_changes)
        assert updated_1 is True

        # Run 2: version guard blocks (1.0.1 > HEAD 1.0.0)
        updated_2 = auto_sync.update_marketplace_json(plugin_changes)
        assert updated_2 is False

        # Verify version was only bumped once
        marketplace_json = tmp_path / ".claude-plugin" / "marketplace.json"
        final_data = json.loads(marketplace_json.read_text(encoding="utf-8"))
        assert final_data["metadata"]["version"] == "1.0.1"

    def test_update_plugin_json_version_stays_at_single_bump(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify version guard prevents multiple bumps across retries.

        Tests: Multiple consecutive runs with version guard
        How: Run update once, then run two more times
        Why: Stress test the double-bump prevention mechanism
        """
        monkeypatch.chdir(tmp_path)

        plugin_name = "test-plugin"
        original_data = {"name": "test-plugin", "version": "1.0.0", "skills": []}
        plugin_json = _make_plugin_json(tmp_path, plugin_name, original_data)

        changes = _changes_with_modified_skill()

        # Simulate HEAD having the original version
        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: dict(original_data))

        # Run 1: bumps to 1.0.1
        auto_sync.update_plugin_json(plugin_name, changes)
        # Runs 2-3: version guard blocks (1.0.1 > HEAD 1.0.0)
        auto_sync.update_plugin_json(plugin_name, changes)
        auto_sync.update_plugin_json(plugin_name, changes)

        # Final version should be 1.0.1, not 1.0.3
        final_data = json.loads(plugin_json.read_text(encoding="utf-8"))
        assert final_data["version"] == "1.0.1"


# ============================================================================
# Area 4: Non-component file change tracking
# ============================================================================


class TestNonComponentFileTracking:
    """Test that non-component files inside plugin dirs trigger patch bumps.

    Files like scripts/, tests/, CLAUDE.md, README.md are inside plugin
    directories but do not match a recognized component_type in
    parse_plugin_path.  These changes should still appear in the modified
    list so the plugin version gets a patch bump.
    """

    def test_script_file_modification_recorded(self) -> None:
        """Verify modifying a script file inside a plugin triggers tracking.

        Tests: _process_file_changes with modified scripts/bar.py
        How: Pass status with a modified script path
        Why: Scripts are non-component files that should still trigger a version bump
        """
        status: dict[str, list[str]] = {"added": [], "deleted": [], "modified": ["plugins/foo/scripts/bar.py"]}

        component_changes, _ = auto_sync._process_file_changes(status)

        assert "foo" in component_changes
        assert len(component_changes["foo"]["modified"]) == 1
        assert component_changes["foo"]["modified"][0]["component_type"] == "other"
        assert component_changes["foo"]["modified"][0]["component_path"] == "scripts/bar.py"

    def test_test_file_modification_recorded(self) -> None:
        """Verify modifying a test file inside a plugin triggers tracking.

        Tests: _process_file_changes with modified tests/test_bar.py
        How: Pass status with a modified test path
        Why: Test files are non-component files that should trigger a version bump
        """
        status: dict[str, list[str]] = {"added": [], "deleted": [], "modified": ["plugins/foo/tests/test_bar.py"]}

        component_changes, _ = auto_sync._process_file_changes(status)

        assert "foo" in component_changes
        assert len(component_changes["foo"]["modified"]) == 1
        assert component_changes["foo"]["modified"][0]["component_type"] == "other"
        assert component_changes["foo"]["modified"][0]["component_path"] == "tests/test_bar.py"

    def test_claude_md_modification_recorded(self) -> None:
        """Verify modifying CLAUDE.md inside a plugin triggers tracking.

        Tests: _process_file_changes with modified CLAUDE.md
        How: Pass status with a modified CLAUDE.md path
        Why: CLAUDE.md is a non-component file that should trigger a version bump
        """
        status: dict[str, list[str]] = {"added": [], "deleted": [], "modified": ["plugins/foo/CLAUDE.md"]}

        component_changes, _ = auto_sync._process_file_changes(status)

        assert "foo" in component_changes
        assert len(component_changes["foo"]["modified"]) == 1
        assert component_changes["foo"]["modified"][0]["component_type"] == "other"
        assert component_changes["foo"]["modified"][0]["component_path"] == "CLAUDE.md"

    def test_readme_modification_recorded(self) -> None:
        """Verify modifying README.md inside a plugin triggers tracking.

        Tests: _process_file_changes with modified README.md
        How: Pass status with a modified README.md path
        Why: README.md is a non-component file that should trigger a version bump
        """
        status: dict[str, list[str]] = {"added": [], "deleted": [], "modified": ["plugins/foo/README.md"]}

        component_changes, _ = auto_sync._process_file_changes(status)

        assert "foo" in component_changes
        assert len(component_changes["foo"]["modified"]) == 1
        assert component_changes["foo"]["modified"][0]["component_type"] == "other"
        assert component_changes["foo"]["modified"][0]["component_path"] == "README.md"

    def test_plugin_json_modification_recorded_as_other_component(self) -> None:
        """Verify plugin.json modifications ARE tracked as 'other' component changes.

        Tests: _process_file_changes records plugin.json modifications as component changes
        How: Pass status with a modified .claude-plugin/plugin.json path
        Why: plugin.json modification (not add/delete) triggers a patch version bump via
             the 'other' component type, so it must appear in component_changes
        """
        status: dict[str, list[str]] = {
            "added": [],
            "deleted": [],
            "modified": ["plugins/foo/.claude-plugin/plugin.json"],
        }

        component_changes, _ = auto_sync._process_file_changes(status)

        # plugin.json modification creates an 'other' component change entry
        assert "foo" in component_changes
        assert len(component_changes["foo"]["modified"]) == 1
        assert component_changes["foo"]["modified"][0]["component_type"] == "other"

    def test_added_non_component_file_recorded(self) -> None:
        """Verify adding a non-component file inside a plugin triggers tracking.

        Tests: _process_file_changes with added non-component file
        How: Pass status with an added script path
        Why: Added non-component files should also trigger a patch bump
        """
        status: dict[str, list[str]] = {"added": ["plugins/foo/scripts/new_script.py"], "deleted": [], "modified": []}

        component_changes, _ = auto_sync._process_file_changes(status)

        assert "foo" in component_changes
        assert len(component_changes["foo"]["modified"]) == 1
        assert component_changes["foo"]["modified"][0]["component_type"] == "other"

    def test_deleted_non_component_file_recorded(self) -> None:
        """Verify deleting a non-component file inside a plugin triggers tracking.

        Tests: _process_file_changes with deleted non-component file
        How: Pass status with a deleted test path
        Why: Deleted non-component files should also trigger a patch bump
        """
        status: dict[str, list[str]] = {"added": [], "deleted": ["plugins/foo/tests/old_test.py"], "modified": []}

        component_changes, _ = auto_sync._process_file_changes(status)

        assert "foo" in component_changes
        assert len(component_changes["foo"]["modified"]) == 1
        assert component_changes["foo"]["modified"][0]["component_type"] == "other"

    def test_non_component_change_triggers_patch_bump(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify non-component changes result in a patch version bump.

        Tests: End-to-end flow from _process_file_changes through update_plugin_json
        How: Process a non-component file change, pass to update_plugin_json
        Why: Ensures the entire pipeline correctly bumps the version
        """
        monkeypatch.chdir(tmp_path)

        plugin_name = "foo"
        original_data = {"name": "foo", "version": "1.0.0", "skills": []}
        _make_plugin_json(tmp_path, plugin_name, original_data)

        status: dict[str, list[str]] = {"added": [], "deleted": [], "modified": ["plugins/foo/scripts/helper.py"]}

        component_changes, _ = auto_sync._process_file_changes(status)

        updated, new_version = auto_sync.update_plugin_json(plugin_name, component_changes[plugin_name])

        assert updated is True
        assert new_version == "1.0.1"


# ============================================================================
# Area 7: Skill discovery — scripts must not be registered as skills
# ============================================================================


class TestDiscoverSkills:
    """Verify _discover_skills only returns skill directories, not scripts."""

    def test_discovers_skill_directory_with_skill_md(self, tmp_path: Path) -> None:
        """A directory with SKILL.md is discovered as a skill.

        Tests: Basic skill discovery for a well-formed skill directory
        How: Create skills/my-skill/SKILL.md and call _discover_skills
        Why: Ensures the core discovery path works
        """
        plugin_dir = tmp_path / "plugins" / "test-plugin"
        skill_dir = plugin_dir / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# My Skill\n")

        result = auto_sync._discover_skills(plugin_dir)

        assert result == ["./skills/my-skill"]

    def test_scripts_in_skill_dir_not_discovered_as_skills(self, tmp_path: Path) -> None:
        """Python scripts inside a skill's scripts/ dir must NOT appear as skills.

        Tests: Bug fix — scripts were incorrectly added to the skills array
        How: Create skills/my-skill/scripts/*.py and verify they are excluded
        Why: Scripts are companion utilities, not skills. The plugin.json skills
             array should only contain skill directory paths per the plugin spec.
        """
        plugin_dir = tmp_path / "plugins" / "test-plugin"
        skill_dir = plugin_dir / "skills" / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# My Skill\n")
        (scripts_dir / "helper.py").write_text("print('hello')\n")
        (scripts_dir / "evaluate.py").write_text("print('eval')\n")

        result = auto_sync._discover_skills(plugin_dir)

        assert result == ["./skills/my-skill"]
        assert not any("/scripts/" in p for p in result)

    def test_multiple_skills_with_scripts_excluded(self, tmp_path: Path) -> None:
        """Multiple skills with scripts/ dirs — only skill dirs appear.

        Tests: Multiple skills each having scripts/ subdirectories
        How: Create two skill dirs each with scripts/*.py, verify only dirs returned
        Why: Ensures the fix works across all skills in a plugin, not just one
        """
        plugin_dir = tmp_path / "plugins" / "test-plugin"
        for name in ("alpha", "beta"):
            skill_dir = plugin_dir / "skills" / name
            scripts_dir = skill_dir / "scripts"
            scripts_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(f"# {name}\n")
            (scripts_dir / "run.py").write_text("pass\n")

        result = auto_sync._discover_skills(plugin_dir)

        assert result == ["./skills/alpha", "./skills/beta"]

    def test_nested_skills_not_discovered(self, tmp_path: Path) -> None:
        """Nested skill directories (e.g., skills/testing/unit) are NOT discovered.

        Tests: Discovery enforces the flat skills/{name}/ constraint — subdirectory
               nesting is not a supported skill layout.
        How: Create skills/testing/unit-tests/SKILL.md (nested) and verify the result
             is an empty list — no nested path is returned.
        Why: Skills must be directly under skills/. Nested directories are not valid
             skill locations; discovery must not register them.
        """
        plugin_dir = tmp_path / "plugins" / "test-plugin"
        parent = plugin_dir / "skills" / "testing"
        parent.mkdir(parents=True)
        child = parent / "unit-tests"
        child.mkdir()
        (child / "SKILL.md").write_text("# Unit Tests\n")

        result = auto_sync._discover_skills(plugin_dir)

        assert result == []

    def test_no_skills_directory(self, tmp_path: Path) -> None:
        """Plugin with no skills/ directory returns empty list.

        Tests: Edge case — no skills directory at all
        How: Call _discover_skills on a plugin dir without skills/
        Why: Ensures graceful handling of plugins that have no skills
        """
        plugin_dir = tmp_path / "plugins" / "test-plugin"
        plugin_dir.mkdir(parents=True)

        result = auto_sync._discover_skills(plugin_dir)

        assert result == []


class TestFindStaleItemsScripts:
    """Verify _find_stale_items correctly identifies script entries as stale."""

    def test_undiscovered_entries_are_stale(self) -> None:
        """Registered entries not in the discovery list are stale.

        Tests: Core stale detection — discovery is the sole authority
        How: Pass entries as registered with no matching disk_items
        Why: Anything not returned by discovery does not belong in the array
        """
        registered = [
            "./skills/my-skill",
            "./skills/my-skill/scripts/helper.py",
            "./skills/my-skill/scripts/evaluate.py",
        ]
        disk_items = ["./skills/my-skill"]

        stale = auto_sync._find_stale_items(registered, disk_items, normalize=True)

        assert "./skills/my-skill/scripts/helper.py" in stale
        assert "./skills/my-skill/scripts/evaluate.py" in stale
        assert "./skills/my-skill" not in stale

    def test_disk_existence_does_not_protect_undiscovered_entries(self, tmp_path: Path) -> None:
        """Files existing on disk are stale if not in the discovery list.

        Tests: Discovery is sole authority — filesystem existence is irrelevant
        How: Entries that exist on disk but are not discovered are still stale
        Why: The discovery functions define what belongs in each component
             array. Disk existence is not a factor.
        """
        registered = [
            "./skills/my-skill",
            "./skills/my-skill/scripts/helper.py",
            "./skills/summarizer/templates/bullets.md",
        ]
        disk_items = ["./skills/my-skill"]

        stale = auto_sync._find_stale_items(registered, disk_items, normalize=True)

        assert "./skills/my-skill" not in stale
        assert "./skills/my-skill/scripts/helper.py" in stale
        assert "./skills/summarizer/templates/bullets.md" in stale

    def test_bare_directory_refs_are_stale(self) -> None:
        """Bare directory references like ./skills are stale.

        Tests: Redundant directory refs are detected as stale
        How: Register ./skills (bare dir), discovery returns specific paths
        Why: Auto-discovery already loads default directories. Bare refs
             are redundant and should be removed by reconcile.
        """
        registered = ["./skills", "./skills/my-skill"]
        disk_items = ["./skills/my-skill"]

        stale = auto_sync._find_stale_items(registered, disk_items, normalize=True)

        assert "./skills" in stale
        assert "./skills/my-skill" not in stale


# ============================================================================
# Area 8: _precommit_sync structural marketplace updates (no version bump)
# ============================================================================


class TestPrecommitSyncMarketplaceStructural:
    """Verify _precommit_sync updates plugin list structure without bumping version.

    With the post-merge CI model, version bumping is deferred; _precommit_sync
    must only apply add/delete structural changes (no version increment).
    """

    def test_precommit_sync_adds_plugin_to_list_without_version_bump(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify new plugin is written to marketplace list but version unchanged.

        Tests: _precommit_sync structural-only write path for added plugin
        How: Stage a new plugin.json (added), mock git status, run _precommit_sync,
             assert plugin list updated and version unchanged.
        Why: Confirms the pre-commit hook no longer bumps marketplace version —
             only the CI post-merge mode does that.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        # Create the new plugin's plugin.json on disk
        _make_plugin_json(tmp_path, "new-plugin", {"name": "new-plugin", "version": "0.1.0"})
        _make_marketplace_json(
            tmp_path,
            {"metadata": {"version": "2.3.0"}, "plugins": [{"name": "existing", "source": "./plugins/existing"}]},
        )

        # Mock git status to report new plugin's plugin.json as added
        staged_status = {"added": ["plugins/new-plugin/.claude-plugin/plugin.json"], "deleted": [], "modified": []}
        monkeypatch.setattr(auto_sync, "get_git_status", lambda: staged_status)
        monkeypatch.setattr(auto_sync, "_git_stage_file", lambda _fp: None)

        # Act
        exit_code = auto_sync._precommit_sync()

        # Assert exit ok
        assert exit_code == 0

        marketplace_json = tmp_path / ".claude-plugin" / "marketplace.json"
        data = json.loads(marketplace_json.read_text(encoding="utf-8"))

        # Version must NOT have changed
        assert data["metadata"]["version"] == "2.3.0"

        # New plugin must be in the list
        names = {p["name"] for p in data["plugins"]}
        assert "new-plugin" in names
        assert "existing" in names

    def test_precommit_sync_modify_only_leaves_marketplace_untouched(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify modify-only changes leave marketplace.json completely unmodified.

        Tests: _precommit_sync skips marketplace for modify-only operations
        How: Stage a modified skill file (not add/delete plugin), run _precommit_sync,
             assert marketplace.json byte-for-byte unchanged.
        Why: Confirm marketplace.json is not touched at all for non-structural changes.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        _make_plugin_json(tmp_path, "alpha", {"name": "alpha", "version": "1.0.0"})
        marketplace_json = _make_marketplace_json(
            tmp_path, {"metadata": {"version": "3.0.0"}, "plugins": [{"name": "alpha", "source": "./plugins/alpha"}]}
        )
        original_content = marketplace_json.read_text(encoding="utf-8")

        # Only a modified skill — no plugin add/delete
        staged_status = {"added": [], "deleted": [], "modified": ["plugins/alpha/skills/my-skill/SKILL.md"]}
        monkeypatch.setattr(auto_sync, "get_git_status", lambda: staged_status)
        monkeypatch.setattr(auto_sync, "_git_stage_file", lambda _fp: None)
        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: {"name": "alpha", "version": "0.9.9"})

        # Act
        exit_code = auto_sync._precommit_sync()

        # Assert
        assert exit_code == 0
        assert marketplace_json.read_text(encoding="utf-8") == original_content


# ============================================================================
# Area 9: _sync_marketplace_mode — post-merge CI marketplace sync
# ============================================================================


def _make_plugin_on_disk(base: Path, plugin_dir_name: str, plugin_name: str | None = None) -> Path:
    """Create a minimal plugin on disk with plugin.json.

    Args:
        base: Root directory (monkeypatched cwd).
        plugin_dir_name: Directory name under plugins/.
        plugin_name: Value for the "name" field; defaults to plugin_dir_name.

    Returns:
        Path to the .claude-plugin/ directory.
    """
    name = plugin_name or plugin_dir_name
    plugin_dir = base / "plugins" / plugin_dir_name / ".claude-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps({"name": name, "version": "1.0.0"}, indent=2) + "\n", encoding="utf-8"
    )
    return plugin_dir


class TestSyncMarketplaceMode:
    """Tests for _sync_marketplace_mode — post-merge CI path."""

    def test_sync_marketplace_mode_bumps_patch_when_no_structural_changes(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Verify patch bump when reconcile finds no structural changes.

        Tests: _sync_marketplace_mode patch-bump path
        How: One plugin on disk, marketplace already lists that plugin at 1.0.0;
             reconcile finds no missing/stale, so _sync_marketplace_mode does a patch bump.
        Why: Post-merge CI needs to reflect that plugin content changed even when
             no plugins were added or removed.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        _make_plugin_on_disk(tmp_path, "alpha")
        _make_marketplace_json(
            tmp_path, {"metadata": {"version": "1.0.0"}, "plugins": [{"name": "alpha", "source": "./plugins/alpha"}]}
        )

        # Suppress git add calls
        monkeypatch.setattr(auto_sync, "_git_stage_file", lambda _fp: None)

        # Act
        exit_code = auto_sync._sync_marketplace_mode()

        # Assert
        assert exit_code == 0
        marketplace_json = tmp_path / ".claude-plugin" / "marketplace.json"
        data = json.loads(marketplace_json.read_text(encoding="utf-8"))
        assert data["metadata"]["version"] == "1.0.1"

    def test_sync_marketplace_mode_delegates_to_reconcile_for_structural_changes(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Verify reconcile path fires when marketplace is out of sync with disk.

        Tests: _sync_marketplace_mode when reconcile detects a missing plugin
        How: Two plugins on disk, marketplace lists only one; _sync_marketplace_mode
             delegates to _reconcile_marketplace which adds the missing plugin and
             bumps the minor version.
        Why: Structural changes (plugin added/removed) must update the plugin list
             and bump version accordingly.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        _make_plugin_on_disk(tmp_path, "alpha")
        _make_plugin_on_disk(tmp_path, "beta")
        _make_marketplace_json(
            tmp_path, {"metadata": {"version": "1.0.0"}, "plugins": [{"name": "alpha", "source": "./plugins/alpha"}]}
        )

        monkeypatch.setattr(auto_sync, "_git_stage_file", lambda _fp: None)

        # Act
        exit_code = auto_sync._sync_marketplace_mode()

        # Assert
        assert exit_code == 0
        marketplace_json = tmp_path / ".claude-plugin" / "marketplace.json"
        data = json.loads(marketplace_json.read_text(encoding="utf-8"))

        # Reconcile bumped minor version because a plugin was added
        _major, minor, _patch = map(int, data["metadata"]["version"].split("."))
        assert minor >= 1, f"Expected minor bump, got {data['metadata']['version']}"

        # beta is now in the plugin list
        names = {p["name"] for p in data["plugins"]}
        assert "beta" in names
        assert "alpha" in names

    def test_sync_marketplace_mode_returns_1_when_marketplace_missing(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Verify exit code 1 when marketplace.json does not exist.

        Tests: _sync_marketplace_mode error path — missing marketplace.json
        How: Create a plugins/ dir but no .claude-plugin/marketplace.json
        Why: The function must fail fast with a clear error rather than creating
             or silently skipping marketplace.json.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        (tmp_path / "plugins").mkdir()

        # Act
        exit_code = auto_sync._sync_marketplace_mode()

        # Assert
        assert exit_code == 1


# ============================================================================
# Phase 1 — Base-ref refactor: behavioral RED tests
#
# These tests define the contract for the origin/main → main → HEAD resolver
# refactor described in .tmp/scratch/reports/version-bump-adversarial.md.
#
# Mock seams introduced by this refactor (not yet present in the codebase):
#   resolve_base() -> str | None
#       Returns the best available base ref: "origin/main" → "main" → None
#       (HEAD is the terminal fallback when None is returned).
#   read_ref_json(ref: str, filepath: str | Path) -> object | None
#       Reads a JSON file at the given git ref. Replaces the HEAD-specific
#       _read_head_json for base-version resolution.
#
# RED rationale per test is documented in the "Why RED" comment.
# ============================================================================


class TestWorkingBehindBase:
    """Test the working < base scenario — the only behavior the refactor changes.

    Report table (adversarial.md lines 57-61):
        working < base  →  CURRENT behavior wrong; refactor yields base + step
        working == base →  behavior unchanged (base+step == current+step)
        working > base  →  behavior unchanged (guard skips both ways)
    """

    def test_working_behind_base_bumps_from_base_not_working(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Working copy behind main: version must be derived from base, not from working.

        Tests: update_plugin_json — working < base scenario (THE FIX)
        How: Plugin file at 1.2.1; base (origin/main) at 1.2.5; patch change.
             Expect result 1.2.6 (base + patch step), NOT 1.2.2 (working + step).
        Why: Two concurrent PR branches both start at 1.2.0.  Branch A merges and
             main advances to 1.2.1.  Branch B rebases; its working copy is still
             at 1.2.1 (already bumped on the branch) but base is now 1.2.5 (after
             further merges).  The hook must derive the new version from base so
             branch B yields 1.2.6, not a collision at 1.2.2.

        Why RED: Current code bumps from current_version (1.2.1) → 1.2.2.
                 The new seams resolve_base / read_ref_json do not exist yet →
                 AttributeError for seam-based path; wrong value for HEAD-fallback
                 path.  Either way the assertion 1.2.6 fails today.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        plugin_name = "test-plugin"
        # Working copy is at 1.2.1 — already bumped on the branch
        working_data = {"name": "test-plugin", "version": "1.2.1", "skills": ["./skills/my-skill"]}
        plugin_json = _make_plugin_json(tmp_path, plugin_name, working_data)

        # Base (origin/main) is at 1.2.5 — main advanced after branch B diverged
        base_data = {"name": "test-plugin", "version": "1.2.5", "skills": ["./skills/my-skill"]}

        # Post-refactor seam: resolve_base returns "origin/main"; read_ref_json
        # returns the base version when asked to read at that ref.
        monkeypatch.setattr(auto_sync, "resolve_base", lambda: "origin/main")
        monkeypatch.setattr(auto_sync, "read_ref_json", lambda _ref, _fp: dict(base_data))

        changes = _changes_with_modified_skill()

        # Act
        updated, version = auto_sync.update_plugin_json(plugin_name, changes)

        # Assert — version derived from base (1.2.5 + patch = 1.2.6), not from working (1.2.2)
        assert updated is True
        assert version == "1.2.6"
        assert json.loads(plugin_json.read_text(encoding="utf-8"))["version"] == "1.2.6"

    def test_working_ahead_of_base_skips_bump(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Working copy already ahead of base: guard must skip the bump.

        Tests: update_plugin_json — working > base with HEAD ≠ base
        How: Working=1.2.1, HEAD=1.2.1, base=1.2.0.  The working copy has been
             bumped on this branch (working > base).  Expect skip.

        Why RED: Current guard compares working vs HEAD (both 1.2.1 → equal →
                 not "already bumped" → proceeds to bump to 1.2.2).
                 Post-refactor guard compares working vs base (1.2.1 > 1.2.0 →
                 skips).  Current code bumps when it should skip, so assertion
                 updated is False fails today.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        plugin_name = "test-plugin"
        # Working copy already bumped on this branch to 1.2.1
        working_data = {"name": "test-plugin", "version": "1.2.1", "skills": []}
        _make_plugin_json(tmp_path, plugin_name, working_data)

        # HEAD is also 1.2.1 — this branch's last commit already has the bump
        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: {"name": "test-plugin", "version": "1.2.1"})

        # Base (origin/main) is 1.2.0 — the branch diverged from 1.2.0
        base_data = {"name": "test-plugin", "version": "1.2.0", "skills": []}
        monkeypatch.setattr(auto_sync, "resolve_base", lambda: "origin/main")
        monkeypatch.setattr(auto_sync, "read_ref_json", lambda _ref, _fp: dict(base_data))

        changes = _changes_with_modified_skill()

        # Act
        updated, version = auto_sync.update_plugin_json(plugin_name, changes)

        # Assert — guard skips: working (1.2.1) already ahead of base (1.2.0)
        assert updated is False
        assert version == "1.2.1"

    def test_working_equals_base_bumps_normally(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Working == base: hook bumps normally; behavior unchanged from today.

        Tests: update_plugin_json — working == base, normal bump path
        How: Both file and base at 1.2.0; patch change → expect 1.2.1.
        Why: Report line 60 confirms this case is unchanged (base+step == current+step).
             Included as a regression guard alongside the working < base fix.

        Why RED: resolve_base / read_ref_json not yet present → AttributeError.
                 The assertion value (1.2.1) matches current output, but the test
                 fails because the seam attributes are absent.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        plugin_name = "test-plugin"
        working_data = {"name": "test-plugin", "version": "1.2.0", "skills": []}
        _make_plugin_json(tmp_path, plugin_name, working_data)

        base_data = {"name": "test-plugin", "version": "1.2.0", "skills": []}
        monkeypatch.setattr(auto_sync, "resolve_base", lambda: "main")
        monkeypatch.setattr(auto_sync, "read_ref_json", lambda _ref, _fp: dict(base_data))

        changes = _changes_with_modified_skill()

        # Act
        updated, version = auto_sync.update_plugin_json(plugin_name, changes)

        # Assert — normal bump proceeds: 1.2.0 + patch = 1.2.1
        assert updated is True
        assert version == "1.2.1"

    def test_manual_bump_preserved_when_working_far_ahead_of_base(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Manual major/minor bump is not clobbered by the hook.

        Tests: update_plugin_json — manual bump safety property (q1 from adversarial.md)
        How: Developer manually sets version to 2.0.0; base is 1.2.0.
             working (2.0.0) > base (1.2.0) → guard skips; 2.0.0 preserved.
        Why: Adversarial.md challenge q1 confirms any manual bump makes
             working > base, which trips the guard.  This test locks that in.

        Why RED: resolve_base / read_ref_json not yet present → AttributeError.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        plugin_name = "test-plugin"
        working_data = {"name": "test-plugin", "version": "2.0.0", "skills": []}
        _make_plugin_json(tmp_path, plugin_name, working_data)

        base_data = {"name": "test-plugin", "version": "1.2.0", "skills": []}
        monkeypatch.setattr(auto_sync, "resolve_base", lambda: "origin/main")
        monkeypatch.setattr(auto_sync, "read_ref_json", lambda _ref, _fp: dict(base_data))

        changes = _changes_with_modified_skill()

        # Act
        updated, version = auto_sync.update_plugin_json(plugin_name, changes)

        # Assert — manual bump preserved; hook does not overwrite 2.0.0
        assert updated is False
        assert version == "2.0.0"


class TestResolveBase:
    """Test the resolve_base() function — ref resolution order contract.

    Contract: origin/main → main → None (HEAD is caller's terminal fallback).
    All tests are seam-level RED: resolve_base does not exist yet.
    """

    def test_resolve_base_prefers_origin_main(self, monkeypatch: Any) -> None:
        """When origin/main is present, resolve_base must return 'origin/main'.

        Tests: resolve_base resolution order — origin/main available
        How: Monkeypatch subprocess so git rev-parse --verify origin/main exits 0.
        Why: origin/main is the freshest available base and should be preferred
             over local main per adversarial.md Approach A.

        Why RED: resolve_base does not exist → AttributeError.
        """
        import subprocess as _subprocess

        def _fake_run(cmd: list[str], **_kwargs: Any) -> Any:
            """Return success for origin/main, failure for everything else."""

            class _Result:
                returncode: int

            r = _Result()
            if "origin/main" in cmd:
                r.returncode = 0
            else:
                r.returncode = 1
            return r

        monkeypatch.setattr(_subprocess, "run", _fake_run)

        # Act
        result = auto_sync.resolve_base()

        # Assert
        assert result == "origin/main"

    def test_resolve_base_falls_back_to_main_when_origin_absent(self, monkeypatch: Any) -> None:
        """When origin/main is absent but main is present, resolve_base returns 'main'.

        Tests: resolve_base resolution order — main fallback
        How: Monkeypatch subprocess so origin/main fails, main succeeds.
        Why: Local main is the next-best base when origin is unavailable
             (shallow clone, fresh checkout).

        Why RED: resolve_base does not exist → AttributeError.
        """
        import subprocess as _subprocess

        def _fake_run(cmd: list[str], **_kwargs: Any) -> Any:
            class _Result:
                returncode: int

            r = _Result()
            r.returncode = 0 if "main" in cmd and "origin/main" not in cmd else 1
            return r

        monkeypatch.setattr(_subprocess, "run", _fake_run)

        result = auto_sync.resolve_base()

        assert result == "main"

    def test_resolve_base_returns_none_when_neither_ref_present(self, monkeypatch: Any) -> None:
        """When neither origin/main nor main is present, resolve_base returns None.

        Tests: resolve_base resolution order — neither ref present
        How: Monkeypatch subprocess so all rev-parse calls fail (shallow CI clone).
        Why: In the manifest-sync CI job, fetch-depth: 1 means origin/main is
             absent.  The caller uses HEAD as the terminal fallback when None.

        Why RED: resolve_base does not exist → AttributeError.
        """
        import subprocess as _subprocess

        def _fake_run(_cmd: list[str], **_kwargs: Any) -> Any:
            class _Result:
                returncode = 1

            return _Result()

        monkeypatch.setattr(_subprocess, "run", _fake_run)

        result = auto_sync.resolve_base()

        assert result is None


class TestGracefulFallbackNoBaseRef:
    """Test that the hook degrades to HEAD-based behavior when no base ref exists.

    When origin/main and main are both absent (fresh clone, CI shallow checkout),
    the hook must not raise and must exit 0 with a sensible version bump.
    """

    def test_update_plugin_json_exits_cleanly_when_base_unavailable(self, tmp_path: Path, monkeypatch: Any) -> None:
        """No base ref → hook falls back to HEAD comparison without crashing.

        Tests: Graceful degradation in update_plugin_json when resolve_base → None
        How: resolve_base returns None (no origin/main, no main); _read_head_json
             returns the current committed version (1.2.0); working file also 1.2.0.
             Expect normal patch bump to 1.2.1 (same as today's HEAD-based behavior).
        Why: Adversarial.md challenge q2 — terminal HEAD fallback is non-negotiable.
             CI manifest-sync runs with fetch-depth: 1; must not crash.

        Why RED: resolve_base does not exist → AttributeError.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        plugin_name = "test-plugin"
        working_data = {"name": "test-plugin", "version": "1.2.0", "skills": []}
        _make_plugin_json(tmp_path, plugin_name, working_data)

        # No base ref available — resolve_base returns None
        monkeypatch.setattr(auto_sync, "resolve_base", lambda: None)

        # HEAD has the same version (normal commit scenario)
        monkeypatch.setattr(auto_sync, "_read_head_json", lambda _fp: {"name": "test-plugin", "version": "1.2.0"})

        changes = _changes_with_modified_skill()

        # Act — must not raise; must return valid (updated, version) tuple
        updated, version = auto_sync.update_plugin_json(plugin_name, changes)

        # Assert — falls back to HEAD-based path; bumps normally; no crash
        assert updated is True
        assert version == "1.2.1"


# ============================================================================
# Area N: read_ref_json integration tests — real git subprocess
# ============================================================================

# integration: exercises real git subprocess


# Minimal environment for hermetic git operations.  Only PATH is inherited so
# git can locate its binary; all identity fields are set explicitly to avoid
# depending on the host global git config or commit-signing settings.
_GIT_ENV: dict[str, str] = {
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "t@t",
    "PATH": os.environ["PATH"],
}


def _init_git_repo(repo: Path, *, files: dict[str, str]) -> None:
    """Initialise a minimal git repo in *repo* with one commit containing *files*.

    Args:
        repo: Directory to initialise as a git repo (must already exist).
        files: Mapping of relative path → file content to write and commit.
    """

    def _run(*args: str) -> None:
        subprocess.run(list(args), cwd=repo, check=True, capture_output=True, env=_GIT_ENV)

    _run("git", "init")
    _run("git", "config", "commit.gpgsign", "false")
    _run("git", "config", "user.email", "t@t")
    _run("git", "config", "user.name", "Test")

    for rel_path, content in files.items():
        full_path = repo / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        _run("git", "add", rel_path)

    _run("git", "commit", "-m", "initial")


def _git_commit_file(repo: Path, rel_path: str, content: str, message: str = "update") -> None:
    """Overwrite *rel_path* in *repo* and create a new commit.

    Args:
        repo: Root of the git repository.
        rel_path: Repo-root-relative path of the file to update.
        content: New file content.
        message: Commit message.
    """
    full_path = repo / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", rel_path], cwd=repo, check=True, capture_output=True, env=_GIT_ENV)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True, capture_output=True, env=_GIT_ENV)


@pytest.mark.integration
class TestReadRefJson:
    """Integration tests for read_ref_json — exercises the real git subprocess.

    These tests use tmp_path and real git repos so that the ``git show
    {ref}:{path}`` subprocess at line 360 of auto_sync_manifests.py is
    exercised against actual commits, not mocked return values.

    Coverage target: lines 355-368 (the non-HEAD branch of read_ref_json).
    """

    def test_read_ref_json_returns_content_at_ref(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Reading HEAD returns the committed JSON dict for that path.

        Tests: read_ref_json delegation to _read_head_json when ref == "HEAD"
        How: Create a temp git repo with a committed plugin.json; call
             read_ref_json("HEAD", path) and assert the returned dict matches
             the written content.
        Why: Verifies that the HEAD-delegation path produces the correct result
             so callers can rely on it when no historical ref is needed.
        """
        # Arrange
        data = {"name": "my-plugin", "version": "1.0.0"}
        rel_path = ".claude-plugin/plugin.json"
        _init_git_repo(tmp_path, files={rel_path: json.dumps(data)})
        monkeypatch.chdir(tmp_path)

        # Act
        result = auto_sync.read_ref_json("HEAD", rel_path)

        # Assert
        assert result == data

    def test_read_ref_json_reads_historical_ref(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Reading HEAD~1 returns the committed JSON at that older commit.

        Tests: read_ref_json git-show subprocess for non-HEAD refs (line 360)
        How: Commit plugin.json with version "1.0.0", then commit again with
             "2.0.0".  Call read_ref_json("HEAD~1", path) and assert version
             is "1.0.0" (historical state, not working tree or HEAD).
        Why: This is the core mechanism of the fix — reading base version from
             origin/main must return the *committed* content at that ref, not
             the current working copy.  This test is the only one that directly
             exercises line 360.
        """
        # Arrange
        rel_path = ".claude-plugin/plugin.json"
        _init_git_repo(tmp_path, files={rel_path: json.dumps({"version": "1.0.0"})})
        _git_commit_file(tmp_path, rel_path, json.dumps({"version": "2.0.0"}), message="bump to 2.0.0")
        monkeypatch.chdir(tmp_path)

        # Act — read the first commit, not HEAD
        result = auto_sync.read_ref_json("HEAD~1", rel_path)

        # Assert — historical content, not current
        assert isinstance(result, dict)
        assert result["version"] == "1.0.0"

    def test_read_ref_json_returns_none_for_missing_file(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Returns None when the path does not exist at HEAD — no exception raised.

        Tests: read_ref_json HEAD delegation → _read_head_json non-zero exit
        How: Initialise a temp git repo (no plugin.json committed) and call
             read_ref_json("HEAD", "nonexistent/path.json").
        Why: Callers depend on None-return-on-absence to detect an unversioned
             plugin; any exception here would crash the pre-commit hook.
        """
        # Arrange — repo has no file at the queried path
        _init_git_repo(tmp_path, files={"README.md": "hello"})
        monkeypatch.chdir(tmp_path)

        # Act
        result = auto_sync.read_ref_json("HEAD", "nonexistent/path.json")

        # Assert
        assert result is None

    def test_read_ref_json_returns_none_for_invalid_ref(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Returns None when the git ref does not exist — no exception raised.

        Tests: read_ref_json git-show subprocess non-zero exit (line 361-362)
        How: Initialise a temp git repo and call read_ref_json with a branch
             name that was never created.
        Why: When origin/main does not exist (fresh clone, shallow fetch),
             git show exits non-zero.  The hook must treat this as "no base
             version" and fall back gracefully rather than propagating an error.
        """
        # Arrange — repo exists but the queried ref does not
        _init_git_repo(tmp_path, files={".claude-plugin/plugin.json": json.dumps({"version": "1.0.0"})})
        monkeypatch.chdir(tmp_path)

        # Act
        result = auto_sync.read_ref_json("nonexistent-branch", ".claude-plugin/plugin.json")

        # Assert
        assert result is None
