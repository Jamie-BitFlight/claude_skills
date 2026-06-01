"""TDD tests for AmbiguousSectionRefError on slug collision in resolve_section().

Phase 0, Concern C2. These tests are authored INDEPENDENTLY of the fix implementation
(T03) to ensure they validate the desired behavior, not just consistency with the
implementation.

Red-state contract (pre-fix):
  test_resolve_section_raises_on_slug_collision FAILS — current code returns first match
  silently instead of raising AmbiguousSectionRefError.

Green-state contract (post-fix, T03):
  Both tests pass — resolve_section raises on collision, returns SectionNode on unique slug.
"""

from __future__ import annotations

import pytest
from progressive_markdown.exceptions import AmbiguousSectionRefError
from progressive_markdown.models import SectionNode
from progressive_markdown.navigator import ProgressiveMarkdownNavigator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_DOCUMENT_WITH_SLUG_COLLISION = """\
## Background

First background section content.

## Background

Second background section content.

## Overview

This section has a unique slug.
"""


# ---------------------------------------------------------------------------
# Collision test (RED pre-fix)
# ---------------------------------------------------------------------------


def test_resolve_section_raises_on_slug_collision() -> None:
    """resolve_section raises AmbiguousSectionRefError when two sections share a slug.

    PRE-FIX STATE: This test MUST FAIL against the current navigator.py because
    lines ~335-339 silently return the first matching section instead of raising.
    A passing result before T03 is implemented indicates the fixture is broken.

    POST-FIX EXPECTATION (T03): AmbiguousSectionRefError is raised with a message
    that names the ambiguous slug and lists both colliding selectors so the caller
    can construct an unambiguous reference.
    """
    nav = ProgressiveMarkdownNavigator.from_markdown(_DOCUMENT_WITH_SLUG_COLLISION)
    doc = nav.current_document()

    # Guard: the fixture must actually produce a slug collision.
    colliding_ids = doc.sections_by_slug.get("background", [])
    assert len(colliding_ids) == 2, (
        f"Test fixture must produce exactly 2 sections with slug 'background', "
        f"got {len(colliding_ids)}. Check that the markdown has two '## Background' headings."
    )

    # Derive expected selectors dynamically so the assertion survives selector-format changes.
    colliding_selectors = [doc.sections[sid].selector for sid in colliding_ids]

    with pytest.raises(AmbiguousSectionRefError) as exc_info:
        nav.resolve_section("background")

    message = str(exc_info.value)

    # The message must name the ambiguous slug so the caller knows what was looked up.
    assert "background" in message, (
        f"Exception message must mention the ambiguous slug 'background'. "
        f"Got: {message!r}"
    )

    # The message must list BOTH colliding selectors as disambiguation hints so the
    # caller can switch to an unambiguous selector on retry.
    for selector in colliding_selectors:
        assert selector in message, (
            f"Expected colliding selector {selector!r} in exception message to help "
            f"disambiguate. Got: {message!r}"
        )


# ---------------------------------------------------------------------------
# Control test (passes against current code — unique slug path is unaffected)
# ---------------------------------------------------------------------------


def test_resolve_section_unique_slug_returns_section_node() -> None:
    """resolve_section returns the SectionNode when the slug is unambiguous.

    This is a control test: it must pass against BOTH the current code and the
    fixed code (T03). Ensures the fix does not introduce false positives for
    sections whose slug appears only once in the document.
    """
    nav = ProgressiveMarkdownNavigator.from_markdown(_DOCUMENT_WITH_SLUG_COLLISION)

    result = nav.resolve_section("overview")

    assert isinstance(result, SectionNode), (
        f"resolve_section('overview') must return a SectionNode for a unique slug. "
        f"Got {type(result).__name__!r}."
    )
    assert result.title == "Overview", (
        f"Resolved section title must be 'Overview'. Got {result.title!r}."
    )
    assert result.slug == "overview", (
        f"Resolved section slug must be 'overview'. Got {result.slug!r}."
    )
