#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "fastmcp>=3.0.2",
#   "gitpython>=3.1.0",
#   "httpx>=0.28.1",
#   "markdown-it-py>=3.0.0",
#   "marko>=2.0.0",
#   "pydantic>=2.12.3",
#   "pygithub>=2.8.1",
#   "ruamel.yaml>=0.18.0",
#   "tiktoken>=0.12.0",
#   "typer>=0.21.2",
# ]
#
# [tool.ty.environment]
# extra-paths = [".."]
# ///
"""PEP 723 wrapper for the SAM CLI."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Same guard as ``sam_schema/cli.py`` (see its comment for why an inherited PYTHONPATH must go),
# repeated here because it has to run *before* the package import below: ``sam_schema/__init__``
# reaches pydantic, so a foreign copy on PYTHONPATH raises inside the package and cli.py's own
# module body never executes. This wrapper is the entry point the implementation-manager
# task_status_hook invokes, so this is the path that has to survive. Keep ``_RELOADED`` in sync.
_RELOADED = "DH_CLI_PYTHONPATH_CLEARED"
if __name__ == "__main__" and os.environ.get("PYTHONPATH") and not os.environ.get(_RELOADED):
    _clean_env = dict(os.environ)
    _clean_env.pop("PYTHONPATH", None)
    _clean_env[_RELOADED] = "1"
    os.execve(sys.executable, [sys.executable, *sys.argv], _clean_env)

_plugin_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_plugin_root))

from scripts.tls_compat import relax_verify_x509_strict

relax_verify_x509_strict()

from sam_schema.cli import app

app()
