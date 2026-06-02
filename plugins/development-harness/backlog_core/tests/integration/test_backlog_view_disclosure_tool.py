"""Integration tests: backlog_view MCP tool — 4 new disclosure params routing.

TDD state (T23 — test author, separate from T24 implementor):
  Intentionally FAILING at collection until T24 wires the 4 optional parameters
  (map, navigate, head, skip_tokens) to backlog_view() in server.py and routes
  them through DisclosureRequestParser + BacklogViewDisclosureHandler.

  TC-T4 (PASSTHROUGH) is GREEN against current code — it is the harness canary.
  If TC-T4 fails, the harness itself is broken; investigate before running T24.

Architecture reference:
  Architect spec §4.6 — backlog_view tool parameter changes
  Architect spec §9.2 — async boundary (pipeline inside asyncio.to_thread)
  ADR-5 — un-gated operations.view_item() call path
  DN-2 — RT-ICA is ~560 tokens; head=100 used for truncation (not 4000)

Test cases:
  TC-T1: map=True on #2515 → map_text under 2000 tokens with ordinals (AC-1).
  TC-T2: navigate=<RT-ICA ordinal> + head=100 → truncated=True, skip_tokens hint.
  TC-T3: navigate="99.99" (miss) → error response with valid_ordinals listed.
  TC-T4: Zero params → PASSTHROUGH → exact legacy key set unchanged.
  TC-T5: head without navigate → param error (head requires navigate).
  TC-T6: map=True on recursive-nav fixture → level-3 ordinals in map_text (AC#2).
  TC-T7: navigate=N.M.0 → sub-heading scope isolation; parent has_children=True (AC#3).
  TC-T8: navigate=N.M.code.0 → fence body returned, no ``` markers, no error (AC#4).
  TC-T9: navigate=N.M.code.99 → same error shape as numeric miss TC-T3 (AC#5).

Spy contract:
  All tests that access item content patch backlog_core.operations.view_item
  (module attribute).  T24 MUST call operations.view_item(selector) via the
  module reference (not a direct import alias) or this spy will not intercept.

RT-ICA ordinal:
  Derived dynamically via _find_rt_ica_ordinal() — never hardcoded.
  Ground truth (DN-2): RT-ICA in the #2515 fixture is ~560 tokens, single entry,
  below TOKEN_BUDGET=4000.  Level-2 emission gate does NOT fire → level-1 ordinal.

DN-2 correction:
  Task spec originally stated head=4000 / total_tokens>10000.
  Actual fixture: RT-ICA is ~560 tokens.  Correction: head=100 triggers truncation
  (100 < 560), total_tokens > 400, next_call contains 'skip_tokens=100' (AC-5).

Expected response key contracts (for T24 implementor):
  MAP   : map_text, total_sections, total_est_tokens, over_budget, selector
  EXTRACT: ordinal, title, content, total_tokens, returned_tokens, truncated, next_call
  NAVIGATE (no head, leaf): ordinal, title, content, total_tokens, truncated (False),
    child_map=None, has_children=False
  NAVIGATE (no head, parent w/ sub-headings): ordinal, title, content='', total_tokens,
    truncated=False, child_map=<str>, has_children=True  (ADR-7)
  NAVIGATE miss: error, requested_ordinal, valid_ordinals
  PASSTHROUGH (summary=True, observed 2026-06-01):
    _full_chars, _hint, _summary, issue_number, labels, plan_path,
    section_filter_miss, sections_index, status, title
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from fastmcp.client import Client

from backlog_core.content_normalizer import ItemContentNormalizer, NormalizedSection
from backlog_core.models import ItemNotFoundError
from backlog_core.operations import ViewItemResult
from backlog_core.ordinal_mapper import OrdinalPathMapper
from backlog_core.server import mcp

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Skip guards
# ---------------------------------------------------------------------------

_FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"
_FIXTURE_2515_EXISTS = (_FIXTURES_DIR / "issue-2515-full.json").exists()

_skip_without_2515 = pytest.mark.skipif(
    not _FIXTURE_2515_EXISTS, reason="issue-2515-full.json not yet regenerated (T01 prerequisite)."
)


def _real_cl100k_available() -> bool:
    """Return True when cl100k_base encoding is warmed in the tiktoken cache."""
    import tiktoken.registry

    return "cl100k_base" in tiktoken.registry.ENCODINGS


_skip_without_real_enc = pytest.mark.skipif(
    not _real_cl100k_available(), reason="Real cl100k_base encoding unavailable (offline/empty cache)."
)

# ---------------------------------------------------------------------------
# PASSTHROUGH key contract (observed 2026-06-01 against current server.py).
# Pin as frozenset so T24 cannot accidentally add or remove keys from the
# zero-param code path (backward-compat AC).
# ---------------------------------------------------------------------------

_PASSTHROUGH_LEGACY_KEYS: frozenset[str] = frozenset({
    "_full_chars",
    "_hint",
    "_summary",
    "issue_number",
    "labels",
    "plan_path",
    "section_filter_miss",
    "sections_index",
    "status",
    "title",
})
"""Exact key set returned by backlog_view(selector='#2515', summary=True) today.

Captured by running the tool against the mocked fixture (summary=True default).
If this assertion ever fails post-T24, the PASSTHROUGH contract is broken.
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_fixture(name: str) -> dict[str, object]:
    """Load a JSON fixture from the tests/fixtures directory."""
    return json.loads((_FIXTURES_DIR / name).read_text(encoding="utf-8"))  # type: ignore[return-value]


