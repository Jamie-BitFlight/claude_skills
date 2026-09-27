"""Regression tests for classifying a GraphQL rate-limit refusal.

Observed 2026-09-27: a ListIssues query answered with a GitHub rate limit got no special
handling. GitHub answers a rate-limited GraphQL query with HTTP 200 and a body shaped
``{"data": null, "errors": [{"type": "RATE_LIMITED", ...}]}``. PyGithub's
``Requester.graphql_query`` (2.9.0 and 2.10.0) never returns such a body: any ``errors`` entry
other than a single ``NOT_FOUND`` becomes ``createException(400, headers, data)``. So the refusal
reaches ``_graphql_request`` as a ``GithubException`` whose ``data`` holds the ``errors`` list and
whose ``headers`` hold ``Retry-After`` / ``x-ratelimit-remaining``. A secondary limit arrives as a
real HTTP 403, which PyGithub raises as ``RateLimitExceededException``.

These tests drive the real PyGithub stack against a loopback HTTP server, so the exception shape
under test is the one PyGithub builds, not a fake's. The client is built with ``retry=None`` so
PyGithub's own retry policy does not sleep on a 403 before the exception reaches us.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from github import Auth, Github

from backlog_core.gh_client import _graphql_request
from backlog_core.models import BackendUnavailableError, GitHubRateLimitedError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

_QUERY = "query ListIssues { viewer { login } }"

_RATE_LIMITED_BODY = {
    "data": None,
    "errors": [{"type": "RATE_LIMITED", "message": "API rate limit exceeded for installation ID 1."}],
}


def _start_server(status: int, body: dict[str, object], headers: dict[str, str]) -> HTTPServer:
    """Answer every POST with one canned response on a loopback port."""

    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:  # ruff: ignore[builtin-argument-shadowing] -- the base class names it format
            """Keep the test output quiet."""

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.fixture
def github_answering() -> Iterator[Callable[..., SimpleNamespace]]:
    """Return a factory: start a loopback GitHub stand-in, get a repo whose requester is real."""
    servers: list[HTTPServer] = []

    def _start(status: int, body: dict[str, object], headers: dict[str, str] | None = None) -> SimpleNamespace:
        server = _start_server(status, body, headers or {})
        servers.append(server)
        client = Github(auth=Auth.Token("t"), base_url=f"http://127.0.0.1:{server.server_port}", retry=None)
        return SimpleNamespace(requester=client.requester)

    yield _start
    for server in servers:
        server.shutdown()
        server.server_close()


class TestGraphQLRateLimitIsClassified:
    """A rate-limit refusal must raise the dedicated retryable type, carrying GitHub's hint."""

    def test_a_rate_limited_errors_entry_raises_the_dedicated_type(
        self, github_answering: Callable[..., SimpleNamespace]
    ) -> None:
        repo = github_answering(200, _RATE_LIMITED_BODY, {"Retry-After": "30"})

        with pytest.raises(GitHubRateLimitedError) as excinfo:
            _graphql_request(repo, _QUERY)

        assert excinfo.value.retryable is True
        assert excinfo.value.retry_after == pytest.approx(30.0)

    def test_retry_after_is_none_when_github_sends_no_hint(
        self, github_answering: Callable[..., SimpleNamespace]
    ) -> None:
        repo = github_answering(200, _RATE_LIMITED_BODY)

        with pytest.raises(GitHubRateLimitedError) as excinfo:
            _graphql_request(repo, _QUERY)

        assert excinfo.value.retry_after is None

    def test_an_exhausted_rate_limit_header_marks_the_refusal(
        self, github_answering: Callable[..., SimpleNamespace]
    ) -> None:
        body = {"data": None, "errors": [{"type": "FORBIDDEN", "message": "quota exhausted"}]}
        repo = github_answering(200, body, {"x-ratelimit-remaining": "0"})

        with pytest.raises(GitHubRateLimitedError):
            _graphql_request(repo, _QUERY)

    def test_a_secondary_rate_limit_403_raises_the_dedicated_type(
        self, github_answering: Callable[..., SimpleNamespace]
    ) -> None:
        body = {"message": "You have exceeded a secondary rate limit. Please wait a few minutes before you try again."}
        repo = github_answering(403, body, {"Retry-After": "60"})

        with pytest.raises(GitHubRateLimitedError) as excinfo:
            _graphql_request(repo, _QUERY)

        assert excinfo.value.retry_after == pytest.approx(60.0)

    def test_it_is_still_a_backend_unavailable_error(self) -> None:
        """Existing ``except BackendUnavailableError`` handlers must keep catching it."""
        assert issubclass(GitHubRateLimitedError, BackendUnavailableError)

    def test_a_non_rate_limit_graphql_error_is_not_swept_into_this_type(
        self, github_answering: Callable[..., SimpleNamespace]
    ) -> None:
        """Negative control: an ordinary query error with quota left is not a rate limit."""
        body = {"data": None, "errors": [{"type": "INVALID", "message": "field invalid"}]}
        repo = github_answering(200, body, {"x-ratelimit-remaining": "4999"})

        with pytest.raises(BackendUnavailableError) as excinfo:
            _graphql_request(repo, _QUERY)

        assert not isinstance(excinfo.value, GitHubRateLimitedError)


class TestAnExhaustedQuotaHeaderDoesNotOverrideTheStatus:
    """``x-ratelimit-remaining: 0`` marks a rate limit only on a refusal status, never on 401/404."""

    @pytest.mark.parametrize(("status", "message"), [(401, "Bad credentials"), (404, "Not Found")], ids=["401", "404"])
    def test_a_non_refusal_status_with_an_exhausted_quota_is_not_a_rate_limit(
        self, github_answering: Callable[..., SimpleNamespace], status: int, message: str
    ) -> None:
        repo = github_answering(status, {"message": message}, {"x-ratelimit-remaining": "0"})

        with pytest.raises(BackendUnavailableError) as excinfo:
            _graphql_request(repo, _QUERY)

        assert not isinstance(excinfo.value, GitHubRateLimitedError)
        assert excinfo.value.retryable is False
