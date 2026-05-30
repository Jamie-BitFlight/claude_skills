"""RED regression tests for GitHub issue #2495.

Two distinct defects fire when ``backlog_view(summary=False)`` is called on a
large GitHub-backed item (raw body, no structured YAML sections).  Both were
observed during grooming of issue #2438 (body ~32k chars).

Defect (a) — over-budget gate suppresses explicitly requested narrowing
-----------------------------------------------------------------------
The auto-compact gate in ``server.backlog_view`` returns a metadata-only
``_build_over_budget_view`` response whenever the serialised full response
exceeds the token budget — *even when* the caller passed ``offset``/``limit``
or ``sections=[...]`` to narrow the payload.  ``offset``/``limit`` narrow
``result.body`` but NOT the structured ``result.sections`` dict, so
``model_dump()`` still serialises to >4000 tokens and the gate trips.  The
pagination the caller requested is computed and then discarded; the caller
receives the section directory instead of the page they asked for.

Defect (b) — numeric / comma / regex section forms MISS on raw GitHub bodies
----------------------------------------------------------------------------
``_apply_body_section_filter`` (the raw-body filter path) only performs
case-insensitive *name* matching against ``## ``/``### `` headers.  It never
interprets ``section="4"`` as a numeric index, ``section="0,2"`` as
comma-separated indices, or ``section="/regex/"`` as a regex — although the
``backlog_view`` tool docstring and the ``section`` parameter description
advertise all of those forms.  A numeric/regex/comma ``section`` value is
compared literally as a header name, misses, leaves the body unchanged
(full size), and therefore (1) reports ``section_filter_miss: True`` and
(2) trips defect (a)'s over-budget gate.

Both test classes MUST FAIL against current code and PASS after the fix.

Test naming: every test contains ``over_budget`` or ``numeric_section`` so
``pytest -k "over_budget or numeric_section"`` selects the whole suite.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from backlog_core.models import BacklogItem, Section, ViewItemResult
from backlog_core.operations import _apply_body_section_filter

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# A multi-section body padded above _VIEW_BODY_CHARS_THRESHOLD (16000 chars) so
# the auto-compact gate engages, mirroring the real #2438 body.  Sections use
# the same ``## `` top-level / ``### `` subsection mix as real issue bodies.
_FILLER = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 60  # ~3.3k chars per block

_OVER_BUDGET_BODY = (
    "## Story\n\nAs an agent I want sections.\n\n"
    f"## Description\n\n{_FILLER}\n\n"
    f"## RT-ICA\n\n{_FILLER}\n\n"
    f"## Issue Classification\n\n{_FILLER}\n\n"
    f"## Root-Cause Analysis\n\n{_FILLER}\n\n"
    f"## Impact Radius\n\n{_FILLER}\n\n"
)

# A many-section body where the structured ``sections`` dict stays > token budget
# even after ``offset``/``limit`` paginate the body.  This reproduces the real
# #2438 offset/limit failure: pagination narrows ``result.body`` (to a handful of
# chars) but NOT ``result.sections``, so ``model_dump()`` still overflows and the
# over-budget gate discards the requested page.
_PAGER_FILLER = "Lorem ipsum dolor sit amet consectetur adipiscing. " * 70
_MANY_SECTION_BODY = "".join(f"## Section {i}\n\n{_PAGER_FILLER}\n\n" for i in range(8))


def _make_local_item(title: str = "Issue 2495") -> BacklogItem:
    """Minimal local BacklogItem so the GitHub-enrichment branch is exercised."""
    return BacklogItem(title=title, sections={"Acceptance Criteria": Section()})


def _patch_github_body(mocker: MockerFixture, issue_num: int, body: str) -> None:
    """Patch the operations layer so view_item enriches from a controlled body."""
    local_item = _make_local_item()
    mocker.patch("backlog_core.operations.parse_backlog", return_value=[local_item])
    mocker.patch("backlog_core.operations.find_item", return_value=local_item)
    mocker.patch("backlog_core.operations.parse_issue_selector", return_value=issue_num)

    def _inject_body(result: ViewItemResult, issue: str, repo: str = "") -> bool:
        result.body = body
        return True

    mocker.patch("backlog_core.operations.view_enrich_from_github", side_effect=_inject_body)


# ---------------------------------------------------------------------------
# Defect (b): numeric / comma / regex section forms must match on raw bodies
# ---------------------------------------------------------------------------


class TestNumericSectionFilterOnRawBody:
    """``_apply_body_section_filter`` must honour the documented section forms.

    The ``backlog_view`` ``section`` parameter is documented to accept a numeric
    index ('2'), comma-separated indices ('0,2'), a regex ('/impact.*/'), or a
    substring/name.  On raw GitHub bodies only the name form works today.
    """

    _SMALL_BODY = "## Alpha\n\nfirst section body\n\n## Beta\n\nsecond section body\n\n## Gamma\n\nthird section body\n"

    def test_numeric_section_index_matches_nth_header(self) -> None:
        """section='1' must select the second header (zero-based index 1).

        RED: ``_apply_body_section_filter`` compares '1' literally as a header
        name, finds no header named '1', sets section_filter_miss=True and
        returns the full body unchanged.
        """
        result = ViewItemResult()
        returned = _apply_body_section_filter(result, self._SMALL_BODY, "1")

        assert result.section_filter_miss is False, (
            "section='1' (numeric index) must resolve to the section at index 1 (Beta), "
            "not report section_filter_miss.  The raw-body filter ignores numeric indices, "
            "so it treats '1' as a literal header name and misses.  This is defect (b) of #2495."
        )
        assert returned.lstrip().startswith("## Beta"), (
            f"section='1' must return the Beta section body; got: {returned[:40]!r}. "
            "Numeric index resolution is not implemented in the raw-body filter path."
        )

    def test_numeric_section_does_not_report_filter_miss(self) -> None:
        """A valid numeric index must never set section_filter_miss on a raw body.

        RED: the miss flag is set because numeric indices are unsupported.
        """
        result = ViewItemResult()
        _apply_body_section_filter(result, self._SMALL_BODY, "0")

        assert result.section_filter_miss is False, (
            "section='0' is a valid index (first section) and must not set "
            "section_filter_miss.  Defect (b): numeric forms are unsupported on raw bodies."
        )

    def test_regex_section_matches_header_on_raw_body(self) -> None:
        """section='/bet.*/' must match the Beta header via regex.

        RED: '/bet.*/' is compared literally as a name and misses.
        """
        result = ViewItemResult()
        returned = _apply_body_section_filter(result, self._SMALL_BODY, "/bet.*/")

        assert result.section_filter_miss is False, (
            "section='/bet.*/' (regex form) must match the Beta header.  The raw-body "
            "filter does not implement regex matching, so it misses.  Defect (b) of #2495."
        )
        assert returned.lstrip().startswith("## Beta"), (
            f"Regex section='/bet.*/' must return the Beta section; got {returned[:40]!r}."
        )


# ---------------------------------------------------------------------------
# Defect (a): over-budget gate must not suppress requested narrowing
# ---------------------------------------------------------------------------


class TestOverBudgetGateHonoursNarrowing:
    """``backlog_view`` must deliver the requested slice even when the item is large.

    When a caller narrows the response via ``section=`` / ``sections=`` /
    ``offset``/``limit`` on an over-budget item, the gate must return the
    narrowed body — not fall back to the metadata-only section directory.
    """

    def test_over_budget_section_filter_returns_section_body(self, mocker: MockerFixture) -> None:
        """section='RT-ICA' on an over-budget raw body returns that section's body.

        Arrange: inject a >16k-char body containing '## RT-ICA'.
        Act: backlog_view(selector, summary=False, section='RT-ICA').
        Assert: the response carries the RT-ICA body, not the over-budget
        metadata-only shape.

        Note: this name form already narrows result.body so it should pass for the
        match case; it anchors the contract that a *matched* section must be
        delivered regardless of original item size.
        """
        _patch_github_body(mocker, 2495, _OVER_BUDGET_BODY)
        from backlog_core import server

        resp = asyncio.run(server.backlog_view(selector="2495", summary=False, section="RT-ICA"))

        assert resp.get("_over_budget") is not True, (
            "A matched section narrows the body well under budget; backlog_view must NOT "
            "return the over-budget metadata-only shape.  Got keys: " + repr(sorted(resp))
        )
        body = resp.get("body")
        assert isinstance(body, str), (
            "The response must contain a 'body' field (string) when section='RT-ICA' is "
            f"requested on an over-budget item.  body present={body is not None}."
        )
        assert "## RT-ICA" in body, (
            "The response body must contain the RT-ICA section when section='RT-ICA' is requested."
        )

    def test_over_budget_numeric_section_returns_section_body(self, mocker: MockerFixture) -> None:
        """section='2' on an over-budget raw body returns the index-2 section, not a miss.

        This is the exact #2438 failure: a numeric section on a large GitHub body
        misses (defect b), leaves the body full, and trips the over-budget gate
        (defect a) so the caller gets metadata only.

        RED: response is _over_budget with section_filter_miss=True.
        """
        _patch_github_body(mocker, 2495, _OVER_BUDGET_BODY)
        from backlog_core import server

        # Index 2 of the body's headers is '## RT-ICA'
        resp = asyncio.run(server.backlog_view(selector="2495", summary=False, section="2"))

        assert resp.get("section_filter_miss") is not True, (
            "section='2' (numeric index) must resolve to a real section on the raw body, "
            "not report section_filter_miss.  Defect (b): numeric forms unsupported -> "
            "miss -> body stays full -> defect (a) over-budget gate trips."
        )
        assert resp.get("_over_budget") is not True, (
            "section='2' must narrow the body so the over-budget gate does not fire.  "
            "Got the metadata-only shape: " + repr(sorted(resp))
        )
        body = resp.get("body")
        assert isinstance(body, str), (
            "section='2' must return a 'body' field (string) on an over-budget item, "
            "not the metadata-only over-budget shape."
        )
        assert "## RT-ICA" in body, "section='2' must return the index-2 section (RT-ICA) body on an over-budget item."

    def test_over_budget_offset_limit_returns_paged_body(self, mocker: MockerFixture) -> None:
        """offset/limit on an over-budget raw body must return the paged content.

        Arrange: inject a >16k-char body.
        Act: backlog_view(selector, summary=False, offset=0, limit=2).
        Assert: a body (the paged slice) is returned, not the over-budget
        metadata-only shape.

        RED: the over-budget gate measures the full model_dump (which still
        contains the un-paginated ``sections`` dict) and returns metadata only,
        discarding the pagination the caller requested.
        """
        _patch_github_body(mocker, 2495, _MANY_SECTION_BODY)
        from backlog_core import server

        resp = asyncio.run(server.backlog_view(selector="2495", summary=False, offset=0, limit=2))

        assert resp.get("_over_budget") is not True, (
            "offset/limit pagination must be honoured on a large item; backlog_view must "
            "not discard the requested page and return the metadata-only over-budget shape. "
            "Got keys: " + repr(sorted(resp)) + ".  This is defect (a) of #2495."
        )
        assert resp.get("body") is not None, (
            "A paged offset/limit request must return a 'body' field, not the over-budget metadata-only response."
        )

    def test_over_budget_sections_filter_returns_named_sections(self, mocker: MockerFixture) -> None:
        """sections=['RT-ICA','Issue Classification'] must return those sections' content.

        Arrange: inject a >16k-char body containing both named sections.
        Act: backlog_view(selector, summary=False, sections=[...]).
        Assert: the narrowed sections are returned, not the over-budget
        metadata-only shape.

        RED: ``_filter_view_sections`` narrows the response dict but the
        over-budget gate measures the un-narrowed ``result.body``/dump and trips,
        returning metadata only.
        """
        _patch_github_body(mocker, 2495, _OVER_BUDGET_BODY)
        from backlog_core import server

        resp = asyncio.run(
            server.backlog_view(selector="2495", summary=False, sections=["RT-ICA", "Issue Classification"])
        )

        assert resp.get("_over_budget") is not True, (
            "sections=[...] narrows the payload to the named sections; backlog_view must "
            "return those sections, not fall back to the over-budget metadata-only shape. "
            "Got keys: " + repr(sorted(resp)) + ".  This is defect (a) of #2495."
        )


# ---------------------------------------------------------------------------
# Review round (#2495): lock the contract — fallback addressability, multi-match
# substring widening, over-budget-after-narrowing, and the sections=[...] miss
# signal.
# ---------------------------------------------------------------------------

# A body whose SINGLE section's own content exceeds _VIEW_TOKEN_BUDGET (4000
# tokens ~= 16k chars).  Requesting that one section narrows to a slice that is
# itself still over budget, so the gate must NOT be bypassed by the narrowing.
_HUGE_SINGLE = "Lorem ipsum dolor sit amet consectetur adipiscing elit. " * 600  # ~33k chars
_SINGLE_OVER_BUDGET_BODY = f"## Tiny\n\nshort intro\n\n## Huge\n\n{_HUGE_SINGLE}\n\n"

# A body with two headers sharing a common substring ('Section') plus 'Other',
# to pin substring-widening (multiple matches concatenated in document order).
_SUBSTRING_BODY = (
    "## Section 1\n\nfirst widget body\n\n## Section 2\n\nsecond widget body\n\n## Other\n\nunrelated body\n"
)
# A body with a header literally named '2' (three headers => index 2 is in range).
_LITERAL_INDEX_BODY = (
    "## Alpha\n\nalpha body\n\n## 2\n\nthe literally-named two section body\n\n## Gamma\n\ngamma body\n"
)


class TestReviewRoundContract:
    """Locks the M1 fallback, substring widening, and m1 no-match signal."""

    def test_over_budget_section_narrowed_slice_still_over_budget(self, mocker: MockerFixture) -> None:
        """A single requested section whose own body exceeds the budget stays gated.

        Narrowing to one section must NOT bypass enforcement: when that section's
        slice is itself over _VIEW_TOKEN_BUDGET the response must remain the
        compact over-budget directory (``_over_budget`` True).
        """
        _patch_github_body(mocker, 2495, _SINGLE_OVER_BUDGET_BODY)
        from backlog_core import server

        resp = asyncio.run(server.backlog_view(selector="2495", summary=False, section="Huge"))

        assert resp.get("_over_budget") is True, (
            "section='Huge' narrows to a single slice that itself exceeds the "
            f"{server._VIEW_TOKEN_BUDGET}-token budget; the over-budget gate must still fire "
            "(narrowing must not bypass budget enforcement).  Got keys: " + repr(sorted(resp))
        )

    def test_substring_section_returns_all_matching_sections_in_order(self) -> None:
        """section='Section' returns BOTH '## Section 1' and '## Section 2' in order.

        Pins the documented substring-widening behaviour so a future exact-match
        regression is caught: a substring that matches multiple headers must
        concatenate all matching section bodies in document order.
        """
        result = ViewItemResult()
        returned = _apply_body_section_filter(result, _SUBSTRING_BODY, "Section")

        assert result.section_filter_miss is False, (
            "section='Section' is a substring of two headers and must match — not miss."
        )
        idx1 = returned.find("## Section 1")
        idx2 = returned.find("## Section 2")
        assert idx1 != -1, f"'## Section 1' must appear in the substring result; got {returned[:80]!r}."
        assert idx2 != -1, f"'## Section 2' must appear in the substring result; got {returned[:80]!r}."
        assert idx1 < idx2, "Matching sections must be concatenated in document order (Section 1 before Section 2)."
        assert "## Other" not in returned, "The non-matching '## Other' section must not be included."

    def test_in_range_numeric_section_selects_by_index_not_name(self) -> None:
        """section='2' with three headers resolves as numeric index 2 (Gamma).

        Pins the documented precedence: the numeric form wins when it is in range,
        even though a header is literally named '2'.  The literal-name fallback is
        covered by the out-of-range companion test below.
        """
        result = ViewItemResult()
        returned = _apply_body_section_filter(result, _LITERAL_INDEX_BODY, "2")

        assert result.section_filter_miss is False, "section='2' must resolve (index 2 = Gamma), never miss."
        assert returned.lstrip().startswith("## Gamma"), (
            f"In-range numeric '2' selects index 2 (Gamma); got {returned[:40]!r}."
        )

    def test_literal_index_named_header_reachable_when_index_out_of_range(self) -> None:
        """A header literally named '## 2' is reachable via the M1 substring fallback.

        With only two headers (indices 0,1), section='2' is out of numeric range,
        so the M1 fallback retries as a substring and matches the literally-named
        '## 2' header — proving the header is not permanently unaddressable.
        """
        body = "## Alpha\n\nalpha body\n\n## 2\n\nthe two section body\n"
        result = ViewItemResult()
        returned = _apply_body_section_filter(result, body, "2")

        assert result.section_filter_miss is False, (
            "section='2' is out of numeric range (only indices 0,1 exist) but a header is "
            "literally named '2'; the M1 fallback must reach it via substring matching, not miss."
        )
        assert "## 2" in returned, (
            f"section='2' must return the literally-named '## 2' section body; got {returned[:60]!r}."
        )
        assert "## Alpha" not in returned, (
            f"section='2' must not include the non-matching '## Alpha' section; got {returned[:60]!r}."
        )

    def test_over_budget_sections_no_match_sets_filter_miss_signal(self, mocker: MockerFixture) -> None:
        """sections=['DOES-NOT-EXIST'] on an over-budget item carries the miss signal.

        The over-budget directory may still be returned, but the response must
        carry ``section_filter_miss`` True so the caller learns the names were
        invalid rather than reading silence as "item too big".
        """
        _patch_github_body(mocker, 2495, _OVER_BUDGET_BODY)
        from backlog_core import server

        resp = asyncio.run(server.backlog_view(selector="2495", summary=False, sections=["DOES-NOT-EXIST"]))

        assert resp.get("section_filter_miss") is True, (
            "sections=['DOES-NOT-EXIST'] matched no structured section and no body header; "
            "the response must set section_filter_miss=True so the caller learns the names were "
            "invalid (m1, #2495).  Got keys: " + repr(sorted(resp))
        )
