"""Proves the session-level socket guard in the root conftest blocks the network.

Contract tests for the default-block + double-gated E2E network policy. These
tests run under the guard themselves (the root conftest applies to every
testpath), so they assert both the blocked path and the loopback-allowed path
from inside the same session the guard governs.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import textwrap
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from tests.network_blocked import NetworkBlocked

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def _probe_command(probe: Path, *args: str) -> list[str]:
    return [sys.executable, "-m", "pytest", str(probe), "-q", "-o", "addopts=", "--rootdir", str(_PLUGIN_ROOT), *args]


def test_outbound_connection_is_blocked() -> None:
    """A direct outbound TCP connect raises instead of reaching the internet.

    Uses RFC 5737 TEST-NET-3 (203.0.113.0/24) so no real host is ever named.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(NetworkBlocked, match="Blocked outbound connection"):
            sock.connect(("203.0.113.1", 443))
    finally:
        sock.close()


def test_dns_resolution_is_blocked() -> None:
    """Name resolution for a non-loopback host raises."""
    with pytest.raises(NetworkBlocked, match="Blocked DNS resolution"):
        socket.getaddrinfo("example.invalid", 443)


def test_connect_ex_is_blocked() -> None:
    """``connect_ex`` raises instead of returning a platform error code."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(NetworkBlocked, match="Blocked outbound connection"):
            sock.connect_ex(("203.0.113.1", 443))
    finally:
        sock.close()


def test_loopback_is_still_allowed() -> None:
    """Localhost stays reachable so local test servers keep working."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        client.connect(server.getsockname())
    finally:
        client.close()
        server.close()


def test_unix_socket_is_still_allowed() -> None:
    """``AF_UNIX`` filesystem sockets stay allowed for local IPC."""
    with tempfile.TemporaryDirectory(prefix="dh-sock-") as socket_dir:
        path = str(Path(socket_dir) / "guard.sock")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server.bind(path)
            server.listen(1)
            client.connect(path)
        finally:
            client.close()
            server.close()


def test_no_public_allow_network_fixture() -> None:
    """No public ``allow_network`` fixture exists in the fixture registry.

    A subprocess test requests the fixture; the run must fail at fixture
    resolution (``fixture 'allow_network' not found``) rather than silently
    lifting the guard.
    """
    with plugin_root_probe(
        """
        def test_requests_allow_network(allow_network) -> None:  # pragma: no cover
            pass
        """
    ) as probe:
        result = subprocess.run(
            _probe_command(probe),
            capture_output=True,
            text=True,
            cwd=str(_PLUGIN_ROOT),
            env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
            timeout=15,
            check=False,
        )
    assert result.returncode != 0, "allow_network fixture must not exist"
    combined = result.stdout + result.stderr
    assert "allow_network" in combined, combined


def test_double_gate_requires_env_var() -> None:
    """An ``@pytest.mark.e2e`` test without the env var is still blocked.

    The block message must name ``DH_ALLOW_TEST_NETWORK=1`` so the operator
    knows the exact escape hatch.
    """
    with plugin_root_probe(
        """
        import pytest
        import socket

        pytestmark = pytest.mark.e2e

        def test_external_attempt() -> None:
            socket.getaddrinfo("example.invalid", 443)
        """
    ) as probe:
        result = subprocess.run(
            [*_probe_command(probe), "-m", "e2e"],
            capture_output=True,
            text=True,
            cwd=str(_PLUGIN_ROOT),
            env={**os.environ, "DH_ALLOW_TEST_NETWORK": "", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
            timeout=15,
            check=False,
        )
    assert result.returncode != 0, result.stdout
    combined = result.stdout + result.stderr
    assert "DH_ALLOW_TEST_NETWORK=1" in combined, combined
    assert "Blocked DNS resolution" in combined, combined


def test_double_gate_opens_with_env_var() -> None:
    """With both the marker and the env var, the policy gate opens.

    Asserts the guard state flips to allowed via a test-only hook (``_state``)
    rather than contacting any real external service.
    """
    with plugin_root_probe(
        """
        import pytest
        from conftest import _state

        pytestmark = pytest.mark.e2e

        def test_gate_open() -> None:
            assert _state["allowed"] is True, "guard must be lifted under double gate"
        """
    ) as probe:
        result = subprocess.run(
            [*_probe_command(probe), "-m", "e2e"],
            capture_output=True,
            text=True,
            cwd=str(_PLUGIN_ROOT),
            env={**os.environ, "DH_ALLOW_TEST_NETWORK": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
            timeout=15,
            check=False,
        )
    assert result.returncode == 0, result.stdout + result.stderr


def test_guard_restores_sockets_after_session() -> None:
    """After a pytest subprocess finishes, the parent process sockets are intact.

    Runs a trivial pytest session in a subprocess (which installs and tears
    down the guard), then opens a loopback socket in this parent process to
    prove teardown restored the real ``socket.connect``.
    """
    with plugin_root_probe(
        """
        def test_noop() -> None:
            pass
        """
    ) as probe:
        subprocess.run(
            _probe_command(probe),
            capture_output=True,
            text=True,
            cwd=str(_PLUGIN_ROOT),
            env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
            timeout=15,
            check=True,
        )
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        client.connect(server.getsockname())  # parent process: real connect works
    finally:
        client.close()
        server.close()


@pytest.mark.parametrize("testpath", ["tests", "tests_sam", "tests_backlog", "sam_schema/tests"])
def test_guard_covers_testpath(testpath: str) -> None:
    """The root conftest guard applies to every configured testpath.

    Writes a probe test into ``<testpath>`` and invokes pytest against just
    that file from the plugin root. The probe attempts DNS resolution of a
    non-loopback host; the guard must block it with ``NetworkBlocked``
    regardless of which testpath the probe lives in.
    """
    probe_dir = _PLUGIN_ROOT / testpath
    probe = probe_dir / "_guard_path_probe.py"
    probe.write_text(
        textwrap.dedent(
            """
            import socket
            import pytest
            from conftest import NetworkBlocked

            def test_probe() -> None:
                with pytest.raises(NetworkBlocked, match="Blocked DNS resolution"):
                    socket.getaddrinfo("example.invalid", 443)
            """
        ),
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            _probe_command(probe),
            capture_output=True,
            text=True,
            cwd=str(_PLUGIN_ROOT),
            env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
            timeout=30,
            check=False,
        )
    finally:
        probe.unlink(missing_ok=True)
    assert result.returncode == 0, f"guard did not cover {testpath}:\n{result.stdout}\n{result.stderr}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@contextmanager
def plugin_root_probe(body: str) -> Iterator[Path]:
    """Write a temp pytest file under the plugin root and yield its path.

    The probe lives inside the plugin root tree so the root ``conftest.py`` is
    discovered (conftest collection walks ancestors of the test file, not the
    ``--rootdir`` flag alone). The probe is removed on exit so no stray files
    are left in the working tree.
    """
    probe_dir = _PLUGIN_ROOT / ".guard_probes"
    probe_dir.mkdir(exist_ok=True)
    fd, name = tempfile.mkstemp(suffix="_probe_test.py", prefix="guard_", dir=str(probe_dir))
    os.close(fd)
    path = Path(name)
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)
