"""Tests for transform_to_backlink_description and bare_reference_description.

Covers #3524. The function must never fabricate a directional relationship claim
from arbitrary forward-phrase prose (verb inversion), and must never reattribute
an existing claim to the wrong entity by quoting it verbatim under a different
Entry (cross-reference-format.md fixes the Entry column as the phrase's
grammatical subject, so a phrase written about target is false, or at least
misleading, once relocated to a row whose Entry is source). The only phrase this
function ever reuses as-is is a mutual "shares" relation, which is true
regardless of which side is named as subject; everything else falls back to
bare_reference_description.
"""

from __future__ import annotations

from hypothesis import given, strategies as st

import backlink_lib as bl

# ---------------------------------------------------------------------------
# Rule 1: same-category "shares" -> append "(bidirectional)"
# ---------------------------------------------------------------------------


class TestSharesBidirectionalPattern:
    """Sharing is symmetric by definition, so reusing the phrase asserts nothing new."""

    def test_shares_same_category_bidirectional(self) -> None:
        """Same-category 'shares pattern' -> 'shares pattern (bidirectional)'."""
        result = bl.transform_to_backlink_description(
            "shares async-first design", "AgentB", "agent-frameworks", "agent-frameworks"
        )
        assert result == "shares async-first design (bidirectional)"

    def test_shares_cross_category_falls_back_to_bare_reference(self) -> None:
        """Cross-category 'shares X' does not get '(bidirectional)' -- category differs,
        so it takes the same conservative fallback as any other non-matching phrase."""
        result = bl.transform_to_backlink_description(
            "shares async-first design", "AgentB", "agent-frameworks", "tools"
        )
        assert "bidirectional" not in result
        assert result == bl.bare_reference_description("AgentB", "agent-frameworks")

    def test_shares_case_insensitive(self) -> None:
        """The 'shares' check is case-insensitive."""
        result = bl.transform_to_backlink_description(
            "Shares a queueing model", "AgentB", "agent-frameworks", "agent-frameworks"
        )
        assert result == "Shares a queueing model (bidirectional)"

    def test_leading_whitespace_tolerated(self) -> None:
        """A phrase padded by table-cell whitespace still counts as leading 'shares'."""
        result = bl.transform_to_backlink_description(
            "  shares a queueing model", "AgentB", "agent-frameworks", "agent-frameworks"
        )
        assert result.endswith("(bidirectional)")


# ---------------------------------------------------------------------------
# Regression: "shares" must be the phrase's FIRST word, not merely present
# (PR #3531 review -- a substring test wrote 25 misattributed rows into the
# corpus, 14 of them self-referential)
# ---------------------------------------------------------------------------


class TestSharesMustLeadThePhrase:
    """The common corpus shape is `<descriptor of the target>; shares <X> with
    <source>`. It contains "shares" but its leading clause describes exactly one
    entity, so relocating it under a row whose Entry is the other entity
    re-attributes that clause -- frequently producing a row asserting that X
    "shares ... with X". Only a phrase whose first word is the symmetric verb is
    subject-independent.
    """

    def test_pocketbase_robyn_case_is_not_reused(self) -> None:
        """Real PR #3531 case: robyn.md's row about PocketBase ("Go-based backend
        alternative; shares realtime and auth patterns with Robyn's WebSocket and
        SSE support") describes PocketBase -- a Go backend -- while Robyn is a
        Python framework with a Rust runtime. The backlink written into
        pocketbase.md (Entry=robyn) must not carry that description forward."""
        forward_phrase = (
            "Go-based backend alternative; shares realtime and auth patterns with Robyn's WebSocket and SSE support"
        )
        result = bl.transform_to_backlink_description(forward_phrase, "robyn", "api-frameworks", "api-frameworks")
        assert "Go-based" not in result
        assert result == "referenced by robyn (api-frameworks)"

    def test_self_referential_row_is_not_produced(self) -> None:
        """A phrase naming the source entity after "shares" must not be relocated
        onto a row whose Entry is that same entity."""
        result = bl.transform_to_backlink_description(
            "TypeScript agent framework with unified LLM API; shares skill reuse philosophy with gitagent",
            "gitagent",
            "agent-frameworks",
            "agent-frameworks",
        )
        assert "shares" not in result
        assert result == "referenced by gitagent (agent-frameworks)"

    def test_mid_phrase_shares_falls_back_even_same_category(self) -> None:
        """Same category is not enough -- the phrase must also lead with "shares"."""
        result = bl.transform_to_backlink_description(
            "Rust git worktree CLI; shares a git-centric model", "tolaria", "developer-tools", "developer-tools"
        )
        assert "bidirectional" not in result
        assert result == bl.bare_reference_description("tolaria", "developer-tools")


