"""Registered merge-train service for immutable plans and reserved dispatch."""

from __future__ import annotations

import hashlib
import json
import operator
import sqlite3
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any, Literal, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from dh_core.integration_branch import ExpectedHeadAdvanceResult, PreparedAdvance
from dh_core.ledger import store, transitions
from dh_core.ledger.transitions import _dispatch_registered as dispatch_registered
from dh_core.merge_evidence import MergeEvidenceStore


class Request(BaseModel):
    """Strict base for merge-train requests and frozen definitions."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DispatchMember(Request):
    """One frozen assignment from the checked dispatch plan."""

    issue: int = Field(ge=1)
    task: str = Field(min_length=1)
    role: Literal["maker", "checker", "integrator"]
    dependencies: tuple[str, ...] = ()
    conflict_group: str | None = None

    @field_validator("conflict_group")
    @classmethod
    def nonempty_group(cls, value: str | None) -> str | None:
        """Reject whitespace resource names rather than treating them as unreserved.

        Returns:
            The validated resource name.
        """
        if value is not None and not value.strip():
            raise ValueError("conflict_group must be non-empty when supplied")
        return value


class DispatchPlanDefinition(Request):
    """The complete checked execution definition registration freezes."""

    logical_id: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    milestone: int = Field(ge=1)
    plan: str = Field(min_length=1)
    integration_branch: str = Field(min_length=1)
    baseline_sha: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    quality_gates: tuple[str, ...]
    members: tuple[DispatchMember, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_members(self) -> DispatchPlanDefinition:
        """Reject aliases represented by duplicate issue or task identities.

        Returns:
            The validated definition.
        """
        tasks = [member.task for member in self.members]
        issues = [member.issue for member in self.members]
        if len(tasks) != len(set(tasks)) or len(issues) != len(set(issues)):
            raise ValueError("dispatch members must have unique task and issue identities")
        return self

    def canonical_bytes(self) -> bytes:
        """Return deterministic complete bytes for identity and event retention."""
        value = self.model_dump(mode="json")
        value["members"] = sorted(value["members"], key=operator.itemgetter("task", "issue"))
        return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


class DispatchPlanSnapshot(Request):
    """Immutable canonical output returned by the authoritative plan parser."""

    logical_id: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    canonical_bytes: bytes = Field(min_length=1)

    @property
    def digest(self) -> str:
        """Return the identity of the exact parser output bytes."""
        return digest(self.canonical_bytes)

    def definition(self) -> DispatchPlanDefinition:
        """Parse the complete canonical bytes through the strict service model.

        Returns:
            The strict execution definition parsed from the authoritative bytes.
        """
        parsed = DispatchPlanDefinition.model_validate_json(self.canonical_bytes)
        if parsed.logical_id != self.logical_id or parsed.revision != self.revision:
            transitions.refuse("dispatch-plan-stale")
        return parsed


class SourceGraphSnapshot(Request):
    """Immutable GitHub/source-graph facts checked against dispatch policy."""

    revision: str = Field(min_length=1)
    milestone: int = Field(ge=1)
    integration_branch: str = Field(min_length=1)
    baseline_sha: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    members: tuple[DispatchMember, ...] = Field(min_length=1)

    @property
    def digest(self) -> str:
        """Return the canonical graph identity computed by the service model."""
        value = self.model_dump(mode="json")
        value["members"] = sorted(value["members"], key=operator.itemgetter("task", "issue"))
        return canonical_digest(value)


class DispatchPlanReader(Protocol):
    """Read immutable canonical dispatch-plan parser output."""

    def read(self, plan_ref: str, /) -> DispatchPlanSnapshot:
        """Return the immutable canonical snapshot for a logical plan reference."""
        ...


class SourceGraphReader(Protocol):
    """Read immutable provider graph facts for one milestone."""

    def read(self, milestone: int, /) -> SourceGraphSnapshot:
        """Return the immutable provider graph snapshot for a milestone."""
        ...


class HostAuthority(Request):
    """Local opaque configuration marker, not an authenticated principal."""

    authority_host_id: str = Field(min_length=1)


class RegisterTrain(Request):
    """Address sources the service resolves; no authority bytes are caller supplied."""

    plan_ref: str = Field(min_length=1)
    milestone: int = Field(ge=1)
    plan: str = Field(min_length=1)


class DispatchReserved(Request):
    """Dispatch one frozen assignment through the registered authority."""

    plan: str
    generation: int = Field(ge=1)
    task: str
    ttl_seconds: int | None = Field(default=None, ge=1)
    worktree: str | None = None


class Assignment(Request):
    """Frozen role assignment consumed by one merge decision."""

    issue: int = Field(ge=1)
    task: str = Field(min_length=1)
    attempt: int = Field(ge=1)
    role: Literal["maker", "checker", "integrator"]


class SubmitCandidate(Request):
    """Submit one immutable maker candidate."""

    plan: str
    generation: int = Field(ge=1)
    branch: str
    pull_request_ref: str
    candidate_sha: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    base_sha: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    maker: Assignment
    maker_evidence_digest: str


class PolicySnapshot(Request):
    """Complete policy-relevant provider observation."""

    candidate_sha: str
    pull_request_ref: str
    required_checks: tuple[tuple[str, str, str], ...]
    unresolved_thread_ids: tuple[str, ...] = ()
    unresponded_thread_ids: tuple[str, ...] = ()
    blocking_reviews: tuple[tuple[str, str], ...] = ()
    capability_identity: str
    complete: bool
    available: bool
    freshness_token: str
    observed_at: datetime

    def semantic_projection(self) -> tuple[object, ...]:
        """Return policy fields without provenance-only values."""
        return (
            self.candidate_sha,
            tuple(sorted(self.required_checks)),
            tuple(sorted(self.unresolved_thread_ids)),
            tuple(sorted(self.unresponded_thread_ids)),
            tuple(sorted(self.blocking_reviews)),
            self.capability_identity,
            self.complete,
            self.available,
        )


class AdmitCandidate(Request):
    """Bind checker authority and complete provider policy evidence."""

    plan: str
    generation: int = Field(ge=1)
    task: str
    candidate_number: int = Field(ge=1)
    checker: Assignment
    checker_evidence_digest: str


class TrainSupersession(Request):
    """Checker-approved replacement definition request."""

    plan: str
    generation: int = Field(ge=1)
    replacement_plan_ref: str
    replacement_milestone: int = Field(ge=1)
    replacement_checker_evidence_digest: str
    reason: str = Field(min_length=1)


class CandidateView(BaseModel):
    """Stored immutable candidate and admission state."""

    plan: str
    generation: int
    task: str
    candidate_number: int
    candidate_sha: str
    superseded_seq: int | None = None
    admitted_seq: int | None = None
    enqueued_seq: int | None = None
    outcome: str | None = None
    noop: str | None = None


class MergeNext(Request):
    """Claim and process the oldest admitted candidate."""

    plan: str
    generation: int = Field(ge=1)
    integrator: Assignment


class ReconcileClaim(Request):
    """Observe and resolve one durable unresolved claim without CAS."""

    plan: str
    claim_number: int = Field(ge=1)
    permanent_reason: str | None = None


class MergeResult(BaseModel):
    """Typed claim phase or terminal outcome."""

    plan: str
    claim_number: int
    phase: str
    outcome: str | None = None
    result_sha: str | None = None
    noop: str | None = None


class PolicyStatusPort(Protocol):
    """Observe complete PR, review, check, and capability policy state."""

    def observe(self, candidate_sha: str, pull_request_ref: str) -> PolicySnapshot:
        """Return one complete immutable snapshot."""
        ...


class GateRunnerPort(Protocol):
    """Run all frozen quality gates against one immutable subject."""

    def run(self, commands: tuple[str, ...], subject_sha: str) -> tuple[str, ...]:
        """Return immutable evidence digests for successful gates."""
        ...


class BranchPreparationPort(Protocol):
    """Prepare and observe one branch-bound immutable result."""

    def prepare(self, candidate_sha: str) -> PreparedAdvance:
        """Return durable exact operands without mutating the target."""
        ...

    def advance(self, prepared: PreparedAdvance) -> ExpectedHeadAdvanceResult:
        """Attempt the sole exact-old target CAS."""
        ...

    def reconcile(self, prepared: PreparedAdvance) -> ExpectedHeadAdvanceResult:
        """Observe the durable prepared result without invoking CAS."""
        ...


class MergeQuery(Request):
    """Select one registered plan, optionally at a historical generation."""

    plan: str
    generation: int | None = Field(default=None, ge=1)


class HistoryQuery(MergeQuery):
    """Select complete event envelopes with caller-controlled pagination."""

    event_kind: str | None = None
    offset: int = Field(default=0, ge=0)
    limit: int | None = Field(default=None, ge=1)


class TrainView(BaseModel):
    """Registered generation identity returned by train mutations."""

    plan: str
    generation: int
    dispatch_plan_id: str
    dispatch_plan_revision: str
    dispatch_plan_digest: str
    source_graph_revision: str
    source_graph_digest: str
    authority_host_id: str
    registered_seq: int
    superseded_seq: int | None = None
    invalidated_seq: int | None = None
    invalidation_reason: str | None = None
    replacement_source: str | None = None
    replacement_revision: str | None = None
    noop: str | None = None


class ReservationView(BaseModel):
    """One materialized conflict-group reservation."""

    plan: str
    generation: int
    conflict_group: str
    task: str
    attempt: int
    role: str
    github_issue: int
    active: bool
    conclusion: str | None


class DispatchView(BaseModel):
    """The assignment tuple atomically opened by registered dispatch."""

    plan: str
    generation: int
    task: str
    attempt: int
    role: str
    github_issue: int
    conflict_group: str | None
    noop: str | None = None


class MergePage(BaseModel):
    """Current registered generation and reservations."""

    train: TrainView
    reservations: list[ReservationView]
    candidates: list[CandidateView] = Field(default_factory=list)
    claims: list[MergeResult] = Field(default_factory=list)


class ExplainQuery(MergeQuery):
    """Explain stored blockers for one generation."""


class Explanation(BaseModel):
    """Stored-state merge readiness explanation."""

    plan: str
    generation: int
    blockers: list[str]


class HistoryPage(BaseModel):
    """Complete matching ledger event envelopes."""

    offset: int
    limit: int | None
    returned: int
    total: int
    events: list[dict[str, object]]


class ValidationResult(BaseModel):
    """Structural findings for a registered train projection."""

    valid: bool
    findings: list[str]


def digest(value: bytes) -> str:
    """Return the lower-case SHA-256 identity used by merge-train definitions."""
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def canonical_digest(value: object) -> str:
    """Hash a deterministic JSON representation of one definition projection.

    Returns:
        Its SHA-256 identity.
    """
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def train_row(connection: sqlite3.Connection, plan: str, generation: int | None = None) -> dict[str, Any]:
    """Read one active or explicitly selected registered generation.

    Returns:
        The materialized train row.
    """
    query = (
        "SELECT * FROM merge_trains WHERE plan = :plan AND superseded_seq IS NULL "
        "AND invalidated_seq IS NULL ORDER BY generation DESC LIMIT 1"
        if generation is None
        else "SELECT * FROM merge_trains WHERE plan = :plan AND generation = :generation "
        "ORDER BY generation DESC LIMIT 1"
    )
    found = store.rows_of(connection.execute(query, {"plan": plan, "generation": generation}))
    if not found:
        transitions.refuse("merge-train-not-registered")
    return found[0]


def definition_event(connection: sqlite3.Connection, plan: str, generation: int) -> dict[str, Any]:
    """Read the immutable definition from its registration event.

    Returns:
        The complete registration payload.
    """
    for event in store.events_of(connection, plan, kind="merge.train-registered"):
        payload = event["payload"]
        if isinstance(payload, dict) and int(payload.get("generation", 0)) == generation:
            return payload
    transitions.refuse("dispatch-plan-stale")
    return None


def require_assignment(
    ledger: sqlite3.Connection, plan: str, generation: int, assignment: Assignment, *, accepted: bool
) -> None:
    """Require an exact registered dispatch binding and current attempt."""
    rows = store.rows_of(
        ledger.execute(
            "SELECT d.*, t.attempts, t.accepted FROM merge_dispatches d JOIN tasks t ON t.plan=d.plan AND t.id=d.task "
            "WHERE d.plan=? AND d.generation=? AND d.task=? AND d.attempt=?",
            (plan, generation, assignment.task, assignment.attempt),
        )
    )
    if not rows:
        transitions.refuse("role-assignment-mismatch")
    row = rows[0]
    if (int(row["github_issue"]), str(row["role"]), int(row["attempts"]), bool(row["accepted"])) != (
        assignment.issue,
        assignment.role,
        assignment.attempt,
        accepted,
    ):
        transitions.refuse("role-assignment-mismatch")


def current_candidate(ledger: sqlite3.Connection, plan: str, generation: int, task: str) -> dict[str, Any] | None:
    """Read the sole current candidate for a task.

    Returns:
        The current row, or None.
    """
    rows = store.rows_of(
        ledger.execute(
            "SELECT * FROM merge_candidates WHERE plan=? AND generation=? AND task=? AND superseded_seq IS NULL "
            "AND outcome IS NULL ORDER BY candidate_number DESC LIMIT 1",
            (plan, generation, task),
        )
    )
    return rows[0] if rows else None


def candidate_row(ledger: sqlite3.Connection, plan: str, generation: int, task: str, number: int) -> dict[str, Any]:
    """Read one exact candidate or refuse.

    Returns:
        The exact candidate row.
    """
    rows = store.rows_of(
        ledger.execute(
            "SELECT * FROM merge_candidates WHERE plan=? AND generation=? AND task=? AND candidate_number=?",
            (plan, generation, task, number),
        )
    )
    if not rows:
        transitions.refuse("merge-train-not-registered")
    return rows[0]


def candidate_view(row: dict[str, Any], *, noop: str | None = None) -> CandidateView:
    """Convert one candidate row to its typed public view.

    Returns:
        The typed candidate view.
    """
    return CandidateView(
        plan=str(row["plan"]),
        generation=int(row["generation"]),
        task=str(row["task"]),
        candidate_number=int(row["candidate_number"]),
        candidate_sha=str(row["candidate_sha"]),
        superseded_seq=int(row["superseded_seq"]) if row["superseded_seq"] is not None else None,
        admitted_seq=int(row["admitted_seq"]) if row["admitted_seq"] is not None else None,
        enqueued_seq=int(row["enqueued_seq"]) if row["enqueued_seq"] is not None else None,
        outcome=str(row["outcome"]) if row["outcome"] is not None else None,
        noop=noop,
    )


def observe_policy(
    service: MergeTrain, candidate: dict[str, Any], *, require_acceptable: bool = True
) -> PolicySnapshot:
    """Observe and validate complete acceptable provider state.

    Returns:
        The complete snapshot.
    """
    observer = cast("PolicyStatusPort", service.policy_observer)
    snapshot = observer.observe(str(candidate["candidate_sha"]), str(candidate["pull_request_ref"]))
    if (require_acceptable and not policy_acceptable(snapshot)) or snapshot.candidate_sha != candidate["candidate_sha"]:
        transitions.refuse("source-graph-stale")
    return snapshot


def policy_acceptable(snapshot: PolicySnapshot) -> bool:
    """Return whether every complete policy fact permits progress."""
    return (
        snapshot.available
        and snapshot.complete
        and not snapshot.unresolved_thread_ids
        and not snapshot.unresponded_thread_ids
        and not snapshot.blocking_reviews
        and all(
            subject == snapshot.candidate_sha and conclusion == "success"
            for _, subject, conclusion in snapshot.required_checks
        )
    )


def claim_row(ledger: sqlite3.Connection, plan: str, number: int) -> dict[str, Any]:
    """Read one exact claim.

    Returns:
        The persisted claim row.
    """
    rows = store.rows_of(ledger.execute("SELECT * FROM merge_claims WHERE plan=? AND claim_number=?", (plan, number)))
    if not rows:
        transitions.refuse("merge-train-not-registered")
    return rows[0]


def update_claim(ledger: sqlite3.Connection, plan: str, number: int, values: Mapping[str, object]) -> None:
    """Apply declared claim fields after appending their event."""
    ledger.execute(
        "UPDATE merge_claims SET phase=COALESCE(:phase,phase), expires=COALESCE(:expires,expires), "
        "expected_target_sha=COALESCE(:expected_target_sha,expected_target_sha), "
        "expected_candidate_sha=COALESCE(:expected_candidate_sha,expected_candidate_sha), "
        "policy_snapshot_digest=COALESCE(:policy_snapshot_digest,policy_snapshot_digest), "
        "result_sha=COALESCE(:result_sha,result_sha), prepared_identity_digest=COALESCE(:prepared_identity_digest,prepared_identity_digest), "
        "prepared_json=COALESCE(:prepared_json,prepared_json), gate_evidence_refs=COALESCE(:gate_evidence_refs,gate_evidence_refs) "
        "WHERE plan=:plan AND claim_number=:claim_number",
        {
            "phase": values.get("phase"),
            "expires": values.get("expires"),
            "expected_target_sha": values.get("expected_target_sha"),
            "expected_candidate_sha": values.get("expected_candidate_sha"),
            "policy_snapshot_digest": values.get("policy_snapshot_digest"),
            "result_sha": values.get("result_sha"),
            "prepared_identity_digest": values.get("prepared_identity_digest"),
            "prepared_json": values.get("prepared_json"),
            "gate_evidence_refs": values.get("gate_evidence_refs"),
            "plan": plan,
            "claim_number": number,
        },
    )


def prepared_from_claim(claim: dict[str, Any]) -> PreparedAdvance:
    """Reconstruct only the durable prepared identity.

    Returns:
        The exact persisted prepared operands.
    """
    value = json.loads(str(claim["prepared_json"]))
    value["ordered_parent_oids"] = tuple(value["ordered_parent_oids"])
    return PreparedAdvance(**value)


def recheck_claim(
    service: MergeTrain, request: MergeNext, candidate: dict[str, Any], claim_number: int, phase: str
) -> None:
    """Recheck authority after external work and before a phase commit."""
    train = train_row(service.ledger, request.plan)
    service.require_host(train)
    require_assignment(service.ledger, request.plan, request.generation, request.integrator, accepted=False)
    claim = claim_row(service.ledger, request.plan, claim_number)
    current = current_candidate(service.ledger, request.plan, request.generation, str(candidate["task"]))
    if (
        claim["phase"] != phase
        or not int(claim["active"])
        or current is None
        or current["candidate_number"] != candidate["candidate_number"]
    ):
        transitions.refuse("train-generation-stale")


def open_claim(
    service: MergeTrain, request: MergeNext, definition: DispatchPlanDefinition
) -> tuple[dict[str, Any], int, DispatchPlanDefinition]:
    """Create the sole active unbound claim.

    Returns:
        Candidate row, claim number, and frozen definition.
    """
    with store.transaction(service.ledger):
        recover_expired_claim(service, request)
        if service.ledger.execute("SELECT 1 FROM merge_claims WHERE plan=? AND active=1", (request.plan,)).fetchone():
            transitions.refuse("registered-plan-active")
        rows = store.rows_of(
            service.ledger.execute(
                "SELECT * FROM merge_candidates WHERE plan=? AND generation=? AND superseded_seq IS NULL "
                "AND admitted_seq IS NOT NULL AND enqueued_seq IS NOT NULL AND outcome IS NULL ORDER BY enqueued_seq, task LIMIT 1",
                (request.plan, request.generation),
            )
        )
        if not rows:
            transitions.refuse("merge-train-not-registered")
        candidate = rows[0]
        number = int(
            service.ledger.execute(
                "SELECT COALESCE(MAX(claim_number), 0) + 1 FROM merge_claims WHERE plan=?", (request.plan,)
            ).fetchone()[0]
        )
        payload = {
            "claim_number": number,
            "candidate_task": candidate["task"],
            "candidate_number": candidate["candidate_number"],
            "integrator_issue": request.integrator.issue,
            "integrator_task": request.integrator.task,
            "integrator_attempt": request.integrator.attempt,
            "phase": "UNBOUND",
            "expires": store.timestamp(store.now() + timedelta(seconds=300)),
        }
        store.append_event(
            service.ledger,
            kind="merge.claimed",
            plan=request.plan,
            task=str(candidate["task"]),
            payload=payload,
            at=store.now(),
        )
        row = {**store.blank_row("merge_claims"), **payload, "plan": request.plan, "active": 1}
        columns = [column.name for column in store.TABLES["merge_claims"]]
        service.ledger.execute(store.insert_statement("merge_claims", columns), {name: row[name] for name in columns})
    return candidate, number, definition


def recover_expired_claim(service: MergeTrain, request: MergeNext) -> None:
    """Recover an expired pre-mutation claim or preserve ambiguous prepared state."""
    rows = store.rows_of(
        service.ledger.execute(
            "SELECT * FROM merge_claims WHERE plan=? AND active=1 ORDER BY claim_number LIMIT 1", (request.plan,)
        )
    )
    if not rows:
        return
    claim = rows[0]
    deadline = store.moment(claim["expires"])
    if deadline is None or store.now() <= deadline:
        transitions.refuse("registered-plan-active")
    if claim["phase"] in {"UNBOUND", "BOUND"}:
        payload = {"claim_number": claim["claim_number"], "conclusion": "EXPIRED_NO_MUTATION"}
        sequence = store.append_event(
            service.ledger,
            kind="merge.claim-recovered",
            plan=request.plan,
            task=str(claim["candidate_task"]),
            payload=payload,
            at=store.now(),
        )
        service.ledger.execute(
            "UPDATE merge_claims SET active=0, conclusion=?, concluded_seq=? WHERE plan=? AND claim_number=?",
            (payload["conclusion"], sequence, request.plan, claim["claim_number"]),
        )
        return
    transitions.refuse("registered-plan-active")


def bind_claim(
    service: MergeTrain, request: MergeNext, candidate: dict[str, Any], number: int
) -> tuple[PreparedAdvance, PolicySnapshot]:
    """Observe immutable heads and persist a bound claim.

    Returns:
        Prepared operands and bound policy snapshot.
    """
    snapshot = observe_policy(service, candidate)
    advancer = cast("BranchPreparationPort", service.branch_advancer)
    prepared = advancer.prepare(str(candidate["candidate_sha"]))
    if prepared.candidate_oid != candidate["candidate_sha"]:
        transitions.refuse("role-assignment-mismatch")
    blob = service.evidence.put(snapshot.model_dump_json().encode(), "application/json")
    payload = {
        "claim_number": number,
        "phase": "BOUND",
        "expires": store.timestamp(store.now() + timedelta(seconds=300)),
        "expected_target_sha": prepared.expected_target_oid,
        "expected_candidate_sha": prepared.candidate_oid,
        "policy_snapshot_digest": blob.digest,
    }
    with store.transaction(service.ledger):
        recheck_claim(service, request, candidate, number, "UNBOUND")
        store.append_event(
            service.ledger,
            kind="merge.claim-bound",
            plan=request.plan,
            task=str(candidate["task"]),
            payload=payload,
            at=store.now(),
        )
        update_claim(service.ledger, request.plan, number, payload)
    return prepared, snapshot


def prepare_claim(
    service: MergeTrain,
    request: MergeNext,
    candidate: dict[str, Any],
    number: int,
    prepared: PreparedAdvance,
    definition: DispatchPlanDefinition,
) -> PolicySnapshot:
    """Run gates, refresh policy, and persist durable prepared identity.

    Returns:
        The final pre-CAS policy snapshot.
    """
    gates = cast("GateRunnerPort", service.gates)
    gate_refs = gates.run(definition.quality_gates, prepared.prepared_result_oid)
    snapshot = observe_policy(service, candidate)
    blob = service.evidence.put(snapshot.model_dump_json().encode(), "application/json")
    payload = {
        "claim_number": number,
        "phase": "PREPARED",
        "expires": store.timestamp(store.now() + timedelta(seconds=300)),
        "result_sha": prepared.prepared_result_oid,
        "prepared_identity_digest": prepared.prepared_identity_digest,
        "prepared_json": prepared.model_dump_json(),
        "gate_evidence_refs": json.dumps(list(gate_refs)),
        "policy_snapshot_digest": blob.digest,
    }
    with store.transaction(service.ledger):
        recheck_claim(service, request, candidate, number, "BOUND")
        store.append_event(
            service.ledger,
            kind="merge.claim-prepared",
            plan=request.plan,
            task=str(candidate["task"]),
            payload=payload,
            at=store.now(),
        )
        update_claim(service.ledger, request.plan, number, payload)
    return snapshot


def finish_claim(
    service: MergeTrain,
    plan: str,
    candidate: dict[str, Any],
    claim_number: int,
    prepared: PreparedAdvance,
    policy_digest: str,
    kind: str,
    conclusion: str,
) -> MergeResult:
    """Atomically terminalize one exact prepared claim and candidate.

    Returns:
        The terminal merge result.
    """
    with store.transaction(service.ledger):
        claim = claim_row(service.ledger, plan, claim_number)
        if claim["prepared_identity_digest"] != prepared.prepared_identity_digest or not int(claim["active"]):
            transitions.refuse("train-generation-stale")
        payload = {
            "generation": candidate["generation"],
            "candidate_number": candidate["candidate_number"],
            "claim_number": claim_number,
            "result_sha": prepared.prepared_result_oid,
            "conclusion": conclusion,
            "policy_snapshot_digest": policy_digest,
        }
        sequence = store.append_event(
            service.ledger, kind=kind, plan=plan, task=str(candidate["task"]), payload=payload, at=store.now()
        )
        service.ledger.execute(
            "UPDATE merge_claims SET active=0, conclusion=?, concluded_seq=? WHERE plan=? AND claim_number=?",
            (conclusion, sequence, plan, claim_number),
        )
        service.ledger.execute(
            "UPDATE merge_candidates SET outcome=?, result_sha=?, finished_seq=? WHERE plan=? AND generation=? AND task=? AND candidate_number=?",
            (
                conclusion,
                prepared.prepared_result_oid,
                sequence,
                plan,
                candidate["generation"],
                candidate["task"],
                candidate["candidate_number"],
            ),
        )
    return MergeResult(
        plan=plan,
        claim_number=claim_number,
        phase="TERMINAL",
        outcome=conclusion,
        result_sha=prepared.prepared_result_oid,
    )


def require_reconciliation(
    service: MergeTrain,
    plan: str,
    candidate: dict[str, Any],
    claim_number: int,
    prepared: PreparedAdvance,
    policy_digest: str,
) -> MergeResult:
    """Persist an active nonterminal reconciliation-required phase.

    Returns:
        The unresolved claim result.
    """
    payload = {
        "claim_number": claim_number,
        "phase": "RECONCILIATION_REQUIRED",
        "result_sha": prepared.prepared_result_oid,
        "prepared_identity_digest": prepared.prepared_identity_digest,
        "policy_snapshot_digest": policy_digest,
    }
    with store.transaction(service.ledger):
        claim = claim_row(service.ledger, plan, claim_number)
        if claim["phase"] != "PREPARED" or not int(claim["active"]):
            transitions.refuse("train-generation-stale")
        store.append_event(
            service.ledger,
            kind="merge.reconciliation-required",
            plan=plan,
            task=str(candidate["task"]),
            payload=payload,
            at=store.now(),
        )
        update_claim(service.ledger, plan, claim_number, payload)
    return MergeResult(
        plan=plan, claim_number=claim_number, phase="RECONCILIATION_REQUIRED", result_sha=prepared.prepared_result_oid
    )


class MergeTrain:
    """Service owning T1 authoritative registration and reserved dispatch."""

    def __init__(
        self,
        ledger: sqlite3.Connection,
        dispatch_plans: DispatchPlanReader,
        source_graph: SourceGraphReader,
        host_authority: HostAuthority,
        evidence: MergeEvidenceStore | None = None,
        policy_observer: PolicyStatusPort | None = None,
        branch_advancer: BranchPreparationPort | None = None,
        gates: GateRunnerPort | None = None,
    ) -> None:
        """Bind the service to one existing ledger and configured host marker."""
        self.ledger = ledger
        self.dispatch_plans: Any = dispatch_plans
        self.source_graph: Any = source_graph
        self.host_authority = host_authority
        self.evidence = evidence or MergeEvidenceStore(ledger)
        self.policy_observer = policy_observer
        self.branch_advancer = branch_advancer
        self.gates = gates
        self.supersede = self.execute_supersede

    def execute_supersede(self, request: TrainSupersession) -> TrainView:
        """Conclude a generation using resolved replacement evidence.

        Returns:
            The retired train generation.
        """
        train = train_row(self.ledger, request.plan, request.generation)
        self.require_host(train)
        replacement = self.dispatch_plans.read(request.replacement_plan_ref)
        graph = self.source_graph.read(request.replacement_milestone)
        definition = replacement.definition()
        evidence, approval = self.evidence.parse(request.replacement_checker_evidence_digest, json.loads)
        if evidence.media_type != "application/json" or not isinstance(approval, dict):
            transitions.refuse("replacement-definition-unapproved")
        expected = {
            "dispatch_plan_id": replacement.logical_id,
            "dispatch_plan_revision": replacement.revision,
            "dispatch_plan_digest": replacement.digest,
        }
        if any(approval.get(name) != value for name, value in expected.items()):
            transitions.refuse("replacement-definition-unapproved")
        self.validate_definition(definition, graph)
        with store.transaction(self.ledger):
            row = train_row(self.ledger, request.plan, request.generation)
            self.require_host(row)
            active = self.ledger.execute(
                "SELECT 1 FROM merge_claims WHERE plan=? AND active=1 UNION ALL "
                "SELECT 1 FROM tasks WHERE plan=? AND (attempt_open=1 OR (status='complete' AND accepted=0)) LIMIT 1",
                (request.plan, request.plan),
            ).fetchone()
            if active is not None:
                transitions.refuse("train-generation-active")
            payload = {
                "generation": request.generation,
                "current_dispatch_plan_revision": str(row["dispatch_plan_revision"]),
                "current_dispatch_plan_digest": str(row["dispatch_plan_digest"]),
                "replacement_dispatch_plan_id": replacement.logical_id,
                "replacement_dispatch_plan_revision": replacement.revision,
                "replacement_dispatch_plan_digest": replacement.digest,
                "replacement_checker_evidence_digest": request.replacement_checker_evidence_digest,
                "reason": request.reason,
            }
            sequence = store.append_event(
                self.ledger,
                kind="merge.train-superseded",
                plan=request.plan,
                task=None,
                payload=payload,
                at=store.now(),
            )
            self.ledger.execute(
                "UPDATE merge_trains SET superseded_seq=? WHERE plan=? AND generation=?",
                (sequence, request.plan, request.generation),
            )
            row["superseded_seq"] = sequence
        return self.train_view(row)

    def submit(self, request: SubmitCandidate) -> CandidateView:
        """Submit or supersede one immutable maker candidate.

        Returns:
            The current candidate.
        """
        train = train_row(self.ledger, request.plan)
        self.require_host(train)
        self.fresh_definition(train)
        self.evidence.require(request.maker_evidence_digest)
        with store.transaction(self.ledger):
            train = train_row(self.ledger, request.plan)
            self.require_host(train)
            if int(train["generation"]) != request.generation:
                transitions.refuse("train-generation-stale")
            require_assignment(self.ledger, request.plan, request.generation, request.maker, accepted=True)
            if request.maker.role != "maker" or request.base_sha != str(train["baseline_sha"]):
                transitions.refuse("role-assignment-mismatch")
            current = current_candidate(self.ledger, request.plan, request.generation, request.maker.task)
            identity = (
                request.branch,
                request.pull_request_ref,
                request.candidate_sha,
                request.base_sha,
                request.maker.issue,
                request.maker.task,
                request.maker.attempt,
                request.maker_evidence_digest,
            )
            if current is not None:
                held = tuple(
                    current[name]
                    for name in (
                        "branch",
                        "pull_request_ref",
                        "candidate_sha",
                        "base_sha",
                        "maker_issue",
                        "maker_task",
                        "maker_attempt",
                        "maker_evidence_digest",
                    )
                )
                if held == identity:
                    return candidate_view(current, noop="already-submitted")
                active_claim = self.ledger.execute(
                    "SELECT 1 FROM merge_claims WHERE plan=? AND candidate_task=? AND candidate_number=? AND active=1",
                    (current["plan"], current["task"], current["candidate_number"]),
                ).fetchone()
                if current["outcome"] is not None or active_claim is not None:
                    transitions.refuse("registered-plan-active")
                next_number = int(current["candidate_number"]) + 1
                superseded = store.append_event(
                    self.ledger,
                    kind="merge.candidate-superseded",
                    plan=request.plan,
                    task=request.maker.task,
                    payload={
                        "generation": request.generation,
                        "candidate_number": int(current["candidate_number"]),
                        "replacement_candidate_number": next_number,
                    },
                    at=store.now(),
                )
                self.ledger.execute(
                    "UPDATE merge_candidates SET superseded_seq = ? WHERE plan = ? AND generation = ? AND task = ? AND candidate_number = ?",
                    (superseded, request.plan, request.generation, request.maker.task, current["candidate_number"]),
                )
            else:
                next_number = 1
            payload = {
                "generation": request.generation,
                "candidate_number": next_number,
                "branch": request.branch,
                "pull_request_ref": request.pull_request_ref,
                "candidate_sha": request.candidate_sha,
                "base_sha": request.base_sha,
                "maker_issue": request.maker.issue,
                "maker_task": request.maker.task,
                "maker_attempt": request.maker.attempt,
                "maker_evidence_digest": request.maker_evidence_digest,
                "supersedes_candidate_number": int(current["candidate_number"]) if current else None,
            }
            sequence = store.append_event(
                self.ledger,
                kind="merge.candidate-submitted",
                plan=request.plan,
                task=request.maker.task,
                payload=payload,
                at=store.now(),
            )
            row = {
                **store.blank_row("merge_candidates"),
                **payload,
                "plan": request.plan,
                "task": request.maker.task,
                "submitted_seq": sequence,
            }
            columns = [column.name for column in store.TABLES["merge_candidates"]]
            self.ledger.execute(
                store.insert_statement("merge_candidates", columns), {name: row[name] for name in columns}
            )
        return candidate_view(row)

    def admit(self, request: AdmitCandidate) -> CandidateView:
        """Admit and enqueue a candidate after checker/provider validation.

        Returns:
            The admitted candidate.
        """
        train = train_row(self.ledger, request.plan)
        self.require_host(train)
        self.fresh_definition(train)
        self.evidence.require(request.checker_evidence_digest)
        observed_candidate = candidate_row(
            self.ledger, request.plan, request.generation, request.task, request.candidate_number
        )
        if self.policy_observer is None:
            transitions.refuse("expected-head-unsupported")
        policy = observe_policy(self, observed_candidate)
        policy_evidence = self.evidence.put(policy.model_dump_json().encode(), "application/json")
        with store.transaction(self.ledger):
            train = train_row(self.ledger, request.plan)
            self.require_host(train)
            if int(train["generation"]) != request.generation:
                transitions.refuse("train-generation-stale")
            require_assignment(self.ledger, request.plan, request.generation, request.checker, accepted=True)
            if request.checker.role != "checker" or request.checker.task == request.task:
                transitions.refuse("role-assignment-mismatch")
            row = candidate_row(self.ledger, request.plan, request.generation, request.task, request.candidate_number)
            if row["superseded_seq"] is not None or row["outcome"] is not None:
                transitions.refuse("train-generation-stale")
            if row["admitted_seq"] is not None:
                exact = (
                    int(row["checker_issue"]),
                    str(row["checker_task"]),
                    int(row["checker_attempt"]),
                    str(row["checker_evidence_digest"]),
                ) == (
                    request.checker.issue,
                    request.checker.task,
                    request.checker.attempt,
                    request.checker_evidence_digest,
                )
                if exact:
                    return candidate_view(row, noop="already-admitted")
                transitions.refuse("role-assignment-mismatch")
            payload = {
                "generation": request.generation,
                "candidate_number": request.candidate_number,
                "checker_issue": request.checker.issue,
                "checker_task": request.checker.task,
                "checker_attempt": request.checker.attempt,
                "checker_evidence_digest": request.checker_evidence_digest,
                "policy_snapshot_digest": policy_evidence.digest,
            }
            admitted_seq = store.append_event(
                self.ledger,
                kind="merge.candidate-admitted",
                plan=request.plan,
                task=request.task,
                payload=payload,
                at=store.now(),
            )
            enqueued_seq = store.append_event(
                self.ledger,
                kind="merge.candidate-enqueued",
                plan=request.plan,
                task=request.task,
                payload={"generation": request.generation, "candidate_number": request.candidate_number},
                at=store.now(),
            )
            self.ledger.execute(
                "UPDATE merge_candidates SET checker_issue=?, checker_task=?, checker_attempt=?, checker_evidence_digest=?, "
                "policy_snapshot_digest=?, admitted_seq=?, enqueued_seq=? WHERE plan=? AND generation=? AND task=? AND candidate_number=?",
                (
                    request.checker.issue,
                    request.checker.task,
                    request.checker.attempt,
                    request.checker_evidence_digest,
                    policy_evidence.digest,
                    admitted_seq,
                    enqueued_seq,
                    request.plan,
                    request.generation,
                    request.task,
                    request.candidate_number,
                ),
            )
            row.update(payload, admitted_seq=admitted_seq, enqueued_seq=enqueued_seq)
        return candidate_view(row)

    def merge_next(self, request: MergeNext) -> MergeResult:
        """Persist unbound, bound, and prepared phases before one exact CAS.

        Returns:
            The terminal or reconciliation-required result.
        """
        train = train_row(self.ledger, request.plan)
        self.require_host(train)
        definition = self.fresh_definition(train)
        if int(train["generation"]) != request.generation or request.integrator.role != "integrator":
            transitions.refuse("role-assignment-mismatch")
        require_assignment(self.ledger, request.plan, request.generation, request.integrator, accepted=False)
        if self.policy_observer is None or self.branch_advancer is None or self.gates is None:
            transitions.refuse("expected-head-unsupported")
        candidate, claim_number, definition = open_claim(self, request, definition)
        prepared, _bound_policy = bind_claim(self, request, candidate, claim_number)
        final_policy = prepare_claim(self, request, candidate, claim_number, prepared, definition)
        advance = self.branch_advancer.advance(prepared)
        post_policy = observe_policy(self, candidate, require_acceptable=False)
        post_blob = self.evidence.put(post_policy.model_dump_json().encode(), "application/json")
        successful_ref = advance.outcome in {"advanced", "advanced-after-reconciliation"}
        fresh = post_policy.semantic_projection() == final_policy.semantic_projection() and policy_acceptable(
            post_policy
        )
        if successful_ref and fresh:
            return finish_claim(
                self, request.plan, candidate, claim_number, prepared, post_blob.digest, "merge.finished", "ADVANCED"
            )
        return require_reconciliation(self, request.plan, candidate, claim_number, prepared, post_blob.digest)

    def reconcile(self, request: ReconcileClaim) -> MergeResult:
        """Resolve one claim through observations only, never a second CAS.

        Returns:
            The still-unresolved or terminal reconciliation result.
        """
        claim = claim_row(self.ledger, request.plan, request.claim_number)
        train = train_row(self.ledger, request.plan)
        self.require_host(train)
        if claim["phase"] != "RECONCILIATION_REQUIRED" or not int(claim["active"]):
            if request.permanent_reason is not None and claim["conclusion"] != "PERMANENT_AMBIGUOUS":
                transitions.refuse("train-generation-stale")
            return MergeResult(
                plan=request.plan,
                claim_number=request.claim_number,
                phase=str(claim["phase"]),
                outcome=str(claim["conclusion"]),
                noop="already-reconciliation-resolved",
            )
        if self.branch_advancer is None or self.policy_observer is None:
            transitions.refuse("expected-head-unsupported")
        prepared = prepared_from_claim(claim)
        observation = self.branch_advancer.reconcile(prepared)
        candidate = candidate_row(
            self.ledger,
            request.plan,
            int(train["generation"]),
            str(claim["candidate_task"]),
            int(claim["candidate_number"]),
        )
        policy = observe_policy(self, candidate, require_acceptable=False)
        evidence = self.evidence.put(policy.model_dump_json().encode(), "application/json")
        if observation.outcome in {"advanced", "advanced-after-reconciliation"} and policy_acceptable(policy):
            return finish_claim(
                self,
                request.plan,
                candidate,
                request.claim_number,
                prepared,
                evidence.digest,
                "merge.reconciled",
                "RECONCILED",
            )
        if observation.outcome == "target-stale" and request.permanent_reason:
            return finish_claim(
                self,
                request.plan,
                candidate,
                request.claim_number,
                prepared,
                evidence.digest,
                "merge.reconciliation-resolved",
                "PERMANENT_AMBIGUOUS",
            )
        return MergeResult(
            plan=request.plan,
            claim_number=request.claim_number,
            phase="RECONCILIATION_REQUIRED",
            noop="reconciliation-still-required",
        )

    def register(self, request: RegisterTrain) -> TrainView:
        """Freeze a definition after checking it against the existing ledger plan.

        Returns:
            The registered generation.
        """
        dispatch_snapshot = self.dispatch_plans.read(request.plan_ref)
        graph_snapshot = self.source_graph.read(request.milestone)
        definition = dispatch_snapshot.definition()
        if definition.plan != request.plan or definition.milestone != request.milestone:
            transitions.refuse("dispatch-plan-disagreement")
        encoded = dispatch_snapshot.canonical_bytes
        definition_digest = dispatch_snapshot.digest
        with store.transaction(self.ledger):
            self.validate_definition(definition, graph_snapshot)
            active = store.rows_of(
                self.ledger.execute(
                    "SELECT * FROM merge_trains WHERE plan = :plan AND superseded_seq IS NULL AND invalidated_seq IS NULL",
                    {"plan": definition.plan},
                )
            )
            if active:
                row = active[0]
                self.require_host(row)
                if (
                    str(row["dispatch_plan_id"]) == dispatch_snapshot.logical_id
                    and str(row["dispatch_plan_revision"]) == dispatch_snapshot.revision
                    and str(row["dispatch_plan_digest"]) == definition_digest
                    and str(row["source_graph_revision"]) == graph_snapshot.revision
                    and str(row["source_graph_digest"]) == graph_snapshot.digest
                ):
                    return self.train_view(row, noop="already-registered")
                if (
                    str(row["source_graph_revision"]) != graph_snapshot.revision
                    or str(row["source_graph_digest"]) != graph_snapshot.digest
                ):
                    transitions.refuse("source-graph-stale")
                transitions.refuse("dispatch-plan-stale")
            if any(int(row["attempt_open"] or 0) == 1 for row in store.plan_tasks(self.ledger, definition.plan)):
                transitions.refuse("preexisting-open-attempt")
            generation = int(
                self.ledger.execute(
                    "SELECT COALESCE(MAX(generation), 0) + 1 FROM merge_trains WHERE plan = :plan",
                    {"plan": definition.plan},
                ).fetchone()[0]
            )
            members = [member.model_dump(mode="json") for member in definition.members]
            payload: dict[str, object] = {
                "generation": generation,
                "milestone": definition.milestone,
                "dispatch_plan_id": definition.logical_id,
                "dispatch_plan_revision": definition.revision,
                "dispatch_plan_digest": definition_digest,
                "source_graph_revision": graph_snapshot.revision,
                "source_graph_digest": graph_snapshot.digest,
                "member_set_digest": canonical_digest(sorted((member["issue"], member["task"]) for member in members)),
                "role_map_digest": canonical_digest(sorted((member["task"], member["role"]) for member in members)),
                "conflict_map_digest": canonical_digest(
                    sorted((member["task"], member["conflict_group"]) for member in members)
                ),
                "integration_branch": definition.integration_branch,
                "baseline_sha": definition.baseline_sha,
                "quality_gates_digest": canonical_digest(definition.quality_gates),
                "authority_host_id": self.host_authority.authority_host_id,
                "definition": json.loads(encoded),
            }
            sequence = store.append_event(
                self.ledger,
                kind="merge.train-registered",
                plan=definition.plan,
                task=None,
                payload=payload,
                at=store.now(),
            )
            row = {
                **payload,
                "plan": definition.plan,
                "registered_seq": sequence,
                "superseded_seq": None,
                "invalidated_seq": None,
                "invalidation_reason": None,
            }
            columns = [column.name for column in store.TABLES["merge_trains"]]
            self.ledger.execute(store.insert_statement("merge_trains", columns), {name: row[name] for name in columns})
        return self.train_view(row)

    def validate_definition(self, definition: DispatchPlanDefinition, graph: SourceGraphSnapshot) -> None:
        """Require exact task, issue, dependency, and conflict-resource agreement."""
        shared_definition = (
            definition.milestone,
            definition.integration_branch,
            definition.baseline_sha,
            tuple(
                sorted(
                    (member.issue, member.task, member.role, member.dependencies, member.conflict_group)
                    for member in definition.members
                )
            ),
        )
        shared_graph = (
            graph.milestone,
            graph.integration_branch,
            graph.baseline_sha,
            tuple(
                sorted(
                    (member.issue, member.task, member.role, member.dependencies, member.conflict_group)
                    for member in graph.members
                )
            ),
        )
        if shared_definition != shared_graph:
            transitions.refuse("dispatch-plan-disagreement")
        plan = store.fetch_plan(self.ledger, definition.plan)
        tasks = {str(row["id"]): row for row in store.plan_tasks(self.ledger, definition.plan)}
        members = {member.task: member for member in definition.members}
        if set(tasks) != set(members):
            transitions.refuse("dispatch-plan-disagreement")
        if plan["milestone"] is not None and int(plan["milestone"]) != definition.milestone:
            transitions.refuse("dispatch-plan-disagreement")
        if plan["integration_branch"] is not None and str(plan["integration_branch"]) != definition.integration_branch:
            transitions.refuse("dispatch-plan-disagreement")
        if plan["base_sha"] is not None and str(plan["base_sha"]) != definition.baseline_sha:
            transitions.refuse("dispatch-plan-disagreement")
        if tuple(store.json_list(plan["quality_gates"])) != definition.quality_gates:
            transitions.refuse("dispatch-plan-disagreement")
        for task_id, row in tasks.items():
            member = members[task_id]
            if int(row["github_issue"] or 0) != member.issue:
                transitions.refuse("dispatch-plan-disagreement")
            if tuple(store.json_list(row["dependencies"])) != member.dependencies:
                transitions.refuse("dispatch-plan-disagreement")
            held_group = str(row["conflict_group"]) if row["conflict_group"] is not None else None
            if held_group != member.conflict_group:
                transitions.refuse("dispatch-plan-disagreement")

    def fresh_definition(self, row: dict[str, Any]) -> DispatchPlanDefinition:
        """Re-read both authorities and require exact registered and ledger agreement.

        Returns:
            The current definition after all authority checks pass.
        """
        payload = definition_event(self.ledger, str(row["plan"]), int(row["generation"]))
        plan_ref = str(payload["dispatch_plan_id"])
        milestone = int(payload["milestone"])
        dispatch_snapshot = self.dispatch_plans.read(plan_ref)
        graph_snapshot = self.source_graph.read(milestone)
        if (
            dispatch_snapshot.revision != row["dispatch_plan_revision"]
            or dispatch_snapshot.digest != row["dispatch_plan_digest"]
        ):
            transitions.refuse("dispatch-plan-stale")
        if (
            graph_snapshot.revision != row["source_graph_revision"]
            or graph_snapshot.digest != row["source_graph_digest"]
        ):
            transitions.refuse("source-graph-stale")
        definition = dispatch_snapshot.definition()
        self.validate_definition(definition, graph_snapshot)
        return definition

    def dispatch(self, request: DispatchReserved) -> DispatchView:
        """Atomically open an attempt and reserve its frozen conflict group.

        Returns:
            The frozen assignment tuple and opened attempt.
        """
        train = train_row(self.ledger, request.plan)
        definition = self.fresh_definition(train)
        member = next((item for item in definition.members if item.task == request.task), None)
        if member is None:
            transitions.refuse("role-assignment-mismatch")
        result = dispatch_registered(
            self.ledger,
            request.plan,
            request.task,
            generation=request.generation,
            authority_host_id=self.host_authority.authority_host_id,
            dispatch_plan_digest=str(train["dispatch_plan_digest"]),
            source_graph_revision=str(train["source_graph_revision"]),
            source_graph_digest=str(train["source_graph_digest"]),
            role=member.role,
            github_issue=member.issue,
            dependencies=member.dependencies,
            conflict_group=member.conflict_group,
            ttl_seconds=request.ttl_seconds,
            worktree=request.worktree,
        )
        return DispatchView(
            plan=request.plan,
            generation=request.generation,
            task=request.task,
            attempt=int(result.attempt or 0),
            role=member.role,
            github_issue=member.issue,
            conflict_group=member.conflict_group,
            noop=result.noop,
        )

    def status(self, query: MergeQuery) -> MergePage:
        """Return one generation and all of its reservation history."""
        row = train_row(self.ledger, query.plan, query.generation)
        reservations = store.rows_of(
            self.ledger.execute(
                "SELECT plan, generation, conflict_group, task, attempt, role, github_issue, active, conclusion "
                "FROM merge_reservations WHERE plan = :plan AND generation = :generation "
                "ORDER BY reserved_seq",
                {"plan": query.plan, "generation": row["generation"]},
            )
        )
        candidates = store.rows_of(
            self.ledger.execute(
                "SELECT * FROM merge_candidates WHERE plan=? AND generation=? ORDER BY task, candidate_number",
                (query.plan, row["generation"]),
            )
        )
        claims = store.rows_of(
            self.ledger.execute("SELECT * FROM merge_claims WHERE plan=? ORDER BY claim_number", (query.plan,))
        )
        return MergePage(
            train=self.train_view(row),
            reservations=[ReservationView.model_validate(item) for item in reservations],
            candidates=[candidate_view(item) for item in candidates],
            claims=[
                MergeResult(
                    plan=query.plan,
                    claim_number=int(item["claim_number"]),
                    phase=str(item["phase"]),
                    outcome=str(item["conclusion"]) if item["conclusion"] is not None else None,
                    result_sha=str(item["result_sha"]) if item["result_sha"] is not None else None,
                )
                for item in claims
            ],
        )

    def explain(self, query: ExplainQuery) -> Explanation:
        """Derive stable blockers solely from stored state.

        Returns:
            Ordered blocker codes.
        """
        page = self.status(query)
        blockers: list[str] = []
        if any(claim.phase == "RECONCILIATION_REQUIRED" and claim.outcome is None for claim in page.claims):
            blockers.append("reconciliation-required")
        if not any(candidate.admitted_seq is not None and candidate.outcome is None for candidate in page.candidates):
            blockers.append("no-admitted-candidate")
        return Explanation(plan=query.plan, generation=page.train.generation, blockers=blockers)

    def history(self, query: HistoryQuery) -> HistoryPage:
        """Return complete matching event envelopes without implicit truncation."""
        events = [
            event for event in store.events_of(self.ledger, query.plan) if str(event["kind"]).startswith("merge.")
        ]
        if query.event_kind is not None:
            events = [event for event in events if event["kind"] == query.event_kind]
        if query.generation is not None:
            events = [
                event
                for event in events
                if isinstance(event["payload"], dict) and event["payload"].get("generation") == query.generation
            ]
        total = len(events)
        selected = events[query.offset :] if query.limit is None else events[query.offset : query.offset + query.limit]
        return HistoryPage(offset=query.offset, limit=query.limit, returned=len(selected), total=total, events=selected)

    def validate(self, query: MergeQuery) -> ValidationResult:
        """Check materialized registration and reservations against immutable events.

        Returns:
            Stable structural findings.
        """
        findings: list[str] = []
        try:
            findings.extend(self.projection_findings())
            page = self.status(query)
            train = train_row(self.ledger, query.plan, query.generation)
            findings.extend(self.registration_findings(page.train))
            if query.generation is not None:
                return ValidationResult(valid=not findings, findings=findings)
            self.fresh_definition(train)
            findings.extend(self.reservation_findings(page))
        except (KeyError, LookupError, ValueError, store.Refusal):
            findings.append("merge-event-stream-invalid")
        return ValidationResult(valid=not findings, findings=findings)

    def projection_findings(self) -> list[str]:
        """Compare merge projections with their event fold.

        Returns:
            Stable projection-drift findings.
        """
        folded = store.fold_events(store.all_events(self.ledger))
        findings: list[str] = []
        queries = {
            "merge_trains": "SELECT * FROM merge_trains ORDER BY plan, generation",
            "merge_dispatches": "SELECT * FROM merge_dispatches ORDER BY plan, generation, task, attempt",
            "merge_reservations": (
                "SELECT * FROM merge_reservations ORDER BY plan, generation, conflict_group, task, attempt"
            ),
            "merge_candidates": "SELECT * FROM merge_candidates ORDER BY plan, generation, task, candidate_number",
            "merge_claims": "SELECT * FROM merge_claims ORDER BY plan, claim_number",
        }
        for table, query in queries.items():
            current = store.rows_of(self.ledger.execute(query))
            if current != folded[table]:
                findings.append(f"{table}-projection-drift")
        return findings

    def registration_findings(self, train: TrainView) -> list[str]:
        """Validate one generation solely from immutable registration evidence.

        Returns:
            Stable immutable-integrity findings.
        """
        payload = definition_event(self.ledger, train.plan, train.generation)
        definition = DispatchPlanDefinition.model_validate_json(json.dumps(payload["definition"]))
        findings = (
            []
            if digest(definition.canonical_bytes()) == train.dispatch_plan_digest
            else ["dispatch-plan-digest-mismatch"]
        )
        registrations = [
            event
            for event in store.events_of(self.ledger, train.plan, kind="merge.train-registered")
            if isinstance(event["payload"], dict) and int(event["payload"].get("generation", 0)) == train.generation
        ]
        if len(registrations) != 1 or int(registrations[0]["seq"]) != train.registered_seq:
            findings.append("registration-event-mismatch")
        members = [member.model_dump(mode="json") for member in definition.members]
        retained = {
            "member_set_digest": canonical_digest(sorted((member["issue"], member["task"]) for member in members)),
            "role_map_digest": canonical_digest(sorted((member["task"], member["role"]) for member in members)),
            "conflict_map_digest": canonical_digest(
                sorted((member["task"], member["conflict_group"]) for member in members)
            ),
            "quality_gates_digest": canonical_digest(definition.quality_gates),
        }
        if any(str(payload[name]) != expected for name, expected in retained.items()):
            findings.append("registration-definition-mismatch")
        return findings

    @staticmethod
    def reservation_retained(task: dict[str, Any]) -> bool:
        """Report whether task lifecycle state retains an acquired reservation.

        Returns:
            True for open, returned, and complete-unaccepted judge intervals.
        """
        return (
            str(task["status"]) == store.IN_PROGRESS
            and (int(task["attempt_open"] or 0) == 1 or int(task["settled"] or 0) == 1)
        ) or (str(task["status"]) == store.COMPLETE and int(task["accepted"] or 0) == 0)

    def reservation_findings(self, page: MergePage) -> list[str]:
        """Validate active reservations and their grouped-binding converse.

        Returns:
            Stable orphan and missing-reservation findings.
        """
        findings: list[str] = []
        tasks = {str(task["id"]): task for task in store.plan_tasks(self.ledger, page.train.plan)}
        dispatches = store.rows_of(
            self.ledger.execute(
                "SELECT * FROM merge_dispatches WHERE plan = :plan AND generation = :generation",
                {"plan": page.train.plan, "generation": page.train.generation},
            )
        )
        for reservation in (item for item in page.reservations if item.active):
            task = tasks.get(reservation.task)
            binding = next(
                (
                    row
                    for row in dispatches
                    if row["task"] == reservation.task
                    and int(row["attempt"]) == reservation.attempt
                    and row["role"] == reservation.role
                    and int(row["github_issue"]) == reservation.github_issue
                    and row["conflict_group"] == reservation.conflict_group
                ),
                None,
            )
            if (
                task is None
                or binding is None
                or reservation.attempt != int(task["attempts"])
                or not self.reservation_retained(task)
            ):
                findings.append("reservation-orphaned")
        for dispatch in dispatches:
            task = tasks.get(str(dispatch["task"]))
            if task is None:
                findings.append("dispatch-binding-orphaned")
                continue
            current = int(task["attempts"] or 0) == int(dispatch["attempt"])
            if current and self.reservation_retained(task) and dispatch["conflict_group"] is not None:
                exact = any(
                    item.active
                    and item.task == dispatch["task"]
                    and item.attempt == int(dispatch["attempt"])
                    and item.conflict_group == dispatch["conflict_group"]
                    for item in page.reservations
                )
                if not exact:
                    findings.append("reservation-missing")
        return findings

    def require_host(self, row: dict[str, object]) -> None:
        """Refuse a local marker mismatch without claiming host authentication."""
        if str(row["authority_host_id"]) != self.host_authority.authority_host_id:
            transitions.refuse("wrong-authority-host")

    def train_view(self, row: dict[str, Any], *, noop: str | None = None) -> TrainView:
        """Convert a materialized row to the public train view.

        Returns:
            The typed public view.
        """
        replacement_source = None
        replacement_revision = None
        if row["invalidated_seq"] is not None:
            terminal = next(
                (
                    event["payload"]
                    for event in store.events_of(self.ledger, str(row["plan"]), kind="merge.train-invalidated")
                    if int(event["seq"]) == int(row["invalidated_seq"])
                ),
                {},
            )
            replacement_source = terminal.get("replacement_source")
            replacement_revision = terminal.get("replacement_revision")
        return TrainView(
            plan=str(row["plan"]),
            generation=int(row["generation"]),
            dispatch_plan_id=str(row["dispatch_plan_id"]),
            dispatch_plan_revision=str(row["dispatch_plan_revision"]),
            dispatch_plan_digest=str(row["dispatch_plan_digest"]),
            source_graph_revision=str(row["source_graph_revision"]),
            source_graph_digest=str(row["source_graph_digest"]),
            authority_host_id=str(row["authority_host_id"]),
            registered_seq=int(row["registered_seq"]),
            superseded_seq=int(row["superseded_seq"]) if row["superseded_seq"] is not None else None,
            invalidated_seq=int(row["invalidated_seq"]) if row["invalidated_seq"] is not None else None,
            invalidation_reason=str(row["invalidation_reason"]) if row["invalidation_reason"] is not None else None,
            replacement_source=str(replacement_source) if replacement_source is not None else None,
            replacement_revision=str(replacement_revision) if replacement_revision is not None else None,
            noop=noop,
        )
