"""``import``, ``export`` and ``from-milestone``: the three commands that cross the boundary.

Every other command in ``ledger_spec.COMMANDS`` reads and writes the ledger and nothing else. These
three carry rows in from somewhere, or push a projection of them out, so each is split in two: the
half that applies the ``ledger_spec.TRANSITIONS`` entry to the database lives here in full, and the
half that talks to the outside is a small, named seam the caller supplies.

``import`` takes a :class:`PlanSource` — plan fields, task fields, sections, a revision — and never
a reader. :func:`plan_source` builds one from a canonical ``sam_schema.core.models.Plan``, which is
what every reader in ``sam_schema/readers`` already produces, so ``--from content`` and
``--from legacy`` are two callers of one function rather than two import paths. ``--from dispatch``
is Slice 5's, which moves the ``DISPATCH_PLAN`` reader; it will be a third caller of the same
function and needs nothing added here.

``export`` computes the projection and the cursor bookkeeping itself and writes through a
:class:`ProjectionStore`. :class:`ContentProjectionStore` is the implementation over the configured
backend's ``ContentProvider``; :func:`content_store` resolves one. The divergence list an export
records is the difference between what the store holds now and what this ledger last wrote, which
is only knowable by reading the record back before writing it.

``ledger_spec.COMMANDS`` names one word, ``content``, for both ``import --from`` and ``export --to``,
and the ``import`` transition binds them by writing an ``export_cursors`` row for that target. The
place they name is the plan's own content record, which the content path reads every plan out of, so
:func:`projection` builds the record in that shape: canonical plan content, carrying the ledger's own
columns and each task's sections under keys ``PlanData`` does not declare and so ignores. An exported
plan is one the content path can open, and a plan the content path holds is one an import can read.

``from-milestone`` takes the milestone's items as :class:`MilestoneItem` values.
:func:`conflict_groups_for` is the seam that fetches ``dispatch_conflicts`` from GitHub; the
transition says the conflict group comes from it "else null", so a caller that passes nothing gets
tasks with no conflict group rather than an error.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any, Protocol, get_args, get_origin

from backlog_core.backend_protocol import get_config
from backlog_core.backend_types import ContentProvider
from backlog_core.models import ContentKind, ContentNotFoundError, ContentRef, ContentUnavailableError, ContentWrite
from pydantic import BaseModel, Field
from sam_schema.core.models import Plan, PlanState, Task
from sam_schema.core.task_backend_types import PlanData

from dh_core import ledger_spec
from dh_core.ledger import store, transitions
from dh_core.ledger.transitions import TransitionResult
from dh_core.operations import dispatch_conflicts

if TYPE_CHECKING:  # pragma: no cover - typing only
    import sqlite3
    from collections.abc import Mapping, Sequence
    from datetime import datetime

CONTENT_TARGET = "content"
"""The export target ``ledger_spec.COMMANDS`` names for ``export --to`` and ``import --from``."""


def transition_note(command: str) -> str:
    """Return the note of a plan-scoped transition.

    Args:
        command: The ``ledger_spec.TRANSITIONS`` command name.

    Returns:
        The note the specification wrote for it.

    Raises:
        KeyError: When the specification has no transition for that command.
    """
    for entry in ledger_spec.TRANSITIONS:
        if entry.command == command:
            return entry.note
    msg = f"{command} has no transition in ledger_spec.TRANSITIONS"
    raise KeyError(msg)


def excluded_columns() -> tuple[str, ...]:
    """Read the columns the projection leaves out from the ``export`` transition's note.

    Returns:
        The column names, in the order the note lists them.

    Raises:
        ValueError: When the note names nothing, or names something that is not a column of
            ``tasks`` or ``plans`` in ``ledger_spec.COLUMNS``.
    """
    note = transition_note("export")
    _, marker, tail = note.partition("projection excludes ")
    names = tuple(part.strip().rstrip(".") for part in tail.split(",") if part.strip()) if marker else ()
    if not names:
        msg = "the export transition's note no longer names the columns the projection excludes"
        raise ValueError(msg)
    known = {column.name for column in ledger_spec.COLUMNS}
    unknown = sorted(set(names) - known)
    if unknown:
        msg = f"the export note excludes {', '.join(unknown)}, which ledger_spec.COLUMNS does not declare"
        raise ValueError(msg)
    return names


PROJECTION_EXCLUDED: tuple[str, ...] = excluded_columns()
"""The lease and worktree columns a projection leaves out, read from the specification's note."""


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------


IMPORTED_SECTION_ATTEMPT = store.IMPORTED_SECTION_ATTEMPT
"""The attempt every imported section is tagged with, as the ``import`` transition states.

``store`` owns the value because the fold of ``task.imported`` tags the sections it rebuilds with
it, and ``store`` cannot import this module.
"""


class SectionSource(BaseModel):
    """One section an import carries in.

    It carries no attempt: the ``import`` transition tags every incoming section
    :data:`IMPORTED_SECTION_ATTEMPT`, whatever attempt it was written under wherever it came from.
    """

    name: str
    content: str


