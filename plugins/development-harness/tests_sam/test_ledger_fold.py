"""Every materialised table is a fold over the log, driven through a whole plan's worth of commands.

``dh_core.ledger_spec`` claims each table in ``COLUMNS`` is materialised from ``events`` and can be
rebuilt from them. :func:`dh_core.ledger.store.rebuild` is that rebuild, and these tests are the
claim's proof: a ledger is driven through a long, varied command sequence, every materialised table
is snapshotted, the tables are emptied and replayed from the log alone, and the result must equal
the snapshot row for row and column for column.

Three parts of the specification exist only because the fold needs them, so each has its own case:

``plan.replaced`` carries the plan row
    ``COLUMNS`` names it in the ``set_by`` of every ``plans`` column, and ``port`` appends it
    instead of ``plan.created`` whenever a plan is replaced. Carrying only ``source`` and
    ``revision``, as it once did, left a fold holding the plan the replace overwrote.

``task.state`` carries ``accepted`` and ``attempt_open``
    ``state --force`` clears acceptance and every ``state`` closes the attempt, but the same kind
    is appended by the cascade and by its reversal, which move a dependent's status and leave both
    columns where they were. The command alone does not say which happened.

``events.at`` is the transition's own moment
    No payload carries a timestamp; ``ledger_spec.INSTANT_COLUMNS`` are read back out of
    ``events.at``, which :func:`dh_core.ledger.store.append_event` now records from the instant its
    caller sampled inside the transaction rather than from a second sample of its own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from dh_core import ledger_spec as spec
from dh_core.ledger import port, store, transitions

if TYPE_CHECKING:  # pragma: no cover - typing only
    import sqlite3
    from collections.abc import Callable, Mapping
    from pathlib import Path

    Checkpoint = Callable[[], object]
    """What a scenario runs between two commands: nothing, or a whole fold of the ledger.

    A checkpoint's return value is ignored, so :func:`assert_rebuilt` can be one directly."""

    Scenario = Callable[[sqlite3.Connection, Path, Checkpoint], str]
    """A scenario builder: it drives one plan and returns its id."""

TTL = 60
"""The lease length every dispatch uses, so ``expires`` is a checkable offset from ``events.at``."""

MILESTONE = 41
"""The milestone ``from-milestone`` builds a plan from."""

MIRROR = "mirror"
"""A second export target. ``ledger_spec.COMMANDS`` names one word for ``export --to`` today, but
``store.PRIMARY_KEYS`` keys ``export_cursors`` by ``(plan, target)``, so one plan may hold several
cursors -- and a fold that assumed the one target would put them all in one row."""


# ---------------------------------------------------------------------------
# Snapshots and the identity the fold must hold
# ---------------------------------------------------------------------------


