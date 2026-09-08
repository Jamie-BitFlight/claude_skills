"""Conformance tests for ``dh_core.ledger.port``: the three commands that cross the boundary.

``dh_core.ledger_spec`` is the contract these drive the implementation through, and every
assertion below names the part of it that states the property.

``import`` carries a plan in
    The ``import`` transition writes "rows from the source; attempt_open 0; attempts and accepted
    from the source, else 0 and 0, so an imported complete task still faces the judge". Every plan
    fixture already under ``tests_sam/fixtures/`` is read by ``sam_schema.readers`` into a
    canonical ``Plan``, imported, and read back field for field against
    ``ledger_spec.PLAN_MODEL_FIELDS`` and ``ledger_spec.TASK_MODEL_FIELDS``. The in-progress task
    of a fixture arrives with no open attempt, so ``reclaim``'s ``leased`` check — waived by
    "--force, or returned, or stale, or attempt_open is 0" — does not fire and the send-back needs
    no ``--force``. The complete task arrives unaccepted, so ``accept`` still has work to do.

``import`` over a plan already held
    The ``exists`` reason's condition is "a plan with this id, or an unarchived plan with this
    milestone, exists and --replace is absent", and the transition waives the check under
    ``--replace``.

``export`` writes a projection, or says ``unchanged``
    The ``unchanged`` reason's condition is "the projection hash equals
    ``export_cursors.projection_hash`` for the target", and the ``export`` transition's note says
    the projection excludes the lease and worktree columns. A wave of renewals therefore leaves
    the hash where it was, and the second export writes nothing at all through the store.

``export`` names what it overwrote
    ``plan.exported`` carries ``divergences`` in its payload. A record edited out of band since
    the last export is named there, and the ledger's projection replaces it.

round trip
    ``export`` then ``import`` of what the store holds preserves ``attempts`` and ``accepted``,
    which the ``import`` transition takes "from the source", and its sections arrive tagged 0
    however they were tagged where they came from, which is the rest of that same effect.

``from-milestone --replace`` changes only the tables its own events set
    ``ledger_spec.EVENTS`` gives ``from-milestone`` exactly ``plan.created``, ``plan.replaced`` and
    ``task.added`` through ``written_by``, and none of those is in the ``set_by`` of a ``sections``
    column (``task.section``, ``task.imported``) or of an ``export_cursors`` column
    (``plan.exported``, ``plan.imported``). A table it can append no setting event for may not
    change, or a fold of the log would still hold what the table has lost.

``export --to content`` writes the record ``import --from content`` reads
    ``ledger_spec.COMMANDS`` names one word, ``content``, for both flags, and the ``import``
    transition binds them by writing ``export_cursors`` with "target content, revision and
    projection_hash of the source". The place they name is the plan's own content record, so an
    exported plan is one ``sam_schema.core.backends.content.ContentTaskProvider`` can still open.

The backend is the in-memory one every other module in ``tests_sam`` uses: ``conftest``'s autouse
``content_backend`` fixture installs it, and :func:`projection_store` resolves ``port.content_store``
over it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from backlog_core.backend_protocol import get_config, set_config
from backlog_core.backend_types import BacklogConfig, ContentProvider
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import ContentKind, ContentRef, ContentWrite
from dh_core import ledger_spec, operations
from dh_core.ledger import port, store, transitions
from sam_schema import sam_plan
from sam_schema.core.backends.content import ContentTaskProvider, parse_plan_content
from sam_schema.core.models import Plan
from sam_schema.readers.detect import FormatDetectionError, read_plan
from sam_schema.readers.normalize import normalize_plan

if TYPE_CHECKING:  # pragma: no cover - typing only
    import sqlite3
    from collections.abc import Iterator, Mapping

FIXTURES = Path(__file__).parent / "fixtures"
"""Where the plan fixtures the readers already cover live."""

PLAN_FIXTURES: tuple[str, ...] = (
    "global_manifest.md",
    "global_manifest_with_bold_fields.md",
    "plan_with_bookends.yaml",
    "pure_yaml_directory",
    "pure_yaml_single.yaml",
    "yaml_frontmatter_multi.md",
)
"""Every fixture under :data:`FIXTURES` that ``sam_schema.readers`` reads into a plan with tasks.

