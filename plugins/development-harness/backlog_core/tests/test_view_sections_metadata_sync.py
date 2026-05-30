"""G3 — sections/body metadata sync, miss handling, malformed regex, key drift (#2495).

Covers defect (c): ``result.sections`` must mirror the narrowed ``result.body``
for all resolved section forms, and a genuine miss must empty both sections and
body and set the miss flag.

Test classes:
- ``TestSectionsMetadataInSync`` — sections dict in sync with narrowed body
- ``TestMalformedRegexDoesNotCrash`` — malformed /regex/ degrades, does not raise
- ``TestSectionMissEmptiesBodyAndSections`` — miss yields empty body + empty sections
- ``TestCompactValidNamesNotReportedAsMiss`` — include_content=False + valid names = no miss
- ``TestStructuredKeyDriftStillDelivered`` — dict matches but body header drifts

Test naming: every test contains ``over_budget`` or ``numeric_section`` so
``pytest -k "over_budget or numeric_section"`` selects the whole #2495 suite.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from backlog_core import operations
from backlog_core.models import ViewItemResult
from backlog_core.operations import _apply_body_section_filter
from backlog_core.tests._view_test_helpers import _patch_github_body, _resp_metadata
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
# Local constants and helpers
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
    """Extract ``## ``/``### `` header names from *body* in document order.

    Args:
        body: Raw markdown body text containing ``## ``/``### `` headers.

    Returns:
        A list of header name strings in document order.
    """
    return [hdr.group(1).strip() for hdr in operations._SECTION_BOUNDARY_RE.finditer(body)]


def _view(mocker: MockerFixture, body: str, section: str) -> ViewItemResult:
    """Drive ``operations.view_item`` against a controlled raw GitHub body.

    Args:
        mocker: The pytest-mock fixture for patching the operations layer.
        body: The controlled body text to inject via the GitHub-enrichment patch.
        section: The ``section=`` value to pass to ``view_item``.

    Returns:
        The ``ViewItemResult`` returned by ``operations.view_item``.
    """
    _patch_github_body(mocker, 2495, body)
    return operations.view_item(selector="2495", include_content=True, section=section)


# ---------------------------------------------------------------------------
# Defect (c): result.sections must stay in sync with the resolved body filter
# ---------------------------------------------------------------------------


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
