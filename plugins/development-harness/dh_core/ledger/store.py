"""The ledger's database: where it lives, how it is opened, and how an event is appended.

One SQLite database per repository holds every plan and task. Its path comes from
``dh_paths.state_root()``, whose slug already derives from the git common directory, so a linked
worktree and its main checkout resolve to one file. It is opened in WAL mode with a busy timeout,
and opening refuses with ``network-filesystem`` when the mount holding it has a type in
``ledger_spec.NETWORK_FILESYSTEMS``, because WAL cannot share its index across such a mount.

The schema is generated from ``ledger_spec.COLUMNS``: every column whose provenance is not
``DERIVED`` becomes a column of its table, its SQLite affinity read from the specification's type
(and, for a ``model`` column, from the annotation of the matching ``Plan`` or ``Task`` field), and
its nullability read from whether that type ends in ``|null``. Derived columns are never stored;
:mod:`dh_core.ledger.derive` computes them at read time from their ``rule``.

The ``events`` table is this module's own — ``ledger_spec.COLUMNS`` describes only the tables
materialised *from* events, so the log's own shape is not specified there. :func:`append_event`
appends one row to it, stamped with the instant its caller sampled inside the transaction. It does
not write the materialised tables: each transition in :mod:`dh_core.ledger.transitions` applies its
own effects and appends its own events inside one transaction, so the two always move together.

:func:`fold_events` runs that the other way: it replays the log into the materialised tables, and
:func:`rebuild` empties them and writes the result back, so every table is a fold over ``events``
and nothing else. The instants come from ``events.at`` — ``ledger_spec.EVENT_INSTANT`` — which is
the transition's own moment rather than a second sample taken here, so a rebuilt ``expires``,
``started``, ``last_activity``, ``first_renewed``, ``completed`` or ``archived`` is the value the
transition wrote and not an approximation of it.

This module owns the conventions the rest of the package follows: instants are naive UTC at second
precision, rendered by :func:`timestamp` and parsed by :func:`moment`; rows are read into
dictionaries by :func:`rows_of`; and a refusal is :class:`Refusal`, carrying one
``ledger_spec.REASONS`` code.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import zlib
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, get_args

import dh_paths
from sam_schema.core.models import Plan, Task

from dh_core import ledger_spec

if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Iterator, Mapping, Sequence

    from pydantic import BaseModel

DATABASE_NAME = "dh.db"
"""The file under ``dh_paths.state_root()`` that holds the ledger."""

BUSY_TIMEOUT_MS = 30_000
"""How long a writer waits for another writer's lock before raising.

``ledger_spec.CONFIG`` names no key for this, so it is this module's own default and every entry
point that opens a database takes it as an argument.
"""

MOUNT_INFO = Path("/proc/self/mountinfo")
"""Linux's per-process mount table, read to name the filesystem type holding a path."""

MOUNT_TIMEOUT_SECONDS = 5
"""How long the ``mount`` fallback may run on a host with no ``/proc/self/mountinfo``."""

MOUNT_POINT_FIELD = 4
"""The zero-based field of a ``/proc/self/mountinfo`` line that holds the mount point.

The line is fixed-width up to the optional fields, then ``-`` and the filesystem type: fields 0
to 4 are the mount id, the parent id, the device, the root, and the mount point.
"""

INTEGER = "INTEGER"
TEXT = "TEXT"

NOT_STARTED = ledger_spec.Status.NOT_STARTED.value
IN_PROGRESS = ledger_spec.Status.IN_PROGRESS.value
COMPLETE = ledger_spec.Status.COMPLETE.value
FAILED = ledger_spec.Status.FAILED.value
DEFERRED = ledger_spec.Status.DEFERRED.value
SKIPPED = ledger_spec.Status.SKIPPED.value

IMPORTED_SECTION_ATTEMPT = 0
"""The attempt every imported section is tagged with, as the ``import`` transition states."""


def flag_vocabulary(command: str, flag: str) -> tuple[str, ...]:
    """Return the alternatives a specification flag's value description lists.

    Args:
        command: The ``ledger_spec.COMMANDS`` entry name.
        flag: The flag name, including its leading dashes.

    Returns:
        The pipe-separated alternatives of that flag's ``value``, in specification order.

    Raises:
        KeyError: When the command or the flag is not in the specification.
    """
    for entry in ledger_spec.COMMANDS:
        if entry.name != command:
            continue
        for candidate in entry.flags:
            if candidate.name == flag:
                return tuple(candidate.value.split("|"))
    msg = f"{command} has no flag {flag} in ledger_spec.COMMANDS"
    raise KeyError(msg)


FINISH_RESULTS: tuple[str, ...] = flag_vocabulary("finish", "--result")
"""The values ``finish --result`` accepts."""

RESULT_STATUS: dict[str, str] = {
    value: (value if value in {s.value for s in ledger_spec.Status} else ledger_spec.Status.BLOCKED.value)
    for value in FINISH_RESULTS
}
"""``finish --result`` to resulting status: the three status-named results map to themselves and
``needs-input`` maps to blocked, as the ``finish`` transition's ``to_status`` states. The fold of
``task.finished`` reads it, because that payload carries the result and not the status."""

CONFIG_DEFAULTS: dict[str, int] = {entry.key: entry.default for entry in ledger_spec.CONFIG}
DEFAULT_TTL_SECONDS: int = CONFIG_DEFAULTS["lease.ttl_seconds"]
DEFAULT_MAX_ATTEMPTS: int = CONFIG_DEFAULTS["loop.max_attempts"]