The rest of the directory is not a plan: ``t0_baseline_sample.yaml`` and
``tn_verification_sample.yaml`` are bookend artifacts, ``malformed/`` is deliberately broken, and
``pure_markdown_checklist.md``, ``nonstandard_frontmatter_tasks.md``,
``yaml_frontmatter_single.md`` and ``yaml_frontmatter_tasks_list.md`` are the reader's own
negative cases. :func:`test_every_plan_fixture_is_covered` checks that classification against the
directory rather than trusting this tuple.
"""

MIXED_FIXTURE = "pure_yaml_single.yaml"
"""The fixture whose tasks are complete, in-progress and not-started in one plan."""

COMPLETE_TASK = "T1"
IN_PROGRESS_TASK = "T2"

PLAN_ID = "Pfixture"
"""The plan id given to a fixture, which carries none of its own."""

TTL_SECONDS = 60
"""A short lease for the dispatches these tests make."""

RENEWALS = 3
"""How many renewals the renewal-only wave makes."""


# ---------------------------------------------------------------------------
# Reading a fixture, and comparing a stored row to the model it came from
# ---------------------------------------------------------------------------


PLAN_STRUCTURED = port.PLAN_STRUCTURED
"""Every ``plans`` column the ledger holds as JSON text, named by the module under test."""

TASK_STRUCTURED = port.TASK_STRUCTURED
"""Every ``tasks`` column the ledger holds as JSON text, named by the module under test."""

decode = port.decode_row
"""The decoder ``port`` reads a stored row back through; these tests compare against the same one."""


def read_fixture(name: str, *, plan_id: str = PLAN_ID) -> Plan:
    """Read one fixture into a canonical plan carrying a plan id.

    Args:
        name: The fixture's name under :data:`FIXTURES`.
        plan_id: The id to give the plan, which the fixtures do not carry.

    Returns:
        The plan ``sam_schema.readers`` produced.
    """
    path = FIXTURES / name
    meta, task_dicts, source_format = read_plan(path)
    plan = normalize_plan(meta, task_dicts, source_format, path).plan
    plan.plan_id = plan_id
    return plan


def reads_as_plan(path: Path) -> bool:
    """Report whether a path under :data:`FIXTURES` reads as a plan with tasks.

    Args:
        path: The fixture path.

    Returns:
        True when ``sam_schema.readers`` produces a plan holding at least one task.
    """
    try:
        meta, task_dicts, source_format = read_plan(path)
        result = normalize_plan(meta, task_dicts, source_format, path)
    except (FormatDetectionError, ValueError, OSError):
        return False
    return bool(result.plan.tasks)


@pytest.fixture
def ledger(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """Open an empty ledger in a temporary directory.

    Args:
        tmp_path: pytest's per-test directory.

    Yields:
        The open connection, closed when the test ends.
    """
    conn = store.open_ledger(tmp_path / store.DATABASE_NAME)
    try:
        yield conn
    finally:
        conn.close()


class RecordingStore:
    """A ``port.ProjectionStore`` over the configured backend that counts what it did."""

    def __init__(self, inner: port.ProjectionStore) -> None:
        """Wrap a projection store.

        Args:
            inner: The store the calls are forwarded to.
        """
        self.inner = inner
        self.reads: list[str] = []
        self.writes: list[str] = []
        self.expected: list[str] = []
        """The ``expected_revision`` each write was guarded by, in order."""

    def read(self, plan: str) -> dict[str, Any] | None:
        """Record and forward a read.

        Args:
            plan: The plan id.

        Returns:
            Whatever the wrapped store holds.
        """
        self.reads.append(plan)
        return self.inner.read(plan)

    def write(self, plan: str, content: Mapping[str, Any], *, expected_revision: str = "") -> str:
        """Record and forward a write.

        Args:
            plan: The plan id.
            content: The projection.
            expected_revision: The revision the export last saw.

        Returns:
            The revision the wrapped store assigned.
        """
        self.writes.append(plan)
        self.expected.append(expected_revision)
        return self.inner.write(plan, content, expected_revision=expected_revision)


@pytest.fixture
def projection_store() -> RecordingStore:
    """Resolve a projection store over the in-memory backend and count its calls.

    Returns:
        The recording store.
    """
    return RecordingStore(port.content_store())


def plan_with_tasks(conn: sqlite3.Connection, *task_ids: str) -> str:
    """Create a ready plan holding one task per id.

    Args:
        conn: An open ledger connection.
        task_ids: The task ids to add.

    Returns:
        The plan id ``create`` assigned.
    """
    result = transitions.create(
        conn,
        slug="port-suite",
        goal="exercise the boundary commands",
        tasks=[{"id": task_id, "title": f"Task {task_id}"} for task_id in task_ids],
    )
    assert result.plan is not None
    return result.plan


def source_from_projection(content: Mapping[str, Any], *, source: str, revision: str = "") -> port.PlanSource:
    """Build an import source from a projection the store holds.

    ``port.plan_source`` builds a source from a canonical ``Plan``, which carries no ``attempts``
    and no ``accepted``. A projection carries both, and the ``import`` transition takes them "from
    the source", so a round trip through the store goes through here.

    Args:
        content: The projection, as ``port.projection`` builds it.
        source: Where the rows came from, recorded in the events.
        revision: The revision the store assigned, recorded on the cursor.

    Returns:
        The source, ready for ``port.import_plan``.
    """
    tasks = [
        port.TaskSource(
            fields=decode({name: task.get(name) for name in ledger_spec.TASK_MODEL_FIELDS}, TASK_STRUCTURED),
            conflict_group=task.get("conflict_group"),
            attempts=int(task.get("attempts") or 0),
            attempts_allowed=int(task.get("attempts_allowed") or 0),
            accepted=int(task.get("accepted") or 0),
            sections=[
                port.SectionSource(name=str(section["name"]), content=str(section["content"]))
                for section in task.get(port.SECTIONS_KEY, [])
            ],
        )
        for task in content[port.TASKS_KEY]
    ]
    return port.PlanSource(
        plan_id=str(content["plan_id"]),
        fields=decode({name: content.get(name) for name in ledger_spec.PLAN_MODEL_FIELDS}, PLAN_STRUCTURED),
        milestone=content.get("milestone"),
        integration_branch=content.get("integration_branch"),
        base_sha=content.get("base_sha"),
        quality_gates=list(content.get("quality_gates") or []),
        tasks=tasks,
        source=source,
        revision=revision,
    )


# ---------------------------------------------------------------------------
# import: the round trip from a fixture
# ---------------------------------------------------------------------------


def test_every_plan_fixture_is_covered() -> None:
    """:data:`PLAN_FIXTURES` names every fixture the readers turn into a plan with tasks."""
    found = {path.name for path in FIXTURES.iterdir() if path.name != "malformed" and reads_as_plan(path)}
    assert found == set(PLAN_FIXTURES)


@pytest.mark.parametrize("fixture", PLAN_FIXTURES)
def test_import_round_trips_plan_fields(ledger: sqlite3.Connection, fixture: str) -> None:
    """Every ``ledger_spec.PLAN_MODEL_FIELDS`` value survives the import unchanged."""
    plan = read_fixture(fixture)
    port.import_plan(ledger, port.plan_source(plan, source=fixture))
    row = decode(store.fetch_plan(ledger, PLAN_ID), PLAN_STRUCTURED)
    dumped = plan.model_dump(mode="json", by_alias=False)
    for field in ledger_spec.PLAN_MODEL_FIELDS:
        assert row[field] == dumped[field], f"plans.{field}"


@pytest.mark.parametrize("fixture", PLAN_FIXTURES)
def test_import_round_trips_task_fields(ledger: sqlite3.Connection, fixture: str) -> None:
    """Every ``ledger_spec.TASK_MODEL_FIELDS`` value of every task survives the import."""
    plan = read_fixture(fixture)
    port.import_plan(ledger, port.plan_source(plan, source=fixture))
    rows = {str(row["id"]): decode(row, TASK_STRUCTURED) for row in store.plan_tasks(ledger, PLAN_ID)}
    assert set(rows) == {task.id for task in plan.tasks}
    for task in plan.tasks:
        dumped = task.model_dump(mode="json", by_alias=False)
        for field in ledger_spec.TASK_MODEL_FIELDS:
            assert rows[task.id][field] == dumped[field], f"tasks.{field} of {task.id}"


@pytest.mark.parametrize("fixture", PLAN_FIXTURES)
def test_import_closes_every_attempt(ledger: sqlite3.Connection, fixture: str) -> None:
    """The ``import`` transition writes ``attempt_open 0`` whatever status the source carried."""
    plan = read_fixture(fixture)
    port.import_plan(ledger, port.plan_source(plan, source=fixture))
    rows = store.plan_tasks(ledger, PLAN_ID)
    assert [row["attempt_open"] for row in rows] == [0] * len(rows)


@pytest.mark.parametrize("fixture", PLAN_FIXTURES)
def test_import_appends_the_events_the_specification_names(ledger: sqlite3.Connection, fixture: str) -> None:
    """A first import appends ``plan.created``, ``task.imported`` and ``plan.imported``."""
    plan = read_fixture(fixture)
    result = port.import_plan(ledger, port.plan_source(plan, source=fixture))
    assert result.events == ["plan.created", "task.imported", "plan.imported"]


def test_imported_in_progress_task_has_no_open_attempt(ledger: sqlite3.Connection) -> None:
    """An in-progress task arrives in-progress with its attempt closed."""
    plan = read_fixture(MIXED_FIXTURE)
    port.import_plan(ledger, port.plan_source(plan, source=MIXED_FIXTURE))
    row = store.fetch_task(ledger, PLAN_ID, IN_PROGRESS_TASK)
    assert row["status"] == ledger_spec.Status.IN_PROGRESS.value
    assert row["attempt_open"] == 0


def test_imported_in_progress_task_reclaims_without_force(ledger: sqlite3.Connection) -> None:
    """``reclaim``'s ``leased`` check is waived when ``attempt_open is 0``, so no ``--force``."""
    plan = read_fixture(MIXED_FIXTURE)
    port.import_plan(ledger, port.plan_source(plan, source=MIXED_FIXTURE))
    result = transitions.reclaim(ledger, PLAN_ID, IN_PROGRESS_TASK, reason="the runner is gone")
    assert result.noop is None
    assert result.status == ledger_spec.Status.NOT_STARTED.value
    assert store.fetch_task(ledger, PLAN_ID, IN_PROGRESS_TASK)["status"] == ledger_spec.Status.NOT_STARTED.value


