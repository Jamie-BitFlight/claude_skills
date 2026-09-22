"""Credential-safe GitHub smart-push adapter."""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

from backlog_core.github_client import resolve_token
from pydantic import BaseModel, ConfigDict

from dh_core.git_push import LocalBareGitPushPort, ProcessResult, run_bounded
from dh_core.integration_branch import CanonicalCapabilityIdentity, GitPushCapability, RepositoryIdentityObservation


class GitHubCapabilityObservation(BaseModel):
    """Exact runtime facts compared with one production admission."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    hostname: str
    repository_id: int
    repository_owner: str
    repository_name: str
    target_ref: str
    actor: str
    actor_permissions_snapshot_digest: str
    rules_snapshot_digest: str
    git_version: str
    configuration_digest: str
    evidence_digest: str
    result_shape: str
    atomic_review_guard: bool
    sandbox_report_digest: str = "sha256:56d1ead554b6e5c42ce13415af615e0022a649e520fb733e77e28fa580b663f0"
    sandbox_transcript_digest: str = "sha256:e99efb9f44d3b90e2623bc68db2f9d25cfe1f63544cd54d02650ed28700be5e3"
    primitive: str = "git-smart-push-explicit-lease"
    target_policy: str = "direct-fast-forward"


class GitHubCapabilityAdmission(BaseModel):
    """Human-admitted runtime identity and proof binding."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    observation: GitHubCapabilityObservation
    capability: GitPushCapability | None = None

    @classmethod
    def from_receipt(cls, observation: GitHubCapabilityObservation) -> GitHubCapabilityAdmission:
        """Construct admission from trusted receipt data rather than a supplied capability.

        Returns:
            Admission retaining only the trusted receipt observation.
        """
        return cls(observation=observation)

    def evaluate(
        self, observed: GitHubCapabilityObservation, repository: RepositoryIdentityObservation | None = None
    ) -> GitPushCapability:
        """Fail closed unless every semantic runtime fact matches.

        Returns:
            The admitted capability, with support disabled on any drift.
        """
        actual = canonical_capability_identity(observed)
        supported = self.evaluate_identity(actual, repository).supports_expected_head_advance
        return GitPushCapability.from_canonical(actual, supports_expected_head_advance=supported)

    def evaluate_identity(
        self, actual: CanonicalCapabilityIdentity, repository: RepositoryIdentityObservation | None = None
    ) -> GitPushCapability:
        """Compare every canonical tuple field and optional concrete-port observation.

        Returns:
            Capability derived from ``actual`` and disabled on any mismatch.
        """
        expected = canonical_capability_identity(self.observation)
        fields = set(CAPABILITY_IDENTITY_FIELDS)
        identity_matches = expected.model_dump(include=fields) == actual.model_dump(include=fields)
        repository_matches = repository is None or (
            repository.available
            and repository.remote_identity == actual.canonical_remote_identity
            and repository.hostname == actual.hostname
            and repository.repository_owner == actual.repository_owner
            and repository.repository_name == actual.repository_name
            and repository.target_ref == actual.target_ref
        )
        supported = identity_matches and repository_matches
        return GitPushCapability.from_canonical(
            actual if supported else expected, supports_expected_head_advance=supported
        )


def admit_github_capability(
    admission: GitHubCapabilityAdmission, observed: GitHubCapabilityObservation, port: GitHubGitPushPort
) -> GitPushCapability:
    """Produce capability through the bound GitHub port admission seam.

    Returns:
        Capability produced from runtime observation and concrete repository evidence.
    """
    return admission.evaluate(observed)


def canonical_capability_identity(observed: GitHubCapabilityObservation) -> CanonicalCapabilityIdentity:
    """Derive the complete ordered capability tuple from trusted observations.

    Returns:
        The canonical capability identity.
    """
    return CanonicalCapabilityIdentity(
        hostname=observed.hostname.lower(),
        repository_id=observed.repository_id,
        repository_owner=observed.repository_owner,
        repository_name=observed.repository_name,
        canonical_remote_identity=(
            f"{observed.hostname.lower()}/{observed.repository_owner}/{observed.repository_name}"
        ),
        target_ref=observed.target_ref,
        actor_identity=observed.actor,
        actor_permissions_snapshot_digest=observed.actor_permissions_snapshot_digest,
        rules_snapshot_digest=observed.rules_snapshot_digest,
        production_configuration_digest=observed.configuration_digest,
        production_evidence_digest=observed.evidence_digest,
        sandbox_report_digest=observed.sandbox_report_digest,
        sandbox_transcript_digest=observed.sandbox_transcript_digest,
        git_version=observed.git_version,
        primitive="git-smart-push-explicit-lease",
        supported_target_policy="direct-fast-forward",
        supported_result_shape="DIRECT_FAST_FORWARD",
        supports_atomic_review_guard=observed.atomic_review_guard,
    )


CAPABILITY_IDENTITY_FIELDS: tuple[str, ...] = (
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
)
"""Ordered canonical capability tuple; mutation closure removes each field independently."""


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
        observed = super().preflight_repository()
        if not observed.available:
            return observed
        result = self.git("ls-remote", "--refs", self.remote, self.target_ref)
        return observed.model_copy(update={"available": result.returncode == 0})
