#!/usr/bin/env -S uv run --quiet --script
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
#
# [tool.ty.environment]
# root = [".", "..", "../scripts"]
# ///
"""Root Typer composer for the provider-neutral SAM CLI."""

from __future__ import annotations

import os
import sys
from io import TextIOWrapper
from pathlib import Path

# CPython puts an inherited PYTHONPATH ahead of the environment uv resolved for this script, so a
# foreign copy of any declared dependency can shadow it, including one that imports cleanly at the
# wrong version. Restart without PYTHONPATH; the plugin's own import roots are added below. Gated
# on __name__ == "__main__": this module is also imported in-process. ``git grep -nE "^from
# sam_schema.cli import" -- plugins/development-harness`` lists those importers, anchored at line
# start so the pattern cannot match prose quoting it, such as this comment. Read that list with two
# adjustments: the PEP 723 wrapper scripts/run_sam_cli.py is in it but is not a test, and
# tests/test_frontend_parity.py is absent from it yet imports this module anyway, from a probe it
# writes at run time. Every remaining entry is a CliRunner test module. On any of those paths
# os.execve would replace the *importer's* own process using the importer's sys.argv, not the
# CLI's -- hijacking whatever host imported us instead of just skipping a module-level restart it
# never needed. The wrapper
# therefore carries its own copy of this guard above its package import, which is the only place it
# can still fire: sam_schema's __init__ reaches pydantic, so a foreign copy on PYTHONPATH raises
# before this module body runs.
if __name__ == "__main__" and os.environ.get("PYTHONPATH"):
    _clean_env = dict(os.environ)
    _clean_env.pop("PYTHONPATH", None)
    os.execve(sys.executable, [sys.executable, *sys.argv], _clean_env)

# Keep direct script invocation safe on platforms whose default streams are not UTF-8.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from tls_compat import relax_verify_x509_strict

relax_verify_x509_strict()

import typer

from sam_schema import artifacts, backlog, cli_active_task, cli_known_failure_types, dispatch, sam_plan

app = typer.Typer(
    name="sam", help="Provider-neutral development harness CLI.", no_args_is_help=True, rich_markup_mode=None
)

app.add_typer(sam_plan.app, name="plan")
app.add_typer(backlog.app, name="backlog")
app.add_typer(dispatch.app, name="dispatch")
app.add_typer(artifacts.app, name="artifact")
app.add_typer(cli_active_task.app, name="active-task")
# A leaf command, not a domain app: the failure-type table is one thing to read, and its
# behavior still lives beside its operation in cli_known_failure_types.py.
app.command("known-failure-types")(cli_known_failure_types.known_failure_types)

if __name__ == "__main__":  # pragma: no cover
    app()

__all__ = ["app"]

# ponytail: the root only composes domain apps; command behavior belongs beside its operation.
