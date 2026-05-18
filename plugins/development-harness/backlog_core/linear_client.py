"""Linear GraphQL client for the backlog MCP package.

Handles attachment creation and retrieval via the Linear Attachments API.
All functions use httpx.Client (sync) and raise BacklogError on failure.

Authentication: Linear personal API keys use ``Authorization: <API_KEY>``
(no Bearer prefix). OAuth tokens use ``Authorization: Bearer <TOKEN>``.

SOURCE: https://linear.app/developers/graphql (accessed 2026-04-05)
SOURCE: https://linear.app/developers/attachments (accessed 2026-04-05)
"""

from __future__ import annotations

import logging
from typing import Any, cast

import httpx
from typing_extensions import TypedDict

from .models import BacklogError

logger = logging.getLogger(__name__)

_LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
_HTTP_UNAUTHORIZED = 401
_HTTP_FORBIDDEN = 403

# ---------------------------------------------------------------------------
# TypedDict response models
# ---------------------------------------------------------------------------


class LinearAttachmentNode(TypedDict):
    """Attachment node returned from Linear GraphQL queries."""

    id: str
    url: str
    title: str
    metadata: dict[str, object]


# ---------------------------------------------------------------------------
# GraphQL mutation / query string constants
# ---------------------------------------------------------------------------

_ATTACHMENT_CREATE_MUTATION = """
mutation AttachmentCreate(
  $issueId: String!,
  $url: String!,
  $title: String!,
  $metadata: JSONObject
) {
  attachmentCreate(input: {
    issueId: $issueId
    url: $url
    title: $title
    metadata: $metadata
  }) {
    success
    attachment {
      id
      url
      title
      metadata
    }
  }
}
"""

_ATTACHMENTS_FOR_ISSUE_QUERY = """
query GetAttachments($issueId: ID!) {
  attachments(filter: {issue: {id: {eq: $issueId}}}) {
    nodes {
      id
      url
      title
      metadata
    }
  }
}
"""

# ---------------------------------------------------------------------------
# Core request helper
# ---------------------------------------------------------------------------


def linear_graphql_request(api_key: str, query: str, variables: dict[str, Any] | None = None) -> dict[str, object]:
    """Execute a GraphQL request against the Linear API.

    Args:
        api_key: Linear personal API key. Used directly as the Authorization
            header value (no Bearer prefix required for personal keys).
        query: GraphQL query or mutation string.
        variables: Optional variables dict to send with the query.

    Returns:
        The ``data`` field from the GraphQL response.

    Raises:
        BacklogError: If the HTTP response is 401/403 (invalid key) or if
            the GraphQL response contains an ``errors`` array.
    """
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    payload: dict[str, object] = {"query": query, "variables": variables or {}}

    with httpx.Client() as client:
        response = client.post(_LINEAR_GRAPHQL_URL, headers=headers, json=payload)

    if response.status_code in {_HTTP_UNAUTHORIZED, _HTTP_FORBIDDEN}:
        msg = "LINEAR_API_KEY is invalid or missing"
        raise BacklogError(msg)

    response.raise_for_status()

    body: dict[str, object] = response.json()
    errors = body.get("errors")
    if errors and isinstance(errors, list) and errors:
        first_error = errors[0]
        message = (
            first_error.get("message", "Unknown Linear API error")
            if isinstance(first_error, dict)
            else str(first_error)
        )
        msg = f"Linear API error: {message}"
        raise BacklogError(msg)

    data = body.get("data")
    if not isinstance(data, dict):
        msg = f"Unexpected Linear API response shape: {body!r}"
        raise BacklogError(msg)

    return data


# ---------------------------------------------------------------------------
# Attachment operations
# ---------------------------------------------------------------------------


def linear_create_attachment(
    api_key: str, issue_id: str, url: str, title: str, metadata: dict[str, object]
) -> dict[str, object]:
    """Create or upsert an attachment on a Linear issue.

    Linear treats the combination of ``url`` and ``issue_id`` as idempotent:
    re-creating an attachment with the same URL on the same issue updates the
    existing attachment rather than creating a duplicate.

    Args:
        api_key: Linear personal API key.
        issue_id: UUID of the Linear issue to attach to.
        url: Attachment URL (acts as the idempotency key per issue).
        title: Display title for the attachment.
        metadata: Arbitrary key-value metadata stored with the attachment.

    Returns:
        The ``attachment`` dict from the ``attachmentCreate`` response,
        containing ``id``, ``url``, ``title``, and ``metadata``.

    Raises:
        BacklogError: On authentication failure or GraphQL errors.
    """
    variables: dict[str, Any] = {"issueId": issue_id, "url": url, "title": title, "metadata": metadata}
    data = linear_graphql_request(api_key, _ATTACHMENT_CREATE_MUTATION, variables)

    result = data.get("attachmentCreate")
    if not isinstance(result, dict):
        msg = f"Unexpected attachmentCreate response: {data!r}"
        raise BacklogError(msg)

    result_d = cast("dict[str, object]", result)
    attachment = result_d.get("attachment")
    if not isinstance(attachment, dict):
        msg = f"attachmentCreate did not return an attachment: {result_d!r}"
        raise BacklogError(msg)

    return cast("dict[str, object]", attachment)


def linear_get_attachments(api_key: str, issue_id: str) -> list[dict[str, object]]:
    """Retrieve all attachments for a Linear issue.

    Args:
        api_key: Linear personal API key.
        issue_id: UUID of the Linear issue.

    Returns:
        List of attachment node dicts, each containing ``id``, ``url``,
        ``title``, and ``metadata``.

    Raises:
        BacklogError: On authentication failure or GraphQL errors.
    """
    variables: dict[str, Any] = {"issueId": issue_id}
    data = linear_graphql_request(api_key, _ATTACHMENTS_FOR_ISSUE_QUERY, variables)

    attachments = data.get("attachments")
    if not isinstance(attachments, dict):
        msg = f"Unexpected attachments response: {data!r}"
        raise BacklogError(msg)

    attachments_d = cast("dict[str, object]", attachments)
    nodes = attachments_d.get("nodes", [])
    if not isinstance(nodes, list):
        msg = f"Unexpected attachments.nodes shape: {attachments_d!r}"
        raise BacklogError(msg)

    return cast("list[dict[str, object]]", nodes)
