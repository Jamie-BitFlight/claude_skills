"""The parts a layer-3 node record is built from: authority, side effects, error routing, and so on.

Split out of :mod:`dh_core.workflow_multigraph.model` for the same file-size reason as
:mod:`dh_core.workflow_multigraph.vocabulary` and :mod:`dh_core.workflow_multigraph.descriptors`. These types are read by
:class:`~dh_core.workflow_multigraph.model.Node`, the layer-3 (workflow) node -- the contract's node record is
shaped for that layer specifically ("Layer 3 ... the node record below is shaped for these").
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from dh_core.workflow_multigraph.vocabulary import Effect


class Authority(BaseModel):
    """Who a node acts as, and which effects that identity is granted."""

    holder: str = Field(min_length=1)
    grants: frozenset[Effect] = frozenset()


class SideEffect(BaseModel):
    """One effect a node has on state outside its own outputs."""

    target: str = Field(min_length=1)
    effect: Effect
    description: str = ""


class ErrorRoute(BaseModel):
    """One failure signal a node can emit, and where it goes."""

    signal: str = Field(min_length=1)
    handled_by: str | None = Field(default=None, description="Node id consuming the signal; None means nowhere.")


class EvidenceRequirement(BaseModel):
    """One claim a node makes and what is required to support it."""

    claim: str = Field(min_length=1)
    supported_by: list[str] = Field(default_factory=list, description="Descriptor or node ids supplying support.")


class Operation(BaseModel):
    """What the node does, in the sources' own terms."""

    kind: str = Field(default="", description="e.g. 'command', 'fold', 'derived-rule'.")
    summary: str = ""


class Termination(BaseModel):
    """Whether and how the node ends a path, and what bounds any loop through it."""

    terminal: bool = False
    outcome: str = ""
    bound: str = Field(default="", description="Loop bound or progress variable; empty when not a loop.")
