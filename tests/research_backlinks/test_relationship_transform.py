"""Tests for transform_to_backlink_description: all 9 Appendix patterns + fallback."""

from __future__ import annotations

import pytest

import backlink_lib as bl

# ---------------------------------------------------------------------------
# Pattern 1: "provides X" → "consumes X provided by"
# ---------------------------------------------------------------------------


class TestProvidesPattern:
    """Pattern 1: 'provides' verb inversion."""

    def test_provides_simple(self) -> None:
        """'provides embedding layer' → 'consumes embedding layer provided by'."""
        result = bl.transform_to_backlink_description("provides embedding layer", "Alpha", "agent-frameworks", "tools")
        assert result == "consumes embedding layer provided by"

    def test_provides_preserves_rest(self) -> None:
        """Remainder after 'provides' is preserved in output."""
        result = bl.transform_to_backlink_description("provides async task queue", "Celery", "tools", "api-frameworks")
        assert "async task queue" in result
        assert result.startswith("consumes")

    def test_provides_no_rest(self) -> None:
        """'provides' alone still produces 'consumes  provided by' (rest is empty)."""
        result = bl.transform_to_backlink_description("provides", "Alpha", "agent-frameworks", "tools")
        assert result == "consumes  provided by"


# ---------------------------------------------------------------------------
# Pattern 2: "consumes X" → "provides X"
# ---------------------------------------------------------------------------


class TestConsumesPattern:
    """Pattern 2: 'consumes' verb inversion."""

    def test_consumes_inverted(self) -> None:
        """'consumes context window' → 'provides context window'."""
        result = bl.transform_to_backlink_description("consumes context window", "Ctx", "context-management", "tools")
        assert result.startswith("provides")
        assert "context window" in result


# ---------------------------------------------------------------------------
# Pattern 3: "extends X" → "is extended by X"
# ---------------------------------------------------------------------------


class TestExtendsPattern:
    """Pattern 3: 'extends' symmetric rest verb."""

    def test_extends_with_rest(self) -> None:
        """'extends tree-sitter parsing' → 'is extended by tree-sitter parsing'."""
        result = bl.transform_to_backlink_description(
            "extends tree-sitter parsing", "SoulForge", "coding-agents", "tools"
        )
        assert result == "is extended by tree-sitter parsing"

    def test_extends_no_rest(self) -> None:
        """'extends' with empty rest uses source_name fallback."""
        result = bl.transform_to_backlink_description("extends", "MyTool", "tools", "agent-frameworks")
        assert result == "is extended by MyTool (tools)"


# ---------------------------------------------------------------------------
# Pattern 4: "wraps X" → "is wrapped by X"
# ---------------------------------------------------------------------------


class TestWrapsPattern:
    """Pattern 4: 'wraps' symmetric rest verb."""

    def test_wraps_with_rest(self) -> None:
        """'wraps the OpenAI SDK' → 'is wrapped by the OpenAI SDK'."""
        result = bl.transform_to_backlink_description("wraps the OpenAI SDK", "Wrapper", "tools", "api-frameworks")
        assert result == "is wrapped by the OpenAI SDK"


# ---------------------------------------------------------------------------
# Pattern 5: "orchestrates X" → "is orchestrated by X"
# ---------------------------------------------------------------------------


class TestOrchestratesPattern:
    """Pattern 5: 'orchestrates' symmetric rest verb."""

    def test_orchestrates_with_rest(self) -> None:
        """'orchestrates worker agents' → 'is orchestrated by worker agents'."""
        result = bl.transform_to_backlink_description(
            "orchestrates worker agents", "Conductor", "agent-frameworks", "tools"
        )
        assert result == "is orchestrated by worker agents"


# ---------------------------------------------------------------------------
# Pattern 6: "calls X" → "is called by X"
# ---------------------------------------------------------------------------


class TestCallsPattern:
    """Pattern 6: 'calls' symmetric rest verb."""

    def test_calls_with_rest(self) -> None:
        """'calls the REST API' → 'is called by the REST API'."""
        result = bl.transform_to_backlink_description("calls the REST API", "Client", "tools", "api-frameworks")
        assert result == "is called by the REST API"


# ---------------------------------------------------------------------------
# Pattern 7: "implements X" → "is implemented by X"
# ---------------------------------------------------------------------------


