"""TDD tests for BacklogViewDisclosureHandler.

Phase 3 handler: orchestration, un-gated ``operations.view_item()`` path, and
three-mode dispatch (MAP / NAVIGATE / EXTRACT).

**TDD state**: This module intentionally fails at collection with ``ImportError``
until T20 adds ``BacklogViewDisclosureHandler`` to
``backlog_core/disclosure_handler.py``.  That is the expected red state.

**ty-check compatibility**: The test-file override
``possibly-unresolved-reference = "warn"`` (pyproject.toml §[tool.ty.overrides]
for ``**/test_*.py``) allows ``ty check`` to exit 0 on the
``BacklogViewDisclosureHandler`` import before T20 writes the class.

Architecture reference:
  - Architect spec §4.4 — handler API + ``_handle_*`` methods
  - Architect spec §5.2 — ``total_est_tokens`` level-1 only
  - Architect spec §5.7 — ``next_call`` format
  - ADR-5 — un-gated ``operations.view_item()`` call path

Test strategy:
  TC-H1: MAP ``total_est_tokens`` is LEVEL-1 only (#2495 double-count regression guard).
  TC-H2: NAVIGATE returns ``NavigateResponse`` with full content, ``truncated=False``.
  TC-H3: EXTRACT on RT-ICA (#2515, head=100) → ``truncated=True``, ``skip_tokens=`` hint.
  TC-H4: Un-gated path — spy on ``view_item``; over-budget #2515 yields non-empty map.
  TC-H5: Navigate-miss → ``OrdinalNotFoundError`` surfaced, valid ordinals listed.
  TC-H6: Navigate-on-parent (§4.4) — mocked mapper, TDD RED; child_map / has_children contracts.

Un-gated spy contract (T20 implementation requirement):
  All tests in TC-H4 patch ``backlog_core.operations.view_item`` (module attribute).
  T20 MUST call ``operations.view_item(selector)`` via the module, NOT via a
  direct-import alias (``from backlog_core.operations import view_item``).
  If T20 uses a direct import, it must re-bind the patch target to
  ``backlog_core.disclosure_handler.view_item``.

RT-ICA ordinal derivation:
  The ordinal for RT-ICA in #2515 is ALWAYS derived at runtime via
  ``_find_rt_ica_ordinal()``.  It is NEVER hardcoded in this file.
  Ground truth from T10 phase gate: RT-ICA in regenerated #2515 fixture is
  ~560 tokens (2,422 chars), single entry, below TOKEN_BUDGET=4000.
  The level-2 emission gate (entry_count > 1 OR est_tokens > TOKEN_BUDGET)
  does NOT fire → only a level-1 ordinal is emitted.

Divergence note DN-2:
  Task spec stated EXTRACT with head=4000 and total_tokens>10000 for RT-ICA.
  Actual fixture (T10 phase gate): RT-ICA is ~560 tokens.
  Resolution: head=100 (triggers truncation on 560-token content) and
  total_tokens>400 (confirms meaningful content, not the erroneous >10000).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from backlog_core.content_normalizer import ItemContentNormalizer, NormalizedSection

# T20 creates BacklogViewDisclosureHandler — ImportError at collection until then.
from backlog_core.disclosure_handler import BacklogViewDisclosureHandler, DisclosureRequest, DisclosureRequestParser
from backlog_core.disclosure_types import (
    BoundedContent,
    BoundedResponse,
    DisclosureMode,
    MapResponse,
    NavigateResponse,
    OrdinalNotFoundError,
)
from backlog_core.models import GroomedSectionMetadata, SectionEntryDict, SectionEntryMetadata, ViewItemResult
from backlog_core.ordinal_mapper import OrdinalEntry, OrdinalPathMapper

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Availability guards
# ---------------------------------------------------------------------------

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
_FIXTURE_2515_EXISTS = (_FIXTURES_DIR / "issue-2515-full.json").exists()

try:
    from progressive_markdown.list_navigator import ENCODING as _ENCODING

    _ENCODING_AVAILABLE: bool = _ENCODING is not None
except (ImportError, OSError):
    _ENCODING_AVAILABLE = False

_skip_without_2515 = pytest.mark.skipif(
    not _FIXTURE_2515_EXISTS, reason="issue-2515-full.json not yet regenerated (T01 prerequisite)."
)
_skip_without_real_enc = pytest.mark.skipif(
    not _ENCODING_AVAILABLE, reason="cl100k_base encoding unavailable (offline environment)."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_fixture(name: str) -> dict[str, object]:
    """Load a JSON fixture file from the fixtures directory."""
    path = _FIXTURES_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[return-value]


def _entry_dict(content: str, entry_id: str = "test-id") -> SectionEntryDict:
    """Minimal SectionEntryDict for test fixtures."""
    return SectionEntryDict(id=entry_id, struck=False, content=content)


def _section(contents: list[str]) -> SectionEntryMetadata:
    """SectionEntryMetadata from a list of entry content strings."""
    entries = [_entry_dict(c, f"e{i}") for i, c in enumerate(contents)]
    return SectionEntryMetadata(num_entries=len(entries), num_struck=0, entries=entries)


def _body_sections_block(order: list[tuple[str, int]]) -> str:
    """Build the ``## Sections`` index block that ``view_item()`` prepends to body."""
    lines = ["## Sections"]
    for idx, (title, count) in enumerate(order):
        lines.append(f"[{idx}] {title} ({count} entries)")
    return "\n".join(lines) + "\n"


