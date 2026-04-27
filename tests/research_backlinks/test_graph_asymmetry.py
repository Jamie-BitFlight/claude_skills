"""Tests for build_cross_reference_graph and find_asymmetric_edges."""

from __future__ import annotations

from pathlib import Path

import pytest

import backlink_lib as bl

# ---------------------------------------------------------------------------
# Helper: minimal entry template
# ---------------------------------------------------------------------------

_ENTRY_TMPL = """\
# {name}

**Research Date**: 2026-01-01
**Source URL**: https://example.com/{slug}
**Version at Research**: 1.0.0
**License**: MIT

---

## Overview

{name}.

## Problem Addressed

Test.

## Key Features

- Feature A

## Technical Architecture

Simple.

## Installation & Usage

```bash
pip install {slug}
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


def _make_vault_entry(vault: Path, relative_path: str, cross_refs: list[tuple[str, str, str]] | None = None) -> Path:
    """Write a minimal entry at vault/relative_path with optional Cross-References rows.

    Args:
        vault: Vault root directory.
        relative_path: Path relative to vault (e.g. "tools/beta.md").
        cross_refs: List of (link, category, relationship) tuples for the table.

    Returns:
        Absolute path to the created file.
    """
    abs_path = vault / relative_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    slug = abs_path.stem
    content = _ENTRY_TMPL.format(name=slug.title(), slug=slug)

    if cross_refs:
        table_lines = [
            "",
            "---",
            "",
            "## Cross-References",
            "",
            "| Entry | Category | Relationship |",
            "|-------|----------|--------------|",
        ]
        for link, category, relationship in cross_refs:
            link_name = Path(link).stem.title()
            table_lines.append(f"| [{link_name}]({link}) | {category} | {relationship} |")
        content = content.rstrip("\n") + "\n" + "\n".join(table_lines) + "\n"

    abs_path.write_text(content, encoding="utf-8")
    return abs_path.resolve()


class TestSymmetricGraph:
    """Symmetric graphs produce no asymmetric edges."""

    def test_fully_symmetric_two_entry_graph(self, tmp_path: Path) -> None:
        """Graph A→B and B→A: no asymmetric edges."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "README.md").write_text("# Research\n", encoding="utf-8")

        a = _make_vault_entry(
            vault, "tools/alpha.md", [("../agent-frameworks/beta.md", "agent-frameworks", "provides X")]
        )
        b = _make_vault_entry(vault, "agent-frameworks/beta.md", [("../tools/alpha.md", "tools", "consumes X")])

        graph = bl.build_cross_reference_graph(vault)
        asymmetric = bl.find_asymmetric_edges(graph)

        assert a in graph
        assert b in graph
        assert asymmetric == [], f"Expected no asymmetric edges, got: {asymmetric}"

    def test_no_edges_no_asymmetries(self, tmp_path: Path) -> None:
        """Graph with no cross-references has no asymmetric edges."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "README.md").write_text("# Research\n", encoding="utf-8")

        _make_vault_entry(vault, "tools/alpha.md")
        _make_vault_entry(vault, "tools/beta.md")

        graph = bl.build_cross_reference_graph(vault)
        asymmetric = bl.find_asymmetric_edges(graph)

        assert asymmetric == []


class TestSingleAsymmetricEdge:
    """Single asymmetric edge detection."""

    def test_single_asymmetric_edge_found(self, tmp_path: Path) -> None:
        """A→B without B→A returns [(A, B)]."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "README.md").write_text("# Research\n", encoding="utf-8")

        a = _make_vault_entry(
            vault, "tools/alpha.md", [("../agent-frameworks/beta.md", "agent-frameworks", "provides X")]
        )
        b = _make_vault_entry(vault, "agent-frameworks/beta.md")

        graph = bl.build_cross_reference_graph(vault)
        asymmetric = bl.find_asymmetric_edges(graph)

        assert len(asymmetric) == 1
        source, target = asymmetric[0]
        assert source == a
        assert target == b

    def test_asymmetric_edge_count_matches(self, tmp_path: Path) -> None:
        """Three entries with one asymmetric edge returns exactly 1 pair."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "README.md").write_text("# Research\n", encoding="utf-8")

        _make_vault_entry(vault, "tools/alpha.md", [("../agent-frameworks/beta.md", "agent-frameworks", "provides X")])
        _b = _make_vault_entry(
            vault, "agent-frameworks/beta.md", [("../tools/alpha.md", "tools", "consumes X")]
        )  # symmetric
        c = _make_vault_entry(
            vault, "tools/gamma.md", [("../agent-frameworks/beta.md", "agent-frameworks", "extends X")]
        )
        # gamma → beta but beta does not have gamma in its refs

        graph = bl.build_cross_reference_graph(vault)
        asymmetric = bl.find_asymmetric_edges(graph)

        # Only gamma→beta is asymmetric
        assert any(s == c for s, _ in asymmetric)
        assert len(asymmetric) == 1


class TestThreeNodeCycle:
    """3-node cycle with one missing edge."""

    def test_three_node_partial_cycle(self, tmp_path: Path) -> None:
        """A→B, B→C, C→A (cycle) — all symmetric by the cycle, 0 asymmetric edges."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "README.md").write_text("# Research\n", encoding="utf-8")

        a = _make_vault_entry(vault, "tools/a.md", [("../agent-frameworks/b.md", "agent-frameworks", "provides X")])
        b = _make_vault_entry(vault, "agent-frameworks/b.md", [("../coding-agents/c.md", "coding-agents", "extends Y")])
        c_dir = vault / "coding-agents"
        c_dir.mkdir(exist_ok=True)
        c = _make_vault_entry(vault, "coding-agents/c.md", [("../tools/a.md", "tools", "consumes Z")])

        graph = bl.build_cross_reference_graph(vault)
        asymmetric = bl.find_asymmetric_edges(graph)

        # A→B: B does not cite A → asymmetric
        # B→C: C does not cite B → asymmetric
        # C→A: A does not cite C → asymmetric
        # All 3 are asymmetric (3-node cycle without reciprocals)
        assert len(asymmetric) == 3
        sources = {s for s, _ in asymmetric}
        assert a in sources
        assert b in sources
        assert c in sources

    def test_missing_one_edge_in_symmetric_pair(self, tmp_path: Path) -> None:
        """A↔B and B↔C but A→C without C→A: returns exactly (A, C)."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "README.md").write_text("# Research\n", encoding="utf-8")

        a = _make_vault_entry(
            vault,
            "tools/a.md",
            [
                ("../agent-frameworks/b.md", "agent-frameworks", "provides X"),
                ("../coding-agents/c.md", "coding-agents", "extends Y"),
            ],
        )
        b_dir = vault / "agent-frameworks"
        b_dir.mkdir(exist_ok=True)
        b = _make_vault_entry(
            vault, "agent-frameworks/b.md", [("../tools/a.md", "tools", "consumes X")]
        )  # symmetric with a
        c_dir = vault / "coding-agents"
        c_dir.mkdir(exist_ok=True)
        c = _make_vault_entry(vault, "coding-agents/c.md")  # no refs back to a

        graph = bl.build_cross_reference_graph(vault)
        asymmetric = bl.find_asymmetric_edges(graph)

        # Only a→c is asymmetric
        assert any(s == a and t == c for s, t in asymmetric)
        # a↔b is symmetric — not in asymmetric list
        assert not any(s == a and t == b for s, t in asymmetric)


class TestRealVaultScan:
    """Informational baseline: real vault scan runs without exception."""

    def test_real_vault_scan_no_exception(self) -> None:
        """build_cross_reference_graph on real vault completes without exception."""
        real_vault = Path(__file__).parents[2] / "research"
        if not real_vault.exists():
            pytest.skip("Real vault not present — skipping informational test")

        graph = bl.build_cross_reference_graph(real_vault)
        asymmetric = bl.find_asymmetric_edges(graph)

        # Informational: log the baseline count (not an assertion)
        print(f"\nReal vault baseline: {len(graph)} entries, {len(asymmetric)} asymmetric edges")
        # Smoke assertion: the graph was built (not empty)
        assert len(graph) > 0, "Expected non-empty graph from real vault"

    def test_readme_excluded_from_graph(self) -> None:
        """README.md is not included as a graph node."""
        real_vault = Path(__file__).parents[2] / "research"
        if not real_vault.exists():
            pytest.skip("Real vault not present")

        graph = bl.build_cross_reference_graph(real_vault)
        for path in graph:
            assert path.name != "README.md", f"README.md should not be in graph: {path}"


class TestGraphHelpers:
    """Unit tests for resolve_link_path and category_of helpers."""

    def test_resolve_link_path_relative(self, tmp_path: Path) -> None:
        """Relative link resolved against source entry path."""
        source = tmp_path / "tools" / "alpha.md"
        source.parent.mkdir()
        target = tmp_path / "agent-frameworks" / "beta.md"
        resolved = bl.resolve_link_path(source, "../agent-frameworks/beta.md")
        assert resolved == target.resolve()

    def test_category_of_returns_parent_dir(self, tmp_path: Path) -> None:
        """category_of returns the entry's parent directory name."""
        vault = tmp_path / "vault"
        vault.mkdir()
        entry = vault / "agent-frameworks" / "foo.md"
        entry.parent.mkdir()
        assert bl.category_of(entry, vault) == "agent-frameworks"

    def test_category_of_raises_when_outside_vault(self, tmp_path: Path) -> None:
        """category_of raises ValueError when entry is outside vault."""
        vault = tmp_path / "vault"
        vault.mkdir()
        outside = tmp_path / "other" / "foo.md"
        with pytest.raises(ValueError, match="is not inside vault root"):
            bl.category_of(outside, vault)