def _find_rt_ica_ordinal(normalized: list[NormalizedSection]) -> str:
    """Derive the RT-ICA ordinal dynamically from the normalised section list.

    Builds the ordinal map via OrdinalPathMapper and returns the ordinal of the
    first OrdinalEntry with 'RT-ICA' in its title.  The ordinal is NEVER
    hardcoded — this function is the single source of truth for it.

    Ground truth (DN-2): RT-ICA in #2515 is ~560 tokens, single entry, below
    TOKEN_BUDGET=4000.  Level-2 emission gate does NOT fire → level-1 ordinal.

    Args:
        normalized: Ordered NormalizedSection list from ItemContentNormalizer.

    Returns:
        Ordinal string for the RT-ICA section (e.g. ``"4"``).

    Raises:
        ValueError: When no entry with 'RT-ICA' in title is found — fixture
            mismatch requiring investigation.
    """
    mapper = OrdinalPathMapper(normalized)
    entries = mapper.build_map()
    rt_ica_entries = [e for e in entries if "RT-ICA" in e.title]
    if not rt_ica_entries:
        all_titles = [(e.ordinal, e.title) for e in entries]
        raise ValueError(f"No OrdinalEntry with 'RT-ICA' in title found. All (ordinal, title) pairs: {all_titles}")
    return rt_ica_entries[0].ordinal


def _extract_response_dict(result: object) -> dict[str, object]:
    """Extract the response dict from a FastMCP call_tool result.

    FastMCP 3.x serialises dict-returning tools as JSON TextContent.
    Tries ``result.data`` first (FastMCP structured-return path), then falls
    back to parsing ``result.content[0].text`` (JSON text content path).

    Args:
        result: ToolResult object returned by ``client.call_tool()``.

    Returns:
        The parsed response dict.

    Raises:
        AssertionError: When neither path yields a dict — indicates a harness
            or FastMCP version mismatch.
    """
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return data
    content = getattr(result, "content", [])
    if content:
        text = getattr(content[0], "text", None)
        if isinstance(text, str):
            return json.loads(text)  # type: ignore[no-any-return]
    raise AssertionError(
        f"Cannot extract dict from call_tool result. "
        f"type={type(result).__name__!r}, "
        f"data={data!r}, "
        f"content={content!r}. "
        "Check FastMCP version or _extract_response_dict helper."
    )


# ---------------------------------------------------------------------------
# Module-level fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def view_result_2515() -> ViewItemResult:
    """ViewItemResult for #2515, used as operations.view_item spy return value.

    Constructed via ``ViewItemResult.model_validate()`` from the regenerated
    fixture — same construction used in test_disclosure_handler.py.
    """
    data = _load_fixture("issue-2515-full.json")
    return ViewItemResult.model_validate(data)


@pytest.fixture(scope="module")
def normalized_2515() -> list[NormalizedSection]:
    """Normalised #2515 sections — used to derive the RT-ICA ordinal dynamically."""
    data = _load_fixture("issue-2515-full.json")
    return ItemContentNormalizer().normalize(ViewItemResult.model_validate(data))


# ---------------------------------------------------------------------------
# TC-T1: MAP mode — map=True on #2515
# ---------------------------------------------------------------------------


