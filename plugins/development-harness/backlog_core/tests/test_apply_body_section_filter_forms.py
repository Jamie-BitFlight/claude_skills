"""Edge-case coverage for _apply_body_section_filter filter-form dispatch (#2495).

Supplements test_view_section_form_resolution.py with additional boundary
conditions not covered there: negative indices, out-of-range indices, spaces
in comma-separated lists, invalid regex graceful degradation, partial substring
matching, and the specific RT-ICA→RT-ICA-Analysis substring scenario that
triggered issue #2495.

These tests directly call _apply_body_section_filter (not via the server layer)
so they test the dispatch logic in isolation.
"""

from __future__ import annotations

from backlog_core.models import ViewItemResult
from backlog_core.operations import _apply_body_section_filter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_BODY = """\
## Story

As a developer I want section filtering to work on large items.

## RT-ICA Analysis

This section has a longer name than just RT-ICA.

## Acceptance Criteria

- [ ] Numeric index works
- [ ] Regex works
- [ ] Substring match works

## Context

Background information here.
"""


# ---------------------------------------------------------------------------
# 1. Substring match — the root scenario from issue #2495
# ---------------------------------------------------------------------------


class TestSubstringMatch:
    """_apply_body_section_filter must use substring match, not exact match.

    The original bug: section='RT-ICA' failed against '## RT-ICA Analysis'
    because the filter used exact name matching rather than substring matching.
    """

    def test_substring_matches_longer_header(self) -> None:
        result = ViewItemResult()
        filtered = _apply_body_section_filter(result, _BODY, "RT-ICA")
        assert result.section_filter_miss is False, (
            "'RT-ICA' must substring-match '## RT-ICA Analysis'. Before the fix (exact match) this was a miss."
        )
        assert "RT-ICA Analysis" in filtered
        assert "## Story" not in filtered
        assert "## Acceptance Criteria" not in filtered

    def test_substring_match_case_insensitive(self) -> None:
        result = ViewItemResult()
        _apply_body_section_filter(result, _BODY, "rt-ica")
        assert result.section_filter_miss is False, "'rt-ica' must case-insensitively match '## RT-ICA Analysis'."

    def test_substring_match_partial_word(self) -> None:
        result = ViewItemResult()
        _apply_body_section_filter(result, _BODY, "cceptance")
        assert result.section_filter_miss is False, "'cceptance' is a substring of 'Acceptance Criteria' — must match."

    def test_no_match_sets_miss_flag_and_returns_body_unchanged(self) -> None:
        result = ViewItemResult()
        original = _BODY
        returned = _apply_body_section_filter(result, original, "Nonexistent Section XYZ")
        assert result.section_filter_miss is True
        assert returned == original, "Body must be unchanged on miss."


# ---------------------------------------------------------------------------
# 2. Numeric index — including negative and out-of-range
# ---------------------------------------------------------------------------


class TestNumericIndex:
    """Numeric index boundary conditions not in test_view_section_form_resolution."""

    def test_negative_index_selects_from_end(self) -> None:
        result = ViewItemResult()
        filtered = _apply_body_section_filter(result, _BODY, "-1")
        assert result.section_filter_miss is False, "Index '-1' must select the last section (Context)."
        assert "## Context" in filtered

    def test_out_of_range_index_degrades_gracefully(self) -> None:
        result = ViewItemResult()
        original = _BODY
        returned = _apply_body_section_filter(result, original, "99")
        # Index 99 is out of range (only 4 headers). Implementation falls back
        # to substring matching for "99" — no header name contains "99" — so miss.
        assert result.section_filter_miss is True, "Index 99 (out of range, no substring match) must be a miss."
        assert returned == original


# ---------------------------------------------------------------------------
# 3. Comma-separated indices — spaces handling
# ---------------------------------------------------------------------------


class TestCommaSeparatedIndices:
    """Comma-separated index forms with surrounding whitespace."""

    def test_indices_with_whitespace_are_normalised(self) -> None:
        result = ViewItemResult()
        filtered = _apply_body_section_filter(result, _BODY, " 0 , 1 ")
        assert result.section_filter_miss is False, "' 0 , 1 ' (with spaces) must select Story and RT-ICA Analysis."
        assert "## Story" in filtered
        assert "RT-ICA Analysis" in filtered


# ---------------------------------------------------------------------------
# 4. Regex pattern — invalid regex graceful degradation and multi-match
# ---------------------------------------------------------------------------


class TestRegexPattern:
    """Regex boundary conditions: invalid patterns and multiple section matches."""

    def test_invalid_regex_degrades_to_miss_not_exception(self) -> None:
        result = ViewItemResult()
        original = _BODY
        returned = _apply_body_section_filter(result, original, "/[invalid/")
        # Invalid regex falls back to substring search for "/[invalid/" — no
        # header contains that string — so section_filter_miss is set.
        assert result.section_filter_miss is True, "An invalid regex must not raise; it must degrade to a miss."
        assert returned == original

    def test_regex_matches_multiple_sections_in_document_order(self) -> None:
        result = ViewItemResult()
        filtered = _apply_body_section_filter(result, _BODY, "/Story|Context/")
        assert result.section_filter_miss is False, "/Story|Context/ must match Story and Context headers."
        assert "## Story" in filtered
        assert "## Context" in filtered
        assert "RT-ICA Analysis" not in filtered
        assert filtered.find("## Story") < filtered.find("## Context"), "Matched sections must be in document order."
