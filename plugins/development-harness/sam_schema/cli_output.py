"""Shared CLI output helpers used across the ``sam`` command modules.

Extracted from ``cli.py`` so command modules split out for the file-size
budget (e.g. ``cli_active_task.py``) can reuse the same error and JSON
emitters without importing ``cli`` itself, which would be circular.
"""

from __future__ import annotations

import json
from typing import NoReturn, TypeGuard

import typer
from pydantic import BaseModel

__all__ = ["emit_result", "err", "exit_with_json_error", "output_json"]


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


def _is_result_mapping(value: object) -> TypeGuard[dict[str, object]]:
    """Narrow operation results to the mapping shape used for diagnostics.

    Returns:
        Whether ``value`` is a string-keyed result mapping.
    """
    return isinstance(value, dict)


def exit_with_json_error(payload: object, *, exit_code: int = 1) -> NoReturn:
    """Emit ``payload`` as JSON to stdout, then exit nonzero.

    Unlike :func:`err`, which writes only a stderr string, this keeps the
    calling agent's JSON parser fed even on failure — a caller reading only
    stdout still receives a parseable ``{"error": ...}`` payload instead of
    an empty stream. The process still exits nonzero afterward, so
    shell-level failure detection (``$?``) is unaffected.

    Args:
        payload: JSON-serializable error payload — typically a mapping with
            an ``"error"`` key and any diagnostic context fields the caller
            wants preserved (e.g. ``milestone_number``).
        exit_code: Process exit code (1 for user/operation errors).

    Raises:
        typer.Exit: Always — after the JSON payload has been written.
    """
    output_json(payload)
    raise typer.Exit(exit_code)


def emit_result(result: object) -> None:
    """Emit an operation result as JSON to stdout, then exit nonzero on error.

    Diagnostic ``messages``/``warnings``/``errors`` lists embedded in a
    mapping result are echoed to stderr first. The result itself always
    reaches stdout as JSON afterward — including when it carries a
    top-level ``"error"`` key — so a calling agent's JSON parser is never
    handed an empty stdout stream in place of the structured payload the
    operations layer returned; a nonzero exit still signals failure to
    shell-level callers.

    Args:
        result: A Pydantic model, mapping, or JSON-serializable object
            returned by the operations layer.

    Raises:
        typer.Exit: When ``result`` is a mapping with an ``"error"`` key —
            raised after the JSON payload has been written to stdout.
    """
    if _is_result_mapping(result):
        for key in ("messages", "warnings", "errors"):
            values = result.get(key, [])
            if isinstance(values, list):
                for value in values:
                    typer.echo(str(value), err=True)
        if "error" in result:
            exit_with_json_error(result)
    output_json(result)
