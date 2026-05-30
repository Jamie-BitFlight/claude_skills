"""Regression tests for entry-block pagination offset accounting (#2495 C5).

Real bug fixed: ``_paginate_body_result`` computed
``remaining = total - offset - len(sliced)`` using the RAW ``offset`` rather than
the clamped ``start = max(0, offset)``. A negative ``offset`` clamps to 0 (every
entry is returned) yet the raw-offset arithmetic made ``remaining`` positive, so
``body_truncated`` was wrongly set with a bogus count even though nothing was
omitted. The fix computes ``remaining`` from the clamped ``start``.

NOT changed (intended contract): an ``offset`` past the last entry yields an
empty body with ``body_truncated`` False — this is the documented behavior of
``test_paginate_body.py::test_paginate_body_offset_exceeds_block_count_returns_empty``
and is preserved here.
"""

from __future__ import annotations

from backlog_core.models import ViewItemResult
from backlog_core.operations import _paginate_body_result

# Five timestamped entry blocks under one ``## Log`` header (ENTRY_RE format:
# ``<div><sub>TIMESTAMP</sub> content</div>``).
_FIVE_ENTRY_BODY = "## Log\n\n" + "\n\n".join(
    f"<div><sub>2026-05-{day:02d} 10:00</sub> entry {day} content</div>" for day in range(1, 6)
)


def test_negative_offset_returns_all_without_false_truncation() -> None:
    """Negative offset clamps to 0 (all entries) and must NOT report truncation.

    RED before fix: start clamps to 0 so all 5 entries are returned, but
    remaining = 5 - (-2) - 5 = 2 > 0 wrongly sets body_truncated with a bogus count.
    """
    result = ViewItemResult()
    _paginate_body_result(result, _FIVE_ENTRY_BODY, offset=-2, limit=0)

    assert result.body_truncated is False, (
        "A negative offset is clamped to 0 and returns every entry, so nothing is "
        "omitted — body_truncated must stay False."
    )


def test_offset_past_end_returns_empty_without_truncation_flag() -> None:
    """Intended contract: offset past the last entry → empty body, no flag.

    Mirrors test_paginate_body.py for the entry-block path; guards against a
    regression that would start flagging past-end pages as truncated.
    """
    result = ViewItemResult()
    _paginate_body_result(result, _FIVE_ENTRY_BODY, offset=100, limit=5)

    assert result.body == ""
    assert result.body_truncated is False


def test_in_range_middle_page_reports_remaining() -> None:
    """A normal in-range page still reports remaining entries (no behavior change)."""
    result = ViewItemResult()
    _paginate_body_result(result, _FIVE_ENTRY_BODY, offset=0, limit=2)

    assert result.body_truncated is True
    assert result.body_total_entries == 5
    assert result.body_remaining_entries == 3
