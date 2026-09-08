"""The finding record and its severity taxonomy.

A finding is one falsified predicate over a frozen graph.
``plugins/development-harness/ARCHITECTURE.md``, "The work graph" §§ "Falsified predicates" and
"Severity rule" fix both halves of what may be claimed:

* the predicates worth reporting are an enumerated list, not free prose -- :class:`Predicate`;
* the severity rule is mechanical. ``BROKEN`` only when a declared or necessarily implied predicate
  is demonstrably false; when the contract is missing, or admits several plausible readings,
  ``CONTRACT_UNSPECIFIED`` or ``AMBIGUOUS`` -- never ``BROKEN``.

Both are data here, and severity is a computed field over :attr:`Finding.basis` with
``extra="forbid"``, so a checker cannot pass a severity of its own choosing: it states what the
sources say about the contract, and the rule assigns the severity. That keeps the boundary at
finding what is broken without speculating why, and it makes the one judgement a checker is
actually making -- was this predicate ever declared -- the field it has to defend, in
:attr:`Finding.basis_evidence`.

Findings are frozen. The findings document is untrusted and immutable: a verifier issues amendments
or counter-findings and never silently rewrites it.

Two predicates come from ARCHITECTURE.md's "The decomposition-exit gate" section rather than
:data:`PREDICATES`' original set: :attr:`Predicate.PRESCRIBED_METHOD_WITHOUT_EVIDENCE` (an
instruction's prescribed method carries no evidence and none is recorded absent -- the
"Provenance: one rule, three sites" rule applied to a task's method) sits under
:attr:`Projection.EVIDENCE_AND_PROVENANCE`, the same projection already used for trust and revision
predicates about what supports a claim. :attr:`Predicate.REFERENT_DOES_NOT_RESOLVE` sits under
:attr:`Projection.CONTROL_FLOW` instead: ARCHITECTURE.md's own wording for that projection is
"reachability, dead nodes, guard coverage, joins, completion, loops", and Tier 1 of the
decomposition-exit gate asks a reachability question of a
referent -- "the referent must exist at decomposition time" -- the same question
:attr:`Predicate.UNREACHABLE` already asks of a node or output. A referent is a target an
instruction must be able to reach, not evidence supporting a claim, so it is grouped with
reachability rather than with provenance.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field

from dh_core.workflow_multigraph.model import Observation, SourceSpan


class Projection(StrEnum):
    """The projection a predicate is checked in; each is derived mechanically from the one multigraph."""

    CONTROL_FLOW = "control-flow"
    DATA_AND_STATE = "data-and-state"
    INTENT_AND_REQUIREMENTS = "intent-and-requirements"
    EVIDENCE_AND_PROVENANCE = "evidence-and-provenance"
    AUTHORITY_AND_EFFECTS = "authority-and-effects"
    RUNTIME_TRACES = "runtime-traces"


class Predicate(StrEnum):
    """The falsified predicates the contract says to report. A finding names one of these."""

    REQUIRED_INPUT_HAS_NO_PRODUCER = "required-input-has-no-producer"
    PRODUCER_TYPE_UNSATISFIED = "producer-output-type-does-not-satisfy-consumer-input-type"
    REQUIRED_FIELD_ABSENT = "required-field-absent"
    CARDINALITY_CONFLICTS_WITH_JOIN = "output-cardinality-conflicts-with-join"
    TRUST_BELOW_REQUIREMENT = "consumer-requires-verified-and-producer-supplies-proposed"
    REVISION_MISMATCH = "artifact-revision-does-not-match-expected-revision"
    STALE_INPUT_UNCHECKED = "input-may-be-stale-and-no-freshness-check-exists"
    FAILURE_OUTPUT_UNCONSUMED = "failure-output-has-no-consuming-edge"
    ACTOR_LACKS_AUTHORITY = "actor-lacks-authority-for-the-effect"
    GUARD_INCOMPLETE_OR_OVERLAPPING = "branch-guard-is-incomplete-or-overlaps-another-guard"
    UNREACHABLE = "node-or-output-is-unreachable"
    PRESCRIBED_METHOD_WITHOUT_EVIDENCE = "prescribed-method-carries-no-evidence-and-none-is-recorded-as-absent"
    REFERENT_DOES_NOT_RESOLVE = "instruction-names-a-referent-that-does-not-resolve"


class PredicateDefinition(BaseModel):
    """One predicate as the contract words it, and the projection that decides it."""

    model_config = ConfigDict(frozen=True)

    statement: str = Field(min_length=1, description="The contract's own wording of the predicate.")
    projection: Projection


PREDICATES: dict[Predicate, PredicateDefinition] = {
    Predicate.REQUIRED_INPUT_HAS_NO_PRODUCER: PredicateDefinition(
        statement="a required input has no producer", projection=Projection.DATA_AND_STATE
    ),
    Predicate.PRODUCER_TYPE_UNSATISFIED: PredicateDefinition(
        statement="a producer's output type does not satisfy the consumer's input type",
        projection=Projection.DATA_AND_STATE,
    ),
    Predicate.REQUIRED_FIELD_ABSENT: PredicateDefinition(
        statement="a required field is absent", projection=Projection.DATA_AND_STATE
    ),
    Predicate.CARDINALITY_CONFLICTS_WITH_JOIN: PredicateDefinition(
        statement="output cardinality conflicts with the join", projection=Projection.CONTROL_FLOW
    ),
    Predicate.TRUST_BELOW_REQUIREMENT: PredicateDefinition(
        statement="the consumer requires VERIFIED and the producer supplies PROPOSED",
        projection=Projection.EVIDENCE_AND_PROVENANCE,
    ),
    Predicate.REVISION_MISMATCH: PredicateDefinition(
        statement="an artifact revision does not match the expected revision",
        projection=Projection.EVIDENCE_AND_PROVENANCE,
    ),
    Predicate.STALE_INPUT_UNCHECKED: PredicateDefinition(
        statement="an input may be stale and no freshness check exists", projection=Projection.DATA_AND_STATE
    ),
    Predicate.FAILURE_OUTPUT_UNCONSUMED: PredicateDefinition(
        statement="a failure output has no consuming edge", projection=Projection.CONTROL_FLOW
    ),
    Predicate.ACTOR_LACKS_AUTHORITY: PredicateDefinition(
        statement="an actor lacks authority for the effect", projection=Projection.AUTHORITY_AND_EFFECTS
    ),
    Predicate.GUARD_INCOMPLETE_OR_OVERLAPPING: PredicateDefinition(
        statement="a branch guard is incomplete, or overlaps another guard", projection=Projection.CONTROL_FLOW
    ),
    Predicate.UNREACHABLE: PredicateDefinition(
        statement="a node or output is unreachable", projection=Projection.CONTROL_FLOW
    ),
    Predicate.PRESCRIBED_METHOD_WITHOUT_EVIDENCE: PredicateDefinition(
        statement="a prescribed method carries no evidence, and none is recorded as absent",
        projection=Projection.EVIDENCE_AND_PROVENANCE,
    ),
    Predicate.REFERENT_DOES_NOT_RESOLVE: PredicateDefinition(
        # CONTROL_FLOW, not EVIDENCE_AND_PROVENANCE -- see the module docstring for why: this is a
        # reachability question, the same one UNREACHABLE already asks of a node or output.
        statement="an instruction names a referent that does not resolve",
        projection=Projection.CONTROL_FLOW,
    ),
}
"""Every :class:`Predicate`, worded as the contract words it. A checker reports from this table."""


class ContractBasis(StrEnum):
    """What the sources say about the predicate the finding falsifies.

    This is the checker's one judgement, and the only input to severity. It is a claim about the
    sources -- whether they state the predicate -- not about the system's behaviour.
    """

    DECLARED = "DECLARED"  # a source states the predicate outright
    NECESSARILY_IMPLIED = "NECESSARILY_IMPLIED"  # no source states it, and nothing works unless it holds
    UNSPECIFIED = "UNSPECIFIED"  # the sources are silent on it
    AMBIGUOUS = "AMBIGUOUS"  # the sources admit several plausible readings, and they disagree here


class Severity(StrEnum):
    """The three severities. There is no fourth, and none is reachable except through the rule."""

    BROKEN = "BROKEN"
    CONTRACT_UNSPECIFIED = "CONTRACT_UNSPECIFIED"
    AMBIGUOUS = "AMBIGUOUS"


SEVERITY_BY_BASIS: dict[ContractBasis, Severity] = {
    ContractBasis.DECLARED: Severity.BROKEN,
    ContractBasis.NECESSARILY_IMPLIED: Severity.BROKEN,
    ContractBasis.UNSPECIFIED: Severity.CONTRACT_UNSPECIFIED,
    ContractBasis.AMBIGUOUS: Severity.AMBIGUOUS,
}
"""The contract's severity rule, as a total function of the basis. Nothing else assigns a severity."""


