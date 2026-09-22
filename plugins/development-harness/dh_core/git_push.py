"""Bounded complete-output gate and exact-lease Git push adapters."""

from __future__ import annotations

import base64
import json
import os
import shlex
import shutil
import signal
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from dh_core.integration_branch import GitObjectFacts, GitPushAttempt, RefObservation, RepositoryIdentityObservation
from dh_core.merge_evidence import MergeEvidenceStore


@dataclass(frozen=True)
class ProcessResult:
    """Complete binary subprocess outcome."""

    argv: tuple[str, ...]
    returncode: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    spawn_error: str | None = None


def run_bounded(
    argv: tuple[str, ...], *, cwd: Path, timeout_seconds: float, env: Mapping[str, str] | None = None
) -> ProcessResult:
    """Run one argv with complete output and descendant-tree timeout.

    Returns:
        The complete binary outcome.
    """
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            env=dict(env) if env is not None else None,
        )
    except OSError as exc:
        return ProcessResult(argv=argv, returncode=None, stdout=b"", stderr=b"", spawn_error=str(exc))
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        return ProcessResult(argv=argv, returncode=process.returncode, stdout=stdout, stderr=stderr)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            taskkill = shutil.which("taskkill")
            if taskkill is None:
                process.kill()
            else:
                subprocess.run(
                    (taskkill, "/PID", str(process.pid), "/T", "/F"),
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    check=False,
                )
        else:
            os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        return ProcessResult(argv=argv, returncode=process.returncode, stdout=stdout, stderr=stderr, timed_out=True)


class GateRunner:
    """Run frozen gate commands and retain complete binary evidence."""

    def __init__(self, evidence: MergeEvidenceStore, *, workdir: Path, timeout_seconds: float = 300) -> None:
        """Bind evidence, explicit workdir, and one total command deadline."""
        self.evidence = evidence
        self.workdir = workdir.resolve()
        self.timeout_seconds = timeout_seconds

    def run(self, commands: tuple[str, ...], subject_sha: str) -> tuple[str, ...]:
        """Run every command and return immutable evidence digests.

        Returns:
            One complete evidence digest per successful command.
        """
        digests: list[str] = []
        for command in commands:
            result = run_bounded(tuple(shlex.split(command)), cwd=self.workdir, timeout_seconds=self.timeout_seconds)
            record = json.dumps(
                {
                    "argv": result.argv,
                    "subject_sha": subject_sha,
                    "returncode": result.returncode,
                    "timed_out": result.timed_out,
                    "spawn_error": result.spawn_error,
                    "stdout_base64": base64.b64encode(result.stdout).decode("ascii"),
                    "stderr_base64": base64.b64encode(result.stderr).decode("ascii"),
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            digests.append(self.evidence.put(record, "application/vnd.dh.gate+json").digest)
            if result.returncode != 0 or result.timed_out or result.spawn_error is not None:
                raise RuntimeError("quality-gate-failed")
        return tuple(digests)


class LocalBareGitPushPort:
    """Explicit-workdir Git smart-push adapter for a bound bare remote."""

    def __init__(
        self, *, workdir: Path, remote: str, remote_identity: str, target_ref: str, timeout_seconds: float = 30
    ) -> None:
        """Bind one object database, remote identity, and full target ref."""
        self.workdir = workdir.resolve()
        self.remote = remote
        self.remote_identity = remote_identity
        self.target_ref = target_ref
        self.timeout_seconds = timeout_seconds

    def git(self, *args: str) -> ProcessResult:
        """Run Git only after the explicit workdir identity guard.

        Returns:
            Complete Git output.
        """
        guard = run_bounded(("git", "rev-parse", "--show-toplevel"), cwd=self.workdir, timeout_seconds=5)
        if guard.returncode != 0 or Path(os.fsdecode(guard.stdout).strip()).resolve() != self.workdir:
            return ProcessResult(
                argv=("git", *args), returncode=None, stdout=b"", stderr=b"", spawn_error="repository-identity-mismatch"
            )
        return run_bounded(("git", *args), cwd=self.workdir, timeout_seconds=self.timeout_seconds)

    def preflight_repository(self) -> RepositoryIdentityObservation:
        """Observe whether the explicit workdir is the bound repository.

        Returns:
            Repository identity and availability.
        """
        result = self.git("remote", "get-url", self.remote)
        return RepositoryIdentityObservation(remote_identity=self.remote_identity, available=result.returncode == 0)

    def observe_ref(self, *, ref: str) -> RefObservation:
        """Observe one exact remote full ref.

        Returns:
            Exact OID and availability.
        """
        result = self.git("ls-remote", "--refs", self.remote, ref)
        text = os.fsdecode(result.stdout).strip().split()
        return RefObservation(
            ref=ref, oid=text[0] if result.returncode == 0 and text else None, available=result.returncode == 0
        )

    def object_facts(self, *, oids: tuple[str, ...]) -> tuple[GitObjectFacts, ...]:
        """Read immutable object types, commit trees, parents, and ancestry.

        Returns:
            One fact record per requested OID.
        """
        facts: list[GitObjectFacts] = []
        for oid in dict.fromkeys(oids):
            kind = self.git("cat-file", "-t", oid)
            object_type = os.fsdecode(kind.stdout).strip()
            tree_oid = None
            parents: tuple[str, ...] = ()
            ancestors: list[str] = []
            if object_type == "commit":
                shown = self.git("show", "-s", "--format=%T %P", oid)
                fields = os.fsdecode(shown.stdout).strip().split()
                tree_oid, parents = fields[0], tuple(fields[1:])
                ancestors.extend(
                    possible
                    for possible in dict.fromkeys(oids)
                    if possible != oid and self.git("merge-base", "--is-ancestor", possible, oid).returncode == 0
                )
            facts.append(
                GitObjectFacts(
                    oid=oid,
                    object_type=cast("Literal['commit', 'tree', 'blob', 'tag']", object_type),
                    tree_oid=tree_oid,
                    parent_oids=parents,
                    ancestors=tuple(ancestors),
                )
            )
        return tuple(facts)

    def push_exact(self, *, expected_target_oid: str, prepared_result_oid: str) -> GitPushAttempt:
        """Push exact new OID with one explicit expected-old lease.

        Returns:
            Complete push attempt evidence.
        """
        result = self.git(
            "push",
            "--porcelain",
            f"--force-with-lease={self.target_ref}:{expected_target_oid}",
            self.remote,
            f"{prepared_result_oid}:{self.target_ref}",
        )
        return GitPushAttempt(
            transmitted=result.spawn_error is None,
            succeeded=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
        )
