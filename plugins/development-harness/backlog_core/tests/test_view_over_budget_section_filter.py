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

Defect (c) — sections metadata desyncs from the resolved body filter
--------------------------------------------------------------------
``_assemble_view_content`` builds ``result.sections`` via
``_build_sections_metadata(..., section=section)`` BEFORE the body is narrowed
by ``_apply_body_section_filter``.  ``_build_sections_metadata`` only matches a
section by EXACT case-insensitive *name*; it does not interpret the numeric,
comma, regex, or non-exact substring forms that ``_apply_body_section_filter``
now resolves via ``_resolve_section_indices``.  For those resolved forms the
body is narrowed correctly but ``result.sections`` is ``{}`` — body and
sections metadata desync, breaking the contract that ``sections`` stays in
sync with ``body``.  Only the exact-name form stays in sync (both match), so
only the newly-supported forms regress.  See ``TestSectionsMetadataInSync``.

Both test classes MUST FAIL against current code and PASS after the fix.

Test naming: every test contains ``over_budget`` or ``numeric_section`` so
``pytest -k "over_budget or numeric_section"`` selects the whole suite.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from backlog_core import operations
from backlog_core.models import BacklogItem, Section, ViewItemResult
from backlog_core.operations import _apply_body_section_filter

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# A multi-section body padded so its serialised response exceeds _VIEW_TOKEN_BUDGET
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


def _resp_body(resp: dict[str, object]) -> str:
    """Return the response ``body`` as a typed ``str`` (boundary accessor).

    ``backlog_view`` returns ``dict[str, object]``; ``dict.get`` therefore yields
    ``object``.  This narrows the ``body`` field to ``str`` once so call sites do
    not each repeat an ``isinstance`` narrowing inside a compound assertion.
    """
    body = resp.get("body")
    assert isinstance(body, str), f"response 'body' must be a str; got {type(body).__name__}."
    return body


