# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "cryptography>=50.0.0",
#   "fastmcp[tasks]==4.1.0",
#   "gitpython>=3.1.59",
#   "httpx>=0.28.1",
#   "hypothesis>=6.0.0",
#   "markdown-it-py>=3.0.0",
#   "marko>=2.2.2",
#   "pygithub>=2.8.1",
#   "pydantic>=2.12.3",
#   "pytest-asyncio>=1.1.0",
#   "pytest-mock>=3.12",
#   "pytest-xdist>=3.5.0",
#   "pytest>=8.4.1",
#   "ruamel.yaml>=0.18.0",
#   "ruff>=0.16.5",
#   "tiktoken>=0.12.0",
#   "typer>=0.21.0",
# ]
# ///
"""Run the development-harness plugin's pytest suites under this runner's own configuration."""

from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent
TEST_PATHS = (
    "tests",
    "tests_sam",
    "tests_backlog",
    "sam_schema/tests",
    "backlog_core/tests",
    "skills/implementation-manager/scripts",
    "skills/kage-bunshin/tests",
)
IMPORT_PATHS = (".", "scripts", "skills/implementation-manager/scripts")
FAST_MARKER = "not e2e and not cross_backend and not integration and not research_vault"
# CI lanes beyond the fast default, each run as this runner plus the lane's marker.
LANES = {"integration": "integration and not research_vault", "cross_backend": "cross_backend"}
PARALLEL_ARGS = ("-n", "2", "--dist", "loadgroup")


def default_parallelism(args: list[str]) -> list[str]:
    """Return the default xdist options unless the caller disabled the xdist plugin.

    The defaults precede the caller's arguments, so an explicit ``-n`` or
    ``--dist`` wins. ``-p no:xdist`` removes the ``-n`` option itself, so the
    defaults are dropped rather than rejected as unknown arguments.

    Returns:
        The xdist options to prepend, or an empty list.
    """
    return [] if any("no:xdist" in arg for arg in args) else list(PARALLEL_ARGS)


def isolated_options() -> list[str]:
    """Return the options that replace parent pytest configuration for this plugin.

    ``-c os.devnull`` and ``--confcutdir`` keep a parent ``pyproject.toml`` and
    parent ``conftest.py`` files out of the run, so it behaves the same inside the
    monorepo and in a standalone copy. The options that parent config would
    have supplied are set here instead. ``TEST_PATHS`` go to pytest as
    ``testpaths``, so a caller's explicit paths replace them. Tests that start
    their own pytest subprocess reuse this list, so it cannot drift from the runner.

    Returns:
        The pytest options, without marker selection or parallelism.
    """
    return [
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
    ]


def main() -> int:
    """Run this plugin's tests with no dependency on a parent directory.

    ``FAST_MARKER`` goes to pytest as a leading ``-m``, so a caller's explicit
    ``-m`` replaces it (``-m ""`` selects every marker).

    Returns:
        The pytest process exit code.
    """
    os.chdir(PLUGIN_ROOT)
    return pytest.main([*isolated_options(), "-m", FAST_MARKER, *default_parallelism(sys.argv[1:]), *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
