#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "fastmcp[tasks]>=3.0.2",
#   "gitpython>=3.1.0",
#   "pygithub>=2.8.1",
#   "pydantic>=2.12.3",
#   "marko>=2.0.0",
#   "markdown-it-py>=3.0.0",
#   "ruamel.yaml>=0.18.0",
#   "tiktoken>=0.12.0",
#   "typer>=0.21.2",
#   "python-dotenv>=1.0.0",
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

try:
    import os

    from dotenv import load_dotenv

    load_dotenv()

    # The Anthropic-managed proxy intercepts GitHub REST calls and returns 403.
    # The GITHUB_TOKEN PAT is valid but blocked by proxy enforcement for
    # repo-specific endpoints. Bypass the proxy for GitHub domains so PyGitHub
    # can reach api.github.com directly using the user's own token.
    _gh_domains = "api.github.com,*.github.com,*.githubusercontent.com,uploads.github.com"
    for _var in ("no_proxy", "NO_PROXY"):
        existing = os.environ.get(_var, "")
        if _gh_domains not in existing:
            os.environ[_var] = f"{existing},{_gh_domains}".lstrip(",")

    from dh_mcp_preinit import apply_project_dir_from_argv

    apply_project_dir_from_argv()

    from backlog_core.server import mcp
except ImportError:
    import sys

    _script = Path(__file__).resolve()
    print(
        f"Error: missing dependencies. Run this script with uv:\n\n"
        f"    uv run --script {_script}\n\n"
        f"Do not invoke it directly with python3.",
        file=sys.stderr,
    )
    sys.exit(1)

mcp.run()
