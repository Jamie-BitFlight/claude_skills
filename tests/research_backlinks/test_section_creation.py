"""Tests for section creation: append_backlink_row when Cross-References is absent."""

from __future__ import annotations

import pytest

import backlink_lib as bl

_FRESHNESS_ONLY = """\
# Target Entry

**Research Date**: 2026-01-01
**Source URL**: https://example.com/target
**Version at Research**: 1.0.0
**License**: MIT

---

## Overview

Entry with Freshness Tracking but no Cross-References section.

## Problem Addressed

Test.

## Key Features

- Feature A

## Technical Architecture

Simple.

## Installation & Usage

```bash
pip install target
```

## Key Statistics

- Stars: 5 (as of 2026-01-01)

## Relevance to Claude Code Development

Test.

## References

- [Example](https://example.com) (accessed 2026-01-01)

## Freshness Tracking

- **Last Verified**: 2026-01-01
- **Version at Verification**: 1.0.0
- **Next Review Recommended**: 2026-07-01
"""

_NO_FRESHNESS_NO_CROSS_REF = """\
# Target Entry

**Research Date**: 2026-01-01
**Source URL**: https://example.com/target
**Version at Research**: 1.0.0
**License**: MIT

---

## Overview

Entry with neither Freshness Tracking nor Cross-References.

## Problem Addressed

Test.
"""


class TestSectionCreatedAfterFreshnessTracking:
    """Entry with Freshness Tracking but no Cross-References gets a new section."""

    def test_new_section_is_created(self) -> None:
        """append_backlink_row creates ## Cross-References after Freshness Tracking."""
        row = bl.CrossRefRow(
            entry_name="AlphaEntry",
            link_path="../agent-frameworks/alpha.md",
            category="agent-frameworks",
            relationship="provides embedding layer",
        )
        new_md, modified = bl.append_backlink_row(_FRESHNESS_ONLY, row)
        assert modified, "modified should be True when a new section is created"
        assert "## Cross-References" in new_md

    def test_new_section_contains_row(self) -> None:
        """The newly created section contains the appended row."""
        row = bl.CrossRefRow(
            entry_name="AlphaEntry",
            link_path="../agent-frameworks/alpha.md",
            category="agent-frameworks",
            relationship="provides embedding layer",
        )
        new_md, _ = bl.append_backlink_row(_FRESHNESS_ONLY, row)
        assert "AlphaEntry" in new_md
        assert "../agent-frameworks/alpha.md" in new_md

    def test_new_section_has_table_header(self) -> None:
        """The newly created section includes the canonical table header and separator."""
        row = bl.CrossRefRow(
            entry_name="BetaEntry", link_path="../tools/beta.md", category="tools", relationship="consumes data"
        )
        new_md, _ = bl.append_backlink_row(_FRESHNESS_ONLY, row)
        assert "| Entry | Category | Relationship |" in new_md
        assert "|-------|----------" in new_md

    def test_new_section_appears_after_freshness(self) -> None:
        """Cross-References section appears after Freshness Tracking section in output."""
        row = bl.CrossRefRow(
            entry_name="GammaEntry",
            link_path="../tools/gamma.md",
            category="tools",
            relationship="orchestrates data flow",
        )
        new_md, _ = bl.append_backlink_row(_FRESHNESS_ONLY, row)
        freshness_idx = new_md.index("## Freshness Tracking")
        cross_ref_idx = new_md.index("## Cross-References")
        assert cross_ref_idx > freshness_idx, "Cross-References section must appear after Freshness Tracking"

    def test_idempotent_after_section_creation(self) -> None:
        """After section is created, a second call with same row returns (md, False)."""
        row = bl.CrossRefRow(
            entry_name="AlphaEntry",
            link_path="../agent-frameworks/alpha.md",
            category="agent-frameworks",
            relationship="provides embedding layer",
        )
        first_md, _ = bl.append_backlink_row(_FRESHNESS_ONLY, row)
        second_md, second_modified = bl.append_backlink_row(first_md, row)
        assert not second_modified
        assert first_md == second_md

    def test_no_freshness_no_cross_ref_raises_value_error(self) -> None:
        """Entry with no Freshness Tracking and no Cross-References raises ValueError."""
        row = bl.CrossRefRow(
            entry_name="DeltaEntry", link_path="../tools/delta.md", category="tools", relationship="calls API"
        )
        with pytest.raises(ValueError, match="Cannot insert Cross-References section"):
            bl.append_backlink_row(_NO_FRESHNESS_NO_CROSS_REF, row)

    def test_append_to_existing_table_not_create_section(self) -> None:
        """When Cross-References already exists, row is appended (not a new section)."""
        md_with_table = (
            _FRESHNESS_ONLY.rstrip("\n") + "\n\n---\n\n## Cross-References\n\n"
            "| Entry | Category | Relationship |\n"
            "|-------|----------|---|\n"
            "| [ExistingEntry](../tools/existing.md) | tools | orchestrates X |\n"
        )
        row = bl.CrossRefRow(
            entry_name="NewEntry", link_path="../tools/new.md", category="tools", relationship="complements X"
        )
        new_md, modified = bl.append_backlink_row(md_with_table, row)
        assert modified
        # The new row must appear exactly once
        assert new_md.count("NewEntry") == 1
        # The existing row must still be present
        assert "ExistingEntry" in new_md
        # No second Cross-References heading created
        assert new_md.count("## Cross-References") == 1
