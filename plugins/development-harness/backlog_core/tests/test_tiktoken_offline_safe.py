"""Tests for the offline-safe tiktoken cache pre-warm installed by conftest (PR #2496).

The conftest must (a) leave ``cl100k_base`` cached so importing ``server`` never
triggers a network download, and (b) provide a deterministic stub encoder whose
token count tracks input length (so over/under-budget branches still differ when
the stub is used offline).
"""

from __future__ import annotations

import tiktoken.registry

from backlog_core.tests.conftest import _StubEncoder


def test_cl100k_base_is_cached_after_conftest() -> None:
    """conftest pre-warmed the cache, so server import will not download."""
    assert "cl100k_base" in tiktoken.registry.ENCODINGS, (
        "conftest._ensure_cl100k_cached must leave cl100k_base in tiktoken's cache "
        "so importing backlog_core.server never hits the network."
    )


def test_stub_encoder_token_count_is_monotonic_in_length() -> None:
    """The offline stub must produce longer token lists for longer text."""
    enc = _StubEncoder()
    assert enc.encode("abcdefgh") == [0, 0]  # 8 chars -> 2 tokens
    assert len(enc.encode("x" * 4000)) > len(enc.encode("x" * 4))
