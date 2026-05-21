"""Tests for backlog_core.backends.bd_runner.

Verifies BdRunner subprocess wrapper behavior using pytest-mock.
No live bd binary is invoked — all subprocess interactions are mocked.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from backlog_core.backends.bd_runner import BdInvocationError, BdJsonDecodeError, BdNotInstalledError, BdRunner, _bd_env

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_FAKE_BD = "/usr/local/bin/bd"
_FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "beads"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _proc(returncode: int = 0, stdout: str = '{"ok": true}', stderr: str = "") -> subprocess.CompletedProcess[str]:
    """Return a completed-process stub with the given exit state."""
    return subprocess.CompletedProcess(args=[_FAKE_BD], returncode=returncode, stdout=stdout, stderr=stderr)


# ---------------------------------------------------------------------------
# Constructor contract — filesystem-free
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_init_does_not_call_shutil_which(mocker: MockerFixture) -> None:
    """BdRunner.__init__ must not call shutil.which."""
    mock_which = mocker.patch("backlog_core.backends.bd_runner.shutil.which")
    mocker.patch("backlog_core.backends.bd_runner.subprocess.run")

    BdRunner()

    mock_which.assert_not_called()


@pytest.mark.unit
def test_init_does_not_call_subprocess_run(mocker: MockerFixture) -> None:
    """BdRunner.__init__ must not call subprocess.run."""
    mocker.patch("backlog_core.backends.bd_runner.shutil.which")
    mock_run = mocker.patch("backlog_core.backends.bd_runner.subprocess.run")

    BdRunner()

    mock_run.assert_not_called()


@pytest.mark.unit
def test_init_stores_custom_timeout(mocker: MockerFixture) -> None:
    """BdRunner stores a custom timeout_seconds for later subprocess invocations."""
    mocker.patch("backlog_core.backends.bd_runner.shutil.which")
    mocker.patch("backlog_core.backends.bd_runner.subprocess.run")

    runner = BdRunner(timeout_seconds=5)

    assert runner._timeout_seconds == 5


# ---------------------------------------------------------------------------
# run_json — happy path
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_run_json_returns_parsed_object(mocker: MockerFixture) -> None:
    """run_json returns the parsed JSON object from bd stdout."""
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mocker.patch(
        "backlog_core.backends.bd_runner.subprocess.run",
        return_value=_proc(stdout='{"id": "bd-a3f8", "status": "open"}'),
    )

    runner = BdRunner()
    result = runner.run_json(["show", "bd-a3f8"])

    assert result == {"id": "bd-a3f8", "status": "open"}


@pytest.mark.unit
def test_run_json_injects_json_flag_when_absent(mocker: MockerFixture) -> None:
    """run_json appends --json to argv when the caller omits it."""
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mock_run = mocker.patch("backlog_core.backends.bd_runner.subprocess.run", return_value=_proc())

    BdRunner().run_json(["show", "bd-a3f8"])

    cmd: list[str] = mock_run.call_args.args[0]
    assert "--json" in cmd


@pytest.mark.unit
def test_run_json_does_not_duplicate_json_flag(mocker: MockerFixture) -> None:
    """run_json does not add a second --json when caller already includes it."""
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mock_run = mocker.patch("backlog_core.backends.bd_runner.subprocess.run", return_value=_proc())

    BdRunner().run_json(["show", "bd-a3f8", "--json"])

    cmd: list[str] = mock_run.call_args.args[0]
    assert cmd.count("--json") == 1


# ---------------------------------------------------------------------------
# run_json — error paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_run_json_raises_not_installed_when_bd_absent(mocker: MockerFixture) -> None:
    """run_json raises BdNotInstalledError when bd is not on PATH."""
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=None)

    with pytest.raises(BdNotInstalledError):
        BdRunner().run_json(["show", "bd-a3f8"])


@pytest.mark.unit
def test_run_json_raises_invocation_error_on_nonzero_exit(mocker: MockerFixture) -> None:
    """run_json raises BdInvocationError when bd exits non-zero; stderr is preserved."""
    fixture_stderr = (_FIXTURES / "bd_invocation_error_stderr.txt").read_text(encoding="utf-8")
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mocker.patch(
        "backlog_core.backends.bd_runner.subprocess.run", return_value=_proc(returncode=1, stderr=fixture_stderr)
    )

    with pytest.raises(BdInvocationError) as exc_info:
        BdRunner().run_json(["show", "bd-notfound"])

    err = exc_info.value
    assert err.returncode == 1
    assert "bd-notfound" in err.stderr


@pytest.mark.unit
def test_run_json_raises_invocation_error_with_neg1_on_timeout(mocker: MockerFixture) -> None:
    """run_json raises BdInvocationError with returncode=-1 on TimeoutExpired."""
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mocker.patch(
        "backlog_core.backends.bd_runner.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=[_FAKE_BD], timeout=30),
    )

    with pytest.raises(BdInvocationError) as exc_info:
        BdRunner().run_json(["show", "bd-a3f8"])

    assert exc_info.value.returncode == -1


@pytest.mark.unit
def test_run_json_raises_invocation_error_with_neg1_on_oserror(mocker: MockerFixture) -> None:
    """run_json raises BdInvocationError with returncode=-1 when bd fails to launch."""
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mocker.patch("backlog_core.backends.bd_runner.subprocess.run", side_effect=OSError("Permission denied"))

    with pytest.raises(BdInvocationError) as exc_info:
        BdRunner().run_json(["show", "bd-a3f8"])

    assert exc_info.value.returncode == -1


@pytest.mark.unit
def test_run_json_raises_json_decode_error_on_non_json_stdout(mocker: MockerFixture) -> None:
    """run_json raises BdJsonDecodeError when bd stdout is not valid JSON."""
    fixture_content = (_FIXTURES / "bd_invalid_json_stdout.txt").read_text(encoding="utf-8")
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mocker.patch("backlog_core.backends.bd_runner.subprocess.run", return_value=_proc(stdout=fixture_content))

    with pytest.raises(BdJsonDecodeError) as exc_info:
        BdRunner().run_json(["show", "bd-a3f8"])

    assert "Welcome to beads" in exc_info.value.raw_output


# ---------------------------------------------------------------------------
# run_text
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_run_text_returns_raw_stdout(mocker: MockerFixture) -> None:
    """run_text returns raw stdout from bd as-is."""
    fixture_content = (_FIXTURES / "bd_dep_add_success.txt").read_text(encoding="utf-8")
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mocker.patch("backlog_core.backends.bd_runner.subprocess.run", return_value=_proc(stdout=fixture_content))

    result = BdRunner().run_text(["dep", "add", "bd-a3f8", "bd-f7ab"])

    assert result == fixture_content


@pytest.mark.unit
def test_run_text_does_not_inject_json_flag(mocker: MockerFixture) -> None:
    """run_text must NOT inject --json into the argv passed to bd."""
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mock_run = mocker.patch("backlog_core.backends.bd_runner.subprocess.run", return_value=_proc(stdout="ok\n"))

    BdRunner().run_text(["dep", "add", "bd-a3f8", "bd-f7ab"])

    cmd: list[str] = mock_run.call_args.args[0]
    assert "--json" not in cmd


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_is_available_returns_true_when_bd_on_path(mocker: MockerFixture) -> None:
    """is_available returns True when bd is found and the version probe succeeds."""
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mocker.patch("backlog_core.backends.bd_runner.subprocess.run", return_value=_proc(stdout='{"version":"0.4.2"}'))

    assert BdRunner().is_available() is True


@pytest.mark.unit
def test_is_available_returns_false_when_bd_not_on_path(mocker: MockerFixture) -> None:
    """is_available returns False when bd is absent from PATH; does not raise."""
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=None)

    assert BdRunner().is_available() is False


@pytest.mark.unit
def test_is_available_returns_false_on_subprocess_error(mocker: MockerFixture) -> None:
    """is_available returns False on OSError from subprocess; does not raise."""
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mocker.patch("backlog_core.backends.bd_runner.subprocess.run", side_effect=OSError("exec failed"))

    assert BdRunner().is_available() is False


@pytest.mark.unit
def test_is_available_caches_after_first_call(mocker: MockerFixture) -> None:
    """is_available does not re-probe bd on subsequent calls."""
    mock_which = mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mocker.patch("backlog_core.backends.bd_runner.subprocess.run", return_value=_proc())

    runner = BdRunner()
    first = runner.is_available()
    second = runner.is_available()

    assert first is second is True
    mock_which.assert_called_once()


# ---------------------------------------------------------------------------
# _resolve_bd_path caching
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_resolve_bd_path_caches_after_first_call(mocker: MockerFixture) -> None:
    """_resolve_bd_path caches the located path; second call skips shutil.which."""
    mock_which = mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)

    runner = BdRunner()
    path1 = runner._resolve_bd_path()
    path2 = runner._resolve_bd_path()

    assert path1 == path2 == _FAKE_BD
    mock_which.assert_called_once()


# ---------------------------------------------------------------------------
# _bd_env — GITHUB_TOKEN filtering
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_bd_env_removes_github_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """_bd_env strips GITHUB_TOKEN to prevent credential leakage into bd subprocesses."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_supersecret")
    monkeypatch.setenv("HOME", "/home/testuser")

    env = _bd_env()

    assert "GITHUB_TOKEN" not in env
    assert "HOME" in env


