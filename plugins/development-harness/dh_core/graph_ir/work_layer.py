"""Layer 2 -- the work graph: nodes are tasks; edges are the same typed relations layer 3 draws from.

``docs/graph-ir/ASSESSOR-CONTRACT.md`` ("The three layers"): "This layer says what may run
concurrently and what waits on what. Every layer-2 graph carries bookends: a review step, a
validate step, and a documentation-check step. They are structural, not optional decoration, and a
graph without them is malformed rather than merely lacking." And: "Layer 2 is the artifact layer 3
produces and mutates. It is not static: layer 3 extends it while work is in flight" -- a task split
before it runs because it would exceed one agent's context window, or a finding inserted mid-work
that the decomposition did not account for, both "with its own edges -- not appended to a task's
notes and not deferred to a later plan."

This module makes three things unconstructible rather than merely checkable:

* a bookend-typed node without a review/validate/documentation-check semantics is impossible --
  :class:`BookendKind` is a closed three-member enum, not free text;
* a node with :attr:`WorkNode.provenance` other than :attr:`WorkNodeProvenance.PLANNED` cannot be
  built without naming :attr:`WorkNode.inserted_by` and :attr:`WorkNode.inserted_reason`
  (:meth:`WorkNode.check_extension_fields`);
* a :class:`WorkGraph` cannot hold a non-planned node that no :class:`ExtensionOperation` produced,
  nor an operation whose product disagrees with its own node's provenance stamp
  (:meth:`WorkGraph.check_extension_consistency`) -- so "which nodes were planned and which were
  inserted, by what, and why" is answerable by reading fields, not by trusting a label.

What stays a query rather than a constructor refusal, per this package's standing rule that the IR
must hold an *unsound* graph: whether a graph is actually missing a bookend
(:meth:`WorkGraph.missing_bookends`), and whether a planned node traces back to nothing in the
decomposition input (:mod:`dh_core.graph_ir.decomposition`) -- both are properties of a graph that
may be malformed, and the contract asks that a malformed graph be representable so its
malformedness can be reported.
"""

from __future__ import annotations

from collections import deque
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dh_core.graph_ir.descriptors import SourceSpan
from dh_core.graph_ir.layer import Layer
from dh_core.graph_ir.model import Observation
from dh_core.graph_ir.vocabulary import EdgeType, ExtractionStatus


class BookendKind(StrEnum):
    """The three structural bookends every layer-2 graph must carry."""

    REVIEW = "review"
    VALIDATE = "validate"
    DOCUMENTATION_CHECK = "documentation-check"


class WorkNodeProvenance(StrEnum):
    """How a layer-2 node came to be in the graph -- planned up front, or added while work ran."""

    PLANNED = "planned"
    """Produced by the up-front decomposition of the grooming and architecture output."""

    SPLIT = "split"
    """A task that would exceed one agent's context window, split by layer 3 before it ran."""

    INSERTED = "inserted"
    """A finding discovered mid-work that the original decomposition did not account for."""


class ExtensionKind(StrEnum):
    """The two ways layer 3 mutates layer 2 while work is in flight."""

    SPLIT = "split"
    INSERT = "insert"


