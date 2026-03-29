#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["python-gitlab>=4.0.0", "gitpython>=3.1.0"]
# ///
"""Gather GitLab CI context for skill preprocessing.

Outputs plain text to stdout with four sections:
1. Current pipeline status
2. Recent pipeline runs (last 5)
3. CI configuration validation
4. First 50 lines of .gitlab-ci.yml

Always exits 0 -- a failing preprocessing script breaks skill loading.
Called via the SKILL.md backtick-bang syntax:
    !`${CLAUDE_PLUGIN_ROOT}/skills/gitlab-skill/scripts/gitlab_context.py`
"""

from __future__ import annotations

import os
import re
import sys
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import git
import gitlab as gitlab_module

if TYPE_CHECKING:
    from gitlab.v4.objects import Project

_SECONDS_PER_MINUTE = 60
_SECONDS_PER_HOUR = 3600
_SECONDS_PER_DAY = 86400
_CI_FILE_PREVIEW_LINES = 50


@lru_cache(maxsize=1)
def _get_repo() -> git.Repo:
    """Get the git repository for the current directory.

    Returns:
        GitPython Repo object for the current repository.
    """
    return git.Repo(Path.cwd(), search_parent_directories=True)


@lru_cache(maxsize=1)
def _parse_git_origin() -> tuple[str, str]:
    """Parse hostname and project path from git origin URL.

    Returns:
        Tuple of (hostname, project_path).

    Raises:
        ValueError: If the origin URL cannot be parsed.
    """
    repo = _get_repo()
    url: str = repo.remotes.origin.url
    if match := re.search(r"(?:@|://(?:[^@]+@)?)([^:/]+)[:/](.+?)(?:\.git)?$", url):
        return match.group(1), match.group(2)
    msg = f"Could not parse git origin URL: {url}"
    raise ValueError(msg)


def get_gitlab_host() -> str:
    """Get GitLab hostname from git remote origin.

    Returns:
        GitLab hostname (e.g. "gitlab.com").
    """
    return _parse_git_origin()[0]


def get_project_path() -> str:
    """Get project path from git remote origin.

    Returns:
        Project path (e.g. "mygroup/myproject").
    """
    return _parse_git_origin()[1]


def _get_current_branch() -> str:
    """Get current git branch name.

    Returns:
        Current branch name.
    """
    repo = _get_repo()
    return repo.active_branch.name


def _resolve_token() -> str | None:
    """Resolve GitLab API token from environment variables.

    Checks in order:
    1. GITLAB_TOKEN environment variable
    2. GITLAB_PRIVATE_TOKEN environment variable

    Returns:
        Token string, or None if neither variable is set.
    """
    return os.environ.get("GITLAB_TOKEN") or os.environ.get("GITLAB_PRIVATE_TOKEN") or None


def get_gitlab_client() -> gitlab_module.Gitlab:
    """Get authenticated GitLab client.

    Returns:
        Authenticated GitLab client instance.

    Raises:
        RuntimeError: If no authentication token is available.
    """
    token = _resolve_token()
    if not token:
        msg = "No GitLab token found. Set GITLAB_TOKEN env var."
        raise RuntimeError(msg)

    return gitlab_module.Gitlab(f"https://{get_gitlab_host()}", private_token=token)


def _get_project(gl: gitlab_module.Gitlab) -> Project:
    """Get the GitLab project for the current repository.

    Args:
        gl: Authenticated GitLab client.

    Returns:
        GitLab project object.
    """
    return gl.projects.get(get_project_path())


def _format_relative_time(created_at: str) -> str:
    """Format an ISO timestamp as a human-readable relative time string.

    Args:
        created_at: ISO 8601 timestamp string from GitLab API.

    Returns:
        Human-readable relative time (e.g. "5 minutes ago").
    """
    try:
        created = datetime.fromisoformat(created_at)
        total_seconds = int((datetime.now(tz=UTC) - created).total_seconds())
    except (ValueError, TypeError):
        return created_at

    if total_seconds < _SECONDS_PER_MINUTE:
        return f"{total_seconds} seconds ago"
    if total_seconds < _SECONDS_PER_HOUR:
        minutes = total_seconds // _SECONDS_PER_MINUTE
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if total_seconds < _SECONDS_PER_DAY:
        hours = total_seconds // _SECONDS_PER_HOUR
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = total_seconds // _SECONDS_PER_DAY
    return f"{days} day{'s' if days != 1 else ''} ago"


