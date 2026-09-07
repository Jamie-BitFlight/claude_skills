"""Layer 1 -- task lifecycle: nodes are statuses, edges are the commands that move between them.

One uniform machine, instantiated per task, tracks where each task's progress is:
``dh_core/ledger_spec.py:TRANSITIONS`` is that machine. This module gives it a graph shape distinct
from :mod:`dh_core.graph_ir.model` (layer 3): a :class:`LedgerNode` is a bare status, not a process
step, and it carries no actor.

This module's premise -- a separate layer-1 graph, projected from layer 3 -- is superseded design.
Per ``plugins/development-harness/ARCHITECTURE.md``, "The work graph" § "What belongs to a node":
"Execution state -- the lifecycle a node runs through while working -- is a property of the node,
not a graph of its own. `dh_core/ledger_spec.py`'s transitions are that lifecycle, and a status is
not a thing on the path from grooming to closure." ``docs/graph-ir/findings/AMENDMENTS.md`` (entry
A-4) records this explicitly: no projection derives the ledger's transitions from a work graph, and
a criterion asking for one is ill-posed. :attr:`LedgerEdge.projects_from` and
:meth:`LedgerGraph.edges_without_workflow_origin`, joined with the layer-3 graph
(:mod:`dh_core.graph_ir.system`), implement the now-superseded projection relationship; this module
has not yet been migrated to the one-graph shape.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from dh_core.graph_ir.descriptors import SourceSpan
from dh_core.graph_ir.layer import Layer
from dh_core.graph_ir.model import Observation
from dh_core.graph_ir.vocabulary import ExtractionStatus


class LedgerStatus(StrEnum):
    """The seven task statuses; layer 1's nodes. Mirrors ``dh_core.ledger_spec.Status``.

    Kept as this module's own enum rather than importing ``ledger_spec.Status`` directly: the IR
    models what the contract states the layer *is*, and ``ledger_spec.py`` is one concrete
    implementation of it, not the layer's definition.
    """

    NOT_STARTED = "not-started"
    IN_PROGRESS = "in-progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    DEFERRED = "deferred"
    SKIPPED = "skipped"
    FAILED = "failed"


class LedgerCommand(StrEnum):
    """The six commands that move a task between statuses; layer 1's edges."""

    DISPATCH = "dispatch"
    FINISH = "finish"
    ACCEPT = "accept"
    RECLAIM = "reclaim"
    STATE = "state"
    SETTLE = "settle"


class LedgerNode(BaseModel):
    """One status a task may hold. Layer 1's node: a status, never a process step."""

    layer: Literal[Layer.LEDGER] = Layer.LEDGER
    id: str = Field(min_length=1)
    status: LedgerStatus
    source_refs: list[SourceSpan] = Field(min_length=1)
    extraction_status: ExtractionStatus


class LedgerEdge(BaseModel):
    """One command instance moving one task between two statuses. Layer 1's edge."""

    layer: Literal[Layer.LEDGER] = Layer.LEDGER
    id: str = Field(min_length=1)
    command: LedgerCommand
    source: str = Field(min_length=1, description="LedgerNode id this transition leaves.")
    target: str = Field(min_length=1, description="LedgerNode id this transition enters.")
    task_ref: str = Field(min_length=1, description="The layer-2 task (WorkNode.id) this transition instance is for.")
    projects_from: str | None = Field(
        default=None,
        description=(
            "Layer-3 (workflow) node id this transition projects. The contract: discarding the actor "
            "onto which this projects is exactly how authority is lost."
        ),
    )
    guard: str | None = None
    source_refs: list[SourceSpan] = Field(min_length=1)
    extraction_status: ExtractionStatus


class LedgerGraph(BaseModel):
    """A recovered layer-1 graph: the status machine plus the transition instances observed for it.

    Construction enforces reference integrity only, matching
    :class:`~dh_core.graph_ir.model.Graph`: unique node and edge ids, and every edge endpoint
    resolving. Whether every edge has a layer-3 origin, and whether that origin exists, are
    questions for the queries below and for :class:`dh_core.graph_ir.system.LayeredGraph`
    respectively -- an edge with no origin is a well-formed graph that has lost its authority, not
    an incoherent one, and the contract requires the IR to be able to hold that.
    """

    layer: Literal[Layer.LEDGER] = Layer.LEDGER
    nodes: list[LedgerNode] = Field(default_factory=list)
    edges: list[LedgerEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_reference_integrity(self) -> LedgerGraph:
        """Reject a graph whose own references do not resolve.

        Returns:
            The validated graph.
        """
        by_id: dict[str, LedgerNode] = {}
        for node in self.nodes:
            if node.id in by_id:
                raise ValueError(f"duplicate node id {node.id!r}")
            by_id[node.id] = node
        seen: set[str] = set()
        for edge in self.edges:
            if edge.id in seen:
                raise ValueError(f"duplicate edge id {edge.id!r}")
            seen.add(edge.id)
            for role, ref in (("source", edge.source), ("target", edge.target)):
                if ref not in by_id:
                    raise ValueError(f"edge {edge.id!r} names unknown {role} node {ref!r}")
        return self

    def node(self, node_id: str) -> LedgerNode:
        """Return the node with this id, raising ``KeyError`` when none carries it.

        Args:
            node_id: The id to resolve.

        Returns:
            The node.
        """
        for node in self.nodes:
            if node.id == node_id:
                return node
        raise KeyError(node_id)

    def edges_without_workflow_origin(self) -> list[Observation]:
        """Find layer-1 edges that name no layer-3 node as their projection origin.

        This is the falsified predicate the projection relationship exists to make checkable: a
        transition with no ``projects_from`` is a command with the actor already discarded, before
        even asking whether the named origin resolves.

        Returns:
            One observation per transition instance with no stated origin.
        """
        return [
            Observation(
                subject=edge.id,
                expected="a layer-3 (workflow) node id this transition projects",
                observed="projects_from is unset",
            )
            for edge in self.edges
            if edge.projects_from is None
        ]

    @classmethod
    def canonical_machine(cls, edges: list[LedgerEdge], source_refs: list[SourceSpan]) -> LedgerGraph:
        """Build the graph with the seven canonical statuses as nodes, plus the given transitions.

        "One uniform machine, instantiated per task": every ``LedgerGraph`` shares the same seven
        status nodes, so this is the constructor most callers want rather than repeating them.

        Args:
            edges: The transition instances to attach to the seven-status machine.
            source_refs: Provenance for each of the seven status nodes.

        Returns:
            The assembled ledger graph.
        """
        nodes = [
            LedgerNode(
                id=status.value, status=status, source_refs=source_refs, extraction_status=ExtractionStatus.OBSERVED
            )
            for status in LedgerStatus
        ]
        return cls(nodes=nodes, edges=edges)
