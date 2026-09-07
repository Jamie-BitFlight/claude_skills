"""The layer-3 (workflow) graph: the node record, the eight edge types, and the queries over them.

The system under assessment is a typed, hierarchical, directed multigraph
(``docs/graph-ir/ASSESSOR-CONTRACT.md``), and that multigraph is three layers, not one. This module
holds **layer 3**, the workflow: nodes are process steps with an actor, a guard and source refs
into a ``SKILL.md`` -- the contract's node record is shaped for this layer specifically. Layer 1
(task lifecycle) lives in :mod:`dh_core.graph_ir.ledger_layer`; layer 2 (the work graph) lives in
:mod:`dh_core.graph_ir.work_layer`; the three tied together live in :mod:`dh_core.graph_ir.system`.
One pair of nodes may carry several edges at once, and collapsing them into a single ``then`` arrow
is what hides the defects worth finding.

Two rules shape it. **The IR must hold a broken system**: report validation puts model fidelity
first, and a sound graph proves nothing if the extractor silently repaired an ambiguity. So the
models refuse only what makes the *graph* incoherent -- an edge naming a node that does not exist,
or a descriptor its endpoint does not declare. Unsoundness is reported by the queries, never by a
constructor. **Every claim is anchored**: :class:`Node` and :class:`Edge` each require a
``SourceSpan`` and an ``ExtractionStatus`` (:mod:`dh_core.graph_ir.descriptors`,
:mod:`dh_core.graph_ir.vocabulary`), so a fidelity reviewer can ask of any element which source it
came from and whether the extractor observed or supplied it. Queries return :class:`Observation`
records, not findings -- turning one into a finding needs the severity rule, which must know
whether the predicate was declared (:mod:`dh_core.graph_ir.findings`).

The vocabulary and descriptor types that used to live in this module -- ``EdgeType``, ``Effect``,
``Cardinality``, ``Trust``, ``Completeness``, ``ExtractionStatus``, ``SourceSpan``, ``Freshness``,
``Descriptor``, ``Authority``, ``SideEffect``, ``ErrorRoute``, ``EvidenceRequirement``,
``Operation``, ``Termination`` -- moved to :mod:`dh_core.graph_ir.vocabulary`,
:mod:`dh_core.graph_ir.descriptors` and :mod:`dh_core.graph_ir.node_parts` as the package grew a
second and third layer, and are re-exported here so existing imports of ``dh_core.graph_ir.model``
keep working unchanged.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterator
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dh_core.graph_ir.descriptors import Descriptor, Freshness, SourceSpan
from dh_core.graph_ir.layer import Layer
from dh_core.graph_ir.node_parts import Authority, ErrorRoute, EvidenceRequirement, Operation, SideEffect, Termination
from dh_core.graph_ir.vocabulary import (
    TRUST_ORDER,
    Cardinality,
    Completeness,
    EdgeType,
    Effect,
    ExtractionStatus,
    Trust,
)

__all__ = [
    "TRUST_ORDER",
    "Authority",
    "Cardinality",
    "Completeness",
    "Descriptor",
    "Edge",
    "EdgeType",
    "Effect",
    "ErrorRoute",
    "EvidenceRequirement",
    "ExtractionStatus",
    "Freshness",
    "Graph",
    "Node",
    "Observation",
    "Operation",
    "SideEffect",
    "SourceSpan",
    "Termination",
    "Trust",
    "WorkflowGraph",
]


class Node(BaseModel):
    """One node of the layer-3 (workflow) graph, as the contract's node record states it."""

    layer: Literal[Layer.WORKFLOW] = Layer.WORKFLOW
    id: str = Field(min_length=1)
    source_refs: list[SourceSpan] = Field(min_length=1)
    actor: str = Field(min_length=1)
    activation_guard: str | None = None
    required_inputs: list[Descriptor] = Field(default_factory=list)
    optional_inputs: list[Descriptor] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    operation: Operation = Field(default_factory=Operation)
    outputs: list[Descriptor] = Field(default_factory=list)
    postconditions: list[str] = Field(default_factory=list)
    invariants: list[str] = Field(default_factory=list)
    side_effects: list[SideEffect] = Field(default_factory=list)
    error_routes: list[ErrorRoute] = Field(default_factory=list)
    termination: Termination = Field(default_factory=Termination)
    evidence_requirements: list[EvidenceRequirement] = Field(default_factory=list)
    authority: Authority
    subgraph_ref: str | None = None
    extraction_status: ExtractionStatus

    def output(self, name: str) -> Descriptor | None:
        """Return the named output descriptor, or None when the node declares no such output.

        Args:
            name: Descriptor name.

        Returns:
            The matching output descriptor.
        """
        return next((d for d in self.outputs if d.name == name), None)

    def input(self, name: str) -> Descriptor | None:
        """Return the named required or optional input, or None when the node declares no such input.

        Args:
            name: Descriptor name.

        Returns:
            The matching input descriptor.
        """
        return next((d for d in [*self.required_inputs, *self.optional_inputs] if d.name == name), None)


