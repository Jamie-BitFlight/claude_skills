# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "cairosvg>=2.9.0",
#   "fastmcp[tasks]==4.0.11",
#   "pydantic>=2.12.5",
#   "pytest>=9.1.1",
#   "pytest-asyncio>=1.4.0",
#   "rich>=14.3.3",
#   "tiktoken>=0.12.0",
# ]
# ///
"""Run the frustration-analyzer plugin's pytest suites under this runner's own configuration."""

from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent
TEST_PATHS = ("tests",)
IMPORT_PATHS = ("tests",)
FAST_MARKER = "not e2e and not cross_backend and not integration and not research_vault"


def main() -> int:
    """Run this plugin's tests with no dependency on a parent directory.

    ``-c os.devnull`` and ``--confcutdir`` keep a parent ``pyproject.toml`` and
    parent ``conftest.py`` files out of the run, so it behaves the same inside the
    monorepo and in a standalone copy. The options that parent config would
    have supplied are set here instead. ``TEST_PATHS`` go to pytest as
    ``testpaths`` and ``FAST_MARKER`` as a leading ``-m``, so a caller's explicit
    paths or ``-m`` replace them (``-m ""`` selects every marker).

    Returns:
        The pytest process exit code.
    """
    os.chdir(PLUGIN_ROOT)
    return pytest.main([
        "-c",
        os.devnull,
        "--rootdir",
        str(PLUGIN_ROOT),
        "--confcutdir",
        str(PLUGIN_ROOT),
        "-o",
        f"testpaths={shlex.join(TEST_PATHS)}",
        "-o",
        f"pythonpath={shlex.join(str(PLUGIN_ROOT / path) for path in IMPORT_PATHS)}",
        "--strict-config",
        "--strict-markers",
        "--import-mode=importlib",
        "--asyncio-mode=auto",
        "-m",
        FAST_MARKER,
        *sys.argv[1:],
    ])


if __name__ == "__main__":
    raise SystemExit(main())
