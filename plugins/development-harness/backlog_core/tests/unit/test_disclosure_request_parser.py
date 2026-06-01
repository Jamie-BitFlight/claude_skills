"""Tests for DisclosureRequestParser.parse() — TDD, authored before T16 implementation.

These tests intentionally fail at collection (ModuleNotFoundError / ImportError) until
T16 creates ``backlog_core/disclosure_handler.py`` with ``DisclosureRequestParser``. That is the correct TDD pre-implementation state.

Behavioral contract pinned by this file
---------------------------------------
**Mode derivation rules** (§4.3):

1. No params → PASSTHROUGH mode; navigate_ordinal=None, head_tokens=None, skip_tokens=0.
2. ``map=True`` alone → MAP mode.
3. ``navigate=ordinal`` alone → NAVIGATE mode; navigate_ordinal echoed.
4. ``navigate=ordinal`` + ``head=N`` → EXTRACT mode; head_tokens=N, skip_tokens defaults 0.
5. ``navigate=ordinal`` + ``head=N`` + ``skip_tokens=K`` → EXTRACT mode continuation;
   skip_tokens=K.

**Error cases** (§6.3, §7.1-7.2):

6. ``head`` without ``navigate`` → DisclosureParamError.
7. ``skip_tokens`` without ``head`` → DisclosureParamError.
8. ``map=True`` + ``navigate`` → DisclosureParamError.
9. ``map=True`` + ``head`` → DisclosureParamError (map is incompatible with extract params).
10. Invalid ordinal format (path traversal ``../secrets``, alpha ``4.0.x``, empty string)
    → DisclosureParamError (security: regex gate runs before any downstream use).
11. ``head=25001`` (above hard max 25000) → DisclosureParamError.
12. ``head=0`` → DisclosureParamError (minimum is 1).
13. ``skip_tokens=-1`` → DisclosureParamError (must be >= 0).

**Accepted ordinal formats** (§7.2):

14. ``"0"`` — single digit accepted.
15. ``"4.0"`` — two-level dot-path accepted.
16. ``"3.0.0"`` — three-level dot-path accepted.

**Boundary values**:

17. ``head=1`` — minimum valid head accepted.
18. ``head=25000`` — maximum valid head accepted.
19. ``skip_tokens=0`` — minimum valid skip_tokens accepted.
"""

from __future__ import annotations

import pytest

# Intentionally fails at collection until T16 creates backlog_core/disclosure_handler.py.
from backlog_core.disclosure_handler import DisclosureRequestParser
from backlog_core.disclosure_types import DisclosureMode, DisclosureParamError

# ---------------------------------------------------------------------------
# Valid mode derivation
# ---------------------------------------------------------------------------


def test_no_params_returns_passthrough() -> None:
    """No disclosure parameters → PASSTHROUGH mode; existing behavior unchanged."""
    req = DisclosureRequestParser().parse()

    assert req.mode == DisclosureMode.PASSTHROUGH
    assert req.navigate_ordinal is None
    assert req.head_tokens is None
    assert req.skip_tokens == 0


def test_map_only_returns_map_mode() -> None:
    """map=True → MAP mode; navigate and head fields are None."""
    req = DisclosureRequestParser().parse(map=True)

    assert req.mode == DisclosureMode.MAP
    assert req.navigate_ordinal is None
    assert req.head_tokens is None


def test_navigate_only_returns_navigate_mode() -> None:
    """navigate=ordinal → NAVIGATE mode; ordinal echoed in navigate_ordinal."""
    req = DisclosureRequestParser().parse(navigate="4.0")

    assert req.mode == DisclosureMode.NAVIGATE
    assert req.navigate_ordinal == "4.0"
    assert req.head_tokens is None


def test_navigate_plus_head_returns_extract_mode() -> None:
    """navigate + head → EXTRACT mode; head echoed as head_tokens."""
    req = DisclosureRequestParser().parse(navigate="4.0", head=4000)

    assert req.mode == DisclosureMode.EXTRACT
    assert req.navigate_ordinal == "4.0"
    assert req.head_tokens == 4000
    assert req.skip_tokens == 0  # default — beginning of content


