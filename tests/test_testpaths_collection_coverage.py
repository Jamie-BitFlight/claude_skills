"""Guard that the declared test roots and the test files on disk stay in agreement.

Two authorities declare test roots. Root ``testpaths`` covers repository-owned tests,
collected by a bare ``uv run pytest``. Each ``plugins/<name>/run_pytests.py`` declares
its plugin's roots in a literal ``TEST_PATHS`` constant, collected by that runner. A test
file outside every root never runs anywhere and reports no failure while it rots; a root
naming a directory that no longer exists collects nothing while looking like coverage.
Both directions are checked here.

Every input is derived, never transcribed. Root ``testpaths`` and ``python_files`` come
from the live pytest config, the values a bare run obeys. Runner roots come from each
runner's ``TEST_PATHS``. A file inside a plugin that has a runner is classified with
pytest's default ``python_files``, because runners pass ``-c os.devnull`` and set no
``python_files`` of their own. The file set comes from ``git ls-files``.

A marker-gated file (``e2e``, ``integration``, ``cross_backend``, ``research_vault``)
needs no exclusion: it still lives inside a ``testpaths`` directory, and its dedicated CI
job selects it by marker.

Scope: only files tracked by git are checked. An untracked test file is invisible to
this guard, which is correct rather than a gap — CI collects from a fresh clone, so a
file git does not carry cannot run there either. If ``git`` is unavailable the discovery
subprocess raises and these tests error out; they never pass for want of evidence.
"""

from __future__ import annotations

import ast
import fnmatch
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent

# This module's own repository-relative path. Discovery that cannot find the guard
# itself is broken, and an empty result from broken discovery must not read as "clean".
_THIS_FILE = "tests/test_testpaths_collection_coverage.py"

# Specific files that are deliberately not this repository's tests, each mapped to the
# reason collecting it would be wrong. Keys are exact file paths, never directory
# prefixes: a prefix would shelter every file later added beneath it, silently skipping
# a genuine test someone drops into that tree.
# pytest's own ``python_files`` default, which applies under every plugin runner: runners
# pass ``-c os.devnull`` and no ``python_files`` override (the runner contract test checks
# that no runner sets one).
_RUNNER_PYTHON_FILES = ("test_*.py", "*_test.py")

_NOT_OUR_TESTS = {
    "plugins/development-harness/skills/test-reviewer/evals/fixtures/review_project/test_app.py": (
        "deliberately flawed sample project that the test-reviewer eval reviews as data; "
        "carries its own pytest.ini and package-relative imports"
    )
}


def unreachable_test_files(
    testpaths: Iterable[str], test_files: Iterable[str], exclusions: Mapping[str, str] | Iterable[str]
) -> list[str]:
    """Return the test files that no ``testpaths`` entry would collect.

    Pure and I/O-free so the fault case can be exercised over synthetic inputs.

    Args:
        testpaths: Directory entries as configured, with or without a trailing slash.
        test_files: Repository-relative test file paths.
        exclusions: Exact file paths that are deliberately not tests.

    Returns:
        Sorted paths that fall under no entry and are not excluded.
    """
    # The trailing slash is load-bearing: a bare ``startswith("tests")`` would treat
    # ``tests_backlog/`` as living inside ``tests/``, which is how 635 tests stayed
    # uncollected while looking covered.
    roots = tuple(f"{entry.rstrip('/')}/" for entry in testpaths)
    excluded = set(exclusions)
    return sorted(path for path in test_files if path not in excluded and not path.startswith(roots))


def _runner_plugins() -> tuple[str, ...]:
    """Return the repository-relative directories of plugins that own a runner, with a trailing slash."""
    return tuple(f"{runner.parent.relative_to(_REPO_ROOT).as_posix()}/" for runner in _runners())


def _runners() -> list[Path]:
    return sorted((_REPO_ROOT / "plugins").glob("*/run_pytests.py"))


def _tracked_test_files(root_patterns: Iterable[str]) -> set[str]:
    """Return tracked files that the collector owning their location would treat as tests.

    Files inside a plugin with a runner match pytest's default ``python_files``; every
    other file matches the root ``python_files``.
    """
    tracked = subprocess.run(
        ["git", "ls-files", "-z", "*.py"], cwd=_REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.split("\0")
    root_patterns = tuple(root_patterns)
    plugins = _runner_plugins()

    def is_test(path: str) -> bool:
        patterns = _RUNNER_PYTHON_FILES if path.startswith(plugins) else root_patterns
        return any(fnmatch.fnmatch(Path(path).name, pat) for pat in patterns)

    return {path for path in tracked if path and is_test(path)}


def _plugin_runner_testpaths() -> list[str]:
    """Return plugin test roots declared by each runner's module-level literal ``TEST_PATHS``."""
    roots: list[str] = []
    for runner in _runners():
        tree = ast.parse(runner.read_text(encoding="utf-8"), filename=str(runner))
        value = next(
            (
                node.value
                for node in tree.body
                if (
                    isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "TEST_PATHS" for t in node.targets)
                )
                or (
                    isinstance(node, ast.AnnAssign)
                    and isinstance(node.target, ast.Name)
                    and node.target.id == "TEST_PATHS"
                )
            ),
            None,
        )
        assert value is not None, f"{runner.relative_to(_REPO_ROOT)} has no literal TEST_PATHS"
        values = ast.literal_eval(value)
        assert isinstance(values, (list, tuple))
        assert values
        plugin = runner.parent.relative_to(_REPO_ROOT)
        roots.extend((plugin / value).as_posix() for value in values)
    return roots