class TestMapMode:
    """TC-T1: map=True on #2515 returns map_text under 2000 tokens with ordinals.

    Validates AC-1 (map under 2000 tokens) at the MCP tool boundary using the
    FastMCP in-memory transport (``Client(mcp)``).

    Spy contract: patches ``backlog_core.operations.view_item`` (module attr).
    RED until T24 adds ``map: bool = False`` parameter to backlog_view().
    """

    @_skip_without_2515
    @_skip_without_real_enc
    async def test_map_response_has_map_text_key(self, view_result_2515: ViewItemResult, mocker: MockerFixture) -> None:
        """map=True response dict contains 'map_text' key (MAP mode routing)."""
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#2515", "map": True})

        data = _extract_response_dict(result)
        assert "map_text" in data, f"map=True must produce 'map_text' key. Got keys: {sorted(data.keys())}"

    @_skip_without_2515
    @_skip_without_real_enc
    async def test_map_text_under_2000_tokens(self, view_result_2515: ViewItemResult, mocker: MockerFixture) -> None:
        """map_text from #2515 must be < 2000 tokens (AC-1 budget guarantee)."""
        from progressive_markdown.list_navigator import ENCODING

        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#2515", "map": True})

        data = _extract_response_dict(result)
        assert "map_text" in data, f"Precondition: map_text missing from keys: {sorted(data.keys())}"
        map_text = data["map_text"]
        assert isinstance(map_text, str), f"map_text must be str, got {type(map_text)}"
        token_count = len(ENCODING.encode(map_text))
        assert token_count < 2000, (
            f"map_text must be < 2000 tokens (AC-1). "
            f"Got {token_count} tokens for #2515 with {len(map_text.splitlines())} lines."
        )

    @_skip_without_2515
    @_skip_without_real_enc
    async def test_map_text_contains_ordinal_lines(
        self, view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """map_text contains ordinal lines (lines starting with a digit)."""
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#2515", "map": True})

        data = _extract_response_dict(result)
        assert "map_text" in data, f"Precondition: map_text missing from keys: {sorted(data.keys())}"
        map_text = data["map_text"]
        assert isinstance(map_text, str), f"map_text must be str, got {type(map_text)}"
        ordinal_lines = [line for line in map_text.splitlines() if line and line[0].isdigit()]
        assert ordinal_lines, (
            f"map_text must contain ordinal lines starting with a digit. "
            f"Got {len(map_text.splitlines())} total lines:\n{map_text[:200]}"
        )

    @_skip_without_2515
    @_skip_without_real_enc
    async def test_map_response_has_positive_total_sections(
        self, view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """map=True response has total_sections > 0 for an item with sections."""
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#2515", "map": True})

        data = _extract_response_dict(result)
        total_sections = data.get("total_sections", 0)
        assert isinstance(total_sections, int), f"total_sections must be int, got {type(total_sections)}"
        assert total_sections > 0, (
            f"total_sections must be > 0 for an item with sections. "
            f"Got total_sections={total_sections!r}. "
            f"Response keys: {sorted(data.keys())}"
        )


# ---------------------------------------------------------------------------
# TC-T2: EXTRACT mode — navigate + head=100 on RT-ICA ordinal
# ---------------------------------------------------------------------------


class TestExtractMode:
    """TC-T2: EXTRACT mode on RT-ICA (#2515, head=100) → truncated + skip_tokens hint.

    RT-ICA ordinal is derived dynamically via _find_rt_ica_ordinal() — never
    hardcoded.  The ordinal is first obtained from the MAP response to mirror
    the real agent workflow.

    DN-2 correction (from plan divergence notes):
      Task spec originally stated head=4000 / total_tokens > 10000.
      Actual fixture: RT-ICA is ~560 tokens (single entry, below TOKEN_BUDGET).
      Correction applied here:
        head=100  →  100 < 560  →  truncated=True
        total_tokens > 400  (not >10000)
        next_call contains 'skip_tokens=100'  (AC-5, not 'offset=')

    Spy contract: patches backlog_core.operations.view_item.
    RED until T24 adds navigate + head parameters to backlog_view().
    """

    @_skip_without_2515
    @_skip_without_real_enc
    async def test_extract_returns_truncated_true(
        self, normalized_2515: list[NormalizedSection], view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """navigate + head=100 on RT-ICA returns truncated=True (100 < ~560t)."""
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)
        rt_ica_ordinal = _find_rt_ica_ordinal(normalized_2515)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "backlog_view", {"selector": "#2515", "navigate": rt_ica_ordinal, "head": 100}
            )

        data = _extract_response_dict(result)
        assert data.get("truncated") is True, (
            f"truncated must be True when head=100 < RT-ICA total_tokens (~560). "
            f"Got truncated={data.get('truncated')!r}, "
            f"total_tokens={data.get('total_tokens')!r}, "
            f"rt_ica_ordinal={rt_ica_ordinal!r}. "
            f"Response keys: {sorted(data.keys())}"
        )

    @_skip_without_2515
    @_skip_without_real_enc
    async def test_extract_returned_tokens_within_head_bound(
        self, normalized_2515: list[NormalizedSection], view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """returned_tokens <= 100 — window does not exceed the requested bound."""
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)
        rt_ica_ordinal = _find_rt_ica_ordinal(normalized_2515)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "backlog_view", {"selector": "#2515", "navigate": rt_ica_ordinal, "head": 100}
            )

        data = _extract_response_dict(result)
        returned = data.get("returned_tokens", -1)
        assert isinstance(returned, int), (
            f"returned_tokens must be an int. Got {type(returned).__name__!r}: {returned!r}"
        )
        assert returned <= 100, (
            f"returned_tokens must be <= head (100). "
            f"Got returned_tokens={returned!r}. "
            f"Response keys: {sorted(data.keys())}"
        )

    @_skip_without_2515
    @_skip_without_real_enc
    async def test_extract_total_tokens_reflects_full_content(
        self, normalized_2515: list[NormalizedSection], view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """total_tokens > 400 — reflects full RT-ICA pre-truncation content (~560t).

        DN-2 correction: task spec stated total_tokens > 10000.
        Actual fixture: RT-ICA is ~560 tokens.  Corrected threshold: > 400.
        """
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)
        rt_ica_ordinal = _find_rt_ica_ordinal(normalized_2515)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "backlog_view", {"selector": "#2515", "navigate": rt_ica_ordinal, "head": 100}
            )

        data = _extract_response_dict(result)
        total = data.get("total_tokens", 0)
        assert isinstance(total, int), f"total_tokens must be an int. Got {type(total).__name__!r}: {total!r}"
        assert total > 400, (
            f"total_tokens must reflect full RT-ICA content (~560t). "
            f"Got total_tokens={total!r}. "
            "(DN-2: corrected from >10000 to >400 based on regenerated fixture.)"
        )

    @_skip_without_2515
    @_skip_without_real_enc
    async def test_extract_next_call_uses_skip_tokens_not_offset(
        self, normalized_2515: list[NormalizedSection], view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """next_call hint contains 'skip_tokens=100', NOT 'offset=' (AC-5)."""
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)
        rt_ica_ordinal = _find_rt_ica_ordinal(normalized_2515)

        async with Client(mcp) as client:
            result = await client.call_tool(
                "backlog_view", {"selector": "#2515", "navigate": rt_ica_ordinal, "head": 100}
            )

        data = _extract_response_dict(result)
        # Precondition: truncated must be True for next_call to be non-None
        assert data.get("truncated") is True, "Precondition: truncated must be True for next_call check."
        next_call_raw = data.get("next_call")
        assert next_call_raw is not None, "next_call must not be None when truncated=True."
        assert isinstance(next_call_raw, str), (
            f"next_call must be a str when truncated=True. Got: {type(next_call_raw)!r}"
        )
        assert next_call_raw != "", f"next_call must be non-empty when truncated=True. Got: {next_call_raw!r}"
        next_call: str = next_call_raw
        assert "skip_tokens=100" in next_call, f"next_call must contain 'skip_tokens=100' (AC-5). Got: {next_call!r}"
        assert "offset=" not in next_call, (
            f"next_call must NOT use 'offset=' (AC-5 — skip_tokens is the contract). Got: {next_call!r}"
        )


# ---------------------------------------------------------------------------
# TC-T3: navigate miss — navigate="99.99" returns error with valid_ordinals
# ---------------------------------------------------------------------------


