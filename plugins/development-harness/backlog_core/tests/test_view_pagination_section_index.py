"""G4 — Pagination, entry-block metadata, and ``## Sections`` index displacement (#2495).

Covers the ``section=None`` line-based pagination path and entry-block pagination:
the synthetic ``## Sections`` index must NOT consume the page budget, and paged
entry-block bodies must keep their describing section metadata in sync.

Test classes:
- ``TestOverBudgetMeasurementExcludesDuplicatedContent`` — under-budget body not gated
  by content-duplication in the sections dict (finding #4)
- ``TestPagedEntryBlockKeepsSectionMetadata`` — paged entry-block keeps section metadata
- ``TestSectionNoneLinePaginationNotDisplacedByIndex`` — M1: index must not displace page
- ``TestPagedSectionNoneIndexDoesNotTripOverBudget`` — Codex P2: paged section=None not
  displaced by a huge whole-item index

Test naming: every test contains ``over_budget`` or ``numeric_section`` so
``pytest -k "over_budget or numeric_section"`` selects the whole #2495 suite.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from backlog_core import operations
from backlog_core.tests._view_test_helpers import _patch_github_body, _resp_body
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
# Local helpers and constants
# ---------------------------------------------------------------------------


def _entry_block_body_under_budget_with_dup_overflow() -> str:
    """Build a ``## ``-headed entry-block body for the finding #4 boundary.

    The body field's own token count sits comfortably UNDER _VIEW_TOKEN_BUDGET,
    but ``_build_sections_metadata`` copies each entry's content into the
    structured ``sections`` dict, so the verbatim full-response token count
    (body + duplicated content) exceeds the budget.  The de-duplicated
    measurement (finding #4) must keep this body inline.

    Returns:
        A multi-entry ``## Log`` body whose verbatim serialisation overflows
        the token budget but whose de-duplicated measurement does not.
    """
    filler = "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod. "
    entries = "\n\n".join(f"<div><sub>2026-05-{i + 1:02d}</sub>\n\n{filler * 70}\n</div>" for i in range(3))
    return f"## Log\n\n{entries}\n"


# A header-only, entry-block-FREE 4-section body (plain GitHub-issue prose, no
# ``<div><sub>…</sub></div>`` blocks) so ``_paginate_body_result`` takes the
# LINE-BASED branch.  Raw line layout (0-based, 15 lines):
#   0 '## Alpha' 1 '' 2 'aaa' 3 '' 4 '## Beta' 5 '' 6 'bbb' 7 ''
#   8 '## Gamma' 9 '' 10 'ggg' 11 '' 12 '## Delta' 13 '' 14 'ddd'
_HEADER_ONLY_BODY = "## Alpha\n\naaa\n\n## Beta\n\nbbb\n\n## Gamma\n\nggg\n\n## Delta\n\nddd\n"
_HEADER_ONLY_RAW_LINE_COUNT = len(_HEADER_ONLY_BODY.splitlines())  # 15 raw body lines


def _many_heading_body(n_headings: int) -> str:
    """Build an entry-block-free raw body whose ``## Sections`` index is huge.

    Each heading carries a deliberately long descriptive name so the generated
    ``## Sections`` index (one line per heading) exceeds _VIEW_TOKEN_BUDGET on its
    own, while each section's prose body is a few tokens — so any small page
    (e.g. ``limit=2``) is well under budget.  No ``<div><sub>...</sub></div>``
    entry blocks, forcing the LINE-BASED pagination branch.

    Args:
        n_headings: Number of section headings to generate.

    Returns:
        A markdown body string with *n_headings* ``## Section NNN …`` headers.
    """
    return "\n".join(
        f"## Section {i:03d} with a deliberately long descriptive heading to inflate the index token cost"
        f"\n\nshort body {i}\n"
        for i in range(n_headings)
    )


# ---------------------------------------------------------------------------
# Finding #4 (#2495): gate must measure the DELIVERED payload without
# double-counting per-entry content the body already carries once.
# ---------------------------------------------------------------------------


class TestOverBudgetMeasurementExcludesDuplicatedContent:
    """Finding #4: a body under budget on its own must not be gated by content duplication."""

    def test_headed_under_budget_body_delivered_inline_despite_sections_dup(self, mocker: MockerFixture) -> None:
        """A ``## ``-headed entry-block body under budget on its own is delivered INLINE.

        RED (pre-fix): the over-budget gate serialises the whole ``full_response`` —
        including the ``sections`` dict whose per-entry ``content`` DUPLICATES the body
        text — and measures THAT.  The duplicated content pushes a body that is
        comfortably under ``_VIEW_TOKEN_BUDGET`` on its own over the budget, so the gate
        wrongly returns the metadata-only over-budget directory.

        After the fix the gate measures the de-duplicated payload (body counted once,
        per-entry ``content`` not double-counted), so the body is delivered inline.
        """
        from backlog_core import server

        body = _entry_block_body_under_budget_with_dup_overflow()

        # Premise: body-alone is under budget, but the verbatim full response (with the
        # content-duplicating sections dict) is over budget — the exact finding #4 trap.
        _patch_github_body(mocker, 2495, body)
        result = operations.view_item(selector="2495", include_content=True)
        full_response = result.model_dump()
        body_tokens = server._token_count(str(full_response["body"]))
        verbatim_tokens = server._token_count(server._json.dumps(full_response))
        assert body_tokens <= server._VIEW_TOKEN_BUDGET, (
            f"premise: the body alone must be UNDER budget; got {body_tokens} tokens."
        )
        assert verbatim_tokens > server._VIEW_TOKEN_BUDGET, (
            f"premise: the verbatim full response (with duplicated per-entry content) must EXCEED "
            f"the budget so the old gate would trip; got {verbatim_tokens} tokens."
        )

        _patch_github_body(mocker, 2495, body)
        resp = asyncio.run(server.backlog_view(selector="2495", summary=False))

        assert resp.get("_over_budget") is not True, (
            "a ``## ``-headed body comfortably under budget on its own must be delivered INLINE; the "
            "over-budget gate must not count the per-entry content the body already carries once. "
            "Got keys: " + repr(sorted(resp)) + ".  Finding #4."
        )
        delivered = _resp_body(resp)
        assert "Lorem ipsum" in delivered, "the body content must be delivered inline, not replaced by the directory."


# ---------------------------------------------------------------------------
# Finding #5 (#2495): paginating an entry-block section must keep result.sections
# describing the paged section (non-empty), not desync to {}.
# ---------------------------------------------------------------------------


class TestPagedEntryBlockKeepsSectionMetadata:
    """Finding #5: paged entry-block body must keep its describing section metadata."""

    _LOG_BODY = (
        "## Log\n\n"
        "<div><sub>2026-05-01</sub> first entry content</div>\n\n"
        "<div><sub>2026-05-02</sub> second entry content</div>\n"
    )

    def test_paged_entry_block_section_metadata_non_empty(self, mocker: MockerFixture) -> None:
        """view_item(section=None, limit=1) on a ``## Log`` entry-block body keeps sections.

        RED (pre-fix): ``_paginate_body_result`` rendered the page as a bare run of
        ``<div><sub>…</sub></div>`` blocks with the ``## Log`` header stripped, so the
        downstream ``_build_sections_metadata`` rebuild parsed a headerless page and set
        ``result.sections = {}`` — a valid page returned the requested entry but EMPTY
        section metadata, breaking the body/metadata sync contract.

        After the fix the page retains its owning ``## Log`` header, so the metadata
        rebuild describes the paged section: ``result.sections`` is non-empty, keyed by
        the real ``Log`` section, and ``num_entries`` reflects the single paged entry.
        """
        _patch_github_body(mocker, 2495, self._LOG_BODY)
        result = operations.view_item(selector="2495", include_content=True, section=None, limit=1)

        assert result.sections, (
            "a paged entry-block section must keep NON-EMPTY section metadata; got {}.  Finding #5: "
            "the headerless paged page rebuilt section metadata as empty."
        )
        assert set(result.sections) == {"Log"}, (
            f"result.sections must be keyed by the real paged section 'Log'; got {sorted(result.sections)}."
        )
        log_meta = result.sections["Log"]
        assert log_meta.get("num_entries") == 1, (
            f"the paged section metadata must describe the single paged entry; got {log_meta.get('num_entries')}."
        )
        assert "Sections" not in result.sections, (
            f"the paged section metadata must not carry a spurious 'Sections' key; got {sorted(result.sections)}."
        )
        # The requested page content is preserved (no regression of entry-block pagination).
        assert "first entry content" in result.body, "the first entry must be on the page."
        assert "second entry content" not in result.body, "the second entry must be excluded by limit=1."
        assert result.body_truncated is True, "one of two entries shown — body_truncated must be True."
        assert result.body_total_entries == 2, (
            f"entry-block totals must reflect both entries; got {result.body_total_entries}."
        )

    def test_paged_offset_into_second_section_keeps_correct_metadata(self, mocker: MockerFixture) -> None:
        """offset paging across two entry-block sections keeps metadata for the paged section.

        A two-section entry-block body (``## Alpha`` with one entry, ``## Beta`` with one
        entry) paged with offset=1/limit=1 must land on the Beta entry and report
        ``result.sections == {'Beta'}`` — proving the owning header is re-attached per
        entry, not assumed to be the first section.
        """
        two_section_body = (
            "## Alpha\n\n"
            "<div><sub>2026-05-01</sub> alpha entry</div>\n\n"
            "## Beta\n\n"
            "<div><sub>2026-05-02</sub> beta entry</div>\n"
        )
        _patch_github_body(mocker, 2495, two_section_body)
        result = operations.view_item(selector="2495", include_content=True, section=None, offset=1, limit=1)

        assert set(result.sections) == {"Beta"}, (
            f"offset=1/limit=1 lands on the Beta entry; result.sections must be {{'Beta'}}; "
            f"got {sorted(result.sections)}.  Finding #5: owning header must be re-attached per entry."
        )
        assert "beta entry" in result.body, "the paged body must carry the Beta entry content."
        assert "alpha entry" not in result.body, "offset=1 must skip the Alpha entry."

    def test_paged_subsection_preserves_header_level(self, mocker: MockerFixture) -> None:
        """A ``### `` subsection paged with limit=1 keeps its ``### `` level in the page.

        Re-attaching the owning header must reproduce the original ``## ``/``### `` level,
        not flatten a subsection to ``## ``.  Metadata is keyed by name regardless of
        level, so this guards display fidelity rather than the sync contract.
        """
        sub_body = (
            "### Detail\n\n"
            "<div><sub>2026-05-01</sub> first detail</div>\n\n"
            "<div><sub>2026-05-02</sub> second detail</div>\n"
        )
        _patch_github_body(mocker, 2495, sub_body)
        result = operations.view_item(selector="2495", include_content=True, section=None, limit=1)

        assert "### Detail" in result.body, f"the paged subsection must keep its '### ' level; got {result.body!r}."
        assert set(result.sections) == {"Detail"}, (
            f"the paged subsection metadata must be keyed by name 'Detail'; got {sorted(result.sections)}."
        )


# ---------------------------------------------------------------------------
# M1 (#2495): on the ``section=None`` line-based pagination path the synthetic
# ``## Sections`` index must NOT consume the page budget, and ``result.sections``
# must reflect the real sections of the returned page — not a spurious
# ``Sections`` key.  Regression introduced by commit d7abdee.
#
# Per the M1 contract the index MAY still appear in the response body; the
# requirements being locked are (1) the index must not consume the page budget
# (real content lands on the page and ``body_total_lines`` reflects the RAW body,
# not the index-inflated line count) and (2) ``result.sections`` must reflect the
# real sections on the returned page — never a spurious ``Sections`` key built
# from the synthetic index.
# ---------------------------------------------------------------------------


class TestSectionNoneLinePaginationNotDisplacedByIndex:
    """M1: the ``## Sections`` index must not displace real content on the page."""

    def test_section_none_limit_returns_real_first_section_not_index(self, mocker: MockerFixture) -> None:
        """view_item(section=None, limit=3) returns the real first section, not the index.

        RED (pre-fix, d7abdee): the synthetic ``## Sections`` index was prepended to
        the body BEFORE line-based pagination, so the first 3 lines were the index
        lines ``## Sections`` / ``[0] Alpha (…)`` / ``[1] Beta (…)``.  ``result.body``
        held only those index lines (the real ``## Alpha`` / ``aaa`` content was
        displaced off the page) and the metadata rebuild keyed it ``{'Sections': …}``.

        After the fix: pagination runs on the RAW body, so the first page carries the
        real Alpha header + content and ``result.sections`` carries the real section
        name ``Alpha`` — never the synthetic ``Sections`` key.  ``body_total_lines``
        reflects the RAW 15-line body, proving the index did not inflate the page
        budget.
        """
        _patch_github_body(mocker, 2495, _HEADER_ONLY_BODY)
        result = operations.view_item(selector="2495", include_content=True, section=None, limit=3)

        assert result.section_filter_miss is False, "section=None is not a narrowing request — must not miss."
        # (a) The returned page carries the REAL first section content, not (only) the index.
        assert "## Alpha" in result.body, (
            f"the first page must contain the real '## Alpha' section header; got {result.body[:80]!r}. "
            "M1: the synthetic index displaced the real content off the page."
        )
        assert "aaa" in result.body, (
            f"the first page must contain the real first-section content 'aaa'; got {result.body[:80]!r}. "
            "M1: pre-fix the index lines consumed the whole limit=3 page."
        )
        # (b) result.sections reflects the REAL first section, not a spurious 'Sections' key.
        assert "Sections" not in result.sections, (
            f"result.sections must not contain a spurious 'Sections' key built from the synthetic "
            f"index; got {sorted(result.sections)}.  M1 regression."
        )
        assert "Alpha" in result.sections, (
            f"result.sections must carry the real first section name 'Alpha'; got {sorted(result.sections)}."
        )
        # (c) The index must not inflate the page budget: totals reflect the RAW body.
        assert result.body_total_lines == _HEADER_ONLY_RAW_LINE_COUNT, (
            f"body_total_lines must reflect the RAW {_HEADER_ONLY_RAW_LINE_COUNT}-line body, not the "
            f"index-inflated count; got {result.body_total_lines}.  M1: the index must not consume the budget."
        )

    def test_section_none_offset_limit_returns_real_paged_section_not_index(self, mocker: MockerFixture) -> None:
        """view_item(section=None, offset=6, limit=5) pages real lines, not index lines.

        Separate ``offset>0`` case (the reviewer asked for both a limit and an offset
        case).  offset=6 skips the first six RAW lines (Alpha + Beta) and the page lands
        on the Gamma section; limit=5 keeps it short while still reaching the Gamma content.

        RED (pre-fix): the prepended index added lines to the front, so the offset
        skipped index lines instead of real body lines and the page never reached the
        real Gamma content (``result.sections`` was the wrong section).  After the fix
        the offset/limit apply to the RAW body lines, the page carries the real Gamma
        header + content, ``result.sections == {'Gamma'}``, and ``body_total_lines``
        reflects the RAW 15-line body.
        """
        _patch_github_body(mocker, 2495, _HEADER_ONLY_BODY)
        result = operations.view_item(selector="2495", include_content=True, section=None, offset=6, limit=5)

        assert result.section_filter_miss is False, "section=None is not a narrowing request — must not miss."
        assert "## Gamma" in result.body, (
            f"offset=6/limit=5 on the RAW body must reach the real '## Gamma' section; got {result.body[:80]!r}. "
            "M1: prepended index lines shifted the offset off the real content."
        )
        assert "ggg" in result.body, (
            f"the paged body must carry the real Gamma content 'ggg'; got {result.body[:80]!r}."
        )
        assert "Sections" not in result.sections, (
            f"result.sections must not carry a spurious 'Sections' key; got {sorted(result.sections)}.  M1 regression."
        )
        assert set(result.sections) == {"Gamma"}, (
            f"result.sections must reflect only the real paged section 'Gamma'; got {sorted(result.sections)}. "
            "M1: pre-fix the index displaced the page so sections held the wrong section."
        )
        assert result.body_total_lines == _HEADER_ONLY_RAW_LINE_COUNT, (
            f"body_total_lines must reflect the RAW {_HEADER_ONLY_RAW_LINE_COUNT}-line body; "
            f"got {result.body_total_lines}.  M1: the index must not inflate the line budget."
        )

    def test_entry_block_body_pagination_unchanged_by_index_deferral(self, mocker: MockerFixture) -> None:
        """Entry-block bodies still paginate by entry block — the M1 fix is path-scoped.

        The ``## Sections`` index is plain text with no ``<div><sub>…</sub></div>``
        entry blocks, so ``parse_entries`` ignores it.  This test proves the entry-block
        pagination geometry is unchanged by the index deferral: a two-entry-block body
        paged with limit=1 returns exactly the first entry block (the second excluded,
        ``body_truncated`` True) and ``result.sections`` never carries the synthetic
        'Sections' key.
        """
        entry_body = (
            "## Log\n\n"
            "<div><sub>2026-05-01</sub> first entry content</div>\n\n"
            "<div><sub>2026-05-02</sub> second entry content</div>\n"
        )
        _patch_github_body(mocker, 2495, entry_body)
        result = operations.view_item(selector="2495", include_content=True, section=None, limit=1)

        assert "first entry content" in result.body, (
            f"entry-block pagination with limit=1 must return the first entry block; got {result.body[:80]!r}."
        )
        assert "second entry content" not in result.body, (
            "entry-block pagination with limit=1 must exclude the second entry block."
        )
        assert result.body_truncated is True, "one of two entry blocks shown — body_truncated must be True."
        assert result.body_total_entries == 2, (
            f"entry-block totals must reflect the two real entry blocks; got {result.body_total_entries}."
        )
        assert "Sections" not in result.sections, (
            f"the entry-block path must not produce a spurious 'Sections' key; got {sorted(result.sections)}."
        )


# ---------------------------------------------------------------------------
# Codex P2 (#2495): the whole-item ``## Sections`` index must not be prepended to
# a PAGED ``section=None`` response.  For a raw body with many headings the index
# alone exceeds _VIEW_TOKEN_BUDGET; prepending it to the budgeted page trips the
# over-budget gate and discards the explicitly-requested page.
# ---------------------------------------------------------------------------


class TestPagedSectionNoneIndexDoesNotTripOverBudget:
    """Codex P2 (#2495): a paged ``section=None`` page must not be displaced by the index.

    The non-paged ``section=None`` path prepends a whole-item ``## Sections`` index
    (M1, e6191da).  For a raw body with many headings that index alone exceeds
    _VIEW_TOKEN_BUDGET.  Pre-fix the index was built on the paged path too and
    prepended to the post-pagination body, so an explicit small page
    (``offset``/``limit``) measured index+page > budget, tripped the over-budget
    gate, and returned the compact directory — dropping the page the caller asked
    for.  After the fix the index is omitted from paged responses and the page is
    delivered inline.
    """

    def test_paged_limit_delivers_page_inline_despite_huge_index(self, mocker: MockerFixture) -> None:
        """backlog_view(summary=False, limit=2) on a many-heading body returns the page.

        RED (pre-fix, e6191da): the whole-item ``## Sections`` index (built from the
        un-paginated body) is prepended to the tiny paged body; the index alone
        exceeds _VIEW_TOKEN_BUDGET so the over-budget gate fires and the caller
        receives the metadata-only directory (``_over_budget`` True, no ``body``)
        instead of the requested page.

        After the fix: the index is not built for paged responses, so the page
        (well under budget) is delivered inline with ``_over_budget`` unset.
        """
        from backlog_core import server

        body = _many_heading_body(400)

        # Premise: the generated index ALONE exceeds the budget, but a single small
        # page is far under it — the exact trap the fix addresses.
        index_tokens = server._token_count(operations._build_sections_index_from_body(body))
        assert index_tokens > server._VIEW_TOKEN_BUDGET, (
            f"premise: the ## Sections index alone must exceed _VIEW_TOKEN_BUDGET; got {index_tokens} tokens. "
            "If not, the many-heading body no longer reproduces the index-overflow trap."
        )

        _patch_github_body(mocker, 2495, body)
        resp = asyncio.run(server.backlog_view(selector="2495", summary=False, limit=2))

        assert resp.get("_over_budget") is not True, (
            "an explicit paged request (limit=2) must be delivered inline; backlog_view must NOT prepend "
            "the unbounded whole-item ## Sections index to the budgeted page and trip the over-budget gate. "
            "Got keys: " + repr(sorted(resp)) + ".  Codex P2 (#2495)."
        )
        body_out = _resp_body(resp)
        assert "## Section 000" in body_out, (
            f"the requested first page must carry the real first section content; got {body_out[:80]!r}."
        )
        assert "## Sections" not in body_out, (
            "the whole-item ## Sections index must NOT be prepended to a paged response — it is unbounded "
            f"and contradicts the paged scope; got a body starting {body_out[:60]!r}.  Codex P2 (#2495)."
        )
        # Page-scoped metadata is what the caller asked for and must be present in sync.
        meta_sections = resp.get("sections")
        assert isinstance(meta_sections, dict), (
            f"the paged response 'sections' metadata must be a dict; got {type(meta_sections).__name__}."
        )
        assert meta_sections, (
            "the paged response must carry NON-EMPTY page-scoped 'sections' metadata in sync with the body; "
            "got an empty dict."
        )
        assert "Sections" not in meta_sections, (
            f"the paged metadata must not carry a spurious 'Sections' key from the synthetic index; "
            f"got {sorted(meta_sections)}."
        )

    def test_paged_offset_delivers_page_inline_despite_huge_index(self, mocker: MockerFixture) -> None:
        """backlog_view(summary=False, offset=4, limit=2) on a many-heading body returns the page.

        Companion offset>0 case: the page lands deeper in the body and must still be
        delivered inline (not displaced by the unbounded whole-item index).
        """
        from backlog_core import server

        body = _many_heading_body(400)
        _patch_github_body(mocker, 2495, body)

        resp = asyncio.run(server.backlog_view(selector="2495", summary=False, offset=4, limit=2))

        assert resp.get("_over_budget") is not True, (
            "an explicit paged request with offset>0 must be delivered inline, not replaced by the "
            "over-budget directory.  Got keys: " + repr(sorted(resp)) + ".  Codex P2 (#2495)."
        )
        body_out = _resp_body(resp)
        assert body_out, "an offset/limit page must return a non-empty body, not the metadata-only directory."
        assert "## Sections" not in body_out, (
            "the unbounded whole-item index must not be prepended to a paged response."
        )

    def test_unpaged_section_none_still_prepends_index(self, mocker: MockerFixture) -> None:
        """An UNPAGED ``section=None`` call still prepends the ## Sections index (M1 not regressed).

        The fix scopes the index to the non-paged path only.  A small unpaged body
        (well under budget) must still receive the prepended index so agents can
        discover available sections — the M1 behaviour (e6191da) is preserved.
        """
        from backlog_core import server

        # Small body so the unpaged response stays under budget and is delivered inline.
        small_body = "## Alpha\n\naaa\n\n## Beta\n\nbbb\n\n## Gamma\n\nggg\n"
        _patch_github_body(mocker, 2495, small_body)

        resp = asyncio.run(server.backlog_view(selector="2495", summary=False))

        assert resp.get("_over_budget") is not True, "premise: the small unpaged body must be delivered inline."
        body_out = _resp_body(resp)
        assert body_out.startswith("## Sections"), (
            "an UNPAGED section=None response must still prepend the ## Sections index (M1, e6191da); "
            f"got a body starting {body_out[:60]!r}.  The paged-path fix must not regress the unpaged path."
        )
        assert "## Alpha" in body_out, "the unpaged body must still carry the real section content after the index."
