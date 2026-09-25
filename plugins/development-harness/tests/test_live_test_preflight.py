"""The real preflight refuses unsafe targets before accessing the provider."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import close_test_issues
import pytest
from github import GithubException
from live_test_scope import SANDBOX_MARKER, LiveTestScope


def configure(monkeypatch) -> LiveTestScope:
    values = {
        "DH_E2E_REPOSITORY": "test-owner/disposable-backlog",
        "DH_E2E_RUN_ID": "777-1",
        "DH_ALLOW_TEST_NETWORK": "1",
        "GITHUB_TOKEN": "test-only-not-a-credential",
        "GITHUB_REPOSITORY": "source-owner/source-repo",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    monkeypatch.delenv("REPO", raising=False)
    monkeypatch.setattr(sys, "argv", ["close_test_issues.py"])
    return LiveTestScope.from_environment(values)


def fake_repository(monkeypatch):
    repository = MagicMock()
    repository.full_name = "test-owner/disposable-backlog"
    repository.default_branch = "main"
    repository.get_contents.return_value.decoded_content = SANDBOX_MARKER
    gateway = MagicMock(return_value=repository)
    monkeypatch.setattr(close_test_issues, "get_github", gateway)
    return repository, gateway


def test_production_configuration_fails_before_authentication(monkeypatch, capsys) -> None:
    configure(monkeypatch)
    monkeypatch.setenv("DH_E2E_REPOSITORY", "Jamie-BitFlight/claude_skills")
    _, gateway = fake_repository(monkeypatch)
    assert close_test_issues.main() == 1
    gateway.assert_not_called()
    assert "source/production" in capsys.readouterr().err


@pytest.mark.parametrize("marker", [b"", b"not a sandbox\n", SANDBOX_MARKER.rstrip(b"\n")])
def test_a_repository_name_alone_is_not_a_sandbox_opt_in(monkeypatch, marker) -> None:
    scope = configure(monkeypatch)
    repository, _ = fake_repository(monkeypatch)
    repository.get_contents.return_value.decoded_content = marker
    with pytest.raises(ValueError, match="exact contents"):
        close_test_issues.open_sandbox(scope)
    repository.get_issues.assert_not_called()
    repository.create_file.assert_not_called()


def test_preflight_only_reads_and_does_not_run_cleanup(monkeypatch) -> None:
    configure(monkeypatch)
    repository, _ = fake_repository(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["close_test_issues.py", "--check-only"])
    assert close_test_issues.main() == 0
    repository.get_issues.assert_not_called()
    repository.create_file.assert_not_called()


def test_cleanup_transport_failure_is_a_nonzero_exit(monkeypatch, capsys) -> None:
    configure(monkeypatch)
    repository, _ = fake_repository(monkeypatch)
    repository.get_issues.side_effect = GithubException(403, {"message": "sandbox access denied"}, None)
    assert close_test_issues.main() == 1
    assert "sandbox access denied" in capsys.readouterr().err