def test_imported_complete_task_is_not_accepted(ledger: sqlite3.Connection) -> None:
    """A complete task arrives complete and unaccepted."""
    plan = read_fixture(MIXED_FIXTURE)
    port.import_plan(ledger, port.plan_source(plan, source=MIXED_FIXTURE))
    row = store.fetch_task(ledger, PLAN_ID, COMPLETE_TASK)
    assert row["status"] == ledger_spec.Status.COMPLETE.value
    assert row["accepted"] == 0


def test_imported_complete_task_still_faces_the_judge(ledger: sqlite3.Connection) -> None:
    """``accept`` on the imported complete task accepts it rather than declining as a no-op."""
    plan = read_fixture(MIXED_FIXTURE)
    port.import_plan(ledger, port.plan_source(plan, source=MIXED_FIXTURE))
    result = transitions.accept(ledger, PLAN_ID, COMPLETE_TASK)
    assert result.noop is None
    assert result.events == ["task.accepted"]
    assert store.fetch_task(ledger, PLAN_ID, COMPLETE_TASK)["accepted"] == 1


# ---------------------------------------------------------------------------
# import: over a plan already held
# ---------------------------------------------------------------------------


def test_second_import_of_one_plan_id_refuses_with_exists(ledger: sqlite3.Connection) -> None:
    """The ``exists`` check fires when a plan with this id is already held."""
    plan = read_fixture(MIXED_FIXTURE)
    source = port.plan_source(plan, source=MIXED_FIXTURE)
    port.import_plan(ledger, source)
    with pytest.raises(store.Refusal) as raised:
        port.import_plan(ledger, source)
    assert raised.value.reason == "exists"


