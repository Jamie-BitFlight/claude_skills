"""Shared fixtures for the knowledge_explorer test suite."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).parents[2] / "research" / "knowledge-explorer.py"


@pytest.fixture(scope="session")
def ke():
    """Import knowledge-explorer.py as a module.

    The file has a hyphenated name, so it cannot be imported with a plain
    `import` statement -- load it via importlib and register it in
    sys.modules before exec so its @dataclass decorators can resolve
    `cls.__module__` during class body evaluation.
    """
    if "knowledge_explorer" in sys.modules:
        return sys.modules["knowledge_explorer"]
    spec = importlib.util.spec_from_file_location("knowledge_explorer", _MODULE_PATH)
    if spec is None or spec.loader is None:
        msg = f"Could not build a module spec for {_MODULE_PATH}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules["knowledge_explorer"] = module
    spec.loader.exec_module(module)
    return module