def _find_rt_ica_ordinal(normalized: list[NormalizedSection]) -> str:
    """Derive the RT-ICA ordinal from the normalised sections at runtime.

    Builds the ordinal map via ``OrdinalPathMapper`` and returns the ordinal of
    the first ``OrdinalEntry`` with ``'RT-ICA'`` in its title.

    Ground truth (T10 phase gate): RT-ICA in the regenerated #2515 fixture is
    ~560 tokens, single entry, below TOKEN_BUDGET=4000.  The level-2 emission
    gate does NOT fire → only a level-1 ordinal is emitted.

    Requires cl100k_base encoding (``_skip_without_real_enc`` guards call sites).

    Args:
        normalized: Ordered ``NormalizedSection`` list from ``ItemContentNormalizer``.

    Returns:
        The ordinal string (level-1 integer, e.g. ``"4"``) for the RT-ICA section.

    Raises:
        ValueError: When no entry with ``'RT-ICA'`` in title is found — indicates
            a fixture mismatch requiring investigation.
    """
    mapper = OrdinalPathMapper(normalized)
    entries = mapper.build_map()
    rt_ica_entries = [e for e in entries if "RT-ICA" in e.title]
    if not rt_ica_entries:
        all_titles = [(e.ordinal, e.title) for e in entries]
        raise ValueError(
            f"No OrdinalEntry with 'RT-ICA' in title found in map. All (ordinal, title) pairs: {all_titles}"
        )
    return rt_ica_entries[0].ordinal


# ---------------------------------------------------------------------------
# Module-level fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def normalized_2515() -> list[NormalizedSection]:
    """Fully normalised #2515 fixture (large item with RT-ICA section).

    Loads the regenerated fixture from T01 and normalises via
    ``ItemContentNormalizer``.  Required by TC-H3 (EXTRACT) and TC-H4 (spy).
    """
    data = _load_fixture("issue-2515-full.json")
    return ItemContentNormalizer().normalize(ViewItemResult.model_validate(data))


@pytest.fixture(scope="module")
def view_result_2515() -> ViewItemResult:
    """``ViewItemResult`` for #2515, used as ``operations.view_item`` mock return value.

    Constructed via ``ViewItemResult.model_validate(data)`` from the full fixture
    JSON — same construction as the existing ``normalized_2515`` fixture in
    ``test_ordinal_mapper.py``.
    """
    data = _load_fixture("issue-2515-full.json")
    return ViewItemResult.model_validate(data)


@pytest.fixture
def multi_entry_view_result() -> ViewItemResult:
    """Two-section ``ViewItemResult`` where section 0 has 2 entries.

    Designed for level-1-only ``total_est_tokens`` test (TC-H1) and NAVIGATE
    tests (TC-H2) and navigate-miss tests (TC-H5).

    Structure:
      [0] AlphaSection (2 entries) — level-2 emission gate fires (entry_count > 1).
      [1] BetaSection  (1 entry)   — level-2 gate does NOT fire.

    The double-count regression guard (TC-H1) relies on AlphaSection emitting
    level-2 lines so the buggy all-entries sum diverges from the correct
    level-1-only sum.
    """
    sections: dict[str, SectionEntryMetadata | GroomedSectionMetadata] = {
        "AlphaSection": _section([
            "First entry for alpha. This sentence provides a meaningful token count.",
            "Second entry for alpha. Another distinct sentence with its own tokens.",
        ]),
        "BetaSection": _section(["Short beta entry."]),
    }
    body = _body_sections_block([("AlphaSection", 2), ("BetaSection", 1)])
    return ViewItemResult(sections=sections, body=body, sections_index="")


# ---------------------------------------------------------------------------
# TC-H1: MAP mode — total_est_tokens is level-1-only (no double-count, #2495 guard)
# ---------------------------------------------------------------------------


