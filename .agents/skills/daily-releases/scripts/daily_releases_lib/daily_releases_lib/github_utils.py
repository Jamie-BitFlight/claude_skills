"""Shared GitHub client utilities for the daily-releases pipeline scripts.

Provides SSL certificate handling, PyGithub client construction, and a
GitHub GraphQL helper used across all daily-releases scripts.
"""

from __future__ import annotations

import os
import sys
from io import TextIOWrapper
from typing import TYPE_CHECKING

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx as _httpx
import typer
from github import Auth, Github, GithubException
from rich.console import Console

if TYPE_CHECKING:
    from github.Repository import Repository

_err_console = Console(stderr=True)


class AppExit(typer.Exit):
    """Exit with user-friendly error message to stderr."""

    exit_code: int

    def __init__(self, code: int = 1, message: str | None = None) -> None:
        """Print message to stderr and exit with code."""
        if message is not None:
            _err_console.print(f"[red]{message}[/red]")
        self.exit_code = code
        super().__init__(code=code)


def get_ssl_verify() -> bool | str:
    """Determine SSL verification setting from environment variables.

    Priority order:

    1. ``GITHUB_SSL_VERIFY=false/0/no`` — disable verification entirely.
    2. ``GITHUB_CA_BUNDLE`` — path to a custom CA bundle file.
    3. ``REQUESTS_CA_BUNDLE`` — fallback CA bundle path (requests convention).
    4. ``CURL_CA_BUNDLE`` — fallback CA bundle path (curl convention).
    5. Default: ``True`` (use system CA store).

    Returns:
        False to disable SSL verification, a CA bundle path string, or True.
    """
    verify_str = os.environ.get("GITHUB_SSL_VERIFY", "true").lower()
    if verify_str in {"false", "0", "no"}:
        return False
    for env_var in ("GITHUB_CA_BUNDLE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        bundle = os.environ.get(env_var)
        if bundle:
            return bundle
    return True


def make_github_client(token: str) -> Github:
    """Create a Github client respecting proxy/SSL environment variables.

    Reads:
        GITHUB_API_URL: Custom API base URL (default: https://api.github.com).
        GITHUB_SSL_VERIFY: Set to 'false', '0', or 'no' to disable SSL verification.
        GITHUB_CA_BUNDLE: Path to custom CA bundle file.
        REQUESTS_CA_BUNDLE: Fallback CA bundle path (requests convention).
        CURL_CA_BUNDLE: Fallback CA bundle path (curl convention).

    Returns:
        Configured Github client instance.
    """
    base_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    verify = get_ssl_verify()
    return Github(auth=Auth.Token(token), base_url=base_url, verify=verify)


def get_github_repo(gh: Github, repo_slug: str) -> Repository:
    """Return PyGithub Repository object.

    Args:
        gh: Authenticated Github client.
        repo_slug: Repository slug in ``OWNER/REPO`` format.

    Returns:
        PyGithub Repository instance.

    Raises:
        AppExit: If the repository cannot be accessed.
    """
    try:
        return gh.get_repo(repo_slug)
    except GithubException as e:
        raise AppExit(code=1, message=f"Cannot access repo '{repo_slug}': {e}") from e


def graphql(token: str, query: str, variables: dict, *, verify: bool | str, base_url: str) -> dict:
    """Execute a GitHub GraphQL query and return the response data dict.

    Args:
        token: GitHub personal access token.
        query: GraphQL query string.
        variables: GraphQL variable bindings.
        verify: SSL verification setting — False, True, or path to CA bundle.
        base_url: GitHub API base URL (e.g. https://api.github.com).

    Returns:
        Parsed ``data`` field from the GraphQL response.

    Raises:
        AppExit: On HTTP errors or GraphQL errors in the response.
    """
    graphql_url = base_url.rstrip("/") + "/graphql"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = _httpx.post(
            graphql_url, json={"query": query, "variables": variables}, headers=headers, verify=verify, timeout=30
        )
        resp.raise_for_status()
    except _httpx.HTTPError as exc:
        raise AppExit(code=1, message=f"GraphQL request failed: {exc}") from exc
    payload = resp.json()
    if errors := payload.get("errors"):
        msg = errors[0].get("message", str(errors))
        raise AppExit(code=1, message=f"GraphQL error: {msg}")
    return payload["data"]
