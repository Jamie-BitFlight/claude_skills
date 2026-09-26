"""Contract for development-harness's standalone pytest boundary."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_RUN_PYTEST_PATH = Path(__file__).parent.parent / "run_pytests.py"
_spec = importlib.util.spec_from_file_location("run_pytests", _RUN_PYTEST_PATH)
assert _spec is not None
assert _spec.loader is not None
_run_pytest_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_run_pytest_mod)

_DEFAULT_TEST_PATHS = _run_pytest_mod._DEFAULT_TEST_PATHS
_PLUGIN_ROOT = _run_pytest_mod._PLUGIN_ROOT


def test_default_test_paths_are_plugin_owned() -> None:
    """The root plugin runner owns complete plugin-relative test topology."""
    assert Path(__file__).parent.parent == _PLUGIN_ROOT
    assert _DEFAULT_TEST_PATHS
    assert all(not path.startswith("plugins/") for path in _DEFAULT_TEST_PATHS)
