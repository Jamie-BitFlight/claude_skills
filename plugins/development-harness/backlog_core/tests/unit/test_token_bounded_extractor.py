"""Tests for TokenBoundedExtractor.extract() — TDD, authored before T18 implementation.

These tests intentionally fail at collection (ModuleNotFoundError) until T18
creates ``backlog_core/disclosure_handler.py`` and implements ``TokenBoundedExtractor``.
That is the correct TDD state.

Behavioral contract pinned by this file:

1. **Windowing**: ``extract(content, head_tokens, skip_tokens=0)`` returns the first
   ``head_tokens`` tokens of ``content`` (decoded). ``returned_tokens == head_tokens``
   and ``truncated=True`` when ``total_tokens > head_tokens``.
2. **No truncation**: When ``head_tokens >= total_tokens``, ``truncated=False`` and
   ``returned_tokens == total_tokens`` (not ``head_tokens``).
3. **Continuation**: ``skip_tokens=<previous returned_tokens>`` advances the window to
   the next token slice. Calling repeatedly until ``truncated=False`` exhausts content.
4. **Overshoot skip**: ``skip_tokens >= total_tokens`` returns ``content == ""``,
   ``truncated=False``, ``returned_tokens == 0``.
5. **total_tokens invariant**: ``total_tokens`` always equals the cl100k_base token count
   of the FULL original content — regardless of ``skip_tokens`` or ``head_tokens`` values.
6. **Encoding consistency**: Uses the same ``ENCODING`` singleton as
   ``progressive_markdown.list_navigator`` — token math is deterministic and verifiable.

See architect spec §4.5 (extract signature + semantics) and ADR-5 (skip_tokens
continuation).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from progressive_markdown.list_navigator import ENCODING

# Intentionally fails at collection until T18 creates this module.
from backlog_core.disclosure_handler import BacklogViewDisclosureHandler, TokenBoundedExtractor
from backlog_core.disclosure_types import BoundedContent, BoundedResponse
from backlog_core.tests.conftest import REAL_CL100K_AVAILABLE

# ---------------------------------------------------------------------------
# Module-level mark — skip all tests when real cl100k_base is unavailable
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    not REAL_CL100K_AVAILABLE,
    reason=(
        "token-bounded extraction tests require the real cl100k_base encoding "
        "(offline stub lacks BPE compression and produces incorrect token counts)"
    ),
)

# ---------------------------------------------------------------------------
# Test fixture content
# ---------------------------------------------------------------------------

# English prose — repeated so total token count is ≥ 300 tokens, which enables
# splitting across at least three equal windows in the continuation tests.
_SAMPLE_PARA = (
    "The progressive disclosure contract defines three orthogonal layers for MCP data access. "
    "Layer one (map) provides structure discovery under two thousand tokens for any item size. "
    "Layer two (navigate) resolves a dot-path ordinal to the full content of that section. "
    "Layer three (extract) applies token-bounded pagination using head and skip_tokens parameters. "
    "Each layer is deterministic when using the cl100k_base tiktoken encoding throughout. "
)
_LONG_CONTENT: str = _SAMPLE_PARA * 8
"""Prose content with ≥ 300 cl100k_base tokens, sufficient for windowing tests."""

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _token_count(text: str) -> int:
    """Return the exact cl100k_base token count for ``text``."""
    return len(ENCODING.encode(text))


def _decode_window(text: str, skip: int, head: int) -> str:
    """Decode tokens ``[skip : skip + head]`` from ``text`` using the module ENCODING."""
    tokens = ENCODING.encode(text)
    return ENCODING.decode(tokens[skip : skip + head])


# ---------------------------------------------------------------------------
# TC-B1: Windowing — head_tokens < total_tokens → truncated=True
# ---------------------------------------------------------------------------


class TestWindowingTruncation:
    """extract() truncates when content is larger than the requested window."""

    def test_head_less_than_total_returns_truncated_true(self) -> None:
        """When head_tokens < total_tokens, truncated must be True."""
        total = _token_count(_LONG_CONTENT)
        head = total // 3
        assert head > 0, "Precondition: head must be positive."

        extractor = TokenBoundedExtractor()
        result = extractor.extract(_LONG_CONTENT, head_tokens=head)

        assert isinstance(result, BoundedContent)
        assert result.truncated is True

    def test_returned_tokens_equals_head_when_truncated(self) -> None:
        """returned_tokens == head_tokens when content is larger than the window."""
        total = _token_count(_LONG_CONTENT)
        head = total // 3

        extractor = TokenBoundedExtractor()
        result = extractor.extract(_LONG_CONTENT, head_tokens=head)

        assert result.returned_tokens == head, (
            f"Expected returned_tokens={head}; got {result.returned_tokens}. total_tokens={total}"
        )

    def test_content_decodes_to_first_token_window(self) -> None:
        """content is the decoded first-head-tokens window, not a character slice."""
        total = _token_count(_LONG_CONTENT)
        head = total // 3
        expected_content = _decode_window(_LONG_CONTENT, skip=0, head=head)

        extractor = TokenBoundedExtractor()
        result = extractor.extract(_LONG_CONTENT, head_tokens=head)

        assert result.content == expected_content, (
            "content must be the decoded token window [0:head_tokens], not a character slice."
        )

    def test_total_tokens_reflects_full_content_pre_truncation(self) -> None:
        """total_tokens is the full content count even when head_tokens truncates output."""
        total = _token_count(_LONG_CONTENT)
        head = total // 3

        extractor = TokenBoundedExtractor()
        result = extractor.extract(_LONG_CONTENT, head_tokens=head)

        assert result.total_tokens == total, (
            f"total_tokens must equal full content token count ({total}); got {result.total_tokens}."
        )

    def test_explicit_skip_tokens_zero_is_same_as_default(self) -> None:
        """Passing skip_tokens=0 explicitly must produce identical results to the default."""
        total = _token_count(_LONG_CONTENT)
        head = total // 3
        extractor = TokenBoundedExtractor()

        default = extractor.extract(_LONG_CONTENT, head_tokens=head)
        explicit = extractor.extract(_LONG_CONTENT, head_tokens=head, skip_tokens=0)

        assert explicit.content == default.content
        assert explicit.total_tokens == default.total_tokens
        assert explicit.returned_tokens == default.returned_tokens
        assert explicit.truncated == default.truncated


# ---------------------------------------------------------------------------
# TC-B2: No truncation — head_tokens >= total_tokens → truncated=False
# ---------------------------------------------------------------------------


class TestNoTruncation:
    """extract() returns all content without truncation when head_tokens ≥ total_tokens."""

    def test_head_equals_total_returns_truncated_false(self) -> None:
        """When head_tokens == total_tokens exactly, truncated must be False."""
        total = _token_count(_LONG_CONTENT)

        extractor = TokenBoundedExtractor()
        result = extractor.extract(_LONG_CONTENT, head_tokens=total)

        assert result.truncated is False

    def test_head_exceeds_total_returns_truncated_false(self) -> None:
        """When head_tokens > total_tokens, truncated must be False."""
        total = _token_count(_LONG_CONTENT)
        head = total + 500  # well above total

        extractor = TokenBoundedExtractor()
        result = extractor.extract(_LONG_CONTENT, head_tokens=head)

        assert result.truncated is False

    def test_returned_tokens_equals_actual_count_not_head(self) -> None:
        """When head_tokens ≥ total_tokens, returned_tokens == total_tokens (not head_tokens)."""
        total = _token_count(_LONG_CONTENT)
        head = total + 100

        extractor = TokenBoundedExtractor()
        result = extractor.extract(_LONG_CONTENT, head_tokens=head)

        assert result.returned_tokens == total, (
            f"returned_tokens must equal actual returned count ({total}), "
            f"not head_tokens ({head}); got {result.returned_tokens}."
        )

    def test_content_is_token_roundtrip_of_full_when_not_truncated(self) -> None:
        """When head_tokens >= total, content is encode→decode roundtrip of full text."""
        # encode→decode may differ from raw input for rare control chars; use roundtrip
        # as the canonical expected value so both sides compare the same representation.
        total = _token_count(_LONG_CONTENT)
        canonical = ENCODING.decode(ENCODING.encode(_LONG_CONTENT))

        extractor = TokenBoundedExtractor()
        result = extractor.extract(_LONG_CONTENT, head_tokens=total)

        assert result.content == canonical

    def test_total_tokens_equals_full_count_when_head_not_truncating(self) -> None:
        """total_tokens reflects the full content count even when head_tokens is generous."""
        total = _token_count(_LONG_CONTENT)

        extractor = TokenBoundedExtractor()
        result = extractor.extract(_LONG_CONTENT, head_tokens=total)

        assert result.total_tokens == total


# ---------------------------------------------------------------------------
# TC-B3: Continuation — advancing skip_tokens pages through the full content
# ---------------------------------------------------------------------------


class TestContinuation:
    """Advancing skip_tokens by returned_tokens pages through the full content."""

    def test_second_window_content_differs_from_first(self) -> None:
        """extract() with skip_tokens=returned_tokens returns the NEXT token window."""
        total = _token_count(_LONG_CONTENT)
        head = total // 3

        extractor = TokenBoundedExtractor()
        result1 = extractor.extract(_LONG_CONTENT, head_tokens=head, skip_tokens=0)
        result2 = extractor.extract(_LONG_CONTENT, head_tokens=head, skip_tokens=result1.returned_tokens)

        assert result1.content != result2.content, "Second window must differ from first window."

    def test_second_window_decodes_to_expected_token_slice(self) -> None:
        """Second window content == decode(tokens[head_tokens : 2 * head_tokens])."""
        total = _token_count(_LONG_CONTENT)
        head = total // 3
        expected = _decode_window(_LONG_CONTENT, skip=head, head=head)

        extractor = TokenBoundedExtractor()
        result1 = extractor.extract(_LONG_CONTENT, head_tokens=head, skip_tokens=0)
        result2 = extractor.extract(_LONG_CONTENT, head_tokens=head, skip_tokens=result1.returned_tokens)

        assert result2.content == expected, "Second window must equal decode(tokens[head:2*head])."

    def test_continuation_eventually_reaches_truncated_false(self) -> None:
        """Advancing skip_tokens by returned_tokens eventually reaches truncated=False."""
        total = _token_count(_LONG_CONTENT)
        head = total // 3
        extractor = TokenBoundedExtractor()

        skip = 0
        for _round in range(30):  # 30 rounds covers any reasonable split
            result = extractor.extract(_LONG_CONTENT, head_tokens=head, skip_tokens=skip)
            if not result.truncated:
                break
            skip += result.returned_tokens
        else:
            pytest.fail("extract() never reached truncated=False after 30 continuation rounds.")

    def test_windows_reconstruct_full_content(self) -> None:
        """Concatenated window strings must equal the token-roundtrip of full content."""
        total = _token_count(_LONG_CONTENT)
        head = total // 3
        extractor = TokenBoundedExtractor()
        # Use encode→decode as canonical so both sides round-trip identically.
        canonical = ENCODING.decode(ENCODING.encode(_LONG_CONTENT))

        windows: list[str] = []
        skip = 0
        for _round in range(30):
            result = extractor.extract(_LONG_CONTENT, head_tokens=head, skip_tokens=skip)
            windows.append(result.content)
            if not result.truncated:
                break
            skip += result.returned_tokens
        else:
            pytest.fail("Continuation did not terminate within 30 rounds.")

        assert "".join(windows) == canonical, (
            "Concatenated decoded windows must reproduce the full token-roundtrip content."
        )

    def test_total_tokens_constant_across_all_continuation_rounds(self) -> None:
        """total_tokens must equal the full content count in every continuation call."""
        total = _token_count(_LONG_CONTENT)
        head = total // 3
        extractor = TokenBoundedExtractor()

        skip = 0
        for round_num in range(30):
            result = extractor.extract(_LONG_CONTENT, head_tokens=head, skip_tokens=skip)
            assert result.total_tokens == total, (
                f"Round {round_num}: total_tokens must always equal {total}; "
                f"got {result.total_tokens} at skip_tokens={skip}."
            )
            if not result.truncated:
                break
            skip += result.returned_tokens


# ---------------------------------------------------------------------------
# TC-B4: Overshoot skip — skip_tokens >= total_tokens → empty content
# ---------------------------------------------------------------------------


class TestSkipOvershoot:
    """extract() returns empty content when skip_tokens exhausts the content."""

    def test_skip_equals_total_returns_empty_content(self) -> None:
        """When skip_tokens == total_tokens, content must be the empty string."""
        total = _token_count(_LONG_CONTENT)

        extractor = TokenBoundedExtractor()
        result = extractor.extract(_LONG_CONTENT, head_tokens=100, skip_tokens=total)

        assert result.content == "", f"content must be empty when skip_tokens ({total}) == total_tokens ({total})."

    def test_skip_exceeds_total_returns_empty_content(self) -> None:
        """When skip_tokens > total_tokens, content must be the empty string."""
        total = _token_count(_LONG_CONTENT)
        skip = total + 500

        extractor = TokenBoundedExtractor()
        result = extractor.extract(_LONG_CONTENT, head_tokens=100, skip_tokens=skip)

        assert result.content == "", f"content must be empty when skip_tokens ({skip}) > total_tokens ({total})."

    def test_skip_overshoot_truncated_false(self) -> None:
        """When skip_tokens >= total_tokens, truncated must be False."""
        total = _token_count(_LONG_CONTENT)

        extractor = TokenBoundedExtractor()
        result = extractor.extract(_LONG_CONTENT, head_tokens=100, skip_tokens=total)

        assert result.truncated is False

    def test_skip_overshoot_returned_tokens_zero(self) -> None:
        """When skip_tokens >= total_tokens, returned_tokens must be 0."""
        total = _token_count(_LONG_CONTENT)

        extractor = TokenBoundedExtractor()
        result = extractor.extract(_LONG_CONTENT, head_tokens=100, skip_tokens=total)

        assert result.returned_tokens == 0, (
            f"returned_tokens must be 0 when skip_tokens ({total}) exhausts content; got {result.returned_tokens}."
        )

    def test_skip_overshoot_total_tokens_still_reflects_full_content(self) -> None:
        """total_tokens invariant holds even when skip_tokens has overshot the content."""
        total = _token_count(_LONG_CONTENT)
        skip = total + 999

        extractor = TokenBoundedExtractor()
        result = extractor.extract(_LONG_CONTENT, head_tokens=100, skip_tokens=skip)

        assert result.total_tokens == total, (
            f"total_tokens must equal full content count ({total}) even when "
            f"skip_tokens ({skip}) overshots; got {result.total_tokens}."
        )


# ---------------------------------------------------------------------------
# TC-B5: total_tokens invariant — always full content count, always cl100k_base
# ---------------------------------------------------------------------------


class TestTotalTokensInvariant:
    """total_tokens is always the cl100k_base count of the FULL original content."""

    def test_total_tokens_matches_encoding_count_for_single_word(self) -> None:
        """For a single short word, total_tokens == len(ENCODING.encode(word))."""
        content = "hello"
        expected = _token_count(content)

        extractor = TokenBoundedExtractor()
        result = extractor.extract(content, head_tokens=1)

        assert result.total_tokens == expected

    def test_total_tokens_matches_encoding_count_for_long_content(self) -> None:
        """For long prose, total_tokens == len(ENCODING.encode(content))."""
        expected = _token_count(_LONG_CONTENT)

        extractor = TokenBoundedExtractor()
        result = extractor.extract(_LONG_CONTENT, head_tokens=10)

        assert result.total_tokens == expected

    def test_total_tokens_unchanged_by_varying_skip_tokens(self) -> None:
        """total_tokens is the same regardless of skip_tokens value."""
        expected = _token_count(_LONG_CONTENT)
        extractor = TokenBoundedExtractor()

        result_no_skip = extractor.extract(_LONG_CONTENT, head_tokens=50, skip_tokens=0)
        result_with_skip = extractor.extract(_LONG_CONTENT, head_tokens=50, skip_tokens=25)

        assert result_no_skip.total_tokens == expected
        assert result_with_skip.total_tokens == expected

    def test_total_tokens_unchanged_by_varying_head_tokens(self) -> None:
        """total_tokens is the same regardless of head_tokens value."""
        expected = _token_count(_LONG_CONTENT)
        extractor = TokenBoundedExtractor()

        result_small_head = extractor.extract(_LONG_CONTENT, head_tokens=5)
        result_large_head = extractor.extract(_LONG_CONTENT, head_tokens=10_000)

        assert result_small_head.total_tokens == expected
        assert result_large_head.total_tokens == expected


# ---------------------------------------------------------------------------
# TC-B6 fixtures — sub-heading structured content and child-map text
# ---------------------------------------------------------------------------

# Markdown with sub-headings; repeated 3x to ensure >= 100 tokens for splitting.
_SUB_HEADING_CONTENT: str = (
    "## Section Alpha\n\n"
    "The first sub-heading discusses progressive disclosure contract semantics.\n"
    "Each disclosure layer is deterministic with the cl100k_base encoding throughout.\n\n"
    "## Section Beta\n\n"
    "The second sub-heading covers ordinal resolution and navigate-on-leaf semantics.\n"
    "Navigate returns the full content of a section or entry without truncation.\n\n"
    "## Section Gamma\n\n"
    "The third sub-heading explains token-bounded pagination via head and skip parameters.\n"
    "Continuation advances the window by passing returned_tokens as the next skip value.\n\n"
) * 3
"""Sub-heading structured markdown; repeated to ensure > 100 cl100k_base tokens."""

# Realistic child-map text as produced by navigate-on-parent semantics (architect §4.4).
_CHILD_MAP_TEXT: str = (
    "- 4.0.0: Sub-heading Alpha — progressive disclosure contract semantics\n"
    "- 4.0.1: Sub-heading Beta — ordinal resolution and leaf navigate\n"
    "- 4.0.2: Sub-heading Gamma — token-bounded pagination with head+skip\n"
)
"""Child-map text for a 3-child parent node; used in AC#3 extract-on-parent tests."""


