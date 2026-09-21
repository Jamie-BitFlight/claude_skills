from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "setup_ci_publish_token.py"


def load_script() -> ModuleType:
    """Load the standalone companion as a module for unit testing."""
    spec = importlib.util.spec_from_file_location("setup_ci_publish_token", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load_script()


class ScriptedRunner:
    """Record glab calls and return scripted results."""

    def __init__(self, *results: str | Exception) -> None:
        self.results = list(results)
        self.calls: list[Any] = []

    def run(self, arguments: Any, *, stdin: str | None = None) -> str:
        """Record one call and return or raise its scripted result."""
        self.calls.append(MODULE.GlabCall(tuple(arguments), stdin=stdin))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def token_json(*, token_id: int = 42, expires_at: str = "2030-01-01") -> str:
    """Return one active matching token as glab JSON."""
    return json.dumps([{"id": token_id, "name": "ci-publish-token", "expires_at": expires_at}])


def variable_json(
    *,
    hidden: bool | None,
    value: str | None = None,
    raw: bool = False,
    variable_type: str = "env_var",
    environment_scope: str = "*",
    description: str | None = "existing",
) -> str:
    """Return variable metadata as glab JSON."""
    return json.dumps([
        {
            "key": MODULE.VARIABLE_NAME,
            "value": value,
            "hidden": hidden,
            "protected": True,
            "masked": True,
            "raw": raw,
            "variable_type": variable_type,
            "environment_scope": environment_scope,
            "description": description,
        }
    ])


def created_token_json(*, token_id: int = 91, secret: str = "created-secret") -> str:
    """Return a newly created token with ID and secret as glab JSON."""
    return json.dumps({"id": token_id, "token": secret, "name": "ci-publish-token-new", "expires_at": "2030-01-01"})


def mutation_timeout(operation: str) -> Exception:
    """Return an indeterminate post-commit mutation timeout."""
    return MODULE.IndeterminateMutationError(f"{operation} timed out; remote state is unknown")


MUTATING_COMMANDS = [
    pytest.param(("token", "create", "ci-publish-token-unique"), id="token-create"),
    pytest.param(("variable", "set", MODULE.VARIABLE_NAME), id="variable-set"),
    pytest.param(("variable", "update", MODULE.VARIABLE_NAME), id="hidden-update"),
    pytest.param(("variable", "delete", MODULE.VARIABLE_NAME), id="readable-delete"),
    pytest.param(("variable", "set", MODULE.VARIABLE_NAME, "--hidden"), id="readable-recreate"),
    pytest.param(("variable", "set", MODULE.VARIABLE_NAME, "--scope", "production"), id="rollback"),
    pytest.param(("token", "revoke", "91"), id="new-token-revoke"),
    pytest.param(("token", "revoke", "73"), id="old-token-revoke"),
]


def test_non_hidden_migration_restores_original_after_replacement_failure() -> None:
    """A failed hidden replacement must restore the original value and security metadata."""
    secret = "rollback-secret-that-must-not-leak"
    original = MODULE.VariableSnapshot(
        value=secret,
        hidden=False,
        protected=False,
        masked=True,
        raw=False,
        variable_type="file",
        environment_scope="production",
        description="original description",
    )
    runner = ScriptedRunner("", MODULE.GlabError("replacement rejected"), "")

    with pytest.raises(MODULE.TokenManagerError, match="original variable was restored") as caught:
        MODULE.replace_variable(runner, "group/project", "CI_PUBLISH_TOKEN", secret, original=original)

    assert runner.calls == [
        MODULE.GlabCall(("variable", "delete", "CI_PUBLISH_TOKEN", "--repo", "group/project", "--scope", "production")),
        MODULE.GlabCall(
            (
                "variable",
                "set",
                "CI_PUBLISH_TOKEN",
                "--repo",
                "group/project",
                "--hidden",
                "--masked",
                "--protected",
                "--scope",
                "production",
                "--type",
                "file",
                "--description",
                "original description",
            ),
            stdin=secret,
        ),
        MODULE.GlabCall(
            (
                "variable",
                "set",
                "CI_PUBLISH_TOKEN",
                "--repo",
                "group/project",
                "--masked",
                "--scope",
                "production",
                "--type",
                "file",
                "--description",
                "original description",
            ),
            stdin=secret,
        ),
    ]
    assert secret not in str(caught.value)
    assert all(secret not in call.arguments for call in runner.calls)


def test_rollback_failure_reports_both_failures_without_secret() -> None:
    """Replacement and rollback failures are both reported with no secret disclosure."""
    secret = "never-print-this-secret"
    original = MODULE.VariableSnapshot(value=secret, hidden=False, masked=True)
    runner = ScriptedRunner("", MODULE.GlabError("replacement rejected"), MODULE.GlabError("rollback rejected"))

    with pytest.raises(MODULE.TokenManagerError, match=r"replacement failed.*rollback also failed") as caught:
        MODULE.replace_variable(runner, "group/project", MODULE.VARIABLE_NAME, secret, original=original)

    assert "replacement rejected" in str(caught.value)
    assert "rollback rejected" in str(caught.value)
    assert secret not in str(caught.value)
    assert secret not in repr(runner.calls)
    assert runner.calls == [
        MODULE.GlabCall(("variable", "delete", MODULE.VARIABLE_NAME, "--repo", "group/project")),
        MODULE.GlabCall(
            (
                "variable",
                "set",
                MODULE.VARIABLE_NAME,
                "--repo",
                "group/project",
                "--hidden",
                "--masked",
                "--protected",
                "--scope",
                "*",
                "--type",
                "env_var",
            ),
            stdin=secret,
        ),
        MODULE.GlabCall(
            (
                "variable",
                "set",
                MODULE.VARIABLE_NAME,
                "--repo",
                "group/project",
                "--masked",
                "--scope",
                "*",
                "--type",
                "env_var",
            ),
            stdin=secret,
        ),
    ]


def test_non_not_found_variable_discovery_failure_stops_before_mutation() -> None:
    """Authentication or network failure during discovery must not be treated as absence."""
    failure = MODULE.GlabError("variable discovery", returncode=1, not_found=False)
    runner = ScriptedRunner(token_json(token_id=73), failure)

    with pytest.raises(MODULE.GlabError):
        MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert len(runner.calls) == 2


def test_variable_discovery_rejects_ambiguous_environment_scopes() -> None:
    """Multiple same-key variables must be rejected instead of silently selecting wildcard scope."""
    runner = ScriptedRunner(
        json.dumps([
            {"key": MODULE.VARIABLE_NAME, "hidden": False, "value": "one", "environment_scope": "*"},
            {"key": MODULE.VARIABLE_NAME, "hidden": False, "value": "two", "environment_scope": "production"},
        ])
    )

    with pytest.raises(MODULE.TokenManagerError, match="multiple environment scopes"):
        MODULE.discover_variable(runner, "group/project")


def test_variable_discovery_finds_match_on_later_page() -> None:
    """Absence is not inferred until every variable page has been read."""
    first_page = [{"key": f"OTHER_{index}"} for index in range(100)]
    expected = {
        "key": MODULE.VARIABLE_NAME,
        "hidden": True,
        "environment_scope": "production",
        "variable_type": "env_var",
    }
    runner = ScriptedRunner(json.dumps(first_page), json.dumps([expected]))

    discovered = MODULE.discover_variable(runner, "group/project")

    assert discovered is not None
    assert discovered.environment_scope == "production"
    assert [call.arguments[-4:] for call in runner.calls] == [
        ("--page", "1", "--per-page", "100"),
        ("--page", "2", "--per-page", "100"),
    ]


def test_variable_discovery_rejects_duplicate_scopes_across_pages() -> None:
    """Duplicate matching keys are rejected even when split across pages."""
    first_page: list[dict[str, Any]] = [{"key": f"OTHER_{index}"} for index in range(99)]
    first_page.append({"key": MODULE.VARIABLE_NAME, "hidden": False, "environment_scope": "*"})
    second_page = [{"key": MODULE.VARIABLE_NAME, "hidden": False, "environment_scope": "production"}]
    runner = ScriptedRunner(json.dumps(first_page), json.dumps(second_page))

    with pytest.raises(MODULE.TokenManagerError, match="multiple environment scopes"):
        MODULE.discover_variable(runner, "group/project")

    assert len(runner.calls) == 2


def test_created_token_is_revoked_when_variable_reconciliation_fails() -> None:
    """A failed variable write must revoke the new token so retry cannot pair an old secret."""
    secret = "new-token-secret"
    runner = ScriptedRunner(
        "[]",
        "[]",
        created_token_json(token_id=91, secret=secret),
        MODULE.GlabError("variable set", returncode=1, not_found=False),
        "",
    )

    with pytest.raises(MODULE.TokenManagerError, match="new token was revoked") as caught:
        MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert runner.calls[-1] == MODULE.GlabCall(("token", "revoke", "91", "--repo", "group/project"))
    assert secret not in str(caught.value)
    assert secret not in repr(runner.calls)


def test_created_token_cleanup_failure_reports_both_failures_without_secret() -> None:
    """Variable and token-cleanup failures are combined without the created secret."""
    secret = "cleanup-secret"
    runner = ScriptedRunner(
        "[]",
        "[]",
        created_token_json(token_id=92, secret=secret),
        MODULE.GlabError("variable set", returncode=1, not_found=False),
        MODULE.GlabError("token revoke", returncode=1, not_found=False),
    )

    with pytest.raises(
        MODULE.TokenManagerError, match=r"variable reconciliation failed.*token cleanup failed"
    ) as caught:
        MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert secret not in str(caught.value)


def test_readable_retry_cannot_pair_discovered_token_with_old_secret() -> None:
    """Failed readable replacement revokes its token before a retry creates another secret."""
    old_secret = "old-variable-secret"
    first_secret = "first-created-secret"
    second_secret = "second-created-secret"
    readable = variable_json(hidden=False, value=old_secret)
    first = ScriptedRunner(
        "[]",
        readable,
        created_token_json(token_id=91, secret=first_secret),
        "",
        MODULE.GlabError("variable set", returncode=1),
        "",
        "",
    )

    with pytest.raises(MODULE.TokenManagerError, match="new token was revoked"):
        MODULE.reconcile(first, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert first.calls[-2].stdin.get_secret_value() == old_secret
    assert first.calls[-1] == MODULE.GlabCall(("token", "revoke", "91", "--repo", "group/project"))

    retry = ScriptedRunner("[]", readable, created_token_json(token_id=92, secret=second_secret), "", "")
    MODULE.reconcile(retry, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))
    assert retry.calls[-1].stdin.get_secret_value() == second_secret
    assert first_secret not in repr(first.calls)
    assert second_secret not in repr(retry.calls)


def test_existing_hidden_variable_is_updated_without_delete() -> None:
    """Replacing an existing hidden value must retain variable identity and hidden state."""
    secret = "replacement-secret"
    runner = ScriptedRunner(
        token_json(expires_at="2026-09-21"), variable_json(hidden=True), created_token_json(secret=secret), ""
    )

    MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert runner.calls[-1].arguments[:3] == ("variable", "update", MODULE.VARIABLE_NAME)
    assert runner.calls[-1].stdin.get_secret_value() == secret
    assert all(call.arguments[:2] != ("variable", "delete") for call in runner.calls)


@pytest.mark.parametrize("tokens", ["[]", token_json(expires_at="2026-09-21")])
def test_hidden_variable_update_failure_revokes_created_token(tokens: str) -> None:
    """Both create branches retain the hidden variable and clean up a failed new token."""
    runner = ScriptedRunner(
        tokens,
        variable_json(hidden=True),
        created_token_json(token_id=91),
        MODULE.GlabError("variable update", returncode=1),
        "",
    )

    with pytest.raises(MODULE.TokenManagerError, match="new token was revoked"):
        MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert all(call.arguments[:2] != ("variable", "delete") for call in runner.calls)
    assert runner.calls[-1] == MODULE.GlabCall(("token", "revoke", "91", "--repo", "group/project"))


def test_variable_set_timeout_does_not_revoke_new_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """A set timeout may have stored the secret, so automatic token revoke is unsafe."""
    secret = "set-timeout-secret"
    monkeypatch.setattr(MODULE.uuid, "uuid4", type("FixedUuid", (), {"hex": "fixed"}))
    runner = ScriptedRunner(
        "[]", "[]", created_token_json(token_id=91, secret=secret), mutation_timeout("variable set")
    )

    with pytest.raises(MODULE.IndeterminateMutationError, match=r"token.*91.*inspect") as caught:
        MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert runner.calls[-1].arguments[:2] == ("variable", "set")
    assert all(call.arguments[:2] != ("token", "revoke") for call in runner.calls)
    assert secret not in str(caught.value)


def test_hidden_update_timeout_does_not_revoke_new_token() -> None:
    """A hidden update timeout may have committed an unreadable new value."""
    secret = "update-timeout-secret"
    runner = ScriptedRunner(
        "[]",
        variable_json(hidden=True),
        created_token_json(token_id=91, secret=secret),
        mutation_timeout("variable update"),
    )

    with pytest.raises(MODULE.IndeterminateMutationError, match=r"token.*91.*inspect") as caught:
        MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert runner.calls[-1].arguments[:2] == ("variable", "update")
    assert all(call.arguments[:2] != ("token", "revoke") for call in runner.calls)
    assert secret not in str(caught.value)


def test_readable_delete_timeout_stops_without_recreate_or_revoke() -> None:
    """Delete timeout leaves existence unknown and forbids follow-up mutation."""
    runner = ScriptedRunner(
        "[]",
        variable_json(hidden=False, value="old-secret"),
        created_token_json(token_id=91),
        mutation_timeout("variable delete"),
    )

    with pytest.raises(MODULE.IndeterminateMutationError):
        MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert runner.calls[-1].arguments[:2] == ("variable", "delete")
    assert len(runner.calls) == 4


def test_readable_replacement_timeout_stops_without_rollback_or_revoke() -> None:
    """Replacement timeout may have committed hidden storage and forbids rollback."""
    runner = ScriptedRunner(
        "[]",
        variable_json(hidden=False, value="old-secret"),
        created_token_json(token_id=91),
        "",
        mutation_timeout("variable set replacement"),
    )

    with pytest.raises(MODULE.IndeterminateMutationError):
        MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert runner.calls[-1].arguments[:2] == ("variable", "set")
    assert len(runner.calls) == 5


def test_readable_rollback_timeout_stops_without_token_revoke() -> None:
    """Rollback timeout leaves restoration unknown and forbids token cleanup."""
    runner = ScriptedRunner(
        "[]",
        variable_json(hidden=False, value="old-secret"),
        created_token_json(token_id=91),
        "",
        MODULE.GlabError("replacement rejected", returncode=1),
        mutation_timeout("variable rollback"),
    )

    with pytest.raises(MODULE.IndeterminateMutationError):
        MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert runner.calls[-1].arguments[:2] == ("variable", "set")
    assert len(runner.calls) == 6


def test_unknown_hidden_state_refuses_mutation() -> None:
    """Unknown hidden metadata must stop before token or variable mutation."""
    runner = ScriptedRunner("[]", variable_json(hidden=None))

    with pytest.raises(MODULE.TokenManagerError, match="hidden state"):
        MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert len(runner.calls) == 2


def test_ambiguous_active_tokens_are_rejected_in_id_order() -> None:
    """The manager must not choose among multiple matching active tokens."""
    runner = ScriptedRunner(
        json.dumps([
            {"id": 9, "name": "ci-publish-token-new", "expires_at": "2030-01-01"},
            {"id": 3, "name": "ci-publish-token", "expires_at": "2030-01-01"},
        ])
    )

    with pytest.raises(MODULE.TokenManagerError, match=r"IDs: 3, 9"):
        MODULE.discover_tokens(runner, "group/project")


def test_expiry_boundary_creates_unique_replacement() -> None:
    """A token expiring on today's UTC date is replaced with a uniquely named token."""
    secret = "new-secret"
    runner = ScriptedRunner(
        token_json(expires_at="2026-09-21"), variable_json(hidden=True), created_token_json(secret=secret), ""
    )

    result = MODULE.reconcile(
        runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, 13, 14, 15, tzinfo=UTC)
    )

    create_call = runner.calls[2]
    assert result == {"status": "done", "action": "created_replacement_token_and_variable"}
    assert create_call.arguments[:3] == ("token", "create", create_call.arguments[2])
    assert create_call.arguments[2].startswith("ci-publish-token-20260921131415-")
    assert create_call.arguments[2] != MODULE.RESOURCE_NAME
    assert runner.calls[-1].stdin.get_secret_value() == secret


