"""Pytest configuration for frustration-analyzer tests.

Adds the plugin's ``mcp/`` directory to ``sys.path`` so that
``import server`` resolves to the frustration-analyzer server module
rather than any other ``server.py`` that might appear earlier on the
default path (e.g. ``agentskill-kaizen/mcp/server.py``).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Insert the frustration-analyzer mcp directory at the FRONT of sys.path
# so ``import server`` always finds the correct module.
_SERVER_DIR = str(Path(__file__).resolve().parent.parent / "mcp")
if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)
