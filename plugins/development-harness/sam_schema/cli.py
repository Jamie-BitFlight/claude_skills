"""Root Typer composer for the provider-neutral SAM CLI."""

from __future__ import annotations

import sys
from io import TextIOWrapper
from pathlib import Path

# Keep direct script invocation safe on platforms whose default streams are not UTF-8.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import typer

from sam_schema import artifacts, backlog, cli_active_task, dispatch, sam_plan

app = typer.Typer(name="sam", help="Provider-neutral development harness CLI.", no_args_is_help=True)

app.add_typer(sam_plan.app, name="plan")
app.add_typer(backlog.app, name="backlog")
app.add_typer(dispatch.app, name="dispatch")
app.add_typer(artifacts.app, name="artifact")
app.add_typer(cli_active_task.app, name="active-task")

if __name__ == "__main__":  # pragma: no cover
    app()

__all__ = ["app"]

# ponytail: the root only composes domain apps; command behavior belongs beside its operation.