def snapshot(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    """Read every materialised table, each ordered by the store's primary key."""
    taken: dict[str, list[dict[str, Any]]] = {}
    for table in store.TABLES:
        order = ", ".join(store.PRIMARY_KEYS[table])
        words = ["SELECT * FROM", table, "ORDER BY", order]
        taken[table] = store.rows_of(conn.execute(" ".join(words)))
    return taken


def assert_rebuilt(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    """Empty every materialised table, replay the log, and assert nothing moved."""
    before = snapshot(conn)
    assert any(before[table] for table in before), "the scenario materialised nothing to compare"
    store.rebuild(conn)
    after = snapshot(conn)
    for table in store.TABLES:
        expected, folded = before[table], after[table]
        assert len(folded) == len(expected), (
            f"folding the log gives {len(folded)} rows of {table} where the ledger held {len(expected)}: "
            f"{[row for row in folded if row not in expected]} appeared, "
            f"{[row for row in expected if row not in folded]} went"
        )
        for held, rebuilt in zip(expected, folded, strict=True):
            assert set(rebuilt) == {column.name for column in store.TABLES[table]}
            for name in held:
                assert rebuilt[name] == held[name], (
                    f"folding the log gives {table}.{name} = {rebuilt[name]!r} on "
                    f"{[held[key] for key in store.PRIMARY_KEYS[table]]}, but the ledger holds {held[name]!r}"
                )
    return before


def kinds_logged(conn: sqlite3.Connection) -> set[str]:
    """Return every event kind the log holds."""
    return {str(event["kind"]) for event in store.all_events(conn)}


# ---------------------------------------------------------------------------
# Building a ledger
# ---------------------------------------------------------------------------


def ledger(tmp_path: Path) -> sqlite3.Connection:
    """Open a ledger in a temporary directory."""
    return store.open_ledger(tmp_path / store.DATABASE_NAME)


class RecordingStore:
    """A :class:`dh_core.ledger.port.ProjectionStore` that keeps the projection in memory."""

    def __init__(self) -> None:
        """Start with nothing written."""
        self.written: dict[str, dict[str, Any]] = {}
        self.revisions = 0

    def read(self, plan: str) -> dict[str, Any] | None:
        """Return the projection this store holds for a plan."""
        return self.written.get(plan)

    def write(self, plan: str, content: Mapping[str, Any], *, expected_revision: str = "") -> str:
        """Record a projection and return the revision assigned to it."""
        del expected_revision
        self.written[plan] = dict(content)
        self.revisions += 1
        return f"revision-{self.revisions:d}"


def reports(conn: sqlite3.Connection, plan: str, task: str, attempt: int, check: Checkpoint) -> None:
    """Append every report section for one attempt, so the report check passes."""
    for name in spec.REPORT_SECTIONS:
        transitions.update(conn, plan, task, attempt=attempt, section=name, section_content=f"{name} for {attempt}")
        check()


def import_source(revision: str, *, title: str, sections: int) -> port.PlanSource:
    """Build an import source carrying one task with attempts, acceptance and its sections."""
    return port.PlanSource(
        plan_id="Pimported",
        fields={"feature": "imported", "goal": "carry a plan in", "description": revision},
        tasks=[
            port.TaskSource(
                fields={"id": "T1", "title": title, "status": spec.Status.COMPLETE.value},
                attempts=2,
                attempts_allowed=5,
                accepted=1,
                sections=[port.SectionSource(name=f"Note {index:d}", content="body") for index in range(sections)],
            ),
            port.TaskSource(fields={"id": "T2", "title": "second", "dependencies": ["T1"]}, attempts_allowed=4),
        ],
        source="content",
        revision=revision,
    )


def milestone_items() -> list[port.MilestoneItem]:
    """Return two milestone items, the second depending on the first."""
    return [
        port.MilestoneItem(issue=10, title="first item", task_id="T1", acceptance_criteria="works"),
        port.MilestoneItem(issue=11, title="second item", task_id="T2", depends_on=["T1"], conflict_group="core"),
    ]


# ---------------------------------------------------------------------------
# The scenarios
# ---------------------------------------------------------------------------
#
# A scenario is a sequence of commands with a ``check`` between each pair. Left as :func:`nothing`
# it just runs; handed :func:`assert_rebuilt` it folds the whole ledger after every single command,
# so a column the fold gets wrong is caught at the command that wrote it rather than at whichever
# later command happened to overwrite it with the value the fold already held.


def nothing() -> None:
    """Do nothing between a scenario's commands."""


def drafted_plan(conn: sqlite3.Connection, tmp_path: Path, check: Checkpoint = nothing) -> str:
    """Create a plan by drafting and appending, then run one task all the way to accepted."""
    plan = str(transitions.create(conn, slug="journey", goal="drive every command").plan)
    check()
    transitions.append_task(conn, plan, task_id="T1", task_title="first", conflict_group="core")
    check()
    transitions.append_task(conn, plan, task_id="T2", task_title="second", definition={"dependencies": ["T1"]})
    check()
    transitions.append_task(conn, plan, task_id="T3", task_title="third", definition={"dependencies": ["T2"]})
    check()
    transitions.finalize(conn, plan)
    check()
    transitions.update(conn, plan, values={"description": "a plan that has been through everything"})
    check()

    worktree = tmp_path / "worktree"
    worktree.mkdir(parents=True)
    attempt = int(transitions.dispatch(conn, plan, "T1", ttl_seconds=TTL, worktree=str(worktree)).attempt or 0)
    check()
    transitions.read(conn, plan, "T1", attempt=attempt)
    check()
    transitions.renew(conn, plan, "T1", attempt=attempt)
    check()
    transitions.renew(conn, path=str(worktree / "file.txt"))
    check()
    transitions.update(conn, plan, "T1", attempt=attempt, values={"skills": ["python"], "priority": 2})
    check()
    transitions.update(conn, plan, "T1", section="Scratch", section_content="not a report")
    check()
    reports(conn, plan, "T1", attempt, check)
    transitions.finish(conn, plan, "T1", attempt=attempt, result=spec.Status.COMPLETE.value, note="done")
    check()
    transitions.settle(conn, plan, "T1", attempt=attempt, return_text="the harness said this")
    check()
    transitions.accept(conn, plan, "T1", note="looks right")
    check()
    return plan


def journey(conn: sqlite3.Connection, tmp_path: Path, check: Checkpoint = nothing) -> str:
    """Drive one plan through the whole vocabulary, ending archived."""
    plan = drafted_plan(conn, tmp_path, check)

    second = int(transitions.dispatch(conn, plan, "T2", ttl_seconds=TTL).attempt or 0)
    check()
    transitions.finish(conn, plan, "T2", attempt=second, result=spec.Status.FAILED.value, note="broke")
    check()
    transitions.reclaim(conn, plan, "T2", reason="try again", response="read this first", more_attempts=True)
    check()

    third = int(transitions.dispatch(conn, plan, "T2", ttl_seconds=TTL).attempt or 0)
    check()
    transitions.settle(conn, plan, "T2", attempt=third, return_text="returned without finishing")
    check()
    transitions.accept(conn, plan, "T2", force=True)
    check()

    transitions.state(conn, plan, "T3", new_status=spec.Status.DEFERRED.value, reason="not this milestone")
    check()
    transitions.archive(conn, plan, reason="superseded")
    check()
    return plan


def accepted_then_forced(conn: sqlite3.Connection, check: Checkpoint = nothing) -> str:
    """Accept a task, then move it with ``state --force``, clearing acceptance and cascading."""
    plan = str(
        transitions.create(
            conn,
            slug="forced",
            goal="clear an acceptance",
            tasks=[
                {"id": "T1", "title": "first"},
                {"id": "T2", "title": "second", "dependencies": ["T1"]},
                {"id": "T3", "title": "third", "dependencies": ["T2"]},
            ],
        ).plan
    )
    check()
    attempt = int(transitions.dispatch(conn, plan, "T1", ttl_seconds=TTL).attempt or 0)
    check()
    reports(conn, plan, "T1", attempt, check)
    transitions.finish(conn, plan, "T1", attempt=attempt, result=spec.Status.COMPLETE.value)
    check()
    transitions.accept(conn, plan, "T1")
    check()
    assert store.fetch_task(conn, plan, "T1")["accepted"] == 1

    transitions.state(conn, plan, "T1", new_status=spec.Status.FAILED.value, reason="judge rejected it", force=True)
    check()
    assert store.fetch_task(conn, plan, "T1")["accepted"] == 0
    assert store.fetch_task(conn, plan, "T2")["status"] == spec.Status.SKIPPED.value
    return plan


def forced(conn: sqlite3.Connection, tmp_path: Path, check: Checkpoint = nothing) -> str:
    """Force an accepted task to failed, then reclaim it so the cascade is reversed."""
    del tmp_path
    plan = accepted_then_forced(conn, check)
    transitions.reclaim(conn, plan, "T1", reason="one more go", force=True)
    check()
    assert store.fetch_task(conn, plan, "T2")["status"] == spec.Status.NOT_STARTED.value
    return plan


def imported(conn: sqlite3.Connection, tmp_path: Path, check: Checkpoint = nothing) -> str:
    """Import a plan, export it, then import over it so ``plan.replaced`` is appended."""
    del tmp_path
    port.import_plan(conn, import_source("r1", title="first", sections=3), projection_hash="hash-one")
    check()
    port.export_plan(conn, "Pimported", projection_store=RecordingStore())
    check()
    port.export_plan(conn, "Pimported", target=MIRROR, projection_store=RecordingStore())
    check()
    port.import_plan(conn, import_source("r2", title="renamed", sections=1), replace=True, projection_hash="hash-two")
    check()
    return "Pimported"


def from_milestone(conn: sqlite3.Connection, tmp_path: Path, check: Checkpoint = nothing) -> str:
    """Build a plan from a milestone, give a task a section, then replace the plan."""
    del tmp_path
    source = port.milestone_source(
        milestone_number=MILESTONE,
        integration_branch="integration/41",
        base_sha="0" * 40,
        items=milestone_items(),
        quality_gates=["uv run pytest"],
        conflict_groups={},
    )
    plan = str(port.from_milestone(conn, source).plan)
    check()
    attempt = int(transitions.dispatch(conn, plan, "T1", ttl_seconds=TTL).attempt or 0)
    check()
    transitions.update(conn, plan, "T1", attempt=attempt, section="Scratch", section_content="survives the replace")
    check()
    transitions.finish(conn, plan, "T1", attempt=attempt, result=spec.Status.FAILED.value)
    check()

    replacement = port.milestone_source(
        milestone_number=MILESTONE,
        integration_branch="integration/41",
        base_sha="1" * 40,
        items=milestone_items()[:1],
        quality_gates=["uv run pytest", "uv run ruff check"],
        conflict_groups={},
    )
    port.from_milestone(conn, replacement, replace=True)
    check()
    return plan


SCENARIOS: dict[str, Scenario] = {
    "journey": journey,
    "forced-state": forced,
    "import-replace": imported,
    "from-milestone-replace": from_milestone,
}
"""Each scenario builds one plan and returns its id; every one must fold to itself throughout."""


def build_all(conn: sqlite3.Connection, tmp_path: Path, check: Checkpoint = nothing) -> None:
    """Run every scenario into one ledger."""
    for index, builder in enumerate(SCENARIOS.values()):
        builder(conn, tmp_path / f"scenario-{index:d}", check)


# ---------------------------------------------------------------------------
# The tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_each_scenario_folds_after_every_command(tmp_path: Path, name: str) -> None:
    conn = ledger(tmp_path)
    SCENARIOS[name](conn, tmp_path, lambda: assert_rebuilt(conn))


def test_every_table_and_every_kind_is_exercised(tmp_path: Path) -> None:
    """The identity is not vacuous: every table holds rows and every event kind was appended."""
    conn = ledger(tmp_path)
    build_all(conn, tmp_path)
    held = snapshot(conn)
    for table in store.TABLES:
        assert held[table], f"no scenario materialised a row of {table}"
    assert kinds_logged(conn) == {event.kind for event in spec.EVENTS}


def test_every_scenario_together_folds(tmp_path: Path) -> None:
    """One ledger holding every scenario's plan folds to itself, after every command of every one."""
    conn = ledger(tmp_path)
    build_all(conn, tmp_path, lambda: assert_rebuilt(conn))


def test_rebuild_is_idempotent(tmp_path: Path) -> None:
    """Folding a folded ledger changes nothing, and appends nothing to the log."""
    conn = ledger(tmp_path)
    build_all(conn, tmp_path)
    events = store.all_events(conn)
    store.rebuild(conn)
    once = snapshot(conn)
    store.rebuild(conn)
    assert snapshot(conn) == once
    assert store.all_events(conn) == events


def test_plan_replaced_carries_the_plan_row(tmp_path: Path) -> None:
    """The replaced plan's own columns come back from ``plan.replaced``, not from the plan it replaced."""
    conn = ledger(tmp_path)
    imported(conn, tmp_path)
    held = assert_rebuilt(conn)["plans"][0]
    assert held["description"] == "r2", "the second import's fields are what the ledger holds"
    replaced = next(event for event in store.all_events(conn) if event["kind"] == "plan.replaced")
    assert set(replaced["payload"]) == set(next(e for e in spec.EVENTS if e.kind == "plan.replaced").payload)
    assert replaced["payload"]["description"] == "r2"
    assert replaced["payload"]["replaced"] == "Pimported"
    assert set(replaced["payload"]["clears"]) == set(port.IMPORT_CLEARS)


def test_from_milestone_replace_clears_only_its_own_tables(tmp_path: Path) -> None:
    """``from-milestone`` empties ``tasks`` alone, and the fold keeps the sections it left behind."""
    conn = ledger(tmp_path)
    plan = from_milestone(conn, tmp_path)
    replaced = next(event for event in store.all_events(conn) if event["kind"] == "plan.replaced")
    assert set(replaced["payload"]["clears"]) == set(port.MILESTONE_CLEARS)
    held = assert_rebuilt(conn)
    assert [row["name"] for row in held["sections"]] == ["Scratch"], "the orphaned section is still there"
    assert [row["id"] for row in held["tasks"] if row["plan"] == plan] == ["T1"]


def test_replacing_a_milestone_plan_under_a_new_id_folds(tmp_path: Path) -> None:
    """A replace that matched on milestone renames the row it matched to the incoming id.

    ``existing_plan`` matches a plan with this id, or an unarchived plan with this milestone. When
    the second matches, the incoming id differs from the one whose rows are emptied, which is why
    ``plan.replaced`` carries ``replaced`` as well as the row. One plan must survive, under the
    incoming id, holding the incoming tasks: an update keyed on the incoming id would match no row
    and leave the emptied plan behind with the new tasks pointing at nothing.
    """
    conn = ledger(tmp_path)
    first = from_milestone(conn, tmp_path)
    replacement = port.milestone_source(
        milestone_number=MILESTONE,
        integration_branch="integration/41",
        base_sha="2" * 40,
        items=milestone_items(),
        plan_id="Pelsewhere",
        conflict_groups={},
    )
    port.from_milestone(conn, replacement, replace=True)
    replaced = [event for event in store.all_events(conn) if event["kind"] == "plan.replaced"][-1]
    assert replaced["plan"] == "Pelsewhere"
    assert replaced["payload"]["replaced"] == first
    held = assert_rebuilt(conn)
    assert [row["plan_id"] for row in held["plans"]] == ["Pelsewhere"]
    assert {row["plan"] for row in held["tasks"]} == {"Pelsewhere"}
    assert held["tasks"], "the replacement's tasks must belong to the surviving plan"
    assert all(row["integration_branch"] == "integration/41" for row in held["plans"])


def test_state_force_on_an_accepted_task_folds(tmp_path: Path) -> None:
    """``task.state`` says whether acceptance survived, so the fold does not have to guess."""
    conn = ledger(tmp_path)
    plan = accepted_then_forced(conn)
    forced_event = next(
        event
        for event in store.all_events(conn)
        if event["kind"] == "task.state" and event["payload"]["reason"] == "judge rejected it"
    )
    assert forced_event["payload"]["accepted"] == 0
    assert forced_event["payload"]["attempt_open"] == 0
    cascaded = next(
        event
        for event in store.all_events(conn)
        if event["kind"] == "task.state" and str(event["payload"]["reason"]).startswith("cascade:")
    )
    assert cascaded["payload"]["accepted"] == 0
    held = assert_rebuilt(conn)
    row = next(task for task in held["tasks"] if task["plan"] == plan and task["id"] == "T1")
    assert row["accepted"] == 0, "the fold must clear acceptance here, and the log is what tells it to"
    assert row["status"] == spec.Status.FAILED.value


def test_instants_come_from_the_event_that_set_them(tmp_path: Path) -> None:
    """Every ``ledger_spec.INSTANT_COLUMNS`` value is an ``events.at`` of this plan's log."""
    conn = ledger(tmp_path)
    plan = drafted_plan(conn, tmp_path)
    stamps = {str(event["at"]) for event in store.all_events(conn)}
    row = store.fetch_task(conn, plan, "T1")
    for name in ("started", "last_activity", "first_renewed", "completed"):
        assert row[name] in stamps, f"tasks.{name} is not the moment of any event in the log"
    expires = store.moment(row["expires"])
    renewed = store.moment(row["last_activity"])
    assert expires is not None
    assert renewed is not None
    assert int((expires - renewed).total_seconds()) == TTL
    assert_rebuilt(conn)
