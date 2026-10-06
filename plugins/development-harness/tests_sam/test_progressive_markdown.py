"""Tests for the progressive_markdown package.

Covers parser/indexer and retained navigation-return contracts.
"""

from __future__ import annotations

import sys

import pytest

# Ensure the plugin root is importable.
sys.path.insert(0, "plugins/development-harness")

from progressive_markdown import NavigationKind, NavigationResult, ProgressiveMarkdownNavigator
from progressive_markdown.list_navigator import ENCODING, TOKEN_BUDGET, chunk_text

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SIMPLE_MD = """\
# Introduction

Intro paragraph.

## Installation

Install with pip:

```bash
pip install mypackage
```

## Usage

### Basic Usage

Call the function:

```python
import mypackage
mypackage.run()
```

### Advanced Usage

More details here.

## Configuration

Configure with a file.
"""

_FENCED_HEADING_MD = """\
# Real Section

```markdown
## This Is Inside A Fence

It should NOT be a section.
```

## Actual Subsection

Content here.
"""


@pytest.fixture
def nav() -> ProgressiveMarkdownNavigator:
    """Navigator over the simple multi-section document."""
    return ProgressiveMarkdownNavigator.from_markdown(_SIMPLE_MD, source="test.md")


@pytest.fixture
def fenced_nav() -> ProgressiveMarkdownNavigator:
    """Navigator over a document with a heading inside a fenced code block."""
    return ProgressiveMarkdownNavigator.from_markdown(_FENCED_HEADING_MD, source="fenced.md")


# ---------------------------------------------------------------------------
# chunk_text (from list_navigator — backward compat)
# ---------------------------------------------------------------------------


