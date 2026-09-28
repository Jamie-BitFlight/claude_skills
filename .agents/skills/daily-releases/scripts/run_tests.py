#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "daily-releases-lib",
#   "pytest>=8.0.0",
#   "typer>=0.21.0",
#   "PyGithub>=2.1.1",
#   "python-dotenv>=1.0.0",
# ]
#
# [tool.uv.sources]
# daily-releases-lib = { path = "daily_releases_lib", editable = true }
# ///
"""Run the tests bundled with the daily-releases skill."""

from __future__ import annotations

from pathlib import Path

import pytest

TEST_PATHS = (".",)

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    raise SystemExit(
        pytest.main(["-q", "-c", str(script_dir / "pytest.ini"), *(str(script_dir / path) for path in TEST_PATHS)])
    )
