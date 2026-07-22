"""Import-order regressions for development-harness module boundaries."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_operations_imports_before_server_without_cycle() -> None:
    """The operations-first import order completes in a fresh interpreter."""
    plugin_dir = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-c", "import dh_core.operations; import backlog_core.server"],
        cwd=plugin_dir,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
