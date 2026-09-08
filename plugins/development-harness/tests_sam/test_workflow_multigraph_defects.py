"""Falsification of the workflow multigraph against the four defects this branch already fixed by hand.

Each defect was a drift the control-flow-only ledger specification could not represent. The
multigraph earns its place only if, for each one, it either refuses to construct the situation
(UNREPRESENTABLE) or makes a predicate over the graph demonstrably false (DETECTABLE) at the
severity the assessor contract's rule assigns.

The verdicts, and why:

D1 AUTHORITY -- DETECTABLE, not unrepresentable. ``import`` marking a ``complete`` task as
   ``accepted`` is a well-formed graph: identical schema, one DATA edge, no dangling reference.
   Refusing to construct it would be the extractor silently repairing the system, which report
   validation forbids. The defect is caught by two predicates over the descriptors' authority and
   trust facets, both BROKEN because ``ledger_spec`` declares what satisfies a dependency.

D2 AUTHORITY -- DETECTABLE. A data write performing a control transition is a node whose side
   effect its own authority does not grant, plus a state node whose transition record has no
   producer. Both are contract predicates; both are BROKEN.

D3 EVIDENCE/DATA -- DETECTABLE, at CONTRACT_UNSPECIFIED rather than BROKEN. The type mismatch
   between prose and a set of paths is mechanical, but no source declares the overlap relation the
   judge is asked to compute, so the severity rule forbids BROKEN. This is the case where the rule
   does real work: a checker that shouted BROKEN here would be speculating about a contract that
   was never written.

D4 STATE/INVALIDATES -- DETECTABLE. Deleting rows nothing records is an INVALIDATES edge with no
   record and a fold input with no producer; the orphaned plan row is a revision mismatch between
   the row written and the row the incoming tasks name.

No defect is UNREPRESENTABLE, and that is the design, not a gap: the multigraph's first obligation
is to hold a faithful picture of a broken system. What it refuses is an incoherent *graph* -- a dangling
edge, an undeclared descriptor, an element with no source span -- and an invented severity.
"""

from __future__ import annotations

import pytest
from dh_core.workflow_multigraph.findings import (
    PREDICATES,
    SEVERITY_BY_BASIS,
    ContractBasis,
    Finding,
    Predicate,
    Severity,
)
from dh_core.workflow_multigraph.model import (
    TRUST_ORDER,
    Authority,
    Cardinality,
    Completeness,
    Descriptor,
    Edge,
    EdgeType,
    Effect,
    ExtractionStatus,
    Freshness,
    Graph,
    Node,
    SideEffect,
    SourceSpan,
    Trust,
)
from pydantic import ValidationError

SPEC = "plugins/development-harness/dh_core/ledger_spec.py"
MODELS = "plugins/development-harness/sam_schema/core/models.py"
VERDICT = "the verdict that an attempt satisfies the task, and so releases its dependents"


def spans(*refs: str) -> tuple[SourceSpan, ...]:
    return tuple(SourceSpan(ref=r) for r in refs)


def desc(name, type_, meaning, **kw):
    kw.setdefault("cardinality", Cardinality.EXACTLY_ONE)
    kw.setdefault("completeness", Completeness.TOTAL)
    kw.setdefault("trust", Trust.PROPOSED)
    kw.setdefault("provenance", SPEC)
    kw.setdefault("extraction_status", ExtractionStatus.OBSERVED)
    kw.setdefault("source_refs", list(spans(SPEC)))
    return Descriptor(name=name, syntactic_type=type_, semantic_meaning=meaning, **kw)


def node(node_id, actor, grants=(), **kw):
    kw.setdefault("extraction_status", ExtractionStatus.OBSERVED)
    kw.setdefault("source_refs", list(spans(SPEC)))
    return Node(id=node_id, actor=actor, authority=Authority(holder=actor, grants=frozenset(grants)), **kw)


