"""Shared provider-process failure reporting for review CLI commands."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from typing import TypeVar

import typer

from pr_review_cli_target import provider_diagnostic

T = TypeVar("T")


def provider_failure_message(operation: str, error: BaseException) -> str:
    """Render a complete provider process failure for every CLI caller.

    Returns:
        The operation context and complete provider stderr, when supplied.
    """
    diagnostic = provider_diagnostic(error)
    return f"{operation}: provider operation failed ({error}){f': {diagnostic}' if diagnostic else ''}"


def provider_operation_or_exit(
    operation: str, provider_operation: Callable[[], T], *, emit_error: Callable[[str], None] | None = None
) -> T:
    """Run one provider operation or exit after emitting its complete diagnostic.

    Returns:
        The provider operation's successful result.
    """
    try:
        return provider_operation()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        message = provider_failure_message(operation, error)
        if emit_error is None:
            typer.echo(message, err=True)
        else:
            emit_error(message)
        raise typer.Exit(code=1) from error
