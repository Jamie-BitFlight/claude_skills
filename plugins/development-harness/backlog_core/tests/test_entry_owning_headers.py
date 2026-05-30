"""Regression test for entry-content header mis-detection (#2495 C4).

Bug: ``_entry_owning_headers`` runs ``_SECTION_BOUNDARY_RE`` over the full body
with no exclusion for ``## ``/``### `` lines that appear INSIDE an entry block's
content. Such a line is part of the entry's text, not a real section boundary,
so a later entry is wrongly attributed to it (and a fictitious section can be
re-attached to the paged body).

Fix: exclude header matches whose position falls within an entry block's span.
"""

from __future__ import annotations

from backlog_core.operations import _entry_owning_headers


def test_header_inside_entry_content_is_not_a_section_boundary() -> None:
    """A ``## `` line inside an entry's content must not own a later entry.

    RED before fix: the second entry is attributed to "## Fake Header In Content"
    (which lives inside the first entry's body) instead of "## Real Section".
    """
    body = (
        "## Real Section\n\n"
        "<div><sub>2026-05-01 10:00</sub> first entry\n"
        "## Fake Header In Content\nmore text</div>\n\n"
        "<div><sub>2026-05-02 10:00</sub> second entry</div>"
    )

    owners = _entry_owning_headers(body)

    assert owners == ["## Real Section", "## Real Section"], (
        "Both entries belong to '## Real Section'. A '## ' line inside the first "
        f"entry's content must not be treated as a section boundary. Got {owners!r}."
    )


def test_real_subsection_header_still_owns_its_entries() -> None:
    """A genuine ``### `` header between entries still owns the following entry."""
    body = (
        "## Log\n\n"
        "<div><sub>2026-05-01 10:00</sub> log entry</div>\n\n"
        "### Detail\n\n"
        "<div><sub>2026-05-02 10:00</sub> detail entry</div>"
    )

    owners = _entry_owning_headers(body)

    assert owners == ["## Log", "### Detail"], (
        f"Real headers between entries must still own their entries. Got {owners!r}."
    )
