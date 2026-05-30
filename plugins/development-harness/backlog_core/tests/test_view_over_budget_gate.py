"""G2 — Over-budget gate honouring narrowing, directory fallback, token measurement (#2495).

Covers defect (a): the over-budget gate must not suppress explicitly requested
narrowing (section= / sections= / offset+limit), and the measurement must
correctly count de-duplicated and cleared-body payloads.

Test classes:
- ``TestOverBudgetGateHonoursNarrowing`` — gate delivers requested slice on large items
- ``TestReviewRoundContract`` — M1 fallback, substring widening, m1 no-match signal
- ``TestEmptySectionsListBehavesLikeNone`` — sections=[] == sections=None (finding #6)
- ``TestUnboundedOverBudgetStillReturnsDirectory`` — default gate not regressed (finding #7)
- ``TestOverBudgetMeasurementCountsClearedBodySoleContent`` — cleared-body measurement (Codex P2)

Test naming: every test contains ``over_budget`` or ``numeric_section`` so
``pytest -k "over_budget or numeric_section"`` selects the whole #2495 suite.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from backlog_core import operations
from backlog_core.models import SectionEntryDict, ViewItemResult
from backlog_core.operations import _apply_body_section_filter
from backlog_core.tests._view_test_helpers import _HUGE_SINGLE, _OVER_BUDGET_BODY, _patch_github_body, _resp_body
from backlog_core.tests.conftest import REAL_CL100K_AVAILABLE

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# These tests assert over/under the token budget using real cl100k_base counts.
# The offline stub (conftest) lacks real BPE compression, so skip them when the
# real encoding is unavailable rather than fail on miscalibrated counts (PR #2496).
pytestmark = pytest.mark.skipif(
    not REAL_CL100K_AVAILABLE,
    reason="token-budget tests require the real cl100k_base encoding (offline stub lacks BPE compression)",
)

# ---------------------------------------------------------------------------
# Local constants — used only within this file
# ---------------------------------------------------------------------------

# A many-section body where the structured ``sections`` dict stays > token budget
# even after ``offset``/``limit`` paginate the body.  This reproduces the real
# #2438 offset/limit failure: pagination narrows ``result.body`` (to a handful of
# chars) but NOT ``result.sections``, so ``model_dump()`` still overflows and the
# over-budget gate discards the requested page.
_PAGER_FILLER = "Lorem ipsum dolor sit amet consectetur adipiscing. " * 70
_MANY_SECTION_BODY = "".join(f"## Section {i}\n\n{_PAGER_FILLER}\n\n" for i in range(8))

# A body whose SINGLE section's own content exceeds _VIEW_TOKEN_BUDGET.
_SINGLE_OVER_BUDGET_BODY = f"## Tiny\n\nshort intro\n\n## Huge\n\n{_HUGE_SINGLE}\n\n"

# A ``## ``-headed body whose OWN prose (the body field alone, before any sections
# duplication) genuinely exceeds _VIEW_TOKEN_BUDGET.  Distinct from _OVER_BUDGET_BODY,
# whose body-alone token count sits UNDER the budget and is now (correctly, finding #4)
# delivered inline — so the unbounded-directory test needs a body that is genuinely too
# large on its own to keep exercising the gate.
_GENUINELY_OVER_BUDGET_BODY = f"## Story\n\nintro\n\n## Huge One\n\n{_HUGE_SINGLE}\n\n## Huge Two\n\n{_HUGE_SINGLE}\n\n"

# A body with two headers sharing a common substring ('Section') plus 'Other',
# to pin substring-widening (multiple matches concatenated in document order).
_SUBSTRING_BODY = (
    "## Section 1\n\nfirst widget body\n\n## Section 2\n\nsecond widget body\n\n## Other\n\nunrelated body\n"
)

# A body with a header literally named '2' (three headers => index 2 is in range).
_LITERAL_INDEX_BODY = (
    "## Alpha\n\nalpha body\n\n## 2\n\nthe literally-named two section body\n\n## Gamma\n\ngamma body\n"
)

# A per-entry ``content`` blob large enough that, when carried alone in the
# structured ``sections`` dict (body cleared), the serialised response exceeds
# _VIEW_TOKEN_BUDGET (4000 tokens ~= 16k chars).  ~33k chars / ~5.5k tokens.
_DRIFT_CONTENT = "Lorem ipsum dolor sit amet consectetur adipiscing elit. " * 600


# ---------------------------------------------------------------------------
# Local helper
# ---------------------------------------------------------------------------


def _drift_view_result() -> ViewItemResult:
    """Build the structured-key drift ``ViewItemResult`` for the under-count repro.

    The structured ``sections`` dict is keyed ``RT-ICA`` (matching a
    ``sections=['RT-ICA']`` request) and carries a large per-entry ``content``.
    The rendered body header drifts (``## RT ICA`` — a SPACE where the key uses a
    HYPHEN), so ``_filter_view_sections`` matches the structured key but finds no
    exact body header and CLEARS the body (finding #5).  After clearing, the
    per-entry ``content`` under ``sections`` is the ONLY delivered copy of the
    content, and the serialised response exceeds _VIEW_TOKEN_BUDGET.

    Returns:
        A ``ViewItemResult`` modelling the structured-key drift scenario.
    """
    return ViewItemResult(
        number=2495,
        title="drift",
        status="status:groomed",
        body=f"## RT ICA\n\n{_DRIFT_CONTENT}",
        sections={
            "RT-ICA": operations._SectionMetadata(
                num_entries=1, num_struck=0, entries=[SectionEntryDict(id="e1", struck=False, content=_DRIFT_CONTENT)]
            )
        },
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
# substring widening, over-budget-after-narrowing, and the sections=[...] miss signal.
# ---------------------------------------------------------------------------


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
# Finding #6: sections=[] must behave identically to sections=None
# ---------------------------------------------------------------------------


class TestEmptySectionsListBehavesLikeNone:
    """Finding #6: sections=[] must behave identically to sections=None."""

    def test_empty_sections_list_matches_none_behaviour(self, mocker: MockerFixture) -> None:
        """backlog_view(summary=False, sections=[]) == backlog_view(summary=False).

        sections=[] must not empty the sections dict, must not disable the heuristic,
        and must not report a miss — it is "no section filter".
        """
        SYNC_BODY = (
            "## Story\n\nstory body\n\n"
            "## Description\n\ndescription body\n\n"
            "## RT-ICA\n\nrt-ica body\n\n"
            "## Issue Classification\n\nclassification body\n\n"
            "## Issue Triage\n\ntriage body\n\n"
            "## Impact Radius\n\nimpact body\n"
        )
        _patch_github_body(mocker, 2495, SYNC_BODY)
        from backlog_core import server

        resp_empty = asyncio.run(server.backlog_view(selector="2495", summary=False, sections=[]))
        _patch_github_body(mocker, 2495, SYNC_BODY)
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


# ---------------------------------------------------------------------------
# Finding #7: removing the body-chars branch must not regress the default gate
# ---------------------------------------------------------------------------


class TestUnboundedOverBudgetStillReturnsDirectory:
    """Finding #7: removing the body-chars branch must not regress the default gate."""

    def test_unbounded_over_budget_default_returns_directory(self, mocker: MockerFixture) -> None:
        """summary=False with NO narrowing on a genuinely-too-large body returns the directory.

        Guards the finding #7 simplification AND the finding #4 measurement change: an
        unbounded body whose OWN content genuinely exceeds _VIEW_TOKEN_BUDGET must still
        gate to the compact directory.  The body field alone is over budget here, so the
        de-duplicated measurement (finding #4 — body counted once, per-entry content not
        double-counted) is still over budget and the directory is returned.
        """
        from backlog_core import server

        # Premise: the body field ALONE exceeds the budget, so this is a genuine over-budget
        # case independent of any sections-dict content duplication (finding #4).
        body_tokens = server._token_count(_GENUINELY_OVER_BUDGET_BODY)
        assert body_tokens > server._VIEW_TOKEN_BUDGET, (
            f"premise: the body alone must exceed _VIEW_TOKEN_BUDGET; got {body_tokens} tokens. "
            "A genuinely-too-large unbounded body must still gate after the finding #4 measurement change."
        )
        _patch_github_body(mocker, 2495, _GENUINELY_OVER_BUDGET_BODY)

        resp = asyncio.run(server.backlog_view(selector="2495", summary=False))

        assert resp.get("_over_budget") is True, (
            "an unbounded genuinely-over-budget default call (no section/sections/offset/limit) must "
            "still return the compact over-budget directory.  Got keys: " + repr(sorted(resp)) + "."
        )

    def test_unbounded_large_but_compressible_body_delivered_inline(self, mocker: MockerFixture) -> None:
        """A large-but-COMPRESSIBLE unbounded body is delivered inline, not as a directory.

        m2 (#2495): the companion test above uses prose filler that trips BOTH the
        removed char heuristic (>16000 chars) AND the token gate, so it never exercises
        the boundary where the two diverge.  This test locks the intended NEW behaviour:
        a body of 20000 identical characters is >16000 chars (the old char heuristic would
        have forced the over-budget directory) but its token count is far under
        ``_VIEW_TOKEN_BUDGET`` (a long run of one repeated character compresses to very
        few tokens).  Because the authoritative gate is now the precise token count of the
        whole serialised response, the body must be delivered INLINE — proving the char
        heuristic removal changed behaviour for compressible bodies (No Invented Limits).

        The body is header-free (no ``## ``/``### `` headers) on purpose: a header would
        make ``_build_sections_metadata`` parse the run into a section entry, duplicating
        the content inside the serialised ``sections`` dict and pushing the *whole
        response* over budget even though the body alone is compressible.  A header-free
        body keeps the section dict empty so the token gate measures the content once.
        """
        compressible_body = "a" * 20000
        _patch_github_body(mocker, 2495, compressible_body)
        from backlog_core import server

        # Guard the premise: >16000 chars (old heuristic would gate) but the WHOLE serialised
        # response is under the token budget — measured exactly as the gate measures it.
        assert len(compressible_body) > 16000, "premise: the body must exceed the old 16000-char heuristic threshold."
        full_response = server._models.ViewItemResult(number=2495, title="Issue 2495", body=compressible_body)
        premise_tokens = server._token_count(server._json.dumps(full_response.model_dump()))
        assert premise_tokens <= server._VIEW_TOKEN_BUDGET, (
            f"premise: the serialised header-free compressible response must be <= _VIEW_TOKEN_BUDGET "
            f"tokens; got {premise_tokens}.  If this fails the test no longer exercises the "
            "heuristic/token divergence boundary (a header would duplicate the run into the sections dict)."
        )

        resp = asyncio.run(server.backlog_view(selector="2495", summary=False))

        assert resp.get("_over_budget") is not True, (
            "a large-but-compressible body (>16000 chars but <= token budget) must be delivered INLINE — "
            "the removed char heuristic would have wrongly forced the over-budget directory.  "
            "Got keys: " + repr(sorted(resp)) + ".  m2 (#2495)."
        )
        body = _resp_body(resp)
        assert ("a" * 20000) in body, (
            "the full compressible body must be delivered inline without truncation (No Invented Limits)."
        )


# ---------------------------------------------------------------------------
# Codex P2 (#2495): cleared-body must not let the sole section copy escape the gate
# ---------------------------------------------------------------------------


class TestOverBudgetMeasurementCountsClearedBodySoleContent:
    """Codex P2 (#2495): a cleared body must not let the sole section copy escape the gate.

    The finding #4 measurement blanks each section's per-entry ``content`` before
    token-counting on the premise that the content is duplicated in ``body``.  On
    the structured-key drift path ``_filter_view_sections`` CLEARS ``body``, so
    that premise fails: the per-entry ``content`` becomes the SOLE delivered copy.
    Blanking it then under-counts the payload and returns an over-budget response
    inline, defeating the budget guard.  The measurement must count the section
    content in full when ``body`` is empty.
    """

    def test_view_payload_token_count_counts_section_content_when_body_cleared(self) -> None:
        """``_view_payload_token_count`` must reflect the SOLE section copy when body is empty.

        RED (pre-fix): the helper blanks the per-entry ``content`` unconditionally,
        so a payload whose serialised form exceeds _VIEW_TOKEN_BUDGET is measured as
        a tiny structural skeleton well UNDER budget — the under-count.
        """
        from backlog_core import server

        result = _drift_view_result()
        response = result.model_dump()
        filtered = server._filter_view_sections(response, ["RT-ICA"], result)

        # Premise: the drift path cleared the body so the section content is the sole copy.
        assert filtered.get("body") == "", (
            "premise: the structured-key drift path must clear the body (finding #5) so the "
            f"section content is the sole delivered copy; got body of {len(str(filtered.get('body')))} chars."
        )
        verbatim_tokens = server._token_count(server._json.dumps(filtered))
        assert verbatim_tokens > server._VIEW_TOKEN_BUDGET, (
            "premise: the serialised drift payload (section content the sole copy) must EXCEED the "
            f"budget; got {verbatim_tokens} tokens.  If not, the test no longer exercises the under-count."
        )

        measured = server._view_payload_token_count(filtered)

        assert measured > server._VIEW_TOKEN_BUDGET, (
            "the over-budget measurement must count the per-entry section content in FULL when the "
            "body was cleared — it is the sole delivered copy, not a duplicate of the body.  Pre-fix "
            f"the helper blanked it unconditionally, under-counting to {measured} tokens (<= budget) "
            "and letting an over-budget payload escape inline.  Codex P2 (#2495)."
        )

    def test_over_budget_drift_section_returns_directory(self, mocker: MockerFixture) -> None:
        """backlog_view(sections=['RT-ICA']) on a drift item returns the over-budget directory.

        End-to-end: ``view_item`` yields the structured-key drift result; the body is
        cleared by ``_filter_view_sections`` and the sole section copy exceeds the
        budget.  The gate must return the compact over-budget directory, not the
        over-budget payload inline.

        RED (pre-fix): the under-counting measurement reported the payload under budget,
        so ``backlog_view`` returned the over-budget content inline with ``_over_budget``
        unset — defeating the budget guard.
        """
        from backlog_core import server

        mocker.patch.object(server.operations, "view_item", side_effect=lambda **_kwargs: _drift_view_result())

        resp = asyncio.run(server.backlog_view(selector="2495", summary=False, sections=["RT-ICA"]))

        assert resp.get("_over_budget") is True, (
            "the drift payload (body cleared, sole section copy over budget) must return the compact "
            "over-budget directory — the measurement must not under-count the sole delivered copy and "
            "let the over-budget payload through inline.  Got keys: " + repr(sorted(resp)) + ".  Codex P2 (#2495)."
        )
        assert resp.get("section_filter_miss") is not True, (
            "the structured 'RT-ICA' key matched the request, so this is NOT a section_filter_miss — "
            "only the budget gate fires here."
        )
