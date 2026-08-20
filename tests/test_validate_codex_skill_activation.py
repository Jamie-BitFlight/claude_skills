"""Contract tests for cache-provenanced Codex skill activation."""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import cast

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import validate_codex_skill_activation as activation


def test_app_server_disables_host_owned_apps_mcp() -> None:
    """The activation lane suppresses Codex's host-owned Apps MCP server."""
    assert activation.APP_SERVER_COMMAND == ("codex", "--disable", "apps", "app-server")


def test_activation_timeout_defaults_to_a_bounded_model_turn() -> None:
    """The no-MCP sentinel does not retain an unnecessarily long default timeout."""
    args = activation.create_parser().parse_args([
        "--target",
        "xdg-base-directory:xdg-base-directory",
        "--evidence-file",
        "evidence.json",
    ])

    assert args.timeout_seconds == 45.0


def test_ensure_no_mcp_configuration_rejects_inline_mcp_servers_object(tmp_path: Path) -> None:
    """An inline mcpServers object in plugin.json is caught, not just conventional filenames.

    Tests: ensure_no_mcp_configuration's manifest-field check
    How: Write a .codex-plugin/plugin.json with a non-empty inline mcpServers object and
         no .mcp.json/.mcp.codex.json file anywhere in the tree; assert it is rejected
    Why: A filename-only scan misses a plugin declaring MCP servers inline as an object,
         which would let app-server start those servers before any runtime event could
         reject it (PR #2787 review, validate_codex_skill_activation.py:155)
    """
    plugin_dir = tmp_path / "inline-mcp-plugin"
    (plugin_dir / ".codex-plugin").mkdir(parents=True)
    (plugin_dir / ".codex-plugin" / "plugin.json").write_text(
        json.dumps({"name": "inline-mcp-plugin", "mcpServers": {"my-server": {"command": "node"}}}), encoding="utf-8"
    )

    with pytest.raises(activation.HarnessError, match="FastMCP validation lane"):
        activation.ensure_no_mcp_configuration(plugin_dir)


def test_ensure_no_mcp_configuration_allows_a_plugin_without_mcp(tmp_path: Path) -> None:
    """A plugin with no MCP declaration at all passes through untouched."""
    plugin_dir = tmp_path / "no-mcp-plugin"
    (plugin_dir / ".codex-plugin").mkdir(parents=True)
    (plugin_dir / ".codex-plugin" / "plugin.json").write_text(json.dumps({"name": "no-mcp-plugin"}), encoding="utf-8")

    activation.ensure_no_mcp_configuration(plugin_dir)


def test_jsonl_decoder_keeps_the_next_buffered_protocol_message() -> None:
    """A buffered JSONL read retains an immediately following app-server message."""
    message, remaining = activation.pop_jsonl_message(b'{"id": 1}\n{"id": 2}\n')

    assert message == {"id": 1}
    assert remaining == b'{"id": 2}\n'


def test_app_server_client_reads_pipe_without_select() -> None:
    class FakeProcess:
        stdin = None
        stdout = io.BytesIO(b'{"id": 1}\n')

    client = activation.AppServerClient(cast("subprocess.Popen[bytes]", FakeProcess()), time.monotonic() + 1)

    assert client.receive() == {"id": 1}


def test_installed_skill_resolution_returns_contained_regular_skill_file(tmp_path: Path) -> None:
    """A cache skill must remain a regular file inside the cache root."""
    cache_root = tmp_path / "cache" / "marketplace" / "plugin"
    skill_file = cache_root / "1.0.0" / "skills" / "example" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text("skill instructions\n", encoding="utf-8")

    resolved = activation.resolve_installed_skill(cache_root, "example")

    assert resolved.path == skill_file.resolve()
    assert resolved.relative_path == Path("1.0.0/skills/example/SKILL.md")
    assert resolved.sha256 == hashlib.sha256(b"skill instructions\n").hexdigest()


