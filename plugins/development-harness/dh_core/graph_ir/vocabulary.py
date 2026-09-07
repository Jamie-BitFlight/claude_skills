"""The layer-agnostic vocabulary: edge types, effects, and the facet enums a descriptor carries.

Split out of :mod:`dh_core.graph_ir.model` so that module stays under the file-size policy as the
package grows a layer at a time. Nothing here is layer-specific -- ``EdgeType`` is the set of
types both layer 2 and layer 3 draw edges from (``plugins/development-harness/ARCHITECTURE.md``,
"The work graph" § "Edge types"), and the facet enums describe a value regardless of which layer's
node declares it.
"""

from __future__ import annotations

from enum import StrEnum


class EdgeType(StrEnum):
    """The typed relations the contract enumerates; a pair of nodes may be joined by several at once."""

    CONTROL = "CONTROL"  # what may run after what
    DATA = "DATA"  # a produced object to the node that consumes it
    STATE = "STATE"  # shared persistent state, including mutual exclusion over a resource
    EVIDENCE = "EVIDENCE"  # what supports a claim
    AUTHORITY = "AUTHORITY"  # who may decide, mutate, approve, publish, retry or terminate
    ERROR = "ERROR"  # where a failure signal goes
    RECOVERY = "RECOVERY"  # how a failure is repaired or retried
    INVALIDATES = "INVALIDATES"  # what a result revokes


class Effect(StrEnum):
    """The effects an authority grants; the contract's authority-and-effects vocabulary."""

    DECIDE = "decide"
    MUTATE = "mutate"
    APPROVE = "approve"
    PUBLISH = "publish"
    RETRY = "retry"
    TERMINATE = "terminate"


class Cardinality(StrEnum):
    """How many values an input or output carries."""

    OPTIONAL = "0..1"
    EXACTLY_ONE = "1"
    ANY = "0..n"
    AT_LEAST_ONE = "1..n"


class Trust(StrEnum):
    """Trust classification of a value. The contract's "candidate" is :attr:`PROPOSED`."""

    UNTRUSTED = "UNTRUSTED"
    PROPOSED = "PROPOSED"
    VERIFIED = "VERIFIED"
    AUTHORITATIVE = "AUTHORITATIVE"


TRUST_ORDER: dict[Trust, int] = {Trust.UNTRUSTED: 0, Trust.PROPOSED: 1, Trust.VERIFIED: 2, Trust.AUTHORITATIVE: 3}
"""Rank deciding whether a supplied trust level meets a required one."""


class Completeness(StrEnum):
    """What the reader may assume about a value covering its subject."""

    TOTAL = "TOTAL"  # every member of the subject is present
    PARTIAL = "PARTIAL"  # members may be missing, and the value says so
    UNSPECIFIED = "UNSPECIFIED"  # nothing in the sources says which of the two holds


class ExtractionStatus(StrEnum):
    """How this element came to be recorded. Fidelity review reads this first."""

    OBSERVED = "OBSERVED"  # stated by a source span
    INFERRED = "INFERRED"  # derived from sources that do not state it outright
    ASSUMED = "ASSUMED"  # supplied by the extractor; no source supports it
    ABSENT = "ABSENT"  # the sources are silent and the extractor recorded the gap
