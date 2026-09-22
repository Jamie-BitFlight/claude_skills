"""Branch-bound expected-head advancement contracts."""

from __future__ import annotations

import hashlib
import json
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Frozen strict adapter model."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class PreparedAdvance(StrictModel):
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


class CanonicalCapabilityIdentity(StrictModel):
    """Canonical actual-remote capability tuple derived by admission."""

    hostname: str
    repository_id: int
    repository_owner: str
    repository_name: str
    canonical_remote_identity: str
    target_ref: str
    actor_identity: str
    actor_permissions_snapshot_digest: str
    rules_snapshot_digest: str
    production_configuration_digest: str
    production_evidence_digest: str
    sandbox_report_digest: str
    sandbox_transcript_digest: str
    git_version: str
    primitive: Literal["git-smart-push-explicit-lease"]
    supported_target_policy: Literal["direct-fast-forward"]
    supported_result_shape: Literal["DIRECT_FAST_FORWARD"]
    supports_atomic_review_guard: bool

    @property
    def digest(self) -> str:
        """Return the canonical compact JSON plus LF identity digest."""
        content = (json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
        return "sha256:" + hashlib.sha256(content).hexdigest()


class GitPushCapability(StrictModel):
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
    canonical_identity: CanonicalCapabilityIdentity | None = None

    @classmethod
    def from_canonical(
        cls, canonical: CanonicalCapabilityIdentity, *, supports_expected_head_advance: bool
    ) -> GitPushCapability:
        """Construct every public field from one canonical identity.

        Returns:
            A capability containing no independently supplied authority fields.
        """
        return cls(
            identity=canonical.digest,
            remote_identity=canonical.canonical_remote_identity,
            target_ref_pattern=canonical.target_ref,
            actor_identity=canonical.actor_identity,
            actor_permissions_snapshot_digest=canonical.actor_permissions_snapshot_digest,
            rules_snapshot_digest=canonical.rules_snapshot_digest,
            proof_evidence_digest=canonical.sandbox_report_digest,
            proof_transcript_digest=canonical.sandbox_transcript_digest,
            git_version=canonical.git_version,
            supported_target_policy=canonical.supported_target_policy,
            supported_result_shape=canonical.supported_result_shape,
            supports_expected_head_advance=supports_expected_head_advance,
            supports_atomic_review_guard=canonical.supports_atomic_review_guard,
            primitive=canonical.primitive,
            canonical_identity=canonical,
        )


class RepositoryIdentityObservation(StrictModel):
    """Observed credential-free repository identity."""

    remote_identity: str
    available: bool
    hostname: str = ""
    repository_owner: str = ""
    repository_name: str = ""
    target_ref: str = ""


class RefObservation(StrictModel):
    """One exact ref observation."""

    ref: str
    oid: str | None
    available: bool


class GitObjectFacts(StrictModel):
    """Immutable object type and graph facts."""

    oid: str
    object_type: Literal["commit", "tree", "blob", "tag"]
    tree_oid: str | None = None
    parent_oids: tuple[str, ...] = ()
    ancestors: tuple[str, ...] = ()


class GitPushAttempt(StrictModel):
    """Complete result classification from one push invocation."""

    transmitted: bool
    succeeded: bool
    stdout: bytes
    stderr: bytes


class ExpectedHeadAdvanceResult(StrictModel):
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


CAPABILITY_AUTHORITY_FIELDS: tuple[str, ...] = (
    "identity",
    "remote_identity",
    "target_ref_pattern",
    "actor_identity",
    "actor_permissions_snapshot_digest",
    "rules_snapshot_digest",
    "git_version",
    "proof_evidence_digest",
    "proof_transcript_digest",
    "supported_result_shape",
    "primitive",
    "supported_target_policy",
    "supports_atomic_review_guard",
)
"""Attempt-2 authority projection; attempt-3 closure requires the complete strict field set."""


def capability_authority_projection(capability: GitPushCapability) -> tuple[object, ...]:
    """Project classified authority fields for one equality comparison.

    Returns:
        Capability values in canonical authority order.
    """
    return tuple(getattr(capability, field) for field in CAPABILITY_AUTHORITY_FIELDS)


def canonical_authority_projection(canonical: CanonicalCapabilityIdentity) -> tuple[object, ...]:
    """Project canonical values corresponding to capability authority fields.

    Returns:
        Canonical values in capability authority order.
    """
    values = {
        "identity": canonical.digest,
        "remote_identity": canonical.canonical_remote_identity,
        "target_ref_pattern": canonical.target_ref,
        "actor_identity": canonical.actor_identity,
        "actor_permissions_snapshot_digest": canonical.actor_permissions_snapshot_digest,
        "rules_snapshot_digest": canonical.rules_snapshot_digest,
        "git_version": canonical.git_version,
        "proof_evidence_digest": canonical.sandbox_report_digest,
        "proof_transcript_digest": canonical.sandbox_transcript_digest,
        "supported_result_shape": canonical.supported_result_shape,
        "primitive": canonical.primitive,
        "supported_target_policy": canonical.supported_target_policy,
        "supports_atomic_review_guard": canonical.supports_atomic_review_guard,
    }
    return tuple(values[field] for field in CAPABILITY_AUTHORITY_FIELDS)


def prepared_identity_digest(prepared: PreparedAdvance) -> str:
    """Hash every prepared operand except the digest field itself.

    Returns:
        The canonical SHA-256 identity.
    """
    value = prepared.model_dump(mode="json")
    value.pop("prepared_identity_digest")
    content = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(content).hexdigest()


class IntegrationBranchAdvancer:
    """Prove immutable operands before invoking a branch-bound push."""

    def __init__(
        self,
        port: GitPushPort,
        capability: GitPushCapability,
        *,
        remote_identity: str,
        target_ref: str,
        candidate_ref: str = "",
    ) -> None:
        """Bind one port and capability to one repository target."""
        self.port = port
        self.push_capability = capability
        self.remote_identity = remote_identity
        self.target_ref = target_ref
        self.candidate_ref = candidate_ref

    def capability(self) -> GitPushCapability:
        """Return the exact capability record checked by this advancer."""
        return self.push_capability

    def advance(self, prepared: PreparedAdvance) -> ExpectedHeadAdvanceResult:
        """Validate and conditionally advance the bound target.

        Returns:
            A stable result with no hidden fallback.
        """
        for validation in (self.validate_inputs, self.validate_observations, self.validate_objects):
            refused = validation(prepared)
            if refused is not None:
                return refused
        attempt = self.port.push_exact(
            expected_target_oid=prepared.expected_target_oid, prepared_result_oid=prepared.prepared_result_oid
        )
        return self.classify_attempt(prepared, attempt)

    def prepare(self, candidate_sha: str) -> PreparedAdvance:
        """Prepare direct-fast-forward operands from exact named refs.

        Returns:
            The immutable prepared identity.
        """
        repository = self.port.preflight_repository()
        canonical = self.push_capability.canonical_identity
        if (
            canonical is None
            or not repository.available
            or repository.remote_identity != canonical.canonical_remote_identity
            or repository.target_ref != canonical.target_ref
        ):
            raise ValueError("repository-identity-mismatch")
        target = self.port.observe_ref(ref=self.target_ref)
        candidate = self.port.observe_ref(ref=self.candidate_ref)
        if not target.available or target.oid is None or candidate.oid != candidate_sha:
            raise ValueError("candidate-or-target-mismatch")
        facts = {fact.oid: fact for fact in self.port.object_facts(oids=(target.oid, candidate_sha))}
        candidate_facts = facts[candidate_sha]
        if candidate_facts.object_type != "commit" or candidate_facts.tree_oid is None:
            raise ValueError("candidate-object-invalid")
        value = PreparedAdvance(
            remote_identity=repository.remote_identity,
            target_ref=self.target_ref,
            candidate_ref=self.candidate_ref,
            expected_target_oid=target.oid,
            candidate_oid=candidate_sha,
            prepared_result_oid=candidate_sha,
            prepared_tree_oid=candidate_facts.tree_oid,
            ordered_parent_oids=candidate_facts.parent_oids,
            prepared_identity_digest="sha256:" + "0" * 64,
        )
        return value.model_copy(update={"prepared_identity_digest": prepared_identity_digest(value)})

    def reconcile(self, prepared: PreparedAdvance) -> ExpectedHeadAdvanceResult:
        """Observe target state without invoking push.

        Returns:
            Exact-result success, unchanged failure, or unresolved state.
        """
        observed = self.port.observe_ref(ref=self.target_ref)
        if observed.available and observed.oid == prepared.prepared_result_oid:
            return ExpectedHeadAdvanceResult(outcome="advanced-after-reconciliation")
        if observed.available and observed.oid == prepared.expected_target_oid:
            return ExpectedHeadAdvanceResult(outcome="not-advanced")
        if observed.available:
            return ExpectedHeadAdvanceResult(outcome="target-stale")
        return ExpectedHeadAdvanceResult(outcome="reconciliation-required")

    def validate_inputs(self, prepared: PreparedAdvance) -> ExpectedHeadAdvanceResult | None:
        """Validate capability, binding, shape, and durable identity.

        Returns:
            A refusal result, or None when input validation passes.
        """
        capability = self.push_capability
        canonical = capability.canonical_identity
        if canonical is None:
            return ExpectedHeadAdvanceResult(outcome="expected-head-unsupported")
        if (
            not capability.supports_expected_head_advance
            or capability_authority_projection(capability) != canonical_authority_projection(canonical)
            or self.remote_identity != canonical.canonical_remote_identity
            or self.target_ref != canonical.target_ref
        ):
            return ExpectedHeadAdvanceResult(outcome="expected-head-unsupported")
        if prepared.remote_identity != self.remote_identity or prepared.target_ref != self.target_ref:
            return ExpectedHeadAdvanceResult(outcome="expected-head-unsupported")
        if prepared.prepared_result_oid != prepared.candidate_oid:
            return ExpectedHeadAdvanceResult(outcome="result-shape-unsupported")
        if prepared.prepared_identity_digest != prepared_identity_digest(prepared):
            return ExpectedHeadAdvanceResult(outcome="prepared-identity-mismatch")
        return None

    def validate_observations(self, prepared: PreparedAdvance) -> ExpectedHeadAdvanceResult | None:
        """Validate repository and exact named refs before object upload.

        Returns:
            A refusal result, or None when observations match.
        """
        repository = self.port.preflight_repository()
        canonical = self.push_capability.canonical_identity
        if canonical is None:
            return ExpectedHeadAdvanceResult(outcome="expected-head-unsupported")
        observed_identity = (
            repository.remote_identity,
            repository.hostname,
            repository.repository_owner,
            repository.repository_name,
            repository.target_ref,
        )
        canonical_identity = (
            canonical.canonical_remote_identity,
            canonical.hostname,
            canonical.repository_owner,
            canonical.repository_name,
            canonical.target_ref,
        )
        if not repository.available or observed_identity != canonical_identity:
            return ExpectedHeadAdvanceResult(outcome="expected-head-unsupported")
        target = self.port.observe_ref(ref=self.target_ref)
        if not target.available:
            return ExpectedHeadAdvanceResult(outcome="reconciliation-required")
        if target.oid != prepared.expected_target_oid:
            return ExpectedHeadAdvanceResult(outcome="target-stale")
        candidate = self.port.observe_ref(ref=prepared.candidate_ref)
        if not candidate.available or candidate.oid != prepared.candidate_oid:
            return ExpectedHeadAdvanceResult(outcome="candidate-mismatch")
        return None

    def validate_objects(self, prepared: PreparedAdvance) -> ExpectedHeadAdvanceResult | None:
        """Validate immutable object type, tree, parent, and ancestry facts.

        Returns:
            A refusal result, or None when object facts match.
        """
        facts = {
            fact.oid: fact
            for fact in self.port.object_facts(
                oids=(
                    prepared.expected_target_oid,
                    prepared.candidate_oid,
                    prepared.prepared_result_oid,
                    prepared.prepared_tree_oid,
                )
            )
        }
        target_facts = facts.get(prepared.expected_target_oid)
        result_facts = facts.get(prepared.prepared_result_oid)
        tree_facts = facts.get(prepared.prepared_tree_oid)
        if target_facts is None or result_facts is None or tree_facts is None:
            return ExpectedHeadAdvanceResult(outcome="prepared-identity-mismatch")
        if (
            target_facts.object_type != "commit"
            or result_facts.object_type != "commit"
            or tree_facts.object_type != "tree"
        ):
            return ExpectedHeadAdvanceResult(outcome="prepared-identity-mismatch")
        if (
            result_facts.tree_oid != prepared.prepared_tree_oid
            or result_facts.parent_oids != prepared.ordered_parent_oids
        ):
            return ExpectedHeadAdvanceResult(outcome="prepared-identity-mismatch")
        if prepared.expected_target_oid not in result_facts.ancestors:
            return ExpectedHeadAdvanceResult(outcome="non-fast-forward-prepared-result")
        return None

    def classify_attempt(self, prepared: PreparedAdvance, attempt: GitPushAttempt) -> ExpectedHeadAdvanceResult:
        """Classify one push only after observing the target again.

        Returns:
            The reconciled stable outcome.
        """
        observed = self.port.observe_ref(ref=self.target_ref)
        if observed.available and observed.oid == prepared.prepared_result_oid:
            outcome = "advanced" if attempt.succeeded else "advanced-after-reconciliation"
            return ExpectedHeadAdvanceResult(outcome=outcome)
        if observed.available and observed.oid != prepared.expected_target_oid:
            return ExpectedHeadAdvanceResult(outcome="target-stale")
        return ExpectedHeadAdvanceResult(
            outcome="transport-failed" if not attempt.transmitted else "reconciliation-required"
        )
