"""Three-phase claim, CAS, and reconciliation tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Literal, cast

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
    def __init__(self, candidate: str) -> None:
        self.candidate = candidate
        self.calls = 0
        self.drift = False

    def observe(self, candidate_sha: str, pull_request_ref: str) -> PolicySnapshot:
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
    def __init__(self, digest: str) -> None:
        self.digest = digest
        self.calls = 0

    def run(self, commands: tuple[str, ...], subject_sha: str) -> tuple[str, ...]:
        self.calls += 1
        return (self.digest,)


class Branch:
    def __init__(self, outcome: str = "advanced") -> None:
        self.outcome = outcome
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
        self.prepared = replace(value, prepared_identity_digest=prepared_identity_digest(value))

    def prepare(self, candidate_sha: str) -> PreparedAdvance:
        assert candidate_sha == self.prepared.candidate_oid
        return self.prepared

    def advance(self, prepared: PreparedAdvance) -> ExpectedHeadAdvanceResult:
        self.advances += 1
        assert prepared == self.prepared
        return ExpectedHeadAdvanceResult(self.outcome)

    def reconcile(self, prepared: PreparedAdvance) -> ExpectedHeadAdvanceResult:
        assert prepared == self.prepared
        return ExpectedHeadAdvanceResult(self.outcome)


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
    policies = Policies("b" * 40)
    policies.drift = drift
    gate_blob = train.evidence.put(b'{"gate":"passed"}', "application/vnd.dh.gate+json")
    gates = Gates(gate_blob.digest)
    branch = Branch(outcome)
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