def test_replace_overwrites_the_plan_already_held(ledger: sqlite3.Connection) -> None:
    """``--replace`` waives ``exists`` and the source's rows replace what was held."""
    plan = read_fixture(MIXED_FIXTURE)
    port.import_plan(ledger, port.plan_source(plan, source=MIXED_FIXTURE))
    replacement = read_fixture(MIXED_FIXTURE)
    replacement.tasks = [task for task in replacement.tasks if task.id != IN_PROGRESS_TASK]
    replacement.goal = "the replaced goal"
    result = port.import_plan(ledger, port.plan_source(replacement, source=MIXED_FIXTURE), replace=True)
    assert result.events == ["plan.replaced", "task.imported", "plan.imported"]
    assert {str(row["id"]) for row in store.plan_tasks(ledger, PLAN_ID)} == {task.id for task in replacement.tasks}
    assert store.fetch_plan(ledger, PLAN_ID)["goal"] == "the replaced goal"


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


def test_export_twice_prints_unchanged_the_second_time(
    ledger: sqlite3.Connection, projection_store: RecordingStore
) -> None:
    """The ``unchanged`` no-op fires when the projection hash equals the cursor's."""
    plan = plan_with_tasks(ledger, "T1", "T2")
    first = port.export_plan(ledger, plan, projection_store=projection_store)
    assert first.noop is None
    assert first.events == ["plan.exported"]
    second = port.export_plan(ledger, plan, projection_store=projection_store)
    assert second.noop == "unchanged"
    assert second.events == []