def test_navigate_head_skip_tokens_is_extract_continuation() -> None:
    """navigate + head + skip_tokens → EXTRACT mode; skip_tokens echoed for continuation."""
    req = DisclosureRequestParser().parse(navigate="4.0", head=4000, skip_tokens=4000)

    assert req.mode == DisclosureMode.EXTRACT
    assert req.navigate_ordinal == "4.0"
    assert req.head_tokens == 4000
    assert req.skip_tokens == 4000


# ---------------------------------------------------------------------------
# Accepted ordinal formats (§7.2)
# ---------------------------------------------------------------------------


def test_ordinal_single_digit_accepted() -> None:
    """Single-digit ordinal "0" matches ^(\\d+\\.)*\\d+$."""
    req = DisclosureRequestParser().parse(navigate="0")

    assert req.mode == DisclosureMode.NAVIGATE
    assert req.navigate_ordinal == "0"


def test_ordinal_two_levels_accepted() -> None:
    """Two-level ordinal "4.0" is accepted."""
    req = DisclosureRequestParser().parse(navigate="4.0")

    assert req.mode == DisclosureMode.NAVIGATE
    assert req.navigate_ordinal == "4.0"


def test_ordinal_three_levels_accepted() -> None:
    """Three-level ordinal "3.0.0" is accepted."""
    req = DisclosureRequestParser().parse(navigate="3.0.0")

    assert req.mode == DisclosureMode.NAVIGATE
    assert req.navigate_ordinal == "3.0.0"


# ---------------------------------------------------------------------------
# Error: conflicting parameter combinations
# ---------------------------------------------------------------------------


def test_head_without_navigate_raises() -> None:
    """head without navigate is meaningless — no target to bound."""
    with pytest.raises(DisclosureParamError):
        DisclosureRequestParser().parse(head=4000)


def test_skip_tokens_without_head_raises() -> None:
    """skip_tokens only valid when head is also set (pagination offset requires a window)."""
    with pytest.raises(DisclosureParamError):
        DisclosureRequestParser().parse(navigate="4.0", skip_tokens=4000)


def test_map_plus_navigate_raises() -> None:
    """map and navigate are mutually exclusive modes."""
    with pytest.raises(DisclosureParamError):
        DisclosureRequestParser().parse(map=True, navigate="4.0")


def test_map_plus_head_raises() -> None:
    """map and head are incompatible — map cannot extract a token window."""
    with pytest.raises(DisclosureParamError):
        DisclosureRequestParser().parse(map=True, head=4000)


# ---------------------------------------------------------------------------
# Error: ordinal format validation — security (§7.2)
# ---------------------------------------------------------------------------


def test_path_traversal_ordinal_raises() -> None:
    """../secrets must be rejected before reaching OrdinalPathMapper."""
    with pytest.raises(DisclosureParamError):
        DisclosureRequestParser().parse(navigate="../secrets")


def test_ordinal_with_alpha_raises() -> None:
    """4.0.x contains a non-digit character and must be rejected."""
    with pytest.raises(DisclosureParamError):
        DisclosureRequestParser().parse(navigate="4.0.x")


def test_empty_ordinal_raises() -> None:
    """Empty string does not match ^(\\d+\\.)*\\d+$ and must be rejected."""
    with pytest.raises(DisclosureParamError):
        DisclosureRequestParser().parse(navigate="")


# ---------------------------------------------------------------------------
# Error: head range (§6.3)
# ---------------------------------------------------------------------------


def test_head_above_hard_max_raises() -> None:
    """head=25001 exceeds the hard maximum of 25000."""
    with pytest.raises(DisclosureParamError):
        DisclosureRequestParser().parse(navigate="1", head=25001)


