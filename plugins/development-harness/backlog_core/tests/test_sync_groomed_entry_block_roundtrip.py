"""Round-trip tests for _insert_named_section entry-block wrapper behaviour.

Fix B for #2585: ``sync_groomed_to_github_issue`` must write entry-block
wrappers (``<div><sub>timestamp</sub>content</div>``) so that GitHub-only
backlog items can be round-tripped through ``parse_entries`` and yield real
entry IDs instead of the zero-timestamp fallback ``0000-00-00T00:00:00Z``.

``_insert_named_section`` is the write path tested here.  After Fix B it
wraps every content write via ``wrap_entry``.  ``parse_entries`` (the read
path) then finds the ``ENTRY_RE`` match and extracts the real timestamp from
the ``<sub>`` tag rather than falling back to the zero-ID default.

Two tests:

1. ``TestInsertNamedSectionEntryBlockRoundtrip.test_insert_named_section_wraps_content``
   — asserts that the string returned by ``_insert_named_section`` contains
   text that ``ENTRY_RE`` can match.

2. ``TestInsertNamedSectionEntryBlockRoundtrip.test_github_only_item_roundtrip_preserves_entry_ids``
   — writes content via ``_insert_named_section``, extracts the section body,
   runs ``parse_entries`` on it, and asserts the resulting entry ID is not the
   zero-timestamp default.
"""

from __future__ import annotations

from backlog_core.entry_blocks import ENTRY_RE, parse_entries
from backlog_core.gh_client import _insert_named_section
from backlog_core.parsing import today

_ZERO_ID_PREFIX = "0000-00-00"
"""Prefix uniquely identifying a zero-timestamp entry ID (same sentinel as Fix A tests)."""


class TestInsertNamedSectionEntryBlockRoundtrip:
    """_insert_named_section must wrap content so the GitHub body is ENTRY_RE-parseable."""

    def test_insert_named_section_wraps_content(self) -> None:
        """Content written by _insert_named_section must match ENTRY_RE.

        Arrange: empty body, generic subsection name, non-empty content.

        Act: call _insert_named_section to produce an updated body.

        Assert: ENTRY_RE.search(result) is truthy — the written content is
        wrapped in a ``<div><sub>timestamp</sub>…</div>`` entry block.

        RED (pre-fix): ``_insert_named_section`` wrote raw ``content`` without
        wrapping, so ``ENTRY_RE`` found no match and ``parse_entries`` fell back
        to the zero-timestamp default for every entry.
        """
        body = ""
        section_name = "Concerns"
        content = "Race condition X exists between writer agents."
        today_str = today()

        result = _insert_named_section(body, section_name, content, today_str)

        assert ENTRY_RE.search(result), (
            f"_insert_named_section must wrap content in an entry block so ENTRY_RE can match. "
            f"Got result:\n{result!r}\n"
            "Expected a <div><sub>timestamp</sub>…</div> wrapper around the content."
        )

    def test_github_only_item_roundtrip_preserves_entry_ids(self) -> None:
        """Content written through _insert_named_section round-trips to real entry IDs.

        This test simulates the GitHub-only item scenario: there is no local YAML
        file, so the only source of entry data is the GitHub issue body written
        by ``sync_groomed_to_github_issue`` (which calls ``_insert_named_section``).

        Arrange: call _insert_named_section to write content into an empty body.

        Act: extract the section body from the result and run parse_entries on it.

        Assert: every parsed entry has an ID that does NOT start with
        ``0000-00-00`` — the real ISO timestamp from wrap_entry is preserved
        through the round-trip.

        RED (pre-fix): raw content written without entry-block wrappers meant
        parse_entries found no ENTRY_RE match and emitted
        ``"0000-00-00T00:00:00Z"`` as the entry ID for every section.
        """
        body = ""
        section_name = "Concerns"
        content = "Potential data loss if write path is not atomic."
        today_str = today()

        result = _insert_named_section(body, section_name, content, today_str)

        # Extract the subsection body under ### Concerns
        import re

        sub_re = re.compile(
            rf"### {re.escape(section_name)}[^\n]*\n([\s\S]*?)(?=\n### |\n## |\Z)", re.IGNORECASE | re.MULTILINE
        )
        m = sub_re.search(result)
        assert m, f"Could not find '### {section_name}' section in _insert_named_section output:\n{result!r}"
        section_body = m.group(1)

        entries = parse_entries(section_body, show="all", since=None)
        assert entries, (
            f"parse_entries returned no entries for section body:\n{section_body!r}\n"
            "Expected at least one entry from the wrapped content."
        )

        for entry in entries:
            assert not entry.id.startswith(_ZERO_ID_PREFIX), (
                f"Entry id={entry.id!r} is the zero-timestamp fallback. "
                "The entry ID must be a real ISO timestamp written by wrap_entry. "
                "Root cause if failing: _insert_named_section did not wrap content "
                "so ENTRY_RE found no match and parse_entries fell back to the zero-ID default."
            )
