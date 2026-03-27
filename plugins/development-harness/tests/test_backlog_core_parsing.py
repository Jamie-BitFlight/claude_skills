"""Tests for backlog_core/parsing.py — pure parsing functions with no GitHub or Typer dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest
from backlog_core.models import BacklogItem, ViewItemResult
from backlog_core.parsing import (
    _parse_frontmatter,
    append_or_replace_section,
    build_backlog_frontmatter,
    build_issue_body,
    build_issue_body_from_file,
    find_fuzzy_duplicates,
    find_item,
    normalize_issue_title,
    parse_item_file,
    title_to_slug,
    view_result_from_local_item,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

# ---------------------------------------------------------------------------
# Test data
#
# NOTE: The nested-metadata stringification bug in _parse_frontmatter was
# fixed in commit 0e0611f.  Tests below that use flat frontmatter were written
# before the fix; their coverage of flat-key parsing paths remains valid and
# intentional.
# ---------------------------------------------------------------------------

# Nested-metadata format (produced by build_backlog_frontmatter) — only name/description accessible
_NESTED_META_FRONTMATTER = """\
---
name: My Test Item
description: A test description
metadata:
  source: test-source
  added: '2026-01-01'
  priority: P1
  type: Feature
  status: open
  topic: my-test-item
---
Body content here.
"""

# Legacy flat format — all top-level keys are accessible
_FLAT_FRONTMATTER = """\
---
title: Legacy Title
source: legacy-source
added: '2025-12-01'
priority: P0
status: open
---
Legacy body.
"""

# Flat format with all fields needed for parse_item_file tests
_FLAT_WITH_ALL_FIELDS = """\
---
name: Flat Item
description: flat description
source: flat-source
added: '2026-01-01'
priority: P1
status: open
issue: '#42'
plan: plan/tasks-1-test.md
---
"""

_FLAT_DONE = """\
---
name: Done Item
description: completed
source: test
added: '2026-01-01'
priority: P1
status: done
---
"""

_NO_FRONTMATTER = "Just plain body text with no YAML."


# ---------------------------------------------------------------------------
# parse_item_file
# ---------------------------------------------------------------------------


class TestParseItemFile:
    """Tests for parse_item_file(text, path) -> BacklogItem."""

    def test_parse_item_file_nested_meta_sets_title(self, tmp_path: Path) -> None:
        # name is a top-level key — survives stringification
        item = parse_item_file(_NESTED_META_FRONTMATTER, tmp_path / "item.md")

        assert item.title == "My Test Item"

    def test_parse_item_file_nested_meta_sets_description(self, tmp_path: Path) -> None:
        # description is a top-level key — survives stringification
        item = parse_item_file(_NESTED_META_FRONTMATTER, tmp_path / "item.md")

        assert item.description == "A test description"

    def test_parse_item_file_nested_meta_body_captured_as_raw_body(self, tmp_path: Path) -> None:
        item = parse_item_file(_NESTED_META_FRONTMATTER, tmp_path / "item.md")

        assert "Body content here." in item.raw_body

    def test_parse_item_file_flat_priority_accessible(self, tmp_path: Path) -> None:
        # When priority is a top-level flat key it is accessible
        item = parse_item_file(_FLAT_WITH_ALL_FIELDS, tmp_path / "item.md")

        assert item.priority == "P1"

    def test_parse_item_file_flat_source_accessible(self, tmp_path: Path) -> None:
        item = parse_item_file(_FLAT_WITH_ALL_FIELDS, tmp_path / "item.md")

        assert item.source == "flat-source"

    def test_parse_item_file_flat_added_accessible(self, tmp_path: Path) -> None:
        item = parse_item_file(_FLAT_WITH_ALL_FIELDS, tmp_path / "item.md")

        assert item.added == "2026-01-01"

    def test_parse_item_file_flat_issue_accessible(self, tmp_path: Path) -> None:
        item = parse_item_file(_FLAT_WITH_ALL_FIELDS, tmp_path / "item.md")

        assert item.issue == "#42"

    def test_parse_item_file_flat_plan_accessible(self, tmp_path: Path) -> None:
        item = parse_item_file(_FLAT_WITH_ALL_FIELDS, tmp_path / "item.md")

        assert item.plan == "plan/tasks-1-test.md"

    def test_parse_item_file_flat_done_status_sets_skip_true(self, tmp_path: Path) -> None:
        item = parse_item_file(_FLAT_DONE, tmp_path / "item.md")

        assert item.skip is True

    def test_parse_item_file_flat_open_status_sets_skip_false(self, tmp_path: Path) -> None:
        item = parse_item_file(_FLAT_WITH_ALL_FIELDS, tmp_path / "item.md")

        assert item.skip is False

    def test_parse_item_file_no_frontmatter_returns_body_in_raw_body(self, tmp_path: Path) -> None:
        item = parse_item_file(_NO_FRONTMATTER, tmp_path / "item.md")

        assert item.raw_body == _NO_FRONTMATTER

    def test_parse_item_file_no_frontmatter_title_is_empty(self, tmp_path: Path) -> None:
        item = parse_item_file(_NO_FRONTMATTER, tmp_path / "item.md")

        assert item.title == ""

    def test_parse_item_file_legacy_frontmatter_uses_title_key(self, tmp_path: Path) -> None:
        item = parse_item_file(_FLAT_FRONTMATTER, tmp_path / "item.md")

        assert item.title == "Legacy Title"

    def test_parse_item_file_legacy_priority_from_flat_key(self, tmp_path: Path) -> None:
        item = parse_item_file(_FLAT_FRONTMATTER, tmp_path / "item.md")

        assert item.priority == "P0"

    def test_parse_item_file_plan_na_becomes_empty_string(self, tmp_path: Path) -> None:
        text = """\
---
name: Item With NA Plan
description: desc
source: test
added: '2026-01-01'
priority: P1
status: open
plan: N/A
---
"""
        item = parse_item_file(text, tmp_path / "item.md")

        assert item.plan == ""

    def test_parse_item_file_plan_path_preserved(self, tmp_path: Path) -> None:
        text = """\
