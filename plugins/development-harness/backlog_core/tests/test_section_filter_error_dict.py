"""RED tests for ADR-3: section-filter miss returns an explicit error dict.

These tests MUST FAIL before T22's implementation and PASS after.

ADR-3 Decision (selected option 3, "Error-on-miss, suggestion-in-error"):
    When a ``section=`` or ``sections=[...]`` filter misses, ``backlog_view``
    returns an error dict instead of silently returning content:

    .. code-block:: python

        {
            "error": "Section not found: <filter>",
            "valid_sections": [...real section names...],
            "suggestion": "Did you mean: 'X'?",   # present only for near-misses
            "section_filter_miss": True,            # flag preserved (backward-compat)
            "messages": [], "warnings": [], "errors": [...]
        }

    No body or content fields appear in the error response.  The
    ``section_filter_miss`` flag is **kept** in error responses for backward
    compatibility — callers that already check the flag continue to work.

Discriminator between pre-fix and post-fix:
    The ``"error"`` and ``"valid_sections"`` keys are absent from the current
    response.  These are the primary RED assertions.  A secondary assertion
    confirms ``"body"`` is absent from the error response (pre-fix: ``"body"``
    is always present as either ``""`` or the full content).

Three ``operations.py`` sites exercised — parametrized via input mode:
    * ``section=`` with ``include_content=True`` exercises site ~3020
      (``_apply_body_section_filter`` setter) AND site ~3167 (caller check
      in ``_assemble_view_content``).
    * ``section=`` with ``include_content=False`` exercises site ~3094
      (``_assemble_view_compact`` setter).
    * ``sections=[...]`` exercises the ``_filter_view_sections`` server wrapper.

Fixture: ``issue-2521-full.json`` — valid section headers (from ``##`` lines):
    Story, Description, Acceptance Criteria, Context,
    Groomed (2026-06-01), Concerns, RT-ICA

Source: architect spec §4.6 and ADR-3.

Test naming convention: every test contains ``section_miss_error`` or
``section_hit`` so ``pytest -k "section_miss_error or section_hit"``
selects the full ADR-3 suite.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING

import backlog_core.server as server
from backlog_core.tests._view_test_helpers import _patch_github_body

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Module-level fixture constants
# ---------------------------------------------------------------------------

_FIXTURE_DIR = Path(__file__).parent / "fixtures"

# Full body text from regenerated #2521 fixture (T10 produced this file).
# Contains ## section headers for: Sections (index), Story, Description,
# Acceptance Criteria, Context, Groomed (2026-06-01), Concerns, RT-ICA.
_ISSUE_2521_BODY: str = json.loads(
    (_FIXTURE_DIR / "issue-2521-full.json").read_text()
)["body"]

# Known real content-section names from the #2521 body (excludes the
# ## Sections index header at the top).
_KNOWN_SECTIONS_2521: frozenset[str] = frozenset(
    {
        "Story",
        "Description",
        "Acceptance Criteria",
        "Context",
        "Groomed (2026-06-01)",
        "Concerns",
        "RT-ICA",
    }
)

# A filter that cannot match any section by any mechanism:
#   - not a numeric index
#   - not a substring of any section name
#   - not a regex that matches any header
_NONEXISTENT_FILTER = "nonexistent_xyz_no_match_8423"

# Near-miss filter: "Concernz" is Levenshtein-distance-1 from "Concerns"
# (final character substitution 's' → 'z').  It is NOT a substring of
# "Concerns", so both the singular-section= and sections=[] paths see a miss.
_NEAR_MISS_FILTER = "Concernz"
_NEAR_MISS_TARGET = "Concerns"

# A valid exact section name for the regression guard.
_VALID_SECTION = "Concerns"


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


def _patch_issue_2521(mocker: MockerFixture) -> None:
    """Patch operations layer so view_item enriches with the #2521 fixture body.

    Args:
        mocker: pytest-mock fixture for patching.
    """
    _patch_github_body(mocker, issue_num=2521, body=_ISSUE_2521_BODY)


# ---------------------------------------------------------------------------
# Site ~3020 + ~3167 — section= with include_content=True (full-body path)
# ---------------------------------------------------------------------------


class TestSectionMissErrorDictIncludeContentTrue:
    """section= miss with include_content=True returns an error dict.

    Exercises ``_apply_body_section_filter`` setter (~3020) and the caller-check
    in ``_assemble_view_content`` (~3167).
    """

    def test_section_miss_error_dict_has_error_key_include_content_true(
        self, mocker: MockerFixture
    ) -> None:
        """section= miss response contains an 'error' key.

        Arrange: GitHub enrichment injects #2521 body; section='nonexistent_xyz_no_match_8423'
                 is absent from that body and cannot match any header by any mechanism.
        Act: call backlog_view(summary=False, include_content=True, section=<miss>).
        Assert: response dict contains 'error' key.

        RED: fails because the current code sets section_filter_miss=True and returns
        an empty body — the response has no 'error' key.  After ADR-3 fix, the
        handler early-returns an error dict instead of a content response.
        """
        # Arrange
        _patch_issue_2521(mocker)

        # Act
        resp = asyncio.run(
            server.backlog_view(
                selector="2521",
                summary=False,
                section=_NONEXISTENT_FILTER,
            )
        )

        # Assert
        assert "error" in resp, (
            f"Response must contain 'error' key on section= miss. "
            f"Got keys: {sorted(resp.keys())}. "
            "Before ADR-3 fix: response has section_filter_miss=True but no 'error' key."
        )

    def test_section_miss_error_dict_has_valid_sections_key_include_content_true(
        self, mocker: MockerFixture
    ) -> None:
        """section= miss response contains a non-empty 'valid_sections' list.

        Arrange: same as above.
        Act: call backlog_view(summary=False, include_content=True, section=<miss>).
        Assert: 'valid_sections' is a non-empty list containing at least one
                known section from #2521.

        RED: fails because the current response does not contain 'valid_sections'.
        """
        # Arrange
        _patch_issue_2521(mocker)

        # Act
        resp = asyncio.run(
            server.backlog_view(
                selector="2521",
                summary=False,
                section=_NONEXISTENT_FILTER,
            )
        )

        # Assert — key present
        assert "valid_sections" in resp, (
            f"Response must contain 'valid_sections' key on section= miss. "
            f"Got keys: {sorted(resp.keys())}."
        )
        valid_raw: object = resp["valid_sections"]
        assert isinstance(valid_raw, list), (
            f"'valid_sections' must be a list; got {type(valid_raw).__name__}."
        )
        assert len(valid_raw) > 0, (
            f"'valid_sections' must be non-empty; got {valid_raw!r}."
        )
        # At least one real #2521 section must appear so callers know what to request.
        known_present = [s for s in valid_raw if s in _KNOWN_SECTIONS_2521]
        assert known_present, (
            f"'valid_sections' {valid_raw!r} must contain at least one of the known "
            f"#2521 sections: {sorted(_KNOWN_SECTIONS_2521)}."
        )

    def test_section_miss_error_dict_no_body_include_content_true(
        self, mocker: MockerFixture
    ) -> None:
        """section= miss error response does not include a 'body' field.

        No content is returned on a miss (ADR-3 selected option 3).

        Arrange: same as above.
        Act: call backlog_view(summary=False, include_content=True, section=<miss>).
        Assert: 'body' key absent from response dict.

        RED: fails because the current code builds the response from
        result.model_dump() which always includes 'body': ''.  The error dict
        returned after the fix omits 'body' entirely.
        """
        # Arrange
        _patch_issue_2521(mocker)

        # Act
        resp = asyncio.run(
            server.backlog_view(
                selector="2521",
                summary=False,
                section=_NONEXISTENT_FILTER,
            )
        )

        # Assert
        assert "body" not in resp, (
            f"Error response must NOT include 'body' key. "
            f"Got body={resp.get('body')!r}. "
            "Before fix: body='' is present because model_dump() always includes it."
        )


# ---------------------------------------------------------------------------
# Site ~3094 — section= with include_content=False (compact / metadata path)
# ---------------------------------------------------------------------------


class TestSectionMissErrorDictCompactMode:
    """section= miss with include_content=False returns an error dict.

    Exercises the ``_assemble_view_compact`` setter at ~3094.
    """

    def test_section_miss_error_dict_has_error_key_compact_mode(
        self, mocker: MockerFixture
    ) -> None:
        """section= miss in compact mode (include_content=False) has 'error' key.

        Arrange: GitHub enrichment injects #2521 body; section=<nonexistent>;
                 include_content=False routes to _assemble_view_compact.
        Act: call backlog_view(summary=False, include_content=False, section=<miss>).
        Assert: response contains 'error' key.

        RED: fails because _assemble_view_compact currently sets
        section_filter_miss=True but does NOT produce an error dict — 'error'
        is absent from the response.
        """
        # Arrange
        _patch_issue_2521(mocker)

        # Act
        resp = asyncio.run(
            server.backlog_view(
                selector="2521",
                summary=False,
                include_content=False,
                section=_NONEXISTENT_FILTER,
            )
        )

        # Assert
        assert "error" in resp, (
            f"Compact-mode response must contain 'error' key on section= miss. "
            f"Got keys: {sorted(resp.keys())}."
        )

    def test_section_miss_error_dict_has_valid_sections_key_compact_mode(
        self, mocker: MockerFixture
    ) -> None:
        """section= miss in compact mode response includes 'valid_sections'.

        RED: fails because the current compact-mode response does not include
        'valid_sections'; the flag-only response omits it.
        """
        # Arrange
        _patch_issue_2521(mocker)

        # Act
        resp = asyncio.run(
            server.backlog_view(
                selector="2521",
                summary=False,
                include_content=False,
                section=_NONEXISTENT_FILTER,
            )
        )

        # Assert
        assert "valid_sections" in resp, (
            f"Compact-mode error response must include 'valid_sections'. "
            f"Got keys: {sorted(resp.keys())}."
        )
        valid_raw: object = resp["valid_sections"]
        assert isinstance(valid_raw, list), (
            f"'valid_sections' must be a list; got {type(valid_raw).__name__}."
        )
        assert len(valid_raw) > 0, (
            f"'valid_sections' must be non-empty; got {valid_raw!r}."
        )

    def test_section_miss_error_dict_no_body_compact_mode(
        self, mocker: MockerFixture
    ) -> None:
        """section= miss in compact mode error response does not include 'body'.

        RED: fails because model_dump() always includes 'body' in the response
        dict; the error response after fix should not include it.
        """
        # Arrange
        _patch_issue_2521(mocker)

        # Act
        resp = asyncio.run(
            server.backlog_view(
                selector="2521",
                summary=False,
                include_content=False,
                section=_NONEXISTENT_FILTER,
            )
        )

        # Assert
        assert "body" not in resp, (
            f"Compact-mode error response must NOT include 'body'. "
            f"Got body={resp.get('body')!r}."
        )


# ---------------------------------------------------------------------------
# Server wrapper — sections=[...] plural path (_filter_view_sections)
# ---------------------------------------------------------------------------


class TestSectionsFilterPluralMissErrorDict:
    """sections=[...] miss exercises the ``_filter_view_sections`` server wrapper."""

    def test_section_miss_error_dict_has_error_key_sections_plural(
        self, mocker: MockerFixture
    ) -> None:
        """sections=[nonexistent] response has 'error' key.

        Arrange: GitHub enrichment injects #2521 body;
                 sections=['nonexistent_xyz_no_match_8423'] does not match any
                 structured section key, sections_metadata entry, or body header.
        Act: call backlog_view(summary=False, sections=[<miss>]).
        Assert: response dict contains 'error' key.

        RED: fails because _filter_view_sections currently sets
        section_filter_miss=True on the response and result, but does NOT add
        an 'error' key.  The response includes the full body unchanged (the
        "silent fallback" described in ADR-3 context).
        """
        # Arrange
        _patch_issue_2521(mocker)

        # Act
        resp = asyncio.run(
            server.backlog_view(
                selector="2521",
                summary=False,
                sections=[_NONEXISTENT_FILTER],
            )
        )

        # Assert
        assert "error" in resp, (
            f"sections=[] miss response must contain 'error' key. "
            f"Got keys: {sorted(resp.keys())}. "
            "Before ADR-3 fix: section_filter_miss=True but no 'error' key."
        )

    def test_section_miss_error_dict_has_valid_sections_key_sections_plural(
        self, mocker: MockerFixture
    ) -> None:
        """sections=[nonexistent] response has non-empty 'valid_sections' list.

        RED: fails because _filter_view_sections does not add 'valid_sections'
        to the response; the current response has only section_filter_miss=True.
        """
        # Arrange
        _patch_issue_2521(mocker)

        # Act
        resp = asyncio.run(
            server.backlog_view(
                selector="2521",
                summary=False,
                sections=[_NONEXISTENT_FILTER],
            )
        )

        # Assert — key present
        assert "valid_sections" in resp, (
            f"sections=[] miss response must contain 'valid_sections'. "
            f"Got keys: {sorted(resp.keys())}."
        )
        valid_raw: object = resp["valid_sections"]
        assert isinstance(valid_raw, list), (
            f"'valid_sections' must be a list; got {type(valid_raw).__name__}."
        )
        assert len(valid_raw) > 0, (
            f"'valid_sections' must be non-empty; got {valid_raw!r}."
        )
        known_present = [s for s in valid_raw if s in _KNOWN_SECTIONS_2521]
        assert known_present, (
            f"'valid_sections' {valid_raw!r} must contain at least one known #2521 "
            f"section: {sorted(_KNOWN_SECTIONS_2521)}."
        )

    def test_section_miss_error_dict_no_body_sections_plural(
        self, mocker: MockerFixture
    ) -> None:
        """sections=[nonexistent] error response does not include 'body'.

        RED: fails because _filter_view_sections does not clear the body on a
        total miss — the response currently includes the full #2521 body.
        This is the silent-fallback described in ADR-3: the caller asked for a
        specific section but received the entire item content with only a flag.
        """
        # Arrange
        _patch_issue_2521(mocker)

        # Act
        resp = asyncio.run(
            server.backlog_view(
                selector="2521",
                summary=False,
                sections=[_NONEXISTENT_FILTER],
            )
        )

        # Assert — 'body' must be absent (error dict has no content fields)
        assert "body" not in resp, (
            f"sections=[] miss error response must NOT include 'body'. "
            f"Got body length: {len(str(resp.get('body', '')))} chars. "
            "Before fix: full body is returned because _filter_view_sections "
            "does not remove it on a total section miss."
        )


# ---------------------------------------------------------------------------
# Near-miss suggestion — Levenshtein closest-match hint in error
# ---------------------------------------------------------------------------


class TestSectionMissErrorDictSuggestion:
    """A near-miss section name yields a Levenshtein best-match suggestion.

    ADR-3 format: ``"suggestion": "Did you mean: 'Concerns'?"``
    Present only when a close match exists; omitted for completely random names.
    """

    def test_section_miss_error_dict_near_miss_has_suggestion_key(
        self, mocker: MockerFixture
    ) -> None:
        """section='Concernz' (distance 1 from 'Concerns') yields 'suggestion' key.

        Arrange: #2521 body (contains '## Concerns');
                 section='Concernz' — Levenshtein-1 from 'Concerns',
                 NOT a substring of any section name (so it is a genuine miss).
        Act: call backlog_view(summary=False, section='Concernz').
        Assert: response contains 'suggestion' key.

        RED: fails because the current response has no 'suggestion' key;
        the flag-only response omits all hint information.
        """
        # Arrange
        _patch_issue_2521(mocker)

        # Act
        resp = asyncio.run(
            server.backlog_view(
                selector="2521",
                summary=False,
                section=_NEAR_MISS_FILTER,
            )
        )

        # Assert
        assert "suggestion" in resp, (
            f"Near-miss filter {_NEAR_MISS_FILTER!r} (Levenshtein-1 from "
            f"{_NEAR_MISS_TARGET!r}) must produce a 'suggestion' key in the "
            f"error response.  Got keys: {sorted(resp.keys())}."
        )

    def test_section_miss_error_dict_near_miss_suggestion_references_closest(
        self, mocker: MockerFixture
    ) -> None:
        """Suggestion value for 'Concernz' references the closest valid section 'Concerns'.

        RED: fails because the current response has no 'suggestion' key.
        After fix: suggestion must be a non-empty string containing 'Concerns'.
        """
        # Arrange
        _patch_issue_2521(mocker)

        # Act
        resp = asyncio.run(
            server.backlog_view(
                selector="2521",
                summary=False,
                section=_NEAR_MISS_FILTER,
            )
        )

        # Assert — suggestion present
        assert "suggestion" in resp, (
            "'suggestion' key must be present for near-miss filter "
            f"{_NEAR_MISS_FILTER!r}."
        )
        suggestion: object = resp["suggestion"]
        assert isinstance(suggestion, str), (
            f"'suggestion' must be a str; got {type(suggestion).__name__}."
        )
        assert _NEAR_MISS_TARGET in suggestion, (
            f"Suggestion {suggestion!r} must reference the closest valid section "
            f"{_NEAR_MISS_TARGET!r}.  'Concernz' is Levenshtein-distance-1 from "
            f"'Concerns' (final char substitution 's' → 'z'); it is the uniquely "
            f"closest match."
        )

    def test_section_miss_error_dict_near_miss_sections_plural_has_suggestion(
        self, mocker: MockerFixture
    ) -> None:
        """sections=['Concernz'] plural miss also yields a 'suggestion' key.

        The _filter_view_sections wrapper handles the plural path; it must also
        compute and include a Levenshtein suggestion for near-misses.

        RED: fails because _filter_view_sections does not add 'suggestion' to
        the response.
        """
        # Arrange
        _patch_issue_2521(mocker)

        # Act
        resp = asyncio.run(
            server.backlog_view(
                selector="2521",
                summary=False,
                sections=[_NEAR_MISS_FILTER],
            )
        )

        # Assert
        assert "suggestion" in resp, (
            f"sections=[] near-miss {[_NEAR_MISS_FILTER]!r} must produce "
            f"'suggestion' key.  Got keys: {sorted(resp.keys())}."
        )
        suggestion_obj: object = resp["suggestion"]
        assert isinstance(suggestion_obj, str), (
            f"'suggestion' must be a str; got {type(suggestion_obj).__name__}."
        )
        assert _NEAR_MISS_TARGET in suggestion_obj, (
            f"Suggestion {suggestion_obj!r} must reference {_NEAR_MISS_TARGET!r}."
        )


# ---------------------------------------------------------------------------
# Regression guard — valid section must still succeed (passes pre- and post-fix)
# ---------------------------------------------------------------------------


class TestSectionHitRegressionGuard:
    """Valid section names continue to succeed after the ADR-3 fix.

    These tests PASS both before and after the fix — they guard against false
    positives where the fix accidentally errors on valid section names.
    """

    def test_section_hit_singular_no_error(self, mocker: MockerFixture) -> None:
        """section='Concerns' on #2521 body returns content, not an error.

        Arrange: #2521 body; section='Concerns' (present as '## Concerns').
        Act: call backlog_view(summary=False, section='Concerns').
        Assert: 'error' key absent; 'body' key present with non-empty content.
        """
        # Arrange
        _patch_issue_2521(mocker)

        # Act
        resp = asyncio.run(
            server.backlog_view(
                selector="2521",
                summary=False,
                section=_VALID_SECTION,
            )
        )

        # Assert — no error
        assert "error" not in resp, (
            f"Valid section={_VALID_SECTION!r} must NOT produce an error response. "
            f"Got: {resp.get('error')!r}."
        )
        # Assert — body present and non-empty
        body: object = resp.get("body")
        assert isinstance(body, str), (
            f"Valid section={_VALID_SECTION!r} must return a str 'body'. "
            f"Got {type(body).__name__}."
        )
        assert len(body) > 0, (
            f"Valid section={_VALID_SECTION!r} must return non-empty 'body'. "
            f"Got body={body!r}."
        )
        assert _VALID_SECTION in body, (
            f"Returned body must contain the '{_VALID_SECTION}' section content. "
            f"Body starts with: {body[:100]!r}."
        )

    def test_section_hit_plural_no_error(self, mocker: MockerFixture) -> None:
        """sections=['Concerns'] on #2521 body returns content, not an error.

        Arrange: #2521 body; sections=['Concerns'] (exact case-insensitive match).
        Act: call backlog_view(summary=False, sections=['Concerns']).
        Assert: 'error' key absent; 'section_filter_miss' False or absent.
        """
        # Arrange
        _patch_issue_2521(mocker)

        # Act
        resp = asyncio.run(
            server.backlog_view(
                selector="2521",
                summary=False,
                sections=[_VALID_SECTION],
            )
        )

        # Assert — no error
        assert "error" not in resp, (
            f"Valid sections=[{_VALID_SECTION!r}] must NOT produce an error response. "
            f"Got: {resp.get('error')!r}."
        )
        # Assert — section_filter_miss is False for a successful match
        assert resp.get("section_filter_miss") is not True, (
            f"section_filter_miss must not be True when sections=[{_VALID_SECTION!r}] "
            f"successfully matches.  Got: {resp.get('section_filter_miss')!r}."
        )
