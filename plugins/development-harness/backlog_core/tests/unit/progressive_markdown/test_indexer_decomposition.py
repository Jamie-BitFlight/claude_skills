"""TEST C3: MarkdownIndexer.build() decomposition gate + behavioral equivalence.

These tests serve two purposes:

1. **PLR lint-gate** (``TestPLRLintGate``): Asserts that ``indexer.py`` passes
   ``ruff check --select PLR0915,PLR0914``.  This test is deliberately RED
   before T07 (the C3 refactoring task) because the monolithic ``build()``
   currently has 74 statements (PLR0915 limit: 50) and 40 local variables
   (PLR0914 limit: 15).  It becomes GREEN after T07 decomposes ``build()``.

2. **Behavioral equivalence** (remaining test classes): Characterise the
   current observable output of ``MarkdownIndexer.build()`` on a
   representative multi-section, multi-heading, multi-code-block document.
   These tests are GREEN before and after T07 — they pin the behavioral
   contract the implementer must preserve during refactoring.

Coverage required by T06 acceptance criteria:
- Nested heading hierarchy (h1 → h2 → h3)
- Multiple sibling h2 sections (selector sibling-index increment)
- Multiple fenced code blocks with language tags
- Parent/child section relationships and child ordering
- Slug and selector generation
- ``body_span`` and ``heading_span`` boundary arithmetic

Running this file before T07 should produce:
  FAILED test_indexer_build_passes_plr_complexity_gates (the lint-gate, RED)
  PASSED everything else (behavioral characterisation, GREEN)
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from progressive_markdown.indexer import MarkdownIndexer
from progressive_markdown.parser import MarkdownItParser

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Absolute path to the file under test.
# parents[0] = progressive_markdown/   (this test's directory)
# parents[1] = unit/
# parents[2] = tests/
# parents[3] = backlog_core/
# parents[4] = plugins/development-harness/
_INDEXER_PATH = Path(__file__).parents[4] / "progressive_markdown" / "indexer.py"

# ---------------------------------------------------------------------------
# Characterisation markdown fixture
# ---------------------------------------------------------------------------
# 23 lines (0-indexed).  Line numbers serve as ground-truth for all
# body_span / heading_span assertions below.
#
#  0: # Title
#  1: (blank)
#  2: Intro prose.
#  3: (blank)
#  4: ## Section A
#  5: (blank)
#  6: Body A.
#  7: (blank)
#  8: ```python
#  9: print(42)
# 10: ```
# 11: (blank)
# 12: ### Sub A
# 13: (blank)
# 14: Sub body.
# 15: (blank)
# 16: ## Section B
# 17: (blank)
# 18: Body B.
# 19: (blank)
# 20: ```bash
# 21: echo hi
# 22: ```
_CHARACTERIZATION_MD = (
    "# Title\n"
    "\n"
    "Intro prose.\n"
    "\n"
    "## Section A\n"
    "\n"
    "Body A.\n"
    "\n"
    "```python\n"
    "print(42)\n"
    "```\n"
    "\n"
    "### Sub A\n"
    "\n"
    "Sub body.\n"
    "\n"
    "## Section B\n"
    "\n"
    "Body B.\n"
    "\n"
    "```bash\n"
    "echo hi\n"
    "```\n"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def document():
    """Build and return a MarkdownDocument from _CHARACTERIZATION_MD."""
    parser = MarkdownItParser()
    result = parser.parse("char.md", _CHARACTERIZATION_MD)
    return MarkdownIndexer().build(result)


# ---------------------------------------------------------------------------
# PLR lint-gate — RED pre-fix, GREEN post-fix
# ---------------------------------------------------------------------------


class TestPLRLintGate:
    """ruff PLR0915/PLR0914 gate on indexer.py.

    This class is deliberately RED before T07 runs.  The monolithic
    ``build()`` currently violates both rules (74 statements, 40 locals).
    After T07 decomposes it, this test becomes GREEN, proving the refactoring
    resolved the complexity violations.
    """

    def test_indexer_build_passes_plr_complexity_gates(self) -> None:
        """ruff --select PLR0915,PLR0914 must exit 0 on indexer.py after decomposition.

        Failing pre-fix proves the gate is wired and detects the violation.
        Passing post-fix proves decomposition succeeded.
        """
        result = subprocess.run(
            ["ruff", "check", "--select", "PLR0915,PLR0914", str(_INDEXER_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"PLR violations remain in indexer.py — T07 refactoring incomplete:\n"
            f"{result.stdout}"
        )


# ---------------------------------------------------------------------------
# TestRootSectionOrdering
# ---------------------------------------------------------------------------


class TestRootSectionOrdering:
    """root_section_ids reflects insertion order of top-level headings."""

    def test_one_root_section_for_single_h1(self, document) -> None:
        """A document with one h1 has exactly one root section id."""
        assert len(document.root_section_ids) == 1

    def test_root_section_title_is_title(self, document) -> None:
        """The sole root section id resolves to the 'Title' heading."""
        root_id = document.root_section_ids[0]
        assert document.sections[root_id].title == "Title"

    def test_four_total_sections(self, document) -> None:
        """Document with h1/h2/h3/h2 headings has exactly 4 sections."""
        assert len(document.sections) == 4


# ---------------------------------------------------------------------------
# TestSelectorAndSlugGeneration
# ---------------------------------------------------------------------------


class TestSelectorAndSlugGeneration:
    """Selectors encode heading depth and sibling index; slugs are URL-safe."""

    def test_h1_selector_is_h1_1(self, document) -> None:
        """First (and only) h1 gets selector 'h1.1'."""
        assert "h1.1" in document.sections_by_selector

    def test_h1_slug_is_title(self, document) -> None:
        """'Title' heading produces slug 'title'."""
        sid = document.sections_by_selector["h1.1"]
        assert document.sections[sid].slug == "title"

    def test_first_h2_selector_is_h2_1_1(self, document) -> None:
        """First h2 (child of h1.1) gets selector 'h2.1.1'."""
        assert "h2.1.1" in document.sections_by_selector

    def test_first_h2_slug_is_section_a(self, document) -> None:
        """'Section A' heading produces slug 'section-a'."""
        sid = document.sections_by_selector["h2.1.1"]
        assert document.sections[sid].slug == "section-a"

    def test_h3_selector_is_h3_1_1_1(self, document) -> None:
        """h3 under h2.1.1 gets selector 'h3.1.1.1'."""
        assert "h3.1.1.1" in document.sections_by_selector

    def test_h3_slug_is_sub_a(self, document) -> None:
        """'Sub A' heading produces slug 'sub-a'."""
        sid = document.sections_by_selector["h3.1.1.1"]
        assert document.sections[sid].slug == "sub-a"

    def test_second_h2_selector_increments_sibling_index(self, document) -> None:
        """Second h2 sibling gets selector 'h2.1.2' (sibling index 2, not 1)."""
        assert "h2.1.2" in document.sections_by_selector

    def test_second_h2_slug_is_section_b(self, document) -> None:
        """'Section B' heading produces slug 'section-b'."""
        sid = document.sections_by_selector["h2.1.2"]
        assert document.sections[sid].slug == "section-b"

    def test_sections_by_slug_contains_all_four_slugs(self, document) -> None:
        """sections_by_slug keys match the four expected slugs exactly."""
        assert set(document.sections_by_slug.keys()) == {
            "title",
            "section-a",
            "sub-a",
            "section-b",
        }

    def test_sections_by_selector_contains_all_four_selectors(self, document) -> None:
        """sections_by_selector keys match the four expected selectors exactly."""
        assert set(document.sections_by_selector.keys()) == {
            "h1.1",
            "h2.1.1",
            "h3.1.1.1",
            "h2.1.2",
        }


# ---------------------------------------------------------------------------
# TestParentChildRelationships
# ---------------------------------------------------------------------------


class TestParentChildRelationships:
    """Parent IDs and child_ids lists reflect heading nesting depth."""

    def test_h1_has_two_direct_children(self, document) -> None:
        """Title (h1) has exactly two direct children."""
        root_id = document.root_section_ids[0]
        assert len(document.sections[root_id].child_ids) == 2

    def test_h1_children_are_section_a_then_section_b(self, document) -> None:
        """Title's children are Section A and Section B in document order."""
        root_id = document.root_section_ids[0]
        child_titles = [
            document.sections[cid].title
            for cid in document.sections[root_id].child_ids
        ]
        assert child_titles == ["Section A", "Section B"]

    def test_section_a_has_one_child_sub_a(self, document) -> None:
        """Section A has exactly one child: Sub A."""
        sid = document.sections_by_selector["h2.1.1"]
        section = document.sections[sid]
        assert len(section.child_ids) == 1
        assert document.sections[section.child_ids[0]].title == "Sub A"

    def test_sub_a_is_leaf_with_no_children(self, document) -> None:
        """Sub A (h3) is a leaf section with an empty child_ids list."""
        sid = document.sections_by_selector["h3.1.1.1"]
        assert document.sections[sid].child_ids == []

    def test_section_b_is_leaf_with_no_children(self, document) -> None:
        """Section B (h2) is a leaf section with an empty child_ids list."""
        sid = document.sections_by_selector["h2.1.2"]
        assert document.sections[sid].child_ids == []

    def test_both_h2s_have_h1_as_parent(self, document) -> None:
        """Both h2 sections have the h1 Title section as their direct parent."""
        root_id = document.root_section_ids[0]
        sec_a_id = document.sections_by_selector["h2.1.1"]
        sec_b_id = document.sections_by_selector["h2.1.2"]
        assert document.sections[sec_a_id].parent_id == root_id
        assert document.sections[sec_b_id].parent_id == root_id

    def test_sub_a_parent_is_section_a(self, document) -> None:
        """Sub A's parent is Section A (not Title)."""
        sec_a_id = document.sections_by_selector["h2.1.1"]
        sub_a_id = document.sections_by_selector["h3.1.1.1"]
        assert document.sections[sub_a_id].parent_id == sec_a_id

    def test_h1_has_no_parent(self, document) -> None:
        """Root section (h1) has parent_id=None."""
        root_id = document.root_section_ids[0]
        assert document.sections[root_id].parent_id is None