---
name: Item With Plan
description: desc
source: test
added: '2026-01-01'
priority: P1
status: open
plan: plan/tasks-1-my-feature.md
---
"""
        item = parse_item_file(text, tmp_path / "item.md")

        assert item.plan == "plan/tasks-1-my-feature.md"

    def test_parse_item_file_groomed_flag_set_from_section_header(self, tmp_path: Path) -> None:
        text = """\
---
name: Groomed Item
description: desc
source: test
added: '2026-01-01'
priority: P1
status: open
---

## Groomed (2026-01-10)

### Priority

Confirmed P1.
"""
        item = parse_item_file(text, tmp_path / "item.md")

        assert item.groomed == "true"

    def test_parse_item_file_missing_optional_fields_use_defaults(self, tmp_path: Path) -> None:
        text = """\
---
name: Bare Item
description: just a desc
priority: P2
status: open
---
"""
        item = parse_item_file(text, tmp_path / "item.md")

        assert item.issue == ""
        assert item.plan == ""
        assert item.groomed == ""

    def test_parse_item_file_resolved_status_sets_skip_true(self, tmp_path: Path) -> None:
        text = """\
---
name: Resolved Item
description: done
source: test
priority: P1
status: resolved
---
"""
        item = parse_item_file(text, tmp_path / "item.md")

        assert item.skip is True

    # -- status field population tests (T2 / #612) --

    def test_parse_item_file_nested_meta_status_populated(self, tmp_path: Path) -> None:
        """Nested-metadata frontmatter with status: open populates item.status.

        Tests: BacklogItem.status field population from nested metadata
        How: Parse _NESTED_META_FRONTMATTER and assert item.status == "open"
        Why: status field must be populated from nested metadata.status key
        """
        # Arrange / Act
        item = parse_item_file(_NESTED_META_FRONTMATTER, tmp_path / "item.md")

        # Assert
        assert item.status == "open"

    def test_parse_item_file_flat_status_preserves_case(self, tmp_path: Path) -> None:
        """Flat frontmatter with mixed-case status preserves original case.

        Tests: Case preservation of status field
        How: Parse frontmatter with status: Done (capital D), verify exact string
        Why: status must preserve raw frontmatter case per architecture spec
        """
        # Arrange
        text = """\
---
name: Case Test
description: case test
source: test
priority: P1
status: Done
---
"""
        # Act
        item = parse_item_file(text, tmp_path / "item.md")

        # Assert
        assert item.status == "Done"

    def test_parse_item_file_no_frontmatter_status_empty(self, tmp_path: Path) -> None:
        """Plain text input with no frontmatter produces empty status.

        Tests: Default status for non-frontmatter files
        How: Parse plain text, verify item.status == ""
        Why: Files without frontmatter must not raise or produce garbage status
        """
        # Arrange / Act
        item = parse_item_file(_NO_FRONTMATTER, tmp_path / "item.md")

        # Assert
        assert item.status == ""

    def test_parse_item_file_missing_status_key_gives_empty(self, tmp_path: Path) -> None:
        """Frontmatter without a status key produces empty status string.

        Tests: Missing optional field behavior
        How: Parse frontmatter with no status key, verify item.status == ""
        Why: status is optional; missing key must default to empty string
        """
        # Arrange
        text = """\
---
name: No Status
description: no status key
source: test
priority: P1
---
"""
        # Act
        item = parse_item_file(text, tmp_path / "item.md")

        # Assert
        assert item.status == ""

    def test_parse_item_file_resolved_status_populates_status_and_skip(self, tmp_path: Path) -> None:
        """Resolved status populates both item.status and item.skip consistently.

        Tests: Consistency between status string and skip boolean
        How: Parse frontmatter with status: resolved, verify both fields
        Why: status and skip must agree — resolved means skip=True and status="resolved"
        """
        # Arrange
        text = """\
---
name: Resolved Consistency
description: test
source: test
priority: P1
status: resolved
---
"""
        # Act
        item = parse_item_file(text, tmp_path / "item.md")

        # Assert
        assert item.status == "resolved"
        assert item.skip is True


# ---------------------------------------------------------------------------
# _parse_frontmatter
# ---------------------------------------------------------------------------


class TestParseFrontmatter:
    """Tests for _parse_frontmatter(text) -> (fm_dict, meta_dict, body)."""

    def test_parse_frontmatter_returns_three_tuple(self) -> None:
        result = _parse_frontmatter(_NESTED_META_FRONTMATTER)

        assert len(result) == 3

    def test_parse_frontmatter_fm_contains_name(self) -> None:
        fm, _meta, _body = _parse_frontmatter(_NESTED_META_FRONTMATTER)

        assert fm.get("name") == "My Test Item"

    def test_parse_frontmatter_fm_contains_description(self) -> None:
        fm, _meta, _body = _parse_frontmatter(_NESTED_META_FRONTMATTER)

        assert fm.get("description") == "A test description"

    def test_parse_frontmatter_body_contains_content(self) -> None:
        _fm, _meta, body = _parse_frontmatter(_NESTED_META_FRONTMATTER)

        assert "Body content here." in body

    def test_parse_frontmatter_flat_fm_contains_priority(self) -> None:
        # Flat frontmatter — priority is directly in fm
        fm, _meta, _body = _parse_frontmatter(_FLAT_FRONTMATTER)

        assert fm.get("priority") == "P0"

    def test_parse_frontmatter_nested_meta_preserves_metadata(self) -> None:
        # _parse_frontmatter now preserves nested metadata dicts instead of
        # stringifying them. The metadata block is extracted and returned as meta.
        _fm, meta, _body = _parse_frontmatter(_NESTED_META_FRONTMATTER)

        assert meta["source"] == "test-source"
        assert meta["added"] == "2026-01-01"
        assert meta["priority"] == "P1"
        assert meta["type"] == "Feature"
        assert meta["status"] == "open"
        assert meta["topic"] == "my-test-item"

    def test_parse_frontmatter_no_metadata_block_gives_empty_meta(self) -> None:
        text = """\