def _resp_metadata(resp: dict[str, object]) -> list[dict[str, object]]:
    """Return ``sections_metadata`` as a list of typed dicts (boundary accessor).

    ``backlog_view`` returns ``dict[str, object]``; each metadata entry is itself a
    serialised ``SectionMeta`` dict.  Validating the shape here once yields fully
    typed ``dict[str, object]`` entries so call sites can index ``"name"`` without
    repeating ``isinstance`` narrowing or hitting ``dict.get`` overload mismatches.
    """
    meta = resp.get("sections_metadata")
    assert isinstance(meta, list), f"response 'sections_metadata' must be a list; got {type(meta).__name__}."
    entries: list[dict[str, object]] = []
    for entry in meta:
        assert isinstance(entry, dict), f"each metadata entry must be a dict; got {type(entry).__name__}."
        entries.append({str(k): v for k, v in entry.items()})
    return entries


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
        body = _resp_body(resp)
        assert body, (
            "A paged offset/limit request must return a non-empty 'body' field, not the "
            "over-budget metadata-only response."
        )
        # The body must be the requested PAGE, not the whole item: an early section is
        # referenced in the page while the last section's content does not leak through.
        assert "Section 0" in body, f"offset=0/limit=2 must include the first section in the page; got {body[:80]!r}."
        assert "## Section 7" not in body, (
            "offset=0/limit=2 must exclude later sections from the page — the full body must "
            "not leak through; got a body containing '## Section 7'."
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
        # The returned body must actually carry the requested section content, in document
        # order, and must NOT leak the non-requested sections (#2495 finding #10 test quality).
        body = _resp_body(resp)
        assert body, "sections=[...] must return a non-empty 'body' field."
        assert "## RT-ICA" in body, "the narrowed body must contain the requested 'RT-ICA' section."
        assert "## Issue Classification" in body, (
            "the narrowed body must contain the requested 'Issue Classification' section."
        )
        assert "## Root-Cause Analysis" not in body, (
            "the narrowed body must NOT contain a non-requested section; got a body leaking '## Root-Cause Analysis'."
        )
        assert body.find("## RT-ICA") < body.find("## Issue Classification"), (
            "matched sections must appear in document order (RT-ICA before Issue Classification)."
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


# ---------------------------------------------------------------------------
# Defect (c): result.sections must stay in sync with the resolved body filter
# ---------------------------------------------------------------------------

# A small multi-section raw body.  '## Issue Classification' and '## Issue
# Triage' share the substring 'Issue' so a substring form matches both.  Section
# headers (document order, zero-based):
#   [0] Story  [1] Description  [2] RT-ICA  [3] Issue Classification
#   [4] Issue Triage  [5] Impact Radius
_SYNC_BODY = (
    "## Story\n\nstory body\n\n"
    "## Description\n\ndescription body\n\n"
    "## RT-ICA\n\nrt-ica body\n\n"
    "## Issue Classification\n\nclassification body\n\n"
    "## Issue Triage\n\ntriage body\n\n"
    "## Impact Radius\n\nimpact body\n"
)


def _body_section_names(body: str) -> list[str]:
    """Extract ``## ``/``### `` header names from *body* in document order."""
    return [hdr.group(1).strip() for hdr in operations._SECTION_BOUNDARY_RE.finditer(body)]


def _view(mocker: MockerFixture, body: str, section: str) -> ViewItemResult:
    """Drive ``operations.view_item`` against a controlled raw GitHub body."""
    _patch_github_body(mocker, 2495, body)
    return operations.view_item(selector="2495", include_content=True, section=section)


class TestSectionsMetadataInSync:
    """``result.sections`` must mirror the narrowed ``result.body`` for ALL forms.

    Defect (c): ``_build_sections_metadata`` filters by exact name only, so for
    numeric / comma / regex / non-exact-substring forms the body is narrowed but
    ``result.sections`` is ``{}`` — the two desync.  After the fix the section
    metadata keys must equal the headers present in the narrowed body for every
    resolved form, and a genuine miss must yield empty sections plus
    ``section_filter_miss=True``.
    """

    def test_numeric_section_keeps_sections_in_sync_with_body(self, mocker: MockerFixture) -> None:
        """section='2' (numeric, in range) narrows body AND populates sections.

        RED: body becomes the RT-ICA slice, but result.sections is {} because
        _build_sections_metadata matched the literal name '2' and missed.
        """
        result = _view(mocker, _SYNC_BODY, "2")

        assert result.section_filter_miss is False, "section='2' resolves to index 2 (RT-ICA); must not miss."
        assert "## RT-ICA" in result.body, f"body must be the RT-ICA slice; got {result.body[:60]!r}."
        assert set(result.sections) == set(_body_section_names(result.body)), (
            "result.sections keys must equal the headers in the narrowed body. "
            f"sections={sorted(result.sections)} body_headers={_body_section_names(result.body)}. "
            "Defect (c): numeric form narrows body but leaves sections empty (desync)."
        )
        assert result.sections, "result.sections must be non-empty for a resolved numeric section."

    def test_regex_section_keeps_sections_in_sync_with_body(self, mocker: MockerFixture) -> None:
        """section='/Impact.*/' (regex) narrows body AND populates sections in sync.

        RED: body becomes the Impact Radius slice, sections stays {}.
        """
        result = _view(mocker, _SYNC_BODY, "/Impact.*/")

        assert result.section_filter_miss is False, "regex '/Impact.*/' must match the Impact Radius header."
        assert "## Impact Radius" in result.body, f"body must be the Impact Radius slice; got {result.body[:60]!r}."
        assert set(result.sections) == set(_body_section_names(result.body)), (
            "result.sections must mirror the narrowed body for the regex form. "
            f"sections={sorted(result.sections)} body_headers={_body_section_names(result.body)}."
        )
        assert set(result.sections) == {"Impact Radius"}, (
            f"only the matched section's metadata must be present; got {sorted(result.sections)}."
        )

    def test_substring_section_multi_match_keeps_sections_in_sync(self, mocker: MockerFixture) -> None:
        """section='Issue' (substring) matches two headers; sections holds both in sync.

        RED: body holds both 'Issue Classification' and 'Issue Triage' slices, but
        sections is {} because neither header name equals 'Issue' exactly.
        """
        result = _view(mocker, _SYNC_BODY, "Issue")

        assert result.section_filter_miss is False, "substring 'Issue' matches two headers; must not miss."
        body_headers = _body_section_names(result.body)
        assert body_headers == ["Issue Classification", "Issue Triage"], (
            f"body must contain both matched sections in document order; got {body_headers}."
        )
        assert set(result.sections) == set(body_headers), (
            "result.sections must contain ALL matched sections, in sync with the body. "
            f"sections={sorted(result.sections)} body_headers={body_headers}. "
            "Defect (c): substring form narrows body but leaves sections empty (desync)."
        )

    def test_exact_name_section_stays_in_sync(self, mocker: MockerFixture) -> None:
        """section='RT-ICA' (exact name) keeps body and sections in sync (regression guard).

        The exact-name form already stays in sync today; this guards the fix from
        regressing the one form that previously worked.
        """
        result = _view(mocker, _SYNC_BODY, "RT-ICA")

        assert result.section_filter_miss is False, "exact name 'RT-ICA' must match."
        assert "## RT-ICA" in result.body, f"body must be the RT-ICA slice; got {result.body[:60]!r}."
        assert set(result.sections) == set(_body_section_names(result.body)) == {"RT-ICA"}, (
            f"exact-name form must keep body and sections in sync; sections={sorted(result.sections)}."
        )

    def test_true_miss_empties_sections_and_sets_filter_miss(self, mocker: MockerFixture) -> None:
        """A genuine miss must empty sections AND set section_filter_miss=True.

        section='/zzz-nomatch/' resolves to no header under any form; the contract
        requires empty sections and the miss flag set (preserving miss behaviour).
        """
        result = _view(mocker, _SYNC_BODY, "/zzz-nomatch/")

        assert result.section_filter_miss is True, "an unresolvable section form must set section_filter_miss=True."
        assert result.sections == {}, f"a genuine miss must leave result.sections empty; got {sorted(result.sections)}."


# ---------------------------------------------------------------------------
# Code-review round (#2495): regex crash, miss+pagination empties, compact
# miss-signal, case/format drift, sections=[] normalisation, redundant gate
# branch, shared-slicer coverage.
# ---------------------------------------------------------------------------


class TestMalformedRegexDoesNotCrash:
    """Finding #1: a malformed ``/regex/`` must degrade, not raise ``re.error``."""

    _BODY = "## Alpha\n\nalpha body\n\n## Beta\n\nbeta body\n"

    def test_malformed_regex_does_not_raise(self) -> None:
        """section='/[/' (unbalanced char class) must not raise ``re.error``.

        RED (pre-fix): ``re.compile('[')`` raises an uncaught ``re.error`` that
        crashes ``backlog_view`` for raw GitHub bodies, where the delimited
        expression is untrusted caller input.
        """
        result = ViewItemResult()
        # Must not raise; degrades to a literal-substring interpretation.
        returned = _apply_body_section_filter(result, self._BODY, "/[/")

        assert isinstance(returned, str), "a malformed regex must still return a body string, never raise."
        # No header is literally named '[' so the substring fallback resolves nothing → miss.
        assert result.section_filter_miss is True, (
            "section='/[/' matches no header under the literal-substring fallback, so it must "
            "report a miss — not crash and not silently return the full body."
        )

    def test_malformed_regex_literal_substring_matches_named_header(self) -> None:
        """A malformed-regex expression that is a literal header substring still matches.

        ``/a[/`` is an invalid regex (unbalanced ``[``).  The degraded path treats the
        whole delimited expression literally — consistent with the regex-matched-nothing
        fallback, which also substring-matches the full ``/.../`` form so a header
        literally named like the expression stays reachable.  A header whose text
        contains ``/a[/`` must therefore match rather than miss.
        """
        body = "## weird /a[/ header\n\nbody one\n\n## Beta\n\nbody two\n"
        result = ViewItemResult()
        returned = _apply_body_section_filter(result, body, "/a[/")

        assert result.section_filter_miss is False, (
            "'/a[/' is a malformed regex; the degraded literal-substring fallback uses the full "
            "delimited expression, which is a substring of the '## weird /a[/ header' header, so "
            "it must match rather than miss (finding #1 graceful degradation)."
        )
        assert "/a[/ header" in returned, (
            f"degraded substring fallback must return the matching section; got {returned[:50]!r}."
        )


class TestSectionMissEmptiesBodyAndSections:
    """Findings #2 and #3: a section miss yields an EMPTY body and EMPTY sections."""

    def test_view_item_section_miss_with_limit_empties_body_and_sections(self, mocker: MockerFixture) -> None:
        """view_item(section='NOPE', limit=3) → miss True, body '' and sections {}.

        RED (pre-fix): the post-pagination metadata rebuild ran unconditionally and
        overwrote the empty sections dict (#2); the full unchanged body was paginated
        and returned, leaking item content (#3).
        """
        result = _view(mocker, _SYNC_BODY, "NOPE")
        # Re-run through view_item with a limit to exercise the pagination path.
        _patch_github_body(mocker, 2495, _SYNC_BODY)
        result = operations.view_item(selector="2495", include_content=True, section="NOPE", limit=3)

        assert result.section_filter_miss is True, "section='NOPE' matches no header — must report a miss."
        assert result.body == "", (
            f"a section miss must yield an EMPTY body (no leaked full-item content); got {result.body[:60]!r}. "
            "Finding #3."
        )
        assert result.sections == {}, (
            f"a section miss must yield EMPTY sections even with limit set; got {sorted(result.sections)}. "
            "Finding #2: the post-pagination rebuild must not overwrite the empty dict."
        )

    def test_view_item_section_typo_empties_body(self, mocker: MockerFixture) -> None:
        """view_item(section='typo', limit=5) → miss True and body empty (no leak)."""
        _patch_github_body(mocker, 2495, _SYNC_BODY)
        result = operations.view_item(selector="2495", include_content=True, section="typo", limit=5)

        assert result.section_filter_miss is True, "section='typo' matches no header — must report a miss."
        assert result.body == "", (
            f"section miss must not leak the full item body through pagination; got {result.body[:60]!r}."
        )


class TestCompactValidNamesNotReportedAsMiss:
    """Finding #4: include_content=False with VALID names must not report a miss."""

    def test_compact_valid_section_name_not_miss_and_metadata_filtered(self, mocker: MockerFixture) -> None:
        """backlog_view(summary=False, include_content=False, sections=['RT-ICA']).

        Compact mode carries no body and an empty sections dict — the inventory is in
        sections_metadata.  A VALID name must filter that inventory and must NOT set
        section_filter_miss.

        RED (pre-fix): dict_matched and body_matched are both False in compact mode, so
        a valid name was wrongly reported as section_filter_miss.
        """
        _patch_github_body(mocker, 2495, _SYNC_BODY)
        from backlog_core import server

        resp = asyncio.run(
            server.backlog_view(selector="2495", summary=False, include_content=False, sections=["RT-ICA"])
        )

        assert resp.get("section_filter_miss") is not True, (
            "a VALID section name in compact mode must NOT report section_filter_miss. "
            "Got keys: " + repr(sorted(resp)) + ".  Finding #4."
        )
        meta = _resp_metadata(resp)
        assert meta, "compact mode must return sections_metadata for a valid name."
        names = {str(entry.get("name", "")) for entry in meta}
        assert names == {"RT-ICA"}, (
            f"sections_metadata must be filtered to only the requested name; got {sorted(names)}."
        )

    def test_compact_invalid_section_name_reports_miss(self, mocker: MockerFixture) -> None:
        """An INVALID name in compact mode still reports a miss (no false negative)."""
        _patch_github_body(mocker, 2495, _SYNC_BODY)
        from backlog_core import server

        resp = asyncio.run(
            server.backlog_view(selector="2495", summary=False, include_content=False, sections=["DOES-NOT-EXIST"])
        )

        assert resp.get("section_filter_miss") is True, (
            "an invalid name in compact mode must still report section_filter_miss so the miss "
            "signal is not lost by the finding #4 fix."
        )


class TestStructuredKeyDriftStillDelivered:
    """Finding #5: dict matches but body header drifts → matched slice, not directory."""

    def test_structured_key_format_drift_returns_matched_not_directory(self, mocker: MockerFixture) -> None:
        """A YAML item whose structured keys differ in FORMAT from the body headers.

        Arrange a local YAML item whose structured section key is 'RT-ICA' while the
        rendered body header is formatted differently ('RT ICA'), so the structured
        ``sections`` dict matches the requested name but ``narrow_body_to_named_sections``
        finds no exact body header.  The matched narrowing must still be delivered (the
        body cleared so the matched ``sections`` fit the budget) rather than replaced by
        the over-budget directory.

        RED (pre-fix): the un-narrowed full body was retained, tripping the over-budget
        gate and returning the directory — defeating the explicit narrowing.
        """
        from backlog_core import operations as ops, server

        # Build a response dict directly to exercise _filter_view_sections in isolation,
        # avoiding GitHub-enrichment coupling: structured sections dict has the key, but
        # the body header text drifts so the exact-name body match misses.
        big = "padding line.\n" * 4000  # ~56k chars → un-narrowed body is over budget
        result = ops.ViewItemResult(
            number=2495,
            title="drift",
            body=f"## RT ICA\n\n{big}",
            sections={"RT-ICA": ops._SectionMetadata(num_entries=1, num_struck=0, entries=[])},
        )
        response = result.model_dump()
        filtered = server._filter_view_sections(response, ["RT-ICA"], result)

        assert filtered.get("section_filter_miss") is not True, (
            "the structured 'RT-ICA' key matched, so this is NOT a miss even though the body "
            "header text drifted. Finding #5."
        )
        filtered_sections = filtered.get("sections")
        assert isinstance(filtered_sections, dict), "filtered response 'sections' must be a dict."
        assert "RT-ICA" in filtered_sections, "the matched structured section must be retained."
        assert filtered.get("body") == "", (
            "when the structured dict matched but the body header drifted, the un-narrowed body "
            "must be cleared so the matched narrowing fits the budget instead of tripping the "
            f"over-budget gate; got body of {len(str(filtered.get('body', '')))} chars. Finding #5."
        )


class TestEmptySectionsListBehavesLikeNone:
    """Finding #6: sections=[] must behave identically to sections=None."""

    def test_empty_sections_list_matches_none_behaviour(self, mocker: MockerFixture) -> None:
        """backlog_view(summary=False, sections=[]) == backlog_view(summary=False).

        sections=[] must not empty the sections dict, must not disable the heuristic,
        and must not report a miss — it is "no section filter".
        """
        _patch_github_body(mocker, 2495, _SYNC_BODY)
        from backlog_core import server

        resp_empty = asyncio.run(server.backlog_view(selector="2495", summary=False, sections=[]))
        _patch_github_body(mocker, 2495, _SYNC_BODY)
        resp_none = asyncio.run(server.backlog_view(selector="2495", summary=False, sections=None))

        assert resp_empty.get("section_filter_miss") is not True, (
            "sections=[] must not report a miss — it is equivalent to no filter. Finding #6."
        )
        assert resp_empty.get("body") == resp_none.get("body"), (
            "sections=[] must return the same body as sections=None (no narrowing applied)."
        )
        assert sorted(resp_empty.get("sections", {})) == sorted(resp_none.get("sections", {})), (
            "sections=[] must leave the sections dict identical to sections=None — it must not empty it."
        )


class TestUnboundedOverBudgetStillReturnsDirectory:
    """Finding #7: removing the body-chars branch must not regress the default gate."""

    def test_unbounded_over_budget_default_returns_directory(self, mocker: MockerFixture) -> None:
        """summary=False with NO narrowing on a huge body still returns the directory.

        Guards the finding #7 simplification: the unconditional token-count check must
        still gate an unbounded over-budget default call to the compact directory.
        """
        _patch_github_body(mocker, 2495, _OVER_BUDGET_BODY)
        from backlog_core import server

        resp = asyncio.run(server.backlog_view(selector="2495", summary=False))

        assert resp.get("_over_budget") is True, (
            "an unbounded over-budget default call (no section/sections/offset/limit) must still "
            "return the compact over-budget directory after the body-chars heuristic removal. "
            "Got keys: " + repr(sorted(resp)) + ".  Finding #7."
        )


class TestCommaSectionFormOnRawBody:
    """Finding 8/10 coverage gap: comma index form on raw GitHub bodies."""

    _BODY = "## Alpha\n\nalpha body\n\n## Beta\n\nbeta body\n\n## Gamma\n\ngamma body\n\n## Delta\n\ndelta body\n"

    def test_comma_indices_select_named_sections_in_order(self) -> None:
        """section='0,2' selects Alpha and Gamma in document order on a raw body."""
        result = ViewItemResult()
        returned = _apply_body_section_filter(result, self._BODY, "0,2")

        assert result.section_filter_miss is False, "section='0,2' (comma indices) must resolve, not miss."
        assert "## Alpha" in returned, f"comma form must include index 0 (Alpha); got {returned[:60]!r}."
        assert "## Gamma" in returned, f"comma form must include index 2 (Gamma); got {returned[:60]!r}."
        assert "## Beta" not in returned, "comma form '0,2' must exclude index 1 (Beta)."
        assert returned.find("## Alpha") < returned.find("## Gamma"), (
            "comma-selected sections must be concatenated in document order."
        )


class TestNarrowBodyToNamedSectionsUnit:
    """Finding 8/10: direct unit coverage for narrow_body_to_named_sections."""

    _BODY = "## Alpha\n\nalpha body\n\n## Beta\n\nbeta body\n\n## Gamma\n\ngamma body\n"

    def test_no_match_returns_body_unchanged_and_false(self) -> None:
        """No matching name → (body, False) with body returned unchanged."""
        narrowed, matched = operations.narrow_body_to_named_sections(self._BODY, ["Nonexistent"])

        assert matched is False, "no requested name matched — matched flag must be False."
        assert narrowed == self._BODY, "on a no-match the body must be returned unchanged (no content loss)."

    def test_case_insensitive_exact_name_match(self) -> None:
        """Names match case-insensitively against ``## ``/``### `` headers."""
        narrowed, matched = operations.narrow_body_to_named_sections(self._BODY, ["bEtA"])

        assert matched is True, "case-insensitive exact name 'bEtA' must match the '## Beta' header."
        assert "## Beta" in narrowed, f"narrowed body must contain the matched Beta section; got {narrowed[:40]!r}."
        assert "## Alpha" not in narrowed, "narrowed body must exclude non-requested sections."

    def test_multiple_names_kept_in_document_order(self) -> None:
        """Matched sections are concatenated in DOCUMENT order, not request order."""
        # Request Gamma before Alpha; result must still be Alpha-then-Gamma (document order).
        narrowed, matched = operations.narrow_body_to_named_sections(self._BODY, ["Gamma", "Alpha"])

        assert matched is True, "both names exist — matched must be True."
        assert narrowed.find("## Alpha") < narrowed.find("## Gamma"), (
            "matched sections must follow document order regardless of request order."
        )
        assert "## Beta" not in narrowed, "the non-requested Beta section must be excluded."