class TaskSource(BaseModel):
    """One task an import carries in, as the ``task.imported`` payload describes it."""

    fields: dict[str, Any] = Field(default_factory=dict)
    """The ``ledger_spec.TASK_MODEL_FIELDS`` values, validated through ``Task``."""
    conflict_group: str | None = None
    attempts: int = 0
    attempts_allowed: int = 0
    accepted: int = 0
    sections: list[SectionSource] = Field(default_factory=list)


class PlanSource(BaseModel):
    """A whole plan an import carries in, from whatever reader produced it."""

    plan_id: str
    fields: dict[str, Any] = Field(default_factory=dict)
    """The ``ledger_spec.PLAN_MODEL_FIELDS`` values, validated through ``Plan``."""
    milestone: int | None = None
    integration_branch: str | None = None
    base_sha: str | None = None
    quality_gates: list[str] = Field(default_factory=list)
    tasks: list[TaskSource] = Field(default_factory=list)
    source: str = ""
    """Where the rows came from, recorded in the ``plan.replaced`` and ``plan.imported`` payloads."""
    revision: str = ""


def plan_source(
    plan: Plan,
    *,
    source: str,
    revision: str = "",
    conflict_groups: Mapping[str, str] | None = None,
    max_attempts: int | None = None,
) -> PlanSource:
    """Build an import source from a canonical plan.

    Every reader under ``sam_schema/readers`` produces a ``Plan``, so this is the one adapter each
    ``--from`` route needs.

    Args:
        plan: The canonical plan, with its tasks.
        source: Where the plan was read from, recorded in the events.
        revision: The source's revision, recorded on the export cursor.
        conflict_groups: Task id to conflict group, for a source that carries them separately.
        max_attempts: The ``loop.max_attempts`` value ``attempts_allowed`` starts at.

    Returns:
        The source, ready for :func:`import_plan`.

    Raises:
        ValueError: When the plan carries no ``plan_id``.
    """
    if not plan.plan_id:
        msg = "a plan source needs a plan_id"
        raise ValueError(msg)
    budget = transitions.DEFAULT_MAX_ATTEMPTS if max_attempts is None else max_attempts
    dumped = plan.model_dump(mode="json", by_alias=False)
    groups = dict(conflict_groups or {})
    tasks = [
        TaskSource(
            fields=task.model_dump(mode="json", by_alias=False),
            conflict_group=groups.get(task.id),
            attempts_allowed=budget,
        )
        for task in plan.tasks
    ]
    return PlanSource(
        plan_id=plan.plan_id,
        fields={name: dumped.get(name) for name in ledger_spec.PLAN_MODEL_FIELDS},
        tasks=tasks,
        source=source,
        revision=revision,
    )


def plan_row(source: PlanSource) -> dict[str, Any]:
    """Build the ``plans`` row an import or a milestone plan writes.

    Args:
        source: The import source.

    Returns:
        Every column of ``plans``, with the model fields validated through ``Plan``.
    """
    fields = {name: value for name, value in source.fields.items() if value is not None}
    fields["plan_id"] = source.plan_id
    fields.setdefault("feature", source.plan_id)
    model = Plan.model_validate(fields).model_dump(mode="json", by_alias=False)
    row = {name: store.encode(model.get(name)) for name in ledger_spec.PLAN_MODEL_FIELDS}
    row.update(
        milestone=source.milestone,
        integration_branch=source.integration_branch,
        base_sha=source.base_sha,
        quality_gates=json.dumps(list(source.quality_gates)),
        archived=None,
    )
    return row


def created_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    """Build the ``plan.created`` payload: the whole plans row bar the one no create sets.

    Args:
        row: A full ``plans`` row.

    Returns:
        Every column ``ledger_spec.EVENTS`` declares for the kind.
    """
    return {name: row.get(name) for name in transitions.PLAN_COLUMNS if name != "archived"}


def replaced_payload(
    row: Mapping[str, Any], *, source: PlanSource, replaced: str, clears: Sequence[str]
) -> dict[str, Any]:
    """Build the ``plan.replaced`` payload: the plan row, its provenance, and what it emptied.

    ``ledger_spec.COLUMNS`` names ``plan.replaced`` in the ``set_by`` of every ``plans`` column, so
    the row rides in the payload exactly as it does on a create. ``replaced`` and ``clears`` say
    which plan's rows went from which tables, which the two commands that append this kind answer
    differently: the ``exists`` check can match on milestone rather than on id, and
    :func:`clearable_tables` gives ``import`` three tables and ``from-milestone`` one.

    Args:
        row: A full ``plans`` row.
        source: The plan being written, for its provenance.
        replaced: The id of the plan whose rows were emptied.
        clears: The tables that were emptied.

    Returns:
        Every column ``ledger_spec.EVENTS`` declares for the kind.
    """
    payload = created_payload(row)
    payload.update(source=source.source, revision=source.revision, replaced=replaced, clears=list(clears))
    return payload


