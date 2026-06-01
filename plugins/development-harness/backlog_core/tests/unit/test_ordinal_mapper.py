"""Tests for OrdinalPathMapper — TDD, authored before T14 implementation.

These tests intentionally fail at collection (ModuleNotFoundError on
``backlog_core.ordinal_mapper``) until T14 creates that module.  That is the
correct TDD state.

Behavioral contract pinned by this file:

1. **Level-1 ordinals**: every ``NormalizedSection`` at index N produces an
   ``OrdinalEntry`` with ``ordinal=str(N)``.  Empty sections (entries=[]) are
   included in the map.
2. **Level-2 emission gate**: level-2 lines are emitted only when
   ``entry_count > 1`` OR ``section_est_tokens > TOKEN_BUDGET``.
3. **est_tokens exact cl100k_base**: ``est_tokens == len(ENCODING.encode(body))``
   — chars//4 approximation would fail the assertion.
4. **resolve() raises OrdinalNotFoundError on miss**: the exception carries
   the full ``valid_ordinals`` list so agents recover without a second round-trip.
5. **format_map_line caps**: title truncated at 50 chars (with "…"); preview at
   60 chars.
6. **RT-ICA ordinal derived dynamically**: the ordinal for RT-ICA in #2515 is
   found by searching the built map by title — never hardcoded.

Implementation note for T14:
  Import surface is ``backlog_core.ordinal_mapper`` (module not yet written).
  Once T14 ships, pytest runs will show these tests passing instead of erroring
  at collection.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import tiktoken
import tiktoken.registry

from backlog_core.content_normalizer import ItemContentNormalizer, NormalizedEntry, NormalizedSection
from backlog_core.disclosure_types import OrdinalNotFoundError

# T14 creates this module — ModuleNotFoundError at collection until then (TDD state)
from backlog_core.ordinal_mapper import OrdinalEntry, OrdinalPathMapper, ResolvedUnit

# ---------------------------------------------------------------------------
# Real-encoding availability guard
# ---------------------------------------------------------------------------


def _real_cl100k_available() -> bool:
    """Return True iff real cl100k_base (not the offline stub) is cached.

    The parent conftest pre-warms the tiktoken registry before any import of
    ``backlog_core.server``.  After that, ``ENCODINGS["cl100k_base"]`` is either
    the real BPE encoding or a deterministic ``_StubEncoder``.

    Distinguisher: real cl100k_base encodes ``"hello"`` as 1 BPE token (id 15339).
    The stub returns ``[0] * ((5+3)//4) == [0, 0]`` (2 elements).
    """
    enc = tiktoken.registry.ENCODINGS.get("cl100k_base")
    if enc is None:
        return False
    try:
        return len(enc.encode("hello")) == 1
    except Exception:  # noqa: BLE001 — stub/real encode() surface is narrow
        return False


_REAL_CL100K: bool = _real_cl100k_available()
_skip_without_real_enc = pytest.mark.skipif(
    not _REAL_CL100K,
    reason="Requires real cl100k_base encoding (not available offline)",
)

ENCODING: tiktoken.Encoding | None = (
    tiktoken.get_encoding("cl100k_base") if _REAL_CL100K else None
)

try:
    from progressive_markdown.list_navigator import TOKEN_BUDGET
except ImportError:
    TOKEN_BUDGET: int = 9_500  # mirror of _DEFAULT_BUDGET when env var absent

# ---------------------------------------------------------------------------
# Fixtures directory
# ---------------------------------------------------------------------------

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((_FIXTURES_DIR / name).read_text())


# ---------------------------------------------------------------------------
# Synthetic section builder
# ---------------------------------------------------------------------------


def _make_sections(*specs: tuple[str, list[str]]) -> list[NormalizedSection]:
    """Build ``list[NormalizedSection]`` with correct 0-based index values.

    Args:
        specs: Sequence of ``(title, [entry_content, ...])`` tuples.

    Returns:
        Ordered list where each section's ``index`` equals its position.
    """
    out: list[NormalizedSection] = []
    for idx, (title, entries) in enumerate(specs):
        out.append(
            NormalizedSection(
                index=idx,
                title=title,
                entries=[
                    NormalizedEntry(index=i, content=c) for i, c in enumerate(entries)
                ],
            )
        )
    return out


# ---------------------------------------------------------------------------
# Module-level fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def groomed_body_doc() -> list[NormalizedSection]:
    """5-section synthetic document for ordinal assignment tests.

    Structure::

        [0] Story                  - 1 entry (short, under budget)
        [1] Description            - 1 entry (short, under budget)
        [2] Acceptance Criteria    - 1 entry (short, under budget)
        [3] Context                - 1 entry (short, under budget)
        [4] Groomed (2026-06-01)   - 2 entries (entry_count > 1 -> gate fires):
              entry 0: "### Concerns\\nPre-existing concerns in progressive_markdown/..."
              entry 1: "### RT-ICA\\nRT-ICA Final: MCP progressive disclosure..."

    Section [4] has entry_count=2 so the level-2 emission gate fires for both
    "4.0" and "4.1" regardless of token size.  This makes level-2 assertions
    deterministic across real and stub encoders.
    """
    return _make_sections(
        (
            "Story",
            ["As a **developer** using Claude Code skills, I want token-efficient MCP access."],
        ),
        (
            "Description",
            ["The development harness has multiple MCP interfaces returning large data."],
        ),
        (
            "Acceptance Criteria",
            ["- [ ] Work matches description\n- [ ] Plan complete"],
        ),
        (
            "Context",
            ["- **Source**: Session observation\n- **Priority**: P1"],
        ),
        (
            "Groomed (2026-06-01)",
            [
                "### Concerns\nPre-existing concerns in progressive_markdown/ surfaced during the session.",
                "### RT-ICA\nRT-ICA Final: MCP progressive disclosure contract is feasible and necessary.",
            ],
        ),
    )


@pytest.fixture(scope="module")
def single_entry_doc() -> list[NormalizedSection]:
    """Three sections each with exactly one short entry — all under TOKEN_BUDGET."""
    return _make_sections(
        ("Alpha", ["Short alpha content."]),
        ("Beta", ["Short beta content."]),
        ("Gamma", ["Short gamma content."]),
    )


@pytest.fixture(scope="module")
def empty_section_doc() -> list[NormalizedSection]:
    """Three-section document where the middle section has zero entries."""
    return _make_sections(
        ("Header", ["Content of the header section."]),
        ("Empty", []),
        ("After Empty", ["Content that follows the empty section."]),
    )


@pytest.fixture(scope="module")
def normalized_2515() -> list[NormalizedSection]:
    """Fully normalized #2515 fixture (53-section large item).

    Loads the regenerated fixture from T01 and normalizes via
    ``ItemContentNormalizer``.
    """
    from backlog_core.models import ViewItemResult

    data = _load_fixture("issue-2515-full.json")
    return ItemContentNormalizer().normalize(ViewItemResult.model_validate(data))


# ---------------------------------------------------------------------------
# TC-O1: Level-1 ordinal assignment
# ---------------------------------------------------------------------------


class TestOrdinalAssignment:
    """Level-1 ordinals must match the 0-based NormalizedSection index."""

    def test_top_level_sections_get_integer_ordinals(
        self, groomed_body_doc: list[NormalizedSection]
    ) -> None:
        """Sections [0] through [4] receive ordinals '0', '1', '2', '3', '4'."""
        mapper = OrdinalPathMapper(groomed_body_doc)
        entries = mapper.build_map()

        level1 = [e for e in entries if "." not in e.ordinal]
        assert len(level1) == 5, (
            f"Expected 5 level-1 entries for 5 sections; got {len(level1)}."
        )
        for expected_int, entry in enumerate(level1):
            assert entry.ordinal == str(expected_int), (
                f"Level-1 entry {expected_int}: expected ordinal "
                f"'{expected_int}'; got {entry.ordinal!r}."
            )

    def test_level1_always_present_for_empty_sections(
        self, empty_section_doc: list[NormalizedSection]
    ) -> None:
        """Section with 0 entries still produces a level-1 OrdinalEntry."""
        mapper = OrdinalPathMapper(empty_section_doc)
        entries = mapper.build_map()

        level1_ordinals = {e.ordinal for e in entries if "." not in e.ordinal}
        assert "1" in level1_ordinals, (
            "Empty section at index 1 must produce level-1 OrdinalEntry with ordinal='1'."
        )

    def test_ordinal_format_is_digit_dotpath(
        self, groomed_body_doc: list[NormalizedSection]
    ) -> None:
        """All ordinals match the contract pattern: ``^(\\d+\\.)*\\d+$``."""
        pattern = re.compile(r"^(\d+\.)*\d+$")
        mapper = OrdinalPathMapper(groomed_body_doc)
        entries = mapper.build_map()

        for entry in entries:
            assert pattern.match(entry.ordinal), (
                f"Ordinal {entry.ordinal!r} does not match '^(\\d+\\.)*\\d+$'."
            )

    def test_groomed_entry_concerns_gets_child_ordinal(
        self, groomed_body_doc: list[NormalizedSection]
    ) -> None:
        """Entry '### Concerns' within section [4] receives ordinal '4.0'.

        Section [4] 'Groomed (2026-06-01)' has 2 entries; the first entry starts
        with '### Concerns'.  OrdinalPathMapper extracts 'Concerns' from the
        sub-heading and assigns ordinal '4.0' (section_index.entry_index).
        """
        mapper = OrdinalPathMapper(groomed_body_doc)
        entries = mapper.build_map()

        concerns = next((e for e in entries if e.title == "Concerns"), None)
        assert concerns is not None, (
            "Expected OrdinalEntry with title='Concerns' in build_map(); not found. "
            f"All entry titles: {[e.title for e in entries]}"
        )
        assert concerns.ordinal == "4.0", (
            f"'Concerns' (first entry of section [4]) must have ordinal '4.0'; "
            f"got {concerns.ordinal!r}."
        )

    def test_second_entry_in_section_gets_sequential_ordinal(
        self, groomed_body_doc: list[NormalizedSection]
    ) -> None:
        """Section [4] second entry (RT-ICA) receives ordinal '4.1'."""
        mapper = OrdinalPathMapper(groomed_body_doc)
        entries = mapper.build_map()

        entry_4_1 = next((e for e in entries if e.ordinal == "4.1"), None)
        assert entry_4_1 is not None, (
            "Expected OrdinalEntry with ordinal='4.1' for section [4] entry 1; not found."
        )
        assert "RT-ICA" in entry_4_1.title, (
            f"Second entry of section [4] must have 'RT-ICA' in title; "
            f"got {entry_4_1.title!r}."
        )


# ---------------------------------------------------------------------------
# TC-O2: Level-2 emission gate
# ---------------------------------------------------------------------------


class TestLevelTwoEmissionGate:
    """Level-2 lines emitted iff ``entry_count > 1`` OR ``est_tokens > TOKEN_BUDGET``."""

    def test_single_entry_under_budget_emits_level1_only(
        self, single_entry_doc: list[NormalizedSection]
    ) -> None:
        """Single-entry sections with short content emit level-1 ONLY — no level-2."""
        mapper = OrdinalPathMapper(single_entry_doc)
        entries = mapper.build_map()

        level2 = [e for e in entries if "." in e.ordinal]
        assert level2 == [], (
            f"Single-entry under-budget sections must emit no level-2 lines; "
            f"got {[e.ordinal for e in level2]}."
        )

    def test_multiple_entries_emit_level2_regardless_of_size(
        self, groomed_body_doc: list[NormalizedSection]
    ) -> None:
        """Section with entry_count > 1 emits level-2 lines for all entries."""
        mapper = OrdinalPathMapper(groomed_body_doc)
        entries = mapper.build_map()

        ordinals = {e.ordinal for e in entries}
        # Section [4] has 2 entries → both "4.0" and "4.1" must appear
        assert "4.0" in ordinals, (
            "Section [4] has 2 entries; ordinal '4.0' must be emitted (entry_count > 1 gate)."
        )
        assert "4.1" in ordinals, (
            "Section [4] has 2 entries; ordinal '4.1' must be emitted (entry_count > 1 gate)."
        )

    @_skip_without_real_enc
    def test_single_entry_over_budget_emits_level2(self) -> None:
        """Single-entry section with content > TOKEN_BUDGET must emit level-2.

        Constructs content whose tiktoken cl100k_base count exceeds TOKEN_BUDGET
        by at least 1 token, then asserts the level-2 line appears.
        """
        assert ENCODING is not None, "ENCODING required — @_skip_without_real_enc should have skipped."

        # Build content exceeding TOKEN_BUDGET.  Use non-repetitive text so real
        # BPE compression doesn't collapse the token count unexpectedly.
        target_tokens = TOKEN_BUDGET + 10
        sentence = "The agent received an unexpected error for request identifier delta. "
        # ~15 tokens per sentence; multiply generously then trim
        content = sentence * (target_tokens // 10)
        raw_tokens = ENCODING.encode(content)
        if len(raw_tokens) > target_tokens:
            content = ENCODING.decode(raw_tokens[:target_tokens])
        elif len(raw_tokens) < TOKEN_BUDGET + 1:
            # Pad until just over budget
            while len(ENCODING.encode(content)) < TOKEN_BUDGET + 1:
                content += " extra token"

        actual_tokens = len(ENCODING.encode(content))
        assert actual_tokens > TOKEN_BUDGET, (
            f"Test setup error: content is {actual_tokens}t which is ≤ TOKEN_BUDGET={TOKEN_BUDGET}. "
            "Increase sentence multiplication factor."
        )

        sections = _make_sections(
            ("SmallSection", ["Short."]),
            ("OverBudget", [content]),  # single entry, but over TOKEN_BUDGET
        )
        mapper = OrdinalPathMapper(sections)
        entries = mapper.build_map()

        ordinals = {e.ordinal for e in entries}
        assert "1.0" in ordinals, (
            f"'OverBudget' section (1 entry, {actual_tokens}t > TOKEN_BUDGET={TOKEN_BUDGET}) "
            f"must emit level-2 ordinal '1.0'. Got ordinals: {sorted(ordinals)}."
        )

    def test_empty_section_emits_no_level2(
        self, empty_section_doc: list[NormalizedSection]
    ) -> None:
        """Section with 0 entries emits only a level-1 ordinal; no level-2 children."""
        mapper = OrdinalPathMapper(empty_section_doc)
        entries = mapper.build_map()

        children_of_empty = [e.ordinal for e in entries if e.ordinal.startswith("1.")]
        assert children_of_empty == [], (
            f"Empty section [1] must emit no level-2 ordinals; got {children_of_empty}."
        )


# ---------------------------------------------------------------------------
# TC-O3: Map line formatting
# ---------------------------------------------------------------------------


class TestFormatMapLine:
    """``format_map_line()`` produces the contract-exact string representation."""

    @staticmethod
    def _entry(
        *,
        ordinal: str = "0",
        title: str = "Title",
        est_tokens: int = 42,
        first_line_preview: str = "Preview text.",
    ) -> OrdinalEntry:
        return OrdinalEntry(
            ordinal=ordinal,
            title=title,
            est_tokens=est_tokens,
            first_line_preview=first_line_preview,
        )

    def test_format_map_line_contains_required_fields(self) -> None:
        """Line contains ordinal, title, token count, and preview."""
        entry = self._entry(ordinal="3", title="Context", est_tokens=85, first_line_preview="Context here")
        mapper = OrdinalPathMapper([])
        line = mapper.format_map_line(entry)

        assert "3" in line, f"Ordinal '3' missing from map line: {line!r}"
        assert "Context" in line, f"Title 'Context' missing from map line: {line!r}"
        assert "85t" in line, f"Token count '85t' missing from map line: {line!r}"
        assert "Context here" in line, f"Preview 'Context here' missing from map line: {line!r}"

    def test_format_map_line_no_preview_when_empty(self) -> None:
        """When ``first_line_preview`` is empty, no preview clause is appended."""
        entry = self._entry(first_line_preview="")
        mapper = OrdinalPathMapper([])
        line = mapper.format_map_line(entry)

        # The preview clause uses '—' as separator; absent when preview is empty
        assert "—" not in line, (
            f"Empty first_line_preview must not produce '—' in map line; got {line!r}."
        )

    def test_format_map_line_title_capped_at_50_chars(self) -> None:
        """Titles longer than 50 chars are truncated to 50 chars ending with '…'."""
        long_title = "A" * 80  # 80 chars — well over the 50-char cap
        entry = self._entry(title=long_title, first_line_preview="")
        mapper = OrdinalPathMapper([])
        line = mapper.format_map_line(entry)

        # The 80-char title must NOT appear verbatim
        assert long_title not in line, (
            f"80-char title must be truncated in the map line; "
            f"full title found in: {line!r}"
        )
        # Truncation must use the single-character ellipsis '…' (U+2026)
        assert "…" in line, (
            f"Truncated title must end with '…'; got {line!r}"
        )

    def test_format_map_line_preview_capped_at_60_chars(self) -> None:
        """Previews longer than 60 chars are truncated."""
        long_preview = "B" * 100  # 100 chars — well over the 60-char cap
        entry = self._entry(first_line_preview=long_preview)
        mapper = OrdinalPathMapper([])
        line = mapper.format_map_line(entry)

        assert long_preview not in line, (
            f"100-char preview must be truncated; full preview found in: {line!r}"
        )

    def test_format_map_line_empty_section_shows_zero_tokens(self) -> None:
        """Entry with ``est_tokens=0`` produces ``(0t)`` in the map line."""
        entry = self._entry(est_tokens=0, first_line_preview="")
        mapper = OrdinalPathMapper([])
        line = mapper.format_map_line(entry)

        assert "(0t)" in line, (
            f"Zero-token entry must show '(0t)' in map line; got {line!r}"
        )


# ---------------------------------------------------------------------------
# TC-O4: resolve() — hit and miss
# ---------------------------------------------------------------------------


class TestResolveOrdinal:
    """``resolve()`` returns ``ResolvedUnit`` on hit and raises on miss."""

    def test_resolve_entry_ordinal_returns_content(
        self, groomed_body_doc: list[NormalizedSection]
    ) -> None:
        """``resolve('4.0')`` returns the first entry of section [4] (Concerns)."""
        mapper = OrdinalPathMapper(groomed_body_doc)
        _ = mapper.build_map()
        resolved = mapper.resolve("4.0")

        assert isinstance(resolved, ResolvedUnit), (
            f"resolve() must return ResolvedUnit; got {type(resolved).__name__}."
        )
        assert "Pre-existing concerns" in resolved.content, (
            f"resolve('4.0') content must include 'Pre-existing concerns'; "
            f"got {resolved.content[:120]!r}."
        )
        assert resolved.total_tokens > 0, (
            "resolve('4.0') must have total_tokens > 0 for non-empty content."
        )

    def test_resolve_section_ordinal_returns_resolved_unit(
        self, groomed_body_doc: list[NormalizedSection]
    ) -> None:
        """``resolve('4')`` (level-1) returns ``ResolvedUnit`` for the full section."""
        mapper = OrdinalPathMapper(groomed_body_doc)
        _ = mapper.build_map()
        resolved = mapper.resolve("4")

        assert isinstance(resolved, ResolvedUnit), (
            f"resolve('4') must return ResolvedUnit; got {type(resolved).__name__}."
        )
        assert resolved.ordinal == "4", (
            f"ResolvedUnit.ordinal must echo '4'; got {resolved.ordinal!r}."
        )
        assert resolved.title == "Groomed (2026-06-01)", (
            f"Level-1 section [4] title must be 'Groomed (2026-06-01)'; "
            f"got {resolved.title!r}."
        )

    def test_resolve_empty_section_has_zero_or_empty_content(
        self, empty_section_doc: list[NormalizedSection]
    ) -> None:
        """Resolving a section with 0 entries returns empty content or total_tokens=0."""
        mapper = OrdinalPathMapper(empty_section_doc)
        _ = mapper.build_map()
        resolved = mapper.resolve("1")  # "Empty" section at index 1

        assert resolved.content == "" or resolved.total_tokens == 0, (
            f"Empty section must produce content='' or total_tokens=0; "
            f"got content={resolved.content!r}, total_tokens={resolved.total_tokens}."
        )

    def test_resolve_miss_raises_ordinal_not_found_error(
        self, groomed_body_doc: list[NormalizedSection]
    ) -> None:
        """``resolve()`` raises ``OrdinalNotFoundError`` for an unknown ordinal."""
        mapper = OrdinalPathMapper(groomed_body_doc)
        _ = mapper.build_map()

        with pytest.raises(OrdinalNotFoundError):
            mapper.resolve("99.99")

    def test_ordinal_not_found_error_message_contains_requested(
        self, groomed_body_doc: list[NormalizedSection]
    ) -> None:
        """``OrdinalNotFoundError`` message includes the requested ordinal."""
        mapper = OrdinalPathMapper(groomed_body_doc)
        _ = mapper.build_map()

        with pytest.raises(OrdinalNotFoundError) as exc_info:
            mapper.resolve("99.99")

        assert "99.99" in str(exc_info.value), (
            "OrdinalNotFoundError message must include the requested ordinal '99.99'."
        )

    def test_ordinal_not_found_error_carries_requested_attribute(
        self, groomed_body_doc: list[NormalizedSection]
    ) -> None:
        """``OrdinalNotFoundError.requested`` is the exact ordinal string passed."""
        mapper = OrdinalPathMapper(groomed_body_doc)
        _ = mapper.build_map()

        with pytest.raises(OrdinalNotFoundError) as exc_info:
            mapper.resolve("99.99")

        assert exc_info.value.requested == "99.99", (
            f"OrdinalNotFoundError.requested must be '99.99'; "
            f"got {exc_info.value.requested!r}."
        )

    def test_ordinal_not_found_error_carries_valid_ordinals(
        self, groomed_body_doc: list[NormalizedSection]
    ) -> None:
        """``OrdinalNotFoundError.valid_ordinals`` includes '4.0' (known level-2)."""
        mapper = OrdinalPathMapper(groomed_body_doc)
        _ = mapper.build_map()

        with pytest.raises(OrdinalNotFoundError) as exc_info:
            mapper.resolve("99.99")

        # "4.0" is a known ordinal from the groomed_body_doc fixture
        assert "4.0" in exc_info.value.valid_ordinals, (
            f"'4.0' must be in OrdinalNotFoundError.valid_ordinals; "
            f"got {exc_info.value.valid_ordinals!r}."
        )

    def test_valid_ordinals_method_returns_all_map_ordinals(
        self, groomed_body_doc: list[NormalizedSection]
    ) -> None:
        """``valid_ordinals()`` returns the complete set of ordinals from ``build_map()``."""
        mapper = OrdinalPathMapper(groomed_body_doc)
        entries = mapper.build_map()
        expected = {e.ordinal for e in entries}

        actual = set(mapper.valid_ordinals())
        assert actual == expected, (
            f"valid_ordinals() must equal the set of ordinals from build_map().\n"
            f"Expected: {sorted(expected)}\n"
            f"Got:      {sorted(actual)}"
        )


# ---------------------------------------------------------------------------
# TC-O5: est_tokens exact cl100k_base counting
# ---------------------------------------------------------------------------


class TestEstTokensCl100kBase:
    """``est_tokens`` must equal the exact tiktoken cl100k_base count — not chars//4."""

    @_skip_without_real_enc
    def test_est_tokens_equals_exact_tiktoken_count(
        self, groomed_body_doc: list[NormalizedSection]
    ) -> None:
        """``est_tokens`` for every ``OrdinalEntry`` matches its tiktoken count.

        A ``chars//4`` approximation would fail this because real cl100k_base BPE
        compression is content-dependent and deviates from ``chars//4`` for most text.

        Verification: compare ``entry.est_tokens`` against
        ``len(ENCODING.encode(resolved.content))`` for all entries (both level-1
        and level-2).
        """
        assert ENCODING is not None
        mapper = OrdinalPathMapper(groomed_body_doc)
        entries = mapper.build_map()

        for entry in entries:
            resolved = mapper.resolve(entry.ordinal)
            expected_tokens = len(ENCODING.encode(resolved.content))
            assert entry.est_tokens == expected_tokens, (
                f"Ordinal {entry.ordinal!r}: est_tokens={entry.est_tokens} "
                f"but tiktoken count={expected_tokens}. "
                f"chars//4 approximation would give {len(resolved.content) // 4}."
            )

    def test_est_tokens_is_zero_for_empty_section(
        self, empty_section_doc: list[NormalizedSection]
    ) -> None:
        """Empty section (0 entries) produces ``est_tokens=0`` in the map."""
        mapper = OrdinalPathMapper(empty_section_doc)
        entries = mapper.build_map()

        empty_entry = next(
            (e for e in entries if e.ordinal == "1"),  # "Empty" at index 1
            None,
        )
        assert empty_entry is not None, "Empty section at index 1 must have level-1 entry '1'."
        assert empty_entry.est_tokens == 0, (
            f"Empty section ordinal '1' must have est_tokens=0; "
            f"got {empty_entry.est_tokens}."
        )

    def test_est_tokens_non_negative_for_all_entries(
        self, groomed_body_doc: list[NormalizedSection]
    ) -> None:
        """``est_tokens`` must be ≥ 0 for every OrdinalEntry."""
        mapper = OrdinalPathMapper(groomed_body_doc)
        entries = mapper.build_map()

        negative = [e for e in entries if e.est_tokens < 0]
        assert negative == [], (
            f"All est_tokens must be non-negative; "
            f"found: {[(e.ordinal, e.est_tokens) for e in negative]}."
        )


# ---------------------------------------------------------------------------
# TC-O6: RT-ICA ordinal derived dynamically from #2515 (never hardcoded)
# ---------------------------------------------------------------------------


_FIXTURE_2515_EXISTS = (_FIXTURES_DIR / "issue-2515-full.json").exists()
_skip_without_2515 = pytest.mark.skipif(
    not _FIXTURE_2515_EXISTS,
    reason="issue-2515-full.json not yet regenerated (T01 prerequisite).",
)


class TestIssue2515RTICADynamic:
    """RT-ICA ordinal in #2515 is derived from the map — never hardcoded.

    CoVe checks (architect spec §8.3):
    1. The test builds the map and searches by title for 'RT-ICA' before resolving.
    2. The test would still pass if RT-ICA's section index changed (position-independent).
    3. Any assertion that hardcodes a position literal for RT-ICA would violate the
       task constraint; none is present in this file for the #2515 RT-ICA test.

    NOTE: any literal '4.0' in this file refers to the SYNTHETIC groomed_body_doc
    fixture (section [4], entry 0) — not to #2515's RT-ICA position.
    """

    @_skip_without_2515
    @_skip_without_real_enc
    def test_rt_ica_ordinal_derived_dynamically(
        self, normalized_2515: list[NormalizedSection]
    ) -> None:
        """Build map, find RT-ICA entry by title, resolve, assert meaningful token count.

        Derivation strategy:
        1. ``OrdinalPathMapper(normalized_2515).build_map()`` produces the full map.
        2. Search for any OrdinalEntry where ``'RT-ICA' in entry.title``.
           RT-ICA in the #2515 fixture (T01) has 1 entry at ~560 tokens — below
           TOKEN_BUDGET — so only a level-1 ordinal is emitted (no level-2).
        3. The found ordinal is passed to ``resolve()``.
        4. Assert ``resolved.total_tokens > 400`` (ground-truth: ~560 tokens in T01).
        5. Assert ``'RT-ICA' in resolved.title`` (confirms the right section).

        This test MUST NOT hardcode any ordinal literal for RT-ICA in the context
        of the #2515 fixture.  The ordinal is whatever ``build_map()`` assigns.
        """
        assert ENCODING is not None
        mapper = OrdinalPathMapper(normalized_2515)
        entries = mapper.build_map()

        # Derive ordinal dynamically — search by title in the built map (any level)
        rt_ica_entries = [e for e in entries if "RT-ICA" in e.title]
        assert rt_ica_entries, (
            "No OrdinalEntry with 'RT-ICA' in title found in #2515 map. "
            f"All entries (ordinal, title): {[(e.ordinal, e.title) for e in entries]}"
        )

        rt_ica_ordinal = rt_ica_entries[0].ordinal
        rt_ica_title = rt_ica_entries[0].title

        resolved = mapper.resolve(rt_ica_ordinal)

        assert "RT-ICA" in resolved.title, (
            f"resolve({rt_ica_ordinal!r}).title must contain 'RT-ICA'; "
            f"got {resolved.title!r}."
        )
        assert resolved.total_tokens > 400, (
            f"RT-ICA entry (ordinal={rt_ica_ordinal!r}) must have meaningful content "
            f"(> 400 tokens); got {resolved.total_tokens}. "
            f"Entry title: {rt_ica_title!r}."
        )

    @_skip_without_2515
    @_skip_without_real_enc
    def test_rt_ica_level2_ordinal_is_in_valid_ordinals(
        self, normalized_2515: list[NormalizedSection]
    ) -> None:
        """RT-ICA (single-entry, under TOKEN_BUDGET) emits only level-1; level-1 is in valid_ordinals().

        Ground truth from T10 phase gate: RT-ICA in #2515 fixture is ~560 tokens — below
        TOKEN_BUDGET.  With entry_count=1 AND est_tokens < TOKEN_BUDGET, the level-2 emission
        gate does NOT fire.  Level-2 must therefore be absent; the level-1 ordinal must be
        present in ``valid_ordinals()``.
        """
        mapper = OrdinalPathMapper(normalized_2515)
        entries = mapper.build_map()

        # Level-2 must NOT be emitted for a single-entry under-budget section
        rt_ica_level2 = [e for e in entries if "RT-ICA" in e.title and "." in e.ordinal]
        assert rt_ica_level2 == [], (
            f"RT-ICA section (1 entry, ~560 tokens) is under TOKEN_BUDGET={TOKEN_BUDGET}; "
            f"level-2 must NOT be emitted. Got: {[e.ordinal for e in rt_ica_level2]}."
        )

        # Level-1 ordinal is derived dynamically and must appear in valid_ordinals()
        rt_ica_level1 = [e for e in entries if "RT-ICA" in e.title and "." not in e.ordinal]
        assert rt_ica_level1, (
            "Precondition: RT-ICA level-1 entry must be in map. "
            f"All entries: {[(e.ordinal, e.title) for e in entries]}"
        )
        rt_ica_ordinal = rt_ica_level1[0].ordinal
        assert rt_ica_ordinal in mapper.valid_ordinals(), (
            f"Derived RT-ICA level-1 ordinal {rt_ica_ordinal!r} must appear in valid_ordinals()."
        )


# ---------------------------------------------------------------------------
# AC-1: Map of #2515 stays under 2 000 tokens (architect spec §5.6)
# ---------------------------------------------------------------------------


class TestIssue2515MapBudget:
    """AC-1: map_text for the 53-section #2515 must remain under 2 000 tokens."""

    @_skip_without_2515
    @_skip_without_real_enc
    def test_map_2515_under_2000_tokens(
        self, normalized_2515: list[NormalizedSection]
    ) -> None:
        """Full map for 53-section #2515 must stay under 2 000 cl100k_base tokens.

        Verifies the level-2 emission gate keeps the map compact.  Worst-case bound
        (architect spec SS5.6): 53 sections x ~40t + small number of over-budget entry
        lines x ~40t < 2000t.
        """
        assert ENCODING is not None
        mapper = OrdinalPathMapper(normalized_2515)
        entries = mapper.build_map()
        map_text = "\n".join(mapper.format_map_line(e) for e in entries)
        actual_tokens = len(ENCODING.encode(map_text))

        assert actual_tokens < 2000, (
            f"Map of #2515 must be < 2 000 tokens; got {actual_tokens}. "
            f"Number of map lines: {len(entries)}. "
            f"Check the level-2 emission gate — too many level-2 lines push over budget."
        )
