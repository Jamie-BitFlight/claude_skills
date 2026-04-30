"""Tests for ecosystem_registry module.

Tests the public API of ecosystem_registry.py:
- get_ecosystem_owned_skill_keys() return value and type
- get_ecosystem_for_key() for owned, standard, and unknown keys
- Immutability guarantee of returned frozenset
"""

from __future__ import annotations

import pytest

import ecosystem_registry
from ecosystem_registry import EcosystemSpec, get_ecosystem_for_key, get_ecosystem_owned_skill_keys


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

    def test_finds_key_in_agent_frontmatter_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_ecosystem_for_key() returns ecosystem name for agent_frontmatter_keys.

        Tests: agent_frontmatter_keys branch of get_ecosystem_for_key()
        How: Monkeypatch _REGISTRY with a test ecosystem whose agent_frontmatter_keys
             contains 'agent_test_key'; call function; assert ecosystem name returned
        Why: This branch (checking spec.agent_frontmatter_keys) had no test coverage.
             Future ecosystems with agent-specific keys must be discoverable via this
             function, and the branch must not regress silently.
        """
        # Arrange — register a test ecosystem with an agent-only key
        test_spec = EcosystemSpec(
            display_name="TestEco",
            source_url="https://test.example.com",
            verified_date="2026-01-01",
            skill_frontmatter_keys=frozenset(),
            agent_frontmatter_keys=frozenset({"agent_test_key"}),
            notes="Test-only ecosystem for branch coverage",
        )
        monkeypatch.setitem(ecosystem_registry._REGISTRY, "testeco", test_spec)

        # Act
        result = get_ecosystem_for_key("agent_test_key")

        # Assert
        assert result == "testeco"


class TestOwnedKeysUnionBothFieldTypes:
    """Regression tests verifying _ECOSYSTEM_OWNED_SKILL_KEYS unions both key types.

    Before fix: frozenset().union(*(spec.skill_frontmatter_keys ...)) omitted agent keys.
    After fix: frozenset().union(*(skill_keys | agent_keys ...)) includes both.
    """

    def test_owned_keys_includes_agent_frontmatter_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_ecosystem_owned_skill_keys() returns keys from agent_frontmatter_keys.

        Tests: _ECOSYSTEM_OWNED_SKILL_KEYS unions both skill and agent key types
        How: Patch _REGISTRY with a test ecosystem that has agent_frontmatter_keys;
             assert the old (buggy) pattern omits the agent key; assert the new
             (fixed) pattern includes it; patch the module constant and verify
             the public function returns it.
        Why: Before fix, the generator expression referenced only skill_frontmatter_keys,
             silently excluding agent_frontmatter_keys from the guard set.
        """
        # Arrange — register a test ecosystem with both skill and agent keys
        test_spec = EcosystemSpec(
            display_name="TestEco",
            source_url="https://test.example.com",
            verified_date="2026-01-01",
            skill_frontmatter_keys=frozenset({"skill_test_key"}),
            agent_frontmatter_keys=frozenset({"agent_test_key"}),
            notes="Test-only ecosystem for regression coverage",
        )
        monkeypatch.setitem(ecosystem_registry._REGISTRY, "testeco", test_spec)

        # Verify the OLD (buggy) pattern omits agent keys
        old_pattern = frozenset().union(
            *(spec.skill_frontmatter_keys for spec in ecosystem_registry._REGISTRY.values())
        )
        assert "agent_test_key" not in old_pattern, "Old pattern should omit agent keys (documents the bug)"

        # Verify the NEW (fixed) pattern includes agent keys
        new_pattern = frozenset().union(
            *(
                spec.skill_frontmatter_keys | spec.agent_frontmatter_keys
                for spec in ecosystem_registry._REGISTRY.values()
            )
        )
        assert "agent_test_key" in new_pattern, "New pattern must include agent_frontmatter_keys"
        assert "skill_test_key" in new_pattern, "New pattern must still include skill_frontmatter_keys"

        # Verify the public function returns the fixed pattern
        monkeypatch.setattr(ecosystem_registry, "_ECOSYSTEM_OWNED_SKILL_KEYS", new_pattern)
        owned = get_ecosystem_owned_skill_keys()
        assert "agent_test_key" in owned
        assert "skill_test_key" in owned