def test_unchanged_export_calls_no_provider_write(ledger: sqlite3.Connection, projection_store: RecordingStore) -> None:
    """The second export writes nothing at all through the store."""
    plan = plan_with_tasks(ledger, "T1", "T2")
    port.export_plan(ledger, plan, projection_store=projection_store)
    port.export_plan(ledger, plan, projection_store=projection_store)
    assert projection_store.writes == [plan]


def test_renewal_only_wave_leaves_export_unchanged(
    ledger: sqlite3.Connection, projection_store: RecordingStore
) -> None:
    """Renewals move only excluded columns, so the projection hash does not move."""
    plan = plan_with_tasks(ledger, "T1")
    dispatched = transitions.dispatch(ledger, plan, "T1", ttl_seconds=TTL_SECONDS)
    assert dispatched.attempt is not None
    port.export_plan(ledger, plan, projection_store=projection_store)
    assert store.fetch_task(ledger, plan, "T1")["first_renewed"] is None
    for _ in range(RENEWALS):
        renewed = transitions.renew(ledger, plan, "T1", attempt=dispatched.attempt)
        assert renewed.events == ["lease.renewed"]
    assert store.fetch_task(ledger, plan, "T1")["first_renewed"] is not None
    after = port.export_plan(ledger, plan, projection_store=projection_store)
    assert after.noop == "unchanged"
    assert projection_store.writes == [plan]


def held_record(plan: str) -> dict[str, Any]:
    """Read the raw record the in-memory backend holds for one plan.

    Args:
        plan: The plan id.

    Returns:
        The decoded projection.
    """
    backend = get_config().backend
    assert isinstance(backend, ContentProvider)
    return json.loads(backend.get_content(ContentRef(kind=ContentKind.PLAN, name=plan)).content)


def edit_held_record(plan: str, content: Mapping[str, Any]) -> None:
    """Write a record for one plan straight through the backend, as a hand edit would.

    Args:
        plan: The plan id.
        content: The record to store.
    """
    backend = get_config().backend
    assert isinstance(backend, ContentProvider)
    reference = ContentRef(kind=ContentKind.PLAN, name=plan)
    backend.put_content(
        ContentWrite(
            reference=reference,
            content=json.dumps(content, sort_keys=True, default=str),
            expected_revision=backend.get_content(reference).revision,
        )
    )


def test_hand_edited_record_is_listed_under_divergences(
    ledger: sqlite3.Connection, projection_store: RecordingStore
) -> None:
    """A record edited out of band since the last export is named in ``divergences``."""
    plan = plan_with_tasks(ledger, "T1", "T2")
    port.export_plan(ledger, plan, projection_store=projection_store)
    edited = held_record(plan)
    edited["tasks"][0]["title"] = "edited by hand"
    edit_held_record(plan, edited)
    transitions.dispatch(ledger, plan, "T2", ttl_seconds=TTL_SECONDS)
    result = port.export_plan(ledger, plan, projection_store=projection_store)
    assert result.noop is None
    assert "T1" in result.changed["divergences"]
    assert projection_store.expected[-1] == ""


def test_hand_edited_record_is_overwritten(ledger: sqlite3.Connection, projection_store: RecordingStore) -> None:
    """The ledger's projection replaces the record the store held."""
    plan = plan_with_tasks(ledger, "T1", "T2")
    port.export_plan(ledger, plan, projection_store=projection_store)
    edited = held_record(plan)
    edited["tasks"][0]["title"] = "edited by hand"
    edit_held_record(plan, edited)
    transitions.dispatch(ledger, plan, "T2", ttl_seconds=TTL_SECONDS)
    port.export_plan(ledger, plan, projection_store=projection_store)
    assert held_record(plan) == json.loads(json.dumps(port.projection(ledger, plan), sort_keys=True, default=str))