def test_head_zero_raises() -> None:
    """head=0 is below the minimum of 1."""
    with pytest.raises(DisclosureParamError):
        DisclosureRequestParser().parse(navigate="1", head=0)


# ---------------------------------------------------------------------------
# Error: skip_tokens range (§6.3)
# ---------------------------------------------------------------------------


def test_negative_skip_tokens_raises() -> None:
    """Negative skip_tokens would produce a negative token offset — invalid."""
    with pytest.raises(DisclosureParamError):
        DisclosureRequestParser().parse(navigate="1", head=1000, skip_tokens=-1)


# ---------------------------------------------------------------------------
# Boundary values
# ---------------------------------------------------------------------------


def test_head_at_minimum_accepted() -> None:
    """head=1 is the minimum valid value (1 ≤ head ≤ 25000)."""
    req = DisclosureRequestParser().parse(navigate="1", head=1)

    assert req.mode == DisclosureMode.EXTRACT
    assert req.head_tokens == 1


def test_head_at_maximum_accepted() -> None:
    """head=25000 is the maximum valid value (1 ≤ head ≤ 25000)."""
    req = DisclosureRequestParser().parse(navigate="1", head=25000)

    assert req.mode == DisclosureMode.EXTRACT
    assert req.head_tokens == 25000


def test_skip_tokens_zero_accepted() -> None:
    """skip_tokens=0 (the default) is the minimum valid offset — start of content."""
    req = DisclosureRequestParser().parse(navigate="1", head=1000, skip_tokens=0)

    assert req.mode == DisclosureMode.EXTRACT
    assert req.skip_tokens == 0


# ---------------------------------------------------------------------------
# DisclosureRequest field invariants
# ---------------------------------------------------------------------------


def test_passthrough_has_none_ordinal_and_none_head() -> None:
    """PASSTHROUGH mode must leave navigate_ordinal and head_tokens unset."""
    req = DisclosureRequestParser().parse()

    assert req.navigate_ordinal is None
    assert req.head_tokens is None


def test_navigate_mode_head_tokens_is_none() -> None:
    """NAVIGATE mode (no head param) must have head_tokens=None."""
    req = DisclosureRequestParser().parse(navigate="4.0")

    assert req.head_tokens is None


def test_extract_mode_echoes_navigate_ordinal() -> None:
    """In EXTRACT mode, navigate_ordinal carries the validated ordinal verbatim."""
    req = DisclosureRequestParser().parse(navigate="3.0.0", head=2000)

    assert req.navigate_ordinal == "3.0.0"


# ---------------------------------------------------------------------------
# Extended ordinal regex — §4.1 + §7.4 TDD contract (T04, expected RED before T09)
#
# Architecture spec new pattern: ^(\d+\.)*(\\d+|code\\.\\d+)$
# Current pattern:               ^(\\d+\\.)*\\d+$
#
# State under the PRE-T09 (current) regex:
#   RED  — test FAILS  (code-fence accept cases; T09 makes them GREEN)
#   GREEN — test PASSES (deep numeric / all reject cases; must stay GREEN after T09)
#
# These tests are exercised through DisclosureRequestParser.parse() — the public
# contract boundary — NOT by importing _ORDINAL_PATTERN directly.
# ---------------------------------------------------------------------------


# ── §7.4 named tests ────────────────────────────────────────────────────────


def test_navigate_code_fence_ordinal_accepted() -> None:
    """'4.0.code.0' must be accepted by the extended pattern.

    State: RED under current ^(\\d+\\.)*\\d+$ (rejects 'code' as non-digit terminal).
    Expected GREEN after T09 extends pattern to ^(\\d+\\.)*(\\d+|code\\.\\d+)$.
    """
    req = DisclosureRequestParser().parse(navigate="4.0.code.0")

    assert req.mode == DisclosureMode.NAVIGATE
    assert req.navigate_ordinal == "4.0.code.0"


