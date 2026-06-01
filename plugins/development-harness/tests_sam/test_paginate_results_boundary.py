"""Boundary tests for _paginate_results — pagination algorithm pinning.

Pins the O(N) binary-search pagination against token-straddling data so that
regressions in the algorithm (off-by-one in bisect direction, dropped
forced-minimum-of-1 guard, incorrect serialization) are immediately visible.

Context:
    _paginate_results was refactored from O(N²) re-serialization to O(N)
    binary search at commit d7175a17.  The existing test suite exercises
    happy-path pagination but does not construct data that straddles the
    4 400-token budget.  Any regression in the binary search (e.g. switching
    from bisect_right to bisect_left semantics, dropping the lo=1 floor)
    would be invisible without these tests.

Token counting implementation (from server.py):
    len(_enc.encode(json.dumps(page_items[:k]))) — tiktoken cl100k_base,
    standard json.dumps separators (key insertion order preserved).  Tests
    use the same encoder to compute calibration values so they remain correct
    if the encoder changes; _assert_calibration() enforces this at collection
    time.

Calibrated item shapes (verified against live _paginate_results in the
Python 3.14 / tiktoken environment in use when these tests were written):
    - body='x' * 2000: each item ~278 tokens (prefix-cumulative).
      token_count([:15]) = 4 172 (≤ 4 400, fits)
      token_count([:16]) = 4 450 (> 4 400, excluded)
      Effective cut-point: 15 items returned when 20+ items are available.
    - body='x' * 34957: single item = 4 401 tokens (> 4 400).
      Forces effective_limit = 1 via the lo ≥ 1 guard.
    - body='x' * 34956: single item = 4 400 tokens (= budget exactly).
      Inclusive boundary: item is included (effective_limit = 1, count = 1).
"""

from __future__ import annotations

import json
from typing import Any

from progressive_markdown.list_navigator import (
    ENCODING as _enc,
    TOKEN_BUDGET as _TOKEN_BUDGET,
    paginate_results as _paginate_results,
)
from hypothesis import given, settings, strategies as st

# ---------------------------------------------------------------------------
# Calibrated constants
#
# All values below were measured by running the tiktoken cl100k_base encoder
# against json.dumps output in the same Python / tiktoken environment used by
# the plugin's test runner (Python 3.14, tiktoken with cl100k_base).
#
# _assert_calibration() verifies these constants at collection time.  If the
# encoding changes, collection fails with a clear error message rather than
# silently asserting a wrong cut-point.
# ---------------------------------------------------------------------------

# Body character count for "normal" items in cut-point tests.
# token_count([:15]) = 4 172 ≤ 4 400 (budget)
# token_count([:16]) = 4 450 > 4 400 (excluded)
_BODY_NORMAL: int = 2000

# Expected effective_limit (cut-point) for 20+ items with _BODY_NORMAL.
_CUT_POINT_K: int = 15

# Token counts at and just past the cut-point (used in calibration assertions).
_T_AT_CUT: int = 4172
_T_PAST_CUT: int = 4450

# Minimum body character count that makes a SINGLE item exceed the budget.
# token_count([:1]) = _TOKEN_BUDGET + 1 = 4 401.
_BODY_OVERSIZED: int = 34957

# 2-item discriminating dataset: item 1 body=1000, item 2 body=33725.
# token_count([item1, item2][:2]) = _TOKEN_BUDGET = 4 400 (exactly at budget).
# token_count([item1, item2, item3][:3]) = 4 441 > _TOKEN_BUDGET (item 3 excluded).
# This dataset exercises the binary-search comparison (lo=1 < hi=3) so the
# <= vs < operator is actually evaluated.  A single-item dataset is floor-dominated
# and never evaluates the comparison.
_BODY_ITEM1_EXACT: int = 1000
_BODY_ITEM2_EXACT: int = 33725
_BODY_ITEM3_EXTRA: int = 100
_T_PREFIX2_EXACT: int = 4400  # token_count([item1, item2][:2]) == _TOKEN_BUDGET


# ---------------------------------------------------------------------------
# Item factory helpers
# ---------------------------------------------------------------------------