class TestNavigateMiss:
    """TC-T3: navigate='99.99' (nonexistent ordinal) → error response.

    No silent-fallback to full content on ordinal miss.  The response must
    contain 'error' and 'valid_ordinals' so callers can recover without a
    second round-trip.

    Spy contract: patches backlog_core.operations.view_item.
    RED until T24 adds navigate parameter and maps OrdinalNotFoundError to error dict.
    """

    @_skip_without_2515
    @_skip_without_real_enc
    async def test_navigate_miss_has_error_key(self, view_result_2515: ViewItemResult, mocker: MockerFixture) -> None:
        """navigate='99.99' response contains 'error' key — no silent fallback."""
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#2515", "navigate": "99.99"})

        data = _extract_response_dict(result)
        assert "error" in data, (
            f"navigate miss must return 'error' key (no silent fallback). Got keys: {sorted(data.keys())}"
        )

    @_skip_without_2515
    @_skip_without_real_enc
    async def test_navigate_miss_includes_valid_ordinals(
        self, view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """navigate miss response includes non-empty 'valid_ordinals' list."""
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#2515", "navigate": "99.99"})

        data = _extract_response_dict(result)
        assert "valid_ordinals" in data, (
            f"navigate miss must include 'valid_ordinals' for recovery. Got keys: {sorted(data.keys())}"
        )
        valid = data.get("valid_ordinals")
        assert isinstance(valid, list), f"valid_ordinals must be a list. Got {type(valid).__name__!r}: {valid!r}"
        assert len(valid) > 0, f"valid_ordinals must be non-empty. Got: {valid!r}"

    @_skip_without_2515
    @_skip_without_real_enc
    async def test_navigate_miss_has_no_body_key(self, view_result_2515: ViewItemResult, mocker: MockerFixture) -> None:
        """navigate miss response has no 'body' key — error dict, not content."""
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#2515", "navigate": "99.99"})

        data = _extract_response_dict(result)
        assert "body" not in data, f"navigate miss must NOT return 'body'. Got keys: {sorted(data.keys())}"


# ---------------------------------------------------------------------------
# TC-T4: PASSTHROUGH — zero disclosure params → exact legacy key set
# ---------------------------------------------------------------------------


class TestPassthrough:
    """TC-T4: Zero disclosure params → PASSTHROUGH — exact legacy key set preserved.

    This test is GREEN against current code (before T24) — it is the harness
    canary.  If it fails, the harness itself is broken.

    Backward-compat assertion: the zero-param call must return the exact same
    key set as it did before T24 was implemented.  This pins the PASSTHROUGH
    contract so T24 cannot accidentally inject or remove keys from the existing
    code path.

    Key set observed 2026-06-01 with summary=True (default) against the #2515
    fixture: _PASSTHROUGH_LEGACY_KEYS (module constant above).

    Spy contract: patches backlog_core.operations.view_item.
    """

    @_skip_without_2515
    async def test_passthrough_exact_legacy_key_set(
        self, view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """Zero-param call returns exactly the same key set as the legacy tool.

        The exact key set is pinned in _PASSTHROUGH_LEGACY_KEYS.  Any deviation
        post-T24 means the PASSTHROUGH code path was inadvertently changed.
        """
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#2515"})

        data = _extract_response_dict(result)
        actual_keys = frozenset(data.keys())
        assert actual_keys == _PASSTHROUGH_LEGACY_KEYS, (
            f"PASSTHROUGH key set must match legacy exactly.\n"
            f"  Missing from response : {_PASSTHROUGH_LEGACY_KEYS - actual_keys}\n"
            f"  Extra in response     : {actual_keys - _PASSTHROUGH_LEGACY_KEYS}\n"
            f"  Expected : {sorted(_PASSTHROUGH_LEGACY_KEYS)}\n"
            f"  Actual   : {sorted(actual_keys)}"
        )

    @_skip_without_2515
    async def test_passthrough_has_no_disclosure_keys(
        self, view_result_2515: ViewItemResult, mocker: MockerFixture
    ) -> None:
        """Zero-param response must not contain any disclosure-only keys."""
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_2515)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#2515"})

        data = _extract_response_dict(result)
        # Keys that ONLY appear in disclosure mode responses:
        disclosure_only = {"map_text", "total_est_tokens", "over_budget", "truncated", "returned_tokens", "next_call"}
        found = disclosure_only.intersection(data.keys())
        assert not found, (
            f"PASSTHROUGH must not inject disclosure keys. Found: {found}. All keys: {sorted(data.keys())}"
        )


# ---------------------------------------------------------------------------
# TC-T5: param error — head without navigate
# ---------------------------------------------------------------------------


class TestParamError:
    """TC-T5: Invalid disclosure param combo → param error response dict.

    head without navigate: DisclosureParamError('head requires navigate')
    should be caught by T24 and surfaced as {'error': ..., ...}.

    No view_item spy needed — DisclosureRequestParser.parse() raises before
    any item content is fetched.

    RED until T24 adds head parameter and routes DisclosureParamError to dict.
    Note: before T24, FastMCP will reject 'head' as an unknown parameter —
    the error response key is still satisfied (FastMCP error dict has 'error').
    """

    async def test_head_without_navigate_returns_error_key(self) -> None:
        """head=100 without navigate → response has 'error' key."""
        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#2515", "head": 100})

        data = _extract_response_dict(result)
        assert "error" in data, f"head without navigate must return 'error' key. Got keys: {sorted(data.keys())}"

    async def test_head_without_navigate_error_mentions_params(self) -> None:
        """head without navigate error message mentions 'head' or 'navigate'."""
        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#2515", "head": 100})

        data = _extract_response_dict(result)
        assert "error" in data, "Precondition: response must have 'error' key."
        err_msg = str(data.get("error", "")).lower()
        assert "navigate" in err_msg or "head" in err_msg, (
            f"Error must mention 'navigate' or 'head'. Got: {data.get('error')!r}"
        )


# ---------------------------------------------------------------------------
# BacklogError catch in _execute_disclosure_or_passthrough (commit f8c04ec6)
# ---------------------------------------------------------------------------


class TestBacklogErrorInDisclosurePath:
    """Verify ItemNotFoundError (BacklogError subclass) returns structured dict.

    Regression guard for commit f8c04ec6:
      ``_execute_disclosure_or_passthrough`` must catch ``BacklogError`` and
      return ``{"error": str(exc)}`` rather than letting the exception propagate
      to FastMCP as an unhandled ``ToolError``.

    These tests run unconditionally — no fixture file or real encoding is
    required because ``operations.view_item`` is replaced by the mock before any
    item content or tokenization is attempted.

    Spy contract:
      Patches ``backlog_core.operations.view_item`` via ``side_effect`` so the
      mock *raises* ``ItemNotFoundError`` instead of returning a value.
    """

    async def test_item_not_found_returns_error_dict_not_tool_error(self, mocker: MockerFixture) -> None:
        """map=True + non-existent selector returns dict with 'error' key.

        Concretely tests that the ``except BacklogError`` branch in
        ``_execute_disclosure_or_passthrough`` is hit: if that catch were removed
        FastMCP would raise ``ToolError`` client-side and ``call_tool`` would
        propagate an exception rather than returning a result with an 'error' key.
        """
        mocker.patch("backlog_core.operations.view_item", side_effect=ItemNotFoundError("#99999"))

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#99999", "map": True})

        data = _extract_response_dict(result)
        assert "error" in data, (
            f"BacklogError must produce a structured dict with 'error' key, "
            f"not an unhandled ToolError. Got keys: {sorted(data.keys())}"
        )

    async def test_item_not_found_error_message_contains_selector(self, mocker: MockerFixture) -> None:
        """'error' value contains the selector from ItemNotFoundError.

        Confirms the catch path reaches ``str(exc)`` which formats as
        ``"No item found for: #99999"`` (per ``ItemNotFoundError.__init__``).
        This distinguishes the BacklogError path from a param-validation error
        that would return 'error' with different content before view_item is called.
        """
        mocker.patch("backlog_core.operations.view_item", side_effect=ItemNotFoundError("#99999"))

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#99999", "map": True})

        data = _extract_response_dict(result)
        assert "error" in data, "Precondition: response must have 'error' key."
        assert "#99999" in str(data["error"]), (
            f"'error' must contain the selector '#99999' from ItemNotFoundError. "
            f"ItemNotFoundError.__init__ formats as 'No item found for: #99999'. "
            f"Got: {data['error']!r}"
        )


# ---------------------------------------------------------------------------
# Synthetic fixture support (recursive-nav shape)
# ---------------------------------------------------------------------------
# issue-recursive-nav.json: a hand-crafted ViewItemResult fixture that contains
# exactly one section ("Analysis") with two entries:
#
#   Entry 0.0  — preamble + one ```python``` fence + two ### sub-headings.
#                Used to verify AC#2, AC#3, AC#4, AC#5 (issue #2529).
#   Entry 0.1  — plain content; present only to make entry_count=2 > 1 so the
#                level-2 emission gate fires and 0.0 / 0.1 ordinals are emitted.
#
# Provenance: hand-crafted to represent the canonical §5.1 shape described in
# the architecture spec (artifact_type="architect", item_id=2529, §5 Data
# Architecture).  It is not derived from a live GitHub issue.  See
# regenerate_fixtures.py for update instructions.
#
# Design decisions:
#   - sections_index (not body) provides document order — summary path used.
#   - Two entries in "Analysis" guarantee level-2 gate fires: entry_count=2 > 1.
#   - Entry 0 content contains one ```python``` fence and two ### sub-headings.
#   - All ordinals derived dynamically from _find_subheading_entry_ordinal().
# ---------------------------------------------------------------------------

_RECURSIVE_NAV_FIXTURE_EXISTS = (_FIXTURES_DIR / "issue-recursive-nav.json").exists()

_skip_without_recursive_nav = pytest.mark.skipif(
    not _RECURSIVE_NAV_FIXTURE_EXISTS, reason="issue-recursive-nav.json not present (hand-crafted fixture for T06)."
)


@pytest.fixture(scope="module")
def view_result_recursive_nav() -> ViewItemResult:
    """ViewItemResult for the synthetic recursive-nav fixture.

    Used as spy return value for TC-T6..TC-T9 (AC#2..AC#5 from issue #2529).
    """
    data = _load_fixture("issue-recursive-nav.json")
    return ViewItemResult.model_validate(data)


@pytest.fixture(scope="module")
def normalized_recursive_nav(view_result_recursive_nav: ViewItemResult) -> list[NormalizedSection]:
    """Normalised recursive-nav sections — used to derive ordinals dynamically."""
    return ItemContentNormalizer().normalize(view_result_recursive_nav)


def _find_subheading_entry_ordinal(normalized: list[NormalizedSection]) -> str:
    """Derive the ordinal of the first entry whose content contains ### sub-headings.

    Builds the ordinal map via OrdinalPathMapper, resolves each entry's content,
    and returns the ordinal of the first entry whose content contains "### ".
    The ordinal is NEVER hardcoded — this function is the drift-resistant source
    of truth for the sub-heading parent ordinal in the recursive-nav fixture.

    Args:
        normalized: Ordered NormalizedSection list from ItemContentNormalizer.

    Returns:
        Ordinal string for the sub-heading-bearing entry (e.g. ``"0.0"``).

    Raises:
        ValueError: When no entry with "### " in content is found — fixture
            mismatch requiring investigation.
    """
    mapper = OrdinalPathMapper(normalized)
    entries = mapper.build_map()
    for e in entries:
        unit = mapper.resolve(e.ordinal)
        if "### " in unit.content:
            return e.ordinal
    all_ordinals = [e.ordinal for e in entries]
    raise ValueError(f"No entry with '### ' (sub-heading marker) in content found. All ordinals: {all_ordinals}")


# ---------------------------------------------------------------------------
# TC-T6: level-3 ordinals appear in map_text (AC#2)
# ---------------------------------------------------------------------------


class TestLevel3MapOrdinals:
    """TC-T6: map=True on recursive-nav fixture lists level-3 ordinals.

    Assertion: when an entry (N.M) contains ### sub-headings, the map_text
    from backlog_view(map=True) must include at least one ordinal whose
    dot-path has three or more segments (N.M.K or deeper).

    RED until T10 extends OrdinalPathMapper to emit level-3 sub-heading
    ordinals from entries whose content parses to non-empty SectionNode trees.

    Spy contract: patches backlog_core.operations.view_item.
    """

    @_skip_without_recursive_nav
    @_skip_without_real_enc
    async def test_map_text_contains_level3_ordinal(
        self,
        view_result_recursive_nav: ViewItemResult,
        normalized_recursive_nav: list[NormalizedSection],
        mocker: MockerFixture,
    ) -> None:
        """map_text must contain at least one level-3 ordinal (N.M.K pattern).

        Verifies AC#2: when an entry has ### sub-headings, the progressive-disclosure
        map lists child ordinals at depth 3 or greater.
        Currently RED: OrdinalPathMapper does not emit sub-heading ordinals.
        """
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_recursive_nav)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#0", "map": True})

        data = _extract_response_dict(result)
        assert "map_text" in data, f"Precondition: map_text missing from response. Got keys: {sorted(data.keys())}"
        map_text = data["map_text"]
        assert isinstance(map_text, str), f"map_text must be str, got {type(map_text).__name__!r}"

        # A level-3 ordinal has at least two dots with all-digit segments.
        level3_ordinals: list[str] = []
        for line in map_text.splitlines():
            if not line:
                continue
            first_token = line.split()[0] if line.split() else ""
            segments = first_token.split(".")
            if len(segments) >= 3 and all(s.isdigit() for s in segments):
                level3_ordinals.append(first_token)

        current_ordinals = [line.split()[0] for line in map_text.splitlines() if line and line[0].isdigit()]
        assert len(level3_ordinals) > 0, (
            f"map_text must contain at least one level-3 ordinal (N.M.K) "
            f"when entry 0.0 has ### sub-headings. "
            f"Currently emitted ordinals: {current_ordinals!r}. "
            "RED: OrdinalPathMapper does not yet emit sub-heading ordinals."
        )


