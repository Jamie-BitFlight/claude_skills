"""Source anchors and the descriptor: the facets an input or output must carry.

Split out of :mod:`dh_core.workflow_multigraph.model` for the same reason as :mod:`dh_core.workflow_multigraph.vocabulary`
-- these types are not layer-specific. A layer-3 :class:`~dh_core.workflow_multigraph.model.Node` and a
layer-2 :class:`~dh_core.workflow_multigraph.work_layer.WorkEdge` can both cite a :class:`SourceSpan`; only
layer 3 currently declares :class:`Descriptor`-typed inputs and outputs, but nothing here assumes
that.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from dh_core.workflow_multigraph.vocabulary import Cardinality, Completeness, ExtractionStatus, Trust


class SourceSpan(BaseModel):
    """One place in the sources an element was read from."""

    model_config = ConfigDict(frozen=True)

    ref: str = Field(min_length=1, description="Path with an anchor or line range, e.g. 'a.py#L10-L20'.")
    quote: str = Field(default="", description="The text at that span, when quoting it aids review.")


class Freshness(BaseModel):
    """The freshness and version facet of a value."""

    version: str | None = Field(default=None, description="Revision or fingerprint the value describes.")
    may_be_stale: bool = Field(default=False, description="The value can be older than the state it describes.")
    freshness_check: str = Field(default="", description="Check establishing currency; empty means none exists.")


class Descriptor(BaseModel):
    """One declared input or output, carrying every facet the contract requires of one.

    Two facets are read by role: on an input, :attr:`required_authority` and :attr:`trust` are what
    the value must carry; on an output, :attr:`granting_authority` and :attr:`trust` are what the
    producer supplies. That asymmetry is the point -- two nodes can exchange valid JSON under
    identical schemas and still hold a broken contract, one producing a claim the other reads as a
    verdict.
    """

    name: str = Field(min_length=1)
    syntactic_type: str = Field(min_length=1, description="Type or schema name of the value.")
    schema_ref: str | None = Field(default=None, description="Pointer to the schema, when one exists.")
    semantic_meaning: str = Field(min_length=1, description="What the value means, not what it is shaped like.")
    cardinality: Cardinality
    required_authority: str | None = Field(default=None, description="Input: the authority the value must carry.")
    granting_authority: str | None = Field(default=None, description="Output: the authority that produced it.")
    provenance: str = Field(min_length=1, description="Where the value comes from.")
    freshness: Freshness = Field(default_factory=Freshness)
    completeness: Completeness
    trust: Trust
    confidentiality: str | None = Field(default=None, description="Confidentiality class, where one applies.")
    satisfies_types: list[str] = Field(default_factory=list, description="Output: consumer types it also satisfies.")
    extraction_status: ExtractionStatus
    source_refs: list[SourceSpan] = Field(min_length=1)

    def satisfies_type_of(self, consumer: Descriptor) -> bool:
        """Return whether this output's type satisfies ``consumer``'s declared input type.

        Returns:
            True when the types match or the output declares it widens to the consumer's type.
        """
        return self.syntactic_type == consumer.syntactic_type or consumer.syntactic_type in self.satisfies_types
