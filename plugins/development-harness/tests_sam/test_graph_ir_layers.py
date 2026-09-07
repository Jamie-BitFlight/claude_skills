"""Falsification of the layered graph IR against ``ASSESSOR-CONTRACT.md``'s "The layers".

Each test targets one obligation from that section: the projection relationship between layer 1
and layer 3, the layer-2 bookend guarantee, extension provenance for a runtime-mutated layer-2
graph, and decomposition traceability between layer 2 and its grooming/architecture input. Where
the contract asks for an illegal combination to be unconstructible, the test asserts a
``ValidationError``; where it asks for a checkable property of a graph that must still be
representable when malformed, the test asserts the query's `Observation` output.
"""

from __future__ import annotations

import pytest
from dh_core.graph_ir.decomposition import DecompositionInput, DecompositionItem, DecompositionSourceKind
from dh_core.graph_ir.layer import Layer
from dh_core.graph_ir.ledger_layer import LedgerCommand, LedgerEdge, LedgerGraph, LedgerStatus
from dh_core.graph_ir.model import Authority, ExtractionStatus, Graph, Node, SourceSpan
from dh_core.graph_ir.system import LayeredGraph
from dh_core.graph_ir.vocabulary import EdgeType
from dh_core.graph_ir.work_layer import (
    BookendKind,
    ExtensionKind,
    ExtensionOperation,
    WorkEdge,
    WorkGraph,
    WorkNode,
    WorkNodeProvenance,
)
from pydantic import ValidationError

CONTRACT = "plugins/development-harness/docs/graph-ir/ASSESSOR-CONTRACT.md"
SPEC = "plugins/development-harness/dh_core/ledger_spec.py"


def spans(*refs: str) -> list[SourceSpan]:
    return [SourceSpan(ref=r) for r in refs]


def workflow_node(node_id: str, actor: str = "judge") -> Node:
    return Node(
        id=node_id,
        actor=actor,
        authority=Authority(holder=actor),
        source_refs=spans(CONTRACT),
        extraction_status=ExtractionStatus.OBSERVED,
    )


def work_node(node_id: str, **kw) -> WorkNode:
    kw.setdefault("source_refs", spans(SPEC))
    kw.setdefault("extraction_status", ExtractionStatus.OBSERVED)
    return WorkNode(id=node_id, task_ref=node_id, **kw)


def work_edge(edge_id: str, type_: EdgeType, source: str, target: str, **kw) -> WorkEdge:
    kw.setdefault("source_refs", spans(SPEC))
    kw.setdefault("extraction_status", ExtractionStatus.OBSERVED)
    return WorkEdge(id=edge_id, type=type_, source=source, target=target, **kw)


# -- layer 1: the projection relationship --------------------------------------------------------


def test_ledger_edge_with_no_projection_is_flagged():
    """A transition naming no layer-3 origin is well-formed but has already lost its actor."""
    accept = LedgerEdge(
        id="accept-e1",
        command=LedgerCommand.ACCEPT,
        source=LedgerStatus.COMPLETE.value,
        target=LedgerStatus.COMPLETE.value,
        task_ref="T1",
        source_refs=spans(SPEC),
        extraction_status=ExtractionStatus.OBSERVED,
    )
    ledger = LedgerGraph.canonical_machine([accept], source_refs=spans(SPEC))
    unattributed = ledger.edges_without_workflow_origin()
    assert [o.subject for o in unattributed] == ["accept-e1"]


def test_ledger_edge_projection_must_resolve_against_the_workflow_graph():
    """A stated projection that names no workflow node is a different defect from stating none."""
    accept = LedgerEdge(
        id="accept-e1",
        command=LedgerCommand.ACCEPT,
        source=LedgerStatus.COMPLETE.value,
        target=LedgerStatus.COMPLETE.value,
        task_ref="T1",
        projects_from="does-not-exist",
        source_refs=spans(SPEC),
        extraction_status=ExtractionStatus.OBSERVED,
    )
    system = LayeredGraph(
        ledger=LedgerGraph.canonical_machine([accept], source_refs=spans(SPEC)),
        work=WorkGraph(),
        workflow=Graph(nodes=[workflow_node("judge-accepts")]),
    )
    assert system.edges_without_workflow_origin() == []  # a projection *is* stated
    unresolved = system.unresolved_projections()
    assert [o.subject for o in unresolved] == ["accept-e1"]


def test_ledger_edge_projection_resolving_is_clean():
    """The positive case: a projection naming a real workflow node raises no observation."""
    accept = LedgerEdge(
        id="accept-e1",
        command=LedgerCommand.ACCEPT,
        source=LedgerStatus.COMPLETE.value,
        target=LedgerStatus.COMPLETE.value,
        task_ref="T1",
        projects_from="judge-accepts",
        source_refs=spans(SPEC),
        extraction_status=ExtractionStatus.OBSERVED,
    )
    system = LayeredGraph(
        ledger=LedgerGraph.canonical_machine([accept], source_refs=spans(SPEC)),
        work=WorkGraph(),
        workflow=Graph(nodes=[workflow_node("judge-accepts")]),
    )
    assert system.edges_without_workflow_origin() == []
    assert system.unresolved_projections() == []


