"""TEST C3: MarkdownIndexer.build() decomposition gate + behavioral equivalence.

These tests serve two purposes:

Behavioral equivalence: characterise the
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

The configured Ruff hook validates linting; this file covers behavioral
characterisation only.
"""

from __future__ import annotations

import pytest
from progressive_markdown.indexer import MarkdownIndexer
from progressive_markdown.parser import MarkdownItParser

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
# Compound output contracts (coexist with the granular characterisation tests)
# ---------------------------------------------------------------------------


class TestIndexerOutputContracts:
    """Full output contracts for the characteristic markdown document."""

    def test_indexer_build_root_sections_contract(self, document) -> None:
        """The indexer retains the characteristic document's root topology."""
        root_titles = [document.sections[section_id].title for section_id in document.root_section_ids]

        assert root_titles == ["Title"]
        assert len(document.sections) == 4

    def test_indexer_build_selector_and_slug_contract(self, document) -> None:
        """Selectors and slugs retain nested and sibling addressing semantics."""
        selector_to_slug = {
            selector: document.sections[section_id].slug
            for selector, section_id in document.sections_by_selector.items()
        }

        assert selector_to_slug == {"h1.1": "title", "h2.1.1": "section-a", "h3.1.1.1": "sub-a", "h2.1.2": "section-b"}
        assert set(document.sections_by_slug) == {"title", "section-a", "sub-a", "section-b"}
        assert set(document.sections_by_selector) == {"h1.1", "h2.1.1", "h3.1.1.1", "h2.1.2"}

    def test_indexer_build_hierarchy_contract(self, document) -> None:
        """Parents, ordered direct children, and leaves retain the section tree."""
        hierarchy = {
            section.title: {
                "parent": document.sections[section.parent_id].title if section.parent_id else None,
                "children": [document.sections[child_id].title for child_id in section.child_ids],
            }
            for section in document.sections.values()
        }

        assert hierarchy == {
            "Title": {"parent": None, "children": ["Section A", "Section B"]},
            "Section A": {"parent": "Title", "children": ["Sub A"]},
            "Sub A": {"parent": "Section A", "children": []},
            "Section B": {"parent": "Title", "children": []},
        }

    def test_indexer_build_fence_contract(self, document) -> None:
        """Fences retain order, metadata, source spans, and section ownership."""
        fences = {
            code_id: {
                "language": block.language,
                "span": (block.span.start_line, block.span.end_line) if block.span else None,
                "section": document.sections[block.section_id].title if block.section_id else None,
            }
            for code_id, block in document.code_blocks.items()
        }
        section_code_ids = {
            document.sections[document.sections_by_selector[selector]].title: document.sections[
                document.sections_by_selector[selector]
            ].code_block_ids
            for selector in ("h2.1.1", "h2.1.2")
        }

        assert fences == {
            "code_0001": {"language": "python", "span": (8, 10), "section": "Section A"},
            "code_0002": {"language": "bash", "span": (20, 22), "section": "Section B"},
        }
        assert section_code_ids == {"Section A": ["code_0001"], "Section B": ["code_0002"]}

    def test_indexer_build_section_span_contract(self, document) -> None:
        """Heading and body spans retain inclusive parent and leaf boundaries."""
        spans = {
            section.title: {
                "heading": (section.heading_span.start_line, section.heading_span.end_line),
                "body": (section.body_span.start_line, section.body_span.end_line),
            }
            for section in document.sections.values()
        }

        assert spans == {
            "Title": {"heading": (0, 0), "body": (1, 3)},
            "Section A": {"heading": (4, 4), "body": (5, 11)},
            "Sub A": {"heading": (12, 12), "body": (13, 15)},
            "Section B": {"heading": (16, 16), "body": (17, 22)},
        }