def existing_plan(conn: sqlite3.Connection, *, plan_id: str, milestone: int | None) -> dict[str, Any] | None:
    """Find the plan the ``exists`` check is about.

    Args:
        conn: An open ledger connection.
        plan_id: The incoming plan's id.
        milestone: The incoming plan's milestone, when it has one.

    Returns:
        The row of the plan with this id, or of an unarchived plan with this milestone, or None.
    """
    found = store.rows_of(conn.execute("SELECT * FROM plans WHERE plan_id = :plan", {"plan": plan_id}))
    if found:
        return found[0]
    if milestone is None:
        return None
    found = store.rows_of(
        conn.execute("SELECT * FROM plans WHERE milestone = :milestone AND archived IS NULL", {"milestone": milestone})
    )
    return found[0] if found else None


def replace_checks(conn: sqlite3.Connection, existing: Mapping[str, Any] | None, *, replace: bool) -> None:
    """Evaluate the ``exists`` and ``leased`` checks both port commands share, in order.

    Args:
        conn: An open ledger connection.
        existing: The row the ``exists`` check found, or None.
        replace: Whether ``--replace`` waives it.
    """
    if existing is None:
        return
    if not replace:
        transitions.refuse("exists")
    plan = str(existing["plan_id"])
    if any(int(row["attempt_open"] or 0) == 1 for row in store.plan_tasks(conn, plan)):
        transitions.refuse("leased")


REPLACEABLE_TABLES: frozenset[str] = frozenset({"tasks", "sections", "export_cursors"})
"""The materialised tables a ``--replace`` deletes rows from.

``plans`` is not among them: :func:`write_plan_row` replaces that one row in place, so nothing of
it is ever deleted.
"""


def clearable_tables(command: str) -> tuple[str, ...]:
    """Name the tables one command may empty for a plan it replaces.

    ``ledger_spec.EVENTS`` says which kinds a command appends through ``written_by``, and
    ``ledger_spec.COLUMNS`` says which kinds set each table's columns through ``set_by``. A table
    the command can append no setting event for may not change: deleting its rows would leave the
    fold of the log holding what the table no longer does.

    Args:
        command: The ``ledger_spec.COMMANDS`` name.

    Returns:
        The tables of :data:`REPLACEABLE_TABLES` the command's own events set, sorted.
    """
    kinds = {event.kind for event in ledger_spec.EVENTS if command in event.written_by}
    return tuple(
        sorted({
            column.table
            for column in ledger_spec.COLUMNS
            if column.table in REPLACEABLE_TABLES
            and column.provenance is not ledger_spec.Provenance.DERIVED
            and kinds.intersection(column.set_by)
        })
    )


IMPORT_CLEARS: tuple[str, ...] = clearable_tables("import")
"""``import`` appends ``task.imported`` and ``plan.imported``, so it may rewrite all three tables."""

MILESTONE_CLEARS: tuple[str, ...] = clearable_tables("from-milestone")
"""``from-milestone`` appends only ``task.added``, so ``tasks`` is the one table it may empty.

Its other two kinds, ``plan.created`` and ``plan.replaced``, set columns of ``plans`` alone. No
event it may append sets a ``sections`` column (``task.section``, ``task.imported``) or an
``export_cursors`` column (``plan.exported``, ``plan.imported``), so a replace leaves both tables
as it found them and the next ``export`` keeps the cursor its compare-and-swap needs.
"""


def clear_plan(conn: sqlite3.Connection, plan: str, *, tables: Sequence[str]) -> None:
    """Remove one plan's rows from the tables a command's own events can rewrite.

    Args:
        conn: An open ledger connection, inside the caller's transaction.
        plan: The plan id.
        tables: The tables to empty, from :func:`clearable_tables`.
    """
    for table in tables:
        words = ["DELETE FROM", table, "WHERE plan = :plan"]
        conn.execute(" ".join(words), {"plan": plan})


def write_plan_row(conn: sqlite3.Connection, row: Mapping[str, Any], *, replacing: bool) -> None:
    """Insert or replace one ``plans`` row.

    Args:
        conn: An open ledger connection, inside the caller's transaction.
        row: A full ``plans`` row.
        replacing: Whether a row with this id already exists.
    """
    if not replacing:
        conn.execute(transitions.PLAN_INSERT_SQL, dict(row))
        return
    assignments = ", ".join(f"{name} = :{name}" for name in transitions.PLAN_COLUMNS if name != "plan_id")
    conn.execute(transitions.update_statement("plans", assignments, "plan_id = :plan_id"), dict(row))


def imported_task_row(task: TaskSource, *, plan: str) -> dict[str, Any]:
    """Build the ``tasks`` row an import writes.

    Args:
        task: The incoming task.
        plan: The plan the row belongs to.

    Returns:
        Every column of ``tasks``: attempt closed, attempts and acceptance from the source.
    """
    row = transitions.task_row(
        task.fields, plan=plan, conflict_group=task.conflict_group, max_attempts=task.attempts_allowed
    )
    row.update(attempts=task.attempts, accepted=task.accepted, attempt_open=0)
    return row


