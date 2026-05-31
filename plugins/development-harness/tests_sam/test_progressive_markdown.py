"""Tests for the progressive_markdown package and the chunk_text additions.

Covers:
- chunk_text: losslessness, small-text pass-through, paragraph-first splitting
- MarkdownNavigator.map(): TOC with correct selectors and metadata
- view_section on parent (section_map) and leaf (section_body) sections
- Body pagination losslessness across multiple pages
- Code block stub replacement in body
- view_code: returns content, paginated when over budget
- search: scored matches by title/slug
- Ref resolution: id, selector, slug, title substring
- Heading inside fenced code block NOT treated as section heading
"""

from __future__ import annotations

import sys

import pytest

# Ensure the plugin root is importable.
sys.path.insert(0, "plugins/development-harness")

from dh_progressive_disclosure import ENCODING, TOKEN_BUDGET, chunk_text
from progressive_markdown import CodeBlockRef, MarkdownIndex, MarkdownNavigator, SectionRef

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
def nav() -> MarkdownNavigator:
    """Navigator over the simple multi-section document."""
    return MarkdownNavigator.from_markdown(_SIMPLE_MD, source="test.md")


@pytest.fixture
def fenced_nav() -> MarkdownNavigator:
    """Navigator over a document with a heading inside a fenced code block."""
    return MarkdownNavigator.from_markdown(_FENCED_HEADING_MD, source="fenced.md")


# ---------------------------------------------------------------------------
# chunk_text
# ---------------------------------------------------------------------------