# ---------------------------------------------------------------------------
# export then import
# ---------------------------------------------------------------------------


def complete_and_accept(conn: sqlite3.Connection, plan: str, task: str) -> None:
    """Run one task through dispatch, its report sections, finish and accept.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.
    """
    dispatched = transitions.dispatch(conn, plan, task, ttl_seconds=TTL_SECONDS)
    assert dispatched.attempt is not None
    for name in ledger_spec.REPORT_SECTIONS:
        transitions.update(conn, plan, task, attempt=dispatched.attempt, section=name, section_content=f"{name} body")
    transitions.finish(conn, plan, task, attempt=dispatched.attempt, result=ledger_spec.Status.COMPLETE.value)
    accepted = transitions.accept(conn, plan, task)
    assert accepted.noop is None


def test_accepted_and_attempts_survive_export_then_import(
    ledger: sqlite3.Connection, projection_store: RecordingStore, tmp_path: Path
) -> None:
    """``attempts`` and ``accepted`` come back from the store, because import takes them from it."""
    plan = plan_with_tasks(ledger, "T1", "T2")
    complete_and_accept(ledger, plan, "T1")
    exported = port.export_plan(ledger, plan, projection_store=projection_store)
    assert exported.noop is None
    held = projection_store.read(plan)
    assert held is not None

    elsewhere = store.open_ledger(tmp_path / "elsewhere.db")
    try:
        port.import_plan(
            elsewhere, source_from_projection(held, source="content", revision=str(exported.changed["revision"]))
        )
        row = store.fetch_task(elsewhere, plan, "T1")
        assert row["attempts"] == 1
        assert row["accepted"] == 1
        assert row["status"] == ledger_spec.Status.COMPLETE.value
        assert row["attempt_open"] == 0
        untouched = store.fetch_task(elsewhere, plan, "T2")
        assert untouched["attempts"] == 0
        assert untouched["accepted"] == 0
    finally:
        elsewhere.close()


def test_sections_survive_export_then_import(
    ledger: sqlite3.Connection, projection_store: RecordingStore, tmp_path: Path
) -> None:
    """The report sections the projection carries come back as rows of ``sections``."""
    plan = plan_with_tasks(ledger, "T1")
    complete_and_accept(ledger, plan, "T1")
    port.export_plan(ledger, plan, projection_store=projection_store)
    held = projection_store.read(plan)
    assert held is not None

    elsewhere = store.open_ledger(tmp_path / "elsewhere.db")
    try:
        port.import_plan(elsewhere, source_from_projection(held, source="content"))
        rows = transitions.sections_of(elsewhere, plan, "T1")
        assert {str(row["name"]) for row in rows} == set(ledger_spec.REPORT_SECTIONS)
        assert [row["attempt"] for row in rows] == [port.IMPORTED_SECTION_ATTEMPT] * len(rows)
    finally:
        elsewhere.close()


# ---------------------------------------------------------------------------
# from-milestone --replace: the tables it may not change
# ---------------------------------------------------------------------------

MILESTONE = 7
"""The milestone both plan sources below are built from."""

MILESTONE_PLAN = f"P{MILESTONE:d}"
"""The plan id ``port.milestone_source`` derives from that milestone."""


def kinds_written_by(command: str) -> frozenset[str]:
    """Return every event kind ``ledger_spec.EVENTS`` says one command appends.

    Args:
        command: The ``ledger_spec.COMMANDS`` name.

    Returns:
        The kinds whose ``written_by`` names that command.
    """
    return frozenset(event.kind for event in ledger_spec.EVENTS if command in event.written_by)


def setters_of(table: str) -> frozenset[str]:
    """Return every event kind whose fold sets a column of one materialised table.

    Args:
        table: The table name.

    Returns:
        The union of the ``set_by`` lists of that table's stored columns.
    """
    return frozenset(
        kind
        for column in ledger_spec.COLUMNS
        if column.table == table and column.provenance is not ledger_spec.Provenance.DERIVED
        for kind in column.set_by
    )


FROM_MILESTONE_KINDS = kinds_written_by("from-milestone")
"""The three kinds the specification lets ``from-milestone`` append."""

UNTOUCHABLE_TABLES: tuple[str, ...] = ("sections", "export_cursors")
"""The tables ``from-milestone`` can append no setting event for, so may not change."""