def test_valid_token_with_missing_variable_replaces_after_durable_write() -> None:
    """A missing variable stores a new token before revoking the old token ID."""
    secret = "replacement-secret"
    runner = ScriptedRunner(token_json(token_id=73), "[]", created_token_json(secret=secret), "", "")

    result = MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert result == {"status": "done", "action": "created_variable_then_revoked_old_token"}
    assert runner.calls[2].arguments[:2] == ("token", "create")
    assert runner.calls[3].stdin.get_secret_value() == secret
    assert runner.calls[4] == MODULE.GlabCall(("token", "revoke", "73", "--repo", "group/project"))


def test_valid_token_missing_variable_write_failure_preserves_old_token() -> None:
    """A failed durable write revokes only the newly created token."""
    secret = "new-secret"
    runner = ScriptedRunner(
        token_json(token_id=73),
        "[]",
        created_token_json(token_id=91, secret=secret),
        MODULE.GlabError("variable set", returncode=1),
        "",
    )

    with pytest.raises(MODULE.TokenManagerError, match="new token was revoked"):
        MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    revoke_calls = [call for call in runner.calls if call.arguments[:2] == ("token", "revoke")]
    assert revoke_calls == [MODULE.GlabCall(("token", "revoke", "91", "--repo", "group/project"))]
    assert all("73" not in call.arguments for call in revoke_calls)


