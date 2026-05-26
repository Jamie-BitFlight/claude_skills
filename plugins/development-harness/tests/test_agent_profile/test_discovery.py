"""Unit tests for agent_profile.discovery module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from agent_profile.discovery import find_agent, scan_all_agents
from agent_profile.models import AgentEntry

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# scan_all_agents
# ---------------------------------------------------------------------------


class TestScanAllAgents:
    def test_finds_agents_in_single_plugin(self, single_plugin_root: Path) -> None:
        agents = scan_all_agents(single_plugin_root)
        names = [a.name for a in agents]
        assert "list-skills-agent" in names
        assert "csv-skills-agent" in names
        assert "no-skills-agent" in names

    def test_finds_agents_across_multiple_plugins(self, multi_plugin_root: Path) -> None:
        agents = scan_all_agents(multi_plugin_root)
        plugins = {a.plugin for a in agents}
        assert "alpha" in plugins
        assert "beta" in plugins

    def test_returns_agent_entry_objects(self, single_plugin_root: Path) -> None:
        agents = scan_all_agents(single_plugin_root)
        for agent in agents:
            assert isinstance(agent, AgentEntry)
            assert agent.path.exists()
            assert agent.path.suffix == ".md"

    def test_sorted_by_plugin_then_name(self, multi_plugin_root: Path) -> None:
        agents = scan_all_agents(multi_plugin_root)
        keys = [(a.plugin, a.name) for a in agents]
        assert keys == sorted(keys)

    def test_subdirectory_agent_produces_colon_name(self, single_plugin_root: Path) -> None:
        agents = scan_all_agents(single_plugin_root)
        names = [a.name for a in agents]
        assert "testing:unit-tester" in names

    def test_empty_plugins_root_returns_empty_list(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        plugins_root.mkdir()
        agents = scan_all_agents(plugins_root)
        assert agents == []

    def test_plugin_without_agents_dir_is_skipped(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        (plugins_root / "no-agents-plugin").mkdir(parents=True)
        agents = scan_all_agents(plugins_root)
        assert agents == []

    def test_plugin_field_matches_directory_name(self, single_plugin_root: Path) -> None:
        agents = scan_all_agents(single_plugin_root)
        for agent in agents:
            assert agent.plugin == "test-plugin"


# ---------------------------------------------------------------------------
# find_agent — bare name
# ---------------------------------------------------------------------------


class TestFindAgentBare:
    def test_finds_unique_bare_name(self, single_plugin_root: Path) -> None:
        agent = find_agent("list-skills-agent", single_plugin_root)
        assert agent.name == "list-skills-agent"
        assert agent.plugin == "test-plugin"

    def test_raises_file_not_found_for_missing_agent(self, single_plugin_root: Path) -> None:
        with pytest.raises(FileNotFoundError, match="nonexistent"):
            find_agent("nonexistent", single_plugin_root)

    def test_raises_value_error_for_ambiguous_bare_name(self, multi_plugin_root: Path) -> None:
        with pytest.raises(ValueError, match="shared-name"):
            find_agent("shared-name", multi_plugin_root)

    def test_error_message_lists_plugin_locations(self, multi_plugin_root: Path) -> None:
        with pytest.raises(ValueError, match="shared-name") as exc_info:
            find_agent("shared-name", multi_plugin_root)
        msg = str(exc_info.value)
        assert "alpha" in msg
        assert "beta" in msg


# ---------------------------------------------------------------------------
# find_agent — plugin-qualified name
# ---------------------------------------------------------------------------


class TestFindAgentPluginQualified:
    def test_finds_by_plugin_qualified_name(self, multi_plugin_root: Path) -> None:
        agent = find_agent("alpha:alpha-agent", multi_plugin_root)
        assert agent.name == "alpha-agent"
        assert agent.plugin == "alpha"

    def test_finds_agent_in_other_plugin_when_qualified(self, multi_plugin_root: Path) -> None:
        agent = find_agent("beta:beta-agent", multi_plugin_root)
        assert agent.name == "beta-agent"
        assert agent.plugin == "beta"

    def test_raises_file_not_found_for_missing_qualified_agent(self, multi_plugin_root: Path) -> None:
        with pytest.raises(FileNotFoundError):
            find_agent("alpha:nonexistent-agent", multi_plugin_root)

    def test_finds_subdirectory_agent_with_plugin_qualified_name(self, single_plugin_root: Path) -> None:
        agent = find_agent("test-plugin:testing:unit-tester", single_plugin_root)
        assert agent.name == "testing:unit-tester"
        assert agent.plugin == "test-plugin"

    def test_path_points_to_existing_file(self, multi_plugin_root: Path) -> None:
        agent = find_agent("alpha:alpha-agent", multi_plugin_root)
        assert agent.path.is_file()


# ---------------------------------------------------------------------------
# Manifest-name index and resolution (RED tests — all fail before implementation)
# ---------------------------------------------------------------------------


class TestBuildManifestNameIndex:
    def test_build_manifest_name_index_returns_mapping(self, manifest_plugin_root: Path) -> None:
        """_build_manifest_name_index must return a dict mapping manifest name 'dh'
        to the 'development-harness' plugin directory.

        Why: The index is the core lookup table that makes manifest-name → directory
        resolution possible. Without it, 'dh:*' agent lookups always fail.
        """
        # Arrange — manifest_plugin_root has development-harness/ with manifest name "dh"
        from agent_profile.discovery import _build_manifest_name_index

        # Act
        index = _build_manifest_name_index(manifest_plugin_root)

        # Assert
        assert "dh" in index
        assert index["dh"] == manifest_plugin_root / "development-harness"

    def test_build_manifest_name_index_handles_broken_manifest_gracefully(self, tmp_path: Path) -> None:
        """A malformed JSON manifest must be skipped, not raise, so sibling plugins
        remain resolvable.

        Why: A single bad manifest in a multi-plugin installation must not break
        all agent lookups. Graceful skip matches the 'log warning, continue' spec.
        """
        from agent_profile.discovery import _build_manifest_name_index

        # Arrange — one plugin with malformed JSON, one with valid manifest
        plugins_root = tmp_path / "plugins"
        broken_dir = plugins_root / "broken-plugin"
        (broken_dir / ".claude-plugin").mkdir(parents=True)
        (broken_dir / ".claude-plugin" / "plugin.json").write_text("{this is not valid json{{{{", encoding="utf-8")

        good_dir = plugins_root / "good-plugin"
        good_agents = good_dir / "agents"
        good_agents.mkdir(parents=True)
        (good_dir / ".claude-plugin").mkdir(parents=True)
        (good_dir / ".claude-plugin" / "plugin.json").write_text(
            '{"name": "good", "version": "1.0.0"}', encoding="utf-8"
        )

        # Act — must not raise despite broken sibling
        index = _build_manifest_name_index(plugins_root)

        # Assert — broken plugin absent, good plugin present
        assert "good" in index
        assert index["good"] == good_dir
        # broken plugin produced no entry (skipped, not raised)
        assert "broken-plugin" not in index

    def test_build_manifest_name_index_raises_on_duplicate_names(self, tmp_path: Path) -> None:
        """Two plugins declaring the same manifest name must raise ValueError.

        Why: Silently picking one would be non-deterministic on some filesystems.
        The spec requires an explicit error listing both conflicting paths.
        """
        from agent_profile.discovery import _build_manifest_name_index

        # Arrange — two plugins both declare name "shared"
        plugins_root = tmp_path / "plugins"
        for dir_name in ("plugin-alpha", "plugin-beta"):
            plugin_dir = plugins_root / dir_name
            (plugin_dir / ".claude-plugin").mkdir(parents=True)
            (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
                '{"name": "shared", "version": "1.0.0"}', encoding="utf-8"
            )

        # Act / Assert — must raise ValueError with both paths mentioned
        with pytest.raises(ValueError, match="shared"):
            _build_manifest_name_index(plugins_root)


class TestFindPluginQualifiedManifestResolution:
    def test_find_plugin_qualified_resolves_manifest_name_to_directory(self, manifest_plugin_root: Path) -> None:
        """find_agent('dh:tn-verification-gate') must resolve when the plugin
        directory is 'development-harness' but the manifest declares name 'dh'.

        Why: This is the exact production bug. task-worker calls profile_load with
        agent_name='dh:tn-verification-gate', which fails because there is no
        plugins/dh/ directory. The manifest-name fallback must fix this.
        """
        # Arrange — manifest_plugin_root has development-harness/ declaring name "dh"

        # Act
        agent = find_agent("dh:tn-verification-gate", manifest_plugin_root)

        # Assert — resolved correctly despite mismatch between qualifier and dir name
        assert agent.name == "tn-verification-gate"
        assert agent.path.is_file()

    def test_find_plugin_qualified_fast_path_still_works(self, manifest_plugin_root: Path) -> None:
        """find_agent('development-harness:tn-verification-gate') must resolve and
        return plugin field normalised to the manifest name 'dh' (Option A policy).

        Why: After the fix, the fast path (directory-name lookup) still resolves the
        file but must normalise AgentEntry.plugin to the manifest name so that
        find_agent() and scan_all_agents() produce consistent plugin values. Without
        this normalisation, callers using directory-name qualifiers get a different
        plugin value than callers using manifest-name qualifiers, which breaks
        comparison logic downstream (e.g. task-worker agent: field matching).
        """
        # Arrange — manifest_plugin_root has development-harness/ declaring name "dh"

        # Act — use directory name directly (fast path); file resolves, but plugin
        # field must be normalised to manifest name
        agent = find_agent("development-harness:tn-verification-gate", manifest_plugin_root)

        # Assert — agent found AND plugin field uses manifest name, not directory name
        assert agent.name == "tn-verification-gate"
        assert agent.path.is_file()
        assert agent.plugin == "dh", (
            f"Expected plugin='dh' (manifest name) but got plugin='{agent.plugin}' "
            "(directory name). Option A requires normalisation to manifest name even "
            "when the fast path resolves the directory."
        )

    def test_find_plugin_qualified_manifest_name_miss_raises_error(self, manifest_plugin_root: Path) -> None:
        """find_agent('nonexistent:agent') must raise FileNotFoundError with a message
        that mentions both directory-name and manifest-based lookup were attempted.

        Why: The error message after the fix must distinguish the new two-strategy
        lookup from the old single-strategy lookup. A message referencing 'manifest'
        tells operators exactly what was searched, not just which directory was missing.
        """
        # Arrange — no plugin named "nonexistent" in directory names or manifests

        # Act / Assert — must raise AND the message must mention manifest lookup
        with pytest.raises(FileNotFoundError, match="manifest"):
            find_agent("nonexistent:tn-verification-gate", manifest_plugin_root)

    def test_find_plugin_qualified_new_error_message_cites_both_strategies(self, manifest_plugin_root: Path) -> None:
        """The FileNotFoundError message when a plugin cannot be resolved must
        mention that both directory names and manifests were checked.

        Why: The old error 'no agents/ directory under plugins/dh' is confusing —
        it implies the directory should exist. The new message must guide operators
        to check both directory names and .claude-plugin/plugin.json manifests.
        """
        # Arrange — plugin qualifier that exists in neither strategy

        # Act / Assert
        with pytest.raises(FileNotFoundError, match="manifest") as exc_info:
            find_agent("totally-unknown:some-agent", manifest_plugin_root)

        msg = str(exc_info.value)
        # Message must mention manifest-based lookup was attempted
        assert "manifest" in msg.lower()


class TestScanAllAgentsManifestName:
    def test_scan_all_agents_plugin_field_uses_manifest_name(self, manifest_plugin_root: Path) -> None:
        """scan_all_agents() must return AgentEntry.plugin == 'dh' (manifest name)
        for agents under 'development-harness/' when that plugin's manifest
        declares name='dh' (Option A policy).

        Why: AgentEntry.plugin is consumed by profile_list and task-worker's
        agent: field comparisons. When find_agent returns plugin='dh' but
        scan_all_agents returns plugin='development-harness', comparisons fail.
        Option A normalises both to the manifest name.
        """
        # Arrange — manifest_plugin_root has development-harness/ with manifest name "dh"

        # Act
        agents = scan_all_agents(manifest_plugin_root)

        # Assert — all agents from this plugin use the manifest name, not dir name
        dh_agents = [a for a in agents if a.path.parent.parent.name == "development-harness"]
        assert len(dh_agents) > 0, "Expected at least one agent from development-harness plugin"
        for agent in dh_agents:
            assert agent.plugin == "dh", (
                f"Expected plugin='dh' (manifest name) but got plugin='{agent.plugin}' "
                f"(directory name) for agent '{agent.name}'. "
                "Option A policy requires scan_all_agents to use manifest name when available."
            )