class ExtensionOperation(BaseModel):
    """One layer-3 mutation of the layer-2 graph, with its own provenance.

    A later reader answers "which nodes were planned and which were inserted, by what, and why" by
    reading :attr:`performed_by` and :attr:`reason` here, cross-checked against the node it names in
    :attr:`produces` -- :meth:`WorkGraph.check_extension_consistency` refuses a graph where the two
    disagree.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    kind: ExtensionKind
    performed_by: str = Field(min_length=1, description="The layer-3 (workflow) node id that performed this operation.")
    reason: str = Field(min_length=1)
    replaces: tuple[str, ...] = Field(
        default_factory=tuple, description="Node ids this operation superseded, e.g. the task a split divided."
    )
    produces: tuple[str, ...] = Field(min_length=1, description="Node ids this operation introduced into the graph.")
    source_refs: list[SourceSpan] = Field(min_length=1)
    extraction_status: ExtractionStatus


class WorkNode(BaseModel):
    """One layer-2 node: a task in the work graph layer 3 decomposes into and extends."""

    layer: Literal[Layer.WORK] = Layer.WORK
    id: str = Field(min_length=1)
    task_ref: str = Field(min_length=1, description="The SAM Task.id (sam_schema.core.models.Task) this node is.")
    bookend: BookendKind | None = Field(default=None, description="Which structural bookend this node is, if any.")
    conflict_group: str | None = Field(
        default=None, description="Mutual-exclusion tag; mirrors ledger_spec.py's tasks.conflict_group."
    )
    provenance: WorkNodeProvenance = WorkNodeProvenance.PLANNED
    inserted_by: str | None = Field(
        default=None, description="Layer-3 node id that performed the extension producing this node."
    )
    inserted_reason: str = Field(default="", description="Why layer 3 extended the graph with this node.")
    decomposition_source: str | None = Field(
        default=None, description="DecompositionItem.id (dh_core.graph_ir.decomposition) this node traces back to."
    )
    source_refs: list[SourceSpan] = Field(min_length=1)
    extraction_status: ExtractionStatus

    @model_validator(mode="after")
    def check_extension_fields(self) -> WorkNode:
        """Refuse a non-planned node that does not name who extended the graph and why.

        Returns:
            The validated node.

        Raises:
            ValueError: If ``provenance`` is not :attr:`WorkNodeProvenance.PLANNED` and either
                ``inserted_by`` or ``inserted_reason`` is missing.
        """
        if self.provenance is not WorkNodeProvenance.PLANNED:
            if self.inserted_by is None:
                raise ValueError(f"node {self.id!r} has provenance {self.provenance.value!r} but no inserted_by")
            if not self.inserted_reason:
                raise ValueError(f"node {self.id!r} has provenance {self.provenance.value!r} but no inserted_reason")
        return self


class WorkEdge(BaseModel):
    """One typed relation between two layer-2 nodes, drawn from the same ``EdgeType`` as layer 3."""

    layer: Literal[Layer.WORK] = Layer.WORK
    id: str = Field(min_length=1)
    type: EdgeType
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    resource: str | None = Field(default=None, description="Named resource a STATE edge holds mutual exclusion over.")
    guard: str | None = None
    source_refs: list[SourceSpan] = Field(min_length=1)
    extraction_status: ExtractionStatus


class WorkGraph(BaseModel):
    """A recovered layer-2 graph: tasks, their ordering and exclusion, and the extensions applied.

    Construction enforces reference integrity, as :class:`~dh_core.graph_ir.model.Graph` does, plus
    the extension-consistency rule described in the module docstring. What it does *not* refuse is a
    graph missing a bookend -- that is a property :meth:`missing_bookends` reports, because a
    malformed graph must still be representable so a check can find the malformation.
    """

    layer: Literal[Layer.WORK] = Layer.WORK
    nodes: list[WorkNode] = Field(default_factory=list)
    edges: list[WorkEdge] = Field(default_factory=list)
    extensions: list[ExtensionOperation] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_reference_integrity(self) -> WorkGraph:
        """Reject a graph whose own references do not resolve.

        Returns:
            The validated graph.
        """
        by_id: dict[str, WorkNode] = {}
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

    @model_validator(mode="after")
    def check_extension_consistency(self) -> WorkGraph:
        """Reject a graph where a node's provenance and the operations that produced it disagree.

        Every non-planned node must be named in exactly the extension whose ``performed_by`` equals
        the node's ``inserted_by``, and whose ``kind`` matches the node's provenance. Every planned
        node must be named by no operation at all.

        Returns:
            The validated graph.

        Raises:
            ValueError: If an operation names an unknown node, a node's provenance does not match
                the operation kind that produced it, the two disagree on who performed it, or a
                non-planned node is produced by no operation.
        """
        by_id = {node.id: node for node in self.nodes}
        expected_provenance = {
            ExtensionKind.SPLIT: WorkNodeProvenance.SPLIT,
            ExtensionKind.INSERT: WorkNodeProvenance.INSERTED,
        }
        produced_by: dict[str, ExtensionOperation] = {}
        for operation in self.extensions:
            for node_id in operation.produces:
                if node_id not in by_id:
                    raise ValueError(f"extension {operation.id!r} produces unknown node {node_id!r}")
                node = by_id[node_id]
                want = expected_provenance[operation.kind]
                if node.provenance is not want:
                    raise ValueError(
                        f"node {node_id!r} produced by {operation.kind.value} extension {operation.id!r} "
                        f"must carry provenance {want.value!r}, got {node.provenance.value!r}"
                    )
                if node.inserted_by != operation.performed_by:
                    raise ValueError(
                        f"node {node_id!r} names inserted_by {node.inserted_by!r}, but extension "
                        f"{operation.id!r} was performed_by {operation.performed_by!r}"
                    )
                produced_by[node_id] = operation
        for node in self.nodes:
            if node.provenance is not WorkNodeProvenance.PLANNED and node.id not in produced_by:
                raise ValueError(
                    f"node {node.id!r} has provenance {node.provenance.value!r} but no extension produces it"
                )
        return self

    def node(self, node_id: str) -> WorkNode:
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

    # -- concurrency and ordering --------------------------------------------------

    def blocked_on(self, node_id: str) -> set[str]:
        """Return the ids of nodes that must run before ``node_id``, per direct CONTROL edges.

        Args:
            node_id: The node to ask about.

        Returns:
            Direct CONTROL predecessors of ``node_id``.
        """
        return {edge.source for edge in self.edges if edge.type is EdgeType.CONTROL and edge.target == node_id}

    def _control_reaches(self, source: str, target: str) -> bool:
        """Return whether a CONTROL path orders ``source`` before ``target``."""
        if source == target:
            return True
        seen = {source}
        queue = deque([source])
        while queue:
            current = queue.popleft()
            for edge in self.edges:
                if edge.type is EdgeType.CONTROL and edge.source == current and edge.target not in seen:
                    if edge.target == target:
                        return True
                    seen.add(edge.target)
                    queue.append(edge.target)
        return False

    def _resources_of(self, node_id: str) -> set[str]:
        """Return the named STATE resources ``node_id`` holds mutual exclusion over."""
        return {
            edge.resource
            for edge in self.edges
            if edge.type is EdgeType.STATE and edge.resource is not None and node_id in {edge.source, edge.target}
        }

    def may_run_concurrently(self, a: str, b: str) -> bool:
        """Return whether nothing in the graph forces an order or an exclusion between ``a`` and ``b``.

        Args:
            a: A node id.
            b: A node id.

        Returns:
            False when a CONTROL path orders one before the other, or both hold the same
            ``conflict_group`` or a shared STATE resource; True otherwise.
        """
        if a == b:
            return False
        if self._control_reaches(a, b) or self._control_reaches(b, a):
            return False
        node_a, node_b = self.node(a), self.node(b)
        if node_a.conflict_group is not None and node_a.conflict_group == node_b.conflict_group:
            return False
        return self._resources_of(a).isdisjoint(self._resources_of(b))

    # -- the bookend guarantee --------------------------------------------------

    def missing_bookends(self) -> list[Observation]:
        """Find bookend kinds no node in this graph declares.

        Returns:
            One observation per missing bookend; empty when review, validate and
            documentation-check are all present.
        """
        present = {node.bookend for node in self.nodes if node.bookend is not None}
        return [
            Observation(
                subject=f"work-graph.{kind.value}",
                expected=f"a node declaring bookend={kind.value!r}",
                observed="no node in this graph declares this bookend",
            )
            for kind in BookendKind
            if kind not in present
        ]

    # -- extension provenance --------------------------------------------------

    def provenance_of(self, node_id: str) -> Observation:
        """Answer, for one node, whether it was planned or how, by what, and why it was added.

        Args:
            node_id: The node to ask about.

        Returns:
            An observation whose ``observed`` states the provenance in full.

        Raises:
            KeyError: If ``node_id`` names no node, or a non-planned node names no producing
                extension (refused at construction, so this signals a graph built by other means).
        """
        node = self.node(node_id)
        if node.provenance is WorkNodeProvenance.PLANNED:
            return Observation(
                subject=node.id, expected="node provenance", observed="planned up front by decomposition"
            )
        operation = next(op for op in self.extensions if node.id in op.produces)
        return Observation(
            subject=node.id,
            expected="node provenance",
            observed=f"{node.provenance.value} by {operation.performed_by!r} ({operation.kind.value}): {operation.reason}",
        )
