#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "gitpython>=3.1.57",
#   "httpx>=0.28.1",
#   "markdown-it-py>=4.2.0",
#   "marko>=2.2.3",
#   "pygithub>=2.9.1",
#   "pydantic>=2.13.4",
#   "ruamel.yaml>=0.19.1",
#   "tiktoken>=0.13.0",
#   "tomlkit>=0.15.1",
#   "typer>=0.27.0",
# ]
# ///
"""Root Typer composer for the provider-neutral SAM CLI."""

from __future__ import annotations

import os
import sys
from io import TextIOWrapper
from pathlib import Path

# CPython prepends an inherited PYTHONPATH ahead of the environment uv resolved for this script,
# so a foreign copy of a declared dependency can win and fail to import. Only pay for a reload
# when that has actually happened: a compatible PYTHONPATH costs one cheap import and no re-exec.
_RELOADED = "DH_CLI_PYTHONPATH_CLEARED"
if os.environ.get("PYTHONPATH") and not os.environ.get(_RELOADED):
    try:
        import pydantic
    except ImportError:
        _clean_env = dict(os.environ)
        _clean_env.pop("PYTHONPATH", None)
        _clean_env[_RELOADED] = "1"
        os.execve(sys.executable, [sys.executable, *sys.argv], _clean_env)
    else:
        del pydantic

# Keep direct script invocation safe on platforms whose default streams are not UTF-8.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import typer

from sam_schema import artifacts, backlog, cli_active_task, dispatch, sam_plan

app = typer.Typer(
    name="sam", help="Provider-neutral development harness CLI.", no_args_is_help=True, rich_markup_mode=None
)

app.add_typer(sam_plan.app, name="plan")
app.add_typer(backlog.app, name="backlog")
app.add_typer(dispatch.app, name="dispatch")
app.add_typer(artifacts.app, name="artifact")
app.add_typer(cli_active_task.app, name="active-task")

if __name__ == "__main__":  # pragma: no cover
    app()

__all__ = ["app"]

# ponytail: the root only composes domain apps; command behavior belongs beside its operation.