def test_valid_token_old_revoke_failure_reports_durable_new_variable() -> None:
    """Old-token cleanup failure reports that the new variable is already durable."""
    secret = "durable-secret"
    runner = ScriptedRunner(
        token_json(token_id=73),
        "[]",
        created_token_json(token_id=91, secret=secret),
        "",
        MODULE.GlabError("old token revoke", returncode=1),
    )

    with pytest.raises(MODULE.TokenManagerError, match=r"variable is durable.*old token revoke failed") as caught:
        MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert runner.calls[-2].arguments[:3] == ("variable", "set", MODULE.VARIABLE_NAME)
    assert runner.calls[-2].stdin.get_secret_value() == secret
    assert runner.calls[-1] == MODULE.GlabCall(("token", "revoke", "73", "--repo", "group/project"))
    assert secret not in str(caught.value)


def test_new_token_revoke_timeout_reports_unknown_status() -> None:
    """Cleanup revoke timeout reports unknown new-token status without more mutation."""
    runner = ScriptedRunner(
        "[]",
        "[]",
        created_token_json(token_id=91),
        MODULE.GlabError("variable set rejected", returncode=1),
        mutation_timeout("new token revoke"),
    )

    with pytest.raises(MODULE.IndeterminateMutationError, match=r"token.*91.*status is unknown"):
        MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert runner.calls[-1] == MODULE.GlabCall(("token", "revoke", "91", "--repo", "group/project"))
    assert len(runner.calls) == 5


