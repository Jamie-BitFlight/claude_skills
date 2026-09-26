# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "markdown-it-py>=4.0.0",
#   "pytest>=9.1.1",
#   "pytest-asyncio>=1.4.0",
# ]
# ///
"""Run the holistic-linting plugin's complete pytest boundary."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent
TEST_PATHS = ("tests",)


def main() -> int:
    """Run this plugin's tests without relying on repository pytest discovery.

    Returns:
        The pytest process exit code.
    """
    os.chdir(PLUGIN_ROOT)
    return pytest.main([
        "-c",
        os.devnull,
        "--rootdir",
        str(PLUGIN_ROOT),
        "-o",
        f"testpaths={' '.join(TEST_PATHS)}",
        "--strict-config",
        "--asyncio-mode=auto",
        *sys.argv[1:],
    ])


if __name__ == "__main__":
    raise SystemExit(main())