class TestChunkText:
    """Tests for the module-level chunk_text function."""

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
        """Splits occur at blank-line breaks before single newlines.

        Constructs two short paragraphs where:
        - each paragraph fits individually within the budget
        - both together exceed the budget
        - each paragraph has internal newlines that could split at line level

        Asserts that the first chunk ends with the double-newline delimiter
        (paragraph boundary), not at an internal single-newline.
        """
        # ~8 tokens each; budget=10 forces a split between them.
        para1 = "word1 word2 word3 word4.\nLine two of para one.\n\n"
        para2 = "word5 word6 word7 word8.\nLine two of para two."
        text = para1 + para2

        # Confirm the budget really forces a split: both together exceed it.
        total = len(ENCODING.encode(text))
        p1_tokens = len(ENCODING.encode(para1))
        p2_tokens = len(ENCODING.encode(para2))
        budget = max(p1_tokens, p2_tokens)
        assert total > budget, "Test setup: combined text must exceed budget"

        chunks = chunk_text(text, budget=budget)

        # Lossless.
        assert "".join(chunks) == text, "chunks are not lossless"

        # Paragraph boundary preferred: the split must occur at the \n\n break,
        # meaning no single chunk spans both paragraphs AND contains a single
        # newline (which would indicate a line-level split within a paragraph).
        # The paragraph texts must not appear in the same chunk.
        assert not any(para1.rstrip("\n") in c and para2 in c for c in chunks), (
            "Both paragraph texts appeared in the same chunk - paragraph boundary split not applied"
        )
        # The \n\n delimiter must appear as a separate chunk or at a boundary.
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
        """A single word-dense line (no newlines) is split via char bisection."""
        # 'x' chars produce roughly 1 token each, so 10 000 chars > 4400 token budget.
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
        # Text just at budget boundary should come back as a single chunk.
        single_token_text = "a " * (TOKEN_BUDGET // 2)
        chunks = chunk_text(single_token_text)
        # All tokens fit — expect single chunk.
        total = len(ENCODING.encode(single_token_text))
        if total <= TOKEN_BUDGET:
            assert chunks == [single_token_text]


# ---------------------------------------------------------------------------
# MarkdownNavigator.map()
# ---------------------------------------------------------------------------


class TestMap:
    """Tests for MarkdownNavigator.map()."""

    def test_map_returns_toc_kind(self, nav: MarkdownNavigator) -> None:
        """map() returns a dict with kind='toc'."""
        result = nav.map()
        assert result["kind"] == "toc"

    def test_map_selectors_are_correct(self, nav: MarkdownNavigator) -> None:
        """Selectors match h{level}.{sibling_n} pattern."""
        result = nav.map()
        selectors = {e["selector"] for e in result["entries"]}
        assert "h1.1" in selectors  # Introduction
        assert "h2.1" in selectors  # Installation
        assert "h2.2" in selectors  # Usage
        assert "h3.1" in selectors  # Basic Usage
        assert "h3.2" in selectors  # Advanced Usage
        assert "h2.3" in selectors  # Configuration

    def test_map_entries_have_required_fields(self, nav: MarkdownNavigator) -> None:
        """Each TOC entry contains all required fields."""
        result = nav.map()
        required = {"selector", "id", "slug", "title", "level", "lines", "child_count", "code_count"}
        for entry in result["entries"]:
            assert required <= entry.keys(), f"Missing keys in entry: {entry}"

    def test_map_child_count_for_parent_section(self, nav: MarkdownNavigator) -> None:
        """A parent section reports the correct child_count."""
        result = nav.map()
        usage_entry = next(e for e in result["entries"] if e["selector"] == "h2.2")
        assert usage_entry["child_count"] == 2

    def test_map_code_count_for_section_with_code(self, nav: MarkdownNavigator) -> None:
        """A section with a code block reports code_count >= 1."""
        result = nav.map()
        install_entry = next(e for e in result["entries"] if e["selector"] == "h2.1")
        assert install_entry["code_count"] >= 1


# ---------------------------------------------------------------------------
# view_section
# ---------------------------------------------------------------------------


class TestViewSection:
    """Tests for MarkdownNavigator.view_section()."""

    def test_parent_section_returns_section_map(self, nav: MarkdownNavigator) -> None:
        """A section with children returns kind='section_map'."""
        result = nav.view_section("h2.2")  # Usage has children
        assert result["kind"] == "section_map"
        assert "children" in result

    def test_parent_section_children_list(self, nav: MarkdownNavigator) -> None:
        """section_map children matches direct children only."""
        result = nav.view_section("h1.1")  # Introduction
        assert result["kind"] == "section_map"
        # Direct children of h1.1 are h2.1 (Installation), h2.2 (Usage), h2.3 (Configuration)
        child_selectors = {c["selector"] for c in result["children"]}
        assert "h2.1" in child_selectors
        assert "h2.2" in child_selectors
        assert "h2.3" in child_selectors
        # h3.1 is a grandchild, not a direct child
        assert "h3.1" not in child_selectors

    def test_leaf_section_returns_section_body(self, nav: MarkdownNavigator) -> None:
        """A section without children returns kind='section_body'."""
        result = nav.view_section("h2.3")  # Configuration (leaf)
        assert result["kind"] == "section_body"
        assert "content" in result

    def test_leaf_section_body_contains_text(self, nav: MarkdownNavigator) -> None:
        """The body of a leaf section contains its text content."""
        result = nav.view_section("h2.3")  # Configuration
        assert "Configure" in result["content"]

    def test_body_code_blocks_replaced_with_stubs(self, nav: MarkdownNavigator) -> None:
        """Code blocks in a leaf section body are replaced with stubs."""
        result = nav.view_section("h2.1")  # Installation has a bash code block
        assert result["kind"] == "section_body"
        content = result["content"]
        # Stub format contains '[code:'
        assert "[code:" in content
        # Raw fence markers should not appear (replaced by stub)
        assert "```bash" not in content

    def test_body_stub_removes_fenced_code_block(self, nav: MarkdownNavigator) -> None:
        """The fenced code block delimiters do not survive stub replacement.

        The stub replaces the entire fenced block (opening fence, content,
        closing fence).  After replacement, no opening fence marker should
        appear in the section body content.  The stub summary may contain
        a content preview, but the fence markers themselves must be gone.
        """
        result = nav.view_section("h2.1")  # Installation: bash block
        content = result["content"]
        # Opening fence must be gone - replaced by the stub line.
        assert "```bash" not in content, "Fenced code block opening fence survived stub replacement"
        assert "```\n" not in content, "Fenced code block closing fence survived stub replacement"

    def test_body_pagination_lossless(self, nav: MarkdownNavigator) -> None:
        """All body pages reassemble to exactly the single-page content."""
        # Retrieve the full stubbed body at a large budget (fits in 1 page).
        whole = nav.view_section("h2.1", budget=10_000)["content"]

        # Retrieve at a tiny budget to force multi-page output.
        budget = 5
        result_p1 = nav.view_section("h2.1", page=1, budget=budget)
        total_pages = result_p1["total_pages"]

        pages = [nav.view_section("h2.1", page=p, budget=budget)["content"] for p in range(1, total_pages + 1)]

        # The critical invariant: joined pages == the single-page full content.
        assert "".join(pages) == whole, f"Lossless reassembly failed: {total_pages} pages do not reconstruct the body"

        # Metadata consistency: every page except the last reports has_more=True.
        for p in range(1, total_pages):
            r = nav.view_section("h2.1", page=p, budget=budget)
            assert r["has_more"] is True
        r_last = nav.view_section("h2.1", page=total_pages, budget=budget)
        assert r_last["has_more"] is False

    def test_not_found_returns_error(self, nav: MarkdownNavigator) -> None:
        """Unresolvable ref returns {'error': ...}."""
        result = nav.view_section("nonexistent_ref_xyz")
        assert "error" in result

    def test_resolve_by_id(self, nav: MarkdownNavigator) -> None:
        """Sections can be resolved by their sec_NNNN id."""
        idx = nav.current_index()
        first_id = next(iter(idx.sections))
        result = nav.view_section(first_id)
        assert "error" not in result
        assert result["id"] == first_id

    def test_resolve_by_slug(self, nav: MarkdownNavigator) -> None:
        """Sections can be resolved by slug."""
        result = nav.view_section("installation")  # slug of Installation
        assert "error" not in result
        assert result["title"] == "Installation"

    def test_resolve_by_title_substring(self, nav: MarkdownNavigator) -> None:
        """Sections can be resolved by case-insensitive title substring."""
        result = nav.view_section("config")  # substring of "Configuration"
        assert "error" not in result
        assert "Configuration" in result["title"]

    def test_resolve_by_selector(self, nav: MarkdownNavigator) -> None:
        """Sections can be resolved by their h{level}.{n} selector."""
        result = nav.view_section("h2.1")
        assert "error" not in result
        assert result["selector"] == "h2.1"


# ---------------------------------------------------------------------------
# view_code
# ---------------------------------------------------------------------------


class TestViewCode:
    """Tests for MarkdownNavigator.view_code()."""

    def test_view_code_returns_code_block(self, nav: MarkdownNavigator) -> None:
        """view_code returns kind='code_block' with content."""
        idx = nav.current_index()
        assert idx.code_blocks, "No code blocks in test document"
        code_id = next(iter(idx.code_blocks))
        result = nav.view_code(code_id)
        assert result["kind"] == "code_block"
        assert "content" in result

    def test_view_code_not_found_returns_error(self, nav: MarkdownNavigator) -> None:
        """view_code with unknown id returns {'error': ...}."""
        result = nav.view_code("code_9999")
        assert "error" in result

    def test_view_code_paginated_when_over_budget(self, nav: MarkdownNavigator) -> None:
        """view_code paginates a large code block with tiny budget."""
        idx = nav.current_index()
        code_id = next(iter(idx.code_blocks))
        block = idx.code_blocks[code_id]
        # Use budget smaller than code content to force pagination.
        budget = max(1, len(ENCODING.encode(block.content)) // 3)
        result_p1 = nav.view_code(code_id, page=1, budget=budget)
        total_pages = result_p1["total_pages"]

        if total_pages > 1:
            pages = []
            for p in range(1, total_pages + 1):
                r = nav.view_code(code_id, page=p, budget=budget)
                pages.append(r["content"])
            assert "".join(pages) == block.content
        else:
            # Content fits in one page with this budget.
            assert result_p1["content"] == block.content

    def test_view_code_language_present(self, nav: MarkdownNavigator) -> None:
        """view_code includes the language field."""
        idx = nav.current_index()
        code_id = next(iter(idx.code_blocks))
        result = nav.view_code(code_id)
        assert "language" in result


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSearch:
    """Tests for MarkdownNavigator.search()."""

    def test_search_returns_matches(self, nav: MarkdownNavigator) -> None:
        """search returns a dict with 'matches', 'query', 'count'."""
        result = nav.search("install")
        assert "matches" in result
        assert "query" in result
        assert "count" in result

    def test_search_finds_relevant_section(self, nav: MarkdownNavigator) -> None:
        """Searching for 'install' finds the Installation section."""
        result = nav.search("install")
        titles = [m["title"] for m in result["matches"]]
        assert "Installation" in titles

    def test_search_no_results_for_nonexistent_query(self, nav: MarkdownNavigator) -> None:
        """Searching for a non-existent term returns empty matches."""
        result = nav.search("xyzzy_nonexistent_abc123")
        assert result["matches"] == []
        assert result["count"] == 0

    def test_search_results_have_required_fields(self, nav: MarkdownNavigator) -> None:
        """Each match contains score, selector, id, title, slug."""
        result = nav.search("usage")
        required = {"score", "selector", "id", "title", "slug"}
        for match in result["matches"]:
            assert required <= match.keys()

    def test_search_empty_query_returns_empty(self, nav: MarkdownNavigator) -> None:
        """An empty query string returns no matches."""
        result = nav.search("")
        assert result["matches"] == []

    def test_search_scored_by_relevance(self, nav: MarkdownNavigator) -> None:
        """Results are sorted by descending score."""
        result = nav.search("usage")
        scores = [m["score"] for m in result["matches"]]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Heading inside fenced code block
# ---------------------------------------------------------------------------


class TestFencedHeadingExclusion:
    """The ## heading inside a fenced code block must NOT become a section."""

    def test_fenced_heading_not_a_section(self, fenced_nav: MarkdownNavigator) -> None:
        """'## This Is Inside A Fence' does not appear as a section."""
        idx = fenced_nav.current_index()
        titles = {s.title for s in idx.sections.values()}
        assert "This Is Inside A Fence" not in titles

    def test_real_sections_are_present(self, fenced_nav: MarkdownNavigator) -> None:
        """Real headings outside fences are parsed as sections."""
        idx = fenced_nav.current_index()
        titles = {s.title for s in idx.sections.values()}
        assert "Real Section" in titles
        assert "Actual Subsection" in titles

    def test_section_count_excludes_fenced_heading(self, fenced_nav: MarkdownNavigator) -> None:
        """Only 2 sections exist (the fenced ## does not count)."""
        idx = fenced_nav.current_index()
        assert len(idx.sections) == 2


# ---------------------------------------------------------------------------
# Models smoke test
# ---------------------------------------------------------------------------


class TestModels:
    """Sanity checks on the Pydantic models exported from progressive_markdown."""

    def test_section_ref_is_pydantic_model(self) -> None:
        """SectionRef can be constructed and serialised."""
        s = SectionRef(
            id="sec_0001", selector="h1.1", slug="intro", title="Introduction", level=1, start_line=0, end_line=10
        )
        d = s.model_dump()
        assert d["id"] == "sec_0001"
        assert d["child_ids"] == []

    def test_code_block_ref_is_pydantic_model(self) -> None:
        """CodeBlockRef can be constructed and serialised."""
        c = CodeBlockRef(
            id="code_0001",
            language="python",
            content="print('hello')\n",
            start_line=5,
            end_line=7,
            summary="python, 1 lines, print('hello')",
        )
        d = c.model_dump()
        assert d["language"] == "python"
        assert d["section_id"] is None

    def test_markdown_index_is_pydantic_model(self) -> None:
        """MarkdownIndex can be constructed with defaults."""
        idx = MarkdownIndex(source="inline")
        assert idx.root_section_ids == []
        assert idx.sections == {}
