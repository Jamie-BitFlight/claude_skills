"""Mutation-runner executable probe contract tests."""

from __future__ import annotations

from tests_sam.run_merge_train_t2_mutations import run_self_test_probes


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