def edge(edge_id, type_, source, target, **kw):
    kw.setdefault("extraction_status", ExtractionStatus.OBSERVED)
    kw.setdefault("source_refs", list(spans(SPEC)))
    return Edge(id=edge_id, type=type_, source=source, target=target, **kw)


# -- D1 -- import grants the judge's verdict on the runner's claim --------------------------------------------------------


def d1_graph() -> Graph:
    importer = node(
        "import",
        "importer",
        grants=[Effect.MUTATE],
        outputs=[
            desc(
                "accepted",
                "int(0|1)",
                VERDICT,
                granting_authority="importer",
                trust=Trust.PROPOSED,
                provenance="the source plan's status column, mapped complete -> accepted",
            )
        ],
    )
    ready = node(
        "ready",
        "ledger",
        grants=[Effect.DECIDE],
        required_inputs=[
            desc(
                "dependency_verdict",
                "int(0|1)",
                VERDICT,
                required_authority="judge",
                trust=Trust.VERIFIED,
                provenance="task.accepted, appended by the accept command",
            )
        ],
    )
    return Graph(
        nodes=[importer, ready],
        edges=[
            edge("e1", EdgeType.DATA, "import", "ready", source_output="accepted", target_input="dependency_verdict")
        ],
    )


def test_d1_import_supplies_the_runners_claim_where_a_judges_verdict_is_required():
    """D1 is DETECTABLE, not unrepresentable.

    The graph is well formed: one DATA edge, endpoints resolve, and the syntactic types are
    identical -- ``int(0|1)`` on both sides, which is why a schema check sees nothing. Refusing to
    build it would mean the multigraph could not hold the system as it actually was, and model fidelity is
    the first thing report validation checks. Two facets carry the difference: the authority the
    value was produced under, and its trust classification.
    """
    graph = d1_graph()
    assert graph.type_incompatible_edges() == [], "identical schema; a type check cannot see this"

    trust = graph.trust_shortfalls()
    authority = graph.authority_shortfalls()
    assert len(trust) == 1
    assert len(authority) == 1
    assert "PROPOSED" in trust[0].observed
    assert "'importer'" in authority[0].observed

    declared = (
        "ledger_spec.SUCCESSFUL_DEPENDENCY: 'A dependency counts as satisfied when it is accepted, or in "
        "one of these statuses'; tasks.ready rule: 'every id in dependencies names a task that is accepted "
        "or in SUCCESSFUL_DEPENDENCY'. The task.accepted event is written_by ['accept'] alone, so acceptance "
        "is the judge's verdict; the tasks.accepted column is also set by task.imported, which is the drift."
    )
    findings = [
        Finding.from_observation(
            Predicate.TRUST_BELOW_REQUIREMENT, ContractBasis.DECLARED, declared, trust[0], spans(SPEC), ("e1",)
        ),
        Finding.from_observation(
            Predicate.ACTOR_LACKS_AUTHORITY, ContractBasis.DECLARED, declared, authority[0], spans(SPEC), ("e1",)
        ),
    ]
    assert [f.severity for f in findings] == [Severity.BROKEN, Severity.BROKEN]
    assert findings[0].statement == "the consumer requires VERIFIED and the producer supplies PROPOSED"


# -- D2 -- a data write performs a control transition --------------------------------------------------------


def d2_graph() -> Graph:
    update = node(
        "update_set_status",
        "runner",
        grants=[Effect.MUTATE],
        outputs=[desc("changed", "json: field=value pairs", "the task model fields --set wrote")],
        side_effects=[
            SideEffect(
                target="tasks.status",
                effect=Effect.DECIDE,
                description="moves the task to complete with no lease check, report check or cascade",
            )
        ],
    )
    status = node(
        "tasks_status",
        "ledger",
        grants=[Effect.MUTATE],
        required_inputs=[
            desc(
                "transition_event",
                "task.state event",
                "the row a rebuild replays to restate the task's status",
                required_authority="orchestrator",
                trust=Trust.AUTHORITATIVE,
                provenance="task.state, written by state, finish, reclaim and accept",
            )
        ],
    )
    return Graph(
        nodes=[update, status],
        edges=[edge("e1", EdgeType.DATA, "update_set_status", "tasks_status", source_output="changed")],
    )