def test_ledger_edge_task_ref_must_resolve_against_the_work_graph():
    """'One uniform machine, instantiated per task' presupposes the task exists in layer 2."""
    accept = LedgerEdge(
        id="accept-e1",
        command=LedgerCommand.ACCEPT,
        source=LedgerStatus.COMPLETE.value,
        target=LedgerStatus.COMPLETE.value,
        task_ref="T-does-not-exist",
        source_refs=spans(SPEC),
        extraction_status=ExtractionStatus.OBSERVED,
    )
    system = LayeredGraph(
        ledger=LedgerGraph.canonical_machine([accept], source_refs=spans(SPEC)),
        work=WorkGraph(nodes=[work_node("T1")]),
        workflow=Graph(),
    )
    assert [o.subject for o in system.unresolved_task_refs()] == ["accept-e1"]

    resolving = system.model_copy(
        update={"ledger": LedgerGraph.canonical_machine([accept.model_copy(update={"task_ref": "T1"})], spans(SPEC))}
    )
    assert resolving.unresolved_task_refs() == []


def test_extension_performer_must_resolve_against_the_workflow_graph():
    """An extension's performer is a claim about layer 3, checkable only once both graphs exist."""
    split_child = work_node(
        "T1a", provenance=WorkNodeProvenance.SPLIT, inserted_by="ghost-node", inserted_reason="exceeded context window"
    )
    operation = ExtensionOperation(
        id="op1",
        kind=ExtensionKind.SPLIT,
        performed_by="ghost-node",
        reason="exceeded context window",
        produces=("T1a",),
        source_refs=spans(CONTRACT),
        extraction_status=ExtractionStatus.OBSERVED,
    )
    system = LayeredGraph(
        ledger=LedgerGraph.canonical_machine([], source_refs=spans(SPEC)),
        work=WorkGraph(nodes=[split_child], extensions=[operation]),
        workflow=Graph(),  # no "ghost-node" here
    )
    assert [o.subject for o in system.unresolved_extension_performers()] == ["op1"]

    resolving = system.model_copy(update={"workflow": Graph(nodes=[workflow_node("ghost-node")])})
    assert resolving.unresolved_extension_performers() == []


# -- layer 2: the bookend guarantee --------------------------------------------------------


def test_work_graph_missing_all_bookends():
    work = WorkGraph(nodes=[work_node("T1"), work_node("T2")])
    missing = work.missing_bookends()
    assert {o.subject for o in missing} == {
        "work-graph.review",
        "work-graph.validate",
        "work-graph.documentation-check",
    }


def test_work_graph_with_all_bookends_is_not_malformed():
    work = WorkGraph(
        nodes=[
            work_node("T1"),
            work_node("T-review", bookend=BookendKind.REVIEW),
            work_node("T-validate", bookend=BookendKind.VALIDATE),
            work_node("T-doc", bookend=BookendKind.DOCUMENTATION_CHECK),
        ]
    )
    assert work.missing_bookends() == []


# -- layer 2: concurrency and ordering --------------------------------------------------------


def test_control_edge_orders_two_nodes():
    work = WorkGraph(nodes=[work_node("T1"), work_node("T2")], edges=[work_edge("e1", EdgeType.CONTROL, "T1", "T2")])
    assert work.blocked_on("T2") == {"T1"}
    assert work.may_run_concurrently("T1", "T2") is False


def test_independent_nodes_may_run_concurrently():
    work = WorkGraph(nodes=[work_node("T1"), work_node("T2")])
    assert work.may_run_concurrently("T1", "T2") is True


def test_shared_conflict_group_forbids_concurrency():
    work = WorkGraph(nodes=[work_node("T1", conflict_group="g"), work_node("T2", conflict_group="g")])
    assert work.may_run_concurrently("T1", "T2") is False


def test_shared_state_resource_forbids_concurrency():
    """A STATE edge directly between the two contending nodes names the resource they share."""
    work = WorkGraph(
        nodes=[work_node("T1"), work_node("T2")],
        edges=[work_edge("e1", EdgeType.STATE, "T1", "T2", resource="lease:T")],
    )
    assert work.may_run_concurrently("T1", "T2") is False


# -- layer 2: extension at runtime --------------------------------------------------------


def test_inserted_node_requires_its_provenance_fields():
    with pytest.raises(ValidationError, match="inserted_by"):
        work_node("T-found", provenance=WorkNodeProvenance.INSERTED)
    with pytest.raises(ValidationError, match="inserted_reason"):
        work_node("T-found", provenance=WorkNodeProvenance.INSERTED, inserted_by="workflow-node")


