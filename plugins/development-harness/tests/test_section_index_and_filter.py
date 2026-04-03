"""Tests for section index, section filtering, and render_sections_as_body.

Covers:
- C: Section index emitted at the top of the rendered body
- D: Section filtering by index, substring, regex, and comma-separated indices
- Edge: no sections → no index block
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure backlog_core is importable from the plugin root
_PLUGIN_ROOT = Path(__file__).parent.parent
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))

from backlog_core.models import BacklogItem, Entry, GroomedData, Section
from backlog_core.operations import (
    _filter_sections,
    _render_section_index,
    _section_display_title,
    render_sections_as_body,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry(content: str, *, struck: bool = False) -> Entry:
    """Build a minimal Entry for tests."""
    if struck:
        return Entry(id="2026-01-01T00:00:00Z", content=content, struck=True, struck_at="2026-01-02T00:00:00Z")
    return Entry(id="2026-01-01T00:00:00Z", content=content)


def _item(sections: dict[str, Section | GroomedData] | None = None) -> BacklogItem:
    """Build a minimal BacklogItem.  ``sections`` defaults to empty dict."""
    return BacklogItem(
        title="Test",
        description="desc",
        priority="P1",
        item_type="Feature",
        status="open",
        added="2026-01-01",
        sections=sections if sections is not None else {},
    )


# ---------------------------------------------------------------------------
# _section_display_title
# ---------------------------------------------------------------------------


class TestSectionDisplayTitle:
    """_section_display_title returns correct display names."""

    def test_known_key_fact_check(self) -> None:
        """Known key 'fact_check' maps to 'Fact-Check'."""
        assert _section_display_title("fact_check") == "Fact-Check"

    def test_known_key_rt_ica(self) -> None:
        """Known key 'rt_ica' maps to 'RT-ICA'."""
        assert _section_display_title("rt_ica") == "RT-ICA"

    def test_groomed_key_with_date(self) -> None:
        """'groomed' key with a date string returns 'Groomed — {date}'."""
        assert _section_display_title("groomed", "2026-03-15") == "Groomed \u2014 2026-03-15"

    def test_groomed_key_no_date(self) -> None:
        """'groomed' key with empty date string returns bare 'Groomed'."""
        assert _section_display_title("groomed", "") == "Groomed"

    def test_unknown_prefix_key(self) -> None:
        """'unknown__impact_radius' key reconstructs to 'Impact Radius'."""
        assert _section_display_title("unknown__impact_radius") == "Impact Radius"

    def test_plain_key_title_cased(self) -> None:
        """Plain key without known prefix is title-cased with spaces."""
        assert _section_display_title("some_section") == "Some Section"


# ---------------------------------------------------------------------------
# _render_section_index — format
# ---------------------------------------------------------------------------


class TestRenderSectionIndex:
    """_render_section_index produces a correctly formatted ## Sections block."""

    def test_empty_sections_returns_empty_string(self) -> None:
        """No sections → empty string (no index block emitted)."""
        item = _item(sections={})
        assert _render_section_index(item) == ""

    def test_index_block_starts_with_sections_heading(self) -> None:
        """Index block starts with '## Sections'."""
        item = _item(sections={"fact_check": Section(entries=[_entry("x")])})
        index = _render_section_index(item)
        assert index.startswith("## Sections")

    def test_index_line_format_with_entries(self) -> None:
        """Each section line shows [idx] Title (N entries)."""
        item = _item(sections={"fact_check": Section(entries=[_entry("a"), _entry("b")])})
        index = _render_section_index(item)
        assert "[0] Fact-Check (2 entries)" in index

    def test_index_struck_entries_not_counted(self) -> None:
        """Struck entries are excluded from the active count in the index."""
        entries = [_entry("active"), _entry("struck one", struck=True)]
        item = _item(sections={"fact_check": Section(entries=entries)})
        index = _render_section_index(item)
        assert "[0] Fact-Check (1 entries)" in index

    def test_index_groomed_shows_subsections(self) -> None:
        """GroomedData entry in index shows subsection count."""
        groomed = GroomedData(date="2026-03-15", subsections={"Priority": "High", "Impact": "Major"})
        item = _item(sections={"groomed": groomed})
        index = _render_section_index(item)
        assert "(2 subsections)" in index

    def test_index_multiple_sections_all_present(self) -> None:
        """Index lists every section in order."""
        item = _item(
            sections={
                "fact_check": Section(entries=[_entry("fc")]),
                "rt_ica": Section(entries=[_entry("rt"), _entry("rt2")]),
            }
        )
        index = _render_section_index(item)
        assert "[0] Fact-Check" in index
        assert "[1] RT-ICA" in index
        # Order: [0] before [1]
        assert index.index("[0]") < index.index("[1]")


