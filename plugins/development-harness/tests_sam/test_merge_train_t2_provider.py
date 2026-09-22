"""Concrete local Git push and bounded gate tests."""

from __future__ import annotations

import base64
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest
from dh_core.git_push import GateRunner, LocalBareGitPushPort, ProcessResult
from dh_core.github_git_push import (
    GitHubCapabilityAdmission,
    GitHubCapabilityObservation,
    GitHubGitPushPort,
    canonical_capability_identity,
)
from dh_core.integration_branch import (
    CanonicalCapabilityIdentity,
    GitPushCapability,
    IntegrationBranchAdvancer,
    RepositoryIdentityObservation,
)
from dh_core.ledger import store
from dh_core.merge_evidence import MergeEvidenceStore
from dh_core.merge_train import AdmitCandidate, MergeNext, PolicySnapshot, ReconcileClaim, SubmitCandidate

from tests_sam.test_merge_train_t2_candidates import accept_assignment, service
from tests_sam.test_merge_train_t2_claims import admitted


def git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(("git", *args), cwd=cwd, capture_output=True, text=True, check=True)
    return completed.stdout.strip()


def repository(tmp_path: Path) -> tuple[Path, Path, str, str]:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    subprocess.run(("git", "init", "--bare", str(remote)), check=True, capture_output=True)
    subprocess.run(("git", "clone", str(remote), str(work)), check=True, capture_output=True)
    git(work, "config", "user.email", "test@example.invalid")
    git(work, "config", "user.name", "Test")
    (work / "value").write_text("base", encoding="utf-8")
    git(work, "add", "value")
    git(work, "commit", "-m", "base")
    base = git(work, "rev-parse", "HEAD")
    git(work, "push", "origin", f"{base}:refs/heads/integration/t2")
    (work / "value").write_text("candidate", encoding="utf-8")
    git(work, "commit", "-am", "candidate")
    candidate = git(work, "rev-parse", "HEAD")
    git(work, "push", "origin", f"{candidate}:refs/heads/candidate")
    return work, remote, base, candidate


def capability(remote: Path) -> GitPushCapability:
    identity = CanonicalCapabilityIdentity(
        hostname="file",
        repository_id=0,
        repository_owner="",
        repository_name=remote.name,
        canonical_remote_identity=remote.resolve().as_uri(),
        target_ref="refs/heads/integration/t2",
        actor_identity="test",
        actor_permissions_snapshot_digest="sha256:" + "1" * 64,
        rules_snapshot_digest="sha256:" + "2" * 64,
        production_configuration_digest="sha256:" + "3" * 64,
        production_evidence_digest="sha256:" + "4" * 64,
        sandbox_report_digest="sha256:" + "3" * 64,
        sandbox_transcript_digest="sha256:" + "4" * 64,
        git_version="test",
        primitive="git-smart-push-explicit-lease",
        supported_target_policy="direct-fast-forward",
        supported_result_shape="DIRECT_FAST_FORWARD",
        supports_atomic_review_guard=False,
    )
    return GitPushCapability(
        identity=identity.digest,
        remote_identity=identity.canonical_remote_identity,
        target_ref_pattern="refs/heads/integration/t2",
        actor_identity="test",
        actor_permissions_snapshot_digest="sha256:" + "1" * 64,
        rules_snapshot_digest="sha256:" + "2" * 64,
        proof_evidence_digest="sha256:" + "3" * 64,
        proof_transcript_digest="sha256:" + "4" * 64,
        git_version="test",
        supports_expected_head_advance=True,
        canonical_identity=identity,
    )


