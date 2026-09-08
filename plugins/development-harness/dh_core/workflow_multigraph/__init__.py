"""The graph IR: the layers of a workflow, and findings over them.

This package implements a three-layer split -- several graphs, each describable on its own and
drawn together only in :class:`~dh_core.workflow_multigraph.system.LayeredGraph` -- that is superseded design:
``docs/workflow-multigraph/findings/AMENDMENTS.md`` (entry A-4) records the move to one graph, described as
types and executed as instances, with no separate layer graphs. This package has not yet been
migrated to that shape; ``plugins/development-harness/ARCHITECTURE.md``'s "The work graph" section
is the current authority.

* :mod:`~dh_core.workflow_multigraph.ledger_layer` -- layer 1, task lifecycle: statuses and the commands
  between them, plus the projection each transition may name back to layer 3.
* :mod:`~dh_core.workflow_multigraph.work_layer` -- layer 2, the work graph: tasks, their concurrency and
  ordering, the bookend guarantee, and the extension operations layer 3 applies at runtime.
* :mod:`~dh_core.workflow_multigraph.model` -- layer 3, the workflow: the node record, the eight edge types,
  and the mechanical queries :data:`~dh_core.workflow_multigraph.findings.PREDICATES` names.
* :mod:`~dh_core.workflow_multigraph.decomposition` -- the grooming and architecture output layer 3 decomposes
  into layer 2, and the traceability queries between them.
* :mod:`~dh_core.workflow_multigraph.instructions` -- the instruction record a task carries out of
  decomposition, and :mod:`~dh_core.workflow_multigraph.decomposition_gate` -- the decomposition-exit gate that
  checks those instructions' referents and quotes against a repo checkout and a
  :class:`~dh_core.workflow_multigraph.work_layer.WorkGraph`.
* :mod:`~dh_core.workflow_multigraph.vocabulary`, :mod:`~dh_core.workflow_multigraph.descriptors`,
  :mod:`~dh_core.workflow_multigraph.node_parts` -- the facet and node-part types layer 3 (and, for the edge
  types and source spans, layer 2) draws from.
* :mod:`~dh_core.workflow_multigraph.findings` -- the finding record and the severity rule, layer-agnostic.
"""

from __future__ import annotations

from dh_core.workflow_multigraph.decomposition import DecompositionInput, DecompositionItem, DecompositionSourceKind
from dh_core.workflow_multigraph.decomposition_gate import (
    DecompositionGate,
    ReferentResolver,
    RepoResolver,
    RepoSourceReader,
    SourceReader,
)
from dh_core.workflow_multigraph.findings import (
    PREDICATES,
    SEVERITY_BY_BASIS,
    ContractBasis,
    Finding,
    Predicate,
    PredicateDefinition,
    Projection,
    Severity,
)
from dh_core.workflow_multigraph.instructions import Instruction, InstructionKind, Referent, ReferentKind
from dh_core.workflow_multigraph.layer import Layer
from dh_core.workflow_multigraph.ledger_layer import LedgerCommand, LedgerEdge, LedgerGraph, LedgerNode, LedgerStatus
from dh_core.workflow_multigraph.model import (
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
from dh_core.workflow_multigraph.system import LayeredGraph
from dh_core.workflow_multigraph.work_layer import (
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
    "DecompositionGate",
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
    "Instruction",
    "InstructionKind",
    "Layer",
    "LayeredGraph",
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
    "Referent",
    "ReferentKind",
    "ReferentResolver",
    "RepoResolver",
    "RepoSourceReader",
    "Severity",
    "SideEffect",
    "SourceReader",
    "SourceSpan",
    "Termination",
    "Trust",
    "WorkEdge",
    "WorkGraph",
    "WorkNode",
    "WorkNodeProvenance",
    "WorkflowGraph",
]
