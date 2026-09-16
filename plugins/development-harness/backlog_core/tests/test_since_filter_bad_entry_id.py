"""A stored entry ID without a timestamp must not escape ``parse_entries`` as a ``ValueError``.

``backlog_view(since=...)`` reaches ``_parse_entry_timestamp`` once per stored entry, via
``view_item`` -> ``_build_sections_metadata`` -> ``parse_entries``. An ID that is neither
the zero-date fallback nor a real ISO timestamp was refused with a plain ``ValueError``.
Nothing on that path matches it -- ``backlog_view``'s only handler is
``except BacklogError`` -- so one such entry in a stored body failed the tool call with an
unhandled exception, and the whole item became unreadable with ``since=``.

The IDs are not caller-supplied: ``find_entry_spans`` takes whatever sits between
``<sub>`` and ``</sub>`` in the stored body. ``wrap_entry`` refuses to adopt an ID that is
not a real timestamp, but bodies written before that guard, and bodies edited in the
GitHub UI, still carry them.

Same defect, same fix as d0f7bee87: raise ``ValidationError``, a ``BacklogError``
subclass, which ``backlog_view`` already renders as an ``error`` field.
"""

from __future__ import annotations

import pytest

from backlog_core.entry_blocks import parse_entries
from backlog_core.models import BacklogError

# An entry-shaped block whose ID is a word, not a timestamp.
_UNTIMESTAMPED_BODY = "<div><sub>seeded</sub>legacy content</div>"


def test_since_read_over_an_untimestamped_entry_refuses_as_a_backlog_error() -> None:
    """The refusal must be catchable by the handler ``backlog_view`` actually has."""
    with pytest.raises(BacklogError, match="does not contain a valid ISO timestamp prefix"):
        parse_entries(_UNTIMESTAMPED_BODY, since="2026-01-01")


def test_a_since_less_read_is_unaffected() -> None:
    """Only the ``since`` filter parses IDs, so the default read still returns the entry."""
    assert [e.content for e in parse_entries(_UNTIMESTAMPED_BODY)] == ["legacy content"]
