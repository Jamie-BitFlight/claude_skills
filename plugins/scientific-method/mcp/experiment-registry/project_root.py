"""Project-root resolution for the experiment-registry MCP server.

Isolated from ``server.py`` so it can be imported and unit-tested without
pulling in FastMCP tool registration, and so its module name does not collide
with other plugins' ``server.py`` files under ty's shared ``extra-paths``
environment (see ``pyproject.toml`` ``[tool.ty.environment]``).
"""

from __future__ import annotations

import os
from pathlib import Path


def resolve_project_root(project_root: str | None) -> Path:
    """Resolve the project root to use for experiment state.

    Priority: explicit *project_root* argument, then the launcher-provided
    ``CLAUDE_PROJECT_DIR`` environment variable (set by this plugin's
    ``.claude-plugin/plugin.json`` mcpServers.env entry via
    ``${CLAUDE_PROJECT_DIR}`` substitution), then the process working
    directory. ``Path.cwd()`` alone is not a safe default — MCP server
    subprocesses are sometimes launched with a cwd inside the installed
    plugin cache rather than the project being worked on.

    Args:
        project_root: Optional project root path supplied by the caller.

    Returns:
        Resolved project root directory.
    """
    if project_root:
        return Path(project_root)
    env_root = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if env_root:
        return Path(env_root)
    return Path.cwd()