class FakeProjectionStore:
    """A :class:`dh_core.ledger.port.ProjectionStore` holding one projection in memory."""

    def __init__(self) -> None:
        """Start with no record held."""
        self.held: dict[str, dict[str, Any]] = {}
        self.revision = 0

    def read(self, plan: str) -> dict[str, Any] | None:
        """Return the projection held for a plan.

        Args:
            plan: The plan id.

        Returns:
            The projection, or None when none is held.
        """
        return self.held.get(plan)

    def write(self, plan: str, content: Mapping[str, Any], *, expected_revision: str = "") -> str:
        """Record a projection and hand back a fresh revision.

        Args:
            plan: The plan id.
            content: The projection.
            expected_revision: The revision the caller expected; recorded, not enforced.

        Returns:
            The new revision.
        """
        self.held[plan] = json.loads(json.dumps(dict(content), default=str))
        self.revision += 1
        return f"rev-{self.revision:d}"


def milestone_plan(*, base_sha: str) -> port.PlanSource:
    """Build the one-task milestone plan both halves of each test write.

    Args:
        base_sha: The branch head the plan records.

    Returns:
        The source, ready for ``port.from_milestone``.
    """
    return port.milestone_source(
        milestone_number=MILESTONE,
        integration_branch="main",
        base_sha=base_sha,
        items=[port.MilestoneItem(issue=1, title="one")],
    )


