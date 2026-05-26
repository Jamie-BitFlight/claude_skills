"""Shared fixtures for agent_profile unit tests.

All fixtures use tmp_path and create synthetic plugin directory trees.
No fixture accesses the real plugins/ filesystem.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_agent(agents_dir: Path, name: str, frontmatter: str, body: str = "Agent body content.") -> Path:
    """Write a synthetic agent .md file."""
    path = agents_dir / f"{name}.md"
    path.write_text(f"---\n{frontmatter}---\n{body}\n", encoding="utf-8")
    return path


def _write_skill(skills_dir: Path, skill_name: str, content: str = "Skill content.", frontmatter: str = "") -> Path:
    """Write a synthetic SKILL.md in a skill subdirectory."""
    skill_dir = skills_dir / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    if frontmatter:
        skill_md.write_text(f"---\n{frontmatter}---\n{content}\n", encoding="utf-8")
    else:
        skill_md.write_text(content, encoding="utf-8")
    return skill_md


def _write_reference(skill_dir: Path, filename: str, content: str) -> Path:
    """Write a reference file inside a skill's references/ subdir."""
    refs_dir = skill_dir / "references"
    refs_dir.mkdir(parents=True, exist_ok=True)
    ref = refs_dir / filename
    ref.write_text(content, encoding="utf-8")
    return ref


# ---------------------------------------------------------------------------
# Single-plugin fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def single_plugin_root(tmp_path: Path) -> Path:
    """A plugins/ root with one plugin 'test-plugin' and several agents."""
    plugins_root = tmp_path / "plugins"
    plugin_dir = plugins_root / "test-plugin"
    agents_dir = plugin_dir / "agents"
    skills_dir = plugin_dir / "skills"
    agents_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)

    # Agent with YAML list skills
    _write_agent(
        agents_dir,
        "list-skills-agent",
        "name: list-skills-agent\ndescription: Agent with YAML list skills\nskills:\n  - skill-a\n  - skill-b\n",
    )

    # Agent with comma-separated skills
    _write_agent(
        agents_dir,
        "csv-skills-agent",
        "name: csv-skills-agent\ndescription: Agent with CSV skills\nskills: skill-a, skill-b\n",
    )

    # Agent with single skill
    _write_agent(
        agents_dir,
        "single-skill-agent",
        "name: single-skill-agent\ndescription: Agent with one skill\nskills: skill-a\n",
    )

    # Agent with no skills
    _write_agent(agents_dir, "no-skills-agent", "name: no-skills-agent\ndescription: Agent with no skills\n")

    # Agent with model and color
    _write_agent(
        agents_dir,
        "full-agent",
        "name: full-agent\ndescription: Fully specified agent\nskills:\n  - skill-a\nmodel: claude-sonnet-4-6\ncolor: '#FF6B35'\n",
    )

    # Subdirectory agent
    sub_dir = agents_dir / "testing"
    sub_dir.mkdir()
    _write_agent(sub_dir, "unit-tester", "name: unit-tester\ndescription: Subdirectory agent\nskills:\n  - skill-a\n")

    # Skills
    _write_skill(skills_dir, "skill-a", content="Skill A content.")
    skill_b_dir = skills_dir / "skill-b"
    skill_b_dir.mkdir(parents=True)
    (skill_b_dir / "SKILL.md").write_text("Skill B content.", encoding="utf-8")
    # Add references to skill-a
    skill_a_dir = skills_dir / "skill-a"
    _write_reference(skill_a_dir, "guide.md", "Guide content.")
    _write_reference(skill_a_dir, "reference.md", "Reference content.")

    return plugins_root


# ---------------------------------------------------------------------------
# Multi-plugin fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def multi_plugin_root(tmp_path: Path) -> Path:
    """A plugins/ root with two plugins for cross-plugin tests."""
    plugins_root = tmp_path / "plugins"

    # Plugin alpha
    alpha_agents = plugins_root / "alpha" / "agents"
    alpha_skills = plugins_root / "alpha" / "skills"
    alpha_agents.mkdir(parents=True)
    alpha_skills.mkdir(parents=True)

    _write_agent(
        alpha_agents, "alpha-agent", "name: alpha-agent\ndescription: Agent in alpha\nskills:\n  - alpha-skill\n"
    )
    _write_agent(alpha_agents, "shared-name", "name: shared-name\ndescription: Agent in alpha with shared name\n")
    _write_skill(alpha_skills, "alpha-skill", "Alpha skill content.")

    # Plugin beta
    beta_agents = plugins_root / "beta" / "agents"
    beta_skills = plugins_root / "beta" / "skills"
    beta_agents.mkdir(parents=True)
    beta_skills.mkdir(parents=True)

    _write_agent(beta_agents, "beta-agent", "name: beta-agent\ndescription: Agent in beta\nskills:\n  - beta-skill\n")
    _write_agent(beta_agents, "shared-name", "name: shared-name\ndescription: Agent in beta with shared name\n")
    _write_skill(beta_skills, "beta-skill", "Beta skill content.")
    # beta also has alpha-skill (ambiguous bare resolution test)
    _write_skill(beta_skills, "alpha-skill", "Alpha skill in beta.")

    return plugins_root