MODELS: dict[str, type[BaseModel]] = {"plans": Plan, "tasks": Task}
"""The canonical model behind each table that carries ``model``-typed columns."""

PRIMARY_KEYS: dict[str, tuple[str, ...]] = {
    "plans": ("plan_id",),
    "tasks": ("plan", "id"),
    "sections": ("plan", "task", "seq"),
    "export_cursors": ("plan", "target"),
}
"""The identity of a row in each materialised table.

``ledger_spec.COLUMNS`` names the columns but not which of them identify a row, so this is the
store's choice. :func:`check_primary_keys` runs at import and rejects a name that is not a column
of that table in the specification, so the two cannot drift apart silently.
"""

INDEXES: dict[str, tuple[tuple[str, ...], ...]] = {
    "tasks": (("plan",), ("plan", "status")),
    "sections": (("plan", "task", "attempt"),),
    "events": (("plan", "task", "kind"), ("plan", "seq")),
}
"""Non-unique indexes over the columns the package's own queries filter on."""


class Refusal(Exception):
    """A command refused, carrying the ``ledger_spec.REASONS`` code that names why.

    The code is the whole message: a caller prints it on stderr and exits non-zero, and no event
    is appended. Every code this carries has ``ReasonKind.REFUSAL`` in the specification; a no-op
    code is returned on a result instead of raised.
    """

    def __init__(self, reason: str) -> None:
        """Store the reason code.

        Args:
            reason: A ``ledger_spec.REASONS`` code of kind ``REFUSAL``.
        """
        super().__init__(reason)
        self.reason = reason


# ---------------------------------------------------------------------------
# Time and rows: the conventions the package shares
# ---------------------------------------------------------------------------


def now() -> datetime:
    """Return the current instant as naive UTC at second precision.

    Returns:
        The current UTC time with no tzinfo and no microseconds, matching what the ledger stores.
    """
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


def timestamp(instant: datetime) -> str:
    """Render an instant the way the ledger stores datetimes.

    Args:
        instant: The instant to render.

    Returns:
        An ISO-8601 string such as ``2026-09-06T12:00:00``, which sorts lexicographically and
        which SQLite's date functions parse.
    """
    return instant.replace(microsecond=0).isoformat()


def moment(value: object) -> datetime | None:
    """Parse a stored datetime column back into a naive UTC instant.

    Args:
        value: The stored column value: an ISO-8601 string, a ``datetime``, or null.

    Returns:
        The instant with no tzinfo, or None when the column is null or unparseable.
    """
    if isinstance(value, datetime):
        return value.astimezone(UTC).replace(tzinfo=None) if value.tzinfo else value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.astimezone(UTC).replace(tzinfo=None) if parsed.tzinfo else parsed


