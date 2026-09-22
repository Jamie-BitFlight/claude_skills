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
from pathlib import Path

import pytest
from dh_core.git_push import GateRunner, LocalBareGitPushPort
from dh_core.integration_branch import GitPushCapability, IntegrationBranchAdvancer
from dh_core.ledger import store
from dh_core.merge_evidence import MergeEvidenceStore


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
    return GitPushCapability(
        identity="local-cap",
        remote_identity=str(remote),
        target_ref_pattern="refs/heads/integration/t2",
        actor_identity="test",
        actor_permissions_snapshot_digest="sha256:" + "1" * 64,
        rules_snapshot_digest="sha256:" + "2" * 64,
        proof_evidence_digest="sha256:" + "3" * 64,
        proof_transcript_digest="sha256:" + "4" * 64,
        git_version="test",
        supports_expected_head_advance=True,
    )


def test_f14_local_bare_push_uses_exact_old_and_prepared_result(tmp_path: Path) -> None:
    work, remote, base, candidate = repository(tmp_path)
    port = LocalBareGitPushPort(
        workdir=work, remote="origin", remote_identity=str(remote), target_ref="refs/heads/integration/t2"
    )
    advancer = IntegrationBranchAdvancer(
        port,
        capability(remote),
        remote_identity=str(remote),
        target_ref="refs/heads/integration/t2",
        candidate_ref="refs/heads/candidate",
    )

    prepared = advancer.prepare(candidate)
    result = advancer.advance(prepared)

    assert prepared.expected_target_oid == base
    assert result.outcome == "advanced"
    assert git(work, "ls-remote", "origin", "refs/heads/integration/t2").split()[0] == candidate


def test_f14_workdir_guard_refuses_before_git_mutation(tmp_path: Path) -> None:
    work, remote, _base, candidate = repository(tmp_path)
    port = LocalBareGitPushPort(
        workdir=work / "missing", remote="origin", remote_identity=str(remote), target_ref="refs/heads/integration/t2"
    )

    attempt = port.push_exact(expected_target_oid="a" * 40, prepared_result_oid=candidate)

    assert not attempt.transmitted
    assert attempt.stdout == b""


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
    child = "import os,time; print(os.getpid(),flush=True); time.sleep(60)"
    parent = (
        "import os,subprocess,sys,time; print(os.getpid(),flush=True); "
        f"subprocess.Popen([sys.executable,'-c',{child!r}]); "
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
    time.sleep(0.1)
    for pid in pids:
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
