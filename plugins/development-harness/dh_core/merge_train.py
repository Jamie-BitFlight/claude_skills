"""Registered merge-train service for immutable plans and reserved dispatch."""

from __future__ import annotations

import hashlib
import json
import operator
import sqlite3
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from dh_core.ledger import store, transitions
from dh_core.ledger.transitions import _dispatch_registered as dispatch_registered


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


class MergeTrain:
    """Service owning T1 authoritative registration and reserved dispatch."""

    def __init__(
        self,
        ledger: sqlite3.Connection,
        dispatch_plans: DispatchPlanReader,
        source_graph: SourceGraphReader,
        host_authority: HostAuthority,
    ) -> None:
        """Bind the service to one existing ledger and configured host marker."""
        self.ledger = ledger
        self.dispatch_plans: Any = dispatch_plans
        self.source_graph: Any = source_graph
        self.host_authority = host_authority

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
            if any(int(row["attempt_open"] or 0) == 1 for row in store.plan_tasks(self.ledger, definition.plan)):
                transitions.refuse("preexisting-open-attempt")
            active = store.rows_of(
                self.ledger.execute(
                    "SELECT * FROM merge_trains WHERE plan = :plan AND superseded_seq IS NULL AND invalidated_seq IS NULL",
                    {"plan": definition.plan},
                )
            )
            if active:
                row = active[0]
                if (
                    str(row["dispatch_plan_revision"]) == dispatch_snapshot.revision
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
        return MergePage(
            train=self.train_view(row), reservations=[ReservationView.model_validate(item) for item in reservations]
        )

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
            folded = store.fold_events(store.all_events(self.ledger))
            projection_queries = {
                "merge_trains": "SELECT * FROM merge_trains ORDER BY plan, generation",
                "merge_dispatches": "SELECT * FROM merge_dispatches ORDER BY plan, generation, task, attempt",
                "merge_reservations": (
                    "SELECT * FROM merge_reservations ORDER BY plan, generation, conflict_group, task, attempt"
                ),
            }
            for table, statement in projection_queries.items():
                current = store.rows_of(self.ledger.execute(statement))
                if current != folded[table]:
                    findings.append(f"{table}-projection-drift")
            page = self.status(query)
            train = train_row(self.ledger, query.plan, query.generation)
            self.fresh_definition(train)
            payload = definition_event(self.ledger, query.plan, page.train.generation)
            encoded = json.dumps(payload["definition"], sort_keys=True, separators=(",", ":")).encode()
            if digest(encoded) != page.train.dispatch_plan_digest:
                findings.append("dispatch-plan-digest-mismatch")
            for reservation in page.reservations:
                task = store.fetch_task(self.ledger, reservation.plan, reservation.task)
                if reservation.attempt > int(task["attempts"]):
                    findings.append("reservation-attempt-invalid")
                if reservation.active and int(task["attempt_open"]) != 1:
                    findings.append("reservation-orphaned")
            for task in store.plan_tasks(self.ledger, query.plan):
                if int(task["attempt_open"] or 0) != 1:
                    continue
                count = self.ledger.execute(
                    "SELECT COUNT(*) FROM merge_dispatches WHERE plan = :plan AND generation = :generation "
                    "AND task = :task AND attempt = :attempt",
                    {
                        "plan": query.plan,
                        "generation": page.train.generation,
                        "task": task["id"],
                        "attempt": task["attempts"],
                    },
                ).fetchone()[0]
                if count != 1:
                    findings.append("dispatch-binding-missing")
        except (KeyError, LookupError, ValueError, store.Refusal):
            findings.append("merge-event-stream-invalid")
        return ValidationResult(valid=not findings, findings=findings)

    def require_host(self, row: dict[str, object]) -> None:
        """Refuse a local marker mismatch without claiming host authentication."""
        if str(row["authority_host_id"]) != self.host_authority.authority_host_id:
            transitions.refuse("wrong-authority-host")

    @staticmethod
    def train_view(row: dict[str, Any], *, noop: str | None = None) -> TrainView:
        """Convert a materialized row to the public train view.

        Returns:
            The typed public view.
        """
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
            noop=noop,
        )
