"""The layer discriminator shared by every layer's node and edge types.

``docs/graph-ir/ASSESSOR-CONTRACT.md`` ("The three layers"): the system is three graphs, each
describable on its own, drawn together only when all three exist. This module holds the one
vocabulary item every layer's model types carry so a reader -- human or query -- can tell which
layer an element belongs to without inspecting its shape.
"""

from __future__ import annotations

from enum import StrEnum


class Layer(StrEnum):
    """Which of the three graphs an element belongs to.

    Each layer's node and edge classes pin this as a ``Literal`` default, so the discriminator is
    part of the type: a layer-2 :class:`~dh_core.graph_ir.work_layer.WorkNode` cannot be
    constructed with ``layer=Layer.WORKFLOW``, and no field lets one layer's element masquerade as
    another's.
    """

    LEDGER = "layer-1-ledger"
    """Task lifecycle: nodes are statuses, edges are the commands that move between them."""

    WORK = "layer-2-work"
    """The work graph: nodes are tasks; concurrency, ordering and the bookend guarantee live here."""

    WORKFLOW = "layer-3-workflow"
    """The workflow: nodes are process steps with an actor, a guard and source refs into a SKILL.md."""