def test_old_token_revoke_timeout_preserves_durable_variable_state() -> None:
    """Old revoke timeout reports unknown status after the new variable is durable."""
    secret = "durable-timeout-secret"
    runner = ScriptedRunner(
        token_json(token_id=73),
        "[]",
        created_token_json(token_id=91, secret=secret),
        "",
        mutation_timeout("old token revoke"),
    )

    with pytest.raises(MODULE.IndeterminateMutationError, match=r"old token.*73.*status is unknown") as caught:
        MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert runner.calls[-2].arguments[:2] == ("variable", "set")
    assert runner.calls[-1] == MODULE.GlabCall(("token", "revoke", "73", "--repo", "group/project"))
    assert secret not in str(caught.value)


def test_valid_token_migrates_readable_variable_without_rotation() -> None:
    """A readable legacy variable is recreated as hidden without rotating its valid token."""
    secret = "existing-secret"
    runner = ScriptedRunner(
        token_json(),
        variable_json(
            hidden=False,
            value=secret,
            raw=True,
            variable_type="file",
            environment_scope="production",
            description="preserve this",
        ),
        "",
        "",
    )

    result = MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert result == {"status": "done", "action": "migrated_variable_to_hidden_storage"}
    assert all(call.arguments[:2] != ("token", "rotate") for call in runner.calls)
    assert runner.calls[-1] == MODULE.GlabCall(
        (
            "variable",
            "set",
            MODULE.VARIABLE_NAME,
            "--repo",
            "group/project",
            "--hidden",
            "--masked",
            "--protected",
            "--raw",
            "--scope",
            "production",
            "--type",
            "file",
            "--description",
            "preserve this",
        ),
        stdin=secret,
    )


