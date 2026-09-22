"""Provider-aware CLI target resolution without provider API mutation."""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from typing import Annotated
from urllib.parse import urlparse

import typer
from pydantic import ValidationError

from pr_review_contracts import ChangeRequestTarget, RepositoryTarget
from pr_review_gitlab_transport import run_glab
from pr_review_subprocess import DEFAULT_COMMAND_TIMEOUT_SECONDS, run_capture

GitHubDetector = Callable[..., tuple[str, str]]
CommandRunner = Callable[..., str]
MIN_REPOSITORY_SEGMENTS = 2


def validate_github_option(value: str | None) -> str | None:
    """Validate an explicit GitHub owner/repository value.

    Args:
        value: Candidate owner/repository option or ``None`` for detection.

    Returns:
        The validated option, or ``None`` when detection is requested.

    Raises:
        typer.BadParameter: If the value is not exactly owner/repository.
    """
    if value is None:
        return None
    owner, separator, repo = value.partition("/")
    if not separator or not owner or not repo or "/" in repo:
        raise typer.BadParameter("must be 'owner/repo' -- exactly one '/', with both halves non-empty")
    return value


GithubOption = Annotated[
    str | None,
    typer.Option(
        "--github",
        help="Target repository as 'owner/repo'. Detected via gh repo view when omitted.",
        callback=validate_github_option,
    ),
]
ProviderOption = Annotated[
    str | None, typer.Option("--provider", help="Provider: github, gitlab, or auto remote detection.")
]
RepoOption = Annotated[str | None, typer.Option("--repo", help="Provider repository namespace/path.")]
HostOption = Annotated[str | None, typer.Option("--host", help="Bare provider hostname; required with GitLab --repo.")]
ProviderTimeoutOption = Annotated[
    float,
    typer.Option(
        "--provider-timeout-seconds",
        "--gh-timeout-seconds",
        "--glab-timeout-seconds",
        min=0.001,
        help="Positive bound for every provider subprocess.",
    ),
]
DEFAULT_PROVIDER_TIMEOUT_SECONDS = DEFAULT_COMMAND_TIMEOUT_SECONDS


def run_git(arguments: list[str], *, timeout: float | None = None) -> str:
    """Run one bounded read-only Git command.

    Args:
        arguments: Complete Git argument vector after the executable.
        timeout: Positive subprocess bound in seconds.

    Returns:
        Complete standard output.

    Raises:
        subprocess.CalledProcessError: If Git exits non-zero.
        subprocess.TimeoutExpired: If Git exceeds the bound.
    """
    return run_capture(["git", *arguments], timeout=timeout)


def validate_repository_path(value: str) -> str:
    """Validate a nested namespace/repository path.

    Args:
        value: Candidate provider namespace and repository path.

    Returns:
        The unchanged valid path.

    Raises:
        typer.BadParameter: If any required path segment is empty.
    """
    segments = value.split("/")
    if len(segments) < MIN_REPOSITORY_SEGMENTS or any(not segment for segment in segments):
        raise typer.BadParameter("repository must contain non-empty namespace and project segments")
    return value


def github_target(
    github: str | None, number: int, *, timeout: float | None, detector: GitHubDetector
) -> ChangeRequestTarget:
    """Resolve the legacy GitHub option with its established diagnostics.

    Args:
        github: Explicit owner/repository path, or ``None`` for detection.
        number: Positive pull-request number.
        timeout: Positive provider-command bound.
        detector: GitHub repository identity detector.

    Returns:
        A canonical GitHub pull-request target.

    Raises:
        typer.Exit: If repository detection fails.
    """
    if github is None:
        try:
            owner, repo = detector(gh_timeout=timeout)
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValidationError) as exc:
            typer.echo(
                f"Could not detect this checkout's GitHub repository via gh repo view ({exc}). "
                "Pass --github owner/repo to specify it explicitly.",
                err=True,
            )
            raise typer.Exit(code=1) from exc
    else:
        owner, repo = github.split("/", 1)
    return ChangeRequestTarget(
        repository=RepositoryTarget(provider="github", hostname="github.com", full_name=f"{owner}/{repo}"),
        number=number,
    )


def gitlab_repo_view(*, timeout: float | None, runner: CommandRunner = run_glab) -> tuple[str, str]:
    """Detect a GitLab host and nested project path through the configured remote.

    Args:
        timeout: Positive provider-command bound.
        runner: Bounded glab command transport.

    Returns:
        The detected bare host and nested project path.

    Raises:
        typer.BadParameter: If glab returns an invalid repository identity.
    """
    raw = runner(["repo", "view", "--output", "json"], timeout=timeout)
    try:
        payload = json.loads(raw)
        full_name = validate_repository_path(str(payload["path_with_namespace"]))
        parsed = urlparse(str(payload["web_url"]))
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise typer.BadParameter(f"glab repo view returned invalid repository identity: {exc}") from exc
    if not parsed.hostname:
        raise typer.BadParameter("glab repo view returned a web_url without a hostname")
    return parsed.hostname, full_name