def test_navigate_deep_numeric_ordinal_accepted() -> None:
    """'4.0.1.2.3' (5-level numeric path) must be accepted.

    State: GREEN under both old and new regex — unlimited numeric depth
    was already supported by ^(\\d+\\.)*\\d+$. Confirms no regression after T09.
    """
    req = DisclosureRequestParser().parse(navigate="4.0.1.2.3")

    assert req.mode == DisclosureMode.NAVIGATE
    assert req.navigate_ordinal == "4.0.1.2.3"


def test_navigate_missing_code_index_rejected() -> None:
    """'4.0.code' (code keyword with no trailing integer) must raise DisclosureParamError.

    State: GREEN under both old and new regex.
    Old pattern: 'code' is a non-digit terminal — rejected.
    New pattern: 'code' must be followed by '.\\d+' — still rejected.
    """
    with pytest.raises(DisclosureParamError):
        DisclosureRequestParser().parse(navigate="4.0.code")


def test_navigate_alpha_segment_rejected() -> None:
    """'4.0.foo.0' must raise DisclosureParamError — 'foo' is neither \\d+ nor 'code'.

    State: GREEN under both old and new regex.
    """
    with pytest.raises(DisclosureParamError):
        DisclosureRequestParser().parse(navigate="4.0.foo.0")


# ── §4.1 accept matrix — additional cases beyond the §7.4 named tests ───────


def test_extended_ordinal_accept_single_digit_four() -> None:
    """'4' (single non-zero digit) must be accepted — GREEN under old and new regex."""
    req = DisclosureRequestParser().parse(navigate="4")

    assert req.mode == DisclosureMode.NAVIGATE
    assert req.navigate_ordinal == "4"


def test_extended_ordinal_accept_two_levels_explicit() -> None:
    """'4.0' explicit §4.1 accept contract — GREEN under old and new regex.

    Note: test_ordinal_two_levels_accepted also covers this ordinal; this test
    explicitly records the §4.1 acceptance contract for the extended-pattern release.
    """
    req = DisclosureRequestParser().parse(navigate="4.0")

    assert req.mode == DisclosureMode.NAVIGATE
    assert req.navigate_ordinal == "4.0"


def test_extended_ordinal_accept_three_levels_explicit() -> None:
    """'4.0.1' (3-level numeric) — GREEN under old and new regex."""
    req = DisclosureRequestParser().parse(navigate="4.0.1")

    assert req.mode == DisclosureMode.NAVIGATE
    assert req.navigate_ordinal == "4.0.1"


def test_extended_ordinal_accept_deep_code_fence() -> None:
    """'4.0.1.code.0' (code fence nested under sub-heading) must be accepted.

    State: RED under current regex; GREEN after T09.
    """
    req = DisclosureRequestParser().parse(navigate="4.0.1.code.0")

    assert req.mode == DisclosureMode.NAVIGATE
    assert req.navigate_ordinal == "4.0.1.code.0"


# ── §4.1 reject matrix — additional cases beyond the §7.4 named tests ───────


def test_extended_ordinal_reject_bare_code() -> None:
    """'code.0' (no leading numeric segment) must raise DisclosureParamError.

    State: GREEN under old and new regex.
    Pattern requires at least one leading \\d+ segment before any terminal.
    """
    with pytest.raises(DisclosureParamError):
        DisclosureRequestParser().parse(navigate="code.0")


def test_extended_ordinal_reject_leading_dot() -> None:
    """'.4' (leading dot) must raise DisclosureParamError.

    State: GREEN under old and new regex — both patterns anchor start with \\d.
    """
    with pytest.raises(DisclosureParamError):
        DisclosureRequestParser().parse(navigate=".4")


def test_extended_ordinal_reject_trailing_dot() -> None:
    """'4.' (trailing dot with empty terminal) must raise DisclosureParamError.

    State: GREEN under old and new regex — both require a non-empty terminal segment.
    """
    with pytest.raises(DisclosureParamError):
        DisclosureRequestParser().parse(navigate="4.")
