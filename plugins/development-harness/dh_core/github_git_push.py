"""Credential-safe GitHub smart-push adapter."""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

from backlog_core.github_client import resolve_token
from pydantic import BaseModel, ConfigDict

from dh_core.git_push import LocalBareGitPushPort, ProcessResult, run_bounded
from dh_core.integration_branch import GitPushCapability, RepositoryIdentityObservation


class GitHubCapabilityObservation(BaseModel):
    """Exact runtime facts compared with one production admission."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    hostname: str
    repository_id: int
    repository: str
    target_ref: str
    actor: str
    actor_permissions_snapshot_digest: str
    rules_snapshot_digest: str
    git_version: str
    configuration_digest: str
    evidence_digest: str
    result_shape: str
    atomic_review_guard: bool


class GitHubCapabilityAdmission(BaseModel):
    """Human-admitted runtime identity and proof binding."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    observation: GitHubCapabilityObservation
    capability: GitPushCapability

    @classmethod
    def from_receipt(cls, observation: GitHubCapabilityObservation) -> GitHubCapabilityAdmission:
        """Construct admission from trusted receipt data rather than a supplied capability."""
        raise NotImplementedError

    def evaluate(self, observed: GitHubCapabilityObservation) -> GitPushCapability:
        """Fail closed unless every semantic runtime fact matches.

        Returns:
            The admitted capability, with support disabled on any drift.
        """
        supported = (
            observed == self.observation
            and observed.target_ref != "refs/heads/main"
            and observed.result_shape == "DIRECT_FAST_FORWARD"
            and not observed.atomic_review_guard
        )
        return self.capability.model_copy(update={"supports_expected_head_advance": supported})


class GitHubGitPushPort(LocalBareGitPushPort):
    """Run exact smart pushes with an ephemeral askpass credential channel."""

    def __init__(
        self,
        *,
        workdir: Path,
        authenticated_remote: str,
        remote_identity: str,
        target_ref: str,
        token: str | None = None,
        timeout_seconds: float = 30,
    ) -> None:
        """Bind one GitHub repository without retaining a credential in identity or argv."""
        super().__init__(
            workdir=workdir,
            remote=authenticated_remote,
            remote_identity=remote_identity,
            target_ref=target_ref,
            timeout_seconds=timeout_seconds,
        )
        self.token = resolve_token(token)

    def git(self, *args: str) -> ProcessResult:
        """Run Git with ephemeral askpass after the explicit repository guard.

        Returns:
            Complete output without credential-bearing argv.
        """
        guard = run_bounded(("git", "rev-parse", "--show-toplevel"), cwd=self.workdir, timeout_seconds=5)
        if guard.returncode != 0 or Path(os.fsdecode(guard.stdout).strip()).resolve() != self.workdir:
            return ProcessResult(
                argv=("git", *args), returncode=None, stdout=b"", stderr=b"", spawn_error="repository-identity-mismatch"
            )
        with tempfile.TemporaryDirectory(prefix="dh-git-askpass-") as temporary:
            suffix = ".bat" if os.name == "nt" else ".sh"
            askpass = Path(temporary) / f"askpass{suffix}"
            if os.name == "nt":
                askpass.write_text(
                    "@echo %~1| findstr /I Username >nul && (echo x-access-token) || (echo %DH_GIT_TOKEN%)\r\n",
                    encoding="utf-8",
                )
            else:
                askpass.write_text(
                    "#!/bin/sh\ncase \"$1\" in *Username*) printf '%s\\n' x-access-token;; "
                    "*) printf '%s\\n' \"$DH_GIT_TOKEN\";; esac\n",
                    encoding="utf-8",
                )
                askpass.chmod(askpass.stat().st_mode | stat.S_IXUSR)
            environment = {
                **os.environ,
                "GIT_ASKPASS": str(askpass),
                "GIT_TERMINAL_PROMPT": "0",
                "DH_GIT_TOKEN": self.token,
            }
            return run_bounded(("git", *args), cwd=self.workdir, timeout_seconds=self.timeout_seconds, env=environment)

    def preflight_repository(self) -> RepositoryIdentityObservation:
        """Verify remote reachability without exposing its credential.

        Returns:
            Bound identity and availability.
        """
        result = self.git("ls-remote", "--refs", self.remote, self.target_ref)
        return RepositoryIdentityObservation(remote_identity=self.remote_identity, available=result.returncode == 0)