def rows_of(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    """Read a cursor into dictionaries keyed by column name.

    Args:
        cursor: A cursor positioned on a completed query.

    Returns:
        One dictionary per row, whatever row factory the connection carries.
    """
    names = [description[0] for description in cursor.description]
    return [dict(zip(names, tuple(row), strict=True)) for row in cursor.fetchall()]


def json_list(raw: object) -> list[str]:
    """Decode a JSON array column into a list of strings.

    Args:
        raw: The stored column value: JSON text, a list, or null.

    Returns:
        The decoded members, or an empty list when the column is null or not an array.
    """
    if isinstance(raw, list):
        return [str(member) for member in raw]
    if not isinstance(raw, str) or not raw.strip():
        return []
    decoded = json.loads(raw)
    return [str(member) for member in decoded] if isinstance(decoded, list) else []


def encode(value: object) -> object:
    """Render one value the way the ledger stores it.

    Args:
        value: A column value from a model dump or a caller.

    Returns:
        JSON text for a list or a mapping, an ISO-8601 string for a datetime, the value itself
        otherwise.
    """
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    if isinstance(value, datetime):
        return timestamp(value)
    return value


def fetch_task(conn: sqlite3.Connection, plan: str, task: str) -> dict[str, Any]:
    """Read one task row.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.

    Returns:
        The row as a dictionary.

    Raises:
        LookupError: When the plan holds no such task.
    """
    found = rows_of(conn.execute("SELECT * FROM tasks WHERE plan = :plan AND id = :task", {"plan": plan, "task": task}))
    if not found:
        msg = f"no task {plan}/{task} in the ledger"
        raise LookupError(msg)
    return found[0]


def fetch_plan(conn: sqlite3.Connection, plan: str) -> dict[str, Any]:
    """Read one plan row.

    Args:
        conn: An open ledger connection.
        plan: The plan id.

    Returns:
        The row as a dictionary.

    Raises:
        LookupError: When no such plan exists.
    """
    found = rows_of(conn.execute("SELECT * FROM plans WHERE plan_id = :plan", {"plan": plan}))
    if not found:
        msg = f"no plan {plan} in the ledger"
        raise LookupError(msg)
    return found[0]


def plan_tasks(conn: sqlite3.Connection, plan: str) -> list[dict[str, Any]]:
    """Read every task row of one plan, ordered by id.

    Args:
        conn: An open ledger connection.
        plan: The plan id.

    Returns:
        The rows as dictionaries.
    """
    return rows_of(conn.execute("SELECT * FROM tasks WHERE plan = :plan ORDER BY id", {"plan": plan}))


# ---------------------------------------------------------------------------
# The schema, generated from ledger_spec.COLUMNS
# ---------------------------------------------------------------------------


def stored_columns() -> dict[str, list[ledger_spec.Column]]:
    """Group every non-derived specification column by its table.

    Returns:
        A mapping from table name to its stored columns, in specification order.
    """
    grouped: dict[str, list[ledger_spec.Column]] = {}
    for column in ledger_spec.COLUMNS:
        if column.provenance is ledger_spec.Provenance.DERIVED:
            continue
        grouped.setdefault(column.table, []).append(column)
    return grouped


TABLES: dict[str, list[ledger_spec.Column]] = stored_columns()
"""Every materialised table the specification declares, with its stored columns."""


def admits_integer(candidate: object) -> bool:
    """Report whether one annotation stores as an integer.

    An ``IntEnum`` field such as ``Task.priority`` dumps to an integer, so its column must have
    integer affinity: a TEXT column would coerce that value to a string and the row would no
    longer hold what the event that set it carried.

    Args:
        candidate: An annotation, or one member of a union's arguments.

    Returns:
        True when the annotation is ``int``, ``bool``, or a subclass of either.
    """
    return isinstance(candidate, type) and issubclass(candidate, (int, bool))


def model_affinity(table: str, name: str) -> str:
    """Read the SQLite affinity of a ``model`` column from its model field.

    Args:
        table: The table the column belongs to.
        name: The column name, which is also the model's field name.

    Returns:
        ``INTEGER`` when the field's annotation admits ``int`` or ``bool``, ``TEXT`` otherwise.

    Raises:
        KeyError: When the table has no model, or the model has no such field.
    """
    model = MODELS[table]
    if name not in model.model_fields:
        msg = f"{table}.{name} is a model column but {model.__name__} has no field {name}"
        raise KeyError(msg)
    annotation = model.model_fields[name].annotation
    candidates = (annotation, *get_args(annotation))
    return INTEGER if any(admits_integer(candidate) for candidate in candidates) else TEXT


def affinity(column: ledger_spec.Column) -> str:
    """Read the SQLite affinity of one specification column from its type.

    Args:
        column: The specification column.

    Returns:
        ``INTEGER`` for an ``int`` or ``bool`` type, ``TEXT`` for everything else.
    """
    if column.type == "model":
        return model_affinity(column.table, column.name)
    return INTEGER if column.type.startswith(("int", "bool")) else TEXT


def nullable(column: ledger_spec.Column) -> bool:
    """Report whether a specification column admits null.

    A ``model`` column takes its nullability from the model, so it is left nullable here and the
    model's own validation is the gate. Every other type states it: a type ending in ``|null``
    admits null and any other type does not.

    Args:
        column: The specification column.

    Returns:
        True when the column may hold null.
    """
    return column.type == "model" or column.type.endswith("|null")


def column_default(column: ledger_spec.Column) -> str:
    """Return the DDL default a not-null column needs, as SQL text.

    Args:
        column: The specification column.

    Returns:
        ``0`` for a not-null integer, ``''`` for a not-null text column, and an empty string when
        the column is nullable and so needs no default.
    """
    if nullable(column):
        return ""
    return "0" if affinity(column) == INTEGER else "''"


def column_ddl(column: ledger_spec.Column) -> str:
    """Assemble the DDL fragment for one column.

    Args:
        column: The specification column.

    Returns:
        The name, affinity, and the NOT NULL and DEFAULT clauses the specification implies.
    """
    words = [column.name, affinity(column)]
    if not nullable(column):
        words.extend(["NOT NULL", "DEFAULT", column_default(column)])
    return " ".join(words)


def check_primary_keys() -> None:
    """Reject a primary key naming a column the specification does not declare.

    Raises:
        ValueError: When a table in :data:`PRIMARY_KEYS` is unknown, or names a column that is
            not a stored column of that table in ``ledger_spec.COLUMNS``.
    """
    for table, key in PRIMARY_KEYS.items():
        if table not in TABLES:
            msg = f"{table} is not a table in ledger_spec.COLUMNS"
            raise ValueError(msg)
        names = {column.name for column in TABLES[table]}
        unknown = sorted(set(key) - names)
        if unknown:
            msg = f"{table} primary key names {', '.join(unknown)}, which ledger_spec.COLUMNS does not declare"
            raise ValueError(msg)


check_primary_keys()


def table_ddl(table: str) -> str:
    """Assemble the ``CREATE TABLE`` statement for one materialised table.

    Args:
        table: The table name.

    Returns:
        The statement, with one column per stored specification column and the store's primary key.
    """
    parts = [column_ddl(column) for column in TABLES[table]]
    key = PRIMARY_KEYS.get(table)
    if key:
        parts.append("PRIMARY KEY (" + ", ".join(key) + ")")
    words = ["CREATE TABLE IF NOT EXISTS", table, "(", ", ".join(parts), ")"]
    return " ".join(words)


EVENTS_DDL = (
    "CREATE TABLE IF NOT EXISTS events ("
    "seq INTEGER PRIMARY KEY AUTOINCREMENT, "
    "at TEXT NOT NULL, "
    "kind TEXT NOT NULL, "
    "plan TEXT NOT NULL, "
    "task TEXT, "
    "payload TEXT NOT NULL)"
)
"""The append-only log. ``ledger_spec.COLUMNS`` describes the tables materialised from it, not it."""


def insert_statement(table: str, columns: Sequence[str]) -> str:
    """Assemble an insert over a fixed column list.

    The statement is assembled from separate words rather than interpolated into one SQL literal:
    every column name comes from ``ledger_spec``, and no caller value reaches the statement text.

    Args:
        table: The table to insert into.
        columns: The columns to write, each also the name of its bound parameter.

    Returns:
        The statement, with one named placeholder per column.
    """
    names = ", ".join(columns)
    binds = ", ".join(":" + name for name in columns)
    words = ["INSERT INTO", table, "(", names, ")", "VALUES", "(", binds, ")"]
    return " ".join(words)


def index_ddl(table: str, columns: Sequence[str]) -> str:
    """Assemble a ``CREATE INDEX`` statement.

    Args:
        table: The table to index.
        columns: The columns of the index, in order.

    Returns:
        The statement, named after the table and its columns.
    """
    name = "_".join(["ix", table, *columns])
    words = ["CREATE INDEX IF NOT EXISTS", name, "ON", table, "(", ", ".join(columns), ")"]
    return " ".join(words)


def schema_statements() -> list[str]:
    """Assemble every DDL statement the ledger's schema needs.

    Returns:
        The table statements in specification order, then the log, then the indexes.
    """
    statements = [table_ddl(table) for table in TABLES]
    statements.append(EVENTS_DDL)
    statements.extend(index_ddl(table, columns) for table, group in INDEXES.items() for columns in group)
    return statements


SCHEMA: tuple[str, ...] = tuple(schema_statements())
"""Every DDL statement, generated once from ``ledger_spec.COLUMNS``."""

SCHEMA_VERSION: int = zlib.crc32("\n".join(SCHEMA).encode()) & 0x7FFF_FFFF
"""``PRAGMA user_version`` for this schema: a checksum of its DDL, so it changes when the
specification's columns change and :func:`ensure_schema` knows to look for new ones."""


def add_column_ddl(table: str, column: ledger_spec.Column) -> str:
    """Assemble the ``ALTER TABLE`` that adds one column to an existing table.

    A not-null column is added with the default :func:`column_default` names, because SQLite
    rejects adding a not-null column without one to a table that already holds rows.

    Args:
        table: The table to alter.
        column: The specification column to add.

    Returns:
        The statement.
    """
    words = ["ALTER TABLE", table, "ADD COLUMN", column_ddl(column)]
    return " ".join(words)


def existing_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """Read the column names a table already has.

    Args:
        conn: An open connection.
        table: The table name.

    Returns:
        The names, empty when the table does not exist.
    """
    found = rows_of(conn.execute("SELECT name FROM pragma_table_info(:table)", {"table": table}))
    return {str(row["name"]) for row in found}


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create the schema, and add any column a database written by an older version lacks.

    Creating is idempotent. Migration is additive only: a column the specification has gained
    since the database was written is added with its default, and a column the specification has
    dropped is left in place rather than deleted, so a rollback still reads the database.

    Args:
        conn: An open connection.
    """
    with transaction(conn):
        for statement in SCHEMA:
            conn.execute(statement)
        for table, columns in TABLES.items():
            present = existing_columns(conn, table)
            for column in columns:
                if column.name not in present:
                    conn.execute(add_column_ddl(table, column))
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION:d}")


# ---------------------------------------------------------------------------
# Opening
# ---------------------------------------------------------------------------


def database_path(project_root: Path | None = None) -> Path:
    """Return the ledger's path for one repository.

    ``dh_paths.state_root`` derives its slug from the git common directory, so a linked worktree
    and the main checkout resolve to the same file.

    Args:
        project_root: The repository root; auto-detected from the process when absent.

    Returns:
        The absolute path of the database file.
    """
    return dh_paths.state_root(project_root) / DATABASE_NAME


def mountinfo_types(text: str) -> list[tuple[str, str]]:
    """Parse ``/proc/self/mountinfo`` into mount points and filesystem types.

    Args:
        text: The file's contents.

    Returns:
        One ``(mount point, filesystem type)`` pair per line it could parse.
    """
    found: list[tuple[str, str]] = []
    for line in text.splitlines():
        head, _, tail = line.partition(" - ")
        fields = head.split()
        rest = tail.split()
        if len(fields) > MOUNT_POINT_FIELD and rest:
            found.append((fields[MOUNT_POINT_FIELD], rest[0]))
    return found


def mount_command_types(text: str) -> list[tuple[str, str]]:
    """Parse ``mount`` output into mount points and filesystem types.

    Two forms are read: GNU's ``device on /point type nfs4 (opts)`` and BSD's
    ``device on /point (nfs, opts)``.

    Args:
        text: The command's stdout.

    Returns:
        One ``(mount point, filesystem type)`` pair per line it could parse.
    """
    found: list[tuple[str, str]] = []
    for line in text.splitlines():
        _, separator, tail = line.partition(" on ")
        if not separator:
            continue
        point, marker, remainder = tail.partition(" type ")
        if marker:
            found.append((point, remainder.split()[0] if remainder.split() else ""))
            continue
        point, marker, remainder = tail.partition(" (")
        if marker:
            found.append((point, remainder.split(",")[0].rstrip(")").strip()))
    return found


def mount_table() -> list[tuple[str, str]]:
    """Read the host's mount table.

    ``/proc/self/mountinfo`` is read where it exists. Otherwise ``mount`` is run, bounded by
    :data:`MOUNT_TIMEOUT_SECONDS`. An empty list means the search found no table, not that the
    host has no mounts.

    Returns:
        One ``(mount point, filesystem type)`` pair per mount the search found.
    """
    if MOUNT_INFO.exists():
        return mountinfo_types(MOUNT_INFO.read_text(encoding="utf-8", errors="replace"))
    executable = shutil.which("mount")
    if executable is None:
        return []
    try:
        completed = subprocess.run(
            [executable], capture_output=True, text=True, timeout=MOUNT_TIMEOUT_SECONDS, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return mount_command_types(completed.stdout)


def filesystem_type(path: Path) -> str:
    """Name the filesystem type of the mount holding a path.

    Args:
        path: The path to locate; it need not exist, but its parents should.

    Returns:
        The type reported by the deepest mount point that is a prefix of the path, or an empty
        string when the mount table could not be read or held no matching entry.
    """
    target = path.expanduser().absolute()
    best_point = ""
    best_type = ""
    for point, kind in mount_table():
        mount_path = Path(point)
        if (target == mount_path or target.is_relative_to(mount_path)) and len(point) >= len(best_point):
            best_point, best_type = point, kind
    return best_type


def check_local_filesystem(path: Path) -> None:
    """Refuse to open a ledger on a mount where WAL cannot share its index.

    Args:
        path: The database path.

    Raises:
        Refusal: With ``network-filesystem`` when the mount's type is in
            ``ledger_spec.NETWORK_FILESYSTEMS``.
    """
    if filesystem_type(path) in ledger_spec.NETWORK_FILESYSTEMS:
        raise Refusal("network-filesystem")


def connect(path: Path, *, busy_timeout_ms: int = BUSY_TIMEOUT_MS) -> sqlite3.Connection:
    """Open one connection to a ledger file in WAL mode.

    The connection runs in autocommit mode so :func:`transaction` can issue its own
    ``BEGIN IMMEDIATE``; Python's implicit transaction handling would otherwise open a deferred
    transaction first and turn a write conflict into a late failure.

    Args:
        path: The database path.
        busy_timeout_ms: How long a writer waits for another writer's lock.

    Returns:
        The open connection.
    """
    conn = sqlite3.connect(path, timeout=busy_timeout_ms / 1000, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute(f"PRAGMA busy_timeout = {busy_timeout_ms:d}")
    return conn


def open_ledger(
    path: Path | None = None, *, project_root: Path | None = None, busy_timeout_ms: int = BUSY_TIMEOUT_MS
) -> sqlite3.Connection:
    """Open the repository's ledger, creating the file and the schema when they are absent.

    Args:
        path: An explicit database path; :func:`database_path` resolves one when absent.
        project_root: The repository root, used only when ``path`` is absent.
        busy_timeout_ms: How long a writer waits for another writer's lock.

    Returns:
        An open connection with the schema present.

    Raises:
        Refusal: With ``network-filesystem`` when the mount holding the database has a type in
            ``ledger_spec.NETWORK_FILESYSTEMS``.
    """
    resolved = path if path is not None else database_path(project_root)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    check_local_filesystem(resolved)
    conn = connect(resolved, busy_timeout_ms=busy_timeout_ms)
    ensure_schema(conn)
    return conn


# ---------------------------------------------------------------------------
# Transactions and the log
# ---------------------------------------------------------------------------


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a block inside one ``BEGIN IMMEDIATE`` transaction.

    The write lock is taken on entry rather than on the first write, so two writers of the same
    row contend at the start of the block instead of at its end. Entering while a transaction is
    already open joins it rather than nesting, so a command may call another command's helper
    without either committing half of the other's work.

    Args:
        conn: An open ledger connection.

    Yields:
        The same connection, inside the transaction.
    """
    if conn.in_transaction:
        yield conn
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.rollback()
        raise
    conn.commit()


def append_event(
    conn: sqlite3.Connection, *, kind: str, plan: str, task: str | None, payload: Mapping[str, Any], at: datetime
) -> int:
    """Append one row to the append-only log, stamped with the transition's own moment.

    The caller applies the transition's effects to the materialised tables inside the same
    transaction; this writes the log entry only. ``at`` is the instant the caller sampled for those
    effects rather than one taken here, so ``events.at`` is the moment the transition acted and
    :func:`fold_events` can read ``ledger_spec.INSTANT_COLUMNS`` back out of it. Sampling a second
    instant here would put the log a few milliseconds — or, behind a busy writer, seconds — away
    from the row it describes.

    Args:
        conn: An open ledger connection, inside the caller's transaction.
        kind: An event kind from ``ledger_spec.EVENTS``.
        plan: The plan the event belongs to.
        task: The task the event belongs to, or None for a plan-scoped event.
        payload: The event payload, stored as JSON.
        at: The instant the transition sampled inside its transaction.

    Returns:
        The sequence number the log assigned.
    """
    cursor = conn.execute(
        "INSERT INTO events (at, kind, plan, task, payload) VALUES (:at, :kind, :plan, :task, :payload)",
        {
            "at": timestamp(at),
            "kind": kind,
            "plan": plan,
            "task": task,
            "payload": json.dumps(dict(payload), default=str, sort_keys=True),
        },
    )
    return int(cursor.lastrowid or 0)


def last_seq(conn: sqlite3.Connection, plan: str) -> int:
    """Return the highest log sequence number recorded for one plan.

    Args:
        conn: An open ledger connection.
        plan: The plan id.

    Returns:
        The sequence number, or zero when the plan has no events.
    """
    found = rows_of(conn.execute("SELECT COALESCE(MAX(seq), 0) AS top FROM events WHERE plan = :plan", {"plan": plan}))
    return int(found[0]["top"])


def events_of(conn: sqlite3.Connection, plan: str, *, task: str | None = None, kind: str = "") -> list[dict[str, Any]]:
    """Read a plan's log entries, oldest first, with the payload decoded.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: Restrict to one task when given.
        kind: Restrict to one event kind when given.

    Returns:
        One dictionary per event, its ``payload`` a decoded mapping.
    """
    clauses = ["plan = :plan"]
    parameters: dict[str, Any] = {"plan": plan}
    if task is not None:
        clauses.append("task = :task")
        parameters["task"] = task
    if kind:
        clauses.append("kind = :kind")
        parameters["kind"] = kind
    words = ["SELECT seq, at, kind, plan, task, payload FROM events WHERE", " AND ".join(clauses), "ORDER BY seq"]
    found = rows_of(conn.execute(" ".join(words), parameters))
    for row in found:
        raw = row["payload"]
        row["payload"] = json.loads(raw) if isinstance(raw, str) else raw
    return found


# ---------------------------------------------------------------------------
# The fold: every materialised table, rebuilt from the log alone
# ---------------------------------------------------------------------------
#
# ``ledger_spec.COLUMNS`` says which event kinds set each column and ``ledger_spec.EVENTS`` says
# what each kind's payload carries. One handler per kind turns that pair into the write the
# transition made, and :func:`fold_events` replays them in ``seq`` order. Nothing here reads a
# materialised table: the only inputs are the events, their payloads, and their ``at``.


def all_events(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Read the whole log, oldest first, with each payload decoded.

    Args:
        conn: An open ledger connection.

    Returns:
        One dictionary per event, its ``payload`` a decoded mapping.
    """
    found = rows_of(conn.execute("SELECT seq, at, kind, plan, task, payload FROM events ORDER BY seq"))
    for row in found:
        raw = row["payload"]
        row["payload"] = json.loads(raw) if isinstance(raw, str) else raw
    return found


def blank_row(table: str) -> dict[str, Any]:
    """Build one row of a materialised table holding the value its DDL would default to.

    Args:
        table: The table name.

    Returns:
        Every stored column of that table, null where the column admits null and the DDL default
        otherwise, so a fold that fills the columns an event carries leaves the rest as the schema
        would have.
    """
    return {
        column.name: (None if nullable(column) else (0 if affinity(column) == INTEGER else ""))
        for column in TABLES[table]
    }


COLUMN_NAMES: dict[str, frozenset[str]] = {
    table: frozenset(column.name for column in columns) for table, columns in TABLES.items()
}
"""The stored column names of each materialised table, for sieving a payload down to them."""

PLAN_OF: dict[str, str] = {"plans": "plan_id", "tasks": "plan", "sections": "plan", "export_cursors": "plan"}
"""The column of each materialised table that names the plan its row belongs to."""

Folded = dict[str, dict[tuple[Any, ...], dict[str, Any]]]
"""Every materialised row a fold has built so far, keyed by table and then by primary key."""


def key_of(table: str, row: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return one row's identity, as :data:`PRIMARY_KEYS` defines it.

    Args:
        table: The table the row belongs to.
        row: The row.

    Returns:
        The primary key values, in order.
    """
    return tuple(row[name] for name in PRIMARY_KEYS[table])


def carried(table: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the part of a payload that names stored columns of one table.

    Args:
        table: The table name.
        payload: The event payload.

    Returns:
        The payload entries whose keys are stored columns of that table.
    """
    return {name: value for name, value in payload.items() if name in COLUMN_NAMES[table]}


def changed_values(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Decode a ``*.fields`` payload's ``changed`` mapping the way the transition stored it.

    Args:
        payload: A ``plan.fields`` or ``task.fields`` payload.

    Returns:
        The changed columns with list and mapping values rendered as JSON text, which is how
        ``transitions.field_assignments`` binds them.
    """
    changed = payload.get("changed") or {}
    return {name: encode(value) for name, value in changed.items()} if isinstance(changed, dict) else {}


def clear_rows(tables: Folded, table: str, plan: str) -> None:
    """Drop every row of one plan from one folded table.

    Args:
        tables: The fold's tables.
        table: The table to empty.
        plan: The plan whose rows go.
    """
    column = PLAN_OF[table]
    for key in [key for key, row in tables[table].items() if str(row[column]) == plan]:
        del tables[table][key]


def task_rows_of(tables: Folded, plan: str) -> list[dict[str, Any]]:
    """Return every folded task row of one plan.

    Args:
        tables: The fold's tables.
        plan: The plan id.

    Returns:
        The rows, in insertion order.
    """
    return [row for row in tables["tasks"].values() if str(row["plan"]) == plan]


def task_of(tables: Folded, event: Mapping[str, Any]) -> dict[str, Any]:
    """Return the folded task row one task-scoped event addresses.

    Args:
        tables: The fold's tables.
        event: The event.

    Returns:
        The row.

    Raises:
        LookupError: When the log moves a task no earlier event created, which means the log is
            not self-contained and the fold would otherwise invent a row.
    """
    key = (str(event["plan"]), str(event["task"]))
    row = tables["tasks"].get(key)
    if row is None:
        msg = f"event {event['seq']} ({event['kind']}) addresses {key[0]}/{key[1]}, which no earlier event created"
        raise LookupError(msg)
    return row


def plan_of(tables: Folded, event: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return the folded plan row one plan-scoped event addresses, or None when there is none.

    Args:
        tables: The fold's tables.
        event: The event.

    Returns:
        The row, or None.
    """
    return tables["plans"].get((str(event["plan"]),))


def cleared_attempt() -> dict[str, Any]:
    """Return the columns ``_clear_attempt_effects`` sets, as the specification lists them.

    Returns:
        The attempt-closing columns and their values.
    """
    return {"attempt_open": 0, "result": None, "note": None, "settled": 0, "return_text": None, "completed": None}


def fold_plan_created(tables: Folded, event: Mapping[str, Any]) -> None:
    """Install the ``plans`` row a ``plan.created`` payload carries."""
    row = blank_row("plans")
    row.update(carried("plans", event["payload"]))
    row["plan_id"] = str(event["plan"])
    row["archived"] = None
    tables["plans"][key_of("plans", row)] = row


def fold_plan_replaced(tables: Folded, event: Mapping[str, Any]) -> None:
    """Empty the tables a replace emptied and write the plan row it wrote.

    ``replaced`` names the plan whose rows went, which is the incoming id except when the
    ``exists`` check matched on milestone instead. The row itself is written by an UPDATE keyed on
    the incoming id, so a replace that matched a differently-identified plan changes nothing —
    which is what the fold does when that id holds no row.
    """
    payload = event["payload"]
    for table in payload.get("clears") or ():
        clear_rows(tables, str(table), str(payload.get("replaced") or event["plan"]))
    key = (str(event["plan"]),)
    if key not in tables["plans"]:
        return
    row = blank_row("plans")
    row.update(carried("plans", payload))
    row["plan_id"] = str(event["plan"])
    row["archived"] = None
    tables["plans"][key] = row


def fold_plan_fields(tables: Folded, event: Mapping[str, Any]) -> None:
    """Apply a ``plan.fields`` payload's ``changed`` mapping to the plan row."""
    row = plan_of(tables, event)
    if row is not None:
        row.update(changed_values(event["payload"]))


def fold_plan_archived(tables: Folded, event: Mapping[str, Any]) -> None:
    """Stamp ``plans.archived`` with the event's instant and close every attempt on the plan."""
    row = plan_of(tables, event)
    if row is not None:
        row["archived"] = str(event["at"])
    for task in task_rows_of(tables, str(event["plan"])):
        task["attempt_open"] = 0


def fold_cursor(tables: Folded, event: Mapping[str, Any]) -> None:
    """Write the ``export_cursors`` row a ``plan.exported`` or ``plan.imported`` payload carries."""
    payload = event["payload"]
    row = blank_row("export_cursors")
    row.update(
        plan=str(event["plan"]),
        target=str(payload["target"]),
        last_seq=int(payload["last_seq"]),
        revision=payload["revision"],
        projection_hash=payload["projection_hash"],
    )
    tables["export_cursors"][key_of("export_cursors", row)] = row


def new_task_row(event: Mapping[str, Any]) -> dict[str, Any]:
    """Build the ``tasks`` row a ``task.added`` or ``task.imported`` payload carries.

    Args:
        event: The event, with its decoded payload.

    Returns:
        Every column of ``tasks``: the payload's own, and the lease and outcome columns a task
        that has never been dispatched holds.
    """
    row = blank_row("tasks")
    row.update(carried("tasks", event["payload"]))
    row["plan"] = str(event["plan"])
    row["id"] = str(event["task"])
    row.update(
        attempt_open=0,
        ttl_seconds=None,
        worktree=None,
        expires=None,
        first_renewed=None,
        result=None,
        note=None,
        settled=0,
        return_text=None,
        response=None,
    )
    return row


def fold_task_added(tables: Folded, event: Mapping[str, Any]) -> None:
    """Install a task the ``append-task`` effect describes: no attempts, nothing accepted."""
    row = new_task_row(event)
    row.update(attempts=0, accepted=0)
    tables["tasks"][key_of("tasks", row)] = row


def fold_task_imported(tables: Folded, event: Mapping[str, Any]) -> None:
    """Install an imported task and its sections, tagged as the ``import`` transition tags them."""
    row = new_task_row(event)
    tables["tasks"][key_of("tasks", row)] = row
    for index, section in enumerate(event["payload"].get("sections") or [], start=1):
        entry = blank_row("sections")
        entry.update(
            plan=str(event["plan"]),
            task=str(event["task"]),
            name=str(section["name"]),
            attempt=IMPORTED_SECTION_ATTEMPT,
            content=str(section["content"]),
            seq=index,
        )
        tables["sections"][key_of("sections", entry)] = entry


def fold_task_section(tables: Folded, event: Mapping[str, Any]) -> None:
    """Append one section row, numbered as ``transitions.next_section_seq`` numbers it."""
    payload = event["payload"]
    plan, task = str(event["plan"]), str(event["task"])
    held = [row["seq"] for row in tables["sections"].values() if str(row["plan"]) == plan and str(row["task"]) == task]
    entry = blank_row("sections")
    entry.update(
        plan=plan,
        task=task,
        name=str(payload["name"]),
        attempt=int(payload["attempt"]),
        content=str(payload["content"]),
        seq=max([int(value) for value in held], default=0) + 1,
    )
    tables["sections"][key_of("sections", entry)] = entry


def fold_task_fields(tables: Folded, event: Mapping[str, Any]) -> None:
    """Apply a ``task.fields`` payload's ``changed`` mapping to the task row."""
    task_of(tables, event).update(changed_values(event["payload"]))


def fold_task_dispatched(tables: Folded, event: Mapping[str, Any]) -> None:
    """Open an attempt: the lease from the event's instant, the attempt columns cleared."""
    payload = event["payload"]
    row = task_of(tables, event)
    instant = moment(event["at"])
    ttl = int(payload["ttl_seconds"]) if payload["ttl_seconds"] is not None else DEFAULT_TTL_SECONDS
    row.update(cleared_attempt())
    row.update(
        status=IN_PROGRESS,
        attempts=int(payload["attempt"]),
        attempt_open=1,
        ttl_seconds=payload["ttl_seconds"],
        worktree=payload["worktree"],
        expires=timestamp(instant + timedelta(seconds=ttl)) if instant is not None else None,
        first_renewed=None,
        started=str(event["at"]),
        last_activity=str(event["at"]),
    )


def fold_lease_renewed(tables: Folded, event: Mapping[str, Any]) -> None:
    """Push the lease out from the event's instant, as ``_renew_effects`` names it."""
    row = task_of(tables, event)
    instant = moment(event["at"])
    ttl = int(row["ttl_seconds"] or DEFAULT_TTL_SECONDS)
    if instant is not None:
        row["expires"] = timestamp(instant + timedelta(seconds=ttl))
    row["last_activity"] = str(event["at"])
    if row["first_renewed"] is None:
        row["first_renewed"] = str(event["at"])


def fold_task_finished(tables: Folded, event: Mapping[str, Any]) -> None:
    """Close the attempt with its outcome; ``completed`` only when the result was complete."""
    payload = event["payload"]
    row = task_of(tables, event)
    result = str(payload["result"])
    row.update(status=RESULT_STATUS[result], attempt_open=0, result=result, note=payload["note"])
    if result == COMPLETE:
        row["completed"] = str(event["at"])


def fold_task_settled(tables: Folded, event: Mapping[str, Any]) -> None:
    """Record what the harness returned, closing the attempt when the task was still in progress."""
    row = task_of(tables, event)
    if row["status"] == IN_PROGRESS:
        row["attempt_open"] = 0
    row.update(settled=1, return_text=event["payload"]["return_text"])


def fold_task_accepted(tables: Folded, event: Mapping[str, Any]) -> None:
    """Mark the task accepted."""
    task_of(tables, event)["accepted"] = 1


def fold_task_reclaimed(tables: Folded, event: Mapping[str, Any]) -> None:
    """Send the task back to not-started with its attempt budget and the orchestrator's response."""
    payload = event["payload"]
    row = task_of(tables, event)
    row.update(cleared_attempt())
    row.update(
        status=NOT_STARTED, attempts_allowed=int(payload["attempts_allowed"]), accepted=0, response=payload["response"]
    )


def fold_task_state(tables: Folded, event: Mapping[str, Any]) -> None:
    """Move the task to the status the payload names, with the acceptance and lease it left."""
    payload = event["payload"]
    row = task_of(tables, event)
    status = str(payload["status"])
    row.update(status=status, accepted=int(payload["accepted"]), attempt_open=int(payload["attempt_open"]))
    if status == COMPLETE:
        row["completed"] = str(event["at"])


HANDLERS: dict[str, Any] = {
    "plan.created": fold_plan_created,
    "plan.replaced": fold_plan_replaced,
    "plan.fields": fold_plan_fields,
    "plan.archived": fold_plan_archived,
    "plan.imported": fold_cursor,
    "plan.exported": fold_cursor,
    "task.added": fold_task_added,
    "task.imported": fold_task_imported,
    "task.fields": fold_task_fields,
    "task.section": fold_task_section,
    "task.dispatched": fold_task_dispatched,
    "lease.renewed": fold_lease_renewed,
    "task.finished": fold_task_finished,
    "task.settled": fold_task_settled,
    "task.accepted": fold_task_accepted,
    "task.reclaimed": fold_task_reclaimed,
    "task.state": fold_task_state,
}
"""One handler per ``ledger_spec.EVENTS`` kind; :func:`check_handlers` runs at import."""


def check_handlers() -> None:
    """Reject a fold that does not handle every event kind the specification declares.

    Raises:
        ValueError: When a kind has no handler, or a handler names a kind the specification does
            not declare.
    """
    declared = {event.kind for event in ledger_spec.EVENTS}
    missing = sorted(declared - set(HANDLERS))
    if missing:
        msg = f"the fold has no handler for {', '.join(missing)}, which ledger_spec.EVENTS declares"
        raise ValueError(msg)
    unknown = sorted(set(HANDLERS) - declared)
    if unknown:
        msg = f"the fold handles {', '.join(unknown)}, which ledger_spec.EVENTS does not declare"
        raise ValueError(msg)


check_handlers()


def fold_events(events: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Replay the log into the materialised tables.

    Args:
        events: Every event, oldest first, each with a decoded ``payload`` and its ``at``.

    Returns:
        One list of rows per materialised table, ordered by primary key.

    Raises:
        ValueError: When an event carries a kind ``ledger_spec.EVENTS`` does not declare.
    """
    tables: Folded = {table: {} for table in TABLES}
    for event in events:
        kind = str(event["kind"])
        handler = HANDLERS.get(kind)
        if handler is None:
            msg = f"event {event['seq']} carries kind {kind}, which ledger_spec.EVENTS does not declare"
            raise ValueError(msg)
        handler(tables, event)
    return {table: [rows[key] for key in sorted(rows, key=str)] for table, rows in tables.items()}


def rebuild(conn: sqlite3.Connection) -> None:
    """Empty every materialised table and write it back from the log alone.

    The rows go and the columns stay: the tables are emptied rather than dropped, so a column an
    older schema left behind — which :func:`ensure_schema` keeps on purpose — is still there
    afterwards. The whole rebuild is one transaction, so a reader either sees the tables the
    transitions wrote or the tables the fold wrote, never half of each.

    Args:
        conn: An open ledger connection.
    """
    folded = fold_events(all_events(conn))
    with transaction(conn):
        for table in TABLES:
            words = ["DELETE FROM", table]
            conn.execute(" ".join(words))
        for table, rows in folded.items():
            if not rows:
                continue
            columns = [column.name for column in TABLES[table]]
            conn.executemany(insert_statement(table, columns), [{name: row[name] for name in columns} for row in rows])
