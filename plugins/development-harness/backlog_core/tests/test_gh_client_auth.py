"""Tests for gh_client's token resolution and missing-token logging behaviour.

``probe_backend_status`` and ``try_get_github`` both decide what to do when no
GitHub token is configured. Two defects lived here: ``probe_backend_status``
checked only the ``GITHUB_TOKEN`` environment variable directly instead of
going through ``github_client.resolve_token``'s full precedence order (backlog
#3599), and ``try_get_github`` logged a missing token at ``logger.exception``
level -- which captures and prints a traceback for what is, by this
function's own docstring, an expected and recoverable condition every caller
already tolerates (backlog #3602).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backlog_core import gh_client
from backlog_core.github_client import TOKEN_ENV_VARS
from backlog_core.models import BackendAvailability

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class TestProbeBackendStatusHonorsEveryTokenVariable:
    """A missing GITHUB_TOKEN must not be reported as "no token" when a later
    precedence variable supplies one -- probe_backend_status must delegate to
    the same resolve_token() precedence make_github_client already uses,
    rather than re-implementing a narrower GITHUB_TOKEN-only check."""

    def test_reports_needs_authentication_when_no_variable_is_set(self, monkeypatch) -> None:
        for name in TOKEN_ENV_VARS:
            monkeypatch.delenv(name, raising=False)

        status = gh_client.probe_backend_status()

        assert status.availability == BackendAvailability.NEEDS_AUTHENTICATION

    def test_gh_token_alone_is_sufficient(self, monkeypatch, mocker: MockerFixture) -> None:
        """GH_TOKEN (gh CLI's own variable) must not be treated as absent."""
        for name in TOKEN_ENV_VARS:
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("GH_TOKEN", "gh-token-value")
        mocker.patch.object(gh_client, "try_get_github", return_value=None)

        status = gh_client.probe_backend_status()

        assert status.availability != BackendAvailability.NEEDS_AUTHENTICATION

    def test_github_personal_access_token_alone_is_sufficient(self, monkeypatch, mocker: MockerFixture) -> None:
        for name in TOKEN_ENV_VARS:
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "pat-value")
        mocker.patch.object(gh_client, "try_get_github", return_value=None)

        status = gh_client.probe_backend_status()

        assert status.availability != BackendAvailability.NEEDS_AUTHENTICATION

    def test_the_error_message_names_every_accepted_variable(self, monkeypatch) -> None:
        for name in TOKEN_ENV_VARS:
            monkeypatch.delenv(name, raising=False)

        status = gh_client.probe_backend_status()

        assert status.error is not None
        for name in TOKEN_ENV_VARS:
            assert name in status.error


class TestTryGetGithubLogsMissingTokenAsAWarning:
    """A missing token is a normal, tolerated condition for this function's callers
    (its own docstring: "Use this for operations where local-only fallback is
    acceptable") -- not an unexpected failure worth logger.exception's traceback."""

    def test_missing_token_is_logged_at_warning_not_exception_level(self, monkeypatch, caplog) -> None:
        for name in TOKEN_ENV_VARS:
            monkeypatch.delenv(name, raising=False)

        with caplog.at_level(logging.WARNING, logger=gh_client.logger.name):
            result = gh_client.try_get_github()

        assert result is None
        records = [r for r in caplog.records if "no GitHub token available" in r.getMessage()]
        assert records, "expected a log record naming the missing token"
        assert all(r.levelno == logging.WARNING for r in records), (
            f"expected WARNING level, got {[r.levelname for r in records]}"
        )
        assert all(r.exc_info is None for r in records), "a missing token must not attach a traceback"
