"""Regression test for the 0000-00-00T00:00:00Z timestamp bug.

When a backlog item's ``added`` field is empty (the common case for newly
created items that have not been given an explicit date), calling
``_apply_groomed_entries`` to seed the first entry of a section must use the
current UTC datetime — not the epoch sentinel ``"0000-00-00T00:00:00Z"``.

Fixed in ``operations._apply_groomed_entries``: the empty-section branch now
calls ``now_iso()`` instead of constructing ``f"{added_date}T00:00:00Z"``
when ``added_date`` is the sentinel value ``"0000-00-00"``.
"""

from __future__ import annotations

import re

from backlog_core.models import Section
from backlog_core.operations import _apply_groomed_entries

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _real_date(ts: str) -> bool:
    """Return True when ts is a valid, non-epoch ISO 8601 timestamp."""
    return bool(_ISO_RE.match(ts)) and ts != "0000-00-00T00:00:00Z"


# ---------------------------------------------------------------------------
# Regression test — verifies the epoch-sentinel bug stays fixed
# ---------------------------------------------------------------------------


def test_apply_groomed_entries_new_section_uses_current_time_not_epoch() -> None:
    """_apply_groomed_entries uses now_iso() for a new section's first entry.

    When a backlog item has no ``added`` date (empty string, the default for
    newly created items), the caller in operations.py passes
    ``added_date="0000-00-00"`` to ``_apply_groomed_entries``.  The function
    must seed the empty section with a real current timestamp from ``now_iso()``
    rather than the epoch sentinel ``"0000-00-00T00:00:00Z"``.
    """
    # Arrange — empty section, no added date (the common case)
    section = Section()
    groomed_content = "Some groomed content"
    added_date = "0000-00-00"  # what operations.py passes when item.added == ""

    # Act — default path: no append, no replace_section, no entry_id, empty section
    _apply_groomed_entries(
        section, groomed_content, append=False, replace_section=False, reason=None, entry_id=None, added_date=added_date
    )

    # Assert — exactly one entry must have been added
    assert len(section.entries) == 1, "expected exactly one entry to be seeded"
    entry = section.entries[0]

    assert _real_date(entry.id), (
        f"Entry id must be a real ISO 8601 timestamp from now_iso(), not the epoch sentinel. Got: {entry.id!r}"
    )
