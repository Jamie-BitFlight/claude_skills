"""Branch-bound expected-head advancement contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class PreparedAdvance:
    """Durable immutable operands for one target update."""

    remote_identity: str
    target_ref: str
    candidate_ref: str
    expected_target_oid: str
    candidate_oid: str
    prepared_result_oid: str
    prepared_tree_oid: str
    ordered_parent_oids: tuple[str, ...]
    prepared_identity_digest: str


@dataclass(frozen=True)
class GitPushCapability:
    """Exact admitted runtime capability identity."""

    identity: str
    remote_identity: str
    target_ref_pattern: str
    actor_identity: str
    actor_permissions_snapshot_digest: str
    rules_snapshot_digest: str
    proof_evidence_digest: str
    proof_transcript_digest: str
    git_version: str
    supported_target_policy: Literal["direct-fast-forward"] = "direct-fast-forward"
    supported_result_shape: Literal["DIRECT_FAST_FORWARD"] = "DIRECT_FAST_FORWARD"
    supports_expected_head_advance: bool = False
    supports_atomic_review_guard: bool = False
    primitive: Literal["git-smart-push-explicit-lease"] = "git-smart-push-explicit-lease"


@dataclass(frozen=True)
class RepositoryIdentityObservation:
    """Observed credential-free repository identity."""

    remote_identity: str
    available: bool


@dataclass(frozen=True)
class RefObservation:
    """One exact ref observation."""

    ref: str
    oid: str | None
    available: bool


@dataclass(frozen=True)
class GitObjectFacts:
    """Immutable object type and graph facts."""

    oid: str
    object_type: Literal["commit", "tree", "blob", "tag"]
    tree_oid: str | None = None
    parent_oids: tuple[str, ...] = ()
    ancestors: tuple[str, ...] = ()


@dataclass(frozen=True)
class GitPushAttempt:
    """Complete result classification from one push invocation."""

    transmitted: bool
    succeeded: bool
    stdout: bytes
    stderr: bytes


@dataclass(frozen=True)
class ExpectedHeadAdvanceResult:
    """Stable advancement outcome."""

    outcome: str


class GitPushPort(Protocol):
    """Branch-bound exact-ref smart-push operations."""

    def preflight_repository(self) -> RepositoryIdentityObservation:
        """Observe the bound repository identity."""
        ...

    def observe_ref(self, *, ref: str) -> RefObservation:
        """Observe one full ref without substituting a branch tip."""
        ...

    def object_facts(self, *, oids: tuple[str, ...]) -> tuple[GitObjectFacts, ...]:
        """Return immutable facts for exact object IDs."""
        ...

    def push_exact(self, *, expected_target_oid: str, prepared_result_oid: str) -> GitPushAttempt:
        """Push one result guarded by one explicit expected old OID."""
        ...


def prepared_identity_digest(prepared: PreparedAdvance) -> str:
    """Hash every prepared operand except the digest field itself.

    Returns:
        The canonical SHA-256 identity.
    """
    value = asdict(prepared)
    value.pop("prepared_identity_digest")
    content = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(content).hexdigest()


class IntegrationBranchAdvancer:
    """Prove immutable operands before invoking a branch-bound push."""

    def __init__(
        self, port: GitPushPort, capability: GitPushCapability, *, remote_identity: str, target_ref: str
    ) -> None:
        """Bind one port and capability to one repository target."""
        self.port = port
        self.push_capability = capability
        self.remote_identity = remote_identity
        self.target_ref = target_ref

    def capability(self) -> GitPushCapability:
        """Return the exact capability record checked by this advancer."""
        return self.push_capability

    def advance(self, prepared: PreparedAdvance) -> ExpectedHeadAdvanceResult:
        """Validate and conditionally advance the bound target."""
        raise NotImplementedError
