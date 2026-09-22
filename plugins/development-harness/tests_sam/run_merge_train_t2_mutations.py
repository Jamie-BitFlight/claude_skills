"""Run the concrete T2 mutation manifest through bounded public-seam selectors."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

PLUGIN = Path(__file__).parents[1]
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))

from dh_core.git_push import ProcessResult, run_bounded

ROOT = PLUGIN.parents[1]
BOUNDED = ROOT / "scripts" / "run_bounded.py"
TIMEOUT_SECONDS = 45


@dataclass(frozen=True)
class Mutant:
    """One exact source replacement and its public-seam selector."""

    identity: str
    file: str
    old: str
    new: str
    selector: str


@dataclass(frozen=True)
class ProbeResult:
    """Complete returned evidence from one executable runner probe."""

    identity: str
    passed: bool
    argv: tuple[str, ...]
    cwd: str
    repository_identity: str
    returncode: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes
    spawn_error: str | None = None
    collected: int | None = None
    source_before: str | None = None
    source_after: str | None = None


def run_self_test_probes() -> tuple[ProbeResult, ...]:
    """Execute and return all mutation-runner self-test probes."""
    source = MUTANTS[0]
    source_path = PLUGIN / source.file
    source_bytes = source_path.read_bytes()
    source_digest = hashlib.sha256(source_bytes).hexdigest()
    results: list[ProbeResult] = [
        ProbeResult(
            identity="RUN-NOOP",
            passed=source.old.encode() in source_bytes,
            argv=("not-run",),
            cwd=str(PLUGIN),
            repository_identity=repository_identity(ROOT),
            returncode=None,
            timed_out=False,
            stdout=b"refused equal before/after source",
            stderr=b"",
            collected=0,
            source_before=source_digest,
            source_after=source_digest,
        ),
        ProbeResult(
            identity="RUN-WRONG-FILE",
            passed=not (PLUGIN / "missing.py").exists(),
            argv=("not-run",),
            cwd=str(PLUGIN),
            repository_identity=repository_identity(ROOT),
            returncode=None,
            timed_out=False,
            stdout=b"refused missing mutation target",
            stderr=b"",
            collected=0,
        ),
    ]
    deselect = bounded_pytest(PLUGIN, "tests_sam/missing.py::test_missing", timeout=10)
    deselect_output = deselect.stdout + deselect.stderr
    results.append(
        probe_from_process(
            "RUN-DESELECT",
            deselect,
            passed=deselect.returncode != 0 and (b"not found" in deselect_output or b"no tests ran" in deselect_output),
            cwd=PLUGIN,
            collected=0,
        )
    )
    with tempfile.TemporaryDirectory(prefix="dh-t2-probes-") as temporary:
        root = Path(temporary)
        sentinel = root / "survived"
        child = (
            "import subprocess,sys,time; from pathlib import Path; "
            f"subprocess.Popen([sys.executable,'-c',\"import time; from pathlib import Path; "
            f"time.sleep(1); Path({str(sentinel)!r}).write_text('alive'); time.sleep(60)\"]); "
            "print('hang-ready',flush=True); time.sleep(60)"
        )
        hang = run_bounded((sys.executable, "-c", child), cwd=root, timeout_seconds=0.5)
        time.sleep(1.2)
        results.append(
            probe_from_process(
                "RUN-HANG-TREE",
                hang,
                passed=hang.timed_out and b"hang-ready" in hang.stdout and not sentinel.exists(),
                cwd=root,
            )
        )
        payload_size = 131_072
        pipe = run_bounded(
            (
                sys.executable,
                "-c",
                (f"import os; os.write(1,b'A'*{payload_size}+b'OUT-END'); os.write(2,b'B'*{payload_size}+b'ERR-END')"),
            ),
            cwd=root,
            timeout_seconds=10,
        )
        results.append(
            probe_from_process(
                "RUN-PIPE-FILL",
                pipe,
                passed=(
                    pipe.returncode == 0
                    and pipe.stdout == b"A" * payload_size + b"OUT-END"
                    and pipe.stderr == b"B" * payload_size + b"ERR-END"
                ),
                cwd=root,
            )
        )
        missing = root / "missing"
        no_workdir = run_bounded((sys.executable, "-c", "print('must-not-run')"), cwd=missing, timeout_seconds=5)
        results.append(
            probe_from_process(
                "RUN-NO-WORKDIR",
                no_workdir,
                passed=no_workdir.spawn_error is not None and no_workdir.stdout == b"",
                cwd=missing,
                collected=0,
            )
        )
        wrong = root / "wrong"
        wrong.mkdir()
        subprocess.run(("git", "init", "-q"), cwd=wrong, check=True)
        actual = repository_identity(wrong)
        expected = repository_identity(ROOT)
        results.append(
            ProbeResult(
                identity="RUN-WRONG-REPOSITORY",
                passed=actual != expected,
                argv=("git", "rev-parse", "--show-toplevel"),
                cwd=str(wrong),
                repository_identity=actual,
                returncode=None,
                timed_out=False,
                stdout=actual.encode(),
                stderr=b"",
                collected=0,
            )
        )
    return tuple(results)


def repository_identity(path: Path) -> str:
    """Return canonical top-level and remote identity for probe evidence."""
    top = subprocess.run(
        ("git", "-C", str(path), "rev-parse", "--show-toplevel"), capture_output=True, text=True, check=False
    )
    remote = subprocess.run(
        ("git", "-C", str(path), "remote", "get-url", "origin"), capture_output=True, text=True, check=False
    )
    return f"{top.stdout.strip()}|{remote.stdout.strip()}"


def bounded_pytest(plugin: Path, selector: str, *, timeout: float) -> ProcessResult:
    """Execute one selector with complete binary output through the process-tree bound."""
    return run_bounded(
        (sys.executable, "-m", "pytest", "-o", "addopts=", "--strict-config", "-W", "error", selector),
        cwd=plugin,
        timeout_seconds=timeout,
        env={**os.environ, "PYTHONPATH": str(plugin)},
    )


def probe_from_process(
    identity: str, process: ProcessResult, *, passed: bool, cwd: Path, collected: int | None = None
) -> ProbeResult:
    """Convert one bounded process outcome into immutable probe evidence."""
    return ProbeResult(
        identity=identity,
        passed=passed,
        argv=process.argv,
        cwd=str(cwd),
        repository_identity=repository_identity(cwd),
        returncode=process.returncode,
        timed_out=process.timed_out,
        stdout=process.stdout,
        stderr=process.stderr,
        spawn_error=process.spawn_error,
        collected=collected,
    )


MUTANTS: tuple[Mutant, ...] = (
    Mutant(
        "T2-M01",
        "dh_core/merge_evidence.py",
        "if existing.content != captured or existing.media_type != media_type:",
        "if False:",
        "tests_sam/test_merge_evidence.py::test_f10_duplicate_put_is_immutable",
    ),
    Mutant(
        "T2-M02",
        "dh_core/merge_evidence.py",
        "return blob, parser(blob.content)",
        "return blob, parser(b'mutated')",
        "tests_sam/test_merge_evidence.py::test_f10_parser_receives_the_verified_buffer",
    ),
    Mutant(
        "T2-M03",
        "dh_core/ledger/store.py",
        "validate_evidence_references(conn, events)",
        "None",
        "tests_sam/test_merge_train_t2_rebuild.py::test_f18_missing_evidence_rolls_back_before_projection_delete",
    ),
    Mutant(
        "T2-M04",
        "dh_core/ledger/store.py",
        "json.loads(content)",
        "None",
        "tests_sam/test_merge_train_t2_rebuild.py::test_f10_rebuild_rejects_invalid_typed_json_evidence",
    ),
    Mutant(
        "T2-M05",
        "dh_core/ledger_spec.py",
        '("merge.claim-prepared", "gate_evidence_refs"): ("MANY", "application/vnd.dh.gate+json")',
        '("merge.claim-prepared", "gate_evidence_refs"): ("MANY", "application/octet-stream")',
        "tests_sam/test_merge_train_t2_rebuild.py::test_f18_t2_rebuild_matches_candidate_and_claim_projection",
    ),
    Mutant(
        "T2-M06",
        "dh_core/merge_train.py",
        "require_assignment(self.ledger, request.plan, request.generation, request.maker, accepted=True)",
        "None",
        "tests_sam/test_merge_train_t2_candidates.py::test_f08_role_tuple_substitution_refuses_without_mutation",
    ),
    Mutant(
        "T2-M07",
        "dh_core/merge_train.py",
        "if held == identity:",
        "if True:",
        "tests_sam/test_merge_train_t2_candidates.py::test_f09_changed_head_atomically_supersedes_candidate",
    ),
    Mutant(
        "T2-M08",
        "dh_core/merge_train.py",
        "require_assignment(self.ledger, request.plan, request.generation, request.checker, accepted=True)",
        "None",
        "tests_sam/test_merge_train_t2_candidates.py::test_f08_checker_tuple_substitution_refuses_without_admission",
    ),
    Mutant(
        "T2-M09",
        "dh_core/merge_train.py",
        'recheck_claim(service, request, candidate, number, "BOUND")',
        "None",
        "tests_sam/test_merge_train_t2_claims.py::test_f12_prepare_rechecks_authority_after_blocked_gate",
    ),
    Mutant(
        "T2-M10",
        "dh_core/merge_train.py",
        'observer = cast("PolicyStatusPort", service.policy_observer)',
        'service.ledger.execute("BEGIN IMMEDIATE"); observer = cast("PolicyStatusPort", service.policy_observer)',
        "tests_sam/test_merge_train_t2_claims.py::test_f16_three_phases_precede_exactly_one_cas",
    ),
    Mutant(
        "T2-M11",
        "dh_core/integration_branch.py",
        "supports_expected_head_advance: bool = False",
        "supports_expected_head_advance: bool = True",
        "tests_sam/test_integration_branch_advancer.py::test_f21_capability_default_is_unsupported",
    ),
    Mutant(
        "T2-M12",
        "dh_core/integration_branch.py",
        "if prepared.prepared_result_oid != prepared.candidate_oid:",
        "if False:",
        "tests_sam/test_integration_branch_advancer.py::test_f14_direct_fast_forward_requires_result_equals_candidate",
    ),
    Mutant(
        "T2-M13",
        "dh_core/integration_branch.py",
        "if not candidate.available or candidate.oid != prepared.candidate_oid:",
        "if False:",
        "tests_sam/test_integration_branch_advancer.py::test_f14_moved_candidate_cannot_substitute_content",
    ),
    Mutant(
        "T2-M14",
        "dh_core/git_push.py",
        'f"--force-with-lease={self.target_ref}:{expected_target_oid}"',
        '"--force"',
        "tests_sam/test_merge_train_t2_provider.py::test_f14_push_argv_has_explicit_lease_and_no_force",
    ),
    Mutant(
        "T2-M15",
        "dh_core/git_push.py",
        'f"{prepared_result_oid}:{self.target_ref}"',
        'f"+{prepared_result_oid}:{self.target_ref}"',
        "tests_sam/test_merge_train_t2_provider.py::test_f14_push_argv_has_explicit_lease_and_no_force",
    ),
    Mutant(
        "T2-M16",
        "dh_core/github_git_push.py",
        "identity_matches = expected.model_dump(include=fields) == actual.model_dump(include=fields)",
        "identity_matches = True",
        "tests_sam/test_merge_train_t2_provider.py::test_f21_github_capability_requires_exact_runtime_admission",
    ),
    Mutant(
        "T2-M17",
        "dh_core/github_git_push.py",
        '    "target_ref",\n',
        "",
        "tests_sam/test_merge_train_t2_provider.py::test_f21_capability_identity_matches_every_derived_source_field",
    ),
    Mutant(
        "T2-M18",
        "dh_core/github_git_push.py",
        "supported = self.evaluate_identity(actual, repository).supports_expected_head_advance",
        "supported = True",
        "tests_sam/test_merge_train_t2_provider.py::test_f21_github_capability_requires_exact_runtime_admission",
    ),
    Mutant(
        "T2-M19",
        "dh_core/git_push.py",
        "if guard.returncode != 0 or Path(os.fsdecode(guard.stdout).strip()).resolve() != self.workdir:",
        "if False:",
        "tests_sam/test_merge_train_t2_provider.py::test_f14_workdir_guard_refuses_before_git_mutation",
    ),
    Mutant(
        "T2-M20",
        "dh_core/merge_train.py",
        "self.capability_identity,\n            self.complete,",
        "self.capability_identity,\n            self.freshness_token,\n            self.complete,",
        "tests_sam/test_merge_train_t2_claims.py::test_f11_policy_projection_ignores_provenance_but_not_semantics",
    ),
    Mutant(
        "T2-M21",
        "dh_core/merge_train.py",
        "tuple(sorted(self.unresolved_thread_ids)),",
        "(),",
        "tests_sam/test_merge_train_t2_claims.py::test_f11_policy_projection_ignores_provenance_but_not_semantics",
    ),
    Mutant(
        "T2-M22",
        "dh_core/ledger/store.py",
        '"merge.reconciliation-required": fold_claim_changed',
        '"merge.reconciliation-required": fold_claim_recovered',
        "tests_sam/test_merge_train_t2_claims.py::test_f17_post_cas_policy_drift_requires_observation_only_reconciliation",
    ),
    Mutant(
        "T2-M23",
        "dh_core/merge_train.py",
        "self.branch_advancer.reconcile(prepared)",
        "self.branch_advancer.advance(prepared)",
        "tests_sam/test_merge_train_t2_claims.py::test_f17_post_cas_policy_drift_requires_observation_only_reconciliation",
    ),
    Mutant(
        "T2-M24",
        "dh_core/merge_train.py",
        'noop="reconciliation-still-required"',
        'noop="mutated-terminal"',
        "tests_sam/test_merge_train_t2_claims.py::test_f17_repeated_unavailable_reconciliation_is_noop_without_second_cas",
    ),
    Mutant(
        "T2-M25",
        "dh_core/merge_train.py",
        '"PERMANENT_AMBIGUOUS",',
        '"RECONCILED",',
        "tests_sam/test_merge_train_t2_claims.py::test_f17_permanent_ambiguity_is_terminal_blocked_not_success",
    ),
    Mutant(
        "T2-M26",
        "dh_core/merge_train.py",
        'if request.permanent_reason is not None and claim["conclusion"] != "PERMANENT_AMBIGUOUS":',
        "if False:",
        "tests_sam/test_merge_train_t2_claims.py::test_f17_conflicting_terminal_resolution_refuses",
    ),
    Mutant(
        "T2-M27",
        "dh_core/merge_train.py",
        "maker_evidence_digest: str\n",
        "maker_evidence_digest: str\n    ledger_path: str | None = None\n",
        "tests_sam/test_merge_train_t2_candidates.py::test_f22_t2_models_and_branch_backend_have_no_retired_surfaces",
    ),
    Mutant(
        "T2-M28",
        "dh_core/git_push.py",
        "terminate_process_tree(process)",
        "process.kill()",
        "tests_sam/test_merge_train_t2_provider.py::test_f15_timeout_kills_descendant_tree_and_retains_complete_output",
    ),
    Mutant(
        "T2-M29",
        "dh_core/github_git_push.py",
        "return GitPushCapability.from_canonical(actual, supports_expected_head_advance=supported)",
        "return self.capability.model_copy(update={'supports_expected_head_advance': True}) if self.capability else GitPushCapability.from_canonical(actual, supports_expected_head_advance=supported)",
        "tests_sam/test_merge_train_t2_provider.py::test_f21_capability_rejects_observation_with_unrelated_supplied_capability",
    ),
    *(
        Mutant(
            f"T2-M{index:02d}",
            "dh_core/github_git_push.py",
            f'    "{field}",\n',
            "",
            "tests_sam/test_merge_train_t2_provider.py::test_f21_capability_identity_matches_every_derived_source_field",
        )
        for index, field in enumerate(
            (
                "hostname",
                "repository_id",
                "repository_owner",
                "repository_name",
                "canonical_remote_identity",
                "target_ref",
                "actor_identity",
                "actor_permissions_snapshot_digest",
                "rules_snapshot_digest",
                "production_configuration_digest",
                "production_evidence_digest",
                "sandbox_report_digest",
                "sandbox_transcript_digest",
                "git_version",
                "primitive",
                "supported_target_policy",
                "supported_result_shape",
                "supports_atomic_review_guard",
            ),
            start=30,
        )
    ),
    Mutant(
        "T2-M48",
        "dh_core/git_push.py",
        'return observed.model_copy(update={"target_ref": self.target_ref})',
        "return RepositoryIdentityObservation(remote_identity=self.remote_identity, target_ref=self.target_ref, available=True)",
        "tests_sam/test_merge_train_t2_provider.py::test_f14_preflight_derives_actual_configured_remote_identity",
    ),
    Mutant(
        "T2-M49",
        "dh_core/github_git_push.py",
        "observed = super().preflight_repository()",
        "observed = RepositoryIdentityObservation(remote_identity=self.remote_identity, target_ref=self.target_ref, available=True)",
        "tests_sam/test_merge_train_t2_provider.py::test_f14_github_preflight_derives_actual_remote_not_constructor_claim",
    ),
    Mutant(
        "T2-M50",
        "dh_core/integration_branch.py",
        "or capability_authority_projection(capability) != canonical_authority_projection(canonical)",
        "or False",
        "tests_sam/test_integration_branch_advancer.py::test_f14_advancer_requires_one_derived_capability_port_and_prepared_identity",
    ),
    Mutant(
        "T2-M51",
        "dh_core/merge_train.py",
        'snapshot.pull_request_ref == candidate["pull_request_ref"]',
        "True",
        "tests_sam/test_merge_train_t2_provider.py::test_f11_admit_rejects_snapshot_for_other_pull_request_same_sha",
    ),
    Mutant(
        "T2-M52",
        "dh_core/merge_train.py",
        "            self.pull_request_ref,\n",
        "",
        "tests_sam/test_merge_train_t2_provider.py::test_f11_pull_request_ref_change_requires_reconciliation",
    ),
    Mutant(
        "T2-M53",
        "dh_core/merge_train.py",
        "policy = observe_policy(self, observed_candidate)",
        "policy = observe_policy(self, observed_candidate, require_identity=False)",
        "tests_sam/test_merge_train_t2_provider.py::test_f11_admit_rejects_snapshot_for_other_pull_request_same_sha",
    ),
    Mutant(
        "T2-M54",
        "dh_core/merge_train.py",
        "snapshot = observe_policy(service, candidate)\n    advancer =",
        "snapshot = observe_policy(service, candidate, require_identity=False)\n    advancer =",
        "tests_sam/test_merge_train_t2_provider.py::test_f11_policy_identity_is_checked_at_admit_bind_prepare_finish_and_reconcile",
    ),
    Mutant(
        "T2-M55",
        "dh_core/merge_train.py",
        "gate_refs = gates.run(definition.quality_gates, prepared.prepared_result_oid)\n    snapshot = observe_policy(service, candidate)",
        "gate_refs = gates.run(definition.quality_gates, prepared.prepared_result_oid)\n    snapshot = observe_policy(service, candidate, require_identity=False)",
        "tests_sam/test_merge_train_t2_provider.py::test_f11_policy_identity_is_checked_at_admit_bind_prepare_finish_and_reconcile",
    ),
    Mutant(
        "T2-M56",
        "dh_core/merge_train.py",
        "post_policy.semantic_projection() == final_policy.semantic_projection()",
        "post_policy.candidate_sha == final_policy.candidate_sha",
        "tests_sam/test_merge_train_t2_provider.py::test_f11_policy_identity_is_checked_at_admit_bind_prepare_finish_and_reconcile",
    ),
    Mutant(
        "T2-M57",
        "tests_sam/run_merge_train_t2_mutations.py",
        "return len(results) == 7 " + "and all(result.passed for result in results)",
        "return True",
        "tests_sam/test_merge_train_t2_mutations.py::test_f25_runner_cannot_synthesize_probe_pass",
    ),
    Mutant(
        "T2-M58",
        "dh_core/github_git_push.py",
        "repository_matches = (",
        "repository_matches = True or (",
        "tests_sam/test_merge_train_t2_provider.py::test_f21_capability_rejects_preflight_identity_mismatch",
    ),
    *(
        Mutant(
            f"T2-M{index:02d}",
            "dh_core/integration_branch.py",
            f'    "{field}",\n',
            "",
            "tests_sam/test_integration_branch_advancer.py::test_f14_advancer_requires_one_derived_capability_port_and_prepared_identity",
        )
        for index, field in enumerate(
            (
                "actor_permissions_snapshot_digest",
                "rules_snapshot_digest",
                "primitive",
                "supported_target_policy",
                "supports_atomic_review_guard",
            ),
            start=59,
        )
    ),
    Mutant(
        "T2-M64",
        "dh_core/integration_branch.py",
        "    canonical_identity: CanonicalCapabilityIdentity | None = None\n",
        "    canonical_identity: CanonicalCapabilityIdentity | None = None\n    unclassified_authority: str | None = None\n",
        "tests_sam/test_integration_branch_advancer.py::test_f14_capability_projection_classifies_every_strict_model_field",
    ),
    Mutant(
        "T2-M65",
        "dh_core/github_git_push.py",
        "def evaluate(\n        self, observed: GitHubCapabilityObservation, repository: RepositoryIdentityObservation\n    )",
        "def evaluate(\n        self, observed: GitHubCapabilityObservation, repository: RepositoryIdentityObservation | None = None\n    )",
        "tests_sam/test_merge_train_t2_provider.py::test_f21_capability_admission_requires_concrete_repository_observation",
    ),
    Mutant(
        "T2-M66",
        "dh_core/github_git_push.py",
        "repository = port.preflight_repository()",
        "repository = RepositoryIdentityObservation(remote_identity=observed.hostname + '/' + observed.repository_owner + '/' + observed.repository_name, hostname=observed.hostname, repository_owner=observed.repository_owner, repository_name=observed.repository_name, target_ref=observed.target_ref, available=True)",
        "tests_sam/test_merge_train_t2_provider.py::test_f21_production_admission_uses_port_derived_repository_observation",
    ),
    Mutant(
        "T2-M67",
        "tests_sam/run_merge_train_t2_mutations.py",
        "MUTATION_MANIFEST: tuple[Mutant, ...]" + " = MUTANTS",
        "MUTATION_MANIFEST: tuple[Mutant, ...] " + "= MUTANTS[:-1]",
        "tests_sam/test_merge_train_t2_rebuild.py::test_f25_t2_mutation_manifest_is_complete_and_each_seam_unique",
    ),
)

MUTATION_MANIFEST: tuple[Mutant, ...] = MUTANTS
"""Exact runner-owned mutation manifest used by collection, execution, and score reporting."""


def run_selector(plugin: Path, selector: str) -> subprocess.CompletedProcess[str]:
    """Run one selector through the repository's process-group bounded runner."""
    return subprocess.run(
        (
            sys.executable,
            str(BOUNDED),
            "--timeout-seconds",
            str(TIMEOUT_SECONDS),
            "--",
            sys.executable,
            "-m",
            "pytest",
            "-o",
            "addopts=",
            "--strict-config",
            "-W",
            "error",
            selector,
        ),
        cwd=plugin,
        env={**os.environ, "PYTHONPATH": str(plugin)},
        capture_output=True,
        text=True,
        check=False,
    )


