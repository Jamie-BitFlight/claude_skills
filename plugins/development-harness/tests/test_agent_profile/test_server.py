"""Integration tests for agent_profile MCP server tools.

Tests invoke profile_load (tool name: 'load') and profile_list (tool name: 'list')
through the FastMCP in-memory client, exercising the full tool dispatch path.

Synthetic test isolation strategy
----------------------------------
All non-integration tests redirect the server to a synthetic tmp_path plugin
tree by patching:

  - ``agent_profile.server.get_plugins_root`` — controls plugin discovery root
  - ``agent_profile.server.find_agent``        — controls agent lookup
  - ``agent_profile.server.scan_all_agents``   — controls agent enumeration
  - ``agent_profile.server.parse_agent_file``  — controls frontmatter parsing

The server functions are synchronous, so ``mocker.patch`` (not ``AsyncMock``)
is used throughout.

Integration tests (``@pytest.mark.integration``) call the real plugins/
filesystem and are gated behind the ``integration`` marker.

Response shape contract
-----------------------
profile_load success:
    {name, plugin, description, model, tools, body, skills, warnings}

profile_load error:
    {"error": "<str>"}

profile_list success:
    {agents: [...], count: int, plugin_filter: str | None}

Each agent entry in profile_list:
    {name, plugin, description, skill_count, model}

Each resolved skill in profile_load.skills:
    {uri, resolved_path, plugin, skill_name, content, reference_files}
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from agent_profile.models import AgentEntry, AgentMetadata, ResolvedSkill
from agent_profile.server import mcp
from fastmcp.client import Client

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AGENT_PROFILE_KEYS = frozenset({"name", "plugin", "description", "model", "tools", "body", "skills", "warnings"})
_PROFILE_LIST_KEYS = frozenset({"agents", "count", "plugin_filter"})
_PROFILE_LIST_ENTRY_KEYS = frozenset({"name", "plugin", "description", "skill_count", "model"})
_RESOLVED_SKILL_KEYS = frozenset({"uri", "resolved_path", "plugin", "skill_name", "content", "reference_files"})


def _make_agent_entry(tmp_path: Path, plugin: str = "test-plugin", name: str = "my-agent") -> AgentEntry:
    """Create a synthetic AgentEntry pointing to a real tmp_path file."""
    agents_dir = tmp_path / "plugins" / plugin / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    agent_file = agents_dir / f"{name}.md"
    agent_file.write_text(
        f"---\nname: {name}\ndescription: Test agent\nskills: []\n---\nAgent body.\n", encoding="utf-8"
    )
    return AgentEntry(name=name, plugin=plugin, path=agent_file)


def _make_metadata(name: str = "my-agent", skills: list[str] | None = None) -> AgentMetadata:
    """Create a minimal AgentMetadata for mocking parse_agent_file."""
    return AgentMetadata(
        name=name, description="Test agent description", skills=skills or [], tools=[], model=None, color=None
    )


def _make_resolved_skill(plugins_root: Path, plugin: str, skill_name: str, uri: str) -> ResolvedSkill:
    """Create a ResolvedSkill backed by a real file in plugins_root."""
    skill_dir = plugins_root / plugin / "skills" / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(f"# {skill_name}\n\nSkill content.", encoding="utf-8")
    return ResolvedSkill(
        uri=uri,
        resolved_path=skill_md,
        plugin=plugin,
        skill_name=skill_name,
        content=f"# {skill_name}\n\nSkill content.",
        reference_files={},
    )


# ---------------------------------------------------------------------------
# Test: profile_load — success path
# ---------------------------------------------------------------------------


class TestProfileLoad:
    """Tests for the 'load' MCP tool (exposed as profile_load via backlog mount).

    Tests: profile_load tool via the agent_profile FastMCP server.
    Strategy: Patch discovery and parser functions to inject synthetic data.
              Verify full AgentProfile dict shape is returned.
    """

    async def test_load_returns_agent_profile_keys(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """profile_load returns a dict with all AgentProfile keys on success.

        Tests: profile_load success response shape.
        How: Mock find_agent to return a synthetic entry, parse_agent_file to
             return metadata with no skills, verify result.data has all keys.
        Why: Consumers depend on a stable dict shape for context injection.
        """
        # Arrange
        entry = _make_agent_entry(tmp_path, plugin="test-plugin", name="simple-agent")
        metadata = _make_metadata(name="simple-agent", skills=[])

        mocker.patch("agent_profile.server.get_plugins_root", return_value=tmp_path / "plugins")
        mocker.patch("agent_profile.server.find_agent", return_value=entry)
        mocker.patch("agent_profile.server.parse_agent_file", return_value=(metadata, "Agent body content."))

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("load", {"agent_name": "simple-agent"})

        # Assert
        assert result.is_error is False
        assert isinstance(result.data, dict)
        assert _AGENT_PROFILE_KEYS.issubset(result.data.keys())

    async def test_load_returns_correct_agent_name_and_plugin(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """profile_load populates name and plugin from the discovered agent entry.

        Tests: name and plugin fields in AgentProfile response.
        How: Mock with a known entry, verify response reflects the mocked values.
        Why: Consumers use name/plugin to route and display agent identity.
        """
        # Arrange
        plugins_root = tmp_path / "plugins"
        entry = _make_agent_entry(tmp_path, plugin="my-plugin", name="target-agent")
        metadata = _make_metadata(name="target-agent")

        mocker.patch("agent_profile.server.get_plugins_root", return_value=plugins_root)
        mocker.patch("agent_profile.server.find_agent", return_value=entry)
        mocker.patch("agent_profile.server.parse_agent_file", return_value=(metadata, "Body."))

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("load", {"agent_name": "target-agent"})

        # Assert
        assert result.data["name"] == "target-agent"
        assert result.data["plugin"] == "my-plugin"

    async def test_load_returns_agent_body(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """profile_load includes the agent instruction body in the response.

        Tests: body field in AgentProfile response.
        How: Mock parse_agent_file to return a specific body string, verify.
        Why: The body is the primary content injected into the task-worker context.
        """
        # Arrange
        entry = _make_agent_entry(tmp_path)
        metadata = _make_metadata()
        expected_body = "You are an expert Python developer. Follow TDD strictly."

        mocker.patch("agent_profile.server.get_plugins_root", return_value=tmp_path / "plugins")
        mocker.patch("agent_profile.server.find_agent", return_value=entry)
        mocker.patch("agent_profile.server.parse_agent_file", return_value=(metadata, expected_body))

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("load", {"agent_name": "my-agent"})

        # Assert
        assert result.data["body"] == expected_body

    async def test_load_returns_empty_skills_for_agent_with_none(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """profile_load returns an empty skills list when the agent declares no skills.

        Tests: skills field is an empty list for a no-skills agent.
        How: Mock metadata with empty skills list, verify the resolved skills list.
        Why: Task-workers loading no-skills agents should not receive broken bundles.
        """
        # Arrange
        entry = _make_agent_entry(tmp_path)
        metadata = _make_metadata(skills=[])

        mocker.patch("agent_profile.server.get_plugins_root", return_value=tmp_path / "plugins")
        mocker.patch("agent_profile.server.find_agent", return_value=entry)
        mocker.patch("agent_profile.server.parse_agent_file", return_value=(metadata, "Body."))

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("load", {"agent_name": "my-agent"})

        # Assert
        assert result.data["skills"] == []
        assert result.data["warnings"] == []

    async def test_load_returns_resolved_skills_with_correct_keys(
        self, mocker: MockerFixture, tmp_path: Path, single_plugin_root: Path
    ) -> None:
        """profile_load returns resolved skill dicts with all ResolvedSkill keys.

        Tests: skills list contains correctly shaped ResolvedSkill dicts.
        How: Use single_plugin_root fixture for real skill files; mock discovery
             to point at that root; parse agent with a skill.
        Why: Consumers depend on skill content for context injection.
        """
        # Arrange
        agents_dir = single_plugin_root / "test-plugin" / "agents"
        agent_file = agents_dir / "list-skills-agent.md"
        entry = AgentEntry(name="list-skills-agent", plugin="test-plugin", path=agent_file)
        metadata = _make_metadata(name="list-skills-agent", skills=["skill-a"])

        mocker.patch("agent_profile.server.get_plugins_root", return_value=single_plugin_root)
        mocker.patch("agent_profile.server.find_agent", return_value=entry)
        mocker.patch("agent_profile.server.parse_agent_file", return_value=(metadata, "Body."))

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("load", {"agent_name": "list-skills-agent"})

        # Assert
        assert result.is_error is False
        skills = result.data["skills"]
        assert len(skills) >= 1
        first_skill = skills[0]
        assert _RESOLVED_SKILL_KEYS.issubset(first_skill.keys())
        assert first_skill["skill_name"] == "skill-a"
        assert "Skill A content" in first_skill["content"]

    async def test_load_skill_includes_reference_files(
        self, mocker: MockerFixture, tmp_path: Path, single_plugin_root: Path
    ) -> None:
        """profile_load includes reference files from the skill's references/ directory.

        Tests: reference_files dict is populated in resolved skill.
        How: Use single_plugin_root which has skill-a with two reference files.
        Why: Reference files are part of the bundled skill context.
        """
        # Arrange
        agents_dir = single_plugin_root / "test-plugin" / "agents"
        agent_file = agents_dir / "single-skill-agent.md"
        entry = AgentEntry(name="single-skill-agent", plugin="test-plugin", path=agent_file)
        metadata = _make_metadata(name="single-skill-agent", skills=["skill-a"])

        mocker.patch("agent_profile.server.get_plugins_root", return_value=single_plugin_root)
        mocker.patch("agent_profile.server.find_agent", return_value=entry)
        mocker.patch("agent_profile.server.parse_agent_file", return_value=(metadata, "Body."))

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("load", {"agent_name": "single-skill-agent"})

        # Assert
        skills = result.data["skills"]
        skill_a = next(s for s in skills if s["skill_name"] == "skill-a")
        ref_files = skill_a["reference_files"]
        assert "guide.md" in ref_files
        assert "reference.md" in ref_files
        assert "Guide content." in ref_files["guide.md"]

    async def test_load_returns_warnings_for_missing_skill(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """profile_load returns a partial profile with warnings when a skill is unresolvable.

        Tests: warnings field in AgentProfile when skill resolution fails.
        How: Mock a metadata with a skill URI that cannot be resolved in the
             tmp_path tree (no matching skill directory exists).
        Why: ADR-3 — partial profile preferred over total failure.
        """
        # Arrange
        plugins_root = tmp_path / "plugins"
        plugins_root.mkdir(parents=True)
        entry = _make_agent_entry(tmp_path, plugin="test-plugin")
        metadata = _make_metadata(skills=["totally-nonexistent-skill-xyz"])

        mocker.patch("agent_profile.server.get_plugins_root", return_value=plugins_root)
        mocker.patch("agent_profile.server.find_agent", return_value=entry)
        mocker.patch("agent_profile.server.parse_agent_file", return_value=(metadata, "Body."))

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("load", {"agent_name": "my-agent"})

        # Assert
        assert result.is_error is False
        assert result.data.get("skills") == []
        warnings = result.data.get("warnings", [])
        assert len(warnings) >= 1
        assert any("totally-nonexistent-skill-xyz" in w for w in warnings)


# ---------------------------------------------------------------------------
# Test: profile_load — error cases
# ---------------------------------------------------------------------------


class TestProfileLoadErrors:
    """Tests for profile_load error handling.

    Tests: profile_load error response shape.
    Strategy: Simulate FileNotFoundError and ValueError from discovery/parser
              functions; verify {"error": str} dict is returned without raising.
    """

    async def test_load_nonexistent_agent_returns_error_dict(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """profile_load returns {"error": str} for a missing agent, not an exception.

        Tests: FileNotFoundError from find_agent is caught and returned as error dict.
        How: Patch find_agent to raise FileNotFoundError, verify response shape.
        Why: MCP clients expect structured errors, not Python exceptions.
        """
        # Arrange
        mocker.patch("agent_profile.server.get_plugins_root", return_value=tmp_path / "plugins")
        mocker.patch(
            "agent_profile.server.find_agent",
            side_effect=FileNotFoundError("Agent 'ghost-agent' not found in any plugin."),
        )

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("load", {"agent_name": "ghost-agent"})

        # Assert
        assert result.is_error is False  # FastMCP returns dict, not MCP error
        assert "error" in result.data
        assert "ghost-agent" in result.data["error"]

    async def test_load_ambiguous_bare_name_returns_error_dict(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """profile_load returns {"error": str} for an ambiguous bare agent name.

        Tests: ValueError from find_agent is caught and returned as error dict.
        How: Patch find_agent to raise ValueError indicating multiple matches.
        Why: Callers must receive actionable errors to use plugin-qualified form.
        """
        # Arrange
        mocker.patch("agent_profile.server.get_plugins_root", return_value=tmp_path / "plugins")
        mocker.patch(
            "agent_profile.server.find_agent",
            side_effect=ValueError(
                "Ambiguous agent name 'code-reviewer': found in multiple plugins: alpha/code-reviewer, beta/code-reviewer."
            ),
        )

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("load", {"agent_name": "code-reviewer"})

        # Assert
        assert "error" in result.data
        assert "code-reviewer" in result.data["error"]

    async def test_load_parse_error_returns_error_dict(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """profile_load returns {"error": str} when agent file has no valid frontmatter.

        Tests: ValueError from parse_agent_file is caught and returned as error dict.
        How: Mock find_agent to succeed, mock parse_agent_file to raise ValueError.
        Why: Malformed agent files must not crash the MCP server.
        """
        # Arrange
        entry = _make_agent_entry(tmp_path)

        mocker.patch("agent_profile.server.get_plugins_root", return_value=tmp_path / "plugins")
        mocker.patch("agent_profile.server.find_agent", return_value=entry)
        mocker.patch(
            "agent_profile.server.parse_agent_file", side_effect=ValueError("No valid frontmatter found in agent file.")
        )

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("load", {"agent_name": "my-agent"})

        # Assert
        assert "error" in result.data
        assert result.is_error is False

    async def test_load_file_disappeared_after_discovery_returns_error_dict(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """profile_load returns {"error": str} when the agent file disappears post-discovery.

        Tests: FileNotFoundError from parse_agent_file is caught and returned as error.
        How: Mock find_agent to succeed, mock parse_agent_file to raise FileNotFoundError.
        Why: Race conditions must not crash the MCP server.
        """
        # Arrange
        entry = _make_agent_entry(tmp_path)

        mocker.patch("agent_profile.server.get_plugins_root", return_value=tmp_path / "plugins")
        mocker.patch("agent_profile.server.find_agent", return_value=entry)
        mocker.patch("agent_profile.server.parse_agent_file", side_effect=FileNotFoundError("File disappeared."))

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("load", {"agent_name": "my-agent"})

        # Assert
        assert "error" in result.data


# ---------------------------------------------------------------------------
# Test: profile_list
# ---------------------------------------------------------------------------


class TestProfileList:
    """Tests for the 'list' MCP tool (exposed as profile_list via backlog mount).

    Tests: profile_list tool response shape and filtering behavior.
    Strategy: Patch scan_all_agents and parse_agent_file to inject synthetic data.
    """

    async def test_list_returns_expected_top_level_keys(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """profile_list returns a dict with agents, count, and plugin_filter keys.

        Tests: profile_list response shape.
        How: Mock scan_all_agents with empty list, verify response structure.
        Why: Consumers depend on a stable top-level dict shape.
        """
        # Arrange
        mocker.patch("agent_profile.server.get_plugins_root", return_value=tmp_path / "plugins")
        mocker.patch("agent_profile.server.scan_all_agents", return_value=[])

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("list", {})

        # Assert
        assert result.is_error is False
        assert _PROFILE_LIST_KEYS.issubset(result.data.keys())
        assert result.data["agents"] == []
        assert result.data["count"] == 0
        assert result.data["plugin_filter"] is None

    async def test_list_returns_all_agents_across_plugins(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """profile_list returns one entry per agent from the synthetic plugin tree.

        Tests: profile_list enumerates multiple agents.
        How: Mock scan_all_agents with 3 entries; mock parse_agent_file; verify count.
        Why: Consumers use profile_list to discover available agents.
        """
        # Arrange
        plugins_root = tmp_path / "plugins"
        entries = [
            _make_agent_entry(tmp_path, plugin="alpha", name="agent-one"),
            _make_agent_entry(tmp_path, plugin="alpha", name="agent-two"),
            _make_agent_entry(tmp_path, plugin="beta", name="agent-three"),
        ]

        def _fake_parse(path: Path) -> tuple[AgentMetadata, str]:
            name = path.stem
            return _make_metadata(name=name, skills=["skill-a"]), "body"

        mocker.patch("agent_profile.server.get_plugins_root", return_value=plugins_root)
        mocker.patch("agent_profile.server.scan_all_agents", return_value=entries)
        mocker.patch("agent_profile.server.parse_agent_file", side_effect=_fake_parse)

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("list", {})

        # Assert
        assert result.data["count"] == 3
        assert len(result.data["agents"]) == 3

    async def test_list_entry_has_correct_keys(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """profile_list entries contain all ProfileListEntry fields.

        Tests: ProfileListEntry key presence in each agent entry.
        How: Mock a single entry and verify the entry dict shape.
        Why: Consumers must be able to display agent discovery results.
        """
        # Arrange
        plugins_root = tmp_path / "plugins"
        entry = _make_agent_entry(tmp_path, plugin="test-plugin", name="profiled-agent")
        metadata = _make_metadata(name="profiled-agent", skills=["skill-a", "skill-b"])

        mocker.patch("agent_profile.server.get_plugins_root", return_value=plugins_root)
        mocker.patch("agent_profile.server.scan_all_agents", return_value=[entry])
        mocker.patch("agent_profile.server.parse_agent_file", return_value=(metadata, "body"))

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("list", {})

        # Assert
        agent_entry = result.data["agents"][0]
        assert _PROFILE_LIST_ENTRY_KEYS.issubset(agent_entry.keys())
        assert agent_entry["name"] == "profiled-agent"
        assert agent_entry["plugin"] == "test-plugin"
        assert agent_entry["skill_count"] == 2

    async def test_list_with_plugin_filter_sets_plugin_filter_field(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """profile_list with plugin filter reflects the filter in the response.

        Tests: plugin_filter field matches the requested plugin value.
        How: Call list with plugin="alpha", verify plugin_filter in response.
        Why: Consumers use plugin_filter to confirm filtering was applied.
        """
        # Arrange
        mocker.patch("agent_profile.server.get_plugins_root", return_value=tmp_path / "plugins")
        mocker.patch("agent_profile.server.scan_all_agents", return_value=[])

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("list", {"plugin": "alpha"})

        # Assert
        assert result.data["plugin_filter"] == "alpha"

    async def test_list_with_plugin_filter_excludes_other_plugins(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """profile_list with plugin filter only returns agents from that plugin.

        Tests: plugin filtering excludes agents from other plugins.
        How: Mock scan_all_agents with agents from two plugins; filter to one.
        Why: Plugin filter is a core enumeration feature for dispatch tooling.
        """
        # Arrange
        plugins_root = tmp_path / "plugins"
        entries = [
            _make_agent_entry(tmp_path, plugin="alpha", name="alpha-agent"),
            _make_agent_entry(tmp_path, plugin="beta", name="beta-agent"),
        ]

        def _fake_parse(path: Path) -> tuple[AgentMetadata, str]:
            name = path.stem
            return _make_metadata(name=name), "body"

        mocker.patch("agent_profile.server.get_plugins_root", return_value=plugins_root)
        mocker.patch("agent_profile.server.scan_all_agents", return_value=entries)
        mocker.patch("agent_profile.server.parse_agent_file", side_effect=_fake_parse)

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("list", {"plugin": "alpha"})

        # Assert
        assert result.data["count"] == 1
        assert result.data["agents"][0]["name"] == "alpha-agent"

    async def test_list_skips_unparseable_agents_with_warning(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """profile_list skips agents that cannot be parsed and includes warnings.

        Tests: parse failure in profile_list does not fail the entire listing.
        How: Mock parse_agent_file to raise ValueError for one of two entries.
        Why: A single malformed agent file must not break the full listing.
        """
        # Arrange
        plugins_root = tmp_path / "plugins"
        entries = [
            _make_agent_entry(tmp_path, plugin="alpha", name="good-agent"),
            _make_agent_entry(tmp_path, plugin="alpha", name="bad-agent"),
        ]

        def _fake_parse(path: Path) -> tuple[AgentMetadata, str]:
            if "bad-agent" in str(path):
                raise ValueError("No valid frontmatter.")
            return _make_metadata(name=path.stem), "body"

        mocker.patch("agent_profile.server.get_plugins_root", return_value=plugins_root)
        mocker.patch("agent_profile.server.scan_all_agents", return_value=entries)
        mocker.patch("agent_profile.server.parse_agent_file", side_effect=_fake_parse)

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("list", {})

        # Assert
        assert result.data["count"] == 1
        assert result.data["agents"][0]["name"] == "good-agent"
        warnings = result.data.get("warnings", [])
        assert len(warnings) >= 1
        assert any("bad-agent" in w for w in warnings)

    async def test_list_without_filter_sets_plugin_filter_to_none(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """profile_list without plugin filter reports plugin_filter as None.

        Tests: plugin_filter is None when no plugin argument is provided.
        How: Call list with no arguments, verify plugin_filter is null.
        Why: Consumers distinguish filtered from unfiltered responses.
        """
        # Arrange
        mocker.patch("agent_profile.server.get_plugins_root", return_value=tmp_path / "plugins")
        mocker.patch("agent_profile.server.scan_all_agents", return_value=[])

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("list", {})

        # Assert
        assert result.data["plugin_filter"] is None


# ---------------------------------------------------------------------------
# Test: circular dependency via synthetic plugin tree
# ---------------------------------------------------------------------------


class TestProfileLoadCircularDependency:
    """Tests for circular skill dependency handling in profile_load.

    Tests: Circular dependency detection does not produce infinite recursion.
    Strategy: Use circular_plugin_root fixture with no mocks — the server
              uses a SkillResolver internally which detects cycles.
    """

    async def test_load_with_circular_skill_deps_returns_profile_with_warning(
        self, mocker: MockerFixture, circular_plugin_root: Path
    ) -> None:
        """profile_load returns a partial profile with warnings for circular skill deps.

        Tests: Circular A→B→A does not cause infinite recursion; warnings are present.
        How: Use circular_plugin_root fixture (skill-a→skill-b→skill-a).
             Redirect server to that root; load the agent that declares skill-a.
        Why: ADR-4 — circular dependencies produce warnings, not errors or infinite loops.
        """
        # Arrange
        agents_dir = circular_plugin_root / "circ-plugin" / "agents"
        agent_file = agents_dir / "circ-agent.md"
        entry = AgentEntry(name="circ-agent", plugin="circ-plugin", path=agent_file)
        metadata = _make_metadata(name="circ-agent", skills=["skill-a"])

        mocker.patch("agent_profile.server.get_plugins_root", return_value=circular_plugin_root)
        mocker.patch("agent_profile.server.find_agent", return_value=entry)
        mocker.patch("agent_profile.server.parse_agent_file", return_value=(metadata, "Body."))

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("load", {"agent_name": "circ-agent"})

        # Assert
        assert result.is_error is False
        assert "error" not in result.data
        warnings = result.data.get("warnings", [])
        assert len(warnings) >= 1
        assert any("circular" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# Test: flat skill resolution via synthetic plugin tree
# ---------------------------------------------------------------------------


class TestProfileLoadDomainPath:
    """Tests for flat skill URI resolution in profile_load.

    Tests: Flat skills/{name}/ URIs resolve correctly relative to the context plugin.
    Strategy: Use domain_plugin_root fixture; patch get_plugins_root only.
    """

    async def test_load_with_flat_skill_resolves_correctly(
        self, mocker: MockerFixture, domain_plugin_root: Path
    ) -> None:
        """profile_load resolves a flat skill URI to the correct SKILL.md.

        Tests: Flat skills/{name}/ format resolves relative to the context plugin.
        How: Use domain_plugin_root with enterprise-foo skill (flat, not nested).
             Mock get_plugins_root to point at that root.
        Why: Skills must be directly under skills/ — nested paths are not supported.
             This test verifies flat skill resolution works correctly.
        """
        # Arrange
        agents_dir = domain_plugin_root / "domain-plugin" / "agents"
        agent_file = agents_dir / "domain-agent.md"
        entry = AgentEntry(name="domain-agent", plugin="domain-plugin", path=agent_file)
        metadata = _make_metadata(name="domain-agent", skills=["enterprise-foo"])

        mocker.patch("agent_profile.server.get_plugins_root", return_value=domain_plugin_root)
        mocker.patch("agent_profile.server.find_agent", return_value=entry)
        mocker.patch("agent_profile.server.parse_agent_file", return_value=(metadata, "Body."))

        # Act
        async with Client(mcp) as client:
            result = await client.call_tool("load", {"agent_name": "domain-agent"})

        # Assert
        assert "error" not in result.data
        skills = result.data["skills"]
        assert len(skills) == 1
        assert skills[0]["skill_name"] == "enterprise-foo"
        assert "Enterprise Foo skill content" in skills[0]["content"]


# ---------------------------------------------------------------------------
# Test: tool registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """Tests for MCP tool registration on the agent_profile server.

    Tests: Both tools are registered and discoverable via list_tools.
    Strategy: Call client.list_tools() and verify tool names.
    """

    async def test_mcp_server_registers_load_and_list_tools(self) -> None:
        """agent_profile server exposes 'load' and 'list' as registered tools.

        Tests: Tool names are discoverable via MCP list_tools.
        How: Call client.list_tools() and check names.
        Why: Tools must be registered for any MCP client to discover and call them.
        """
        # Arrange / Act
        async with Client(mcp) as client:
            tools = await client.list_tools()

        # Assert
        tool_names = {t.name for t in tools}
        assert "load" in tool_names
        assert "list" in tool_names

    async def test_mcp_server_exposes_exactly_two_tools(self) -> None:
        """agent_profile server exposes exactly two tools: load and list.

        Tests: No unexpected tools are registered.
        How: Verify len(tools) == 2.
        Why: Tool count is part of the server contract; accidental extras cause confusion.
        """
        # Arrange / Act
        async with Client(mcp) as client:
            tools = await client.list_tools()

        # Assert
        assert len(tools) == 2


# ---------------------------------------------------------------------------
# Integration tests — real plugins/ filesystem
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRealPluginsIntegration:
    """Integration tests using the real plugins/ filesystem.

    Tests: profile_load and profile_list work end-to-end against real agent files.
    Strategy: No mocking — tools use the real get_plugins_root() resolution.
    """

    @pytest.fixture(autouse=True)
    def _set_plugin_root(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set CLAUDE_PLUGIN_ROOT to the development-harness plugin directory.

        In the MCP server process, CLAUDE_PLUGIN_ROOT may point to a plugin cache
        path rather than the development-harness repo root, causing get_plugins_root()
        to resolve to a directory with zero agents.  Overriding the env var here
        directs discovery at the correct source tree for the duration of each test.
        """
        from pathlib import Path

        # tests/test_agent_profile/test_server.py → development-harness/
        plugin_dir = str(Path(__file__).parent.parent.parent)
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", plugin_dir)

    async def test_profile_list_returns_nonzero_count(self) -> None:
        """profile_list against real plugins returns at least one agent.

        Tests: Real-filesystem agent discovery returns non-empty listing.
        How: Call list with no filter, verify count > 0.
        Why: Validates the tool works end-to-end with the actual codebase.
        """
        # Arrange / Act
        async with Client(mcp) as client:
            result = await client.call_tool("list", {})

        # Assert
        assert result.is_error is False
        assert result.data.get("count", 0) > 0

    async def test_profile_list_filtered_to_development_harness_returns_agents(self) -> None:
        """profile_list filtered to development-harness returns >= 1 agent.

        Tests: Plugin-filtered listing works with real plugin directory.
        How: Call list with plugin="development-harness", verify count.
        Why: Dispatch tooling filters by plugin to route tasks to correct agents.
        """
        # Arrange / Act
        async with Client(mcp) as client:
            result = await client.call_tool("list", {"plugin": "development-harness"})

        # Assert
        assert result.data["count"] >= 1
        assert result.data["plugin_filter"] == "development-harness"

    async def test_profile_load_task_worker_returns_nonempty_body(self) -> None:
        """profile_load for 'task-worker' returns a non-empty instruction body.

        Tests: profile_load works end-to-end against a real agent file.
        How: Call load with agent_name="task-worker", verify body and shape.
        Why: task-worker is the primary consumer of profile_load.
        """
        # Arrange / Act
        async with Client(mcp) as client:
            result = await client.call_tool("load", {"agent_name": "task-worker"})

        # Assert
        assert result.is_error is False
        assert "error" not in result.data
        assert result.data["name"] == "task-worker"
        assert result.data["plugin"] == "development-harness"
        assert len(result.data["body"]) > 0
        assert isinstance(result.data["skills"], list)
        assert isinstance(result.data["warnings"], list)

    async def test_profile_load_nonexistent_agent_returns_error_without_exception(self) -> None:
        """profile_load with an unknown agent name returns error dict, not exception.

        Tests: Error handling in real-filesystem path is consistent with mocked path.
        How: Call load with a name that cannot exist.
        Why: Verifies error path works end-to-end, not just in unit test mocks.
        """
        # Arrange / Act
        async with Client(mcp) as client:
            result = await client.call_tool("load", {"agent_name": "__no_such_agent_xyz__"})

        # Assert
        assert result.is_error is False
        assert "error" in result.data
