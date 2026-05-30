"""Shared helpers and cross-file body constants for the #2495 view test suite.

These helpers are referenced by multiple split test modules in
``backlog_core/tests/``.  The underscore prefix prevents pytest from
collecting this module as a test file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backlog_core.models import BacklogItem, Section, ViewItemResult

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Cross-file body constants (referenced by classes in more than one target file)
# ---------------------------------------------------------------------------

# A multi-section body padded so its serialised response exceeds _VIEW_TOKEN_BUDGET
# the auto-compact gate engages, mirroring the real #2438 body.  Sections use
# the same ``## `` top-level / ``### `` subsection mix as real issue bodies.
_FILLER = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 60  # ~3.3k chars per block

_OVER_BUDGET_BODY = (
    "## Story\n\nAs an agent I want sections.\n\n"
    f"## Description\n\n{_FILLER}\n\n"
    f"## RT-ICA\n\n{_FILLER}\n\n"
    f"## Issue Classification\n\n{_FILLER}\n\n"
    f"## Root-Cause Analysis\n\n{_FILLER}\n\n"
    f"## Impact Radius\n\n{_FILLER}\n\n"
)

# A body whose SINGLE section's own content exceeds _VIEW_TOKEN_BUDGET (4000
# tokens ~= 16k chars).  Requesting that one section narrows to a slice that is
# itself still over budget, so the gate must NOT be bypassed by the narrowing.
_HUGE_SINGLE = "Lorem ipsum dolor sit amet consectetur adipiscing elit. " * 600  # ~33k chars


# ---------------------------------------------------------------------------
# Shared helper functions
# ---------------------------------------------------------------------------


def _make_local_item(title: str = "Issue 2495") -> BacklogItem:
    """Minimal local BacklogItem so the GitHub-enrichment branch is exercised."""
    return BacklogItem(title=title, sections={"Acceptance Criteria": Section()})


def _patch_github_body(mocker: MockerFixture, issue_num: int, body: str) -> None:
    """Patch the operations layer so view_item enriches from a controlled body."""
    local_item = _make_local_item()
    mocker.patch("backlog_core.operations.parse_backlog", return_value=[local_item])
    mocker.patch("backlog_core.operations.find_item", return_value=local_item)
    mocker.patch("backlog_core.operations.parse_issue_selector", return_value=issue_num)

    def _inject_body(result: ViewItemResult, issue: str, repo: str = "") -> bool:
        result.body = body
        return True

    mocker.patch("backlog_core.operations.view_enrich_from_github", side_effect=_inject_body)


def _resp_body(resp: dict[str, object]) -> str:
    """Return the response ``body`` as a typed ``str`` (boundary accessor).

    ``backlog_view`` returns ``dict[str, object]``; ``dict.get`` therefore yields
    ``object``.  This narrows the ``body`` field to ``str`` once so call sites do
    not each repeat an ``isinstance`` narrowing inside a compound assertion.

    Args:
        resp: Raw response dict from ``backlog_view``.

    Returns:
        The ``body`` field as a ``str``.

    Raises:
        AssertionError: When the ``body`` field is absent or not a ``str``.
    """
    body = resp.get("body")
    assert isinstance(body, str), f"response 'body' must be a str; got {type(body).__name__}."
    return body


def _resp_metadata(resp: dict[str, object]) -> list[dict[str, object]]:
    """Return ``sections_metadata`` as a list of typed dicts (boundary accessor).

    ``backlog_view`` returns ``dict[str, object]``; each metadata entry is itself a
    serialised ``SectionMeta`` dict.  Validating the shape here once yields fully
    typed ``dict[str, object]`` entries so call sites can index ``"name"`` without
    repeating ``isinstance`` narrowing or hitting ``dict.get`` overload mismatches.

    Args:
        resp: Raw response dict from ``backlog_view``.

    Returns:
        A list of ``dict[str, object]`` entries from ``sections_metadata``.

    Raises:
        AssertionError: When the field is absent, not a list, or contains non-dict entries.
    """
    meta = resp.get("sections_metadata")
    assert isinstance(meta, list), f"response 'sections_metadata' must be a list; got {type(meta).__name__}."
    entries: list[dict[str, object]] = []
    for entry in meta:
        assert isinstance(entry, dict), f"each metadata entry must be a dict; got {type(entry).__name__}."
        entries.append({str(k): v for k, v in entry.items()})
    return entries


__all__ = [
    "_FILLER",
    "_HUGE_SINGLE",
    "_OVER_BUDGET_BODY",
    "_make_local_item",
    "_patch_github_body",
    "_resp_body",
    "_resp_metadata",
]