def _make_item(n: int, body_chars: int) -> dict[str, Any]:
    """Return a minimal plan-item dict with a body string of known length.

    Args:
        n: Numeric suffix for the item ID (e.g. 1 → 'T01').
        body_chars: Number of 'x' characters in the body field.

    Returns:
        Dict with id, title, status, and body fields.
    """
    return {"id": f"T{n:02d}", "title": f"Task {n}", "status": "not-started", "body": "x" * body_chars}


def _token_count_prefix(items: list[dict[str, Any]], k: int) -> int:
    """Return the token count of json.dumps(items[:k]) under cl100k_base.

    This mirrors the exact expression used by _paginate_results so that
    calibration values in this module are computed by the same function,
    not by a separate approximation.

    Args:
        items: List of plan-item dicts.
        k: Prefix length.

    Returns:
        Token count as an integer.
    """
    return len(_enc.encode(json.dumps(items[:k])))


# ---------------------------------------------------------------------------
# Calibration assertions — fail fast if encoder changes invalidate test data
# ---------------------------------------------------------------------------


def _assert_calibration() -> None:
    """Assert that item shapes produce the expected token counts.

    Called once at module import time.  If tiktoken's cl100k_base encoding
    changes, these assertions fail immediately rather than producing silent
    wrong cut-point assertions in individual tests.

    Body sizes were calibrated in the Python 3.14 / tiktoken environment
    used by the plugin's test runner.  The calibration constants
    (_BODY_OVERSIZED, _BODY_AT_BUDGET, _BODY_NORMAL, _CUT_POINT_K) are
    module-level so every test references them rather than repeating literals.
    """
    items_2000 = [_make_item(i, _BODY_NORMAL) for i in range(1, 21)]
    assert _token_count_prefix(items_2000, _CUT_POINT_K) == _T_AT_CUT, (
        f"Calibration failure: {_CUT_POINT_K} x body={_BODY_NORMAL} no longer produces {_T_AT_CUT} tokens"
    )
    assert _token_count_prefix(items_2000, _CUT_POINT_K + 1) == _T_PAST_CUT, (
        f"Calibration failure: {_CUT_POINT_K + 1} x body={_BODY_NORMAL} no longer produces {_T_PAST_CUT} tokens"
    )
    assert _token_count_prefix([_make_item(1, _BODY_OVERSIZED)], 1) == _TOKEN_BUDGET + 1, (
        f"Calibration failure: body={_BODY_OVERSIZED} no longer produces {_TOKEN_BUDGET + 1} tokens"
    )
    # 2-item discriminating dataset (exercises the binary search comparison body)
    exact_items = [_make_item(1, _BODY_ITEM1_EXACT), _make_item(2, _BODY_ITEM2_EXACT), _make_item(3, _BODY_ITEM3_EXTRA)]
    assert _token_count_prefix(exact_items, 2) == _T_PREFIX2_EXACT, (
        f"Calibration failure: 2-item prefix no longer produces "
        f"{_T_PREFIX2_EXACT} tokens exactly (got "
        f"{_token_count_prefix(exact_items, 2)})"
    )
    assert _token_count_prefix(exact_items, 3) > _TOKEN_BUDGET, (
        "Calibration failure: 3-item prefix should exceed budget (item 3 excluded)"
    )


_assert_calibration()


# ---------------------------------------------------------------------------
# Helper — call _paginate_results with test defaults
# ---------------------------------------------------------------------------


def _paginate(
    all_items: list[dict[str, Any]], *, offset: int = 0, limit: int | None = None, tool_name: str = "test_tool"
) -> dict[str, Any]:
    """Thin wrapper around _paginate_results with empty message lists.

    Args:
        all_items: Full list of items to paginate.
        offset: Number of items to skip from the start.
        limit: Explicit page size (None → auto from token budget).
        tool_name: Name used in ``next_call`` template string.

    Returns:
        Full response dict from _paginate_results.
    """
    return _paginate_results(
        all_items, offset=offset, limit=limit, messages=[], warnings=[], errors=[], tool_name=tool_name
    )


# ---------------------------------------------------------------------------
# Test 1: Token-straddling cut-point
# ---------------------------------------------------------------------------