# ---------------------------------------------------------------------------
# TC-B6: Sub-heading boundary — EXTRACT with sub-heading leaf content
# AC#1: truncated=True + next_call carries skip_tokens hint
# AC#2: exact boundary (tokens == head) → truncated=False, next_call=None
# Both tests route through _handle_extract() to obtain BoundedResponse.next_call.
# Expected GREEN — leaf EXTRACT already handled by existing handler logic.
# ---------------------------------------------------------------------------


class TestSubHeadingBoundaryExtract:
    """EXTRACT mode correctly bounds sub-heading content and emits next_call hint.

    Routes through ``BacklogViewDisclosureHandler._handle_extract()`` so that
    ``BoundedResponse.next_call`` is accessible for assertion.  The module-level
    ``pytestmark`` skipif already guards both tests against the offline stub.
    """

    def test_sub_heading_content_truncated_yields_next_call_skip_hint(self) -> None:
        """AC#1: EXTRACT on sub-heading leaf with content > head yields truncated=True
        and next_call carrying the skip_tokens=<returned_tokens> continuation value.
        """
        total = _token_count(_SUB_HEADING_CONTENT)
        head = total // 3
        assert head > 0, "Precondition: head must be positive."

        mock_unit = MagicMock()
        mock_unit.title = "Sub-heading Node"
        mock_unit.content = _SUB_HEADING_CONTENT
        # Set explicitly — T10 adds `if unit.has_sub_heading_children:` branch;
        # False here keeps leaf path active so these GREEN tests stay green after T10.
        mock_unit.has_sub_heading_children = False
        mock_unit.is_code_block = False

        mock_mapper = MagicMock()
        mock_mapper.resolve.return_value = mock_unit

        handler = BacklogViewDisclosureHandler()
        result = handler._handle_extract(
            selector="#2529", ordinal="4.0.0", head_tokens=head, skip_tokens=0, mapper=mock_mapper
        )

        assert isinstance(result, BoundedResponse)
        assert result.truncated is True, "Sub-heading content larger than head_tokens must yield truncated=True."
        assert result.next_call is not None, "truncated=True must produce a non-None next_call continuation hint."
        assert f"skip_tokens={head}" in result.next_call, (
            f"next_call must embed skip_tokens={head} (== returned_tokens at first window); got: {result.next_call!r}"
        )

    def test_sub_heading_content_exact_boundary_no_truncation_and_no_next_call(self) -> None:
        """AC#2: EXTRACT on sub-heading leaf with head_tokens == total yields
        truncated=False and next_call=None (no continuation needed).
        """
        total = _token_count(_SUB_HEADING_CONTENT)

        mock_unit = MagicMock()
        mock_unit.title = "Sub-heading Node"
        mock_unit.content = _SUB_HEADING_CONTENT
        mock_unit.has_sub_heading_children = False  # leaf — stays green after T10
        mock_unit.is_code_block = False

        mock_mapper = MagicMock()
        mock_mapper.resolve.return_value = mock_unit

        handler = BacklogViewDisclosureHandler()
        result = handler._handle_extract(
            selector="#2529", ordinal="4.0.0", head_tokens=total, skip_tokens=0, mapper=mock_mapper
        )

        assert isinstance(result, BoundedResponse)
        assert result.truncated is False, "Exact boundary (head_tokens == total_tokens) must yield truncated=False."
        assert result.next_call is None, "truncated=False must produce next_call=None (no continuation needed)."
        assert result.returned_tokens == total, (
            f"returned_tokens must equal total ({total}) at exact boundary; got {result.returned_tokens}."
        )


