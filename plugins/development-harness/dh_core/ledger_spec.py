"""Executable specification of the DH work ledger.

The ledger is one SQLite database per repository holding every SAM plan and task, an
append-only ``events`` table, and tables materialised from it. This module is the single
definition of that state machine: the tables and their columns, the event kinds, the commands
and their flags, the reason codes, and every transition a command can make, as data.

``tests_sam/test_ledger_spec.py`` proves the specification closed: every column is set by an
event or derived by a named rule, every event kind is emitted by a transition, every reason code
is owned by one definition and used by one or more transitions, every task status is handled by
every task command, and the statuses equal ``sam_schema.core.models.TaskStatus``.

``dh_core/ledger.py`` (Slice 2 of ``docs/work-ledger/plan.md``) implements this module and is
tested against it. Until it exists, this module is the design; after it exists, this module is
the contract the conformance tests drive it through.

The runner key is the attempt number. ``dispatch`` increments ``attempts`` and prints it; the
runner passes ``--address P/T --attempt N`` on every command; a command from a superseded attempt
is refused with ``stale-attempt``. No session id or agent id appears anywhere in this module.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Statuses
# ---------------------------------------------------------------------------


class Status(StrEnum):
    """Task statuses; the closure test asserts these equal ``TaskStatus``."""

    NOT_STARTED = "not-started"
    IN_PROGRESS = "in-progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    DEFERRED = "deferred"
    SKIPPED = "skipped"
    FAILED = "failed"


ANY = "*"
"""Wildcard ``from_status`` for a transition that applies in every status."""

SUCCESSFUL_DEPENDENCY = frozenset({Status.DEFERRED, Status.SKIPPED})
"""A dependency counts as satisfied when it is accepted, or in one of these statuses."""

BATCH_TERMINAL = frozenset({Status.COMPLETE, Status.FAILED, Status.BLOCKED, Status.DEFERRED, Status.SKIPPED})
"""Statuses in which a task needs no runner; ``in-progress`` is batch-terminal only when returned."""


# ---------------------------------------------------------------------------
# Tables and columns
# ---------------------------------------------------------------------------


class Provenance(StrEnum):
    """How a materialised column gets its value."""

    EVENT = "event"
    """Set inside the transaction that appends one of the events named in ``set_by``."""

    DERIVED = "derived"
    """Computed at read time by the rule in ``rule``; never stored."""

    SOURCE = "source"
    """Copied from the ``Plan`` or ``Task`` model at ``plan.created`` / ``task.added`` and changed by ``*.fields``."""


class Column(BaseModel):
    """One column of a materialised table."""

    table: str
    name: str
    type: str
    provenance: Provenance
    set_by: list[str] = Field(default_factory=list)
    """Event kinds whose fold sets this column; empty for ``DERIVED``."""
    rule: str = ""
    """For ``DERIVED``: the rule in one sentence."""


def _cols(table: str, provenance: Provenance, set_by: list[str], **names: str) -> list[Column]:
    return [Column(table=table, name=n, type=t, provenance=provenance, set_by=set_by) for n, t in names.items()]


PLAN_MODEL_FIELDS: tuple[str, ...] = (
    "plan_id",
    "feature",
    "version",
    "description",
    "state",
    "goal",
    "context",
    "acceptance_criteria",
    "acceptance_criteria_structured",
    "issue",
    "architecture",
    "feature_context",
    "codebase_patterns",
    "backend_ref",
    "autonomy",
)
"""``Plan`` fields the ledger stores as columns of ``plans`` (``tasks`` and ``source_*`` excluded)."""

TASK_MODEL_FIELDS: tuple[str, ...] = (
    "id",
    "title",
    "status",
    "agent",
    "dependencies",
    "priority",
    "complexity",
    "skills",
    "blocked_by",
    "parallelize_with",
    "created",
    "started",
    "completed",
    "last_activity",
    "issue_classification",
    "scenario_target",
    "analysis_method",
    "divergence_notes",
    "accuracy_risk",
    "reason",
    "body",
    "description",
    "objective",
    "requirements",
    "constraints",
    "expected_outputs",
    "acceptance_criteria",
    "verification_steps",
    "context_notes",
    "handoff",
    "is_bookend",
    "bookend_type",
    "github_issue",
)
"""``Task`` fields the ledger stores as columns of ``tasks``. ``context_notes`` holds no sections;
sections live in the ``sections`` table and the projection renders them back into it."""

COLUMNS: list[Column] = [
    # plans
    *[
        Column(
            table="plans",
            name=f,
            type="model",
            provenance=Provenance.SOURCE,
            set_by=["plan.created", "plan.fields", "plan.replaced"],
        )
        for f in PLAN_MODEL_FIELDS
    ],
    *_cols(
        "plans",
        Provenance.EVENT,
        ["plan.created", "plan.replaced"],
        milestone="int|null",
        integration_branch="text|null",
        base_sha="text|null",
    ),
    *_cols("plans", Provenance.EVENT, ["plan.created", "plan.fields", "plan.replaced"], quality_gates="json"),
    *_cols("plans", Provenance.EVENT, ["plan.archived"], archived="datetime|null"),
    Column(
        table="plans",
        name="progress",
        type="text",
        provenance=Provenance.DERIVED,
        rule=(
            "archived when plans.archived is set; else failed when no task is not-started, in-progress, blocked, or complete-unaccepted "
            "and at least one is failed; else done when every task is accepted, deferred or skipped; else open"
        ),
    ),
    # tasks: model fields
    *[
        Column(
            table="tasks",
            name=f,
            type="model",
            provenance=Provenance.SOURCE,
            set_by=["task.added", "task.fields", "task.imported"],
        )
        for f in TASK_MODEL_FIELDS
        if f not in {"status", "started", "completed", "last_activity"}
    ],
    Column(
        table="tasks",
        name="status",
        type="text",
        provenance=Provenance.EVENT,
        set_by=["task.added", "task.imported", "task.dispatched", "task.finished", "task.state", "task.reclaimed"],
    ),
    Column(
        table="tasks",
        name="started",
        type="datetime|null",
        provenance=Provenance.EVENT,
        set_by=["task.dispatched", "task.imported"],
    ),
    Column(
        table="tasks",
        name="completed",
        type="datetime|null",
        provenance=Provenance.EVENT,
        set_by=["task.finished", "task.state", "task.dispatched", "task.reclaimed", "task.imported"],
    ),
    Column(
        table="tasks",
        name="last_activity",
        type="datetime|null",
        provenance=Provenance.EVENT,
        set_by=["lease.renewed", "task.dispatched", "task.imported"],
    ),
    # tasks: ledger columns
    *_cols("tasks", Provenance.EVENT, ["task.added", "task.imported"], plan="text", conflict_group="text|null"),
    *_cols("tasks", Provenance.EVENT, ["task.dispatched", "task.imported", "task.added"], attempts="int"),
    *_cols("tasks", Provenance.EVENT, ["task.reclaimed", "task.imported", "task.added"], attempts_allowed="int"),
    *_cols(
        "tasks",
        Provenance.EVENT,
        ["task.accepted", "task.reclaimed", "task.state", "task.imported", "task.added"],
        accepted="int",
    ),
    *_cols(
        "tasks",
        Provenance.EVENT,
        [
            "task.dispatched",
            "task.finished",
            "task.settled",
            "task.reclaimed",
            "task.state",
            "task.imported",
            "task.added",
            "plan.archived",
        ],
        attempt_open="int",
    ),
    *_cols(
        "tasks",
        Provenance.EVENT,
        ["task.dispatched", "task.imported", "task.added"],
        ttl_seconds="int|null",
        worktree="text|null",
    ),
    *_cols(
        "tasks",
        Provenance.EVENT,
        ["task.dispatched", "lease.renewed", "task.imported", "task.added"],
        expires="datetime|null",
    ),
    *_cols(
        "tasks",
        Provenance.EVENT,
        ["task.dispatched", "lease.renewed", "task.imported", "task.added"],
        first_renewed="datetime|null",
    ),
    *_cols(
        "tasks",
        Provenance.EVENT,
        ["task.finished", "task.dispatched", "task.reclaimed", "task.imported", "task.added"],
        result="text|null",
        note="text|null",
    ),
    *_cols(
        "tasks",
        Provenance.EVENT,
        ["task.settled", "task.dispatched", "task.reclaimed", "task.imported", "task.added"],
        settled="int",
        return_text="text|null",
    ),
    *_cols("tasks", Provenance.EVENT, ["task.reclaimed", "task.imported", "task.added"], response="text|null"),
    Column(
        table="tasks",
        name="ready",
        type="bool",
        provenance=Provenance.DERIVED,
        rule=(
            "status is not-started, and every id in dependencies names a task that is accepted or in SUCCESSFUL_DEPENDENCY, "
            "and no other task with the same non-null conflict_group is in-progress or complete-unaccepted"
        ),
    ),
    Column(
        table="tasks",
        name="expired",
        type="bool",
        provenance=Provenance.DERIVED,
        rule="attempt_open is 1 and now is past expires",
    ),
    Column(
        table="tasks",
        name="stale",
        type="bool",
        provenance=Provenance.DERIVED,
        rule="attempt_open is 1 and now is past expires plus ttl_seconds",
    ),
    Column(
        table="tasks",
        name="returned",
        type="bool",
        provenance=Provenance.DERIVED,
        rule="status is in-progress and settled is 1",
    ),
    Column(
        table="tasks",
        name="renew_by",
        type="datetime|null",
        provenance=Provenance.DERIVED,
        rule="expires when attempt_open is 1, else null",
    ),
    # sections
    *_cols(
        "sections",
        Provenance.EVENT,
        ["task.section", "task.imported"],
        plan="text",
        task="text",
        name="text",
        attempt="int",
        content="text",
        seq="int",
    ),
    # export_cursors
    *_cols(
        "export_cursors",
        Provenance.EVENT,
        ["plan.exported", "plan.imported"],
        plan="text",
        target="text",
        last_seq="int",
        revision="text|null",
        projection_hash="text|null",
    ),
]

REPORT_SECTIONS: tuple[str, ...] = ("Completion Report", "Verification Results")
"""The two sections the report check requires, each tagged with the current attempt."""

RESPONSE_SECTION = "Orchestrator Response"
"""Rendered by ``read`` from ``tasks.response`` at the top of the current attempt; not a stored section."""


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class EventKind(BaseModel):
    """One kind of row in ``events``."""

    kind: str
    payload: list[str]
    written_by: list[str]
    """Commands that append this kind."""


EVENTS: list[EventKind] = [
    EventKind(
        kind="plan.created",
        payload=[*PLAN_MODEL_FIELDS, "milestone", "integration_branch", "base_sha", "quality_gates"],
        written_by=["create", "from-milestone", "import"],
    ),
    EventKind(kind="plan.replaced", payload=["source", "revision"], written_by=["import", "from-milestone"]),
    EventKind(kind="plan.fields", payload=["changed"], written_by=["update", "finalize"]),
    EventKind(kind="plan.archived", payload=["reason"], written_by=["archive"]),
    EventKind(kind="plan.imported", payload=["source", "revision", "projection_hash"], written_by=["import"]),
    EventKind(
        kind="plan.exported",
        payload=["target", "last_seq", "revision", "projection_hash", "divergences"],
        written_by=["export"],
    ),
    EventKind(
        kind="task.added",
        payload=[*TASK_MODEL_FIELDS, "conflict_group"],
        written_by=["create", "append-task", "from-milestone"],
    ),
    EventKind(
        kind="task.imported",
        payload=[
            *TASK_MODEL_FIELDS,
            "conflict_group",
            "attempts",
            "attempts_allowed",
            "accepted",
            "sections",
            "source",
        ],
        written_by=["import"],
    ),
    EventKind(kind="task.fields", payload=["changed"], written_by=["update"]),
    EventKind(kind="task.section", payload=["name", "attempt", "content"], written_by=["update"]),
    EventKind(kind="task.dispatched", payload=["attempt", "ttl_seconds", "worktree"], written_by=["dispatch"]),
    EventKind(kind="lease.renewed", payload=["attempt", "via"], written_by=["read", "update", "renew"]),
    EventKind(kind="task.finished", payload=["attempt", "result", "note"], written_by=["finish"]),
    EventKind(kind="task.settled", payload=["attempt", "return_text", "via"], written_by=["settle"]),
    EventKind(kind="task.accepted", payload=["note"], written_by=["accept"]),
    EventKind(
        kind="task.reclaimed", payload=["from_status", "reason", "response", "attempts_allowed"], written_by=["reclaim"]
    ),
    EventKind(kind="task.state", payload=["status", "reason"], written_by=["state", "finish", "reclaim", "accept"]),
]


# ---------------------------------------------------------------------------
# Reason codes
# ---------------------------------------------------------------------------


class ReasonKind(StrEnum):
    """What printing a reason code means for exit status and the event log."""

    REFUSAL = "refusal"
    """Exit non-zero, the code on stderr, no event appended."""

    NOOP = "noop"
    """Exit zero, the code on stdout, no event appended."""

    OUTCOME = "outcome"
    """Exit zero, the code recorded as the ``reason`` of a ``task.state`` event."""


class Reason(BaseModel):
    """One reason code a command prints, with the condition that produces it."""

    code: str
    kind: ReasonKind
    condition: str


REASONS: list[Reason] = [
    Reason(
        code="network-filesystem",
        kind=ReasonKind.REFUSAL,
        condition="the mount holding the database path has a type in NETWORK_FILESYSTEMS",
    ),
    Reason(code="archived", kind=ReasonKind.REFUSAL, condition="plans.archived is set"),
    Reason(
        code="leased",
        kind=ReasonKind.REFUSAL,
        condition="attempt_open is 1 and the command's exception (returned, stale, --force) does not hold",
    ),
    Reason(code="not-ready", kind=ReasonKind.REFUSAL, condition="tasks.ready is false"),
    Reason(
        code="stale-attempt",
        kind=ReasonKind.REFUSAL,
        condition="--attempt differs from tasks.attempts, or attempt_open is 0",
    ),
    Reason(
        code="attempt-required",
        kind=ReasonKind.REFUSAL,
        condition="--append-section names a report section and --attempt is absent",
    ),
    Reason(
        code="unmatched-path",
        kind=ReasonKind.REFUSAL,
        condition="no task with attempt_open 1 has a worktree that contains --path",
    ),
    Reason(
        code="report-missing",
        kind=ReasonKind.REFUSAL,
        condition="a section in REPORT_SECTIONS has no row tagged with the current attempt",
    ),
    Reason(
        code="not-complete",
        kind=ReasonKind.REFUSAL,
        condition="status is not complete-with-attempt-closed and the task is not returned",
    ),
    Reason(code="task-accepted", kind=ReasonKind.REFUSAL, condition="accepted is 1 and --force is absent"),
    Reason(
        code="dependents-started",
        kind=ReasonKind.REFUSAL,
        condition="a task naming this one in dependencies has attempts above 0, is not skipped by this task's cascade, and --force is absent",
    ),
    Reason(
        code="attempts-exhausted",
        kind=ReasonKind.REFUSAL,
        condition="attempts is at or above attempts_allowed and --more-attempts is absent",
    ),
    Reason(
        code="status-invalid",
        kind=ReasonKind.REFUSAL,
        condition="--new-status is not one of complete, failed, blocked, deferred, skipped",
    ),
    Reason(
        code="exists",
        kind=ReasonKind.REFUSAL,
        condition="a plan with this id, or an unarchived plan with this milestone, exists and --replace is absent",
    ),
    Reason(code="already-settled", kind=ReasonKind.NOOP, condition="settled is 1 for the named attempt"),
    Reason(code="already-accepted", kind=ReasonKind.NOOP, condition="accepted is 1"),
    Reason(code="already-open", kind=ReasonKind.NOOP, condition="status is not-started"),
    Reason(
        code="unchanged",
        kind=ReasonKind.NOOP,
        condition="the projection hash equals export_cursors.projection_hash for the target",
    ),
    Reason(
        code="cascade:T{n}",
        kind=ReasonKind.OUTCOME,
        condition="the task became failed and this not-started transitive dependent moved to skipped",
    ),
    Reason(
        code="cascade-reversed:T{n}",
        kind=ReasonKind.OUTCOME,
        condition="the task left failed and this dependent, still skipped with cascade:T{n}, moved to not-started",
    ),
    Reason(
        code="returned-complete",
        kind=ReasonKind.OUTCOME,
        condition="accept moved a returned task to complete before accepting it",
    ),
]

NETWORK_FILESYSTEMS: tuple[str, ...] = ("nfs", "nfs4", "cifs", "smb2", "fuse.sshfs", "9p")
"""Mount types on which WAL mode cannot share memory; open refuses with ``network-filesystem``."""


# ---------------------------------------------------------------------------
# Commands and flags
# ---------------------------------------------------------------------------


class Flag(BaseModel):
    """One command-line flag of a ``sam plan`` command."""

    name: str
    required: bool = False
    value: str = ""
    """Value description; empty for a boolean flag."""


class Scope(StrEnum):
    """Whether a command acts on one task or on a plan."""

    TASK = "task"
    PLAN = "plan"


class Command(BaseModel):
    """One ``sam plan`` command; ``sam_task``/``sam_plan`` MCP actions map one to one."""

    name: str
    scope: Scope
    flags: list[Flag]
    renews: bool = False
    """Renews the current attempt's lease when ``--attempt`` is supplied and valid."""
    key: str = ""
    """How the command identifies the attempt it acts on: ``attempt``, ``path``, ``attempt|path`` or empty."""
    summary: str


