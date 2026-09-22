"""Mutation-runner executable probe contract tests."""

from __future__ import annotations

import pytest

from tests_sam import run_merge_train_t2_mutations as runner
from tests_sam.run_merge_train_t2_mutations import ProbeResult, run_self_test_probes


def test_f25_runner_executes_every_self_test_probe() -> None:
    results = run_self_test_probes()
    assert {result.identity for result in results} == {
        "RUN-NOOP",
        "RUN-WRONG-FILE",
        "RUN-DESELECT",
        "RUN-HANG-TREE",
        "RUN-PIPE-FILL",
        "RUN-NO-WORKDIR",
        "RUN-WRONG-REPOSITORY",
    }
    for result in results:
        assert result.passed
        assert result.argv
        assert result.cwd
        assert result.repository_identity
        assert isinstance(result.stdout, bytes)
        assert isinstance(result.stderr, bytes)


def test_f25_runner_cannot_synthesize_probe_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    failed = ProbeResult(
        identity="RUN-HANG-TREE",
        passed=False,
        argv=("probe",),
        cwd="/tmp",
        repository_identity="repo",
        returncode=0,
        timed_out=False,
        stdout=b"",
        stderr=b"",
    )
    monkeypatch.setattr(runner, "run_self_test_probes", lambda: (failed,))
    assert not runner.runner_self_tests()
