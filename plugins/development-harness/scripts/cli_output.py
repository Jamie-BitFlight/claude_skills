"""Shared CLI output helpers for development-harness migration scripts.

``dh_migrate.py``, ``migrate_tasks_to_github.py``, ``migrate_backlog_to_yaml.py``,
``verify_migration_fidelity.py``, and ``manifest_resolver.py`` are invoked
exclusively by AI agents via subprocess — never by a human at an interactive
terminal. There is no dual audience and no "sometimes interactive" case, so
these tools optimize for one consumer: a token-parsing LLM reading process
output, not a human visually scanning a terminal.

That rules out two things ``rich.console.Console`` provided:

- ``Table``/``Panel`` rendering. Outside a TTY, ``rich.console.Console`` falls
  back to a hardcoded 80-column width (``rich/console.py`` —
  ``width = width or 80``), wrapping or truncating that output. A hand-rolled
  plain-text table has the same underlying defect for this consumer: aligned
  columns require the reader to track column position across rows
  (positional binding — "the 3rd value belongs to the 3rd header"), which is
  a worse fit for an LLM parsing tokens than JSON's repeated explicit key at
  each value. ``output_json`` replaces both — structured/tabular data is
  emitted as JSON, not aligned columns or bordered boxes.
- Color/style markup. Irrelevant with no terminal reading it; stripped
  entirely rather than replaced.

This module mirrors the JSON-emission convention already established in
``sam_schema/cli_output.py`` (compact ``json.dumps`` with ``separators``, no
indentation — see ``.claude/CLAUDE.md`` "JSON output" rule) so both script
families in this plugin format structured output the same way.

Plain single-line status, progress, and error messages that are not
structured/tabular (e.g. "Moving X -> Y") are NOT routed through this module
— call sites print those directly via ``typer.echo()``, which resolves the
current ``sys.stdout``/``sys.stderr`` per call (unlike a bound
``logging.StreamHandler``), so output is correctly captured by both
Click/Typer's ``CliRunner`` in tests and by the parent process in real
subprocess invocation.
"""

from __future__ import annotations

import json
from typing import NoReturn

import typer

__all__ = ["err", "output_json"]


def err(msg: str, exit_code: int = 1) -> NoReturn:
    """Print an error message to stderr and exit.

    Args:
        msg: Error message for the calling agent.
        exit_code: Process exit code.

    Raises:
        typer.Exit: Always — terminates the command with *exit_code*.
    """
    typer.echo(f"Error: {msg}", err=True)
    raise typer.Exit(exit_code)


def output_json(data: object) -> None:
    """Print *data* as compact JSON to stdout.

    No indentation — see ``.claude/CLAUDE.md`` "JSON output" rule: indentation
    multiplies token cost for an agent reader and provides no value for
    machine-readable data.

    Args:
        data: JSON-serializable object (dict, list, or primitive). Non-native
            types (e.g. ``Path``) are stringified via the ``default=str`` fallback.
    """
    typer.echo(json.dumps(data, default=str, separators=(",", ":")))