def test_d2_a_data_edge_performs_a_control_transition():
    """D2 is DETECTABLE.

    Nothing about the shape of this graph is malformed -- a node writes fields and touches state --
    so there is nothing for a constructor to refuse. What the multigraph separates is the *effect* from the
    edge that carries it: the node's authority grants ``mutate`` and the transition it performs is
    ``decide``, and the status node's transition record has no producer at all, so the fold cannot
    restate the column it just changed.
    """
    graph = d2_graph()
    ungranted = graph.effects_without_authority()
    assert len(ungranted) == 1
    assert ungranted[0].subject == "update_set_status:decide:tasks.status"

    unproduced = [o for o in graph.inputs_without_producer() if o.subject == "tasks_status.transition_event"]
    assert len(unproduced) == 1
    assert [e.type for e in graph.edges if e.target == "tasks_status"] == [EdgeType.DATA]

    findings = [
        Finding.from_observation(
            Predicate.ACTOR_LACKS_AUTHORITY,
            ContractBasis.DECLARED,
            "ledger_spec.COMMANDS: state is 'the orchestrator's decision without a runner' and carries the "
            "leased, task-accepted and report-missing checks; update's summary is 'task.fields, plan.fields, "
            "task.section' and it carries none of them.",
            ungranted[0],
            spans(SPEC),
            ("update_set_status",),
        ),
        Finding.from_observation(
            Predicate.REQUIRED_INPUT_HAS_NO_PRODUCER,
            ContractBasis.DECLARED,
            "ledger_spec module docstring: 'Every materialised table is a fold over the log'; COLUMNS gives "
            "tasks.status set_by task.added, task.imported, task.dispatched, task.finished, task.state, "
            "task.reclaimed -- task.fields is not among them.",
            unproduced[0],
            spans(SPEC),
            ("tasks_status",),
        ),
    ]
    assert {f.severity for f in findings} == {Severity.BROKEN}


# -- D3 -- FILES_CHANGED overlap is prose, not a relation --------------------------------------------------------


def d3_graph() -> Graph:
    report = node(
        "runner_report",
        "runner",
        grants=[Effect.MUTATE],
        outputs=[
            desc(
                "files_changed",
                "markdown-section-body",
                "free text the runner wrote under a FILES_CHANGED heading",
                completeness=Completeness.UNSPECIFIED,
                granting_authority="runner",
                provenance="a sections row named in REPORT_SECTIONS, tagged with the attempt",
            )
        ],
    )
    sendback = node(
        "tn_sendback",
        "judge",
        grants=[Effect.DECIDE, Effect.RETRY],
        required_inputs=[
            desc(
                "changed_files",
                "set[path]",
                "every file the attempt wrote, as paths intersectable with the files a failing criterion names",
                required_authority="runner",
                trust=Trust.PROPOSED,
                completeness=Completeness.TOTAL,
                extraction_status=ExtractionStatus.INFERRED,
                provenance="the TN send-back rule, stated as prose addressed to a judge",
            )
        ],
    )
    return Graph(
        nodes=[report, sendback],
        edges=[
            edge(
                "e1",
                EdgeType.EVIDENCE,
                "runner_report",
                "tn_sendback",
                source_output="files_changed",
                target_input="changed_files",
            )
        ],
    )


