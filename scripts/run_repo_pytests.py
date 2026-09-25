#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest>=9.1.1",
#   "pytest-asyncio>=1.4.0",
#   "pytest-cov>=7.1.0",
#   "pytest-mock>=3.15.1",
#   "pytest-xdist>=3.8.0",
# ]
# ///
"""Run repository-owned pytest tests, excluding plugin-owned suites."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TEST_PATHS = (
    "tests",
    "examples/solid-review-ab/tests",
    ".claude/skills/gh/scripts",
    ".claude/skills/gh/tests",
    ".agents/skills/receiving-pr-reviews/scripts",
)


def main() -> int:
    """Run repository-owned tests from a stable root."""
    os.chdir(REPO_ROOT)
    return pytest.main([*(sys.argv[1:] or TEST_PATHS)])


if __name__ == "__main__":
    raise SystemExit(main())
