"""Guard that every test file on disk is reachable from root ``testpaths``.

CI's default lane is a bare ``uv run pytest``, which collects only the directories
listed in ``[tool.pytest.ini_options] testpaths``. A test file outside every one of
those directories never runs anywhere and reports no failure while it rots.

Both sides of the comparison are derived, not transcribed: the directories come from
``pyproject.toml``, the filename patterns from the live pytest config, and the file
set from ``git ls-files``. A marker-gated file (``e2e``, ``integration``,
``cross_backend``, ``research_vault``) needs no exclusion here — it still lives inside
a ``testpaths`` directory and its dedicated CI job selects it by marker.
"""

from __future__ import annotations

import fnmatch
import subprocess
import tomllib
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Paths that are deliberately not this repository's tests. Each entry is a prefix
# relative to the repository root and must state why collecting it would be wrong.
_NOT_OUR_TESTS = {
    # Deliberately flawed sample project that the test-reviewer eval feeds to an
    # agent as input. It carries its own pytest.ini and relative imports, and its
    # tests are the artefact under review, not assertions about this repository.
    "plugins/development-harness/skills/test-reviewer/evals/fixtures/": (
        "test-reviewer eval input fixture, reviewed as data rather than executed"
    )
}


def _tracked_test_files(patterns: list[str]) -> set[str]:
    """Return repository-relative paths of tracked files matching pytest's ``python_files``."""
    tracked = subprocess.run(
        ["git", "ls-files", "-z", "*.py"], cwd=_REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.split("\0")
    return {path for path in tracked if path and any(fnmatch.fnmatch(Path(path).name, pattern) for pattern in patterns)}


def test_every_test_file_is_inside_a_configured_testpath(pytestconfig: pytest.Config) -> None:
    """Each tracked test file sits under a ``testpaths`` entry or an explained exclusion."""
    testpaths = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["pytest"][
        "ini_options"
    ]["testpaths"]
    collected_roots = tuple(f"{entry.rstrip('/')}/" for entry in testpaths)

    unreachable = sorted(
        path
        for path in _tracked_test_files(pytestconfig.getini("python_files"))
        if not path.startswith(collected_roots) and not path.startswith(tuple(_NOT_OUR_TESTS))
    )

    assert not unreachable, (
        "These test files are outside every pyproject.toml testpaths entry, so the default "
        "pytest lane never collects them. Add the owning directory to testpaths, or add the "
        f"path to _NOT_OUR_TESTS with the reason it is not a test: {unreachable}"
    )


def test_no_stale_exclusions(pytestconfig: pytest.Config) -> None:
    """Every ``_NOT_OUR_TESTS`` prefix still shelters at least one test file."""
    test_files = _tracked_test_files(pytestconfig.getini("python_files"))
    unused = sorted(prefix for prefix in _NOT_OUR_TESTS if not any(path.startswith(prefix) for path in test_files))

    assert not unused, f"Exclusions no longer match any test file and should be deleted: {unused}"