# ---------------------------------------------------------------------------
# TC-T7: navigate to sub-heading returns scoped content (AC#3)
# ---------------------------------------------------------------------------


class TestSubHeadingScopeIsolation:
    """TC-T7: navigate=N.M.K returns content scoped to that sub-heading only.

    Three sub-cases:
      A) navigate to parent entry (N.M) with sub-headings → has_children=True,
         content="" (ADR-7: prose accessed via children, not parent blob).
      B) navigate to parent entry (N.M) → content="" (not full entry blob).
      C) navigate to first child (N.M.0) → ONLY that sub-heading's body,
         not the sibling (N.M.1) content.

    RED until T10 wires navigate-on-parent logic and level-3 ordinal resolution.

    Spy contract: patches backlog_core.operations.view_item.
    """

    @_skip_without_recursive_nav
    @_skip_without_real_enc
    async def test_sub_heading_parent_has_children_true(
        self,
        view_result_recursive_nav: ViewItemResult,
        normalized_recursive_nav: list[NormalizedSection],
        mocker: MockerFixture,
    ) -> None:
        """navigate to an entry with ### sub-headings returns has_children=True.

        Verifies AC#3: parent node must advertise its sub-heading children.
        Currently RED: _handle_navigate returns NavigateResponse(has_children=False).
        """
        parent_ordinal = _find_subheading_entry_ordinal(normalized_recursive_nav)
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_recursive_nav)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#0", "navigate": parent_ordinal})

        data = _extract_response_dict(result)
        assert "error" not in data, (
            f"navigate to parent entry '{parent_ordinal}' must not return error. "
            f"Got keys: {sorted(data.keys())}, error: {data.get('error')!r}"
        )
        has_children = data.get("has_children")
        assert has_children is True, (
            f"navigate to entry with ### sub-headings must return has_children=True. "
            f"Got has_children={has_children!r}. "
            "RED: _handle_navigate() does not yet set has_children=True for parent nodes."
        )

    @_skip_without_recursive_nav
    @_skip_without_real_enc
    async def test_sub_heading_parent_content_is_empty_string(
        self,
        view_result_recursive_nav: ViewItemResult,
        normalized_recursive_nav: list[NormalizedSection],
        mocker: MockerFixture,
    ) -> None:
        """navigate to parent entry returns content='' when has sub-headings (ADR-7).

        Verifies AC#3: prose is accessed by navigating to individual sub-headings,
        not by reading the parent blob directly.
        Currently RED: _handle_navigate returns full entry content, not ''.
        """
        parent_ordinal = _find_subheading_entry_ordinal(normalized_recursive_nav)
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_recursive_nav)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#0", "navigate": parent_ordinal})

        data = _extract_response_dict(result)
        content = data.get("content", "MISSING")
        has_children = data.get("has_children", False)
        assert has_children is True, (
            f"Parent node with sub-headings must have has_children=True (ADR-7). "
            f"Got has_children={has_children!r}. "
            "RED: currently returns has_children=False."
        )
        assert content == "", (
            f"Parent node with sub-headings must have content='' (ADR-7). "
            f"Got content={content!r} "
            f"(len={len(content) if isinstance(content, str) else '?'}). "
            "RED: currently returns full entry blob."
        )

    @_skip_without_recursive_nav
    @_skip_without_real_enc
    async def test_sub_heading_first_child_returns_scoped_content(
        self,
        view_result_recursive_nav: ViewItemResult,
        normalized_recursive_nav: list[NormalizedSection],
        mocker: MockerFixture,
    ) -> None:
        """navigate=N.M.0 returns only the first sub-heading's body, not siblings.

        Verifies AC#3: sibling sub-heading content must not bleed into the response.
        The fixture Entry 0 contains two sub-headings:
          ### Sub-heading One  →  ordinal N.M.0
          ### Sub-heading Two  →  ordinal N.M.1
        Navigating to N.M.0 must include 'Sub-heading One' and exclude 'Sub-heading Two'.

        Currently RED: ordinal N.M.0 is not in the resolution map →
        OrdinalNotFoundError → response has 'error' key, not 'content'.
        """
        parent_ordinal = _find_subheading_entry_ordinal(normalized_recursive_nav)
        first_subheading_ordinal = f"{parent_ordinal}.0"
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_recursive_nav)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#0", "navigate": first_subheading_ordinal})

        data = _extract_response_dict(result)
        assert "error" not in data, (
            f"navigate to first sub-heading '{first_subheading_ordinal}' must not return error. Got: {data!r}"
        )
        content = data.get("content", "")
        assert isinstance(content, str), f"content must be str, got {type(content).__name__!r}"
        assert "Sub-heading One" in content, (
            f"First sub-heading (N.M.0) content must include 'Sub-heading One'. Got content={content!r}"
        )
        assert "Sub-heading Two" not in content, (
            f"First sub-heading (N.M.0) must NOT include sibling 'Sub-heading Two'. Got content={content!r}"
        )