def import_plan(
    conn: sqlite3.Connection,
    source: PlanSource,
    *,
    replace: bool = False,
    target: str = CONTENT_TARGET,
    projection_hash: str = "",
) -> TransitionResult:
    """Write a plan read from somewhere else into the ledger.

    Args:
        conn: An open ledger connection.
        source: The plan, its tasks and their sections.
        replace: Waive the ``exists`` check and overwrite the plan already held.
        target: The export cursor the source's revision is recorded against.
        projection_hash: The hash of the source's projection, recorded on the cursor.

    Returns:
        A result naming the plan and the events appended.
    """
    events: list[str] = []
    with store.transaction(conn):
        moment = store.now()
        existing = existing_plan(conn, plan_id=source.plan_id, milestone=source.milestone)
        replace_checks(conn, existing, replace=replace)
        row = plan_row(source)
        if existing is not None:
            clear_plan(conn, str(existing["plan_id"]), tables=IMPORT_CLEARS)
        write_plan_row(conn, row, replacing=existing is not None)
        if existing is None:
            transitions.append(
                conn, kind="plan.created", plan=source.plan_id, task=None, payload=created_payload(row), at=moment
            )
            events.append("plan.created")
        else:
            transitions.append(
                conn,
                kind="plan.replaced",
                plan=source.plan_id,
                task=None,
                payload=replaced_payload(row, source=source, replaced=str(existing["plan_id"]), clears=IMPORT_CLEARS),
                at=moment,
            )
            events.append("plan.replaced")
        for task in source.tasks:
            import_task(conn, task, plan=source.plan_id, source=source.source, moment=moment)
        if source.tasks:
            events.append("task.imported")
        seq = store.last_seq(conn, source.plan_id)
        write_cursor(
            conn,
            plan=source.plan_id,
            target=target,
            last_seq=seq,
            revision=source.revision,
            projection_hash=projection_hash,
        )
        transitions.append(
            conn,
            kind="plan.imported",
            plan=source.plan_id,
            task=None,
            payload={
                "source": source.source,
                "revision": source.revision,
                "projection_hash": projection_hash,
                "target": target,
                "last_seq": seq,
            },
            at=moment,
        )
        events.append("plan.imported")
    return TransitionResult(command="import", plan=source.plan_id, events=events, changed={"tasks": len(source.tasks)})


def import_task(conn: sqlite3.Connection, task: TaskSource, *, plan: str, source: str, moment: datetime) -> None:
    """Write one imported task and its sections, and append ``task.imported``.

    Args:
        conn: An open ledger connection, inside the caller's transaction.
        task: The incoming task.
        plan: The plan the task belongs to.
        source: Where the rows came from, recorded in the payload.
        moment: The instant the caller sampled for this transition.
    """
    row = imported_task_row(task, plan=plan)
    conn.execute(transitions.TASK_INSERT_SQL, row)
    for index, section in enumerate(task.sections, start=1):
        conn.execute(
            "INSERT INTO sections (plan, task, name, attempt, content, seq) "
            "VALUES (:plan, :task, :name, :attempt, :content, :seq)",
            {
                "plan": plan,
                "task": row["id"],
                "name": section.name,
                "attempt": IMPORTED_SECTION_ATTEMPT,
                "content": section.content,
                "seq": index,
            },
        )
    payload = {name: row.get(name) for name in (*ledger_spec.TASK_MODEL_FIELDS, "conflict_group")}
    payload.update(
        attempts=row["attempts"],
        attempts_allowed=row["attempts_allowed"],
        accepted=row["accepted"],
        sections=[section.model_dump() for section in task.sections],
        source=source,
    )
    transitions.append(conn, kind="task.imported", plan=plan, task=str(row["id"]), payload=payload, at=moment)


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


TASKS_KEY = "tasks"
"""The key a plan document holds its tasks under, in ``PlanData`` and in the projection alike."""

SECTIONS_KEY = "sections"
"""The key each task of the projection holds its ``sections`` rows under."""


def structured_fields(model: type[BaseModel]) -> frozenset[str]:
    """Name the model fields the ledger stores as JSON text.

    Args:
        model: ``Plan`` or ``Task``.

    Returns:
        Every field whose annotation admits a list or a mapping, which is what
        ``transitions.task_row`` and :func:`plan_row` encode with ``json.dumps``.
    """
    found: set[str] = set()
    for name, field in model.model_fields.items():
        for candidate in (field.annotation, *get_args(field.annotation)):
            if candidate in {list, dict} or get_origin(candidate) in {list, dict}:
                found.add(name)
    return frozenset(found)


def json_columns(table: str) -> frozenset[str]:
    """Name the ledger columns of one table whose ``ledger_spec`` type says they hold JSON text.

    Args:
        table: The table name.

    Returns:
        The column names whose declared type starts with ``json``.
    """
    return frozenset(
        column.name for column in ledger_spec.COLUMNS if column.table == table and column.type.startswith("json")
    )


PLAN_STRUCTURED: frozenset[str] = structured_fields(Plan) | json_columns("plans")
"""Every ``plans`` column the ledger holds as JSON text."""

