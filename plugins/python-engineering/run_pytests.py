# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "anthropic>=0.89.0",
#   "cairosvg>=2.9.0",
#   "defusedxml>=0.7.1",
#   "duckdb>=1.5.5",
#   "fastmcp[tasks]>=4.0.0",
#   "gitpython>=3.1.58",
#   "httpx>=0.28.1",
#   "hypothesis>=6.164.0",
#   "markdown-it-py>=4.0.0",
#   "marko>=2.2.2",
#   "mcp[cli]>=1.27.0",
#   "prefixspan>=0.5.2",
#   "pydantic>=2.12.5",
#   "pygithub>=2.9.0",
#   "pytest-mock>=3.15.1",
#   "pytest>=9.1.1",
#   "pytest-asyncio>=1.4.0",
#   "pytest-cov>=7.1.0",
#   "pytest-xdist>=3.8.0",
#   "python-frontmatter>=1.3.0",
#   "rich>=14.3.3",
#   "ruamel-yaml>=0.19.1",
#   "tiktoken>=0.12.0",
#   "tomlkit>=0.15.1",
#   "typer>=0.27.0",
# ]
# ///
"""Run python-engineering plugin pytest suites without a plugin-local project."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent
TEST_PATHS = (
    "scripts",
)


def main() -> int:
    """Run this plugin's complete configured pytest boundary.

    Returns:
        The pytest process exit code.
    """
    os.chdir(PLUGIN_ROOT)
    return pytest.main(["-c", os.devnull, "--strict-config", "--asyncio-mode=auto", *(sys.argv[1:] or TEST_PATHS)])


if __name__ == "__main__":
    raise SystemExit(main())