def _derived_inputs(config: pytest.Config) -> tuple[list[str], set[str]]:
    """Return all authoritative test roots and tracked test files, proven usable first.

    Guards against the vacuous pass: if either input came back empty, every comparison
    below would succeed while having examined nothing. "All clear" and "I could not
    look" must not produce the same verdict.
    """
    testpaths = [*config.getini("testpaths"), *_plugin_runner_testpaths()]
    patterns = list(config.getini("python_files"))
    assert testpaths, "pytest and plugin runners report no test roots, so nothing here can judge collection coverage"
    assert patterns, "pytest reports no python_files patterns, so no file can be recognised as a test"

    test_files = _tracked_test_files(patterns)
    assert _THIS_FILE in test_files, (
        f"discovery did not find this guard's own file ({_THIS_FILE}) among {len(test_files)} "
        "tracked test files, so an empty result would mean discovery is broken, not that "
        "coverage is complete"
    )
    return testpaths, test_files


def test_every_test_file_is_inside_a_configured_testpath(pytestconfig: pytest.Config) -> None:
    """Each tracked test file sits under a repo testpath or plugin runner root, or an explained exclusion."""
    testpaths, test_files = _derived_inputs(pytestconfig)

    unreachable = unreachable_test_files(testpaths, test_files, _NOT_OUR_TESTS)

    assert not unreachable, (
        "These test files are outside every repository testpaths entry and every plugin "
        "runner's test roots, so no CI lane collects them. Add the owning directory to its "
        "plugin's run_pytests.py (or, for a repository-owned test, to root testpaths), or add "
        f"the exact path to _NOT_OUR_TESTS with the reason it is not a test: {unreachable}"
    )


def test_every_configured_testpath_exists(pytestconfig: pytest.Config) -> None:
    """No ``testpaths`` entry names a directory that is gone.

    An entry left behind after its directory is deleted collects nothing in silence and
    reads as coverage that does not exist. This repo has shipped that state before.
    """
    testpaths, _ = _derived_inputs(pytestconfig)

    missing = sorted(entry for entry in testpaths if not (_REPO_ROOT / entry).is_dir())

    assert not missing, (
        "These testpaths entries do not resolve to a directory, so they contribute no "
        f"tests while appearing to: {missing}"
    )


def test_exclusions_name_existing_test_files_and_state_a_reason(pytestconfig: pytest.Config) -> None:
    """Each ``_NOT_OUR_TESTS`` key is a real tracked test file carrying a stated reason.

    Requiring an exact, currently-present path is what keeps the exclusion list from
    decaying into a directory sweep, and forces a reason to be written rather than
    merely invited by a comment.
    """
    _, test_files = _derived_inputs(pytestconfig)

    unknown = sorted(path for path in _NOT_OUR_TESTS if path not in test_files)
    reasonless = sorted(path for path, reason in _NOT_OUR_TESTS.items() if not reason.strip())

    assert not unknown, (
        "These exclusions do not name a tracked test file — delete the stale entry, or "
        f"replace a directory prefix with the exact paths it was covering: {unknown}"
    )
    assert not reasonless, f"These exclusions state no reason for being excluded: {reasonless}"


@pytest.mark.parametrize(
    ("testpaths", "test_files", "expected"),
    [
        pytest.param(["tests"], {"tests/test_a.py"}, [], id="directly-inside-an-entry"),
        pytest.param(["tests"], {"tests/nested/deep/test_a.py"}, [], id="nested-below-an-entry"),
        pytest.param(["tests/"], {"tests/test_a.py"}, [], id="entry-with-trailing-slash"),
        pytest.param(["tests"], {"elsewhere/test_a.py"}, ["elsewhere/test_a.py"], id="outside-every-entry"),
        # The exact prefix confusion that hid 635 tests: tests_backlog/ is a sibling of
        # tests/, not a child, so an entry of "tests" must not swallow it.
        pytest.param(
            ["tests"],
            {"tests_backlog/test_a.py"},
            ["tests_backlog/test_a.py"],
            id="sibling-sharing-an-entry-name-prefix",
        ),
        pytest.param(
            ["tests"],
            {"tests/test_a.py", "a/test_b.py", "b/test_c.py"},
            ["a/test_b.py", "b/test_c.py"],
            id="reports-every-uncovered-file-sorted",
        ),
    ],
)
def test_unreachable_test_files_reports_the_fault_cases(
    testpaths: list[str], test_files: set[str], expected: list[str]
) -> None:
    """The decision function flags uncollected files instead of returning nothing."""
    assert unreachable_test_files(testpaths, test_files, {}) == expected


def test_unreachable_test_files_honours_exclusions() -> None:
    """An excluded path is not reported even though no entry covers it."""
    assert unreachable_test_files(["tests"], {"elsewhere/test_a.py"}, {"elsewhere/test_a.py": "why"}) == []
