# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "cryptography>=48.0.1",
#   "fastmcp[tasks]>=3.2.0",
#   "gitpython>=3.1.0",
#   "httpx>=0.28.1",
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
#   "ruff>=0.16.5",
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

_PLUGIN_ROOT = Path(__file__).resolve().parent
_DEFAULT_TEST_PATHS = [
    "tests",
    "tests_sam",
    "tests_backlog",
    "sam_schema/tests",
    "backlog_core/tests",
    "skills/implementation-manager/scripts",
    "skills/kage-bunshin/tests",
]
_REQUIRED_ARGS = ["--asyncio-mode=auto", "--strict-config"]
_PARALLEL_ARGS = ["-n", "2", "--dist", "loadgroup"]


def _default_parallelism(args: list[str]) -> list[str]:
    """Return the default xdist options unless the caller disabled the xdist plugin.

    The defaults precede the caller's arguments, so an explicit ``-n`` or
    ``--dist`` wins. ``-p no:xdist`` removes the ``-n`` option itself, so the
    defaults are dropped rather than rejected as unknown arguments.

    Returns:
        The xdist options to prepend, or an empty list.
    """
    return [] if any("no:xdist" in arg for arg in args) else _PARALLEL_ARGS


def main() -> int:
    """Run the plugin test suites from the bundle root and forward arguments.

    ``-c os.devnull`` keeps a parent ``pyproject.toml`` from configuring the
    run, so the suite behaves the same inside the monorepo and in a standalone
    bundle. Without that config, ``asyncio_mode = "auto"`` must be passed here
    or pytest's strict default would silently skip this plugin's
    intentionally-undecorated async tests. ``--strict-config`` turns invalid or
    unavailable pytest configuration into a hard failure instead of a silently
    degraded warning. The default suites go to pytest as ``testpaths`` so an
    option-only invocation (``-m``, ``--collect-only``) still collects only
    them, while explicit path arguments override them. Tests run on two xdist
    workers with ``loadgroup`` distribution by default, matching the monorepo's
    root configuration; see ``_default_parallelism`` for overriding it.

    Returns:
        The pytest process exit code.
    """
    os.chdir(_PLUGIN_ROOT)
    return pytest.main([
        "-c",
        os.devnull,
        "--rootdir",
        str(_PLUGIN_ROOT),
        "-o",
        f"testpaths={' '.join(_DEFAULT_TEST_PATHS)}",
        *_REQUIRED_ARGS,
        *_default_parallelism(sys.argv[1:]),
        *sys.argv[1:],
    ])


if __name__ == "__main__":
    raise SystemExit(main())
