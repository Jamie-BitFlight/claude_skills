"""Tests for conflict handling: manually-authored backlinks, dangling paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

import backlink_lib as bl

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Manually-authored backlinks with different relationship descriptions
# ---------------------------------------------------------------------------

_ENTRY_WITH_MANUAL_BACKLINK = """\
# Target Entry

**Research Date**: 2026-01-01
**Source URL**: https://example.com/target
**Version at Research**: 1.0.0
**License**: MIT

---

## Overview

Target entry with a manually-authored backlink.

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

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [SourceEntry](../agent-frameworks/source.md) | agent-frameworks | hand-written description by original author |
"""


class TestManuallyAuthoredBacklinks:
    """Agent skips existing rows regardless of relationship description differences."""

    def test_existing_link_not_overwritten(self) -> None:
        """If link_path already exists, append_backlink_row returns (md, False) unchanged.

        This tests the idempotency guarantee: if a human manually wrote a backlink row
        with a different relationship description, the agent must not overwrite it.
        The detection key is link_path — not the relationship text.
        """
        row_with_different_rel = bl.CrossRefRow(
            entry_name="SourceEntry",
            link_path="../agent-frameworks/source.md",
            category="agent-frameworks",
            relationship="provides data pipeline (auto-generated)",  # different from hand-written
        )
        new_md, modified = bl.append_backlink_row(_ENTRY_WITH_MANUAL_BACKLINK, row_with_different_rel)
        assert not modified, "append_backlink_row must not overwrite a manually-authored row with same link_path"
        assert new_md == _ENTRY_WITH_MANUAL_BACKLINK, "Markdown must remain identical when existing row is detected"

    def test_manually_authored_row_preserved_in_output(self) -> None:
        """Original relationship description is preserved after no-op append."""
        row = bl.CrossRefRow(
            entry_name="SourceEntry",
            link_path="../agent-frameworks/source.md",
            category="agent-frameworks",
            relationship="auto-generated description",
        )
        new_md, _ = bl.append_backlink_row(_ENTRY_WITH_MANUAL_BACKLINK, row)
        assert "hand-written description by original author" in new_md

    def test_different_link_path_does_append(self) -> None:
        """A row with a different link_path IS appended (it's a new entry)."""
        row = bl.CrossRefRow(
            entry_name="AnotherSource",
            link_path="../agent-frameworks/another_source.md",
            category="agent-frameworks",
            relationship="provides data pipeline",
        )
        new_md, modified = bl.append_backlink_row(_ENTRY_WITH_MANUAL_BACKLINK, row)
        assert modified, "A row with a new link_path must be appended"
        assert "AnotherSource" in new_md
        # Original manual row still present
        assert "hand-written description by original author" in new_md

    def test_backlink_exists_detects_manual_row(self) -> None:
        """backlink_exists correctly detects manually-authored rows."""
        assert bl.backlink_exists(_ENTRY_WITH_MANUAL_BACKLINK, "../agent-frameworks/source.md")

    def test_backlink_exists_false_for_absent_link(self) -> None:
        """backlink_exists returns False for a link not in the table."""
        assert not bl.backlink_exists(_ENTRY_WITH_MANUAL_BACKLINK, "../tools/absent.md")


# ---------------------------------------------------------------------------
# Dangling paths (broken links)
# ---------------------------------------------------------------------------


class TestDanglingPaths:
    """build_cross_reference_graph gracefully handles broken links."""

    def _make_entry_with_dangling_link(self, path: Path) -> None:
        """Write an entry with a cross-reference to a non-existent target."""
        path.parent.mkdir(parents=True, exist_ok=True)
        content = """\
# Source Entry

**Research Date**: 2026-01-01
**Source URL**: https://example.com/source
**Version at Research**: 1.0.0
**License**: MIT

---

## Overview

Entry with a dangling link.

## Problem Addressed

Test.

## Key Features

- Feature A

## Technical Architecture

Simple.

## Installation & Usage

```bash
pip install source
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

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [NonExistent](../tools/does_not_exist.md) | tools | provides nonexistent service |
"""
        path.write_text(content, encoding="utf-8")

    def test_dangling_link_does_not_crash(self, tmp_path: Path) -> None:
        """build_cross_reference_graph does not raise when a cited path does not exist."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "README.md").write_text("# Research\n", encoding="utf-8")
        (vault / "agent-frameworks").mkdir()

        self._make_entry_with_dangling_link(vault / "agent-frameworks" / "source.md")

        # Must not raise — dangling links are skipped
        graph = bl.build_cross_reference_graph(vault)
        source = (vault / "agent-frameworks" / "source.md").resolve()
        assert source in graph
        # The dangling target is not in the adjacency list
        assert graph[source] == [], "Dangling link must be skipped — target not in adjacency list"

    def test_dangling_link_not_in_graph_nodes(self, tmp_path: Path) -> None:
        """The non-existent target is not added to the graph as a node."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "README.md").write_text("# Research\n", encoding="utf-8")
        (vault / "agent-frameworks").mkdir()

        self._make_entry_with_dangling_link(vault / "agent-frameworks" / "source.md")
        graph = bl.build_cross_reference_graph(vault)

        dangling = (vault / "tools" / "does_not_exist.md").resolve()
        assert dangling not in graph, "Dangling target must not appear as a graph node"

    def test_dangling_link_finds_no_asymmetries(self, tmp_path: Path) -> None:
        """Graph with only dangling links finds no asymmetric edges (target not in graph)."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "README.md").write_text("# Research\n", encoding="utf-8")
        (vault / "agent-frameworks").mkdir()

        self._make_entry_with_dangling_link(vault / "agent-frameworks" / "source.md")
        graph = bl.build_cross_reference_graph(vault)
        asymmetric = bl.find_asymmetric_edges(graph)

        assert asymmetric == [], "No asymmetric edges expected when only target is dangling (not a graph node)"

    def test_mixed_valid_and_dangling_links(self, tmp_path: Path) -> None:
        """Entry with one valid + one dangling link: only valid link in adjacency list."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "README.md").write_text("# Research\n", encoding="utf-8")
        (vault / "agent-frameworks").mkdir()
        (vault / "tools").mkdir()

        # Source entry with one valid and one dangling link
        source_content = """\
# Source Entry

**Research Date**: 2026-01-01
**Source URL**: https://example.com/source
**Version at Research**: 1.0.0
**License**: MIT

---

## Overview

Entry.

## Problem Addressed

Test.

## Key Features

- Feature A

## Technical Architecture

Simple.

## Installation & Usage

```bash
pip install source
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

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [ValidTarget](../tools/valid.md) | tools | provides X |
| [Missing](../tools/missing.md) | tools | consumes Y |
"""
        (vault / "agent-frameworks" / "source.md").write_text(source_content, encoding="utf-8")

        # Create the valid target
        valid_content = """\
# Valid Target

**Research Date**: 2026-01-01
**Source URL**: https://example.com/valid
**Version at Research**: 1.0.0
**License**: MIT

---

## Overview

Valid entry.

## Problem Addressed

Test.

## Key Features

- Feature A

## Technical Architecture

Simple.

## Installation & Usage

```bash
pip install valid
```

## Key Statistics

- Stars: 3 (as of 2026-01-01)

## Relevance to Claude Code Development

Test.

## References

- [Example](https://example.com) (accessed 2026-01-01)

## Freshness Tracking

- **Last Verified**: 2026-01-01
- **Version at Verification**: 1.0.0
- **Next Review Recommended**: 2026-07-01
"""
        (vault / "tools" / "valid.md").write_text(valid_content, encoding="utf-8")
        # tools/missing.md does NOT exist

        graph = bl.build_cross_reference_graph(vault)
        source_abs = (vault / "agent-frameworks" / "source.md").resolve()
        valid_abs = (vault / "tools" / "valid.md").resolve()

        assert valid_abs in graph[source_abs], "Valid target must be in adjacency list"
        missing_abs = (vault / "tools" / "missing.md").resolve()
        assert missing_abs not in graph[source_abs], "Missing target must not be in adjacency list"


# ---------------------------------------------------------------------------
# extract_section_block helper
# ---------------------------------------------------------------------------


class TestExtractSectionBlock:
    """Tests for the extract_section_block utility function."""

    def test_returns_none_when_heading_absent(self) -> None:
        """Returns None when the specified heading is not found."""
        md = "# Entry\n\n## Overview\n\nSome content.\n"
        result = bl.extract_section_block(md, "Cross-References")
        assert result is None

    def test_returns_correct_range_when_found(self) -> None:
        """Returns (start_line, end_line) tuple for the found heading."""
        md = (
            "# Entry\n\n"
            "## Cross-References\n\n"
            "| Entry | Category | Relationship |\n"
            "|-------|----------|---|\n"
            "| [Alpha](../tools/alpha.md) | tools | provides X |\n\n"
            "## Freshness Tracking\n\n"
            "- done\n"
        )
        result = bl.extract_section_block(md, "Cross-References")
        assert result is not None
        start, end = result
        assert start > 0
        assert end > start