@pytest.mark.unit
def test_bd_env_passes_non_blocked_vars_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """_bd_env passes through all variables that are not on the block list."""
    monkeypatch.setenv("MY_CUSTOM_VAR", "custom_value")

    env = _bd_env()

    assert env["MY_CUSTOM_VAR"] == "custom_value"


# ---------------------------------------------------------------------------
# env_overrides — constructor parameter (architect spec §4.1 line 214)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_init_stores_env_overrides() -> None:
    """BdRunner stores env_overrides for use in subprocess invocations."""
    runner = BdRunner(env_overrides={"MY_VAR": "my_value"})
    assert runner._env_overrides == {"MY_VAR": "my_value"}


@pytest.mark.unit
def test_init_env_overrides_defaults_to_none() -> None:
    """BdRunner defaults env_overrides to None."""
    runner = BdRunner()
    assert runner._env_overrides is None


@pytest.mark.unit
def test_run_json_passes_env_overrides_to_subprocess(mocker: MockerFixture) -> None:
    """run_json merges env_overrides into the subprocess environment."""
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mock_run = mocker.patch("backlog_core.backends.bd_runner.subprocess.run", return_value=_proc(stdout='{"ok": true}'))

    BdRunner(env_overrides={"BD_TEST_VAR": "test_value"}).run_json(["show", "bd-a3f8"])

    assert mock_run.call_args.kwargs["env"]["BD_TEST_VAR"] == "test_value"