---
name: Flat Only
description: no metadata block
---
flat body
"""
        _fm, meta, _body = _parse_frontmatter(text)

        assert meta == {}

    def test_parse_frontmatter_malformed_yaml_returns_str_types(self) -> None:
        text = "---\n: : invalid yaml\n---\nbody"

        fm, meta, body = _parse_frontmatter(text)

        # Malformed frontmatter must not raise — function handles it gracefully
        assert isinstance(fm, dict)
        assert isinstance(meta, dict)
        assert isinstance(body, str)

    def test_parse_frontmatter_plain_text_gives_empty_fm_and_meta(self) -> None:
        _fm, meta, _body = _parse_frontmatter(_NO_FRONTMATTER)

        assert meta == {}


# ---------------------------------------------------------------------------
# find_item
# ---------------------------------------------------------------------------


class TestFindItem:
    """Tests for find_item(items, selector) -> BacklogItem | None."""

    def _make_items(self) -> list[BacklogItem]:
        return [
            BacklogItem(title="SAM Error Recovery", issue="#10", file_path="/tmp/p1-sam.md"),
            BacklogItem(title="Backlog Duplicate Detection", issue="#20", file_path="/tmp/p1-dup.md"),
            BacklogItem(title="Validate Terminal Browser", issue="#30", file_path="/tmp/p2-browser.md"),
        ]

    def test_find_item_exact_title_match_returns_item(self) -> None:
        items = self._make_items()

        result = find_item(items, "SAM Error Recovery")

        assert result is not None
        assert result.title == "SAM Error Recovery"

    def test_find_item_partial_title_match_returns_item(self) -> None:
        items = self._make_items()

        result = find_item(items, "Duplicate")

        assert result is not None
        assert result.title == "Backlog Duplicate Detection"

    def test_find_item_case_insensitive_match(self) -> None:
        items = self._make_items()

        result = find_item(items, "sam error")

        assert result is not None
        assert result.title == "SAM Error Recovery"

    def test_find_item_hash_selector_matches_issue_number(self) -> None:
        items = self._make_items()

        result = find_item(items, "#10")

        assert result is not None
        assert result.issue == "#10"

    def test_find_item_bare_number_selector_matches_issue_number(self) -> None:
        items = self._make_items()

        result = find_item(items, "20")

        assert result is not None
        assert result.issue == "#20"

    def test_find_item_no_match_returns_none(self) -> None:
        items = self._make_items()

        result = find_item(items, "completely unrelated xyz")

        assert result is None

    def test_find_item_unknown_issue_number_returns_none(self) -> None:
        items = self._make_items()

        result = find_item(items, "#999")

        assert result is None

    def test_find_item_github_url_extracts_issue_number(self) -> None:
        items = self._make_items()

        result = find_item(items, "https://github.com/owner/repo/issues/30")

        assert result is not None
        assert result.issue == "#30"


# ---------------------------------------------------------------------------
# build_issue_body
# ---------------------------------------------------------------------------


class TestBuildIssueBody:
    """Tests for build_issue_body(item: BacklogItem) -> str."""

    def _full_item(self) -> BacklogItem:
        return BacklogItem(
            title="Add new feature",
            description="This feature adds X to Y.",
            source="user request",
            added="2026-01-01",
            priority="P1",
            item_type="Feature",
            files="packages/foo/bar.py",
            suggested_location="packages/foo/",
        )

    def test_build_issue_body_contains_story_section(self) -> None:
        body = build_issue_body(self._full_item())

        assert "## Story" in body

    def test_build_issue_body_contains_description_section(self) -> None:
        body = build_issue_body(self._full_item())

        assert "## Description" in body
        assert "This feature adds X to Y." in body

    def test_build_issue_body_contains_acceptance_criteria_section(self) -> None:
        body = build_issue_body(self._full_item())

        assert "## Acceptance Criteria" in body

    def test_build_issue_body_contains_context_section_with_source(self) -> None:
        body = build_issue_body(self._full_item())

        assert "## Context" in body
        assert "user request" in body

    def test_build_issue_body_contains_files_section_when_files_set(self) -> None:
        body = build_issue_body(self._full_item())

        assert "## Files" in body
        assert "packages/foo/bar.py" in body

    def test_build_issue_body_contains_suggested_location_when_set(self) -> None:
        body = build_issue_body(self._full_item())

        assert "## Suggested Location" in body
        assert "packages/foo/" in body

    def test_build_issue_body_no_files_section_when_files_empty(self) -> None:
        item = BacklogItem(title="Simple", description="desc", priority="P2")

        body = build_issue_body(item)

        assert "## Files" not in body

    def test_build_issue_body_no_suggested_location_section_when_empty(self) -> None:
        item = BacklogItem(title="Simple", description="desc", priority="P2")

        body = build_issue_body(item)

        assert "## Suggested Location" not in body

    def test_build_issue_body_ends_with_newline(self) -> None:
        body = build_issue_body(self._full_item())

        assert body.endswith("\n")

    def test_build_issue_body_minimal_item_still_produces_valid_body(self) -> None:
        item = BacklogItem(title="Bare minimum")

        body = build_issue_body(item)

        assert "## Story" in body
        assert "## Description" in body
        assert "## Acceptance Criteria" in body
        assert "## Context" in body


# ---------------------------------------------------------------------------
# build_issue_body_from_file (BacklogItem-based, parsing.py)
# ---------------------------------------------------------------------------


# Realistic groomed backlog item body with multiple sections
_GROOMED_RAW_BODY = """\
**Description**: Implement duplicate detection for backlog items

**Suggested location**: packages/backlog/

## Story

As a **developer**, I want to **detect duplicate backlog items** so that **the backlog stays clean**.

## Description

Full description of the feature with all details preserved.

## Groomed (2026-01-15)