# ---------------------------------------------------------------------------
# Regression: leading "shares" is necessary but NOT sufficient (PR #3531 second
# review). Both cases below are latent -- no corpus row exhibits either -- and
# both defeated the earlier `startswith("shares")` guard.
# ---------------------------------------------------------------------------


class TestLeadingSharesIsNotSufficient:
    """The guard claimed a phrase beginning with the symmetric verb "reads the
    same regardless of which entry is named as Entry". Two shapes falsify that.
    """

    def test_word_prefix_is_not_the_verb(self) -> None:
        """`startswith` has no word boundary: "shareset" is not "shares"."""
        result = bl.transform_to_backlink_description(
            "shareset semantics differ", "robyn", "api-frameworks", "api-frameworks"
        )
        assert "bidirectional" not in result
        assert result == bl.bare_reference_description("robyn", "api-frameworks")

    def test_trailing_with_source_would_self_reference(self) -> None:
        """ "shares <X> with <source>" leads with the verb and is still not symmetric.

        The backlink row names the source as Entry, and Entry is the phrase's
        grammatical subject, so carrying it over asserts "Robyn shares a queueing
        model with Robyn".
        """
        result = bl.transform_to_backlink_description(
            "shares a queueing model with Robyn", "Robyn", "api-frameworks", "api-frameworks"
        )
        assert "bidirectional" not in result
        assert result == bl.bare_reference_description("Robyn", "api-frameworks")

    def test_source_named_outside_a_with_clause_stays_eligible(self) -> None:
        """Only the "with" construction collapses subject into object.

        A phrase that mentions the source elsewhere is redundant under the
        source's own Entry, not false. Seven corpus rows have this shape and
        must keep their content.
        """
        forward_phrase = (
            "Shares Tauri + Rust cross-platform desktop architecture; Yume focuses on multi-agent orchestration UI"
        )
        result = bl.transform_to_backlink_description(forward_phrase, "Yume", "developer-tools", "developer-tools")
        assert result == f"{forward_phrase} (bidirectional)"


# ---------------------------------------------------------------------------
# Rule 2: bare_reference_description fallback -- no verb inversion, no verbatim
# reattribution, ever
# ---------------------------------------------------------------------------


class TestBareReferenceFallback:
    """Every non-'shares' phrase falls back to bare_reference_description."""

    def test_fallback_on_unknown_phrase(self) -> None:
        """Unrecognized phrase -> bare reference, no invented direction or reused content."""
        result = bl.transform_to_backlink_description(
            "is adjacent to deployment pipeline", "Alpha", "agent-frameworks", "tools"
        )
        assert result == "referenced by Alpha (agent-frameworks)"

    def test_fallback_does_not_reuse_forward_phrase_content(self) -> None:
        """The forward phrase's words never appear in the fallback output."""
        result = bl.transform_to_backlink_description(
            "totally unknown relationship", "SomeTool", "tools", "coding-agents"
        )
        assert "totally unknown relationship" not in result
        assert result == "referenced by SomeTool (tools)"

    def test_fallback_delegates_to_bare_reference_description(self) -> None:
        """The fallback is bare_reference_description itself, not a duplicated template."""
        result = bl.transform_to_backlink_description("some relationship", "AuthSvc", "tools", "api-frameworks")
        assert result == bl.bare_reference_description("AuthSvc", "tools")


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
        assert result == "referenced by Alpha (agent-frameworks)"

    def test_issue_reproduction_cgc_skylos_case(self) -> None:
        """The exact #3524 reproduction case: no fabricated MCP integration claim."""
        result = bl.transform_to_backlink_description(
            "provides AST graph context and dead-code analysis through MCP", "Skylos", "code-auditing", "mcp-ecosystem"
        )
        assert "consumes" not in result
        assert "AST graph context" not in result
        assert result == "referenced by Skylos (code-auditing)"

    def test_extends_is_not_inverted(self) -> None:
        """'extends X' must not become 'is extended by X'."""
        result = bl.transform_to_backlink_description(
            "extends tree-sitter parsing", "SoulForge", "coding-agents", "tools"
        )
        assert result == "referenced by SoulForge (coding-agents)"

    def test_inverse_verbs_table_removed(self) -> None:
        """The INVERSE_VERBS verb-substitution table no longer exists in the module."""
        assert not hasattr(bl, "INVERSE_VERBS")


