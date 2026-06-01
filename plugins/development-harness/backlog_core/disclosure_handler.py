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

from backlog_core.disclosure_types import DisclosureMode, DisclosureParamError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ORDINAL_PATTERN: re.Pattern[str] = re.compile(r"^(\d+\.)*\d+$")
"""Ordinal dot-path regex from architect spec §7.2.

Accepts: ``"0"``, ``"4.0"``, ``"3.0.0"``.
Rejects: empty string, path traversal (``../secrets``), alpha chars (``4.0.x``).
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
                "map and navigate are mutually exclusive — choose one mode.",
                {"map": map, "navigate": navigate},
            )
        if map and head is not None:
            raise DisclosureParamError(
                "map is incompatible with head — map cannot extract a token window.",
                {"map": map, "head": head},
            )
        if head is not None and navigate is None:
            raise DisclosureParamError(
                "head requires navigate — no target section to apply the token bound to.",
                {"head": head},
            )
        if skip_tokens != 0 and head is None:
            raise DisclosureParamError(
                "skip_tokens requires head — a pagination offset is only valid "
                "when a token window (head) is also set.",
                {"skip_tokens": skip_tokens},
            )

        # ------------------------------------------------------------------
        # 2. Range checks — run before ordinal validation
        # ------------------------------------------------------------------
        if skip_tokens < 0:
            raise DisclosureParamError(
                f"skip_tokens must be >= 0 (got {skip_tokens}).",
                {"skip_tokens": skip_tokens},
            )
        if head is not None and not (_HEAD_MIN <= head <= _HEAD_MAX):
            raise DisclosureParamError(
                f"head must be between {_HEAD_MIN} and {_HEAD_MAX} (got {head}).",
                {"head": head},
            )

        # ------------------------------------------------------------------
        # 3. Ordinal security gate (§7.2) — runs before any downstream use
        # ------------------------------------------------------------------
        if navigate is not None and not _ORDINAL_PATTERN.fullmatch(navigate):
            raise DisclosureParamError(
                f"navigate ordinal {navigate!r} is invalid. "
                r"Expected format matching ^(\d+\.)*\d+$ "
                '(e.g. "0", "4.0", "3.0.0").',
                {"navigate": navigate},
            )

        # ------------------------------------------------------------------
        # 4. Mode derivation — only reached when all validations pass
        # ------------------------------------------------------------------
        if map:
            return DisclosureRequest(
                mode=DisclosureMode.MAP,
                navigate_ordinal=None,
                head_tokens=None,
                skip_tokens=skip_tokens,
            )
        if navigate is not None and head is not None:
            return DisclosureRequest(
                mode=DisclosureMode.EXTRACT,
                navigate_ordinal=navigate,
                head_tokens=head,
                skip_tokens=skip_tokens,
            )
        if navigate is not None:
            return DisclosureRequest(
                mode=DisclosureMode.NAVIGATE,
                navigate_ordinal=navigate,
                head_tokens=None,
                skip_tokens=skip_tokens,
            )
        return DisclosureRequest(
            mode=DisclosureMode.PASSTHROUGH,
            navigate_ordinal=None,
            head_tokens=None,
            skip_tokens=skip_tokens,
        )