ADDRESS = Flag(name="--address", required=True, value="P/T")
PLAN_ADDRESS = Flag(name="--plan-address", required=True, value="P")
ATTEMPT = Flag(name="--attempt", value="N, printed by dispatch")
PATH = Flag(name="--path", value="a file or directory inside a dispatched worktree")
NOTE = Flag(name="--note", value="free text stored on the row")
FORCE = Flag(name="--force")

COMMANDS: list[Command] = [
    Command(
        name="create",
        scope=Scope.PLAN,
        flags=[
            Flag(name="--slug", required=True, value="slug"),
            Flag(name="--goal", required=True, value="text"),
            Flag(name="--owner-reference", value="work item"),
            Flag(name="--quality-gate", value="command, repeatable"),
        ],
        summary="plan.created; tasks may follow with append-task",
    ),
    Command(
        name="append-task",
        scope=Scope.PLAN,
        flags=[
            PLAN_ADDRESS,
            Flag(name="--task-id", required=True, value="T"),
            Flag(name="--task-title", required=True, value="text"),
            Flag(name="--conflict-group", value="name"),
        ],
        summary="task.added on a drafting plan",
    ),
    Command(name="finalize", scope=Scope.PLAN, flags=[PLAN_ADDRESS], summary="plan.fields: state ready"),
    Command(name="validate", scope=Scope.PLAN, flags=[PLAN_ADDRESS], summary="reads; prints structural findings"),
    Command(name="list", scope=Scope.PLAN, flags=[], summary="reads every plan row"),
    Command(
        name="status",
        scope=Scope.PLAN,
        flags=[PLAN_ADDRESS],
        summary="reads every task row with derived columns and plan progress",
    ),
    Command(name="ready", scope=Scope.PLAN, flags=[PLAN_ADDRESS], summary="reads tasks whose ready is true"),
    Command(
        name="archive",
        scope=Scope.PLAN,
        flags=[PLAN_ADDRESS, Flag(name="--reason", required=True, value="text")],
        summary="plan.archived; closes every open attempt",
    ),
    Command(
        name="from-milestone",
        scope=Scope.PLAN,
        flags=[
            Flag(name="--milestone-number", required=True, value="N"),
            Flag(name="--integration-branch", required=True, value="branch"),
            Flag(name="--quality-gate", value="command, repeatable"),
            Flag(name="--replace"),
            Flag(name="--dry-run"),
        ],
        summary="plan.created and task.added from the milestone's items; base_sha is the branch head",
    ),
    Command(
        name="import",
        scope=Scope.PLAN,
        flags=[
            Flag(name="--from", value="content|legacy|dispatch"),
            Flag(name="--all"),
            Flag(name="--plan-address", value="P"),
            Flag(name="--replace"),
        ],
        summary="plan.created or plan.replaced, task.imported, plan.imported",
    ),
    Command(
        name="export",
        scope=Scope.PLAN,
        flags=[PLAN_ADDRESS, Flag(name="--to", value="content")],
        summary="plan.exported, or unchanged",
    ),
    Command(
        name="update",
        scope=Scope.TASK,
        flags=[
            PLAN_ADDRESS,
            Flag(name="--task-id", value="T"),
            ATTEMPT,
            Flag(name="--append-section", value="name"),
            Flag(name="--set", value="field=value, repeatable"),
        ],
        renews=True,
        key="attempt",
        summary="task.fields, plan.fields, task.section",
    ),
    Command(
        name="read",
        scope=Scope.TASK,
        flags=[ADDRESS, ATTEMPT],
        renews=True,
        key="attempt",
        summary="reads one task with its current-attempt sections and response",
    ),
    Command(
        name="dispatch",
        scope=Scope.TASK,
        flags=[ADDRESS, Flag(name="--ttl", value="seconds"), Flag(name="--worktree", value="path")],
        summary="task.dispatched; prints the attempt number",
    ),
    Command(
        name="renew",
        scope=Scope.TASK,
        flags=[Flag(name="--address", value="P/T"), ATTEMPT, PATH],
        renews=True,
        key="attempt|path",
        summary="lease.renewed",
    ),
    Command(
        name="finish",
        scope=Scope.TASK,
        flags=[
            ADDRESS,
            Flag(name="--attempt", required=True, value="N"),
            Flag(name="--result", required=True, value="complete|failed|blocked|needs-input"),
            NOTE,
        ],
        key="attempt",
        summary="task.finished; the runner's last command",
    ),
    Command(
        name="settle",
        scope=Scope.TASK,
        flags=[
            Flag(name="--address", value="P/T"),
            ATTEMPT,
            PATH,
            Flag(name="--return-text", value="what the harness call returned"),
        ],
        key="attempt|path",
        summary="task.settled",
    ),
    Command(name="accept", scope=Scope.TASK, flags=[ADDRESS, NOTE, FORCE], summary="task.accepted"),
    Command(
        name="reclaim",
        scope=Scope.TASK,
        flags=[
            ADDRESS,
            Flag(name="--reason", required=True, value="text"),
            Flag(name="--response", value="text the next runner reads first"),
            FORCE,
            Flag(name="--more-attempts"),
        ],
        summary="task.reclaimed; the send-back",
    ),
    Command(
        name="state",
        scope=Scope.TASK,
        flags=[
            ADDRESS,
            Flag(name="--new-status", required=True, value="complete|failed|blocked|deferred|skipped"),
            Flag(name="--reason", required=True, value="text"),
            FORCE,
        ],
        summary="task.state; the orchestrator's decision without a runner",
    ),
]

