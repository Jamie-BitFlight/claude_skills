"""The four ``ledger_spec.COMMANDS`` entries that only read.

``list``, ``status``, ``ready`` and ``validate`` have no ``ledger_spec.TRANSITIONS`` entry, because
a transition is a change and these change nothing. Their summaries in ``ledger_spec.COMMANDS`` are
the whole brief: ``list`` reads every plan row, ``status`` reads every task row with its derived
columns and the plan's progress, ``ready`` reads the tasks whose ``ready`` is true, and ``validate``
prints structural findings.

A finding is not a reason code. ``ledger_spec.REASONS`` is the vocabulary a command prints to say
why it refused or did nothing; :class:`FindingCode` is ``validate``'s own vocabulary for a
structural problem in a plan that no command refuses over. :func:`check_finding_codes` runs at
import and rejects a finding code that collides with a reason code, so the two stay tellable apart.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field
from sam_schema.core.models import PlanState

from dh_core import ledger_spec
from dh_core.ledger import derive, store

if TYPE_CHECKING:  # pragma: no cover - typing only
    import sqlite3
    from collections.abc import Mapping, Sequence


class FindingCode(StrEnum):
    """The structural problems ``validate`` reports."""

    NO_TASKS = "no-tasks"
    """The plan holds no task rows."""

    MISSING_DEPENDENCY = "missing-dependency"
    """A task names a dependency the plan does not hold, so it can never become ready."""

    SELF_DEPENDENCY = "self-dependency"
    """A task names itself in ``dependencies``."""

    DEPENDENCY_CYCLE = "dependency-cycle"
    """A task is reachable from itself through ``dependencies``."""

    ARCHIVED = "archived-plan"
    """The plan is archived, so no command that changes it will run."""

    DRAFTING = "drafting-plan"
    """The plan is still drafting, so ``finalize`` has not run."""


def check_finding_codes() -> None:
    """Reject a finding code that collides with a ``ledger_spec.REASONS`` code.

    Raises:
        ValueError: When a finding code is also a reason code.
    """
    reasons = {reason.code for reason in ledger_spec.REASONS}
    clashing = sorted(code for code in FindingCode if code in reasons)
    if clashing:
        msg = f"{', '.join(clashing)} is both a validate finding and a ledger_spec reason code"
        raise ValueError(msg)


check_finding_codes()


class Finding(BaseModel):
    """One structural problem ``validate`` found."""

    code: FindingCode
    task: str = ""
    """The task the finding is about; empty for a plan-level finding."""
    detail: str = ""


class PlanStatus(BaseModel):
    """What ``status`` reads: the plan row, its progress, and every task with its derived columns."""

    plan: str
    state: str = ""
    progress: str
    archived: str | None = None
    row: dict[str, Any] = Field(default_factory=dict)
    tasks: list[dict[str, Any]] = Field(default_factory=list)


def list_plans(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Read every plan row with its derived progress.

    Args:
        conn: An open ledger connection.

    Returns:
        One dictionary per plan, ordered by id, each carrying a ``progress`` key.
    """
    rows = store.rows_of(conn.execute("SELECT * FROM plans ORDER BY plan_id"))
    for row in rows:
        row["progress"] = derive.progress(conn, str(row["plan_id"]))
    return rows


def status(conn: sqlite3.Connection, plan: str) -> PlanStatus:
    """Read one plan's tasks with their derived columns and the plan's progress.

    Args:
        conn: An open ledger connection.
        plan: The plan id.

    Returns:
        The plan row, its progress, and one dictionary per task with the derived columns merged in.

    Raises:
        LookupError: When no such plan exists.
    """
    row = store.fetch_plan(conn, plan)
    instant = store.now()
    tasks: list[dict[str, Any]] = []
    for task in store.plan_tasks(conn, plan):
        merged = dict(task)
        merged.update(derive.task_derived(conn, task, instant))
        tasks.append(merged)
    return PlanStatus(
        plan=plan,
        state=str(row["state"] or ""),
        progress=derive.progress(conn, plan),
        archived=row["archived"],
        row=row,
        tasks=tasks,
    )


def ready(conn: sqlite3.Connection, plan: str) -> list[dict[str, Any]]:
    """Read the tasks of one plan whose ``ready`` is true.

    Args:
        conn: An open ledger connection.
        plan: The plan id.

    Returns:
        The dispatchable task rows, ordered by id.
    """
    return derive.ready_tasks(conn, plan)


def cycles(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """Find every task that is reachable from itself through ``dependencies``.

    Args:
        rows: Every task row of one plan.

    Returns:
        The ids of the tasks on a cycle, sorted.
    """
    edges = {str(row["id"]): store.json_list(row["dependencies"]) for row in rows}
    on_cycle: set[str] = set()
    for start, dependencies in edges.items():
        seen: set[str] = set()
        frontier = list(dependencies)
        while frontier:
            node = frontier.pop()
            if node == start:
                on_cycle.add(start)
                break
            if node in seen:
                continue
            seen.add(node)
            frontier.extend(edges.get(node, []))
    return sorted(on_cycle)


def dependency_findings(rows: Sequence[Mapping[str, Any]]) -> list[Finding]:
    """Report every dependency of a plan's tasks that names nothing, or names itself.

    Args:
        rows: Every task row of one plan.

    Returns:
        The findings, in task order.
    """
    known = {str(row["id"]) for row in rows}
    findings: list[Finding] = []
    for row in rows:
        task = str(row["id"])
        for dependency in store.json_list(row["dependencies"]):
            if dependency == task:
                findings.append(Finding(code=FindingCode.SELF_DEPENDENCY, task=task, detail=dependency))
            elif dependency not in known:
                findings.append(Finding(code=FindingCode.MISSING_DEPENDENCY, task=task, detail=dependency))
    return findings


def validate(conn: sqlite3.Connection, plan: str) -> list[Finding]:
    """Read one plan and report its structural problems.

    Nothing here refuses: a finding is a statement about the plan, and the caller decides what to
    do with it.

    Args:
        conn: An open ledger connection.
        plan: The plan id.

    Returns:
        The findings, plan-level ones first.

    Raises:
        LookupError: When no such plan exists.
    """
    row = store.fetch_plan(conn, plan)
    rows = store.plan_tasks(conn, plan)
    findings: list[Finding] = []
    if row["archived"] is not None:
        findings.append(Finding(code=FindingCode.ARCHIVED, detail=str(row["archived"])))
    if str(row["state"] or "") == PlanState.DRAFTING.value:
        findings.append(Finding(code=FindingCode.DRAFTING))
    if not rows:
        findings.append(Finding(code=FindingCode.NO_TASKS))
    findings.extend(dependency_findings(rows))
    findings.extend(Finding(code=FindingCode.DEPENDENCY_CYCLE, task=task) for task in cycles(rows))
    return findings
