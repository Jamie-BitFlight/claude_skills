"""The graph IR: three layers of a workflow, and findings over them.

``docs/graph-ir/ASSESSOR-CONTRACT.md`` ("The three layers") is the authority: the system is three
graphs, each describable on its own and drawn together only in :class:`~dh_core.graph_ir.system.ThreeLayerGraph`.

* :mod:`~dh_core.graph_ir.ledger_layer` -- layer 1, task lifecycle: statuses and the commands
  between them, plus the projection each transition may name back to layer 3.
* :mod:`~dh_core.graph_ir.work_layer` -- layer 2, the work graph: tasks, their concurrency and
  ordering, the bookend guarantee, and the extension operations layer 3 applies at runtime.
* :mod:`~dh_core.graph_ir.model` -- layer 3, the workflow: the node record, the eight edge types,
  and the mechanical queries the contract's falsified-predicate list names.
* :mod:`~dh_core.graph_ir.decomposition` -- the grooming and architecture output layer 3 decomposes
  into layer 2, and the traceability queries between the two.
* :mod:`~dh_core.graph_ir.vocabulary`, :mod:`~dh_core.graph_ir.descriptors`,
  :mod:`~dh_core.graph_ir.node_parts` -- the facet and node-part types layer 3 (and, for the edge
  types and source spans, layer 2) draws from.
* :mod:`~dh_core.graph_ir.findings` -- the finding record and the severity rule, layer-agnostic.
"""

from __future__ import annotations

from dh_core.graph_ir.decomposition import DecompositionInput, DecompositionItem, DecompositionSourceKind
from dh_core.graph_ir.findings import (
    PREDICATES,
    SEVERITY_BY_BASIS,
    ContractBasis,
    Finding,
    Predicate,
    PredicateDefinition,
    Projection,
    Severity,
)
from dh_core.graph_ir.layer import Layer
from dh_core.graph_ir.ledger_layer import LedgerCommand, LedgerEdge, LedgerGraph, LedgerNode, LedgerStatus
from dh_core.graph_ir.model import (
    TRUST_ORDER,
    Authority,
    Cardinality,
    Completeness,
    Descriptor,
    Edge,
    EdgeType,
    Effect,
    ErrorRoute,
    EvidenceRequirement,
    ExtractionStatus,
    Freshness,
    Graph,
    Node,
    Observation,
    Operation,
    SideEffect,
    SourceSpan,
    Termination,
    Trust,
    WorkflowGraph,
)
from dh_core.graph_ir.system import ThreeLayerGraph
from dh_core.graph_ir.work_layer import (
    BookendKind,
    ExtensionKind,
    ExtensionOperation,
    WorkEdge,
    WorkGraph,
    WorkNode,
    WorkNodeProvenance,
)

__all__ = [
    "PREDICATES",
    "SEVERITY_BY_BASIS",
    "TRUST_ORDER",
    "Authority",
    "BookendKind",
    "Cardinality",
    "Completeness",
    "ContractBasis",
    "DecompositionInput",
    "DecompositionItem",
    "DecompositionSourceKind",
    "Descriptor",
    "Edge",
    "EdgeType",
    "Effect",
    "ErrorRoute",
    "EvidenceRequirement",
    "ExtensionKind",
    "ExtensionOperation",
    "ExtractionStatus",
    "Finding",
    "Freshness",
    "Graph",
    "Layer",
    "LedgerCommand",
    "LedgerEdge",
    "LedgerGraph",
    "LedgerNode",
    "LedgerStatus",
    "Node",
    "Observation",
    "Operation",
    "Predicate",
    "PredicateDefinition",
    "Projection",
    "Severity",
    "SideEffect",
    "SourceSpan",
    "Termination",
    "ThreeLayerGraph",
    "Trust",
    "WorkEdge",
    "WorkGraph",
    "WorkNode",
    "WorkNodeProvenance",
    "WorkflowGraph",
]