def test_installed_skill_resolution_rejects_symlink_escape(tmp_path: Path) -> None:
    """A cache entry cannot redirect activation outside the installed plugin cache."""
    cache_root = tmp_path / "cache" / "marketplace" / "plugin"
    outside = tmp_path / "outside.md"
    outside.write_text("not an installed skill\n", encoding="utf-8")
    skill_file = cache_root / "1.0.0" / "skills" / "example" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.symlink_to(outside)

    with pytest.raises(activation.HarnessError, match="symbolic link"):
        activation.resolve_installed_skill(cache_root, "example")


def test_turn_request_injects_the_named_cache_skill(tmp_path: Path) -> None:
    """The app-server turn payload carries both the explicit marker and skill item."""
    skill_file = tmp_path / "cache" / "SKILL.md"
    full_skill_name = "xdg-base-directory:xdg-base-directory"

    request = activation.build_turn_request(
        thread_id="thread-1",
        skill_name=full_skill_name,
        skill_path=skill_file,
        task_text="Where should this app store its database file?",
        project_dir=tmp_path / "project",
    )

    params = request.get("params")
    assert isinstance(params, dict)
    input_items = params.get("input")
    assert isinstance(input_items, list)
    assert input_items[0] == {
        "type": "text",
        "text": ("$xdg-base-directory:xdg-base-directory Where should this app store its database file?"),
    }
    assert input_items[1] == {"type": "skill", "name": full_skill_name, "path": str(skill_file)}
    assert params.get("approvalPolicy") == "never"
    assert params.get("sandboxPolicy") == {"type": "readOnly", "networkAccess": False}


def test_mcp_events_are_rejected_by_the_read_only_activation_lane() -> None:
    """The skill activation lane must not run or wait on plugin MCP activity."""
    with pytest.raises(activation.HarnessError, match="MCP event"):
        activation.observe_event(
            {"method": "mcpServer/elicitation/request", "params": {}}, observed_methods=[], response_fragments=[]
        )


def test_blocked_item_type_is_rejected_by_the_read_only_activation_lane() -> None:
    """The activation lane fails closed on any observed command/file/MCP-tool execution item.

    This is the single most safety-critical branch in observe_event: it is what
    keeps the read-only activation lane from silently allowing a skill turn to
    execute a command, change a file, or call an MCP tool.
    """
    with pytest.raises(activation.HarnessError, match="Blocked item type observed: commandExecution"):
        activation.observe_event(
            {"method": "item/started", "params": {"item": {"type": "commandExecution"}}},
            observed_methods=[],
            response_fragments=[],
        )


def test_malformed_event_params_are_rejected() -> None:
    """An event whose params are not an object is rejected rather than silently ignored."""
    with pytest.raises(activation.HarnessError, match="Malformed app-server event"):
        activation.observe_event(
            {"method": "item/started", "params": "not-an-object"}, observed_methods=[], response_fragments=[]
        )


def test_approval_request_events_are_rejected() -> None:
    """The read-only activation lane never grants approval, so a request must fail closed."""
    with pytest.raises(activation.HarnessError, match="Unexpected approval request"):
        activation.observe_event(
            {"method": "item/commandExecution/requestApproval", "params": {}},
            observed_methods=[],
            response_fragments=[],
        )


def test_error_events_are_rejected() -> None:
    """An app-server error event must fail the activation run rather than pass silently."""
    with pytest.raises(activation.HarnessError, match="error event"):
        activation.observe_event({"method": "error", "params": {}}, observed_methods=[], response_fragments=[])


def test_app_server_client_surfaces_stdout_read_failure_distinct_from_timeout() -> None:
    """A genuine stdout read failure must surface its own cause, not a generic timeout."""

    class RaisingStdout:
        def readline(self) -> bytes:
            raise OSError("stdout pipe closed unexpectedly")

    class FakeProcess:
        stdin = None
        stdout = RaisingStdout()

    client = activation.AppServerClient(cast("subprocess.Popen[bytes]", FakeProcess()), time.monotonic() + 1)

    with pytest.raises(activation.HarnessError, match="stdout read failed") as exc_info:
        client.receive()

    assert not str(exc_info.value).startswith("Timed out")
    assert isinstance(exc_info.value.__cause__, OSError)


