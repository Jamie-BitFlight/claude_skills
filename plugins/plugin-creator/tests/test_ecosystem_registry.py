"""Tests for ecosystem_registry module.

Tests the public API of ecosystem_registry.py:
- get_ecosystem_owned_skill_keys() return value and type
- get_ecosystem_owned_agent_keys() return value and type
- get_ecosystem_for_key() for owned, standard, and unknown keys, including agent branch
- Immutability guarantee of returned frozensets
"""

from __future__ import annotations

import pytest

import ecosystem_registry as _reg
from ecosystem_registry import (
    EcosystemSpec,
    get_ecosystem_for_key,
    get_ecosystem_owned_agent_keys,
    get_ecosystem_owned_skill_keys,
)


class TestGetEcosystemOwnedKeys:
    """Tests for get_ecosystem_owned_skill_keys() public function.

    Scope: Verifies return value contains the expected OpenCode key,
    return type is frozenset (immutable), and no Claude Code standard
    fields bleed into the owned-keys set.

    Strategy: Black-box tests against the module's public API; no
    knowledge of internal _REGISTRY structure required.
    """

    def test_contains_mcp(self) -> None:
        """get_ecosystem_owned_skill_keys() includes 'mcp'.

        Tests: OpenCode mcp field appears in owned-keys set
        How: Call function, check 'mcp' membership
        Why: The mcp key is the sole registered OpenCode skill_frontmatter_key;
             plugin_validator.py depends on this membership check to skip FM009
             rewrites on mcp: blocks.
        """
        # Arrange / Act
        owned = get_ecosystem_owned_skill_keys()

        # Assert
        assert "mcp" in owned

    def test_returns_frozenset(self) -> None:
        """get_ecosystem_owned_skill_keys() returns a frozenset, not a plain set.

        Tests: Return type is frozenset
        How: Call function, check isinstance
        Why: plugin_validator.py stores the result in a local variable and
             checks membership in a loop; frozenset guarantees callers cannot
             accidentally mutate the registry by calling .add() or .discard().
        """
        # Arrange / Act
        owned = get_ecosystem_owned_skill_keys()

        # Assert
        assert isinstance(owned, frozenset)

    def test_frozenset_is_immutable(self) -> None:
        """Returned frozenset raises AttributeError on attempted mutation.

        Tests: Immutability contract of returned value
        How: Attempt frozenset.add() and expect AttributeError
        Why: Callers must not be able to expand the owned-key set at runtime;
             frozenset enforces this at the language level.
        """
        # Arrange
        owned = get_ecosystem_owned_skill_keys()

        # Act / Assert — use getattr to invoke .add() dynamically, since
        # frozenset has no .add attribute and ty correctly flags direct calls.
        method_name = "add"
        with pytest.raises(AttributeError):
            getattr(owned, method_name)("test")

    def test_description_not_in_owned_keys(self) -> None:
        """Claude Code's 'description' field is not in ecosystem-owned keys.

        Tests: Standard Claude Code fields are absent from the owned-keys set
        How: Check 'description' is not a member of get_ecosystem_owned_skill_keys()
        Why: description is a Claude Code field; if it were marked as
             ecosystem-owned, FM009 fixes would silently stop applying to it,
             breaking validation for Claude Code-only skills.
        """
        # Arrange / Act
        owned = get_ecosystem_owned_skill_keys()

        # Assert
        assert "description" not in owned


