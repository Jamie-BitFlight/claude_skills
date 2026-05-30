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

from typing import cast

import tiktoken
import tiktoken.registry


class _StubEncoder:
    """Deterministic ~4-chars-per-token stand-in for cl100k_base (offline only)."""

    def encode(self, text: str, *_args: object, **_kwargs: object) -> list[int]:
        """Return a token list whose length tracks the input length monotonically."""
        return [0] * ((len(text) + 3) // 4)


def _ensure_cl100k_cached() -> None:
    """Pre-warm tiktoken's encoding cache so importing ``server`` never downloads."""
    if "cl100k_base" in tiktoken.registry.ENCODINGS:
        return
    try:
        tiktoken.get_encoding("cl100k_base")  # populates ENCODINGS from cache/network
    except Exception:  # noqa: BLE001 - tiktoken raises undeclared download/network errors when its cache is empty and the network is unreachable; the concrete class is not part of its public API, so seed a deterministic stub to keep tests runnable offline.
        tiktoken.registry.ENCODINGS["cl100k_base"] = cast("tiktoken.Encoding", _StubEncoder())


_ensure_cl100k_cached()
