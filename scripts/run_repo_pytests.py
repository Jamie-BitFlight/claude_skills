"""Run repository-owned pytest tests from the root development environment."""

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
    """Run repository-owned tests from a stable root.

    Returns:
        The pytest process exit code.
    """
    os.chdir(REPO_ROOT)
    return pytest.main([*(sys.argv[1:] or TEST_PATHS)])


if __name__ == "__main__":
    raise SystemExit(main())