# ---------------------------------------------------------------------------
# TestCodeBlocks
# ---------------------------------------------------------------------------


class TestCodeBlocks:
    """Code blocks are attributed to sections with correct language and spans."""

    def test_two_code_blocks_extracted(self, document) -> None:
        """Document with two fenced code blocks produces exactly two CodeBlock entries."""
        assert len(document.code_blocks) == 2

    def test_python_block_has_language_python(self, document) -> None:
        """First code block (code_0001) has language 'python'."""
        assert document.code_blocks["code_0001"].language == "python"

    def test_python_block_attributed_to_section_a(self, document) -> None:
        """Python block section_id resolves to 'Section A'."""
        cb = document.code_blocks["code_0001"]
        assert cb.section_id is not None
        assert document.sections[cb.section_id].title == "Section A"

    def test_python_block_span_is_lines_8_to_10(self, document) -> None:
        """Python block fence occupies lines 8-10 inclusive (0-based)."""
        span = document.code_blocks["code_0001"].span
        assert span is not None
        assert span.start_line == 8
        assert span.end_line == 10

    def test_bash_block_has_language_bash(self, document) -> None:
        """Second code block (code_0002) has language 'bash'."""
        assert document.code_blocks["code_0002"].language == "bash"

    def test_bash_block_attributed_to_section_b(self, document) -> None:
        """Bash block section_id resolves to 'Section B'."""
        cb = document.code_blocks["code_0002"]
        assert cb.section_id is not None
        assert document.sections[cb.section_id].title == "Section B"

    def test_bash_block_span_is_lines_20_to_22(self, document) -> None:
        """Bash block fence occupies lines 20-22 inclusive (0-based)."""
        span = document.code_blocks["code_0002"].span
        assert span is not None
        assert span.start_line == 20
        assert span.end_line == 22

    def test_section_a_code_block_ids_contains_python_block(self, document) -> None:
        """Section A code_block_ids is exactly ['code_0001']."""
        sec_a_id = document.sections_by_selector["h2.1.1"]
        assert document.sections[sec_a_id].code_block_ids == ["code_0001"]

    def test_section_b_code_block_ids_contains_bash_block(self, document) -> None:
        """Section B code_block_ids is exactly ['code_0002']."""
        sec_b_id = document.sections_by_selector["h2.1.2"]
        assert document.sections[sec_b_id].code_block_ids == ["code_0002"]


