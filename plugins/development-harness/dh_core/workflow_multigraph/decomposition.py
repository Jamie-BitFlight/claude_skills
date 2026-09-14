"""The decomposition input: what layer 3 consumes to produce a layer-2 work graph.

``plugins/development-harness/ARCHITECTURE.md``, "The work graph" § "What the model must carry":
decomposition takes the grooming and design output -- research, fact checks, dependencies,
documentation, concerns -- into work with its concurrency and ordering stated. Each of those nouns
becomes a :class:`DecompositionItem`
of the matching :class:`DecompositionSourceKind`, so a :class:`~dh_core.workflow_multigraph.work_layer.WorkNode`
can name the item it traces back to and a check can ask the traceability question in both
directions: :meth:`DecompositionInput.untraced_planned_nodes` (a work node tracing to nothing here)
and :meth:`DecompositionInput.unreached_items` (an item here that reached no work node).

Only *planned* work nodes are checked against the decomposition input. A node with
:attr:`~dh_core.workflow_multigraph.work_layer.WorkNodeProvenance.SPLIT` or
:attr:`~dh_core.workflow_multigraph.work_layer.WorkNodeProvenance.INSERTED` provenance was, by the contract's
own account, added *because* the original decomposition did not account for it -- holding such a
node to the same traceability standard as a planned one would be asking the extension mechanism to
justify the very gap it exists to fill.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from dh_core.workflow_multigraph.descriptors import SourceSpan
from dh_core.workflow_multigraph.model import Observation
from dh_core.workflow_multigraph.vocabulary import ExtractionStatus
from dh_core.workflow_multigraph.work_layer import WorkGraph, WorkNodeProvenance


class DecompositionSourceKind(StrEnum):
    """The kinds of grooming and architecture output layer 3 decomposes, as the contract names them."""

    RESEARCH = "research"
    FACT_CHECK = "fact-check"
    DEPENDENCY = "dependency"
    DOCUMENTATION = "documentation"
    CONCERN = "concern"


class DecompositionItem(BaseModel):
    """One piece of grooming or architecture output offered to layer 3's decomposition."""

    id: str = Field(min_length=1)
    kind: DecompositionSourceKind
    summary: str = Field(min_length=1)
    source_refs: list[SourceSpan] = Field(min_length=1)
    extraction_status: ExtractionStatus


class DecompositionInput(BaseModel):
    """The grooming and architecture output layer 3 decomposes into a layer-2 work graph."""

    items: list[DecompositionItem] = Field(default_factory=list)

    def item(self, item_id: str) -> DecompositionItem | None:
        """Return the named item, or None when no item carries this id.

        Args:
            item_id: The id to resolve.

        Returns:
            The matching item.
        """
        return next((i for i in self.items if i.id == item_id), None)

    def untraced_planned_nodes(self, work: WorkGraph) -> list[Observation]:
        """Find planned work-graph nodes whose ``decomposition_source`` names no item here.

        Args:
            work: The layer-2 graph to check.

        Returns:
            One observation per planned node that does not trace back to this input.
        """
        ids = {i.id for i in self.items}
        return [
            Observation(
                subject=node.id,
                expected="decomposition_source naming an item in the decomposition input",
                observed=(
                    "no decomposition_source is set"
                    if node.decomposition_source is None
                    else f"names {node.decomposition_source!r}, absent from the decomposition input"
                ),
            )
            for node in work.nodes
            if node.provenance is WorkNodeProvenance.PLANNED and node.decomposition_source not in ids
        ]

    def unreached_items(self, work: WorkGraph) -> list[Observation]:
        """Find decomposition items that no work-graph node traces back to.

        Args:
            work: The layer-2 graph to check.

        Returns:
            One observation per item that reached no node.
        """
        reached = {node.decomposition_source for node in work.nodes if node.decomposition_source is not None}
        return [
            Observation(
                subject=item.id,
                expected="at least one work-graph node naming this item as its decomposition_source",
                observed="no node traces back to it",
            )
            for item in self.items
            if item.id not in reached
        ]
