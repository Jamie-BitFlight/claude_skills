"""Tests for parse_cross_references_table using marko AST parsing."""

from __future__ import annotations

import pytest

import backlink_lib as bl


class TestEmptyEntry:
    """Entries without a Cross-References section."""

    def test_no_section_returns_empty_list(self) -> None:
        """Empty entry (no ## Cross-References) returns []."""
        md = "# Entry\n\n## Overview\n\nSome content.\n"
        result = bl.parse_cross_references_table(md)
        assert result == []

    def test_empty_string_returns_empty_list(self) -> None:
        """Completely empty string returns []."""
        result = bl.parse_cross_references_table("")
        assert result == []

    def test_section_heading_only_no_table_returns_empty(self) -> None:
        """## Cross-References present but no table returns []."""
        md = "# Entry\n\n## Cross-References\n\nNo table here.\n"
        result = bl.parse_cross_references_table(md)
        assert result == []

    def test_fenced_cross_references_table_is_ignored(self) -> None:
        md = """\
# Entry

```markdown
## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Alpha](../agent-frameworks/alpha.md) | agent-frameworks | example |
```
"""
        assert bl.parse_cross_references_table(md) == []

    def test_commented_cross_references_table_is_ignored(self) -> None:
        md = """\
# Entry

<!--
## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Alpha](../agent-frameworks/alpha.md) | agent-frameworks | example |
-->
"""
        assert bl.parse_cross_references_table(md) == []


class TestSingleRowTable:
    """One-row Cross-References table parsing."""

    def test_single_row_returns_one_item(self) -> None:
        """Single-row table returns exactly 1 CrossRefRow with all fields."""
        md = (
            "# Entry\n\n"
            "## Cross-References\n\n"
            "| Entry | Category | Relationship |\n"
            "|-------|----------|---|\n"
            "| [Alpha](../agent-frameworks/alpha.md) | agent-frameworks | provides embedding layer |\n"
        )
        rows = bl.parse_cross_references_table(md)
        assert len(rows) == 1
        row = rows[0]
        assert row.entry_name == "Alpha"
        assert row.link_path == "../agent-frameworks/alpha.md"
        assert row.category == "agent-frameworks"
        assert row.relationship == "provides embedding layer"

    def test_single_row_same_category_link(self) -> None:
        """Relative same-directory link (./sibling.md) is parsed correctly."""
        md = (
            "# Entry\n\n"
            "## Cross-References\n\n"
            "| Entry | Category | Relationship |\n"
            "|-------|----------|---|\n"
            "| [Sibling](./sibling.md) | ai-observability | complements drift detection |\n"
        )
        rows = bl.parse_cross_references_table(md)
        assert len(rows) == 1
        assert rows[0].link_path == "./sibling.md"

    def test_inline_markup_is_rendered_from_ast(self) -> None:
        md = (
            "# Entry\n\n"
            "## *Cross-References*\n\n"
            "| Entry | Category | Relationship |\n"
            "|-------|----------|---|\n"
            "| [*Alpha*](../agent-frameworks/alpha.md) | *agent-frameworks* | provides **embedding** |\n"
        )
        rows = bl.parse_cross_references_table(md)
        assert rows == [
            bl.CrossRefRow(
                entry_name="Alpha",
                link_path="../agent-frameworks/alpha.md",
                category="agent-frameworks",
                relationship="provides embedding",
            )
        ]

    def test_escaped_pipe_stays_in_one_relationship_cell(self) -> None:
        md = (
            "# Entry\n\n"
            "## Cross-References\n\n"
            "| Entry | Category | Relationship |\n"
            "|-------|----------|---|\n"
            "| [Alpha](../agent-frameworks/alpha.md) | agent-frameworks | relates A \\| B |\n"
        )
        rows = bl.parse_cross_references_table(md)
        assert rows[0].relationship == "relates A | B"


class TestMultiRowTable:
    """Multi-row Cross-References table parsing."""

    def test_eight_row_table_returns_all_in_order(self) -> None:
        """8-row table returns all 8 rows in document order."""
        header = "# Entry\n\n## Cross-References\n\n| Entry | Category | Relationship |\n|-------|----------|---|\n"
        rows_md = "\n".join(f"| [Tool{i}](../cat/tool{i}.md) | category | relationship {i} |" for i in range(1, 9))
        md = header + rows_md + "\n"
        result = bl.parse_cross_references_table(md)
        assert len(result) == 8
        for i, row in enumerate(result, start=1):
            assert row.entry_name == f"Tool{i}"
            assert row.link_path == f"../cat/tool{i}.md"
            assert row.relationship == f"relationship {i}"


class TestMalformedTable:
    """Table parsing raises ValueError for malformed rows."""

    def test_row_missing_link_raises_value_error(self) -> None:
        """Row where Entry cell has plain text (no link) raises ValueError."""
        md = (
            "# Entry\n\n"
            "## Cross-References\n\n"
            "| Entry | Category | Relationship |\n"
            "|-------|----------|---|\n"
            "| NoLink | agent-frameworks | provides X |\n"
        )
        with pytest.raises(ValueError, match="markdown link"):
            bl.parse_cross_references_table(md)