# ---------------------------------------------------------------------------
# TC-T8: code-fence retrieval via N.M.code.0 (AC#4)
# ---------------------------------------------------------------------------


class TestCodeFenceRetrieval:
    """TC-T8: navigate=N.M.code.0 returns the first code-fence body.

    The returned content is the raw fence body without the surrounding ```
    markers.  The fixture Entry 0 contains:

        ```python
        def first_fence():
            return "fence body"
        ```

    So the response content must include 'first_fence' and must NOT include
    the '```' backtick delimiters.

    RED until:
      1) T04 extends _ORDINAL_PATTERN to accept N.M.code.K ordinals.
      2) T08/T10 wires fence extraction and ordinal resolution in OrdinalPathMapper.

    Spy contract: patches backlog_core.operations.view_item.
    """

    @_skip_without_recursive_nav
    @_skip_without_real_enc
    async def test_navigate_to_code_fence_returns_content_key(
        self,
        view_result_recursive_nav: ViewItemResult,
        normalized_recursive_nav: list[NormalizedSection],
        mocker: MockerFixture,
    ) -> None:
        """navigate=N.M.code.0 response has 'content' key, not 'error'.

        Currently RED: _ORDINAL_PATTERN rejects 'code' segment →
        DisclosureParamError → response has 'error' + 'invalid_params'.
        """
        parent_ordinal = _find_subheading_entry_ordinal(normalized_recursive_nav)
        fence_ordinal = f"{parent_ordinal}.code.0"
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_recursive_nav)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#0", "navigate": fence_ordinal})

        data = _extract_response_dict(result)
        assert "content" in data, (
            f"navigate='{fence_ordinal}' must return 'content' key. "
            f"Got keys: {sorted(data.keys())}. "
            "RED: _ORDINAL_PATTERN rejects 'code' → DisclosureParamError "
            "{'error', 'invalid_params'}."
        )
        assert "error" not in data, f"navigate='{fence_ordinal}' must not return 'error'. Got: {data.get('error')!r}"

    @_skip_without_recursive_nav
    @_skip_without_real_enc
    async def test_navigate_to_code_fence_returns_fence_body_without_markers(
        self,
        view_result_recursive_nav: ViewItemResult,
        normalized_recursive_nav: list[NormalizedSection],
        mocker: MockerFixture,
    ) -> None:
        """navigate=N.M.code.0 content is raw fence body without ``` delimiters.

        Verifies AC#4: the raw fence body (without surrounding backtick markers)
        is returned.  Language tag is NOT included in the content string.

        Currently RED: see test_navigate_to_code_fence_returns_content_key.
        """
        parent_ordinal = _find_subheading_entry_ordinal(normalized_recursive_nav)
        fence_ordinal = f"{parent_ordinal}.code.0"
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_recursive_nav)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#0", "navigate": fence_ordinal})

        data = _extract_response_dict(result)
        content = data.get("content", "")
        if not isinstance(content, str):
            pytest.skip(
                f"content is {type(content).__name__!r}; "
                "precondition test (test_navigate_to_code_fence_returns_content_key) "
                "must pass first."
            )
        assert "first_fence" in content, (
            f"Code fence body must contain the function name 'first_fence' "
            f"from the fixture's ```python block. "
            f"Got content={content!r}"
        )
        assert "```" not in content, (
            f"Code fence body must not contain backtick fence markers (```). Raw body only. Got content={content!r}"
        )


