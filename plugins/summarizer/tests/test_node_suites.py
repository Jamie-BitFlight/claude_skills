"""Run the plugin's Node hook test suites inside the pytest runner.

``run_pytests.py`` is the plugin's CI test boundary; without this bridge the
``*.cjs`` suites never execute in CI. The hooks themselves require Node, so a
missing ``node`` binary is a failure, not a skip.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent


def test_node_hook_suites_pass() -> None:
    """Every ``tests/*.cjs`` suite passes under ``node --test``."""
    node = shutil.which("node")
    assert node, "node is required to run the summarizer hook suites"
    suites = sorted(str(path) for path in TESTS_DIR.glob("*.cjs"))
    assert suites, "no Node suites found"
    result = subprocess.run(
        [node, "--test", "--test-reporter=tap", *suites], capture_output=True, text=True, timeout=300, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
