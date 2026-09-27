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
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest
import tiktoken

from tests.network_blocked import NetworkBlocked

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def _load_runner() -> ModuleType:
    """Load this plugin's ``run_pytests.py``, which ships with the plugin."""
    spec = spec_from_file_location("dh_run_pytests", _PLUGIN_ROOT / "run_pytests.py")
    assert spec is not None
    assert spec.loader is not None
    runner = module_from_spec(spec)
    spec.loader.exec_module(runner)
    return runner


_RUNNER = _load_runner()

# A hang guard for the subprocess probes, not a performance bound: each probe
# starts a fresh interpreter that imports the plugin conftest, which takes
# seconds on an idle machine and far longer on a loaded CI runner.
_PROBE_TIMEOUT = 120


def _configured_testpaths() -> list[str]:
    """Return the test roots this plugin's ``run_pytests.py`` declares.

    Reading the runner rather than listing the roots keeps the guard covering every
    directory the plugin's suite collects, including ones added after this test was
    written.
    """
    return list(_RUNNER.TEST_PATHS)


def _probe_command(probe: Path, *args: str) -> list[str]:
    """Build a probe run with the runner's own isolated options.

    Returns:
        The argv for a pytest subprocess that collects only *probe*.
    """
    return [
        sys.executable,
        "-m",
        "pytest",
        *_RUNNER.isolated_options(),
        "-p",
        "no:cacheprovider",
        str(probe),
        "-q",
        *args,
    ]


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


def test_no_public_allow_network_fixture(request: pytest.FixtureRequest) -> None:
    """No public ``allow_network`` fixture exists in the fixture registry.

    Requesting it must fail at fixture resolution rather than silently lifting
    the guard.
    """
    with pytest.raises(pytest.FixtureLookupError, match="allow_network"):
        request.getfixturevalue("allow_network")


@pytest.mark.integration
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
            env={**os.environ, "DH_ALLOW_TEST_NETWORK": ""},
            timeout=_PROBE_TIMEOUT,
            check=False,
        )
    assert result.returncode != 0, result.stdout
    combined = result.stdout + result.stderr
    assert "DH_ALLOW_TEST_NETWORK=1" in combined, combined
    assert "Blocked DNS resolution" in combined, combined


@pytest.mark.integration
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
            env={**os.environ, "DH_ALLOW_TEST_NETWORK": "1"},
            timeout=_PROBE_TIMEOUT,
            check=False,
        )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.integration
def test_double_gate_stays_open_through_class_scoped_teardown() -> None:
    """The gate stays open while a class-scoped e2e fixture tears down.

    A class-scoped fixture finalises after every function-scoped fixture of the
    last test in the class. Computing the policy in a function-scoped fixture
    re-armed the guard before that point, so an e2e fixture that cleans up the
    GitHub issues its tests created died on the guard (#3546). Asserts the
    state via the test-only ``_state`` hook, contacting no external service.
    """
    with plugin_root_probe(
        """
        import pytest
        from conftest import _state

        pytestmark = pytest.mark.e2e

        @pytest.fixture(scope="class")
        def class_fixture():
            yield
            assert _state["allowed"] is True, "guard must stay lifted during class teardown"


        class TestProbe:
            def test_one(self, class_fixture) -> None:
                assert _state["allowed"] is True

            def test_two(self, class_fixture) -> None:
                assert _state["allowed"] is True
        """
    ) as probe:
        result = subprocess.run(
            [*_probe_command(probe), "-m", "e2e"],
            capture_output=True,
            text=True,
            cwd=str(_PLUGIN_ROOT),
            env={**os.environ, "DH_ALLOW_TEST_NETWORK": "1"},
            timeout=_PROBE_TIMEOUT,
            check=False,
        )
    assert result.returncode == 0, result.stdout + result.stderr


def test_guard_restores_sockets_after_session(pytestconfig: pytest.Config) -> None:
    """Removing the guard restores the real socket functions, and installing re-arms them.

    ``pytest_unconfigure`` removes the guard through ``remove_network_guard``. This
    calls that function and ``install_network_guard`` in-process. The guard is per
    process, so under xdist this touches only the current worker, and the
    ``finally`` re-arms it for the tests after. The tiktoken fallback has its own
    patch, so it must survive the round trip.
    """
    guard = next(
        plugin
        for plugin in pytestconfig.pluginmanager.get_plugins()
        if Path(getattr(plugin, "__file__", "") or "").resolve() == _PLUGIN_ROOT / "conftest.py"
    )
    armed = (socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo)
    assert armed == (guard._guarded_connect, guard._guarded_connect_ex, guard._guarded_getaddrinfo)
    get_encoding = tiktoken.get_encoding
    guard.remove_network_guard()
    try:
        restored = (socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo)
        assert restored == (guard._real_connect, guard._real_connect_ex, guard._real_getaddrinfo)
    finally:
        guard.install_network_guard()
    assert (socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo) == armed
    assert tiktoken.get_encoding is get_encoding


@pytest.mark.integration
@pytest.mark.parametrize("testpath", _configured_testpaths())
def test_guard_covers_testpath(testpath: str) -> None:
    """The root conftest guard applies to every configured testpath.

    Writes a probe test into ``<testpath>`` and invokes pytest against just
    that file from the plugin root. The probe attempts DNS resolution of a
    non-loopback host; the guard must block it with ``NetworkBlocked``
    regardless of which testpath the probe lives in.
    """
    probe_dir = _PLUGIN_ROOT / testpath
    probe = probe_dir / "test_guard_path_probe.py"
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
            timeout=_PROBE_TIMEOUT,
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
    fd, name = tempfile.mkstemp(suffix=".py", prefix="test_guard_probe_", dir=str(probe_dir))
    os.close(fd)
    path = Path(name)
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)
