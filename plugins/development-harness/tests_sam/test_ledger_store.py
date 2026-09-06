"""Conformance tests for the ledger's database: where it lives, and how it is opened.

``dh_core.ledger_spec`` is the contract these drive ``dh_core.ledger.store`` through. Four
properties of the store are exercised here, each one the specification states rather than the
implementation's own convenience:

``dispatch`` is single-winner across processes
    ``ledger_spec.TRANSITIONS`` gives ``dispatch`` from ``not-started`` the checks ``archived``,
    ``leased`` and ``not-ready``, and the effect ``attempts + 1``. Sixteen separate operating
    system processes race one ready task through it; exactly one exits zero holding attempt 1 and
    the rest refuse with a ``ledger_spec.REASONS`` code of kind ``REFUSAL``.

one database per repository, not per checkout
    ``store.database_path`` resolves through ``dh_paths.state_root``, whose slug derives from the
    git common directory, so a linked worktree and its main checkout address one file.

``network-filesystem``
    ``ledger_spec.REASONS`` gives the code the condition "the mount holding the database path has
    a type in ``NETWORK_FILESYSTEMS``". The mount lookup is monkeypatched so every type in that
    tuple is exercised without needing the mount.

additive migration
    A database written by a previous schema version opens: every column the specification has
    gained since is added with the default its type implies, every row and every event survives,
    and a column the specification no longer declares is left in place.

the lease clock under write-lock contention
    ``ledger_spec.TRANSITIONS`` gives ``dispatch`` the effect ``expires = now + ttl_seconds`` and
    ``renew`` the same expression, and ``ledger_spec.COLUMNS`` derives ``tasks.expired`` as
    "attempt_open is 1 and now is past expires" and ``tasks.renew_by`` as "expires when
    attempt_open is 1". Together they say a command that opens or renews an attempt leaves a
    deadline in the future: a lease that is expired the instant it is granted is not a lease.
    :func:`transaction` waits up to :data:`store.BUSY_TIMEOUT_MS` for another writer, so these put
    one command behind another and read the derived columns back.

Not covered, because it does not exist: a fold that rebuilds the materialised tables from the log.
``dh_core.ledger`` has no ``Ledger`` class and no ``fold``, and ``dh_core/ledger/store.py`` says in
its own module docstring why: the ``ledger_spec.EVENTS`` payloads carry no value for the columns
their events set. ``plan.replaced`` is the plainest case — ``ledger_spec.COLUMNS`` names it in the
``set_by`` of every ``plans`` column, and its payload is ``source`` and ``revision``.
"""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

import dh_paths
import pytest
from dh_core import ledger_spec
from dh_core.ledger import derive, store, transitions

if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Callable

    from dh_core.ledger.transitions import TransitionResult

PLUGIN_ROOT = Path(store.__file__).resolve().parents[2]
"""The directory that must be on a child process's ``sys.path`` for ``dh_core`` to import."""

RACERS = 16
"""How many separate processes race one dispatch."""

START_TIMEOUT_SECONDS = 120.0
"""How long the parent waits for every racer to open the ledger before opening the gate."""

WAIT_TIMEOUT_SECONDS = 120.0
"""How long the parent waits for one racer to finish after the gate opens."""

POLL_SECONDS = 0.01
"""How often the parent counts the racers that have signalled ready."""

WINNER_ATTEMPT = 1
"""The attempt number the one winning dispatch prints, from ``attempts + 1`` on a fresh task."""

REFUSALS_ALLOWED = frozenset({"leased", "not-ready"})
"""The ``dispatch`` checks a loser can fail once the winner holds the attempt."""

