"""Regression coverage for acyclic backlog backend imports."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_PLUGIN_DIR = Path(__file__).parents[1]
_BACKEND_NAMES = ("github", "memory", "sqlite", "beads")
_IMPORT_ORDERS = (
    "import backlog_core.backend_protocol\nimport backlog_core.backends.github_backend",
    "import backlog_core.backends.github_backend\nimport backlog_core.backend_protocol",
)


@pytest.mark.unit
@pytest.mark.parametrize("imports", _IMPORT_ORDERS)
def test_backend_factory_import_order(imports: str) -> None:
    """Both import orders construct every backend and satisfy the contract."""
    script = f"""
{imports}
from backlog_core.backend_protocol import BacklogBackend, create_backend

for name, expected in {dict(zip(_BACKEND_NAMES, ("GitHubBackend", "InMemoryBackend", "SQLiteBackend", "BeadsBackend"), strict=False)).__repr__()}.items():
    backend = create_backend(name)
    assert type(backend).__name__ == expected
    assert isinstance(backend, BacklogBackend)
"""
    env = os.environ | {"PYTHONPATH": str(_PLUGIN_DIR)}
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, check=False, env=env, text=True)

    assert result.returncode == 0, result.stderr
