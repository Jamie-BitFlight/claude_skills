"""Candidate and checker-admission vertical tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal, cast

import pytest
from dh_core.ledger import store, transitions
from dh_core.merge_evidence import MergeEvidenceStore
from dh_core.merge_train import (
    AdmitCandidate,
    Assignment,
    DispatchMember,
    DispatchPlanDefinition,
    DispatchPlanSnapshot,
    DispatchReserved,
    HostAuthority,
    MergeQuery,
    MergeTrain,
    RegisterTrain,
    SourceGraphSnapshot,
    SubmitCandidate,
)


class Reader:
    def __init__(self, value):
        self.value = value

    def read(self, _key):
        return self.value


def service(tmp_path: Path) -> tuple[MergeTrain, sqlite3.Connection]:
    connection = store.open_ledger(tmp_path / "dh.db")
    transitions.create(
        connection,
        slug="t2",
        goal="test",
        plan_id="Pt2",
        base_sha="a" * 40,
        tasks=[
            {"id": "T1", "title": "maker", "github_issue": 1},
            {"id": "T2", "title": "checker", "github_issue": 2},
            {"id": "T3", "title": "integrator", "github_issue": 3},
        ],
    )
    definition = DispatchPlanDefinition(
        logical_id="d",
        revision="1",
        milestone=1,
        plan="Pt2",
        integration_branch="integration/t2",
        baseline_sha="a" * 40,
        quality_gates=(),
        members=(
            DispatchMember(issue=1, task="T1", role="maker"),
            DispatchMember(issue=2, task="T2", role="checker"),
            DispatchMember(issue=3, task="T3", role="integrator"),
        ),
    )
    plans = Reader(DispatchPlanSnapshot(logical_id="d", revision="1", canonical_bytes=definition.canonical_bytes()))
    graph = Reader(
        SourceGraphSnapshot(
            revision="g1",
            milestone=1,
            integration_branch="integration/t2",
            baseline_sha="a" * 40,
            members=definition.members,
        )
    )
    result = MergeTrain(connection, plans, graph, HostAuthority(authority_host_id="h"), MergeEvidenceStore(connection))
    result.register(RegisterTrain(plan_ref="d", milestone=1, plan="Pt2"))
    return result, connection


def accept_assignment(train: MergeTrain, connection, task: str) -> Assignment:
    dispatched = train.dispatch(DispatchReserved(plan="Pt2", generation=1, task=task))
    for section in ("Completion Report", "Verification Results"):
        transitions.update(
            connection, "Pt2", task, attempt=dispatched.attempt, section=section, section_content="complete"
        )
    transitions.finish(connection, "Pt2", task, attempt=dispatched.attempt, result="complete")
    transitions.accept(connection, "Pt2", task)
    role = cast("Literal['maker', 'checker', 'integrator']", dispatched.role)
    return Assignment(issue=dispatched.github_issue, task=task, attempt=dispatched.attempt, role=role)


def test_f09_changed_head_atomically_supersedes_candidate(tmp_path: Path) -> None:
    train, connection = service(tmp_path)
    maker = accept_assignment(train, connection, "T1")
    evidence = train.evidence.put(b"maker", "application/json")

    first = train.submit(
        SubmitCandidate(
            plan="Pt2",
            generation=1,
            branch="candidate",
            pull_request_ref="PR1",
            candidate_sha="b" * 40,
            base_sha="a" * 40,
            maker=maker,
            maker_evidence_digest=evidence.digest,
        )
    )
    repeated = train.submit(
        SubmitCandidate(
            plan="Pt2",
            generation=1,
            branch="candidate",
            pull_request_ref="PR1",
            candidate_sha="b" * 40,
            base_sha="a" * 40,
            maker=maker,
            maker_evidence_digest=evidence.digest,
        )
    )
    second = train.submit(
        SubmitCandidate(
            plan="Pt2",
            generation=1,
            branch="candidate",
            pull_request_ref="PR1",
            candidate_sha="c" * 40,
            base_sha="a" * 40,
            maker=maker,
            maker_evidence_digest=evidence.digest,
        )
    )

    assert (first.candidate_number, repeated.noop, second.candidate_number) == (1, "already-submitted", 2)
    rows = store.rows_of(
        connection.execute("SELECT candidate_number, superseded_seq FROM merge_candidates ORDER BY candidate_number")
    )
    assert rows[0]["superseded_seq"] is not None
    assert rows[1]["superseded_seq"] is None


def test_f08_role_tuple_substitution_refuses_without_mutation(tmp_path: Path) -> None:
    train, connection = service(tmp_path)
    maker = accept_assignment(train, connection, "T1")
    evidence = train.evidence.put(b"maker", "application/json")
    wrong = maker.model_copy(update={"issue": 99})

    with pytest.raises(store.Refusal, match="role-assignment-mismatch"):
        train.submit(
            SubmitCandidate(
                plan="Pt2",
                generation=1,
                branch="candidate",
                pull_request_ref="PR1",
                candidate_sha="b" * 40,
                base_sha="a" * 40,
                maker=wrong,
                maker_evidence_digest=evidence.digest,
            )
        )
    assert connection.execute("SELECT COUNT(*) FROM merge_candidates").fetchone()[0] == 0


def test_f11_admission_binds_distinct_accepted_checker(tmp_path: Path) -> None:
    train, connection = service(tmp_path)
    maker = accept_assignment(train, connection, "T1")
    maker_evidence = train.evidence.put(b"maker", "application/json")
    candidate = train.submit(
        SubmitCandidate(
            plan="Pt2",
            generation=1,
            branch="candidate",
            pull_request_ref="PR1",
            candidate_sha="b" * 40,
            base_sha="a" * 40,
            maker=maker,
            maker_evidence_digest=maker_evidence.digest,
        )
    )
    checker = accept_assignment(train, connection, "T2")
    checker_evidence = train.evidence.put(b"checker", "application/json")

    admitted = train.admit(
        AdmitCandidate(
            plan="Pt2",
            generation=1,
            task="T1",
            candidate_number=candidate.candidate_number,
            checker=checker,
            checker_evidence_digest=checker_evidence.digest,
        )
    )

    assert admitted.admitted_seq is not None
    assert admitted.enqueued_seq is not None
    assert train.status(MergeQuery(plan="Pt2")).train.generation == 1