TASK_STRUCTURED: frozenset[str] = structured_fields(Task) | json_columns("tasks")
"""Every ``tasks`` column the ledger holds as JSON text."""


def decode_row(row: Mapping[str, Any], structured: frozenset[str]) -> dict[str, Any]:
    """Decode the JSON-text columns of one stored row back into Python values.

    Args:
        row: A ``plans`` or ``tasks`` row, or a slice of one.
        structured: The column names stored as JSON text.

    Returns:
        The row with its structured columns decoded and everything else untouched.
    """
    return {
        name: json.loads(value) if name in structured and isinstance(value, str) else value
        for name, value in row.items()
    }


def ledger_columns(table: str, model_fields: Sequence[str]) -> tuple[str, ...]:
    """Name the stored columns of one table the projection carries beyond the canonical model.

    Args:
        table: The table name.
        model_fields: The model fields of that table, which the canonical dump already carries.

    Returns:
        Its other stored columns, minus the ones :data:`PROJECTION_EXCLUDED` names.
    """
    known = set(model_fields)
    return tuple(
        column.name
        for column in ledger_spec.COLUMNS
        if column.table == table
        and column.provenance is not ledger_spec.Provenance.DERIVED
        and column.name not in known
        and column.name not in PROJECTION_EXCLUDED
    )


LEDGER_PLAN_COLUMNS: tuple[str, ...] = ledger_columns("plans", ledger_spec.PLAN_MODEL_FIELDS)
"""The ``plans`` columns the document carries past ``PlanData``: the milestone and the gates."""

LEDGER_TASK_COLUMNS: tuple[str, ...] = ledger_columns("tasks", ledger_spec.TASK_MODEL_FIELDS)
"""The ``tasks`` columns the document carries past ``TaskData``: attempts, acceptance, the group.

``import`` takes ``attempts`` and ``accepted`` "from the source", so a round trip through the store
only preserves them because they ride here. ``PlanData`` validation drops what it does not declare,
so they reach an importer that reads the record raw and not one that reads it as a plan.
"""

PLAN_TEXT_KEYS: frozenset[str] = frozenset(
    name for name in PlanData.__required_keys__ if PlanData.__annotations__.get(name) is str
)
"""The plan-document keys that must hold text.

``Plan`` makes ``goal``, ``context`` and ``acceptance_criteria`` optional and ``PlanData`` does not,
so a plan the ledger holds with none of them still has to reach the record as empty strings for
``sam_schema.core.backends.content.parse_plan_content`` to read it back.
"""


def visible(row: Mapping[str, Any]) -> dict[str, Any]:
    """Drop the columns :data:`PROJECTION_EXCLUDED` names from one row.

    Args:
        row: A ``sections`` row.

    Returns:
        The row without the lease and worktree columns.
    """
    return {name: value for name, value in row.items() if name not in PROJECTION_EXCLUDED}


def without_excluded(entry: dict[str, Any]) -> dict[str, Any]:
    """Empty the values of the columns the projection excludes, keeping the keys the record needs.

    ``last_activity`` is both an excluded column and a required key of ``TaskData``, so it is
    nulled rather than dropped: the record stays readable and a wave of renewals still leaves the
    projection hash where it was.

    Args:
        entry: A canonical task or plan mapping.

    Returns:
        The same mapping with every excluded name it carries set to None.
    """
    for name in PROJECTION_EXCLUDED:
        if name in entry:
            entry[name] = None
    return entry


def content_task(row: Mapping[str, Any], sections: list[dict[str, Any]]) -> dict[str, Any]:
    """Render one task row as the task a plan document carries.

    Args:
        row: The ``tasks`` row.
        sections: That task's ``sections`` rows.

    Returns:
        The canonical ``Task`` dump, the ledger's own columns, and the sections.
    """
    fields = decode_row({name: row.get(name) for name in ledger_spec.TASK_MODEL_FIELDS}, TASK_STRUCTURED)
    entry = Task.model_validate(fields).model_dump(mode="json", by_alias=False)
    entry.update(decode_row({name: row.get(name) for name in LEDGER_TASK_COLUMNS}, TASK_STRUCTURED))
    entry = without_excluded(entry)
    entry[SECTIONS_KEY] = sections
    return entry


def content_plan(row: Mapping[str, Any]) -> dict[str, Any]:
    """Render one plan row as the head of a plan document.

    Args:
        row: The ``plans`` row.

    Returns:
        The canonical ``Plan`` dump without its tasks, plus the ledger's own plan columns.
    """
    fields = decode_row({name: row.get(name) for name in ledger_spec.PLAN_MODEL_FIELDS}, PLAN_STRUCTURED)
    entry = Plan.model_validate(fields).model_dump(mode="json", by_alias=False)
    entry.pop(TASKS_KEY, None)
    for name in PLAN_TEXT_KEYS & set(entry):
        entry[name] = entry[name] or ""
    entry.update(decode_row({name: row.get(name) for name in LEDGER_PLAN_COLUMNS}, PLAN_STRUCTURED))
    return without_excluded(entry)