def gitlab_target(
    repo: str | None, host: str | None, number: int, *, timeout: float | None, runner: CommandRunner = run_glab
) -> ChangeRequestTarget:
    """Resolve an explicit or remote-detected GitLab merge-request target.

    Args:
        repo: Explicit nested project path, or ``None`` for detection.
        host: Explicit bare GitLab hostname, or ``None`` for detection.
        number: Positive merge-request number.
        timeout: Positive provider-command bound.
        runner: Bounded glab command transport.

    Returns:
        A canonical GitLab merge-request target.

    Raises:
        typer.BadParameter: If target options are incomplete or invalid.
    """
    if (repo is None) != (host is None):
        raise typer.BadParameter("GitLab target requires --repo and --host together, or neither for detection")
    resolved_host, resolved_repo = (
        (host, validate_repository_path(repo)) if repo and host else gitlab_repo_view(timeout=timeout, runner=runner)
    )
    return ChangeRequestTarget(
        repository=RepositoryTarget(provider="gitlab", hostname=resolved_host, full_name=resolved_repo), number=number
    )


def remote_identity(remote: str) -> tuple[str, str]:
    """Parse SSH or HTTPS remote coordinates without classifying the forge.

    Args:
        remote: Complete SSH or HTTPS remote URL.

    Returns:
        The lower-case host and nested repository path.

    Raises:
        typer.BadParameter: If the remote is not a supported URL.
    """
    value = remote.strip()
    if "://" in value:
        parsed = urlparse(value)
        host = parsed.hostname
        path = parsed.path.lstrip("/")
    else:
        match = re.fullmatch(r"(?:[^@]+@)?([^:]+):(.+)", value)
        host, path = (match.group(1), match.group(2)) if match else (None, "")
    if not host:
        raise typer.BadParameter("origin remote is not a supported SSH or HTTPS URL")
    return host.lower(), validate_repository_path(path.removesuffix(".git"))


def auto_target(
    number: int,
    *,
    timeout: float | None,
    github_resolver: Callable[[str | None, int], ChangeRequestTarget],
    git_runner: CommandRunner = run_git,
    glab_runner: CommandRunner = run_glab,
) -> ChangeRequestTarget:
    """Resolve the forge from the current origin and verify custom GitLab identity.

    Args:
        number: Positive change-request number.
        timeout: Positive provider-command bound.
        github_resolver: GitHub target resolver.
        git_runner: Bounded read-only Git command transport.
        glab_runner: Bounded glab command transport.

    Returns:
        A canonical GitHub or GitLab target.

    Raises:
        typer.BadParameter: If the remote and provider identity disagree.
    """
    host, repo = remote_identity(git_runner(["remote", "get-url", "origin"], timeout=timeout))
    if host == "github.com":
        if repo.count("/") != 1:
            raise typer.BadParameter("GitHub origin must be exactly owner/repository")
        return github_resolver(repo, number)
    detected_host, detected_repo = gitlab_repo_view(timeout=timeout, runner=glab_runner)
    if (detected_host.lower(), detected_repo) != (host, repo):
        raise typer.BadParameter("origin remote and glab repo view identify different repositories")
    return gitlab_target(detected_repo, detected_host, number, timeout=timeout, runner=glab_runner)


def resolve_target(
    *,
    provider: str | None,
    repo: str | None,
    host: str | None,
    github: str | None,
    number: int,
    timeout: float | None,
    github_resolver: Callable[[str | None, int], ChangeRequestTarget],
) -> ChangeRequestTarget:
    """Select exactly one provider without mixing legacy and generic options.

    Args:
        provider: Explicit provider name or automatic selection mode.
        repo: Explicit provider repository path.
        host: Explicit provider hostname.
        github: Legacy GitHub owner/repository option.
        number: Positive change-request number.
        timeout: Positive provider-command bound.
        github_resolver: GitHub target resolver.

    Returns:
        The canonical target selected from non-conflicting options.

    Raises:
        typer.BadParameter: If the target options conflict or are invalid.
    """
    if github is not None and (provider not in {None, "github"} or repo is not None or host is not None):
        raise typer.BadParameter("--github cannot be combined with GitLab or generic target options")
    if provider in {None, "github"}:
        if repo is not None or host is not None:
            if provider is None:
                raise typer.BadParameter("--repo/--host require --provider")
            if host not in {None, "github.com"}:
                raise typer.BadParameter("GitHub host must be github.com")
            return github_resolver(repo, number)
        return github_resolver(github, number)
    if provider == "gitlab":
        return gitlab_target(repo, host, number, timeout=timeout)
    if provider == "auto":
        if repo is not None or host is not None:
            raise typer.BadParameter("auto detection cannot be combined with --repo or --host")
        return auto_target(number, timeout=timeout, github_resolver=github_resolver)
    raise typer.BadParameter("provider must be github, gitlab, or auto")
