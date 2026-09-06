"""The DH work ledger: one SQLite database per repository holding every SAM plan and task.

``dh_core.ledger_spec`` is the state machine as data — the tables and their column provenance, the
event kinds, the commands and their flags, the reason codes, and every transition. This package
implements it, and is the surface everything else calls:

``open_ledger``
    Opens the repository's database, creating the file and the schema when absent, and refuses with
    ``network-filesystem`` on a mount where WAL cannot share its index.

``Refusal``
    Raised by any command that refused, carrying the one ``ledger_spec.REASONS`` code that says
    why. A no-op is not a refusal: it comes back on the result's ``noop`` field instead.

one callable per ``ledger_spec.COMMANDS`` entry
    ``commands.COMMAND_FUNCTIONS`` maps each command name to it, and ``commands.check_commands``
    runs at import so a command added to the specification is a loud failure here rather than a
    surface that quietly lacks it. Three names differ from the specification's, because Python
    already has them: ``list`` is :func:`list_plans`, ``import`` is :func:`import_plan`, and
    ``export`` is :func:`export_plan` for symmetry with it.

The modules behind the surface, and what each owns:

``store``
    The database. Where it lives, opening it, the schema generated from ``ledger_spec.COLUMNS``,
    the append-only ``events`` table, and the conventions the rest of the package shares — naive
    UTC at second precision, rows as dictionaries, ``Refusal``, and ``transaction``, which a caller
    wraps around several commands so they commit or roll back together.

``derive``
    The derived columns, each from its ``rule``. ``READY_PREDICATE`` is the one implementation of
    ``tasks.ready``, which ``dispatch`` composes into the WHERE clause of its conditional UPDATE.

``transitions``
    One function per mutating ``ledger_spec.TRANSITIONS`` entry: the entry's checks in order, then
    its effects and events in one transaction.

``queries``
    The four commands that only read, and the structural findings ``validate`` reports.

``port``
    ``import``, ``export`` and ``from-milestone``: the three that cross the boundary, each split
    into the half that writes the ledger and a named seam for the half that does not.

``commands``
    The registry above, and the import-time check that it matches ``ledger_spec.COMMANDS``.
"""

from __future__ import annotations

from dh_core.ledger.commands import COMMAND_FUNCTIONS, check_commands
from dh_core.ledger.derive import progress, ready_tasks, renew_by, returned, stale
from dh_core.ledger.port import (
    CONTENT_TARGET,
    ContentProjectionStore,
    MilestoneItem,
    PlanSource,
    ProjectionStore,
    SectionSource,
    TaskSource,
    conflict_groups_for,
    content_store,
    export_plan,
    from_milestone,
    import_plan,
    milestone_source,
    plan_source,
    projection,
    projection_hash,
)
from dh_core.ledger.queries import Finding, FindingCode, PlanStatus, list_plans, ready, status, validate
from dh_core.ledger.store import Refusal, database_path, open_ledger, transaction
from dh_core.ledger.transitions import (
    PLAN_FIELD_COLUMNS,
    TASK_FIELD_COLUMNS,
    TransitionResult,
    accept,
    append_task,
    archive,
    create,
    dispatch,
    finalize,
    finish,
    read,
    reclaim,
    renew,
    settle,
    state,
    update,
)

__all__ = [
    "COMMAND_FUNCTIONS",
    "CONTENT_TARGET",
    "PLAN_FIELD_COLUMNS",
    "TASK_FIELD_COLUMNS",
    "ContentProjectionStore",
    "Finding",
    "FindingCode",
    "MilestoneItem",
    "PlanSource",
    "PlanStatus",
    "ProjectionStore",
    "Refusal",
    "SectionSource",
    "TaskSource",
    "TransitionResult",
    "accept",
    "append_task",
    "archive",
    "check_commands",
    "conflict_groups_for",
    "content_store",
    "create",
    "database_path",
    "dispatch",
    "export_plan",
    "finalize",
    "finish",
    "from_milestone",
    "import_plan",
    "list_plans",
    "milestone_source",
    "open_ledger",
    "plan_source",
    "progress",
    "projection",
    "projection_hash",
    "read",
    "ready",
    "ready_tasks",
    "reclaim",
    "renew",
    "renew_by",
    "returned",
    "settle",
    "stale",
    "state",
    "status",
    "transaction",
    "update",
    "validate",
]