WORKER_SOURCE = '''"""Race one dispatch from a separate process and exit with its outcome.

Written to a temporary file by ``test_sixteen_processes_race_one_dispatch`` and run through a
fresh interpreter, so the contention is between operating system processes rather than threads
sharing one connection.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

plugin_root, database, plan, task, ready_dir, gate = sys.argv[1:7]
sys.path.insert(0, plugin_root)

from dh_core.ledger import store, transitions

connection = store.open_ledger(path=Path(database))
Path(ready_dir, str(os.getpid())).write_text("", encoding="utf-8")
opened = Path(gate)
while not opened.exists():
    time.sleep(0.002)
try:
    outcome = transitions.dispatch(connection, plan, task)
except store.Refusal as refusal:
    sys.stdout.write("refused:" + refusal.reason)
    sys.exit(1)
sys.stdout.write("attempt:" + str(outcome.attempt))
sys.exit(0)
'''

LEGACY_ABSENT: dict[str, frozenset[str]] = {
    "plans": frozenset({"base_sha", "quality_gates"}),
    "tasks": frozenset({"response", "return_text", "settled"}),
    "sections": frozenset({"content"}),
    "export_cursors": frozenset({"revision"}),
}
"""One or more columns per materialised table that a previous schema version did not have.

Each name is a stored ``ledger_spec.COLUMNS`` entry that is not part of the store's primary key
for its table, so a table without it is still a table the previous version could write.
"""

LEGACY_ONLY_COLUMN = "legacy_note"
"""A column no ``ledger_spec.COLUMNS`` entry declares, to prove migration deletes nothing."""


def user_version(connection: sqlite3.Connection) -> int:
    """Read ``PRAGMA user_version`` from an open connection.

    Args:
        connection: Any open SQLite connection.

    Returns:
        The stored schema version number.
    """
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def mount_table_of(*entries: tuple[str, str]):
    """Build a stand-in for ``store.mount_table``.

    Args:
        entries: ``(mount point, filesystem type)`` pairs the stand-in reports.

    Returns:
        A callable returning those pairs, suitable for ``monkeypatch.setattr``.
    """
    listed = list(entries)
    return lambda: list(listed)


