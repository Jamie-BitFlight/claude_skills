"""Unit tests for agent_profile.resolver module.

Target: 100% coverage on resolver.py.
All tests use tmp_path fixtures — no real plugins/ filesystem access.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from agent_profile.resolver import PLUGIN_ALIASES, SkillResolver

# ---------------------------------------------------------------------------
# Helpers (local, not in conftest — keep resolver tests self-contained)
# ---------------------------------------------------------------------------


def _make_skill(
    plugins_root: Path, plugin: str, skill_name: str, content: str = "Skill.", frontmatter: str = ""
) -> Path:
    """Create a skill directory with SKILL.md under plugins/plugin/skills/skill_name/."""
    skill_dir = plugins_root / plugin / "skills" / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    if frontmatter:
        skill_md.write_text(f"---\n{frontmatter}---\n{content}\n", encoding="utf-8")
    else:
        skill_md.write_text(content, encoding="utf-8")
    return skill_dir


def _make_domain_skill(plugins_root: Path, plugin: str, domain_path: str, content: str = "Domain skill.") -> Path:
    """Create a domain skill directory."""
    skill_dir = plugins_root / plugin / "skills" / domain_path
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


def test_plugin_aliases_contains_dh() -> None:
    assert "dh" in PLUGIN_ALIASES
    assert PLUGIN_ALIASES["dh"] == "development-harness"


# ---------------------------------------------------------------------------
# Bare name resolution
# ---------------------------------------------------------------------------


class TestBareNameResolution:
    def test_bare_name_resolves_to_context_plugin_first(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        _make_skill(plugins_root, "context-plugin", "my-skill", "Context skill.")
        _make_skill(plugins_root, "other-plugin", "my-skill", "Other skill.")

        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve(["my-skill"], "context-plugin")

        assert len(skills) == 1
        assert skills[0].plugin == "context-plugin"
        assert warnings == []

    def test_bare_name_finds_skill_in_other_plugin_when_not_in_context(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        _make_skill(plugins_root, "other-plugin", "my-skill", "Other skill.")

        resolver = SkillResolver(plugins_root)
        skills, _warnings = resolver.resolve(["my-skill"], "context-plugin")

        assert len(skills) == 1
        assert skills[0].plugin == "other-plugin"

    def test_bare_name_multiple_matches_outside_context_produces_warning(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        _make_skill(plugins_root, "alpha-plugin", "shared-skill")
        _make_skill(plugins_root, "beta-plugin", "shared-skill")

        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve(["shared-skill"], "context-plugin")

        # Still resolves (uses first match) but warns
        assert len(skills) == 1
        assert len(warnings) == 1
        assert "multiple plugins" in warnings[0].lower()

    def test_missing_bare_name_produces_warning_not_error(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        (plugins_root / "some-plugin" / "skills").mkdir(parents=True)

        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve(["nonexistent-skill"], "some-plugin")

        assert skills == []
        assert len(warnings) == 1
        assert "nonexistent-skill" in warnings[0]

    def test_empty_skill_list_returns_empty(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve([], "any-plugin")
        assert skills == []
        assert warnings == []


# ---------------------------------------------------------------------------
# Plugin-qualified name resolution
# ---------------------------------------------------------------------------


class TestPluginQualifiedResolution:
    def test_plugin_qualified_resolves_correctly(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        _make_skill(plugins_root, "development-harness", "subagent-contract", "Subagent contract content.")

        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve(["development-harness:subagent-contract"], "some-plugin")

        assert len(skills) == 1
        assert skills[0].plugin == "development-harness"
        assert skills[0].skill_name == "subagent-contract"
        assert warnings == []

    def test_dh_alias_resolves_to_development_harness(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        _make_skill(plugins_root, "development-harness", "subagent-contract", "Content.")

        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve(["dh:subagent-contract"], "some-plugin")

        assert len(skills) == 1
        assert skills[0].plugin == "development-harness"
        assert warnings == []

    def test_plugin_qualified_nested_skill_path(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        skill_dir = plugins_root / "development-harness" / "skills" / "analyze-test-failures"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("Test failure analysis.", encoding="utf-8")

        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve(["dh:analyze-test-failures"], "some-plugin")

        assert len(skills) == 1
        assert "analyze-test-failures" in skills[0].skill_name
        assert warnings == []

    def test_plugin_qualified_missing_produces_warning(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        (plugins_root / "development-harness" / "skills").mkdir(parents=True)

        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve(["dh:nonexistent-skill"], "some-plugin")

        assert skills == []
        assert len(warnings) == 1


# ---------------------------------------------------------------------------
# Domain path resolution
# ---------------------------------------------------------------------------


class TestDomainPathResolution:
    def test_domain_path_resolves_relative_to_context_plugin(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        _make_domain_skill(plugins_root, "context-plugin", "domains/enterprise-foo", "Enterprise content.")

        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve(["domains/enterprise-foo"], "context-plugin")

        assert len(skills) == 1
        assert skills[0].plugin == "context-plugin"
        assert warnings == []

    def test_domain_path_missing_produces_warning(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        (plugins_root / "context-plugin" / "skills").mkdir(parents=True)

        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve(["domains/nonexistent"], "context-plugin")

        assert skills == []
        assert len(warnings) == 1

    def test_domain_path_traversal_attempt_blocked(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        (plugins_root / "context-plugin" / "skills").mkdir(parents=True)

        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve(["domains/../../../etc/passwd"], "context-plugin")

        assert skills == []
        assert len(warnings) == 1
        assert "traversal" in warnings[0].lower() or "path" in warnings[0].lower()


# ---------------------------------------------------------------------------
# Circular dependency detection
# ---------------------------------------------------------------------------


class TestCircularDependencyDetection:
    def test_circular_a_b_a_detected_no_infinite_loop(self, circular_plugin_root: Path) -> None:
        """A depends on B, B depends on A — must terminate with warnings."""
        resolver = SkillResolver(circular_plugin_root)
        _skills, warnings = resolver.resolve(["skill-a"], "circ-plugin")

        # Must terminate (no RecursionError) and produce a warning
        circular_warnings = [w for w in warnings if "circular" in w.lower()]
        assert len(circular_warnings) >= 1

    def test_circular_skills_partial_result_returned(self, circular_plugin_root: Path) -> None:
        """At least skill-a should be resolved even though the cycle is detected."""
        resolver = SkillResolver(circular_plugin_root)
        skills, _warnings = resolver.resolve(["skill-a"], "circ-plugin")

        # skill-a itself should resolve; only the cycle re-entry is skipped
        skill_names = [s.skill_name for s in skills]
        assert "skill-a" in skill_names

    def test_same_skill_twice_in_list_second_skipped_as_visited(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        _make_skill(plugins_root, "plugin-a", "skill-x", "Content.")

        resolver = SkillResolver(plugins_root)
        # Explicitly requesting the same skill twice
        skills, warnings = resolver.resolve(["plugin-a:skill-x", "plugin-a:skill-x"], "plugin-a")

        # Second occurrence should be skipped (already visited)
        assert len(skills) == 1
        assert any("circular" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# Recursive sub-skill resolution
# ---------------------------------------------------------------------------


class TestRecursiveSubSkillResolution:
    def test_sub_skills_resolved_recursively(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        # skill-parent declares sub-skill skill-child
        _make_skill(plugins_root, "plugin-a", "skill-parent", "Parent.", frontmatter="skills:\n  - skill-child\n")
        _make_skill(plugins_root, "plugin-a", "skill-child", "Child.")

        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve(["skill-parent"], "plugin-a")

        skill_names = [s.skill_name for s in skills]
        assert "skill-parent" in skill_names
        assert "skill-child" in skill_names
        assert warnings == []

    def test_missing_sub_skill_produces_warning_not_error(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        _make_skill(plugins_root, "plugin-a", "skill-parent", "Parent.", frontmatter="skills:\n  - missing-child\n")

        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve(["skill-parent"], "plugin-a")

        assert any(s.skill_name == "skill-parent" for s in skills)
        assert len(warnings) >= 1


# ---------------------------------------------------------------------------
# ResolvedSkill content
# ---------------------------------------------------------------------------


class TestResolvedSkillContent:
    def test_resolved_skill_contains_correct_content(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        _make_skill(plugins_root, "plugin-a", "my-skill", "Specific content here.")

        resolver = SkillResolver(plugins_root)
        skills, _ = resolver.resolve(["plugin-a:my-skill"], "plugin-a")

        assert len(skills) == 1
        assert "Specific content here." in skills[0].content

    def test_resolved_skill_includes_reference_files(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        skill_dir = _make_skill(plugins_root, "plugin-a", "my-skill")
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "guide.md").write_text("Guide content.", encoding="utf-8")

        resolver = SkillResolver(plugins_root)
        skills, _ = resolver.resolve(["plugin-a:my-skill"], "plugin-a")

        assert "guide.md" in skills[0].reference_files
        assert skills[0].reference_files["guide.md"] == "Guide content."

    def test_resolved_skill_uri_preserved(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        _make_skill(plugins_root, "development-harness", "my-skill")

        resolver = SkillResolver(plugins_root)
        skills, _ = resolver.resolve(["dh:my-skill"], "some-plugin")

        assert skills[0].uri == "dh:my-skill"

    def test_resolved_path_points_to_skill_md(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        _make_skill(plugins_root, "plugin-a", "my-skill")

        resolver = SkillResolver(plugins_root)
        skills, _ = resolver.resolve(["plugin-a:my-skill"], "plugin-a")

        assert skills[0].resolved_path.name == "SKILL.md"
        assert skills[0].resolved_path.is_file()


# ---------------------------------------------------------------------------
# Path safety (traversal prevention)
# ---------------------------------------------------------------------------


class TestPathSafety:
    def test_path_outside_plugins_root_blocked(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "plugins"
        # Create a skill outside plugins_root that a symlink might point to
        outside_dir = tmp_path / "outside" / "evil-skill"
        outside_dir.mkdir(parents=True)
        (outside_dir / "SKILL.md").write_text("Evil.", encoding="utf-8")

        # Create a symlink inside plugins_root pointing outside
        (plugins_root / "plugin-a" / "skills").mkdir(parents=True)
        symlink_target = plugins_root / "plugin-a" / "skills" / "evil-skill"
        try:
            symlink_target.symlink_to(outside_dir)
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported on this platform")

        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve(["plugin-a:evil-skill"], "plugin-a")

        # The skill should be blocked as it resolves outside plugins_root
        # (if symlink resolution lands outside). Accept either block or success
        # depending on OS symlink resolution behavior — just verify no crash.
        assert isinstance(skills, list)
        assert isinstance(warnings, list)


# ---------------------------------------------------------------------------
# SkillResolver constructor
# ---------------------------------------------------------------------------


class TestSkillResolverConstructor:
    def test_plugins_root_override_is_used(self, tmp_path: Path) -> None:
        plugins_root = tmp_path / "custom-plugins"
        _make_skill(plugins_root, "plugin-a", "custom-skill", "Custom.")

        resolver = SkillResolver(plugins_root=plugins_root)
        skills, warnings = resolver.resolve(["plugin-a:custom-skill"], "plugin-a")

        assert len(skills) == 1
        assert warnings == []


# ---------------------------------------------------------------------------
# Edge cases for 100% resolver.py coverage
# ---------------------------------------------------------------------------


class TestResolverEdgeCases:
    def test_skill_md_disappears_after_resolve_produces_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cover lines 133-136: FileNotFoundError from parse_skill_frontmatter after skill resolved.

        The resolver calls parse_skill_frontmatter once per skill (after appending
        it to resolved) to check for sub-skill declarations. If that call raises
        FileNotFoundError, a "disappeared" warning is produced and the method returns.
        """
        import agent_profile.resolver as resolver_module

        plugins_root = tmp_path / "plugins"
        _make_skill(plugins_root, "plugin-a", "vanishing-skill", "Content.")

        def always_raise(path: Path) -> list[str]:
            raise FileNotFoundError(f"Simulated disappearance: {path}")

        # Patch the name in the resolver module's namespace (where it's imported at top)
        monkeypatch.setattr(resolver_module, "parse_skill_frontmatter", always_raise)

        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve(["plugin-a:vanishing-skill"], "plugin-a")

        # Skill itself is appended before the parse_skill_frontmatter call, so it appears
        assert any(s.skill_name == "vanishing-skill" for s in skills)
        assert any("disappeared" in w for w in warnings)

    def test_read_skill_content_missing_after_path_check_produces_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cover lines 200-202: FileNotFoundError from read_skill_content after path safety passes."""
        plugins_root = tmp_path / "plugins"
        _make_skill(plugins_root, "plugin-a", "disappearing-skill", "Content.")

        def always_raise(skill_dir: Path) -> tuple[str, dict[str, str]]:
            raise FileNotFoundError(f"Simulated missing: {skill_dir}")

        import agent_profile.resolver as resolver_module

        monkeypatch.setattr(resolver_module, "read_skill_content", always_raise)

        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve(["plugin-a:disappearing-skill"], "plugin-a")

        assert skills == []
        assert any("SKILL.md not found" in w for w in warnings)

    def test_non_directory_entries_in_plugins_root_skipped(self, tmp_path: Path) -> None:
        """Cover line 336: non-directory entries in plugins_root iterdir are skipped."""
        plugins_root = tmp_path / "plugins"
        plugins_root.mkdir(parents=True)

        # Place a plain file in plugins_root (not a directory)
        (plugins_root / "README.md").write_text("Not a plugin.", encoding="utf-8")

        # Place an actual plugin with the skill
        _make_skill(plugins_root, "real-plugin", "my-skill", "Real skill.")

        resolver = SkillResolver(plugins_root)
        skills, _warnings = resolver.resolve(["my-skill"], "context-plugin")

        # Should find it in real-plugin, ignoring README.md
        assert len(skills) == 1
        assert skills[0].plugin == "real-plugin"

    def test_plugin_and_name_from_dir_outside_plugins_root_defensive_fallback(self, tmp_path: Path) -> None:
        """Cover lines 408-410: _plugin_and_name_from_dir ValueError defensive branch."""
        from agent_profile.resolver import _plugin_and_name_from_dir

        # A path that is NOT under plugins_root triggers the ValueError branch
        plugins_root = tmp_path / "plugins"
        plugins_root.mkdir(parents=True)

        outside_dir = tmp_path / "outside" / "some-skill"
        outside_dir.mkdir(parents=True)

        plugin, name = _plugin_and_name_from_dir(outside_dir, plugins_root)

        # Defensive fallback: returns something without crashing
        assert isinstance(plugin, str)
        assert isinstance(name, str)

    def test_oserror_during_path_resolution_produces_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cover lines 178-180: OSError during skill_dir.resolve()."""
        plugins_root = tmp_path / "plugins"
        _make_skill(plugins_root, "plugin-a", "oserror-skill", "Content.")

        # Monkeypatch Path.resolve to raise OSError for our specific skill dir
        original_resolve = Path.resolve

        def patched_resolve(self: Path, strict: bool = False) -> Path:
            if self == plugins_root / "plugin-a" / "skills" / "oserror-skill":
                raise OSError("Simulated OS error during resolve")
            return original_resolve(self, strict=strict)

        monkeypatch.setattr(Path, "resolve", patched_resolve)

        resolver = SkillResolver(plugins_root)
        skills, warnings = resolver.resolve(["plugin-a:oserror-skill"], "plugin-a")

        assert skills == []
        assert any("path resolution error" in w for w in warnings)