def production_observation(**changes: object) -> GitHubCapabilityObservation:
    values = {
        "hostname": "github.com",
        "repository_id": 1080600074,
        "repository_owner": "Jamie-BitFlight",
        "repository_name": "claude_skills",
        "target_ref": "refs/heads/integration/runtime-integrity",
        "actor": "Jamie-BitFlight",
        "actor_permissions_snapshot_digest": "sha256:" + "1" * 64,
        "rules_snapshot_digest": "sha256:" + "2" * 64,
        "git_version": "2.55.0",
        "configuration_digest": "sha256:" + "3" * 64,
        "evidence_digest": "sha256:" + "4" * 64,
        "result_shape": "DIRECT_FAST_FORWARD",
        "atomic_review_guard": False,
    }
    values.update(changes)
    return GitHubCapabilityObservation.model_validate(values)


def test_f21_github_capability_requires_exact_runtime_admission(tmp_path: Path) -> None:
    admitted = capability(tmp_path).model_copy(
        update={
            "remote_identity": "github.com/Jamie-BitFlight/claude_skills",
            "target_ref_pattern": "refs/heads/integration/runtime-integrity",
        }
    )
    observation = production_observation()
    admission = GitHubCapabilityAdmission(observation=observation, capability=admitted)

    assert admission.evaluate(observation).supports_expected_head_advance
    for drift in (
        {"repository_id": 1},
        {"actor": "other"},
        {"rules_snapshot_digest": "sha256:" + "9" * 64},
        {"git_version": "2.54.0"},
        {"evidence_digest": "sha256:" + "8" * 64},
        {"target_ref": "refs/heads/main"},
        {"atomic_review_guard": True},
    ):
        assert not admission.evaluate(production_observation(**drift)).supports_expected_head_advance


def test_f21_capability_rejects_observation_with_unrelated_supplied_capability(tmp_path: Path) -> None:
    observation = production_observation()
    attacker = capability(tmp_path).model_copy(
        update={"remote_identity": "github.com/attacker/other", "actor_identity": "attacker", "git_version": "0.0.0"}
    )
    admission = GitHubCapabilityAdmission.from_receipt(observation).model_copy(update={"capability": attacker})

    result = admission.evaluate(observation)

    assert result.remote_identity == "github.com/Jamie-BitFlight/claude_skills"
    assert result.actor_identity == "Jamie-BitFlight"
    assert result.git_version == "2.55.0"


def test_f21_capability_rejects_preflight_identity_mismatch() -> None:
    receipt = production_observation()
    admission = GitHubCapabilityAdmission.from_receipt(receipt)
    actual = canonical_capability_identity(receipt)
    attacker = RepositoryIdentityObservation(
        remote_identity="github.com/attacker/other",
        hostname="github.com",
        repository_owner="attacker",
        repository_name="other",
        target_ref=actual.target_ref,
        available=True,
    )

    assert not admission.evaluate_identity(actual, attacker).supports_expected_head_advance


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("hostname", "evil.example"),
        ("repository_id", 1),
        ("repository_owner", "attacker"),
        ("repository_name", "other"),
        ("canonical_remote_identity", "github.com/attacker/other"),
        ("target_ref", "refs/heads/main"),
        ("actor_identity", "attacker"),
        ("actor_permissions_snapshot_digest", "sha256:" + "7" * 64),
        ("rules_snapshot_digest", "sha256:" + "8" * 64),
        ("git_version", "0.0.0"),
        ("production_configuration_digest", "sha256:" + "9" * 64),
        ("production_evidence_digest", "sha256:" + "a" * 64),
        ("supported_result_shape", "MERGE_COMMIT"),
        ("supports_atomic_review_guard", True),
        ("sandbox_report_digest", "sha256:" + "b" * 64),
        ("sandbox_transcript_digest", "sha256:" + "c" * 64),
        ("primitive", "other"),
        ("supported_target_policy", "other"),
    ],
)
def test_f21_capability_identity_matches_every_derived_source_field(field: str, value: object) -> None:
    receipt = production_observation()
    admission = GitHubCapabilityAdmission.from_receipt(receipt)
    actual = canonical_capability_identity(receipt).model_copy(update={field: value})

    result = admission.evaluate_identity(actual)

    assert not result.supports_expected_head_advance