def test_work_graph_refuses_a_non_planned_node_with_no_producing_extension():
    orphan = work_node(
        "T-found", provenance=WorkNodeProvenance.INSERTED, inserted_by="workflow-node", inserted_reason="found mid-run"
    )
    with pytest.raises(ValidationError, match="no extension produces it"):
        WorkGraph(nodes=[orphan])


def test_work_graph_refuses_an_extension_whose_kind_disagrees_with_the_node():
    split_child = work_node(
        "T1a",
        provenance=WorkNodeProvenance.SPLIT,
        inserted_by="workflow-node",
        inserted_reason="exceeded context window",
    )
    wrong_kind = ExtensionOperation(
        id="op1",
        kind=ExtensionKind.INSERT,  # disagrees with the node's SPLIT provenance
        performed_by="workflow-node",
        reason="exceeded context window",
        produces=("T1a",),
        source_refs=spans(CONTRACT),
        extraction_status=ExtractionStatus.OBSERVED,
    )
    with pytest.raises(ValidationError, match="must carry provenance"):
        WorkGraph(nodes=[split_child], extensions=[wrong_kind])


def test_work_graph_accepts_a_consistent_split_and_reports_its_provenance():
    split_child = work_node(
        "T1a",
        provenance=WorkNodeProvenance.SPLIT,
        inserted_by="workflow-node",
        inserted_reason="exceeded context window",
    )
    operation = ExtensionOperation(
        id="op1",
        kind=ExtensionKind.SPLIT,
        performed_by="workflow-node",
        reason="exceeded context window",
        replaces=("T1",),
        produces=("T1a",),
        source_refs=spans(CONTRACT),
        extraction_status=ExtractionStatus.OBSERVED,
    )
    work = WorkGraph(nodes=[split_child], extensions=[operation])
    answer = work.provenance_of("T1a")
    assert answer.observed == "split by 'workflow-node' (split): exceeded context window"

    planned = work_node("T2")
    work_with_planned = WorkGraph(nodes=[planned])
    assert work_with_planned.provenance_of("T2").observed == "planned up front by decomposition"


# -- layer 2 / decomposition input: traceability --------------------------------------------------------


def _decomposition_item(item_id: str) -> DecompositionItem:
    return DecompositionItem(
        id=item_id,
        kind=DecompositionSourceKind.RESEARCH,
        summary="prior art for the retry loop",
        source_refs=spans(CONTRACT),
        extraction_status=ExtractionStatus.OBSERVED,
    )


def test_planned_node_tracing_to_an_item_is_clean_both_ways():
    decomposition = DecompositionInput(items=[_decomposition_item("R1")])
    work = WorkGraph(nodes=[work_node("T1", decomposition_source="R1")])
    assert decomposition.untraced_planned_nodes(work) == []
    assert decomposition.unreached_items(work) == []


def test_planned_node_with_no_decomposition_source_is_untraced():
    decomposition = DecompositionInput(items=[_decomposition_item("R1")])
    work = WorkGraph(nodes=[work_node("T1")])
    untraced = decomposition.untraced_planned_nodes(work)
    assert [o.subject for o in untraced] == ["T1"]
    unreached = decomposition.unreached_items(work)
    assert [o.subject for o in unreached] == ["R1"]


def test_inserted_node_is_not_held_to_decomposition_traceability():
    decomposition = DecompositionInput(items=[_decomposition_item("R1")])
    inserted = work_node(
        "T-found", provenance=WorkNodeProvenance.INSERTED, inserted_by="workflow-node", inserted_reason="found mid-run"
    )
    operation = ExtensionOperation(
        id="op1",
        kind=ExtensionKind.INSERT,
        performed_by="workflow-node",
        reason="found mid-run",
        produces=("T-found",),
        source_refs=spans(CONTRACT),
        extraction_status=ExtractionStatus.OBSERVED,
    )
    work = WorkGraph(nodes=[inserted], extensions=[operation])
    # T-found has no decomposition_source and is not PLANNED, so it is silently exempt --
    # it was inserted precisely because the decomposition did not account for it.
    assert decomposition.untraced_planned_nodes(work) == []


# -- the layer discriminator is a type, not a label --------------------------------------------------------


def test_each_layer_pins_its_own_discriminator():
    ledger_node = LedgerGraph.canonical_machine([], source_refs=spans(SPEC)).nodes[0]
    assert ledger_node.layer is Layer.LEDGER
    assert work_node("T1").layer is Layer.WORK
    assert workflow_node("N1").layer is Layer.WORKFLOW


def test_a_work_node_cannot_be_stamped_with_another_layer():
    """A layer-2 node stamped layer 3 must be refused at construction, not merely discouraged.

    Built through ``model_validate`` on a mapping rather than by keyword: the whole point is an
    argument the type system rejects, so passing it directly makes the type checker report the
    test's own subject as a defect.
    """
    with pytest.raises(ValidationError):
        WorkNode.model_validate({
            "id": "T1",
            "task_ref": "T1",
            "layer": Layer.WORKFLOW,
            "source_refs": spans(SPEC),
            "extraction_status": ExtractionStatus.OBSERVED,
        })