class TestGetEcosystemForKey:
    """Tests for get_ecosystem_for_key() public function.

    Scope: Verifies correct ecosystem name returned for known keys,
    None returned for standard and unknown keys, and parametrized
    coverage of multiple unknown key shapes.

    Strategy: Direct calls with specific inputs; relies only on the
    public contract, not on _REGISTRY internals.
    """

    def test_mcp_returns_opencode(self) -> None:
        """get_ecosystem_for_key('mcp') returns 'opencode'.

        Tests: OpenCode owns the mcp frontmatter key
        How: Call with 'mcp', assert return value equals 'opencode'
        Why: plugin_validator.py uses this to emit a named ecosystem in
             diagnostic messages; the exact string 'opencode' must match.
        """
        # Arrange / Act
        result = get_ecosystem_for_key("mcp")

        # Assert
        assert result == "opencode"

    def test_description_returns_none(self) -> None:
        """get_ecosystem_for_key('description') returns None.

        Tests: Standard Claude Code fields are not ecosystem-owned
        How: Call with 'description', assert return value is None
        Why: description is a Claude Code field; returning None here signals
             to plugin_validator.py that FM009 processing should proceed
             normally for this key.
        """
        # Arrange / Act
        result = get_ecosystem_for_key("description")

        # Assert
        assert result is None

    def test_unknown_key_returns_none(self) -> None:
        """get_ecosystem_for_key with an unregistered key returns None.

        Tests: Keys not owned by any ecosystem return None
        How: Call with 'unknown-field-xyz', assert return value is None
        Why: Any key absent from all ecosystem registries must return None
             so the validator applies standard FM009 logic to it.
        """
        # Arrange / Act
        result = get_ecosystem_for_key("unknown-field-xyz")

        # Assert
        assert result is None

    @pytest.mark.parametrize(
        "unknown_key", ["name", "tools", "user-invocable", "skills", "hooks", "memory", "completely-made-up-key", ""]
    )
    def test_various_unknown_keys_return_none(self, unknown_key: str) -> None:
        """get_ecosystem_for_key returns None for all non-ecosystem keys.

        Tests: Parametrized coverage of multiple unknown key shapes
        How: Call with each key in the parametrize list, assert None
        Why: Ensures the function does not produce false positives for any
             Claude Code standard field or arbitrary unregistered key; a false
             positive would suppress FM009 fixes incorrectly.
        """
        # Arrange / Act
        result = get_ecosystem_for_key(unknown_key)

        # Assert
        assert result is None, f"Expected None for key {unknown_key!r}, got {result!r}"

    def test_agent_frontmatter_key_returns_ecosystem(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_ecosystem_for_key() checks agent_frontmatter_keys, not only skill_frontmatter_keys.

        Tests: The agent_frontmatter_keys branch in get_ecosystem_for_key()
        How: Monkeypatch _REGISTRY with a test ecosystem declaring an agent-only key;
             call get_ecosystem_for_key() and assert it returns the ecosystem name.
        Why: No current registered ecosystem has agent_frontmatter_keys, so this branch
             is only reachable via injection. Without this test the branch is uncovered
             and a regression (e.g. dropping the agent_frontmatter_keys check) would go
             undetected.
        """
        # Arrange — inject a registry entry with an agent-only key
        test_spec = EcosystemSpec(
            display_name="TestEco",
            source_url="https://example.com",
            verified_date="2026-01-01",
            skill_frontmatter_keys=frozenset(),
            agent_frontmatter_keys=frozenset({"agent-only-key"}),
            notes="",
        )
        monkeypatch.setattr(_reg, "_REGISTRY", {"testeco": test_spec})

        # Act
        result = get_ecosystem_for_key("agent-only-key")

        # Assert
        assert result == "testeco"


class TestGetEcosystemOwnedAgentKeys:
    """Tests for get_ecosystem_owned_agent_keys() public function.

    Scope: Verifies return type is frozenset (immutable) and that the function
    is symmetric with get_ecosystem_owned_skill_keys() — same contract, different
    field. Current registry has no agent keys so the set is empty; tests verify
    shape and immutability, not membership.

    Strategy: Black-box tests against the public API; immutability via attribute
    access attempt; future membership tests belong here when agent keys are added.
    """

    def test_returns_frozenset(self) -> None:
        """get_ecosystem_owned_agent_keys() returns a frozenset, not a plain set.

        Tests: Return type is frozenset
        How: Call function, check isinstance
        Why: Same immutability contract as get_ecosystem_owned_skill_keys(); callers
             must not be able to mutate the registry guard set at runtime.
        """
        # Arrange / Act
        owned = get_ecosystem_owned_agent_keys()

        # Assert
        assert isinstance(owned, frozenset)

    def test_frozenset_is_immutable(self) -> None:
        """Returned frozenset raises AttributeError on attempted mutation.

        Tests: Immutability contract of returned value
        How: Attempt frozenset.add() and expect AttributeError
        Why: Same contract as the skill-keys guard set.
        """
        # Arrange
        owned = get_ecosystem_owned_agent_keys()

        # Act / Assert
        method_name = "add"
        with pytest.raises(AttributeError):
            getattr(owned, method_name)("test")

    def test_currently_empty(self) -> None:
        """get_ecosystem_owned_agent_keys() is empty when no ecosystem declares agent keys.

        Tests: Zero-impact current state documented as a test
        How: Assert len == 0
        Why: All current ecosystems have empty agent_frontmatter_keys. This test
             documents the expected current state and will fail (as intended) when
             an ecosystem adds an agent key, prompting a review of the guard set.
        """
        # Arrange / Act
        owned = get_ecosystem_owned_agent_keys()

        # Assert
        assert len(owned) == 0

    def test_skill_key_not_in_agent_keys(self) -> None:
        """The 'mcp' skill key is absent from the agent-owned keys set.

        Tests: Skill and agent key sets are disjoint for the current registry
        How: Check 'mcp' is not a member of get_ecosystem_owned_agent_keys()
        Why: mcp is registered as a skill_frontmatter_key only; including it in
             the agent guard set would incorrectly suppress FM009 on agent files.
        """
        # Arrange / Act
        owned = get_ecosystem_owned_agent_keys()

        # Assert
        assert "mcp" not in owned