def test_f14_preflight_derives_actual_configured_remote_identity(tmp_path: Path) -> None:
    work, remote, _base, _candidate = repository(tmp_path)
    port = LocalBareGitPushPort(
        workdir=work,
        remote="origin",
        remote_identity="github.com/attacker/other",
        target_ref="refs/heads/integration/t2",
    )

    observed = port.preflight_repository()

    assert observed.available
    assert observed.remote_identity != "github.com/attacker/other"
    assert Path(observed.remote_identity.removeprefix("file://")) == remote.resolve()


def test_f14_github_preflight_derives_actual_remote_not_constructor_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    port = GitHubGitPushPort(
        workdir=tmp_path,
        authenticated_remote="git@github.com:Jamie-BitFlight/claude_skills.git",
        remote_identity="github.com/attacker/other",
        target_ref="refs/heads/integration/runtime-integrity",
        token="test-token",
    )

    def scripted(*args: str) -> ProcessResult:
        if args == ("remote", "get-url", port.remote):
            return ProcessResult(argv=args, returncode=2, stdout=b"", stderr=b"unknown remote")
        if args == ("remote",):
            return ProcessResult(argv=args, returncode=0, stdout=b"origin\n", stderr=b"")
        if args == ("remote", "get-url", "origin"):
            return ProcessResult(
                argv=args, returncode=0, stdout=b"git@github.com:Jamie-BitFlight/claude_skills.git\n", stderr=b""
            )
        return ProcessResult(argv=args, returncode=0, stdout=b"oid\tref\n", stderr=b"")

    monkeypatch.setattr(port, "git", scripted)
    observed = port.preflight_repository()

    assert observed.remote_identity == "github.com/Jamie-BitFlight/claude_skills"
    assert observed.repository_owner == "Jamie-BitFlight"
    assert observed.repository_name == "claude_skills"


def test_f11_admit_rejects_snapshot_for_other_pull_request_same_sha(tmp_path: Path) -> None:
    train, connection = service(tmp_path)
    maker = accept_assignment(train, connection, "T1")
    candidate = train.submit(
        SubmitCandidate(
            plan="Pt2",
            generation=1,
            branch="candidate",
            pull_request_ref="PR-EXPECTED",
            candidate_sha="b" * 40,
            base_sha="a" * 40,
            maker=maker,
            maker_evidence_digest=train.evidence.put(b'{"maker":true}', "application/json").digest,
        )
    )
    checker = accept_assignment(train, connection, "T2")
    checker_evidence = train.evidence.put(b'{"checker":true}', "application/json")

    class WrongPullRequest:
        def observe(self, candidate_sha: str, pull_request_ref: str) -> PolicySnapshot:
            return PolicySnapshot(
                candidate_sha=candidate_sha,
                pull_request_ref="PR-OTHER",
                required_checks=(("tests", candidate_sha, "success"),),
                capability_identity="cap",
                complete=True,
                available=True,
                freshness_token="fresh",
                observed_at=datetime(2026, 1, 1),
            )

    train.policy_observer = WrongPullRequest()
    with pytest.raises(store.Refusal):
        train.admit(
            AdmitCandidate(
                plan="Pt2",
                generation=1,
                task="T1",
                candidate_number=candidate.candidate_number,
                checker=checker,
                checker_evidence_digest=checker_evidence.digest,
            )
        )
    assert connection.execute("SELECT admitted_seq FROM merge_candidates").fetchone()[0] is None


def test_f11_pull_request_ref_change_requires_reconciliation() -> None:
    expected = PolicySnapshot(
        candidate_sha="b" * 40,
        pull_request_ref="PR-EXPECTED",
        required_checks=(("tests", "b" * 40, "success"),),
        capability_identity="cap",
        complete=True,
        available=True,
        freshness_token="one",
        observed_at=datetime(2026, 1, 1),
    )
    other = expected.model_copy(update={"pull_request_ref": "PR-OTHER", "freshness_token": "two"})
    assert expected.semantic_projection() != other.semantic_projection()