### Priority

Confirmed P1 — high impact on workflow efficiency.

### Reproducibility

N/A — new feature.

## Fact-Check

Score: 9/10 — verified against codebase.
"""

_UNGROOMED_RAW_BODY = """\
**Description**: Some ungroomed idea

## Story

As a developer, I want to do something.

## Description

Not yet groomed.
"""


class TestBuildIssueBodyFromFile:
    """Tests for build_issue_body_from_file(item: BacklogItem) -> str | None.

    Verifies the passthrough behavior: raw_body is returned directly when
    it contains a '## Groomed' section, and None is returned otherwise.
    """

    def test_returns_none_when_raw_body_has_no_groomed_section(self) -> None:
        """Ungroomed items return None — they should not be synced to GitHub.

        Tests: Gate logic for sync eligibility
        How: Create BacklogItem with body lacking '## Groomed', call function
        Why: Ungroomed items must not push incomplete bodies to GitHub issues
        """
        # Arrange
        item = BacklogItem(title="Ungroomed Item", description="desc", raw_body=_UNGROOMED_RAW_BODY)

        # Act
        result = build_issue_body_from_file(item)

        # Assert
        assert result is None

    def test_returns_stripped_body_plus_newline_when_groomed_present(self) -> None:
        """Groomed items return raw_body.strip() + newline.

        Tests: Passthrough behavior for groomed content
        How: Create BacklogItem with groomed body, verify output matches input
        Why: Body must be emitted verbatim without synthetic generation
        """
        # Arrange
        item = BacklogItem(title="Groomed Item", description="desc", raw_body=_GROOMED_RAW_BODY)

        # Act
        result = build_issue_body_from_file(item)

        # Assert
        assert result is not None
        assert result == _GROOMED_RAW_BODY.strip() + "\n"

    def test_preserves_all_sections_without_duplication(self) -> None:
        """All sections from raw_body appear exactly once in output.

        Tests: Content integrity — no duplication or loss
        How: Count occurrences of each section header in the result
        Why: Previous bug duplicated Story headers; this is a regression guard
        """
        # Arrange
        item = BacklogItem(title="Full Item", description="desc", raw_body=_GROOMED_RAW_BODY)

        # Act
        result = build_issue_body_from_file(item)

        # Assert
        assert result is not None
        assert result.count("## Story") == 1
        assert result.count("## Description") == 1
        assert result.count("## Groomed") == 1
        assert result.count("## Fact-Check") == 1

    def test_does_not_generate_synthetic_story_text(self) -> None:
        """Output must NOT contain synthetic 'As a developer, I want to' text.

        Tests: Regression guard for old synthetic header bug
        How: Verify output does not contain the old template pattern
        Why: The refactored function passes through raw_body; it must never
             generate synthetic content like build_issue_body() does
        """
        # Arrange
        item = BacklogItem(
            title="Detect Duplicates", description="Implement duplicate detection", raw_body=_GROOMED_RAW_BODY
        )

        # Act
        result = build_issue_body_from_file(item)

        # Assert
        assert result is not None
        # The old bug generated "As a **role**, I want to **goal**..." from title
        # The new behavior passes through whatever Story text the file already has
        assert "I want to **detect duplicates" not in result.lower()

    def test_does_not_truncate_content(self) -> None:
        """Full raw_body content is preserved — no truncation.

        Tests: No Invented Limits compliance
        How: Verify all content from raw_body appears in result
        Why: Truncation violates the repo's 'No Invented Limits' policy
        """
        # Arrange
        item = BacklogItem(title="Full Content", description="desc", raw_body=_GROOMED_RAW_BODY)

        # Act
        result = build_issue_body_from_file(item)

        # Assert
        assert result is not None
        assert "Score: 9/10" in result
        assert "Confirmed P1" in result
        assert "Full description of the feature" in result

    def test_returns_none_for_empty_raw_body(self) -> None:
        """Empty raw_body returns None.

        Tests: Edge case — empty body
        How: Create BacklogItem with empty raw_body
        Why: Empty body has no groomed section, must return None
        """
        # Arrange
        item = BacklogItem(title="Empty", raw_body="")

        # Act
        result = build_issue_body_from_file(item)

        # Assert
        assert result is None

    def test_output_ends_with_single_newline(self) -> None:
        """Output ends with exactly one trailing newline.

        Tests: Consistent formatting
        How: Check result ends with newline but not double newline
        Why: GitHub markdown rendering expects clean trailing newline
        """
        # Arrange
        item = BacklogItem(title="Trailing", raw_body="Some content\n\n## Groomed (2026-01-01)\n\nDone.\n\n\n")

        # Act
        result = build_issue_body_from_file(item)

        # Assert
        assert result is not None
        assert result.endswith("\n")
        assert not result.endswith("\n\n")

    def test_groomed_keyword_in_non_heading_position_does_not_match(self) -> None:
        """The word 'Groomed' in body text (not as ## heading) returns None.

        Tests: Heading-level matching specificity
        How: Body contains 'Groomed' in prose but no '## Groomed' heading
        Why: Only the section heading indicates actual grooming status
        """
        # Arrange
        item = BacklogItem(title="False Positive", raw_body="This item has not been Groomed yet.\n\nStill needs work.")

        # Act
        result = build_issue_body_from_file(item)

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# _build_issue_body_from_file (dict-based, scripts/backlog.py)
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason=(
        "scripts/backlog.py does not exist in this repository. The dict-based "
        "_build_issue_body_from_file was planned but never implemented. "
        "backlog_core.parsing.build_issue_body_from_file takes BacklogItem, not dict. "
        "See plan/tasks-1-backlog-state-reconciliation.md"
    )
)
class TestBuildIssueBodyFromFileDict:
    """Tests for _build_issue_body_from_file(item: dict) -> str | None.

    This is the dict-based version that was planned for scripts/backlog.py. It
    uses '_raw_body' key instead of BacklogItem.raw_body attribute.
    NOTE: scripts/backlog.py was never created; these tests are skipped until
    the dict-based variant is implemented in backlog_core.
    """

    @staticmethod
    def _call_build(build_fn: object, item: dict[str, str]) -> str | None:
        """Narrow *build_fn* for ty; body never runs while the class is skipped."""
        fn = cast("Callable[[dict[str, str]], str | None]", build_fn)
        return fn(item)

    @pytest.fixture
    def build_fn(self) -> object:
        """Skip — scripts/backlog.py was intentionally deleted; class is skipped.

        The dict-based _build_issue_body_from_file was planned for
        scripts/backlog.py which no longer exists. All functionality moved to
        backlog_core/. This fixture skips rather than raising FileNotFoundError
        so that pytest's fixture collection does not fail even if the class-level
        skip marker is bypassed.

        Returns:
            Never returns; always skips.
        """
        raise pytest.skip.Exception("scripts/backlog.py does not exist. Functionality moved to backlog_core/.")

    def test_returns_none_when_no_groomed_section(self, build_fn: object) -> None:
        """Dict item without '## Groomed' in _raw_body returns None.

        Tests: Gate logic for dict-based version
        How: Pass dict with _raw_body lacking groomed heading
        Why: Consistency with BacklogItem-based version
        """
        # Arrange
        item = {"_raw_body": _UNGROOMED_RAW_BODY, "_title": "Test"}

        # Act
        result = self._call_build(build_fn, item)

        # Assert
        assert result is None

    def test_returns_body_when_groomed_present(self, build_fn: object) -> None:
        """Dict item with '## Groomed' in _raw_body returns stripped body + newline.

        Tests: Passthrough behavior for dict-based version
        How: Pass dict with groomed _raw_body, verify output
        Why: Must match BacklogItem-based version behavior
        """
        # Arrange
        item = {"_raw_body": _GROOMED_RAW_BODY, "_title": "Test"}

        # Act
        result = self._call_build(build_fn, item)

        # Assert
        assert result is not None
        assert result == _GROOMED_RAW_BODY.strip() + "\n"

    def test_preserves_all_sections(self, build_fn: object) -> None:
        """All sections from _raw_body appear exactly once — no duplication.

        Tests: Content integrity for dict-based version
        How: Count section headers in output
        Why: Regression guard matching BacklogItem-based tests
        """
        # Arrange
        item = {"_raw_body": _GROOMED_RAW_BODY}

        # Act
        result = self._call_build(build_fn, item)

        # Assert
        assert result is not None
        assert result.count("## Story") == 1
        assert result.count("## Groomed") == 1

    def test_missing_raw_body_key_returns_none(self, build_fn: object) -> None:
        """Dict without _raw_body key returns None (empty string default).

        Tests: Missing key handling
        How: Pass dict without _raw_body key
        Why: Function uses .get() with default; must not raise
        """
        # Arrange
        item: dict[str, str] = {"_title": "No body"}

        # Act
        result = self._call_build(build_fn, item)

        # Assert
        assert result is None

    def test_does_not_generate_synthetic_story(self, build_fn: object) -> None:
        """Dict-based version must not generate synthetic story text.

        Tests: Regression guard for old bug
        How: Verify output contains only the raw_body content
        Why: The function was refactored to passthrough; synthetic generation is gone
        """
        # Arrange
        item = {"_raw_body": _GROOMED_RAW_BODY, "_title": "Detect Duplicates"}

        # Act
        result = self._call_build(build_fn, item)

        # Assert
        assert result is not None
        assert "I want to **detect duplicates" not in result.lower()


# ---------------------------------------------------------------------------
# build_backlog_frontmatter
# ---------------------------------------------------------------------------


class TestBuildBacklogFrontmatter:
    """Tests for build_backlog_frontmatter(...) -> str."""

    def _build(self, **kwargs: str) -> str:
        defaults = {
            "name": "Test Feature",
            "description": "A new feature",
            "source": "user",
            "added": "2026-01-01",
            "priority": "P1",
            "type_val": "Feature",
            "status": "open",
        }
        defaults.update(kwargs)
        return build_backlog_frontmatter(**defaults)

    def test_build_backlog_frontmatter_starts_with_dashes(self) -> None:
        result = self._build()

        assert result.startswith("---")

    def test_build_backlog_frontmatter_contains_name(self) -> None:
        result = self._build(name="My Feature")

        assert "My Feature" in result

    def test_build_backlog_frontmatter_contains_priority(self) -> None:
        result = self._build(priority="P0")

        assert "P0" in result

    def test_build_backlog_frontmatter_contains_status(self) -> None:
        result = self._build(status="open")

        assert "open" in result

    def test_build_backlog_frontmatter_contains_source(self) -> None:
        result = self._build(source="automated")

        assert "automated" in result

    def test_build_backlog_frontmatter_issue_included_when_provided(self) -> None:
        result = self._build(issue="#42")

        assert "#42" in result

    def test_build_backlog_frontmatter_issue_omitted_when_empty(self) -> None:
        result = self._build()

        assert "issue" not in result

    def test_build_backlog_frontmatter_plan_included_when_provided(self) -> None:
        result = self._build(plan="plan/tasks-1-test.md")

        assert "plan/tasks-1-test.md" in result

    def test_build_backlog_frontmatter_groomed_included_when_provided(self) -> None:
        result = self._build(groomed="true")

        assert "groomed" in result

    def test_build_backlog_frontmatter_contains_topic_slug(self) -> None:
        result = self._build(name="My New Feature")

        # topic is a slug derived from the name
        assert "my-new-feature" in result


# ---------------------------------------------------------------------------
# find_fuzzy_duplicates
# ---------------------------------------------------------------------------


class TestFindFuzzyDuplicates:
    """Tests for find_fuzzy_duplicates(title, items, threshold) -> list[tuple]."""

    def test_find_fuzzy_duplicates_exact_match_returns_one_result(self) -> None:
        items = [BacklogItem(title="SAM Error Recovery", file_path="/tmp/p1-sam.md")]

        matches = find_fuzzy_duplicates("SAM Error Recovery", items)

        assert len(matches) == 1

    def test_find_fuzzy_duplicates_exact_match_ratio_is_one(self) -> None:
        items = [BacklogItem(title="SAM Error Recovery", file_path="/tmp/p1-sam.md")]

        matches = find_fuzzy_duplicates("SAM Error Recovery", items)

        assert matches[0][1] >= 1.0

    def test_find_fuzzy_duplicates_similar_title_detected_above_threshold(self) -> None:
        items = [BacklogItem(title="backlog.py add implement duplicate detection", file_path="/tmp/p1-dup.md")]

        matches = find_fuzzy_duplicates("backlog.py add implement fuzzy duplicate detection", items)

        assert len(matches) == 1
        assert matches[0][1] >= 0.80

    def test_find_fuzzy_duplicates_dissimilar_title_returns_empty(self) -> None:
        items = [BacklogItem(title="Validate Terminal Browser", file_path="/tmp/p2-browser.md")]

        matches = find_fuzzy_duplicates("SAM Error Recovery", items)

        assert matches == []

    def test_find_fuzzy_duplicates_skips_items_with_skip_true(self) -> None:
        items = [BacklogItem(title="SAM Error Recovery", file_path="/tmp/p1-sam.md", skip=True)]

        matches = find_fuzzy_duplicates("SAM Error Recovery", items)

        assert matches == []

    def test_find_fuzzy_duplicates_strips_commit_prefix_before_comparison(self) -> None:
        items = [BacklogItem(title="feat: SAM Error Recovery", file_path="/tmp/p1-sam.md")]

        matches = find_fuzzy_duplicates("SAM Error Recovery", items)

        assert len(matches) == 1
        assert matches[0][1] >= 1.0

    def test_find_fuzzy_duplicates_new_title_commit_prefix_stripped(self) -> None:
        items = [BacklogItem(title="SAM Error Recovery", file_path="/tmp/p1-sam.md")]

        matches = find_fuzzy_duplicates("fix: SAM Error Recovery", items)

        assert len(matches) == 1

    def test_find_fuzzy_duplicates_returns_tuples_of_title_ratio_path(self) -> None:
        items = [BacklogItem(title="SAM Error Recovery", file_path="/tmp/p1-sam.md")]

        matches = find_fuzzy_duplicates("SAM Error Recovery", items)

        title, ratio, path = matches[0]
        assert title == "SAM Error Recovery"
        assert isinstance(ratio, float)
        assert path == "/tmp/p1-sam.md"

    def test_find_fuzzy_duplicates_sorted_by_ratio_descending(self) -> None:
        items = [
            BacklogItem(title="SAM recovery mechanism", file_path="/tmp/a.md"),
            BacklogItem(title="SAM Error Recovery", file_path="/tmp/b.md"),
        ]

        matches = find_fuzzy_duplicates("SAM Error Recovery", items)

        ratios = [m[1] for m in matches]
        assert ratios == sorted(ratios, reverse=True)

    def test_find_fuzzy_duplicates_empty_title_returns_empty(self) -> None:
        items = [BacklogItem(title="SAM Error Recovery", file_path="/tmp/p1-sam.md")]

        matches = find_fuzzy_duplicates("", items)

        assert matches == []

    def test_find_fuzzy_duplicates_custom_threshold_respected(self) -> None:
        items = [BacklogItem(title="Completely different title", file_path="/tmp/p1.md")]

        # With 0.0 threshold everything matches
        matches = find_fuzzy_duplicates("SAM Error Recovery", items, threshold=0.0)

        assert len(matches) == 1


# ---------------------------------------------------------------------------
# normalize_issue_title
# ---------------------------------------------------------------------------


class TestNormalizeIssueTitle:
    """Tests for normalize_issue_title(title) -> str."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("feat: SAM: Error Recovery", "sam: error recovery"),
            ("fix: Bug in parser", "bug in parser"),
            ("refactor: Clean up models", "clean up models"),
            ("docs: Update README", "update readme"),
            ("chore: Bump dependencies", "bump dependencies"),
            ("perf: Optimize query", "optimize query"),
            ("test: Add unit tests", "add unit tests"),
            ("ci: Update workflow", "update workflow"),
            ("SAM: Error Recovery", "sam: error recovery"),
            ("No prefix title", "no prefix title"),
            ("FEAT: Upper case prefix", "upper case prefix"),
        ],
    )
    def test_normalize_issue_title_strips_prefix_and_lowercases(self, raw: str, expected: str) -> None:
        assert normalize_issue_title(raw) == expected

    def test_normalize_issue_title_empty_string_returns_empty(self) -> None:
        assert normalize_issue_title("") == ""


