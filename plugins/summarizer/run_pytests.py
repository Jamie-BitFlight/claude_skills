# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest>=9.1.1",
#   "pytest-asyncio>=1.4.0",
# ]
# ///
"""Run the summarizer plugin's complete pytest boundary."""

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
    return pytest.main(["-c", os.devnull, "--strict-config", "--asyncio-mode=auto", *(sys.argv[1:] or TEST_PATHS)])


if __name__ == "__main__":
    raise SystemExit(main())
