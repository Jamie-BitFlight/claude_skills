"""Drift guard for run_pytest.py's standalone test-path duplication.

``run_pytest.py`` re-declares ``_DEFAULT_TEST_PATHS`` because a standalone bundle has no
parent ``pyproject.toml`` to read ``testpaths`` from (see its module docstring). This test
catches drift between that duplication and the root ``pyproject.toml`` when both are checked
out together — it is skipped for a standalone bundle, which has no root ``pyproject.toml``.
"""

from __future__ import annotations

import importlib.util
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

def test_default_test_paths_are_plugin_owned() -> None:
    """The standalone runner, not root pytest config, owns this plugin's test topology."""
    assert _DEFAULT_TEST_PATHS
    assert all(not path.startswith("plugins/") for path in _DEFAULT_TEST_PATHS)