RETIRED_COMMANDS: tuple[str, ...] = (
    "claim",
    "sam-task-create",
    "sam-tasks",
    "sam-task-status",
    "sam-ready-tasks",
    "migrate",
)
"""``sam plan`` commands the ledger retires; ``sam dispatch`` and ``sam active-task`` groups retire whole."""


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------


class Check(BaseModel):
    """One precondition, evaluated in order; the first failing check's reason is printed."""

    reason: str
    unless: str = ""
    """Flag or fact that waives the check."""


class Effect(BaseModel):
    """One column change a transition makes, as ``column`` and the value expression."""

    column: str
    value: str


class Transition(BaseModel):
    """What one command does from one status: checks in order, then effects and events."""

    command: str
    from_status: str
    """A ``Status`` value or ``ANY``."""
    checks: list[Check] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    to_status: str = ""
    """Resulting status; empty when unchanged."""
    noop: str = ""
    """Reason code when this transition is a no-op rather than a change."""
    note: str = ""


def _renew_effects() -> list[Effect]:
    return [
        Effect(column="expires", value="now + ttl_seconds"),
        Effect(column="last_activity", value="now"),
        Effect(column="first_renewed", value="now when null"),
    ]


def _clear_attempt_effects() -> list[Effect]:
    return [
        Effect(column="attempt_open", value="0"),
        Effect(column="result", value="null"),
        Effect(column="note", value="null"),
        Effect(column="settled", value="0"),
        Effect(column="return_text", value="null"),
        Effect(column="completed", value="null"),
    ]


