"""GitLab REST API operations for the backlog MCP package.

Provides snippet and issue-note operations via the GitLab Projects API.
Requires a PRIVATE-TOKEN for authentication; all snippets are created private.

GitLab API version: v4 (GitLab 13.0+)
Multi-file snippet files array uses action: create | update | delete | move.
SOURCE: https://docs.gitlab.com/ee/api/project_snippets.html (accessed 2026-04-05)
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx
from typing_extensions import TypedDict

from .models import BacklogError

logger = logging.getLogger(__name__)

_HTTP_UNAUTHORIZED = 401
_HTTP_FORBIDDEN = 403


class GitLabSnippetNode(TypedDict):
    """Typed representation of a GitLab project snippet with file contents."""

    id: int
    title: str
    web_url: str
    files_content: dict[str, str]


def _auth_headers(private_token: str) -> dict[str, str]:
    return {"PRIVATE-TOKEN": private_token}


def _raise_for_gitlab_error(response: httpx.Response) -> None:
    """Raise BacklogError for GitLab API error responses."""
    if response.status_code in {_HTTP_UNAUTHORIZED, _HTTP_FORBIDDEN}:
        msg = "GITLAB_TOKEN is invalid or missing"
        raise BacklogError(msg)
    if response.is_error:
        msg = f"GitLab API error {response.status_code}: {response.text}"
        raise BacklogError(msg)


def gitlab_create_snippet(
    project_id: str | int,
    private_token: str,
    gitlab_url: str,
    title: str,
    files: list[dict[str, Any]],
    visibility: str = "private",
) -> dict[str, Any]:
    """Create a multi-file project snippet.

    Args:
        project_id: GitLab project ID or URL-encoded path.
        private_token: GitLab personal access token.
        gitlab_url: GitLab instance base URL (e.g. https://gitlab.com).
        title: Snippet title.
        files: List of file dicts with ``file_path`` and ``content`` keys.
        visibility: Snippet visibility — "private", "internal", or "public".

    Returns:
        Snippet dict from GitLab API (includes ``id``, ``web_url``, etc.).

    Raises:
        BacklogError: On authentication failure or HTTP error.
    """
    url = f"{gitlab_url}/api/v4/projects/{project_id}/snippets"
    payload: dict[str, Any] = {"title": title, "visibility": visibility, "files": files}
    with httpx.Client() as client:
        response = client.post(url, json=payload, headers=_auth_headers(private_token))
    _raise_for_gitlab_error(response)
    result: dict[str, Any] = response.json()
    logger.debug("Created GitLab snippet id=%s", result.get("id"))
    return result


def gitlab_update_snippet(
    project_id: str | int, snippet_id: int, private_token: str, gitlab_url: str, files: list[dict[str, Any]]
) -> dict[str, Any]:
    """Update files in an existing project snippet.

    Each entry in ``files`` must include ``action``, ``file_path``, and
    ``content``.  Use ``action: "update"`` to overwrite an existing file.

    SOURCE: https://docs.gitlab.com/ee/api/project_snippets.html#update-snippet
    Valid action values: "create", "update", "delete", "move" (GitLab 13.0+).

    Args:
        project_id: GitLab project ID or URL-encoded path.
        snippet_id: ID of the snippet to update.
        private_token: GitLab personal access token.
        gitlab_url: GitLab instance base URL.
        files: List of file action dicts.

    Returns:
        Updated snippet dict from GitLab API.

    Raises:
        BacklogError: On authentication failure or HTTP error.
    """
    url = f"{gitlab_url}/api/v4/projects/{project_id}/snippets/{snippet_id}"
    payload: dict[str, Any] = {"files": files}
    with httpx.Client() as client:
        response = client.put(url, json=payload, headers=_auth_headers(private_token))
    _raise_for_gitlab_error(response)
    result: dict[str, Any] = response.json()
    logger.debug("Updated GitLab snippet id=%s", snippet_id)
    return result


def gitlab_get_snippet(project_id: str | int, snippet_id: int, private_token: str, gitlab_url: str) -> dict[str, Any]:
    """Fetch a project snippet and its file contents.

    Retrieves snippet metadata, then fetches raw content for each file
    via the ``/files/{ref}/{file_path}/raw`` endpoint.  File contents are
    attached under the ``files_content`` key keyed by file path.

    Args:
        project_id: GitLab project ID or URL-encoded path.
        snippet_id: ID of the snippet to retrieve.
        private_token: GitLab personal access token.
        gitlab_url: GitLab instance base URL.

    Returns:
        Snippet dict with an extra ``files_content: dict[str, str]`` key.

    Raises:
        BacklogError: On authentication failure or HTTP error.
    """
    url = f"{gitlab_url}/api/v4/projects/{project_id}/snippets/{snippet_id}"
    headers = _auth_headers(private_token)
    with httpx.Client() as client:
        response = client.get(url, headers=headers)
        _raise_for_gitlab_error(response)
        snippet: dict[str, Any] = response.json()

        files_content: dict[str, str] = {}
        for file_entry in snippet.get("files", []):
            file_path: str = file_entry.get("path", "")
            if not file_path:
                continue
            encoded_path = quote(file_path, safe="")
            raw_url = f"{gitlab_url}/api/v4/projects/{project_id}/snippets/{snippet_id}/files/main/{encoded_path}/raw"
            raw_response = client.get(raw_url, headers=headers)
            _raise_for_gitlab_error(raw_response)
            files_content[file_path] = raw_response.text

    snippet["files_content"] = files_content
    logger.debug("Fetched GitLab snippet id=%s with %d file(s)", snippet_id, len(files_content))
    return snippet


def gitlab_create_issue_note(
    project_id: str | int, issue_iid: int, private_token: str, gitlab_url: str, body: str
) -> dict[str, Any]:
    """Post a comment note on a GitLab issue.

    Args:
        project_id: GitLab project ID or URL-encoded path.
        issue_iid: Internal issue ID (iid, not the global id).
        private_token: GitLab personal access token.
        gitlab_url: GitLab instance base URL.
        body: Note body text (markdown supported).

    Returns:
        Created note dict from GitLab API.

    Raises:
        BacklogError: On authentication failure or HTTP error.
    """
    url = f"{gitlab_url}/api/v4/projects/{project_id}/issues/{issue_iid}/notes"
    with httpx.Client() as client:
        response = client.post(url, json={"body": body}, headers=_auth_headers(private_token))
    _raise_for_gitlab_error(response)
    result: dict[str, Any] = response.json()
    logger.debug("Created note id=%s on issue iid=%s", result.get("id"), issue_iid)
    return result


def gitlab_list_issue_notes(
    project_id: str | int, issue_iid: int, private_token: str, gitlab_url: str
) -> list[dict[str, Any]]:
    """List all notes (comments) on a GitLab issue.

    Args:
        project_id: GitLab project ID or URL-encoded path.
        issue_iid: Internal issue ID (iid).
        private_token: GitLab personal access token.
        gitlab_url: GitLab instance base URL.

    Returns:
        List of note dicts from GitLab API.

    Raises:
        BacklogError: On authentication failure or HTTP error.
    """
    url = f"{gitlab_url}/api/v4/projects/{project_id}/issues/{issue_iid}/notes"
    with httpx.Client() as client:
        response = client.get(url, headers=_auth_headers(private_token))
    _raise_for_gitlab_error(response)
    notes: list[dict[str, Any]] = response.json()
    logger.debug("Listed %d notes on issue iid=%s", len(notes), issue_iid)
    return notes