@pytest.mark.parametrize(("phase", "wrong_call"), [("bind", 1), ("prepare", 2), ("finish", 3)])
def test_f11_policy_identity_is_checked_at_admit_bind_prepare_finish_and_reconcile(
    tmp_path: Path, phase: str, wrong_call: int
) -> None:
    train, _connection, integrator, _policies, _gates, _branch = admitted(tmp_path)

    class WrongAtCall:
        calls = 0

        def observe(self, candidate_sha: str, pull_request_ref: str) -> PolicySnapshot:
            self.calls += 1
            return PolicySnapshot(
                candidate_sha=candidate_sha,
                pull_request_ref="PR-OTHER" if self.calls == wrong_call else pull_request_ref,
                required_checks=(("tests", candidate_sha, "success"),),
                capability_identity="cap-1",
                complete=True,
                available=True,
                freshness_token=f"token-{self.calls}",
                observed_at=datetime(2026, 1, 1, 0, 0, self.calls),
            )

    train.policy_observer = WrongAtCall()
    if phase in {"bind", "prepare"}:
        with pytest.raises(store.Refusal):
            train.merge_next(MergeNext(plan="Pt2", generation=1, integrator=integrator))
    else:
        result = train.merge_next(MergeNext(plan="Pt2", generation=1, integrator=integrator))
        assert result.phase == "RECONCILIATION_REQUIRED"


def test_f11_policy_identity_is_checked_during_reconcile(tmp_path: Path) -> None:
    train, _connection, integrator, policies, _gates, branch = admitted(tmp_path, drift=True)
    unresolved = train.merge_next(MergeNext(plan="Pt2", generation=1, integrator=integrator))
    policies.drift = False
    branch.outcome = "advanced-after-reconciliation"

    class OtherPullRequest:
        def observe(self, candidate_sha: str, pull_request_ref: str) -> PolicySnapshot:
            return PolicySnapshot(
                candidate_sha=candidate_sha,
                pull_request_ref="PR-OTHER",
                required_checks=(("tests", candidate_sha, "success"),),
                capability_identity="cap-1",
                complete=True,
                available=True,
                freshness_token="reconcile",
                observed_at=datetime(2026, 1, 2),
            )

    train.policy_observer = OtherPullRequest()
    result = train.reconcile(ReconcileClaim(plan="Pt2", claim_number=unresolved.claim_number))
    assert result.noop == "reconciliation-still-required"


def test_f14_local_bare_push_uses_exact_old_and_prepared_result(tmp_path: Path) -> None:
    work, remote, base, candidate = repository(tmp_path)
    port = LocalBareGitPushPort(
        workdir=work, remote="origin", remote_identity=str(remote), target_ref="refs/heads/integration/t2"
    )
    advancer = IntegrationBranchAdvancer(
        port,
        capability(remote),
        remote_identity=remote.resolve().as_uri(),
        target_ref="refs/heads/integration/t2",
        candidate_ref="refs/heads/candidate",
    )

    prepared = advancer.prepare(candidate)
    result = advancer.advance(prepared)

    assert prepared.expected_target_oid == base
    assert result.outcome == "advanced"
    assert git(work, "ls-remote", "origin", "refs/heads/integration/t2").split()[0] == candidate


def test_f14_workdir_guard_refuses_before_git_mutation(tmp_path: Path) -> None:
    _work, remote, _base, candidate = repository(tmp_path)
    port = LocalBareGitPushPort(
        workdir=tmp_path, remote="origin", remote_identity=str(remote), target_ref="refs/heads/integration/t2"
    )

    attempt = port.push_exact(expected_target_oid="a" * 40, prepared_result_oid=candidate)

    assert not attempt.transmitted
    assert attempt.stdout == b""
    missing = LocalBareGitPushPort(
        workdir=tmp_path / "missing",
        remote="origin",
        remote_identity=str(remote),
        target_ref="refs/heads/integration/t2",
    ).push_exact(expected_target_oid="a" * 40, prepared_result_oid=candidate)
    assert not missing.transmitted