class TestTokenStraddlingCutPoint:
    """Verify the binary search finds the correct cut-point when items straddle the budget."""

    def test_cut_point_at_budget_boundary(self) -> None:
        """Return exactly _CUT_POINT_K items when 20 items straddle the 4 400-token budget.

        Calibration:
            body=_BODY_NORMAL → token_count([:_CUT_POINT_K])     = _T_AT_CUT  ≤ 4 400 (fits)
                                  token_count([:_CUT_POINT_K + 1]) = _T_PAST_CUT > 4 400 (excluded)
        The binary search must converge to effective_limit = _CUT_POINT_K, not
        _CUT_POINT_K - 1 or _CUT_POINT_K + 1.
        A bisect_left / bisect_right inversion would produce the wrong value.
        """
        # Arrange
        items = [_make_item(i, _BODY_NORMAL) for i in range(1, 21)]

        # Act
        result = _paginate(items)

        # Assert
        pagination = result["pagination"]
        assert pagination["limit"] == _CUT_POINT_K, (
            f"Expected effective_limit={_CUT_POINT_K} but got {pagination['limit']}; "
            f"token_count([:{_CUT_POINT_K}])={_T_AT_CUT}, "
            f"token_count([:{_CUT_POINT_K + 1}])={_T_PAST_CUT}, budget={_TOKEN_BUDGET}"
        )
        assert result["count"] == _CUT_POINT_K
        assert pagination["has_more"] is True
        assert pagination["total"] == 20

    def test_items_list_matches_pagination_limit(self) -> None:
        """The items list length equals the pagination limit.

        Asserts that the returned ``items`` slice is consistent with the
        ``pagination.limit`` value — no off-by-one between slice and metadata.
        """
        # Arrange
        items = [_make_item(i, _BODY_NORMAL) for i in range(1, 21)]

        # Act
        result = _paginate(items)

        # Assert
        assert len(result["items"]) == result["pagination"]["limit"]

    def test_next_call_uses_correct_offset(self) -> None:
        """next_call offset equals the number of items in the current page.

        When _CUT_POINT_K items are returned from offset=0, next_call should
        continue at offset=_CUT_POINT_K.
        """
        # Arrange
        items = [_make_item(i, _BODY_NORMAL) for i in range(1, 21)]
        expected = f"sam_plan(offset={_CUT_POINT_K}, limit={_CUT_POINT_K})"

        # Act
        result = _paginate(items, tool_name="sam_plan")

        # Assert
        assert "next_call" in result
        assert result["next_call"] == expected


# ---------------------------------------------------------------------------
# Test 2: Forced-minimum-of-1 guard
# ---------------------------------------------------------------------------


class TestForcedMinimumOfOne:
    """Verify a single oversized item still returns effective_limit=1.

    The binary search starts with lo=1.  Even when the serialized single
    item exceeds the token budget, lo never falls below 1, so the item is
    always included.  This guard must survive any future refactor.
    """

    def test_single_oversized_item_returns_effective_limit_one(self) -> None:
        """A single item exceeding 4 400 tokens returns effective_limit=1.

        Calibration:
            body=_BODY_OVERSIZED → token_count([:1]) = _TOKEN_BUDGET + 1 (exceeds)
        The function must still return 1 item — the budget cannot reduce the
        page below the minimum of 1.  The lo=1 floor in the binary search
        invariant ensures this.
        """
        # Arrange
        oversized = [_make_item(1, _BODY_OVERSIZED)]
        assert _token_count_prefix(oversized, 1) > _TOKEN_BUDGET, "Precondition: item must exceed budget"

        # Act
        result = _paginate(oversized)

        # Assert
        assert result["pagination"]["limit"] == 1, (
            f"Forced-minimum guard failed: expected effective_limit=1 for oversized item, "
            f"got {result['pagination']['limit']}"
        )
        assert result["count"] == 1
        assert result["pagination"]["has_more"] is False

    def test_multiple_oversized_items_returns_effective_limit_one(self) -> None:
        """When every item individually exceeds the budget, returns exactly 1 item.

        Verifies the guard holds when there are multiple oversized items in the
        list — the binary search must not skip the lo=1 floor and return 0.
        """
        # Arrange
        items = [_make_item(i, _BODY_OVERSIZED) for i in range(1, 5)]

        # Act
        result = _paginate(items)

        # Assert
        assert result["pagination"]["limit"] == 1
        assert result["count"] == 1
        assert result["pagination"]["has_more"] is True


