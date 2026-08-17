#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "fastmcp>=3.0.2",
#   "gitpython>=3.1.0",
#   "markdown-it-py>=3.0.0",
#   "marko>=2.0.0",
#   "pydantic>=2.12.3",
#   "pygithub>=2.8.1",
#   "ruamel.yaml>=0.18.0",
#   "tiktoken>=0.12.0",
#   "typer>=0.21.2",
# ]
# ///
"""PEP 723 wrapper for the SAM CLI."""

from __future__ import annotations

import sys
from pathlib import Path

_plugin_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_plugin_root))

from sam_schema.cli import app

app()
