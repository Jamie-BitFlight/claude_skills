from __future__ import annotations

from unittest.mock import MagicMock

from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.models import ProviderPatch, ReconcileRequest, ReconcileScope


def _issue(number: int, revision: str = "rev-1") -> dict[str, object]:
    return {
        "id": f"node-{number}",
        "number": number,
        "title": f"Issue {number}",
        "body": "body",
        "state": "OPEN",
        "labels": [{"id": "label-1", "name": "feature"}],
        "updatedAt": revision,
        "createdAt": "2026-08-12T00:00:00Z",
        "milestone": None,
        "assignees": [],
    }


def test_github_sync_provider_normalizes_bounded_snapshot() -> None:
    # Given: a GitHub backend returning a GraphQL issue page
    backend = GitHubBackend()
    repository = MagicMock(full_name="owner/repo")
    backend.get_github = MagicMock(return_value=repository)
    backend._fetch_issues_graphql = MagicMock(return_value=[_issue(1)])

    # When: reconciliation fetches an initial snapshot
    snapshot = backend.fetch_snapshot(ReconcileRequest(scope=ReconcileScope.INITIAL))

    # Then: the normalized provider item retains body, labels, and revision
    assert snapshot.items[0].reference == "#1"
    assert snapshot.items[0].labels == ["feature"]
    assert snapshot.items[0].revision == "rev-1"
    assert backend._fetch_issues_graphql.call_args.kwargs["first"] == 100


def test_github_sync_provider_reports_conflict_without_mutation() -> None:
    # Given: a preflight revision that differs from the patch expectation
    backend = GitHubBackend()
    repository = MagicMock(full_name="owner/repo")
    backend.get_github = MagicMock(return_value=repository)
    backend._fetch_issues_graphql = MagicMock(return_value=[_issue(1, revision="rev-2")])
    backend._update_issues_graphql_batch = MagicMock()
    patch = ProviderPatch(provider_id="node-1", reference="#1", expected_revision="rev-1", body="updated")

    # When: the patch is applied
    result = backend.apply_patches([patch])

    # Then: the provider body mutation is skipped and the conflict is surfaced
    assert result[0].status == "conflict"
    backend._update_issues_graphql_batch.assert_not_called()