# ---------------------------------------------------------------------------
# render_sections_as_body — index prepended
# ---------------------------------------------------------------------------


class TestRenderSectionsAsBodyIndex:
    """render_sections_as_body prepends the section index when no filter is active."""

    def test_index_present_in_full_render(self) -> None:
        """Full render includes ## Sections index block before sections."""
        item = _item(sections={"fact_check": Section(entries=[_entry("x")])})
        body = render_sections_as_body(item)
        assert "## Sections" in body
        # Index appears before the section content
        assert body.index("## Sections") < body.index("## Fact-Check")

    def test_no_index_when_empty_sections(self) -> None:
        """No sections → empty string (no index, no body)."""
        item = _item(sections={})
        assert render_sections_as_body(item) == ""

    def test_no_index_when_section_filter_active(self) -> None:
        """When section filter is active, no index block is prepended."""
        item = _item(
            sections={"fact_check": Section(entries=[_entry("fc")]), "rt_ica": Section(entries=[_entry("rt")])}
        )
        body = render_sections_as_body(item, section="0")
        assert "## Sections" not in body
        assert "## Fact-Check" in body

    def test_groomed_rendered_correctly(self) -> None:
        """GroomedData is rendered with ## Groomed (date) and ### subsections."""
        groomed = GroomedData(date="2026-03-15", subsections={"Priority": "High"})
        item = _item(sections={"groomed": groomed})
        body = render_sections_as_body(item)
        assert "## Groomed (2026-03-15)" in body
        assert "### Priority" in body
        assert "High" in body


# ---------------------------------------------------------------------------
# _filter_sections — by index
# ---------------------------------------------------------------------------


class TestFilterSectionsByIndex:
    """_filter_sections: numeric index selection."""

    def test_single_index_returns_one_section(self) -> None:
        """filter '2' returns only the section at index 2."""
        item = _item(
            sections={
                "fact_check": Section(entries=[_entry("a")]),
                "rt_ica": Section(entries=[_entry("b")]),
                "unknown__custom": Section(entries=[_entry("c")]),
            }
        )
        result = _filter_sections(item, "2")
        assert list(result.keys()) == ["unknown__custom"]

    def test_comma_separated_indices(self) -> None:
        """filter '0,2' returns sections at indices 0 and 2."""
        item = _item(
            sections={
                "fact_check": Section(entries=[_entry("a")]),
                "rt_ica": Section(entries=[_entry("b")]),
                "unknown__custom": Section(entries=[_entry("c")]),
            }
        )
        result = _filter_sections(item, "0,2")
        assert set(result.keys()) == {"fact_check", "unknown__custom"}

    def test_out_of_range_index_ignored(self) -> None:
        """Index beyond section count is silently ignored (no KeyError)."""
        item = _item(sections={"fact_check": Section(entries=[_entry("a")])})
        result = _filter_sections(item, "99")
        assert result == {}

    def test_empty_sections_returns_empty(self) -> None:
        """filter on item with no sections returns empty dict."""
        item = _item(sections={})
        assert _filter_sections(item, "0") == {}


# ---------------------------------------------------------------------------
# _filter_sections — by substring
# ---------------------------------------------------------------------------