class Finding(BaseModel):
    """One falsified predicate over a frozen graph.

    ``extra="forbid"`` and the computed :attr:`severity` together mean a checker states the
    predicate, the basis, the spans and what it observed, and the rule does the rest.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    predicate: Predicate
    basis: ContractBasis
    basis_evidence: str = Field(min_length=1, description="Why the basis is what it is, citing the sources.")
    subject: str = Field(min_length=1, description="Node id, edge id, or 'node.descriptor' the finding is about.")
    expected: str = Field(min_length=1, description="What the predicate requires.")
    observed: str = Field(min_length=1, description="What the graph holds instead.")
    source_spans: tuple[SourceSpan, ...] = Field(min_length=1)
    graph_refs: tuple[str, ...] = Field(default=(), description="Node and edge ids the finding rests on.")

    @computed_field
    @property
    def severity(self) -> Severity:
        """The severity the contract's rule assigns to this finding's basis."""
        return SEVERITY_BY_BASIS[self.basis]

    @property
    def statement(self) -> str:
        """The contract's wording of the falsified predicate."""
        return PREDICATES[self.predicate].statement

    @classmethod
    def from_observation(
        cls,
        predicate: Predicate,
        basis: ContractBasis,
        basis_evidence: str,
        observation: Observation,
        source_spans: tuple[SourceSpan, ...],
        graph_refs: tuple[str, ...] = (),
    ) -> Finding:
        """Build a finding from a graph query's observation.

        Args:
            predicate: The predicate the observation falsifies.
            basis: What the sources say about that predicate.
            basis_evidence: Why the basis is what it is, citing the sources.
            observation: The expected-against-observed pair a graph query returned.
            source_spans: Where in the sources this was read; at least one.
            graph_refs: Node and edge ids the finding rests on.

        Returns:
            The finding, with its severity assigned by the rule.
        """
        return cls(
            predicate=predicate,
            basis=basis,
            basis_evidence=basis_evidence,
            subject=observation.subject,
            expected=observation.expected,
            observed=observation.observed,
            source_spans=source_spans,
            graph_refs=graph_refs,
        )