def test_f14_push_argv_has_explicit_lease_and_no_force(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    port = LocalBareGitPushPort(
        workdir=tmp_path, remote="origin", remote_identity="local/test", target_ref="refs/heads/integration/t2"
    )
    observed: tuple[str, ...] = ()

    def capture(*args: str) -> ProcessResult:
        nonlocal observed
        observed = args
        return ProcessResult(argv=("git", *args), returncode=0, stdout=b"ok", stderr=b"")

    monkeypatch.setattr(port, "git", capture)
    port.push_exact(expected_target_oid="a" * 40, prepared_result_oid="b" * 40)

    assert f"--force-with-lease=refs/heads/integration/t2:{'a' * 40}" in observed
    assert "--force" not in observed
    assert not any(value.startswith("+") for value in observed)


def test_f15_gate_runner_retains_complete_binary_stdout_stderr(tmp_path: Path) -> None:
    connection = store.open_ledger(tmp_path / "dh.db")
    evidence = MergeEvidenceStore(connection)
    runner = GateRunner(evidence, workdir=tmp_path)
    script = "import os; os.write(1,b'out\\x00end'); os.write(2,b'err\\xffend')"

    digests = runner.run((shlex.join((sys.executable, "-c", script)),), "b" * 40)
    record = json.loads(evidence.get(digests[0]).content)

    assert base64.b64decode(record["stdout_base64"]) == b"out\x00end"
    assert base64.b64decode(record["stderr_base64"]) == b"err\xffend"


def test_f22_installed_plugin_imports_t2_from_unrelated_workdir(tmp_path: Path) -> None:
    plugin = Path(__file__).parents[1]
    installed = tmp_path / "installed" / "development-harness"
    unrelated = tmp_path / "unrelated"
    shutil.copytree(plugin, installed)
    unrelated.mkdir()
    script = (
        "from dh_core.merge_train import MergeNext, TrainSupersession; "
        "from dh_core.git_push import GateRunner, LocalBareGitPushPort; "
        "from dh_core.integration_branch import IntegrationBranchAdvancer; print('installed-t2-ok')"
    )

    completed = subprocess.run(
        (sys.executable, "-c", script),
        cwd=unrelated,
        env={**os.environ, "PYTHONPATH": str(installed)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "installed-t2-ok"


def test_f15_timeout_kills_descendant_tree_and_retains_complete_output(tmp_path: Path) -> None:
    connection = store.open_ledger(tmp_path / "dh.db")
    evidence = MergeEvidenceStore(connection)
    runner = GateRunner(evidence, workdir=tmp_path, timeout_seconds=0.5)
    sentinel = tmp_path / "child-survived"
    child = (
        "import time; from pathlib import Path; "
        f"time.sleep(1); Path({str(sentinel)!r}).write_text('alive'); time.sleep(60)"
    )
    parent = (
        "import os,subprocess,sys,time; print(os.getpid(),flush=True); "
        f"subprocess.Popen([sys.executable,'-c',{child!r}],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
        "sys.stderr.write('before-timeout\\n'); sys.stderr.flush(); time.sleep(60)"
    )

    with pytest.raises(RuntimeError, match="quality-gate-failed"):
        runner.run((shlex.join((sys.executable, "-c", parent)),), "b" * 40)

    row = connection.execute(
        "SELECT content FROM merge_evidence_blobs WHERE media_type='application/vnd.dh.gate+json'"
    ).fetchone()
    record = json.loads(row[0])
    pids = [int(value) for value in base64.b64decode(record["stdout_base64"]).splitlines()]
    assert record["timed_out"] is True
    assert b"before-timeout" in base64.b64decode(record["stderr_base64"])
    time.sleep(1.3)
    assert not sentinel.exists()
    for pid in pids:
        if sys.platform == "win32":
            tasklist = subprocess.run(
                ("tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"), capture_output=True, text=True, check=False
            )
            assert f'"{pid}"' not in tasklist.stdout
        else:
            with pytest.raises(ProcessLookupError):
                os.kill(pid, 0)