CASCADE = Effect(
    column="status",
    value="skipped, on every transitive dependent that is not-started, each with task.state reason cascade:T{n}",
)
REVERSAL = Effect(
    column="status",
    value="not-started, on every dependent still skipped with cascade:T{n}, each with task.state reason cascade-reversed:T{n}",
)

OPEN_STATUSES = [
    Status.NOT_STARTED,
    Status.IN_PROGRESS,
    Status.COMPLETE,
    Status.BLOCKED,
    Status.DEFERRED,
    Status.SKIPPED,
    Status.FAILED,
]

TRANSITIONS: list[Transition] = [
    # dispatch
    Transition(
        command="dispatch",
        from_status=Status.NOT_STARTED,
        checks=[Check(reason="archived"), Check(reason="leased"), Check(reason="not-ready")],
        effects=[
            Effect(column="attempts", value="attempts + 1"),
            Effect(column="attempt_open", value="1"),
            Effect(column="ttl_seconds", value="--ttl or lease.ttl_seconds"),
            Effect(column="worktree", value="--worktree or null"),
            Effect(column="expires", value="now + ttl_seconds"),
            Effect(column="first_renewed", value="null"),
            Effect(column="started", value="now"),
            Effect(column="last_activity", value="now"),
            *[e for e in _clear_attempt_effects() if e.column != "attempt_open"],
        ],
        events=["task.dispatched"],
        to_status=Status.IN_PROGRESS,
        note="prints the new attempts value on stdout; every other command prints attempts only inside status output",
    ),
    *[
        Transition(
            command="dispatch",
            from_status=s,
            checks=[Check(reason="archived"), Check(reason="leased"), Check(reason="not-ready")],
        )
        for s in OPEN_STATUSES
        if s != Status.NOT_STARTED
    ],
    # read
    Transition(
        command="read",
        from_status=Status.IN_PROGRESS,
        checks=[Check(reason="stale-attempt", unless="--attempt absent")],
        effects=_renew_effects(),
        events=["lease.renewed"],
        note="without --attempt: reads, renews nothing, appends nothing",
    ),
    *[
        Transition(
            command="read",
            from_status=s,
            checks=[Check(reason="stale-attempt", unless="--attempt absent")],
            note="without --attempt: reads only",
        )
        for s in OPEN_STATUSES
        if s != Status.IN_PROGRESS
    ],
    # update
    Transition(
        command="update",
        from_status=Status.IN_PROGRESS,
        checks=[Check(reason="stale-attempt", unless="--attempt absent"), Check(reason="attempt-required")],
        effects=[
            Effect(column="sections", value="one row (name, attempts, content) per --append-section"),
            Effect(column="task model fields", value="per --set"),
            *_renew_effects(),
        ],
        events=["task.section", "task.fields", "plan.fields", "lease.renewed"],
        note="lease.renewed only with --attempt; task.section tagged with tasks.attempts",
    ),
    *[
        Transition(
            command="update",
            from_status=s,
            checks=[Check(reason="stale-attempt", unless="--attempt absent"), Check(reason="attempt-required")],
            effects=[Effect(column="task model fields", value="per --set")],
            events=["task.fields", "plan.fields"],
            note="a non-report section appends with attempt = tasks.attempts",
        )
        for s in OPEN_STATUSES
        if s != Status.IN_PROGRESS
    ],
    # renew
    Transition(
        command="renew",
        from_status=Status.IN_PROGRESS,
        checks=[
            Check(reason="stale-attempt", unless="--path given"),
            Check(reason="unmatched-path", unless="--attempt given"),
        ],
        effects=_renew_effects(),
        events=["lease.renewed"],
        note="prints renew_by",
    ),
    *[
        Transition(
            command="renew",
            from_status=s,
            checks=[
                Check(reason="stale-attempt", unless="--path given"),
                Check(reason="unmatched-path", unless="--attempt given"),
            ],
        )
        for s in OPEN_STATUSES
        if s != Status.IN_PROGRESS
    ],
    # finish
    Transition(
        command="finish",
        from_status=Status.IN_PROGRESS,
        checks=[Check(reason="stale-attempt"), Check(reason="report-missing", unless="--result is not complete")],
        effects=[
            Effect(column="attempt_open", value="0"),
            Effect(column="result", value="--result"),
            Effect(column="note", value="--note"),
            Effect(column="completed", value="now when --result is complete"),
            CASCADE,
        ],
        events=["task.finished", "task.state"],
        to_status="complete when --result complete; failed when failed; blocked when blocked or needs-input",
        note="task.state rows only for the cascade; expires keeps its value",
    ),
    *[
        Transition(command="finish", from_status=s, checks=[Check(reason="stale-attempt")])
        for s in OPEN_STATUSES
        if s != Status.IN_PROGRESS
    ],
    # settle
    Transition(
        command="settle",
        from_status=Status.IN_PROGRESS,
        checks=[
            Check(reason="stale-attempt", unless="--path given or attempt_open is 0 and --attempt equals attempts"),
            Check(reason="unmatched-path", unless="--attempt given"),
            Check(reason="already-settled"),
        ],
        effects=[
            Effect(column="settled", value="1"),
            Effect(column="return_text", value="--return-text"),
            Effect(column="attempt_open", value="0"),
        ],
        events=["task.settled"],
        note="settle names the attempt; it is accepted after finish closed the attempt, so the harness return text is always recorded",
    ),
    *[
        Transition(
            command="settle",
            from_status=s,
            checks=[Check(reason="stale-attempt", unless="--attempt equals attempts"), Check(reason="already-settled")],
            effects=[Effect(column="settled", value="1"), Effect(column="return_text", value="--return-text")],
            events=["task.settled"],
            note="status unchanged",
        )
        for s in (Status.COMPLETE, Status.FAILED, Status.BLOCKED)
    ],
    *[
        Transition(command="settle", from_status=s, checks=[Check(reason="stale-attempt")])
        for s in (Status.NOT_STARTED, Status.DEFERRED, Status.SKIPPED)
    ],
    # accept
    Transition(
        command="accept",
        from_status=Status.COMPLETE,
        checks=[Check(reason="already-accepted"), Check(reason="not-complete", unless="attempt_open is 0")],
        effects=[Effect(column="accepted", value="1")],
        events=["task.accepted"],
    ),
    Transition(
        command="accept",
        from_status=Status.IN_PROGRESS,
        checks=[
            Check(reason="already-accepted"),
            Check(reason="not-complete", unless="returned"),
            Check(reason="report-missing", unless="--force"),
        ],
        effects=[Effect(column="completed", value="now"), Effect(column="accepted", value="1")],
        events=["task.state", "task.accepted"],
        to_status=Status.COMPLETE,
        note="task.state reason returned-complete",
    ),
    *[
        Transition(
            command="accept", from_status=s, checks=[Check(reason="already-accepted"), Check(reason="not-complete")]
        )
        for s in (Status.NOT_STARTED, Status.FAILED, Status.BLOCKED, Status.DEFERRED, Status.SKIPPED)
    ],
    # reclaim
    Transition(
        command="reclaim", from_status=Status.NOT_STARTED, checks=[Check(reason="already-open")], noop="already-open"
    ),
    *[
        Transition(
            command="reclaim",
            from_status=s,
            checks=[
                Check(reason="task-accepted", unless="--force"),
                Check(reason="leased", unless="--force, or returned, or stale, or attempt_open is 0"),
                Check(reason="dependents-started", unless="--force"),
                Check(reason="attempts-exhausted", unless="--more-attempts"),
            ],
            effects=[
                Effect(column="attempts_allowed", value="attempts_allowed + loop.max_attempts when --more-attempts"),
                *_clear_attempt_effects(),
                Effect(column="accepted", value="0"),
                Effect(column="response", value="--response or null"),
                REVERSAL,
            ],
            events=["task.reclaimed", "task.state"],
            to_status=Status.NOT_STARTED,
            note="task.state rows only for the reversal, which applies when from_status is failed; sections keep their attempt tag and read renders older attempts under '<name> (attempt N)'",
        )
        for s in OPEN_STATUSES
        if s != Status.NOT_STARTED
    ],
    # state
    *[
        Transition(
            command="state",
            from_status=s,
            checks=[
                Check(reason="status-invalid"),
                Check(reason="task-accepted", unless="--force"),
                Check(reason="leased", unless="--force, or attempt_open is 0"),
                Check(reason="report-missing", unless="--new-status is not complete, or --force"),
            ],
            effects=[
                Effect(column="attempt_open", value="0"),
                Effect(column="accepted", value="0 when --force"),
                Effect(column="completed", value="now when --new-status is complete"),
                CASCADE,
                REVERSAL,
            ],
            events=["task.state"],
            to_status="--new-status",
            note="CASCADE applies when entering failed; REVERSAL when leaving failed",
        )
        for s in OPEN_STATUSES
    ],
    # plan-scoped
    Transition(
        command="create",
        from_status=ANY,
        checks=[Check(reason="exists")],
        effects=[
            Effect(column="plans", value="one row; state drafting when no task is given"),
            Effect(column="tasks", value="one row per task given"),
        ],
        events=["plan.created", "task.added"],
    ),
    Transition(
        command="append-task",
        from_status=ANY,
        checks=[Check(reason="archived")],
        effects=[
            Effect(
                column="tasks",
                value="one row with attempts 0, attempts_allowed loop.max_attempts, accepted 0, attempt_open 0",
            )
        ],
        events=["task.added"],
    ),
    Transition(
        command="finalize",
        from_status=ANY,
        checks=[Check(reason="archived")],
        effects=[Effect(column="state", value="ready")],
        events=["plan.fields"],
    ),
    Transition(
        command="archive",
        from_status=ANY,
        checks=[Check(reason="archived")],
        effects=[Effect(column="archived", value="now"), Effect(column="attempt_open", value="0 on every task")],
        events=["plan.archived"],
    ),
    Transition(
        command="import",
        from_status=ANY,
        checks=[
            Check(reason="exists", unless="--replace"),
            Check(reason="leased", unless="no task of the existing plan has attempt_open 1"),
        ],
        effects=[
            Effect(
                column="plans, tasks, sections",
                value="rows from the source; attempt_open 0; attempts and accepted from the source, else 0 and (status is complete); sections tagged 0",
            ),
            Effect(column="export_cursors", value="target content, revision and projection_hash of the source"),
        ],
        events=["plan.created", "plan.replaced", "task.imported", "plan.imported"],
        note="no cascade runs on import",
    ),
    Transition(
        command="export",
        from_status=ANY,
        checks=[Check(reason="unchanged")],
        effects=[Effect(column="export_cursors", value="last_seq, revision, projection_hash")],
        events=["plan.exported"],
        note="projection excludes last_activity, expires, first_renewed, renew_by, worktree, ttl_seconds",
    ),
    Transition(
        command="from-milestone",
        from_status=ANY,
        checks=[
            Check(reason="exists", unless="--replace"),
            Check(reason="leased", unless="no task of the existing plan has attempt_open 1"),
        ],
        effects=[
            Effect(column="plans", value="milestone, integration_branch, base_sha = the branch head, quality_gates"),
            Effect(
                column="tasks",
                value="one per item: github_issue, dependencies = depends_on, acceptance_criteria and verification_steps = groomed sections, conflict_group from dispatch_conflicts on GitHub, else null",
            ),
        ],
        events=["plan.created", "plan.replaced", "task.added"],
    ),
]


class Config(BaseModel):
    """One ``.dh/config.yaml`` key the ledger reads."""

    key: str
    default: int
    used_by: str


CONFIG: list[Config] = [
    Config(
        key="lease.ttl_seconds",
        default=1800,
        used_by="dispatch; sized above the longest gap between a runner's sam commands",
    ),
    Config(
        key="loop.max_attempts", default=3, used_by="reclaim; attempts_allowed starts here and --more-attempts adds it"
    ),
]