# ---------------------------------------------------------------------------
# title_to_slug (slugify)
# ---------------------------------------------------------------------------


class TestTitleToSlug:
    """Tests for title_to_slug(title) -> str."""

    @pytest.mark.parametrize(
        ("title", "expected"),
        [
            ("Hello World", "hello-world"),
            ("SAM: Error Recovery", "sam-error-recovery"),
            ("Add [new] feature (v2)", "add-new-feature-v2"),
            ("  Spaces   Around  ", "spaces-around"),
            ("Special!@#$%chars", "specialchars"),
            ("Multiple---Hyphens", "multiple-hyphens"),
            ("CamelCase Title", "camelcase-title"),
        ],
    )
    def test_title_to_slug_converts_title_to_valid_slug(self, title: str, expected: str) -> None:
        assert title_to_slug(title) == expected

    def test_title_to_slug_truncates_at_max_len(self) -> None:
        long_title = "a" * 100

        slug = title_to_slug(long_title, max_len=60)

        assert len(slug) <= 60

    def test_title_to_slug_strips_strikethrough_prefix(self) -> None:
        # Strikethrough syntax used for resolved items in BACKLOG.md
        slug = title_to_slug("~~Done Item~~ RESOLVED")

        assert slug == "done-item"

    def test_title_to_slug_result_is_lowercase(self) -> None:
        slug = title_to_slug("UPPERCASE TITLE")

        assert slug == slug.lower()

    def test_title_to_slug_no_leading_or_trailing_hyphens(self) -> None:
        slug = title_to_slug("  -Hyphen at edges-  ")

        assert not slug.startswith("-")
        assert not slug.endswith("-")


