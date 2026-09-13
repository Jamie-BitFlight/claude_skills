"""Tests for transform_to_backlink_description and bare_reference_description.

Covers #3524: the function must never fabricate a directional relationship claim
from arbitrary forward-phrase prose. It only marks an already-symmetric "shares"
phrase as bidirectional, or attributes the forward phrase verbatim -- it never
inverts a verb.
"""

from __future__ import annotations

import backlink_lib as bl

# ---------------------------------------------------------------------------
# Rule 1: same-category "shares" -> append "(bidirectional)"
# ---------------------------------------------------------------------------


class TestSharesBidirectionalPattern:
    """Sharing is symmetric by definition, so marking it bidirectional asserts nothing new."""

    def test_shares_same_category_bidirectional(self) -> None:
        """Same-category 'shares pattern' -> 'shares pattern (bidirectional)'."""
        result = bl.transform_to_backlink_description(
            "shares async-first design", "AgentB", "agent-frameworks", "agent-frameworks"
        )
        assert result == "shares async-first design (bidirectional)"

    def test_shares_cross_category_falls_through_to_attribution(self) -> None:
        """Cross-category 'shares X' does not get '(bidirectional)' -- category differs."""
        result = bl.transform_to_backlink_description(
            "shares async-first design", "AgentB", "agent-frameworks", "tools"
        )
        assert "bidirectional" not in result
        assert result == "cites this entry: shares async-first design"

    def test_shares_case_insensitive(self) -> None:
        """The 'shares' check is case-insensitive."""
        result = bl.transform_to_backlink_description(
            "Shares a queueing model", "AgentB", "agent-frameworks", "agent-frameworks"
        )
        assert result == "Shares a queueing model (bidirectional)"


# ---------------------------------------------------------------------------
# Rule 2: attribution fallback -- no verb inversion, ever
# ---------------------------------------------------------------------------


class TestAttributionFallback:
    """Every non-'shares' phrase is attributed verbatim, never inverted."""

    def test_fallback_on_unknown_phrase(self) -> None:
        """Unrecognized phrase -> attributed verbatim, no invented direction."""
        result = bl.transform_to_backlink_description(
            "is adjacent to deployment pipeline", "Alpha", "agent-frameworks", "tools"
        )
        assert result == "cites this entry: is adjacent to deployment pipeline"

    def test_fallback_preserves_forward_phrase_verbatim(self) -> None:
        """The forward phrase is never altered -- only prefixed with attribution."""
        result = bl.transform_to_backlink_description(
            "totally unknown relationship", "SomeTool", "tools", "coding-agents"
        )
        assert result == "cites this entry: totally unknown relationship"

    def test_fallback_does_not_restate_source_name_or_category(self) -> None:
        """Attribution never duplicates the Entry/Category columns already in the row."""
        result = bl.transform_to_backlink_description("some relationship", "AuthSvc", "tools", "api-frameworks")
        assert "AuthSvc" not in result
        assert "tools" not in result


# ---------------------------------------------------------------------------
# Regression: directional verbs must not be inverted (root cause of #3524)
# ---------------------------------------------------------------------------


class TestNoVerbInversionRegression:
    """A forward phrase that starts with a directional verb must not be inverted.

    These are the exact failure modes reported in #3524: the removed INVERSE_VERBS
    table asserted a "consumes" relationship for "provides" phrases (dangling
    fragment, and no way to verify the claimed integration is real), and collapsed
    "complements" phrases to a category-restating template that discarded all
    relationship content.
    """

    def test_provides_is_not_inverted_to_consumes(self) -> None:
        """'provides X' must not become 'consumes X provided by' (dangling, unverifiable)."""
        result = bl.transform_to_backlink_description("provides embedding layer", "Alpha", "agent-frameworks", "tools")
        assert not result.startswith("consumes")
        assert "provided by" not in result
        assert result == "cites this entry: provides embedding layer"

    def test_issue_reproduction_cgc_skylos_case(self) -> None:
        """The exact #3524 reproduction case: no fabricated MCP integration claim."""
        result = bl.transform_to_backlink_description(
            "provides AST graph context and dead-code analysis through MCP", "Skylos", "code-auditing", "mcp-ecosystem"
        )
        assert "consumes" not in result
        assert not result.endswith("provided by")
        assert result == "cites this entry: provides AST graph context and dead-code analysis through MCP"

    def test_complements_does_not_collapse_to_category_restatement(self) -> None:
        """'complements X' must not become 'is complemented by {name} ({category})' -- that
        discards the actual relationship content and restates columns already in the row."""
        result = bl.transform_to_backlink_description(
            "complements drift detection", "Logfire", "ai-observability", "ai-observability"
        )
        assert "Logfire" not in result
        assert "ai-observability" not in result
        assert "complements drift detection" in result

    def test_extends_is_not_inverted(self) -> None:
        """'extends X' must not become 'is extended by X'."""
        result = bl.transform_to_backlink_description(
            "extends tree-sitter parsing", "SoulForge", "coding-agents", "tools"
        )
        assert result == "cites this entry: extends tree-sitter parsing"

    def test_inverse_verbs_table_removed(self) -> None:
        """The INVERSE_VERBS verb-substitution table no longer exists in the module."""
        assert not hasattr(bl, "INVERSE_VERBS")


# ---------------------------------------------------------------------------
# bare_reference_description: single source of truth for the no-forward-phrase case
# ---------------------------------------------------------------------------


class TestBareReferenceDescription:
    """Used only when no forward phrase exists at all (distinct from low-confidence inversion)."""

    def test_bare_reference_names_source_and_category(self) -> None:
        """Bare reference names the source entry and its category."""
        result = bl.bare_reference_description("Alpha", "agent-frameworks")
        assert result == "referenced by Alpha (agent-frameworks)"