class TestImplementsPattern:
    """Pattern 7: 'implements' symmetric rest verb."""

    def test_implements_with_rest(self) -> None:
        """'implements MCP protocol' → 'is implemented by MCP protocol'."""
        result = bl.transform_to_backlink_description("implements MCP protocol", "Server", "tools", "api-frameworks")
        assert result == "is implemented by MCP protocol"


# ---------------------------------------------------------------------------
# Pattern 8: "complements X" → "is complemented by {source_name} ({source_category})"
# ---------------------------------------------------------------------------


class TestComplementsPattern:
    """Pattern 8: 'complements' uses source_name in output."""

    def test_complements_uses_source_name(self) -> None:
        """'complements drift detection' → 'is complemented by Logfire (ai-observability)'."""
        result = bl.transform_to_backlink_description(
            "complements drift detection", "Logfire", "ai-observability", "ai-observability"
        )
        assert result == "is complemented by Logfire (ai-observability)"

    def test_complements_cross_category(self) -> None:
        """'complements async pipeline' uses source_name regardless of category."""
        result = bl.transform_to_backlink_description(
            "complements async pipeline", "AsyncTool", "tools", "api-frameworks"
        )
        assert "AsyncTool" in result
        assert "tools" in result


# ---------------------------------------------------------------------------
# Pattern 9: same-category "shares" → append "(bidirectional)"
# ---------------------------------------------------------------------------


class TestSharesBidirectionalPattern:
    """Pattern 9: same-category 'shares' appends '(bidirectional)'."""

    def test_shares_same_category_bidirectional(self) -> None:
        """Same-category 'shares pattern' → 'shares pattern (bidirectional)'."""
        result = bl.transform_to_backlink_description(
            "shares async-first design", "AgentB", "agent-frameworks", "agent-frameworks"
        )
        assert result == "shares async-first design (bidirectional)"

    def test_shares_cross_category_no_bidirectional(self) -> None:
        """Cross-category 'shares X' falls through to fallback (no 'bidirectional')."""
        result = bl.transform_to_backlink_description(
            "shares async-first design", "AgentB", "agent-frameworks", "tools"
        )
        # Cross-category: 'shares' not preceded by a known verb → fallback
        assert "bidirectional" not in result


# ---------------------------------------------------------------------------
# Pattern 10: fallback — no known verb, cross-category
# ---------------------------------------------------------------------------


class TestFallbackPattern:
    """Pattern 10: fallback 'referenced by {source_name} ({source_category})'."""

    def test_fallback_on_unknown_phrase(self) -> None:
        """Unrecognized phrase → 'referenced by Alpha (agent-frameworks)'."""
        result = bl.transform_to_backlink_description(
            "is adjacent to deployment pipeline", "Alpha", "agent-frameworks", "tools"
        )
        assert result == "referenced by Alpha (agent-frameworks)"

    def test_fallback_preserves_source_name(self) -> None:
        """Fallback includes the exact source_name provided."""
        result = bl.transform_to_backlink_description(
            "totally unknown relationship", "SomeTool", "tools", "coding-agents"
        )
        assert "SomeTool" in result
        assert "tools" in result

    def test_case_insensitive_verb_matching(self) -> None:
        """Verb matching is case-insensitive (phrase_lower used)."""
        result = bl.transform_to_backlink_description(
            "Provides authentication layer", "AuthSvc", "tools", "api-frameworks"
        )
        # "Provides" starts with known verb "provides" in lowercase check
        assert result.startswith("consumes")


# ---------------------------------------------------------------------------
# Inverse verb table completeness
# ---------------------------------------------------------------------------


class TestInverseVerbTable:
    """Verify all listed INVERSE_VERBS keys produce distinct transforms."""

    @pytest.mark.parametrize(
        ("verb", "expected_inverse"),
        [
            ("provides", "consumes"),
            ("consumes", "provides"),
            ("extends", "is extended by"),
            ("is extended by", "extends"),
            ("wraps", "is wrapped by"),
            ("is wrapped by", "wraps"),
            ("feeds", "is fed by"),
            ("orchestrates", "is orchestrated by"),
            ("delegates to", "receives delegation from"),
            ("calls", "is called by"),
            ("implements", "is implemented by"),
            ("replaces", "is replaced by"),
            ("complements", "is complemented by"),
            ("alternatives to", "alternative for"),
        ],
    )
    def test_inverse_verb_in_table(self, verb: str, expected_inverse: str) -> None:
        """Each verb maps to expected_inverse in INVERSE_VERBS dict."""
        assert verb in bl.INVERSE_VERBS
        assert bl.INVERSE_VERBS[verb] == expected_inverse
