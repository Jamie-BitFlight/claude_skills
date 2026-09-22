"""Branch-bound expected-head advancement public-seam tests."""

from __future__ import annotations

from dh_core.integration_branch import (
    CanonicalCapabilityIdentity,
    GitObjectFacts,
    GitPushAttempt,
    GitPushCapability,
    IntegrationBranchAdvancer,
    PreparedAdvance,
    RefObservation,
    RepositoryIdentityObservation,
    prepared_identity_digest,
)


class PushSpy:
    def __init__(self) -> None:
        self.pushes: list[tuple[str, str]] = []
        self.refs = {"refs/heads/integration/runtime-integrity": "a" * 40, "refs/heads/candidate": "b" * 40}

    def preflight_repository(self) -> RepositoryIdentityObservation:
        return RepositoryIdentityObservation(remote_identity="github.com/Jamie-BitFlight/claude_skills", available=True)

    def observe_ref(self, *, ref: str) -> RefObservation:
        return RefObservation(ref=ref, oid=self.refs.get(ref), available=True)

    def object_facts(self, *, oids: tuple[str, ...]) -> tuple[GitObjectFacts, ...]:
        return tuple(
            GitObjectFacts(
                oid=oid,
                object_type="tree" if oid == "c" * 40 else "commit",
                tree_oid="c" * 40 if oid != "c" * 40 else None,
                parent_oids=(("a" * 40,) if oid == "b" * 40 else ()),
                ancestors=("a" * 40,) if oid == "b" * 40 else (),
            )
            for oid in oids
        )

    def push_exact(self, *, expected_target_oid: str, prepared_result_oid: str) -> GitPushAttempt:
        self.pushes.append((expected_target_oid, prepared_result_oid))
        self.refs["refs/heads/integration/runtime-integrity"] = prepared_result_oid
        return GitPushAttempt(transmitted=True, succeeded=True, stdout=b"ok", stderr=b"")


def capability(*, supported: bool = True) -> GitPushCapability:
    return GitPushCapability(
        identity="capability-1",
        remote_identity="github.com/Jamie-BitFlight/claude_skills",
        target_ref_pattern="refs/heads/integration/runtime-integrity",
        actor_identity="Jamie-BitFlight",
        actor_permissions_snapshot_digest="sha256:" + "1" * 64,
        rules_snapshot_digest="sha256:" + "2" * 64,
        proof_evidence_digest="sha256:" + "3" * 64,
        proof_transcript_digest="sha256:" + "4" * 64,
        git_version="2.55.0",
        supports_expected_head_advance=supported,
    )


def canonical_identity() -> CanonicalCapabilityIdentity:
    return CanonicalCapabilityIdentity(
        hostname="github.com",
        repository_id=1080600074,
        repository_owner="Jamie-BitFlight",
        repository_name="claude_skills",
        canonical_remote_identity="github.com/Jamie-BitFlight/claude_skills",
        target_ref="refs/heads/integration/runtime-integrity",
        actor_identity="Jamie-BitFlight",
        actor_permissions_snapshot_digest="sha256:" + "1" * 64,
        rules_snapshot_digest="sha256:" + "2" * 64,
        production_configuration_digest="sha256:" + "3" * 64,
        production_evidence_digest="sha256:" + "4" * 64,
        sandbox_report_digest="sha256:" + "5" * 64,
        sandbox_transcript_digest="sha256:" + "6" * 64,
        git_version="2.55.0",
        primitive="git-smart-push-explicit-lease",
        supported_target_policy="direct-fast-forward",
        supported_result_shape="DIRECT_FAST_FORWARD",
        supports_atomic_review_guard=False,
    )


def prepared() -> PreparedAdvance:
    value = PreparedAdvance(
        remote_identity="github.com/Jamie-BitFlight/claude_skills",
        target_ref="refs/heads/integration/runtime-integrity",
        candidate_ref="refs/heads/candidate",
        expected_target_oid="a" * 40,
        candidate_oid="b" * 40,
        prepared_result_oid="b" * 40,
        prepared_tree_oid="c" * 40,
        ordered_parent_oids=("a" * 40,),
        prepared_identity_digest="sha256:" + "0" * 64,
    )
    return value.model_copy(update={"prepared_identity_digest": prepared_identity_digest(value)})


def test_f21_default_capability_false_returns_expected_head_unsupported() -> None:
    port = PushSpy()
    advancer = IntegrationBranchAdvancer(
        port,
        capability(supported=False),
        remote_identity="github.com/Jamie-BitFlight/claude_skills",
        target_ref="refs/heads/integration/runtime-integrity",
    )

    result = advancer.advance(prepared())

    assert result.outcome == "expected-head-unsupported"
    assert port.pushes == []


def test_f21_capability_default_is_unsupported() -> None:
    value = capability().model_dump()
    value.pop("supports_expected_head_advance")
    assert not GitPushCapability.model_validate(value).supports_expected_head_advance


def test_f14_direct_fast_forward_requires_result_equals_candidate() -> None:
    port = PushSpy()
    advancer = IntegrationBranchAdvancer(
        port,
        capability(),
        remote_identity=capability().remote_identity,
        target_ref="refs/heads/integration/runtime-integrity",
    )
    request = prepared().model_copy(update={"prepared_result_oid": "d" * 40})
    request = request.model_copy(update={"prepared_identity_digest": prepared_identity_digest(request)})

    result = advancer.advance(request)

    assert result.outcome == "result-shape-unsupported"
    assert port.pushes == []


def test_f14_atomic_store_rejects_stale_expected_target() -> None:
    port = PushSpy()
    port.refs["refs/heads/integration/runtime-integrity"] = "d" * 40
    advancer = IntegrationBranchAdvancer(
        port,
        capability(),
        remote_identity=capability().remote_identity,
        target_ref="refs/heads/integration/runtime-integrity",
    )

    result = advancer.advance(prepared())

    assert result.outcome == "target-stale"
    assert port.pushes == []


def test_f14_moved_candidate_cannot_substitute_content() -> None:
    port = PushSpy()
    port.refs["refs/heads/candidate"] = "d" * 40
    advancer = IntegrationBranchAdvancer(
        port,
        capability(),
        remote_identity=capability().remote_identity,
        target_ref="refs/heads/integration/runtime-integrity",
    )

    result = advancer.advance(prepared())

    assert result.outcome == "candidate-mismatch"
    assert port.pushes == []


def test_f14_exact_prepared_operands_advance() -> None:
    port = PushSpy()
    advancer = IntegrationBranchAdvancer(
        port,
        capability(),
        remote_identity=capability().remote_identity,
        target_ref="refs/heads/integration/runtime-integrity",
    )

    result = advancer.advance(prepared())

    assert result.outcome == "advanced"
    assert port.pushes == [("a" * 40, "b" * 40)]


def test_f14_advancer_requires_one_derived_capability_port_and_prepared_identity() -> None:
    port = PushSpy()
    admitted = capability().model_copy(update={"canonical_identity": canonical_identity()})
    attacker = admitted.model_copy(update={"actor_identity": "attacker", "git_version": "0.0.0"})
    advancer = IntegrationBranchAdvancer(
        port, attacker, remote_identity=attacker.remote_identity, target_ref="refs/heads/integration/runtime-integrity"
    )

    result = advancer.advance(prepared())

    assert result.outcome == "expected-head-unsupported"
    assert port.pushes == []