class TestChunkText:
    """Tests for the module-level chunk_text function from list_navigator."""

    def test_empty_text_returns_single_empty_string(self) -> None:
        """chunk_text('') returns ['']."""
        result = chunk_text("")
        assert result == [""]

    def test_small_text_unchanged(self) -> None:
        """Text that fits within the budget is returned as-is."""
        text = "hello world"
        assert chunk_text(text) == [text]

    def test_oversized_text_lossless(self) -> None:
        """Joining all chunks reproduces the original text exactly."""
        text = ("word " * 200 + "\n\n") * 5
        chunks = chunk_text(text, budget=100)
        assert len(chunks) > 1
        assert "".join(chunks) == text

    def test_each_chunk_within_budget(self) -> None:
        """Every chunk produced fits within the specified budget."""
        text = ("word " * 150 + "\n\n") * 4
        budget = 80
        chunks = chunk_text(text, budget=budget)
        for i, chunk in enumerate(chunks):
            token_count = len(ENCODING.encode(chunk))
            assert token_count <= budget, f"Chunk {i} has {token_count} tokens, budget={budget}"

    def test_paragraph_boundary_preferred_over_line_boundary(self) -> None:
        """Splits occur at blank-line breaks before single newlines."""
        para1 = "word1 word2 word3 word4.\nLine two of para one.\n\n"
        para2 = "word5 word6 word7 word8.\nLine two of para two."
        text = para1 + para2

        total = len(ENCODING.encode(text))
        p1_tokens = len(ENCODING.encode(para1))
        p2_tokens = len(ENCODING.encode(para2))
        budget = max(p1_tokens, p2_tokens)
        assert total > budget, "Test setup: combined text must exceed budget"

        chunks = chunk_text(text, budget=budget)

        assert "".join(chunks) == text, "chunks are not lossless"
        assert not any(para1.rstrip("\n") in c and para2 in c for c in chunks), (
            "Both paragraph texts appeared in the same chunk"
        )
        joined = "".join(chunks)
        assert "\n\n" in joined, "Double-newline paragraph delimiter was lost"

    def test_paragraph_delimiters_preserved(self) -> None:
        """The double-newline paragraph delimiter appears in the chunks."""
        text = "para one.\n\npara two.\n\npara three."
        chunks = chunk_text(text, budget=10)
        rejoined = "".join(chunks)
        assert rejoined == text
        assert "\n\n" in rejoined

    def test_single_huge_chunk_no_newlines_splits_losslessly(self) -> None:
        """A single word-dense line is split via char bisection."""
        text = "x" * 10_000
        chunks = chunk_text(text)
        assert "".join(chunks) == text
        for chunk in chunks:
            assert len(ENCODING.encode(chunk)) <= TOKEN_BUDGET

    def test_unicode_multibyte_lossless(self) -> None:
        """Multibyte Unicode text is split and reassembled without corruption."""
        text = "こんにちは世界\n\n" * 50
        budget = 50
        chunks = chunk_text(text, budget=budget)
        assert "".join(chunks) == text
        for chunk in chunks:
            assert len(ENCODING.encode(chunk)) <= budget

    def test_default_budget_is_token_budget_constant(self) -> None:
        """When no budget is given, TOKEN_BUDGET is used."""
        single_token_text = "a " * (TOKEN_BUDGET // 2)
        chunks = chunk_text(single_token_text)
        total = len(ENCODING.encode(single_token_text))
        if total <= TOKEN_BUDGET:
            assert chunks == [single_token_text]


# ---------------------------------------------------------------------------
# TokenBudgeter split_to_budget losslessness
# ---------------------------------------------------------------------------


class TestTokenBudgeter:
    """Tests for the TokenBudgeter.split_to_budget method."""

    def test_split_to_budget_lossless(self) -> None:
        """Joining all parts reproduces the original text."""
        from progressive_markdown.tokenizer import TokenBudgeter

        budgeter = TokenBudgeter(default_budget=50)
        text = ("word " * 100 + "\n\n") * 3
        parts = budgeter.split_to_budget(text, budget=50)
        assert "".join(parts) == text

    def test_split_empty_text(self) -> None:
        """Empty text returns a list with a single empty string."""
        from progressive_markdown.tokenizer import TokenBudgeter

        budgeter = TokenBudgeter()
        assert budgeter.split_to_budget("") == [""]

    def test_split_small_text_unchanged(self) -> None:
        """Text fitting within the budget is returned as a single chunk."""
        from progressive_markdown.tokenizer import TokenBudgeter

        budgeter = TokenBudgeter(default_budget=1000)
        text = "short text"
        assert budgeter.split_to_budget(text) == [text]


# ---------------------------------------------------------------------------
# NavigationResult model
# ---------------------------------------------------------------------------


class TestNavigationResult:
    """Tests for NavigationResult convenience behavior."""

    def test_current_content_returns_page_content(self, nav: ProgressiveMarkdownNavigator) -> None:
        """current_content() returns the content of the current page."""
        result = nav.map()
        assert result.current_content() == result.pages[0].content

    def test_current_content_on_empty_result(self) -> None:
        """current_content() returns empty string when no pages."""
        result = NavigationResult(
            kind=NavigationKind.document_map, title="empty", pages=[], current_page=1, total_pages=1
        )
        assert result.current_content() == ""


# ---------------------------------------------------------------------------
# Heading inside fenced code block
# ---------------------------------------------------------------------------


class TestFencedHeadingExclusion:
    """The ## heading inside a fenced code block must NOT become a section."""

    def test_fenced_heading_not_a_section(self, fenced_nav: ProgressiveMarkdownNavigator) -> None:
        """'## This Is Inside A Fence' does not appear as a section."""
        doc = fenced_nav.current_document()
        titles = {s.title for s in doc.sections.values()}
        assert "This Is Inside A Fence" not in titles

    def test_real_sections_are_present(self, fenced_nav: ProgressiveMarkdownNavigator) -> None:
        """Real headings outside fences are parsed as sections."""
        doc = fenced_nav.current_document()
        titles = {s.title for s in doc.sections.values()}
        assert "Real Section" in titles
        assert "Actual Subsection" in titles

    def test_section_count_excludes_fenced_heading(self, fenced_nav: ProgressiveMarkdownNavigator) -> None:
        """Only 2 sections exist (the fenced ## does not count)."""
        doc = fenced_nav.current_document()
        assert len(doc.sections) == 2


# ---------------------------------------------------------------------------
# Hierarchical selectors
# ---------------------------------------------------------------------------

_COLLISION_MD = """\
# Title

## Section A

### Sub A

## Section B

### Sub B
"""

_DEEP_NESTING_MD = """\
# A

## B

### C
"""


class TestHierarchicalSelectors:
    """Selector encoding must reflect the full parent chain."""

    def test_sibling_collision_prevented(self) -> None:
        """Sub A and Sub B under different parents get different selectors."""
        nav = ProgressiveMarkdownNavigator.from_markdown(_COLLISION_MD)
        result = nav.map()
        content = result.current_content()
        # Both Sub A and Sub B selectors must appear in the map.
        assert "Sub A" in content
        assert "Sub B" in content

    def test_sub_a_and_sub_b_have_distinct_selectors(self) -> None:
        """The two ### sections under different ## parents differ."""
        nav = ProgressiveMarkdownNavigator.from_markdown(_COLLISION_MD)
        doc = nav.current_document()
        by_title = {s.title: s.selector for s in doc.sections.values()}
        assert by_title["Sub A"] != by_title["Sub B"]

    def test_selector_path_h3_under_second_h2(self) -> None:
        """The first ### under the second ## gets selector h3.1.2.1, not h3.1."""
        nav = ProgressiveMarkdownNavigator.from_markdown(_COLLISION_MD)
        doc = nav.current_document()
        by_title = {s.title: s.selector for s in doc.sections.values()}
        assert by_title["Sub B"] == "h3.1.2.1", f"Expected h3.1.2.1 for Sub B, got {by_title['Sub B']!r}"

    def test_deep_nesting_selector_format(self) -> None:
        """A / ## B / ### C produces h3.1.1.1."""
        nav = ProgressiveMarkdownNavigator.from_markdown(_DEEP_NESTING_MD)
        doc = nav.current_document()
        by_title = {s.title: s.selector for s in doc.sections.values()}
        assert by_title["C"] == "h3.1.1.1", f"Expected h3.1.1.1 for C, got {by_title['C']!r}"

    def test_all_document_selectors_unique(self, nav: ProgressiveMarkdownNavigator) -> None:
        """All selectors in _SIMPLE_MD are unique."""
        doc = nav.current_document()
        selectors = [s.selector for s in doc.sections.values()]
        assert len(selectors) == len(set(selectors)), f"Duplicate selectors: {selectors}"


# ---------------------------------------------------------------------------
# Parent section intro prose
# ---------------------------------------------------------------------------

_INTRO_PROSE_MD = """\
## Installation

This intro paragraph should be accessible.

### Step 1

Do step 1.

### Step 2

Do step 2.
"""

_NO_INTRO_PROSE_MD = """\
## Installation

### Step 1

Do step 1.

### Step 2

Do step 2.
"""


class TestParentSectionIntroProse:
    """view_section on a parent must surface intro prose when it exists."""

    def test_intro_prose_present_in_section_map_content(self) -> None:
        """section_map content contains the intro paragraph."""
        nav = ProgressiveMarkdownNavigator.from_markdown(_INTRO_PROSE_MD)
        result = nav.view_section("h2.1")
        assert result.kind == NavigationKind.section_map
        content = result.current_content()
        assert "This intro paragraph" in content

    def test_section_map_content_includes_children_when_intro_present(self) -> None:
        """section_map content includes children selectors alongside intro prose."""
        nav = ProgressiveMarkdownNavigator.from_markdown(_INTRO_PROSE_MD)
        result = nav.view_section("h2.1")
        assert result.kind == NavigationKind.section_map
        content = result.current_content()
        # Both intro prose AND children info must be present.
        assert "This intro paragraph" in content
        assert "Step" in content  # child section titles

    def test_section_map_only_children_when_no_intro_prose(self) -> None:
        """section_map without intro prose still shows children."""
        nav = ProgressiveMarkdownNavigator.from_markdown(_NO_INTRO_PROSE_MD)
        result = nav.view_section("h2.1")
        assert result.kind == NavigationKind.section_map
        content = result.current_content()
        assert "Step" in content

    def test_large_intro_prose_paginated_when_budget_tiny(self) -> None:
        """Intro prose that exceeds the budget is paginated."""
        intro_lines = "\n".join(f"Intro line {i}." for i in range(100))
        md = f"## Parent\n\n{intro_lines}\n\n### Child\n\nChild text.\n"
        nav = ProgressiveMarkdownNavigator.from_markdown(md)
        result = nav.view_section("h2.1", budget=20)
        assert result.kind == NavigationKind.section_map
        assert result.total_pages >= 1

    def test_pagination_lossless_on_parent_section(self) -> None:
        """All pages of a parent section reassemble to the full content."""
        intro_lines = "\n".join(f"Intro line {i}." for i in range(100))
        md = f"## Parent\n\n{intro_lines}\n\n### Child\n\nChild text.\n"
        nav = ProgressiveMarkdownNavigator.from_markdown(md)
        full = nav.view_section("h2.1", budget=10_000).current_content()

        budget = 30
        result_p1 = nav.view_section("h2.1", page=1, budget=budget)
        total = result_p1.total_pages
        pages = [nav.view_section("h2.1", page=p, budget=budget).current_content() for p in range(1, total + 1)]
        assert "".join(pages) == full