# ---------------------------------------------------------------------------
# Test 3: Item exactly at the budget boundary
# ---------------------------------------------------------------------------


class TestExactBudgetBoundary:
    """Verify the inclusive boundary: cumulative token_count == budget means the item is included.

    This class uses a 2-item dataset so the binary search comparison body actually
    executes (lo=1 < hi=2 is True).  A single-item dataset is dominated by the
    lo=1 floor and never evaluates the ``<= _TOKEN_BUDGET`` expression, making it
    indistinguishable from the forced-minimum-of-1 guard.
    """

    def test_item_at_exact_cumulative_budget_is_included(self) -> None:
        """Item 2 is included when the 2-item prefix lands exactly at the token budget.

        Calibration:
            item1 body=_BODY_ITEM1_EXACT, item2 body=_BODY_ITEM2_EXACT:
            token_count([:2]) = _TOKEN_BUDGET = 4 400 (inclusive boundary, fits by ≤)
            token_count([:3]) > _TOKEN_BUDGET (item 3 excluded)

        The binary search evaluates ``len(_enc.encode(json.dumps(page_items[:mid]))) <=
        _TOKEN_BUDGET`` with mid=2, so this test discriminates ``<=`` from ``<``.
        Under a strict ``<`` operator:
            4400 < 4400 → False → hi = mid - 1 = 1 → effective_limit = 1 (wrong)
        Under the correct ``<=`` operator:
            4400 <= 4400 → True → lo = mid = 2 → effective_limit = 2 (correct)
        """
        # Arrange
        items = [_make_item(1, _BODY_ITEM1_EXACT), _make_item(2, _BODY_ITEM2_EXACT), _make_item(3, _BODY_ITEM3_EXTRA)]
        assert _token_count_prefix(items, 2) == _TOKEN_BUDGET, (
            "Precondition: 2-item prefix must equal the token budget exactly"
        )
        assert _token_count_prefix(items, 3) > _TOKEN_BUDGET, "Precondition: 3-item prefix must exceed the budget"

        # Act
        result = _paginate(items)

        # Assert
        assert result["pagination"]["limit"] == 2, (
            f"Inclusive boundary failed: 2-item prefix at exactly {_TOKEN_BUDGET} tokens "
            f"should produce effective_limit=2, but got {result['pagination']['limit']}. "
            f"A strict '<' operator would produce effective_limit=1."
        )
        assert result["count"] == 2
        assert result["pagination"]["has_more"] is True


# ---------------------------------------------------------------------------
# Test 4: Off-by-one regression — item at cut-point included, next excluded
# ---------------------------------------------------------------------------


