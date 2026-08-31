"""Shared MCP entrypoint pre-init: runs before any ``fastmcp``-importing module.

``backlog_core.models`` resolves the repo root at import time.  Parsing
``--project-dir`` here and setting ``DH_PROJECT_ROOT`` ensures the path is
visible before any ``backlog_core`` or ``sam_schema`` import.

Also disables FastMCP's Rich logging/traceback handler (see module-level
block below) before ``fastmcp`` is imported anywhere in the process.
"""

from __future__ import annotations

import os
import sys

# FastMCP attaches a RichHandler with rich_tracebacks=True. rich/logging.py
# lazily imports rich.traceback inside emit(), so a broken rich install turns
# any tool exception into "No module named 'rich.traceback'" and hides the real
# error. These servers speak stdio to an AI agent — Rich rendering has no reader.
# setdefault, so a developer can re-enable it by exporting the var.
os.environ.setdefault("FASTMCP_ENABLE_RICH_LOGGING", "false")
os.environ.setdefault("FASTMCP_ENABLE_RICH_TRACEBACKS", "false")


def apply_project_dir_from_argv() -> None:
    """If argv contains ``--project-dir``, set ``DH_PROJECT_ROOT`` when unset."""
    argv = sys.argv[1:]
    for i, arg in enumerate(argv):
        if arg == "--project-dir" and i + 1 < len(argv):
            os.environ.setdefault("DH_PROJECT_ROOT", argv[i + 1])
            return
        if arg.startswith("--project-dir="):
            os.environ.setdefault("DH_PROJECT_ROOT", arg.split("=", 1)[1])
            return