class TestFilterSectionsBySubstring:
    """_filter_sections: case-insensitive substring match."""

    def test_substring_match_known_section(self) -> None:
        """filter 'RT-ICA' matches the rt_ica section by display title."""
        item = _item(
            sections={"fact_check": Section(entries=[_entry("fc")]), "rt_ica": Section(entries=[_entry("rt")])}
        )
        result = _filter_sections(item, "RT-ICA")
        assert "rt_ica" in result
        assert "fact_check" not in result

    def test_substring_match_case_insensitive(self) -> None:
        """filter 'rt-ica' (lowercase) still matches the RT-ICA section."""
        item = _item(sections={"rt_ica": Section(entries=[_entry("rt")])})
        result = _filter_sections(item, "rt-ica")
        assert "rt_ica" in result

    def test_substring_match_unknown_section(self) -> None:
        """filter 'Impact' matches unknown__impact_radius display title."""
        item = _item(sections={"unknown__impact_radius": Section(entries=[_entry("ir")])})
        result = _filter_sections(item, "Impact")
        assert "unknown__impact_radius" in result

    def test_no_match_returns_empty(self) -> None:
        """filter with no matching sections returns empty dict."""
        item = _item(sections={"fact_check": Section(entries=[_entry("fc")])})
        result = _filter_sections(item, "Nonexistent")
        assert result == {}


# ---------------------------------------------------------------------------
# _filter_sections — by regex
# ---------------------------------------------------------------------------


class TestFilterSectionsByRegex:
    """_filter_sections: /regex/ delimited pattern."""

    def test_regex_match_impact_sections(self) -> None:
        """filter '/impact.*/' matches section titles containing 'impact'."""
        item = _item(
            sections={
                "fact_check": Section(entries=[_entry("fc")]),
                "unknown__impact_radius": Section(entries=[_entry("ir")]),
                "unknown__impact_score": Section(entries=[_entry("is_")]),
            }
        )
        result = _filter_sections(item, "/impact.*/")
        assert "unknown__impact_radius" in result
        assert "unknown__impact_score" in result
        assert "fact_check" not in result

    def test_regex_case_insensitive(self) -> None:
        """Regex filter is case-insensitive."""
        item = _item(sections={"rt_ica": Section(entries=[_entry("rt")])})
        result = _filter_sections(item, "/RT.*/")
        assert "rt_ica" in result

    def test_empty_regex_body_not_treated_as_regex(self) -> None:
        """'//' (empty regex body) is technically valid but matches everything."""
        item = _item(sections={"fact_check": Section(entries=[_entry("fc")])})
        # An empty regex matches everything — it should return all sections
        result = _filter_sections(item, "//")
        assert "fact_check" in result


# ---------------------------------------------------------------------------
# render_sections_as_body with section filter — body and sections filtered
# ---------------------------------------------------------------------------


class TestRenderSectionsAsBodyFiltered:
    """render_sections_as_body with section filter returns only matched sections."""

    def test_filter_by_index_returns_only_that_section(self) -> None:
        """section='1' returns only the second section's content."""
        item = _item(
            sections={
                "fact_check": Section(entries=[_entry("fact content")]),
                "rt_ica": Section(entries=[_entry("rt content")]),
            }
        )
        body = render_sections_as_body(item, section="1")
        assert "rt content" in body
        assert "fact content" not in body

    def test_filter_no_match_returns_empty(self) -> None:
        """section filter with no match returns empty string."""
        item = _item(sections={"fact_check": Section(entries=[_entry("fc")])})
        body = render_sections_as_body(item, section="Nonexistent")
        assert body == ""

    def test_filter_comma_indices_returns_multiple(self) -> None:
        """Comma-separated indices include both matched sections."""
        item = _item(
            sections={
                "fact_check": Section(entries=[_entry("fc")]),
                "rt_ica": Section(entries=[_entry("rt")]),
                "unknown__notes": Section(entries=[_entry("note")]),
            }
        )
        body = render_sections_as_body(item, section="0,2")
        assert "## Fact-Check" in body
        assert "## Notes" in body
        assert "## RT-ICA" not in body
