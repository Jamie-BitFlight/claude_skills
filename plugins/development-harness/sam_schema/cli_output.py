"""Shared CLI output helpers used across the ``sam`` command modules.

Extracted from ``cli.py`` so command modules split out for the file-size
budget (e.g. ``cli_active_task.py``) can reuse the same error and JSON
emitters without importing ``cli`` itself, which would be circular.
"""

from __future__ import annotations

import json
from typing import NoReturn

import typer
from pydantic import BaseModel

__all__ = ["err", "output_json"]


def err(msg: str, exit_code: int = 1) -> NoReturn:
    """Print an error message to stderr and exit.

    Args:
        msg: Human-readable error message.
        exit_code: Process exit code (1 for user errors, 2 for internal errors).

    Raises:
        typer.Exit: Always — terminates the command with *exit_code*.
    """
    typer.echo(f"Error: {msg}", err=True)
    raise typer.Exit(exit_code)


def output_json(data: object, *, exclude_none: bool = True) -> None:
    """Print ``data`` as compact JSON to stdout.

    Pydantic models use ``model_dump_json(by_alias=True, exclude_none=...)``
    directly so wire-alias keys (kebab-case) and absent-optional elision
    are preserved. Other objects fall back to ``json.dumps`` with a string
    default.

    Args:
        data: A Pydantic model, list of models, or JSON-serializable object.
        exclude_none: When ``True`` (default), omit fields whose value is
            ``None``. Set to ``False`` when the caller needs explicit
            ``null`` values (e.g., ``active_task: null``).
    """
    if isinstance(data, BaseModel):
        typer.echo(data.model_dump_json(by_alias=True, exclude_none=exclude_none))
    elif isinstance(data, list) and data and all(isinstance(item, BaseModel) for item in data):
        typer.echo(
            json.dumps(
                [
                    item.model_dump(mode="json", by_alias=True, exclude_none=exclude_none)
                    for item in data
                    if isinstance(item, BaseModel)
                ],
                default=str,
                separators=(",", ":"),
            )
        )
    else:
        typer.echo(json.dumps(data, default=str, separators=(",", ":")))