# ---------------------------------------------------------------------------
# view_result_from_local_item
# ---------------------------------------------------------------------------


class TestViewResultFromLocalItem:
    """Tests for view_result_from_local_item(item: BacklogItem) -> ViewItemResult."""

    def test_view_result_from_local_item_maps_title(self) -> None:
        item = BacklogItem(title="My Item", section="P1")

        result = view_result_from_local_item(item)

        assert result.title == "My Item"

    def test_view_result_from_local_item_maps_section_to_priority(self) -> None:
        item = BacklogItem(title="My Item", section="P0")

        result = view_result_from_local_item(item)

        assert result.priority == "P0"

    def test_view_result_from_local_item_maps_issue(self) -> None:
        item = BacklogItem(title="My Item", issue="#55", section="P1")

        result = view_result_from_local_item(item)

        assert result.issue == "#55"

    def test_view_result_from_local_item_maps_plan(self) -> None:
        item = BacklogItem(title="My Item", plan="plan/tasks-1-test.md", section="P1")

        result = view_result_from_local_item(item)

        assert result.plan == "plan/tasks-1-test.md"

    def test_view_result_from_local_item_maps_file_path(self) -> None:
        item = BacklogItem(title="My Item", file_path="/tmp/p1-my-item.md", section="P1")

        result = view_result_from_local_item(item)

        assert result.file_path == "/tmp/p1-my-item.md"

    def test_view_result_from_local_item_groomed_true_when_set(self) -> None:
        item = BacklogItem(title="My Item", groomed="true", section="P1")

        result = view_result_from_local_item(item)

        assert result.groomed is True

    def test_view_result_from_local_item_groomed_false_when_empty(self) -> None:
        item = BacklogItem(title="My Item", groomed="", section="P1")

        result = view_result_from_local_item(item)

        assert result.groomed is False

    def test_view_result_from_local_item_returns_view_item_result_type(self) -> None:
        item = BacklogItem(title="My Item", section="P1")

        result = view_result_from_local_item(item)

        assert isinstance(result, ViewItemResult)

    def test_view_result_from_local_item_uses_item_description_directly(self) -> None:
        """View helper uses description from BacklogItem model, not file re-read.

        Tests: Description field mapping after T1 refactor (#612)
        How: Create BacklogItem with description set, verify result.description matches
        Why: After T1 removed file re-read, description comes from the parsed model
        """
        # Arrange
        item = BacklogItem(title="Flat Item", section="P1", description="flat description")

        # Act
        result = view_result_from_local_item(item)

        # Assert
        assert result.description == "flat description"

    def test_view_result_from_local_item_no_file_path_skips_file_read(self) -> None:
        item = BacklogItem(title="No path item", section="P2", file_path="")

        result = view_result_from_local_item(item)

        # Should not raise even with empty file_path
        assert result.title == "No path item"

    # -- status field mapping tests (T2 / #612) --

    def test_view_result_from_local_item_maps_status(self) -> None:
        """BacklogItem with status="open" produces result.status == "open".

        Tests: Status field mapping from BacklogItem to ViewItemResult
        How: Create BacklogItem with status="open", call view helper, check result
        Why: Status must flow from parsed model to view result without file I/O
        """
        # Arrange
        item = BacklogItem(title="Status Item", section="P1", status="open")

        # Act
        result = view_result_from_local_item(item)

        # Assert
        assert result.status == "open"

    def test_view_result_from_local_item_default_status_empty(self) -> None:
        """BacklogItem with default (empty) status produces empty result.status.

        Tests: Default status propagation
        How: Create BacklogItem without setting status, verify result.status == ""
        Why: Default empty status must propagate consistently to ViewItemResult
        """
        # Arrange
        item = BacklogItem(title="Default Status", section="P1")

        # Act
        result = view_result_from_local_item(item)

        # Assert
        assert result.status == ""

    def test_view_result_from_local_item_nonexistent_path_no_error(self) -> None:
        """BacklogItem with nonexistent file_path and status="open" succeeds without FileNotFoundError.

        Tests: Regression — old code re-read file from disk and would fail on missing files
        How: Create BacklogItem with status and nonexistent file_path, verify no exception
        Why: After T1 refactor, view helper uses item.status directly — no file I/O needed
        """
        # Arrange
        item = BacklogItem(
            title="Missing File", section="P1", status="open", file_path="/nonexistent/path/that/does/not/exist.md"
        )

        # Act
        result = view_result_from_local_item(item)

        # Assert
        assert result.status == "open"