@pytest.mark.unit
def test_env_overrides_take_precedence_over_inherited_env(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """env_overrides values override inherited process environment variables."""
    monkeypatch.setenv("BD_EXISTING_VAR", "original_value")
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mock_run = mocker.patch("backlog_core.backends.bd_runner.subprocess.run", return_value=_proc(stdout='{"ok": true}'))

    BdRunner(env_overrides={"BD_EXISTING_VAR": "overridden_value"}).run_json(["show", "bd-a3f8"])

    assert mock_run.call_args.kwargs["env"]["BD_EXISTING_VAR"] == "overridden_value"


@pytest.mark.unit
def test_env_overrides_none_preserves_inherited_env_without_blocked_vars(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """env_overrides=None passes inherited env minus blocked vars, same as no overrides."""
    monkeypatch.setenv("HOME", "/home/testuser")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mock_run = mocker.patch("backlog_core.backends.bd_runner.subprocess.run", return_value=_proc(stdout='{"ok": true}'))

    BdRunner(env_overrides=None).run_json(["show", "bd-a3f8"])

    env = mock_run.call_args.kwargs["env"]
    assert "HOME" in env
    assert "GITHUB_TOKEN" not in env


@pytest.mark.unit
def test_env_overrides_cannot_inject_blocked_vars(mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """Blocked vars (e.g. GITHUB_TOKEN) in env_overrides are silently stripped."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mock_run = mocker.patch("backlog_core.backends.bd_runner.subprocess.run", return_value=_proc(stdout='{"ok": true}'))

    BdRunner(env_overrides={"GITHUB_TOKEN": "injected", "SAFE_VAR": "ok"}).run_json(["show", "bd-a3f8"])

    env = mock_run.call_args.kwargs["env"]
    assert "GITHUB_TOKEN" not in env
    assert env["SAFE_VAR"] == "ok"


@pytest.mark.unit
def test_is_available_passes_env_overrides_to_subprocess(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """is_available passes env_overrides into its subprocess call, stripping blocked vars."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value=_FAKE_BD)
    mock_run = mocker.patch("backlog_core.backends.bd_runner.subprocess.run", return_value=_proc())

    BdRunner(env_overrides={"BD_AVAIL_VAR": "check_value"}).is_available()

    env = mock_run.call_args.kwargs["env"]
    assert env["BD_AVAIL_VAR"] == "check_value"
    assert "GITHUB_TOKEN" not in env
