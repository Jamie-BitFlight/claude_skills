"""G1 — Section-form resolution on raw bodies (#2495).

Covers defect (b): numeric / comma / regex section forms must match on raw
GitHub bodies, and the plural ``sections=[...]`` dict filter must match
case-insensitively.

Test classes:
- ``TestNumericSectionFilterOnRawBody`` — numeric / regex forms on raw bodies
- ``TestCommaSectionFormOnRawBody`` — comma index form on raw bodies
- ``TestNarrowBodyToNamedSectionsUnit`` — direct unit for narrow_body_to_named_sections
- ``TestSectionsDictFilterIsCaseInsensitive`` — case-insensitive dict filter (Codex P2)

Test naming: every test contains ``over_budget`` or ``numeric_section`` so
``pytest -k "over_budget or numeric_section"`` selects the whole #2495 suite.
"""

from __future__ import annotations

import pytest

from backlog_core import operations
from backlog_core.models import ViewItemResult
from backlog_core.operations import _apply_body_section_filter
from backlog_core.tests._view_test_helpers import _resp_metadata
from backlog_core.tests.conftest import REAL_CL100K_AVAILABLE

# These tests assert over/under the token budget using real cl100k_base counts.
# The offline stub (conftest) lacks real BPE compression, so skip them when the
# real encoding is unavailable rather than fail on miscalibrated counts (PR #2496).
pytestmark = pytest.mark.skipif(
    not REAL_CL100K_AVAILABLE,
    reason="token-budget tests require the real cl100k_base encoding (offline stub lacks BPE compression)",
)


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
# Finding 8/10 coverage gap: comma index form on raw GitHub bodies
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Finding 8/10: direct unit coverage for narrow_body_to_named_sections
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Codex P2 (#2495): case-insensitive sections=[...] dict filter
# ---------------------------------------------------------------------------


def _filter_sections_isolated(
    body: str,
    structured_keys: list[str],
    requested: list[str],
    *,
    sections_metadata: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Run ``_filter_view_sections`` in isolation over a hand-built result.

    Builds a :class:`ViewItemResult` with the given raw *body*, structured
    ``sections`` keyed by *structured_keys*, and optional *sections_metadata*,
    serialises it with ``model_dump()``, and returns the filtered response dict.
    Avoids GitHub-enrichment coupling so the dict / metadata / body arms of
    ``_filter_view_sections`` are exercised directly.

    Args:
        body: Raw body text carrying ``## ``/``### `` headers.
        structured_keys: Keys for the structured ``sections`` dict (the
            ``include_content=True`` inventory).
        requested: The ``sections=[...]`` names to filter by.
        sections_metadata: Optional compact ``sections_metadata`` inventory
            (the ``include_content=False`` arm); each entry is a ``SectionMeta``
            shaped dict.

    Returns:
        The filtered response dict returned by ``_filter_view_sections``.
    """
    from backlog_core import operations as ops, server

    result = ops.ViewItemResult(
        number=2495,
        title="case-insensitive filter",
        body=body,
        sections={key: ops._SectionMetadata(num_entries=1, num_struck=0, entries=[]) for key in structured_keys},
        sections_metadata=[],
    )
    response = result.model_dump()
    if sections_metadata is not None:
        # model_dump() flattens SectionMeta entries to plain dicts; set the compact
        # inventory directly so the include_content=False metadata arm is exercised.
        response["sections_metadata"] = sections_metadata
    return server._filter_view_sections(response, requested, result)


class TestSectionsDictFilterIsCaseInsensitive:
    """Codex P2 (#2495): the ``sections=[...]`` dict filter must match case-insensitively.

    ``narrow_body_to_named_sections`` (body arm) and the ``sections_metadata`` arm
    both match section names case-insensitively, but the structured ``sections``
    dict filter used a CASE-SENSITIVE ``k in requested`` membership test.  When
    ``sections=[...]`` named a section differing only by case from the parsed key
    (e.g. ``["rt-ica"]`` against an ``RT-ICA`` key / ``## RT-ICA`` header), the body
    arm matched and narrowed the body while the dict arm dropped the metadata —
    leaving ``sections={}`` with NO ``section_filter_miss`` signal, silently breaking
    the body/metadata sync contract.

    Only the case-sensitivity of the plural ``sections=[...]`` dict filter changes;
    the exact-name (not substring) matching semantics are preserved.
    """

    def test_lowercase_request_keeps_matching_dict_entry_and_body(self) -> None:
        """``sections=['rt-ica']`` against an ``RT-ICA`` key / ``## RT-ICA`` header.

        RED (pre-fix): the body is narrowed (the body arm is case-insensitive) but the
        structured ``sections`` dict is empty (the dict arm was case-sensitive), so the
        caller receives the body slice with ``sections: {}`` and NO ``section_filter_miss``
        — a silent body/metadata desync.
        """
        body = f"## Story\n\nstory body\n\n## RT-ICA\n\nrt-ica body\n\n## Impact Radius\n\n{'pad ' * 50}\n"
        filtered = _filter_sections_isolated(body, ["RT-ICA"], ["rt-ica"])

        sections = filtered.get("sections")
        assert isinstance(sections, dict), "filtered response 'sections' must be a dict."
        assert "RT-ICA" in sections, (
            "a lowercase 'rt-ica' request must keep the case-differing 'RT-ICA' structured key — "
            f"the dict filter must be case-insensitive like the body filter; got keys {sorted(sections)}. Codex P2."
        )
        assert "rt-ica body" in str(filtered.get("body", "")), (
            "the body arm narrows case-insensitively; the narrowed RT-ICA slice must be present."
        )
        assert "story body" not in str(filtered.get("body", "")), (
            "only the requested RT-ICA section must remain in the narrowed body."
        )
        assert filtered.get("section_filter_miss") is not True, (
            "a case-differing name that matches a structured key AND a body header is NOT a miss — "
            "section_filter_miss must not be set. Codex P2."
        )

    def test_uppercase_request_keeps_matching_dict_entry(self) -> None:
        """``sections=['RT-ICA']`` (upper) against a lowercase ``rt-ica`` key / ``## rt-ica`` header.

        Mirror of the lowercase case proving the comparison folds case in both
        directions, not merely lowercasing the request.
        """
        body = f"## Summary\n\nsummary body\n\n## rt-ica\n\nlower header body\n\n## Tail\n\n{'pad ' * 50}\n"
        filtered = _filter_sections_isolated(body, ["rt-ica"], ["RT-ICA"])

        sections = filtered.get("sections")
        assert isinstance(sections, dict), "filtered response 'sections' must be a dict."
        assert "rt-ica" in sections, (
            "an uppercase 'RT-ICA' request must keep the lowercase 'rt-ica' structured key; "
            f"got keys {sorted(sections)}. Codex P2."
        )
        assert "lower header body" in str(filtered.get("body", "")), (
            "the case-insensitive body arm must narrow to the matching lowercase header slice."
        )
        assert filtered.get("section_filter_miss") is not True, (
            "an uppercase request matching a lowercase key/header is not a miss. Codex P2."
        )

    def test_case_insensitive_dict_match_keeps_metadata_arm_in_sync(self) -> None:
        """Compact ``sections_metadata`` arm: a case-differing valid name stays a non-miss.

        Exercises the ``include_content=False`` arm (already case-insensitive from
        finding #4) alongside the now-aligned dict arm: a lowercase request against a
        mixed-case metadata entry filters the inventory and does not report a miss.
        """
        body = f"## RT-ICA\n\nrt-ica body\n\n## Other\n\n{'pad ' * 50}\n"
        meta: list[dict[str, object]] = [
            {"name": "RT-ICA", "num_entries": 1, "num_struck": 0},
            {"name": "Other", "num_entries": 0, "num_struck": 0},
        ]
        filtered = _filter_sections_isolated(body, ["RT-ICA"], ["rt-ica"], sections_metadata=meta)

        kept_meta = _resp_metadata(filtered)
        kept_names = {str(entry.get("name", "")) for entry in kept_meta}
        assert kept_names == {"RT-ICA"}, (
            f"the metadata arm must filter to only the case-insensitively matching name; got {sorted(kept_names)}."
        )
        assert filtered.get("section_filter_miss") is not True, (
            "the dict, body, and metadata arms must all agree this is a match, not a miss. Codex P2."
        )

    def test_genuinely_absent_name_still_sets_filter_miss(self) -> None:
        """A name absent from the dict, body headers, AND metadata still sets section_filter_miss.

        Guards that the case-folding change does not weaken the no-match signal: a name
        that matches nothing — in any case — must still report a miss.
        """
        body = f"## Story\n\nstory body\n\n## RT-ICA\n\nrt-ica body\n\n## Tail\n\n{'pad ' * 50}\n"
        meta: list[dict[str, object]] = [{"name": "RT-ICA", "num_entries": 1, "num_struck": 0}]
        filtered = _filter_sections_isolated(body, ["RT-ICA"], ["does-not-exist"], sections_metadata=meta)

        assert filtered.get("sections") == {}, "an absent name must leave the structured sections dict empty."
        assert filtered.get("section_filter_miss") is True, (
            "a name absent from the dict, body, and metadata in EVERY case must still set "
            "section_filter_miss — the case-folding fix must not suppress genuine misses. Codex P2."
        )