def git(*arguments: str, cwd: Path) -> None:
    """Run one git command in a directory, failing the test on a non-zero exit.

    Args:
        arguments: The git arguments, without the executable name.
        cwd: The working directory to run in.
    """
    subprocess.run(["git", *arguments], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def one_ready_task(tmp_path: Path) -> tuple[Path, str, str]:
    """Build a ledger holding one plan whose single task is ready to dispatch.

    Args:
        tmp_path: The test's temporary directory.

    Returns:
        The database path, the plan id, and the task id.
    """
    database = tmp_path / "ledger" / store.DATABASE_NAME
    connection = store.open_ledger(path=database)
    try:
        created = transitions.create(
            connection, slug="race", goal="one runner wins", tasks=[{"id": "T1", "title": "the prize"}]
        )
    finally:
        connection.close()
    return database, str(created.plan), "T1"


@pytest.fixture
def fixture_repository(tmp_path: Path) -> tuple[Path, Path]:
    """Build a git repository with one linked worktree.

    Args:
        tmp_path: The test's temporary directory.

    Returns:
        The main checkout's root and the linked worktree's root.
    """
    if shutil.which("git") is None:
        pytest.skip("git is not on PATH, so a worktree fixture cannot be built")
    main = tmp_path / "main"
    main.mkdir()
    git("init", "--initial-branch=main", cwd=main)
    git("config", "user.email", "ledger@example.invalid", cwd=main)
    git("config", "user.name", "Ledger Test", cwd=main)
    git("config", "commit.gpgsign", "false", cwd=main)
    git("commit", "--allow-empty", "--message", "root", cwd=main)
    linked = tmp_path / "linked"
    git("worktree", "add", "--quiet", "-b", "side", str(linked), cwd=main)
    return main, linked


# ---------------------------------------------------------------------------
# dispatch under contention between processes
# ---------------------------------------------------------------------------


def test_sixteen_processes_race_one_dispatch(tmp_path: Path, one_ready_task: tuple[Path, str, str]) -> None:
    """Sixteen processes race one ready task; one wins attempt 1 and fifteen refuse."""
    database, plan, task = one_ready_task
    worker = tmp_path / "race_worker.py"
    worker.write_text(WORKER_SOURCE, encoding="utf-8")
    ready_dir = tmp_path / "ready"
    ready_dir.mkdir()
    gate = tmp_path / "gate"

    command = [sys.executable, str(worker), str(PLUGIN_ROOT), str(database), plan, task, str(ready_dir), str(gate)]
    processes = [
        subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(RACERS)
    ]
    try:
        deadline = time.monotonic() + START_TIMEOUT_SECONDS
        while len(list(ready_dir.iterdir())) < RACERS and time.monotonic() < deadline:
            time.sleep(POLL_SECONDS)
        assert len(list(ready_dir.iterdir())) == RACERS, "not every racer opened the ledger before the gate opened"
        gate.write_text("", encoding="utf-8")
        spoken = [process.communicate(timeout=WAIT_TIMEOUT_SECONDS) for process in processes]
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()

    codes = [process.returncode for process in processes]
    said = [out.strip() for out, _ in spoken]
    complaints = [err.strip() for _, err in spoken if err.strip()]
    assert set(codes) <= {0, 1}, f"a racer neither won nor refused: {complaints}"

    winners = [text for code, text in zip(codes, said, strict=True) if code == 0]
    losers = [text for code, text in zip(codes, said, strict=True) if code != 0]
    assert winners == [f"attempt:{WINNER_ATTEMPT}"], f"exactly one racer must win: {said}"
    assert len(losers) == RACERS - 1
    assert {text.removeprefix("refused:") for text in losers} <= REFUSALS_ALLOWED, f"unexpected refusals: {losers}"

    connection = store.open_ledger(path=database)
    try:
        row = store.fetch_task(connection, plan, task)
        assert row["attempts"] == WINNER_ATTEMPT
        assert row["attempt_open"] == 1
        assert row["status"] == ledger_spec.Status.IN_PROGRESS.value
        assert len(store.events_of(connection, plan, task=task, kind="task.dispatched")) == 1
    finally:
        connection.close()


def test_every_refusal_a_loser_prints_is_a_refusal_in_the_specification() -> None:
    """The codes a losing racer may print are ``REFUSAL`` reasons of the ``dispatch`` transition."""
    kinds = {reason.code: reason.kind for reason in ledger_spec.REASONS}
    assert all(kinds[code] is ledger_spec.ReasonKind.REFUSAL for code in REFUSALS_ALLOWED)
    entry = next(
        transition
        for transition in ledger_spec.TRANSITIONS
        if transition.command == "dispatch" and transition.from_status == ledger_spec.Status.NOT_STARTED
    )
    assert {check.reason for check in entry.checks} >= REFUSALS_ALLOWED


# ---------------------------------------------------------------------------
# one database per repository
# ---------------------------------------------------------------------------


def test_a_worktree_and_its_main_checkout_resolve_to_one_database_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fixture_repository: tuple[Path, Path]
) -> None:
    """The path resolved from inside a linked worktree is the path resolved from the main checkout."""
    main, linked = fixture_repository
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "state"))
    for name in (
        "DH_PROJECT_ROOT",
        "WORKSPACE_FOLDER_PATHS",
        "CURSOR_PROJECT_ROOT",
        "CLAUDE_PROJECT_DIR",
        "DH_CODEX_MCP",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.chdir(main)
    from_main = store.database_path()
    monkeypatch.chdir(linked)
    from_worktree = store.database_path()

    assert from_worktree == from_main
    assert from_main.parent == dh_paths.state_root(main.resolve())
    assert from_main.name == store.DATABASE_NAME


def test_a_worktree_and_its_main_checkout_open_the_same_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fixture_repository: tuple[Path, Path]
) -> None:
    """A plan created from the main checkout is read back from inside the linked worktree."""
    main, linked = fixture_repository
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "state"))
    for name in (
        "DH_PROJECT_ROOT",
        "WORKSPACE_FOLDER_PATHS",
        "CURSOR_PROJECT_ROOT",
        "CLAUDE_PROJECT_DIR",
        "DH_CODEX_MCP",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.chdir(main)
    from_main = store.open_ledger()
    try:
        created = transitions.create(from_main, slug="shared", goal="one file per repository")
    finally:
        from_main.close()

    monkeypatch.chdir(linked)
    from_worktree = store.open_ledger()
    try:
        assert store.fetch_plan(from_worktree, str(created.plan))["feature"] == "shared"
    finally:
        from_worktree.close()


# ---------------------------------------------------------------------------
# network-filesystem
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ledger_spec.NETWORK_FILESYSTEMS)
def test_opening_on_a_network_filesystem_refuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    """Every type in ``NETWORK_FILESYSTEMS`` refuses with ``network-filesystem`` and writes nothing."""
    share = tmp_path / "share"
    database = share / store.DATABASE_NAME
    monkeypatch.setattr(store, "mount_table", mount_table_of(("/", "ext4"), (str(share), kind)))

    assert store.filesystem_type(database) == kind
    with pytest.raises(store.Refusal) as raised:
        store.open_ledger(path=database)
    assert raised.value.reason == "network-filesystem"
    assert not database.exists()