# ---------------------------------------------------------------------------
# TestBodySpanBoundaries
# ---------------------------------------------------------------------------


class TestBodySpanBoundaries:
    """body_span and heading_span encode precise line ranges for each section.

    The body_span boundaries are the core contract T07 must preserve:
    body starts on the line after the heading and ends on the line before
    the first child heading (or on the last line of the section for leaves).
    These tests pin the span arithmetic so any regression is immediately
    visible.
    """

    def test_h1_heading_span_is_line_0_only(self, document) -> None:
        """h1 'Title' heading occupies only line 0 (start_line == end_line == 0)."""
        root_id = document.root_section_ids[0]
        hs = document.sections[root_id].heading_span
        assert hs.start_line == 0
        assert hs.end_line == 0

    def test_h1_body_span_covers_intro_prose_lines_1_to_3(self, document) -> None:
        """h1 body (intro prose) spans lines 1-3, before the first h2 at line 4."""
        root_id = document.root_section_ids[0]
        bs = document.sections[root_id].body_span
        assert bs.start_line == 1
        assert bs.end_line == 3

    def test_section_a_heading_span_is_line_4_only(self, document) -> None:
        """Section A heading occupies only line 4."""
        sec_a_id = document.sections_by_selector["h2.1.1"]
        hs = document.sections[sec_a_id].heading_span
        assert hs.start_line == 4
        assert hs.end_line == 4

    def test_section_a_body_span_ends_before_sub_a_at_line_12(self, document) -> None:
        """Section A body spans lines 5-11 (line before Sub A heading at 12)."""
        sec_a_id = document.sections_by_selector["h2.1.1"]
        bs = document.sections[sec_a_id].body_span
        assert bs.start_line == 5
        assert bs.end_line == 11

    def test_sub_a_heading_span_is_line_12_only(self, document) -> None:
        """Sub A heading occupies only line 12."""
        sub_a_id = document.sections_by_selector["h3.1.1.1"]
        hs = document.sections[sub_a_id].heading_span
        assert hs.start_line == 12
        assert hs.end_line == 12

    def test_sub_a_body_span_is_leaf_lines_13_to_15(self, document) -> None:
        """Sub A body (leaf, no children) spans lines 13-15."""
        sub_a_id = document.sections_by_selector["h3.1.1.1"]
        bs = document.sections[sub_a_id].body_span
        assert bs.start_line == 13
        assert bs.end_line == 15

    def test_section_b_heading_span_is_line_16_only(self, document) -> None:
        """Section B heading occupies only line 16."""
        sec_b_id = document.sections_by_selector["h2.1.2"]
        hs = document.sections[sec_b_id].heading_span
        assert hs.start_line == 16
        assert hs.end_line == 16

    def test_section_b_body_span_extends_to_end_of_document(self, document) -> None:
        """Section B body (leaf) spans lines 17-22 (last line of the document)."""
        sec_b_id = document.sections_by_selector["h2.1.2"]
        bs = document.sections[sec_b_id].body_span
        assert bs.start_line == 17
        assert bs.end_line == 22