def test_d3_files_changed_is_prose_where_a_computable_set_is_required():
    """D3 is DETECTABLE, and the severity rule holds it at CONTRACT_UNSPECIFIED.

    The mismatch is mechanical: ``markdown-section-body`` does not satisfy ``set[path]``, and the
    producer declares no widening. What is not mechanical is whether anything was promised. Nothing
    in the ledger specification declares the overlap relation -- reclaim takes ``--reason`` as free
    text, and REPORT_SECTIONS names the sections without giving them structure -- so the requirement
    is recorded INFERRED, and the rule refuses BROKEN. Reporting this as a broken contract would be
    speculating about a contract nobody wrote.
    """
    graph = d3_graph()
    mismatches = graph.type_incompatible_edges()
    assert len(mismatches) == 1
    assert "set[path]" in mismatches[0].expected
    assert "markdown-section-body" in mismatches[0].observed
    assert graph.node("tn_sendback").required_inputs[0].extraction_status is ExtractionStatus.INFERRED

    finding = Finding.from_observation(
        Predicate.PRODUCER_TYPE_UNSATISFIED,
        ContractBasis.UNSPECIFIED,
        "ledger_spec declares reclaim --reason as 'text' and REPORT_SECTIONS as two section names; no source "
        "states that FILES_CHANGED is a path list, nor that reclaim intersects it with a criterion's files.",
        mismatches[0],
        spans(SPEC),
        ("e1",),
    )
    assert finding.severity is Severity.CONTRACT_UNSPECIFIED
    assert finding.severity is not Severity.BROKEN

    # The rule is only as honest as the basis, which is why basis_evidence is mandatory and is what
    # finding verification re-checks: claim DECLARED and the same observation becomes BROKEN.
    overclaimed = finding.model_copy(update={"basis": ContractBasis.DECLARED})
    assert overclaimed.severity is Severity.BROKEN


# -- D4 -- a replace revokes state nothing records --------------------------------------------------------


def d4_graph() -> Graph:
    replace = node(
        "from_milestone_replace",
        "orchestrator",
        grants=[Effect.MUTATE, Effect.PUBLISH],
        outputs=[
            desc(
                "plan_row",
                "plans row",
                "the plan row the replace left behind",
                granting_authority="orchestrator",
                trust=Trust.AUTHORITATIVE,
                freshness=Freshness(version="P-old"),
            )
        ],
    )
    fold = node(
        "fold_rebuild",
        "ledger",
        grants=[Effect.MUTATE],
        required_inputs=[
            desc(
                "sections_clears_record",
                "event payload field 'clears'",
                "the record naming which tables the replace emptied",
                required_authority="orchestrator",
                trust=Trust.AUTHORITATIVE,
                provenance="the plan.replaced payload",
            ),
            desc(
                "plan_row_for_tasks",
                "plans row",
                "the plan row the incoming task rows name in tasks.plan",
                required_authority="orchestrator",
                trust=Trust.AUTHORITATIVE,
                freshness=Freshness(version="P-new"),
            ),
        ],
    )
    sections = node("sections", "ledger", grants=[Effect.MUTATE])
    cursors = node("export_cursors", "ledger", grants=[Effect.MUTATE])
    return Graph(
        nodes=[replace, fold, sections, cursors],
        edges=[
            edge("inv_sections", EdgeType.INVALIDATES, "from_milestone_replace", "sections"),
            edge("inv_cursors", EdgeType.INVALIDATES, "from_milestone_replace", "export_cursors"),
            edge(
                "e_plan",
                EdgeType.DATA,
                "from_milestone_replace",
                "fold_rebuild",
                source_output="plan_row",
                target_input="plan_row_for_tasks",
            ),
        ],
    )


