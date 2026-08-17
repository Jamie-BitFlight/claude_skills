"""Drift guard for run_pytest.py's standalone test-path duplication.

``run_pytest.py`` re-declares ``_DEFAULT_TEST_PATHS`` because a standalone bundle has no
parent ``pyproject.toml`` to read ``testpaths`` from (see its module docstring). This test
catches drift between that duplication and the root ``pyproject.toml`` when both are checked
out together — it is skipped for a standalone bundle, which has no root ``pyproject.toml``.
"""

from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path

import pytest

# run_pytest.py is a standalone PEP 723 script, not a package member — load it directly
# from its sibling path rather than relying on pythonpath registration.
_RUN_PYTEST_PATH = Path(__file__).parent / "run_pytest.py"
_spec = importlib.util.spec_from_file_location("run_pytest", _RUN_PYTEST_PATH)
assert _spec is not None
assert _spec.loader is not None
_run_pytest_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_run_pytest_mod)

_DEFAULT_TEST_PATHS = _run_pytest_mod._DEFAULT_TEST_PATHS
_PLUGIN_ROOT = _run_pytest_mod._PLUGIN_ROOT

_ROOT_PYPROJECT = _PLUGIN_ROOT.parent.parent / "pyproject.toml"


@pytest.mark.skipif(not _ROOT_PYPROJECT.exists(), reason="standalone bundle has no root pyproject.toml")
def test_default_test_paths_match_pyproject_testpaths() -> None:
    """This plugin's *existing* entries in root ``testpaths`` must equal ``_DEFAULT_TEST_PATHS``.

    A ``testpaths`` entry whose directory does not exist (dead config, unrelated to this
    guard) is excluded from the comparison rather than forcing a false failure here.
    """
    repo_root = _ROOT_PYPROJECT.parent
    testpaths = tomllib.loads(_ROOT_PYPROJECT.read_text())["tool"]["pytest"]["ini_options"]["testpaths"]
    plugin_prefix = "plugins/development-harness/"
    plugin_testpaths = {
        path.removeprefix(plugin_prefix)
        for path in testpaths
        if path.startswith(plugin_prefix) and (repo_root / path).is_dir()
    }
    assert set(_DEFAULT_TEST_PATHS) == plugin_testpaths
