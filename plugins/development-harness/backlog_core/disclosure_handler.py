"""Disclosure handler for the MCP progressive disclosure contract.

This module is extended across implementation phases:

- Phase 2 (T16): ``DisclosureRequest`` dataclass + ``DisclosureRequestParser``
  (parsing and boundary validation only — no I/O, no fetching, no mapping).
- Phase 3 (T17/T18): ``TokenBoundedExtractor`` + ``BacklogViewDisclosureHandler``
  (orchestration, token bounding, response assembly).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from progressive_markdown.list_navigator import ENCODING, TOKEN_BUDGET

from backlog_core import operations
from backlog_core.content_normalizer import ItemContentNormalizer
from backlog_core.disclosure_types import (
    BoundedContent,
    BoundedResponse,
    DisclosureMode,
    DisclosureParamError,
    MapResponse,
    NavigateResponse,
)
from backlog_core.ordinal_mapper import OrdinalEntry, OrdinalPathMapper

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ORDINAL_PATTERN: re.Pattern[str] = re.compile(r"^\d+(\.\d+)*(\.code\.\d+)?$")
"""Ordinal dot-path regex from architect spec §7.2 (corrected from spec literal — see DN-1).

Format: numeric path, optionally ending in one code-fence terminal.
Accepts: ``"0"``, ``"4.0"``, ``"3.0.0"``, ``"4.0.code.0"``, ``"4.0.1.code.0"``.
Rejects: empty string, path traversal (``../secrets``), alpha chars (``4.0.x``),
bare ``code.0`` (no leading numeric segment), ``4.0.code`` (code without index),
``4.0.foo.0`` (non-code alpha segment).
"""

_HEAD_MIN: int = 1
_HEAD_MAX: int = 25_000


# ---------------------------------------------------------------------------
# DisclosureRequest — validated, strongly typed parameter bundle
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DisclosureRequest:
    """Parsed and validated disclosure parameters for a single MCP call.

    All fields are validated before instantiation.  Callers receive a strongly
    typed request object — no raw input survives to downstream components.

    Attributes:
        mode: Derived operating mode (PASSTHROUGH / MAP / NAVIGATE / EXTRACT).
        navigate_ordinal: Validated ordinal string; ``None`` for MAP and PASSTHROUGH.
        head_tokens: Token window size; ``None`` for non-EXTRACT modes.
        skip_tokens: Token offset for pagination; always 0 for non-EXTRACT modes.
    """

    mode: DisclosureMode
    navigate_ordinal: str | None
    head_tokens: int | None
    skip_tokens: int


# ---------------------------------------------------------------------------
# DisclosureRequestParser — Phase 2 boundary validator (SRP: parse only)
# ---------------------------------------------------------------------------


class DisclosureRequestParser:
    """Validate and parse four optional MCP parameters into a ``DisclosureRequest``.

    **Responsibility boundary**: parsing and validation only.  This class performs
    no fetching, mapping, token counting, or any I/O.  All constraint violations
    raise ``DisclosureParamError`` before any downstream code sees the values.

    Rules implemented (architect spec §4.3, §6.3, §7.1-7.2):

    1. No params → PASSTHROUGH.
    2. ``map=True`` alone → MAP.
    3. ``navigate`` alone → NAVIGATE.
    4. ``navigate`` + ``head`` → EXTRACT.
    5. ``navigate`` + ``head`` + ``skip_tokens`` → EXTRACT continuation.
    6. ``head`` without ``navigate`` → ``DisclosureParamError``.
    7. ``skip_tokens`` (non-zero) without ``head`` → ``DisclosureParamError``.
    8. ``map`` + ``navigate`` → ``DisclosureParamError`` (mutually exclusive).
    9. ``map`` + ``head`` → ``DisclosureParamError`` (incompatible).
    10. Invalid ordinal format → ``DisclosureParamError`` (security gate §7.2).
    11. ``head`` out of [1, 25000] → ``DisclosureParamError``.
    12. ``skip_tokens < 0`` → ``DisclosureParamError``.
    """

    def parse(
        self,
        *,
        map: bool = False,  # noqa: A002 — shadows builtin; matches MCP parameter name exactly
        navigate: str | None = None,
        head: int | None = None,
        skip_tokens: int = 0,
    ) -> DisclosureRequest:
        """Parse disclosure parameters and return a validated ``DisclosureRequest``.

        Args:
            map: When ``True``, request a structural map of the item (MAP mode).
            navigate: Dot-path ordinal targeting a section or entry in the item.
            head: Maximum token window to return; activates EXTRACT mode when
                combined with ``navigate``.
            skip_tokens: Token offset for pagination continuation (requires ``head``).

        Returns:
            A ``DisclosureRequest`` with ``mode`` derived from the parameter combination.

        Raises:
            DisclosureParamError: On any invalid parameter or conflicting combination.
        """
        # ------------------------------------------------------------------
        # 1. Conflict checks — checked first to give the clearest error messages
        # ------------------------------------------------------------------
        if map and navigate is not None:
            raise DisclosureParamError(
                "map and navigate are mutually exclusive — choose one mode.", {"map": map, "navigate": navigate}
            )
        if map and head is not None:
            raise DisclosureParamError(
                "map is incompatible with head — map cannot extract a token window.", {"map": map, "head": head}
            )
        if head is not None and navigate is None:
            raise DisclosureParamError(
                "head requires navigate — no target section to apply the token bound to.", {"head": head}
            )
        if skip_tokens != 0 and head is None:
            raise DisclosureParamError(
                "skip_tokens requires head — a pagination offset is only valid when a token window (head) is also set.",
                {"skip_tokens": skip_tokens},
            )

        # ------------------------------------------------------------------
        # 2. Range checks — run before ordinal validation
        # ------------------------------------------------------------------
        if skip_tokens < 0:
            raise DisclosureParamError(f"skip_tokens must be >= 0 (got {skip_tokens}).", {"skip_tokens": skip_tokens})
        if head is not None and not (_HEAD_MIN <= head <= _HEAD_MAX):
            raise DisclosureParamError(
                f"head must be between {_HEAD_MIN} and {_HEAD_MAX} (got {head}).", {"head": head}
            )

        # ------------------------------------------------------------------
        # 3. Ordinal security gate (§7.2) — runs before any downstream use
        # ------------------------------------------------------------------
        if navigate is not None and not _ORDINAL_PATTERN.fullmatch(navigate):
            raise DisclosureParamError(
                f"navigate ordinal {navigate!r} is invalid. "
                r"Expected format matching ^\d+(\.\d+)*(\.code\.\d+)?$ "
                '(e.g. "0", "4.0", "3.0.0", "4.0.code.0").',
                {"navigate": navigate},
            )

        # ------------------------------------------------------------------
        # 4. Mode derivation — only reached when all validations pass
        # ------------------------------------------------------------------
        if map:
            return DisclosureRequest(
                mode=DisclosureMode.MAP, navigate_ordinal=None, head_tokens=None, skip_tokens=skip_tokens
            )
        if navigate is not None and head is not None:
            return DisclosureRequest(
                mode=DisclosureMode.EXTRACT, navigate_ordinal=navigate, head_tokens=head, skip_tokens=skip_tokens
            )
        if navigate is not None:
            return DisclosureRequest(
                mode=DisclosureMode.NAVIGATE, navigate_ordinal=navigate, head_tokens=None, skip_tokens=skip_tokens
            )
        return DisclosureRequest(
            mode=DisclosureMode.PASSTHROUGH, navigate_ordinal=None, head_tokens=None, skip_tokens=skip_tokens
        )


# ---------------------------------------------------------------------------
# TokenBoundedExtractor — Phase 3 (T18): cl100k_base token windowing (SRP)
# ---------------------------------------------------------------------------


class TokenBoundedExtractor:
    """Apply cl100k_base token-bounded windowing to text content.

    **Responsibility boundary**: token bounding only.  This class encodes content,
    slices a token window, and decodes it back to a string.  It does NOT construct
    ``next_call`` hints (that is the handler's responsibility per architect spec §5.7)
    and does NOT fetch content from any external source.

    Uses the shared ``ENCODING`` singleton from ``progressive_markdown.list_navigator``
    (ADR-2) so token counts are consistent with budget gates, map estimates, and the
    rest of the progressive disclosure pipeline.

    Example::

        extractor = TokenBoundedExtractor()
        result = extractor.extract(content, head_tokens=4000)
        if result.truncated:
            # next window: pass result.returned_tokens as skip_tokens
            rest = extractor.extract(content, head_tokens=4000, skip_tokens=result.returned_tokens)
    """

    def extract(self, content: str, head_tokens: int, skip_tokens: int = 0) -> BoundedContent:
        """Return the token window ``[skip_tokens : skip_tokens + head_tokens]``.

        The full content is encoded once with ``cl100k_base``.  The requested slice
        is decoded back to a string.  When ``skip_tokens`` meets or exceeds the total
        token count the window is empty, ``returned_tokens`` is 0, and
        ``truncated`` is ``False`` (the caller has read past the end of content).

        Args:
            content: Source text to window.  Encoded once per call; the token list
                is not cached between calls.
            head_tokens: Maximum number of tokens to return in this window.  A value
                larger than the remaining tokens after skipping is clamped to the
                actual remaining count (no padding).
            skip_tokens: Token offset for pagination continuation.  ``0`` starts
                from the beginning of content.  Defaults to ``0``.

        Returns:
            A ``BoundedContent`` value object with:

            - ``content``: Decoded token window (empty string when skip overshots).
            - ``total_tokens``: cl100k_base count of the FULL original content —
              invariant across all window positions.
            - ``returned_tokens``: Token count of the decoded window (≤ ``head_tokens``).
            - ``truncated``: ``True`` when there are tokens beyond the returned window.
        """
        all_tokens: list[int] = ENCODING.encode(content)
        total_tokens: int = len(all_tokens)
        window_tokens: list[int] = all_tokens[skip_tokens : skip_tokens + head_tokens]
        returned_tokens: int = len(window_tokens)
        decoded: str = ENCODING.decode(window_tokens)
        truncated: bool = skip_tokens + returned_tokens < total_tokens
        return BoundedContent(
            content=decoded, total_tokens=total_tokens, returned_tokens=returned_tokens, truncated=truncated
        )


# ---------------------------------------------------------------------------
# BacklogViewDisclosureHandler — Phase 3 (T20): orchestration (SRP: orchestrate only)
# ---------------------------------------------------------------------------


class BacklogViewDisclosureHandler:
    """Orchestrate progressive disclosure modes from un-gated item content.

    **Responsibility boundary**: orchestration only.  This class fetches item
    content via the un-gated ``operations.view_item()`` path, delegates
    normalization to ``ItemContentNormalizer``, ordinal mapping to a fresh
    ``OrdinalPathMapper`` per call (stateful per-item), and token windowing to
    ``TokenBoundedExtractor``.  It does NOT normalize, map, or token-count
    directly (SRP/DIP).

    **Mapper per call** (architect spec §4.4): ``OrdinalPathMapper`` is
    stateful — its ``_resolution_map`` is populated by ``build_map()`` and is
    specific to a single item's section list.  A fresh mapper instance is
    constructed on every ``handle()`` call rather than injected, so each call
    is isolated with no cross-call state leakage.  ``normalizer`` and
    ``extractor`` are stateless and may be injected or left as defaults.

    **Un-gated path** (ADR-5): The gated ``backlog_view`` tool returns
    ``body=""`` for over-budget items.  ``operations.view_item()`` is called
    directly (via the module reference ``backlog_core.operations``) to obtain
    the full body regardless of token budget.

    **Spy contract**: patch target is ``backlog_core.operations.view_item``
    (the module attribute).  ``handle()`` calls ``operations.view_item(selector)``
    via the module, NOT via a direct-import alias, so the spy intercepts the
    call correctly.

    Example::

        handler = BacklogViewDisclosureHandler()
        request = DisclosureRequestParser().parse(map=True)
        result = handler.handle("#2515", request)
        assert isinstance(result, MapResponse)
    """

    def __init__(
        self, normalizer: ItemContentNormalizer | None = None, extractor: TokenBoundedExtractor | None = None
    ) -> None:
        """Initialise handler with optional injected collaborators.

        Args:
            normalizer: ``ItemContentNormalizer`` instance.  Defaults to a
                new instance when ``None``.
            extractor: ``TokenBoundedExtractor`` instance.  Defaults to a
                new instance when ``None``.
        """
        self._normalizer = normalizer if normalizer is not None else ItemContentNormalizer()
        self._extractor = extractor if extractor is not None else TokenBoundedExtractor()

    def handle(self, selector: str, request: DisclosureRequest) -> MapResponse | NavigateResponse | BoundedResponse:
        """Fetch item content and dispatch to the appropriate disclosure handler.

        Calls ``operations.view_item(selector)`` once (un-gated, full content),
        normalizes the result, builds the ordinal map, then dispatches by mode.

        Args:
            selector: Issue selector (e.g. ``"#2515"``) forwarded unchanged
                to ``operations.view_item()``.
            request: Validated ``DisclosureRequest`` produced by
                ``DisclosureRequestParser``.

        Returns:
            ``MapResponse``, ``NavigateResponse``, or ``BoundedResponse``
            depending on ``request.mode``.

        Raises:
            ValueError: When ``request.mode`` is ``PASSTHROUGH`` — the caller
                must route PASSTHROUGH to the existing code path before calling
                this handler.
            OrdinalNotFoundError: When the ``navigate`` ordinal is not present
                in the item's ordinal map (raised from ``_handle_navigate`` or
                ``_handle_extract``).
        """
        # Un-gated fetch (ADR-5): call via module reference so spy on
        # ``backlog_core.operations.view_item`` intercepts the call.
        # ``include_content=True`` is the default — full body and sections.
        view_result = operations.view_item(selector)
        sections = self._normalizer.normalize(view_result)

        # Fresh mapper per call — OrdinalPathMapper is stateful per-item.
        mapper = OrdinalPathMapper(sections)
        entries = mapper.build_map()

        match request.mode:
            case DisclosureMode.MAP:
                return self._handle_map(selector, entries, mapper)
            case DisclosureMode.NAVIGATE:
                if request.navigate_ordinal is None:  # parser invariant: always set for NAVIGATE
                    raise ValueError("NAVIGATE mode requires navigate_ordinal.")
                return self._handle_navigate(request.navigate_ordinal, mapper)
            case DisclosureMode.EXTRACT:
                if request.navigate_ordinal is None:  # parser invariant: always set for EXTRACT
                    raise ValueError("EXTRACT mode requires navigate_ordinal.")
                if request.head_tokens is None:  # parser invariant: always set for EXTRACT
                    raise ValueError("EXTRACT mode requires head_tokens.")
                return self._handle_extract(
                    selector, request.navigate_ordinal, request.head_tokens, request.skip_tokens, mapper
                )
            case _:
                raise ValueError(
                    f"BacklogViewDisclosureHandler does not handle mode "
                    f"{request.mode!r}. Route PASSTHROUGH to the existing "
                    f"code path before calling handle()."
                )

    def _handle_map(self, selector: str, entries: list[OrdinalEntry], mapper: OrdinalPathMapper) -> MapResponse:
        """Build a structural map response.

        ``MapResponse.total_est_tokens`` sums LEVEL-1 section estimates only
        (ordinals without a dot).  Level-2 entry lines are excluded to prevent
        double-counting body text already included in the parent section
        estimate (architect spec §5.2, #2495 regression guard).

        Args:
            selector: Item selector echoed into the response.
            entries: Map entries from ``OrdinalPathMapper.build_map()``.
            mapper: Mapper used for ``format_map_line()`` formatting.

        Returns:
            ``MapResponse`` with formatted ``map_text``, ``total_sections``
            (level-1 count), ``total_est_tokens`` (level-1 sum only), and
            ``over_budget`` flag.
        """
        level1_entries = [e for e in entries if "." not in e.ordinal]
        total_est_tokens = sum(e.est_tokens for e in level1_entries)
        map_text = "\n".join(mapper.format_map_line(e) for e in entries)
        return MapResponse(
            selector=selector,
            total_sections=len(level1_entries),
            total_est_tokens=total_est_tokens,
            map_text=map_text,
            over_budget=total_est_tokens > TOKEN_BUDGET,
        )

    def _handle_navigate(self, ordinal: str, mapper: OrdinalPathMapper) -> NavigateResponse:
        """Resolve an ordinal to full section/entry content.

        Args:
            ordinal: Validated dot-path ordinal (e.g. ``"4.0"``).
            mapper: Mapper with a populated resolution map (``build_map()``
                already called by ``handle()``).

        Returns:
            ``NavigateResponse`` with full content and ``truncated=False``.

        Raises:
            OrdinalNotFoundError: When ``ordinal`` is not in the resolution
                map.  The exception carries ``valid_ordinals`` so callers can
                recover without a second round-trip.
        """
        unit = mapper.resolve(ordinal)
        return NavigateResponse(
            ordinal=ordinal, title=unit.title, content=unit.content, total_tokens=unit.total_tokens, truncated=False
        )

    def _handle_extract(
        self, selector: str, ordinal: str, head_tokens: int, skip_tokens: int, mapper: OrdinalPathMapper
    ) -> BoundedResponse:
        """Extract a token-bounded window from a section/entry.

        Builds a ``next_call`` continuation hint when the window is truncated.
        The hint uses ``skip_tokens=`` (not ``offset=``) per architect spec §5.7.
        The next skip position is cumulative: ``skip_tokens + bounded.returned_tokens``
        (absolute token offset into the full content sequence).

        Args:
            selector: Item selector included in the ``next_call`` hint (in
                scope here; ``BoundedContent`` carries no selector — ADR-5).
            ordinal: Validated dot-path ordinal.
            head_tokens: Token window size from the ``DisclosureRequest``.
            skip_tokens: Token offset from the ``DisclosureRequest`` (0 for
                the first window).
            mapper: Mapper with a populated resolution map.

        Returns:
            ``BoundedResponse`` with ``next_call`` populated when truncated,
            ``None`` otherwise.

        Raises:
            OrdinalNotFoundError: When ``ordinal`` is not in the resolution
                map.
        """
        unit = mapper.resolve(ordinal)
        bounded = self._extractor.extract(unit.content, head_tokens=head_tokens, skip_tokens=skip_tokens)
        next_call: str | None = None
        if bounded.truncated:
            next_skip = skip_tokens + bounded.returned_tokens
            next_call = (
                f'backlog_view(selector="{selector}", navigate="{ordinal}", '
                f"head={head_tokens}, skip_tokens={next_skip})"
            )
        return BoundedResponse(
            ordinal=ordinal,
            title=unit.title,
            content=bounded.content,
            total_tokens=bounded.total_tokens,
            returned_tokens=bounded.returned_tokens,
            truncated=bounded.truncated,
            next_call=next_call,
        )