class TestOffByOneRegression:
    """Pin the precise inclusive/exclusive behaviour at the binary-search cut-point.

    These tests will catch a bisect_left / bisect_right inversion where the
    search converges one step too few (item N-1 returned instead of N) or one
    step too many (item N+1 returned instead of N).
    """

    def test_item_at_cut_point_is_included(self) -> None:
        """The last item that fits within the token budget is present in the result.

        With 20 items of body=_BODY_NORMAL, item _CUT_POINT_K is the last that fits:
            token_count([:_CUT_POINT_K]) = _T_AT_CUT ≤ _TOKEN_BUDGET
        It must appear in result['items'].
        """
        # Arrange
        items = [_make_item(i, _BODY_NORMAL) for i in range(1, 21)]
        cut_item_id = items[_CUT_POINT_K - 1]["id"]  # 0-indexed = 1-indexed _CUT_POINT_K

        # Act
        result = _paginate(items)
        returned_ids = {item["id"] for item in result["items"]}

        # Assert
        assert cut_item_id in returned_ids, (
            f"Item at cut-point ({cut_item_id}) should be in the result but is absent. "
            f"effective_limit={result['pagination']['limit']}, returned={sorted(returned_ids)}"
        )

    def test_item_just_past_cut_point_is_excluded(self) -> None:
        """The first item that would exceed the token budget is absent from the result.

        With 20 items of body=_BODY_NORMAL, item _CUT_POINT_K + 1 is the first that
        exceeds the budget:
            token_count([:_CUT_POINT_K + 1]) = _T_PAST_CUT > _TOKEN_BUDGET
        It must NOT appear in result['items'].
        """
        # Arrange
        items = [_make_item(i, _BODY_NORMAL) for i in range(1, 21)]
        over_item_id = items[_CUT_POINT_K]["id"]  # 0-indexed _CUT_POINT_K = 1-indexed +1

        # Act
        result = _paginate(items)
        returned_ids = {item["id"] for item in result["items"]}

        # Assert
        assert over_item_id not in returned_ids, (
            f"Item just past cut-point ({over_item_id}) must be excluded, but appeared in result. "
            f"effective_limit={result['pagination']['limit']}, returned={sorted(returned_ids)}"
        )

    def test_cut_point_is_exactly_k_not_k_minus_one_or_k_plus_one(self) -> None:
        """The effective_limit is _CUT_POINT_K, not _CUT_POINT_K±1.

        This test is the clearest statement of the off-by-one invariant and the
        one most likely to catch a bisect direction error.
        """
        # Arrange
        items = [_make_item(i, _BODY_NORMAL) for i in range(1, 21)]

        # Act
        result = _paginate(items)
        limit = result["pagination"]["limit"]

        # Assert
        assert limit != _CUT_POINT_K - 1, (
            f"Bisect converged one item short: got {_CUT_POINT_K - 1}, expected {_CUT_POINT_K}"
        )
        assert limit != _CUT_POINT_K + 1, (
            f"Bisect converged one item too many: got {_CUT_POINT_K + 1}, expected {_CUT_POINT_K}"
        )
        assert limit == _CUT_POINT_K, f"Expected effective_limit={_CUT_POINT_K}, got {limit}"


# ---------------------------------------------------------------------------
# Test 5: Offset correctness
# ---------------------------------------------------------------------------


class TestOffsetBehavior:
    """Verify that offset shifts the page_items window without affecting the cut-point logic."""

    def test_offset_shifts_window_and_cut_point_still_applies(self) -> None:
        """With 25 items and offset=5, the cut-point applies to the 20-item window.

        page_items = items[5:] → 20 items with body=_BODY_NORMAL.
        The binary search runs on page_items, producing the same effective_limit
        of _CUT_POINT_K.
        """
        # Arrange
        items = [_make_item(i, _BODY_NORMAL) for i in range(1, 26)]

        # Act
        result = _paginate(items, offset=5)

        # Assert
        pagination = result["pagination"]
        assert pagination["limit"] == _CUT_POINT_K
        assert pagination["offset"] == 5
        assert result["count"] == _CUT_POINT_K
        assert pagination["has_more"] is True
        assert pagination["total"] == 25

    def test_explicit_limit_bypasses_token_budget(self) -> None:
        """An explicit limit parameter bypasses the token budget binary search.

        When limit is provided, _paginate_results uses it directly without
        consulting the token budget.  This test confirms the bypass path
        is not affected by the binary search refactor.
        """
        # Arrange
        items = [_make_item(i, _BODY_NORMAL) for i in range(1, 21)]

        # Act — request only 5 items (well within budget)
        result = _paginate(items, limit=5)

        # Assert
        assert result["pagination"]["limit"] == 5
        assert result["count"] == 5

    def test_empty_items_returns_zero_count(self) -> None:
        """An empty all_items list returns count=0 without entering the binary search.

        The ``if page_items:`` guard means the binary search branch is never
        reached.  effective_limit falls back to len(page_items) == 0.
        """
        # Arrange / Act
        result = _paginate([])

        # Assert
        assert result["count"] == 0
        assert result["pagination"]["limit"] == 0
        assert result["pagination"]["has_more"] is False


# ---------------------------------------------------------------------------
# Test 6: Response structure invariants
# ---------------------------------------------------------------------------