# ---------------------------------------------------------------------------
# Circular dependency fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def circular_plugin_root(tmp_path: Path) -> Path:
    """A plugins/ root where skill-a depends on skill-b, which depends on skill-a."""
    plugins_root = tmp_path / "plugins"
    plugin_dir = plugins_root / "circ-plugin"
    agents_dir = plugin_dir / "agents"
    skills_dir = plugin_dir / "skills"
    agents_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)

    _write_agent(
        agents_dir,
        "circ-agent",
        "name: circ-agent\ndescription: Agent triggering circular skills\nskills:\n  - skill-a\n",
    )

    # skill-a declares sub-skill skill-b
    _write_skill(skills_dir, "skill-a", content="Skill A.", frontmatter="skills:\n  - skill-b\n")
    # skill-b declares sub-skill skill-a (circular!)
    _write_skill(skills_dir, "skill-b", content="Skill B.", frontmatter="skills:\n  - skill-a\n")

    return plugins_root


# ---------------------------------------------------------------------------
# Domain path fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def domain_plugin_root(tmp_path: Path) -> Path:
    """A plugins/ root with a flat skill directly under skills/enterprise-foo/."""
    plugins_root = tmp_path / "plugins"
    plugin_dir = plugins_root / "domain-plugin"
    agents_dir = plugin_dir / "agents"
    skills_dir = plugin_dir / "skills"
    agents_dir.mkdir(parents=True)
    skills_dir.mkdir(parents=True)

    _write_agent(
        agents_dir,
        "domain-agent",
        "name: domain-agent\ndescription: Agent using domain skill\nskills:\n  - enterprise-foo\n",
    )

    # Create the skill directory flat under skills/ (nesting is not supported)
    skill_dir = skills_dir / "enterprise-foo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("Enterprise Foo skill content.", encoding="utf-8")

    return plugins_root


# ---------------------------------------------------------------------------
# Manifest helpers (for manifest-name index tests)
# ---------------------------------------------------------------------------


def _write_manifest(plugin_dir: Path, name: str, extra: dict | None = None) -> Path:
    """Write a .claude-plugin/plugin.json manifest declaring the given plugin name.

    Args:
        plugin_dir: The plugin directory that will contain .claude-plugin/.
        name: The manifest ``name`` field value (e.g. "dh").
        extra: Additional fields to merge into the manifest JSON.

    Returns:
        Path to the written plugin.json file.
    """
    manifest_dir = plugin_dir / ".claude-plugin"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "plugin.json"
    payload: dict = {"name": name, "version": "1.0.0"}
    if extra:
        payload.update(extra)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    return manifest_path


# ---------------------------------------------------------------------------
# Cache-clear autouse fixture — prevents cross-test cache pollution
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_manifest_index_cache() -> Generator[None, None, None]:
    """Clear _build_manifest_name_index cache before and after every test.

    This prevents a cached plugins_root from one test bleeding into another.
    The function may not exist before implementation; the fixture degrades
    gracefully in that case.
    """
    try:
        from agent_profile.discovery import _build_manifest_name_index

        _build_manifest_name_index.cache_clear()
    except (ImportError, AttributeError):
        pass
    yield
    try:
        from agent_profile.discovery import _build_manifest_name_index

        _build_manifest_name_index.cache_clear()
    except (ImportError, AttributeError):
        pass


# ---------------------------------------------------------------------------
# Manifest-name plugin root fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def manifest_plugin_root(tmp_path: Path) -> Path:
    """A plugins/ root where the plugin directory is 'development-harness'
    but the manifest declares name 'dh'.

    Directory structure::

        plugins/
          development-harness/
            .claude-plugin/
              plugin.json   <- {"name": "dh", ...}
            agents/
              tn-verification-gate.md
              task-worker.md

    This is the exact scenario that triggers the bug: callers using the
    manifest name "dh" cannot resolve to the directory "development-harness".
    """
    plugins_root = tmp_path / "plugins"
    plugin_dir = plugins_root / "development-harness"
    agents_dir = plugin_dir / "agents"
    agents_dir.mkdir(parents=True)

    _write_manifest(plugin_dir, "dh")

    _write_agent(
        agents_dir, "tn-verification-gate", "name: tn-verification-gate\ndescription: Verification gate agent\n"
    )
    _write_agent(agents_dir, "task-worker", "name: task-worker\ndescription: Task execution agent\n")

    return plugins_root