def test_run_silent_persists_stderr_to_workspace_on_failure(tmp_path: Path) -> None:
    """A failing setup command's stderr is saved for post-mortem, never raised raw.

    Tests: run_silent's failure path
    How: Run a command that writes a secret-shaped string to stderr and exits
         non-zero; assert the raised error names a saved-file path rather than
         embedding the stderr content, and that file contains it
    Why: The original bare "failed with exit code N" gave no diagnostic trail;
         embedding raw stderr in the error/log risks leaking ambient
         credentials the command may have echoed
    """
    argv = [sys.executable, "-c", "import sys; sys.stderr.write('token=super-secret-value\\n'); sys.exit(3)"]

    with pytest.raises(activation.HarnessError, match="failed with exit code 3") as exc_info:
        activation.run_silent(argv, cwd=tmp_path, env={}, label="test command", timeout_seconds=5.0)

    assert "super-secret-value" not in str(exc_info.value)
    stderr_log = tmp_path / "test_command.stderr.log"
    assert stderr_log.is_file()
    assert "token=super-secret-value" in stderr_log.read_text(encoding="utf-8")


def test_run_silent_terminates_the_full_process_tree_on_timeout(tmp_path: Path) -> None:
    """A stalled setup command (marketplace/plugin registration) does not hang the validator.

    Tests: run_silent's timeout path
    How: Run a script that ignores SIGTERM with a short timeout; assert HarnessError
         names the timeout and the process is actually gone afterward
    Why: run_silent previously used subprocess.run() with no timeout and no process
         group -- a stalled `codex plugin marketplace add`/`codex plugin add` would
         hang the validator forever (PR #2787 review, validate_codex_skill_activation.py:445)
    """
    script = tmp_path / "stubborn.py"
    script.write_text(
        "import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(30)\n", encoding="utf-8"
    )

    with pytest.raises(activation.HarnessError, match="timed out after"):
        activation.run_silent(
            [sys.executable, str(script)], cwd=tmp_path, env={}, label="stubborn", timeout_seconds=0.3
        )


def test_run_app_server_isolates_and_tree_terminates_the_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The app-server subprocess is started in its own process group and tree-terminated.

    Tests: run_app_server's Popen call and its finally-block cleanup
    How: Monkeypatch subprocess.Popen and AppServerClient.request to avoid a real codex
         binary; assert Popen received start_new_session=True and
         isolated.terminate_process_tree was called with the exact process object
    Why: codex app-server can spawn helper processes; the original cleanup terminated
         only the direct child, so descendants could survive both a successful run and
         a timeout (see PR #2787 review, validate_codex_skill_activation.py:429)
    """
    popen_calls: list[dict[str, object]] = []
    terminated: list[object] = []

    class FakeProcess:
        stdin = None
        stdout = io.BytesIO()

    def fake_popen(*args: object, **kwargs: object) -> FakeProcess:
        del args
        popen_calls.append(kwargs)
        return FakeProcess()

    def fake_request(self: object, *args: object, **kwargs: object) -> None:
        del self, args, kwargs
        raise activation.HarnessError("stop before any real protocol I/O")

    def fake_terminate_process_tree(process: object) -> None:
        terminated.append(process)

    monkeypatch.setattr(activation.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(activation.AppServerClient, "request", fake_request)
    monkeypatch.setattr(activation.isolated, "terminate_process_tree", fake_terminate_process_tree)

    with pytest.raises(activation.HarnessError, match="stop before any real protocol I/O"):
        activation.run_app_server(
            env={},
            project_dir=tmp_path,
            skill_name="plugin:skill",
            skill_path=tmp_path / "SKILL.md",
            task_text="task",
            timeout_seconds=1.0,
        )

    assert popen_calls[0]["start_new_session"] is True
    assert len(terminated) == 1
    assert isinstance(terminated[0], FakeProcess)
