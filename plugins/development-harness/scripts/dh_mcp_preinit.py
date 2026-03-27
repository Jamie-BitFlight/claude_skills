"""Shared MCP entrypoint pre-init: parse --project-dir before package imports.

``backlog_core.models`` resolves the repo root at import time.  Parsing
``--project-dir`` here and setting ``DH_PROJECT_ROOT`` ensures the path is
visible before any ``backlog_core`` or ``sam_schema`` import.
"""

from __future__ import annotations

import os
import sys


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
