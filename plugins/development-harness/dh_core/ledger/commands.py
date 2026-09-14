"""The map from a ``ledger_spec.COMMANDS`` name to the callable that implements it.

The specification lists the commands; this lists what each one runs. :func:`check_commands` runs at
import and compares the two sets in both directions, so a command added to the specification is a
loud failure here rather than a surface that quietly lacks it, and a callable exposed under a name
the specification does not have fails the same way.

Three names differ from the specification's, because Python already has them: ``list`` is
``queries.list_plans``, ``import`` is ``port.import_plan``, and ``export`` is ``port.export_plan``
for symmetry with it. Nothing else is renamed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dh_core import ledger_spec
from dh_core.ledger import port, queries, transitions

if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Callable

COMMAND_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "create": transitions.create,
    "append-task": transitions.append_task,
    "finalize": transitions.finalize,
    "validate": queries.validate,
    "list": queries.list_plans,
    "status": queries.status,
    "ready": queries.ready,
    "archive": transitions.archive,
    "from-milestone": port.from_milestone,
    "import": port.import_plan,
    "export": port.export_plan,
    "update": transitions.update,
    "read": transitions.read,
    "dispatch": transitions.dispatch,
    "renew": transitions.renew,
    "finish": transitions.finish,
    "settle": transitions.settle,
    "accept": transitions.accept,
    "reclaim": transitions.reclaim,
    "state": transitions.state,
}
"""Every ``ledger_spec.COMMANDS`` entry, by the name the specification gives it."""


def check_commands() -> None:
    """Reject a surface that does not match ``ledger_spec.COMMANDS`` one to one.

    Raises:
        ValueError: When the specification names a command this package does not implement, or
            this package exposes one the specification does not name.
    """
    specified = {command.name for command in ledger_spec.COMMANDS}
    missing = sorted(specified - set(COMMAND_FUNCTIONS))
    extra = sorted(set(COMMAND_FUNCTIONS) - specified)
    parts: list[str] = []
    if missing:
        parts.append(f"ledger_spec.COMMANDS names {', '.join(missing)} with no callable here")
    if extra:
        parts.append(f"this package exposes {', '.join(extra)}, which ledger_spec.COMMANDS does not name")
    if parts:
        raise ValueError("; ".join(parts))


check_commands()
