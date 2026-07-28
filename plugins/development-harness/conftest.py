"""Session-level network guard for the development-harness test suite.

This file lives at the pytest rootdir so it applies to every path in
``[tool.pytest.ini_options] testpaths`` (``tests``, ``tests_sam``,
``tests_backlog``, ``sam_schema/tests``).

Unit tests must never perform real network I/O: it is slow, non-deterministic,
credential-dependent, and -- as observed with the GitHub backend -- capable of
mutating production state. Any outbound connection raises ``NetworkBlocked``
loudly instead of silently succeeding. ``AF_UNIX`` sockets and loopback
addresses stay allowed so local IPC and test servers keep working.

Genuine E2E network access is double-gated: a test must be marked
``@pytest.mark.e2e`` (already excluded from the default run via ``-m "not e2e"``)
**and** the operator must set ``DH_ALLOW_TEST_NETWORK=1``. There is no public
fixture that lifts the guard; the policy is computed per-test from the marker
and the environment.
"""

from __future__ import annotations

import os
import socket
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from socket import _Address, _RetAddress

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "localhost.localdomain", ""})

_ADVICE = (
    "Unit tests must not touch the network -- mock the client at its call boundary. "
    "Genuine E2E requires @pytest.mark.e2e and DH_ALLOW_TEST_NETWORK=1."
)

# Mutable holder so the per-test fixture can toggle the guard without a `global`
# statement. Read by the guarded functions and flipped by ``_network_policy``.
_state = {"allowed": False}

# Single module-level MonkeyPatch installs the guard at session start and
# undoes it at session end, restoring the real socket functions reliably and
# without ``# type: ignore`` suppressions.
_network_patch = pytest.MonkeyPatch()

# tiktoken downloads its BPE encoding from openaipublic.blob.core.windows.net
# on first use when there's no local cache.  Fresh CI runners have no cache,
# so the network guard blocks the download and crashes every test that
# imports backlog_core.server.  Mock get_encoding before any import triggers
# it so the encoding object exists without hitting the network.
import tiktoken as _tk
from tests.network_blocked import NetworkBlocked

_mock_enc = _tk.Encoding(
    name="cl100k_base",
    pat_str=r"""(?i:'s|'t|'re|'ve|'m|'ll|'d)|[^\r\n\p{L}\p{N}]?\p{L}+|\p{N}{1,3}| ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+""",
    mergeable_ranks={b" ": 1, b"test": 2},
    special_tokens={},
)
_tk.get_encoding = lambda name, **kw: _mock_enc  # type: ignore[method-assign]


def _is_local(address: _Address) -> bool:
    """Report whether a socket address is loopback or a filesystem path.

    Args:
        address: The address passed to ``connect``/``connect_ex``. A ``str`` or
            ``bytes`` value means ``AF_UNIX``; a tuple means AF_INET/AF_INET6.

    Returns:
        True when the address is a Unix socket path or a loopback host.
    """
    if isinstance(address, (str, bytes)):  # AF_UNIX path
        return True
    if isinstance(address, tuple) and address:
        return str(address[0]) in _LOOPBACK_HOSTS
    return False


def _guarded_connect(self: socket.socket, address: _Address) -> None:
    """Block ``socket.connect`` to non-loopback addresses.

    Args:
        self: The socket being connected.
        address: Target address.

    Raises:
        NetworkBlocked: When the address is not loopback and the guard is armed.
    """
    if not (_state["allowed"] or _is_local(address)):
        msg = f"Blocked outbound connection to {address!r}. {_ADVICE}"
        raise NetworkBlocked(msg)
    _real_connect(self, address)


def _guarded_connect_ex(self: socket.socket, address: _Address) -> int:
    """Block ``socket.connect_ex`` to non-loopback addresses.

    Args:
        self: The socket being connected.
        address: Target address.

    Returns:
        The platform error code from the real ``connect_ex`` when permitted.

    Raises:
        NetworkBlocked: When the address is not loopback and the guard is armed.
    """
    if not (_state["allowed"] or _is_local(address)):
        msg = f"Blocked outbound connection to {address!r}. {_ADVICE}"
        raise NetworkBlocked(msg)
    return _real_connect_ex(self, address)


def _guarded_getaddrinfo(
    host: str | bytes | None, port: str | bytes | int | None, *args: int, **kwargs: int
) -> list[tuple[socket.AddressFamily, socket.SocketKind, int, str, _RetAddress]]:
    """Block DNS resolution of non-loopback hosts.

    Args:
        host: Hostname or address being resolved.
        port: Port or service name.
        *args: Positional ``family``/``type``/``proto``/``flags`` values.
        **kwargs: Keyword forms of the same.

    Returns:
        The real ``getaddrinfo`` result when the host is loopback.

    Raises:
        NetworkBlocked: When the host is not loopback and the guard is armed.
    """
    if not (_state["allowed"] or _is_local((host, port))):
        msg = f"Blocked DNS resolution of {host!r}. {_ADVICE}"
        raise NetworkBlocked(msg)
    return _real_getaddrinfo(host, port, *args, **kwargs)


# Real functions captured at import time, before the guard is installed.
# Referenced by the guarded wrappers via closure so they do not re-enter.
_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex
_real_getaddrinfo = socket.getaddrinfo


def pytest_configure(config: pytest.Config) -> None:
    """Install the socket guard for the whole session.

    Args:
        config: The pytest config object (unused).
    """
    _network_patch.setattr(socket.socket, "connect", _guarded_connect)
    _network_patch.setattr(socket.socket, "connect_ex", _guarded_connect_ex)
    _network_patch.setattr(socket, "getaddrinfo", _guarded_getaddrinfo)


def pytest_unconfigure(config: pytest.Config) -> None:
    """Restore the real socket functions at session teardown.

    Args:
        config: The pytest config object (unused).
    """
    _network_patch.undo()


@pytest.fixture(autouse=True)
def _network_policy(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Compute the per-test network policy from the e2e marker + env var.

    No public ``allow_network`` fixture is exposed. The guard is armed by
    default; it is lifted only when the test carries ``@pytest.mark.e2e`` and
    the operator set ``DH_ALLOW_TEST_NETWORK=1``. When the marker is present
    but the env var is not, the guard stays armed so the first attempted
    connection fails with a message naming the required env var.

    Args:
        request: The pytest fixture request for the current test.
        monkeypatch: Unused; present because autouse fixtures in this conftest
            frequently need it and listing it keeps the signature stable.

    Yields:
        None, with the guard armed (or lifted under the double gate).
    """
    marked_e2e = request.node.get_closest_marker("e2e") is not None
    explicitly_enabled = os.environ.get("DH_ALLOW_TEST_NETWORK") == "1"
    _state["allowed"] = marked_e2e and explicitly_enabled
    try:
        yield
    finally:
        _state["allowed"] = False