@pytest.mark.parametrize(
    ("hidden", "expected"), [(True, {"status": "ok", "action": "already_configured", "expires_at": "2030-01-01"})]
)
def test_valid_token_with_existing_variable_does_not_mutate(hidden: bool, expected: dict[str, str]) -> None:
    """An existing hidden variable is not changed while its token remains valid."""
    runner = ScriptedRunner(token_json(), variable_json(hidden=hidden))

    result = MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert result == expected
    assert len(runner.calls) == 2


def test_missing_token_creates_token_and_variable() -> None:
    """No active token creates a unique token and hidden variable."""
    secret = "created-secret"
    runner = ScriptedRunner("[]", "[]", created_token_json(secret=secret), "")

    result = MODULE.reconcile(runner, "group/project", today=date(2026, 9, 21), now=datetime(2026, 9, 21, tzinfo=UTC))

    assert result == {"status": "done", "action": "created_token_and_variable"}
    assert runner.calls[-1].stdin.get_secret_value() == secret


def test_subprocess_failure_redacts_stdin_and_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ambiguous mutating process failure is indeterminate and cannot disclose diagnostics."""
    secret = "secret-in-stdin-and-stderr"

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        assert secret not in args[0]
        assert kwargs["input"] == secret.encode()
        return subprocess.CompletedProcess(args[0], 1, stdout=b"", stderr=f"server echoed {secret}".encode())

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)

    with pytest.raises(MODULE.IndeterminateMutationError) as caught:
        MODULE.SubprocessGlabRunner("/usr/bin/glab").run(("variable", "set", MODULE.VARIABLE_NAME), stdin=secret)

    assert secret not in str(caught.value)


@pytest.mark.parametrize("arguments", MUTATING_COMMANDS)
def test_mutating_connection_error_is_indeterminate(
    monkeypatch: pytest.MonkeyPatch, arguments: tuple[str, ...]
) -> None:
    """A nonzero mutation without explicit rejection evidence has unknown remote state."""
    diagnostic_secret = "diagnostic-secret"
    process_calls: list[list[str]] = []

    def connection_error(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        process_calls.append(command)
        return subprocess.CompletedProcess(
            command, 1, stdout=b"", stderr=f"connection reset after response {diagnostic_secret}".encode()
        )

    monkeypatch.setattr(MODULE.subprocess, "run", connection_error)

    with pytest.raises(MODULE.IndeterminateMutationError, match="remote state is unknown") as caught:
        MODULE.SubprocessGlabRunner("/usr/bin/glab").run(arguments, stdin="value-secret")

    assert len(process_calls) == 1
    assert diagnostic_secret not in str(caught.value)
    assert "value-secret" not in str(caught.value)


def test_explicit_http_rejection_is_definitive_for_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    """A tested HTTP 4xx response proves GitLab rejected the mutation."""

    def rejected(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(command, 1, stdout=b"", stderr=b"glab: rejected (HTTP 400: Bad Request)")

    monkeypatch.setattr(MODULE.subprocess, "run", rejected)

    with pytest.raises(MODULE.GlabError) as caught:
        MODULE.SubprocessGlabRunner("/usr/bin/glab").run(("variable", "set", MODULE.VARIABLE_NAME), stdin="secret")

    assert not isinstance(caught.value, MODULE.IndeterminateMutationError)


def test_output_requiring_mutation_invalid_output_is_indeterminate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Token creation requires decodable output to establish its ID and secret."""

    def invalid_output(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(command, 0, stdout=b"\xff", stderr=b"")

    monkeypatch.setattr(MODULE.subprocess, "run", invalid_output)

    with pytest.raises(MODULE.IndeterminateMutationError, match="remote state is unknown"):
        MODULE.SubprocessGlabRunner("/usr/bin/glab").run(("token", "create", "ci-publish-token-unique"))


@pytest.mark.parametrize("arguments", MUTATING_COMMANDS[1:])
def test_no_output_mutation_invalid_stdout_does_not_invent_failure(
    monkeypatch: pytest.MonkeyPatch, arguments: tuple[str, ...]
) -> None:
    """Exit zero establishes completion when callers do not consume mutation output."""
    process_calls: list[list[str]] = []

    def invalid_output(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        process_calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=b"\xff", stderr=b"")

    monkeypatch.setattr(MODULE.subprocess, "run", invalid_output)

    assert MODULE.SubprocessGlabRunner("/usr/bin/glab").run(arguments, stdin="value-secret") == ""
    assert len(process_calls) == 1


def test_mutating_subprocess_timeout_is_indeterminate(monkeypatch: pytest.MonkeyPatch) -> None:
    """A timeout after a mutating request cannot be classified as a definitive failure."""

    def timeout(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(MODULE.subprocess, "run", timeout)

    with pytest.raises(MODULE.IndeterminateMutationError, match="remote state is unknown"):
        MODULE.SubprocessGlabRunner("/usr/bin/glab").run(
            ("variable", "set", MODULE.VARIABLE_NAME, "--repo", "group/project"), stdin="secret"
        )


def test_read_only_subprocess_timeout_remains_glab_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Read-only timeout has no possible committed mutation."""

    def timeout(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(MODULE.subprocess, "run", timeout)

    with pytest.raises(MODULE.GlabError) as caught:
        MODULE.SubprocessGlabRunner("/usr/bin/glab").run(("api", "user"))

    assert not isinstance(caught.value, getattr(MODULE, "IndeterminateMutationError", ()))


@pytest.mark.parametrize(
    "malformed", ["not-json", '{"id":"bad","token":{"secret":"leak"}}', created_token_json(secret="")]
)
def test_malformed_create_output_rediscovers_unique_name_and_revokes(
    monkeypatch: pytest.MonkeyPatch, malformed: str
) -> None:
    """Malformed successful creation output is cleaned up by its exact unique name."""
    unique_name = "ci-publish-token-20260921000000-fixed"
    monkeypatch.setattr(MODULE.uuid, "uuid4", type("FixedUuid", (), {"hex": "fixed"}))
    first_token_page = [{"id": index, "name": f"unrelated-{index}", "expires_at": "2030-01-01"} for index in range(100)]
    exact_token = {"id": 91, "name": unique_name, "expires_at": "2030-01-01"}
    runner = ScriptedRunner(malformed, json.dumps(first_token_page), json.dumps([exact_token]), "")

    with pytest.raises(MODULE.TokenManagerError, match="created token was revoked") as caught:
        MODULE.create_token(runner, "group/project", datetime(2026, 9, 21, tzinfo=UTC))

    assert runner.calls[0].arguments[2] == unique_name
    assert runner.calls[-1] == MODULE.GlabCall(("token", "revoke", "91", "--repo", "group/project"))
    assert "leak" not in str(caught.value)


def test_malformed_create_output_cleanup_failure_reports_both_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed output and failed name-based cleanup are both reported without response content."""
    unique_name = "ci-publish-token-20260921000000-fixed"
    monkeypatch.setattr(MODULE.uuid, "uuid4", type("FixedUuid", (), {"hex": "fixed"}))
    exact_token = {"id": 91, "name": unique_name, "expires_at": "2030-01-01"}
    runner = ScriptedRunner(
        '{"id":"bad","token":{"secret":"leak"}}',
        json.dumps([exact_token]),
        MODULE.GlabError("token revoke", returncode=1),
    )

    with pytest.raises(MODULE.TokenManagerError, match=r"create output was invalid.*cleanup failed") as caught:
        MODULE.create_token(runner, "group/project", datetime(2026, 9, 21, tzinfo=UTC))

    assert "leak" not in str(caught.value)


def test_malformed_create_output_revoke_timeout_reports_unknown_status(monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed-output cleanup timeout preserves an indeterminate token status."""
    unique_name = "ci-publish-token-20260921000000-fixed"
    monkeypatch.setattr(MODULE.uuid, "uuid4", type("FixedUuid", (), {"hex": "fixed"}))
    exact_token = {"id": 91, "name": unique_name, "expires_at": "2030-01-01"}
    runner = ScriptedRunner("not-json", json.dumps([exact_token]), mutation_timeout("token revoke"))

    with pytest.raises(MODULE.IndeterminateMutationError, match=r"token.*91.*status is unknown"):
        MODULE.create_token(runner, "group/project", datetime(2026, 9, 21, tzinfo=UTC))

    assert runner.calls[-1] == MODULE.GlabCall(("token", "revoke", "91", "--repo", "group/project"))


def test_token_create_timeout_rediscovers_and_revokes_exact_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """Post-commit create timeout recovers only after exact-name state is established."""
    unique_name = "ci-publish-token-20260921000000-fixed"
    monkeypatch.setattr(MODULE.uuid, "uuid4", type("FixedUuid", (), {"hex": "fixed"}))
    exact_token = {"id": 91, "name": unique_name, "expires_at": "2030-01-01"}
    runner = ScriptedRunner(mutation_timeout("token create"), json.dumps([exact_token]), "")

    with pytest.raises(MODULE.TokenManagerError, match=r"token create timed out.*91.*revoked"):
        MODULE.create_token(runner, "group/project", datetime(2026, 9, 21, tzinfo=UTC))

    assert runner.calls[0].arguments[2] == unique_name
    assert runner.calls[-1] == MODULE.GlabCall(("token", "revoke", "91", "--repo", "group/project"))


def test_token_create_timeout_without_exact_match_requires_manual_inspection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unestablished create outcome stops without another mutation."""
    unique_name = "ci-publish-token-20260921000000-fixed"
    monkeypatch.setattr(MODULE.uuid, "uuid4", type("FixedUuid", (), {"hex": "fixed"}))
    runner = ScriptedRunner(mutation_timeout("token create"), "[]")

    with pytest.raises(MODULE.IndeterminateMutationError, match=r"manual inspection.*ci-publish-token"):
        MODULE.create_token(runner, "group/project", datetime(2026, 9, 21, tzinfo=UTC))

    assert runner.calls[0].arguments[2] == unique_name
    assert len(runner.calls) == 2


def test_indeterminate_error_main_output_is_compact_and_secret_free(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Indeterminate state is emitted as compact JSON without secret material."""
    monkeypatch.setattr(
        MODULE,
        "run_manager",
        lambda: (_ for _ in ()).throw(
            MODULE.IndeterminateMutationError("variable set indeterminate for token 91; inspect GitLab")
        ),
    )

    assert MODULE.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "status": "error",
        "message": "variable set indeterminate for token 91; inspect GitLab",
    }
    assert "secret" not in captured.err


@pytest.mark.parametrize(
    "failure", [subprocess.TimeoutExpired(["glab"], 60), OSError("secret operating-system detail")]
)
def test_subprocess_runtime_failures_are_safe_token_manager_errors(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    """Timeout and spawn failures become compact, redacted manager errors."""

    def fail_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        raise failure

    monkeypatch.setattr(MODULE.subprocess, "run", fail_run)

    with pytest.raises(MODULE.TokenManagerError) as caught:
        MODULE.SubprocessGlabRunner("/usr/bin/glab").run(("api", "user"))

    assert "secret operating-system detail" not in str(caught.value)


def test_subprocess_is_bounded_and_rejects_non_utf8_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """The process boundary has a timeout and explicitly decodes UTF-8."""

    def invalid_output(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        assert kwargs["timeout"] == MODULE.GLAB_TIMEOUT_SECONDS
        assert kwargs["input"] is None
        return subprocess.CompletedProcess(args[0], 0, stdout=b"\xff", stderr=b"")

    monkeypatch.setattr(MODULE.subprocess, "run", invalid_output)

    with pytest.raises(MODULE.TokenManagerError, match="UTF-8"):
        MODULE.SubprocessGlabRunner("/usr/bin/glab").run(("api", "user"))


@pytest.mark.parametrize(
    ("function_name", "payload"), [("discover_tokens", '[{"id":"bad","name":"ci-publish-token","expires_at":"bad"}]')]
)
def test_model_validation_failures_are_safe(function_name: str, payload: str) -> None:
    """Malformed glab models become redacted TokenManagerError values."""
    runner = ScriptedRunner(payload)
    function = getattr(MODULE, function_name)

    with pytest.raises(MODULE.TokenManagerError) as caught:
        function(runner, "group/project")

    assert "leak" not in str(caught.value)


def test_main_converts_oserror_to_compact_secret_free_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Unhandled OS failures cannot escape as tracebacks or disclose details."""
    monkeypatch.setattr(MODULE, "run_manager", lambda: (_ for _ in ()).throw(OSError("secret path")))

    assert MODULE.main() == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {"status": "error", "message": "operating system operation failed"}


@pytest.mark.parametrize("invalid_file", ["git_config", "dotenv"])
def test_main_converts_local_context_parse_failures_to_compact_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, invalid_file: str
) -> None:
    """Malformed config and invalid UTF-8 produce generic compact JSON without file content."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    if invalid_file == "git_config":
        (git_dir / "config").write_text("secret malformed config", encoding="utf-8")
    else:
        (tmp_path / ".env").write_bytes(b"secret=\xff")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(MODULE.shutil, "which", lambda executable: "/usr/bin/glab")
    monkeypatch.setattr(MODULE.os, "environ", {"GITLAB_TOKEN": "personal-token"})

    assert MODULE.main() == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {"status": "error", "message": "local GitLab context could not be read"}
    assert "secret" not in captured.err


def test_explicit_coordinates_bypass_missing_origin(tmp_path: Path) -> None:
    """Complete explicit coordinates do not require an origin remote."""
    (tmp_path / ".git").mkdir()

    assert MODULE.resolve_context(
        tmp_path,
        {"GITLAB_TOKEN": "personal-token", "GITLAB_HOST": "gitlab.example.com", "CI_PROJECT_PATH": "group/project"},
    ) == ("personal-token", "gitlab.example.com", "group/project")


@pytest.mark.parametrize(
    "remote_url", ["https://gitlab.example.com/group/project.git", "git@gitlab.example.com:group/project.git"]
)
def test_remote_coordinates_support_https_and_scp_ssh(tmp_path: Path, remote_url: str) -> None:
    """Origin discovery supports documented HTTPS and SCP-style SSH remotes."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text(f'[remote "origin"]\nurl = {remote_url}\n', encoding="utf-8")

    assert MODULE.remote_coordinates(tmp_path) == ("gitlab.example.com", "group/project")


def test_remote_coordinates_preserve_https_non_default_port(tmp_path: Path) -> None:
    """HTTPS origin discovery retains the explicit GitLab port."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text(
        '[remote "origin"]\nurl = https://gitlab.example.com:8443/group/project.git\n', encoding="utf-8"
    )

    assert MODULE.remote_coordinates(tmp_path) == ("gitlab.example.com:8443", "group/project")


@pytest.mark.parametrize("port", ["invalid", "70000"])
def test_main_rejects_malformed_https_origin_port_compactly(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, port: str
) -> None:
    """Malformed and out-of-range HTTPS ports produce compact context errors."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text(
        f'[remote "origin"]\nurl = https://gitlab.example.com:{port}/group/project.git\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(MODULE.shutil, "which", lambda executable: "/usr/bin/glab")
    monkeypatch.setattr(MODULE.os, "environ", {"GITLAB_TOKEN": "personal-token"})

    assert MODULE.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {"status": "error", "message": "git origin URL has invalid port"}


def test_remote_coordinates_support_worktree_git_file(tmp_path: Path) -> None:
    """Origin discovery follows worktree gitdir and commondir metadata."""
    common = tmp_path / "common"
    worktree_git = common / "worktrees" / "feature"
    worktree_git.mkdir(parents=True)
    (tmp_path / ".git").write_text(f"gitdir: {worktree_git}\n", encoding="utf-8")
    (worktree_git / "commondir").write_text("../..\n", encoding="utf-8")
    (common / "config").write_text(
        '[remote "origin"]\nurl = https://gitlab.example.com/group/project.git\n', encoding="utf-8"
    )

    assert MODULE.remote_coordinates(tmp_path) == ("gitlab.example.com", "group/project")


@pytest.mark.parametrize(
    ("host", "project"),
    [
        ("https://gitlab.example.com", "group/project"),
        ("gitlab.example.com/path", "group/project"),
        ("gitlab.example.com", "project"),
        ("gitlab.example.com", "group//project"),
        (" ", "group/project"),
    ],
)
def test_malformed_explicit_coordinates_fail(tmp_path: Path, host: str, project: str) -> None:
    """Malformed explicit host and project values are rejected before persistence."""
    (tmp_path / ".git").mkdir()

    with pytest.raises(MODULE.TokenManagerError, match=r"GitLab (host|project path)"):
        MODULE.resolve_context(
            tmp_path, {"GITLAB_TOKEN": "personal-token", "GITLAB_HOST": host, "CI_PROJECT_PATH": project}
        )


def test_permission_checks_require_api_scope_and_maintainer_access() -> None:
    """Permission checks inspect PAT scope, current user, and numeric project access."""
    runner = ScriptedRunner('{"scopes":["api"]}', '{"id":17}', '{"access_level":40}')

    MODULE.verify_permissions(runner, "group/project")

    assert [call.arguments for call in runner.calls] == [
        ("api", "personal_access_tokens/self"),
        ("api", "user"),
        ("api", "projects/group%2Fproject/members/all/17"),
    ]
