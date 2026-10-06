"""Local contracts for the exported workflow-multigraph predicates."""

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


def spans() -> tuple[SourceSpan, ...]:
    return (SourceSpan(ref="contract"),)


def descriptor(name, type_, meaning, **kwargs):
    kwargs.setdefault("cardinality", Cardinality.EXACTLY_ONE)
    kwargs.setdefault("completeness", Completeness.TOTAL)
    kwargs.setdefault("trust", Trust.PROPOSED)
    kwargs.setdefault("provenance", "contract")
    kwargs.setdefault("extraction_status", ExtractionStatus.OBSERVED)
    kwargs.setdefault("source_refs", list(spans()))
    return Descriptor(name=name, syntactic_type=type_, semantic_meaning=meaning, **kwargs)


def node(node_id, *, grants=(), **kwargs):
    kwargs.setdefault("extraction_status", ExtractionStatus.OBSERVED)
    kwargs.setdefault("source_refs", list(spans()))
    return Node(id=node_id, actor="actor", authority=Authority(holder="actor", grants=frozenset(grants)), **kwargs)


def edge(edge_id, type_, source, target, **kwargs):
    kwargs.setdefault("extraction_status", ExtractionStatus.OBSERVED)
    kwargs.setdefault("source_refs", list(spans()))
    return Edge(id=edge_id, type=type_, source=source, target=target, **kwargs)


def test_graph_reports_trust_and_authority_shortfalls() -> None:
    graph = Graph(
        nodes=[
            node("producer", outputs=[descriptor("value", "int", "a value", granting_authority="writer")]),
            node(
                "consumer",
                required_inputs=[
                    descriptor("value", "int", "a value", required_authority="judge", trust=Trust.VERIFIED)
                ],
            ),
        ],
        edges=[edge("value-edge", EdgeType.DATA, "producer", "consumer", source_output="value", target_input="value")],
    )

    assert [observation.subject for observation in graph.trust_shortfalls()] == ["value-edge"]
    assert [observation.subject for observation in graph.authority_shortfalls()] == ["value-edge"]


def test_graph_reports_ungranted_effect_and_missing_input() -> None:
    graph = Graph(
        nodes=[
            node(
                "writer",
                grants=(Effect.MUTATE,),
                side_effects=[SideEffect(target="state", effect=Effect.DECIDE, description="changes state")],
            ),
            node("reader", required_inputs=[descriptor("record", "event", "a required record")]),
        ]
    )

    assert [observation.subject for observation in graph.effects_without_authority()] == ["writer:decide:state"]
    assert [observation.subject for observation in graph.inputs_without_producer()] == ["reader.record"]


def test_graph_reports_type_mismatch_and_uses_declared_severity_basis() -> None:
    graph = Graph(
        nodes=[
            node("producer", outputs=[descriptor("value", "text", "text")]),
            node("consumer", required_inputs=[descriptor("value", "set[path]", "paths")]),
        ],
        edges=[edge("value-edge", EdgeType.DATA, "producer", "consumer", source_output="value", target_input="value")],
    )

    mismatch = graph.type_incompatible_edges()
    assert [observation.subject for observation in mismatch] == ["value-edge"]
    finding = Finding.from_observation(
        Predicate.PRODUCER_TYPE_UNSATISFIED,
        ContractBasis.UNSPECIFIED,
        "The local example does not declare this requirement.",
        mismatch[0],
        spans(),
    )
    assert finding.severity is Severity.CONTRACT_UNSPECIFIED
    assert finding.model_copy(update={"basis": ContractBasis.DECLARED}).severity is Severity.BROKEN


def test_graph_reports_unrecorded_invalidation_and_revision_mismatch() -> None:
    graph = Graph(
        nodes=[
            node("producer", outputs=[descriptor("value", "record", "a record", freshness=Freshness(version="old"))]),
            node(
                "consumer",
                required_inputs=[descriptor("value", "record", "a record", freshness=Freshness(version="new"))],
            ),
        ],
        edges=[
            edge("value-edge", EdgeType.DATA, "producer", "consumer", source_output="value", target_input="value"),
            edge("revoke-edge", EdgeType.INVALIDATES, "producer", "consumer"),
        ],
    )

    assert [observation.subject for observation in graph.unrecorded_invalidations()] == ["revoke-edge"]
    assert [observation.subject for observation in graph.revision_mismatches()] == ["value-edge"]


def test_severity_cannot_be_invented() -> None:
    payload = {
        "predicate": Predicate.TRUST_BELOW_REQUIREMENT,
        "basis": ContractBasis.UNSPECIFIED,
        "basis_evidence": "No declared requirement.",
        "subject": "edge",
        "expected": "verified",
        "observed": "proposed",
        "source_spans": spans(),
    }
    assert Finding.model_validate(payload).severity is Severity.CONTRACT_UNSPECIFIED
    with pytest.raises(ValidationError):
        Finding.model_validate({**payload, "severity": Severity.BROKEN})


def test_severity_taxonomy_is_closed() -> None:
    assert set(SEVERITY_BY_BASIS) == set(ContractBasis)
    assert set(SEVERITY_BY_BASIS.values()) == set(Severity)
    assert set(PREDICATES) == set(Predicate)
    assert all(PREDICATES[predicate].statement for predicate in Predicate)
    assert sorted(TRUST_ORDER, key=TRUST_ORDER.__getitem__) == [
        Trust.UNTRUSTED,
        Trust.PROPOSED,
        Trust.VERIFIED,
        Trust.AUTHORITATIVE,
    ]


def test_graph_refuses_an_incoherent_graph() -> None:
    with pytest.raises(ValidationError, match="unknown target node"):
        Graph(nodes=[node("a")], edges=[edge("edge", EdgeType.CONTROL, "a", "b")])
    with pytest.raises(ValidationError, match="absent from"):
        Graph(nodes=[node("a"), node("b")], edges=[edge("edge", EdgeType.DATA, "a", "b", source_output="missing")])
    with pytest.raises(ValidationError, match="duplicate node id"):
        Graph(nodes=[node("a"), node("a")])


def test_every_element_carries_its_provenance() -> None:
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
            source_spans=spans(),
        )