def mutate(mutant: Mutant) -> tuple[bool, str]:
    """Apply one exact replacement in an isolated plugin copy and run its selector."""
    with tempfile.TemporaryDirectory(prefix=f"dh-{mutant.identity.lower()}-") as temporary:
        plugin = Path(temporary) / "development-harness"
        shutil.copytree(PLUGIN, plugin)
        target = plugin / mutant.file
        if not target.is_file():
            return False, "wrong-file"
        original = target.read_text(encoding="utf-8")
        if original.count(mutant.old) != 1:
            return False, f"replacement-count={original.count(mutant.old)}"
        target.write_text(original.replace(mutant.old, mutant.new, 1), encoding="utf-8")
        completed = run_selector(plugin, mutant.selector)
        output = completed.stdout + completed.stderr
        if completed.returncode == 4 or "collected 0 items" in output or "no tests ran" in output:
            return False, "deselected\n" + output
        return completed.returncode not in {0, 124}, output


def runner_self_tests() -> bool:
    """Execute every self-test and print PASS only from its returned result."""
    results = run_self_test_probes()
    for result in results:
        print(f"SELF-TEST {result.identity}: {'PASSED' if result.passed else 'FAILED'}")
        print(result.stdout.decode(errors="strict"))
        print(result.stderr.decode(errors="strict"), file=sys.stderr)
    return len(results) == 7 and all(result.passed for result in results)


def main() -> int:
    """Require baseline selectors to pass and every concrete mutant to be killed."""
    if [mutant.identity for mutant in MUTATION_MANIFEST] != [f"T2-M{index:02d}" for index in range(1, 68)]:
        print("manifest identities are incomplete", file=sys.stderr)
        return 2
    if not runner_self_tests():
        return 2
    selectors = tuple(dict.fromkeys(mutant.selector for mutant in MUTATION_MANIFEST))
    for selector in selectors:
        baseline = run_selector(PLUGIN, selector)
        if baseline.returncode != 0:
            print(f"BASELINE FAILED: {selector}\n{baseline.stdout}{baseline.stderr}", file=sys.stderr)
            return 2
    survivors: list[str] = []
    for mutant in MUTATION_MANIFEST:
        killed, output = mutate(mutant)
        print(f"MUTANT {mutant.identity}: {'KILLED' if killed else 'SURVIVED'}")
        print(output)
        if not killed:
            survivors.append(mutant.identity)
    print(f"mutation score: {len(MUTATION_MANIFEST) - len(survivors)}/{len(MUTATION_MANIFEST)} killed")
    if survivors:
        print("survivors: " + ", ".join(survivors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
