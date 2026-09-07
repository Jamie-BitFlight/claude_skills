"""The system: the layers bound together, and the checks that only make sense across them.

``docs/graph-ir/ASSESSOR-CONTRACT.md`` ("The layers"): "The system is several graphs. Each is
describable on its own; the system is only drawn when all of them exist together. A representation
that carries one of them and calls itself the model of the system is the flattening this contract
exists to prevent." :class:`LayeredGraph` is that "all of them exist together" object: it holds a
:class:`~dh_core.graph_ir.ledger_layer.LedgerGraph`, a :class:`~dh_core.graph_ir.work_layer.WorkGraph`,
a :class:`~dh_core.graph_ir.model.Graph` (workflow, layer 3), and the
:class:`~dh_core.graph_ir.decomposition.DecompositionInput` layer 3 consumed -- and nothing more. It
adds no new node or edge type; it only makes cross-layer references resolvable.

Some checks belong here rather than on a single layer, because each is a claim one layer's element
makes about a *different* layer's graph, and only an object holding both can tell whether it
resolves: :meth:`unresolved_projections` (a ledger edge's ``projects_from`` against the workflow
graph), :meth:`unresolved_task_refs` (a ledger edge's ``task_ref`` against the work graph), and
:meth:`unresolved_extension_performers` (a work-graph extension's ``performed_by`` against the
workflow graph). Every other query is a single layer's own and is exposed here only for
convenience, so a caller that already has the whole system does not have to reach into ``.ledger``
or ``.work`` by hand.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from dh_core.graph_ir.decomposition import DecompositionInput
from dh_core.graph_ir.ledger_layer import LedgerGraph
from dh_core.graph_ir.model import Graph, Observation
from dh_core.graph_ir.work_layer import WorkGraph


class LayeredGraph(BaseModel):
    """The ledger, work and workflow graphs together.

    Layer 1 (ledger), layer 2 (work) and layer 3 (workflow), plus the decomposition input layer 3
    consumed to produce and extend layer 2.
    """

    ledger: LedgerGraph
    work: WorkGraph
    workflow: Graph
    decomposition: DecompositionInput = Field(default_factory=DecompositionInput)

    def unresolved_projections(self) -> list[Observation]:
        """Find layer-1 edges whose ``projects_from`` names no node in the workflow graph.

        Complements :meth:`~dh_core.graph_ir.ledger_layer.LedgerGraph.edges_without_workflow_origin`,
        which finds edges with no stated origin at all; this finds edges that state one and it does
        not resolve. Neither case is refused at construction -- a ledger edge can be built and
        checked without the workflow graph it claims to project from being present yet.

        Returns:
            One observation per unresolved projection.
        """
        workflow_ids = {node.id for node in self.workflow.nodes}
        return [
            Observation(
                subject=edge.id,
                expected="projects_from naming a node in the workflow (layer-3) graph",
                observed=f"{edge.projects_from!r} is not a workflow node id",
            )
            for edge in self.ledger.edges
            if edge.projects_from is not None and edge.projects_from not in workflow_ids
        ]

    def unresolved_task_refs(self) -> list[Observation]:
        """Find layer-1 edges whose ``task_ref`` names no node in the work (layer-2) graph.

        "One uniform machine, instantiated per task" only holds when the task each instantiation is
        for actually exists in the work graph; this is that reference resolving.

        Returns:
            One observation per transition instance naming a task the work graph does not have.
        """
        work_ids = {node.id for node in self.work.nodes}
        return [
            Observation(
                subject=edge.id,
                expected="task_ref naming a node in the work (layer-2) graph",
                observed=f"{edge.task_ref!r} is not a work-graph node id",
            )
            for edge in self.ledger.edges
            if edge.task_ref not in work_ids
        ]

    def unresolved_extension_performers(self) -> list[Observation]:
        """Find layer-2 extension operations whose ``performed_by`` names no workflow node.

        :class:`~dh_core.graph_ir.work_layer.ExtensionOperation` and :class:`WorkNode` already
        cross-check each other for internal consistency (a split's product must carry the split's
        ``performed_by`` as its ``inserted_by``); what neither can check alone is whether the
        performer itself is a real layer-3 node, which needs the workflow graph.

        Returns:
            One observation per extension whose performer does not resolve.
        """
        workflow_ids = {node.id for node in self.workflow.nodes}
        return [
            Observation(
                subject=operation.id,
                expected="performed_by naming a node in the workflow (layer-3) graph",
                observed=f"{operation.performed_by!r} is not a workflow node id",
            )
            for operation in self.work.extensions
            if operation.performed_by not in workflow_ids
        ]

    def edges_without_workflow_origin(self) -> list[Observation]:
        """Delegate to :meth:`LedgerGraph.edges_without_workflow_origin`.

        Returns:
            One observation per layer-1 edge with no stated projection origin.
        """
        return self.ledger.edges_without_workflow_origin()

    def missing_bookends(self) -> list[Observation]:
        """Delegate to :meth:`WorkGraph.missing_bookends`.

        Returns:
            One observation per bookend kind the work graph does not declare.
        """
        return self.work.missing_bookends()

    def untraced_planned_nodes(self) -> list[Observation]:
        """Delegate to :meth:`DecompositionInput.untraced_planned_nodes`.

        Returns:
            One observation per planned work node tracing back to nothing in the decomposition input.
        """
        return self.decomposition.untraced_planned_nodes(self.work)

    def unreached_decomposition_items(self) -> list[Observation]:
        """Delegate to :meth:`DecompositionInput.unreached_items`.

        Returns:
            One observation per decomposition item that reached no work-graph node.
        """
        return self.decomposition.unreached_items(self.work)
