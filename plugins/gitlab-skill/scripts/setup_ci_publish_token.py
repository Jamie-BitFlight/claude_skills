#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
# ]
# ///
"""Create or repair GitLab CI publishing-token configuration."""

from __future__ import annotations

import configparser
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import NoReturn, Protocol
from urllib.parse import quote, urlparse

from pydantic import BaseModel, Field, SecretStr, ValidationError

RESOURCE_NAME = "ci-publish-token"
VARIABLE_NAME = "CI_PUBLISH_TOKEN"
RESOURCE_DURATION = "8760h"
RESOURCE_DESCRIPTION = "CI/CD token for publishing releases and uploading artifacts"
VARIABLE_DESCRIPTION = "Project access token for CI/CD release publishing and artifact uploads"
MAINTAINER_ACCESS_LEVEL = 40
GLAB_TIMEOUT_SECONDS = 60
PAGE_SIZE = 100
MAX_PORT = 65535
MIN_PROJECT_SEGMENTS = 2
HOST_PATTERN = re.compile(r"(?:[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?)(?::[0-9]{1,5})?")
PROJECT_SEGMENT_PATTERN = re.compile(r"[A-Za-z0-9_.-]+")
HTTP_STATUS_PATTERN = re.compile(r"\bHTTP\s+(?P<status>[0-9]{3})\b", re.IGNORECASE)
HTTP_CLIENT_ERROR_MIN = 400
HTTP_CLIENT_ERROR_MAX_EXCLUSIVE = 500
HTTP_NOT_FOUND = 404
INDETERMINATE_CLIENT_STATUSES = {408, 499}


class TokenManagerError(RuntimeError):
    """A safe, caller-facing token-manager failure."""


class GlabError(TokenManagerError):
    """A redacted glab invocation failure."""

    def __init__(self, operation: str, *, returncode: int | None = None, not_found: bool = False) -> None:
        """Initialize a typed failure without captured process output."""
        self.operation = operation
        self.returncode = returncode
        self.not_found = not_found
        status = f" with exit status {returncode}" if returncode is not None else ""
        super().__init__(f"{operation} failed{status}")


class IndeterminateMutationError(TokenManagerError):
    """A mutation whose remote outcome cannot be inferred safely."""


def is_mutating_glab_command(arguments: Sequence[str]) -> bool:
    """Return whether arguments select a mutating glab operation."""
    prefix = tuple(arguments[:2])
    return prefix in {
        ("token", "create"),
        ("token", "revoke"),
        ("variable", "set"),
        ("variable", "update"),
        ("variable", "delete"),
    }


def mutation_requires_output(arguments: Sequence[str]) -> bool:
    """Return whether successful mutation output is required by its caller."""
    return tuple(arguments[:2]) == ("token", "create")


def explicit_rejection_status(stderr: str) -> int | None:
    """Return an explicit HTTP rejection status, excluding uncertain client-timeout statuses."""
    match = HTTP_STATUS_PATTERN.search(stderr)
    if match is None:
        return None
    status = int(match.group("status"))
    if (
        HTTP_CLIENT_ERROR_MIN <= status < HTTP_CLIENT_ERROR_MAX_EXCLUSIVE
        and status not in INDETERMINATE_CLIENT_STATUSES
    ):
        return status
    return None


class GlabCall(BaseModel):
    """One glab call, with stdin excluded from normal representation."""

    arguments: tuple[str, ...]
    stdin: SecretStr | None = None

    def __init__(self, arguments: tuple[str, ...], stdin: str | None = None) -> None:
        """Initialize a call while wrapping optional stdin as a redacted secret."""
        super().__init__(arguments=arguments, stdin=SecretStr(stdin) if stdin is not None else None)


class VariableSnapshot(BaseModel):
    """Restorable state for one project CI/CD variable."""

    value: SecretStr | None = None
    hidden: bool | None = None
    protected: bool = False
    masked: bool = False
    raw: bool = False
    variable_type: str = "env_var"
    environment_scope: str = "*"
    description: str | None = None