def _gather_pipeline_status(project: Project) -> str:
    """Gather current pipeline status for the active branch.

    Args:
        project: GitLab project object.

    Returns:
        Plain text description of the latest pipeline status.
    """
    branch = _get_current_branch()
    pipelines = project.pipelines.list(ref=branch, per_page=1, get_all=False)
    if not pipelines:
        return f"No pipeline found for branch '{branch}'."

    p = pipelines[0]
    return f"{p.status} (Pipeline #{p.id} on branch {p.ref})"


def _gather_recent_pipelines(project: Project) -> str:
    """Gather the last 5 pipeline runs across all refs.

    Args:
        project: GitLab project object.

    Returns:
        Plain text list of recent pipelines.
    """
    pipelines = project.pipelines.list(per_page=5, get_all=False)
    if not pipelines:
        return "No recent pipelines found."

    lines: list[str] = []
    for p in pipelines:
        relative_time = _format_relative_time(p.created_at)
        lines.append(f"- #{p.id} {p.status} {p.ref} ({relative_time})")
    return "\n".join(lines)


def _gather_ci_validation(project: Project) -> str:
    """Validate the CI configuration via the GitLab API.

    Reads .gitlab-ci.yml from the filesystem and sends it to the
    project's CI lint endpoint for validation.

    Args:
        project: GitLab project object.

    Returns:
        Validation result as plain text.
    """
    ci_file = Path(".gitlab-ci.yml")
    if not ci_file.exists():
        return "No .gitlab-ci.yml in current directory."

    content = ci_file.read_text(encoding="utf-8")
    try:
        result = project.ci_lint.create({"content": content})
    except Exception as exc:  # noqa: BLE001
        return f"Could not validate CI config: {exc}"
    else:
        if result.valid:
            return "Valid -- .gitlab-ci.yml passes CI lint."
        errors = "\n".join(f"  - {e}" for e in (result.errors or []))
        return f"Invalid -- .gitlab-ci.yml has errors:\n{errors}"


def _gather_ci_file_preview() -> str:
    """Read the first 50 lines of .gitlab-ci.yml from the filesystem.

    Returns:
        First 50 lines of the file, or a message if not found.
    """
    ci_file = Path(".gitlab-ci.yml")
    if not ci_file.exists():
        return "No .gitlab-ci.yml in current directory."

    all_lines = ci_file.read_text(encoding="utf-8").splitlines()
    preview = "\n".join(all_lines[:_CI_FILE_PREVIEW_LINES])
    if len(all_lines) > _CI_FILE_PREVIEW_LINES:
        preview += f"\n... ({len(all_lines) - _CI_FILE_PREVIEW_LINES} more lines)"
    return preview


def main() -> None:
    """Gather GitLab CI context and print to stdout."""
    try:
        gl = get_gitlab_client()
        project = _get_project(gl)
    except Exception as exc:  # noqa: BLE001
        print(f"**Pipeline status:** {exc}")
        return

    # 1. Pipeline status
    try:
        pipeline_status = _gather_pipeline_status(project)
    except Exception as exc:  # noqa: BLE001
        pipeline_status = f"Error retrieving pipeline status: {exc}"
    print(f"**Pipeline status:** {pipeline_status}")
    print()

    # 2. Recent pipelines
    try:
        recent = _gather_recent_pipelines(project)
    except Exception as exc:  # noqa: BLE001
        recent = f"Error retrieving recent pipelines: {exc}"
    print(f"**Recent pipeline runs:**\n{recent}")
    print()

    # 3. CI lint validation
    try:
        validation = _gather_ci_validation(project)
    except Exception as exc:  # noqa: BLE001
        validation = f"Error validating CI config: {exc}"
    print(f"**CI configuration:** {validation}")
    print()

    # 4. CI file preview
    preview = _gather_ci_file_preview()
    print(f"**Current .gitlab-ci.yml (first 50 lines):**\n{preview}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        pass
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"**Pipeline status:** {exc}")
        sys.exit(0)