def projection(conn: sqlite3.Connection, plan: str) -> dict[str, Any]:
    """Build the projection of one plan: what an export writes and a divergence check compares.

    The document is the plan's canonical content — the shape
    ``sam_schema.core.backends.content.ContentTaskProvider`` reads every plan record as — carrying
    the ledger's own columns and each task's sections as keys ``PlanData`` does not declare and so
    ignores. ``export --to content`` and ``import --from content`` name one place in
    ``ledger_spec.COMMANDS``, and this is what makes them one place: an exported plan is a plan the
    content path can open, and a plan the content path holds is one an import can read.

    Args:
        conn: An open ledger connection.
        plan: The plan id.

    Returns:
        The plan document, with the excluded columns emptied.

    Raises:
        LookupError: When no such plan exists.
    """
    document = content_plan(store.fetch_plan(conn, plan))
    document[TASKS_KEY] = [
        content_task(row, [visible(section) for section in transitions.sections_of(conn, plan, str(row["id"]))])
        for row in store.plan_tasks(conn, plan)
    ]
    return document


def projection_hash(content: Mapping[str, Any]) -> str:
    """Hash a projection so two of them can be compared without reading both.

    Args:
        content: The projection.

    Returns:
        The hex SHA-256 of its canonical JSON form.
    """
    canonical = json.dumps(content, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def plan_part(document: Mapping[str, Any]) -> dict[str, Any]:
    """Return everything a plan document says about the plan itself.

    Args:
        document: A plan document, as :func:`projection` builds one.

    Returns:
        The document without its tasks.
    """
    return {name: value for name, value in document.items() if name != TASKS_KEY}


def divergences(held: Mapping[str, Any] | None, current: Mapping[str, Any]) -> list[str]:
    """Name what the store holds that this ledger's projection does not say.

    Args:
        held: The projection read back from the store, or None when it holds nothing.
        current: The projection this export is about to write.

    Returns:
        The task ids whose rows differ, plus ``plan`` when the plan itself differs, sorted. Empty
        when the store holds nothing, which is an absent record rather than a divergent one.
    """
    if held is None:
        return []
    found: list[str] = []
    if plan_part(held) != plan_part(current):
        found.append("plan")
    held_tasks = list(held.get(TASKS_KEY) or [])
    current_tasks = list(current.get(TASKS_KEY) or [])
    by_id = {str(task.get("id")): task for task in held_tasks}
    for task in current_tasks:
        identifier = str(task.get("id"))
        if by_id.get(identifier) != task:
            found.append(identifier)
    found.extend(identifier for identifier in by_id if identifier not in {str(t.get("id")) for t in current_tasks})
    return sorted(set(found))


class ProjectionStore(Protocol):
    """Where an export writes a plan's projection and reads it back to detect divergence."""

    def read(self, plan: str) -> dict[str, Any] | None:
        """Return the projection the store holds for a plan, or None when it holds none."""
        ...

    def write(self, plan: str, content: Mapping[str, Any], *, expected_revision: str = "") -> str:
        """Write a projection and return the revision the store assigned."""
        ...


class ContentProjectionStore:
    """A :class:`ProjectionStore` over the configured backend's plan content records.

    The record it writes is the plan's own ``ContentKind.PLAN`` record, which is the one
    ``sam_schema.core.backends.content.ContentTaskProvider`` reads every plan out of.
    :func:`projection` builds the document in that shape, so an export leaves a record the content
    path — and therefore ``import --from content`` — can still read.
    """

    def __init__(self, provider: ContentProvider, *, owner_reference: str = "") -> None:
        """Store the provider the projections are written through.

        Args:
            provider: The configured backend's content capability.
            owner_reference: The work item the plan records belong to.
        """
        self.provider = provider
        self.owner_reference = owner_reference

    def reference(self, plan: str) -> ContentRef:
        """Return the logical identity of one plan's record.

        Args:
            plan: The plan id.

        Returns:
            The content reference.
        """
        return ContentRef(kind=ContentKind.PLAN, name=plan)

    def read(self, plan: str) -> dict[str, Any] | None:
        """Read the projection the backend holds for a plan.

        Args:
            plan: The plan id.

        Returns:
            The decoded projection, or None when the backend holds no record or holds one this
            ledger did not write.
        """
        try:
            record = self.provider.get_content(self.reference(plan))
        except ContentNotFoundError:
            return None
        decoded = json.loads(record.content)
        return decoded if isinstance(decoded, dict) else None

    def write(self, plan: str, content: Mapping[str, Any], *, expected_revision: str = "") -> str:
        """Write a projection to the backend.

        Args:
            plan: The plan id.
            content: The projection.
            expected_revision: The revision this export last saw, for compare-and-swap.

        Returns:
            The revision the backend assigned.
        """
        record = self.provider.put_content(
            ContentWrite(
                reference=self.reference(plan),
                content=json.dumps(content, sort_keys=True, default=str),
                owner_reference=self.owner_reference or None,
                expected_revision=expected_revision,
            )
        )
        return record.revision


def content_store(owner_reference: str = "") -> ContentProjectionStore:
    """Resolve a projection store over the configured backend.

    ``ContentProvider`` is an optional backend capability, so the gate is the same runtime check
    ``dh_core.operations`` makes: a backend without it raises rather than failing at the first write.

    Args:
        owner_reference: The work item the plan records belong to.

    Returns:
        The store, wrapping whatever backend ``.dh/config.yaml`` selects.

    Raises:
        ContentUnavailableError: When the configured backend has no content capability.
    """
    backend = get_config().backend
    if not isinstance(backend, ContentProvider):
        msg = "the configured backend does not support content records, so a plan cannot be exported to it"
        raise ContentUnavailableError(msg)
    return ContentProjectionStore(backend, owner_reference=owner_reference)


def read_cursor(conn: sqlite3.Connection, plan: str, target: str) -> dict[str, Any] | None:
    """Read one plan's export cursor for a target.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        target: The export target.

    Returns:
        The cursor row, or None when the plan has never been exported to that target.
    """
    found = store.rows_of(
        conn.execute(
            "SELECT * FROM export_cursors WHERE plan = :plan AND target = :target", {"plan": plan, "target": target}
        )
    )
    return found[0] if found else None


def write_cursor(
    conn: sqlite3.Connection, *, plan: str, target: str, last_seq: int, revision: str, projection_hash: str
) -> None:
    """Insert or replace one export cursor.

    Args:
        conn: An open ledger connection, inside the caller's transaction.
        plan: The plan id.
        target: The export target.
        last_seq: The log sequence number the projection reflects.
        revision: The revision the target assigned.
        projection_hash: The hash of the projection written.
    """
    conn.execute(
        "INSERT INTO export_cursors (plan, target, last_seq, revision, projection_hash) "
        "VALUES (:plan, :target, :last_seq, :revision, :projection_hash) "
        "ON CONFLICT (plan, target) DO UPDATE SET "
        "last_seq = :last_seq, revision = :revision, projection_hash = :projection_hash",
        {
            "plan": plan,
            "target": target,
            "last_seq": last_seq,
            "revision": revision,
            "projection_hash": projection_hash,
        },
    )


def export_plan(
    conn: sqlite3.Connection, plan: str, *, target: str = CONTENT_TARGET, projection_store: ProjectionStore
) -> TransitionResult:
    """Write a plan's projection to a target, or report that nothing changed.

    The record is read back before it is written, so a projection edited out of band since the last
    export is named in ``divergences`` rather than silently overwritten without a trace. The
    compare-and-swap is against the revision the last export left, so it guards a write that landed
    between this read-back and this write; a divergence the read-back already named is recorded and
    then overwritten, because the ``export`` transition's only check is ``unchanged`` and
    ``ledger_spec.REASONS`` has no code for a store that moved.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        target: The export target.
        projection_store: Where the projection is written and read back from.

    Returns:
        A result naming the revision and any divergence, or an ``unchanged`` no-op.
    """
    content = projection(conn, plan)
    digest = projection_hash(content)
    cursor = read_cursor(conn, plan, target)
    if cursor is not None and str(cursor["projection_hash"] or "") == digest:
        return transitions.declined("export", "unchanged", plan)
    held = projection_store.read(plan)
    diverged = divergences(held, content)
    unmoved = held is not None and not diverged
    expected = str(cursor["revision"] or "") if cursor is not None and unmoved else ""
    revision = projection_store.write(plan, content, expected_revision=expected)
    with store.transaction(conn):
        moment = store.now()
        seq = store.last_seq(conn, plan)
        write_cursor(conn, plan=plan, target=target, last_seq=seq, revision=revision, projection_hash=digest)
        transitions.append(
            conn,
            kind="plan.exported",
            plan=plan,
            task=None,
            payload={
                "target": target,
                "last_seq": seq,
                "revision": revision,
                "projection_hash": digest,
                "divergences": diverged,
            },
            at=moment,
        )
    return TransitionResult(
        command="export",
        plan=plan,
        events=["plan.exported"],
        changed={"revision": revision, "projection_hash": digest, "divergences": diverged},
    )


# ---------------------------------------------------------------------------
# from-milestone
# ---------------------------------------------------------------------------


class MilestoneItem(BaseModel):
    """One milestone item, as the ``from-milestone`` transition describes a task built from it."""

    issue: int
    title: str
    task_id: str = ""
    """The task's id within the plan; positional when empty."""
    depends_on: list[str] = Field(default_factory=list)
    acceptance_criteria: str = ""
    verification_steps: str = ""
    conflict_group: str | None = None


def milestone_task(item: MilestoneItem, *, position: int, groups: Mapping[int, str]) -> TaskSource:
    """Build the task source for one milestone item.

    Args:
        item: The milestone item.
        position: Its one-based position, used when it carries no task id.
        groups: Issue number to conflict group, from ``dispatch_conflicts``.

    Returns:
        The task, with the fields the transition names.
    """
    return TaskSource(
        fields={
            "id": item.task_id or f"T{position}",
            "title": item.title,
            "github_issue": item.issue,
            "dependencies": list(item.depends_on),
            "acceptance_criteria": item.acceptance_criteria,
            "verification_steps": item.verification_steps,
        },
        conflict_group=item.conflict_group or groups.get(item.issue),
    )


def conflict_groups_for(milestone_number: int, repo: str = "") -> dict[int, str]:
    """Read each milestone item's conflict group from ``dispatch_conflicts``.

    Args:
        milestone_number: The milestone.
        repo: The repository, in ``owner/name`` form; the configured one when empty.

    Returns:
        Issue number to conflict group name, empty when the backend could not answer — the
        transition's "else null".
    """
    answer = dispatch_conflicts(milestone_number, repo)
    groups: dict[int, str] = {}
    for group in answer.get("conflict_groups", []):
        name = str(group.get("name") or group.get("group") or "")
        for issue in group.get("issues", []) or group.get("items", []):
            number = issue.get("issue") if isinstance(issue, dict) else issue
            if name and isinstance(number, int):
                groups[number] = name
    return groups


def milestone_source(
    *,
    milestone_number: int,
    integration_branch: str,
    base_sha: str,
    items: Sequence[MilestoneItem],
    quality_gates: Sequence[str] = (),
    plan_id: str = "",
    conflict_groups: Mapping[int, str] | None = None,
    max_attempts: int | None = None,
) -> PlanSource:
    """Build the plan a milestone's items describe.

    Args:
        milestone_number: The milestone.
        integration_branch: The branch the accepted items merge into.
        base_sha: The branch head a judge diffs a report against.
        items: The milestone's items, in dispatch order.
        quality_gates: The shell commands run before an item merges.
        plan_id: The plan id to use; derived from the milestone when empty.
        conflict_groups: Issue number to conflict group; none means no item has one.
        max_attempts: The ``loop.max_attempts`` value ``attempts_allowed`` starts at.

    Returns:
        The source, ready for :func:`from_milestone`.
    """
    budget = transitions.DEFAULT_MAX_ATTEMPTS if max_attempts is None else max_attempts
    groups = dict(conflict_groups or {})
    tasks = [milestone_task(item, position=index, groups=groups) for index, item in enumerate(items, start=1)]
    for task in tasks:
        task.attempts_allowed = budget
    return PlanSource(
        plan_id=plan_id or f"P{milestone_number:d}",
        fields={
            "feature": f"milestone-{milestone_number:d}",
            "goal": f"Deliver milestone {milestone_number:d} on {integration_branch}",
            "state": PlanState.READY.value if tasks else PlanState.DRAFTING.value,
        },
        milestone=milestone_number,
        integration_branch=integration_branch,
        base_sha=base_sha,
        quality_gates=list(quality_gates),
        tasks=tasks,
        source="milestone",
    )


def from_milestone(
    conn: sqlite3.Connection, source: PlanSource, *, replace: bool = False, dry_run: bool = False
) -> TransitionResult:
    """Write a milestone's items into the ledger as one plan.

    The tasks are added, not imported: they have never been run anywhere, so they start with no
    attempts and the ``task.added`` event, which is what ``ledger_spec.EVENTS`` says ``from-milestone``
    writes.

    Args:
        conn: An open ledger connection.
        source: The plan the milestone describes, from :func:`milestone_source`.
        replace: Waive the ``exists`` check and overwrite the plan already held.
        dry_run: Evaluate the checks and report what would be written, without writing.

    Returns:
        A result naming the plan and the events appended; with ``dry_run`` the events are empty.
    """
    kind = ""
    with store.transaction(conn):
        moment = store.now()
        existing = existing_plan(conn, plan_id=source.plan_id, milestone=source.milestone)
        replace_checks(conn, existing, replace=replace)
        if dry_run:
            return TransitionResult(command="from-milestone", plan=source.plan_id, changed={"tasks": len(source.tasks)})
        row = plan_row(source)
        if existing is not None:
            clear_plan(conn, str(existing["plan_id"]), tables=MILESTONE_CLEARS)
        write_plan_row(conn, row, replacing=existing is not None)
        kind = "plan.replaced" if existing is not None else "plan.created"
        payload = (
            replaced_payload(row, source=source, replaced=str(existing["plan_id"]), clears=MILESTONE_CLEARS)
            if existing is not None
            else created_payload(row)
        )
        transitions.append(conn, kind=kind, plan=source.plan_id, task=None, payload=payload, at=moment)
        for task in source.tasks:
            transitions.insert_task(
                conn,
                transitions.task_row(
                    task.fields,
                    plan=source.plan_id,
                    conflict_group=task.conflict_group,
                    max_attempts=task.attempts_allowed,
                ),
                event="task.added",
                moment=moment,
            )
    return TransitionResult(
        command="from-milestone",
        plan=source.plan_id,
        events=[kind, *(["task.added"] if source.tasks else [])],
        changed={"tasks": len(source.tasks)},
    )
