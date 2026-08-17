#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "cryptography>=48.0.1",
#   "fastmcp[tasks]>=3.2.0",
#   "gitpython>=3.1.0",
#   "hypothesis>=6.0.0",
#   "markdown-it-py>=3.0.0",
#   "marko>=2.2.2",
#   "pygments>=2.20.0",
#   "pygithub>=2.8.1",
#   "pydantic>=2.12.3",
#   "pytest-asyncio>=1.1.0",
#   "pytest-cov>=6.2.1",
#   "pytest-mock>=3.12",
#   "pytest-xdist>=3.5.0",
#   "pytest>=8.4.1",
#   "ruamel.yaml>=0.18.0",
#   "tiktoken>=0.12.0",
#   "tomlkit>=0.13.0",
#   "typer>=0.21.0",
# ]
# ///
"""Run development-harness tests without a plugin-local project environment."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_TEST_PATHS = ["tests", "tests_sam", "sam_schema/tests", "backlog_core/tests"]
_REQUIRED_ARGS = ["--asyncio-mode=auto", "--strict-config"]


def main() -> int:
    """Run the plugin test suites from the bundle root and forward arguments.

    A standalone bundle has no parent ``pyproject.toml`` to supply
    ``asyncio_mode = "auto"``, so pytest's strict default would silently skip
    this repo's intentionally-undecorated async tests. ``--strict-config``
    turns invalid or unavailable pytest configuration into a hard failure
    instead of a silently degraded warning.

    Returns:
        The pytest process exit code.
    """
    os.chdir(_PLUGIN_ROOT)
    args = sys.argv[1:] or _DEFAULT_TEST_PATHS
    return pytest.main([*_REQUIRED_ARGS, *args])


if __name__ == "__main__":
    raise SystemExit(main())