# ---------------------------------------------------------------------------
# TC-B7: EXTRACT on parent node — child_map bounding (expected RED until T10)
# AC#3: EXTRACT on has_sub_heading_children=True must bound child_map text.
# ---------------------------------------------------------------------------


class TestExtractOnParentNode:
    """EXTRACT mode on a has_sub_heading_children=True node bounds child_map text.

    Authored against architect spec §4.4 (EXTRACT-on-parent bounds child_map).

    **Expected RED until T10** implements EXTRACT-on-parent branching in
    ``BacklogViewDisclosureHandler._handle_extract()``.  At T10, the handler will
    check ``unit.has_sub_heading_children`` and bound ``unit.child_map`` instead of
    ``unit.content``.

    Both tests fail at assertion (not at import or collection) because the mock
    ``has_sub_heading_children=True`` attribute is not yet inspected by the handler.
    The current handler always uses ``unit.content``, which is ``""`` for parents
    (ADR-7), so result.content returns ``""`` and result.truncated is ``False``.
    """

    def test_extract_on_parent_bounds_child_map_text_not_content(self) -> None:
        """AC#3: EXTRACT on has_sub_heading_children=True node returns bounded child_map.

        Expected RED until T10.  Current handler uses unit.content (``""`` for parents
        per ADR-7), so result.content is ``""`` instead of the expected child_map text.
        """
        child_map_tokens = _token_count(_CHILD_MAP_TEXT)
        # head larger than child_map — no truncation on the child_map side
        head = child_map_tokens + 100

        mock_unit = MagicMock()
        mock_unit.title = "Parent Node"
        mock_unit.content = ""  # ADR-7: parent content is empty string when sub-headings exist
        mock_unit.has_sub_heading_children = True
        mock_unit.is_code_block = False
        mock_unit.child_map = _CHILD_MAP_TEXT

        mock_mapper = MagicMock()
        mock_mapper.resolve.return_value = mock_unit

        handler = BacklogViewDisclosureHandler()
        result = handler._handle_extract(
            selector="#2529", ordinal="4.0", head_tokens=head, skip_tokens=0, mapper=mock_mapper
        )

        # T10 contract: content is bounded child_map text (token-roundtrip canonical form)
        expected_content = ENCODING.decode(ENCODING.encode(_CHILD_MAP_TEXT))
        assert result.content == expected_content, (
            "EXTRACT on has_sub_heading_children=True must bound child_map text, "
            "not empty entry prose. Expected RED until T10 implements EXTRACT-on-parent "
            'branching in _handle_extract(). Current: result.content == ""; '
            f"expected: {expected_content!r}"
        )

    def test_extract_on_parent_truncated_reflects_child_map_size(self) -> None:
        """AC#3 variation: long child_map truncated at head yields truncated=True and next_call.

        Expected RED until T10.  Current handler bounds unit.content (``""``, 0 tokens),
        so result.truncated is ``False`` and result.next_call is ``None``.
        """
        long_child_map = "\n".join(f"- 4.0.{i}: Sub-section {i} — token-bounded extraction target" for i in range(40))
        child_map_tokens = _token_count(long_child_map)
        head = child_map_tokens // 2
        assert head > 0, "Precondition: head must be positive."

        mock_unit = MagicMock()
        mock_unit.title = "Large Parent Node"
        mock_unit.content = ""  # ADR-7: parent content is empty string
        mock_unit.has_sub_heading_children = True
        mock_unit.is_code_block = False
        mock_unit.child_map = long_child_map

        mock_mapper = MagicMock()
        mock_mapper.resolve.return_value = mock_unit

        handler = BacklogViewDisclosureHandler()
        result = handler._handle_extract(
            selector="#2529", ordinal="4.0", head_tokens=head, skip_tokens=0, mapper=mock_mapper
        )

        # T10 contract: truncation reflects child_map size, not empty-string content
        assert result.truncated is True, (
            "EXTRACT on parent with large child_map must yield truncated=True. "
            "Expected RED until T10 implements EXTRACT-on-parent branching. "
            'Current: result.truncated is False (handler bounds "" → 0 tokens).'
        )
        assert result.next_call is not None, (
            "truncated=True on parent EXTRACT must produce a next_call continuation hint. Expected RED until T10."
        )