# ---------------------------------------------------------------------------
# append_or_replace_section — regex crash guard
# ---------------------------------------------------------------------------


class TestAppendOrReplaceSectionBackslash:
    """Content containing regex backreference syntax must not crash re.sub."""

    def test_append_or_replace_section_with_backslash_in_content(self) -> None:
        body = "## Fact-Check\n\nOld content\n"
        content_with_backslash = r"Score: \1 — verified"

        result = append_or_replace_section(body, "Fact-Check", content_with_backslash)

        assert r"\1" in result

    def test_append_or_replace_section_subsection_with_backslash(self) -> None:
        body = "## Groomed (2026-01-01)\n\n### Priority\n\nOld\n"
        content = r"High \g<name> priority"

        result = append_or_replace_section(body, "Priority", content)

        assert r"\g<name>" in result


# ---------------------------------------------------------------------------
# SamTask parsing / building
# ---------------------------------------------------------------------------

from backlog_core.models import SamTask
from backlog_core.parsing import build_sam_task_body, build_sam_task_issue_title, parse_sam_task_metadata

_SAM_BODY = (
    "## What\n\nAudit new uv CLI subcommands\n\n"
    "## Acceptance Criteria\n\n- [ ] All documented\n\n"
    "<!-- sam:task\n"
    "task_id: T1\n"
    "feature: uv-skill-update\n"
    "type: research\n"
    "status: not-started\n"
    "agent: context-gathering\n"
    "priority: 1\n"
    "skills:\n"
    "- uv\n"
    "- python3-development\n"
    "dependencies: []\n"
    "-->\n"
)