class TestResponseStructureInvariants:
    """Verify the returned dict always contains the required keys."""

    def test_required_keys_present_in_normal_response(self) -> None:
        """All required top-level keys are present for a normal paginated response.

        Tests that the binary-search refactor did not accidentally drop any of
        the response fields the MCP callers depend on.
        """
        # Arrange
        items = [_make_item(i, _BODY_NORMAL) for i in range(1, 21)]

        # Act
        result = _paginate(items)

        # Assert
        required_top_level = {"items", "count", "pagination", "messages", "warnings", "errors"}
        assert required_top_level <= result.keys(), f"Missing top-level keys: {required_top_level - result.keys()}"

        required_pagination = {"offset", "limit", "total", "has_more"}
        assert required_pagination <= result["pagination"].keys(), (
            f"Missing pagination keys: {required_pagination - result['pagination'].keys()}"
        )

    def test_next_call_absent_when_no_more_pages(self) -> None:
        """next_call is absent from the response when all items fit on one page.

        When has_more is False, the caller should not see a next_call key.
        """
        # Arrange — 3 tiny items that all fit in the budget
        items = [_make_item(i, 10) for i in range(1, 4)]

        # Act
        result = _paginate(items)

        # Assert
        assert result["pagination"]["has_more"] is False
        assert "next_call" not in result, (
            f"next_call should be absent when has_more=False, got: {result.get('next_call')}"
        )

    def test_messages_warnings_errors_propagated(self) -> None:
        """Messages, warnings, and errors from the caller are echoed verbatim.

        _paginate_results does not modify the lists — it injects them as-is.
        """
        # Arrange
        items = [_make_item(i, 10) for i in range(1, 4)]
        msgs = ["info: plan loaded"]
        warns = ["warning: large plan"]
        errs = ["error: task missing"]

        # Act
        result = _paginate_results(
            items, offset=0, limit=None, messages=msgs, warnings=warns, errors=errs, tool_name="test_tool"
        )

        # Assert
        assert result["messages"] == msgs
        assert result["warnings"] == warns
        assert result["errors"] == errs


# ---------------------------------------------------------------------------
# Hypothesis: budget invariant across random item sizes
# ---------------------------------------------------------------------------


@given(item_sizes=st.lists(st.integers(min_value=1, max_value=5000), min_size=1, max_size=30))
@settings(max_examples=100, deadline=None)
def test_hypothesis_budget_invariant(item_sizes: list[int]) -> None:
    """Token budget invariant: the cut-point is maximal and bounded.

    For any list of items with randomised body sizes, the invariant is:

    - effective_limit >= 1 (floor from lo=1, no empty pages)
    - len(items) == effective_limit (page slice matches limit metadata)
    - If effective_limit > 1: token_count(returned_slice) <= budget
      (under-inclusion guard: the returned prefix fits within the budget)
    - If effective_limit < len(all_items): token_count(items[:effective_limit+1]) > budget
      (maximality guard: the next item would have exceeded the budget, so the
      cut is at the largest valid k, not a smaller one)

    The maximality guard is the key addition: without it, a bisect bug that
    returns effective_limit=k-1 (one too few) would pass the under-inclusion
    check alone, because a shorter prefix trivially fits within the budget.

    Args:
        item_sizes: List of body character counts for each generated item.
    """
    items = [_make_item(i + 1, size) for i, size in enumerate(item_sizes)]
    result = _paginate(items)
    effective_limit = result["pagination"]["limit"]

    # Floor: the binary search must never return 0 items when page_items is non-empty
    assert effective_limit >= 1, f"effective_limit={effective_limit} is less than 1 for non-empty items list"

    # Consistency: the returned items list must match the pagination limit
    assert len(result["items"]) == effective_limit

    # Under-inclusion guard: if effective_limit > 1, the prefix must fit within budget
    if effective_limit > 1:
        returned_slice = result["items"]
        token_count = _token_count_prefix(returned_slice, len(returned_slice))
        assert token_count <= _TOKEN_BUDGET, (
            f"Budget exceeded: token_count={token_count} > budget={_TOKEN_BUDGET} for effective_limit={effective_limit}"
        )

    # Maximality guard: if there are more items, the next item must have pushed over budget
    if effective_limit < len(items):
        next_count = _token_count_prefix(items, effective_limit + 1)
        assert next_count > _TOKEN_BUDGET, (
            f"Cut-point is not maximal: adding item {effective_limit + 1} produces "
            f"{next_count} tokens which is still within budget={_TOKEN_BUDGET}. "
            f"The binary search converged too early at effective_limit={effective_limit}."
        )