class AccessToken(BaseModel):
    """Relevant project access-token metadata."""

    id: int
    name: str
    expires_at: date


class CreatedToken(BaseModel):
    """A newly created token whose secret is redacted by construction."""

    id: int
    name: str
    token: SecretStr = Field(min_length=1)


class GlabRunner(Protocol):
    """Execution boundary for glab."""

    def run(self, arguments: Sequence[str], *, stdin: str | None = None) -> str:
        """Run glab and return stdout, raising GlabError on failure."""
        ...


class SubprocessGlabRunner:
    """Run glab without a shell and without exposing stdin secrets."""

    def __init__(self, executable: str) -> None:
        """Initialize with the resolved glab executable path."""
        self.executable = executable

    def run(self, arguments: Sequence[str], *, stdin: str | None = None) -> str:
        """Run glab and return stdout.

        Args:
            arguments: Arguments after the glab executable.
            stdin: Optional secret input passed only over standard input.

        Returns:
            Captured standard output.

        Raises:
            GlabError: If glab reports an explicit rejection or a read-only call fails.
            IndeterminateMutationError: If a mutating outcome cannot be established.
        """
        operation = " ".join(("glab", *arguments))
        try:
            completed = subprocess.run(
                [self.executable, *arguments],
                input=stdin.encode("utf-8") if stdin is not None else None,
                capture_output=True,
                check=False,
                timeout=GLAB_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            if is_mutating_glab_command(arguments):
                raise IndeterminateMutationError(f"{operation} timed out; remote state is unknown") from None
            raise GlabError(f"{operation} timed out") from None
        except OSError:
            raise GlabError(f"unable to start {operation}") from None
        stderr = completed.stderr.decode("utf-8", errors="replace")
        if completed.returncode != 0:
            rejection_status = explicit_rejection_status(stderr)
            if is_mutating_glab_command(arguments) and rejection_status is None:
                raise IndeterminateMutationError(
                    f"{operation} ended without explicit GitLab rejection; remote state is unknown"
                )
            not_found = rejection_status == HTTP_NOT_FOUND
            raise GlabError(operation, returncode=completed.returncode, not_found=not_found)
        try:
            return completed.stdout.decode("utf-8")
        except UnicodeDecodeError:
            if is_mutating_glab_command(arguments):
                if mutation_requires_output(arguments):
                    raise IndeterminateMutationError(
                        f"{operation} completed but returned undecodable output; remote state is unknown"
                    ) from None
                return ""
            raise TokenManagerError(f"{operation} returned output that is not valid UTF-8") from None


def parse_json(raw: str, description: str) -> object:
    """Parse glab JSON without repeating potentially sensitive output in errors.

    Returns:
        The decoded JSON value.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise TokenManagerError(f"glab returned invalid JSON for {description}") from None


def load_dotenv(path: Path) -> dict[str, str]:
    """Read simple KEY=VALUE entries without executing the file.

    Returns:
        Values keyed by environment variable name.
    """
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def remote_coordinates(root: Path) -> tuple[str, str]:
    """Return host and project path from the origin URL in .git/config."""
    git_path = root / ".git"
    config_path = git_path / "config"
    if git_path.is_file():
        marker = git_path.read_text(encoding="utf-8").strip()
        if not marker.startswith("gitdir:"):
            raise TokenManagerError("the .git file does not identify a git directory")
        git_dir = Path(marker.removeprefix("gitdir:").strip())
        if not git_dir.is_absolute():
            git_dir = (root / git_dir).resolve()
        config_path = git_dir / "config"
        if not config_path.is_file():
            common_dir = (git_dir / "commondir").read_text(encoding="utf-8").strip()
            config_path = (git_dir / common_dir / "config").resolve()
    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")
    try:
        remote_url = parser['remote "origin"']["url"]
    except KeyError as error:
        raise TokenManagerError("the git origin remote is not configured") from error

    if "://" in remote_url:
        parsed = urlparse(remote_url)
        host = parsed.hostname or ""
        try:
            port = parsed.port
        except ValueError:
            raise TokenManagerError("git origin URL has invalid port") from None
        if port is not None:
            host = f"{host}:{port}"
        project = parsed.path.lstrip("/")
    else:
        address = remote_url.rsplit("@", maxsplit=1)[-1]
        if ":" not in address:
            raise TokenManagerError("the git origin URL is not a supported GitLab URL")
        host, project = address.split(":", maxsplit=1)
    project = project.removesuffix(".git")
    if not host or not project:
        raise TokenManagerError("the git origin URL does not contain a host and project path")
    return host, project


def validate_host(value: str) -> str:
    """Validate a GitLab hostname with an optional numeric port.

    Returns:
        The validated hostname.
    """
    if value != value.strip() or not HOST_PATTERN.fullmatch(value):
        raise TokenManagerError("GitLab host must be a hostname with an optional numeric port")
    if ":" in value:
        port = int(value.rsplit(":", maxsplit=1)[1])
        if not 0 < port <= MAX_PORT:
            raise TokenManagerError("GitLab host port must be between 1 and 65535")
    return value


def validate_project_path(value: str) -> str:
    """Validate a namespaced GitLab project path.

    Returns:
        The validated project path.
    """
    if value != value.strip() or "://" in value:
        raise TokenManagerError("GitLab project path must be a namespaced path without a URL scheme")
    segments = value.split("/")
    if len(segments) < MIN_PROJECT_SEGMENTS or any(
        not PROJECT_SEGMENT_PATTERN.fullmatch(segment) for segment in segments
    ):
        raise TokenManagerError("GitLab project path must contain valid namespace and project segments")
    return value


def persist_local_context(root: Path, values: Mapping[str, str]) -> None:
    """Persist non-secret project coordinates and ensure .env is ignored."""
    env_path = root / ".env"
    existing = load_dotenv(env_path)
    additions = [f"{key}={value}" for key, value in values.items() if key not in existing]
    if additions:
        prefix = "" if not env_path.exists() or env_path.stat().st_size == 0 else "\n"
        with env_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(prefix + "\n".join(additions) + "\n")

    ignore_path = root / ".gitignore"
    ignore_lines = ignore_path.read_text(encoding="utf-8").splitlines() if ignore_path.is_file() else []
    if not any(line.strip() in {".env", "/.env"} for line in ignore_lines):
        prefix = "" if not ignore_path.exists() or ignore_path.stat().st_size == 0 else "\n"
        with ignore_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(f"{prefix}# Ignore localized environment variables\n.env\n")


def variable_write_arguments(
    command: str, project: str, key: str, snapshot: VariableSnapshot, *, harden: bool
) -> tuple[str, ...]:
    """Build metadata-only arguments for glab variable set or update.

    Returns:
        Arguments that never contain the variable value.
    """
    arguments = ["variable", command, key, "--repo", project]
    if harden and command == "set":
        arguments.append("--hidden")
    if harden or snapshot.masked:
        arguments.append("--masked")
    if harden or snapshot.protected:
        arguments.append("--protected")
    if snapshot.raw:
        arguments.append("--raw")
    arguments.extend(("--scope", snapshot.environment_scope, "--type", snapshot.variable_type))
    if snapshot.description is not None:
        arguments.extend(("--description", snapshot.description))
    return tuple(arguments)


def replace_variable(
    runner: GlabRunner, project: str, key: str, value: str, *, original: VariableSnapshot | None = None
) -> None:
    """Reconcile a value according to verified variable visibility."""
    if original is None:
        new_variable = VariableSnapshot(
            hidden=True,
            protected=True,
            masked=True,
            variable_type="env_var",
            environment_scope="*",
            description=VARIABLE_DESCRIPTION,
        )
        runner.run(variable_write_arguments("set", project, key, new_variable, harden=True), stdin=value)
        return

    if original.hidden is None:
        raise TokenManagerError(f"{key} hidden state is unavailable; no mutation was attempted")
    if original.hidden:
        runner.run(variable_write_arguments("update", project, key, original, harden=True), stdin=value)
        return
    if original.value is None:
        raise TokenManagerError(f"{key} is readable but its current value was not returned; no mutation was attempted")

    delete_arguments = ["variable", "delete", key, "--repo", project]
    if original.environment_scope != "*":
        delete_arguments.extend(("--scope", original.environment_scope))
    runner.run(delete_arguments)
    try:
        runner.run(variable_write_arguments("set", project, key, original, harden=True), stdin=value)
    except GlabError as replacement_error:
        try:
            runner.run(
                variable_write_arguments("set", project, key, original, harden=False),
                stdin=original.value.get_secret_value(),
            )
        except GlabError as rollback_error:
            raise TokenManagerError(
                f"hidden replacement failed ({replacement_error}); rollback also failed ({rollback_error})"
            ) from None
        raise TokenManagerError(
            f"hidden replacement failed ({replacement_error}); original variable was restored"
        ) from None


def collect_pages(
    runner: GlabRunner, arguments_for_page: Callable[[int], Sequence[str]], description: str
) -> list[object]:
    """Collect JSON-array pages until the server returns a short page.

    Returns:
        Every item from every page in response order.
    """
    items: list[object] = []
    page = 1
    while True:
        arguments = arguments_for_page(page)
        payload = parse_json(runner.run(arguments), description)
        if not isinstance(payload, list):
            raise TokenManagerError(f"{description} output was not a JSON array")
        items.extend(payload)
        if len(payload) < PAGE_SIZE:
            return items
        page += 1


def active_token_records(runner: GlabRunner, project: str) -> list[object]:
    """Return every active project token record through paginated API requests."""
    encoded_project = quote(project, safe="")
    return collect_pages(
        runner,
        lambda page: ("api", f"projects/{encoded_project}/access_tokens?state=active&page={page}&per_page={PAGE_SIZE}"),
        "active project access tokens",
    )


def discover_tokens(runner: GlabRunner, project: str) -> list[AccessToken]:
    """Return matching active project access tokens, rejecting ambiguous state."""
    payload = active_token_records(runner, project)
    matches: list[AccessToken] = []
    try:
        matches.extend(
            AccessToken.model_validate(item)
            for item in payload
            if isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and (item["name"] == RESOURCE_NAME or item["name"].startswith(f"{RESOURCE_NAME}-"))
        )
    except ValidationError:
        raise TokenManagerError("active project access-token output contained invalid metadata") from None
    matches.sort(key=lambda token: token.id)
    if len(matches) > 1:
        token_ids = ", ".join(str(token.id) for token in matches)
        raise TokenManagerError(
            f"multiple active '{RESOURCE_NAME}' tokens exist (IDs: {token_ids}); revoke all but one"
        )
    return matches


def revoke_token_by_exact_name(runner: GlabRunner, project: str, name: str) -> None:
    """Rediscover one unique token name across all pages and revoke its ID."""
    token = find_token_by_exact_name(runner, project, name)
    try:
        runner.run(("token", "revoke", str(token.id), "--repo", project))
    except IndeterminateMutationError:
        raise IndeterminateMutationError(
            f"token {name} (ID {token.id}) revoke timed out and its status is unknown; inspect GitLab"
        ) from None


def find_token_by_exact_name(runner: GlabRunner, project: str, name: str) -> AccessToken:
    """Return the sole active token with an exact unique name."""
    exact_records = [
        item for item in active_token_records(runner, project) if isinstance(item, dict) and item.get("name") == name
    ]
    if len(exact_records) != 1:
        raise TokenManagerError("created token cleanup could not identify exactly one matching token")
    try:
        return AccessToken.model_validate(exact_records[0])
    except ValidationError:
        raise TokenManagerError("created token cleanup found invalid token metadata") from None


def discover_variable(runner: GlabRunner, project: str) -> VariableSnapshot | None:
    """Return the sole matching project variable after scope-aware discovery."""
    payload = collect_pages(
        runner,
        lambda page: (
            "variable",
            "list",
            "--repo",
            project,
            "--output",
            "json",
            "--page",
            str(page),
            "--per-page",
            str(PAGE_SIZE),
        ),
        "project variables",
    )
    matches = [item for item in payload if isinstance(item, dict) and item.get("key") == VARIABLE_NAME]
    if not matches:
        return None
    if len(matches) > 1:
        scopes = sorted(str(item.get("environment_scope", "*")) for item in matches)
        raise TokenManagerError(
            f"{VARIABLE_NAME} exists in multiple environment scopes ({', '.join(scopes)}); select one manually"
        )
    try:
        return VariableSnapshot.model_validate(matches[0])
    except ValidationError:
        raise TokenManagerError(f"{VARIABLE_NAME} output contained invalid metadata") from None


def verify_permissions(runner: GlabRunner, project: str) -> None:
    """Verify personal-token API scope and Maintainer project access."""
    pat = parse_json(runner.run(("api", "personal_access_tokens/self")), "personal access token")
    if not isinstance(pat, dict) or "api" not in pat.get("scopes", []):
        raise TokenManagerError("the current GITLAB_TOKEN does not have the 'api' scope")
    user = parse_json(runner.run(("api", "user")), "current user")
    if not isinstance(user, dict) or not isinstance(user.get("id"), int):
        raise TokenManagerError("the current GitLab user ID was not returned")
    encoded_project = quote(project, safe="")
    member = parse_json(
        runner.run(("api", f"projects/{encoded_project}/members/all/{user['id']}")), "project membership"
    )
    if not isinstance(member, dict) or not isinstance(member.get("access_level"), int):
        raise TokenManagerError("the project membership access level was not returned")
    if member["access_level"] < MAINTAINER_ACCESS_LEVEL:
        raise TokenManagerError(f"the current GITLAB_TOKEN does not have Maintainer (40) access to {project}")


def create_token(runner: GlabRunner, project: str, now: datetime) -> CreatedToken:
    """Create a uniquely named project access token.

    Returns:
        The new token ID and redacted secret value emitted by glab.
    """
    name = f"{RESOURCE_NAME}-{now.astimezone(UTC):%Y%m%d%H%M%S}-{uuid.uuid4().hex}"
    try:
        raw = runner.run((
            "token",
            "create",
            name,
            "--repo",
            project,
            "--access-level",
            "maintainer",
            "--scope",
            "api",
            "--duration",
            RESOURCE_DURATION,
            "--description",
            RESOURCE_DESCRIPTION,
            "--output",
            "json",
        ))
    except IndeterminateMutationError:
        recover_timed_out_token_create(runner, project, name)
    try:
        payload = parse_json(raw, "created project access token")
        created = CreatedToken.model_validate(payload)
        return created.model_copy(update={"name": name})
    except (TokenManagerError, ValidationError) as output_error:
        safe_output_error = (
            output_error
            if isinstance(output_error, TokenManagerError)
            else TokenManagerError("created project access-token output contained invalid metadata")
        )
        try:
            revoke_token_by_exact_name(runner, project, name)
        except IndeterminateMutationError as cleanup_error:
            raise IndeterminateMutationError(
                f"create output was invalid ({safe_output_error}); {cleanup_error}"
            ) from None
        except TokenManagerError as cleanup_error:
            raise TokenManagerError(
                f"create output was invalid ({safe_output_error}); cleanup failed ({cleanup_error})"
            ) from None
        raise TokenManagerError(f"create output was invalid ({safe_output_error}); created token was revoked") from None


def recover_timed_out_token_create(runner: GlabRunner, project: str, name: str) -> NoReturn:
    """Resolve a timed-out create only when exact-name remote state can be established."""
    try:
        token = find_token_by_exact_name(runner, project, name)
    except TokenManagerError as discovery_error:
        raise IndeterminateMutationError(
            f"manual inspection is required for token name {name} before retry; "
            f"token create timed out and remote state is unknown ({discovery_error})"
        ) from None
    try:
        runner.run(("token", "revoke", str(token.id), "--repo", project))
    except IndeterminateMutationError:
        raise IndeterminateMutationError(
            f"token create timed out for name {name}; token ID {token.id} was found but revoke status is unknown; "
            "manual inspection is required before retry"
        ) from None
    except TokenManagerError as cleanup_error:
        raise TokenManagerError(
            f"token create timed out for name {name}; token ID {token.id} cleanup failed ({cleanup_error}); "
            "manual inspection is required"
        ) from None
    raise TokenManagerError(f"token create timed out for name {name}; token ID {token.id} was found and revoked")


def reconcile_created_token(
    runner: GlabRunner, project: str, created: CreatedToken, variable: VariableSnapshot | None
) -> None:
    """Write a created secret and revoke its token if variable reconciliation fails."""
    try:
        replace_variable(runner, project, VARIABLE_NAME, created.token.get_secret_value(), original=variable)
    except IndeterminateMutationError as mutation_error:
        raise IndeterminateMutationError(
            f"{mutation_error}; token {created.name} (ID {created.id}) may now be stored; "
            "inspect the CI variable and token before retry; no automatic cleanup was attempted"
        ) from None
    except TokenManagerError as variable_error:
        try:
            runner.run(("token", "revoke", str(created.id), "--repo", project))
        except IndeterminateMutationError:
            raise IndeterminateMutationError(
                f"variable reconciliation failed ({variable_error}); new token {created.name} "
                f"(ID {created.id}) revoke timed out and its status is unknown; inspect GitLab before retry"
            ) from None
        except TokenManagerError as cleanup_error:
            raise TokenManagerError(
                f"variable reconciliation failed ({variable_error}); token cleanup failed ({cleanup_error})"
            ) from None
        raise TokenManagerError(f"variable reconciliation failed ({variable_error}); new token was revoked") from None


def replace_active_token(
    runner: GlabRunner, project: str, old_token_id: int, now: datetime, variable: VariableSnapshot | None
) -> None:
    """Create and durably store a replacement before revoking the old token."""
    created = create_token(runner, project, now)
    reconcile_created_token(runner, project, created, variable)
    try:
        runner.run(("token", "revoke", str(old_token_id), "--repo", project))
    except IndeterminateMutationError:
        raise IndeterminateMutationError(
            f"new variable is durable, but old token ID {old_token_id} revoke timed out and its status is unknown; "
            "inspect GitLab before retry"
        ) from None
    except TokenManagerError as cleanup_error:
        raise TokenManagerError(
            f"new variable is durable, but old token revoke failed ({cleanup_error}); revoke token ID {old_token_id}"
        ) from None


def reconcile(runner: GlabRunner, project: str, *, today: date, now: datetime) -> dict[str, str]:
    """Reconcile token and variable state.

    Returns:
        A secret-free action result.
    """
    tokens = discover_tokens(runner, project)
    variable = discover_variable(runner, project)
    if variable is not None and variable.hidden is None:
        raise TokenManagerError(f"{VARIABLE_NAME} hidden state is unavailable; no mutation was attempted")
    if not tokens:
        created = create_token(runner, project, now)
        reconcile_created_token(runner, project, created, variable)
        return {"status": "done", "action": "created_token_and_variable"}

    token = tokens[0]
    if token.expires_at <= today:
        replace_active_token(runner, project, token.id, now, variable)
        return {"status": "done", "action": "created_replacement_token_and_variable"}
    if variable is None:
        replace_active_token(runner, project, token.id, now, None)
        return {"status": "done", "action": "created_variable_then_revoked_old_token"}
    if variable.hidden is False:
        if variable.value is None or not variable.value.get_secret_value():
            raise TokenManagerError(f"{VARIABLE_NAME} is not hidden, but its current value was not returned")
        try:
            replace_variable(runner, project, VARIABLE_NAME, variable.value.get_secret_value(), original=variable)
        except IndeterminateMutationError as mutation_error:
            raise IndeterminateMutationError(
                f"{mutation_error}; active token ID {token.id}; inspect the CI variable before retry"
            ) from None
        return {"status": "done", "action": "migrated_variable_to_hidden_storage"}
    return {"status": "ok", "action": "already_configured", "expires_at": token.expires_at.isoformat()}


def resolve_context_unchecked(root: Path, environment: Mapping[str, str]) -> tuple[str, str, str]:
    """Resolve context while allowing local parser/decoder exceptions to propagate.

    Returns:
        Authentication token, GitLab host, and project path.
    """
    dotenv = load_dotenv(root / ".env")
    token = (
        environment.get("GITLAB_TOKEN")
        or environment.get("GL_TOKEN")
        or dotenv.get("GITLAB_TOKEN")
        or dotenv.get("GL_TOKEN")
    )
    if not token or not token.strip():
        raise TokenManagerError("set GITLAB_TOKEN or GL_TOKEN to a personal access token with the api scope")
    host = environment.get("GITLAB_HOST") or dotenv.get("GITLAB_HOST") or environment.get("CI_SERVER_HOST")
    project = environment.get("CI_PROJECT_PATH") or dotenv.get("CI_PROJECT_PATH")
    if host is None or project is None:
        remote_host, remote_project = remote_coordinates(root)
        host = host or remote_host
        project = project or remote_project
    return token, validate_host(host), validate_project_path(project)


def resolve_context(root: Path, environment: Mapping[str, str]) -> tuple[str, str, str]:
    """Resolve context while translating unsafe local parsing failures.

    Returns:
        Authentication token, GitLab host, and project path.
    """
    try:
        return resolve_context_unchecked(root, environment)
    except (configparser.Error, UnicodeError):
        raise TokenManagerError("local GitLab context could not be read") from None


def run_manager() -> dict[str, str]:
    """Validate prerequisites and reconcile the GitLab state.

    Returns:
        A secret-free action result.
    """
    root = Path.cwd()
    if not (root / ".git").exists():
        raise TokenManagerError("run this command from the git repository root")
    executable = shutil.which("glab")
    if executable is None:
        raise TokenManagerError("glab is required and was not found on PATH")
    token, host, project = resolve_context(root, os.environ)
    os.environ["GITLAB_TOKEN"] = token
    os.environ["GITLAB_HOST"] = host
    os.environ["CI_PROJECT_PATH"] = project
    if "GITLAB_CI" not in os.environ:
        try:
            persist_local_context(root, {"GITLAB_HOST": host, "CI_PROJECT_PATH": project})
        except UnicodeError:
            raise TokenManagerError("local GitLab context could not be read") from None
    runner = SubprocessGlabRunner(executable)
    verify_permissions(runner, project)
    current_time = datetime.now(UTC)
    return reconcile(runner, project, today=current_time.date(), now=current_time)


def main() -> int:
    """Run the token manager and emit one compact JSON result.

    Returns:
        Process exit status.
    """
    try:
        result = run_manager()
    except TokenManagerError as error:
        print(json.dumps({"status": "error", "message": str(error)}, separators=(",", ":")), file=sys.stderr)
        return 1
    except OSError:
        print(
            json.dumps({"status": "error", "message": "operating system operation failed"}, separators=(",", ":")),
            file=sys.stderr,
        )
        return 1
    else:
        print(json.dumps(result, separators=(",", ":")))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