def test_opening_on_a_local_filesystem_creates_the_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A mount whose type is not in ``NETWORK_FILESYSTEMS`` opens normally."""
    database = tmp_path / "local" / store.DATABASE_NAME
    monkeypatch.setattr(store, "mount_table", mount_table_of(("/", "ext4")))

    connection = store.open_ledger(path=database)
    try:
        assert database.exists()
        assert user_version(connection) == store.SCHEMA_VERSION
    finally:
        connection.close()


def test_the_deepest_mount_point_names_the_filesystem_type(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A local mount nested inside a network mount decides the type, so the open is allowed."""
    database = tmp_path / "local" / store.DATABASE_NAME
    monkeypatch.setattr(store, "mount_table", mount_table_of(("/", "nfs4"), (str(tmp_path), "ext4")))

    assert store.filesystem_type(database) == "ext4"
    connection = store.open_ledger(path=database)
    connection.close()


def test_an_unreadable_mount_table_does_not_refuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty mount table names no type, and a type that is not network is not a refusal."""
    database = tmp_path / "unknown" / store.DATABASE_NAME
    monkeypatch.setattr(store, "mount_table", mount_table_of())

    assert store.filesystem_type(database) == ""
    connection = store.open_ledger(path=database)
    connection.close()


# ---------------------------------------------------------------------------
# a database written by a previous schema version
# ---------------------------------------------------------------------------


def legacy_table_ddl(table: str) -> str:
    """Assemble the ``CREATE TABLE`` a previous schema version would have written.

    Args:
        table: The materialised table name.

    Returns:
        The statement, with the columns in :data:`LEGACY_ABSENT` for that table left out.
    """
    absent = LEGACY_ABSENT[table]
    parts = [store.column_ddl(column) for column in store.TABLES[table] if column.name not in absent]
    key = store.PRIMARY_KEYS.get(table)
    if key:
        parts.append("PRIMARY KEY (" + ", ".join(key) + ")")
    return " ".join(["CREATE TABLE", table, "(", ", ".join(parts), ")"])


def write_previous_version(database: Path, *, version: int) -> None:
    """Write a database in the shape a previous schema version left behind.

    Args:
        database: The file to create.
        version: The ``PRAGMA user_version`` that version stamped.
    """
    connection = sqlite3.connect(database)
    try:
        for table in store.TABLES:
            connection.execute(legacy_table_ddl(table))
        connection.execute(f"ALTER TABLE plans ADD COLUMN {LEGACY_ONLY_COLUMN} TEXT")
        connection.execute(store.EVENTS_DDL)
        connection.execute(
            "INSERT INTO plans (plan_id, feature, state, legacy_note) VALUES ('P1', 'legacy', 'ready', 'kept')"
        )
        connection.execute(
            "INSERT INTO tasks (plan, id, title, status, attempts, attempts_allowed, accepted, attempt_open) "
            "VALUES ('P1', 'T1', 'carried over', 'not-started', 0, 3, 0, 0)"
        )
        connection.execute("INSERT INTO sections (plan, task, name, attempt, seq) VALUES ('P1', 'T1', 'Notes', 0, 1)")
        connection.execute("INSERT INTO export_cursors (plan, target, last_seq) VALUES ('P1', 'content', 1)")
        connection.execute(
            "INSERT INTO events (at, kind, plan, task, payload) "
            "VALUES ('2026-01-01T00:00:00', 'plan.created', 'P1', NULL, '{}')"
        )
        connection.execute(f"PRAGMA user_version = {version:d}")
        connection.commit()
    finally:
        connection.close()


def test_the_previous_version_fixture_really_lacks_the_columns(tmp_path: Path) -> None:
    """The fixture is a genuinely older database: the columns are absent and the stamp differs."""
    database = tmp_path / store.DATABASE_NAME
    previous = store.SCHEMA_VERSION - 1
    write_previous_version(database, version=previous)

    connection = sqlite3.connect(database)
    try:
        assert user_version(connection) == previous
        for table, absent in LEGACY_ABSENT.items():
            assert store.existing_columns(connection, table).isdisjoint(absent)
    finally:
        connection.close()


def test_a_previous_schema_version_opens_and_migrates(tmp_path: Path) -> None:
    """Opening an older database adds every missing column, keeps every row, and restamps it."""
    database = tmp_path / store.DATABASE_NAME
    write_previous_version(database, version=store.SCHEMA_VERSION - 1)

    connection = store.open_ledger(path=database)
    try:
        for table, columns in store.TABLES.items():
            assert {column.name for column in columns} <= store.existing_columns(connection, table)
        assert user_version(connection) == store.SCHEMA_VERSION

        plan = store.fetch_plan(connection, "P1")
        assert plan["feature"] == "legacy"
        assert plan["base_sha"] is None
        assert plan["quality_gates"] == ""
        assert plan[LEGACY_ONLY_COLUMN] == "kept"

        row = store.fetch_task(connection, "P1", "T1")
        assert row["title"] == "carried over"
        assert row["settled"] == 0
        assert row["response"] is None
        assert row["return_text"] is None

        sections = store.rows_of(connection.execute("SELECT * FROM sections"))
        assert [(section["name"], section["content"]) for section in sections] == [("Notes", "")]
        cursors = store.rows_of(connection.execute("SELECT * FROM export_cursors"))
        assert [(cursor["target"], cursor["last_seq"], cursor["revision"]) for cursor in cursors] == [
            ("content", 1, None)
        ]
        assert [event["kind"] for event in store.events_of(connection, "P1")] == ["plan.created"]
    finally:
        connection.close()


def test_a_migrated_database_still_dispatches(tmp_path: Path) -> None:
    """After migration the carried-over task dispatches, so the added columns hold usable defaults."""
    database = tmp_path / store.DATABASE_NAME
    write_previous_version(database, version=store.SCHEMA_VERSION - 1)

    connection = store.open_ledger(path=database)
    try:
        outcome = transitions.dispatch(connection, "P1", "T1")
        assert outcome.attempt == WINNER_ATTEMPT
        assert outcome.status == ledger_spec.Status.IN_PROGRESS.value
        row = store.fetch_task(connection, "P1", "T1")
        assert row["settled"] == 0
        assert row["ttl_seconds"] == next(
            entry.default for entry in ledger_spec.CONFIG if entry.key == "lease.ttl_seconds"
        )
    finally:
        connection.close()


def test_opening_an_up_to_date_database_changes_nothing(tmp_path: Path) -> None:
    """A second open of a current database adds no column and leaves the stamp alone."""
    database = tmp_path / store.DATABASE_NAME
    first = store.open_ledger(path=database)
    try:
        before = {table: store.existing_columns(first, table) for table in store.TABLES}
        transitions.create(first, slug="stable", goal="reopening is idempotent")
    finally:
        first.close()

    second = store.open_ledger(path=database)
    try:
        assert {table: store.existing_columns(second, table) for table in store.TABLES} == before
        assert user_version(second) == store.SCHEMA_VERSION
        assert len(store.rows_of(second.execute("SELECT plan_id FROM plans"))) == 1
    finally:
        second.close()


# ---------------------------------------------------------------------------
# The lease clock under write-lock contention
# ---------------------------------------------------------------------------

LEASE_TTL_SECONDS = 1
"""The lease length the contended command writes; the smallest ``--ttl`` the surface accepts."""

HOLD_SECONDS = 3.0
"""How long the competing writer holds the write lock: longer than the lease it delays."""

LOCK_TIMEOUT_SECONDS = 30.0
"""How long a test waits for the competing writer to take the lock before giving up."""

SETTLE_SECONDS = 0.2
"""A pause after the lock is taken, so the contended command starts behind it."""


def hold_write_lock(database: Path, holding: threading.Event) -> None:
    """Hold the ledger's write lock for :data:`HOLD_SECONDS`, from this thread's own connection.

    The competing writer is ``store.transaction`` itself, which is what every mutating command
    holds for its duration, and which ``store.open_ledger`` takes on every open because
    ``ensure_schema`` runs inside it.

    Args:
        database: The ledger file.
        holding: Set once the lock is held, so the caller knows when to start contending.
    """
    conn = store.open_ledger(database)
    try:
        with store.transaction(conn):
            holding.set()
            time.sleep(HOLD_SECONDS)
    finally:
        conn.close()


def behind_a_writer(database: Path, call: Callable[[], TransitionResult]) -> TransitionResult:
    """Run one ledger command while another writer holds the write lock.

    Args:
        database: The ledger file.
        call: A zero-argument callable running the ledger command under test.

    Returns:
        What the command returned, once the lock it waited for was released.

    Raises:
        AssertionError: When the competing writer never took the lock.
    """
    holding = threading.Event()
    thread = threading.Thread(target=hold_write_lock, args=(database, holding))
    thread.start()
    try:
        assert holding.wait(LOCK_TIMEOUT_SECONDS), "the competing writer never took the write lock"
        time.sleep(SETTLE_SECONDS)
        return call()
    finally:
        thread.join()


def one_task_plan(conn: sqlite3.Connection) -> str:
    """Create a plan holding one dispatchable task.

    Args:
        conn: An open ledger connection.

    Returns:
        The plan id.
    """
    return str(transitions.create(conn, slug="feature", goal="goal", tasks=[{"id": "T1", "title": "one"}]).plan)


def test_dispatch_behind_a_writer_grants_a_lease_that_has_not_expired(tmp_path: Path) -> None:
    """``dispatch`` leaves ``expires`` at ``now + ttl_seconds``, so ``expired`` is false.

    Args:
        tmp_path: pytest's per-test directory.
    """
    database = tmp_path / store.DATABASE_NAME
    setup = store.open_ledger(database)
    plan = one_task_plan(setup)
    setup.close()

    conn = store.open_ledger(database)
    try:
        result = behind_a_writer(
            database, lambda: transitions.dispatch(conn, plan, "T1", ttl_seconds=LEASE_TTL_SECONDS)
        )
        assert result.attempt == 1
        assert derive.expired(conn, plan, "T1") is False, (
            "dispatch handed the runner an attempt whose lease had already expired before it printed the attempt number"
        )
    finally:
        conn.close()


def test_renew_behind_a_writer_leaves_renew_by_in_the_future(tmp_path: Path) -> None:
    """A successful ``renew`` prints a ``renew_by`` in the future and clears ``expired``.

    Args:
        tmp_path: pytest's per-test directory.
    """
    database = tmp_path / store.DATABASE_NAME
    setup = store.open_ledger(database)
    plan = one_task_plan(setup)
    attempt = int(transitions.dispatch(setup, plan, "T1", ttl_seconds=LEASE_TTL_SECONDS).attempt or 0)
    setup.close()

    conn = store.open_ledger(database)
    try:
        result = behind_a_writer(database, lambda: transitions.renew(conn, plan, "T1", attempt=attempt))
        assert result.events == ["lease.renewed"]
        deadline = result.renew_by
        assert deadline is not None
        assert deadline > store.now(), "renew reported a lease deadline that had already passed"
        assert derive.expired(conn, plan, "T1") is False, "the task was still expired after a successful renew"
    finally:
        conn.close()
