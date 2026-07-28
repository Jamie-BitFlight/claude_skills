"""Offline-safe ``tiktoken`` for backlog_core view tests (PR #2496 Codex finding).

Importing ``backlog_core.server`` initializes
``server._enc = tiktoken.get_encoding("cl100k_base")`` at module load, which
downloads the encoding when the tiktoken cache is empty. In a fresh/offline
environment that network call fails (``ProxyError``) and the view tests error
before reaching their assertions.

``tiktoken.registry.get_encoding`` returns ``ENCODINGS[name]`` directly when the
name is already cached (verified against tiktoken source). So this conftest
pre-populates that cache *before any test imports ``server``*:

- When the cache/network provides the real encoding (CI, dev), it is used
  unchanged — preserving the token-budget calibration the over-budget tests rely
  on.
- When loading fails (offline / empty cache), a deterministic stub encoder is
  seeded so ``server`` imports and the tests run without any network call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import tiktoken
import tiktoken.registry

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence, Set as AbstractSet


class _StubEncoder(tiktoken.Encoding):
    """Deterministic ~4-chars-per-token stand-in for cl100k_base (offline only).

    Inherits from tiktoken.Encoding so it satisfies the ENCODINGS registry type
    (dict[str, Encoding]) without a cast().  __init__ bypasses the BPE
    initialisation — the stub only needs encode() and decode().
    """

    def __init__(self) -> None:
        object.__init__(self)  # skip BPE init — no encoding data is needed

    def encode(
        self,
        text: str,
        *,
        allowed_special: Literal["all"] | AbstractSet[str] = frozenset(),
        disallowed_special: Literal["all"] | Collection[str] = "all",
    ) -> list[int]:
        """Return a token list whose length tracks the input length monotonically."""
        return [0] * ((len(text) + 3) // 4)

    def decode(self, tokens: Sequence[int], errors: str = "replace") -> str:
        """Return a placeholder string proportional to the token count."""
        return " " * (len(tokens) * 4)


def _ensure_cl100k_cached() -> bool:
    """Pre-warm tiktoken's encoding cache so importing ``server`` never downloads.

    Returns True when the REAL ``cl100k_base`` encoding is available (cache or
    network). When it is unavailable, seeds a deterministic stub so ``server``
    still imports, and returns False — token-budget tests skip in that case
    because the stub lacks real BPE compression and cannot reproduce their
    calibrated counts (a repeated-character body that compresses far under budget
    with the real encoder would measure over budget with a len-based stub).
    """
    if "cl100k_base" in tiktoken.registry.ENCODINGS:
        return True
    try:
        tiktoken.get_encoding("cl100k_base")  # populates ENCODINGS from cache/network
    except Exception:  # ruff: ignore[blind-except] - tiktoken raises undeclared download/network errors when its cache is empty and the network is unreachable; the concrete class is not part of its public API, so seed a deterministic stub to keep server importable offline.
        tiktoken.registry.ENCODINGS["cl100k_base"] = _StubEncoder()
        return False
    else:
        return True


REAL_CL100K_AVAILABLE = _ensure_cl100k_cached()
"""True when the real cl100k_base encoding loaded; token-budget tests skip if False."""
