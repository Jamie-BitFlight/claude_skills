"""Pin NavigationResult return contract for ProgressiveDisclosure.select() and .page().

Phase 0, Concern C1. Tests are authored independently of the implementation (T09)
to ensure they validate desired behavior, not just consistency with implementation.

Architect §4.1.1 defines the authoritative post-fix signatures::

    class ProgressiveDisclosure:
        def select(self, selector: str) -> NavigationResult: ...
        def page(self, page_num: int = 1) -> NavigationResult: ...

``paginate_results()`` in the same module is a separate list-pagination shim.
Its ``dict[str, Any]`` return type is NOT changed by C1.

Test state pre-fix (current code):
  - ``select(found_id)``   returns ``dict[str, Any]``          → RED (isinstance fails)
  - ``select(missing_id)`` returns ``None``                    → RED (is not None fails)
  - ``page(1)``            returns ``dict[str, Any]``          → RED (isinstance fails)
  - ``paginate_results()`` returns ``dict[str, Any]``          → GREEN (legacy contract)
  - ``NavigationResult.model_dump()``                          → GREEN (Pydantic method exists)

Test state post-fix (T09 implemented):
  All five tests GREEN.
"""

from __future__ import annotations

import pytest
from progressive_markdown.list_navigator import DisclosureConfig, ProgressiveDisclosure, paginate_results
from progressive_markdown.models import NavigationKind, NavigationResult, Page

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_ITEMS: list[dict[str, object]] = [
    {"id": "T01", "title": "Write tests", "status": "not-started"},
    {"id": "T02", "title": "Implement fix", "status": "not-started"},
    {"id": "T03", "title": "Run linter", "status": "not-started"},
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def disclosure() -> ProgressiveDisclosure:
    """ProgressiveDisclosure instance over three sample task items."""
    return ProgressiveDisclosure(_ITEMS, config=DisclosureConfig(id_field="id"), tool_name="test_tool")


# ---------------------------------------------------------------------------
# C1a — select() returns NavigationResult for a found item (RED pre-fix)
# ---------------------------------------------------------------------------


def test_select_found_item_returns_navigation_result(disclosure: ProgressiveDisclosure) -> None:
    """select() must return NavigationResult when the item is found (architect §4.1.1).

    PRE-FIX STATE: FAILS.
    Current implementation returns the raw item dict, not NavigationResult.
    isinstance(dict, NavigationResult) is False → AssertionError.

    POST-FIX EXPECTATION (T09):
    select("T01") returns a NavigationResult instance.
    Kind and page structure are implementation choices for T09; only
    the return type is pinned here per the authoritative §4.1.1 signature.
    """
    result = disclosure.select("T01")

    assert isinstance(result, NavigationResult), (
        f"select() must return NavigationResult for a found item. "
        f"Got {type(result).__name__!r}. "
        f"Fix: update ProgressiveDisclosure.select() per architect §4.1.1."
    )


# ---------------------------------------------------------------------------
# C1b — select() returns NavigationResult (not None) for a missing item (RED pre-fix)
# ---------------------------------------------------------------------------


def test_select_missing_item_returns_navigation_result_not_none(disclosure: ProgressiveDisclosure) -> None:
    """select() must return NavigationResult for an unmatched selector — never None.

    Architect §4.1.1: ``def select(self, selector: str) -> NavigationResult``
    The return type has no ``| None`` branch. Not-found must be signalled inside
    the NavigationResult (e.g. via ``kind`` or empty pages) without breaking the
    uniform return type contract.

    PRE-FIX STATE: FAILS.
    Current implementation returns ``None`` for an unmatched item_id.
    ``assert result is not None`` → AssertionError.

    POST-FIX EXPECTATION (T09):
    select("NONEXISTENT") returns a NavigationResult. The specific kind
    (e.g. ``NavigationKind.error``) is T09's implementation choice and is
    NOT asserted here — only the return type is pinned.
    """
    result = disclosure.select("NONEXISTENT")

    assert result is not None, (
        "select() must not return None for an unmatched selector. "
        "Fix: return NavigationResult (e.g. kind=error) per architect §4.1.1."
    )
    assert isinstance(result, NavigationResult), (
        f"select() must return NavigationResult for an unmatched selector. Got {type(result).__name__!r}."
    )


# ---------------------------------------------------------------------------
# C1c — page() returns NavigationResult (RED pre-fix)
# ---------------------------------------------------------------------------


def test_page_returns_navigation_result(disclosure: ProgressiveDisclosure) -> None:
    """page() must return NavigationResult (architect §4.1.1).

    PRE-FIX STATE: FAILS.
    Current implementation returns a plain dict with keys ``items``, ``count``,
    ``pagination``. isinstance(dict, NavigationResult) is False → AssertionError.

    POST-FIX EXPECTATION (T09):
    page(1) returns a NavigationResult instance. Structural details (pages list
    shape, current_page value) are implementation choices for T09 and are not
    asserted here — the authoritative §4.1.1 signature pins only the return type.
    """
    result = disclosure.page(1)

    assert isinstance(result, NavigationResult), (
        f"page() must return NavigationResult. "
        f"Got {type(result).__name__!r}. "
        f"Fix: update ProgressiveDisclosure.page() per architect §4.1.1."
    )


# ---------------------------------------------------------------------------
# C1d — paginate_results() dict shim preserved (GREEN pre-fix and post-fix)
# ---------------------------------------------------------------------------


def test_paginate_results_returns_dict_with_legacy_keys() -> None:
    """paginate_results() must retain its legacy dict return shape — unchanged by C1.

    The function is a drop-in shim for list tools (offset/limit pagination).
    Architect §4.1.1 explicitly states: 'paginate_results() ... returns dict[str, Any]
    (list pagination, different contract) — this return type is not changed.'

    GREEN pre-fix: current code returns dict with these keys.
    GREEN post-fix: shim is untouched by the C1 fix.
    """
    items = [{"id": f"T{i:02d}", "title": f"Task {i}"} for i in range(5)]

    result = paginate_results(items, offset=0, limit=3, messages=[], warnings=[], errors=[], tool_name="test_tool")

    assert isinstance(result, dict), (
        f"paginate_results() must return dict (legacy shim). Got {type(result).__name__!r}."
    )
    # Core legacy keys that callers depend on
    for key in ("items", "count", "pagination", "messages", "warnings", "errors"):
        assert key in result, f"Legacy key {key!r} must be present in paginate_results() output."
    # Pagination sub-dict shape
    pagination = result["pagination"]
    for sub_key in ("offset", "limit", "total", "has_more"):
        assert sub_key in pagination, f"pagination[{sub_key!r}] must be present in paginate_results() output."
    # Verify count reflects the limit
    assert result["count"] == 3
    assert result["pagination"]["total"] == 5


# ---------------------------------------------------------------------------
# C1e — NavigationResult.model_dump() is available for dict-migration callers
# ---------------------------------------------------------------------------


def test_navigation_result_model_dump_available_for_dict_migration() -> None:
    """NavigationResult.model_dump() must produce a complete serialisable dict.

    Callers currently receiving select()/page() as dicts can migrate to
    ``result.model_dump()`` to get the equivalent dict representation.
    Architect §4.1.1 backward-compat note: 'NavigationResult is a Pydantic
    model with .model_dump() → existing callers receiving a dict can migrate
    to result.model_dump().'

    GREEN pre-fix: NavigationResult already has model_dump() (Pydantic v2 model).
    GREEN post-fix: unchanged.
    """
    page = Page(content="Task T01 content", page_number=1, total_pages=1, token_count=4, budget=9500)
    nav_result = NavigationResult(
        kind=NavigationKind.section_body, title="T01", pages=[page], current_page=1, total_pages=1
    )

    dumped = nav_result.model_dump()

    assert isinstance(dumped, dict), "NavigationResult.model_dump() must return dict for dict-migration callers."
    # Fields that migration callers need to read back
    for field in ("kind", "title", "pages", "current_page", "total_pages", "has_more"):
        assert field in dumped, f"model_dump() must include field {field!r} for complete dict migration."
    # Computed field has_more is included in model_dump() (Pydantic v2 @computed_field)
    assert isinstance(dumped["has_more"], bool)