class TestParseSamTaskMetadata:
    def test_round_trip(self) -> None:
        task = SamTask(
            task_id="T1",
            feature="uv-skill-update",
            task_type="research",
            status="not-started",
            agent="context-gathering",
            priority=1,
            skills=["uv", "python3-development"],
            dependencies=[],
        )
        body = build_sam_task_body(task, "Audit new uv CLI subcommands", ["All documented"])
        parsed = parse_sam_task_metadata(body)

        assert parsed is not None
        assert parsed.task_id == task.task_id
        assert parsed.feature == task.feature
        assert parsed.task_type == task.task_type
        assert parsed.status == task.status
        assert parsed.agent == task.agent
        assert parsed.priority == task.priority
        assert parsed.skills == task.skills
        assert parsed.dependencies == task.dependencies

    def test_returns_none_when_no_block(self) -> None:
        assert parse_sam_task_metadata("## What\n\nNo metadata here.\n") is None

    def test_returns_none_on_malformed_yaml(self) -> None:
        body = "<!-- sam:task\n: bad: [yaml\n-->\n"
        assert parse_sam_task_metadata(body) is None

    def test_returns_none_on_empty_body(self) -> None:
        assert parse_sam_task_metadata("") is None

    def test_parses_known_body(self) -> None:
        parsed = parse_sam_task_metadata(_SAM_BODY)
        assert parsed is not None
        assert parsed.task_id == "T1"
        assert parsed.skills == ["uv", "python3-development"]


class TestBuildSamTaskIssueTitle:
    def test_format(self) -> None:
        task = SamTask(task_id="T2", feature="my-feat", task_type="implementation")
        title = build_sam_task_issue_title(task, "Add the thing")
        assert title == "[my-feat/T2] implementation: Add the thing"


# ---------------------------------------------------------------------------
# parse_backlog_from_directory — corruption resilience
# ---------------------------------------------------------------------------


class TestParseBacklogFromDirectoryCorruptionResilience:
    """parse_backlog_from_directory skips corrupt files and logs a warning.

    The corrupt-YAML scenario: a file whose frontmatter block contains a bare
    ``---`` delimiter (producing two YAML documents).  ruamel.yaml raises
    ``YAMLError`` — not caught by _parse_frontmatter's except clause — causing
    the entire parse run to abort.  The fix wraps parse_item_file per-file so
    the corrupt file is skipped with a logged warning and remaining files are
    returned normally.
    """

    # Content that causes ruamel.yaml to raise YAMLError: duplicate key 'name'
    # with incompatible types (scalar then mapping).  This is a realistic
    # corruption pattern — ruamel.yaml raises ``ComposerError: while constructing
    # a mapping … found duplicate key`` with severity that cannot be caught by
    # _parse_frontmatter's existing ``except (ValueError, KeyError, TypeError)``.
    _CORRUPT_FRONTMATTER = """\
---
name: Corrupt Item
name:
  nested: bad
metadata:
  topic: corrupt-item
  priority: P1
  status: open
---

Body text.
"""

    _VALID_FRONTMATTER = """\
---
name: Valid Item
description: clean frontmatter
metadata:
  topic: valid-item
  source: test
  added: '2026-01-01'
  priority: P1
  type: Feature
  status: open
---

Body of valid item.
"""

    def test_parse_backlog_from_directory_skips_corrupt_file_returns_valid(self, backlog_dir) -> None:
        """A corrupt file is skipped; the valid file in the same directory is returned."""
        # Arrange
        from backlog_core.parsing import parse_backlog_from_directory

        corrupt_file = backlog_dir / "p1-corrupt-item.md"
        valid_file = backlog_dir / "p1-valid-item.md"
        corrupt_file.write_text(self._CORRUPT_FRONTMATTER, encoding="utf-8")
        valid_file.write_text(self._VALID_FRONTMATTER, encoding="utf-8")

        # Act
        items = parse_backlog_from_directory()

        # Assert
        titles = [it.title for it in items]
        assert "Valid Item" in titles
        assert "Corrupt Item" not in titles

    def test_parse_backlog_from_directory_logs_warning_for_corrupt_file(self, backlog_dir, caplog) -> None:
        """A warning containing the corrupt file path is emitted to the log."""
        import logging

        from backlog_core.parsing import parse_backlog_from_directory

        # Arrange
        corrupt_file = backlog_dir / "p1-corrupt-item.md"
        corrupt_file.write_text(self._CORRUPT_FRONTMATTER, encoding="utf-8")

        # Act
        with caplog.at_level(logging.WARNING, logger="backlog_core.parsing"):
            parse_backlog_from_directory()

        # Assert — at least one warning message names the corrupt file
        assert any(
            "corrupt" in record.message.lower() and "p1-corrupt-item.md" in record.message for record in caplog.records
        )

    def test_parse_backlog_from_directory_does_not_crash_on_all_corrupt_files(self, backlog_dir) -> None:
        """When every file is corrupt, parse_backlog_from_directory returns an empty list."""
        from backlog_core.parsing import parse_backlog_from_directory

        # Arrange — write two different corrupt files
        (backlog_dir / "p0-corrupt-a.md").write_text(self._CORRUPT_FRONTMATTER, encoding="utf-8")
        (backlog_dir / "p1-corrupt-b.md").write_text(self._CORRUPT_FRONTMATTER, encoding="utf-8")

        # Act
        items = parse_backlog_from_directory()

        # Assert — no crash, empty result
        assert items == []
