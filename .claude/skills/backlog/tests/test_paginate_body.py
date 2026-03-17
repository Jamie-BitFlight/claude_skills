"""Tests for entry-block-aware pagination in _paginate_body.

Covers:
- offset/limit operates on entry blocks, never splitting mid-block
- fallback to line-based pagination when body has no entry blocks
"""

from __future__ import annotations

import backlog_core.operations as ops

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TS = [
    "2026-01-01T01:00:00Z",
    "2026-01-01T02:00:00Z",
    "2026-01-01T03:00:00Z",
    "2026-01-01T04:00:00Z",
    "2026-01-01T05:00:00Z",
]


def _make_entry(ts: str, content: str) -> str:
    """Build a single HTML entry block."""
    return f"<div><sub>{ts}</sub>\n\n{content}\n</div>"


def _make_body(count: int) -> str:
    """Return a body string containing *count* distinct entry blocks."""
    return "\n\n".join(_make_entry(_TS[i], f"Content {i + 1}") for i in range(count))


# ---------------------------------------------------------------------------
# Entry-block pagination
# ---------------------------------------------------------------------------


def test_paginate_body_offset2_limit2_returns_blocks_3_and_4_intact():
    """offset=2, limit=2 on a 5-block body returns blocks 3 and 4 without splitting them."""
    # Arrange
    body = _make_body(5)
    data: dict = {}

    # Act
    ops._paginate_body(data, body, offset=2, limit=2)

    # Assert — two blocks returned
    result_body = data["body"]
    # Each block must appear intact (not cut mid-tag)
    block3 = _make_entry(_TS[2], "Content 3")
    block4 = _make_entry(_TS[3], "Content 4")
    assert block3 in result_body
    assert block4 in result_body

    # Blocks 1, 2, and 5 must not appear
    assert _TS[0] not in result_body  # block 1
    assert _TS[1] not in result_body  # block 2
    assert _TS[4] not in result_body  # block 5


def test_paginate_body_offset2_limit2_sets_truncation_metadata():
    """Truncation metadata reflects remaining blocks after the page."""
    # Arrange
    body = _make_body(5)
    data: dict = {}

    # Act
    ops._paginate_body(data, body, offset=2, limit=2)

    # Assert
    assert data.get("body_truncated") is True
    assert data["body_remaining_entries"] == 1  # block 5 is beyond the page
    assert data["body_total_entries"] == 5


def test_paginate_body_entry_block_boundary_never_broken():
    """No partial div tags appear in the paginated output."""
    # Arrange — use a body whose entry blocks each contain multi-line content
    multi_line_entries = "\n\n".join(
        _make_entry(_TS[i], f"Line A of block {i + 1}\n\nLine B of block {i + 1}\n\nLine C of block {i + 1}")
        for i in range(4)
    )
    data: dict = {}

    # Act
    ops._paginate_body(data, multi_line_entries, offset=1, limit=2)

    # Assert — every <div> is matched by a corresponding </div>
    result = data["body"]
    open_tags = result.count("<div>")
    close_tags = result.count("</div>")
    assert open_tags == close_tags, "Unbalanced div tags — block was split mid-block"
    assert open_tags == 2, "Expected exactly 2 complete blocks"


def test_paginate_body_offset_zero_limit_zero_returns_all_blocks():
    """offset=0, limit=0 (unlimited) returns all entry blocks unchanged."""
    # Arrange
    body = _make_body(3)
    data: dict = {}

    # Act
    ops._paginate_body(data, body, offset=0, limit=0)

    # Assert — all three timestamps present, no truncation flag
    for ts in _TS[:3]:
        assert ts in data["body"]
    assert "body_truncated" not in data


def test_paginate_body_offset_exceeds_block_count_returns_empty():
    """offset larger than block count yields an empty body with no truncation flag."""
    # Arrange
    body = _make_body(3)
    data: dict = {}

    # Act
    ops._paginate_body(data, body, offset=10, limit=5)

    # Assert
    assert data["body"] == ""
    assert "body_truncated" not in data


# ---------------------------------------------------------------------------
# Fallback to line-based pagination for plain-text bodies
# ---------------------------------------------------------------------------


def test_paginate_body_no_entry_blocks_falls_back_to_line_based():
    """A body with no entry blocks uses line-based offset/limit (no regression)."""
    # Arrange — 5 plain text lines, no div wrappers
    lines = ["Line 1", "Line 2", "Line 3", "Line 4", "Line 5"]
    body = "\n".join(lines)
    data: dict = {}

    # Act
    ops._paginate_body(data, body, offset=1, limit=2)

    # Assert — lines 2 and 3 returned
    result_lines = data["body"].splitlines()
    assert result_lines == ["Line 2", "Line 3"]


def test_paginate_body_no_entry_blocks_truncation_metadata_uses_lines():
    """Line-based fallback sets body_remaining_lines, not body_remaining_entries."""
    # Arrange
    lines = ["A", "B", "C", "D", "E"]
    body = "\n".join(lines)
    data: dict = {}

    # Act
    ops._paginate_body(data, body, offset=1, limit=2)

    # Assert
    assert data.get("body_truncated") is True
    assert "body_remaining_lines" in data
    assert "body_remaining_entries" not in data
    assert data["body_remaining_lines"] == 2  # lines D and E remain


def test_paginate_body_no_entry_blocks_no_truncation_when_within_limit():
    """Line-based fallback sets no truncation flag when all lines fit in limit."""
    # Arrange
    body = "Only line"
    data: dict = {}

    # Act
    ops._paginate_body(data, body, offset=0, limit=5)

    # Assert
    assert "body_truncated" not in data
    assert data["body"] == "Only line"