# ---------------------------------------------------------------------------
# TC-T9: code-fence miss has same error shape as numeric miss TC-T3 (AC#5)
# ---------------------------------------------------------------------------


class TestCodeFenceMissErrorShape:
    """TC-T9: navigate=N.M.code.99 produces the same error shape as numeric miss.

    ADR (no new error type for code-fence misses): OrdinalNotFoundError is
    reused, so the error dict must carry exactly three keys:
      'error', 'requested_ordinal', 'valid_ordinals'
    — identical to the numeric-miss shape from TC-T3 (navigate='99.99').

    RED until T04 extends _ORDINAL_PATTERN (current state: regex rejects
    'code' segment → DisclosureParamError → 2-key dict without 'valid_ordinals')
    and T08/T10 wires OrdinalNotFoundError for code-fence misses.

    Spy contract: patches backlog_core.operations.view_item.
    """

    #: Key set expected in any OrdinalNotFoundError response (matches TC-T3).
    _ORDINAL_NOT_FOUND_KEYS: frozenset[str] = frozenset({"error", "requested_ordinal", "valid_ordinals"})

    @_skip_without_recursive_nav
    @_skip_without_real_enc
    async def test_code_fence_miss_includes_valid_ordinals(
        self,
        view_result_recursive_nav: ViewItemResult,
        normalized_recursive_nav: list[NormalizedSection],
        mocker: MockerFixture,
    ) -> None:
        """navigate=N.M.code.99 response includes non-empty 'valid_ordinals' list.

        Currently RED: _ORDINAL_PATTERN rejects 'code' → DisclosureParamError →
        response has 'invalid_params' but NOT 'valid_ordinals'.
        After T04+T10: regex accepts → mapper miss → OrdinalNotFoundError →
        'valid_ordinals' present and non-empty.
        """
        parent_ordinal = _find_subheading_entry_ordinal(normalized_recursive_nav)
        miss_ordinal = f"{parent_ordinal}.code.99"
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_recursive_nav)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#0", "navigate": miss_ordinal})

        data = _extract_response_dict(result)
        assert "valid_ordinals" in data, (
            f"Code-fence miss ('{miss_ordinal}') must include 'valid_ordinals' "
            f"for agent recovery without a second round-trip. "
            f"Got keys: {sorted(data.keys())}. "
            "RED: regex rejects 'code' → DisclosureParamError → 'invalid_params' "
            "not 'valid_ordinals'."
        )
        valid = data.get("valid_ordinals")
        assert isinstance(valid, list), f"valid_ordinals must be a list. Got {type(valid).__name__!r}: {valid!r}"
        assert len(valid) > 0, f"valid_ordinals must be non-empty (agent recovery list). Got: {valid!r}"

    @_skip_without_recursive_nav
    @_skip_without_real_enc
    async def test_code_fence_miss_includes_requested_ordinal(
        self,
        view_result_recursive_nav: ViewItemResult,
        normalized_recursive_nav: list[NormalizedSection],
        mocker: MockerFixture,
    ) -> None:
        """navigate=N.M.code.99 response echoes the requested ordinal string.

        Verifies OrdinalNotFoundError shape: 'requested_ordinal' must equal the
        exact ordinal string that was requested.
        Currently RED: same reason as test_code_fence_miss_includes_valid_ordinals.
        """
        parent_ordinal = _find_subheading_entry_ordinal(normalized_recursive_nav)
        miss_ordinal = f"{parent_ordinal}.code.99"
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_recursive_nav)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#0", "navigate": miss_ordinal})

        data = _extract_response_dict(result)
        assert "requested_ordinal" in data, (
            f"Code-fence miss must echo 'requested_ordinal'. Got keys: {sorted(data.keys())}"
        )
        assert data["requested_ordinal"] == miss_ordinal, (
            f"'requested_ordinal' must equal the miss ordinal. "
            f"Expected {miss_ordinal!r}, got {data['requested_ordinal']!r}"
        )

    @_skip_without_recursive_nav
    @_skip_without_real_enc
    async def test_code_fence_miss_key_set_matches_numeric_miss(
        self,
        view_result_recursive_nav: ViewItemResult,
        normalized_recursive_nav: list[NormalizedSection],
        mocker: MockerFixture,
    ) -> None:
        """navigate=N.M.code.99 key set identical to navigate='99.99' (TC-T3 shape).

        Verifies AC#5: no new error type for code-fence misses — OrdinalNotFoundError
        is reused.  The 3-key dict shape is pinned in _ORDINAL_NOT_FOUND_KEYS.

        Expected keys: {sorted(self._ORDINAL_NOT_FOUND_KEYS)}.

        Currently RED: DisclosureParamError produces {'error', 'invalid_params'} —
        2 keys, missing 'requested_ordinal' and 'valid_ordinals'.
        """
        parent_ordinal = _find_subheading_entry_ordinal(normalized_recursive_nav)
        miss_ordinal = f"{parent_ordinal}.code.99"
        mocker.patch("backlog_core.operations.view_item", return_value=view_result_recursive_nav)

        async with Client(mcp) as client:
            result = await client.call_tool("backlog_view", {"selector": "#0", "navigate": miss_ordinal})

        data = _extract_response_dict(result)
        actual_keys = frozenset(data.keys())
        assert actual_keys == self._ORDINAL_NOT_FOUND_KEYS, (
            f"Code-fence miss key set must match numeric-miss shape (TC-T3).\n"
            f"  Expected keys : {sorted(self._ORDINAL_NOT_FOUND_KEYS)}\n"
            f"  Actual keys   : {sorted(actual_keys)}\n"
            f"  Missing keys  : {sorted(self._ORDINAL_NOT_FOUND_KEYS - actual_keys)}\n"
            f"  Extra keys    : {sorted(actual_keys - self._ORDINAL_NOT_FOUND_KEYS)}\n"
            "RED: _ORDINAL_PATTERN rejects 'code' → DisclosureParamError "
            "{'error', 'invalid_params'} — missing 'requested_ordinal', 'valid_ordinals'."
        )
