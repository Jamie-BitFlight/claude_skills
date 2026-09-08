"""Hold ``implement-feature``'s ``plan status`` reads to the shape the ledger actually answers in.

``implement-feature`` runs ``plan import --from content`` before its Progress Loop, so every
``plan status`` from that point on is answered by the work ledger and shaped by
:class:`dh_core.ledger.queries.PlanStatus`. That model keeps every plan-level field inside ``row``.
The content store answers through a second, unrelated class of the same name,
:class:`sam_schema.core.models.PlanStatus`, which keeps those fields at the top level. The two
shapes share field *names*, and their models share a class *name*, while disagreeing about depth,
so a read written against the content shape does not fail against the ledger — it returns nothing,
and the reader falls through to whatever default the prose names.

For ``autonomy`` that fall-through is a safety gate: ``full_auto`` is the mode that asks the user
for no confirmations, so a plan authored as ``per_task`` or ``checkpoint`` whose autonomy read
misses runs unattended with nothing raised. :func:`test_ledger_status_keeps_plan_fields_in_row`
pins the shape that makes such a read miss, and
:func:`test_skill_reads_only_top_level_fields_the_ledger_answers_with` fails on any documented
``status["..."]`` read whose first key is not a field of ``PlanStatus``.

What the second test cannot see is prose that names a key without that notation. It is a check on
the documented read paths, not a proof that the skill's prose is shape-correct throughout.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import pytest
from dh_core.ledger import port, queries, store
from dh_core.ledger.queries import PlanStatus
from sam_schema.core.models import Plan, Task

if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Iterator

SKILL_PATH = Path(__file__).parents[1] / "skills" / "implement-feature" / "SKILL.md"
"""The skill whose ``plan status`` reads these tests hold to the ledger's shape."""

STATUS_READ = re.compile(r'status\["([^"]+)"\]')
"""Every documented read of a ``plan status`` response, capturing the first key it indexes."""

Autonomy = Literal["full_auto", "checkpoint", "per_task"]
"""The dispatch gating modes ``Plan.autonomy`` admits."""

PLAN_ID = "Pautonomy"
"""The plan id the reproduction imports under."""


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


@pytest.mark.parametrize("autonomy", ["per_task", "checkpoint"])
def test_ledger_status_keeps_plan_fields_in_row(ledger: sqlite3.Connection, autonomy: Autonomy) -> None:
    """A plan's autonomy survives the import into ``row``, and appears nowhere above it.

    Tests: the ledger's ``status`` shape, which decides where ``implement-feature`` must read.
    How: import a plan carrying a non-default autonomy, then read ``status`` back.
    Why: a top-level read of ``autonomy`` returns nothing here, and an unattended run is what the
         reader falls through to.
    """
    plan = Plan(
        feature="autonomy-probe",
        goal="probe autonomy",
        autonomy=autonomy,
        tasks=[Task(id="T1", title="first task", status="not-started")],
        plan_id=PLAN_ID,
    )
    port.import_plan(ledger, port.plan_source(plan, source="test"))

    status = queries.status(ledger, PLAN_ID)
    dumped = status.model_dump()

    assert dumped["row"]["autonomy"] == autonomy
    for absent in ("autonomy", "completion_pct", "ready_tasks"):
        assert absent not in dumped, f"{absent} is a top-level key of the ledger's status shape"


def test_skill_reads_only_top_level_fields_the_ledger_answers_with() -> None:
    """Every ``status["..."]`` the skill documents indexes a field ``PlanStatus`` declares.

    Tests: that no documented read reaches for a plan-level field at the top level.
    How: scan the skill for the read notation and check each first key against the model.
    Why: the content store's shape carries those names at the top level and the ledger's does not,
         so a read that survives the move between stores is the one that fails silently.
    """
    text = SKILL_PATH.read_text(encoding="utf-8")
    read_keys = sorted(set(STATUS_READ.findall(text)))

    assert read_keys, f"no status read found in {SKILL_PATH.name}; the check would pass vacuously"
    unknown = [key for key in read_keys if key not in PlanStatus.model_fields]
    assert not unknown, (
        f"{SKILL_PATH.name} reads {unknown} from the top level of a plan status response; "
        f"PlanStatus declares {sorted(PlanStatus.model_fields)}, and every plan-level field "
        f"sits inside row"
    )