class Edge(BaseModel):
    """One typed relation between two layer-3 nodes."""

    layer: Literal[Layer.WORKFLOW] = Layer.WORKFLOW
    id: str = Field(min_length=1)
    type: EdgeType
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    source_output: str | None = Field(default=None, description="Output descriptor on the source, when it carries one.")
    target_input: str | None = Field(default=None, description="Input descriptor on the target, when it fills one.")
    guard: str | None = None
    recorded_by: list[str] = Field(
        default_factory=list, description="What records this relation happened -- events, artifacts."
    )
    source_refs: list[SourceSpan] = Field(min_length=1)
    extraction_status: ExtractionStatus


class Observation(BaseModel):
    """One thing a graph query found, phrased as expected against observed."""

    model_config = ConfigDict(frozen=True)

    subject: str = Field(min_length=1, description="Node id, edge id, or 'node.descriptor'.")
    expected: str = Field(min_length=1)
    observed: str = Field(min_length=1)


class Graph(BaseModel):
    """A recovered layer-3 (workflow) graph, with the mechanical queries the contract names.

    Construction enforces reference integrity only: unique node and edge ids, every endpoint
    resolving, and every named descriptor declared by the endpoint said to carry it. Nothing else
    is refused -- an unsound system must be representable for its unsoundness to be reported.
    """

    layer: Literal[Layer.WORKFLOW] = Layer.WORKFLOW
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_reference_integrity(self) -> Graph:
        """Reject a graph whose own references do not resolve.

        Returns:
            The validated graph.
        """
        by_id: dict[str, Node] = {}
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
            if edge.source_output is not None and by_id[edge.source].output(edge.source_output) is None:
                raise ValueError(f"edge {edge.id!r} names output {edge.source_output!r} absent from {edge.source!r}")
            if edge.target_input is not None and by_id[edge.target].input(edge.target_input) is None:
                raise ValueError(f"edge {edge.id!r} names input {edge.target_input!r} absent from {edge.target!r}")
        return self

    def node(self, node_id: str) -> Node:
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

    def _pairs(self) -> Iterator[tuple[Edge, Descriptor, Descriptor]]:
        """Yield each edge that joins a declared output to a declared input, with both descriptors."""
        for edge in self.edges:
            if edge.source_output is None or edge.target_input is None:
                continue
            produced = self.node(edge.source).output(edge.source_output)
            consumed = self.node(edge.target).input(edge.target_input)
            if produced is not None and consumed is not None:
                yield edge, produced, consumed

    # -- the contract's falsified predicates, as queries -------------------

    def inputs_without_producer(self) -> list[Observation]:
        """Find required inputs that no incoming edge fills.

        Returns:
            One observation per unfilled required input.
        """
        filled = {(e.target, e.target_input) for e in self.edges if e.target_input is not None}
        return [
            Observation(
                subject=f"{node.id}.{needed.name}",
                expected=f"an edge supplying {needed.semantic_meaning!r}",
                observed="no incoming edge fills this required input",
            )
            for node in self.nodes
            for needed in node.required_inputs
            if (node.id, needed.name) not in filled
        ]

    def type_incompatible_edges(self) -> list[Observation]:
        """Find edges whose producer type does not satisfy the consumer's declared input type.

        Returns:
            One observation per incompatible edge.
        """
        return [
            Observation(
                subject=edge.id,
                expected=f"type {consumed.syntactic_type!r} ({consumed.semantic_meaning})",
                observed=f"{edge.source}.{produced.name} supplies {produced.syntactic_type!r}",
            )
            for edge, produced, consumed in self._pairs()
            if not produced.satisfies_type_of(consumed)
        ]

    def trust_shortfalls(self) -> list[Observation]:
        """Find edges where the supplied trust classification is below the required one.

        Returns:
            One observation per shortfall.
        """
        return [
            Observation(
                subject=edge.id,
                expected=f"{edge.target}.{consumed.name} requires {consumed.trust.value}",
                observed=f"{edge.source}.{produced.name} supplies {produced.trust.value}",
            )
            for edge, produced, consumed in self._pairs()
            if TRUST_ORDER[produced.trust] < TRUST_ORDER[consumed.trust]
        ]

    def authority_shortfalls(self) -> list[Observation]:
        """Find edges whose producer holds an authority other than the one the consumer requires.

        Returns:
            One observation per shortfall.
        """
        return [
            Observation(
                subject=edge.id,
                expected=f"{edge.target}.{consumed.name} requires authority {consumed.required_authority!r}",
                observed=f"{edge.source}.{produced.name} was produced under {produced.granting_authority!r}",
            )
            for edge, produced, consumed in self._pairs()
            if consumed.required_authority is not None and produced.granting_authority != consumed.required_authority
        ]

    def effects_without_authority(self) -> list[Observation]:
        """Find side effects a node's own authority does not grant it.

        Returns:
            One observation per ungranted effect.
        """
        return [
            Observation(
                subject=f"{node.id}:{effect.effect.value}:{effect.target}",
                expected=f"{node.authority.holder!r} granted {effect.effect.value} over {effect.target}",
                observed=f"grants are {sorted(e.value for e in node.authority.grants)}",
            )
            for node in self.nodes
            for effect in node.side_effects
            if effect.effect not in node.authority.grants
        ]

    def unrecorded_invalidations(self) -> list[Observation]:
        """Find INVALIDATES edges that nothing records.

        Returns:
            One observation per revocation no record accounts for.
        """
        return [
            Observation(
                subject=edge.id,
                expected=f"a record accounting for {edge.source} revoking {edge.target}",
                observed="recorded_by is empty",
            )
            for edge in self.edges
            if edge.type is EdgeType.INVALIDATES and not edge.recorded_by
        ]

    def unchecked_stale_inputs(self) -> list[Observation]:
        """Find required inputs that may be stale with no freshness check.

        Returns:
            One observation per unchecked input.
        """
        return [
            Observation(
                subject=f"{node.id}.{needed.name}",
                expected="a freshness check, or a value that cannot be stale",
                observed="may_be_stale with no freshness_check",
            )
            for node in self.nodes
            for needed in node.required_inputs
            if needed.freshness.may_be_stale and not needed.freshness.freshness_check
        ]

    def revision_mismatches(self) -> list[Observation]:
        """Find edges joining two descriptors that name different revisions.

        Returns:
            One observation per mismatch.
        """
        return [
            Observation(
                subject=edge.id,
                expected=f"revision {consumed.freshness.version!r}",
                observed=f"revision {produced.freshness.version!r}",
            )
            for edge, produced, consumed in self._pairs()
            if None not in {produced.freshness.version, consumed.freshness.version}
            and produced.freshness.version != consumed.freshness.version
        ]

    def unrouted_failures(self) -> list[Observation]:
        """Find failure signals with no consuming edge.

        Returns:
            One observation per unrouted signal.
        """
        routed = {(e.source, e.source_output) for e in self.edges if e.type in {EdgeType.ERROR, EdgeType.RECOVERY}}
        return [
            Observation(
                subject=f"{node.id}.{route.signal}",
                expected="an ERROR or RECOVERY edge consuming this signal",
                observed="handled_by is unset and no edge carries it",
            )
            for node in self.nodes
            for route in node.error_routes
            if route.handled_by is None and (node.id, route.signal) not in routed
        ]

    def unreachable_nodes(self, entry: str) -> list[Observation]:
        """Find nodes no CONTROL path reaches from the ``entry`` node.

        Returns:
            One observation per unreachable node.
        """
        seen = {entry}
        queue = deque([entry])
        while queue:
            current = queue.popleft()
            for edge in self.edges:
                if edge.type is EdgeType.CONTROL and edge.source == current and edge.target not in seen:
                    seen.add(edge.target)
                    queue.append(edge.target)
        return [
            Observation(subject=node.id, expected=f"a CONTROL path from {entry!r}", observed="unreachable")
            for node in self.nodes
            if node.id not in seen
        ]


WorkflowGraph = Graph
"""Alias naming :class:`Graph` by its layer, for code that assembles all three layers together."""