class TestMapTotalEstTokensLevelOneOnly:
    """MAP ``total_est_tokens`` sums LEVEL-1 section estimates only.

    Regression guard for #2495: if the handler incorrectly sums ALL
    ``OrdinalEntry.est_tokens`` (including level-2 children), it would
    double-count sections with multiple entries.

    AlphaSection has 2 entries → level-2 ordinals ``"0.0"`` and ``"0.1"`` are
    emitted with their own ``est_tokens``.  The handler must sum ONLY ``"0"``
    and ``"1"`` (level-1 entries), not ``"0"`` + ``"0.0"`` + ``"0.1"`` + ``"1"``.
    """

    @_skip_without_real_enc
    def test_total_est_tokens_equals_level1_sum_only(
        self, multi_entry_view_result: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """MAP ``total_est_tokens`` equals level-1 sum only; level-2 excluded.

        Strategy: compute the expected value from the same normalizer + mapper
        pipeline that the handler uses, but select only level-1 entries.
        A buggy handler summing all entries would return a higher value.
        """
        mocker.patch("backlog_core.operations.view_item", return_value=multi_entry_view_result)

        handler = BacklogViewDisclosureHandler()
        parser = DisclosureRequestParser()
        request = parser.parse(map=True)
        result = handler.handle("synthetic-selector", request)

        assert isinstance(result, MapResponse), f"Expected MapResponse; got {type(result).__name__}."

        # Compute expected level-1-only total independently.
        normalized = ItemContentNormalizer().normalize(multi_entry_view_result)
        mapper = OrdinalPathMapper(normalized)
        map_entries = mapper.build_map()
        expected_level1_total = sum(e.est_tokens for e in map_entries if "." not in e.ordinal)

        assert result.total_est_tokens == expected_level1_total, (
            f"total_est_tokens must equal the sum of level-1 est_tokens only.\n"
            f"Expected (level-1 only): {expected_level1_total}\n"
            f"Got: {result.total_est_tokens}\n"
            f"If Got > Expected, the handler is double-counting level-2 entries (#2495).\n"
            f"All (ordinal, est_tokens): {[(e.ordinal, e.est_tokens) for e in map_entries]}"
        )

    @_skip_without_real_enc
    def test_total_est_tokens_strictly_less_than_all_entry_sum(
        self, multi_entry_view_result: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """``total_est_tokens`` < sum-of-all-entries when level-2 entries exist.

        AlphaSection emits level-2 entries.  A buggy handler summing all entries
        would produce a value larger than the correct level-1-only sum.
        """
        mocker.patch("backlog_core.operations.view_item", return_value=multi_entry_view_result)

        handler = BacklogViewDisclosureHandler()
        parser = DisclosureRequestParser()
        request = parser.parse(map=True)
        result = handler.handle("synthetic-selector", request)

        assert isinstance(result, MapResponse)

        normalized = ItemContentNormalizer().normalize(multi_entry_view_result)
        mapper = OrdinalPathMapper(normalized)
        map_entries = mapper.build_map()

        level2_entries = [e for e in map_entries if "." in e.ordinal]
        assert level2_entries, (
            "AlphaSection (2 entries) must emit level-2 OrdinalEntries for this test "
            "to be discriminating — check multi_entry_view_result fixture."
        )
        all_entries_sum = sum(e.est_tokens for e in map_entries)

        assert result.total_est_tokens < all_entries_sum, (
            f"total_est_tokens ({result.total_est_tokens}) must be < all-entry sum "
            f"({all_entries_sum}) confirming level-2 entries are excluded.\n"
            f"All (ordinal, est_tokens): {[(e.ordinal, e.est_tokens) for e in map_entries]}"
        )

    @_skip_without_real_enc
    def test_map_returns_map_response_type(
        self, multi_entry_view_result: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """handle() with MAP request returns ``MapResponse``."""
        mocker.patch("backlog_core.operations.view_item", return_value=multi_entry_view_result)

        handler = BacklogViewDisclosureHandler()
        request = DisclosureRequestParser().parse(map=True)
        result = handler.handle("synthetic-selector", request)

        assert isinstance(result, MapResponse), f"Expected MapResponse; got {type(result).__name__}."

    @_skip_without_real_enc
    def test_map_response_has_non_empty_map_text(
        self, multi_entry_view_result: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """MAP ``map_text`` is non-empty for any document with at least one section."""
        mocker.patch("backlog_core.operations.view_item", return_value=multi_entry_view_result)

        handler = BacklogViewDisclosureHandler()
        request = DisclosureRequestParser().parse(map=True)
        result = handler.handle("synthetic-selector", request)

        assert isinstance(result, MapResponse)
        assert result.map_text, "map_text must not be empty for a document with sections."


# ---------------------------------------------------------------------------
# TC-H2: NAVIGATE mode — full content, truncated=False
# ---------------------------------------------------------------------------


class TestNavigateMode:
    """NAVIGATE returns ``NavigateResponse`` with full content, ``truncated=False``.

    Uses ordinal ``"0"`` (level-1, always valid for a non-empty document) to
    avoid running ``OrdinalPathMapper.build_map()`` in test setup.  The handler
    still runs ``build_map()`` internally (to populate its resolution map),
    which is why ``_skip_without_real_enc`` is required.
    """

    @_skip_without_real_enc
    def test_navigate_returns_navigate_response(
        self, multi_entry_view_result: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """handle() with NAVIGATE request returns ``NavigateResponse``."""
        mocker.patch("backlog_core.operations.view_item", return_value=multi_entry_view_result)

        handler = BacklogViewDisclosureHandler()
        request = DisclosureRequestParser().parse(navigate="0")
        result = handler.handle("synthetic-selector", request)

        assert isinstance(result, NavigateResponse), f"Expected NavigateResponse; got {type(result).__name__}."

    @_skip_without_real_enc
    def test_navigate_truncated_is_always_false(
        self, multi_entry_view_result: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """``NavigateResponse.truncated`` is always ``False`` — no ``head`` was supplied."""
        mocker.patch("backlog_core.operations.view_item", return_value=multi_entry_view_result)

        handler = BacklogViewDisclosureHandler()
        request = DisclosureRequestParser().parse(navigate="0")
        result = handler.handle("synthetic-selector", request)

        assert isinstance(result, NavigateResponse)
        assert result.truncated is False, (
            "NavigateResponse.truncated must be False — navigate without head "
            "returns full section content with no token window applied."
        )

    @_skip_without_real_enc
    def test_navigate_content_is_non_empty(
        self, multi_entry_view_result: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """``NavigateResponse.content`` is non-empty for a valid ordinal."""
        mocker.patch("backlog_core.operations.view_item", return_value=multi_entry_view_result)

        handler = BacklogViewDisclosureHandler()
        request = DisclosureRequestParser().parse(navigate="0")
        result = handler.handle("synthetic-selector", request)

        assert isinstance(result, NavigateResponse)
        assert result.content, "NavigateResponse.content must not be empty for ordinal '0'."

    @_skip_without_real_enc
    def test_navigate_total_tokens_is_positive(
        self, multi_entry_view_result: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """``NavigateResponse.total_tokens`` is the full ``cl100k_base`` count (> 0)."""
        mocker.patch("backlog_core.operations.view_item", return_value=multi_entry_view_result)

        handler = BacklogViewDisclosureHandler()
        request = DisclosureRequestParser().parse(navigate="0")
        result = handler.handle("synthetic-selector", request)

        assert isinstance(result, NavigateResponse)
        assert result.total_tokens > 0, "NavigateResponse.total_tokens must be positive for non-empty content."


# ---------------------------------------------------------------------------
# TC-H3: EXTRACT mode — RT-ICA entry (#2515), head=100, truncated + next_call
# ---------------------------------------------------------------------------


class TestExtractModeRTICA:
    """EXTRACT on RT-ICA (#2515) with head=100 produces ``BoundedResponse``.

    Ground truth from T10 phase gate:
    - RT-ICA entry in #2515 is ~560 tokens (2,422 chars), single entry.
    - ``head=100 < 560`` → ``truncated=True``, ``returned_tokens ≤ 100``.
    - ``next_call`` uses ``skip_tokens=``, NOT ``offset=`` (AC-5).
    - ``next_call`` is on ``BoundedResponse``, NOT on ``BoundedContent`` (ADR-5).
    - ``total_tokens > 400`` confirms full pre-truncation content (~560 tokens).

    The RT-ICA ordinal is derived at runtime via ``_find_rt_ica_ordinal()``.
    It is never hardcoded in this file.

    Divergence note DN-2: task spec stated head=4000 / total_tokens>10000.
    Actual fixture data (~560 tokens) requires head=100 / total_tokens>400.
    """

    @_skip_without_2515
    @_skip_without_real_enc
    def test_extract_returns_bounded_response(
        self, normalized_2515: list[NormalizedSection], view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """handle() with EXTRACT request returns ``BoundedResponse``."""
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        rt_ica_ordinal = _find_rt_ica_ordinal(normalized_2515)
        result = BacklogViewDisclosureHandler().handle(
            "#2515", DisclosureRequestParser().parse(navigate=rt_ica_ordinal, head=100)
        )

        assert isinstance(result, BoundedResponse), f"Expected BoundedResponse; got {type(result).__name__}."

    @_skip_without_2515
    @_skip_without_real_enc
    def test_extract_truncated_true(
        self, normalized_2515: list[NormalizedSection], view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """``BoundedResponse.truncated`` is ``True`` when head=100 < RT-ICA total (~560t)."""
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        rt_ica_ordinal = _find_rt_ica_ordinal(normalized_2515)
        result = BacklogViewDisclosureHandler().handle(
            "#2515", DisclosureRequestParser().parse(navigate=rt_ica_ordinal, head=100)
        )

        assert isinstance(result, BoundedResponse)
        assert result.truncated is True, (
            f"truncated must be True when head=100 < RT-ICA total_tokens (~560). "
            f"Got truncated={result.truncated}, total_tokens={result.total_tokens}."
        )

    @_skip_without_2515
    @_skip_without_real_enc
    def test_extract_returned_tokens_within_head_bound(
        self, normalized_2515: list[NormalizedSection], view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """``returned_tokens ≤ head`` (100) — window does not exceed requested bound."""
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        rt_ica_ordinal = _find_rt_ica_ordinal(normalized_2515)
        result = BacklogViewDisclosureHandler().handle(
            "#2515", DisclosureRequestParser().parse(navigate=rt_ica_ordinal, head=100)
        )

        assert isinstance(result, BoundedResponse)
        assert result.returned_tokens <= 100, f"returned_tokens must be ≤ head=100; got {result.returned_tokens}."

    @_skip_without_2515
    @_skip_without_real_enc
    def test_extract_total_tokens_reflects_full_rt_ica_content(
        self, normalized_2515: list[NormalizedSection], view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """``total_tokens > 400`` — full RT-ICA content pre-truncation (~560 tokens).

        This asserts that ``total_tokens`` reflects the COMPLETE content before the
        head window was applied (not the window size), and that RT-ICA has meaningful
        content.  Ground truth from T10: ~560 tokens.
        """
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        rt_ica_ordinal = _find_rt_ica_ordinal(normalized_2515)
        result = BacklogViewDisclosureHandler().handle(
            "#2515", DisclosureRequestParser().parse(navigate=rt_ica_ordinal, head=100)
        )

        assert isinstance(result, BoundedResponse)
        assert result.total_tokens > 400, (
            f"total_tokens must be > 400 (ground truth: RT-ICA is ~560 tokens). "
            f"Got {result.total_tokens}. "
            f"total_tokens is the FULL pre-truncation count, not the window size."
        )

    @_skip_without_2515
    @_skip_without_real_enc
    def test_extract_next_call_uses_skip_tokens_not_offset(
        self, normalized_2515: list[NormalizedSection], view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """``next_call`` continuation hint uses ``skip_tokens=``, NOT ``offset=`` (AC-5)."""
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        rt_ica_ordinal = _find_rt_ica_ordinal(normalized_2515)
        result = BacklogViewDisclosureHandler().handle(
            "#2515", DisclosureRequestParser().parse(navigate=rt_ica_ordinal, head=100)
        )

        assert isinstance(result, BoundedResponse)
        assert result.next_call is not None, "next_call must not be None when truncated=True."

        # Use result.returned_tokens for the expected skip value (per extractor doc:
        # "pass returned_tokens as skip_tokens for the next window").
        expected_skip = str(result.returned_tokens)
        assert f"skip_tokens={expected_skip}" in result.next_call, (
            f"next_call must contain 'skip_tokens={expected_skip}' "
            f"(= returned_tokens={result.returned_tokens}); "
            f"got: {result.next_call!r}.\n"
            "AC-5: continuation parameter is 'skip_tokens', not 'offset'."
        )
        assert "offset=" not in result.next_call, (
            f"next_call must NOT contain 'offset='; got: {result.next_call!r}.\n"
            "AC-5: the continuation parameter is 'skip_tokens', never 'offset'."
        )

    @_skip_without_2515
    @_skip_without_real_enc
    def test_extract_next_call_is_on_bounded_response_not_bounded_content(
        self, normalized_2515: list[NormalizedSection], view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """``next_call`` is a field of ``BoundedResponse``, NOT ``BoundedContent``.

        ``BoundedContent`` is the internal intermediate produced by
        ``TokenBoundedExtractor`` — it carries no ``next_call`` field and no
        ``selector`` (ADR-5).  The handler assembles ``next_call`` on
        ``BoundedResponse`` where the selector is in scope.
        """
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        rt_ica_ordinal = _find_rt_ica_ordinal(normalized_2515)
        result = BacklogViewDisclosureHandler().handle(
            "#2515", DisclosureRequestParser().parse(navigate=rt_ica_ordinal, head=100)
        )

        # BoundedContent has NO next_call field.  BoundedResponse DOES.
        # isinstance check confirms the handler returns the outer value object.
        assert isinstance(result, BoundedResponse), (
            "EXTRACT must return BoundedResponse (has next_call). "
            "Returning BoundedContent (no next_call) is a contract violation."
        )
        assert hasattr(result, "next_call"), "BoundedResponse.next_call field must exist on the returned object."

    @_skip_without_2515
    @_skip_without_real_enc
    def test_extract_next_call_contains_selector(
        self, normalized_2515: list[NormalizedSection], view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """``next_call`` hint includes selector ``'#2515'`` (assembled at handler scope).

        The handler assembles ``next_call`` where ``selector`` is in scope;
        ``BoundedContent`` (from ``TokenBoundedExtractor``) carries no selector.
        """
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        rt_ica_ordinal = _find_rt_ica_ordinal(normalized_2515)
        result = BacklogViewDisclosureHandler().handle(
            "#2515", DisclosureRequestParser().parse(navigate=rt_ica_ordinal, head=100)
        )

        assert isinstance(result, BoundedResponse)
        assert result.next_call is not None
        assert "#2515" in result.next_call, (
            f"next_call must reference the selector '#2515'; got: {result.next_call!r}.\n"
            "The selector is only in scope at handler level — not in BoundedContent."
        )


# ---------------------------------------------------------------------------
# TC-H4: Un-gated path — handler calls operations.view_item() directly
# ---------------------------------------------------------------------------


class TestUngatedViewItemPath:
    """handle() sources content via ``operations.view_item()`` (un-gated path).

    Why un-gated is critical: the gated ``backlog_view`` tool path returns
    ``body=""`` for over-budget items (like #2515).  The handler MUST call
    ``operations.view_item(selector)`` directly to obtain the full body.

    Spy contract: tests patch ``backlog_core.operations.view_item`` (module
    attribute).  T20 must call it as ``operations.view_item(selector)`` via the
    module, or declare the patch target in its handoff.
    """

    @_skip_without_2515
    @_skip_without_real_enc
    def test_handle_calls_view_item_exactly_once(self, view_result_2515: ViewItemResult, mocker: MockerFixture) -> None:
        """handle() calls ``operations.view_item()`` exactly once (un-gated path)."""
        view_item_spy = mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        BacklogViewDisclosureHandler().handle("#2515", DisclosureRequestParser().parse(map=True))

        view_item_spy.assert_called_once()

    @_skip_without_2515
    @_skip_without_real_enc
    def test_handle_passes_selector_to_view_item(self, view_result_2515: ViewItemResult, mocker: MockerFixture) -> None:
        """handle() passes the selector ``'#2515'`` unchanged to ``view_item()``."""
        view_item_spy = mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        BacklogViewDisclosureHandler().handle("#2515", DisclosureRequestParser().parse(map=True))

        call_args = view_item_spy.call_args
        assert call_args is not None, "view_item() must have been called."
        pos_args = list(call_args.args) if call_args.args else []
        kw_args = call_args.kwargs or {}
        pos_selector = pos_args[0] if pos_args else None
        kw_selector = kw_args.get("selector")
        assert pos_selector == "#2515" or kw_selector == "#2515", (
            f"view_item() must receive selector='#2515' as positional or keyword arg.\n"
            f"Got positional[0]={pos_selector!r}, keyword selector={kw_selector!r}."
        )

    @_skip_without_2515
    @_skip_without_real_enc
    def test_overbudget_item_produces_non_empty_map_text(
        self, view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """Over-budget #2515 produces non-empty ``map_text`` via the un-gated path.

        This proves the handler obtains the full body (not the empty gated response)
        and produces a navigable map.  Non-empty ``map_text`` + non-zero
        ``total_sections`` together confirm that the over-budget item is fully
        accessible via the un-gated path.
        """
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        result = BacklogViewDisclosureHandler().handle("#2515", DisclosureRequestParser().parse(map=True))

        assert isinstance(result, MapResponse), f"Expected MapResponse; got {type(result).__name__}."
        assert result.map_text, (
            "map_text must be non-empty for #2515 via the un-gated path. "
            "An empty gated response body would produce no map lines."
        )
        assert result.total_sections > 0, f"total_sections must be > 0 for #2515; got {result.total_sections}."


# ---------------------------------------------------------------------------
# TC-H5: Navigate-miss — OrdinalNotFoundError surfaced, no full-content fallback
# ---------------------------------------------------------------------------


class TestNavigateMiss:
    """Handler surfaces ``OrdinalNotFoundError`` for unknown ordinals.

    Regression guard for the silent-fallback bug (ADR-3): old code fell back to
    full content when a section name was not found.  The handler MUST NOT return
    a ``NavigateResponse`` with full content for an unknown ordinal.

    The error must include the valid ordinals list so agents can recover in a
    single round-trip (architect spec §4.5 error contract).
    """

    @_skip_without_real_enc
    def test_navigate_miss_does_not_return_navigate_response(
        self, multi_entry_view_result: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """handle() with unknown ordinal does NOT return a ``NavigateResponse``.

        Silent full-content fallback is prohibited (ADR-3).  The result must be
        either a raised ``OrdinalNotFoundError`` or a non-``NavigateResponse`` value.
        """
        mocker.patch("backlog_core.operations.view_item", return_value=multi_entry_view_result)

        handler = BacklogViewDisclosureHandler()
        request = DisclosureRequestParser().parse(navigate="99.99")

        try:
            result = handler.handle("synthetic-selector", request)
            assert not isinstance(result, NavigateResponse), (
                "handle() must NOT return NavigateResponse for unknown ordinal '99.99'. "
                "Returning full content as a silent fallback violates ADR-3."
            )
        except OrdinalNotFoundError:
            # Raising OrdinalNotFoundError is the preferred behaviour.
            pass

    @_skip_without_real_enc
    def test_navigate_miss_raises_ordinal_not_found_error(
        self, multi_entry_view_result: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """handle() raises ``OrdinalNotFoundError`` for unknown ordinal ``'99.99'``.

        ``OrdinalNotFoundError.requested`` must equal the ordinal that was passed.
        """
        mocker.patch("backlog_core.operations.view_item", return_value=multi_entry_view_result)

        handler = BacklogViewDisclosureHandler()
        request = DisclosureRequestParser().parse(navigate="99.99")

        with pytest.raises(OrdinalNotFoundError) as exc_info:
            handler.handle("synthetic-selector", request)

        assert exc_info.value.requested == "99.99", (
            f"OrdinalNotFoundError.requested must be '99.99'; got {exc_info.value.requested!r}."
        )

    @_skip_without_real_enc
    def test_navigate_miss_error_includes_valid_ordinals(
        self, multi_entry_view_result: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """``OrdinalNotFoundError.valid_ordinals`` lists all ordinals in the document.

        Agents need valid ordinals to recover without a second round-trip
        (architect spec §4.5 error contract).
        """
        mocker.patch("backlog_core.operations.view_item", return_value=multi_entry_view_result)

        # Compute expected valid ordinals from the same pipeline the handler will use.
        normalized = ItemContentNormalizer().normalize(multi_entry_view_result)
        mapper = OrdinalPathMapper(normalized)
        expected_valid = set(mapper.valid_ordinals())
        assert expected_valid, "Expected valid ordinals must be non-empty for this test."

        handler = BacklogViewDisclosureHandler()
        request = DisclosureRequestParser().parse(navigate="99.99")

        with pytest.raises(OrdinalNotFoundError) as exc_info:
            handler.handle("synthetic-selector", request)

        actual_valid = set(exc_info.value.valid_ordinals)
        assert expected_valid.issubset(actual_valid), (
            f"OrdinalNotFoundError.valid_ordinals must include all expected ordinals.\n"
            f"Expected (from pipeline): {sorted(expected_valid)}\n"
            f"Got: {sorted(actual_valid)}"
        )


# ---------------------------------------------------------------------------
# TC-H6: Navigate-on-parent semantics (§4.4) — TDD RED
# ---------------------------------------------------------------------------


class TestNavigateOnParentResponse:
    """Navigate-on-parent response contracts (architect spec §4.4) — TDD RED.

    Tests pin the three node-type response branches added by T10:
    - Sub-heading parent → ``child_map`` non-None, ``has_children=True``, ``content=""``
    - Leaf sub-heading → content carries prose-with-tokens, ``child_map=None``
    - Code block → content is raw fence body (no inline tokens), ``child_map=None``

    Strategy (§7.3 — integration-level with mocked mapper):
    ``OrdinalPathMapper`` is mocked for all four tests so that the cl100k_base
    token-counting encoder is not a prerequisite.  Each mock's ``resolve()``
    side-effect returns a ``MagicMock`` shaped like ``SubtreeNode`` (§6.1),
    driving the handler branching logic under test.

    CoVe assertions (§7.3 revision rule — aligned to §4.4 and ADR-4 / ADR-7):
    - Code-block content must NOT contain ``[code:...]`` tokens (raw fence body).
    - Leaf content DOES contain ``[code:...]`` tokens (mapper replaced fence inline).
    - ``content=""`` (not ``None``) when ``has_children=True`` (ADR-7).

    TDD state: tests 1 and 4 are unconditionally RED until T10 implements the
    navigate-on-parent branch; tests 2 and 3 verify the leaf/code paths remain
    correct after T10 introduces branching.
    """

    def test_navigate_to_sub_heading_parent_returns_child_map(
        self, multi_entry_view_result: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """Navigate to a sub-heading parent: child_map non-None, has_children=True, content==''.

        §4.4 contract when ``SubtreeNode.has_sub_heading_children=True``:
        - ``NavigateResponse.has_children`` must be ``True``
        - ``NavigateResponse.child_map`` must not be ``None``
        - ``NavigateResponse.content`` must be ``""`` (ADR-7)

        TDD RED: ``_handle_navigate`` currently returns ``has_children=False``
        (dataclass default) for every node type — navigate-on-parent branch absent.
        """
        mocker.patch("backlog_core.operations.view_item", return_value=multi_entry_view_result)

        # Arrange — sub-heading parent SubtreeNode mock (§6.1 shape)
        parent_node = mocker.MagicMock()
        parent_node.has_sub_heading_children = True
        parent_node.is_code_block = False
        parent_node.content = ""
        parent_node.total_tokens = 0
        parent_node.title = "Planning Entry"
        parent_node.ordinal = "0.0"
        parent_node.child_ordinals = ["0.0.0", "0.0.1"]
        parent_node.code_block_ordinals = []

        child_a = mocker.MagicMock()
        child_a.title = "SubHeadingA"
        child_a.total_tokens = 10
        child_a.has_sub_heading_children = False
        child_a.is_code_block = False
        child_a.ordinal = "0.0.0"
        child_a.child_ordinals = []
        child_a.code_block_ordinals = []

        child_b = mocker.MagicMock()
        child_b.title = "SubHeadingB"
        child_b.total_tokens = 12
        child_b.has_sub_heading_children = False
        child_b.is_code_block = False
        child_b.ordinal = "0.0.1"
        child_b.child_ordinals = []
        child_b.code_block_ordinals = []

        nodes: dict[str, object] = {"0.0": parent_node, "0.0.0": child_a, "0.0.1": child_b}

        def _resolve(ordinal: str) -> object:
            if ordinal in nodes:
                return nodes[ordinal]
            raise OrdinalNotFoundError(ordinal, list(nodes))

        mock_mapper = mocker.MagicMock()
        mock_mapper.build_map.return_value = [
            OrdinalEntry(ordinal="0.0", title="Planning Entry", est_tokens=22, first_line_preview="...")
        ]
        mock_mapper.resolve.side_effect = _resolve
        mock_mapper.valid_ordinals.return_value = list(nodes)
        mocker.patch("backlog_core.disclosure_handler.OrdinalPathMapper", return_value=mock_mapper)

        # Act
        result = BacklogViewDisclosureHandler().handle(
            "synthetic-selector", DisclosureRequestParser().parse(navigate="0.0")
        )

        # Assert
        assert isinstance(result, NavigateResponse), (
            f"Navigate to sub-heading parent must return NavigateResponse; got {type(result).__name__}."
        )
        assert result.has_children is True, (
            "has_children must be True when SubtreeNode.has_sub_heading_children=True (§4.4). "
            "RED: current handler always returns has_children=False."
        )
        assert result.child_map is not None, "child_map must not be None for a sub-heading parent (§4.4)."
        assert result.content == "", f"content must be '' when has_children=True (ADR-7); got {result.content!r}."

    def test_navigate_to_leaf_returns_prose_with_tokens(
        self, multi_entry_view_result: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """Navigate to a leaf node: content has prose-with-tokens, child_map=None.

        §4.4 contract when ``has_sub_heading_children=False`` and
        ``is_code_block=False`` (flat or leaf sub-heading):
        - ``has_children`` is ``False``
        - ``child_map`` is ``None``
        - ``content`` contains ``[code:...]`` navigation token(s) placed by the mapper

        Verifies the leaf path continues to work after T10 introduces the
        navigate-on-parent branch.  The mapper (mocked here) pre-substitutes
        fences inline before the handler receives the ``SubtreeNode`` (§4.2).
        """
        mocker.patch("backlog_core.operations.view_item", return_value=multi_entry_view_result)

        # Arrange — leaf SubtreeNode with inline fence token (§6.1 + §4.2)
        leaf_node = mocker.MagicMock()
        leaf_node.has_sub_heading_children = False
        leaf_node.is_code_block = False
        leaf_node.content = (
            "Intro prose describing a computation.\n\n[code:0.0.code.0]\n\nTrailing prose after the fence."
        )
        leaf_node.total_tokens = 30
        leaf_node.title = "Leaf SubHeading"
        leaf_node.ordinal = "0.0"
        leaf_node.child_ordinals = []
        leaf_node.code_block_ordinals = ["0.0.code.0"]

        mock_mapper = mocker.MagicMock()
        mock_mapper.build_map.return_value = [
            OrdinalEntry(ordinal="0.0", title="Leaf SubHeading", est_tokens=30, first_line_preview="Intro prose")
        ]
        mock_mapper.resolve.return_value = leaf_node
        mock_mapper.valid_ordinals.return_value = ["0.0"]
        mocker.patch("backlog_core.disclosure_handler.OrdinalPathMapper", return_value=mock_mapper)

        # Act
        result = BacklogViewDisclosureHandler().handle(
            "synthetic-selector", DisclosureRequestParser().parse(navigate="0.0")
        )

        # Assert
        assert isinstance(result, NavigateResponse), (
            f"Navigate to leaf must return NavigateResponse; got {type(result).__name__}."
        )
        assert result.has_children is False, "has_children must be False for a leaf node (ADR-4)."
        assert result.child_map is None, "child_map must be None for a leaf node (§4.4)."
        assert "[code:" in result.content, (
            "content must contain '[code:...]' navigation token(s) — mapper replaces "
            f"fences inline (§4.2). Got content={result.content!r}."
        )

    def test_navigate_to_code_block_returns_fence_body(
        self, multi_entry_view_result: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """Navigate to a code block: content is raw fence body, no tokens, child_map=None.

        §4.4 contract when ``SubtreeNode.is_code_block=True``:
        - ``content`` is the raw fence body (no surrounding backticks)
        - ``content`` does NOT contain ``[code:...]`` navigation tokens
        - ``child_map`` is ``None``
        - ``has_children`` is ``False``

        Uses ``DisclosureRequest`` constructed directly, bypassing the parser,
        because code-fence ordinals like ``"0.0.code.0"`` fail the current
        ``_ORDINAL_PATTERN`` regex until T04 / T08 extend it.

        CoVe check (§7.3): raw fence body must NOT contain navigation tokens —
        the mapper stores the raw code content without token substitution (§4.2).
        """
        mocker.patch("backlog_core.operations.view_item", return_value=multi_entry_view_result)

        raw_fence_body = "x = 42\nprint(x)\n"

        # Arrange — code-block SubtreeNode (§6.1, is_code_block=True)
        code_node = mocker.MagicMock()
        code_node.has_sub_heading_children = False
        code_node.is_code_block = True
        code_node.content = raw_fence_body
        code_node.total_tokens = 5
        code_node.title = "python"
        code_node.ordinal = "0.0.code.0"
        code_node.child_ordinals = []
        code_node.code_block_ordinals = []

        mock_mapper = mocker.MagicMock()
        mock_mapper.build_map.return_value = [
            OrdinalEntry(ordinal="0.0", title="Entry", est_tokens=50, first_line_preview="...")
        ]
        mock_mapper.resolve.return_value = code_node
        mock_mapper.valid_ordinals.return_value = ["0.0", "0.0.code.0"]
        mocker.patch("backlog_core.disclosure_handler.OrdinalPathMapper", return_value=mock_mapper)

        # Bypass parser — "0.0.code.0" fails current _ORDINAL_PATTERN (T04 extends it).
        request = DisclosureRequest(
            mode=DisclosureMode.NAVIGATE, navigate_ordinal="0.0.code.0", head_tokens=None, skip_tokens=0
        )

        # Act
        result = BacklogViewDisclosureHandler().handle("synthetic-selector", request)

        # Assert
        assert isinstance(result, NavigateResponse), (
            f"Navigate to code block must return NavigateResponse; got {type(result).__name__}."
        )
        assert result.has_children is False, "has_children must be False for a code-block node (ADR-4)."
        assert result.child_map is None, "child_map must be None for a code-block node (§4.4)."
        assert "[code:" not in result.content, (
            "Code-block content must NOT contain '[code:...]' tokens — "
            f"raw fence body has no token substitution (§4.2). Got {result.content!r}."
        )
        assert result.content == raw_fence_body, (
            f"content must equal the raw fence body {raw_fence_body!r}; got {result.content!r}."
        )

    def test_extract_on_parent_bounds_child_map(
        self, multi_entry_view_result: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """EXTRACT mode on sub-heading parent: child_map is token-bounded, truncated=True.

        §4.4 EXTRACT contract when ``has_sub_heading_children=True`` and ``head`` set:
        - Returns ``NavigateResponse`` (not ``BoundedResponse``)
        - ``has_children`` is ``True``
        - ``child_map`` is not ``None``
        - ``truncated`` is ``True`` when the child_map text exceeds ``head`` tokens

        Uses mocked ``OrdinalPathMapper`` + mocked ``TokenBoundedExtractor`` so
        the cl100k_base encoder is not required.

        TDD RED: current ``_handle_extract`` unconditionally returns
        ``BoundedResponse`` — the navigate-on-parent EXTRACT branch is absent.
        """
        mocker.patch("backlog_core.operations.view_item", return_value=multi_entry_view_result)

        # Arrange — parent SubtreeNode with 8 children (large child_map)
        parent_node = mocker.MagicMock()
        parent_node.has_sub_heading_children = True
        parent_node.is_code_block = False
        parent_node.content = ""
        parent_node.total_tokens = 0
        parent_node.title = "Design Section"
        parent_node.ordinal = "0.0"
        parent_node.child_ordinals = [f"0.0.{i}" for i in range(8)]
        parent_node.code_block_ordinals = []

        child_nodes: dict[str, object] = {}
        for i in range(8):
            child = mocker.MagicMock()
            child.title = f"SubHeading{i}"
            child.total_tokens = 15
            child.has_sub_heading_children = False
            child.is_code_block = False
            child.ordinal = f"0.0.{i}"
            child.child_ordinals = []
            child.code_block_ordinals = []
            child_nodes[f"0.0.{i}"] = child

        nodes: dict[str, object] = {"0.0": parent_node, **child_nodes}

        def _resolve(ordinal: str) -> object:
            if ordinal in nodes:
                return nodes[ordinal]
            raise OrdinalNotFoundError(ordinal, list(nodes))

        mock_mapper = mocker.MagicMock()
        mock_mapper.build_map.return_value = [
            OrdinalEntry(ordinal="0.0", title="Design Section", est_tokens=120, first_line_preview="...")
        ]
        mock_mapper.resolve.side_effect = _resolve
        mock_mapper.valid_ordinals.return_value = list(nodes)
        mocker.patch("backlog_core.disclosure_handler.OrdinalPathMapper", return_value=mock_mapper)

        # Mock extractor: bounding a large child_map to head=1 → truncated=True
        mock_extractor = mocker.MagicMock()
        mock_extractor.extract.return_value = BoundedContent(
            content="0.0.0  SubHeading0\n", returned_tokens=3, total_tokens=120, truncated=True
        )
        mocker.patch("backlog_core.disclosure_handler.TokenBoundedExtractor", return_value=mock_extractor)

        # Act — EXTRACT mode: navigate="0.0" + head=1 (forces truncation)
        result = BacklogViewDisclosureHandler().handle(
            "synthetic-selector", DisclosureRequestParser().parse(navigate="0.0", head=1)
        )

        # Assert
        assert isinstance(result, NavigateResponse), (
            f"EXTRACT on sub-heading parent must return NavigateResponse; "
            f"got {type(result).__name__}. "
            "RED: current _handle_extract always returns BoundedResponse."
        )
        assert result.has_children is True, "has_children must be True for sub-heading parent in EXTRACT mode (§4.4)."
        assert result.child_map is not None, "child_map must not be None when has_children=True."
        assert result.truncated is True, "truncated must be True when child_map text exceeds head=1 token (§4.4)."
