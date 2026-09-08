"""``sam known-failure-types`` -- the work-failure vocabulary, as JSON.

Mirrors the ``sam_known_failure_types`` MCP tool in ``sam_schema/server.py`` so both transports
return the same table from the same source, ``dh_core.known_failure_types``. Neither frontend owns
a copy of the vocabulary.

The command is declared here rather than in ``cli.py`` because command behaviour belongs beside its
operation; ``cli.py`` only attaches it. It is a leaf command rather than a Typer sub-app because the
table is one thing to read, not a group of operations on it.
"""

from __future__ import annotations

from typing import Annotated

import typer
from dh_core.known_failure_types import page

from sam_schema.cli_output import err, output_json

__all__ = ["known_failure_types"]


def known_failure_types(
    offset: Annotated[
        int, typer.Option("--offset", help="Skip this many rows. Default 0 -- the table starts at the beginning.")
    ] = 0,
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            help="Return at most this many rows. Omitted (the default) returns every remaining row; the whole table "
            "is never truncated on the caller's behalf.",
        ),
    ] = None,
) -> None:
    """Print the known work-failure types as compact JSON.

    The full table is the default. ``--offset`` and ``--limit`` exist so a caller that wants a
    window chooses it; nothing shortens the output otherwise. The result always carries ``total``,
    so a caller reading a window knows how much it did not read.

    Args:
        offset: How many rows to skip before the window starts.
        limit: How many rows the window holds at most; ``None`` returns every remaining row.

    Raises:
        typer.Exit: When ``offset`` or ``limit`` is negative.
    """
    try:
        result = page(offset=offset, limit=limit)
    except ValueError as exc:
        err(str(exc))
    output_json(result)