def test_d4_replace_revokes_state_no_event_accounts_for():
    """D4 is DETECTABLE.

    An INVALIDATES edge is the only place this defect exists at all: the control-flow-only
    specification has no relation for "what this result revokes", so the deletion of the sections
    and export-cursor rows was invisible. Here it is two edges whose ``recorded_by`` is empty, and a
    fold input -- the record of what was emptied -- that no output produces. The orphaned plan row
    is separate: the row written names one plan revision and the incoming task rows name another.
    """
    graph = d4_graph()
    unrecorded = graph.unrecorded_invalidations()
    assert {o.subject for o in unrecorded} == {"inv_sections", "inv_cursors"}

    unproduced = [o for o in graph.inputs_without_producer() if o.subject.endswith("sections_clears_record")]
    assert len(unproduced) == 1

    orphan = graph.revision_mismatches()
    assert len(orphan) == 1
    assert orphan[0].expected == "revision 'P-new'"
    assert orphan[0].observed == "revision 'P-old'"

    fold_obligation = (
        "ledger_spec module docstring: 'Every materialised table is a fold over the log: rebuild empties them "
        "and replays events into them'; the plan.replaced payload carries 'clears', the tables it emptied."
    )
    findings = [
        Finding.from_observation(
            Predicate.REQUIRED_INPUT_HAS_NO_PRODUCER,
            ContractBasis.DECLARED,
            fold_obligation,
            unproduced[0],
            spans(SPEC),
            ("inv_sections", "inv_cursors"),
        ),
        Finding.from_observation(
            Predicate.REVISION_MISMATCH,
            ContractBasis.NECESSARILY_IMPLIED,
            "No source states it, but tasks.plan is a text column holding the owning plan's id and every "
            "plan-scoped read joins on it; a task row naming a plan row that was not written for it cannot be "
            "read back at all.",
            orphan[0],
            spans(SPEC, MODELS),
            ("e_plan",),
        ),
    ]
    assert {f.severity for f in findings} == {Severity.BROKEN}


# -- What the multigraph does refuse -------------------------------------------------


def test_severity_cannot_be_invented():
    observation = d1_graph().trust_shortfalls()[0]
    payload = {
        "predicate": Predicate.TRUST_BELOW_REQUIREMENT,
        "basis": ContractBasis.UNSPECIFIED,
        "basis_evidence": "nothing in the sources declares it",
        "subject": observation.subject,
        "expected": observation.expected,
        "observed": observation.observed,
        "source_spans": spans(SPEC),
    }
    assert Finding.model_validate(payload).severity is Severity.CONTRACT_UNSPECIFIED
    with pytest.raises(ValidationError):
        Finding.model_validate({**payload, "severity": Severity.BROKEN})


def test_severity_taxonomy_is_closed():
    assert set(SEVERITY_BY_BASIS) == set(ContractBasis)
    assert set(SEVERITY_BY_BASIS.values()) == set(Severity)
    assert set(PREDICATES) == set(Predicate)
    assert all(PREDICATES[p].statement for p in Predicate)
    assert sorted(TRUST_ORDER, key=lambda t: TRUST_ORDER[t]) == [
        Trust.UNTRUSTED,
        Trust.PROPOSED,
        Trust.VERIFIED,
        Trust.AUTHORITATIVE,
    ]


def test_graph_refuses_an_incoherent_graph():
    with pytest.raises(ValidationError, match="unknown target node"):
        Graph(nodes=[node("a", "x")], edges=[edge("e", EdgeType.CONTROL, "a", "b")])
    with pytest.raises(ValidationError, match="absent from"):
        Graph(
            nodes=[node("a", "x"), node("b", "y")], edges=[edge("e", EdgeType.DATA, "a", "b", source_output="nothing")]
        )
    with pytest.raises(ValidationError, match="duplicate node id"):
        Graph(nodes=[node("a", "x"), node("a", "y")])


def test_every_element_carries_its_provenance():
    with pytest.raises(ValidationError):
        Node.model_validate({"id": "a", "actor": "x", "authority": {"holder": "x"}, "extraction_status": "OBSERVED"})
    with pytest.raises(ValidationError):
        Finding(
            predicate=Predicate.UNREACHABLE,
            basis=ContractBasis.DECLARED,
            basis_evidence="",
            subject="a",
            expected="b",
            observed="c",
            source_spans=spans(SPEC),
        )
