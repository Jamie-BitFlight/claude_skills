"""Regression tests against the REAL #3152 body — the boundary-scanner defect (#3157), Option B.

Every other regression test in ``test_section_boundary_scanner.py`` uses a small,
hand-built body. That is deliberate for isolating one behaviour at a time, but it
is also exactly the shape of reproduction that let this defect survive two prior
patches: a hand-built body that merely *resembles* the failure proves the fix
works on the resemblance, not on the real pathology.

This module instead freezes the REAL, network-fetched, agent-managed body for
backlog item #3152 as a committed fixture (``fixtures/issue-3152-resolved-body.md``,
derived from ``fixtures/issue-3152.yaml`` via
``github_sync.render_issue_body(yaml_io.load_item(...))`` — verified element-identical
to a live network run of the same item) and drives the real assembly path against
it. The only thing ever stubbed is the network fetch
(``view_enrich_from_github``, via :func:`_patch_github_body`); every function
between that seam and the assertion is the genuine production code path.

Six ``operations.py`` consumers previously re-implemented ``## ``/``### ``
boundary detection with the naive ``_SECTION_BOUNDARY_RE`` line regex
(``^#{2,3} (.+?)$``), which cannot tell a real section heading from a
heading-shaped line quoted inside an entry block's own content (e.g. a
fact-checker verdict quoting one claim per ``## Claim ...`` heading). On this
item's real body that regex invents 46 phantom sections where only 10 are
real, and — more seriously — two of those six consumers silently return the
WRONG or TRUNCATED section content while reporting success
(``matched=True``, no ``section_filter_miss``). All six now delegate to
:func:`~backlog_core.parsing.split_body_sections`, the entry-block-aware
marko-AST splitter, and ``_SECTION_BOUNDARY_RE`` itself has been deleted.

Correction against the count some earlier grooming discussion used: the real
answer is 10 sections, not 9. ``Description`` is a body section rendered from
the ``description`` field and is not a key in ``item.sections`` — a test
asserting 9 through the body-parsing path fails on CORRECT code.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from backlog_core import operations
from backlog_core.models import ViewItemResult
from backlog_core.operations import _apply_body_section_filter, narrow_body_to_named_sections
from backlog_core.parsing import split_body_sections
from backlog_core.tests._view_test_helpers import _patch_github_body

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_FIXTURE_BODY = (Path(__file__).parent / "fixtures" / "issue-3152-resolved-body.md").read_text()

# The 10 real top-level sections in document order, independently verified
# against ``fixtures/issue-3152.yaml`` (9 ``item.sections`` keys plus the
# ``description``-field-rendered ``Description`` section, which is never a
# key in ``item.sections`` — see module docstring).
_REAL_SECTION_NAMES = frozenset({
    "Description",
    "Fact-Check",
    "RT-ICA",
    "Issue Classification",
    "Impact Radius",
    "Acceptance Criteria",
    "Story",
    "Context",
    "Root-Cause Analysis",
    "Resolution",
})


class TestFixtureHasThePathology:
    """Step 1 (design §3): assert the INPUT has the defect's precondition first.

    A test that only asserts the output can pass by accident if the fixture
    never actually exercised the pathology. These assertions fail loudly if a
    future fixture regeneration produces a body that no longer contains
    heading-shaped lines nested inside entry-block content.
    """

    def test_fixture_is_the_real_large_resolved_body(self) -> None:
        """The fixture is the real ~72KB resolved body, not a small stand-in."""
        assert len(_FIXTURE_BODY) > 70_000, (
            f"expected the real #3152 resolved body (>70,000 chars), got {len(_FIXTURE_BODY)}"
        )

    def test_fixture_contains_multiple_entry_blocks(self) -> None:
        """The fixture contains the timestamped entry-block wrappers the defect depends on."""
        assert _FIXTURE_BODY.count("<div><sub>") >= 9, (
            f"expected at least 9 entry blocks, got {_FIXTURE_BODY.count('<div><sub>')}"
        )

    def test_fixture_contains_heading_shaped_lines_inside_entry_content(self) -> None:
        """The fixture contains the phantom ``## Claim `` headings nested in an entry.

        These are the exact lines the naive ``#{2,3}`` line regex mistook for
        section boundaries.
        """
        claim_headings = re.findall(r"^## Claim ", _FIXTURE_BODY, re.MULTILINE)
        assert len(claim_headings) >= 27, f"expected at least 27 '## Claim ' lines, got {len(claim_headings)}"


class TestViewItemReturnsTenSectionsNotFortySix:
    """Step 2 (design §3): drive the real summary-assembly path through ``view_item``.

    The only stub is the network fetch (:func:`_patch_github_body` patches
    ``view_enrich_from_github``); ``view_item`` -> ``_assemble_view_compact`` ->
    ``_build_sections_compact`` -> ``split_body_sections`` all run for real.

    An offline ``view_item("#3152")`` call proves nothing here: with no body
    injected, ``result.body`` stays empty and the compact assembly falls back
    to the YAML-structured path (``_populate_yaml_item_compact``), which never
    calls ``_build_sections_compact`` at all — so it returns the same count on
    broken and fixed code alike. Injecting the real resolved body via the
    GitHub-enrichment seam is what actually exercises the buggy path.
    """

    def test_view_item_compact_reports_ten_real_sections(self, mocker: MockerFixture) -> None:
        """``view_item(include_content=False)`` reports 10 sections for the real body.

        RED before the fix: 46 (36 phantom ``## Claim``/``### Code —`` headings
        nested inside entry-block content, mistaken for section boundaries).
        """
        _patch_github_body(mocker, 3152, _FIXTURE_BODY)

        result = operations.view_item(selector="3152", include_content=False)

        names = {m["name"] for m in result.sections_metadata}
        assert len(result.sections_metadata) == 10, (
            f"expected 10 sections, got {len(result.sections_metadata)}: {sorted(names)}"
        )
        assert names == _REAL_SECTION_NAMES, f"unexpected section-name set: {sorted(names)}"
        assert not any(name.startswith("Claim ") for name in names), (
            "no phantom 'Claim ...' section from entry-block content may appear"
        )

    def test_view_item_compact_sections_index_lists_no_phantom_claims(self, mocker: MockerFixture) -> None:
        """The rendered ``sections_index`` also excludes phantom entry-content headings."""
        _patch_github_body(mocker, 3152, _FIXTURE_BODY)

        result = operations.view_item(selector="3152", include_content=False)

        assert "Claim" not in result.sections_index, (
            f"sections_index must not list a phantom 'Claim' entry:\n{result.sections_index}"
        )


class TestNarrowBodyToNamedSectionsPreservesFullContent:
    """Step 3 (design §3): the two bugs Option A (patching only ``_build_sections_compact``)

    would have left live. Both silently reported success while returning the
    wrong or truncated content — worse than an inflated count, since an agent
    reading a truncated section has no signal that it was truncated.
    """

    def test_fact_check_section_is_not_truncated_to_178_chars(self) -> None:
        """RED before the fix: 178 chars (one phantom ``## Claim`` fragment, not the real section)."""
        narrowed, matched = narrow_body_to_named_sections(_FIXTURE_BODY, ["Fact-Check"])

        assert matched, "Fact-Check must resolve to a real section"
        assert len(narrowed) > 25_000, (
            f"Fact-Check must return its full ~28KB content, got {len(narrowed)} chars: {narrowed[:200]!r}"
        )
        assert "## Fact-Check" in narrowed

    def test_impact_radius_section_is_not_truncated_to_under_ten_thousand_chars(self) -> None:
        """RED before the fix: 9,786 chars (63% content loss from phantom sub-headings)."""
        narrowed, matched = narrow_body_to_named_sections(_FIXTURE_BODY, ["Impact Radius"])

        assert matched, "Impact Radius must resolve to a real section"
        assert len(narrowed) > 24_000, f"Impact Radius must return its full ~26KB content, got {len(narrowed)} chars"
        assert "## Impact Radius" in narrowed


class TestApplyBodySectionFilterResolvesTheCorrectSection:
    """Step 3 (design §3): numeric-index resolution must land on the real section, not a phantom one."""

    def test_numeric_index_four_resolves_to_impact_radius_not_a_phantom_claim(self) -> None:
        """RED before the fix: index 4 resolved to 'Claim A: ...' — a phantom entry-content heading."""
        result = ViewItemResult()

        narrowed = _apply_body_section_filter(result, _FIXTURE_BODY, "4")

        assert not result.section_filter_miss
        first_line = narrowed.splitlines()[0]
        assert first_line == "## Impact Radius", f"index 4 resolved to the wrong section: {first_line!r}"
        assert "Claim A" not in narrowed.splitlines()[0]


class TestFalsification:
    """Step 4 (design §3): falsification checks that must fail to fail.

    A test that cannot be shown to fail against the pre-fix defect, or that
    passes for an unrelated reason, is not evidence the fix works.
    """

    def test_old_naive_regex_produces_forty_six_sections_on_the_same_real_body(self) -> None:
        """The deleted ``_SECTION_BOUNDARY_RE`` pattern, run inline against the real body.

        ``_SECTION_BOUNDARY_RE`` (``operations.py``, pre-#3157) was
        ``re.compile(r"^#{2,3} (.+?)$", re.MULTILINE)``. It no longer exists
        in ``operations.py`` (that is the point of this fix), so this test
        reproduces it verbatim as a local pattern to prove the fixture and the
        new tests above are not vacuously true — the naive scan really did
        (and, unpatched, still would) misreport 46 sections for this exact body.
        """
        old_naive_section_boundary_re = re.compile(r"^#{2,3} (.+?)$", re.MULTILINE)

        old_count = len(old_naive_section_boundary_re.findall(_FIXTURE_BODY))

        assert old_count == 46, (
            f"expected the naive regex to (mis)report 46 sections on the real body, got {old_count}. "
            "If this fixture changed, re-verify the 46-vs-10 defect numbers in the design brief."
        )

    def test_regex_and_splitter_agree_on_a_body_with_no_entry_blocks(self) -> None:
        """The fix changes entry-block behaviour only, not plain-heading behaviour.

        This uses a synthetic body — not the real #3152 fixture — because the
        property under test here is "the two boundary detectors agree when
        entry-block-awareness is irrelevant", which is unrelated to the #3152
        defect and does not risk a hypothesis-shaped false reproduction: there
        is no bug being illustrated, only an equivalence being checked.
        """
        plain_body = (
            "### Concerns\n\nRace condition X.\n\n## Impact Radius\n\nAffects A and B.\n\n### Plan\n\nStep 1.\n"
        )
        old_naive_section_boundary_re = re.compile(r"^#{2,3} (.+?)$", re.MULTILINE)

        old_names = [m.group(1).strip() for m in old_naive_section_boundary_re.finditer(plain_body)]
        new_names = [span.name for span in split_body_sections(plain_body)]

        assert old_names == new_names, f"naive regex and split_body_sections disagree: {old_names} != {new_names}"
