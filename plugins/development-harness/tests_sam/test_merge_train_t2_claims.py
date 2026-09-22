"""Three-phase claim, CAS, and reconciliation tests."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal, cast

import pytest
from dh_core.integration_branch import ExpectedHeadAdvanceResult, PreparedAdvance, prepared_identity_digest
from dh_core.ledger import store
from dh_core.merge_train import (
    AdmitCandidate,
    Assignment,
    DispatchReserved,
    MergeNext,
    PolicySnapshot,
    ReconcileClaim,
    SubmitCandidate,
)

from tests_sam.test_merge_train_t2_candidates import accept_assignment, service


class Policies:
    def __init__(self, candidate: str, connection=None) -> None:
        self.candidate = candidate
        self.connection = connection
        self.calls = 0
        self.drift = False

    def observe(self, candidate_sha: str, pull_request_ref: str) -> PolicySnapshot:
        if self.connection is not None:
            assert not self.connection.in_transaction
        self.calls += 1
        checks = (("tests", candidate_sha, "failure" if self.drift and self.calls >= 3 else "success"),)
        return PolicySnapshot(
            candidate_sha=candidate_sha,
            pull_request_ref=pull_request_ref,
            required_checks=checks,
            capability_identity="cap-1",
            complete=True,
            available=True,
            freshness_token=f"token-{self.calls}",
            observed_at=datetime(2026, 1, 1, 0, 0, self.calls),
        )


class Gates:
    def __init__(self, digest: str, connection=None, after=None) -> None:
        self.digest = digest
        self.connection = connection
        self.after = after
        self.calls = 0

    def run(self, commands: tuple[str, ...], subject_sha: str) -> tuple[str, ...]:
        if self.connection is not None:
            assert not self.connection.in_transaction
        self.calls += 1
        if self.after is not None:
            self.after()
        return (self.digest,)


class Branch:
    def __init__(self, outcome: str = "advanced", connection=None) -> None:
        self.outcome = outcome
        self.connection = connection
        self.advances = 0
        value = PreparedAdvance(
            remote_identity="local/test",
            target_ref="refs/heads/integration/t2",
            candidate_ref="refs/heads/candidate",
            expected_target_oid="a" * 40,
            candidate_oid="b" * 40,
            prepared_result_oid="b" * 40,
            prepared_tree_oid="c" * 40,
            ordered_parent_oids=("a" * 40,),
            prepared_identity_digest="sha256:" + "0" * 64,
        )
        self.prepared = value.model_copy(update={"prepared_identity_digest": prepared_identity_digest(value)})

    def prepare(self, candidate_sha: str) -> PreparedAdvance:
        if self.connection is not None:
            assert not self.connection.in_transaction
        assert candidate_sha == self.prepared.candidate_oid
        return self.prepared

    def advance(self, prepared: PreparedAdvance) -> ExpectedHeadAdvanceResult:
        if self.connection is not None:
            assert not self.connection.in_transaction
        self.advances += 1
        assert prepared == self.prepared
        return ExpectedHeadAdvanceResult(outcome=self.outcome)

    def reconcile(self, prepared: PreparedAdvance) -> ExpectedHeadAdvanceResult:
        if self.connection is not None:
            assert not self.connection.in_transaction
        assert prepared == self.prepared
        return ExpectedHeadAdvanceResult(outcome=self.outcome)


def admitted(tmp_path: Path, *, drift: bool = False, outcome: str = "advanced"):
    train, connection = service(tmp_path)
    maker = accept_assignment(train, connection, "T1")
    maker_evidence = train.evidence.put(b'{"maker":true}', "application/json")
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
    checker_evidence = train.evidence.put(b'{"checker":true}', "application/json")
    train.admit(
        AdmitCandidate(
            plan="Pt2",
            generation=1,
            task="T1",
            candidate_number=candidate.candidate_number,
            checker=checker,
            checker_evidence_digest=checker_evidence.digest,
        )
    )
    dispatched = train.dispatch(DispatchReserved(plan="Pt2", generation=1, task="T3"))
    role = cast("Literal['maker', 'checker', 'integrator']", dispatched.role)
    integrator = Assignment(issue=3, task="T3", attempt=dispatched.attempt, role=role)
    policies = Policies("b" * 40, connection)
    policies.drift = drift
    gate_blob = train.evidence.put(b'{"gate":"passed"}', "application/vnd.dh.gate+json")
    gates = Gates(gate_blob.digest, connection)
    branch = Branch(outcome, connection)
    train.policy_observer = policies
    train.gates = gates
    train.branch_advancer = branch
    return train, connection, integrator, policies, gates, branch


def test_f16_three_phases_precede_exactly_one_cas(tmp_path: Path) -> None:
    train, connection, integrator, policies, gates, branch = admitted(tmp_path)

    result = train.merge_next(MergeNext(plan="Pt2", generation=1, integrator=integrator))

    assert result.outcome == "ADVANCED"
    assert branch.advances == 1
    assert gates.calls == 1
    assert policies.calls == 3
    kinds = [event["kind"] for event in store.events_of(connection, "Pt2")]
    assert (
        kinds.index("merge.claimed")
        < kinds.index("merge.claim-bound")
        < kinds.index("merge.claim-prepared")
        < kinds.index("merge.finished")
    )


def test_f17_post_cas_policy_drift_requires_observation_only_reconciliation(tmp_path: Path) -> None:
    train, connection, integrator, policies, _gates, branch = admitted(tmp_path, drift=True)

    result = train.merge_next(MergeNext(plan="Pt2", generation=1, integrator=integrator))
    policies.drift = False
    branch.outcome = "advanced-after-reconciliation"
    resolved = train.reconcile(ReconcileClaim(plan="Pt2", claim_number=result.claim_number))

    assert result.phase == "RECONCILIATION_REQUIRED"
    assert resolved.outcome == "RECONCILED"
    assert branch.advances == 1
    store.rebuild(connection)
    row = connection.execute("SELECT active, conclusion FROM merge_claims").fetchone()
    assert tuple(row) == (0, "RECONCILED")


def test_f11_policy_projection_ignores_provenance_but_not_semantics() -> None:
    policy = Policies("b" * 40).observe("b" * 40, "PR1")
    provenance = policy.model_copy(update={"freshness_token": "other", "observed_at": datetime(2027, 1, 1)})
    semantic = policy.model_copy(update={"unresolved_thread_ids": ("thread-1",)})

    assert policy.semantic_projection() == provenance.semantic_projection()
    assert policy.semantic_projection() != semantic.semantic_projection()


def test_f17_repeated_unavailable_reconciliation_is_noop_without_second_cas(tmp_path: Path) -> None:
    train, connection, integrator, policies, _gates, branch = admitted(tmp_path, drift=True)
    unresolved = train.merge_next(MergeNext(plan="Pt2", generation=1, integrator=integrator))
    policies.drift = False
    branch.outcome = "reconciliation-required"
    before = len(store.events_of(connection, "Pt2"))

    first = train.reconcile(ReconcileClaim(plan="Pt2", claim_number=unresolved.claim_number))
    second = train.reconcile(ReconcileClaim(plan="Pt2", claim_number=unresolved.claim_number))

    assert first.noop == second.noop == "reconciliation-still-required"
    assert len(store.events_of(connection, "Pt2")) == before
    assert branch.advances == 1


def test_f17_permanent_ambiguity_is_terminal_blocked_not_success(tmp_path: Path) -> None:
    train, _connection, integrator, policies, _gates, branch = admitted(tmp_path, drift=True)
    unresolved = train.merge_next(MergeNext(plan="Pt2", generation=1, integrator=integrator))
    policies.drift = False
    branch.outcome = "target-stale"

    result = train.reconcile(
        ReconcileClaim(plan="Pt2", claim_number=unresolved.claim_number, permanent_reason="human reviewed ambiguity")
    )

    assert result.outcome == "PERMANENT_AMBIGUOUS"
    assert result.outcome not in {"ADVANCED", "RECONCILED"}


def test_f12_prepare_rechecks_authority_after_blocked_gate(tmp_path: Path) -> None:
    train, connection, integrator, _policies, gates, branch = admitted(tmp_path)
    gates.after = lambda: connection.execute("UPDATE tasks SET attempts=2 WHERE plan='Pt2' AND id='T3'")

    with pytest.raises(store.Refusal, match="role-assignment-mismatch"):
        train.merge_next(MergeNext(plan="Pt2", generation=1, integrator=integrator))

    assert branch.advances == 0


def test_f17_conflicting_terminal_resolution_refuses(tmp_path: Path) -> None:
    train, _connection, integrator, policies, _gates, branch = admitted(tmp_path, drift=True)
    unresolved = train.merge_next(MergeNext(plan="Pt2", generation=1, integrator=integrator))
    policies.drift = False
    branch.outcome = "advanced-after-reconciliation"
    train.reconcile(ReconcileClaim(plan="Pt2", claim_number=unresolved.claim_number))

    with pytest.raises(store.Refusal, match="train-generation-stale"):
        train.reconcile(
            ReconcileClaim(
                plan="Pt2", claim_number=unresolved.claim_number, permanent_reason="conflicting blocked resolution"
            )
        )
