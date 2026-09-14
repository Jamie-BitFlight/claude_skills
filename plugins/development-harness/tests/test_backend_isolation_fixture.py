"""Contract tests for the autouse ``_isolated_backend`` fixture in ``conftest.py``.

The fixture installs an in-memory backend for every test so no test reaches a
real backend. It is function-scoped, so it runs *after* any higher-scoped
fixture that installs a live backend. E2E tests install ``GitHubBackend`` from a
class-scoped fixture, so without an e2e exemption the in-memory double replaces
it for every e2e test body — ``try_get_github()`` returns ``None`` and
``add_item`` silently produces a local-only item with ``item_ref == ""``
instead of creating a real issue (#3546).

The exemption cannot be observed from inside a test the fixture already
governs, so each test here runs a probe session in a subprocess: a probe file
written under this directory picks up this ``conftest.py`` exactly as a real
test does, and asserts which backend its own test body sees.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_PLUGIN_ROOT = _TESTS_DIR.parent


@contextmanager
def _tests_dir_probe(body: str) -> Iterator[Path]:
    """Write a temp pytest file under the tests directory and yield its path.

    The probe must live beside this file so this directory's ``conftest.py``
    (and its autouse ``_isolated_backend`` fixture) is discovered — conftest
    collection walks the ancestors of the test file itself.
    """
    probe_dir = _TESTS_DIR / ".backend_probes"
    probe_dir.mkdir(exist_ok=True)
    fd, name = tempfile.mkstemp(suffix="_probe_test.py", prefix="backend_", dir=str(probe_dir))
    os.close(fd)
    path = Path(name)
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


def _run_probe(probe: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the probe in its own pytest session with this repo's addopts cleared."""
    return subprocess.run(
        [sys.executable, "-m", "pytest", str(probe), "-q", "-o", "addopts=", "--rootdir", str(_PLUGIN_ROOT), *args],
        capture_output=True,
        text=True,
        cwd=str(_PLUGIN_ROOT),
        env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        timeout=120,
        check=False,
    )


_CLASS_SCOPED_LIVE_BACKEND_PROBE = """
    import pytest
    from backlog_core.backend_protocol import get_config, reset_config, set_config
    from backlog_core.backend_types import BacklogConfig
    from backlog_core.backends.memory_backend import InMemoryBackend


    class SentinelBackend(InMemoryBackend):
        '''Stands in for the live backend an e2e fixture installs.'''


    @pytest.fixture(scope="class")
    def live_backend():
        backend = SentinelBackend()
        set_config(BacklogConfig(backend=backend))
        yield backend
        reset_config()


    class TestProbe:
        {marker}

        def test_first(self, live_backend) -> None:
            assert type(get_config().backend).__name__ == "{expected}"

        def test_second(self, live_backend) -> None:
            assert type(get_config().backend).__name__ == "{expected}"
"""


def test_e2e_test_keeps_the_backend_installed_by_its_own_fixture() -> None:
    """An e2e class keeps its own backend for every test in the class.

    Guards the #3546 regression: the function-scoped autouse fixture must not
    replace the backend a class-scoped e2e fixture installed, and must not
    reset it between tests in that class.
    """
    with _tests_dir_probe(
        _CLASS_SCOPED_LIVE_BACKEND_PROBE.format(marker="pytestmark = pytest.mark.e2e", expected="SentinelBackend")
    ) as probe:
        result = _run_probe(probe, "-m", "e2e")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 passed" in result.stdout, result.stdout + result.stderr


def test_non_e2e_test_gets_the_in_memory_backend() -> None:
    """A non-e2e class still has its backend replaced by the in-memory double."""
    with _tests_dir_probe(
        _CLASS_SCOPED_LIVE_BACKEND_PROBE.format(marker="", expected="ProviderMemoryBackend")
    ) as probe:
        result = _run_probe(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 passed" in result.stdout, result.stdout + result.stderr
