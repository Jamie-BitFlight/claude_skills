"""Shared pytest fixtures for frustration-analyzer tests.

Network guard: unit tests must never perform real network I/O.
Any outbound connection raises ``NetworkBlocked``. Loopback and
AF_UNIX sockets stay allowed so local IPC and test servers work.

tiktoken: downloads its BPE encoding from openaipublic.blob.core.windows.net
on first use when there's no local cache. Pre-warm it before the guard
is installed, and fall back to a byte-level stub encoder when the real
encoding isn't cached locally.
"""

from __future__ import annotations

import socket
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path
    from socket import _Address, _RetAddress

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "localhost.localdomain", ""})

_ADVICE = (
    "Unit tests must not touch the network -- mock the client at its call boundary. "
    "Genuine E2E requires @pytest.mark.e2e and DH_ALLOW_TEST_NETWORK=1."
)

_state = {"allowed": False}

# Single module-level MonkeyPatch installs the guard at session start and
# undoes it at session end, restoring the real socket functions.
_network_patch = pytest.MonkeyPatch()


class NetworkBlocked(RuntimeError):
    """Raised when a test attempts a network connection while the guard is armed."""


import tiktoken as _tk

# tiktoken downloads its BPE encoding from openaipublic.blob.core.windows.net
# on first use when there's no local cache.  Fresh CI runners have no cache,
# so the network guard blocks the download.  Try to load the real encoding
# first; if that fails (no cache + network blocked), fall back to a byte-level
# mock that can encode any string without the real BPE tables.
try:
    _tk.get_encoding("cl100k_base")
except OSError:
    _mock_enc = _tk.Encoding(
        name="cl100k_base",
        pat_str=r"""(?i:'s|'t|'re|'ve|'m|'ll|'d)|[^\r\n\p{L}\p{N}]?\p{L}+|\p{N}{1,3}| ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+""",
        mergeable_ranks={bytes([i]): i for i in range(256)},
        special_tokens={},
    )

    def _mock_get_encoding(name: str, **kwargs: object) -> _tk.Encoding:
        return _mock_enc

    _tk.get_encoding = _mock_get_encoding


def _is_local(address: _Address) -> bool:
    if isinstance(address, (str, bytes)):
        return True
    if isinstance(address, tuple) and address:
        return str(address[0]) in _LOOPBACK_HOSTS
    return False


def _guarded_connect(self: socket.socket, address: _Address) -> None:
    if not (_state["allowed"] or _is_local(address)):
        msg = f"Blocked outbound connection to {address!r}. {_ADVICE}"
        raise NetworkBlocked(msg)
    _real_connect(self, address)


def _guarded_connect_ex(self: socket.socket, address: _Address) -> int:
    if not (_state["allowed"] or _is_local(address)):
        msg = f"Blocked outbound connection to {address!r}. {_ADVICE}"
        raise NetworkBlocked(msg)
    return _real_connect_ex(self, address)


def _guarded_getaddrinfo(
    host: str | bytes | None, port: str | bytes | int | None, *args: int, **kwargs: int
) -> list[tuple[socket.AddressFamily, socket.SocketKind, int, str, _RetAddress]]:
    if not (_state["allowed"] or _is_local((host, port))):
        msg = f"Blocked DNS resolution of {host!r}. {_ADVICE}"
        raise NetworkBlocked(msg)
    return _real_getaddrinfo(host, port, *args, **kwargs)


_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex
_real_getaddrinfo = socket.getaddrinfo


def pytest_configure(config: pytest.Config) -> None:
    _network_patch.setattr(socket.socket, "connect", _guarded_connect)
    _network_patch.setattr(socket.socket, "connect_ex", _guarded_connect_ex)
    _network_patch.setattr(socket, "getaddrinfo", _guarded_getaddrinfo)


def pytest_unconfigure(config: pytest.Config) -> None:
    _network_patch.undo()


# ── fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def render(tmp_path: Path):
    """Return a helper that calls _render_card into tmp_path."""
    from _server import ASSISTANT, TASK, USER, render_card

    def _render(filename: str = "card.svg", **kwargs):
        out = tmp_path / filename
        result = render_card(TASK, ASSISTANT, USER, str(out), **kwargs)
        return out, result

    return _render
