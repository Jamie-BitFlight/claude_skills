"""Tests for _from_entry_template_meta and its dispatch in parse_frontmatter_entry.

Regression coverage for the bug Codex flagged on PR #2723: entries written in
the current entry-template.md schema (top-level name/research_date/source_url,
freshness data in a freshness_tracking mapping or flat keys) fell through to
_from_flat_meta, which requires topic/verified (not research_date/last_verified)
and raised FrontmatterValidationError -- silently dropping the entry from
build_tree() via the contextlib.suppress(KBError) in that function.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

# ---------------------------------------------------------------------------
# Fixtures: minimal frontmatter blocks in each recognised schema
# ---------------------------------------------------------------------------

_NESTED_FRESHNESS = dedent("""\
    ---
    name: example-tool
    description: A tool that does the thing.
    category: developer-tools
    research_date: 2026-01-01
    source_url: https://example.com/example-tool
    version_at_research: "2.0.0"
    license: MIT
    freshness_tracking:
      last_verified: 2026-01-01
      version_at_verification: "2.0.0"
      next_review: 2026-04-01
    ---

    ## Overview

    Test entry.
    """)

_FLAT_FRESHNESS = dedent("""\
    ---
    name: example-tool
    category: developer-tools
    research_date: 2026-01-01
    resource_url: https://example.com/example-tool
    last_verified: 2026-01-01
    version_at_verification: "2.0.0"
    next_review: 2026-04-01
    ---

    ## Overview

    Test entry using resource_url and flat freshness keys.
    """)

_MISSING_FRESHNESS = dedent("""\
    ---
    name: example-tool
    category: developer-tools
    research_date: 2026-01-01
    source_url: https://example.com/example-tool
    ---

    ## Overview

    Test entry with no freshness data anywhere.
    """)

_MISSING_SOURCE_URL = dedent("""\
    ---
    name: example-tool
    category: developer-tools
    research_date: 2026-01-01
    freshness_tracking:
      last_verified: 2026-01-01
      next_review: 2026-04-01
    ---

    ## Overview

    Test entry with neither source_url nor resource_url.
    """)

_LEGACY_RESEARCH_CURATOR = dedent("""\
    ---
    title: Example Tool
    subtitle: A tool that does the thing.
    category: developer-tools
    resource_url: https://example.com/example-tool
    date_created: "2026-01-01"
    date_last_reviewed: "2026-01-01"
    ---

    ## Overview

    Legacy research-curator format entry -- must not be routed to the new parser.
    """)

_SKILL_SPEC = dedent("""\
    ---
    name: Example Tool
    description: A tool that does the thing.
    license: MIT
    metadata:
      topic: example-tool
      category: developer-tools
      source_url: https://example.com/example-tool
      verified: "2026-01-01"
      next_review: "2026-04-01"
    ---

    ## Overview

    Skill-spec format entry -- must not be routed to the new parser.
    """)


class TestFromEntryTemplateMeta:
    """Direct tests of _from_entry_template_meta."""

    def test_nested_freshness_tracking_parses(self, ke) -> None:
        """freshness_tracking.last_verified/next_review are read correctly."""
        entry = ke.parse_frontmatter_entry(_NESTED_FRESHNESS, Path("developer-tools/example-tool.md"))
        assert entry.name == "example-tool"
        assert entry.category == "developer-tools"
        assert entry.source_url == "https://example.com/example-tool"
        assert str(entry.verified) == "2026-01-01"
        assert str(entry.next_review) == "2026-04-01"
        assert entry.version == "2.0.0"
        assert entry.license == "MIT"

    def test_flat_freshness_keys_parse(self, ke) -> None:
        """Flat last_verified/next_review (no freshness_tracking dict) are read correctly."""
        entry = ke.parse_frontmatter_entry(_FLAT_FRESHNESS, Path("developer-tools/example-tool.md"))
        assert str(entry.verified) == "2026-01-01"
        assert str(entry.next_review) == "2026-04-01"

    def test_resource_url_fallback(self, ke) -> None:
        """resource_url is used when source_url is absent."""
        entry = ke.parse_frontmatter_entry(_FLAT_FRESHNESS, Path("developer-tools/example-tool.md"))
        assert entry.source_url == "https://example.com/example-tool"

    def test_topic_defaults_to_file_stem(self, ke) -> None:
        """No topic field in this schema -- topic defaults to the file stem."""
        entry = ke.parse_frontmatter_entry(_NESTED_FRESHNESS, Path("developer-tools/example-tool.md"))
        assert entry.topic == "example-tool"

    def test_missing_freshness_raises(self, ke) -> None:
        """Neither freshness_tracking nor flat last_verified/next_review present -- raises."""
        with pytest.raises(ke.FrontmatterValidationError) as exc_info:
            ke.parse_frontmatter_entry(_MISSING_FRESHNESS, Path("developer-tools/example-tool.md"))
        assert "freshness_tracking.last_verified" in exc_info.value.missing_fields
        assert "freshness_tracking.next_review" in exc_info.value.missing_fields

    def test_missing_source_url_raises(self, ke) -> None:
        """Neither source_url nor resource_url present -- raises."""
        with pytest.raises(ke.FrontmatterValidationError) as exc_info:
            ke.parse_frontmatter_entry(_MISSING_SOURCE_URL, Path("developer-tools/example-tool.md"))
        assert "source_url" in exc_info.value.missing_fields


class TestDispatchRoutesToCorrectSchema:
    """parse_frontmatter_entry must route each format to its own parser, not the new one."""

    def test_legacy_research_curator_format_not_broken(self, ke) -> None:
        """Legacy title/resource_url/date_created entries still parse via the old branch."""
        entry = ke.parse_frontmatter_entry(_LEGACY_RESEARCH_CURATOR, Path("developer-tools/example-tool.md"))
        assert entry.name == "Example Tool"
        assert str(entry.verified) == "2026-01-01"

    def test_skill_spec_format_not_broken(self, ke) -> None:
        """Skill-spec (metadata mapping) entries still parse via the skill-spec branch."""
        entry = ke.parse_frontmatter_entry(_SKILL_SPEC, Path("developer-tools/example-tool.md"))
        assert entry.topic == "example-tool"
        assert entry.name == "Example Tool"

    def test_entry_template_format_routes_to_new_branch(self, ke) -> None:
        """research_date + name at top level (no title, no metadata dict) routes here."""
        entry = ke.parse_frontmatter_entry(_NESTED_FRESHNESS, Path("developer-tools/example-tool.md"))
        # Only _from_entry_template_meta defaults topic to the file stem while
        # accepting research_date as a required field; reaching this assertion
        # without an exception confirms the correct branch was taken.
        assert entry.topic == "example-tool"


class TestBuildTreeRecoversEntry:
    """End-to-end: an entry-template-format file must survive build_tree(), not be silently skipped."""

    def test_entry_appears_in_build_tree(self, ke, tmp_path: Path) -> None:
        """Regression test for the exact bug: entry must not be silently dropped."""
        category_dir = tmp_path / "developer-tools"
        category_dir.mkdir()
        (category_dir / "example-tool.md").write_text(_NESTED_FRESHNESS, encoding="utf-8")

        entries = ke.build_tree(tmp_path)

        assert len(entries) == 1, "entry must survive build_tree(), not be silently swallowed by contextlib.suppress"
        assert entries[0].name == "example-tool"