# ---------------------------------------------------------------------------
# Regression: verbatim reattribution must not misattribute the target's own
# capability to the source entry (second root cause found in PR #3525 review)
# ---------------------------------------------------------------------------


class TestNoVerbatimReattributionRegression:
    """A forward phrase describes whoever is named as Entry in its *original* row --
    per cross-reference-format.md, the Entry column is the phrase's grammatical
    subject. Reusing that phrase verbatim in a new row whose Entry is a different
    entity keeps the words attached to the wrong subject. This function must never
    do that for a non-"shares" phrase.
    """

    def test_syft_hound_case_does_not_attribute_hound_capability_to_syft(self) -> None:
        """Real #3525-review case: syft.md's row about Hound ('complements SBOM
        generation with hypothesis-driven security analysis...') describes Hound,
        not Syft. The backlink written into hound.md (Entry=Syft) must not carry
        that description forward as if it were about Syft."""
        forward_phrase = (
            "Complements SBOM generation with hypothesis-driven security analysis "
            "and knowledge graph-based vulnerability reasoning"
        )
        result = bl.transform_to_backlink_description(forward_phrase, "Syft", "code-auditing", "code-auditing")
        assert "hypothesis-driven security analysis" not in result
        assert result == "referenced by Syft (code-auditing)"

    def test_phrase_naming_targets_own_display_name_is_not_reused(self) -> None:
        """A phrase describing the target by name is not safe to reuse under a
        different Entry -- it still describes the same entity by name, now
        misleadingly placed under the source's row."""
        result = bl.transform_to_backlink_description(
            "OmniRoute routes requests to this backend", "LocalAI", "llm-infrastructure", "api-frameworks"
        )
        assert "OmniRoute" not in result
        assert result == "referenced by LocalAI (llm-infrastructure)"


# ---------------------------------------------------------------------------
# bare_reference_description: single source of truth for the conservative floor
# ---------------------------------------------------------------------------


class TestBareReferenceDescription:
    """Used both as transform_to_backlink_description's fallback and when no
    forward phrase exists at all (no parseable forward row)."""

    def test_bare_reference_names_source_and_category(self) -> None:
        """Bare reference names the source entry and its category."""
        result = bl.bare_reference_description("Alpha", "agent-frameworks")
        assert result == "referenced by Alpha (agent-frameworks)"


# ---------------------------------------------------------------------------
# Property: no non-"shares" phrase ever leaks into the output (generalizes the
# two named regressions above to arbitrary prose, per PR #3525 review point 3 --
# exact-string assertions on known bad inputs would not catch a new phrase shape
# that reintroduces verbatim reattribution)
# ---------------------------------------------------------------------------


class TestNeverLeaksForwardPhraseContent:
    """For any forward phrase that does not trigger the "shares" rule, the output
    must be exactly bare_reference_description(source_name, source_category) --
    none of the forward phrase's own words may appear in it, regardless of verb,
    proper nouns, or phrasing."""

    @given(
        forward_phrase=st.text(min_size=1, max_size=200).filter(lambda s: not s.lstrip().lower().startswith("shares")),
        source_name=st.sampled_from(["Alpha", "Syft", "LocalAI", "Skylos"]),
        source_category=st.sampled_from(["tools", "code-auditing", "llm-infrastructure"]),
        target_category=st.sampled_from(["tools", "code-auditing", "llm-infrastructure", "mcp-ecosystem"]),
    )
    def test_non_shares_phrase_never_appears_in_output(
        self, forward_phrase: str, source_name: str, source_category: str, target_category: str
    ) -> None:
        """No forward-phrase content reaches the output unless it hit the "shares" rule."""
        result = bl.transform_to_backlink_description(forward_phrase, source_name, source_category, target_category)
        # Equality against the fixed bare-reference template is the property itself: it can
        # only hold if none of forward_phrase's content survived into the output.
        assert result == bl.bare_reference_description(source_name, source_category)
