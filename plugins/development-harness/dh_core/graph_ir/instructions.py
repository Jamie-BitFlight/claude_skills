"""The instruction record a task carries out of decomposition.

``docs/graph-ir/ASSESSOR-CONTRACT.md`` ("The decomposition-exit gate"): "A task leaving stage 5
carries instructions. The rule they must satisfy is the owner's: do not write tasks with claims or
processes from training data. ... So the gate measures referents, in two tiers." This module holds
the two shapes of instruction that section names:

* a :attr:`InstructionKind.DELEGATING` instruction "sends the agent somewhere" -- it names a
  :class:`Referent` the agent must go resolve, drawn from the contract's tier-1 table
  (:class:`ReferentKind`).
* a :attr:`InstructionKind.ASSERTING` instruction "stat[es] how a system behaves" -- it must carry a
  :class:`~dh_core.graph_ir.descriptors.SourceSpan` whose ``quote`` is found verbatim in the text at
  its ``ref``, or record the absence honestly: an ``extraction_status`` of ``ASSUMED``/``ABSENT``
  plus a non-empty ``absence_note`` ("no source establishes this; falsify it before relying on it").

:meth:`Instruction.check_kind_matches_payload` refuses only the one structural disagreement the
contract names outright -- a ``DELEGATING`` instruction with no :class:`Referent` at all, and the
mirror case of an ``ASSERTING`` instruction carrying referents (a ``DELEGATING`` payload under an
``ASSERTING`` kind). It does **not** refuse an ``ASSERTING`` instruction with no span and no recorded
absence, nor a referent whose target does not resolve, nor a span whose quote is not actually in the
text at its ref: this package's standing rule (``work_layer.py``'s module docstring) is that the IR
must be able to hold the unsound graph so its unsoundness can be reported, and those three failures
are exactly what :mod:`dh_core.graph_ir.decomposition_gate` exists to detect and report as findings.
Refusing to construct them would make the defect invisible instead of reported.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dh_core.graph_ir.descriptors import SourceSpan
from dh_core.graph_ir.vocabulary import ExtractionStatus


class InstructionKind(StrEnum):
    """The shapes a decomposed instruction takes, per the contract's decomposition-exit gate."""

    DELEGATING = "delegating"
    """Sends the agent somewhere -- names a referent that must resolve (Tier 1)."""

    ASSERTING = "asserting"
    """States how a system behaves -- must quote a resolving source, or record the gap (Tier 2)."""


class ReferentKind(StrEnum):
    """The contract's tier-1 table: what a delegating instruction may point at, and to what it resolves.

    ``ASSESSOR-CONTRACT.md``, "Tier 1 -- a delegating instruction must resolve":

    | referent | resolves to |
    |---|---|
    | ``SKILL`` | a directory containing ``SKILL.md`` |
    | ``TASK_OUTPUT`` | a work-graph node declaring that output |
    | ``FILE`` | a path that exists |
    | ``RULE`` | a rules file, or a named section of one |
    | ``ARTIFACT`` | a type in the artifact registry, with its id |
    | ``GRAPH_POSITION`` | the successor node the instruction asserts will exist |
    """

    SKILL = "SKILL"
    TASK_OUTPUT = "TASK_OUTPUT"
    FILE = "FILE"
    RULE = "RULE"
    ARTIFACT = "ARTIFACT"
    GRAPH_POSITION = "GRAPH_POSITION"


class Referent(BaseModel):
    """One thing a :attr:`InstructionKind.DELEGATING` instruction sends the agent to resolve."""

    model_config = ConfigDict(frozen=True)

    kind: ReferentKind
    target: str = Field(
        min_length=1,
        description=(
            "What the referent names: a skill name (bare, or 'plugin:skill'), a work-graph node id, "
            "a repo-relative path, a rules-file path (optionally '#section'), or 'type#id' for an "
            "artifact."
        ),
    )
    source_refs: list[SourceSpan] = Field(min_length=1, description="Where the instruction named this referent.")


class Instruction(BaseModel):
    """One instruction a task carries out of decomposition, per the contract's decomposition-exit gate.

    Every instruction is the declaration it makes: a ``DELEGATING`` instruction declares its referent
    exists, and an ``ASSERTING`` one declares its quote is there to be read -- "the instruction is the
    declaration" (``ASSESSOR-CONTRACT.md``, Tier 1). Whether the declaration holds is
    :mod:`~dh_core.graph_ir.decomposition_gate`'s question, not this model's; this model's own
    :meth:`check_kind_matches_payload` refuses only a payload shaped for the wrong kind.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    kind: InstructionKind
    text: str = Field(min_length=1, description="The instruction as the task carries it.")
    referents: tuple[Referent, ...] = Field(
        default=(), description="DELEGATING payload: at least one referent the agent must resolve."
    )
    source_refs: list[SourceSpan] = Field(
        default_factory=list, description="ASSERTING payload: spans whose quote should be found verbatim at their ref."
    )
    extraction_status: ExtractionStatus | None = Field(
        default=None, description="ASSERTING payload: ASSUMED/ABSENT records an honestly-marked gap."
    )
    absence_note: str = Field(
        default="", description="ASSERTING payload: 'no source establishes this; falsify it before relying on it'."
    )

    @model_validator(mode="after")
    def check_kind_matches_payload(self) -> Instruction:
        """Refuse an instruction whose kind and payload disagree structurally.

        Returns:
            The validated instruction.

        Raises:
            ValueError: If a ``DELEGATING`` instruction carries no :class:`Referent` at all, or an
                ``ASSERTING`` instruction carries referents -- a ``DELEGATING`` payload under the
                other kind.
        """
        if self.kind is InstructionKind.DELEGATING and not self.referents:
            raise ValueError(f"instruction {self.id!r} is DELEGATING but carries no referent")
        if self.kind is InstructionKind.ASSERTING and self.referents:
            raise ValueError(f"instruction {self.id!r} is ASSERTING but carries referents, a DELEGATING payload")
        return self

    def is_recorded_absent(self) -> bool:
        """Return whether this instruction honestly records an absent method, per Tier 2's exit.

        Returns:
            True when :attr:`extraction_status` is ``ASSUMED`` or ``ABSENT`` and :attr:`absence_note`
            is non-empty -- "the gap stated", the contract's honest exit from Tier 2.
        """
        return self.extraction_status in {ExtractionStatus.ASSUMED, ExtractionStatus.ABSENT} and bool(
            self.absence_note.strip()
        )