@pytest.fixture
def milestone_ledger(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a ledger holding the milestone's plan, and close it afterwards.

    Args:
        tmp_path: pytest's per-test directory.

    Yields:
        An open connection whose ledger already holds the milestone plan.
    """
    connection = store.open_ledger(tmp_path / store.DATABASE_NAME)
    try:
        port.from_milestone(connection, milestone_plan(base_sha="aaa"))
        yield connection
    finally:
        connection.close()


def table_rows(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    """Read every row of one materialised table.

    Args:
        conn: An open ledger connection.
        table: The table name.

    Returns:
        The rows as dictionaries.
    """
    words = ["SELECT * FROM", table, "ORDER BY plan"]
    return store.rows_of(conn.execute(" ".join(words)))


@pytest.mark.parametrize("table", UNTOUCHABLE_TABLES)
def test_from_milestone_appends_no_event_that_sets_the_table(table: str) -> None:
    """The specification gives ``from-milestone`` no event whose fold sets these tables."""
    assert not FROM_MILESTONE_KINDS & setters_of(table), (
        f"this module assumes ledger_spec gives from-milestone no event that sets {table}"
    )


def test_from_milestone_replace_keeps_the_sections_it_cannot_account_for(milestone_ledger: sqlite3.Connection) -> None:
    """A replace leaves ``sections`` rows the log's ``task.section`` events still hold."""
    transitions.update(milestone_ledger, MILESTONE_PLAN, "T1", section="Notes", section_content="kept")
    before = table_rows(milestone_ledger, "sections")
    assert before, "the fixture did not record a section to replace over"

    result = port.from_milestone(milestone_ledger, milestone_plan(base_sha="bbb"), replace=True)

    assert set(result.events) <= set(FROM_MILESTONE_KINDS)
    assert table_rows(milestone_ledger, "sections") == before, (
        "from-milestone --replace deleted the plan's sections while appending only "
        f"{sorted(set(result.events))}, and ledger_spec.COLUMNS says the fold of sections is set by "
        f"{sorted(setters_of('sections'))}, so the log still holds a section the table has lost"
    )


def test_from_milestone_replace_keeps_the_export_cursor_it_cannot_account_for(
    milestone_ledger: sqlite3.Connection,
) -> None:
    """A replace leaves the ``export_cursors`` row the log's ``plan.exported`` event still holds."""
    port.export_plan(milestone_ledger, MILESTONE_PLAN, projection_store=FakeProjectionStore())
    before = table_rows(milestone_ledger, "export_cursors")
    assert before, "the fixture did not record an export cursor to replace over"

    result = port.from_milestone(milestone_ledger, milestone_plan(base_sha="bbb"), replace=True)

    assert set(result.events) <= set(FROM_MILESTONE_KINDS)
    assert table_rows(milestone_ledger, "export_cursors") == before, (
        "from-milestone --replace deleted the plan's export cursor while appending only "
        f"{sorted(set(result.events))}, and ledger_spec.COLUMNS says the fold of export_cursors is set "
        f"by {sorted(setters_of('export_cursors'))}, so the next export loses both its unchanged "
        "check and the expected_revision its compare-and-swap needs"
    )


# ---------------------------------------------------------------------------
# export to content, then import from it
# ---------------------------------------------------------------------------

SOURCE = port.CONTENT_TARGET
"""The one ``ledger_spec.COMMANDS`` word that names both ``import --from`` and ``export --to``."""

ROUND_TRIP_TASK = "T1"
"""The single task every plan in this group carries."""


@pytest.fixture
def provider() -> InMemoryBackend:
    """Make a content-capable backend the configured one for the duration of a test.

    The suite's autouse fixture already installs a backend; this replaces it with one the test
    holds a direct reference to, so the record ``export`` writes can be read back raw. Teardown is
    the autouse fixture's ``reset_config``, which runs after this one.

    Returns:
        The backend both the ledger's projection store and the content path resolve to.
    """
    backend = InMemoryBackend()
    set_config(BacklogConfig(backend=backend))
    return backend


def worked_plan(conn: sqlite3.Connection) -> str:
    """Build a plan whose one task has been dispatched, reported, finished and accepted.

    Args:
        conn: An open ledger connection.

    Returns:
        The plan id.
    """
    plan = str(transitions.create(conn, slug="round-trip", goal="prove the round trip").plan)
    transitions.append_task(conn, plan, task_id=ROUND_TRIP_TASK, task_title="the one task")
    transitions.finalize(conn, plan)
    attempt = int(transitions.dispatch(conn, plan, ROUND_TRIP_TASK).attempt or 0)
    for name in ledger_spec.REPORT_SECTIONS:
        transitions.update(conn, plan, ROUND_TRIP_TASK, attempt=attempt, section=name, section_content=f"{name} body")
    transitions.finish(conn, plan, ROUND_TRIP_TASK, attempt=attempt, result=ledger_spec.Status.COMPLETE.value)
    transitions.accept(conn, plan, ROUND_TRIP_TASK)
    return plan


def seeded_plan(backend: InMemoryBackend) -> str:
    """Write one canonical plan through the content path, the way an import's source holds it.

    Args:
        backend: The configured backend.

    Returns:
        The plan id the content path assigned.
    """
    created = operations.create_plan(
        ContentTaskProvider(backend),
        slug="seeded",
        goal="a plan the content path already holds",
        tasks=[{"id": ROUND_TRIP_TASK, "title": "the one task", "status": ledger_spec.Status.NOT_STARTED.value}],
    )
    return str(created.plan_id)


def test_a_plan_exported_to_content_can_be_imported_back_from_content(
    provider: InMemoryBackend, ledger: sqlite3.Connection
) -> None:
    """``import --from content`` reads the record ``export --to content`` wrote for the plan.

    Args:
        provider: The configured backend.
        ledger: An open ledger connection.
    """
    plan = worked_plan(ledger)
    port.export_plan(ledger, plan, target=SOURCE, projection_store=port.content_store())

    sources = sam_plan.import_sources(SOURCE, plan, all_plans=False)

    assert [source.plan_id for source in sources] == [plan]


def test_export_leaves_the_plan_record_the_content_path_reads(
    provider: InMemoryBackend, ledger: sqlite3.Connection
) -> None:
    """A plan imported from content and exported back is still readable on the content path.

    Args:
        provider: The configured backend.
        ledger: An open ledger connection.
    """
    plan = seeded_plan(provider)
    read_back = operations.read_plan(ContentTaskProvider(provider), plan).plan
    port.import_plan(ledger, port.plan_source(read_back, source=SOURCE))

    port.export_plan(ledger, plan, target=SOURCE, projection_store=port.content_store())

    assert operations.read_plan(ContentTaskProvider(provider), plan).plan.plan_id == plan


def test_the_record_export_writes_parses_as_plan_content(provider: InMemoryBackend, ledger: sqlite3.Connection) -> None:
    """The ``ContentKind.PLAN`` record an export leaves parses the way every other one does.

    Args:
        provider: The configured backend.
        ledger: An open ledger connection.
    """
    plan = worked_plan(ledger)
    port.export_plan(ledger, plan, target=SOURCE, projection_store=port.content_store())

    record = provider.get_content(ContentRef(kind=ContentKind.PLAN, name=plan))

    assert parse_plan_content(record.content, plan)["plan_id"] == plan
