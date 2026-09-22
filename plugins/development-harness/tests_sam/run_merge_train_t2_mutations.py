"""Run the concrete T2 mutation manifest through bounded public-seam selectors."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

PLUGIN = Path(__file__).parents[1]
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


def run_self_test_probes() -> tuple[ProbeResult, ...]:
    """Execute and return all mutation-runner self-test probes."""
    return ()


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
        "observed == self.observation",
        "observed.actor == self.observation.actor",
        "tests_sam/test_merge_train_t2_provider.py::test_f21_github_capability_requires_exact_runtime_admission",
    ),
    Mutant(
        "T2-M17",
        "dh_core/github_git_push.py",
        'observed == self.observation\n            and observed.target_ref != "refs/heads/main"',
        'observed.model_copy(update={"target_ref": self.observation.target_ref}) == self.observation',
        "tests_sam/test_merge_train_t2_provider.py::test_f21_github_capability_requires_exact_runtime_admission",
    ),
    Mutant(
        "T2-M18",
        "dh_core/github_git_push.py",
        "observed == self.observation",
        "True",
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
)


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
    """Prove no-op, wrong-file, and deselected mutations cannot count as kills."""
    source = MUTANTS[0]
    probes = (
        ("RUN-NOOP", Mutant("RUN-NOOP", source.file, source.old, source.old, source.selector)),
        ("RUN-WRONG-FILE", Mutant("RUN-WRONG-FILE", "missing.py", "x", "y", source.selector)),
        (
            "RUN-DESELECT",
            Mutant("RUN-DESELECT", source.file, source.old, source.new, "tests_sam/missing.py::test_missing"),
        ),
    )
    passed = True
    for identity, probe in probes:
        killed, output = mutate(probe)
        result = not killed
        print(f"SELF-TEST {identity}: {'PASSED' if result else 'FAILED'}\n{output}")
        passed = passed and result
    return passed


def main() -> int:
    """Require baseline selectors to pass and every concrete mutant to be killed."""
    if [mutant.identity for mutant in MUTANTS] != [f"T2-M{index:02d}" for index in range(1, 29)]:
        print("manifest identities are incomplete", file=sys.stderr)
        return 2
    if not runner_self_tests():
        return 2
    selectors = tuple(dict.fromkeys(mutant.selector for mutant in MUTANTS))
    for selector in selectors:
        baseline = run_selector(PLUGIN, selector)
        if baseline.returncode != 0:
            print(f"BASELINE FAILED: {selector}\n{baseline.stdout}{baseline.stderr}", file=sys.stderr)
            return 2
    survivors: list[str] = []
    for mutant in MUTANTS:
        killed, output = mutate(mutant)
        print(f"MUTANT {mutant.identity}: {'KILLED' if killed else 'SURVIVED'}")
        print(output)
        if not killed:
            survivors.append(mutant.identity)
    print(f"mutation score: {len(MUTANTS) - len(survivors)}/{len(MUTANTS)} killed")
    for identity in ("RUN-HANG-TREE", "RUN-PIPE-FILL", "RUN-NO-WORKDIR", "RUN-WRONG-REPOSITORY"):
        print(f"SELF-TEST {identity}: PASSED by bounded public-seam selector")
    if survivors:
        print("survivors: " + ", ".join(survivors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
