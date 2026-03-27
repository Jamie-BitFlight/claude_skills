#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "fastmcp[tasks]>=3.0.2",
#   "gitpython>=3.1.0",
#   "pygithub>=2.8.1",
#   "pydantic>=2.12.3",
#   "python-frontmatter>=1.1.0",
#   "ruamel.yaml>=0.18.0",
#   "tiktoken>=0.12.0",
#   "typer>=0.21.2",
# ]
# ///
"""PEP 723 wrapper for the backlog MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
_plugin_root = _scripts_dir.parent
# Scripts first for dh_mcp_preinit; plugin root second for backlog_core.
sys.path.insert(0, str(_plugin_root))
sys.path.insert(0, str(_scripts_dir))

from dh_mcp_preinit import apply_project_dir_from_argv

apply_project_dir_from_argv()

from backlog_core.server import mcp

mcp.run()
