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

    A bare Pydantic model uses ``model_dump_json(by_alias=True,
    exclude_none=...)`` directly, so wire-alias keys (kebab-case) and
    absent-optional elision are produced by Pydantic's own serializer.

    Anything else — a plain ``dict``/``TypedDict`` result, a list, or any
    structure that carries Pydantic model instances nested inside it at any
    depth (e.g. an operations-layer ``TypedDict`` result shaped like
    ``{"comments": [CommentListEntry(...), ...]}``) — is serialized via
    ``json.dumps`` with a ``default`` callback that recursively dumps every
    ``BaseModel`` it encounters through ``model_dump(mode="json", ...)``.
    This makes ``output_json`` the single serialization boundary for the CLI:
    an operations-layer function may return a typed Pydantic object anywhere
    inside its result without every call site remembering to flatten it to a
    plain dict first, and the JSON wire type stays a real object instead of
    silently degrading to a Python ``repr()`` string. A value that is neither
    natively JSON-serializable nor a ``BaseModel`` (e.g. ``Path``) still
    stringifies via ``str()`` as the final fallback.

    Args:
        data: A Pydantic model, or any JSON-serializable object — optionally
            containing nested Pydantic model instances at any depth.
        exclude_none: When ``True`` (default), omit fields whose value is
            ``None``. Applied to both a bare top-level model and to any
            model nested inside *data*. Set to ``False`` when the caller
            needs explicit ``null`` values (e.g., ``active_task: null``).
    """
    if isinstance(data, BaseModel):
        typer.echo(data.model_dump_json(by_alias=True, exclude_none=exclude_none))
        return

    def _dump_nested_model(value: object) -> object:
        """Fallback for a value ``json.dumps`` cannot serialize natively.

        Args:
            value: A non-JSON-native value encountered during traversal.

        Returns:
            A JSON-native ``dict`` when *value* is a nested ``BaseModel``;
            otherwise *value*'s string representation.
        """
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json", by_alias=True, exclude_none=exclude_none)
        return str(value)

    typer.echo(json.dumps(data, default=_dump_nested_model, separators=(",", ":")))


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
